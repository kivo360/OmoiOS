"""GitHub tools for agent operations.

These tools allow agents to interact with GitHub repositories
on behalf of users who have connected their GitHub accounts.
"""

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel

from omoi_os.services.database import DatabaseService
from omoi_os.services.github_api import GitHubAPIService


# ============================================================================
# Pydantic Models for Tool Results
# ============================================================================


class RepoInfo(BaseModel):
    """Simplified repository info for agents."""

    name: str
    full_name: str
    description: Optional[str] = None
    private: bool
    html_url: str
    default_branch: str
    language: Optional[str] = None


class FileInfo(BaseModel):
    """File info for agents."""

    name: str
    path: str
    type: str
    size: int = 0


class TreeFileInfo(BaseModel):
    """Tree file info for agents."""

    path: str
    type: str  # "file" or "dir"
    size: Optional[int] = None


class WriteFileResult(BaseModel):
    """Result of writing a file."""

    success: bool
    message: str
    commit_sha: Optional[str] = None
    error: Optional[str] = None


class CreatePRResult(BaseModel):
    """Result of creating a pull request."""

    success: bool
    number: Optional[int] = None
    html_url: Optional[str] = None
    state: Optional[str] = None
    title: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# GitHub Tools Class
# ============================================================================


class GitHubTools:
    """
    Agent-friendly GitHub tools.

    These tools wrap the GitHubAPIService to provide simplified
    methods for common GitHub operations.

    Initialize with a user_id to bind all operations to that user's
    GitHub token.
    """

    def __init__(self, db: DatabaseService, user_id: UUID):
        """
        Initialize GitHub tools for a specific user.

        Args:
            db: Database service instance
            user_id: UUID of the user whose GitHub token to use
        """
        self.db = db
        self.user_id = user_id
        self._api = GitHubAPIService(db)

    async def list_repos(
        self,
        visibility: str = "all",
        limit: int = 30,
    ) -> list[RepoInfo]:
        """
        List repositories for the connected GitHub account.

        Args:
            visibility: Filter by visibility (all, public, private)
            limit: Maximum number of repos to return

        Returns:
            List of repository dictionaries with name, full_name,
            description, private, html_url, default_branch
        """
        repos = await self._api.list_user_repos(
            user_id=self.user_id,
            visibility=visibility,
            per_page=limit,
        )

        return [
            RepoInfo(
                name=r.name,
                full_name=r.full_name,
                description=r.description,
                private=r.private,
                html_url=r.html_url,
                default_branch=r.default_branch,
                language=r.language,
            )
            for r in repos
        ]

    async def read_file(
        self,
        owner: str,
        repo: str,
        path: str,
        branch: Optional[str] = None,
    ) -> Optional[str]:
        """
        Read file content from a repository.

        Args:
            owner: Repository owner (username or org)
            repo: Repository name
            path: File path within the repository
            branch: Branch name (optional, defaults to default branch)

        Returns:
            File content as string, or None if not found
        """
        result = await self._api.get_file_content(
            user_id=self.user_id,
            owner=owner,
            repo=repo,
            path=path,
            ref=branch,
        )

        return result.content if result else None

    async def list_files(
        self,
        owner: str,
        repo: str,
        path: str = "",
        branch: Optional[str] = None,
    ) -> list[FileInfo]:
        """
        List files in a repository directory.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Directory path (empty for root)
            branch: Branch name (optional)

        Returns:
            List of file/directory dictionaries with name, path, type
        """
        items = await self._api.list_directory(
            user_id=self.user_id,
            owner=owner,
            repo=repo,
            path=path,
            ref=branch,
        )

        return [
            FileInfo(
                name=item.name,
                path=item.path,
                type=item.type,
                size=item.size,
            )
            for item in items
        ]

    async def get_repo_tree(
        self,
        owner: str,
        repo: str,
        branch: Optional[str] = None,
    ) -> list[TreeFileInfo]:
        """
        Get full file tree for a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name (optional, defaults to HEAD)

        Returns:
            List of all files with path and type
        """
        tree_sha = branch or "HEAD"
        items = await self._api.get_tree(
            user_id=self.user_id,
            owner=owner,
            repo=repo,
            tree_sha=tree_sha,
            recursive=True,
        )

        return [
            TreeFileInfo(
                path=item.path,
                type="file" if item.type == "blob" else "dir",
                size=item.size,
            )
            for item in items
        ]

    async def write_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: Optional[str] = None,
    ) -> WriteFileResult:
        """
        Create or update a file in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            content: File content
            message: Commit message
            branch: Branch name (optional)

        Returns:
            Result dictionary with commit info
        """
        # Check if file exists to get SHA for update
        existing = await self._api.get_file_content(
            user_id=self.user_id,
            owner=owner,
            repo=repo,
            path=path,
            ref=branch,
        )

        sha = existing.sha if existing else None

        result = await self._api.create_or_update_file(
            user_id=self.user_id,
            owner=owner,
            repo=repo,
            path=path,
            content=content,
            message=message,
            branch=branch,
            sha=sha,
        )

        return WriteFileResult(
            success=result.success,
            message=result.message,
            commit_sha=result.commit_sha,
            error=result.error,
        )

    async def create_branch(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        from_branch: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create a new branch in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            branch_name: Name for the new branch
            from_branch: Branch to create from (defaults to default branch)

        Returns:
            Result dictionary with branch info
        """
        # Get the SHA of the source branch
        branches = await self._api.list_branches(
            user_id=self.user_id,
            owner=owner,
            repo=repo,
        )

        # Find the source branch
        source_sha = None
        if from_branch:
            for b in branches:
                if b.name == from_branch:
                    source_sha = b.sha
                    break
        else:
            # Get repo to find default branch
            repo_info = await self._api.get_repo(
                user_id=self.user_id,
                owner=owner,
                repo=repo,
            )
            if repo_info:
                default_branch = repo_info.default_branch
                for b in branches:
                    if b.name == default_branch:
                        source_sha = b.sha
                        break

        if not source_sha:
            return {
                "success": False,
                "error": "Source branch not found",
            }

        result = await self._api.create_branch(
            user_id=self.user_id,
            owner=owner,
            repo=repo,
            branch_name=branch_name,
            from_sha=source_sha,
        )

        return {
            "success": result.success,
            "ref": result.ref,
            "sha": result.sha,
            "error": result.error,
        }

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head_branch: str,
        base_branch: str,
        body: Optional[str] = None,
    ) -> CreatePRResult:
        """
        Create a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            head_branch: Source branch with changes
            base_branch: Target branch to merge into
            body: PR description (optional)

        Returns:
            PR info dictionary with number, html_url, state
        """
        result = await self._api.create_pull_request(
            user_id=self.user_id,
            owner=owner,
            repo=repo,
            title=title,
            head=head_branch,
            base=base_branch,
            body=body,
        )

        return CreatePRResult(
            success=result.success,
            number=result.number,
            html_url=result.html_url,
            state=result.state,
            title=title if result.success else None,
            error=result.error,
        )

    async def get_repo_info(
        self,
        owner: str,
        repo: str,
    ) -> Optional[RepoInfo]:
        """
        Get repository information.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Repository info or None if not found
        """
        result = await self._api.get_repo(
            user_id=self.user_id,
            owner=owner,
            repo=repo,
        )

        if not result:
            return None

        return RepoInfo(
            name=result.name,
            full_name=result.full_name,
            description=result.description,
            private=result.private,
            html_url=result.html_url,
            default_branch=result.default_branch,
            language=result.language,
        )

    async def list_branches(
        self,
        owner: str,
        repo: str,
    ) -> list[dict[str, Any]]:
        """
        List branches in a repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of branch dictionaries with name, sha, protected
        """
        branches = await self._api.list_branches(
            user_id=self.user_id,
            owner=owner,
            repo=repo,
        )

        return [
            {
                "name": b.name,
                "sha": b.sha,
                "protected": b.protected,
            }
            for b in branches
        ]


# ============================================================================
# Factory Function
# ============================================================================


def create_github_tools(db: DatabaseService, user_id: UUID) -> GitHubTools:
    """
    Create a GitHubTools instance for a user.

    This is a convenience factory function for creating GitHubTools.

    Args:
        db: Database service instance
        user_id: UUID of the user whose GitHub token to use

    Returns:
        GitHubTools instance
    """
    return GitHubTools(db=db, user_id=user_id)
