"""Environment service for managing environments and versioned configurations.

Provides:
- Environment CRUD operations
- Immutable versioned variable storage
- Secret encryption/decryption for sensitive variables
"""

from __future__ import annotations

from typing import Optional, Tuple
from uuid import UUID

from omoi_os.logging import get_logger
from omoi_os.models.environment import Environment, EnvironmentVersion
from omoi_os.services.credential_encryption import (
    CredentialEncryptionService,
    get_credential_encryption_service,
)
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)

# Valid variable types
VALID_VARIABLE_TYPES = {"string", "secret", "json"}


class EnvironmentServiceError(Exception):
    """Base exception for environment service errors."""

    pass


class InvalidVariableError(EnvironmentServiceError):
    """Raised when variable structure is invalid."""

    pass


class EnvironmentService:
    """Service for managing environments and versioned configurations.

    Provides unified interface for:
    - Creating and listing environments
    - Creating immutable versions with variables
    - Encrypting/decrypting secret variables
    """

    def __init__(
        self,
        db: Optional[DatabaseService] = None,
        encryption: Optional[CredentialEncryptionService] = None,
    ):
        """Initialize environment service.

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

    def create_environment(
        self,
        org_id: UUID,
        name: str,
        description: Optional[str] = None,
    ) -> Environment:
        """Create a new environment.

        Args:
            org_id: Organization ID that owns the environment
            name: Environment name (unique within org)
            description: Optional environment description

        Returns:
            Created Environment model

        Raises:
            IntegrityError: If environment name already exists in org
        """
        db = self._get_db()
        with db.get_session() as session:
            environment = Environment(
                org_id=org_id,
                name=name,
                description=description,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session.add(environment)
            session.commit()
            session.refresh(environment)

            logger.info(
                "Environment created",
                environment_id=str(environment.id),
                org_id=str(org_id),
                name=name,
            )

            session.expunge(environment)
            return environment

    def list_environments(
        self,
        org_id: UUID,
    ) -> list[Environment]:
        """List all environments in an organization.

        Args:
            org_id: Organization ID to filter by

        Returns:
            List of Environment models
        """
        db = self._get_db()
        with db.get_session() as session:
            envs = (
                session.query(Environment)
                .filter(Environment.org_id == org_id)
                .order_by(Environment.created_at.desc())
                .all()
            )
            for env in envs:
                session.expunge(env)
            return envs

    def get_environment(
        self,
        env_id: UUID,
    ) -> Tuple[Environment, Optional[EnvironmentVersion]]:
        """Get environment by ID with its latest version.

        Args:
            env_id: Environment ID

        Returns:
            Tuple of (Environment, latest EnvironmentVersion or None)

        Raises:
            EnvironmentServiceError: If environment not found
        """
        db = self._get_db()
        with db.get_session() as session:
            environment = (
                session.query(Environment).filter(Environment.id == env_id).first()
            )

            if environment is None:
                raise EnvironmentServiceError(f"Environment not found: {env_id}")

            # Get latest version (if any)
            latest_version = (
                session.query(EnvironmentVersion)
                .filter(EnvironmentVersion.environment_id == env_id)
                .order_by(EnvironmentVersion.version_number.desc())
                .first()
            )

            session.expunge(environment)
            if latest_version is not None:
                session.expunge(latest_version)
            return environment, latest_version

    def get_version_by_number(
        self,
        env_id: UUID,
        version_number: int,
    ) -> EnvironmentVersion:
        """Fetch a specific version of an environment by its sequential number.

        Args:
            env_id: Environment ID
            version_number: Version number (1, 2, 3...)

        Returns:
            EnvironmentVersion model (detached from session)

        Raises:
            EnvironmentServiceError: If environment or version not found
        """
        db = self._get_db()
        with db.get_session() as session:
            version = (
                session.query(EnvironmentVersion)
                .filter(
                    EnvironmentVersion.environment_id == env_id,
                    EnvironmentVersion.version_number == version_number,
                )
                .first()
            )
            if version is None:
                raise EnvironmentServiceError(
                    f"Version {version_number} not found for environment {env_id}"
                )
            session.expunge(version)
            return version

    def _validate_variable(
        self,
        name: str,
        variable: dict,
    ) -> None:
        """Validate variable structure.

        Args:
            name: Variable name
            variable: Variable dict with "type" and "value"

        Raises:
            InvalidVariableError: If variable structure is invalid
        """
        if not isinstance(variable, dict):
            raise InvalidVariableError(
                f"Variable '{name}' must be a dict with 'type' and 'value'"
            )

        if "type" not in variable:
            raise InvalidVariableError(
                f"Variable '{name}' missing required field: 'type'"
            )

        if "value" not in variable:
            raise InvalidVariableError(
                f"Variable '{name}' missing required field: 'value'"
            )

        var_type = variable["type"]
        if var_type not in VALID_VARIABLE_TYPES:
            raise InvalidVariableError(
                f"Variable '{name}' has invalid type '{var_type}'. "
                f"Must be one of: {VALID_VARIABLE_TYPES}"
            )

    def create_version(
        self,
        env_id: UUID,
        variables: dict[str, dict],
    ) -> EnvironmentVersion:
        """Create a new immutable version for an environment.

        Args:
            env_id: Environment ID
            variables: Dict of variable name -> {"type": "string|secret|json", "value": "..."}

        Returns:
            Created EnvironmentVersion model

        Raises:
            EnvironmentServiceError: If environment not found
            InvalidVariableError: If variable structure is invalid
        """
        db = self._get_db()
        encryption = self._get_encryption()

        # Validate all variables first
        for name, variable in variables.items():
            self._validate_variable(name, variable)

        with db.get_session() as session:
            # Verify environment exists
            environment = (
                session.query(Environment).filter(Environment.id == env_id).first()
            )
            if environment is None:
                raise EnvironmentServiceError(f"Environment not found: {env_id}")

            # Calculate next version number
            max_version = (
                session.query(EnvironmentVersion.version_number)
                .filter(EnvironmentVersion.environment_id == env_id)
                .order_by(EnvironmentVersion.version_number.desc())
                .first()
            )
            next_version_number = 1 if max_version is None else max_version[0] + 1

            # Process variables (encrypt secrets)
            processed_variables = {}
            for name, variable in variables.items():
                var_type = variable["type"]
                value = variable["value"]

                if var_type == "secret" and encryption.is_configured:
                    # Encrypt secret value
                    try:
                        value = encryption.encrypt(value)
                    except Exception as e:
                        logger.error(
                            "Failed to encrypt secret variable",
                            variable_name=name,
                            error=str(e),
                        )
                        raise EnvironmentServiceError(
                            f"Failed to encrypt secret variable '{name}'"
                        ) from e

                processed_variables[name] = {
                    "type": var_type,
                    "value": value,
                }

            # Create version
            version = EnvironmentVersion(
                environment_id=env_id,
                version_number=next_version_number,
                variables=processed_variables,
                created_at=utc_now(),
            )
            session.add(version)
            session.commit()
            session.refresh(version)

            logger.info(
                "Environment version created",
                version_id=str(version.id),
                environment_id=str(env_id),
                version_number=next_version_number,
                variables_count=len(processed_variables),
            )

            session.expunge(version)
            return version

    def get_decrypted_variables(
        self,
        version: EnvironmentVersion,
    ) -> dict[str, dict]:
        """Get variables with secret values decrypted.

        Args:
            version: EnvironmentVersion model

        Returns:
            Dict of variable name -> {"type": "string|secret|json", "value": "..."}
            Secret values are decrypted if encryption is configured.

        Raises:
            EnvironmentServiceError: If decryption fails
        """
        encryption = self._get_encryption()
        result = {}

        for name, variable in version.variables.items():
            var_type = variable["type"]
            value = variable["value"]

            if var_type == "secret" and encryption.is_configured:
                # Decrypt secret value
                try:
                    value = encryption.decrypt(value)
                except Exception as e:
                    logger.error(
                        "Failed to decrypt secret variable",
                        variable_name=name,
                        version_id=str(version.id),
                        error=str(e),
                    )
                    raise EnvironmentServiceError(
                        f"Failed to decrypt secret variable '{name}'"
                    ) from e

            result[name] = {
                "type": var_type,
                "value": value,
            }

        return result

    def mask_secret_variables(
        self,
        variables: dict[str, dict],
    ) -> dict[str, dict]:
        """Mask secret variable values for API responses.

        Args:
            variables: Dict of variable name -> {"type": "...", "value": "..."}

        Returns:
            Copy with secret values replaced by "***"
        """
        result = {}
        for name, variable in variables.items():
            var_type = variable["type"]
            value = variable["value"]

            if var_type == "secret":
                value = "***"

            result[name] = {
                "type": var_type,
                "value": value,
            }

        return result


# Global singleton instance
_service_instance: Optional[EnvironmentService] = None


def get_environment_service() -> EnvironmentService:
    """Get the global environment service instance (singleton pattern).

    Returns:
        EnvironmentService instance
    """
    global _service_instance

    if _service_instance is None:
        _service_instance = EnvironmentService()

    return _service_instance


def reset_environment_service() -> None:
    """Reset the global environment service instance.

    Useful for testing to ensure clean state between tests.
    """
    global _service_instance
    _service_instance = None
