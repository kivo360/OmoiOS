"""GitHub repository API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from omoi_os.api.dependencies import get_db_service, get_current_user
from omoi_os.models.user import User
from omoi_os.models.project import Project
from omoi_os.services.database import DatabaseService
from sqlalchemy import select
from omoi_os.services.github_api import (
    GitHubAPIService,
    GitHubRepo,
    GitHubBranch,
    GitHubFile,
    GitHubCommit,
    GitHubPullRequest,
    DirectoryItem,
    TreeItem,
    FileOperationResult,
    BranchCreateResult,
    PullRequestCreateResult,
)


router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class CreateFileRequest(BaseModel):
    """Request to create or update a file."""

    content: str
    message: str
    branch: Optional[str] = None


class CreateBranchRequest(BaseModel):
    """Request to create a branch."""

    branch_name: str
    from_sha: str


class CreatePullRequestRequest(BaseModel):
    """Request to create a pull request."""

    title: str
    head: str
    base: str
    body: Optional[str] = None
    draft: bool = False


# ============================================================================
# Dependencies
# ============================================================================


def get_github_api_service(
    db: DatabaseService = Depends(get_db_service),
) -> GitHubAPIService:
    """Get GitHub API service instance."""
    return GitHubAPIService(db)


def verify_github_connected(current_user: User = Depends(get_current_user)) -> User:
    """Verify that the user has GitHub connected."""
    attrs = current_user.attributes or {}
    access_token = attrs.get("github_access_token")
    user_id = attrs.get("github_user_id")

    # Debug logging
    import logging

    logger = logging.getLogger(__name__)
    logger.debug(f"Verifying GitHub connection for user {current_user.id}")
    logger.debug(f"Has access_token: {access_token is not None}")
    logger.debug(f"Has user_id: {user_id is not None}")
    logger.debug(f"All GitHub keys: {[k for k in attrs.keys() if 'github' in k]}")

    if not access_token:
        raise HTTPException(
            status_code=400,
            detail="GitHub not connected. Please authenticate with GitHub first.",
        )
    return current_user


# ============================================================================
# Diagnostic Routes
# ============================================================================


@router.get("/connection-status")
async def get_github_connection_status(
    current_user: User = Depends(get_current_user),
):
    """Get GitHub connection status and diagnostic information."""
    attrs = current_user.attributes or {}

    has_user_id = attrs.get("github_user_id") is not None
    has_access_token = attrs.get("github_access_token") is not None
    has_username = attrs.get("github_username") is not None

    return {
        "connected": has_user_id and has_access_token,
        "has_user_id": has_user_id,
        "has_access_token": has_access_token,
        "has_username": has_username,
        "username": attrs.get("github_username"),
        "github_keys": [k for k in attrs.keys() if "github" in k],
    }


# ============================================================================
# Connected Repositories Routes
# ============================================================================


class RepositoryInfo(BaseModel):
    """Repository information for connected repositories."""

    owner: str
    repo: str
    connected: bool = True
    webhook_configured: bool = False


@router.get("/connected", response_model=list[RepositoryInfo])
async def list_connected_repositories(
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """List repositories connected to projects for the current user."""
    with db.get_session() as session:
        # Get all projects for the current user that have GitHub repos connected
        # Use created_by to find user's projects
        # Filter by status='active' instead of deleted_at (Project model uses status field)
        projects = (
            session.execute(
                select(Project).where(
                    Project.created_by == current_user.id,
                    Project.github_owner.isnot(None),
                    Project.github_repo.isnot(None),
                    Project.status == "active",
                )
            )
            .scalars()
            .all()
        )

        # Convert to RepositoryInfo format
        repos = []
        seen = set()
        for project in projects:
            if project.github_owner and project.github_repo:
                key = f"{project.github_owner}/{project.github_repo}"
                if key not in seen:
                    repos.append(
                        RepositoryInfo(
                            owner=project.github_owner,
                            repo=project.github_repo,
                            connected=True,
                            webhook_configured=False,  # TODO: Check if webhook is configured
                        )
                    )
                    seen.add(key)

        return repos


# ============================================================================
# Repository Routes
# ============================================================================


@router.get("/repos", response_model=list[GitHubRepo])
async def list_repos(
    visibility: str = Query("all", pattern="^(all|public|private)$"),
    sort: str = Query("updated", pattern="^(created|updated|pushed|full_name)$"),
    per_page: int = Query(30, ge=1, le=100),
    page: int = Query(1, ge=1),
    current_user: User = Depends(verify_github_connected),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """List repositories for the authenticated user."""
    import logging

    logger = logging.getLogger(__name__)

    try:
        repos = await github_service.list_user_repos(
            user_id=current_user.id,
            visibility=visibility,
            sort=sort,
            per_page=per_page,
            page=page,
        )
        logger.info(f"Retrieved {len(repos)} repositories for user {current_user.id}")
        return repos
    except ValueError as e:
        # Handle authentication errors from GitHub API
        logger.error(f"GitHub API error for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.get("/repos/{owner}/{repo}", response_model=GitHubRepo)
async def get_repo(
    owner: str,
    repo: str,
    current_user: User = Depends(verify_github_connected),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """Get repository details."""
    result = await github_service.get_repo(
        user_id=current_user.id,
        owner=owner,
        repo=repo,
    )

    if not result:
        raise HTTPException(status_code=404, detail="Repository not found")

    return result


# ============================================================================
# Branch Routes
# ============================================================================


@router.get("/repos/{owner}/{repo}/branches", response_model=list[GitHubBranch])
async def list_branches(
    owner: str,
    repo: str,
    per_page: int = Query(30, ge=1, le=100),
    page: int = Query(1, ge=1),
    current_user: User = Depends(verify_github_connected),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """List repository branches."""
    branches = await github_service.list_branches(
        user_id=current_user.id,
        owner=owner,
        repo=repo,
        per_page=per_page,
        page=page,
    )
    return branches


@router.post("/repos/{owner}/{repo}/branches", response_model=BranchCreateResult)
async def create_branch(
    owner: str,
    repo: str,
    request: CreateBranchRequest,
    current_user: User = Depends(verify_github_connected),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """Create a new branch."""
    result = await github_service.create_branch(
        user_id=current_user.id,
        owner=owner,
        repo=repo,
        branch_name=request.branch_name,
        from_sha=request.from_sha,
    )

    if not result.success:
        raise HTTPException(
            status_code=400, detail=result.error or "Failed to create branch"
        )

    return result


# ============================================================================
# File Routes
# ============================================================================


@router.get("/repos/{owner}/{repo}/contents/{path:path}", response_model=GitHubFile)
async def get_file_content(
    owner: str,
    repo: str,
    path: str,
    ref: Optional[str] = Query(None),
    current_user: User = Depends(verify_github_connected),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """Get file content from repository."""
    result = await github_service.get_file_content(
        user_id=current_user.id,
        owner=owner,
        repo=repo,
        path=path,
        ref=ref,
    )

    if not result:
        raise HTTPException(status_code=404, detail="File not found")

    return result


@router.put(
    "/repos/{owner}/{repo}/contents/{path:path}", response_model=FileOperationResult
)
async def create_or_update_file(
    owner: str,
    repo: str,
    path: str,
    request: CreateFileRequest,
    current_user: User = Depends(verify_github_connected),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """Create or update a file in the repository."""
    # Check if file exists to get SHA for update
    existing = await github_service.get_file_content(
        user_id=current_user.id,
        owner=owner,
        repo=repo,
        path=path,
        ref=request.branch,
    )

    sha = existing.sha if existing else None

    result = await github_service.create_or_update_file(
        user_id=current_user.id,
        owner=owner,
        repo=repo,
        path=path,
        content=request.content,
        message=request.message,
        branch=request.branch,
        sha=sha,
    )

    if not result.success:
        raise HTTPException(
            status_code=400, detail=result.error or "Failed to create/update file"
        )

    return result


@router.get("/repos/{owner}/{repo}/directory", response_model=list[DirectoryItem])
async def list_directory(
    owner: str,
    repo: str,
    path: str = Query(""),
    ref: Optional[str] = Query(None),
    current_user: User = Depends(verify_github_connected),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """List directory contents."""
    items = await github_service.list_directory(
        user_id=current_user.id,
        owner=owner,
        repo=repo,
        path=path,
        ref=ref,
    )
    return items


@router.get("/repos/{owner}/{repo}/tree", response_model=list[TreeItem])
async def get_tree(
    owner: str,
    repo: str,
    tree_sha: str = Query("HEAD"),
    recursive: bool = Query(True),
    current_user: User = Depends(verify_github_connected),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """Get repository file tree."""
    items = await github_service.get_tree(
        user_id=current_user.id,
        owner=owner,
        repo=repo,
        tree_sha=tree_sha,
        recursive=recursive,
    )
    return items


# ============================================================================
# Commit Routes
# ============================================================================


@router.get("/repos/{owner}/{repo}/commits", response_model=list[GitHubCommit])
async def list_commits(
    owner: str,
    repo: str,
    sha: Optional[str] = Query(None),
    path: Optional[str] = Query(None),
    per_page: int = Query(30, ge=1, le=100),
    page: int = Query(1, ge=1),
    current_user: User = Depends(verify_github_connected),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """List repository commits."""
    commits = await github_service.list_commits(
        user_id=current_user.id,
        owner=owner,
        repo=repo,
        sha=sha,
        path=path,
        per_page=per_page,
        page=page,
    )
    return commits


# ============================================================================
# Pull Request Routes
# ============================================================================


@router.get("/repos/{owner}/{repo}/pulls", response_model=list[GitHubPullRequest])
async def list_pull_requests(
    owner: str,
    repo: str,
    state: str = Query("open", pattern="^(open|closed|all)$"),
    per_page: int = Query(30, ge=1, le=100),
    page: int = Query(1, ge=1),
    current_user: User = Depends(verify_github_connected),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """List repository pull requests."""
    prs = await github_service.list_pull_requests(
        user_id=current_user.id,
        owner=owner,
        repo=repo,
        state=state,
        per_page=per_page,
        page=page,
    )
    return prs


@router.post("/repos/{owner}/{repo}/pulls", response_model=PullRequestCreateResult)
async def create_pull_request(
    owner: str,
    repo: str,
    request: CreatePullRequestRequest,
    current_user: User = Depends(verify_github_connected),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """Create a pull request."""
    result = await github_service.create_pull_request(
        user_id=current_user.id,
        owner=owner,
        repo=repo,
        title=request.title,
        head=request.head,
        base=request.base,
        body=request.body,
        draft=request.draft,
    )

    if not result.success:
        raise HTTPException(
            status_code=400, detail=result.error or "Failed to create pull request"
        )

    return result
