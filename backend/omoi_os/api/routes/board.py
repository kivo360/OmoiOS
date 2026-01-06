"""API routes for Kanban board operations."""

import asyncio
from typing import List, Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from omoi_os.api.dependencies import get_db_service, get_current_user
from omoi_os.models.user import User
from omoi_os.services.board import BoardService
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService

router = APIRouter(prefix="/board", tags=["board"])


# Request/Response Models
class MoveTicketRequest(BaseModel):
    """Request to move ticket to different column."""

    ticket_id: str = Field(..., description="Ticket ID to move")
    target_column_id: str = Field(..., description="Target column ID")
    force: bool = Field(False, description="Force move even if WIP limit exceeded")


class BoardViewResponse(BaseModel):
    """Response for board view."""

    columns: List[Dict[str, Any]]


class ColumnStatsResponse(BaseModel):
    """Response for column statistics."""

    column_id: str
    name: str
    ticket_count: int
    wip_limit: Optional[int]
    utilization: Optional[float]
    wip_exceeded: bool


class WIPViolationResponse(BaseModel):
    """Response for WIP limit violations."""

    column_id: str
    column_name: str
    wip_limit: int
    current_count: int
    excess: int


# Dependency: Get BoardService
def get_board_service() -> BoardService:
    """Get board service with dependencies."""
    event_bus = EventBusService()
    return BoardService(event_bus=event_bus)


# ============================================================================
# Sync helpers that run in thread pool (non-blocking)
# ============================================================================
# BoardService uses sync SQLAlchemy operations, so we run them in a thread pool
# to avoid blocking the event loop while still being non-blocking for async callers.


def _get_board_view_sync(
    db: DatabaseService,
    board_service: BoardService,
    user_id: UUID,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get board view (runs in thread pool)."""
    with db.get_session() as session:
        # Check if board columns exist, if not, create defaults
        from omoi_os.models.board_column import BoardColumn

        existing_columns = session.query(BoardColumn).first()

        if not existing_columns:
            board_service.create_default_board(session=session)
            session.commit()

        board_data = board_service.get_board_view(session=session, project_id=project_id, user_id=user_id)
        return board_data


def _move_ticket_sync(
    db: DatabaseService,
    board_service: BoardService,
    ticket_id: str,
    target_column_id: str,
    force: bool = False,
) -> Dict[str, Any]:
    """Move ticket to column (runs in thread pool)."""
    with db.get_session() as session:
        ticket = board_service.move_ticket_to_column(
            session=session,
            ticket_id=ticket_id,
            target_column_id=target_column_id,
            force=force,
        )
        session.commit()

        return {
            "ticket_id": ticket.id,
            "new_phase": ticket.phase_id,
            "new_column": target_column_id,
            "status": "moved",
        }


def _get_column_stats_sync(
    db: DatabaseService,
    board_service: BoardService,
    project_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get column stats (runs in thread pool)."""
    with db.get_session() as session:
        stats = board_service.get_column_stats(session=session, project_id=project_id)
        return stats


def _check_wip_violations_sync(
    db: DatabaseService,
    board_service: BoardService,
    project_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Check WIP violations (runs in thread pool)."""
    with db.get_session() as session:
        violations = board_service.check_wip_limits(session=session, project_id=project_id)
        return violations


def _auto_transition_ticket_sync(
    db: DatabaseService,
    board_service: BoardService,
    ticket_id: str,
) -> Optional[Dict[str, Any]]:
    """Auto transition ticket (runs in thread pool)."""
    with db.get_session() as session:
        result = board_service.auto_transition_ticket(session=session, ticket_id=ticket_id)

        if result:
            session.commit()
            return {
                "ticket_id": result.id,
                "new_phase": result.phase_id,
                "transitioned": True,
            }
        else:
            return None


def _get_column_for_phase_sync(
    db: DatabaseService,
    board_service: BoardService,
    phase_id: str,
) -> Optional[Dict[str, Any]]:
    """Get column for phase (runs in thread pool)."""
    with db.get_session() as session:
        column = board_service.get_column_for_phase(session=session, phase_id=phase_id)

        if column:
            return column.to_dict()
        return None


@router.get("/view", response_model=BoardViewResponse)
async def get_board_view(
    project_id: Optional[str] = Query(None, description="Filter tickets by project ID. Omit for cross-project board."),
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    board_service: BoardService = Depends(get_board_service),
) -> BoardViewResponse:
    """
    Get complete Kanban board view for the authenticated user.

    Returns all columns with tickets organized by current phase.
    Automatically initializes default board columns if none exist.
    Only shows tickets belonging to the authenticated user.

    Args:
        project_id: Optional project ID to filter tickets. If omitted, shows all user's tickets (cross-project board).
    """
    try:
        # Run sync service in thread pool (non-blocking)
        board_data = await asyncio.to_thread(
            _get_board_view_sync, db, board_service, current_user.id, project_id
        )
        return BoardViewResponse(**board_data)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get board view: {str(e)}"
        )


@router.post("/move")
async def move_ticket(
    request: MoveTicketRequest,
    db: DatabaseService = Depends(get_db_service),
    board_service: BoardService = Depends(get_board_service),
) -> Dict[str, Any]:
    """
    Move ticket to a different board column.

    This updates the ticket's phase to match the target column's first
    phase mapping. Respects WIP limits unless force=True.
    """
    try:
        # Run sync service in thread pool (non-blocking)
        result = await asyncio.to_thread(
            _move_ticket_sync,
            db,
            board_service,
            request.ticket_id,
            request.target_column_id,
            request.force,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to move ticket: {str(e)}")


@router.get("/stats", response_model=List[ColumnStatsResponse])
async def get_column_stats(
    project_id: Optional[str] = Query(None, description="Filter tickets by project ID. Omit for all projects."),
    db: DatabaseService = Depends(get_db_service),
    board_service: BoardService = Depends(get_board_service),
) -> List[ColumnStatsResponse]:
    """
    Get statistics for all board columns.

    Includes ticket counts, WIP utilization, and limit violations.

    Args:
        project_id: Optional project ID to filter tickets. If omitted, shows all projects.
    """
    try:
        # Run sync service in thread pool (non-blocking)
        stats = await asyncio.to_thread(
            _get_column_stats_sync, db, board_service, project_id
        )
        return [ColumnStatsResponse(**stat) for stat in stats]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get column stats: {str(e)}"
        )


@router.get("/wip-violations", response_model=List[WIPViolationResponse])
async def check_wip_violations(
    project_id: Optional[str] = Query(None, description="Filter tickets by project ID. Omit for all projects."),
    db: DatabaseService = Depends(get_db_service),
    board_service: BoardService = Depends(get_board_service),
) -> List[WIPViolationResponse]:
    """
    Check for WIP limit violations across all columns.

    Returns columns where current ticket count exceeds WIP limit.
    Useful for Guardian monitoring and resource reallocation.

    Args:
        project_id: Optional project ID to filter tickets. If omitted, checks all projects.
    """
    try:
        # Run sync service in thread pool (non-blocking)
        violations = await asyncio.to_thread(
            _check_wip_violations_sync, db, board_service, project_id
        )
        return [WIPViolationResponse(**v) for v in violations]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to check WIP limits: {str(e)}"
        )


@router.post("/auto-transition/{ticket_id}")
async def auto_transition_ticket(
    ticket_id: str,
    db: DatabaseService = Depends(get_db_service),
    board_service: BoardService = Depends(get_board_service),
) -> Dict[str, Any]:
    """
    Automatically transition ticket to next column if configured.

    Used when a ticket completes and should move to the next stage
    (e.g., building → testing).
    """
    try:
        # Run sync service in thread pool (non-blocking)
        result = await asyncio.to_thread(
            _auto_transition_ticket_sync, db, board_service, ticket_id
        )

        if result:
            return result
        else:
            return {
                "ticket_id": ticket_id,
                "transitioned": False,
                "reason": "No auto-transition configured or WIP limit exceeded",
            }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to auto-transition: {str(e)}"
        )


@router.get("/column/{phase_id}")
async def get_column_for_phase(
    phase_id: str,
    db: DatabaseService = Depends(get_db_service),
    board_service: BoardService = Depends(get_board_service),
) -> Dict[str, Any]:
    """
    Find which board column a phase belongs to.

    Useful for determining visual position of a ticket.
    """
    try:
        # Run sync service in thread pool (non-blocking)
        column_data = await asyncio.to_thread(
            _get_column_for_phase_sync, db, board_service, phase_id
        )

        if column_data:
            return column_data
        else:
            raise HTTPException(
                status_code=404, detail=f"No column found for phase {phase_id}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to find column: {str(e)}")
