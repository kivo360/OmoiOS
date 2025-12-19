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

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from omoi_os.api.dependencies import get_db_service
from omoi_os.logging import get_logger
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
) -> str:
    """
    Persist event to database.

    Phase 4: Database persistence for audit trails.

    For agent.completed events with session_id, also saves the session transcript
    to claude_session_transcripts table for cross-sandbox resumption.

    Args:
        db: Database service
        sandbox_id: Unique identifier for the sandbox
        event_type: Original event type (e.g., 'agent.tool_use')
        event_data: Event payload dictionary
        source: Event source ('agent', 'worker', 'system')

    Returns:
        Persisted event ID
    """
    from omoi_os.models.sandbox_event import SandboxEvent

    with db.get_session() as session:
        db_event = SandboxEvent(
            sandbox_id=sandbox_id,
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


def save_session_transcript(
    db: DatabaseService,
    session_id: str,
    sandbox_id: str,
    task_id: str | None = None,
    transcript_b64: str | None = None,
    metadata: dict | None = None,
) -> None:
    """
    Save Claude session transcript to database for cross-sandbox resumption.

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


def get_session_transcript(db: DatabaseService, session_id: str) -> str | None:
    """
    Retrieve Claude session transcript from database.

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


@router.post("/{sandbox_id}/events", response_model=SandboxEventResponse)
async def post_sandbox_event(
    sandbox_id: str,
    event: SandboxEventCreate,
    request: Request = None,
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
        request: FastAPI Request object for logging

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
    # Log incoming request for debugging 502 issues
    logger.info(
        f"[SandboxEvent] Received {event.event_type} from sandbox {sandbox_id[:20]}... "
        f"(source: {event.source})"
    )

    # Persist to database (Phase 4) - optional, don't fail if DB unavailable
    # Persist to database (Phase 4) - optional, fails gracefully
    event_id: str | None = None
    try:
        db = get_db_service()
        event_id = persist_sandbox_event(
            db=db,
            sandbox_id=sandbox_id,
            event_type=event.event_type,
            event_data=event.event_data,
            source=event.source,
        )
        logger.debug(
            f"[SandboxEvent] Persisted event {event_id} for {event.event_type}"
        )
    except Exception as e:
        # Persistence is optional - don't fail if DB unavailable
        logger.warning(
            f"[SandboxEvent] Failed to persist event {event.event_type} for sandbox {sandbox_id}: {e}"
        )

    # Handle task status transitions based on event type
    # This includes: agent.started -> running, agent.completed -> completed, agent.failed/error -> failed
    if event.event_type in ("agent.started", "agent.completed", "agent.failed", "agent.error"):
        try:
            db = get_db_service()
            from omoi_os.models.task import Task
            from omoi_os.services.task_queue import TaskQueueService

            task_id = event.event_data.get("task_id")
            logger.debug(
                f"Task status update: event_type={event.event_type}, task_id={task_id}, sandbox_id={sandbox_id}"
            )

            if not task_id:
                # Try to find task by sandbox_id as fallback
                logger.debug(
                    f"No task_id in event_data, searching by sandbox_id={sandbox_id}"
                )
                with db.get_session() as session:
                    task = (
                        session.query(Task)
                        .filter(Task.sandbox_id == sandbox_id)
                        .filter(Task.status.in_(["assigned", "running"]))
                        .first()
                    )
                    if task:
                        task_id = str(task.id)
                        logger.info(f"Found task {task_id} by sandbox_id fallback")
                    else:
                        logger.warning(
                            f"No task found for sandbox {sandbox_id} with status assigned/running"
                        )

            if task_id:
                task_queue = TaskQueueService(db)

                # Handle agent.started -> transition to running
                if event.event_type == "agent.started":
                    logger.info(f"Updating task {task_id} status to running (agent.started)")
                    task_queue.update_task_status(
                        task_id=task_id,
                        status="running",
                    )
                    logger.info(f"Successfully updated task {task_id} to running")

                # Handle agent.completed -> transition to completed
                elif event.event_type == "agent.completed":
                    # Extract result from event_data
                    result = {
                        "success": event.event_data.get("success", True),
                        "turns": event.event_data.get("turns"),
                        "cost_usd": event.event_data.get("cost_usd"),
                        "session_id": event.event_data.get("session_id"),
                        "stop_reason": event.event_data.get("stop_reason"),
                    }
                    # Include final output if available
                    if "final_output" in event.event_data:
                        result["output"] = event.event_data["final_output"]
                        logger.debug(
                            f"Task {task_id} completion includes final_output ({len(result.get('output', ''))} chars)"
                        )
                    else:
                        logger.debug(f"Task {task_id} completion missing final_output")

                    logger.info(f"Updating task {task_id} status to completed")
                    task_queue.update_task_status(
                        task_id=task_id,
                        status="completed",
                        result=result,
                    )
                    logger.info(f"Successfully updated task {task_id} to completed")

                # Handle agent.failed/error -> transition to failed
                elif event.event_type in ("agent.failed", "agent.error"):
                    error_message = event.event_data.get(
                        "error", "Task execution failed"
                    )
                    logger.info(
                        f"Updating task {task_id} status to failed: {error_message}"
                    )
                    task_queue.update_task_status(
                        task_id=task_id,
                        status="failed",
                        error_message=error_message,
                    )
                    logger.info(f"Successfully updated task {task_id} to failed")
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
    """

    sandbox_id: str
    events: list[SandboxEventItem]
    heartbeat_summary: HeartbeatSummary
    total_events: int  # Total including heartbeats
    trajectory_events: int  # Count excluding heartbeats


def query_sandbox_events(
    db: DatabaseService,
    sandbox_id: str,
    limit: int = 100,
    offset: int = 0,
    event_type: Optional[str] = None,
) -> tuple[list[dict], int]:
    """
    Query persisted events for a sandbox.

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
        events, total_count = query_sandbox_events(
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
    limit: int = 100,
) -> dict:
    """
    Query trajectory events with heartbeat aggregation.

    This provides a cleaner view by:
    - Excluding heartbeat events from the main list
    - Aggregating heartbeat info (count, first, last)
    - Returning only meaningful trajectory events

    Args:
        db: Database service
        sandbox_id: Sandbox identifier
        limit: Maximum non-heartbeat events to return

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
        trajectory_events = (
            session.query(SandboxEvent)
            .filter(SandboxEvent.sandbox_id == sandbox_id)
            .filter(~SandboxEvent.event_type.in_(heartbeat_types))
            .order_by(SandboxEvent.created_at.asc())  # Chronological order
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


@router.get("/{sandbox_id}/trajectory", response_model=TrajectorySummaryResponse)
async def get_sandbox_trajectory(
    sandbox_id: str,
    limit: int = Query(default=100, le=500, ge=1, description="Max events to return"),
) -> TrajectorySummaryResponse:
    """
    Get trajectory summary for a sandbox with heartbeat aggregation.

    This endpoint is optimized for viewing agent activity by:
    - Excluding heartbeat events from the main event list
    - Providing a summary of heartbeats (count, first timestamp, last timestamp)
    - Returning events in chronological order (oldest to newest)

    Much faster than fetching all events when there are many heartbeats.

    Args:
        sandbox_id: Sandbox identifier (from URL path)
        limit: Maximum number of trajectory events to return (default: 100, max: 500)

    Returns:
        TrajectorySummaryResponse with filtered events and heartbeat summary

    Example:
        GET /api/v1/sandboxes/sandbox-abc123/trajectory?limit=50

        Response:
        {
            "sandbox_id": "sandbox-abc123",
            "events": [...],  // Non-heartbeat events only
            "heartbeat_summary": {
                "count": 150,
                "first_heartbeat": "2025-12-19T10:00:00Z",
                "last_heartbeat": "2025-12-19T10:25:00Z"
            },
            "total_events": 165,
            "trajectory_events": 15
        }
    """
    try:
        db = get_db_service()
        result = query_trajectory_summary(
            db=db,
            sandbox_id=sandbox_id,
            limit=limit,
        )
        return TrajectorySummaryResponse(
            sandbox_id=result["sandbox_id"],
            events=[SandboxEventItem(**e) for e in result["events"]],
            heartbeat_summary=HeartbeatSummary(**result["heartbeat_summary"]),
            total_events=result["total_events"],
            trajectory_events=result["trajectory_events"],
        )
    except Exception as e:
        logger.error(f"Failed to get trajectory for sandbox {sandbox_id}: {e}")
        # Return empty response if error
        return TrajectorySummaryResponse(
            sandbox_id=sandbox_id,
            events=[],
            heartbeat_summary=HeartbeatSummary(count=0),
            total_events=0,
            trajectory_events=0,
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
