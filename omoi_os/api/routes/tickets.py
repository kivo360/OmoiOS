"""Ticket API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict

from omoi_os.api.dependencies import get_db_service, get_task_queue
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.context_service import ContextService


router = APIRouter()


class TicketCreate(BaseModel):
    """Request model for creating a ticket."""

    title: str
    description: str | None = None
    phase_id: str = "PHASE_REQUIREMENTS"
    priority: str = "MEDIUM"


class TicketResponse(BaseModel):
    """Response model for ticket."""

    id: UUID
    title: str
    description: str | None
    phase_id: str
    status: str
    priority: str

    model_config = ConfigDict(from_attributes=True)


@router.post("", response_model=TicketResponse)
async def create_ticket(
    ticket_data: TicketCreate,
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
):
    """
    Create a new ticket and enqueue initial tasks.

    Args:
        ticket_data: Ticket creation data
        db: Database service
        queue: Task queue service

    Returns:
        Created ticket
    """
    with db.get_session() as session:
        ticket = Ticket(
            title=ticket_data.title,
            description=ticket_data.description,
            phase_id=ticket_data.phase_id,
            status="pending",
            priority=ticket_data.priority,
        )
        session.add(ticket)
        session.flush()

        # Create initial task for the ticket
        queue.enqueue_task(
            ticket_id=ticket.id,
            phase_id=ticket_data.phase_id,
            task_type="analyze_requirements",
            description=f"Analyze requirements for: {ticket_data.title}",
            priority=ticket_data.priority,
        )

        session.commit()
        session.refresh(ticket)
        return TicketResponse.model_validate(ticket)


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: UUID,
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get a ticket by ID.

    Args:
        ticket_id: Ticket ID
        db: Database service

    Returns:
        Ticket instance
    """
    with db.get_session() as session:
        ticket = session.get(Ticket, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return TicketResponse.model_validate(ticket)


@router.get("/{ticket_id}/context")
async def get_ticket_context(
    ticket_id: UUID,
    db: DatabaseService = Depends(get_db_service),
):
    """
    Retrieve stored aggregated context and summary for a ticket.
    """
    with db.get_session() as session:
        ticket = session.get(Ticket, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        session.expunge(ticket)
    return {
        "ticket_id": str(ticket_id),
        "full_context": ticket.context or {},
        "summary": ticket.context_summary,
    }


@router.post("/{ticket_id}/update-context")
async def update_ticket_context_endpoint(
    ticket_id: UUID,
    phase_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """
    Aggregate phase tasks and update ticket context fields.
    """
    service = ContextService(db)
    service.update_ticket_context(str(ticket_id), phase_id)
    return {"status": "updated"}
