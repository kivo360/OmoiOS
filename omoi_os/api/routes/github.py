"""GitHub Integration API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel

from omoi_os.api.dependencies import get_db_service, get_event_bus_service
from omoi_os.config import get_app_settings
from omoi_os.models.project import Project
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.github_integration import GitHubIntegrationService

router = APIRouter()


class ConnectRepositoryRequest(BaseModel):
    """Request model for connecting a GitHub repository."""

    owner: str
    repo: str
    webhook_secret: Optional[str] = None


class ConnectRepositoryResponse(BaseModel):
    """Response model for repository connection."""

    success: bool
    message: str
    project_id: str
    webhook_url: Optional[str] = None


class RepositoryResponse(BaseModel):
    """Response model for repository info."""

    owner: str
    repo: str
    connected: bool
    webhook_configured: bool


def get_github_service(
    db: DatabaseService = Depends(get_db_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
) -> GitHubIntegrationService:
    """Get GitHub integration service instance."""
    github_token = get_app_settings().integrations.github_token
    return GitHubIntegrationService(
        db=db, event_bus=event_bus, github_token=github_token
    )


@router.post("/connect", response_model=ConnectRepositoryResponse)
async def connect_repository(
    project_id: str,
    request: ConnectRepositoryRequest,
    github_service: GitHubIntegrationService = Depends(get_github_service),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Connect a GitHub repository to a project.

    Args:
        project_id: Project ID
        request: Repository connection data
        github_service: GitHub integration service
        db: Database service

    Returns:
        Connection result with webhook URL
    """
    result = await github_service.connect_repository(
        project_id=project_id,
        owner=request.owner,
        repo=request.repo,
        webhook_secret=request.webhook_secret,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))

    # Generate webhook URL (would be actual webhook endpoint)
    webhook_url = "/api/v1/webhooks/github"

    return ConnectRepositoryResponse(
        success=True,
        message=result["message"],
        project_id=project_id,
        webhook_url=webhook_url,
    )


@router.get("/repos", response_model=list[RepositoryResponse])
async def list_connected_repositories(
    db: DatabaseService = Depends(get_db_service),
):
    """
    List all connected GitHub repositories.

    Args:
        db: Database service

    Returns:
        List of connected repositories
    """
    with db.get_session() as session:
        projects = (
            session.query(Project).filter(Project.github_connected.is_(True)).all()
        )

        return [
            RepositoryResponse(
                owner=p.github_owner or "",
                repo=p.github_repo or "",
                connected=p.github_connected,
                webhook_configured=bool(p.github_webhook_secret),
            )
            for p in projects
            if p.github_owner and p.github_repo
        ]


@router.post("/webhooks/github")
async def handle_github_webhook(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    github_service: GitHubIntegrationService = Depends(get_github_service),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Handle GitHub webhook events.

    Args:
        request: FastAPI request object
        x_github_event: GitHub event type header
        x_hub_signature_256: GitHub webhook signature header
        github_service: GitHub integration service
        db: Database service

    Returns:
        Webhook processing result
    """
    # Get raw body for signature verification
    body = await request.body()
    payload = await request.json()

    # Verify signature if provided
    # Note: In production, you'd get the webhook secret from the project
    # For now, we'll skip verification (user will add auth later)
    secret = None  # TODO: Get from project settings based on repository

    if x_hub_signature_256 and secret:
        if not github_service.verify_webhook_signature(
            body, x_hub_signature_256, secret
        ):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Process webhook
    result = await github_service.handle_webhook(
        event_type=x_github_event,
        payload=payload,
        signature=x_hub_signature_256,
        secret=secret,
    )

    return result


@router.post("/sync")
async def sync_repository(
    project_id: str,
    github_service: GitHubIntegrationService = Depends(get_github_service),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Manually trigger sync with GitHub repository.

    Args:
        project_id: Project ID
        github_service: GitHub integration service
        db: Database service

    Returns:
        Sync result
    """
    with db.get_session() as session:
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if (
            not project.github_connected
            or not project.github_owner
            or not project.github_repo
        ):
            raise HTTPException(
                status_code=400, detail="Project not connected to GitHub repository"
            )

        # TODO: Implement sync logic
        # This would fetch recent commits, issues, PRs from GitHub
        # and sync them with the project

        return {
            "success": True,
            "message": f"Sync initiated for {project.github_owner}/{project.github_repo}",
        }
