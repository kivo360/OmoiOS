"""API routes for Kanban board operations."""

from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from omoi_os.api.dependencies import get_db_service
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


@router.get("/view", response_model=BoardViewResponse)
def get_board_view(
    db: DatabaseService = Depends(get_db_service),
    board_service: BoardService = Depends(get_board_service),
) -> BoardViewResponse:
    """
    Get complete Kanban board view.

    Returns all columns with tickets organized by current phase.
    Automatically initializes default board columns if none exist.
    """
    try:
        with db.get_session() as session:
            # Check if board columns exist, if not, create defaults
            from omoi_os.models.board_column import BoardColumn
            from sqlalchemy import select
            
            existing_columns = session.execute(select(BoardColumn)).scalars().first()
            if not existing_columns:
                # Initialize default board columns
                board_service.create_default_board(session=session)
                session.commit()
            
            board_data = board_service.get_board_view(session=session)
            return BoardViewResponse(**board_data)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get board view: {str(e)}"
        )


@router.post("/move")
def move_ticket(
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
        with db.get_session() as session:
            ticket = board_service.move_ticket_to_column(
                session=session,
                ticket_id=request.ticket_id,
                target_column_id=request.target_column_id,
                force=request.force,
            )
            session.commit()

            return {
                "ticket_id": ticket.id,
                "new_phase": ticket.phase_id,
                "new_column": request.target_column_id,
                "status": "moved",
            }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to move ticket: {str(e)}")


@router.get("/stats", response_model=List[ColumnStatsResponse])
def get_column_stats(
    db: DatabaseService = Depends(get_db_service),
    board_service: BoardService = Depends(get_board_service),
) -> List[ColumnStatsResponse]:
    """
    Get statistics for all board columns.

    Includes ticket counts, WIP utilization, and limit violations.
    """
    try:
        with db.get_session() as session:
            stats = board_service.get_column_stats(session=session)
            return [ColumnStatsResponse(**stat) for stat in stats]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get column stats: {str(e)}"
        )


@router.get("/wip-violations", response_model=List[WIPViolationResponse])
def check_wip_violations(
    db: DatabaseService = Depends(get_db_service),
    board_service: BoardService = Depends(get_board_service),
) -> List[WIPViolationResponse]:
    """
    Check for WIP limit violations across all columns.

    Returns columns where current ticket count exceeds WIP limit.
    Useful for Guardian monitoring and resource reallocation.
    """
    try:
        with db.get_session() as session:
            violations = board_service.check_wip_limits(session=session)
            return [WIPViolationResponse(**v) for v in violations]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to check WIP limits: {str(e)}"
        )


@router.post("/auto-transition/{ticket_id}")
def auto_transition_ticket(
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
def get_column_for_phase(
    phase_id: str,
    db: DatabaseService = Depends(get_db_service),
    board_service: BoardService = Depends(get_board_service),
) -> Dict[str, Any]:
    """
    Find which board column a phase belongs to.

    Useful for determining visual position of a ticket.
    """
    try:
        with db.get_session() as session:
            column = board_service.get_column_for_phase(session=session, phase_id=phase_id)

            if column:
                return column.to_dict()
            else:
                raise HTTPException(
                    status_code=404, detail=f"No column found for phase {phase_id}"
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to find column: {str(e)}")
