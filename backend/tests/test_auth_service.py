"""Tests for AuthService."""

import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from omoi_os.models.user import User
from omoi_os.models.auth import Session, APIKey
from omoi_os.services.auth_service import AuthService

# Test database setup
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
TEST_JWT_SECRET = "test-secret-key-for-testing-only"


@pytest_asyncio.fixture
async def async_engine():
    """Create async test database engine."""
    engine = create_async_engine(TEST_DB_URL, echo=False)

    async with engine.begin() as conn:
        # Only create tables needed for auth testing
        await conn.run_sync(User.__table__.create, checkfirst=True)
        await conn.run_sync(Session.__table__.create, checkfirst=True)
        await conn.run_sync(APIKey.__table__.create, checkfirst=True)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine):
    """Create async database session."""
    async_session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def auth_service(db_session):
    """Create AuthService instance."""
    return AuthService(
        db=db_session,
        jwt_secret=TEST_JWT_SECRET,
        jwt_algorithm="HS256",
        access_token_expire_minutes=15,
        refresh_token_expire_days=7,
    )


class TestPasswordOperations:
    """Test password hashing and validation."""

    @pytest.mark.asyncio
    async def test_hash_password(self, auth_service):
        """Test password hashing."""
        password = "TestPassword123"
        hashed = auth_service.hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt hash
        assert len(hashed) > 50

    @pytest.mark.asyncio
    async def test_verify_password(self, auth_service):
        """Test password verification."""
        password = "TestPassword123"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password(password, hashed)
        assert not auth_service.verify_password("WrongPassword", hashed)

    @pytest.mark.asyncio
    async def test_password_strength_validation(self, auth_service):
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

    @pytest.mark.asyncio
    async def test_create_access_token(self, auth_service):
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

    @pytest.mark.asyncio
    async def test_create_refresh_token(self, auth_service):
        """Test refresh token creation."""
        user_id = uuid4()
        token = auth_service.create_refresh_token(user_id)

        assert isinstance(token, str)

        # Verify token
        token_data = auth_service.verify_token(token, token_type="refresh")
        assert token_data is not None
        assert token_data.user_id == user_id
        assert token_data.token_type == "refresh"

    @pytest.mark.asyncio
    async def test_verify_invalid_token(self, auth_service):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.here"
        token_data = auth_service.verify_token(invalid_token)

        assert token_data is None

    @pytest.mark.asyncio
    async def test_verify_wrong_token_type(self, auth_service):
        """Test verification fails for wrong token type."""
        user_id = uuid4()
        access_token = auth_service.create_access_token(user_id)

        # Try to verify as refresh token
        token_data = auth_service.verify_token(access_token, token_type="refresh")
        assert token_data is None


class TestUserRegistration:
    """Test user registration."""

    @pytest.mark.asyncio
    async def test_register_user(self, auth_service, db_session):
        """Test successful user registration."""
        user = await auth_service.register_user(
            email="test@example.com",
            password="ValidPassword123",
            full_name="Test User",
            department="Engineering",
        )

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.department == "Engineering"
        assert user.is_verified is False
        assert user.is_active is True
        assert user.is_super_admin is False
        assert user.hashed_password != "ValidPassword123"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, auth_service, db_session):
        """Test registration with duplicate email fails."""
        await auth_service.register_user(
            email="test@example.com", password="ValidPassword123"
        )

        with pytest.raises(ValueError, match="Email already registered"):
            await auth_service.register_user(
                email="test@example.com", password="AnotherPassword123"
            )

    @pytest.mark.asyncio
    async def test_register_weak_password(self, auth_service, db_session):
        """Test registration with weak password fails."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            await auth_service.register_user(email="test@example.com", password="weak")


class TestUserAuthentication:
    """Test user authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_user(self, auth_service, db_session):
        """Test successful authentication."""
        # Register user
        await auth_service.register_user(
            email="test@example.com", password="ValidPassword123"
        )

        # Authenticate
        user = await auth_service.authenticate_user(
            email="test@example.com", password="ValidPassword123"
        )

        assert user is not None
        assert user.email == "test@example.com"
        assert user.last_login_at is not None

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, auth_service, db_session):
        """Test authentication with wrong password."""
        await auth_service.register_user(
            email="test@example.com", password="ValidPassword123"
        )

        user = await auth_service.authenticate_user(
            email="test@example.com", password="WrongPassword123"
        )

        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user(self, auth_service, db_session):
        """Test authentication with nonexistent email."""
        user = await auth_service.authenticate_user(
            email="nonexistent@example.com", password="Password123"
        )

        assert user is None


class TestAPIKeyOperations:
    """Test API key generation and verification."""

    @pytest.mark.asyncio
    async def test_generate_api_key(self, auth_service):
        """Test API key generation."""
        full_key, prefix, hashed_key = auth_service.generate_api_key()

        assert full_key.startswith("sk_live_")
        assert prefix == full_key[:16]
        assert len(hashed_key) == 64  # SHA-256 hex
        assert hashed_key != full_key

    @pytest.mark.asyncio
    async def test_create_api_key(self, auth_service, db_session):
        """Test API key creation for user."""
        # Create user first
        user = await auth_service.register_user(
            email="test@example.com", password="ValidPassword123"
        )

        # Create API key
        api_key, full_key = await auth_service.create_api_key(
            user_id=user.id, name="Test Key", scopes=["read", "write"]
        )

        assert api_key.id is not None
        assert api_key.name == "Test Key"
        assert api_key.scopes == ["read", "write"]
        assert api_key.key_prefix.startswith("sk_live_")
        assert full_key.startswith("sk_live_")
        assert api_key.is_active is True

    @pytest.mark.asyncio
    async def test_verify_api_key(self, auth_service, db_session):
        """Test API key verification."""
        # Create user and API key
        user = await auth_service.register_user(
            email="test@example.com", password="ValidPassword123"
        )

        api_key, full_key = await auth_service.create_api_key(
            user_id=user.id, name="Test Key"
        )

        # Verify key
        result = await auth_service.verify_api_key(full_key)

        assert result is not None
        verified_user, verified_key = result
        assert verified_user.id == user.id
        assert verified_key.id == api_key.id
        assert verified_key.last_used_at is not None

    @pytest.mark.asyncio
    async def test_verify_invalid_api_key(self, auth_service, db_session):
        """Test verification of invalid API key."""
        result = await auth_service.verify_api_key("sk_live_invalid_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_revoke_api_key(self, auth_service, db_session):
        """Test API key revocation."""
        # Create user and API key
        user = await auth_service.register_user(
            email="test@example.com", password="ValidPassword123"
        )

        api_key, full_key = await auth_service.create_api_key(
            user_id=user.id, name="Test Key"
        )

        # Revoke key
        await auth_service.revoke_api_key(api_key.id)

        # Verify key no longer works
        result = await auth_service.verify_api_key(full_key)
        assert result is None


class TestEmailVerification:
    """Test email verification workflow."""

    @pytest.mark.asyncio
    async def test_create_verification_token(self, auth_service):
        """Test verification token creation."""
        user_id = uuid4()
        token = auth_service.create_verification_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 20

    @pytest.mark.asyncio
    async def test_verify_email(self, auth_service, db_session):
        """Test email verification."""
        # Create unverified user
        user = await auth_service.register_user(
            email="test@example.com", password="ValidPassword123"
        )

        assert user.is_verified is False

        # Create verification token
        token = auth_service.create_verification_token(user.id)

        # Verify email
        success = await auth_service.verify_email(token)
        assert success

        # Check user is now verified
        verified_user = await auth_service.get_user_by_id(user.id)
        assert verified_user.is_verified is True

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, auth_service, db_session):
        """Test email verification with invalid token."""
        success = await auth_service.verify_email("invalid.token.here")
        assert not success


class TestPasswordReset:
    """Test password reset workflow."""

    @pytest.mark.asyncio
    async def test_create_reset_token(self, auth_service):
        """Test reset token creation."""
        user_id = uuid4()
        token = auth_service.create_reset_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 20

    @pytest.mark.asyncio
    async def test_reset_password(self, auth_service, db_session):
        """Test password reset."""
        # Create user
        user = await auth_service.register_user(
            email="test@example.com", password="OldPassword123"
        )

        # Verify old password works
        auth_user = await auth_service.authenticate_user(
            email="test@example.com", password="OldPassword123"
        )
        assert auth_user is not None

        # Create reset token
        reset_token = auth_service.create_reset_token(user.id)

        # Reset password
        success = await auth_service.reset_password(reset_token, "NewPassword456")
        assert success

        # Old password should no longer work
        auth_user = await auth_service.authenticate_user(
            email="test@example.com", password="OldPassword123"
        )
        assert auth_user is None

        # New password should work
        auth_user = await auth_service.authenticate_user(
            email="test@example.com", password="NewPassword456"
        )
        assert auth_user is not None

    @pytest.mark.asyncio
    async def test_reset_password_weak(self, auth_service, db_session):
        """Test password reset with weak password."""
        user = await auth_service.register_user(
            email="test@example.com", password="OldPassword123"
        )

        reset_token = auth_service.create_reset_token(user.id)

        with pytest.raises(ValueError, match="at least 8 characters"):
            await auth_service.reset_password(reset_token, "weak")


class TestUserLookup:
    """Test user lookup operations."""

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, auth_service, db_session):
        """Test getting user by ID."""
        user = await auth_service.register_user(
            email="test@example.com", password="ValidPassword123"
        )

        found_user = await auth_service.get_user_by_id(user.id)

        assert found_user is not None
        assert found_user.id == user.id
        assert found_user.email == user.email

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, auth_service, db_session):
        """Test getting user by email."""
        user = await auth_service.register_user(
            email="test@example.com", password="ValidPassword123"
        )

        found_user = await auth_service.get_user_by_email("test@example.com")

        assert found_user is not None
        assert found_user.id == user.id
        assert found_user.email == user.email

    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, auth_service, db_session):
        """Test getting nonexistent user returns None."""
        user = await auth_service.get_user_by_id(uuid4())
        assert user is None

        user = await auth_service.get_user_by_email("nonexistent@example.com")
        assert user is None


class TestSessionOperations:
    """Test session management (if implemented)."""

    @pytest.mark.asyncio
    async def test_create_session(self, auth_service, db_session):
        """Test session creation."""
        # Create user
        user = await auth_service.register_user(
            email="test@example.com", password="ValidPassword123"
        )

        # Create session
        session = await auth_service.create_session(
            user_id=user.id, ip_address="127.0.0.1", user_agent="Test Client"
        )

        assert session.id is not None
        assert session.user_id == user.id
        assert session.ip_address == "127.0.0.1"
        assert session.user_agent == "Test Client"
        assert session.expires_at is not None


class TestFullAuthFlow:
    """Test complete authentication flows."""

    @pytest.mark.asyncio
    async def test_register_login_flow(self, auth_service, db_session):
        """Test complete register and login flow."""
        # Register
        user = await auth_service.register_user(
            email="test@example.com", password="ValidPassword123", full_name="Test User"
        )

        assert user.id is not None
        assert not user.is_verified

        # Login
        auth_user = await auth_service.authenticate_user(
            email="test@example.com", password="ValidPassword123"
        )

        assert auth_user is not None
        assert auth_user.id == user.id

        # Create tokens
        access_token = auth_service.create_access_token(auth_user.id)
        refresh_token = auth_service.create_refresh_token(auth_user.id)

        # Verify tokens
        access_data = auth_service.verify_token(access_token, "access")
        refresh_data = auth_service.verify_token(refresh_token, "refresh")

        assert access_data.user_id == auth_user.id
        assert refresh_data.user_id == auth_user.id

    @pytest.mark.asyncio
    async def test_register_verify_login_flow(self, auth_service, db_session):
        """Test register, verify email, then login."""
        # Register
        user = await auth_service.register_user(
            email="test@example.com", password="ValidPassword123"
        )

        # Verify email
        verification_token = auth_service.create_verification_token(user.id)
        success = await auth_service.verify_email(verification_token)

        assert success

        # Check user is verified
        user = await auth_service.get_user_by_id(user.id)
        assert user.is_verified

        # Login should still work
        auth_user = await auth_service.authenticate_user(
            email="test@example.com", password="ValidPassword123"
        )

        assert auth_user is not None
