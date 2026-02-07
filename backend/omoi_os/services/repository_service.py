"""Service for GitHub repository operations."""

import logging
from typing import Optional

import httpx

from omoi_os.schemas.github import (
    CreateRepositoryRequest,
    CreateRepositoryResponse,
    GitHubOwner,
)

logger = logging.getLogger(__name__)


class RepositoryServiceError(Exception):
    """Base exception for repository service errors."""

    pass


class GitHubAPIError(RepositoryServiceError):
    """Exception raised when GitHub API returns an error."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"GitHub API error ({status_code}): {message}")


class RepositoryService:
    """Service for GitHub repository operations."""

    GITHUB_API_BASE = "https://api.github.com"
    API_VERSION = "2022-11-28"

    def __init__(self, github_token: str):
        """
        Initialize the repository service.

        Args:
            github_token: GitHub personal access token or OAuth token
        """
        self.github_token = github_token
        self.client = httpx.AsyncClient(
            base_url=self.GITHUB_API_BASE,
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": self.API_VERSION,
            },
            timeout=30.0,
        )

    async def list_owners(self) -> list[GitHubOwner]:
        """
        List accounts/orgs user can create repos in.

        Returns:
            List of GitHubOwner objects representing users and orgs

        Raises:
            GitHubAPIError: If GitHub API returns an error
        """
        # Get authenticated user first
        user_resp = await self.client.get("/user")
        if user_resp.status_code != 200:
            raise GitHubAPIError(
                user_resp.status_code, user_resp.json().get("message", "Unknown error")
            )

        user = user_resp.json()
        owners = [
            GitHubOwner(
                login=user["login"],
                id=user["id"],
                type="User",
                avatar_url=user.get("avatar_url"),
            )
        ]

        # Get organizations user belongs to
        orgs_resp = await self.client.get("/user/orgs")
        if orgs_resp.status_code != 200:
            logger.warning(f"Failed to fetch organizations: {orgs_resp.status_code}")
            # Return just user on org fetch failure
            return owners

        for org in orgs_resp.json():
            owners.append(
                GitHubOwner(
                    login=org["login"],
                    id=org["id"],
                    type="Organization",
                    avatar_url=org.get("avatar_url"),
                )
            )

        return owners

    async def check_availability(
        self, owner: str, name: str
    ) -> tuple[bool, Optional[str]]:
        """
        Check if repo name is available.

        Args:
            owner: Repository owner (user or org login)
            name: Desired repository name

        Returns:
            Tuple of (available: bool, suggestion: Optional[str])
            If not available, suggestion contains an alternative name if found.

        Raises:
            GitHubAPIError: If GitHub API returns an unexpected error
        """
        resp = await self.client.get(f"/repos/{owner}/{name}")

        if resp.status_code == 404:
            return True, None
        elif resp.status_code == 200:
            # Name taken, suggest alternative
            for i in range(2, 10):
                alt_name = f"{name}-{i}"
                alt_resp = await self.client.get(f"/repos/{owner}/{alt_name}")
                if alt_resp.status_code == 404:
                    return False, alt_name
            return False, None
        else:
            raise GitHubAPIError(
                resp.status_code, resp.json().get("message", "Unknown error")
            )

    async def create_repository(
        self, request: CreateRepositoryRequest, project_id: str
    ) -> CreateRepositoryResponse:
        """
        Create a new GitHub repository.

        Args:
            request: Repository creation request with name, owner, visibility, etc.
            project_id: OmoiOS project ID to associate with the repository

        Returns:
            CreateRepositoryResponse with repository details

        Raises:
            GitHubAPIError: If GitHub API returns an error
        """
        # Determine if owner is an org or user
        is_org = await self._is_organization(request.owner)

        payload = {
            "name": request.name,
            "description": request.description or "",
            "private": request.visibility.value == "private",
            "auto_init": True,
        }

        url = f"/orgs/{request.owner}/repos" if is_org else "/user/repos"

        resp = await self.client.post(url, json=payload)
        if resp.status_code not in (200, 201):
            error_data = resp.json()
            raise GitHubAPIError(
                resp.status_code,
                error_data.get("message", "Failed to create repository"),
            )

        repo_data = resp.json()

        return CreateRepositoryResponse(
            id=repo_data["id"],
            name=repo_data["name"],
            full_name=repo_data["full_name"],
            html_url=repo_data["html_url"],
            clone_url=repo_data["clone_url"],
            default_branch=repo_data.get("default_branch", "main"),
            project_id=project_id,
        )

    async def _is_organization(self, owner: str) -> bool:
        """
        Check if an owner is an organization.

        Args:
            owner: Owner login name

        Returns:
            True if owner is an organization, False if user
        """
        # First check if it's the authenticated user
        user_resp = await self.client.get("/user")
        if user_resp.status_code == 200:
            user = user_resp.json()
            if user["login"].lower() == owner.lower():
                return False

        # Check orgs
        orgs_resp = await self.client.get("/user/orgs")
        if orgs_resp.status_code == 200:
            for org in orgs_resp.json():
                if org["login"].lower() == owner.lower():
                    return True

        return False

    async def get_repository(self, owner: str, name: str) -> Optional[dict]:
        """
        Get repository details.

        Args:
            owner: Repository owner
            name: Repository name

        Returns:
            Repository data dict or None if not found
        """
        resp = await self.client.get(f"/repos/{owner}/{name}")
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise GitHubAPIError(
                resp.status_code, resp.json().get("message", "Unknown error")
            )
        return resp.json()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self) -> "RepositoryService":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
