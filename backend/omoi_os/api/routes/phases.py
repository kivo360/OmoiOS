"""Phase gate API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from omoi_os.api.dependencies import get_db_service
from omoi_os.models.phase_gate_artifact import PhaseGateArtifact
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService
from omoi_os.services.phase_gate import PhaseGateService


router = APIRouter()


class ArtifactCreate(BaseModel):
    """Request body for registering artifacts via API."""

    phase_id: str
    artifact_type: str
    artifact_path: str | None = None
    artifact_content: dict | None = None
    collected_by: str = "api"


class ArtifactResponse(BaseModel):
    """Response payload after storing an artifact."""

    id: str
    artifact_type: str
    phase_id: str
    artifact_path: str | None
    artifact_content: dict | None

    model_config = ConfigDict(from_attributes=True)


@router.post("/tickets/{ticket_id}/validate-gate")
async def validate_gate(
    ticket_id: UUID,
    phase_id: str | None = None,
    db: DatabaseService = Depends(get_db_service),
):
    """Validate phase gate for a ticket."""
    ticket = _get_ticket_or_404(db, ticket_id)
    service = PhaseGateService(db)
    target_phase = phase_id or ticket.phase_id
    result = service.validate_gate(str(ticket.id), target_phase)
    return {
        "gate_status": result.gate_status,
        "requirements_met": result.gate_status == "passed",
        "blocking_reasons": result.blocking_reasons or [],
    }


@router.get("/tickets/{ticket_id}/gate-status")
async def get_gate_status(
    ticket_id: UUID,
    phase_id: str | None = None,
    db: DatabaseService = Depends(get_db_service),
):
    """Retrieve current gate requirement status."""
    ticket = _get_ticket_or_404(db, ticket_id)
    service = PhaseGateService(db)
    target_phase = phase_id or ticket.phase_id
    status = service.check_gate_requirements(str(ticket.id), target_phase)
    return status


@router.post("/tickets/{ticket_id}/artifacts", response_model=ArtifactResponse)
async def add_artifact(
    ticket_id: UUID,
    artifact: ArtifactCreate,
    db: DatabaseService = Depends(get_db_service),
):
    """Register a phase gate artifact manually."""
    ticket = _get_ticket_or_404(db, ticket_id)
    artifact_db = PhaseGateArtifact(
        ticket_id=str(ticket.id),
        phase_id=artifact.phase_id,
        artifact_type=artifact.artifact_type,
        artifact_path=artifact.artifact_path,
        artifact_content=artifact.artifact_content,
        collected_by=artifact.collected_by,
    )
    with db.get_session() as session:
        session.add(artifact_db)
        session.flush()
        session.refresh(artifact_db)
        session.expunge(artifact_db)
    return artifact_db


def _get_ticket_or_404(db: DatabaseService, ticket_id: UUID) -> Ticket:
    """Fetch ticket or raise 404."""
    with db.get_session() as session:
        ticket = session.get(Ticket, str(ticket_id))
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        session.expunge(ticket)
        return ticket
