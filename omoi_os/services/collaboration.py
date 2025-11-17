"""Collaboration service for agent-to-agent messaging and handoffs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from omoi_os.models.agent_message import AgentMessage, CollaborationThread
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent


@dataclass
class MessageDTO:
    """Data transfer object for agent messages."""

    message_id: str
    thread_id: str
    from_agent_id: str
    to_agent_id: Optional[str]
    message_type: str
    content: str
    message_metadata: Optional[dict]
    read_at: Optional[str]
    created_at: str


@dataclass
class ThreadDTO:
    """Data transfer object for collaboration threads."""

    thread_id: str
    thread_type: str
    ticket_id: Optional[str]
    task_id: Optional[str]
    participants: list[str]
    status: str
    thread_metadata: Optional[dict]
    created_at: str
    closed_at: Optional[str]


class CollaborationService:
    """Service for managing agent-to-agent collaboration and messaging."""

    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
    ):
        """
        Initialize collaboration service.

        Args:
            db: Database service
            event_bus: Optional event bus for publishing collaboration events
        """
        self.db = db
        self.event_bus = event_bus

    # ---------------------------------------------------------------------
    # Thread Management
    # ---------------------------------------------------------------------

    def create_thread(
        self,
        thread_type: str,
        participants: List[str],
        ticket_id: Optional[str] = None,
        task_id: Optional[str] = None,
        thread_metadata: Optional[dict] = None,
    ) -> CollaborationThread:
        """
        Create a new collaboration thread.

        Args:
            thread_type: Type of collaboration (handoff, review, consultation)
            participants: List of agent IDs participating
            ticket_id: Optional ticket context
            task_id: Optional task context
            thread_metadata: Optional metadata

        Returns:
            Created CollaborationThread
        """
        with self.db.get_session() as session:
            thread = CollaborationThread(
                thread_type=thread_type,
                participants=participants,
                ticket_id=ticket_id,
                task_id=task_id,
                thread_metadata=thread_metadata,
                status="active",
            )
            session.add(thread)
            session.commit()
            session.refresh(thread)
            session.expunge(thread)

            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="agent.collab.started",
                        entity_type="thread",
                        entity_id=thread.id,
                        payload={
                            "thread_id": thread.id,
                            "thread_type": thread_type,
                            "participants": participants,
                            "ticket_id": ticket_id,
                            "task_id": task_id,
                        },
                    )
                )

            return thread

    def close_thread(self, thread_id: str) -> bool:
        """
        Close a collaboration thread.

        Args:
            thread_id: Thread ID to close

        Returns:
            True if closed successfully
        """
        from omoi_os.utils.datetime import utc_now

        with self.db.get_session() as session:
            thread = session.query(CollaborationThread).filter(
                CollaborationThread.id == thread_id
            ).first()
            if not thread:
                return False

            thread.status = "resolved"
            thread.closed_at = utc_now()
            session.commit()

            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="agent.collab.ended",
                        entity_type="thread",
                        entity_id=thread_id,
                        payload={"thread_id": thread_id},
                    )
                )

            return True

    def get_thread(self, thread_id: str) -> Optional[CollaborationThread]:
        """Get a collaboration thread by ID."""
        with self.db.get_session() as session:
            thread = session.query(CollaborationThread).filter(
                CollaborationThread.id == thread_id
            ).first()
            if thread:
                session.expunge(thread)
            return thread

    def list_threads(
        self,
        agent_id: Optional[str] = None,
        ticket_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[CollaborationThread]:
        """
        List collaboration threads with optional filters.

        Args:
            agent_id: Filter to threads with this participant
            ticket_id: Filter to threads for this ticket
            status: Filter by thread status

        Returns:
            List of CollaborationThread objects
        """
        with self.db.get_session() as session:
            query = session.query(CollaborationThread)

            if ticket_id:
                query = query.filter(CollaborationThread.ticket_id == ticket_id)
            if status:
                query = query.filter(CollaborationThread.status == status)

            threads = query.all()

            # Filter by participant (JSONB contains check)
            if agent_id:
                threads = [
                    t for t in threads
                    if agent_id in (t.participants or [])
                ]

            # Expunge for use outside session
            for thread in threads:
                session.expunge(thread)

            return threads

    # ---------------------------------------------------------------------
    # Messaging
    # ---------------------------------------------------------------------

    def send_message(
        self,
        thread_id: str,
        from_agent_id: str,
        message_type: str,
        content: str,
        to_agent_id: Optional[str] = None,
        message_metadata: Optional[dict] = None,
    ) -> AgentMessage:
        """
        Send a message in a collaboration thread.

        Args:
            thread_id: Thread to send message in
            from_agent_id: Sending agent ID
            message_type: Type of message (info, question, handoff_request, etc.)
            content: Message content
            to_agent_id: Optional target agent (None for broadcast)
            message_metadata: Optional metadata

        Returns:
            Created AgentMessage
        """
        with self.db.get_session() as session:
            message = AgentMessage(
                thread_id=thread_id,
                from_agent_id=from_agent_id,
                to_agent_id=to_agent_id,
                message_type=message_type,
                content=content,
                message_metadata=message_metadata,
            )
            session.add(message)
            session.commit()
            session.refresh(message)
            session.expunge(message)

            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="agent.message.sent",
                        entity_type="message",
                        entity_id=message.id,
                        payload={
                            "thread_id": thread_id,
                            "from_agent_id": from_agent_id,
                            "to_agent_id": to_agent_id,
                            "message_type": message_type,
                            "message_metadata": message_metadata,
                        },
                    )
                )

            return message

    def get_thread_messages(
        self,
        thread_id: str,
        limit: int = 50,
        unread_only: bool = False,
    ) -> List[AgentMessage]:
        """
        Get messages in a thread.

        Args:
            thread_id: Thread ID
            limit: Maximum messages to return
            unread_only: Only return unread messages

        Returns:
            List of AgentMessage objects
        """
        with self.db.get_session() as session:
            query = session.query(AgentMessage).filter(
                AgentMessage.thread_id == thread_id
            ).order_by(AgentMessage.created_at.desc())

            if unread_only:
                query = query.filter(AgentMessage.read_at.is_(None))

            messages = query.limit(limit).all()

            for message in messages:
                session.expunge(message)

            return messages

    def mark_message_read(self, message_id: str) -> bool:
        """Mark a message as read."""
        from omoi_os.utils.datetime import utc_now

        with self.db.get_session() as session:
            message = session.query(AgentMessage).filter(
                AgentMessage.id == message_id
            ).first()
            if not message:
                return False

            message.read_at = utc_now()
            session.commit()
            return True

    # ---------------------------------------------------------------------
    # Handoff Protocol
    # ---------------------------------------------------------------------

    def request_handoff(
        self,
        from_agent_id: str,
        to_agent_id: str,
        task_id: str,
        reason: str,
        context: Optional[dict] = None,
    ) -> tuple[CollaborationThread, AgentMessage]:
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
        # Create handoff thread
        thread = self.create_thread(
            thread_type="handoff",
            participants=[from_agent_id, to_agent_id],
            task_id=task_id,
            thread_metadata={"initiator": from_agent_id, "reason": reason},
        )

        # Send handoff request message
        message = self.send_message(
            thread_id=thread.id,
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            message_type="handoff_request",
            content=reason,
            message_metadata=context,
        )

        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="agent.handoff.requested",
                    entity_type="handoff",
                    entity_id=thread.id,
                    payload={
                        "thread_id": thread.id,
                        "from_agent_id": from_agent_id,
                        "to_agent_id": to_agent_id,
                        "task_id": task_id,
                        "reason": reason,
                    },
                )
            )

        return thread, message

    def accept_handoff(
        self,
        thread_id: str,
        accepting_agent_id: str,
        message: str = "Handoff accepted",
    ) -> AgentMessage:
        """
        Accept a handoff request.

        Args:
            thread_id: Handoff thread ID
            accepting_agent_id: Agent accepting the handoff
            message: Acceptance message

        Returns:
            Created response message
        """
        # Get thread to find original requester
        thread = self.get_thread(thread_id)
        if not thread:
            raise ValueError(f"Thread {thread_id} not found")

        # Send acceptance message
        response = self.send_message(
            thread_id=thread_id,
            from_agent_id=accepting_agent_id,
            message_type="handoff_accepted",
            content=message,
        )

        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="agent.handoff.accepted",
                    entity_type="handoff",
                    entity_id=thread_id,
                    payload={
                        "thread_id": thread_id,
                        "accepting_agent_id": accepting_agent_id,
                        "task_id": thread.task_id,
                    },
                )
            )

        return response

    def decline_handoff(
        self,
        thread_id: str,
        declining_agent_id: str,
        reason: str,
    ) -> AgentMessage:
        """
        Decline a handoff request.

        Args:
            thread_id: Handoff thread ID
            declining_agent_id: Agent declining the handoff
            reason: Reason for declining

        Returns:
            Created response message
        """
        response = self.send_message(
            thread_id=thread_id,
            from_agent_id=declining_agent_id,
            message_type="handoff_declined",
            content=reason,
        )

        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="agent.handoff.declined",
                    entity_type="handoff",
                    entity_id=thread_id,
                    payload={
                        "thread_id": thread_id,
                        "declining_agent_id": declining_agent_id,
                        "reason": reason,
                    },
                )
            )

        return response

