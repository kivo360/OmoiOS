"""Unit tests for RepositoryService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from omoi_os.services.repository_service import (
    GitHubAPIError,
    RepositoryService,
)
from omoi_os.schemas.github import (
    CreateRepositoryRequest,
    RepoVisibility,
    RepoTemplate,
)


class TestRepositoryService:
    """Tests for RepositoryService."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock httpx client."""
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def service(self, mock_client):
        """Create a RepositoryService with mocked client."""
        with patch("omoi_os.services.repository_service.httpx.AsyncClient") as mock:
            mock.return_value = mock_client
            svc = RepositoryService(github_token="test-token")
            svc.client = mock_client
            return svc

    @pytest.mark.asyncio
    async def test_list_owners_returns_user_and_orgs(self, service, mock_client):
        """Test list_owners returns authenticated user and their orgs."""
        # Mock user response
        mock_user_resp = MagicMock()
        mock_user_resp.status_code = 200
        mock_user_resp.json.return_value = {
            "login": "testuser",
            "id": 123,
            "avatar_url": "https://example.com/avatar.png",
        }

        # Mock orgs response
        mock_orgs_resp = MagicMock()
        mock_orgs_resp.status_code = 200
        mock_orgs_resp.json.return_value = [
            {
                "login": "test-org",
                "id": 456,
                "avatar_url": "https://example.com/org-avatar.png",
            }
        ]

        mock_client.get.side_effect = [mock_user_resp, mock_orgs_resp]

        owners = await service.list_owners()

        assert len(owners) == 2
        assert owners[0].login == "testuser"
        assert owners[0].type == "User"
        assert owners[1].login == "test-org"
        assert owners[1].type == "Organization"

    @pytest.mark.asyncio
    async def test_list_owners_handles_user_api_error(self, service, mock_client):
        """Test list_owners raises GitHubAPIError on user fetch failure."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"message": "Bad credentials"}

        mock_client.get.return_value = mock_resp

        with pytest.raises(GitHubAPIError) as exc_info:
            await service.list_owners()

        assert exc_info.value.status_code == 401
        assert "Bad credentials" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_owners_handles_orgs_failure_gracefully(
        self, service, mock_client
    ):
        """Test list_owners returns just user if orgs fetch fails."""
        mock_user_resp = MagicMock()
        mock_user_resp.status_code = 200
        mock_user_resp.json.return_value = {
            "login": "testuser",
            "id": 123,
            "avatar_url": None,
        }

        mock_orgs_resp = MagicMock()
        mock_orgs_resp.status_code = 403

        mock_client.get.side_effect = [mock_user_resp, mock_orgs_resp]

        owners = await service.list_owners()

        assert len(owners) == 1
        assert owners[0].login == "testuser"

    @pytest.mark.asyncio
    async def test_check_availability_returns_true_for_404(
        self, service, mock_client
    ):
        """Test check_availability returns True when repo doesn't exist."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        mock_client.get.return_value = mock_resp

        available, suggestion = await service.check_availability("owner", "new-repo")

        assert available is True
        assert suggestion is None

    @pytest.mark.asyncio
    async def test_check_availability_returns_false_with_suggestion(
        self, service, mock_client
    ):
        """Test check_availability returns suggestion when name taken."""
        # First call: repo exists (200)
        # Second call: repo-2 doesn't exist (404)
        mock_resp_200 = MagicMock()
        mock_resp_200.status_code = 200

        mock_resp_404 = MagicMock()
        mock_resp_404.status_code = 404

        mock_client.get.side_effect = [mock_resp_200, mock_resp_404]

        available, suggestion = await service.check_availability("owner", "my-repo")

        assert available is False
        assert suggestion == "my-repo-2"

    @pytest.mark.asyncio
    async def test_check_availability_no_suggestion_when_all_taken(
        self, service, mock_client
    ):
        """Test check_availability returns no suggestion when all alternatives taken."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        # All checks return 200 (repo exists)
        mock_client.get.return_value = mock_resp

        available, suggestion = await service.check_availability("owner", "my-repo")

        assert available is False
        assert suggestion is None

    @pytest.mark.asyncio
    async def test_create_repository_for_user(self, service, mock_client):
        """Test create_repository creates repo under user account."""
        # Mock user check - returns current user
        mock_user_resp = MagicMock()
        mock_user_resp.status_code = 200
        mock_user_resp.json.return_value = {"login": "testuser"}

        # Mock repo creation
        mock_create_resp = MagicMock()
        mock_create_resp.status_code = 201
        mock_create_resp.json.return_value = {
            "id": 789,
            "name": "new-repo",
            "full_name": "testuser/new-repo",
            "html_url": "https://github.com/testuser/new-repo",
            "clone_url": "https://github.com/testuser/new-repo.git",
            "default_branch": "main",
        }

        mock_client.get.return_value = mock_user_resp
        mock_client.post.return_value = mock_create_resp

        request = CreateRepositoryRequest(
            name="new-repo",
            owner="testuser",
            visibility=RepoVisibility.PRIVATE,
            template=RepoTemplate.EMPTY,
        )

        result = await service.create_repository(request, project_id="proj-123")

        assert result.id == 789
        assert result.name == "new-repo"
        assert result.full_name == "testuser/new-repo"
        assert result.project_id == "proj-123"

        # Verify called with user repos endpoint
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/user/repos"

    @pytest.mark.asyncio
    async def test_create_repository_for_org(self, service, mock_client):
        """Test create_repository creates repo under organization."""
        # Mock user check - different user
        mock_user_resp = MagicMock()
        mock_user_resp.status_code = 200
        mock_user_resp.json.return_value = {"login": "different-user"}

        # Mock orgs check - owner is in orgs
        mock_orgs_resp = MagicMock()
        mock_orgs_resp.status_code = 200
        mock_orgs_resp.json.return_value = [{"login": "my-org"}]

        # Mock repo creation
        mock_create_resp = MagicMock()
        mock_create_resp.status_code = 201
        mock_create_resp.json.return_value = {
            "id": 999,
            "name": "org-repo",
            "full_name": "my-org/org-repo",
            "html_url": "https://github.com/my-org/org-repo",
            "clone_url": "https://github.com/my-org/org-repo.git",
            "default_branch": "main",
        }

        mock_client.get.side_effect = [mock_user_resp, mock_orgs_resp]
        mock_client.post.return_value = mock_create_resp

        request = CreateRepositoryRequest(
            name="org-repo",
            owner="my-org",
            visibility=RepoVisibility.PUBLIC,
        )

        result = await service.create_repository(request, project_id="proj-456")

        assert result.id == 999
        assert result.full_name == "my-org/org-repo"

        # Verify called with org repos endpoint
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/orgs/my-org/repos"

    @pytest.mark.asyncio
    async def test_create_repository_handles_error(self, service, mock_client):
        """Test create_repository raises GitHubAPIError on failure."""
        mock_user_resp = MagicMock()
        mock_user_resp.status_code = 200
        mock_user_resp.json.return_value = {"login": "testuser"}

        mock_create_resp = MagicMock()
        mock_create_resp.status_code = 422
        mock_create_resp.json.return_value = {"message": "Repository name already exists"}

        mock_client.get.return_value = mock_user_resp
        mock_client.post.return_value = mock_create_resp

        request = CreateRepositoryRequest(
            name="existing-repo",
            owner="testuser",
        )

        with pytest.raises(GitHubAPIError) as exc_info:
            await service.create_repository(request, project_id="proj-123")

        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_get_repository_returns_data(self, service, mock_client):
        """Test get_repository returns repo data."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": 123,
            "name": "test-repo",
            "full_name": "owner/test-repo",
        }

        mock_client.get.return_value = mock_resp

        result = await service.get_repository("owner", "test-repo")

        assert result["id"] == 123
        assert result["name"] == "test-repo"

    @pytest.mark.asyncio
    async def test_get_repository_returns_none_for_404(self, service, mock_client):
        """Test get_repository returns None for non-existent repo."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        mock_client.get.return_value = mock_resp

        result = await service.get_repository("owner", "nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test service can be used as async context manager."""
        with patch("omoi_os.services.repository_service.httpx.AsyncClient") as mock:
            mock_client = AsyncMock()
            mock.return_value = mock_client

            async with RepositoryService("test-token") as service:
                assert service is not None

            mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, service, mock_client):
        """Test close method closes the client."""
        await service.close()

        mock_client.aclose.assert_called_once()


class TestRepositoryServiceInit:
    """Tests for RepositoryService initialization."""

    def test_init_sets_headers(self):
        """Test initialization sets correct headers."""
        with patch("omoi_os.services.repository_service.httpx.AsyncClient") as mock:
            RepositoryService("my-github-token")

            mock.assert_called_once()
            call_kwargs = mock.call_args[1]

            assert call_kwargs["headers"]["Authorization"] == "Bearer my-github-token"
            assert "application/vnd.github+json" in call_kwargs["headers"]["Accept"]
            assert "X-GitHub-Api-Version" in call_kwargs["headers"]

    def test_init_sets_base_url(self):
        """Test initialization sets GitHub API base URL."""
        with patch("omoi_os.services.repository_service.httpx.AsyncClient") as mock:
            RepositoryService("token")

            call_kwargs = mock.call_args[1]
            assert call_kwargs["base_url"] == "https://api.github.com"

    def test_init_sets_timeout(self):
        """Test initialization sets timeout."""
        with patch("omoi_os.services.repository_service.httpx.AsyncClient") as mock:
            RepositoryService("token")

            call_kwargs = mock.call_args[1]
            assert call_kwargs["timeout"] == 30.0
