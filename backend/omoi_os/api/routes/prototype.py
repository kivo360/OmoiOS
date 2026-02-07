"""Prototype API routes for rapid prototyping mode.

Phase 3: Prototyping Mode — fast prompt-to-preview iteration without
the full spec pipeline.

Endpoints:
- POST   /session                    — Start a prototype session
- GET    /session/{session_id}       — Get session status
- POST   /session/{session_id}/prompt  — Apply a prompt
- POST   /session/{session_id}/export  — Export to git repo
- DELETE /session/{session_id}       — End session
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from omoi_os.api.dependencies import get_current_user, get_prototype_manager
from omoi_os.models.user import User
from omoi_os.services.prototype_manager import PrototypeManager, PrototypeSession

router = APIRouter()


# ============================================================================
# Request / Response Schemas
# ============================================================================


class StartSessionRequest(BaseModel):
    """Request to start a new prototype session."""

    framework: str  # "react-vite" | "next" | "vue-vite"


class ApplyPromptRequest(BaseModel):
    """Request to apply a prompt to the prototype."""

    prompt: str


class ExportRequest(BaseModel):
    """Request to export prototype code to a git repo."""

    repo_url: str
    branch: str = "prototype"
    commit_message: str = "Export prototype"


class PromptHistoryItem(BaseModel):
    """A single prompt/response pair."""

    prompt: str
    response_summary: str
    timestamp: str


class SessionResponse(BaseModel):
    """Response schema for prototype session data."""

    id: str
    user_id: str
    framework: str
    sandbox_id: Optional[str] = None
    preview_id: Optional[str] = None
    status: str
    preview_url: Optional[str] = None
    prompt_history: List[PromptHistoryItem] = []
    error_message: Optional[str] = None
    created_at: str


class PromptResponse(BaseModel):
    """Response from applying a prompt."""

    prompt: str
    response_summary: str
    timestamp: str


class ExportResponse(BaseModel):
    """Response from exporting to a repo."""

    repo_url: str
    branch: str
    commit_message: str
    timestamp: str


# ============================================================================
# Helpers
# ============================================================================


def _session_to_response(session: PrototypeSession) -> SessionResponse:
    """Convert internal session dataclass to API response."""
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        framework=session.framework,
        sandbox_id=session.sandbox_id,
        preview_id=session.preview_id,
        status=(
            session.status.value if hasattr(session.status, "value") else session.status
        ),
        preview_url=session.preview_url,
        prompt_history=[PromptHistoryItem(**item) for item in session.prompt_history],
        error_message=session.error_message,
        created_at=session.created_at,
    )


# ============================================================================
# Routes
# ============================================================================


@router.post(
    "/session",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a prototype session",
)
async def start_session(
    body: StartSessionRequest,
    current_user: User = Depends(get_current_user),
    manager: PrototypeManager = Depends(get_prototype_manager),
):
    """Start a new prototype session with a framework template.

    Creates a Daytona sandbox from a pre-built snapshot, starts the
    dev server, and returns a preview URL.
    """
    try:
        session = await manager.start_session(
            user_id=str(current_user.id),
            framework=body.framework,
        )
        return _session_to_response(session)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/session/{session_id}",
    response_model=SessionResponse,
    summary="Get prototype session status",
)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    manager: PrototypeManager = Depends(get_prototype_manager),
):
    """Get the current status of a prototype session."""
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    return _session_to_response(session)


@router.post(
    "/session/{session_id}/prompt",
    response_model=PromptResponse,
    summary="Apply a prompt to the prototype",
)
async def apply_prompt(
    session_id: str,
    body: ApplyPromptRequest,
    current_user: User = Depends(get_current_user),
    manager: PrototypeManager = Depends(get_prototype_manager),
):
    """Apply a prompt to generate or modify code in the prototype sandbox."""
    try:
        result = await manager.apply_prompt(session_id, body.prompt)
        return PromptResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/session/{session_id}/export",
    response_model=ExportResponse,
    summary="Export prototype to a git repository",
)
async def export_to_repo(
    session_id: str,
    body: ExportRequest,
    current_user: User = Depends(get_current_user),
    manager: PrototypeManager = Depends(get_prototype_manager),
):
    """Export the prototype sandbox code to a git repository."""
    try:
        result = await manager.export_to_repo(
            session_id=session_id,
            repo_url=body.repo_url,
            branch=body.branch,
            commit_message=body.commit_message,
        )
        return ExportResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete(
    "/session/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="End a prototype session",
)
async def end_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    manager: PrototypeManager = Depends(get_prototype_manager),
):
    """End a prototype session and clean up its sandbox resources."""
    try:
        await manager.end_session(session_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
