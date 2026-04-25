"""Unit tests for AsyncOmoiOSClient.

Tests use unittest.mock to mock httpx responses, verifying that:
1. The client makes correct HTTP requests (method, URL, headers, body)
2. Responses are parsed into correct Pydantic models
3. Errors are mapped to correct exception types
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from omoios import (
    AsyncOmoiOSClient,
    BindingKind,
    Credential,
    CreateCredentialRequest,
    CreateEnvironmentRequest,
    CreateEnvironmentVersionRequest,
    CreateWebhookRequest,
    Environment,
    EnvironmentVersion,
    EnvironmentVariable,
    Artifact,
    WebhookEvent,
    WebhookSubscription,
    WebhookDelivery,
    WorkspaceSettings,
    UpdateWorkspaceSettingsRequest,
)
from omoios.exceptions import AuthError, NotFoundError, ValidationError, ServerError


@pytest.fixture
def client():
    """Create an AsyncOmoiOSClient for testing."""
    return AsyncOmoiOSClient("http://localhost:18000", api_key="test-api-key")


@pytest.fixture
def jwt_client():
    """Create an AsyncOmoiOSClient with JWT authentication."""
    return AsyncOmoiOSClient("http://localhost:18000", jwt_token="test-jwt-token")


class TestAsyncClientAuth:
    """Test authentication headers."""

    @pytest.mark.asyncio
    async def test_api_key_auth(self, client):
        """Test API key is sent as Authorization: Bearer (spec §01) + legacy X-API-Key."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client.credentials.list(workspace_id="ws-1")

            call_args = mock_request.call_args
            # Spec §01 primary: Bearer token
            assert call_args.kwargs["headers"]["Authorization"] == "Bearer test-api-key"
            # Transitional echo for backends not yet on Bearer
            assert call_args.kwargs["headers"]["X-API-Key"] == "test-api-key"

    @pytest.mark.asyncio
    async def test_jwt_auth(self, jwt_client):
        """Test JWT token is sent in Authorization header."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        with patch.object(jwt_client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await jwt_client.credentials.list(workspace_id="ws-1")

            call_args = mock_request.call_args
            assert call_args.kwargs["headers"]["Authorization"] == "Bearer test-jwt-token"

    @pytest.mark.asyncio
    async def test_auth_error_raises_auth_error(self, client):
        """Test 401 response raises AuthError."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Invalid API key"}

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            with pytest.raises(AuthError):
                await client.credentials.list(workspace_id="ws-1")


class TestAsyncClientCredentials:
    """Test credential operations."""

    @pytest.mark.asyncio
    async def test_list_credentials(self, client):
        """Test list_credentials makes correct request and parses response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "workspace_id": "550e8400-e29b-41d4-a716-446655440001",
                "kind": "bearer_secret",
                "name": "test-api-key",
                "config": {"scope": "read"},
                "version": 1,
                "created_at": "2024-01-01T00:00:00Z",
                "rotated_at": None,
            }
        ]

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            creds = await client.credentials.list(workspace_id="ws-1")

            assert len(creds) == 1
            assert isinstance(creds[0], Credential)
            assert creds[0].name == "test-api-key"
            assert creds[0].version == 1
            assert creds[0].config == {"scope": "read"}

            mock_request.assert_called_once_with(
                "GET",
                "http://localhost:18000/api/v1/credentials",
                headers={"Authorization": "Bearer test-api-key", "X-API-Key": "test-api-key"},
                params={"workspace_id": "ws-1"},
            )

    @pytest.mark.asyncio
    async def test_get_credential(self, client):
        """Test get_credential makes correct request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "workspace_id": "550e8400-e29b-41d4-a716-446655440001",
            "kind": "bearer_secret",
            "name": "test-api-key",
            "config": {},
            "version": 1,
            "created_at": "2024-01-01T00:00:00Z",
            "rotated_at": None,
        }

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            cred = await client.credentials.get("550e8400-e29b-41d4-a716-446655440000")

            assert isinstance(cred, Credential)
            assert cred.id == "550e8400-e29b-41d4-a716-446655440000"
            mock_request.assert_called_once_with(
                "GET",
                "http://localhost:18000/api/v1/credentials/550e8400-e29b-41d4-a716-446655440000",
                headers={"Authorization": "Bearer test-api-key", "X-API-Key": "test-api-key"},
            )

    @pytest.mark.asyncio
    async def test_get_credential_not_found(self, client):
        """Test get_credential raises NotFoundError on 404."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"detail": "Credential not found"}

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            with pytest.raises(NotFoundError, match="Credential not found"):
                await client.credentials.get("invalid-id")

    @pytest.mark.asyncio
    async def test_create_credential(self, client):
        """Test create_credential sends correct request body."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "workspace_id": "550e8400-e29b-41d4-a716-446655440001",
            "kind": "user_oauth",
            "name": "oauth-token",
            "config": {"scopes": ["repo"]},
            "version": 1,
            "created_at": "2024-01-01T00:00:00Z",
            "rotated_at": None,
        }

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            request = CreateCredentialRequest(
                workspace_id="550e8400-e29b-41d4-a716-446655440001",
                kind=BindingKind.USER_OAUTH,
                name="oauth-token",
                value="secret-value",
                config={"scopes": ["repo"]},
            )
            cred = await client.credentials.create(request)

            assert isinstance(cred, Credential)
            assert cred.name == "oauth-token"
            assert cred.config == {"scopes": ["repo"]}

            call_args = mock_request.call_args
            assert call_args.args[0] == "POST"
            assert call_args.args[1] == "http://localhost:18000/api/v1/credentials"
            sent_json = call_args.kwargs["json"]
            assert sent_json["kind"] == "user_oauth"
            assert sent_json["value"] == "secret-value"

    @pytest.mark.asyncio
    async def test_delete_credential(self, client):
        """Test delete_credential makes DELETE request."""
        mock_response = MagicMock()
        mock_response.status_code = 204

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client.credentials.delete("550e8400-e29b-41d4-a716-446655440000")

            mock_request.assert_called_once_with(
                "DELETE",
                "http://localhost:18000/api/v1/credentials/550e8400-e29b-41d4-a716-446655440000",
                headers={"Authorization": "Bearer test-api-key", "X-API-Key": "test-api-key"},
            )


class TestAsyncClientEnvironments:
    """Test environment operations."""

    @pytest.mark.asyncio
    async def test_list_environments(self, client):
        """Test list_environments makes correct request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "org_id": "550e8400-e29b-41d4-a716-446655440001",
                "name": "staging",
                "description": "Staging environment",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        ]

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            envs = await client.environments.list(org_id="org-1")

            assert len(envs) == 1
            assert isinstance(envs[0], Environment)
            assert envs[0].name == "staging"
            mock_request.assert_called_once_with(
                "GET",
                "http://localhost:18000/api/v1/environments",
                headers={"Authorization": "Bearer test-api-key", "X-API-Key": "test-api-key"},
                params={"org_id": "org-1"},
            )

    @pytest.mark.asyncio
    async def test_get_environment(self, client):
        """Test get_environment returns environment with version."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "environment": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "org_id": "550e8400-e29b-41d4-a716-446655440001",
                "name": "staging",
                "description": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
            "latest_version": {
                "id": "550e8400-e29b-41d4-a716-446655440002",
                "environment_id": "550e8400-e29b-41d4-a716-446655440000",
                "version_number": 1,
                "variables": {
                    "DB_URL": {"type": "string", "value": "postgres://localhost/staging"}
                },
                "created_at": "2024-01-01T00:00:00Z",
            },
        }

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            result = await client.environments.get("550e8400-e29b-41d4-a716-446655440000")

            assert "environment" in result
            assert "latest_version" in result
            assert isinstance(result["environment"], Environment)
            assert isinstance(result["latest_version"], EnvironmentVersion)
            assert result["latest_version"].version_number == 1

    @pytest.mark.asyncio
    async def test_create_environment(self, client):
        """Test create_environment sends correct request."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "org_id": "550e8400-e29b-41d4-a716-446655440001",
            "name": "production",
            "description": "Production environment",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            request = CreateEnvironmentRequest(
                name="production",
                description="Production environment",
                org_id="550e8400-e29b-41d4-a716-446655440001",
            )
            env = await client.environments.create(request)

            assert isinstance(env, Environment)
            assert env.name == "production"

    @pytest.mark.asyncio
    async def test_create_environment_version(self, client):
        """Test create_environment_version sends correct request."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "550e8400-e29b-41d4-a716-446655440002",
            "environment_id": "550e8400-e29b-41d4-a716-446655440000",
            "version_number": 1,
            "variables": {"VAR1": {"type": "string", "value": "hello"}},
            "created_at": "2024-01-01T00:00:00Z",
        }

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            request = CreateEnvironmentVersionRequest(
                variables={
                    "VAR1": EnvironmentVariable(type="string", value="hello")
                }
            )
            version = await client.environments.create_version(
                "550e8400-e29b-41d4-a716-446655440000", request
            )

            assert isinstance(version, EnvironmentVersion)
            assert version.version_number == 1
            assert version.variables["VAR1"].type.value == "string"


class TestAsyncClientArtifacts:
    """Test artifact operations."""

    @pytest.mark.asyncio
    async def test_upload_artifact(self, client):
        """Test upload_artifact sends multipart request."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "workspace_id": "550e8400-e29b-41d4-a716-446655440001",
            "name": "test.txt",
            "storage_backend": "local",
            "checksum": "sha256:abc123",
            "size_bytes": 12,
            "content_type": "text/plain",
            "artifact_metadata": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            artifact = await client.artifacts.upload(
                file_content=b"hello world",
                workspace_id="ws-1",
                filename="test.txt",
            )

            assert isinstance(artifact, Artifact)
            assert artifact.name == "test.txt"
            assert artifact.size_bytes == 12

            call_args = mock_request.call_args
            assert call_args.args[0] == "POST"
            assert call_args.args[1] == "http://localhost:18000/api/v1/artifacts/upload"

    @pytest.mark.asyncio
    async def test_list_artifacts(self, client):
        """Test list_artifacts makes correct request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "workspace_id": "ws-1",
                "name": "test.txt",
                "storage_backend": "local",
                "checksum": "sha256:abc123",
                "size_bytes": 12,
                "content_type": "text/plain",
                "artifact_metadata": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        ]

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            artifacts = await client.artifacts.list(workspace_id="ws-1")

            assert len(artifacts) == 1
            assert isinstance(artifacts[0], Artifact)

    @pytest.mark.asyncio
    async def test_download_artifact(self, client):
        """Test download_artifact returns bytes."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"file content"

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            content = await client.artifacts.download("art-1")

            assert content == b"file content"
            mock_request.assert_called_once_with(
                "GET",
                "http://localhost:18000/api/v1/artifacts/art-1/download",
                headers={"Authorization": "Bearer test-api-key", "X-API-Key": "test-api-key"},
            )

    @pytest.mark.asyncio
    async def test_delete_artifact(self, client):
        """Test delete_artifact makes DELETE request."""
        mock_response = MagicMock()
        mock_response.status_code = 204

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client.artifacts.delete("art-1")

            mock_request.assert_called_once_with(
                "DELETE",
                "http://localhost:18000/api/v1/artifacts/art-1",
                headers={"Authorization": "Bearer test-api-key", "X-API-Key": "test-api-key"},
            )


class TestAsyncClientWebhooks:
    """Test webhook operations."""

    @pytest.mark.asyncio
    async def test_list_webhooks(self, client):
        """Test list_webhooks makes correct request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "wh-1",
                "org_id": "org-1",
                "url": "https://example.com/webhook",
                "events": ["spec.created", "task.started"],
                "active": True,
                "created_at": "2024-01-01T00:00:00Z",
            }
        ]

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            webhooks = await client.webhooks.list()

            assert len(webhooks) == 1
            assert isinstance(webhooks[0], WebhookSubscription)
            assert webhooks[0].url == "https://example.com/webhook"

    @pytest.mark.asyncio
    async def test_create_webhook(self, client):
        """Test create_webhook sends correct request."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "wh-1",
            "org_id": "org-1",
            "url": "https://myapp.com/webhook",
            "events": ["spec.created"],
            "active": True,
            "created_at": "2024-01-01T00:00:00Z",
        }

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            request = CreateWebhookRequest(
                url="https://myapp.com/webhook",
                events=[WebhookEvent.SPEC_CREATED],
                secret="webhook-secret",
            )
            webhook = await client.webhooks.create(request)

            assert isinstance(webhook, WebhookSubscription)
            assert webhook.url == "https://myapp.com/webhook"

    @pytest.mark.asyncio
    async def test_delete_webhook(self, client):
        """Test delete_webhook makes DELETE request."""
        mock_response = MagicMock()
        mock_response.status_code = 204

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            await client.webhooks.delete("wh-1")

            mock_request.assert_called_once_with(
                "DELETE",
                "http://localhost:18000/api/v1/webhooks/wh-1",
                headers={"Authorization": "Bearer test-api-key", "X-API-Key": "test-api-key"},
            )

    @pytest.mark.asyncio
    async def test_list_webhook_deliveries(self, client):
        """Test list_webhook_deliveries makes correct request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "wd-1",
                "subscription_id": "wh-1",
                "event": "spec.created",
                "payload": {"spec_id": "spec-1"},
                "status": "delivered",
                "attempts": 1,
                "next_retry_at": None,
                "created_at": "2024-01-01T00:00:00Z",
            }
        ]

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            deliveries = await client.webhooks.list_deliveries("wh-1")

            assert len(deliveries) == 1
            assert isinstance(deliveries[0], WebhookDelivery)
            assert deliveries[0].status == "delivered"


class TestAsyncClientWorkspaces:
    """Test workspace operations."""

    @pytest.mark.asyncio
    async def test_get_workspace_settings(self, client):
        """Test get_workspace_settings makes correct request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "ws-settings-1",
            "workspace_id": "ws-1",
            "egress_allowlist": ["api.github.com"],
            "max_artifact_size_mb": 100,
            "allowed_binding_kinds": ["bearer_secret", "user_oauth"],
        }

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            settings = await client.workspaces.get_settings("ws-1")

            assert isinstance(settings, WorkspaceSettings)
            assert settings.workspace_id == "ws-1"
            assert settings.max_artifact_size_mb == 100
            mock_request.assert_called_once_with(
                "GET",
                "http://localhost:18000/api/v1/workspaces/ws-1/settings",
                headers={"Authorization": "Bearer test-api-key", "X-API-Key": "test-api-key"},
            )

    @pytest.mark.asyncio
    async def test_update_workspace_settings(self, client):
        """Test update_workspace_settings sends correct request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "ws-settings-1",
            "workspace_id": "ws-1",
            "egress_allowlist": ["api.github.com", "pypi.org"],
            "max_artifact_size_mb": 200,
            "allowed_binding_kinds": ["bearer_secret"],
        }

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            request = UpdateWorkspaceSettingsRequest(
                egress_allowlist=["api.github.com", "pypi.org"],
                max_artifact_size_mb=200,
            )
            settings = await client.workspaces.update_settings("ws-1", request)

            assert isinstance(settings, WorkspaceSettings)
            assert settings.max_artifact_size_mb == 200

            call_args = mock_request.call_args
            assert call_args.args[0] == "PUT"
            sent_json = call_args.kwargs["json"]
            assert sent_json["max_artifact_size_mb"] == 200


class TestAsyncClientErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_not_found_error(self, client):
        """Test 404 raises NotFoundError."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"detail": "Not found"}

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            with pytest.raises(NotFoundError):
                await client.credentials.get("missing")

    @pytest.mark.asyncio
    async def test_validation_error(self, client):
        """Test 400 raises ValidationError."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"detail": "Invalid kind"}

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            with pytest.raises(ValidationError):
                await client.credentials.create(
                    CreateCredentialRequest(
                        workspace_id="ws-1",
                        kind=BindingKind.BEARER_SECRET,
                        name="test",
                        value="val",
                    )
                )

    @pytest.mark.asyncio
    async def test_server_error(self, client):
        """Test 500 raises ServerError."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"detail": "Internal error"}

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            with pytest.raises(ServerError):
                await client.environments.list(org_id="org-1")

    @pytest.mark.asyncio
    async def test_client_context_manager(self):
        """Test client works as async context manager."""
        async with AsyncOmoiOSClient("http://localhost:18000", api_key="key") as client:
            assert client.api_key == "key"
            assert client._http is not None
