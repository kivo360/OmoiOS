"""GitHub API service for repository operations."""

from typing import Any, Optional
from uuid import UUID
import base64

import httpx
from pydantic import BaseModel

from omoi_os.models.user import User
from omoi_os.services.database import DatabaseService


# ============================================================================
# Pydantic Models
# ============================================================================


class GitHubRepo(BaseModel):
    """GitHub repository info."""

    id: int
    name: str
    full_name: str
    owner: str
    description: Optional[str] = None
    private: bool
    html_url: str
    clone_url: str
    default_branch: str = "main"
    language: Optional[str] = None
    stargazers_count: int = 0
    forks_count: int = 0

    model_config = {"extra": "ignore"}


class GitHubBranch(BaseModel):
    """GitHub branch info."""

    name: str
    sha: str
    protected: bool = False

    model_config = {"extra": "ignore"}


class GitHubFile(BaseModel):
    """GitHub file info."""

    name: str
    path: str
    sha: str
    size: int = 0
    type: str  # "file" or "dir"
    content: Optional[str] = None  # Base64 decoded content
    encoding: Optional[str] = None

    model_config = {"extra": "ignore"}


class GitHubCommit(BaseModel):
    """GitHub commit info."""

    sha: str
    message: str
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    date: Optional[str] = None
    html_url: Optional[str] = None

    model_config = {"extra": "ignore"}


class GitHubPullRequest(BaseModel):
    """GitHub pull request info."""

    number: int
    title: str
    state: str
    html_url: str
    head_branch: str
    base_branch: str
    body: Optional[str] = None
    merged: bool = False
    mergeable: Optional[bool] = None
    draft: bool = False

    model_config = {"extra": "ignore"}


class DirectoryItem(BaseModel):
    """Item in a directory listing."""

    name: str
    path: str
    type: str  # "file" or "dir"
    size: int = 0
    sha: str

    model_config = {"extra": "ignore"}


class TreeItem(BaseModel):
    """Item in a repository tree."""

    path: str
    type: str  # "blob" or "tree"
    sha: str
    size: Optional[int] = None

    model_config = {"extra": "ignore"}


class FileOperationResult(BaseModel):
    """Result of a file create/update operation."""

    success: bool
    message: str
    commit_sha: Optional[str] = None
    content_sha: Optional[str] = None
    error: Optional[str] = None

    model_config = {"extra": "ignore"}


class BranchCreateResult(BaseModel):
    """Result of a branch creation."""

    success: bool
    ref: Optional[str] = None
    sha: Optional[str] = None
    error: Optional[str] = None

    model_config = {"extra": "ignore"}


class PullRequestCreateResult(BaseModel):
    """Result of a pull request creation."""

    success: bool
    number: Optional[int] = None
    html_url: Optional[str] = None
    state: Optional[str] = None
    error: Optional[str] = None

    model_config = {"extra": "ignore"}


# ============================================================================
# GitHub API Service
# ============================================================================


class GitHubAPIService:
    """Service for GitHub API operations using user OAuth tokens."""

    BASE_URL = "https://api.github.com"

    def __init__(self, db: DatabaseService):
        self.db = db

    def _get_user_token(self, user: User) -> Optional[str]:
        """Get GitHub access token from user attributes."""
        attrs = user.attributes or {}
        return attrs.get("github_access_token")

    def _get_user_token_by_id(self, user_id: UUID) -> Optional[str]:
        """Get GitHub access token by user ID."""
        with self.db.get_session() as session:
            user = session.get(User, user_id)
            if user:
                return self._get_user_token(user)
        return None

    def _headers(self, token: str) -> dict[str, str]:
        """Get request headers with auth token."""
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def list_user_repos(
        self,
        user_id: UUID,
        visibility: str = "all",
        sort: str = "updated",
        per_page: int = 30,
        page: int = 1,
    ) -> list[GitHubRepo]:
        """
        List repositories for the authenticated user.

        Args:
            user_id: User ID
            visibility: all, public, or private
            sort: created, updated, pushed, full_name
            per_page: Results per page (max 100)
            page: Page number
        """
        token = self._get_user_token_by_id(user_id)
        if not token:
            return []

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/user/repos",
                headers=self._headers(token),
                params={
                    "visibility": visibility,
                    "sort": sort,
                    "per_page": per_page,
                    "page": page,
                },
            )

            if response.status_code != 200:
                return []

            repos = response.json()
            return [
                GitHubRepo(
                    id=r["id"],
                    name=r["name"],
                    full_name=r["full_name"],
                    owner=r["owner"]["login"],
                    description=r.get("description"),
                    private=r["private"],
                    html_url=r["html_url"],
                    clone_url=r["clone_url"],
                    default_branch=r.get("default_branch", "main"),
                    language=r.get("language"),
                    stargazers_count=r.get("stargazers_count", 0),
                    forks_count=r.get("forks_count", 0),
                )
                for r in repos
            ]

    async def get_repo(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
    ) -> Optional[GitHubRepo]:
        """Get repository details."""
        token = self._get_user_token_by_id(user_id)
        if not token:
            return None

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}",
                headers=self._headers(token),
            )

            if response.status_code != 200:
                return None

            r = response.json()
            return GitHubRepo(
                id=r["id"],
                name=r["name"],
                full_name=r["full_name"],
                owner=r["owner"]["login"],
                description=r.get("description"),
                private=r["private"],
                html_url=r["html_url"],
                clone_url=r["clone_url"],
                default_branch=r.get("default_branch", "main"),
                language=r.get("language"),
                stargazers_count=r.get("stargazers_count", 0),
                forks_count=r.get("forks_count", 0),
            )

    async def list_branches(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        per_page: int = 30,
        page: int = 1,
    ) -> list[GitHubBranch]:
        """List repository branches."""
        token = self._get_user_token_by_id(user_id)
        if not token:
            return []

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/branches",
                headers=self._headers(token),
                params={"per_page": per_page, "page": page},
            )

            if response.status_code != 200:
                return []

            branches = response.json()
            return [
                GitHubBranch(
                    name=b["name"],
                    sha=b["commit"]["sha"],
                    protected=b.get("protected", False),
                )
                for b in branches
            ]

    async def get_file_content(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        path: str,
        ref: Optional[str] = None,
    ) -> Optional[GitHubFile]:
        """Get file content from repository."""
        token = self._get_user_token_by_id(user_id)
        if not token:
            return None

        params: dict[str, str] = {}
        if ref:
            params["ref"] = ref

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/contents/{path}",
                headers=self._headers(token),
                params=params,
            )

            if response.status_code != 200:
                return None

            data = response.json()

            # Handle file content
            content = None
            if data.get("content") and data.get("encoding") == "base64":
                try:
                    content = base64.b64decode(data["content"]).decode("utf-8")
                except Exception:
                    content = None

            return GitHubFile(
                name=data["name"],
                path=data["path"],
                sha=data["sha"],
                size=data.get("size", 0),
                type=data["type"],
                content=content,
                encoding=data.get("encoding"),
            )

    async def list_directory(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        path: str = "",
        ref: Optional[str] = None,
    ) -> list[DirectoryItem]:
        """List directory contents."""
        token = self._get_user_token_by_id(user_id)
        if not token:
            return []

        params: dict[str, str] = {}
        if ref:
            params["ref"] = ref

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/contents/{path}",
                headers=self._headers(token),
                params=params,
            )

            if response.status_code != 200:
                return []

            data = response.json()

            # If single file, wrap in list
            if isinstance(data, dict):
                data = [data]

            return [
                DirectoryItem(
                    name=item["name"],
                    path=item["path"],
                    type=item["type"],
                    size=item.get("size", 0),
                    sha=item["sha"],
                )
                for item in data
            ]

    async def get_tree(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        tree_sha: str = "HEAD",
        recursive: bool = True,
    ) -> list[TreeItem]:
        """Get repository file tree."""
        token = self._get_user_token_by_id(user_id)
        if not token:
            return []

        async with httpx.AsyncClient() as client:
            params: dict[str, str] = {}
            if recursive:
                params["recursive"] = "1"

            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/git/trees/{tree_sha}",
                headers=self._headers(token),
                params=params,
            )

            if response.status_code != 200:
                return []

            data = response.json()
            return [
                TreeItem(
                    path=item["path"],
                    type=item["type"],
                    sha=item["sha"],
                    size=item.get("size"),
                )
                for item in data.get("tree", [])
            ]

    async def create_or_update_file(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: Optional[str] = None,
        sha: Optional[str] = None,
    ) -> FileOperationResult:
        """Create or update a file in the repository."""
        token = self._get_user_token_by_id(user_id)
        if not token:
            return FileOperationResult(success=False, message="No GitHub token", error="No GitHub token")

        # Encode content to base64
        encoded_content = base64.b64encode(content.encode()).decode()

        data: dict[str, Any] = {
            "message": message,
            "content": encoded_content,
        }

        if branch:
            data["branch"] = branch
        if sha:
            data["sha"] = sha  # Required for updates

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.BASE_URL}/repos/{owner}/{repo}/contents/{path}",
                headers=self._headers(token),
                json=data,
            )

            result = response.json()

            if response.status_code in (200, 201):
                return FileOperationResult(
                    success=True,
                    message="File created/updated successfully",
                    commit_sha=result.get("commit", {}).get("sha"),
                    content_sha=result.get("content", {}).get("sha"),
                )
            else:
                return FileOperationResult(
                    success=False,
                    message=result.get("message", "Operation failed"),
                    error=result.get("message"),
                )

    async def create_branch(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        branch_name: str,
        from_sha: str,
    ) -> BranchCreateResult:
        """Create a new branch."""
        token = self._get_user_token_by_id(user_id)
        if not token:
            return BranchCreateResult(success=False, error="No GitHub token")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/repos/{owner}/{repo}/git/refs",
                headers=self._headers(token),
                json={
                    "ref": f"refs/heads/{branch_name}",
                    "sha": from_sha,
                },
            )

            result = response.json()

            if response.status_code == 201:
                return BranchCreateResult(
                    success=True,
                    ref=result.get("ref"),
                    sha=result.get("object", {}).get("sha"),
                )
            else:
                return BranchCreateResult(
                    success=False,
                    error=result.get("message", "Failed to create branch"),
                )

    async def create_pull_request(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: Optional[str] = None,
        draft: bool = False,
    ) -> PullRequestCreateResult:
        """Create a pull request."""
        token = self._get_user_token_by_id(user_id)
        if not token:
            return PullRequestCreateResult(success=False, error="No GitHub token")

        data: dict[str, Any] = {
            "title": title,
            "head": head,
            "base": base,
            "draft": draft,
        }

        if body:
            data["body"] = body

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/repos/{owner}/{repo}/pulls",
                headers=self._headers(token),
                json=data,
            )

            result = response.json()

            if response.status_code == 201:
                return PullRequestCreateResult(
                    success=True,
                    number=result.get("number"),
                    html_url=result.get("html_url"),
                    state=result.get("state"),
                )
            else:
                return PullRequestCreateResult(
                    success=False,
                    error=result.get("message", "Failed to create pull request"),
                )

    async def list_commits(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        sha: Optional[str] = None,
        path: Optional[str] = None,
        per_page: int = 30,
        page: int = 1,
    ) -> list[GitHubCommit]:
        """List repository commits."""
        token = self._get_user_token_by_id(user_id)
        if not token:
            return []

        params: dict[str, Any] = {
            "per_page": per_page,
            "page": page,
        }
        if sha:
            params["sha"] = sha
        if path:
            params["path"] = path

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/commits",
                headers=self._headers(token),
                params=params,
            )

            if response.status_code != 200:
                return []

            commits = response.json()
            return [
                GitHubCommit(
                    sha=c["sha"],
                    message=c["commit"]["message"],
                    author_name=c["commit"]["author"]["name"] if c["commit"].get("author") else None,
                    author_email=c["commit"]["author"]["email"] if c["commit"].get("author") else None,
                    date=c["commit"]["author"]["date"] if c["commit"].get("author") else None,
                    html_url=c.get("html_url"),
                )
                for c in commits
            ]

    async def list_pull_requests(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 30,
        page: int = 1,
    ) -> list[GitHubPullRequest]:
        """List repository pull requests."""
        token = self._get_user_token_by_id(user_id)
        if not token:
            return []

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/pulls",
                headers=self._headers(token),
                params={
                    "state": state,
                    "per_page": per_page,
                    "page": page,
                },
            )

            if response.status_code != 200:
                return []

            prs = response.json()
            return [
                GitHubPullRequest(
                    number=pr["number"],
                    title=pr["title"],
                    state=pr["state"],
                    html_url=pr["html_url"],
                    head_branch=pr["head"]["ref"],
                    base_branch=pr["base"]["ref"],
                    body=pr.get("body"),
                    merged=pr.get("merged", False),
                    mergeable=pr.get("mergeable"),
                    draft=pr.get("draft", False),
                )
                for pr in prs
            ]
