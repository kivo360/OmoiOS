"""Unit tests for credential broker service.

Tests Requirements:
- REQ-CRED-001: Create credential bindings with 3 kinds
- REQ-CRED-002: Encrypt values before storage
- REQ-CRED-003: List credentials by workspace
- REQ-CRED-004: Get credential by ID
- REQ-CRED-005: Delete credentials
- REQ-CRED-006: Inject credentials into sandboxes
- REQ-CRED-007: Audit logging for all operations
"""

from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from omoi_os.models.credential_access_log import CredentialAccessLog
from omoi_os.models.credential_binding import CredentialBinding
from omoi_os.models.environment import Environment, EnvironmentVersion
from omoi_os.models.organization import Organization
from omoi_os.models.sandbox_session import SandboxSession
from omoi_os.models.user import User
from omoi_os.models.user_credentials import UserCredential
from omoi_os.models.workspace import Workspace
from omoi_os.services.credential_broker import (
    CredentialBrokerError,
    CredentialBrokerService,
    CredentialNotFoundError,
    InvalidBindingKindError,
    UnknownAliasError,
    get_credential_broker_service,
    reset_credential_broker_service,
)
from omoi_os.services.credential_encryption import (
    CredentialEncryptionService,
    reset_credential_encryption_service,
)
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def encryption_key() -> str:
    """Generate a valid test encryption key."""
    return "a" * 64  # 64 hex chars = 32 bytes


@pytest.fixture
def encryption_service(encryption_key: str) -> CredentialEncryptionService:
    """Create an encryption service with test key."""
    reset_credential_encryption_service()
    service = CredentialEncryptionService(encryption_key=encryption_key)
    return service


@pytest.fixture
def credential_broker_service(
    db_service: DatabaseService,
    encryption_service: CredentialEncryptionService,
) -> CredentialBrokerService:
    """Create a credential broker service with test dependencies."""
    reset_credential_broker_service()
    service = CredentialBrokerService(db=db_service, encryption=encryption_service)
    return service


@pytest.fixture
def test_workspace_id() -> UUID:
    """Create a test workspace ID."""
    return uuid4()


@pytest.fixture
def sandbox_alias_context(
    db_service: DatabaseService,
    test_user: User,
) -> dict[str, UUID | SandboxSession]:
    """Create persisted workspace, environment version, and sandbox session."""
    with db_service.get_session() as session:
        org = Organization(
            id=uuid4(),
            name="Credential Alias Org",
            slug=f"credential-alias-org-{uuid4().hex}",
            owner_id=test_user.id,
        )
        session.add(org)
        session.flush()

        workspace = Workspace(
            id=uuid4(),
            organization_id=org.id,
            name="Credential Alias Workspace",
            slug=f"credential-alias-workspace-{uuid4().hex}",
        )
        environment = Environment(
            id=uuid4(),
            org_id=org.id,
            name=f"credential-alias-env-{uuid4().hex}",
        )
        session.add_all([workspace, environment])
        session.flush()

        env_version = EnvironmentVersion(
            id=uuid4(),
            environment_id=environment.id,
            version_number=1,
            variables={},
            credentials={},
        )
        sandbox_session = SandboxSession(
            id=uuid4(),
            session_token_hash=f"{uuid4().hex}{uuid4().hex}",
            session_token_prefix="sess_tok",
            workspace_id=workspace.id,
            environment_version_id=env_version.id,
            expires_at=utc_now() + timedelta(hours=1),
        )
        session.add_all([env_version, sandbox_session])
        session.commit()
        session.refresh(sandbox_session)
        session.expunge(sandbox_session)

        return {
            "workspace_id": workspace.id,
            "environment_version_id": env_version.id,
            "sandbox_session": sandbox_session,
            "user_id": test_user.id,
        }


def set_environment_credentials(
    db_service: DatabaseService,
    environment_version_id: UUID,
    credentials: dict,
) -> None:
    """Persist credential alias mappings for a test environment version."""
    with db_service.get_session() as session:
        env_version = session.get(EnvironmentVersion, environment_version_id)
        assert env_version is not None
        env_version.credentials = credentials
        session.commit()


# ============================================================================
# Credential Creation Tests
# ============================================================================


class TestCredentialCreation:
    """Tests for credential creation."""

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_create_bearer_secret_binding(
        self,
        credential_broker_service: CredentialBrokerService,
        test_workspace_id: UUID,
    ):
        """Test create bearer_secret binding returns object with id."""
        binding = credential_broker_service.create_binding(
            workspace_id=test_workspace_id,
            kind="bearer_secret",
            name="api-key",
            value="sk-test-12345",
        )

        assert isinstance(binding, CredentialBinding)
        assert binding.id is not None
        assert isinstance(binding.id, UUID)
        assert binding.workspace_id == test_workspace_id
        assert binding.kind == "bearer_secret"
        assert binding.name == "api-key"
        assert binding.encrypted_value != "sk-test-12345"  # Should be encrypted
        assert binding.config == {}
        assert binding.version == 1
        assert binding.created_at is not None

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_create_user_oauth_binding(
        self,
        credential_broker_service: CredentialBrokerService,
        test_workspace_id: UUID,
    ):
        """Test create user_oauth binding stores correctly."""
        binding = credential_broker_service.create_binding(
            workspace_id=test_workspace_id,
            kind="user_oauth",
            name="google-oauth",
            value="oauth-token-12345",
            config={"scopes": ["email", "profile"]},
        )

        assert binding.kind == "user_oauth"
        assert binding.name == "google-oauth"
        assert binding.config == {"scopes": ["email", "profile"]}

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_create_github_app_binding(
        self,
        credential_broker_service: CredentialBrokerService,
        test_workspace_id: UUID,
    ):
        """Test create github_app binding stores correctly."""
        binding = credential_broker_service.create_binding(
            workspace_id=test_workspace_id,
            kind="github_app",
            name="github-app-token",
            value="gh-app-token-12345",
            config={"app_id": "123456", "installation_id": "789012"},
        )

        assert binding.kind == "github_app"
        assert binding.name == "github-app-token"
        assert binding.config == {"app_id": "123456", "installation_id": "789012"}

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_create_with_invalid_kind_raises_error(
        self,
        credential_broker_service: CredentialBrokerService,
        test_workspace_id: UUID,
    ):
        """Test create with invalid kind raises InvalidBindingKindError."""
        with pytest.raises(InvalidBindingKindError) as exc_info:
            credential_broker_service.create_binding(
                workspace_id=test_workspace_id,
                kind="invalid_kind",
                name="test",
                value="test-value",
            )

        assert "invalid binding kind" in str(exc_info.value).lower()

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_create_when_encryption_not_configured_raises_error(
        self,
        db_service: DatabaseService,
        test_workspace_id: UUID,
    ):
        """Test create when encryption not configured raises CredentialBrokerError."""
        # Reset with no encryption key
        reset_credential_encryption_service()
        reset_credential_broker_service()
        unconfigured_encryption = CredentialEncryptionService(encryption_key=None)
        service = CredentialBrokerService(
            db=db_service, encryption=unconfigured_encryption
        )

        with pytest.raises(CredentialBrokerError) as exc_info:
            service.create_binding(
                workspace_id=test_workspace_id,
                kind="bearer_secret",
                name="test",
                value="test-value",
            )

        assert "not configured" in str(exc_info.value).lower()


# ============================================================================
# Credential Listing Tests
# ============================================================================


class TestCredentialListing:
    """Tests for credential listing."""

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_list_returns_empty_array_initially(
        self,
        credential_broker_service: CredentialBrokerService,
        test_workspace_id: UUID,
    ):
        """Test list returns empty array initially."""
        bindings = credential_broker_service.list_bindings(
            workspace_id=test_workspace_id
        )
        assert bindings == []

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_list_returns_array_with_created_bindings(
        self,
        credential_broker_service: CredentialBrokerService,
        test_workspace_id: UUID,
    ):
        """Test list returns array with created bindings."""
        binding1 = credential_broker_service.create_binding(
            workspace_id=test_workspace_id,
            kind="bearer_secret",
            name="key-1",
            value="value-1",
        )
        binding2 = credential_broker_service.create_binding(
            workspace_id=test_workspace_id,
            kind="bearer_secret",
            name="key-2",
            value="value-2",
        )

        bindings = credential_broker_service.list_bindings(
            workspace_id=test_workspace_id
        )

        assert len(bindings) == 2
        ids = {b.id for b in bindings}
        assert binding1.id in ids
        assert binding2.id in ids

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_list_filters_by_workspace_id(
        self,
        credential_broker_service: CredentialBrokerService,
        test_workspace_id: UUID,
    ):
        """Test list filters by workspace_id."""
        other_workspace_id = uuid4()

        # Create in first workspace
        binding1 = credential_broker_service.create_binding(
            workspace_id=test_workspace_id,
            kind="bearer_secret",
            name="key-1",
            value="value-1",
        )

        # Create in second workspace
        credential_broker_service.create_binding(
            workspace_id=other_workspace_id,
            kind="bearer_secret",
            name="key-2",
            value="value-2",
        )

        # List first workspace
        bindings = credential_broker_service.list_bindings(
            workspace_id=test_workspace_id
        )
        assert len(bindings) == 1
        assert bindings[0].id == binding1.id


# ============================================================================
# Credential Get Tests
# ============================================================================


class TestCredentialGet:
    """Tests for getting credentials by ID."""

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_get_by_id_returns_binding(
        self,
        credential_broker_service: CredentialBrokerService,
        test_workspace_id: UUID,
    ):
        """Test get by id returns the binding."""
        created = credential_broker_service.create_binding(
            workspace_id=test_workspace_id,
            kind="bearer_secret",
            name="api-key",
            value="secret-value",
        )

        fetched = credential_broker_service.get_binding(binding_id=created.id)

        assert fetched.id == created.id
        assert fetched.workspace_id == test_workspace_id
        assert fetched.kind == "bearer_secret"
        assert fetched.name == "api-key"

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_get_missing_id_raises_error(
        self,
        credential_broker_service: CredentialBrokerService,
    ):
        """Test get by id for non-existent binding raises error."""
        with pytest.raises(CredentialNotFoundError) as exc_info:
            credential_broker_service.get_binding(binding_id=uuid4())

        assert "not found" in str(exc_info.value).lower()


# ============================================================================
# Credential Delete Tests
# ============================================================================


class TestCredentialDelete:
    """Tests for deleting credentials."""

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_delete_removes_binding(
        self,
        credential_broker_service: CredentialBrokerService,
        test_workspace_id: UUID,
    ):
        """Test delete removes the binding."""
        created = credential_broker_service.create_binding(
            workspace_id=test_workspace_id,
            kind="bearer_secret",
            name="api-key",
            value="secret-value",
        )

        # Delete the binding
        credential_broker_service.delete_binding(binding_id=created.id)

        # Verify it's gone
        with pytest.raises(CredentialNotFoundError):
            credential_broker_service.get_binding(binding_id=created.id)


# ============================================================================
# Encryption Tests
# ============================================================================


class TestEncryption:
    """Tests for credential encryption."""

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_encrypted_value_in_db_is_not_plaintext(
        self,
        credential_broker_service: CredentialBrokerService,
        test_workspace_id: UUID,
        db_service: DatabaseService,
    ):
        """Test encrypted value in DB is NOT the plaintext."""
        plaintext = "my-secret-api-key-12345"

        binding = credential_broker_service.create_binding(
            workspace_id=test_workspace_id,
            kind="bearer_secret",
            name="api-key",
            value=plaintext,
        )

        # Query DB directly to verify encryption
        with db_service.get_session() as session:
            row = session.get(CredentialBinding, binding.id)
            assert row is not None
            assert row.encrypted_value != plaintext
            # Should look like Fernet encrypted data (base64 with special chars)
            assert (
                "=" in row.encrypted_value
                or "_" in row.encrypted_value
                or "-" in row.encrypted_value
            )


# ============================================================================
# Inject Credentials Tests
# ============================================================================


class TestInjectCredentials:
    """Tests for credential injection."""

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_inject_credentials_returns_env_var_dict(
        self,
        credential_broker_service: CredentialBrokerService,
        test_workspace_id: UUID,
    ):
        """Test inject_credentials returns dict mapping env-var-name to decrypted value."""
        # Create some credentials
        credential_broker_service.create_binding(
            workspace_id=test_workspace_id,
            kind="bearer_secret",
            name="api-key",
            value="secret-api-key-123",
        )
        credential_broker_service.create_binding(
            workspace_id=test_workspace_id,
            kind="user_oauth",
            name="google-token",
            value="oauth-token-456",
        )

        # Inject credentials
        env_vars = credential_broker_service.inject_credentials(
            workspace_id=test_workspace_id
        )

        # Verify env var names and decrypted values
        assert "OMOIOS_CRED_BEARER_SECRET_API_KEY" in env_vars
        assert env_vars["OMOIOS_CRED_BEARER_SECRET_API_KEY"] == "secret-api-key-123"
        assert "OMOIOS_CRED_USER_OAUTH_GOOGLE_TOKEN" in env_vars
        assert env_vars["OMOIOS_CRED_USER_OAUTH_GOOGLE_TOKEN"] == "oauth-token-456"


# ============================================================================
# Resolve Alias Tests
# ============================================================================


class TestResolveAlias:
    """Tests for sandbox session credential alias resolution."""

    @pytest.mark.unit
    @pytest.mark.requires_db
    @pytest.mark.asyncio
    async def test_resolve_bearer_secret_decrypts_and_audits(
        self,
        credential_broker_service: CredentialBrokerService,
        sandbox_alias_context: dict[str, UUID | SandboxSession],
        db_service: DatabaseService,
    ):
        """Test bearer_secret alias returns plaintext and writes sandbox audit log."""
        workspace_id = sandbox_alias_context["workspace_id"]
        environment_version_id = sandbox_alias_context["environment_version_id"]
        sandbox_session = sandbox_alias_context["sandbox_session"]
        assert isinstance(workspace_id, UUID)
        assert isinstance(environment_version_id, UUID)
        assert isinstance(sandbox_session, SandboxSession)

        binding = credential_broker_service.create_binding(
            workspace_id=workspace_id,
            kind="bearer_secret",
            name="anthropic-api-key",
            value="sk-ant-test-secret",
        )
        set_environment_credentials(
            db_service,
            environment_version_id,
            {
                "anthropic": {
                    "kind": "bearer_secret",
                    "binding_id": str(binding.id),
                }
            },
        )

        payload = await credential_broker_service.resolve_alias(
            sandbox_session,
            "anthropic",
        )

        assert payload == {
            "kind": "bearer_secret",
            "value": "sk-ant-test-secret",
        }
        with db_service.get_session() as session:
            log_entry = (
                session.query(CredentialAccessLog)
                .filter(
                    CredentialAccessLog.sandbox_session_id == sandbox_session.id,
                    CredentialAccessLog.action == "inject",
                )
                .one()
            )
            assert log_entry.workspace_id == workspace_id
            assert log_entry.access_metadata == {
                "alias": "anthropic",
                "kind": "bearer_secret",
            }

    @pytest.mark.unit
    @pytest.mark.requires_db
    @pytest.mark.asyncio
    async def test_resolve_user_oauth_refreshes_near_expiry(
        self,
        credential_broker_service: CredentialBrokerService,
        encryption_service: CredentialEncryptionService,
        sandbox_alias_context: dict[str, UUID | SandboxSession],
        db_service: DatabaseService,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test user_oauth alias refreshes near-expiry tokens before returning."""
        environment_version_id = sandbox_alias_context["environment_version_id"]
        sandbox_session = sandbox_alias_context["sandbox_session"]
        user_id = sandbox_alias_context["user_id"]
        assert isinstance(environment_version_id, UUID)
        assert isinstance(sandbox_session, SandboxSession)
        assert isinstance(user_id, UUID)

        stale_expiry = utc_now() + timedelta(minutes=1)
        fresh_expiry = utc_now() + timedelta(hours=1)
        with db_service.get_session() as session:
            credential = UserCredential(
                id=uuid4(),
                user_id=user_id,
                provider="github",
                name="github-oauth",
                api_key="legacy-token",
                encrypted_value=encryption_service.encrypt("stale-token"),
                config_data={"expires_at": stale_expiry.isoformat()},
                is_active=True,
            )
            session.add(credential)
            session.commit()
            credential_id = credential.id

        async def refresh_user_oauth(
            credential: UserCredential,
            mapping: dict,
        ) -> dict:
            return {
                "access_token": "fresh-token",
                "expires_at": fresh_expiry.isoformat(),
            }

        monkeypatch.setattr(
            credential_broker_service,
            "_refresh_user_oauth",
            refresh_user_oauth,
        )
        set_environment_credentials(
            db_service,
            environment_version_id,
            {
                "github": {
                    "kind": "user_oauth",
                    "credential_id": str(credential_id),
                }
            },
        )

        payload = await credential_broker_service.resolve_alias(
            sandbox_session, "github"
        )

        assert payload == {
            "kind": "user_oauth",
            "access_token": "fresh-token",
            "expires_at": fresh_expiry.isoformat(),
        }
        with db_service.get_session() as session:
            refreshed = session.get(UserCredential, credential_id)
            assert refreshed is not None
            assert refreshed.encrypted_value is not None
            assert (
                encryption_service.decrypt(refreshed.encrypted_value) == "fresh-token"
            )
            assert refreshed.config_data == {"expires_at": fresh_expiry.isoformat()}

    @pytest.mark.unit
    @pytest.mark.requires_db
    @pytest.mark.asyncio
    async def test_resolve_github_app_mints_installation_token(
        self,
        credential_broker_service: CredentialBrokerService,
        sandbox_alias_context: dict[str, UUID | SandboxSession],
        db_service: DatabaseService,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test github_app alias returns a minted installation token payload."""
        environment_version_id = sandbox_alias_context["environment_version_id"]
        sandbox_session = sandbox_alias_context["sandbox_session"]
        assert isinstance(environment_version_id, UUID)
        assert isinstance(sandbox_session, SandboxSession)

        expires_at = utc_now() + timedelta(minutes=30)

        async def request_github_installation_token(mapping: dict) -> dict:
            assert mapping["installation_id"] == "78901234"
            return {"token": "ghs_test_token", "expires_at": expires_at.isoformat()}

        monkeypatch.setattr(
            credential_broker_service,
            "_request_github_installation_token",
            request_github_installation_token,
        )
        set_environment_credentials(
            db_service,
            environment_version_id,
            {
                "github-app": {
                    "kind": "github_app",
                    "app_id": "123456",
                    "installation_id": "78901234",
                }
            },
        )

        payload = await credential_broker_service.resolve_alias(
            sandbox_session,
            "github-app",
        )

        assert payload == {
            "kind": "github_app",
            "token": "ghs_test_token",
            "expires_at": expires_at.isoformat(),
        }

    @pytest.mark.unit
    @pytest.mark.requires_db
    @pytest.mark.asyncio
    async def test_resolve_unknown_alias_raises_error(
        self,
        credential_broker_service: CredentialBrokerService,
        sandbox_alias_context: dict[str, UUID | SandboxSession],
    ):
        """Test missing aliases raise UnknownAliasError for route-layer 404 mapping."""
        sandbox_session = sandbox_alias_context["sandbox_session"]
        assert isinstance(sandbox_session, SandboxSession)

        with pytest.raises(UnknownAliasError):
            await credential_broker_service.resolve_alias(sandbox_session, "missing")


# ============================================================================
# Audit Log Tests
# ============================================================================


class TestAuditLog:
    """Tests for audit logging."""

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_create_writes_audit_log(
        self,
        credential_broker_service: CredentialBrokerService,
        test_workspace_id: UUID,
        db_service: DatabaseService,
    ):
        """Test create operation writes a CredentialAccessLog entry."""
        binding = credential_broker_service.create_binding(
            workspace_id=test_workspace_id,
            kind="bearer_secret",
            name="api-key",
            value="secret-value",
            actor="test-user-123",
        )

        # Query audit log
        with db_service.get_session() as session:
            logs = (
                session.query(CredentialAccessLog)
                .filter(CredentialAccessLog.credential_binding_id == binding.id)
                .all()
            )

            assert len(logs) == 1
            assert logs[0].action == "create"
            assert logs[0].workspace_id == test_workspace_id
            assert logs[0].actor == "test-user-123"

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_get_writes_audit_log(
        self,
        credential_broker_service: CredentialBrokerService,
        test_workspace_id: UUID,
        db_service: DatabaseService,
    ):
        """Test get operation writes a CredentialAccessLog entry."""
        binding = credential_broker_service.create_binding(
            workspace_id=test_workspace_id,
            kind="bearer_secret",
            name="api-key",
            value="secret-value",
        )

        # Get the binding
        credential_broker_service.get_binding(
            binding_id=binding.id,
            actor="test-user-456",
        )

        # Query audit log for read actions
        with db_service.get_session() as session:
            logs = (
                session.query(CredentialAccessLog)
                .filter(
                    CredentialAccessLog.credential_binding_id == binding.id,
                    CredentialAccessLog.action == "read",
                )
                .all()
            )

            assert len(logs) == 1
            assert logs[0].action == "read"
            assert logs[0].actor == "test-user-456"

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_delete_writes_audit_log(
        self,
        credential_broker_service: CredentialBrokerService,
        test_workspace_id: UUID,
        db_service: DatabaseService,
    ):
        """Test delete operation writes a CredentialAccessLog entry."""
        binding = credential_broker_service.create_binding(
            workspace_id=test_workspace_id,
            kind="bearer_secret",
            name="api-key",
            value="secret-value",
        )

        binding_id = binding.id
        workspace_id = binding.workspace_id

        # Delete the binding
        credential_broker_service.delete_binding(
            binding_id=binding_id,
            actor="test-user-789",
        )

        # Query audit log (credential_binding_id should still be set)
        with db_service.get_session() as session:
            logs = (
                session.query(CredentialAccessLog)
                .filter(
                    CredentialAccessLog.credential_binding_id == binding_id,
                    CredentialAccessLog.action == "delete",
                )
                .all()
            )

            assert len(logs) == 1
            assert logs[0].action == "delete"
            assert logs[0].actor == "test-user-789"
            assert logs[0].workspace_id == workspace_id

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_inject_writes_audit_log(
        self,
        credential_broker_service: CredentialBrokerService,
        test_workspace_id: UUID,
        db_service: DatabaseService,
    ):
        """Test inject operation writes CredentialAccessLog entries."""
        binding = credential_broker_service.create_binding(
            workspace_id=test_workspace_id,
            kind="bearer_secret",
            name="api-key",
            value="secret-value",
        )

        # Inject credentials
        credential_broker_service.inject_credentials(
            workspace_id=test_workspace_id,
            actor="sandbox-agent-123",
        )

        # Query audit log for inject actions
        with db_service.get_session() as session:
            logs = (
                session.query(CredentialAccessLog)
                .filter(
                    CredentialAccessLog.credential_binding_id == binding.id,
                    CredentialAccessLog.action == "inject",
                )
                .all()
            )

            assert len(logs) == 1
            assert logs[0].action == "inject"
            assert logs[0].actor == "sandbox-agent-123"

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_list_writes_audit_log_with_null_binding_id(
        self,
        credential_broker_service: CredentialBrokerService,
        test_workspace_id: UUID,
        db_service: DatabaseService,
    ):
        """Test list operation writes audit log with credential_binding_id=None."""
        # Create a credential
        credential_broker_service.create_binding(
            workspace_id=test_workspace_id,
            kind="bearer_secret",
            name="api-key",
            value="secret-value",
        )

        # List credentials
        credential_broker_service.list_bindings(
            workspace_id=test_workspace_id,
            actor="test-user-list",
        )

        # Query audit log for list operation (credential_binding_id should be None)
        with db_service.get_session() as session:
            logs = (
                session.query(CredentialAccessLog)
                .filter(
                    CredentialAccessLog.workspace_id == test_workspace_id,
                    CredentialAccessLog.action == "read",
                    CredentialAccessLog.credential_binding_id.is_(None),
                )
                .all()
            )

            assert len(logs) == 1
            assert logs[0].action == "read"
            assert logs[0].credential_binding_id is None
            assert logs[0].actor == "test-user-list"


# ============================================================================
# Singleton Pattern Tests
# ============================================================================


class TestCredentialBrokerServiceSingleton:
    """Tests for credential broker service singleton pattern."""

    @pytest.mark.unit
    def test_get_credential_broker_service_returns_singleton(self):
        """Test get_credential_broker_service returns cached instance."""
        reset_credential_broker_service()

        service1 = get_credential_broker_service()
        service2 = get_credential_broker_service()

        assert service1 is service2

    @pytest.mark.unit
    def test_reset_creates_new_instance(self):
        """Test reset allows creating new instance."""
        service1 = get_credential_broker_service()
        reset_credential_broker_service()
        service2 = get_credential_broker_service()

        assert service1 is not service2
