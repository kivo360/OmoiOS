"""Collaboration service for agent-to-agent messaging and handoffs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

import httpx
from sqlalchemy import or_

from omoi_os.logging import get_logger
from omoi_os.models.agent_message import AgentMessage, CollaborationThread
from omoi_os.models.task import Task
from omoi_os.models.agent import Agent
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent

logger = get_logger(__name__)


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
    # Sandbox Message Delivery
    # ---------------------------------------------------------------------

    def _deliver_sandbox_message(self, sandbox_id: str, message: str) -> bool:
        """Deliver a message to a sandbox agent via message injection API.

        Args:
            sandbox_id: Target sandbox ID
            message: Message content to deliver

        Returns:
            True if message was delivered successfully
        """
        # Get base URL from environment or default
        base_url = (
            os.environ.get("MCP_SERVER_URL", "http://localhost:18000")
            .replace("/mcp", "")
            .rstrip("/")
        )

        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(
                    f"{base_url}/api/v1/sandboxes/{sandbox_id}/messages",
                    json={
                        "content": message,
                        "message_type": "agent_collaboration",
                    },
                )

                if response.status_code == 200:
                    logger.info(
                        f"Successfully delivered collaboration message to sandbox {sandbox_id}"
                    )
                    return True
                else:
                    logger.warning(
                        f"Failed to deliver sandbox message: {response.status_code} - {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Failed to deliver sandbox message to {sandbox_id}: {e}")
            return False

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
            thread = (
                session.query(CollaborationThread)
                .filter(CollaborationThread.id == thread_id)
                .first()
            )
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
            thread = (
                session.query(CollaborationThread)
                .filter(CollaborationThread.id == thread_id)
                .first()
            )
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
                threads = [t for t in threads if agent_id in (t.participants or [])]

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

            # Deliver message to recipient if specified (Recommendation 4)
            if to_agent_id:
                self._deliver_message_to_agents(
                    message,
                    [to_agent_id],
                    is_broadcast=False,
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
            query = (
                session.query(AgentMessage)
                .filter(AgentMessage.thread_id == thread_id)
                .order_by(AgentMessage.created_at.desc())
            )

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
            message = (
                session.query(AgentMessage)
                .filter(AgentMessage.id == message_id)
                .first()
            )
            if not message:
                return False

            message.read_at = utc_now()
            session.commit()
            return True

    def get_agent_messages(
        self,
        agent_id: str,
        limit: int = 50,
        unread_only: bool = False,
    ) -> List[AgentMessage]:
        """
        Get all messages for an agent (sent to or from this agent).

        Args:
            agent_id: Agent ID
            limit: Maximum messages to return
            unread_only: Only return unread messages

        Returns:
            List of AgentMessage objects
        """
        with self.db.get_session() as session:
            query = (
                session.query(AgentMessage)
                .filter(
                    (AgentMessage.from_agent_id == agent_id)
                    | (AgentMessage.to_agent_id == agent_id)
                )
                .order_by(AgentMessage.created_at.desc())
            )

            if unread_only:
                query = query.filter(AgentMessage.read_at.is_(None))

            messages = query.limit(limit).all()

            for message in messages:
                session.expunge(message)

            return messages

    def get_or_create_thread(
        self,
        participants: List[str],
        ticket_id: Optional[str] = None,
        task_id: Optional[str] = None,
        thread_type: str = "consultation",
    ) -> CollaborationThread:
        """
        Get existing thread or create new one for given participants.

        Args:
            participants: List of agent IDs (must be exactly 2 for direct messages)
            ticket_id: Optional ticket ID for context
            task_id: Optional task ID for context
            thread_type: Type of thread (consultation, handoff, review)

        Returns:
            CollaborationThread (existing or newly created)
        """
        with self.db.get_session() as session:
            # Try to find existing active thread with same participants
            existing_threads = (
                session.query(CollaborationThread)
                .filter(
                    CollaborationThread.status == "active",
                    CollaborationThread.thread_type == thread_type,
                )
                .all()
            )

            # Check if any thread has exact same participants
            for thread in existing_threads:
                if set(thread.participants or []) == set(participants):
                    if ticket_id is None or thread.ticket_id == ticket_id:
                        if task_id is None or thread.task_id == task_id:
                            session.expunge(thread)
                            return thread

            # Create new thread
            thread = CollaborationThread(
                thread_type=thread_type,
                participants=participants,
                ticket_id=ticket_id,
                task_id=task_id,
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

    def broadcast_message(
        self,
        from_agent_id: str,
        message: str,
        message_type: str = "info",
        ticket_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> dict:
        """
        Broadcast a message to all active agents (simplified API - Recommendation 3).

        This method automatically:
        1. Gets all active agents
        2. Creates a broadcast thread
        3. Sends message to all agents
        4. Optionally saves to memory if message_type indicates discovery/warning

        Args:
            from_agent_id: Sending agent ID
            message: Message content
            message_type: Type of message (info, question, warning, discovery)
            ticket_id: Optional ticket ID for context
            task_id: Optional task ID for context

        Returns:
            Dictionary with success status and recipient count
        """

        with self.db.get_session() as session:
            # Get all active agents (excluding sender)
            active_statuses = ["working", "pending", "assigned", "idle"]
            active_agents = (
                session.query(Agent)
                .filter(
                    Agent.status.in_(active_statuses),
                    Agent.id != from_agent_id,
                )
                .all()
            )

            if not active_agents:
                return {
                    "success": True,
                    "recipient_count": 0,
                    "message": "No active agents to broadcast to",
                }

            recipient_ids = [agent.id for agent in active_agents]

            # Create broadcast thread with all participants
            thread = self.create_thread(
                thread_type="consultation",
                participants=[from_agent_id] + recipient_ids,
                ticket_id=ticket_id,
                task_id=task_id,
                thread_metadata={"broadcast": True, "message_type": message_type},
            )

            # Send message to all recipients (to_agent_id=None means broadcast in thread)
            message_obj = self.send_message(
                thread_id=thread.id,
                from_agent_id=from_agent_id,
                to_agent_id=None,  # None = broadcast
                message_type=message_type,
                content=message,
                message_metadata={
                    "broadcast": True,
                    "recipient_count": len(recipient_ids),
                },
            )

            # Deliver messages to agent conversations with prefixes (Recommendation 4)
            # This delivers messages to OpenHands conversations so agents see them immediately
            self._deliver_message_to_agents(
                message_obj,
                recipient_ids,
                is_broadcast=True,
            )

            # Auto-save to memory if discovery or warning (Recommendation 5)
            if message_type in ("discovery", "warning") and message:
                try:
                    from omoi_os.api.main import memory_service

                    if memory_service:
                        # Determine memory type based on message_type
                        memory_type_map = {
                            "discovery": "discovery",
                            "warning": "warning",
                        }
                        memory_type = memory_type_map.get(message_type, "discovery")

                        # Save to memory (async, non-blocking)
                        import asyncio

                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                # If loop is running, schedule as task
                                asyncio.create_task(
                                    self._save_message_to_memory(
                                        memory_service,
                                        message,
                                        memory_type,
                                        from_agent_id,
                                        ticket_id,
                                        task_id,
                                    )
                                )
                            else:
                                # If no loop, run in executor
                                loop.run_until_complete(
                                    self._save_message_to_memory(
                                        memory_service,
                                        message,
                                        memory_type,
                                        from_agent_id,
                                        ticket_id,
                                        task_id,
                                    )
                                )
                        except RuntimeError:
                            # No event loop, skip memory save (non-critical)
                            pass
                except Exception:
                    # Memory save failure is non-critical
                    pass

            return {
                "success": True,
                "recipient_count": len(recipient_ids),
                "message_id": message_obj.id,
                "thread_id": thread.id,
                "message": f"Message broadcast to {len(recipient_ids)} agent(s)",
            }

    async def _save_message_to_memory(
        self,
        memory_service,
        content: str,
        memory_type: str,
        agent_id: str,
        ticket_id: Optional[str],
        task_id: Optional[str],
    ) -> None:
        """Helper to save message to memory system (async)."""
        try:
            # Create a temporary task_id if we have task_id, otherwise use a placeholder
            # Memory service requires a task_id, so we'll use task_id if available
            if task_id:
                # Store execution summary in memory
                with self.db.get_session() as session:
                    memory_service.store_execution(
                        session=session,
                        task_id=task_id,
                        execution_summary=content,
                        success=True,
                        memory_type=memory_type,
                    )
                    session.commit()
        except Exception:
            # Non-critical failure
            pass

    def _deliver_message_to_agents(
        self,
        message: AgentMessage,
        recipient_ids: List[str],
        is_broadcast: bool = False,
    ) -> None:
        """
        Deliver message to agent OpenHands conversations with prefixes (Recommendation 4).

        This method finds each recipient agent's active conversation and delivers
        the message via OpenHands conversation.send_message() API, similar to
        Guardian interventions but with agent message prefixes.

        Args:
            message: AgentMessage to deliver
            recipient_ids: List of agent IDs to deliver to
            is_broadcast: Whether this is a broadcast message
        """
        from omoi_os.models.agent import Agent

        try:
            with self.db.get_session() as session:
                # Format message with prefix
                sender_id_short = (
                    message.from_agent_id[:8]
                    if len(message.from_agent_id) > 8
                    else message.from_agent_id
                )

                if is_broadcast:
                    formatted_message = (
                        f"[AGENT {sender_id_short} BROADCAST]: {message.content}"
                    )
                elif message.to_agent_id:
                    recipient_id_short = (
                        message.to_agent_id[:8]
                        if len(message.to_agent_id) > 8
                        else message.to_agent_id
                    )
                    formatted_message = f"[AGENT {sender_id_short} TO AGENT {recipient_id_short}]: {message.content}"
                else:
                    formatted_message = f"[AGENT {sender_id_short}]: {message.content}"

                # Deliver to each recipient
                for recipient_id in recipient_ids:
                    try:
                        # Find agent's active task - supports both sandbox and legacy modes
                        active_task = (
                            session.query(Task)
                            .filter(
                                or_(
                                    Task.assigned_agent_id == recipient_id,
                                    Task.sandbox_id.isnot(
                                        None
                                    ),  # Include sandbox tasks
                                ),
                                Task.status == "running",
                            )
                            .first()
                        )

                        if not active_task:
                            logger.debug(
                                f"No active task found for recipient {recipient_id[:8]}"
                            )
                            continue

                        # Route message delivery based on execution mode
                        if active_task.sandbox_id:
                            # Sandbox mode - use message injection API (sync)
                            self._deliver_sandbox_message(
                                active_task.sandbox_id, formatted_message
                            )
                        elif (
                            active_task.conversation_id and active_task.persistence_dir
                        ):
                            # Deliver via OpenHands Conversation API directly (similar to Guardian but for agent messages)
                            try:
                                from openhands.sdk import (
                                    Conversation,
                                    Agent as OpenHandsAgent,
                                )
                                from openhands.tools.preset.default import (
                                    get_default_agent,
                                )
                                from openhands.sdk import LLM
                                from omoi_os.config import load_llm_settings

                                # Get workspace directory from agent or task
                                workspace_dir = (
                                    active_task.result.get("workspace_dir")
                                    if active_task.result
                                    else None
                                )
                                if not workspace_dir:
                                    # Try to get from agent
                                    agent_model = (
                                        session.query(Agent)
                                        .filter_by(id=recipient_id)
                                        .first()
                                    )
                                    if agent_model and hasattr(
                                        agent_model, "workspace_dir"
                                    ):
                                        workspace_dir = agent_model.workspace_dir

                                if workspace_dir:
                                    # Create LLM and agent for conversation resumption
                                    llm_settings = load_llm_settings()
                                    if llm_settings.api_key:
                                        llm = LLM(
                                            model=llm_settings.model,
                                            api_key=llm_settings.api_key,
                                        )
                                        agent_instance: OpenHandsAgent = (
                                            get_default_agent(llm=llm, cli_mode=True)
                                        )

                                        # Resume conversation
                                        conversation = Conversation(
                                            conversation_id=active_task.conversation_id,
                                            persistence_dir=active_task.persistence_dir,
                                            agent=agent_instance,
                                            workspace=workspace_dir,
                                        )

                                        # Send message (already formatted with prefix)
                                        conversation.send_message(formatted_message)

                                        # Trigger processing if idle (non-blocking)
                                        from openhands.sdk.conversation.state import (
                                            AgentExecutionStatus,
                                        )

                                        if (
                                            conversation.state.agent_status
                                            == AgentExecutionStatus.IDLE
                                        ):
                                            import threading

                                            thread = threading.Thread(
                                                target=conversation.run, daemon=True
                                            )
                                            thread.start()
                            except Exception as delivery_error:
                                # Non-critical - message is still stored in database
                                logger.warning(
                                    f"Failed to deliver message via OpenHands API: {delivery_error}"
                                )
                    except Exception as e:
                        # Non-critical failure - message is still stored in database
                        logger.warning(
                            f"Failed to deliver message to agent {recipient_id[:8]}: {e}"
                        )
        except Exception as e:
            # Non-critical failure
            logger.warning(f"Failed to deliver messages to agents: {e}")

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
