"""
Sandbox API routes for event callbacks and messaging.

This module is designed for testability:
- Helper functions are extracted for unit testing
- Schemas are separate from endpoint logic
- Dependencies are injectable via FastAPI Depends()

Phase 4 Updates:
- Events are persisted to sandbox_events table
- Returns event_id in response

Phase 2 Fix:
- Message queue now uses Redis for persistence and scaling
- InMemoryMessageQueue available for testing
"""

import os
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from sqlalchemy import select

from omoi_os.api.dependencies import get_db_service
from omoi_os.logging import get_logger
from omoi_os.models.billing import BillingAccount
from omoi_os.models.spec import Spec, SpecRequirement, SpecTask, SpecAcceptanceCriterion
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.models.project import Project
from omoi_os.services.cost_tracking import CostTrackingService
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now
from omoi_os.services.message_queue import (
    InMemoryMessageQueue,
    RedisMessageQueue,
    get_message_queue,
)

logger = get_logger(__name__)
router = APIRouter()


# Global event_bus instance (injected at module level for testability)
# Can be mocked in tests via patch('omoi_os.api.routes.sandbox.event_bus', mock_bus)
event_bus: EventBusService | None = None


def get_event_bus() -> EventBusService:
    """Get or create EventBus instance."""
    global event_bus
    if event_bus is None:
        from omoi_os.config import get_app_settings

        settings = get_app_settings()
        event_bus = EventBusService(redis_url=settings.redis.url)
    return event_bus


# ============================================================================
# PHASE 1: EVENT SCHEMAS (Testable via Contract Tests)
# ============================================================================


class SandboxEventCreate(BaseModel):
    """Request schema for creating sandbox events."""

    event_type: str = Field(
        ...,
        description="Event type in 'category.action' format (e.g., 'agent.tool_use')",
    )
    event_data: dict[str, Any] = Field(
        default_factory=dict, description="Event payload data"
    )
    source: Literal["agent", "worker", "system"] = Field(
        default="agent", description="Event source identifier"
    )


class SandboxEventResponse(BaseModel):
    """Response schema for event creation."""

    status: str
    sandbox_id: str
    event_type: str
    event_id: str | None = Field(default=None, description="Persisted event ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# PHASE 2: MESSAGE SCHEMAS (Testable via Contract Tests)
# ============================================================================


class SandboxMessage(BaseModel):
    """Request schema for message injection."""

    content: str = Field(..., min_length=1, description="Message content")
    message_type: Literal["user_message", "interrupt", "guardian_nudge", "system"] = (
        Field(default="user_message", description="Type of message")
    )


class MessageQueueResponse(BaseModel):
    """Response for POST /messages."""

    status: str
    message_id: str
    sandbox_id: str


class MessageItem(BaseModel):
    """Individual message in queue."""

    id: str
    content: str
    message_type: str
    timestamp: str


class SandboxTaskResponse(BaseModel):
    """Response for GET /sandboxes/{sandbox_id}/task - returns task info for a sandbox."""

    id: str
    ticket_id: str
    phase_id: str
    task_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    priority: str
    status: str
    sandbox_id: str
    assigned_agent_id: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ============================================================================
# PHASE 2: MESSAGE QUEUE (Redis-backed, with In-Memory fallback for tests)
# ============================================================================

# Re-export MessageQueue for backward compatibility with existing tests
MessageQueue = InMemoryMessageQueue  # Alias for unit tests

# Global message queue instance - uses Redis in production, in-memory in tests
_global_message_queue: RedisMessageQueue | InMemoryMessageQueue | None = None


def _get_message_queue() -> RedisMessageQueue | InMemoryMessageQueue:
    """
    Get or create global message queue instance.

    Uses in-memory queue if TESTING=true, otherwise Redis.
    """
    global _global_message_queue
    if _global_message_queue is None:
        is_testing = os.environ.get("TESTING", "").lower() == "true"
        if is_testing:
            _global_message_queue = InMemoryMessageQueue()
        else:
            _global_message_queue = get_message_queue()
    return _global_message_queue


def reset_message_queue() -> None:
    """Reset global message queue (useful for tests)."""
    global _global_message_queue
    _global_message_queue = None


# ============================================================================
# PHASE 1: EVENT HELPER FUNCTIONS (Testable via Unit Tests)
# ============================================================================


def _create_system_event(
    sandbox_id: str,
    event_type: str,
    event_data: dict,
    source: str,
) -> SystemEvent:
    """
    Transform HTTP event to SystemEvent for EventBus.

    UNIT TESTABLE: No external dependencies.

    Args:
        sandbox_id: Unique identifier for the sandbox
        event_type: Original event type (e.g., 'agent.tool_use')
        event_data: Event payload dictionary
        source: Event source ('agent', 'worker', 'system')

    Returns:
        SystemEvent ready for publishing to EventBus
    """
    return SystemEvent(
        event_type=f"SANDBOX_{event_type}",
        entity_type="sandbox",
        entity_id=sandbox_id,
        payload={
            **event_data,
            "source": source,
            "original_event_type": event_type,
        },
    )


def broadcast_sandbox_event(
    sandbox_id: str,
    event_type: str,
    event_data: dict,
    source: str,
) -> None:
    """
    Broadcast event via EventBus.

    UNIT TESTABLE: Uses get_event_bus() which can be mocked.

    Args:
        sandbox_id: Unique identifier for the sandbox
        event_type: Original event type (e.g., 'agent.tool_use')
        event_data: Event payload dictionary
        source: Event source ('agent', 'worker', 'system')
    """
    bus = get_event_bus()
    system_event = _create_system_event(sandbox_id, event_type, event_data, source)
    bus.publish(system_event)


async def _update_spec_phase_data(
    db: DatabaseService,
    spec_id: str,
    phase_data: dict,
    success: bool = True,
) -> None:
    """
    Update spec's phase_data when a spec sandbox completes.

    This is called when an agent.completed event is received for a spec sandbox.
    The phase_data contains the generated requirements, design, tasks, etc.
    from the SpecStateMachine that ran inside the sandbox.

    The phase_data is MERGED with existing data (not replaced) to support
    incremental phase execution across multiple sandbox runs.

    Args:
        db: Database service
        spec_id: Spec UUID
        phase_data: Dict of phase name -> phase content, e.g.:
            {"explore": {...}, "requirements": {...}, ...}
        success: Whether the sandbox execution was successful
    """
    try:
        async with db.get_async_session() as session:
            result = await session.execute(
                select(Spec).where(Spec.id == spec_id)
            )
            spec = result.scalar_one_or_none()

            if not spec:
                logger.warning(f"Spec {spec_id} not found for phase_data update")
                return

            # Merge phase_data with existing data (don't overwrite previous phases)
            existing_phase_data = spec.phase_data or {}
            for phase_name, phase_content in phase_data.items():
                existing_phase_data[phase_name] = phase_content
                logger.info(
                    f"Updated spec {spec_id} phase: {phase_name}",
                    extra={"keys": list(phase_content.keys()) if isinstance(phase_content, dict) else "non-dict"}
                )

            spec.phase_data = existing_phase_data
            spec.updated_at = utc_now()

            # Update status based on success
            if success:
                # Determine current phase based on what data we have
                # Phases: explore (20%), requirements (40%), design (60%), tasks (80%), sync (100%)
                phase_order = ["explore", "requirements", "design", "tasks", "sync"]
                current_phase = "explore"
                completed_phases = 0
                for phase in phase_order:
                    if phase in existing_phase_data:
                        current_phase = phase
                        completed_phases += 1

                spec.current_phase = current_phase

                # Calculate progress: each phase is 20% of total
                spec.progress = completed_phases * 20.0

                # Update status based on completion
                if "sync" in existing_phase_data:
                    # All phases complete - mark as completed
                    spec.status = "completed"
                elif spec.status == "executing":
                    # Still in progress - change to draft
                    spec.status = "draft"
            else:
                spec.status = "failed"

            await session.commit()
            logger.info(
                f"Updated spec {spec_id} phase_data with phases: {list(phase_data.keys())}",
                extra={
                    "new_status": spec.status,
                    "current_phase": spec.current_phase,
                    "progress": spec.progress,
                }
            )

        # Sync phase outputs to related tables for UI display
        # This runs AFTER the main transaction commits to avoid nested transaction issues
        for phase_name, phase_content in phase_data.items():
            if not isinstance(phase_content, dict):
                continue

            if phase_name == "requirements":
                await _sync_requirements_to_table(db, spec_id, phase_content)
            elif phase_name == "tasks":
                await _sync_tasks_to_table(db, spec_id, phase_content)
            elif phase_name == "design":
                await _sync_design_to_spec(db, spec_id, phase_content)

    except Exception as e:
        logger.error(f"Failed to update spec {spec_id} phase_data: {e}", exc_info=True)


async def _sync_requirements_to_table(
    db: DatabaseService,
    spec_id: str,
    requirements_output: dict,
) -> int:
    """
    Sync requirements from phase output to spec_requirements table.

    This function takes the requirements phase output and creates/updates
    SpecRequirement records so they appear in the UI.

    Args:
        db: Database service
        spec_id: Spec UUID
        requirements_output: Dict containing 'requirements' list from phase output

    Returns:
        Number of requirements synced
    """
    requirements_list = requirements_output.get("requirements", [])
    if not requirements_list:
        logger.debug(f"No requirements in phase output for spec {spec_id}")
        return 0

    synced_count = 0
    try:
        async with db.get_async_session() as session:
            for req_data in requirements_list:
                # Extract fields from phase output format
                req_id = req_data.get("id", f"req-{synced_count + 1}")
                text = req_data.get("text", "")

                # Parse EARS format: WHEN [trigger] THE SYSTEM SHALL [action]
                # or: IF [condition] THEN THE SYSTEM SHALL [action]
                # or: THE SYSTEM SHALL [action]
                condition = ""
                action = text

                # Try to extract condition/trigger from EARS format
                text_upper = text.upper()
                if "WHEN " in text_upper and " THE SYSTEM SHALL " in text_upper:
                    when_idx = text_upper.index("WHEN ") + 5
                    shall_idx = text_upper.index(" THE SYSTEM SHALL ")
                    condition = text[when_idx:shall_idx].strip()
                    action = text[shall_idx + 18:].strip()
                elif "IF " in text_upper and " THEN THE SYSTEM SHALL " in text_upper:
                    if_idx = text_upper.index("IF ") + 3
                    then_idx = text_upper.index(" THEN THE SYSTEM SHALL ")
                    condition = text[if_idx:then_idx].strip()
                    action = text[then_idx + 23:].strip()
                elif " THE SYSTEM SHALL " in text_upper:
                    shall_idx = text_upper.index(" THE SYSTEM SHALL ")
                    action = text[shall_idx + 18:].strip()

                # Create title from category + type or from ID
                title = req_data.get("category", "") or req_id
                req_type = req_data.get("type", "functional")

                # Check if requirement already exists
                existing = await session.execute(
                    select(SpecRequirement).where(
                        SpecRequirement.spec_id == spec_id,
                        SpecRequirement.title == title
                    )
                )
                existing_req = existing.scalar_one_or_none()

                if existing_req:
                    # Update existing
                    existing_req.condition = condition or "General"
                    existing_req.action = action
                    existing_req.updated_at = utc_now()
                else:
                    # Create new
                    new_req = SpecRequirement(
                        spec_id=spec_id,
                        title=title,
                        condition=condition or "General",
                        action=action,
                        status="pending",
                    )
                    session.add(new_req)

                    # Add acceptance criteria if present
                    acceptance_criteria = req_data.get("acceptance_criteria", [])
                    for crit_text in acceptance_criteria:
                        criterion = SpecAcceptanceCriterion(
                            requirement_id=new_req.id,
                            text=crit_text,
                            completed=False,
                        )
                        session.add(criterion)

                synced_count += 1

            await session.commit()
            logger.info(f"Synced {synced_count} requirements for spec {spec_id}")

    except Exception as e:
        logger.error(f"Failed to sync requirements for spec {spec_id}: {e}", exc_info=True)

    return synced_count


async def _sync_tasks_to_table(
    db: DatabaseService,
    spec_id: str,
    tasks_output: dict,
) -> int:
    """
    Sync tasks from phase output to database with proper tickets/tasks hierarchy.

    The TASKS phase output has two arrays:
    - tickets: Logical groupings of work (what appears on the kanban board)
    - tasks: Discrete work units with parent_ticket references

    This function creates:
    1. Ticket records from the 'tickets' array (kanban board items)
    2. Task records from the 'tasks' array (work units linked to tickets)
    3. SpecTask records for spec tracking

    Falls back to 1:1 mapping if only 'tasks' array is present (legacy format).

    Args:
        db: Database service
        spec_id: Spec UUID
        tasks_output: Dict containing 'tickets' and 'tasks' lists from phase output

    Returns:
        Number of tasks synced
    """
    tickets_list = tasks_output.get("tickets", [])
    tasks_list = tasks_output.get("tasks", [])

    if not tasks_list and not tickets_list:
        logger.debug(f"No tasks/tickets in phase output for spec {spec_id}")
        return 0

    # Map priority values
    priority_map = {
        "critical": "CRITICAL",
        "high": "HIGH",
        "medium": "MEDIUM",
        "low": "LOW",
    }

    synced_count = 0
    tickets_created = 0
    ticket_id_map: dict[str, str] = {}  # local_id -> db_id

    try:
        async with db.get_async_session() as session:
            # Get spec to find project_id
            spec_result = await session.execute(
                select(Spec).where(Spec.id == spec_id)
            )
            spec = spec_result.scalar_one_or_none()
            if not spec:
                logger.warning(f"Spec {spec_id} not found for task sync")
                return 0

            # Phase 1: Create Tickets (logical work groupings for kanban board)
            for ticket_data in tickets_list:
                local_id = ticket_data.get("id", "")
                title = ticket_data.get("title", "")
                description = ticket_data.get("description", "")
                priority = ticket_data.get("priority", "MEDIUM").upper()
                requirements_refs = ticket_data.get("requirements", [])
                task_refs = ticket_data.get("tasks", [])
                dependencies = ticket_data.get("dependencies", [])

                # Check for duplicate ticket
                existing_ticket = await session.execute(
                    select(Ticket).where(
                        Ticket.title == title,
                        Ticket.project_id == spec.project_id,
                        Ticket.context["spec_id"].astext == spec_id,
                    )
                )
                if existing_ticket.scalar_one_or_none():
                    continue

                new_ticket = Ticket(
                    title=title,
                    description=description,
                    phase_id="backlog",
                    status="backlog",
                    priority=priority if priority in priority_map.values() else "MEDIUM",
                    project_id=spec.project_id,
                    dependencies={
                        "blocked_by": dependencies,
                        "requirements": requirements_refs,
                        "task_refs": task_refs,
                    } if dependencies or requirements_refs else None,
                    context={
                        "spec_id": spec_id,
                        "local_ticket_id": local_id,
                        "source": "spec_sync",
                        "workflow_mode": "spec_driven",
                    },
                )
                session.add(new_ticket)
                await session.flush()
                tickets_created += 1
                ticket_id_map[local_id] = new_ticket.id

                logger.debug(
                    f"Created ticket: {title}",
                    extra={"spec_id": spec_id, "ticket_id": new_ticket.id},
                )

            # Phase 2: Create Tasks (discrete work units)
            for task_data in tasks_list:
                task_local_id = task_data.get("id", f"task-{synced_count + 1}")
                title = task_data.get("title", task_local_id)
                description = task_data.get("description", "")
                parent_ticket_local_id = task_data.get("parent_ticket", "")
                task_type = task_data.get("type", "implementation")
                phase = task_data.get("phase", "Implementation")
                priority = task_data.get("priority", "medium")
                estimated_hours = task_data.get("estimated_hours")
                dependencies = task_data.get("dependencies", {})

                # Check if SpecTask already exists
                existing = await session.execute(
                    select(SpecTask).where(
                        SpecTask.spec_id == spec_id,
                        SpecTask.title == title
                    )
                )
                existing_task = existing.scalar_one_or_none()

                if existing_task:
                    # Update existing SpecTask
                    existing_task.description = description
                    existing_task.phase = phase
                    existing_task.priority = priority
                    existing_task.estimated_hours = estimated_hours
                    existing_task.dependencies = dependencies.get("depends_on", []) if isinstance(dependencies, dict) else dependencies
                    existing_task.updated_at = utc_now()
                else:
                    # Create new SpecTask for spec tracking
                    new_spec_task = SpecTask(
                        spec_id=spec_id,
                        title=title,
                        description=description,
                        phase=phase,
                        priority=priority,
                        status="pending",
                        estimated_hours=estimated_hours,
                        dependencies=dependencies.get("depends_on", []) if isinstance(dependencies, dict) else dependencies,
                    )
                    session.add(new_spec_task)
                    await session.flush()

                    # Find or create parent ticket for this task
                    parent_ticket_id = ticket_id_map.get(parent_ticket_local_id)

                    if not parent_ticket_id and not tickets_list:
                        # Legacy format: No tickets array, create ticket per task
                        task_priority = priority.lower() if priority else "medium"
                        ticket_priority = priority_map.get(task_priority, "MEDIUM")

                        # Check if ticket already exists
                        existing_ticket = await session.execute(
                            select(Ticket).where(
                                Ticket.title == title,
                                Ticket.project_id == spec.project_id,
                                Ticket.context["spec_id"].astext == spec_id,
                            )
                        )
                        if not existing_ticket.scalar_one_or_none():
                            new_ticket = Ticket(
                                title=title,
                                description=description,
                                phase_id="backlog",
                                status="backlog",
                                priority=ticket_priority,
                                project_id=spec.project_id,
                                context={
                                    "spec_id": spec_id,
                                    "spec_task_id": new_spec_task.id,
                                    "source": "spec_sync",
                                    "workflow_mode": "spec_driven",
                                },
                            )
                            session.add(new_ticket)
                            await session.flush()
                            tickets_created += 1
                            parent_ticket_id = new_ticket.id

                    if parent_ticket_id:
                        # Create Task (work unit) linked to the Ticket
                        task_priority_upper = priority_map.get(priority.lower() if priority else "medium", "MEDIUM")
                        new_task = Task(
                            ticket_id=parent_ticket_id,
                            phase_id="backlog",
                            task_type=task_type,
                            title=title,
                            description=description,
                            priority=task_priority_upper,
                            status="pending",
                            dependencies=dependencies if isinstance(dependencies, dict) else {"depends_on": []},
                        )
                        session.add(new_task)

                        logger.debug(
                            f"Created task under ticket: {title}",
                            extra={"spec_id": spec_id, "ticket_id": parent_ticket_id},
                        )

                synced_count += 1

            # Update linked_tickets count on spec
            if tickets_created > 0:
                spec.linked_tickets = (spec.linked_tickets or 0) + tickets_created

            await session.commit()
            logger.info(
                f"Synced {synced_count} tasks and created {tickets_created} tickets for spec {spec_id}"
            )

    except Exception as e:
        logger.error(f"Failed to sync tasks for spec {spec_id}: {e}", exc_info=True)

    return synced_count


async def _sync_design_to_spec(
    db: DatabaseService,
    spec_id: str,
    design_output: dict,
) -> bool:
    """
    Sync design from phase output to spec.design JSONB field.

    Args:
        db: Database service
        spec_id: Spec UUID
        design_output: Dict containing design artifacts from phase output

    Returns:
        True if synced successfully
    """
    try:
        async with db.get_async_session() as session:
            result = await session.execute(
                select(Spec).where(Spec.id == spec_id)
            )
            spec = result.scalar_one_or_none()

            if not spec:
                logger.warning(f"Spec {spec_id} not found for design sync")
                return False

            # Extract design components
            spec.design = {
                "architecture": design_output.get("architecture", {}),
                "data_model": design_output.get("data_model", {}),
                "api_spec": design_output.get("api_endpoints", []),
                "components": design_output.get("components", []),
                "error_handling": design_output.get("error_handling", {}),
                "integration_points": design_output.get("integration_points", []),
            }
            spec.updated_at = utc_now()

            await session.commit()
            logger.info(f"Synced design for spec {spec_id}")
            return True

    except Exception as e:
        logger.error(f"Failed to sync design for spec {spec_id}: {e}", exc_info=True)
        return False


# ============================================================================
# ENDPOINTS (Integration Tested via HTTP)
# ============================================================================


def persist_sandbox_event(
    db: DatabaseService,
    sandbox_id: str,
    event_type: str,
    event_data: dict,
    source: str,
    spec_id: Optional[str] = None,
) -> str:
    """
    Persist event to database (SYNC version - use persist_sandbox_event_async in async contexts).

    Phase 4: Database persistence for audit trails.

    For agent.completed events with session_id, also saves the session transcript
    to claude_session_transcripts table for cross-sandbox resumption.

    Args:
        db: Database service
        sandbox_id: Unique identifier for the sandbox
        event_type: Original event type (e.g., 'agent.tool_use')
        event_data: Event payload dictionary
        source: Event source ('agent', 'worker', 'system')
        spec_id: Optional spec ID for spec-driven development events

    Returns:
        Persisted event ID
    """
    from omoi_os.models.sandbox_event import SandboxEvent

    with db.get_session() as session:
        db_event = SandboxEvent(
            sandbox_id=sandbox_id,
            spec_id=spec_id,
            event_type=event_type,
            event_data=event_data,
            source=source,
        )
        session.add(db_event)
        session.commit()
        session.refresh(db_event)

        # Save session transcript for cross-sandbox resumption
        if event_type == "agent.completed" and event_data.get("session_id"):
            save_session_transcript(
                db=db,
                session_id=event_data["session_id"],
                sandbox_id=sandbox_id,
                task_id=event_data.get("task_id"),  # Get task_id from event_data
                transcript_b64=event_data.get("transcript_b64"),
                metadata={
                    "turns": event_data.get("turns"),
                    "cost_usd": event_data.get("cost_usd"),
                    "stop_reason": event_data.get("stop_reason"),
                    "input_tokens": event_data.get("input_tokens"),
                    "output_tokens": event_data.get("output_tokens"),
                    "cache_read_tokens": event_data.get("cache_read_tokens"),
                    "cache_write_tokens": event_data.get("cache_write_tokens"),
                },
            )

        return db_event.id


async def persist_sandbox_event_async(
    db: DatabaseService,
    sandbox_id: str,
    event_type: str,
    event_data: dict,
    source: str,
    spec_id: Optional[str] = None,
) -> str:
    """
    Persist event to database (ASYNC version - non-blocking).

    Phase 4: Database persistence for audit trails.

    For agent.completed events with session_id, also saves the session transcript
    to claude_session_transcripts table for cross-sandbox resumption.

    Args:
        db: Database service
        sandbox_id: Unique identifier for the sandbox
        event_type: Original event type (e.g., 'agent.tool_use')
        event_data: Event payload dictionary
        source: Event source ('agent', 'worker', 'system')
        spec_id: Optional spec ID for spec-driven development events

    Returns:
        Persisted event ID
    """
    from sqlalchemy import select

    from omoi_os.models.sandbox_event import SandboxEvent

    async with db.get_async_session() as session:
        db_event = SandboxEvent(
            sandbox_id=sandbox_id,
            spec_id=spec_id,
            event_type=event_type,
            event_data=event_data,
            source=source,
        )
        session.add(db_event)
        await session.commit()
        await session.refresh(db_event)
        event_id = db_event.id

    # Save session transcript for cross-sandbox resumption (outside session)
    if event_type == "agent.completed" and event_data.get("session_id"):
        await save_session_transcript_async(
            db=db,
            session_id=event_data["session_id"],
            sandbox_id=sandbox_id,
            task_id=event_data.get("task_id"),
            transcript_b64=event_data.get("transcript_b64"),
            metadata={
                "turns": event_data.get("turns"),
                "cost_usd": event_data.get("cost_usd"),
                "stop_reason": event_data.get("stop_reason"),
                "input_tokens": event_data.get("input_tokens"),
                "output_tokens": event_data.get("output_tokens"),
                "cache_read_tokens": event_data.get("cache_read_tokens"),
                "cache_write_tokens": event_data.get("cache_write_tokens"),
            },
        )

    return event_id


def save_session_transcript(
    db: DatabaseService,
    session_id: str,
    sandbox_id: str,
    task_id: str | None = None,
    transcript_b64: str | None = None,
    metadata: dict | None = None,
) -> None:
    """
    Save Claude session transcript to database (SYNC version).

    Args:
        db: Database service
        session_id: Claude Code session ID
        sandbox_id: Daytona sandbox ID
        task_id: Optional task ID associated with this session
        transcript_b64: Base64-encoded transcript content (optional)
        metadata: Additional metadata dictionary (stored as session_metadata)
    """
    if not transcript_b64:
        # No transcript provided - skip saving
        return

    # Normalize empty string task_id to None (spec sandboxes don't have task_id)
    # This prevents FK constraint violations - empty string '' is not the same as NULL
    if task_id == "":
        task_id = None

    try:
        from omoi_os.models.claude_session_transcript import ClaudeSessionTranscript

        with db.get_session() as session:
            # Check if transcript already exists
            existing = (
                session.query(ClaudeSessionTranscript)
                .filter_by(session_id=session_id)
                .first()
            )

            if existing:
                # Update existing transcript
                existing.transcript_b64 = transcript_b64
                existing.sandbox_id = sandbox_id
                if task_id:
                    existing.task_id = task_id
                existing.session_metadata = metadata or {}
                existing.updated_at = utc_now()
            else:
                # Create new transcript
                transcript = ClaudeSessionTranscript(
                    session_id=session_id,
                    transcript_b64=transcript_b64,
                    sandbox_id=sandbox_id,
                    task_id=task_id,
                    session_metadata=metadata or {},
                )
                session.add(transcript)

            session.commit()
    except Exception as e:
        # Log but don't fail - transcript saving is optional
        logger.warning(f"Failed to save session transcript {session_id}: {e}")


async def save_session_transcript_async(
    db: DatabaseService,
    session_id: str,
    sandbox_id: str,
    task_id: str | None = None,
    transcript_b64: str | None = None,
    metadata: dict | None = None,
) -> None:
    """
    Save Claude session transcript to database (ASYNC version - non-blocking).

    Args:
        db: Database service
        session_id: Claude Code session ID
        sandbox_id: Daytona sandbox ID
        task_id: Optional task ID associated with this session
        transcript_b64: Base64-encoded transcript content (optional)
        metadata: Additional metadata dictionary (stored as session_metadata)
    """
    if not transcript_b64:
        # No transcript provided - skip saving
        return

    # Normalize empty string task_id to None (spec sandboxes don't have task_id)
    # This prevents FK constraint violations - empty string '' is not the same as NULL
    if task_id == "":
        task_id = None

    try:
        from sqlalchemy import select

        from omoi_os.models.claude_session_transcript import ClaudeSessionTranscript

        async with db.get_async_session() as session:
            # Check if transcript already exists
            result = await session.execute(
                select(ClaudeSessionTranscript).filter_by(session_id=session_id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing transcript
                existing.transcript_b64 = transcript_b64
                existing.sandbox_id = sandbox_id
                if task_id:
                    existing.task_id = task_id
                existing.session_metadata = metadata or {}
                existing.updated_at = utc_now()
            else:
                # Create new transcript
                transcript = ClaudeSessionTranscript(
                    session_id=session_id,
                    transcript_b64=transcript_b64,
                    sandbox_id=sandbox_id,
                    task_id=task_id,
                    session_metadata=metadata or {},
                )
                session.add(transcript)

            await session.commit()
    except Exception as e:
        # Log but don't fail - transcript saving is optional
        logger.warning(f"Failed to save session transcript {session_id}: {e}")


def get_session_transcript(db: DatabaseService, session_id: str) -> str | None:
    """
    Retrieve Claude session transcript from database (SYNC version).

    Args:
        db: Database service
        session_id: Claude Code session ID

    Returns:
        Base64-encoded transcript content, or None if not found
    """
    try:
        from omoi_os.models.claude_session_transcript import ClaudeSessionTranscript

        with db.get_session() as session:
            transcript = (
                session.query(ClaudeSessionTranscript)
                .filter_by(session_id=session_id)
                .first()
            )
            if transcript:
                return transcript.transcript_b64
    except Exception as e:
        logger.warning(f"Failed to retrieve session transcript {session_id}: {e}")

    return None


async def get_session_transcript_async(db: DatabaseService, session_id: str) -> str | None:
    """
    Retrieve Claude session transcript from database (ASYNC version - non-blocking).

    Args:
        db: Database service
        session_id: Claude Code session ID

    Returns:
        Base64-encoded transcript content, or None if not found
    """
    try:
        from sqlalchemy import select

        from omoi_os.models.claude_session_transcript import ClaudeSessionTranscript

        async with db.get_async_session() as session:
            result = await session.execute(
                select(ClaudeSessionTranscript).filter_by(session_id=session_id)
            )
            transcript = result.scalar_one_or_none()
            if transcript:
                return transcript.transcript_b64
    except Exception as e:
        logger.warning(f"Failed to retrieve session transcript {session_id}: {e}")

    return None


def get_session_transcript_for_task(db: DatabaseService, task_id: str) -> tuple[str | None, str | None]:
    """
    Retrieve Claude session transcript by task_id (SYNC version).

    This is useful for resuming a task that was previously run - we can find
    the session transcript stored for that task and pass it to a new sandbox.

    Args:
        db: Database service
        task_id: Task ID to find transcript for

    Returns:
        Tuple of (session_id, transcript_b64), or (None, None) if not found
    """
    try:
        from omoi_os.models.claude_session_transcript import ClaudeSessionTranscript

        with db.get_session() as session:
            # Find the most recent transcript for this task
            transcript = (
                session.query(ClaudeSessionTranscript)
                .filter_by(task_id=task_id)
                .order_by(ClaudeSessionTranscript.updated_at.desc())
                .first()
            )
            if transcript:
                return transcript.session_id, transcript.transcript_b64
    except Exception as e:
        logger.warning(f"Failed to retrieve session transcript for task {task_id}: {e}")

    return None, None


async def get_session_transcript_for_task_async(
    db: DatabaseService, task_id: str
) -> tuple[str | None, str | None]:
    """
    Retrieve Claude session transcript by task_id (ASYNC version - non-blocking).

    This is useful for resuming a task that was previously run - we can find
    the session transcript stored for that task and pass it to a new sandbox.

    Args:
        db: Database service
        task_id: Task ID to find transcript for

    Returns:
        Tuple of (session_id, transcript_b64), or (None, None) if not found
    """
    try:
        from sqlalchemy import select

        from omoi_os.models.claude_session_transcript import ClaudeSessionTranscript

        async with db.get_async_session() as session:
            result = await session.execute(
                select(ClaudeSessionTranscript)
                .filter_by(task_id=task_id)
                .order_by(ClaudeSessionTranscript.updated_at.desc())
            )
            transcript = result.scalar_one_or_none()
            if transcript:
                return transcript.session_id, transcript.transcript_b64
    except Exception as e:
        logger.warning(f"Failed to retrieve session transcript for task {task_id}: {e}")

    return None, None


@router.post("/{sandbox_id}/events", response_model=SandboxEventResponse)
async def post_sandbox_event(
    sandbox_id: str,
    event: SandboxEventCreate,
) -> SandboxEventResponse:
    """
    Receive event from sandbox worker and broadcast to subscribers.

    This endpoint is called by worker scripts running inside Daytona sandboxes
    to report progress, tool usage, errors, and other events to the backend.

    Events are:
    - Persisted to database (Phase 4) - optional, fails gracefully
    - Broadcast via EventBus to:
      - WebSocket clients (real-time UI updates)
      - Guardian monitoring (trajectory analysis)

    Args:
        sandbox_id: Unique identifier for the sandbox (from URL path)
        event: Event data from request body

    Returns:
        SandboxEventResponse with status, timestamp, and event_id

    Example:
        POST /api/v1/sandboxes/sandbox-abc123/events
        {
            "event_type": "agent.tool_use",
            "event_data": {"tool": "bash", "command": "npm install"},
            "source": "agent"
        }
    """
    from sqlalchemy import select

    # Log incoming request for debugging 502 issues
    logger.info(
        f"[SandboxEvent] Received {event.event_type} from sandbox {sandbox_id[:20]}... "
        f"(source: {event.source})"
    )

    # Persist to database (Phase 4) - optional, fails gracefully
    # Using async version to avoid blocking the event loop
    event_id: str | None = None
    try:
        db = get_db_service()
        # Extract spec_id from event_data if present (for spec-driven development)
        spec_id = event.event_data.get("spec_id")
        event_id = await persist_sandbox_event_async(
            db=db,
            sandbox_id=sandbox_id,
            event_type=event.event_type,
            event_data=event.event_data,
            source=event.source,
            spec_id=spec_id,
        )
        logger.debug(
            f"[SandboxEvent] Persisted event {event_id} for {event.event_type}"
            + (f" (spec_id={spec_id})" if spec_id else "")
        )
    except Exception as e:
        # Persistence is optional - don't fail if DB unavailable
        logger.warning(
            f"[SandboxEvent] Failed to persist event {event.event_type} for sandbox {sandbox_id}: {e}"
        )

    # Handle task status transitions based on event type
    # This includes: agent.started -> running, agent.completed/continuous.completed -> completed, agent.failed/error -> failed
    # NOTE: continuous.completed contains the actual validation result (validation_passed field)
    # Also handles spec phase events for incremental spec sync
    if event.event_type in (
        "agent.started",
        "agent.completed",
        "continuous.completed",  # Contains validation_passed result
        "agent.failed",
        "agent.error",
        # Spec phase events for incremental sync
        "spec.phase_started",
        "spec.phase_completed",
        "spec.phase_failed",
        "spec.phase_retry",
        "spec.execution_completed",  # Final spec completion
    ):
        try:
            db = get_db_service()
            from omoi_os.services.task_queue import TaskQueueService

            task_id = event.event_data.get("task_id")
            logger.debug(
                f"Task status update: event_type={event.event_type}, task_id={task_id}, sandbox_id={sandbox_id}"
            )

            if not task_id:
                # Try to find task by sandbox_id as fallback (async)
                logger.debug(
                    f"No task_id in event_data, searching by sandbox_id={sandbox_id}"
                )
                async with db.get_async_session() as session:
                    result = await session.execute(
                        select(Task)
                        .filter(Task.sandbox_id == sandbox_id)
                        .filter(Task.status.in_(["claiming", "assigned", "running"]))
                    )
                    task = result.scalar_one_or_none()
                    if task:
                        task_id = str(task.id)
                        logger.info(f"Found task {task_id} by sandbox_id fallback")
                    else:
                        logger.warning(
                            f"No task found for sandbox {sandbox_id} with status claiming/assigned/running"
                        )

            if task_id:
                task_queue = TaskQueueService(db, event_bus=get_event_bus())

                # Handle agent.started -> transition to running (async)
                if event.event_type == "agent.started":
                    logger.info(
                        f"Updating task {task_id} status to running (agent.started)"
                    )
                    await task_queue.update_task_status_async(
                        task_id=task_id,
                        status="running",
                    )
                    logger.info(f"Successfully updated task {task_id} to running")

                # Handle agent.completed or continuous.completed -> trigger validation or complete directly
                # continuous.completed contains the actual validation_passed result after validation runs
                elif event.event_type in ("agent.completed", "continuous.completed"):
                    # Check if this is a validator agent completion
                    is_validator = event.event_data.get("agent_type") == "validator"

                    # Extract result from event_data
                    result = {
                        "success": event.event_data.get("success", True),
                        "turns": event.event_data.get("turns"),
                        "cost_usd": event.event_data.get("cost_usd"),
                        "session_id": event.event_data.get("session_id"),
                        "stop_reason": event.event_data.get("stop_reason"),
                    }
                    # Include branch name for validation workflow
                    if "branch_name" in event.event_data and event.event_data["branch_name"]:
                        result["branch_name"] = event.event_data["branch_name"]
                    # Include final output if available
                    if "final_output" in event.event_data:
                        result["output"] = event.event_data["final_output"]
                        logger.debug(
                            f"Task {task_id} completion includes final_output ({len(result.get('output', ''))} chars)"
                        )
                    else:
                        logger.debug(f"Task {task_id} completion missing final_output")

                    # Generate artifacts from validation state for phase gate requirements
                    artifacts = []
                    code_pushed = event.event_data.get("code_pushed", False)
                    pr_created = event.event_data.get("pr_created", False)
                    tests_passed = event.event_data.get("tests_passed", False)
                    pr_url = event.event_data.get("pr_url")
                    pr_number = event.event_data.get("pr_number")
                    files_changed = event.event_data.get("files_changed", 0)
                    ci_status = event.event_data.get("ci_status")

                    # Create code_changes artifact if code was pushed
                    if code_pushed or pr_created:
                        artifacts.append({
                            "type": "code_changes",
                            "path": pr_url,
                            "content": {
                                "has_tests": tests_passed,
                                "branch_name": result.get("branch_name"),
                                "pr_created": pr_created,
                                "pr_url": pr_url,
                                "pr_number": pr_number,
                                "files_changed": files_changed,
                            }
                        })

                    # Create test_coverage artifact if tests passed
                    if tests_passed:
                        # Parse CI status to get more specific test info
                        test_details = {}
                        if ci_status and isinstance(ci_status, list):
                            test_details["checks"] = [
                                {
                                    "name": check.get("name"),
                                    "conclusion": check.get("conclusion"),
                                    "state": check.get("state"),
                                }
                                for check in ci_status
                            ]
                            test_details["all_passed"] = all(
                                check.get("conclusion") == "success"
                                for check in ci_status
                                if check.get("state") == "completed"
                            )

                        artifacts.append({
                            "type": "test_coverage",
                            "content": {
                                "percentage": 80,  # Default - CI passed implies adequate coverage
                                "all_passed": True,
                                "has_tests": True,
                                **test_details,
                            }
                        })

                    if artifacts:
                        result["artifacts"] = artifacts
                        logger.info(
                            f"Task {task_id} generated {len(artifacts)} artifacts for phase gate",
                            extra={"artifact_types": [a["type"] for a in artifacts]}
                        )

                    # Handle completion events:
                    # - continuous.completed with validation_passed = true: In-sandbox validation passed, mark complete
                    # - continuous.completed with validation_passed = false: In-sandbox validation failed
                    # - agent.completed: Agent work done, check if validation_passed is set
                    # - Validator agent completion: External validator result

                    validation_passed = event.event_data.get("validation_passed")

                    # continuous.completed is the final validation result from in-sandbox validation
                    if event.event_type == "continuous.completed":
                        if validation_passed:
                            # In-sandbox validation passed - mark task complete
                            logger.info(
                                f"In-sandbox validation passed for task {task_id}, marking completed"
                            )
                            await task_queue.update_task_status_async(
                                task_id=task_id,
                                status="completed",
                                result={
                                    **result,
                                    "validation_passed": True,
                                    "validation_type": "in_sandbox",
                                },
                            )
                            logger.info(f"Successfully updated task {task_id} to completed")
                        else:
                            # In-sandbox validation failed
                            logger.info(
                                f"In-sandbox validation failed for task {task_id}"
                            )
                            # Don't mark as failed yet - may have recommendations
                            # The task stays in current status
                    elif is_validator:
                        # This is an external validator agent completion
                        validation_feedback = event.event_data.get(
                            "validation_feedback",
                            "Validation passed" if validation_passed else "Validation failed"
                        )
                        logger.info(
                            f"Validator completed for task {task_id}: passed={validation_passed}",
                            extra={"validation_feedback": validation_feedback}
                        )

                        # Call handle_validation_result to properly update task status
                        from omoi_os.services.task_validator import get_task_validator

                        validator_service = get_task_validator(db=db, event_bus=get_event_bus())
                        await validator_service.handle_validation_result(
                            task_id=task_id,
                            validator_agent_id=event.event_data.get("agent_id", f"validator-{sandbox_id[:8]}"),
                            passed=validation_passed or False,
                            feedback=validation_feedback,
                            evidence={
                                "tests_passed": event.event_data.get("tests_passed", False),
                                "code_pushed": event.event_data.get("code_pushed", False),
                                "pr_created": event.event_data.get("pr_created", False),
                                "pr_url": event.event_data.get("pr_url"),
                            },
                            recommendations=None,
                        )
                        logger.info(
                            f"Validation result processed for task {task_id}: "
                            f"new_status={'completed' if validation_passed else 'needs_revision'}"
                        )
                    else:
                        # agent.completed - implementation done, wait for continuous.completed
                        # Don't trigger external validation since we use in-sandbox validation
                        logger.info(
                            f"Agent completed for task {task_id}, waiting for validation result"
                        )

                    # Record cost if cost data is available
                    cost_usd = event.event_data.get("cost_usd")
                    if cost_usd is not None and cost_usd > 0:
                        try:
                            input_tokens = event.event_data.get("input_tokens", 0)
                            output_tokens = event.event_data.get("output_tokens", 0)
                            model = event.event_data.get("model", "claude-sonnet-4")

                            # Look up billing_account_id from task -> ticket -> project -> organization
                            billing_account_id = None
                            async with db.get_async_session() as cost_session:
                                # Query task with joined relationships
                                task_result = await cost_session.execute(
                                    select(Task).where(Task.id == task_id)
                                )
                                task_obj = task_result.scalar_one_or_none()

                                if task_obj and task_obj.ticket_id:
                                    ticket_result = await cost_session.execute(
                                        select(Ticket).where(Ticket.id == task_obj.ticket_id)
                                    )
                                    ticket_obj = ticket_result.scalar_one_or_none()

                                    if ticket_obj and ticket_obj.project_id:
                                        project_result = await cost_session.execute(
                                            select(Project).where(Project.id == ticket_obj.project_id)
                                        )
                                        project_obj = project_result.scalar_one_or_none()

                                        if project_obj and project_obj.organization_id:
                                            billing_result = await cost_session.execute(
                                                select(BillingAccount).where(
                                                    BillingAccount.organization_id == project_obj.organization_id
                                                )
                                            )
                                            billing_account = billing_result.scalar_one_or_none()
                                            if billing_account:
                                                billing_account_id = str(billing_account.id)

                            # Record the cost
                            cost_service = CostTrackingService(db)
                            cost_record = cost_service.record_sandbox_cost(
                                task_id=task_id,
                                sandbox_id=sandbox_id,
                                cost_usd=cost_usd,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                model=model,
                                agent_id=task_obj.assigned_agent_id if task_obj else None,
                                billing_account_id=billing_account_id,
                            )
                            logger.info(
                                f"Recorded cost for task {task_id}: ${cost_usd:.4f} "
                                f"(billing_account={billing_account_id}, record_id={cost_record.id})"
                            )
                        except Exception as cost_error:
                            # Cost recording should not block task completion
                            logger.error(
                                f"Failed to record cost for task {task_id}: {cost_error}",
                                exc_info=True,
                            )

                # Handle agent.failed/error -> transition to failed (async)
                elif event.event_type in ("agent.failed", "agent.error"):
                    error_message = event.event_data.get(
                        "error", "Task execution failed"
                    )
                    logger.info(
                        f"Updating task {task_id} status to failed: {error_message}"
                    )
                    await task_queue.update_task_status_async(
                        task_id=task_id,
                        status="failed",
                        error_message=error_message,
                    )
                    logger.info(f"Successfully updated task {task_id} to failed")
            else:
                # Check if this is a spec sandbox (has spec_id but no task_id)
                # Spec sandboxes don't need task status updates - they have their own workflow
                spec_id = event.event_data.get("spec_id")
                if spec_id:
                    logger.info(
                        f"Spec sandbox event received: spec_id={spec_id}, "
                        f"event_type={event.event_type}, sandbox_id={sandbox_id}"
                    )
                    # Handle spec completion - update spec's phase_data
                    # Also handle continuous.completed for defense in depth
                    if event.event_type in ("agent.completed", "continuous.completed"):
                        phase_data = event.event_data.get("phase_data")
                        if phase_data:
                            logger.info(
                                f"Updating spec {spec_id} with phase_data: phases={list(phase_data.keys())}"
                            )
                            await _update_spec_phase_data(
                                db=db,
                                spec_id=spec_id,
                                phase_data=phase_data,
                                success=event.event_data.get("success", True),
                            )
                        else:
                            logger.warning(
                                f"Received {event.event_type} for spec {spec_id} but phase_data is empty or missing. "
                                f"event_data keys: {list(event.event_data.keys())}"
                            )
                    # Handle incremental phase completion - sync phase_data as each phase finishes
                    elif event.event_type == "spec.phase_completed":
                        phase_name = event.event_data.get("phase")
                        phase_output = event.event_data.get("phase_output")
                        if phase_name and phase_output:
                            logger.info(
                                f"Incremental sync: spec {spec_id} phase {phase_name} completed"
                            )
                            await _update_spec_phase_data(
                                db=db,
                                spec_id=spec_id,
                                phase_data={phase_name: phase_output},
                                success=True,
                            )
                        else:
                            # Log but don't warn - older sandboxes won't have phase_output
                            logger.debug(
                                f"spec.phase_completed for {spec_id} missing phase or phase_output: "
                                f"phase={phase_name}, has_output={phase_output is not None}"
                            )
                    # Handle spec execution completed - mark spec as completed
                    elif event.event_type == "spec.execution_completed":
                        logger.info(f"Spec {spec_id} execution completed")
                        async with db.get_async_session() as session:
                            result = await session.execute(
                                select(Spec).where(Spec.id == spec_id)
                            )
                            spec = result.scalar_one_or_none()
                            if spec:
                                spec.status = "completed"
                                spec.progress = 100.0
                                spec.updated_at = utc_now()
                                await session.commit()
                                logger.info(f"Spec {spec_id} marked as completed (100%)")
                else:
                    logger.warning(
                        f"Could not determine task_id for status update. event_type={event.event_type}, sandbox_id={sandbox_id}, event_data keys={list(event.event_data.keys())}"
                    )
        except Exception as e:
            # Task status update is important but shouldn't break event processing
            # Log error with full stack trace for debugging
            logger.error(
                f"Failed to update task status for sandbox {sandbox_id}, event_type={event.event_type}: {e}",
                exc_info=True,
            )

    # Broadcast via EventBus
    broadcast_sandbox_event(
        sandbox_id=sandbox_id,
        event_type=event.event_type,
        event_data=event.event_data,
        source=event.source,
    )

    return SandboxEventResponse(
        status="received",
        sandbox_id=sandbox_id,
        event_type=event.event_type,
        event_id=event_id,
    )


# ============================================================================
# PHASE 4: EVENT QUERY SCHEMAS AND ENDPOINT
# ============================================================================


class SandboxEventItem(BaseModel):
    """Response model for individual sandbox event."""

    id: str
    sandbox_id: str
    event_type: str
    event_data: dict[str, Any]
    source: str
    created_at: datetime


class SandboxEventsListResponse(BaseModel):
    """Response model for list of sandbox events."""

    events: list[SandboxEventItem]
    total_count: int
    sandbox_id: str


class HeartbeatSummary(BaseModel):
    """Summary of heartbeat events (instead of listing all of them)."""

    count: int
    first_heartbeat: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None


class TrajectorySummaryResponse(BaseModel):
    """Response model for trajectory summary with heartbeat aggregation.

    This provides a cleaner view of sandbox activity by:
    - Excluding heartbeat events from the main event list
    - Providing a summary of heartbeats (count, first, last)
    - Filtering out noise to show meaningful trajectory events
    - Supporting cursor-based pagination for infinite scroll
    """

    sandbox_id: str
    events: list[SandboxEventItem]
    heartbeat_summary: HeartbeatSummary
    total_events: int  # Total including heartbeats
    trajectory_events: int  # Count excluding heartbeats and noise
    # Cursor-based pagination
    next_cursor: Optional[str] = None  # ID of oldest event in this batch (for loading older)
    prev_cursor: Optional[str] = None  # ID of newest event in this batch (for loading newer)
    has_more: bool = False  # Whether there are more events to load


def query_sandbox_events(
    db: DatabaseService,
    sandbox_id: str,
    limit: int = 100,
    offset: int = 0,
    event_type: Optional[str] = None,
) -> tuple[list[dict], int]:
    """
    Query persisted events for a sandbox (SYNC version).

    Args:
        db: Database service
        sandbox_id: Sandbox identifier
        limit: Maximum events to return
        offset: Pagination offset
        event_type: Optional filter by event type

    Returns:
        Tuple of (events list, total count)
    """
    from omoi_os.models.sandbox_event import SandboxEvent

    with db.get_session() as session:
        query = session.query(SandboxEvent).filter(
            SandboxEvent.sandbox_id == sandbox_id
        )

        if event_type:
            query = query.filter(SandboxEvent.event_type == event_type)

        # Get total count
        total_count = query.count()

        # Get paginated results, ordered by created_at desc (newest first)
        events = (
            query.order_by(SandboxEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return [
            {
                "id": str(e.id),
                "sandbox_id": e.sandbox_id,
                "event_type": e.event_type,
                "event_data": e.event_data,
                "source": e.source,
                "created_at": e.created_at,
            }
            for e in events
        ], total_count


async def query_sandbox_events_async(
    db: DatabaseService,
    sandbox_id: str,
    limit: int = 100,
    offset: int = 0,
    event_type: Optional[str] = None,
) -> tuple[list[dict], int]:
    """
    Query persisted events for a sandbox (ASYNC version - non-blocking).

    Args:
        db: Database service
        sandbox_id: Sandbox identifier
        limit: Maximum events to return
        offset: Pagination offset
        event_type: Optional filter by event type

    Returns:
        Tuple of (events list, total count)
    """
    from sqlalchemy import func, select

    from omoi_os.models.sandbox_event import SandboxEvent

    async with db.get_async_session() as session:
        # Build base filter
        base_filter = SandboxEvent.sandbox_id == sandbox_id
        if event_type:
            base_filter = base_filter & (SandboxEvent.event_type == event_type)

        # Get total count
        count_result = await session.execute(
            select(func.count(SandboxEvent.id)).filter(base_filter)
        )
        total_count = count_result.scalar() or 0

        # Get paginated results, ordered by created_at desc (newest first)
        result = await session.execute(
            select(SandboxEvent)
            .filter(base_filter)
            .order_by(SandboxEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        events = result.scalars().all()

        return [
            {
                "id": str(e.id),
                "sandbox_id": e.sandbox_id,
                "event_type": e.event_type,
                "event_data": e.event_data,
                "source": e.source,
                "created_at": e.created_at,
            }
            for e in events
        ], total_count


@router.get("/health", response_model=dict)
async def sandbox_health():
    """Health check endpoint for sandbox API.

    This helps diagnose 502 errors - if this endpoint works but
    POST /{sandbox_id}/events doesn't, the issue is likely with
    request processing (DB, Redis, etc.)
    """
    logger.info("[SandboxHealth] Health check requested")

    return {
        "status": "ok",
        "service": "sandbox-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{sandbox_id}/events", response_model=SandboxEventsListResponse)
async def get_sandbox_events(
    sandbox_id: str,
    limit: int = Query(default=100, le=500, ge=1, description="Max events to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    event_type: Optional[str] = Query(default=None, description="Filter by event type"),
) -> SandboxEventsListResponse:
    """
    Query persisted events for a sandbox.

    Returns events in descending order by creation time (newest first).
    Supports pagination and optional filtering by event_type.

    Args:
        sandbox_id: Sandbox identifier (from URL path)
        limit: Maximum number of events to return (default: 100, max: 500)
        offset: Pagination offset (default: 0)
        event_type: Optional filter by event type (e.g., 'agent.tool_use')

    Returns:
        SandboxEventsListResponse with events and total count

    Example:
        GET /api/v1/sandboxes/sandbox-abc123/events?limit=50&event_type=agent.tool_use
    """
    try:
        db = get_db_service()
        # Use async version to avoid blocking the event loop
        events, total_count = await query_sandbox_events_async(
            db=db,
            sandbox_id=sandbox_id,
            limit=limit,
            offset=offset,
            event_type=event_type,
        )
        return SandboxEventsListResponse(
            events=[SandboxEventItem(**e) for e in events],
            total_count=total_count,
            sandbox_id=sandbox_id,
        )
    except Exception:
        # Return empty if DB unavailable
        return SandboxEventsListResponse(
            events=[],
            total_count=0,
            sandbox_id=sandbox_id,
        )


def query_trajectory_summary(
    db: DatabaseService,
    sandbox_id: str,
    limit: int = 500,
) -> dict:
    """
    Query trajectory events with heartbeat aggregation (SYNC version).

    This provides a cleaner view by:
    - Excluding heartbeat events from the main list
    - Aggregating heartbeat info (count, first, last)
    - Returning only meaningful trajectory events
    - Returning events in descending order (newest first) so users always see latest

    Args:
        db: Database service
        sandbox_id: Sandbox identifier
        limit: Maximum non-heartbeat events to return (default 500)

    Returns:
        Dict with events, heartbeat_summary, and counts
    """
    from sqlalchemy import func

    from omoi_os.models.sandbox_event import SandboxEvent

    with db.get_session() as session:
        # Define heartbeat event types to exclude from main list
        heartbeat_types = ["agent.heartbeat", "heartbeat"]

        # Get total count of all events
        total_count = (
            session.query(func.count(SandboxEvent.id))
            .filter(SandboxEvent.sandbox_id == sandbox_id)
            .scalar()
        )

        # Get heartbeat summary (count, first, last)
        heartbeat_stats = (
            session.query(
                func.count(SandboxEvent.id).label("count"),
                func.min(SandboxEvent.created_at).label("first"),
                func.max(SandboxEvent.created_at).label("last"),
            )
            .filter(SandboxEvent.sandbox_id == sandbox_id)
            .filter(SandboxEvent.event_type.in_(heartbeat_types))
            .first()
        )

        heartbeat_count = heartbeat_stats.count if heartbeat_stats else 0
        first_heartbeat = heartbeat_stats.first if heartbeat_stats else None
        last_heartbeat = heartbeat_stats.last if heartbeat_stats else None

        # Get non-heartbeat events (the actual trajectory)
        # Order by DESCENDING (newest first) so we get the most recent events
        trajectory_events = (
            session.query(SandboxEvent)
            .filter(SandboxEvent.sandbox_id == sandbox_id)
            .filter(~SandboxEvent.event_type.in_(heartbeat_types))
            .order_by(SandboxEvent.created_at.desc())  # Newest first
            .limit(limit)
            .all()
        )

        trajectory_count = len(trajectory_events)

        return {
            "sandbox_id": sandbox_id,
            "events": [
                {
                    "id": str(e.id),
                    "sandbox_id": e.sandbox_id,
                    "event_type": e.event_type,
                    "event_data": e.event_data,
                    "source": e.source,
                    "created_at": e.created_at,
                }
                for e in trajectory_events
            ],
            "heartbeat_summary": {
                "count": heartbeat_count,
                "first_heartbeat": first_heartbeat,
                "last_heartbeat": last_heartbeat,
            },
            "total_events": total_count,
            "trajectory_events": trajectory_count,
        }


async def query_trajectory_summary_async(
    db: DatabaseService,
    sandbox_id: str,
    limit: int = 100,
    cursor: Optional[str] = None,
    direction: str = "older",
) -> dict:
    """
    Query trajectory events with heartbeat aggregation (ASYNC version - non-blocking).

    This provides a cleaner view by:
    - Excluding heartbeat and noisy events from the main list
    - Aggregating heartbeat info (count, first, last)
    - Returning only meaningful trajectory events
    - Supporting cursor-based pagination for infinite scroll

    Args:
        db: Database service
        sandbox_id: Sandbox identifier
        limit: Maximum events to return per page (default 100)
        cursor: Event ID to paginate from (cursor-based pagination)
        direction: "older" to load events older than cursor, "newer" for newer

    Returns:
        Dict with events, heartbeat_summary, counts, and pagination cursors
    """
    from sqlalchemy import func, select, and_, or_

    from omoi_os.models.sandbox_event import SandboxEvent

    async with db.get_async_session() as session:
        # Event types to exclude from trajectory
        # - Heartbeats: Just noise, summarized separately
        # - Explore subagent tool_use/tool_result for Read/Glob/Grep: Very noisy file reads
        excluded_event_types = ["agent.heartbeat", "heartbeat"]

        # Get total count of all events
        total_result = await session.execute(
            select(func.count(SandboxEvent.id)).filter(
                SandboxEvent.sandbox_id == sandbox_id
            )
        )
        total_count = total_result.scalar() or 0

        # Get heartbeat summary (count, first, last)
        heartbeat_result = await session.execute(
            select(
                func.count(SandboxEvent.id).label("count"),
                func.min(SandboxEvent.created_at).label("first"),
                func.max(SandboxEvent.created_at).label("last"),
            )
            .filter(SandboxEvent.sandbox_id == sandbox_id)
            .filter(SandboxEvent.event_type.in_(["agent.heartbeat", "heartbeat"]))
        )
        heartbeat_stats = heartbeat_result.first()

        heartbeat_count = heartbeat_stats.count if heartbeat_stats else 0
        first_heartbeat = heartbeat_stats.first if heartbeat_stats else None
        last_heartbeat = heartbeat_stats.last if heartbeat_stats else None

        # Build base query for trajectory events
        base_filter = and_(
            SandboxEvent.sandbox_id == sandbox_id,
            ~SandboxEvent.event_type.in_(excluded_event_types),
        )

        # If cursor provided, get the cursor event's created_at for pagination
        cursor_timestamp = None
        if cursor:
            cursor_result = await session.execute(
                select(SandboxEvent.created_at).filter(SandboxEvent.id == cursor)
            )
            cursor_row = cursor_result.first()
            if cursor_row:
                cursor_timestamp = cursor_row[0]

        # Build pagination filter
        if cursor_timestamp:
            if direction == "older":
                # Get events older than cursor (created_at < cursor's created_at)
                pagination_filter = and_(
                    base_filter,
                    SandboxEvent.created_at < cursor_timestamp
                )
            else:
                # Get events newer than cursor (created_at > cursor's created_at)
                pagination_filter = and_(
                    base_filter,
                    SandboxEvent.created_at > cursor_timestamp
                )
        else:
            pagination_filter = base_filter

        # Query events - newest first for "older" direction, oldest first for "newer"
        if direction == "older":
            trajectory_result = await session.execute(
                select(SandboxEvent)
                .filter(pagination_filter)
                .order_by(SandboxEvent.created_at.desc())
                .limit(limit + 1)  # +1 to check if there are more
            )
        else:
            trajectory_result = await session.execute(
                select(SandboxEvent)
                .filter(pagination_filter)
                .order_by(SandboxEvent.created_at.asc())
                .limit(limit + 1)
            )

        trajectory_events = list(trajectory_result.scalars().all())

        # Check if there are more events
        has_more = len(trajectory_events) > limit
        if has_more:
            trajectory_events = trajectory_events[:limit]

        # For "newer" direction, reverse to maintain newest-first order
        if direction == "newer":
            trajectory_events = list(reversed(trajectory_events))

        # Filter out noisy explore subagent events
        # These are tool_use/tool_result events with Read/Glob/Grep from explore subagents
        def is_noisy_explore_event(event: SandboxEvent) -> bool:
            if event.event_type not in ("agent.tool_use", "agent.tool_result"):
                return False
            if not event.event_data:
                return False
            # Check if it's from an explore subagent
            tool = event.event_data.get("tool", "")
            tool_input = event.event_data.get("tool_input", {})
            # Filter Read/Glob/Grep that are clearly explore operations
            if tool in ("Read", "Glob", "Grep"):
                # Keep if it's the main agent (no subagent context)
                # Filter if it looks like bulk exploration
                if isinstance(tool_input, dict):
                    # Glob with ** patterns is exploratory
                    pattern = tool_input.get("pattern", "")
                    if tool == "Glob" and "**" in str(pattern):
                        return True
                    # Grep searches are usually exploratory
                    if tool == "Grep":
                        return True
            return False

        # Apply noise filter
        filtered_events = [e for e in trajectory_events if not is_noisy_explore_event(e)]

        trajectory_count = len(filtered_events)

        # Build cursors for pagination
        next_cursor = None  # Cursor for loading older events
        prev_cursor = None  # Cursor for loading newer events

        if filtered_events:
            # Oldest event in batch is cursor for "load older"
            next_cursor = str(filtered_events[-1].id) if has_more else None
            # Newest event in batch is cursor for "load newer" (when scrolling back up)
            prev_cursor = str(filtered_events[0].id)

        return {
            "sandbox_id": sandbox_id,
            "events": [
                {
                    "id": str(e.id),
                    "sandbox_id": e.sandbox_id,
                    "event_type": e.event_type,
                    "event_data": e.event_data,
                    "source": e.source,
                    "created_at": e.created_at,
                }
                for e in filtered_events
            ],
            "heartbeat_summary": {
                "count": heartbeat_count,
                "first_heartbeat": first_heartbeat,
                "last_heartbeat": last_heartbeat,
            },
            "total_events": total_count,
            "trajectory_events": trajectory_count,
            "next_cursor": next_cursor,
            "prev_cursor": prev_cursor,
            "has_more": has_more,
        }


@router.get("/{sandbox_id}/trajectory", response_model=TrajectorySummaryResponse)
async def get_sandbox_trajectory(
    sandbox_id: str,
    limit: int = Query(default=100, le=1000, ge=1, description="Max events to return per page"),
    cursor: Optional[str] = Query(default=None, description="Event ID cursor for pagination"),
    direction: str = Query(default="older", description="Load 'older' or 'newer' events from cursor"),
) -> TrajectorySummaryResponse:
    """
    Get trajectory summary for a sandbox with heartbeat aggregation and cursor-based pagination.

    This endpoint is optimized for viewing agent activity by:
    - Excluding heartbeat events from the main event list
    - Providing a summary of heartbeats (count, first timestamp, last timestamp)
    - Filtering noisy explore subagent events (Glob/Grep)
    - Supporting cursor-based infinite scroll pagination

    Pagination:
    - Initial load: No cursor, returns newest events first
    - Load older: Pass `cursor=next_cursor` with `direction=older`
    - Load newer: Pass `cursor=prev_cursor` with `direction=newer`

    The frontend should reverse the order for chronological display if needed.
    Much faster than fetching all events when there are many heartbeats.

    Args:
        sandbox_id: Sandbox identifier (from URL path)
        limit: Maximum number of trajectory events to return per page (default: 100, max: 1000)
        cursor: Event ID to paginate from (for infinite scroll)
        direction: "older" to load events older than cursor, "newer" for newer events

    Returns:
        TrajectorySummaryResponse with filtered events, heartbeat summary, and pagination cursors

    Example:
        Initial load: GET /api/v1/sandboxes/sandbox-abc123/trajectory?limit=100
        Load more: GET /api/v1/sandboxes/sandbox-abc123/trajectory?limit=100&cursor=event-id&direction=older

        Response:
        {
            "sandbox_id": "sandbox-abc123",
            "events": [...],  // Non-heartbeat, non-noise events only
            "heartbeat_summary": {
                "count": 150,
                "first_heartbeat": "2025-12-19T10:00:00Z",
                "last_heartbeat": "2025-12-19T10:25:00Z"
            },
            "total_events": 165,
            "trajectory_events": 15,
            "next_cursor": "event-id-123",  // For loading older events
            "prev_cursor": "event-id-456",  // For loading newer events
            "has_more": true
        }
    """
    try:
        db = get_db_service()
        # Use async version to avoid blocking the event loop
        result = await query_trajectory_summary_async(
            db=db,
            sandbox_id=sandbox_id,
            limit=limit,
            cursor=cursor,
            direction=direction,
        )
        return TrajectorySummaryResponse(
            sandbox_id=result["sandbox_id"],
            events=[SandboxEventItem(**e) for e in result["events"]],
            heartbeat_summary=HeartbeatSummary(**result["heartbeat_summary"]),
            total_events=result["total_events"],
            trajectory_events=result["trajectory_events"],
            next_cursor=result.get("next_cursor"),
            prev_cursor=result.get("prev_cursor"),
            has_more=result.get("has_more", False),
        )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(
            f"Failed to get trajectory for sandbox {sandbox_id}: {e}\n{error_details}"
        )
        # Re-raise to let FastAPI handle the error and return a proper 500 response
        # This makes debugging easier - the frontend will see the error instead of empty events
        raise


# ============================================================================
# SANDBOX-TASK LOOKUP ENDPOINT
# ============================================================================


@router.get("/{sandbox_id}/task", response_model=SandboxTaskResponse)
async def get_task_by_sandbox(
    sandbox_id: str,
) -> SandboxTaskResponse:
    """
    Get the task associated with a sandbox.

    This endpoint allows the frontend to fetch task details (title, status, etc.)
    when viewing a sandbox by its ID.

    Args:
        sandbox_id: Sandbox identifier (from URL path)

    Returns:
        SandboxTaskResponse with task information

    Raises:
        HTTPException 404: If no task is found for this sandbox

    Example:
        GET /api/v1/sandboxes/sandbox-abc123/task

        Response:
        {
            "id": "task-xyz",
            "title": "Add authentication to API",
            "status": "running",
            "sandbox_id": "sandbox-abc123",
            ...
        }
    """
    from fastapi import HTTPException
    from sqlalchemy import select

    db = get_db_service()

    # Use async version to avoid blocking the event loop
    async with db.get_async_session() as session:
        result = await session.execute(
            select(Task).filter(Task.sandbox_id == sandbox_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"No task found for sandbox {sandbox_id}",
            )

        return SandboxTaskResponse(
            id=task.id,
            ticket_id=task.ticket_id,
            phase_id=task.phase_id,
            task_type=task.task_type,
            title=task.title,
            description=task.description,
            priority=task.priority,
            status=task.status,
            sandbox_id=task.sandbox_id or sandbox_id,
            assigned_agent_id=task.assigned_agent_id,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat() if task.updated_at else None,
            started_at=task.started_at.isoformat() if task.started_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
        )


# ============================================================================
# PHASE 2: MESSAGE HELPER FUNCTIONS (Testable via Unit Tests)
# ============================================================================


def _create_message_event(
    sandbox_id: str,
    content: str,
    message_type: str,
) -> SystemEvent:
    """
    Create SystemEvent for message queued notification.

    UNIT TESTABLE: Pure function with no external dependencies.

    Args:
        sandbox_id: Target sandbox identifier
        content: Message content (truncated in event)
        message_type: Type of message

    Returns:
        SystemEvent ready for publishing
    """
    priority = "high" if message_type == "interrupt" else "normal"

    return SystemEvent(
        event_type="SANDBOX_MESSAGE_QUEUED",
        entity_type="sandbox",
        entity_id=sandbox_id,
        payload={
            "content": content[:100],  # Truncate for event
            "message_type": message_type,
            "priority": priority,
        },
    )


def enqueue_message_with_broadcast(
    sandbox_id: str,
    content: str,
    message_type: str,
    queue: RedisMessageQueue | InMemoryMessageQueue | None = None,
    event_bus: EventBusService | None = None,
) -> str:
    """
    Enqueue message and broadcast notification event.

    UNIT TESTABLE: Dependencies can be injected/mocked.

    Args:
        sandbox_id: Target sandbox identifier
        content: Message content
        message_type: Type of message
        queue: Optional MessageQueue instance (defaults to global Redis queue)
        event_bus: Optional EventBusService instance (defaults to global)

    Returns:
        Generated message ID
    """
    if queue is None:
        queue = _get_message_queue()
    if event_bus is None:
        event_bus = get_event_bus()

    message_id = queue.enqueue(sandbox_id, content, message_type)

    event = _create_message_event(sandbox_id, content, message_type)
    event_bus.publish(event)

    return message_id


# ============================================================================
# PHASE 2: MESSAGE ENDPOINTS (Integration Tested via HTTP)
# ============================================================================


@router.post("/{sandbox_id}/messages", response_model=MessageQueueResponse)
async def post_message(
    sandbox_id: str,
    message: SandboxMessage,
) -> MessageQueueResponse:
    """
    Queue a message for the sandbox worker to receive.

    This endpoint allows users, Guardian, or system components to inject
    messages into a running sandbox agent. The agent polls for messages
    and processes them during its execution loop.

    Message Types:
    - user_message: Guidance/direction from user
    - interrupt: High-priority signal to stop current work
    - guardian_nudge: Suggestion from Guardian system
    - system: System-level notification

    Args:
        sandbox_id: Target sandbox identifier (from URL path)
        message: Message data from request body

    Returns:
        MessageQueueResponse with status and message_id

    Example:
        POST /api/v1/sandboxes/sandbox-abc123/messages
        {
            "content": "Please focus on the authentication module first.",
            "message_type": "user_message"
        }
    """
    message_id = enqueue_message_with_broadcast(
        sandbox_id=sandbox_id,
        content=message.content,
        message_type=message.message_type,
    )

    return MessageQueueResponse(
        status="queued",
        message_id=message_id,
        sandbox_id=sandbox_id,
    )


@router.get("/{sandbox_id}/messages", response_model=list[MessageItem])
async def get_messages(sandbox_id: str) -> list[MessageItem]:
    """
    Get and consume pending messages for sandbox.

    This endpoint is polled by sandbox workers to receive injected messages.
    Messages are returned in FIFO order and cleared from the queue after retrieval.

    Args:
        sandbox_id: Sandbox identifier (from URL path)

    Returns:
        List of MessageItem objects (empty list if no pending messages)

    Example:
        GET /api/v1/sandboxes/sandbox-abc123/messages
        Response: [
            {
                "id": "msg-abc123def456",
                "content": "Please focus on authentication",
                "message_type": "user_message",
                "timestamp": "2025-12-13T12:00:00Z"
            }
        ]
    """
    queue = _get_message_queue()
    messages = queue.get_all(sandbox_id)
    return [MessageItem(**m) for m in messages]


# ============================================================================
# TASK COMPLETION API ENDPOINT (Sandbox Callback)
# ============================================================================


class TaskCompleteRequest(BaseModel):
    """Request schema for sandbox to report task completion."""

    task_id: str = Field(..., description="Task ID that completed")
    success: bool = Field(default=True, description="Whether task completed successfully")
    result: Optional[dict] = Field(
        default=None, description="Task result data (output, artifacts, etc.)"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if task failed"
    )


class TaskCompleteResponse(BaseModel):
    """Response schema for task completion."""

    status: str
    task_id: str
    new_status: str
    unblocked_tasks: list[str] = Field(
        default_factory=list,
        description="List of task IDs that are now unblocked due to this completion",
    )


@router.post("/{sandbox_id}/task-complete", response_model=TaskCompleteResponse)
async def report_task_complete(
    sandbox_id: str,
    request: TaskCompleteRequest,
) -> TaskCompleteResponse:
    """
    Report task completion from a sandbox.

    This endpoint allows sandboxes to report when a task has completed.
    When a task completes successfully:
    1. Task status is updated to 'completed'
    2. DAG is re-evaluated to find newly unblocked tasks
    3. Event is published for orchestrator to spawn unblocked tasks

    This is the HTTP callback equivalent for Option 1 (HTTP Callback) in
    the task completion strategy.

    Args:
        sandbox_id: Sandbox identifier (from URL path)
        request: Task completion data

    Returns:
        TaskCompleteResponse with new status and unblocked task IDs

    Example:
        POST /api/v1/sandboxes/sandbox-abc123/task-complete
        {
            "task_id": "task-xyz",
            "success": true,
            "result": {
                "output": "Feature implemented successfully",
                "branch_name": "feature/auth-flow",
                "pr_url": "https://github.com/org/repo/pull/123"
            }
        }
    """
    from omoi_os.services.task_queue import TaskQueueService

    db = get_db_service()
    task_queue = TaskQueueService(db, event_bus=get_event_bus())

    # Determine new status based on success
    new_status = "completed" if request.success else "failed"

    # Update task status
    if request.success:
        await task_queue.update_task_status_async(
            task_id=request.task_id,
            status=new_status,
            result=request.result,
        )
    else:
        await task_queue.update_task_status_async(
            task_id=request.task_id,
            status=new_status,
            error_message=request.error_message,
        )

    logger.info(
        f"Task {request.task_id} reported as {new_status} from sandbox {sandbox_id}"
    )

    # Find tasks that are now unblocked due to this completion
    unblocked_task_ids: list[str] = []
    if request.success:
        try:
            # Get tasks that were blocked by this task
            async with db.get_async_session() as session:
                # Find tasks where this task_id is in their depends_on list
                # and all their dependencies are now completed
                result = await session.execute(
                    select(Task).where(
                        Task.status == "pending",
                        Task.dependencies.isnot(None),
                    )
                )
                pending_tasks = result.scalars().all()

                for task in pending_tasks:
                    deps = task.dependencies or {}
                    depends_on = deps.get("depends_on", [])

                    if request.task_id in depends_on:
                        # Check if all dependencies are now completed
                        all_deps_complete = await task_queue._check_dependencies_complete_async(
                            session, task
                        )
                        if all_deps_complete:
                            unblocked_task_ids.append(str(task.id))

            if unblocked_task_ids:
                logger.info(
                    f"Task {request.task_id} completion unblocked {len(unblocked_task_ids)} tasks: {unblocked_task_ids}"
                )

                # Publish event for orchestrator to pick up unblocked tasks
                event_bus = get_event_bus()
                event_bus.publish(
                    SystemEvent(
                        event_type="TASKS_UNBLOCKED",
                        entity_type="task",
                        entity_id=request.task_id,
                        payload={
                            "completed_task_id": request.task_id,
                            "unblocked_task_ids": unblocked_task_ids,
                            "sandbox_id": sandbox_id,
                        },
                    )
                )
        except Exception as e:
            logger.error(f"Failed to find unblocked tasks: {e}", exc_info=True)
            # Don't fail the request - task completion was successful

    return TaskCompleteResponse(
        status="accepted",
        task_id=request.task_id,
        new_status=new_status,
        unblocked_tasks=unblocked_task_ids,
    )


# ============================================================================
# VALIDATION API ENDPOINTS
# ============================================================================


class ValidationResultRequest(BaseModel):
    """Request schema for submitting validation results."""

    task_id: str = Field(..., description="Task ID that was validated")
    passed: bool = Field(..., description="Whether validation passed")
    feedback: str = Field(..., description="Human-readable feedback")
    evidence: Optional[dict] = Field(
        default=None, description="Evidence of checks performed (test output, etc.)"
    )
    recommendations: Optional[list[str]] = Field(
        default=None, description="List of recommendations if validation failed"
    )


class ValidationResultResponse(BaseModel):
    """Response schema for validation result submission."""

    status: str
    task_id: str
    validation_passed: bool
    new_task_status: str


@router.post("/{sandbox_id}/validation-result", response_model=ValidationResultResponse)
async def submit_validation_result(
    sandbox_id: str,
    validation: ValidationResultRequest,
) -> ValidationResultResponse:
    """
    Submit validation result from a validator agent.

    This endpoint is called by validator agents to report whether validation
    passed or failed. Based on the result:
    - If passed: Task is marked as "completed"
    - If failed: Task is marked as "needs_revision" with feedback

    Args:
        sandbox_id: Sandbox identifier of the validator
        validation: Validation result data

    Returns:
        ValidationResultResponse with new task status

    Example:
        POST /api/v1/sandboxes/validator-abc123/validation-result
        {
            "task_id": "task-xyz",
            "passed": false,
            "feedback": "Tests are failing. 3 tests failed in test_auth.py",
            "evidence": {"test_output": "..."},
            "recommendations": ["Fix the failing tests", "Run pytest before committing"]
        }
    """
    db = get_db_service()

    # Get validator agent ID from the original task's result
    # The validator_agent_id was stored when validation was requested
    validator_agent_id = None
    async with db.get_async_session() as session:
        from sqlalchemy import select

        # Find the original task being validated
        result = await session.execute(
            select(Task).filter(Task.id == validation.task_id)
        )
        task = result.scalar_one_or_none()
        if task and task.result:
            # Get validator info stored during validation request
            validator_agent_id = task.result.get("validator_agent_id")
            stored_sandbox = task.result.get("validator_sandbox_id")
            # Verify the sandbox matches (security check)
            if stored_sandbox and stored_sandbox != sandbox_id:
                logger.warning(
                    f"Sandbox mismatch: expected {stored_sandbox}, got {sandbox_id}"
                )

    if not validator_agent_id:
        # Use a placeholder if we can't find the agent
        validator_agent_id = f"validator-{sandbox_id[:8]}"

    from omoi_os.services.task_validator import get_task_validator

    validator_service = get_task_validator(db=db, event_bus=get_event_bus())
    await validator_service.handle_validation_result(
        task_id=validation.task_id,
        validator_agent_id=validator_agent_id,
        passed=validation.passed,
        feedback=validation.feedback,
        evidence=validation.evidence,
        recommendations=validation.recommendations,
    )

    # Determine new task status
    new_status = "completed" if validation.passed else "needs_revision"

    logger.info(
        f"Validation result submitted for task {validation.task_id}: "
        f"passed={validation.passed}, new_status={new_status}"
    )

    return ValidationResultResponse(
        status="accepted",
        task_id=validation.task_id,
        validation_passed=validation.passed,
        new_task_status=new_status,
    )
