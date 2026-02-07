"""Unit tests for auth service (no database required)."""

import pytest
from datetime import timedelta
from uuid import uuid4

from omoi_os.services.auth_service import AuthService


# Mock database session
class MockDB:
    """Mock database session for unit testing."""

    async def execute(self, *args, **kwargs):
        pass

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass


TEST_JWT_SECRET = "test-secret-key-for-testing-only"


@pytest.fixture
def auth_service():
    """Create AuthService instance with mock DB."""
    return AuthService(
        db=MockDB(),
        jwt_secret=TEST_JWT_SECRET,
        jwt_algorithm="HS256",
        access_token_expire_minutes=15,
        refresh_token_expire_days=7,
    )


class TestPasswordOperations:
    """Test password hashing and validation."""

    def test_hash_password(self, auth_service):
        """Test password hashing."""
        password = "TestPassword123"
        hashed = auth_service.hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt hash
        assert len(hashed) > 50

    def test_verify_password(self, auth_service):
        """Test password verification."""
        password = "TestPassword123"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password(password, hashed)
        assert not auth_service.verify_password("WrongPassword", hashed)

    def test_password_strength_validation(self, auth_service):
        """Test password strength requirements."""
        # Valid password
        valid, error = auth_service.validate_password_strength("ValidPass123")
        assert valid
        assert error is None

        # Too short
        valid, error = auth_service.validate_password_strength("Short1")
        assert not valid
        assert "at least 8 characters" in error

        # No uppercase
        valid, error = auth_service.validate_password_strength("lowercase123")
        assert not valid
        assert "uppercase" in error

        # No lowercase
        valid, error = auth_service.validate_password_strength("UPPERCASE123")
        assert not valid
        assert "lowercase" in error

        # No digit
        valid, error = auth_service.validate_password_strength("NoDigitsHere")
        assert not valid
        assert "digit" in error


class TestJWTOperations:
    """Test JWT token generation and validation."""

    def test_create_access_token(self, auth_service):
        """Test access token creation."""
        user_id = uuid4()
        token = auth_service.create_access_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 20

        # Verify token
        token_data = auth_service.verify_token(token, token_type="access")
        assert token_data is not None
        assert token_data.user_id == user_id
        assert token_data.token_type == "access"

    def test_create_refresh_token(self, auth_service):
        """Test refresh token creation."""
        user_id = uuid4()
        token = auth_service.create_refresh_token(user_id)

        assert isinstance(token, str)

        # Verify token
        token_data = auth_service.verify_token(token, token_type="refresh")
        assert token_data is not None
        assert token_data.user_id == user_id
        assert token_data.token_type == "refresh"

    def test_verify_invalid_token(self, auth_service):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.here"
        token_data = auth_service.verify_token(invalid_token)

        assert token_data is None

    def test_verify_wrong_token_type(self, auth_service):
        """Test verification fails for wrong token type."""
        user_id = uuid4()
        access_token = auth_service.create_access_token(user_id)

        # Try to verify as refresh token
        token_data = auth_service.verify_token(access_token, token_type="refresh")
        assert token_data is None

    def test_token_expiration(self, auth_service):
        """Test tokens expire correctly."""
        user_id = uuid4()

        # Create token with very short expiration
        token = auth_service.create_access_token(
            user_id, expires_delta=timedelta(seconds=-1)  # Already expired
        )

        # Should fail verification due to expiration
        token_data = auth_service.verify_token(token, token_type="access")
        assert token_data is None


class TestAPIKeyOperations:
    """Test API key generation."""

    def test_generate_api_key(self, auth_service):
        """Test API key generation."""
        full_key, prefix, hashed_key = auth_service.generate_api_key()

        assert full_key.startswith("sk_live_")
        assert prefix == full_key[:16]
        assert len(hashed_key) == 64  # SHA-256 hex
        assert hashed_key != full_key

    def test_generate_unique_keys(self, auth_service):
        """Test generated keys are unique."""
        key1, _, hash1 = auth_service.generate_api_key()
        key2, _, hash2 = auth_service.generate_api_key()

        assert key1 != key2
        assert hash1 != hash2


class TestTokenGeneration:
    """Test various token types."""

    def test_create_verification_token(self, auth_service):
        """Test email verification token creation."""
        user_id = uuid4()
        token = auth_service.create_verification_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 20

        # Verify it's the right type
        token_data = auth_service.verify_token(token, token_type="email_verification")
        assert token_data is not None
        assert token_data.user_id == user_id

    def test_create_reset_token(self, auth_service):
        """Test password reset token creation."""
        user_id = uuid4()
        token = auth_service.create_reset_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 20

        # Verify it's the right type
        token_data = auth_service.verify_token(token, token_type="password_reset")
        assert token_data is not None
        assert token_data.user_id == user_id
