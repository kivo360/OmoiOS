"""Credential broker service for secure credential storage and injection.

Provides:
- Credential CRUD operations with encryption
- Workspace-scoped credential binding
- Audit logging for all access
- Secure injection into sandboxes
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import httpx
from jose import jwt

from omoi_os.logging import get_logger
from omoi_os.models.credential_access_log import CredentialAccessLog
from omoi_os.models.credential_binding import CredentialBinding
from omoi_os.models.environment import EnvironmentVersion
from omoi_os.models.sandbox_session import SandboxSession
from omoi_os.models.user_credentials import UserCredential
from omoi_os.services.credential_encryption import (
    CredentialEncryptionService,
    get_credential_encryption_service,
)
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)

# Valid binding kinds
VALID_BINDING_KINDS = {"bearer_secret", "user_oauth", "github_app"}
OAUTH_REFRESH_WINDOW = timedelta(minutes=5)
GITHUB_APP_JWT_TTL = timedelta(minutes=9)


class CredentialBrokerError(Exception):
    """Base exception for credential broker errors."""

    pass


class InvalidBindingKindError(CredentialBrokerError):
    """Raised when an invalid binding kind is specified."""

    pass


class UnsupportedBindingKindError(CredentialBrokerError):
    """Raised when an alias references an unsupported binding kind."""

    pass


class UnknownAliasError(CredentialBrokerError):
    """Raised when an environment version does not define a credential alias."""

    def __init__(self, alias: str):
        super().__init__(f"Unknown credential alias: {alias}")


class CredentialNotFoundError(CredentialBrokerError):
    """Raised when a credential is not found."""

    pass


class CredentialBrokerService:
    """Service for managing encrypted credentials bound to workspaces.

    Provides secure storage and injection of credentials with:
    - Fernet AES-256-GCM encryption
    - Workspace-scoped access control
    - Comprehensive audit logging
    - Support for multiple binding kinds
    """

    def __init__(
        self,
        db: Optional[DatabaseService] = None,
        encryption: Optional[CredentialEncryptionService] = None,
    ):
        """Initialize credential broker service.

        Args:
            db: Database service (optional, for testing)
            encryption: Encryption service (optional, for testing)
        """
        self._db = db
        self._encryption = encryption

    def _get_db(self) -> DatabaseService:
        """Get database service, initializing if needed."""
        if self._db is None:
            from omoi_os.config import get_app_settings

            settings = get_app_settings()
            self._db = DatabaseService(connection_string=settings.database.url)
        return self._db

    def _get_encryption(self) -> CredentialEncryptionService:
        """Get encryption service, initializing if needed."""
        if self._encryption is None:
            self._encryption = get_credential_encryption_service()
        return self._encryption

    def _write_access_log(
        self,
        workspace_id: UUID,
        action: str,
        credential_binding_id: Optional[UUID] = None,
        sandbox_session_id: Optional[UUID] = None,
        actor: Optional[str] = None,
        access_metadata: Optional[dict] = None,
    ) -> None:
        """Write an access log entry.

        Args:
            workspace_id: Workspace ID for scoping
            action: Action type (create, read, delete, inject)
            credential_binding_id: Optional credential binding ID
            actor: Optional user ID or agent ID
            access_metadata: Optional additional metadata
        """
        db = self._get_db()
        with db.get_session() as session:
            log_entry = CredentialAccessLog(
                credential_binding_id=credential_binding_id,
                sandbox_session_id=sandbox_session_id,
                workspace_id=workspace_id,
                action=action,
                actor=actor,
                accessed_at=utc_now(),
                access_metadata=access_metadata or {},
            )
            session.add(log_entry)
            session.commit()

    async def resolve_aliases_for_spawn(
        self,
        environment_version_id: UUID,
        workspace_id: UUID,
    ) -> dict[str, dict]:
        """Resolve every alias on an env_version for inline sandbox injection.

        Variant of ``resolve_alias`` that doesn't require a SandboxSession
        — used by sandbox spawners (Modal/Daytona) that need to render
        ``auth.json`` directly into the sandbox filesystem at create time
        because bootstrap.sh never executes there.

        Returns ``{alias: payload}`` shaped exactly like ``resolve_alias``
        — drops aliases whose binding can't be resolved (missing,
        wrong workspace) so a single broken alias doesn't kill spawn.
        """
        env_version = self._load_env_version(environment_version_id)
        out: dict[str, dict] = {}
        for alias, mapping in (env_version.credentials or {}).items():
            if not isinstance(mapping, dict):
                continue
            kind = mapping.get("kind")
            try:
                if kind == "bearer_secret":
                    binding_id = self._required_mapping_uuid(mapping, "binding_id")
                    binding = self._load_workspace_binding(
                        binding_id=binding_id,
                        workspace_id=workspace_id,
                        expected_kind="bearer_secret",
                    )
                    out[alias] = {
                        "kind": "bearer_secret",
                        "value": self._decrypt_secret_value(binding.encrypted_value),
                    }
                elif kind == "github_app":
                    out[alias] = await self._resolve_github_app(mapping)
                elif kind == "user_oauth":
                    # OAuth refresh requires a SandboxSession for refresh
                    # flows; skip in spawn-time path. Spawner will rely on
                    # bootstrap broker fetch for this kind (or on the
                    # bearer_secret variant).
                    logger.info(
                        "Skipping user_oauth alias in spawn-time auth.json render",
                        extra={"alias": alias},
                    )
                    continue
                else:
                    continue
            except CredentialBrokerError as exc:
                logger.warning(
                    "Spawn-time alias resolution failed",
                    extra={"alias": alias, "kind": kind, "error": str(exc)},
                )
                continue
        return out

    async def resolve_alias(self, session: SandboxSession, alias: str) -> dict:
        """Resolve a credential alias from the session's environment version.

        Args:
            session: Sandbox session whose pinned environment version defines aliases.
            alias: Alias name from ``environment_versions.credentials``.

        Returns:
            Per-kind credential payload. Plaintext values are returned only to the
            caller and are never logged.

        Raises:
            UnknownAliasError: If the alias is not present on the environment version.
            UnsupportedBindingKindError: If the alias uses an unsupported kind.
            CredentialNotFoundError: If a referenced credential does not exist or is
                outside the session workspace.
            CredentialBrokerError: If a credential cannot be decrypted or minted.
        """
        env_version = self._load_env_version(session.environment_version_id)
        mapping = (env_version.credentials or {}).get(alias)
        if mapping is None:
            raise UnknownAliasError(alias)
        if not isinstance(mapping, dict):
            raise CredentialBrokerError("Credential alias mapping is malformed")

        kind = mapping.get("kind")
        if kind == "bearer_secret":
            payload = self._resolve_bearer_secret(session, mapping)
        elif kind == "user_oauth":
            payload = await self._resolve_user_oauth(session, mapping)
        elif kind == "github_app":
            payload = await self._resolve_github_app(mapping)
        else:
            raise UnsupportedBindingKindError(f"Unsupported binding kind: {kind}")

        self._audit(session, alias, kind)
        return payload

    def _load_env_version(self, environment_version_id: UUID) -> EnvironmentVersion:
        """Load the pinned environment version for alias resolution."""
        db = self._get_db()
        with db.get_session() as db_session:
            env_version = db_session.get(EnvironmentVersion, environment_version_id)
            if env_version is None:
                raise CredentialBrokerError("Environment version not found")
            db_session.expunge(env_version)
            return env_version

    def _audit(self, session: SandboxSession, alias: str, kind: str) -> None:
        """Write a sandbox-scoped credential resolution audit event."""
        self._write_access_log(
            workspace_id=session.workspace_id,
            action="inject",
            sandbox_session_id=session.id,
            actor=f"sandbox_session:{session.session_token_prefix}",
            access_metadata={"alias": alias, "kind": kind},
        )

    def _resolve_bearer_secret(
        self,
        session: SandboxSession,
        mapping: dict,
    ) -> dict:
        """Resolve a bearer secret alias to plaintext."""
        binding_id = self._required_mapping_uuid(mapping, "binding_id")
        binding = self._load_workspace_binding(
            binding_id=binding_id,
            workspace_id=session.workspace_id,
            expected_kind="bearer_secret",
        )
        return {
            "kind": "bearer_secret",
            "value": self._decrypt_secret_value(binding.encrypted_value),
        }

    async def _resolve_user_oauth(
        self,
        session: SandboxSession,
        mapping: dict,
    ) -> dict:
        """Resolve a user OAuth alias, refreshing near-expiry tokens fail-closed."""
        credential_id = self._required_mapping_uuid(
            mapping,
            "credential_id",
            "user_credential_id",
            "binding_id",
        )
        credential = self._load_user_credential(credential_id)
        expires_at = self._parse_expires_at(
            (credential.config_data or {}).get("expires_at")
            or mapping.get("expires_at")
        )
        if expires_at is None:
            raise CredentialBrokerError("OAuth credential expiry is missing")

        if self._is_near_expiry(expires_at):
            refreshed_payload = await self._refresh_user_oauth(credential, mapping)
            if refreshed_payload is None:
                raise CredentialBrokerError(
                    "OAuth credential is near expiry and cannot be refreshed"
                )
            access_token = refreshed_payload["access_token"]
            expires_at = self._parse_expires_at(refreshed_payload["expires_at"])
            if expires_at is None:
                raise CredentialBrokerError(
                    "Refreshed OAuth credential expiry is missing"
                )
            self._store_refreshed_user_oauth(credential.id, access_token, expires_at)
        else:
            access_token = self._decrypt_user_credential(credential)

        return {
            "kind": "user_oauth",
            "access_token": access_token,
            "expires_at": expires_at.isoformat(),
        }

    async def _resolve_github_app(self, mapping: dict) -> dict:
        """Resolve a GitHub App alias by minting an installation token."""
        token_response = await self._request_github_installation_token(mapping)
        token = token_response.get("token")
        expires_at = self._parse_expires_at(token_response.get("expires_at"))
        if not token or expires_at is None:
            raise CredentialBrokerError(
                "GitHub App installation token response is invalid"
            )
        return {
            "kind": "github_app",
            "token": token,
            "expires_at": expires_at.isoformat(),
        }

    def _load_workspace_binding(
        self,
        binding_id: UUID,
        workspace_id: UUID,
        expected_kind: str,
    ) -> CredentialBinding:
        """Load a credential binding scoped to the sandbox workspace."""
        db = self._get_db()
        with db.get_session() as db_session:
            binding = db_session.get(CredentialBinding, binding_id)
            if (
                binding is None
                or binding.workspace_id != workspace_id
                or binding.kind != expected_kind
            ):
                raise CredentialNotFoundError(
                    "Credential binding not found in requested workspace"
                )
            db_session.expunge(binding)
            return binding

    def _load_user_credential(self, credential_id: UUID) -> UserCredential:
        """Load an active user credential by id."""
        db = self._get_db()
        with db.get_session() as db_session:
            credential = db_session.get(UserCredential, credential_id)
            if credential is None or not credential.is_active:
                raise CredentialNotFoundError("User OAuth credential not found")
            db_session.expunge(credential)
            return credential

    def _decrypt_secret_value(self, encrypted_value: str) -> str:
        """Decrypt an encrypted credential without exposing details on failure."""
        encryption = self._get_encryption()
        if not encryption.is_configured:
            raise CredentialBrokerError(
                "Credential encryption is not configured. "
                "Set CREDENTIAL_ENCRYPTION_KEY environment variable."
            )
        try:
            return encryption.decrypt(encrypted_value)
        except Exception as exc:
            logger.error("Failed to decrypt credential value", error=str(exc))
            raise CredentialBrokerError("Failed to decrypt credential value") from exc

    def _decrypt_user_credential(self, credential: UserCredential) -> str:
        """Return the OAuth access token from encrypted storage or legacy plaintext."""
        if credential.encrypted_value:
            return self._decrypt_secret_value(credential.encrypted_value)
        return credential.api_key

    async def _refresh_user_oauth(
        self,
        credential: UserCredential,
        mapping: dict,
    ) -> Optional[dict]:
        """Refresh a near-expiry OAuth credential.

        Provider-specific refresh clients are intentionally not coupled into the
        broker. Tests and future provider adapters can override this seam; v1
        fails closed if no adapter is supplied.
        """
        return None

    def _store_refreshed_user_oauth(
        self,
        credential_id: UUID,
        access_token: str,
        expires_at: datetime,
    ) -> None:
        """Persist refreshed OAuth token material encrypted at rest."""
        encrypted_value = self._get_encryption().encrypt(access_token)
        db = self._get_db()
        with db.get_session() as db_session:
            credential = db_session.get(UserCredential, credential_id)
            if credential is None:
                raise CredentialNotFoundError("User OAuth credential not found")
            credential.encrypted_value = encrypted_value
            credential.config_data = {
                **(credential.config_data or {}),
                "expires_at": expires_at.isoformat(),
            }
            credential.last_used_at = utc_now()
            db_session.commit()

    async def _request_github_installation_token(self, mapping: dict) -> dict:
        """Mint a GitHub App installation token from alias mapping details."""
        installation_id = mapping.get("installation_id")
        if not installation_id:
            raise CredentialBrokerError("GitHub App installation ID is missing")

        app_jwt = mapping.get("app_jwt") or self._create_github_app_jwt(mapping)
        url = (
            f"https://api.github.com/app/installations/{installation_id}/access_tokens"
        )
        headers = {
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers)
            response.raise_for_status()
            return response.json()

    def _create_github_app_jwt(self, mapping: dict) -> str:
        """Create a short-lived GitHub App JWT for installation token minting."""
        app_id = mapping.get("app_id")
        private_key = self._load_github_app_private_key(mapping)
        if not app_id:
            raise CredentialBrokerError("GitHub App ID is missing")

        now = utc_now()
        token_claims = {
            "iat": int((now - timedelta(seconds=60)).timestamp()),
            "exp": int((now + GITHUB_APP_JWT_TTL).timestamp()),
            "iss": str(app_id),
        }
        return jwt.encode(token_claims, private_key, algorithm="RS256")

    def _load_github_app_private_key(self, mapping: dict) -> str:
        """Load a GitHub App private key from encrypted mapping references."""
        encrypted_private_key = mapping.get("encrypted_private_key")
        if encrypted_private_key:
            return self._decrypt_secret_value(encrypted_private_key)

        private_key_binding_id = mapping.get("private_key_binding_id")
        if private_key_binding_id:
            binding_id = self._required_mapping_uuid(mapping, "private_key_binding_id")
            db = self._get_db()
            with db.get_session() as db_session:
                binding = db_session.get(CredentialBinding, binding_id)
                if binding is None or binding.kind != "bearer_secret":
                    raise CredentialNotFoundError("GitHub App private key not found")
                return self._decrypt_secret_value(binding.encrypted_value)

        private_key = mapping.get("private_key")
        if private_key:
            return str(private_key)

        raise CredentialBrokerError("GitHub App private key is missing")

    def _required_mapping_uuid(self, mapping: dict, *keys: str) -> UUID:
        """Return the first UUID value found for the provided mapping keys."""
        for key in keys:
            value = mapping.get(key)
            if value:
                return UUID(str(value))
        raise CredentialBrokerError("Credential alias mapping is missing a reference")

    def _parse_expires_at(self, value: object) -> Optional[datetime]:
        """Parse ISO8601 expiry values from mapping or credential config."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        raise CredentialBrokerError("Credential expiry format is invalid")

    def _is_near_expiry(self, expires_at: datetime) -> bool:
        """Return whether a credential should be refreshed before use."""
        return expires_at <= utc_now() + OAUTH_REFRESH_WINDOW

    def create_binding(
        self,
        workspace_id: UUID,
        kind: str,
        name: str,
        value: str,
        config: Optional[dict] = None,
        actor: Optional[str] = None,
    ) -> CredentialBinding:
        """Create a new credential binding.

        Args:
            workspace_id: Workspace ID that owns this credential
            kind: Binding kind (bearer_secret, user_oauth, github_app)
            name: Human-readable name for the credential
            value: Plaintext credential value (will be encrypted)
            config: Optional additional configuration
            actor: Optional user ID or agent ID for audit log

        Returns:
            Created CredentialBinding model

        Raises:
            InvalidBindingKindError: If kind is not valid
            CredentialBrokerError: If encryption is not configured
        """
        # Validate kind
        if kind not in VALID_BINDING_KINDS:
            raise InvalidBindingKindError(
                f"Invalid binding kind '{kind}'. Must be one of: {VALID_BINDING_KINDS}"
            )

        # Get encryption service
        encryption = self._get_encryption()
        if not encryption.is_configured:
            raise CredentialBrokerError(
                "Credential encryption is not configured. "
                "Set CREDENTIAL_ENCRYPTION_KEY environment variable."
            )

        # Encrypt the value
        try:
            encrypted_value = encryption.encrypt(value)
        except Exception as e:
            logger.error("Failed to encrypt credential value", error=str(e))
            raise CredentialBrokerError("Failed to encrypt credential value") from e

        db = self._get_db()
        with db.get_session() as session:
            binding = CredentialBinding(
                workspace_id=workspace_id,
                kind=kind,
                name=name,
                encrypted_value=encrypted_value,
                config=config or {},
                version=1,
                created_at=utc_now(),
                rotated_at=None,
            )
            session.add(binding)
            session.commit()
            session.refresh(binding)

            logger.info(
                "Credential binding created",
                binding_id=str(binding.id),
                workspace_id=str(workspace_id),
                kind=kind,
                name=name,
            )

            # Write audit log
            self._write_access_log(
                workspace_id=workspace_id,
                action="create",
                credential_binding_id=binding.id,
                actor=actor,
                access_metadata={"kind": kind, "name": name},
            )

            session.expunge(binding)
            return binding

    def list_bindings(
        self,
        workspace_id: UUID,
        actor: Optional[str] = None,
    ) -> list[CredentialBinding]:
        """List all credential bindings in a workspace.

        Args:
            workspace_id: Workspace ID to filter by
            actor: Optional user ID or agent ID for audit log

        Returns:
            List of CredentialBinding models (without decrypted values)
        """
        db = self._get_db()
        with db.get_session() as session:
            bindings = (
                session.query(CredentialBinding)
                .filter(CredentialBinding.workspace_id == workspace_id)
                .order_by(CredentialBinding.created_at.desc())
                .all()
            )

            # Write audit log for list operation (no specific binding ID)
            self._write_access_log(
                workspace_id=workspace_id,
                action="read",
                credential_binding_id=None,
                actor=actor,
                access_metadata={"count": len(bindings)},
            )

            for binding in bindings:
                session.expunge(binding)
            return bindings

    def get_binding(
        self,
        binding_id: UUID,
        actor: Optional[str] = None,
    ) -> CredentialBinding:
        """Get a credential binding by ID.

        Args:
            binding_id: Credential binding ID
            actor: Optional user ID or agent ID for audit log

        Returns:
            CredentialBinding model

        Raises:
            CredentialNotFoundError: If binding not found
        """
        db = self._get_db()
        with db.get_session() as session:
            binding = (
                session.query(CredentialBinding)
                .filter(CredentialBinding.id == binding_id)
                .first()
            )

            if binding is None:
                raise CredentialNotFoundError(
                    f"Credential binding not found: {binding_id}"
                )

            # Write audit log
            self._write_access_log(
                workspace_id=binding.workspace_id,
                action="read",
                credential_binding_id=binding.id,
                actor=actor,
                access_metadata={"kind": binding.kind, "name": binding.name},
            )

            session.expunge(binding)
            return binding

    def delete_binding(
        self,
        binding_id: UUID,
        actor: Optional[str] = None,
    ) -> None:
        """Delete a credential binding.

        Args:
            binding_id: Credential binding ID
            actor: Optional user ID or agent ID for audit log

        Raises:
            CredentialNotFoundError: If binding not found
        """
        db = self._get_db()
        with db.get_session() as session:
            binding = (
                session.query(CredentialBinding)
                .filter(CredentialBinding.id == binding_id)
                .first()
            )

            if binding is None:
                raise CredentialNotFoundError(
                    f"Credential binding not found: {binding_id}"
                )

            workspace_id = binding.workspace_id
            kind = binding.kind
            name = binding.name

            session.delete(binding)
            session.commit()

            logger.info(
                "Credential binding deleted",
                binding_id=str(binding_id),
                workspace_id=str(workspace_id),
            )

            # Write audit log
            self._write_access_log(
                workspace_id=workspace_id,
                action="delete",
                credential_binding_id=binding_id,
                actor=actor,
                access_metadata={"kind": kind, "name": name},
            )

    def inject_credentials(
        self,
        workspace_id: UUID,
        actor: Optional[str] = None,
    ) -> dict[str, str]:
        """Get decrypted credentials for injection into a sandbox.

        Returns a dictionary mapping environment variable names to
        decrypted credential values. Each credential is logged as
        an inject action in the audit log.

        Args:
            workspace_id: Workspace ID to get credentials for
            actor: Optional user ID or agent ID for audit log

        Returns:
            Dictionary of {env_var_name: decrypted_value}

        Raises:
            CredentialBrokerError: If decryption fails
        """
        db = self._get_db()
        encryption = self._get_encryption()

        if not encryption.is_configured:
            raise CredentialBrokerError(
                "Credential encryption is not configured. "
                "Set CREDENTIAL_ENCRYPTION_KEY environment variable."
            )

        with db.get_session() as session:
            bindings = (
                session.query(CredentialBinding)
                .filter(CredentialBinding.workspace_id == workspace_id)
                .all()
            )

            result = {}
            for binding in bindings:
                # Decrypt the value
                try:
                    decrypted_value = encryption.decrypt(binding.encrypted_value)
                except Exception as e:
                    logger.error(
                        "Failed to decrypt credential",
                        binding_id=str(binding.id),
                        error=str(e),
                    )
                    raise CredentialBrokerError(
                        f"Failed to decrypt credential '{binding.name}'"
                    ) from e

                # Build env var name: OMOIOS_CRED_<KIND>_<NAME>
                # Replace non-alphanumeric with underscore
                safe_name = "".join(
                    c if c.isalnum() else "_" for c in binding.name
                ).upper()
                env_var_name = f"OMOIOS_CRED_{binding.kind.upper()}_{safe_name}"
                result[env_var_name] = decrypted_value

                # Write audit log for each injected credential
                self._write_access_log(
                    workspace_id=workspace_id,
                    action="inject",
                    credential_binding_id=binding.id,
                    actor=actor,
                    access_metadata={
                        "kind": binding.kind,
                        "name": binding.name,
                        "env_var": env_var_name,
                    },
                )

            logger.info(
                "Credentials injected for workspace",
                workspace_id=str(workspace_id),
                count=len(bindings),
            )

            return result

    def inject_credentials_by_ids(
        self,
        workspace_id: UUID,
        binding_ids: list[UUID],
        actor: Optional[str] = None,
    ) -> dict[str, str]:
        """Get selected decrypted workspace credentials for sandbox injection.

        Args:
            workspace_id: Workspace ID that must own every requested credential
            binding_ids: Credential binding IDs to inject
            actor: Optional user ID or agent ID for audit log

        Returns:
            Dictionary of {env_var_name: decrypted_value}

        Raises:
            CredentialNotFoundError: If a requested binding is missing or out of scope
            CredentialBrokerError: If decryption fails
        """
        if not binding_ids:
            return {}

        db = self._get_db()
        encryption = self._get_encryption()

        if not encryption.is_configured:
            raise CredentialBrokerError(
                "Credential encryption is not configured. "
                "Set CREDENTIAL_ENCRYPTION_KEY environment variable."
            )

        requested_ids = set(binding_ids)
        with db.get_session() as session:
            bindings = (
                session.query(CredentialBinding)
                .filter(
                    CredentialBinding.workspace_id == workspace_id,
                    CredentialBinding.id.in_(requested_ids),
                )
                .all()
            )
            found_ids = {binding.id for binding in bindings}
            missing_ids = requested_ids - found_ids
            if missing_ids:
                raise CredentialNotFoundError(
                    "Credential binding not found in requested workspace"
                )

            result = {}
            for binding in bindings:
                try:
                    decrypted_value = encryption.decrypt(binding.encrypted_value)
                except Exception as e:
                    logger.error(
                        "Failed to decrypt credential",
                        binding_id=str(binding.id),
                        error=str(e),
                    )
                    raise CredentialBrokerError(
                        f"Failed to decrypt credential '{binding.name}'"
                    ) from e

                safe_name = "".join(
                    c if c.isalnum() else "_" for c in binding.name
                ).upper()
                env_var_name = f"OMOIOS_CRED_{binding.kind.upper()}_{safe_name}"
                result[env_var_name] = decrypted_value

                self._write_access_log(
                    workspace_id=workspace_id,
                    action="inject",
                    credential_binding_id=binding.id,
                    actor=actor,
                    access_metadata={
                        "kind": binding.kind,
                        "name": binding.name,
                        "env_var": env_var_name,
                    },
                )

            return result


# Global singleton instance
_service_instance: Optional[CredentialBrokerService] = None


def get_credential_broker_service() -> CredentialBrokerService:
    """Get the global credential broker service instance (singleton pattern).

    Returns:
        CredentialBrokerService instance
    """
    global _service_instance

    if _service_instance is None:
        _service_instance = CredentialBrokerService()

    return _service_instance


def reset_credential_broker_service() -> None:
    """Reset the global credential broker service instance.

    Useful for testing to ensure clean state between tests.
    """
    global _service_instance
    _service_instance = None
