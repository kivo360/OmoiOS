"""Tests for /api/v1/auth/* endpoints.

Run options:
    pytest tests/api/test_auth_api.py -m unit       # Fast unit tests only
    pytest tests/api/test_auth_api.py -m integration  # Integration tests (need DB)
    pytest tests/api/test_auth_api.py -m auth       # All auth tests
    pytest tests/api/test_auth_api.py               # All tests
"""

import pytest
from fastapi.testclient import TestClient

from omoi_os.models.user import User

# =============================================================================
# UNIT TESTS (Fast, no database required, uses mocked dependencies)
# =============================================================================


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.auth
class TestAuthEndpointsUnit:
    """Unit tests for auth endpoints using mocked authentication."""

    def test_get_me_mock_authenticated(self, mock_authenticated_client: TestClient):
        """Test /me using mock authentication (fastest, no DB)."""
        response = mock_authenticated_client.get("/api/v1/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "mockuser@example.com"
        assert data["full_name"] == "Mock User"

    def test_logout_mock_authenticated(self, mock_authenticated_client: TestClient):
        """Test logout endpoint with mocked auth."""
        response = mock_authenticated_client.post("/api/v1/auth/logout")

        assert response.status_code == 200
        assert "logged out" in response.json()["message"].lower()


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.auth
class TestAuthValidationUnit:
    """Unit tests for request validation (no auth needed)."""

    def test_register_missing_email(self, client: TestClient):
        """Test registration fails without email."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "password": "SecurePass123!",
                "full_name": "No Email User",
            },
        )
        assert response.status_code == 422

    def test_register_invalid_email_format(self, client: TestClient):
        """Test registration fails with invalid email format."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123!",
                "full_name": "Bad Email User",
            },
        )
        assert response.status_code == 422

    def test_login_missing_password(self, client: TestClient):
        """Test login fails without password."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com"},
        )
        assert response.status_code == 422

    def test_refresh_missing_token(self, client: TestClient):
        """Test refresh fails without token."""
        response = client.post("/api/v1/auth/refresh", json={})
        assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.auth
class TestProtectedEndpointsUnit:
    """Unit tests verifying endpoints require authentication."""

    @pytest.mark.parametrize(
        "method,endpoint",
        [
            ("GET", "/api/v1/auth/me"),
            ("PATCH", "/api/v1/auth/me"),
            ("POST", "/api/v1/auth/logout"),
            ("POST", "/api/v1/auth/change-password"),
            ("GET", "/api/v1/auth/api-keys"),
            ("POST", "/api/v1/auth/api-keys"),
        ],
    )
    def test_endpoint_requires_auth(
        self, client: TestClient, method: str, endpoint: str
    ):
        """Test that protected endpoints return 401/403 without auth."""
        if method == "GET":
            response = client.get(endpoint)
        elif method == "POST":
            response = client.post(endpoint, json={})
        elif method == "PATCH":
            response = client.patch(endpoint, json={})
        else:
            response = client.request(method, endpoint)

        assert response.status_code in [401, 403, 422]


# =============================================================================
# INTEGRATION TESTS (Slower, requires database, tests real auth flow)
# =============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.auth
@pytest.mark.requires_db
class TestAuthRegistrationIntegration:
    """Integration tests for user registration with real database."""

    def test_register_success(self, client: TestClient):
        """Test successful user registration creates user in database."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "full_name": "New User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert "id" in data
        assert "hashed_password" not in data  # Never expose password

    def test_register_duplicate_email(self, client: TestClient):
        """Test registration fails for duplicate email."""
        # First registration
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePass123!",
                "full_name": "First User",
            },
        )

        # Second registration with same email
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "DifferentPass123!",
                "full_name": "Second User",
            },
        )

        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.auth
@pytest.mark.requires_db
class TestAuthLoginIntegration:
    """Integration tests for login with real database."""

    def test_login_success(self, client: TestClient, test_user: User):
        """Test successful login returns valid JWT tokens."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPass123!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

        # Verify token is usable
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == test_user.email

    def test_login_invalid_password(self, client: TestClient, test_user: User):
        """Test login fails with wrong password."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login fails for non-existent user."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePass123!",
            },
        )

        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.auth
@pytest.mark.requires_db
class TestAuthMeIntegration:
    """Integration tests for /auth/me with real JWT tokens."""

    def test_get_me_with_real_token(
        self, client: TestClient, auth_headers: dict, test_user: User
    ):
        """Test /me with real JWT token."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["id"] == str(test_user.id)
        assert data["full_name"] == test_user.full_name

    def test_get_me_authenticated_client(
        self, authenticated_client: TestClient, test_user: User
    ):
        """Test /me using authenticated_client fixture."""
        response = authenticated_client.get("/api/v1/auth/me")

        assert response.status_code == 200
        assert response.json()["email"] == test_user.email

    def test_update_me(self, authenticated_client: TestClient, test_user: User):
        """Test updating user profile."""
        response = authenticated_client.patch(
            "/api/v1/auth/me",
            json={"full_name": "Updated Name"},
        )

        assert response.status_code == 200
        assert response.json()["full_name"] == "Updated Name"


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.auth
@pytest.mark.requires_db
class TestAuthTokenRefreshIntegration:
    """Integration tests for token refresh."""

    def test_refresh_token_success(self, client: TestClient, test_user: User):
        """Test refreshing access token with valid refresh token."""
        # Login to get tokens
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPass123!",
            },
        )
        tokens = login_response.json()

        # Refresh
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )

        assert response.status_code == 200
        new_tokens = response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens

        # New token should work
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
        )
        assert me_response.status_code == 200

    def test_refresh_token_invalid(self, client: TestClient):
        """Test refresh fails with invalid token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token-here"},
        )

        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.auth
@pytest.mark.requires_db
class TestAuthAPIKeysIntegration:
    """Integration tests for API key management."""

    def test_create_and_list_api_keys(self, authenticated_client: TestClient):
        """Test creating and listing API keys."""
        # Create API key
        create_response = authenticated_client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Test Key", "scopes": ["read"]},
        )

        assert create_response.status_code == 201
        key_data = create_response.json()
        assert key_data["name"] == "Test Key"
        assert "key" in key_data  # Full key returned only on creation

        # List API keys
        list_response = authenticated_client.get("/api/v1/auth/api-keys")

        assert list_response.status_code == 200
        keys = list_response.json()
        assert len(keys) >= 1
        assert any(k["name"] == "Test Key" for k in keys)
