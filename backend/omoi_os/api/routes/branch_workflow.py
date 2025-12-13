"""
Branch workflow API routes.

Phase 5: Exposes BranchWorkflowService operations via HTTP for:
- Creating feature branches when tasks start
- Creating PRs when tasks complete
- Managing branch lifecycle
"""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from omoi_os.services.branch_workflow import BranchWorkflowService
from omoi_os.services.github_api import GitHubAPIService

router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================


class StartWorkRequest(BaseModel):
    """Request to start work on a ticket (create branch)."""

    ticket_id: str = Field(..., description="Ticket identifier")
    ticket_title: str = Field(..., description="Ticket title for branch naming")
    repo_owner: str = Field(..., description="GitHub repository owner")
    repo_name: str = Field(..., description="GitHub repository name")
    user_id: str = Field(..., description="User ID for GitHub API authentication")
    ticket_type: str = Field(
        default="feature", description="Ticket type (feature, bug, etc.)"
    )
    priority: Optional[str] = Field(
        default=None, description="Priority (critical for hotfix)"
    )


class StartWorkResponse(BaseModel):
    """Response from starting work."""

    success: bool
    branch_name: Optional[str] = None
    sha: Optional[str] = None
    error: Optional[str] = None


class FinishWorkRequest(BaseModel):
    """Request to finish work (create PR)."""

    ticket_id: str = Field(..., description="Ticket identifier")
    ticket_title: str = Field(..., description="Ticket title for PR")
    branch_name: str = Field(..., description="Feature branch name")
    repo_owner: str = Field(..., description="GitHub repository owner")
    repo_name: str = Field(..., description="GitHub repository name")
    user_id: str = Field(..., description="User ID for GitHub API authentication")
    pr_body: Optional[str] = Field(default=None, description="PR body/description")


class FinishWorkResponse(BaseModel):
    """Response from finishing work."""

    success: bool
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    error: Optional[str] = None


class MergeWorkRequest(BaseModel):
    """Request to merge completed work."""

    ticket_id: str = Field(..., description="Ticket identifier")
    pr_number: int = Field(..., description="Pull request number")
    repo_owner: str = Field(..., description="GitHub repository owner")
    repo_name: str = Field(..., description="GitHub repository name")
    user_id: str = Field(..., description="User ID for GitHub API authentication")
    delete_branch_after: bool = Field(
        default=True, description="Delete branch after merge"
    )
    merge_method: str = Field(
        default="squash", description="Merge method (merge, squash, rebase)"
    )


class MergeWorkResponse(BaseModel):
    """Response from merging work."""

    success: bool
    merge_sha: Optional[str] = None
    has_conflicts: bool = False
    error: Optional[str] = None


class BranchStatusRequest(BaseModel):
    """Request to get branch status."""

    branch_name: str = Field(..., description="Branch name to check")
    repo_owner: str = Field(..., description="GitHub repository owner")
    repo_name: str = Field(..., description="GitHub repository name")
    user_id: str = Field(..., description="User ID for GitHub API authentication")


class BranchStatusResponse(BaseModel):
    """Response with branch status."""

    success: bool
    ahead_by: int = 0
    behind_by: int = 0
    has_conflicts: bool = False
    error: Optional[str] = None


# ============================================================================
# SERVICE FACTORY
# ============================================================================

_branch_workflow_service: BranchWorkflowService | None = None


def get_branch_workflow_service() -> BranchWorkflowService:
    """Get or create BranchWorkflowService instance."""
    global _branch_workflow_service
    if _branch_workflow_service is None:
        # Create GitHub API service
        from omoi_os.services.database import DatabaseService
        from omoi_os.config import get_app_settings

        settings = get_app_settings()
        db_service = DatabaseService(connection_string=settings.database.url)
        github_service = GitHubAPIService(db=db_service)

        _branch_workflow_service = BranchWorkflowService(github_service=github_service)
    return _branch_workflow_service


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("/start", response_model=StartWorkResponse)
async def start_work_on_ticket(request: StartWorkRequest) -> StartWorkResponse:
    """
    Create a feature branch for a ticket.

    This endpoint is called when an agent starts working on a task.
    It creates a properly named branch following GitFlow conventions:
    - feature/{ticket-id}-{description} for features
    - fix/{ticket-id}-{description} for bugs
    - hotfix/{ticket-id}-{description} for critical bugs

    Args:
        request: StartWorkRequest with ticket and repo info

    Returns:
        StartWorkResponse with branch name and status
    """
    service = get_branch_workflow_service()

    result = await service.start_work_on_ticket(
        ticket_id=request.ticket_id,
        ticket_title=request.ticket_title,
        repo_owner=request.repo_owner,
        repo_name=request.repo_name,
        user_id=request.user_id,
        ticket_type=request.ticket_type,
        priority=request.priority,
    )

    return StartWorkResponse(
        success=result.get("success", False),
        branch_name=result.get("branch_name"),
        sha=result.get("sha"),
        error=result.get("error"),
    )


@router.post("/finish", response_model=FinishWorkResponse)
async def finish_work_on_ticket(request: FinishWorkRequest) -> FinishWorkResponse:
    """
    Create a pull request for completed work.

    This endpoint is called when an agent finishes working on a task.
    It creates a PR from the feature branch to the default branch.

    Args:
        request: FinishWorkRequest with ticket, branch, and repo info

    Returns:
        FinishWorkResponse with PR number and URL
    """
    service = get_branch_workflow_service()

    result = await service.finish_work_on_ticket(
        ticket_id=request.ticket_id,
        ticket_title=request.ticket_title,
        branch_name=request.branch_name,
        repo_owner=request.repo_owner,
        repo_name=request.repo_name,
        user_id=request.user_id,
        pr_body=request.pr_body,
    )

    return FinishWorkResponse(
        success=result.get("success", False),
        pr_number=result.get("pr_number"),
        pr_url=result.get("pr_url"),
        error=result.get("error"),
    )


@router.post("/merge", response_model=MergeWorkResponse)
async def merge_ticket_work(request: MergeWorkRequest) -> MergeWorkResponse:
    """
    Merge a pull request and cleanup.

    This endpoint merges a PR and optionally deletes the feature branch.
    It checks for merge conflicts before attempting to merge.

    Args:
        request: MergeWorkRequest with PR and repo info

    Returns:
        MergeWorkResponse with merge status
    """
    service = get_branch_workflow_service()

    result = await service.merge_ticket_work(
        ticket_id=request.ticket_id,
        pr_number=request.pr_number,
        repo_owner=request.repo_owner,
        repo_name=request.repo_name,
        user_id=request.user_id,
        delete_branch_after=request.delete_branch_after,
        merge_method=request.merge_method,
    )

    return MergeWorkResponse(
        success=result.get("success", False),
        merge_sha=result.get("merge_sha"),
        has_conflicts=result.get("has_conflicts", False),
        error=result.get("error"),
    )


@router.post("/status", response_model=BranchStatusResponse)
async def get_branch_status(request: BranchStatusRequest) -> BranchStatusResponse:
    """
    Get status of a feature branch.

    Returns how far ahead/behind the branch is from the default branch.

    Args:
        request: BranchStatusRequest with branch and repo info

    Returns:
        BranchStatusResponse with ahead/behind counts
    """
    service = get_branch_workflow_service()

    result = await service.get_branch_status(
        branch_name=request.branch_name,
        repo_owner=request.repo_owner,
        repo_name=request.repo_name,
        user_id=request.user_id,
    )

    return BranchStatusResponse(
        success=result.get("success", False),
        ahead_by=result.get("ahead_by", 0),
        behind_by=result.get("behind_by", 0),
        has_conflicts=result.get("has_conflicts", False),
        error=result.get("error"),
    )
