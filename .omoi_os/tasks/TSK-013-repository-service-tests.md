---
id: TSK-013
title: Write unit tests for RepositoryService
created: 2026-01-09
status: pending
priority: HIGH
type: test
parent_ticket: TKT-007
estimate: M
dependencies:
  depends_on:
    - TSK-009
  blocks: []
---

# TSK-013: Write unit tests for RepositoryService

## Objective

Create comprehensive unit tests for the RepositoryService class, mocking GitHub API responses.

## Context

Tests should cover all methods, error cases, and edge cases without making real GitHub API calls.

## Deliverables

- [ ] `backend/tests/unit/services/test_repository_service.py`

## Implementation Notes

```python
# backend/tests/unit/services/test_repository_service.py

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from omoi_os.services.repository_service import RepositoryService
from omoi_os.models.github import CreateRepositoryRequest, RepoVisibility

@pytest.fixture
def mock_github_responses():
    """Mock GitHub API responses."""
    return {
        "user": {
            "login": "testuser",
            "id": 123,
            "avatar_url": "https://avatars.github.com/u/123"
        },
        "orgs": [
            {"login": "test-org", "id": 456, "avatar_url": "https://..."}
        ],
        "repo": {
            "id": 789,
            "name": "test-repo",
            "full_name": "testuser/test-repo",
            "html_url": "https://github.com/testuser/test-repo",
            "clone_url": "https://github.com/testuser/test-repo.git",
            "default_branch": "main"
        }
    }

class TestRepositoryService:
    """Tests for RepositoryService."""

    @pytest.mark.asyncio
    async def test_list_owners_returns_user_and_orgs(self, mock_github_responses):
        """Test that list_owners returns personal account and organizations."""
        with patch("httpx.AsyncClient") as mock_client:
            # Setup mock responses
            instance = mock_client.return_value
            instance.get = AsyncMock(side_effect=[
                MagicMock(json=lambda: mock_github_responses["user"], raise_for_status=lambda: None),
                MagicMock(json=lambda: mock_github_responses["orgs"], raise_for_status=lambda: None),
            ])

            service = RepositoryService("fake-token")
            owners = await service.list_owners()

            assert len(owners) == 2
            assert owners[0].login == "testuser"
            assert owners[0].type == "User"
            assert owners[1].login == "test-org"
            assert owners[1].type == "Organization"

    @pytest.mark.asyncio
    async def test_check_availability_returns_true_for_404(self):
        """Test that 404 response means repo is available."""
        with patch("httpx.AsyncClient") as mock_client:
            instance = mock_client.return_value
            instance.get = AsyncMock(return_value=MagicMock(status_code=404))

            service = RepositoryService("fake-token")
            available, suggestion = await service.check_availability("owner", "repo")

            assert available is True
            assert suggestion is None

    @pytest.mark.asyncio
    async def test_check_availability_returns_false_with_suggestion(self):
        """Test that 200 response means repo exists, suggests alternative."""
        with patch("httpx.AsyncClient") as mock_client:
            instance = mock_client.return_value
            # First call returns 200 (exists), second returns 404 (available)
            instance.get = AsyncMock(side_effect=[
                MagicMock(status_code=200),
                MagicMock(status_code=404),
            ])

            service = RepositoryService("fake-token")
            available, suggestion = await service.check_availability("owner", "repo")

            assert available is False
            assert suggestion == "repo-2"

    @pytest.mark.asyncio
    async def test_create_repository_personal_account(self, mock_github_responses):
        """Test creating repo in personal account."""
        with patch("httpx.AsyncClient") as mock_client:
            instance = mock_client.return_value
            instance.post = AsyncMock(return_value=MagicMock(
                json=lambda: mock_github_responses["repo"],
                raise_for_status=lambda: None
            ))

            service = RepositoryService("fake-token")
            request = CreateRepositoryRequest(
                name="test-repo",
                owner="testuser",
                visibility=RepoVisibility.PRIVATE,
            )
            result = await service.create_repository(request, is_org=False)

            assert result["name"] == "test-repo"
            instance.post.assert_called_once()
            # Verify called /user/repos, not /orgs/.../repos
            call_args = instance.post.call_args
            assert "/user/repos" in str(call_args)

    @pytest.mark.asyncio
    async def test_create_repository_organization(self, mock_github_responses):
        """Test creating repo in organization."""
        with patch("httpx.AsyncClient") as mock_client:
            instance = mock_client.return_value
            instance.post = AsyncMock(return_value=MagicMock(
                json=lambda: mock_github_responses["repo"],
                raise_for_status=lambda: None
            ))

            service = RepositoryService("fake-token")
            request = CreateRepositoryRequest(
                name="test-repo",
                owner="test-org",
                visibility=RepoVisibility.PRIVATE,
            )
            result = await service.create_repository(request, is_org=True)

            assert result["name"] == "test-repo"
            call_args = instance.post.call_args
            assert "/orgs/test-org/repos" in str(call_args)
```

## Verification

```bash
uv run pytest tests/unit/services/test_repository_service.py -v
```

## Done When

- [ ] Tests for list_owners (user + orgs)
- [ ] Tests for check_availability (available, not available, suggestions)
- [ ] Tests for create_repository (personal + org)
- [ ] Tests for error handling
- [ ] All tests pass
- [ ] Good coverage of edge cases
