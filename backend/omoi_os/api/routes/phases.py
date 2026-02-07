"""Phase gate and phase management API routes."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from omoi_os.api.dependencies import (
    get_current_user,
    get_db_service,
    get_phase_manager_service,
    verify_ticket_access,
)
from omoi_os.models.phase_gate_artifact import PhaseGateArtifact
from omoi_os.models.ticket import Ticket
from omoi_os.models.user import User
from omoi_os.services.database import DatabaseService
from omoi_os.services.phase_gate import PhaseGateService
from omoi_os.services.phase_manager import PhaseManager

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


# =============================================================================
# Phase Transition Routes (using unified PhaseManager)
# =============================================================================


class PhaseTransitionRequest(BaseModel):
    """Request body for phase transitions."""

    to_phase: str
    reason: Optional[str] = None
    force: bool = False
    spawn_tasks: bool = True


class PhaseTransitionResponse(BaseModel):
    """Response for phase transitions."""

    success: bool
    ticket_id: str
    from_phase: str
    to_phase: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    reason: Optional[str] = None
    artifacts_collected: int = 0
    tasks_spawned: int = 0
    blocking_reasons: List[str] = []


class PhaseInfoResponse(BaseModel):
    """Response for phase information."""

    id: str
    name: str
    description: str
    sequence_order: int
    allowed_transitions: List[str]
    mapped_status: str
    execution_mode: str
    continuous_mode: bool
    is_terminal: bool
    skippable: bool


class CheckAdvanceResponse(BaseModel):
    """Response for check and advance operation."""

    success: bool
    ticket_id: str
    advanced: bool
    from_phase: Optional[str] = None
    to_phase: Optional[str] = None
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    blocking_reasons: List[str] = []


@router.get("/configs")
async def list_phase_configs(
    phase_manager: PhaseManager = Depends(get_phase_manager_service),
) -> List[PhaseInfoResponse]:
    """
    List all phase configurations.

    Returns a list of all available phases with their configurations,
    sorted by sequence order.
    """
    phases = phase_manager.get_all_phases()
    return [
        PhaseInfoResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            sequence_order=p.sequence_order,
            allowed_transitions=list(p.allowed_transitions),
            mapped_status=p.mapped_status,
            execution_mode=p.execution_mode.value,
            continuous_mode=p.continuous_mode,
            is_terminal=p.is_terminal,
            skippable=p.skippable,
        )
        for p in phases
    ]


@router.get("/configs/{phase_id}")
async def get_phase_config(
    phase_id: str,
    phase_manager: PhaseManager = Depends(get_phase_manager_service),
) -> PhaseInfoResponse:
    """
    Get configuration for a specific phase.

    Args:
        phase_id: Phase identifier (e.g., "PHASE_IMPLEMENTATION")

    Returns:
        Phase configuration details
    """
    config = phase_manager.get_phase_config(phase_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Phase {phase_id} not found")
    return PhaseInfoResponse(
        id=config.id,
        name=config.name,
        description=config.description,
        sequence_order=config.sequence_order,
        allowed_transitions=list(config.allowed_transitions),
        mapped_status=config.mapped_status,
        execution_mode=config.execution_mode.value,
        continuous_mode=config.continuous_mode,
        is_terminal=config.is_terminal,
        skippable=config.skippable,
    )


@router.post("/tickets/{ticket_id}/phase-transition")
async def transition_phase(
    ticket_id: UUID,
    request: PhaseTransitionRequest,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    phase_manager: PhaseManager = Depends(get_phase_manager_service),
) -> PhaseTransitionResponse:
    """
    Transition a ticket to a new phase using the unified PhaseManager.

    This endpoint:
    1. Validates the transition is allowed
    2. Aggregates context from current phase
    3. Updates ticket phase and status
    4. Records phase history
    5. Spawns tasks for new phase (optional)

    Args:
        ticket_id: Ticket UUID
        request: Transition request with target phase and options

    Returns:
        PhaseTransitionResponse with transition result
    """
    # Verify user has access to this ticket
    await verify_ticket_access(str(ticket_id), current_user, db)

    result = phase_manager.transition_to_phase(
        ticket_id=str(ticket_id),
        to_phase=request.to_phase,
        initiated_by=str(current_user.id),
        reason=request.reason,
        force=request.force,
        spawn_tasks=request.spawn_tasks,
    )

    if not result.success and result.blocking_reasons:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Phase transition failed",
                "blocking_reasons": result.blocking_reasons,
            },
        )

    return PhaseTransitionResponse(
        success=result.success,
        ticket_id=str(ticket_id),
        from_phase=result.from_phase,
        to_phase=result.to_phase,
        from_status=result.from_status,
        to_status=result.to_status,
        reason=result.reason,
        artifacts_collected=result.artifacts_collected,
        tasks_spawned=result.tasks_spawned,
        blocking_reasons=result.blocking_reasons,
    )


@router.post("/tickets/{ticket_id}/check-advance")
async def check_and_advance_phase(
    ticket_id: UUID,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    phase_manager: PhaseManager = Depends(get_phase_manager_service),
) -> CheckAdvanceResponse:
    """
    Check if a ticket can advance and advance if all gate criteria are met.

    This endpoint uses PhaseManager's check_and_advance method to:
    1. Check if all tasks in current phase are complete
    2. Validate phase gate criteria
    3. Automatically advance to next phase if criteria are met

    Args:
        ticket_id: Ticket UUID to check and potentially advance

    Returns:
        CheckAdvanceResponse with result
    """
    # Verify user has access to this ticket
    await verify_ticket_access(str(ticket_id), current_user, db)

    result = phase_manager.check_and_advance(str(ticket_id))

    return CheckAdvanceResponse(
        success=result.success,
        ticket_id=str(ticket_id),
        advanced=result.success and result.from_phase != result.to_phase,
        from_phase=result.from_phase,
        to_phase=result.to_phase if result.success else None,
        from_status=result.from_status,
        to_status=result.to_status if result.success else None,
        blocking_reasons=result.blocking_reasons,
    )


@router.post("/tickets/{ticket_id}/fast-track")
async def fast_track_to_implementation(
    ticket_id: UUID,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    phase_manager: PhaseManager = Depends(get_phase_manager_service),
) -> PhaseTransitionResponse:
    """
    Fast-track a ticket directly to PHASE_IMPLEMENTATION.

    This skips requirements and design phases for tickets that don't need
    extensive planning (e.g., small fixes, well-defined tasks).

    Only works for tickets currently in PHASE_BACKLOG or PHASE_REQUIREMENTS.

    Args:
        ticket_id: Ticket UUID to fast-track
        reason: Optional reason for fast-tracking

    Returns:
        PhaseTransitionResponse with result
    """
    # Verify user has access to this ticket
    await verify_ticket_access(str(ticket_id), current_user, db)

    result = phase_manager.fast_track_to_implementation(
        ticket_id=str(ticket_id),
        initiated_by=str(current_user.id),
        reason=reason or "Fast-tracked by user",
    )

    if not result.success and result.blocking_reasons:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Fast-track failed",
                "blocking_reasons": result.blocking_reasons,
            },
        )

    return PhaseTransitionResponse(
        success=result.success,
        ticket_id=str(ticket_id),
        from_phase=result.from_phase,
        to_phase=result.to_phase,
        from_status=result.from_status,
        to_status=result.to_status,
        reason=result.reason,
        artifacts_collected=result.artifacts_collected,
        tasks_spawned=result.tasks_spawned,
        blocking_reasons=result.blocking_reasons,
    )


@router.post("/tickets/{ticket_id}/complete")
async def complete_ticket(
    ticket_id: UUID,
    reason: Optional[str] = None,
    force: bool = False,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    phase_manager: PhaseManager = Depends(get_phase_manager_service),
) -> PhaseTransitionResponse:
    """
    Move a ticket to PHASE_DONE (completed state).

    Requires all gate criteria for current phase to be met unless force=True.

    Args:
        ticket_id: Ticket UUID to complete
        reason: Optional completion reason
        force: Skip gate validation if True

    Returns:
        PhaseTransitionResponse with result
    """
    # Verify user has access to this ticket
    await verify_ticket_access(str(ticket_id), current_user, db)

    result = phase_manager.move_to_done(
        ticket_id=str(ticket_id),
        initiated_by=str(current_user.id),
        reason=reason or "Completed by user",
        force=force,
    )

    if not result.success and result.blocking_reasons:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Completion failed",
                "blocking_reasons": result.blocking_reasons,
            },
        )

    return PhaseTransitionResponse(
        success=result.success,
        ticket_id=str(ticket_id),
        from_phase=result.from_phase,
        to_phase=result.to_phase,
        from_status=result.from_status,
        to_status=result.to_status,
        reason=result.reason,
        artifacts_collected=result.artifacts_collected,
        tasks_spawned=result.tasks_spawned,
        blocking_reasons=result.blocking_reasons,
    )


@router.get("/tickets/{ticket_id}/can-transition/{to_phase}")
async def can_transition(
    ticket_id: UUID,
    to_phase: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    phase_manager: PhaseManager = Depends(get_phase_manager_service),
):
    """
    Check if a ticket can transition to a specific phase.

    Args:
        ticket_id: Ticket UUID
        to_phase: Target phase to check

    Returns:
        Dict with can_transition flag and blocking reasons if any
    """
    # Verify user has access to this ticket
    await verify_ticket_access(str(ticket_id), current_user, db)

    can, reasons = phase_manager.can_transition(str(ticket_id), to_phase)

    return {
        "ticket_id": str(ticket_id),
        "to_phase": to_phase,
        "can_transition": can,
        "blocking_reasons": reasons,
    }
