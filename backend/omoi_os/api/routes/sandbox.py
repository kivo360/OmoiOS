"""
Sandbox API routes for event callbacks and messaging.

This module is designed for testability:
- Helper functions are extracted for unit testing
- Schemas are separate from endpoint logic
- Dependencies are injectable via FastAPI Depends()

Phase 4 Updates:
- Events are persisted to sandbox_events table
- Returns event_id in response
"""

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from omoi_os.api.dependencies import get_db_service
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent

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
# PHASE 2: MESSAGE QUEUE (Testable via Unit Tests)
# ============================================================================


class MessageQueue:
    """
    Thread-safe in-memory message queue.

    UNIT TESTABLE: No external dependencies.

    Note: For production with multiple server instances, replace with Redis-based
    implementation. This in-memory version is suitable for single-instance deployment
    and testing.
    """

    def __init__(self):
        self._queues: dict[str, list[dict]] = defaultdict(list)
        self._lock = Lock()

    def enqueue(
        self,
        sandbox_id: str,
        content: str,
        message_type: str,
    ) -> str:
        """
        Add message to queue. Returns message_id.

        Args:
            sandbox_id: Target sandbox identifier
            content: Message content
            message_type: Type of message

        Returns:
            Generated message ID
        """
        message_id = f"msg-{uuid.uuid4().hex[:12]}"

        with self._lock:
            self._queues[sandbox_id].append(
                {
                    "id": message_id,
                    "content": content,
                    "message_type": message_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        return message_id

    def get_all(self, sandbox_id: str) -> list[dict]:
        """
        Get and clear all messages for sandbox.

        Args:
            sandbox_id: Sandbox identifier

        Returns:
            List of message dictionaries (FIFO order)
        """
        with self._lock:
            messages = self._queues.pop(sandbox_id, [])
        return messages


# Global message queue instance
_global_message_queue = MessageQueue()


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
        return db_event.id


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
    except Exception:
        # Persistence is optional - don't fail if DB unavailable
        pass

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
    queue: MessageQueue | None = None,
    event_bus: EventBusService | None = None,
) -> str:
    """
    Enqueue message and broadcast notification event.

    UNIT TESTABLE: Dependencies can be injected/mocked.

    Args:
        sandbox_id: Target sandbox identifier
        content: Message content
        message_type: Type of message
        queue: Optional MessageQueue instance (defaults to global)
        event_bus: Optional EventBusService instance (defaults to global)

    Returns:
        Generated message ID
    """
    if queue is None:
        queue = _global_message_queue
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
    messages = _global_message_queue.get_all(sandbox_id)
    return [MessageItem(**m) for m in messages]
