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
    if event.event_type in (
        "agent.started",
        "agent.completed",
        "continuous.completed",  # Contains validation_passed result
        "agent.failed",
        "agent.error",
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
                    logger.debug(
                        f"Spec sandbox event (spec_id={spec_id}), skipping task status update. "
                        f"event_type={event.event_type}, sandbox_id={sandbox_id}"
                    )
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
