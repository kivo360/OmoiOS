"""Ticket API routes."""

import asyncio
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, or_, func

from omoi_os.api.dependencies import (
    get_db_service,
    get_task_queue,
    get_phase_gate_service,
    get_event_bus_service,
    get_approval_service,
    get_ticket_dedup_service,
)
from omoi_os.services.ticket_dedup import TicketDeduplicationService
from omoi_os.models.ticket import Ticket
from omoi_os.models.ticket_status import TicketStatus
from omoi_os.models.approval_status import ApprovalStatus
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.context_service import ContextService
from omoi_os.services.ticket_workflow import (
    TicketWorkflowOrchestrator,
    InvalidTransitionError,
)
from omoi_os.services.phase_gate import PhaseGateService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.approval import ApprovalService, InvalidApprovalStateError
from omoi_os.services.reasoning_listener import log_reasoning_event


router = APIRouter()


class TicketListResponse(BaseModel):
    """Response model for ticket list."""

    tickets: list
    total: int


@router.get("/list", response_model=TicketListResponse)
@router.get("", response_model=TicketListResponse)
async def list_tickets(
    limit: int = 10,
    offset: int = 0,
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    phase_id: Optional[str] = Query(None, description="Filter by phase"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    db: DatabaseService = Depends(get_db_service),
):
    """List tickets with pagination and optional filters (async)."""
    async with db.get_async_session() as session:
        # Build base query
        stmt = select(Ticket)

        # Apply filters
        if status:
            stmt = stmt.filter(Ticket.status == status)
        if priority:
            stmt = stmt.filter(Ticket.priority == priority)
        if phase_id:
            stmt = stmt.filter(Ticket.phase_id == phase_id)
        if search:
            search_term = f"%{search}%"
            stmt = stmt.filter(
                or_(
                    Ticket.title.ilike(search_term),
                    Ticket.description.ilike(search_term),
                )
            )

        # Get total count and paginated results in parallel
        count_stmt = select(func.count()).select_from(stmt.subquery())
        paginated_stmt = stmt.order_by(Ticket.created_at.desc()).offset(offset).limit(limit)

        # Execute both queries (could be parallelized with gather if on separate sessions)
        count_result = await session.execute(count_stmt)
        total = count_result.scalar() or 0

        result = await session.execute(paginated_stmt)
        tickets = result.scalars().all()

        return TicketListResponse(
            tickets=[
                {
                    "id": str(t.id),
                    "title": t.title,
                    "description": t.description,
                    "status": t.status,
                    "priority": t.priority,
                    "phase_id": t.phase_id,
                    "project_id": t.project_id,
                    "approval_status": t.approval_status,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tickets
            ],
            total=total,
        )


class TicketCreate(BaseModel):
    """Request model for creating a ticket."""

    title: str
    description: str | None = None
    phase_id: str = "PHASE_REQUIREMENTS"
    priority: str = "MEDIUM"
    project_id: str | None = None  # Optional project association
    check_duplicates: bool = True  # Enable duplicate checking by default
    similarity_threshold: float = 0.85  # Threshold for considering duplicates
    force_create: bool = False  # Create even if duplicates found


class DuplicateCandidateResponse(BaseModel):
    """Response model for duplicate candidate."""

    ticket_id: str
    title: str
    description: str
    status: str
    similarity_score: float


class DuplicateCheckResponse(BaseModel):
    """Response when duplicates are found."""

    is_duplicate: bool
    message: str
    candidates: list[DuplicateCandidateResponse]
    highest_similarity: float


class TicketResponse(BaseModel):
    """Response model for ticket."""

    id: UUID
    title: str
    description: str | None
    phase_id: str
    status: str
    priority: str
    project_id: str | None = None
    approval_status: str | None = None

    model_config = ConfigDict(from_attributes=True)


async def _generate_embedding_background(
    ticket_id: str,
    title: str,
    description: str | None,
    dedup_service: TicketDeduplicationService,
    db: DatabaseService,
) -> None:
    """Background task to generate and store embedding for a ticket.

    Per async_python_patterns.md Section 4.3, this defers non-critical embedding
    generation to a background task to reduce user-facing latency.
    """
    from omoi_os.logging import get_logger
    logger = get_logger(__name__)

    try:
        # Generate embedding
        content = f"{title}\n{description or ''}"
        embedding = dedup_service.embedding_service.generate_embedding(content)

        if embedding:
            # Store using async session
            async with db.get_async_session() as session:
                from sqlalchemy import update
                stmt = (
                    update(Ticket)
                    .where(Ticket.id == ticket_id)
                    .values(embedding_vector=embedding)
                )
                await session.execute(stmt)
                await session.commit()
                logger.debug(f"Background embedding stored for ticket {ticket_id}")
    except Exception as e:
        logger.warning(f"Failed to generate embedding in background for ticket {ticket_id}: {e}")


@router.post("", response_model=TicketResponse | DuplicateCheckResponse)
async def create_ticket(
    ticket_data: TicketCreate,
    background_tasks: BackgroundTasks,
    requested_by_agent_id: str | None = None,
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
    approval_service: ApprovalService = Depends(get_approval_service),
    dedup_service: TicketDeduplicationService = Depends(get_ticket_dedup_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """
    Create a new ticket and enqueue initial tasks (with approval gate if enabled).

    Uses async patterns per async_python_patterns.md:
    - Async database operations for non-blocking I/O
    - Background tasks for embedding generation
    - Fire-and-forget event publishing

    Args:
        ticket_data: Ticket creation data
        background_tasks: FastAPI background tasks
        requested_by_agent_id: Optional agent ID that requested this ticket
        db: Database service
        queue: Task queue service
        approval_service: Approval service for human-in-the-loop approval
        dedup_service: Ticket deduplication service

    Returns:
        Created ticket, or DuplicateCheckResponse if duplicates found
    """
    # Check for duplicates if enabled
    embedding = None
    if ticket_data.check_duplicates and not ticket_data.force_create:
        # Dedup check (includes embedding generation)
        # Note: This is still sync because it calls external embedding service
        # TODO: Make embedding service async for full async flow
        dedup_result = dedup_service.check_duplicate(
            title=ticket_data.title,
            description=ticket_data.description,
            threshold=ticket_data.similarity_threshold,
            exclude_statuses=["done", "cancelled"],  # Don't match closed tickets
        )

        if dedup_result.is_duplicate:
            return DuplicateCheckResponse(
                is_duplicate=True,
                message=f"Found {len(dedup_result.candidates)} similar ticket(s). Set force_create=true to create anyway.",
                candidates=[
                    DuplicateCandidateResponse(
                        ticket_id=c.ticket_id,
                        title=c.title,
                        description=c.description,
                        status=c.status,
                        similarity_score=c.similarity_score,
                    )
                    for c in dedup_result.candidates
                ],
                highest_similarity=dedup_result.highest_similarity,
            )

        # Store the embedding for later use
        embedding = dedup_result.embedding

    # Use async session for ticket creation
    async with db.get_async_session() as session:
        ticket = Ticket(
            title=ticket_data.title,
            description=ticket_data.description,
            phase_id=ticket_data.phase_id or "PHASE_BACKLOG",
            status=TicketStatus.BACKLOG.value,  # Start in backlog per REQ-TKT-SM-001
            priority=ticket_data.priority,
            project_id=ticket_data.project_id,  # Associate ticket with project
        )

        # Store embedding if we generated one during dedup check
        if embedding:
            ticket.embedding_vector = embedding

        session.add(ticket)
        await session.flush()

        # Apply approval gate if enabled (REQ-THA-002, REQ-THA-003)
        # Note: approval_service still uses sync session internally
        ticket = approval_service.create_ticket_with_approval(
            ticket, requested_by_agent_id=requested_by_agent_id
        )

        # Flush to get ticket.id before emitting event
        await session.flush()
        ticket_id = str(ticket.id)

        # Defer embedding generation to background if not already done
        # Per async_python_patterns.md Section 4.3: Non-critical work in background
        if not embedding and ticket_data.check_duplicates:
            background_tasks.add_task(
                _generate_embedding_background,
                ticket_id=ticket_id,
                title=ticket_data.title,
                description=ticket_data.description,
                dedup_service=dedup_service,
                db=db,
            )

        # Emit pending event if approval is enabled (REQ-THA-010)
        if ApprovalStatus.is_pending(ticket.approval_status):
            approval_service._emit_pending_event(ticket)

        # Commit ticket FIRST so it's visible to subsequent operations
        # This is critical - enqueue_task needs to see the committed ticket
        await session.commit()
        await session.refresh(ticket)

        # Capture values needed after session context ends
        should_create_task = ApprovalStatus.can_proceed(ticket.approval_status)
        ticket_id_for_task = ticket.id
        phase_for_task = ticket_data.phase_id
        title_for_task = ticket_data.title
        priority_for_task = ticket_data.priority

        # Build response before any background work
        response = TicketResponse.model_validate(ticket)

    # Only create initial task if ticket is approved (REQ-THA-007)
    # IMPORTANT: This must happen AFTER commit so ticket is visible in new session
    if should_create_task:
        queue.enqueue_task(
            ticket_id=ticket_id_for_task,
            phase_id=phase_for_task,
            task_type="analyze_requirements",
            description=f"Analyze requirements for: {title_for_task}",
            priority=priority_for_task,
            session=None,  # Creates own session, ticket already committed
        )

    # Fire-and-forget: Log reasoning event and publish event
    # These don't need to block the response
    log_reasoning_event(
        db=db,
        entity_type="ticket",
        entity_id=ticket_id,
        event_type="ticket_created",
        title="Ticket Created",
        description=f"Created ticket: {ticket_data.title}",
        agent=requested_by_agent_id,
        details={
            "context": ticket_data.description,
            "created_by": requested_by_agent_id or "user",
            "phase": ticket_data.phase_id,
            "priority": ticket_data.priority,
        },
    )

    # Publish TICKET_CREATED event for orchestrator instant wakeup
    event_bus.publish(
        SystemEvent(
            event_type="TICKET_CREATED",
            entity_type="ticket",
            entity_id=ticket_id,
            payload={
                "title": ticket_data.title,
                "priority": ticket_data.priority,
                "phase_id": ticket_data.phase_id,
            },
        )
    )

    return response


class DuplicateCheckRequest(BaseModel):
    """Request model for duplicate check."""

    title: str
    description: str | None = None
    similarity_threshold: float = 0.85
    top_k: int = 5


@router.post("/check-duplicates", response_model=DuplicateCheckResponse)
async def check_duplicates(
    request: DuplicateCheckRequest,
    dedup_service: TicketDeduplicationService = Depends(get_ticket_dedup_service),
):
    """
    Check if a ticket with similar content already exists.

    Uses pgvector embedding similarity to find potential duplicates.
    This endpoint does not create a ticket, just checks for duplicates.

    Args:
        request: Duplicate check request with title and description
        dedup_service: Ticket deduplication service

    Returns:
        DuplicateCheckResponse with duplicate status and candidates
    """
    result = dedup_service.check_duplicate(
        title=request.title,
        description=request.description,
        threshold=request.similarity_threshold,
        top_k=request.top_k,
        exclude_statuses=["done", "cancelled"],
    )

    return DuplicateCheckResponse(
        is_duplicate=result.is_duplicate,
        message=f"Found {len(result.candidates)} similar ticket(s)"
        if result.is_duplicate
        else "No duplicates found",
        candidates=[
            DuplicateCandidateResponse(
                ticket_id=c.ticket_id,
                title=c.title,
                description=c.description,
                status=c.status,
                similarity_score=c.similarity_score,
            )
            for c in result.candidates
        ],
        highest_similarity=result.highest_similarity,
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: UUID,
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get a ticket by ID (async).

    Args:
        ticket_id: Ticket ID
        db: Database service

    Returns:
        Ticket instance
    """
    async with db.get_async_session() as session:
        result = await session.execute(
            select(Ticket).filter(Ticket.id == str(ticket_id))
        )
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return TicketResponse.model_validate(ticket)


@router.get("/{ticket_id}/context")
async def get_ticket_context(
    ticket_id: UUID,
    db: DatabaseService = Depends(get_db_service),
):
    """
    Retrieve stored aggregated context and summary for a ticket (async).
    """
    async with db.get_async_session() as session:
        result = await session.execute(
            select(Ticket).filter(Ticket.id == str(ticket_id))
        )
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        # Extract values before session closes
        context = ticket.context or {}
        summary = ticket.context_summary

    return {
        "ticket_id": str(ticket_id),
        "full_context": context,
        "summary": summary,
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


class TransitionRequest(BaseModel):
    """Request model for ticket status transition."""

    to_status: str
    reason: str | None = None
    force: bool = False


@router.post("/{ticket_id}/transition")
async def transition_ticket_status(
    ticket_id: UUID,
    request: TransitionRequest,
    db: DatabaseService = Depends(get_db_service),
    task_queue: TaskQueueService = Depends(get_task_queue),
    phase_gate: PhaseGateService = Depends(get_phase_gate_service),
    event_bus: EventBusService | None = Depends(get_event_bus_service),
):
    """
    Transition ticket to new status with state machine validation (REQ-TKT-SM-002).

    Args:
        ticket_id: Ticket ID
        request: Transition request
        db: Database service
        task_queue: Task queue service
        phase_gate: Phase gate service
        event_bus: Event bus service

    Returns:
        Updated ticket
    """
    orchestrator = TicketWorkflowOrchestrator(db, task_queue, phase_gate, event_bus)

    # Get old status for logging
    with db.get_session() as session:
        old_ticket = session.get(Ticket, ticket_id)
        old_status = old_ticket.status if old_ticket else "unknown"

    try:
        ticket = orchestrator.transition_status(
            str(ticket_id),
            request.to_status,
            initiated_by="api",
            reason=request.reason,
            force=request.force,
        )
    except InvalidTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Log reasoning event for status transition
    log_reasoning_event(
        db=db,
        entity_type="ticket",
        entity_id=str(ticket_id),
        event_type="agent_decision",
        title=f"Status Transition: {old_status} → {request.to_status}",
        description=request.reason or f"Ticket transitioned to {request.to_status}",
        details={
            "from_status": old_status,
            "to_status": request.to_status,
            "reason": request.reason,
            "forced": request.force,
        },
        decision={
            "type": "transition",
            "action": f"Move to {request.to_status}",
            "reasoning": request.reason or "Status transition requested",
        },
    )

    return TicketResponse.model_validate(ticket)


@router.post("/{ticket_id}/block")
async def block_ticket(
    ticket_id: UUID,
    blocker_type: str,
    suggested_remediation: str | None = None,
    db: DatabaseService = Depends(get_db_service),
    task_queue: TaskQueueService = Depends(get_task_queue),
    phase_gate: PhaseGateService = Depends(get_phase_gate_service),
    event_bus: EventBusService | None = Depends(get_event_bus_service),
):
    """
    Mark ticket as blocked (REQ-TKT-BL-001, REQ-TKT-BL-002).

    Args:
        ticket_id: Ticket ID
        blocker_type: Blocker classification
        suggested_remediation: Optional suggested remediation
        db: Database service
        task_queue: Task queue service
        phase_gate: Phase gate service
        event_bus: Event bus service

    Returns:
        Updated ticket
    """
    orchestrator = TicketWorkflowOrchestrator(db, task_queue, phase_gate, event_bus)
    ticket = orchestrator.mark_blocked(
        str(ticket_id),
        blocker_type,
        suggested_remediation=suggested_remediation,
        initiated_by="api",
    )

    # Log reasoning event for blocking
    log_reasoning_event(
        db=db,
        entity_type="ticket",
        entity_id=str(ticket_id),
        event_type="blocking_added",
        title=f"Ticket Blocked: {blocker_type}",
        description=f"Ticket blocked due to {blocker_type}",
        details={
            "blocker_type": blocker_type,
            "suggested_remediation": suggested_remediation,
        },
        evidence=[{"type": "blocker", "content": blocker_type}] if blocker_type else [],
    )

    return TicketResponse.model_validate(ticket)


@router.post("/{ticket_id}/unblock")
async def unblock_ticket(
    ticket_id: UUID,
    db: DatabaseService = Depends(get_db_service),
    task_queue: TaskQueueService = Depends(get_task_queue),
    phase_gate: PhaseGateService = Depends(get_phase_gate_service),
    event_bus: EventBusService | None = Depends(get_event_bus_service),
):
    """
    Unblock ticket (REQ-TKT-BL-001).

    Args:
        ticket_id: Ticket ID
        db: Database service
        task_queue: Task queue service
        phase_gate: Phase gate service
        event_bus: Event bus service

    Returns:
        Updated ticket
    """
    orchestrator = TicketWorkflowOrchestrator(db, task_queue, phase_gate, event_bus)
    ticket = orchestrator.unblock_ticket(str(ticket_id), initiated_by="api")

    # Log reasoning event for unblocking
    log_reasoning_event(
        db=db,
        entity_type="ticket",
        entity_id=str(ticket_id),
        event_type="blocking_added",  # reuse type, content distinguishes
        title="Ticket Unblocked",
        description="Blocker resolved, ticket unblocked",
        details={"action": "unblock"},
        decision={
            "type": "proceed",
            "action": "Resume work",
            "reasoning": "Blocker has been resolved",
        },
    )

    return TicketResponse.model_validate(ticket)


@router.post("/{ticket_id}/regress")
async def regress_ticket(
    ticket_id: UUID,
    to_status: str,
    validation_feedback: str | None = None,
    db: DatabaseService = Depends(get_db_service),
    task_queue: TaskQueueService = Depends(get_task_queue),
    phase_gate: PhaseGateService = Depends(get_phase_gate_service),
    event_bus: EventBusService | None = Depends(get_event_bus_service),
):
    """
    Regress ticket to previous actionable phase (REQ-TKT-SM-004).

    Args:
        ticket_id: Ticket ID
        to_status: Target status (typically BUILDING for testing regressions)
        validation_feedback: Optional validation feedback
        db: Database service
        task_queue: Task queue service
        phase_gate: Phase gate service
        event_bus: Event bus service

    Returns:
        Updated ticket
    """
    orchestrator = TicketWorkflowOrchestrator(db, task_queue, phase_gate, event_bus)
    ticket = orchestrator.regress_ticket(
        str(ticket_id),
        to_status,
        validation_feedback=validation_feedback,
        initiated_by="api",
    )
    return TicketResponse.model_validate(ticket)


@router.post("/{ticket_id}/progress")
async def progress_ticket(
    ticket_id: UUID,
    db: DatabaseService = Depends(get_db_service),
    task_queue: TaskQueueService = Depends(get_task_queue),
    phase_gate: PhaseGateService = Depends(get_phase_gate_service),
    event_bus: EventBusService | None = Depends(get_event_bus_service),
):
    """
    Automatically progress ticket to next phase if gate criteria met (REQ-TKT-SM-003).

    Args:
        ticket_id: Ticket ID
        db: Database service
        task_queue: Task queue service
        phase_gate: Phase gate service
        event_bus: Event bus service

    Returns:
        Updated ticket if progressed, None if no progression
    """
    orchestrator = TicketWorkflowOrchestrator(db, task_queue, phase_gate, event_bus)
    ticket = orchestrator.check_and_progress_ticket(str(ticket_id))
    if ticket:
        return TicketResponse.model_validate(ticket)
    return {"status": "no_progression"}


@router.post("/detect-blocking")
async def detect_blocking(
    db: DatabaseService = Depends(get_db_service),
    task_queue: TaskQueueService = Depends(get_task_queue),
    phase_gate: PhaseGateService = Depends(get_phase_gate_service),
    event_bus: EventBusService | None = Depends(get_event_bus_service),
):
    """
    Detect tickets that should be marked as blocked (REQ-TKT-BL-001).

    Args:
        db: Database service
        task_queue: Task queue service
        phase_gate: Phase gate service
        event_bus: Event bus service

    Returns:
        List of tickets that should be blocked
    """
    orchestrator = TicketWorkflowOrchestrator(db, task_queue, phase_gate, event_bus)
    results = orchestrator.detect_blocking()

    # Mark tickets as blocked
    for result in results:
        if result["should_block"]:
            orchestrator.mark_blocked(
                result["ticket_id"],
                result["blocker_type"],
                initiated_by="blocking-detector",
            )

    return {"detected": len(results), "results": results}


# Approval endpoints (REQ-THA-*)


class ApproveTicketRequest(BaseModel):
    """Request model for approving a ticket (REQ-THA-*)."""

    ticket_id: str


class ApproveTicketResponse(BaseModel):
    """Response model for approving a ticket (REQ-THA-*)."""

    ticket_id: str
    status: str  # "approved"


class RejectTicketRequest(BaseModel):
    """Request model for rejecting a ticket (REQ-THA-*)."""

    ticket_id: str
    rejection_reason: str


class RejectTicketResponse(BaseModel):
    """Response model for rejecting a ticket (REQ-THA-*)."""

    ticket_id: str
    status: str  # "rejected"


@router.post("/approve", response_model=ApproveTicketResponse)
async def approve_ticket(
    request: ApproveTicketRequest,
    approver_id: str = "api_user",  # TODO: Get from auth context
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
    approval_service: ApprovalService = Depends(get_approval_service),
):
    """
    Approve a pending ticket and create initial task (REQ-THA-*).

    Args:
        request: Approve ticket request
        approver_id: ID of the approver (human user)
        db: Database service
        queue: Task queue service
        approval_service: Approval service

    Returns:
        Approval response

    Raises:
        HTTPException: 400 if ticket is not in pending_review state, 404 if not found
    """
    try:
        ticket = approval_service.approve_ticket(request.ticket_id, approver_id)

        # Create initial task now that ticket is approved (REQ-THA-007)
        # This fixes the gap where manually approved tickets had no tasks created
        with db.get_session() as session:
            ticket_obj: Ticket | None = session.get(Ticket, request.ticket_id)
            if ticket_obj:
                queue.enqueue_task(
                    ticket_id=str(ticket_obj.id),
                    phase_id=ticket_obj.phase_id or "PHASE_REQUIREMENTS",
                    task_type="analyze_requirements",
                    description=f"Analyze requirements for: {ticket_obj.title}",
                    priority=ticket_obj.priority or "MEDIUM",
                    session=session,
                )
                session.commit()

        return ApproveTicketResponse(
            ticket_id=str(ticket.id),
            status=ticket.approval_status,
        )
    except InvalidApprovalStateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/reject", response_model=RejectTicketResponse)
async def reject_ticket(
    request: RejectTicketRequest,
    rejector_id: str = "api_user",  # TODO: Get from auth context
    approval_service: ApprovalService = Depends(get_approval_service),
):
    """
    Reject a pending ticket (REQ-THA-*).

    Args:
        request: Reject ticket request
        rejector_id: ID of the rejector (human user)
        approval_service: Approval service

    Returns:
        Rejection response

    Raises:
        HTTPException: 400 if ticket is not in pending_review state, 404 if not found
    """
    try:
        ticket = approval_service.reject_ticket(
            request.ticket_id, request.rejection_reason, rejector_id
        )
        return RejectTicketResponse(
            ticket_id=str(ticket.id),
            status=ticket.approval_status,
        )
    except InvalidApprovalStateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/pending-review-count")
async def get_pending_review_count(
    approval_service: ApprovalService = Depends(get_approval_service),
):
    """
    Get count of tickets pending approval (REQ-THA-*).

    Returns:
        Count of pending tickets
    """
    count = approval_service.get_pending_count()
    return {"pending_count": count}


@router.get("/approval-status")
async def get_approval_status(
    ticket_id: str,
    approval_service: ApprovalService = Depends(get_approval_service),
):
    """
    Get approval status for a ticket (REQ-THA-*).

    Args:
        ticket_id: Ticket ID
        approval_service: Approval service

    Returns:
        Approval status dict

    Raises:
        HTTPException: 404 if ticket not found
    """
    status = approval_service.get_approval_status(ticket_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return status
