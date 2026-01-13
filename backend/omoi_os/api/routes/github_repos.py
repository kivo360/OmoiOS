"""GitHub repository API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from omoi_os.api.dependencies import get_db_service, get_approved_user
from omoi_os.logging import get_logger
from omoi_os.models.user import User
from omoi_os.models.project import Project
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

logger = get_logger(__name__)
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


def verify_github_connected(current_user: User = Depends(get_approved_user)) -> User:
    """Verify that the user has GitHub connected."""
    attrs = current_user.attributes or {}
    access_token = attrs.get("github_access_token")
    user_id = attrs.get("github_user_id")

    # Debug logging
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
    current_user: User = Depends(get_approved_user),
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


@router.get("/repos-test")
async def test_list_repos(
    current_user: User = Depends(verify_github_connected),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """
    Simple test endpoint to debug repository listing.
    Returns step-by-step information about what's happening.
    """
    attrs = current_user.attributes or {}
    token_from_attrs = attrs.get("github_access_token")

    result = {
        "user_id": str(current_user.id),
        "has_token_in_attrs": token_from_attrs is not None,
        "token_length": len(token_from_attrs) if token_from_attrs else 0,
        "github_keys": [k for k in attrs.keys() if "github" in k],
    }

    # Try to get token via service method (using internal method for debugging)
    # Note: This is for debugging only
    try:
        token_from_service = github_service._get_user_token_by_id(current_user.id)
        result["has_token_from_service"] = token_from_service is not None
        result["token_from_service_length"] = (
            len(token_from_service) if token_from_service else 0
        )
    except Exception as e:
        result["token_service_error"] = str(e)

    # Try to call the service method
    try:
        repos = await github_service.list_user_repos(
            user_id=current_user.id,
            visibility="all",
            sort="updated",
            per_page=100,
            page=1,
            fetch_all_pages=True,
        )
        result["repos_count"] = len(repos)
        result["first_3_repos"] = [r.full_name for r in repos[:3]] if repos else []
        result["success"] = True
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
        result["error_type"] = type(e).__name__
        logger.exception(f"Error in test_list_repos: {e}")

    return result


@router.get("/repos-diagnostic")
async def diagnostic_list_repos(
    current_user: User = Depends(verify_github_connected),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """
    Diagnostic endpoint to see exactly what GitHub API returns.

    This shows:
    - Raw API response details
    - Total repositories found
    - Pagination information
    - Token scopes (if available)
    - Sample repository data
    """
    import httpx

    attrs = current_user.attributes or {}
    token = attrs.get("github_access_token")

    if not token:
        return {
            "error": "No GitHub access token found",
            "user_id": str(current_user.id),
        }

    # Make direct API call to get full response details
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user/repos",
            headers={
                "Authorization": f"Bearer {token}",  # Match the format used by GitHubAPIService
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            params={
                "visibility": "all",
                "sort": "updated",
                "per_page": 100,
                "page": 1,
            },
        )

        # Get pagination info from headers
        link_header = response.headers.get("Link", "")
        total_count = None
        if 'rel="last"' in link_header:
            # Extract last page number from Link header
            import re

            last_match = re.search(r'page=(\d+)>; rel="last"', link_header)
            if last_match:
                total_count = int(last_match.group(1)) * 100  # Approximate

        # Get rate limit info
        rate_limit_remaining = response.headers.get("X-RateLimit-Remaining")
        rate_limit_total = response.headers.get("X-RateLimit-Limit")

        repos_data = response.json() if response.status_code == 200 else None

        diagnostic_info = {
            "api_status_code": response.status_code,
            "api_response_headers": {
                "link": link_header,
                "x-ratelimit-remaining": rate_limit_remaining,
                "x-ratelimit-limit": rate_limit_total,
                "x-oauth-scopes": response.headers.get(
                    "X-OAuth-Scopes", "Not available"
                ),
            },
            "repositories_returned": len(repos_data) if repos_data else 0,
            "estimated_total": total_count,
            "has_more_pages": 'rel="next"' in link_header,
            "sample_repositories": repos_data[:5]
            if repos_data
            else None,  # First 5 repos
            "all_repo_names": [r["full_name"] for r in repos_data]
            if repos_data
            else [],
            "token_valid": response.status_code == 200,
            "error_message": response.text[:500]
            if response.status_code != 200
            else None,
        }

        logger.info(
            f"GitHub diagnostic for user {current_user.id}: "
            f"status={response.status_code}, repos={len(repos_data) if repos_data else 0}, "
            f"scopes={response.headers.get('X-OAuth-Scopes', 'unknown')}"
        )

        return diagnostic_info


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
    current_user: User = Depends(get_approved_user),
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
    per_page: int = Query(100, ge=1, le=100),  # Default to 100 for efficiency
    page: int = Query(
        1, ge=1
    ),  # Kept for API compatibility, but ignored when fetch_all_pages=True
    current_user: User = Depends(verify_github_connected),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """List repositories for the authenticated user."""
    # Debug: Log user and connection status
    attrs = current_user.attributes or {}
    has_token = attrs.get("github_access_token") is not None
    logger.info(
        "list_repos called",
        user_id=str(current_user.id),
        has_token=has_token,
        visibility=visibility,
        sort=sort,
        per_page=per_page,
    )

    try:
        # Log token status BEFORE calling service (like test endpoint does)
        token_from_attrs = attrs.get("github_access_token")
        logger.info(
            f"[list_repos] Token check: has_token_in_attrs={token_from_attrs is not None}, "
            f"token_length={len(token_from_attrs) if token_from_attrs else 0}"
        )

        # EXACT COPY of test endpoint service call that works
        # The test endpoint returns 204 repos, so this should work too
        logger.info(
            f"[list_repos] About to call list_user_repos with user_id={current_user.id}, "
            f"visibility=all, sort=updated, per_page=100, page=1, fetch_all_pages=True"
        )
        repos = await github_service.list_user_repos(
            user_id=current_user.id,
            visibility="all",
            sort="updated",
            per_page=100,
            page=1,
            fetch_all_pages=True,
        )
        logger.info(
            f"[list_repos] Service returned {len(repos)} repositories for user {current_user.id}. "
            f"First 3: {[r.full_name for r in repos[:3]] if repos else 'none'}"
        )
        if len(repos) == 0:
            logger.error(
                f"[list_repos] CRITICAL BUG: Service returned 0 repos but /repos-test returns 204 for user {current_user.id}!"
            )
            # Try to get token via service method to compare
            try:
                token_from_service = github_service._get_user_token_by_id(
                    current_user.id
                )
                logger.error(
                    f"[list_repos] Token from service: has_token={token_from_service is not None}, "
                    f"length={len(token_from_service) if token_from_service else 0}"
                )
            except Exception as e:
                logger.error(f"[list_repos] Error getting token from service: {e}")
        return repos
    except ValueError as e:
        # Handle authentication errors from GitHub API
        logger.error(f"GitHub API error for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        # Catch any other unexpected errors
        logger.exception(
            f"Unexpected error in list_repos for user {current_user.id}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
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


# ============================================================================
# GitHub Disconnect Routes
# ============================================================================


@router.delete("/disconnect")
async def disconnect_github(
    current_user: User = Depends(get_approved_user),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Disconnect GitHub from the current user's account.

    This clears all GitHub-related data from the user's attributes,
    allowing them to reconnect with a different GitHub account or
    allowing the same GitHub account to be used with a different user.
    """
    attrs = current_user.attributes or {}

    # Check if GitHub is connected
    if not attrs.get("github_access_token") and not attrs.get("github_user_id"):
        raise HTTPException(
            status_code=400,
            detail="GitHub is not connected to this account."
        )

    # Store username for response before clearing
    github_username = attrs.get("github_username")

    # Clear all GitHub-related attributes
    github_keys_to_remove = [k for k in attrs.keys() if "github" in k.lower()]
    for key in github_keys_to_remove:
        del attrs[key]

    # Update user in database
    with db.get_session() as session:
        from sqlalchemy import update
        session.execute(
            update(User)
            .where(User.id == current_user.id)
            .values(attributes=attrs)
        )
        session.commit()

    logger.info(f"User {current_user.id} disconnected GitHub account: {github_username}")

    return {
        "success": True,
        "message": f"GitHub account @{github_username} has been disconnected.",
        "disconnected_username": github_username,
        "cleared_keys": github_keys_to_remove,
    }


@router.delete("/admin/disconnect/{user_id}")
async def admin_disconnect_github_for_user(
    user_id: str,
    current_user: User = Depends(get_approved_user),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Admin endpoint to disconnect GitHub from a specific user.

    Requires admin role (checked below).
    """
    # Check if current user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required."
        )

    with db.get_session() as session:
        from sqlalchemy import select, update
        from uuid import UUID

        # Get target user
        result = session.execute(
            select(User).where(User.id == UUID(user_id))
        )
        target_user = result.scalar_one_or_none()

        if not target_user:
            raise HTTPException(status_code=404, detail="User not found.")

        attrs = target_user.attributes or {}
        github_username = attrs.get("github_username")

        if not attrs.get("github_access_token") and not attrs.get("github_user_id"):
            raise HTTPException(
                status_code=400,
                detail=f"GitHub is not connected for user {target_user.email}."
            )

        # Clear GitHub attributes
        github_keys_to_remove = [k for k in attrs.keys() if "github" in k.lower()]
        for key in github_keys_to_remove:
            del attrs[key]

        session.execute(
            update(User)
            .where(User.id == UUID(user_id))
            .values(attributes=attrs)
        )
        session.commit()

    logger.info(f"Admin {current_user.email} disconnected GitHub for user {user_id} ({github_username})")

    return {
        "success": True,
        "message": f"GitHub disconnected for user {target_user.email}",
        "user_id": user_id,
        "user_email": target_user.email,
        "disconnected_username": github_username,
    }


@router.delete("/admin/disconnect-all")
async def admin_disconnect_all_github(
    current_user: User = Depends(get_approved_user),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Admin endpoint to disconnect GitHub from ALL users.

    Use with caution - this will require all users to reconnect GitHub.
    """
    # Check if current user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required."
        )

    disconnected_count = 0
    disconnected_users = []

    with db.get_session() as session:
        from sqlalchemy import select, update

        # Get all users with GitHub connected
        result = session.execute(select(User))
        users = result.scalars().all()

        for user in users:
            attrs = user.attributes or {}
            if attrs.get("github_access_token") or attrs.get("github_user_id"):
                github_username = attrs.get("github_username")

                # Clear GitHub attributes
                github_keys = [k for k in attrs.keys() if "github" in k.lower()]
                for key in github_keys:
                    del attrs[key]

                session.execute(
                    update(User)
                    .where(User.id == user.id)
                    .values(attributes=attrs)
                )

                disconnected_count += 1
                disconnected_users.append({
                    "user_id": str(user.id),
                    "email": user.email,
                    "github_username": github_username,
                })

        session.commit()

    logger.warning(f"Admin {current_user.email} disconnected GitHub for ALL users ({disconnected_count} users)")

    return {
        "success": True,
        "message": f"GitHub disconnected for {disconnected_count} users.",
        "disconnected_count": disconnected_count,
        "disconnected_users": disconnected_users,
    }
