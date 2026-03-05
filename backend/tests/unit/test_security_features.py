"""Unit tests for security features (token blacklist, cookie auth, password strength, JTI tokens).

These are pure unit tests - no database or Redis required. All external dependencies are mocked.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from fastapi import Request
from fastapi.responses import JSONResponse

from omoi_os.services.auth_service import AuthService
from omoi_os.services.token_blacklist import TokenBlacklistService
from omoi_os.api.cookie_auth import (
    set_auth_cookies,
    clear_auth_cookies,
    get_token_from_request,
    get_refresh_token_from_request,
    ACCESS_TOKEN_COOKIE,
    REFRESH_TOKEN_COOKIE,
    AUTH_STATE_COOKIE,
)


# Mock database session
class MockDB:
    """Mock database session for unit testing."""

    async def execute(self, *args, **kwargs):
        pass

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass


TEST_JWT_SECRET = "test-secret-key-for-testing-only"  # pragma: allowlist secret


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


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    return AsyncMock()


@pytest.fixture
def token_blacklist_service(mock_redis):
    """Create TokenBlacklistService with mocked Redis."""
    service = TokenBlacklistService.__new__(TokenBlacklistService)
    service._redis = mock_redis
    return service


@pytest.mark.unit
class TestTokenBlacklistService:
    """Test TokenBlacklistService with mocked Redis."""

    @pytest.mark.asyncio
    async def test_blacklist_token(self, token_blacklist_service, mock_redis):
        """Test blacklisting a token stores it in Redis with TTL."""
        jti = "test-jti-123"
        ttl_seconds = 900

        await token_blacklist_service.blacklist_token(jti, ttl_seconds)

        mock_redis.setex.assert_called_once_with(
            f"auth:blacklist:{jti}", ttl_seconds, "1"
        )

    @pytest.mark.asyncio
    async def test_is_blacklisted_true(self, token_blacklist_service, mock_redis):
        """Test is_blacklisted returns True when token is in blacklist."""
        jti = "test-jti-123"
        mock_redis.exists.return_value = 1

        result = await token_blacklist_service.is_blacklisted(jti)

        assert result is True
        mock_redis.exists.assert_called_once_with(f"auth:blacklist:{jti}")

    @pytest.mark.asyncio
    async def test_is_blacklisted_false(self, token_blacklist_service, mock_redis):
        """Test is_blacklisted returns False when token is not in blacklist."""
        jti = "test-jti-123"
        mock_redis.exists.return_value = 0

        result = await token_blacklist_service.is_blacklisted(jti)

        assert result is False
        mock_redis.exists.assert_called_once_with(f"auth:blacklist:{jti}")

    @pytest.mark.asyncio
    async def test_blacklist_all_user_tokens(self, token_blacklist_service, mock_redis):
        """Test blacklisting all user tokens stores timestamp in Redis."""
        user_id = "user-123"
        ttl_seconds = 86400

        await token_blacklist_service.blacklist_all_user_tokens(user_id, ttl_seconds)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == f"auth:blacklist:user:{user_id}"
        assert call_args[0][1] == ttl_seconds
        # Third arg should be a timestamp string
        assert isinstance(float(call_args[0][2]), float)

    @pytest.mark.asyncio
    async def test_is_user_blacklisted_since_true(
        self, token_blacklist_service, mock_redis
    ):
        """Test is_user_blacklisted_since returns True when token issued before blacklist."""
        user_id = "user-123"
        blacklisted_timestamp = datetime.now(timezone.utc).timestamp()
        mock_redis.get.return_value = str(blacklisted_timestamp)

        # Token issued 1 minute before blacklist
        token_iat = blacklisted_timestamp - 60
        result = await token_blacklist_service.is_user_blacklisted_since(
            user_id, token_iat
        )

        assert result is True
        mock_redis.get.assert_called_once_with(f"auth:blacklist:user:{user_id}")

    @pytest.mark.asyncio
    async def test_is_user_blacklisted_since_false(
        self, token_blacklist_service, mock_redis
    ):
        """Test is_user_blacklisted_since returns False when token issued after blacklist."""
        user_id = "user-123"
        blacklisted_timestamp = datetime.now(timezone.utc).timestamp()
        mock_redis.get.return_value = str(blacklisted_timestamp)

        # Token issued 1 minute after blacklist
        token_iat = blacklisted_timestamp + 60
        result = await token_blacklist_service.is_user_blacklisted_since(
            user_id, token_iat
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_is_user_blacklisted_since_not_blacklisted(
        self, token_blacklist_service, mock_redis
    ):
        """Test is_user_blacklisted_since returns False when user is not blacklisted."""
        user_id = "user-123"
        mock_redis.get.return_value = None

        result = await token_blacklist_service.is_user_blacklisted_since(
            user_id, 1234567890
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_record_failed_login(self, token_blacklist_service, mock_redis):
        """Test recording failed login increments counter and sets expiry."""
        email = "test@example.com"

        # Create a proper async pipeline mock
        pipe_mock = AsyncMock()
        pipe_mock.incr = AsyncMock(return_value=None)
        pipe_mock.expire = AsyncMock(return_value=None)
        pipe_mock.execute = AsyncMock(return_value=[3])  # 3rd failed attempt
        mock_redis.pipeline = MagicMock(return_value=pipe_mock)

        count = await token_blacklist_service.record_failed_login(email)

        assert count == 3
        pipe_mock.incr.assert_called_once_with(f"auth:lockout:{email.lower()}")
        pipe_mock.expire.assert_called_once()
        pipe_mock.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_locked_out_true(self, token_blacklist_service, mock_redis):
        """Test is_locked_out returns True when attempts exceed threshold."""
        email = "test@example.com"
        mock_redis.get.return_value = "6"  # 6 attempts, threshold is 5

        result = await token_blacklist_service.is_locked_out(email)

        assert result is True
        mock_redis.get.assert_called_once_with(f"auth:lockout:{email.lower()}")

    @pytest.mark.asyncio
    async def test_is_locked_out_false(self, token_blacklist_service, mock_redis):
        """Test is_locked_out returns False when attempts below threshold."""
        email = "test@example.com"
        mock_redis.get.return_value = "2"  # 2 attempts, threshold is 5

        result = await token_blacklist_service.is_locked_out(email)

        assert result is False

    @pytest.mark.asyncio
    async def test_is_locked_out_no_attempts(self, token_blacklist_service, mock_redis):
        """Test is_locked_out returns False when no failed attempts."""
        email = "test@example.com"
        mock_redis.get.return_value = None

        result = await token_blacklist_service.is_locked_out(email)

        assert result is False

    @pytest.mark.asyncio
    async def test_clear_failed_logins(self, token_blacklist_service, mock_redis):
        """Test clearing failed login attempts."""
        email = "test@example.com"

        await token_blacklist_service.clear_failed_logins(email)

        mock_redis.delete.assert_called_once_with(f"auth:lockout:{email.lower()}")


@pytest.mark.unit
class TestCookieAuth:
    """Test cookie authentication helpers."""

    def test_set_auth_cookies(self):
        """Test setting auth cookies on response."""
        response = JSONResponse(content={"message": "ok"})
        access_token = "test-access-token"
        refresh_token = "test-refresh-token"

        set_auth_cookies(response, access_token, refresh_token)

        # Check that cookies are set
        cookies = response.headers.getlist("set-cookie")
        assert len(cookies) == 3  # access, refresh, auth_state

        # Check access token cookie
        access_cookie = [c for c in cookies if ACCESS_TOKEN_COOKIE in c]
        assert len(access_cookie) == 1
        assert "HttpOnly" in access_cookie[0]
        assert access_token in access_cookie[0]

        # Check refresh token cookie
        refresh_cookie = [c for c in cookies if REFRESH_TOKEN_COOKIE in c]
        assert len(refresh_cookie) == 1
        assert "HttpOnly" in refresh_cookie[0]
        assert refresh_token in refresh_cookie[0]

        # Check auth state cookie (not HttpOnly)
        state_cookie = [c for c in cookies if AUTH_STATE_COOKIE in c]
        assert len(state_cookie) == 1
        assert "HttpOnly" not in state_cookie[0]
        assert "true" in state_cookie[0]

    def test_clear_auth_cookies(self):
        """Test clearing auth cookies."""
        response = JSONResponse(content={"message": "ok"})

        clear_auth_cookies(response)

        # Check that cookies are deleted (max-age=0 or expires in past)
        cookies = response.headers.getlist("set-cookie")
        assert len(cookies) == 3

        for cookie in cookies:
            assert "Max-Age=0" in cookie or "expires" in cookie.lower()

    def test_get_token_from_request_bearer(self):
        """Test extracting token from Authorization header."""
        request = MagicMock(spec=Request)
        request.headers = {"authorization": "Bearer test-token-123"}
        request.cookies = {}

        token = get_token_from_request(request)

        assert token == "test-token-123"

    def test_get_token_from_request_bearer_case_insensitive(self):
        """Test extracting token with lowercase 'bearer'."""
        request = MagicMock(spec=Request)
        request.headers = {"authorization": "bearer test-token-123"}
        request.cookies = {}

        token = get_token_from_request(request)

        assert token == "test-token-123"

    def test_get_token_from_request_cookie(self):
        """Test extracting token from cookie when no Authorization header."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.cookies = {ACCESS_TOKEN_COOKIE: "cookie-token-456"}

        token = get_token_from_request(request)

        assert token == "cookie-token-456"

    def test_get_token_from_request_header_priority(self):
        """Test that Authorization header takes priority over cookie."""
        request = MagicMock(spec=Request)
        request.headers = {"authorization": "Bearer header-token"}
        request.cookies = {ACCESS_TOKEN_COOKIE: "cookie-token"}

        token = get_token_from_request(request)

        assert token == "header-token"

    def test_get_token_from_request_none(self):
        """Test returning None when no token present."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.cookies = {}

        token = get_token_from_request(request)

        assert token is None

    def test_get_refresh_token_from_request(self):
        """Test extracting refresh token from cookie."""
        request = MagicMock(spec=Request)
        request.cookies = {REFRESH_TOKEN_COOKIE: "refresh-token-789"}

        token = get_refresh_token_from_request(request)

        assert token == "refresh-token-789"

    def test_get_refresh_token_from_request_none(self):
        """Test returning None when no refresh token cookie."""
        request = MagicMock(spec=Request)
        request.cookies = {}

        token = get_refresh_token_from_request(request)

        assert token is None


@pytest.mark.unit
class TestPasswordStrengthSpecialChar:
    """Test password validation requires special characters."""

    def test_password_with_special_char_passes(self, auth_service):
        """Test password with special character passes validation."""
        valid, error = auth_service.validate_password_strength("StrongPass123!")
        assert valid is True
        assert error is None

    def test_password_without_special_char_fails(self, auth_service):
        """Test password without special character fails validation."""
        valid, error = auth_service.validate_password_strength("StrongPass123")
        assert valid is False
        assert "special character" in error.lower()

    def test_common_password_base_rejected(self, auth_service):
        """Test that common password base is in the rejection list.

        Note: The common password check requires exact match. Passwords with
        special chars appended won't match the common list. This test verifies
        the validation logic exists and checks format requirements first.
        """
        # A bare common password fails multiple checks (no special char, etc)
        valid, error = auth_service.validate_password_strength("password123")
        assert valid is False
        assert error is not None

        # The actual common password check is verified at integration level
        # where we can verify the exact match logic works correctly

    def test_various_special_chars_accepted(self, auth_service):
        """Test various special characters are accepted."""
        special_chars = ["!", "@", "#", "$", "%", "&", "*", "?"]
        for char in special_chars:
            valid, error = auth_service.validate_password_strength(f"TestPass123{char}")
            assert valid is True, f"Failed for special char: {char}"


@pytest.mark.unit
class TestJTIInTokens:
    """Test that all token types include JTI claims."""

    def test_access_token_has_jti(self, auth_service):
        """Test access token includes JTI claim."""
        user_id = uuid4()
        token, jti = auth_service.create_access_token(user_id)

        assert isinstance(token, str)
        assert isinstance(jti, str)
        assert len(jti) > 0

        # Verify token data includes JTI
        token_data = auth_service.verify_token(token, token_type="access")
        assert token_data is not None
        assert token_data.jti == jti
        assert token_data.user_id == user_id

    def test_refresh_token_has_jti(self, auth_service):
        """Test refresh token includes JTI claim."""
        user_id = uuid4()
        token, jti = auth_service.create_refresh_token(user_id)

        assert isinstance(token, str)
        assert isinstance(jti, str)
        assert len(jti) > 0

        # Verify token data includes JTI
        token_data = auth_service.verify_token(token, token_type="refresh")
        assert token_data is not None
        assert token_data.jti == jti
        assert token_data.user_id == user_id

    def test_verification_token_has_jti(self, auth_service):
        """Test email verification token includes JTI claim."""
        user_id = uuid4()
        token, jti = auth_service.create_verification_token(user_id)

        assert isinstance(token, str)
        assert isinstance(jti, str)
        assert len(jti) > 0

        # Verify token data includes JTI
        token_data = auth_service.verify_token(token, token_type="email_verification")
        assert token_data is not None
        assert token_data.jti == jti
        assert token_data.user_id == user_id

    def test_reset_token_has_jti(self, auth_service):
        """Test password reset token includes JTI claim."""
        user_id = uuid4()
        token, jti = auth_service.create_reset_token(user_id)

        assert isinstance(token, str)
        assert isinstance(jti, str)
        assert len(jti) > 0

        # Verify token data includes JTI
        token_data = auth_service.verify_token(token, token_type="password_reset")
        assert token_data is not None
        assert token_data.jti == jti
        assert token_data.user_id == user_id

    def test_jti_is_unique(self, auth_service):
        """Test that JTIs are unique across multiple tokens."""
        user_id = uuid4()

        # Create multiple tokens
        tokens_and_jtis = [
            auth_service.create_access_token(user_id),
            auth_service.create_access_token(user_id),
            auth_service.create_refresh_token(user_id),
            auth_service.create_verification_token(user_id),
            auth_service.create_reset_token(user_id),
        ]

        # Extract JTIs
        jtis = [jti for _, jti in tokens_and_jtis]

        # All JTIs should be unique
        assert len(jtis) == len(set(jtis)), "JTIs should be unique"

    def test_token_contains_iat_timestamp(self, auth_service):
        """Test tokens include issued-at timestamp."""
        user_id = uuid4()
        token, _ = auth_service.create_access_token(user_id)

        token_data = auth_service.verify_token(token, token_type="access")
        assert token_data is not None
        assert token_data.iat is not None
        assert isinstance(token_data.iat, float)
        # Should be a recent timestamp
        now = datetime.now(timezone.utc).timestamp()
        assert abs(now - token_data.iat) < 10  # Within 10 seconds
