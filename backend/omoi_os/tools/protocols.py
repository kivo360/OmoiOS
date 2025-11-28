"""Protocol definitions for OmoiOS tool service interfaces.

These protocols define the expected interfaces that services must implement
to be used by the OpenHands tools. Using Protocol allows for duck typing
while still providing type safety through static analysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from omoi_os.models.agent_message import AgentMessage, CollaborationThread
    from omoi_os.models.task import Task
    from omoi_os.models.task_discovery import TaskDiscovery


# =============================================================================
# Database Service Protocol
# =============================================================================


@runtime_checkable
class DatabaseServiceProtocol(Protocol):
    """Protocol for database service operations."""

    def get_session(self) -> "SessionContextManager":
        """Get a database session context manager."""
        ...


class SessionContextManager(Protocol):
    """Protocol for session context manager returned by get_session()."""

    def __enter__(self) -> "Session": ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None: ...


# =============================================================================
# Task Queue Service Protocol
# =============================================================================


@runtime_checkable
class TaskQueueServiceProtocol(Protocol):
    """Protocol for task queue service operations.

    This matches the interface of TaskQueueService from
    omoi_os.services.task_queue.
    """

    def enqueue_task(
        self,
        ticket_id: str,
        phase_id: str,
        task_type: str,
        description: str,
        priority: str,
        dependencies: dict[str, Any] | None = None,
        session: Optional["Session"] = None,
    ) -> "Task":
        """
        Add a task to the queue.

        Args:
            ticket_id: UUID of the parent ticket
            phase_id: Phase identifier (e.g., "PHASE_IMPLEMENTATION")
            task_type: Type of task (e.g., "implement_feature")
            description: Task description
            priority: Task priority (CRITICAL, HIGH, MEDIUM, LOW)
            dependencies: Optional dependencies dict
            session: Optional database session

        Returns:
            Created Task object
        """
        ...

    def update_task_status(
        self,
        task_id: str,
        status: str,
        result_summary: str | None = None,
        error_message: str | None = None,
        session: Optional["Session"] = None,
    ) -> Optional["Task"]:
        """
        Update a task's status.

        Args:
            task_id: Task ID to update
            status: New status (pending, in_progress, completed, failed, cancelled)
            result_summary: Summary of results (for completed/failed)
            error_message: Error details (for failed status)
            session: Optional database session

        Returns:
            Updated Task object or None if not found
        """
        ...


# =============================================================================
# Discovery Service Protocol
# =============================================================================


@runtime_checkable
class DiscoveryServiceProtocol(Protocol):
    """Protocol for discovery service operations.

    This matches the interface of DiscoveryService from
    omoi_os.services.discovery.
    """

    def record_discovery(
        self,
        source_task_id: str | None,
        discovery_type: str,
        description: str,
        spawned_task_id: str | None = None,
        priority_boost: bool = False,
    ) -> Optional["TaskDiscovery"]:
        """
        Record a discovery made during task execution.

        Args:
            source_task_id: ID of the task that made the discovery
            discovery_type: Type of discovery (bug, optimization, etc.)
            description: Description of what was discovered
            spawned_task_id: ID of task spawned from this discovery
            priority_boost: Whether to boost priority

        Returns:
            Created TaskDiscovery object or None
        """
        ...


# =============================================================================
# Collaboration Service Protocol
# =============================================================================


@runtime_checkable
class CollaborationServiceProtocol(Protocol):
    """Protocol for collaboration service operations.

    This matches the interface of CollaborationService from
    omoi_os.services.collaboration.
    """

    def broadcast_message(
        self,
        from_agent_id: str,
        message: str,
        message_type: str = "info",
        ticket_id: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Broadcast a message to all active agents.

        Args:
            from_agent_id: Sending agent ID
            message: Message content
            message_type: Type of message (info, question, warning, discovery)
            ticket_id: Optional ticket ID for context
            task_id: Optional task ID for context

        Returns:
            Dictionary with success status and recipient count:
            {
                "success": bool,
                "recipient_count": int,
                "message": str (optional)
            }
        """
        ...

    def get_or_create_thread(
        self,
        participants: list[str],
        ticket_id: str | None = None,
        task_id: str | None = None,
        thread_type: str = "consultation",
    ) -> "CollaborationThread":
        """
        Get existing thread or create new one for given participants.

        Args:
            participants: List of agent IDs
            ticket_id: Optional ticket ID
            task_id: Optional task ID
            thread_type: Type of thread

        Returns:
            CollaborationThread object
        """
        ...

    def send_message(
        self,
        thread_id: str,
        from_agent_id: str,
        message_type: str,
        content: str,
        to_agent_id: str | None = None,
        message_metadata: dict[str, Any] | None = None,
    ) -> "AgentMessage":
        """
        Send a message in a collaboration thread.

        Args:
            thread_id: Thread to send message in
            from_agent_id: Sending agent ID
            message_type: Type of message
            content: Message content
            to_agent_id: Optional target agent
            message_metadata: Optional metadata

        Returns:
            Created AgentMessage
        """
        ...

    def get_agent_messages(
        self,
        agent_id: str,
        limit: int = 50,
        unread_only: bool = False,
    ) -> list["AgentMessage"]:
        """
        Get all messages for an agent.

        Args:
            agent_id: Agent ID
            limit: Maximum messages to return
            unread_only: Only return unread messages

        Returns:
            List of AgentMessage objects
        """
        ...

    def mark_message_read(self, message_id: str) -> bool:
        """
        Mark a message as read.

        Args:
            message_id: Message ID to mark as read

        Returns:
            True if successful, False if message not found
        """
        ...

    def request_handoff(
        self,
        from_agent_id: str,
        to_agent_id: str,
        task_id: str,
        reason: str,
        context: dict[str, Any] | None = None,
    ) -> tuple["CollaborationThread", "AgentMessage"]:
        """
        Request a task handoff from one agent to another.

        Args:
            from_agent_id: Agent requesting handoff
            to_agent_id: Target agent
            task_id: Task to hand off
            reason: Reason for handoff
            context: Optional handoff context

        Returns:
            Tuple of (CollaborationThread, AgentMessage)
        """
        ...


# =============================================================================
# Event Bus Service Protocol
# =============================================================================


@runtime_checkable
class EventBusServiceProtocol(Protocol):
    """Protocol for event bus service operations."""

    def publish(self, event: Any) -> None:
        """
        Publish an event.

        Args:
            event: Event to publish (typically SystemEvent)
        """
        ...
