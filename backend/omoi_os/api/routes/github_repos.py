"""GitHub repository API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from omoi_os.api.dependencies import get_db_service, get_current_user
from omoi_os.models.user import User
from omoi_os.services.database import DatabaseService
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
    if not (current_user.attributes or {}).get("github_access_token"):
        raise HTTPException(
            status_code=400,
            detail="GitHub not connected. Please authenticate with GitHub first.",
        )
    return current_user


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
    repos = await github_service.list_user_repos(
        user_id=current_user.id,
        visibility=visibility,
        sort=sort,
        per_page=per_page,
        page=page,
    )
    return repos


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
        raise HTTPException(status_code=400, detail=result.error or "Failed to create branch")

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


@router.put("/repos/{owner}/{repo}/contents/{path:path}", response_model=FileOperationResult)
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
        raise HTTPException(status_code=400, detail=result.error or "Failed to create/update file")

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
        raise HTTPException(status_code=400, detail=result.error or "Failed to create pull request")

    return result
