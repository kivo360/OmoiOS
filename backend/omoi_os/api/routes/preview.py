"""Preview API routes for live preview management.

Phase 1: Backend Preview Routes + DaytonaSpawner Integration.

Provides CRUD endpoints for managing live preview sessions:
- POST /                     — Create preview for a sandbox
- GET /{preview_id}          — Get preview status + URL
- DELETE /{preview_id}       — Stop preview
- GET /sandbox/{sandbox_id}  — Get preview by sandbox ID
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from omoi_os.api.dependencies import (
    get_current_user,
    get_db_service,
    get_event_bus_service,
)
from omoi_os.models.user import User
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.preview_manager import PreviewManager

router = APIRouter()


# ============================================================================
# Request / Response Schemas
# ============================================================================


class CreatePreviewRequest(BaseModel):
    """Request body for creating a preview session."""

    sandbox_id: str
    task_id: Optional[str] = None
    project_id: Optional[str] = None
    port: int = 3000
    framework: Optional[str] = None


class PreviewResponse(BaseModel):
    """Response schema for preview session data."""

    id: str
    sandbox_id: str
    task_id: Optional[str] = None
    project_id: Optional[str] = None
    status: str
    preview_url: Optional[str] = None
    port: int
    framework: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    ready_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ============================================================================
# Helper
# ============================================================================


def _get_preview_manager(
    db: DatabaseService = Depends(get_db_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
) -> PreviewManager:
    """Dependency to construct PreviewManager."""
    return PreviewManager(db=db, event_bus=event_bus)


# ============================================================================
# Routes
# ============================================================================


@router.post(
    "/",
    response_model=PreviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a preview session",
)
async def create_preview(
    body: CreatePreviewRequest,
    current_user: User = Depends(get_current_user),
    manager: PreviewManager = Depends(_get_preview_manager),
):
    """Create a new preview session for a sandbox.

    The preview starts in PENDING status. The DaytonaSpawner (or caller)
    should subsequently update it to STARTING → READY as the dev server boots.
    """
    try:
        preview = await manager.create_preview(
            sandbox_id=body.sandbox_id,
            task_id=body.task_id,
            project_id=body.project_id,
            user_id=str(current_user.id),
            port=body.port,
            framework=body.framework,
        )
        return PreviewResponse.model_validate(preview)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "/{preview_id}",
    response_model=PreviewResponse,
    summary="Get preview by ID",
)
async def get_preview(
    preview_id: str,
    current_user: User = Depends(get_current_user),
    manager: PreviewManager = Depends(_get_preview_manager),
):
    """Get preview session details by preview ID."""
    preview = await manager.get_by_id(preview_id)
    if not preview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preview not found: {preview_id}",
        )
    return PreviewResponse.model_validate(preview)


@router.delete(
    "/{preview_id}",
    response_model=PreviewResponse,
    summary="Stop a preview",
)
async def stop_preview(
    preview_id: str,
    current_user: User = Depends(get_current_user),
    manager: PreviewManager = Depends(_get_preview_manager),
):
    """Stop (deactivate) a preview session.

    Transitions the preview to STOPPED status. Does not delete the
    sandbox itself — that's handled by the spawner lifecycle.
    """
    try:
        preview = await manager.mark_stopped(preview_id)
        return PreviewResponse.model_validate(preview)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preview not found: {preview_id}",
        )


class PreviewNotifyRequest(BaseModel):
    """Worker callback for preview state changes."""

    sandbox_id: str
    status: str  # "starting", "ready", "failed"
    preview_url: Optional[str] = None  # Override if worker knows the URL
    error_message: Optional[str] = None


@router.post("/notify", summary="Worker preview status callback")
async def notify_preview_status(
    body: PreviewNotifyRequest,
    db: DatabaseService = Depends(get_db_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """Called by sandbox worker to update preview session status.

    No auth required — worker calls this from inside the sandbox.
    The preview URL is pre-stored by the spawner from the Daytona SDK.
    """
    manager = PreviewManager(db=db, event_bus=event_bus)
    preview = await manager.get_by_sandbox(body.sandbox_id)
    if not preview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No preview for sandbox: {body.sandbox_id}",
        )

    preview_id = str(preview.id)

    if body.status == "starting":
        await manager.mark_starting(preview_id)
    elif body.status == "ready":
        # Use pre-stored URL from spawner, or override if worker provides one
        url = body.preview_url or preview.preview_url or ""
        token = preview.preview_token
        await manager.mark_ready(preview_id, url, token)
    elif body.status == "failed":
        await manager.mark_failed(preview_id, body.error_message or "Unknown error")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {body.status}",
        )

    return {"status": "ok", "preview_id": preview_id}


@router.get(
    "/sandbox/{sandbox_id}",
    response_model=PreviewResponse,
    summary="Get preview by sandbox ID",
)
async def get_preview_by_sandbox(
    sandbox_id: str,
    current_user: User = Depends(get_current_user),
    manager: PreviewManager = Depends(_get_preview_manager),
):
    """Get preview session details by Daytona sandbox ID."""
    preview = await manager.get_by_sandbox(sandbox_id)
    if not preview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No preview found for sandbox: {sandbox_id}",
        )
    return PreviewResponse.model_validate(preview)
