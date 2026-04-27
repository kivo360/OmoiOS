"""Unit tests for environment service.

Tests Requirements:
- REQ-ENV-001: Environment creation with org_id, name, description
- REQ-ENV-002: Environment listing by organization
- REQ-ENV-003: Immutable versioned configurations
- REQ-ENV-004: Secret variable encryption/decryption
- REQ-ENV-005: Variable type validation (string, secret, json)
"""

from uuid import UUID, uuid4

import pytest

from omoi_os.models.environment import Environment, EnvironmentVersion
from omoi_os.services.credential_encryption import (
    CredentialEncryptionService,
    reset_credential_encryption_service,
)
from omoi_os.services.database import DatabaseService
from omoi_os.services.environment_service import (
    EnvironmentService,
    EnvironmentServiceError,
    InvalidVariableError,
    get_environment_service,
    reset_environment_service,
)


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
def environment_service(
    db_service: DatabaseService,
    encryption_service: CredentialEncryptionService,
) -> EnvironmentService:
    """Create an environment service with test dependencies."""
    reset_environment_service()
    service = EnvironmentService(db=db_service, encryption=encryption_service)
    return service


@pytest.fixture
def test_org_id() -> UUID:
    """Create a test organization ID."""
    return uuid4()


# ============================================================================
# Environment Creation Tests
# ============================================================================


class TestEnvironmentCreation:
    """Tests for environment creation."""

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_create_environment_returns_environment(
        self,
        environment_service: EnvironmentService,
        test_org_id: UUID,
    ):
        """Test create environment returns Environment with id, org_id, name."""
        environment = environment_service.create_environment(
            org_id=test_org_id,
            name="test-env",
            description="Test environment",
        )

        assert isinstance(environment, Environment)
        assert environment.id is not None
        assert isinstance(environment.id, UUID)
        assert environment.org_id == test_org_id
        assert environment.name == "test-env"
        assert environment.description == "Test environment"
        assert environment.created_at is not None
        assert environment.updated_at is not None

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_create_environment_without_description(
        self,
        environment_service: EnvironmentService,
        test_org_id: UUID,
    ):
        """Test create environment without description works."""
        environment = environment_service.create_environment(
            org_id=test_org_id,
            name="test-env-no-desc",
        )

        assert environment.description is None

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_create_duplicate_name_raises_integrity_error(
        self,
        environment_service: EnvironmentService,
        test_org_id: UUID,
    ):
        """Test duplicate name in same org raises IntegrityError."""
        environment_service.create_environment(
            org_id=test_org_id,
            name="duplicate-env",
        )

        # Attempt to create another with same name
        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            environment_service.create_environment(
                org_id=test_org_id,
                name="duplicate-env",
            )


# ============================================================================
# Environment Listing Tests
# ============================================================================


class TestEnvironmentListing:
    """Tests for environment listing."""

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_list_returns_empty_array_initially(
        self,
        environment_service: EnvironmentService,
        test_org_id: UUID,
    ):
        """Test list returns empty array initially."""
        environments = environment_service.list_environments(org_id=test_org_id)
        assert environments == []

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_list_returns_array_with_created_envs(
        self,
        environment_service: EnvironmentService,
        test_org_id: UUID,
    ):
        """Test list returns array with created environments."""
        env1 = environment_service.create_environment(
            org_id=test_org_id,
            name="env-1",
        )
        env2 = environment_service.create_environment(
            org_id=test_org_id,
            name="env-2",
        )

        environments = environment_service.list_environments(org_id=test_org_id)

        assert len(environments) == 2
        ids = {e.id for e in environments}
        assert env1.id in ids
        assert env2.id in ids

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_list_filters_by_org_id(
        self,
        environment_service: EnvironmentService,
        test_org_id: UUID,
    ):
        """Test list filters by org_id."""
        other_org_id = uuid4()

        # Create in first org
        env1 = environment_service.create_environment(
            org_id=test_org_id,
            name="env-1",
        )

        # Create in second org (side-effect only — we don't reference it after)
        environment_service.create_environment(
            org_id=other_org_id,
            name="env-2",
        )

        # List first org
        environments = environment_service.list_environments(org_id=test_org_id)
        assert len(environments) == 1
        assert environments[0].id == env1.id


# ============================================================================
# Environment Get Tests
# ============================================================================


class TestEnvironmentGet:
    """Tests for getting environment by ID."""

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_get_by_id_with_no_versions_returns_none_version(
        self,
        environment_service: EnvironmentService,
        test_org_id: UUID,
    ):
        """Test get by id with no versions returns (env, None)."""
        env = environment_service.create_environment(
            org_id=test_org_id,
            name="test-env",
        )

        environment, latest_version = environment_service.get_environment(env.id)

        assert environment.id == env.id
        assert latest_version is None

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_get_by_id_not_found_raises_error(
        self,
        environment_service: EnvironmentService,
    ):
        """Test get by id for non-existent environment raises error."""
        with pytest.raises(EnvironmentServiceError) as exc_info:
            environment_service.get_environment(uuid4())

        assert "not found" in str(exc_info.value).lower()


# ============================================================================
# Version Creation Tests
# ============================================================================


class TestVersionCreation:
    """Tests for version creation."""

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_create_version_with_string_variable(
        self,
        environment_service: EnvironmentService,
        test_org_id: UUID,
    ):
        """Test create version with string variable: version_number=1, variables stored correctly."""
        env = environment_service.create_environment(
            org_id=test_org_id,
            name="test-env",
        )

        version = environment_service.create_version(
            env_id=env.id,
            variables={
                "API_URL": {"type": "string", "value": "https://api.example.com"},
            },
        )

        assert isinstance(version, EnvironmentVersion)
        assert version.environment_id == env.id
        assert version.version_number == 1
        assert version.variables["API_URL"]["type"] == "string"
        assert version.variables["API_URL"]["value"] == "https://api.example.com"

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_create_second_version_increments_version_number(
        self,
        environment_service: EnvironmentService,
        test_org_id: UUID,
        db_service: DatabaseService,
    ):
        """Test create second version: version_number=2, first version still exists unchanged."""
        env = environment_service.create_environment(
            org_id=test_org_id,
            name="test-env",
        )

        # Create first version
        version1 = environment_service.create_version(
            env_id=env.id,
            variables={
                "VAR1": {"type": "string", "value": "value1"},
            },
        )

        # Create second version
        version2 = environment_service.create_version(
            env_id=env.id,
            variables={
                "VAR1": {"type": "string", "value": "value1_updated"},
                "VAR2": {"type": "string", "value": "value2"},
            },
        )

        assert version1.version_number == 1
        assert version2.version_number == 2

        # Verify first version is unchanged
        with db_service.get_session() as session:
            v1_from_db = session.get(EnvironmentVersion, version1.id)
            assert v1_from_db.variables["VAR1"]["value"] == "value1"

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_create_version_with_json_variable(
        self,
        environment_service: EnvironmentService,
        test_org_id: UUID,
    ):
        """Test create version with json variable stores correctly."""
        env = environment_service.create_environment(
            org_id=test_org_id,
            name="test-env",
        )

        version = environment_service.create_version(
            env_id=env.id,
            variables={
                "CONFIG": {"type": "json", "value": '{"key": "value", "num": 123}'},
            },
        )

        assert version.variables["CONFIG"]["type"] == "json"
        assert version.variables["CONFIG"]["value"] == '{"key": "value", "num": 123}'


# ============================================================================
# Secret Encryption Tests
# ============================================================================


class TestSecretEncryption:
    """Tests for secret variable encryption."""

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_create_version_with_secret_encrypts_value(
        self,
        environment_service: EnvironmentService,
        test_org_id: UUID,
    ):
        """Test create version with secret variable: stored value is encrypted."""
        env = environment_service.create_environment(
            org_id=test_org_id,
            name="test-env",
        )

        secret_value = "my-secret-api-key-12345"

        version = environment_service.create_version(
            env_id=env.id,
            variables={
                "API_KEY": {"type": "secret", "value": secret_value},
            },
        )

        # Stored value should be encrypted (different from input)
        stored_value = version.variables["API_KEY"]["value"]
        assert stored_value != secret_value
        # Should look like Fernet encrypted data (base64 with special chars)
        assert "=" in stored_value or "_" in stored_value or "-" in stored_value

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_get_decrypted_variables_returns_original_secret(
        self,
        environment_service: EnvironmentService,
        test_org_id: UUID,
    ):
        """Test get_decrypted_variables returns original secret value (round-trip)."""
        env = environment_service.create_environment(
            org_id=test_org_id,
            name="test-env",
        )

        secret_value = "my-secret-api-key-12345"

        version = environment_service.create_version(
            env_id=env.id,
            variables={
                "API_KEY": {"type": "secret", "value": secret_value},
                "PLAIN": {"type": "string", "value": "plain-value"},
            },
        )

        decrypted = environment_service.get_decrypted_variables(version)

        # Secret should be decrypted back to original
        assert decrypted["API_KEY"]["value"] == secret_value
        assert decrypted["API_KEY"]["type"] == "secret"
        # Plain string should be unchanged
        assert decrypted["PLAIN"]["value"] == "plain-value"
        assert decrypted["PLAIN"]["type"] == "string"


# ============================================================================
# Variable Validation Tests
# ============================================================================


class TestVariableValidation:
    """Tests for variable structure validation."""

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_missing_type_raises_error(
        self,
        environment_service: EnvironmentService,
        test_org_id: UUID,
    ):
        """Test variable missing 'type' field raises InvalidVariableError."""
        env = environment_service.create_environment(
            org_id=test_org_id,
            name="test-env",
        )

        with pytest.raises(InvalidVariableError) as exc_info:
            environment_service.create_version(
                env_id=env.id,
                variables={
                    "VAR": {"value": "some-value"},  # Missing 'type'
                },
            )

        assert "type" in str(exc_info.value).lower()

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_missing_value_raises_error(
        self,
        environment_service: EnvironmentService,
        test_org_id: UUID,
    ):
        """Test variable missing 'value' field raises InvalidVariableError."""
        env = environment_service.create_environment(
            org_id=test_org_id,
            name="test-env",
        )

        with pytest.raises(InvalidVariableError) as exc_info:
            environment_service.create_version(
                env_id=env.id,
                variables={
                    "VAR": {"type": "string"},  # Missing 'value'
                },
            )

        assert "value" in str(exc_info.value).lower()

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_invalid_type_raises_error(
        self,
        environment_service: EnvironmentService,
        test_org_id: UUID,
    ):
        """Test variable with invalid type raises InvalidVariableError."""
        env = environment_service.create_environment(
            org_id=test_org_id,
            name="test-env",
        )

        with pytest.raises(InvalidVariableError) as exc_info:
            environment_service.create_version(
                env_id=env.id,
                variables={
                    "VAR": {"type": "invalid_type", "value": "some-value"},
                },
            )

        assert "invalid type" in str(exc_info.value).lower()

    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_non_dict_variable_raises_error(
        self,
        environment_service: EnvironmentService,
        test_org_id: UUID,
    ):
        """Test non-dict variable raises InvalidVariableError."""
        env = environment_service.create_environment(
            org_id=test_org_id,
            name="test-env",
        )

        with pytest.raises(InvalidVariableError) as exc_info:
            environment_service.create_version(
                env_id=env.id,
                variables={
                    "VAR": "just-a-string",  # Not a dict
                },
            )

        assert "dict" in str(exc_info.value).lower()


# ============================================================================
# Masking Tests
# ============================================================================


class TestVariableMasking:
    """Tests for variable masking in API responses."""

    @pytest.mark.unit
    def test_mask_secret_variables_masks_secrets(
        self,
        environment_service: EnvironmentService,
    ):
        """Test mask_secret_variables replaces secret values with '***'."""
        variables = {
            "API_KEY": {"type": "secret", "value": "secret-value-123"},
            "API_URL": {"type": "string", "value": "https://api.example.com"},
            "CONFIG": {"type": "json", "value": '{"key": "value"}'},
        }

        masked = environment_service.mask_secret_variables(variables)

        assert masked["API_KEY"]["value"] == "***"
        assert masked["API_KEY"]["type"] == "secret"
        assert masked["API_URL"]["value"] == "https://api.example.com"
        assert masked["CONFIG"]["value"] == '{"key": "value"}'


# ============================================================================
# Singleton Pattern Tests
# ============================================================================


class TestEnvironmentServiceSingleton:
    """Tests for environment service singleton pattern."""

    @pytest.mark.unit
    def test_get_environment_service_returns_singleton(self):
        """Test get_environment_service returns cached instance."""
        reset_environment_service()

        service1 = get_environment_service()
        service2 = get_environment_service()

        assert service1 is service2

    @pytest.mark.unit
    def test_reset_creates_new_instance(self):
        """Test reset allows creating new instance."""
        service1 = get_environment_service()
        reset_environment_service()
        service2 = get_environment_service()

        assert service1 is not service2
