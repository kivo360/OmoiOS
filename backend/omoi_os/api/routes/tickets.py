"""Ticket API routes."""

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
    get_current_user,
    get_accessible_project_ids,
    verify_project_access,
    verify_ticket_access,
)
from omoi_os.models.user import User
from omoi_os.services.ticket_dedup import TicketDeduplicationService
from omoi_os.models.ticket import Ticket
from omoi_os.models.spec import Spec
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


# ============================================================================
# Frontend capability detection for live preview
# ============================================================================

_FRONTEND_KEYWORDS = frozenset(
    {
        "react",
        "vue",
        "next",
        "vite",
        "frontend",
        "ui",
        "web",
        "component",
        "button",
        "dashboard",
        "form",
        "tailwind",
        "css",
        "html",
        "layout",
        "responsive",
        "animation",
        "page",
        "styled",
        "svelte",
        "angular",
        "preview",
    }
)


def _detect_frontend_capabilities(title: str, description: str | None) -> list[str]:
    """Detect frontend capabilities from task text using keyword matching.

    Returns a list of matched keywords if any frontend indicators are found,
    or an empty list if none match. Used to set required_capabilities on tasks
    so the spawner can enable live preview for frontend work.
    """
    text = f"{title} {description or ''}".lower()
    found = [kw for kw in _FRONTEND_KEYWORDS if kw in text]
    return found


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
    project_id: Optional[str] = Query(None, description="Filter by project"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """
    List tickets with pagination and optional filters (async).

    Requires authentication. Only returns tickets from projects the user has access to
    (multi-tenant filtering via Project → Organization membership).
    """
    # Get user's accessible project IDs for multi-tenant filtering
    accessible_project_ids = await get_accessible_project_ids(current_user, db)

    # If user has no accessible projects, return empty
    if not accessible_project_ids:
        return TicketListResponse(tickets=[], total=0)

    async with db.get_async_session() as session:
        # Build base query - filter to accessible projects and exclude archived specs
        stmt = (
            select(Ticket)
            .outerjoin(Spec, Ticket.spec_id == Spec.id)
            .filter(Ticket.project_id.in_([str(pid) for pid in accessible_project_ids]))
            .filter(
                # Include tickets that either:
                # 1. Have no spec_id (not linked to any spec), OR
                # 2. Are linked to a spec that is NOT archived
                or_(
                    Ticket.spec_id.is_(None),
                    Spec.archived == False,  # noqa: E712
                )
            )
        )

        # Apply optional filters
        if project_id:
            # Verify user has access to the specific project they're filtering by
            if project_id not in [str(pid) for pid in accessible_project_ids]:
                raise HTTPException(
                    status_code=403, detail="You don't have access to this project"
                )
            stmt = stmt.filter(Ticket.project_id == project_id)
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
        paginated_stmt = (
            stmt.order_by(Ticket.created_at.desc()).offset(offset).limit(limit)
        )

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

    # GitHub repo info for auto-project creation when project_id is not provided
    # Format: github_owner="kivo360", github_repo="OmioOS" for repo "kivo360/OmioOS"
    github_owner: str | None = None
    github_repo: str | None = None

    # Workflow mode from frontend - determines execution behavior
    # - "quick": Direct implementation mode
    # - "spec_driven": Spec-driven development with structured output
    workflow_mode: str | None = None  # "quick" or "spec_driven"

    # Ticket dependencies for spec-driven workflows
    # Format: {"blocked_by": ["TKT-001"], "blocks": ["TKT-003"]}
    dependencies: dict | None = None


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
        logger.warning(
            f"Failed to generate embedding in background for ticket {ticket_id}: {e}"
        )


async def _trigger_spec_driven_workflow(
    db: DatabaseService,
    ticket_id: str,
    project_id: str,
    title: str,
    description: str,
    user_id: str,
) -> None:
    """Trigger spec-driven workflow for a ticket.

    This creates a Spec record and spawns the spec state machine via Daytona.
    The state machine will run through phases: explore -> requirements -> design -> tasks -> sync

    Args:
        db: Database service
        ticket_id: The ticket ID that triggered this workflow
        project_id: Project ID for the spec
        title: Title for the spec (from ticket)
        description: Description for the spec (from ticket)
        user_id: User ID who created the ticket
    """
    from omoi_os.logging import get_logger
    from omoi_os.models.spec import Spec
    from omoi_os.services.billing_service import get_billing_service
    from omoi_os.services.daytona_spawner import get_daytona_spawner
    from omoi_os.services.event_bus import get_event_bus

    logger = get_logger(__name__)

    try:
        # 1. Check billing before creating spec
        org_id = await _get_organization_id_for_project(db, project_id)
        if org_id:
            billing_service = get_billing_service(db)
            can_execute, billing_reason = billing_service.can_execute_workflow(org_id)
            if not can_execute:
                logger.warning(
                    f"Spec-driven workflow blocked by billing for ticket {ticket_id}: {billing_reason}"
                )
                return  # Silently skip - ticket is still created but spec workflow won't run

        # 2. Create the Spec record
        async with db.get_async_session() as session:
            spec = Spec(
                title=title,
                description=description,
                project_id=project_id,
                user_id=user_id,
                status="executing",
                current_phase="explore",
                spec_context={
                    "source_ticket_id": ticket_id,
                    "workflow_mode": "spec_driven",
                },
            )
            session.add(spec)
            await session.commit()
            await session.refresh(spec)
            spec_id = spec.id

        logger.info(
            f"Created spec {spec_id} from ticket {ticket_id} for spec-driven workflow"
        )

        # 3. Spawn the spec state machine
        event_bus = None
        try:
            event_bus = get_event_bus()
        except Exception:
            pass

        spawner = get_daytona_spawner(db=db, event_bus=event_bus)

        sandbox_id = await spawner.spawn_for_phase(
            spec_id=spec_id,
            phase="explore",
            project_id=project_id,
            phase_context={
                "title": title,
                "description": description,
                "source_ticket_id": ticket_id,
            },
        )

        logger.info(
            f"Spawned spec sandbox {sandbox_id} for spec {spec_id} (ticket {ticket_id})"
        )

    except Exception as e:
        logger.error(
            f"Failed to trigger spec-driven workflow for ticket {ticket_id}: {e}",
            exc_info=True,
        )
        # Don't re-raise - ticket creation should still succeed even if spec workflow fails


async def _get_organization_id_for_project(
    db: DatabaseService,
    project_id: str,
) -> str | None:
    """Get organization ID for a project."""
    from omoi_os.models.project import Project

    async with db.get_async_session() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(Project.organization_id).where(Project.id == project_id)
        )
        row = result.first()
        return str(row[0]) if row and row[0] else None


@router.post("", response_model=TicketResponse | DuplicateCheckResponse)
async def create_ticket(
    ticket_data: TicketCreate,
    background_tasks: BackgroundTasks,
    requested_by_agent_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
    approval_service: ApprovalService = Depends(get_approval_service),
    dedup_service: TicketDeduplicationService = Depends(get_ticket_dedup_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """
    Create a new ticket and enqueue initial tasks (with approval gate if enabled).

    Requires authentication. If project_id is provided, verifies user has access
    to that project (multi-tenant filtering).

    Uses async patterns per async_python_patterns.md:
    - Async database operations for non-blocking I/O
    - Background tasks for embedding generation
    - Fire-and-forget event publishing

    Args:
        ticket_data: Ticket creation data
        background_tasks: FastAPI background tasks
        requested_by_agent_id: Optional agent ID that requested this ticket
        current_user: Authenticated user
        db: Database service
        queue: Task queue service
        approval_service: Approval service for human-in-the-loop approval
        dedup_service: Ticket deduplication service

    Returns:
        Created ticket, or DuplicateCheckResponse if duplicates found
    """
    # Log incoming ticket data for debugging
    from omoi_os.logging import get_logger

    _logger = get_logger(__name__)
    _logger.info(
        f"create_ticket called: project_id={ticket_data.project_id}, "
        f"github_owner={ticket_data.github_owner}, github_repo={ticket_data.github_repo}, "
        f"user_id={current_user.id}, title={ticket_data.title[:50] if ticket_data.title else 'N/A'}..."
    )

    # If project_id provided, verify user has access
    if ticket_data.project_id:
        await verify_project_access(ticket_data.project_id, current_user, db)

    # Auto-create project if github_owner/github_repo provided but no project_id
    # This enables the "select repo, auto-create project" workflow from the frontend
    if (
        not ticket_data.project_id
        and ticket_data.github_owner
        and ticket_data.github_repo
    ):
        from omoi_os.models.project import Project
        from omoi_os.models.organization import OrganizationMembership
        from omoi_os.logging import get_logger
        from sqlalchemy import select, or_

        logger = get_logger(__name__)

        logger.info(
            f"Auto-project check: github_owner={ticket_data.github_owner}, "
            f"github_repo={ticket_data.github_repo}, user_id={current_user.id}"
        )

        async with db.get_async_session() as session:
            # Get user's organization IDs for scoped project lookup
            # This ensures we only find/create projects the user has access to
            # Query memberships within the session to avoid DetachedInstanceError
            membership_query = select(OrganizationMembership.organization_id).where(
                OrganizationMembership.user_id == current_user.id
            )
            membership_result = await session.execute(membership_query)
            user_org_ids = [row[0] for row in membership_result.fetchall()]
            logger.info(f"User org IDs for project lookup: {user_org_ids}")
            # Check if a project already exists for this repo that the user can access
            # A user can access a project if:
            # 1. They created it (created_by = user.id), OR
            # 2. It belongs to one of their organizations
            query = select(Project).where(
                Project.github_owner == ticket_data.github_owner,
                Project.github_repo == ticket_data.github_repo,
            )

            # Add user access filter
            if user_org_ids:
                query = query.where(
                    or_(
                        Project.created_by == current_user.id,
                        Project.organization_id.in_(user_org_ids),
                    )
                )
            else:
                # No org memberships - only match projects created by this user
                query = query.where(Project.created_by == current_user.id)

            existing_project = await session.execute(query)
            existing = existing_project.scalar_one_or_none()

            if existing:
                # Use existing project for this repo (that user has access to)
                ticket_data.project_id = existing.id
                logger.info(
                    f"Using existing project {existing.id} for repo "
                    f"{ticket_data.github_owner}/{ticket_data.github_repo} "
                    f"(user: {current_user.id})"
                )
            else:
                # Create new project for this repo scoped to this user
                # Get user's primary organization (if any)
                org_id = user_org_ids[0] if user_org_ids else None

                new_project = Project(
                    name=f"{ticket_data.github_owner}/{ticket_data.github_repo}",
                    description=f"Auto-created project for GitHub repository {ticket_data.github_owner}/{ticket_data.github_repo}",
                    github_owner=ticket_data.github_owner,
                    github_repo=ticket_data.github_repo,
                    github_connected=True,
                    created_by=current_user.id,
                    organization_id=org_id,
                    status="active",
                )
                session.add(new_project)
                await session.commit()
                await session.refresh(new_project)

                ticket_data.project_id = new_project.id
                logger.info(
                    f"Auto-created project {new_project.id} for repo "
                    f"{ticket_data.github_owner}/{ticket_data.github_repo} "
                    f"(user: {current_user.id}, org: {org_id})"
                )

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

    # Generate a clean title for quick mode using LLM
    # This converts user prompts like "add a button to logout" into proper titles like "Add Logout Button"
    ticket_title = ticket_data.title
    if ticket_data.workflow_mode == "quick":
        try:
            from omoi_os.services.title_generation_service import (
                get_title_generation_service,
            )

            title_service = get_title_generation_service()
            # Use description (the full prompt) as context for better title generation
            generated = await title_service.generate_title(
                task_type="implement_feature",
                description=ticket_data.description,
                context=f"User request: {ticket_data.title}",
            )
            ticket_title = generated
        except Exception as e:
            # Fallback to provided title if generation fails
            import structlog

            logger = structlog.get_logger()
            logger.warning(
                f"Failed to generate ticket title, using provided value: {e}"
            )

    # Use async session for ticket creation
    async with db.get_async_session() as session:
        # Build ticket context with workflow_mode if specified
        ticket_context = None
        if ticket_data.workflow_mode:
            ticket_context = {"workflow_mode": ticket_data.workflow_mode}

        ticket = Ticket(
            title=ticket_title,
            description=ticket_data.description,
            phase_id=ticket_data.phase_id or "PHASE_BACKLOG",
            status=TicketStatus.BACKLOG.value,  # Start in backlog per REQ-TKT-SM-001
            priority=ticket_data.priority,
            project_id=ticket_data.project_id,  # Associate ticket with project
            user_id=current_user.id,  # Associate ticket with user for filtering (UUID)
            dependencies=ticket_data.dependencies,  # Ticket-to-ticket dependencies (blocked_by/blocks)
            context=ticket_context,  # Store workflow_mode for filtering on board
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
        title_for_task = ticket.title  # Use the (potentially generated) ticket title
        priority_for_task = ticket_data.priority
        workflow_mode_for_task = ticket_data.workflow_mode

        # Build response before any background work
        response = TicketResponse.model_validate(ticket)

    # Only create initial task if ticket is approved (REQ-THA-007)
    # IMPORTANT: This must happen AFTER commit so ticket is visible in new session
    if should_create_task:
        # Check if this is spec-driven mode - triggers the spec state machine instead of regular task
        if workflow_mode_for_task == "spec_driven":
            # Spec-driven workflow: Create spec and spawn state machine
            await _trigger_spec_driven_workflow(
                db=db,
                ticket_id=ticket_id_for_task,
                project_id=ticket_data.project_id,
                title=title_for_task,
                description=ticket_data.description or "",
                user_id=current_user.id,
            )
        else:
            # Regular workflow: Create task for orchestrator
            # Quick mode tasks bypass autonomous_execution_enabled check
            # because the user explicitly requested immediate execution
            execution_config = None
            if workflow_mode_for_task == "quick":
                execution_config = {"force_execute": True}

            # Detect frontend capabilities for live preview support
            capabilities = _detect_frontend_capabilities(
                title_for_task, ticket_data.description
            )

            queue.enqueue_task(
                ticket_id=ticket_id_for_task,
                phase_id=phase_for_task,
                task_type=(
                    "implement_feature"
                    if workflow_mode_for_task == "quick"
                    else "analyze_requirements"
                ),
                description=(
                    f"Implement: {title_for_task}"
                    if workflow_mode_for_task == "quick"
                    else f"Analyze requirements for: {title_for_task}"
                ),
                priority=priority_for_task,
                session=None,  # Creates own session, ticket already committed
                execution_config=execution_config,
                required_capabilities=capabilities or None,
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
    current_user: User = Depends(get_current_user),
    dedup_service: TicketDeduplicationService = Depends(get_ticket_dedup_service),
):
    """
    Check if a ticket with similar content already exists.

    Requires authentication.
    Uses pgvector embedding similarity to find potential duplicates.
    This endpoint does not create a ticket, just checks for duplicates.

    Args:
        request: Duplicate check request with title and description
        current_user: Authenticated user
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
        message=(
            f"Found {len(result.candidates)} similar ticket(s)"
            if result.is_duplicate
            else "No duplicates found"
        ),
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
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get a ticket by ID (async).

    Requires authentication and verifies user has access to the ticket's project.

    Args:
        ticket_id: Ticket ID
        current_user: Authenticated user
        db: Database service

    Returns:
        Ticket instance
    """
    # Verify user has access to this ticket
    await verify_ticket_access(str(ticket_id), current_user, db)

    async with db.get_async_session() as session:
        result = await session.execute(
            select(Ticket).filter(Ticket.id == str(ticket_id))
        )
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return TicketResponse.model_validate(ticket)


class TicketUpdateRequest(BaseModel):
    """Request model for updating a ticket."""

    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: UUID,
    update: TicketUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Update a ticket by ID (async).

    Requires authentication and verifies user has access to the ticket's project.
    When status is updated, phase_id is automatically synced to match.

    Args:
        ticket_id: Ticket ID
        update: Fields to update
        current_user: Authenticated user
        db: Database service

    Returns:
        Updated ticket instance
    """
    from omoi_os.services.ticket_workflow import TicketWorkflowOrchestrator

    # Verify user has access to this ticket
    await verify_ticket_access(str(ticket_id), current_user, db)

    async with db.get_async_session() as session:
        result = await session.execute(
            select(Ticket).filter(Ticket.id == str(ticket_id))
        )
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        # Update only provided fields
        update_data = update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(ticket, field, value)

        # Sync phase_id when status changes to keep board column in sync
        if "status" in update_data and update_data["status"] is not None:
            new_status = update_data["status"]
            if new_status in TicketWorkflowOrchestrator.STATUS_TO_PHASE:
                ticket.phase_id = TicketWorkflowOrchestrator.STATUS_TO_PHASE[new_status]

        await session.commit()
        await session.refresh(ticket)
        return TicketResponse.model_validate(ticket)


@router.get("/{ticket_id}/context")
async def get_ticket_context(
    ticket_id: UUID,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Retrieve stored aggregated context and summary for a ticket (async).

    Requires authentication and verifies user has access to the ticket's project.
    """
    # Verify user has access to this ticket
    await verify_ticket_access(str(ticket_id), current_user, db)
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
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Aggregate phase tasks and update ticket context fields.

    Requires authentication and verifies user has access to the ticket's project.
    """
    # Verify user has access to this ticket
    await verify_ticket_access(str(ticket_id), current_user, db)

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
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    task_queue: TaskQueueService = Depends(get_task_queue),
    phase_gate: PhaseGateService = Depends(get_phase_gate_service),
    event_bus: EventBusService | None = Depends(get_event_bus_service),
):
    """
    Transition ticket to new status with state machine validation (REQ-TKT-SM-002).

    Requires authentication and verifies user has access to the ticket's project.

    Args:
        ticket_id: Ticket ID
        request: Transition request
        current_user: Authenticated user
        db: Database service
        task_queue: Task queue service
        phase_gate: Phase gate service
        event_bus: Event bus service

    Returns:
        Updated ticket
    """
    # Verify user has access to this ticket
    await verify_ticket_access(str(ticket_id), current_user, db)
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
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    task_queue: TaskQueueService = Depends(get_task_queue),
    phase_gate: PhaseGateService = Depends(get_phase_gate_service),
    event_bus: EventBusService | None = Depends(get_event_bus_service),
):
    """
    Mark ticket as blocked (REQ-TKT-BL-001, REQ-TKT-BL-002).

    Requires authentication and verifies user has access to the ticket's project.

    Args:
        ticket_id: Ticket ID
        blocker_type: Blocker classification
        suggested_remediation: Optional suggested remediation
        current_user: Authenticated user
        db: Database service
        task_queue: Task queue service
        phase_gate: Phase gate service
        event_bus: Event bus service

    Returns:
        Updated ticket
    """
    # Verify user has access to this ticket
    await verify_ticket_access(str(ticket_id), current_user, db)
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
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    task_queue: TaskQueueService = Depends(get_task_queue),
    phase_gate: PhaseGateService = Depends(get_phase_gate_service),
    event_bus: EventBusService | None = Depends(get_event_bus_service),
):
    """
    Unblock ticket (REQ-TKT-BL-001).

    Requires authentication and verifies user has access to the ticket's project.

    Args:
        ticket_id: Ticket ID
        current_user: Authenticated user
        db: Database service
        task_queue: Task queue service
        phase_gate: Phase gate service
        event_bus: Event bus service

    Returns:
        Updated ticket
    """
    # Verify user has access to this ticket
    await verify_ticket_access(str(ticket_id), current_user, db)
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
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    task_queue: TaskQueueService = Depends(get_task_queue),
    phase_gate: PhaseGateService = Depends(get_phase_gate_service),
    event_bus: EventBusService | None = Depends(get_event_bus_service),
):
    """
    Regress ticket to previous actionable phase (REQ-TKT-SM-004).

    Requires authentication and verifies user has access to the ticket's project.

    Args:
        ticket_id: Ticket ID
        to_status: Target status (typically BUILDING for testing regressions)
        validation_feedback: Optional validation feedback
        current_user: Authenticated user
        db: Database service
        task_queue: Task queue service
        phase_gate: Phase gate service
        event_bus: Event bus service

    Returns:
        Updated ticket
    """
    # Verify user has access to this ticket
    await verify_ticket_access(str(ticket_id), current_user, db)
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
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    task_queue: TaskQueueService = Depends(get_task_queue),
    phase_gate: PhaseGateService = Depends(get_phase_gate_service),
    event_bus: EventBusService | None = Depends(get_event_bus_service),
):
    """
    Automatically progress ticket to next phase if gate criteria met (REQ-TKT-SM-003).

    Requires authentication and verifies user has access to the ticket's project.

    Args:
        ticket_id: Ticket ID
        current_user: Authenticated user
        db: Database service
        task_queue: Task queue service
        phase_gate: Phase gate service
        event_bus: Event bus service

    Returns:
        Updated ticket if progressed, None if no progression
    """
    # Verify user has access to this ticket
    await verify_ticket_access(str(ticket_id), current_user, db)
    orchestrator = TicketWorkflowOrchestrator(db, task_queue, phase_gate, event_bus)
    ticket = orchestrator.check_and_progress_ticket(str(ticket_id))
    if ticket:
        return TicketResponse.model_validate(ticket)
    return {"status": "no_progression"}


@router.post("/detect-blocking")
async def detect_blocking(
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    task_queue: TaskQueueService = Depends(get_task_queue),
    phase_gate: PhaseGateService = Depends(get_phase_gate_service),
    event_bus: EventBusService | None = Depends(get_event_bus_service),
):
    """
    Detect tickets that should be marked as blocked (REQ-TKT-BL-001).

    Requires authentication.

    Args:
        current_user: Authenticated user
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
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
    approval_service: ApprovalService = Depends(get_approval_service),
):
    """
    Approve a pending ticket and create initial task (REQ-THA-*).

    Requires authentication and verifies user has access to the ticket's project.

    Args:
        request: Approve ticket request
        current_user: Authenticated user (used as approver)
        db: Database service
        queue: Task queue service
        approval_service: Approval service

    Returns:
        Approval response

    Raises:
        HTTPException: 400 if ticket is not in pending_review state, 404 if not found
    """
    # Verify user has access to this ticket
    await verify_ticket_access(request.ticket_id, current_user, db)

    # Use current user's ID as the approver
    approver_id = str(current_user.id)
    try:
        ticket = approval_service.approve_ticket(request.ticket_id, approver_id)

        # Create initial task now that ticket is approved (REQ-THA-007)
        # This fixes the gap where manually approved tickets had no tasks created
        with db.get_session() as session:
            ticket_obj: Ticket | None = session.get(Ticket, request.ticket_id)
            if ticket_obj:
                # Detect frontend capabilities for live preview support
                capabilities = _detect_frontend_capabilities(
                    ticket_obj.title or "", ticket_obj.description
                )
                queue.enqueue_task(
                    ticket_id=str(ticket_obj.id),
                    phase_id=ticket_obj.phase_id or "PHASE_REQUIREMENTS",
                    task_type="analyze_requirements",
                    description=f"Analyze requirements for: {ticket_obj.title}",
                    priority=ticket_obj.priority or "MEDIUM",
                    session=session,
                    required_capabilities=capabilities or None,
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
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    approval_service: ApprovalService = Depends(get_approval_service),
):
    """
    Reject a pending ticket (REQ-THA-*).

    Requires authentication and verifies user has access to the ticket's project.

    Args:
        request: Reject ticket request
        current_user: Authenticated user (used as rejector)
        db: Database service
        approval_service: Approval service

    Returns:
        Rejection response

    Raises:
        HTTPException: 400 if ticket is not in pending_review state, 404 if not found
    """
    # Verify user has access to this ticket
    await verify_ticket_access(request.ticket_id, current_user, db)

    # Use current user's ID as the rejector
    rejector_id = str(current_user.id)
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
    current_user: User = Depends(get_current_user),
    approval_service: ApprovalService = Depends(get_approval_service),
):
    """
    Get count of tickets pending approval (REQ-THA-*).

    Requires authentication.

    Returns:
        Count of pending tickets
    """
    # Note: This returns global count. In a proper multi-tenant implementation,
    # this should be filtered by user's accessible projects.
    count = approval_service.get_pending_count()
    return {"pending_count": count}


@router.get("/approval-status")
async def get_approval_status(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    approval_service: ApprovalService = Depends(get_approval_service),
):
    """
    Get approval status for a ticket (REQ-THA-*).

    Requires authentication and verifies user has access to the ticket's project.

    Args:
        ticket_id: Ticket ID
        current_user: Authenticated user
        db: Database service
        approval_service: Approval service

    Returns:
        Approval status dict

    Raises:
        HTTPException: 404 if ticket not found
    """
    # Verify user has access to this ticket
    await verify_ticket_access(ticket_id, current_user, db)

    status = approval_service.get_approval_status(ticket_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return status


# =============================================================================
# Phase Progression Endpoints (Hook 1 + Hook 2 manual triggers)
# =============================================================================


class PhaseCheckResponse(BaseModel):
    """Response for phase completion check."""

    ticket_id: str
    current_phase: Optional[str] = None
    current_status: Optional[str] = None
    all_phase_tasks_complete: bool
    advanced: bool
    new_phase: Optional[str] = None
    new_status: Optional[str] = None
    error: Optional[str] = None


class SpawnTasksResponse(BaseModel):
    """Response for spawning phase tasks."""

    ticket_id: str
    phase: Optional[str] = None
    tasks_spawned: int
    error: Optional[str] = None


@router.post("/{ticket_id}/check-phase-completion", response_model=PhaseCheckResponse)
async def check_phase_completion(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    task_queue: TaskQueueService = Depends(get_task_queue),
    phase_gate: PhaseGateService = Depends(get_phase_gate_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """
    Manually check and attempt phase advancement for a ticket (Hook 1 trigger).

    This endpoint checks if all tasks in the ticket's current phase are complete,
    and if so, attempts to advance the ticket to the next phase.

    Use cases:
    - Testing the automatic phase advancement logic
    - Recovery from missed events
    - Manual verification of phase status

    Args:
        ticket_id: Ticket ID to check

    Returns:
        PhaseCheckResponse with current status and advancement result
    """
    # Verify user has access to this ticket
    await verify_ticket_access(ticket_id, current_user, db)

    from omoi_os.services.phase_progression_service import get_phase_progression_service
    from omoi_os.services.ticket_workflow import TicketWorkflowOrchestrator

    try:
        # Get or create the phase progression service
        phase_progression = get_phase_progression_service(
            db=db,
            task_queue=task_queue,
            phase_gate=phase_gate,
            event_bus=event_bus,
        )

        # Ensure workflow orchestrator is set
        if phase_progression._workflow_orchestrator is None:
            workflow_orchestrator = TicketWorkflowOrchestrator(
                db=db,
                task_queue=task_queue,
                phase_gate=phase_gate,
                event_bus=event_bus,
            )
            phase_progression.set_workflow_orchestrator(workflow_orchestrator)

        result = phase_progression.check_phase_completion(ticket_id)
        return PhaseCheckResponse(**result)

    except Exception as e:
        return PhaseCheckResponse(
            ticket_id=ticket_id,
            all_phase_tasks_complete=False,
            advanced=False,
            error=str(e),
        )


@router.post("/{ticket_id}/spawn-phase-tasks", response_model=SpawnTasksResponse)
async def spawn_phase_tasks(
    ticket_id: str,
    phase_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    task_queue: TaskQueueService = Depends(get_task_queue),
    phase_gate: PhaseGateService = Depends(get_phase_gate_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """
    Manually spawn tasks for a ticket's current or specified phase (Hook 2 trigger).

    This endpoint spawns the initial tasks for a phase. If the ticket has a spec
    with pre-defined tasks, those are used; otherwise, default phase tasks are spawned.

    Use cases:
    - Testing the automatic task spawning logic
    - Recovery from missed phase transitions
    - Manual task creation for a specific phase

    Args:
        ticket_id: Ticket ID to spawn tasks for
        phase_id: Optional specific phase ID (defaults to ticket's current phase)

    Returns:
        SpawnTasksResponse with spawn result
    """
    # Verify user has access to this ticket
    await verify_ticket_access(ticket_id, current_user, db)

    from omoi_os.services.phase_progression_service import get_phase_progression_service

    try:
        # Get or create the phase progression service
        phase_progression = get_phase_progression_service(
            db=db,
            task_queue=task_queue,
            phase_gate=phase_gate,
            event_bus=event_bus,
        )

        result = phase_progression.spawn_tasks_for_phase(ticket_id, phase_id)
        return SpawnTasksResponse(**result)

    except Exception as e:
        return SpawnTasksResponse(
            ticket_id=ticket_id,
            tasks_spawned=0,
            error=str(e),
        )
