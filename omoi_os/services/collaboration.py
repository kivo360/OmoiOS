"""Collaboration service managing agent messaging threads and handoffs."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import asc, desc

from omoi_os.models.collaboration import (
    AgentHandoffRequest,
    CollaborationMessage,
    CollaborationThread,
)
from omoi_os.models.event import (
    AgentHandoffRequestedEvent,
    AgentMessageEvent,
    CollaborationThreadStartedEvent,
)
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.utils.datetime import utc_now


class CollaborationService:
    """Handles persistence and event fan-out for collaboration threads."""

    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
    ):
        self.db = db
        self.event_bus = event_bus

    # ------------------------------------------------------------------
    # Thread lifecycle
    # ------------------------------------------------------------------

    def create_thread(
        self,
        *,
        subject: str,
        context_type: str,
        context_id: str,
        created_by_agent_id: str,
        participants: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
    ) -> CollaborationThread:
        participants = self._normalize_agents(participants or [])
        if created_by_agent_id not in participants:
            participants.append(created_by_agent_id)

        timestamp = utc_now()
        with self.db.get_session() as session:
            thread = CollaborationThread(
                subject=subject,
                context_type=context_type,
                context_id=context_id,
                created_by_agent_id=created_by_agent_id,
                participants=participants,
                metadata=metadata,
                created_at=timestamp,
                updated_at=timestamp,
            )
            session.add(thread)
            session.flush()
            session.refresh(thread)

        self._publish_collaboration_started(thread)
        return thread

    def get_thread(self, thread_id: str) -> CollaborationThread:
        with self.db.get_session() as session:
            thread = session.get(CollaborationThread, thread_id)
            if not thread:
                raise ValueError(f"Thread {thread_id} not found")
            session.expunge(thread)
            return thread

    def list_threads(
        self,
        *,
        participant_agent_id: Optional[str] = None,
        context_type: Optional[str] = None,
        context_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[CollaborationThread]:
        with self.db.get_session() as session:
            query = session.query(CollaborationThread)
            if participant_agent_id:
                query = query.filter(
                    CollaborationThread.participants.contains([participant_agent_id])
                )
            if context_type:
                query = query.filter(CollaborationThread.context_type == context_type)
            if context_id:
                query = query.filter(CollaborationThread.context_id == context_id)

            threads = (
                query.order_by(desc(CollaborationThread.updated_at))
                .limit(limit)
                .all()
            )
            for thread in threads:
                session.expunge(thread)
            return threads

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    def send_message(
        self,
        *,
        thread_id: str,
        sender_agent_id: str,
        body: str,
        message_type: str = "text",
        target_agent_id: Optional[str] = None,
        payload: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> CollaborationMessage:
        timestamp = utc_now()
        with self.db.get_session() as session:
            thread = session.get(CollaborationThread, thread_id)
            if not thread:
                raise ValueError(f"Thread {thread_id} not found")

            participants = set(thread.participants or [])
            participants.add(sender_agent_id)
            if target_agent_id:
                participants.add(target_agent_id)
            thread.participants = self._normalize_agents(list(participants))
            thread.updated_at = timestamp
            thread.last_message_at = timestamp

            message = CollaborationMessage(
                thread_id=thread_id,
                sender_agent_id=sender_agent_id,
                target_agent_id=target_agent_id,
                message_type=message_type,
                body=body,
                payload=payload,
                metadata=metadata,
                created_at=timestamp,
            )
            session.add(message)
            session.flush()
            session.refresh(message)

        self._publish_message_sent(
            AgentMessageEvent(
                message_id=message.id,
                thread_id=thread_id,
                sender_agent_id=sender_agent_id,
                target_agent_id=target_agent_id,
                message_type=message_type,
                body_preview=self._body_preview(body),
                metadata=metadata,
            )
        )
        return message

    def list_messages(
        self, *, thread_id: str, limit: int = 50
    ) -> List[CollaborationMessage]:
        with self.db.get_session() as session:
            messages = (
                session.query(CollaborationMessage)
                .filter(CollaborationMessage.thread_id == thread_id)
                .order_by(asc(CollaborationMessage.created_at))
                .limit(limit)
                .all()
            )
            for message in messages:
                session.expunge(message)
            return messages

    # ------------------------------------------------------------------
    # Handoffs
    # ------------------------------------------------------------------

    def request_handoff(
        self,
        *,
        thread_id: str,
        requesting_agent_id: str,
        target_agent_id: Optional[str] = None,
        reason: Optional[str] = None,
        required_capabilities: Optional[List[str]] = None,
        ticket_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> AgentHandoffRequest:
        timestamp = utc_now()
        normalized_caps = self._normalize_tokens(required_capabilities or [])
        with self.db.get_session() as session:
            thread = session.get(CollaborationThread, thread_id)
            if not thread:
                raise ValueError(f"Thread {thread_id} not found")

            participants = set(thread.participants or [])
            participants.add(requesting_agent_id)
            if target_agent_id:
                participants.add(target_agent_id)
            thread.participants = self._normalize_agents(list(participants))
            thread.updated_at = timestamp

            handoff = AgentHandoffRequest(
                thread_id=thread_id,
                requesting_agent_id=requesting_agent_id,
                target_agent_id=target_agent_id,
                status="pending",
                required_capabilities=normalized_caps or None,
                reason=reason,
                ticket_id=ticket_id,
                task_id=task_id,
                metadata=metadata,
                created_at=timestamp,
            )
            session.add(handoff)
            session.flush()
            session.refresh(handoff)

        self._publish_handoff_requested(
            AgentHandoffRequestedEvent(
                handoff_id=handoff.id,
                thread_id=thread_id,
                requesting_agent_id=requesting_agent_id,
                target_agent_id=target_agent_id,
                status=handoff.status,
                required_capabilities=handoff.required_capabilities or [],
                reason=reason,
                task_id=task_id,
                ticket_id=ticket_id,
                metadata=metadata,
            )
        )
        return handoff

    def list_handoffs(
        self, *, thread_id: Optional[str] = None, status: Optional[str] = None
    ) -> List[AgentHandoffRequest]:
        with self.db.get_session() as session:
            query = session.query(AgentHandoffRequest)
            if thread_id:
                query = query.filter(AgentHandoffRequest.thread_id == thread_id)
            if status:
                query = query.filter(AgentHandoffRequest.status == status)
            handoffs = query.order_by(desc(AgentHandoffRequest.created_at)).all()
            for handoff in handoffs:
                session.expunge(handoff)
            return handoffs

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _publish_message_sent(self, payload: AgentMessageEvent) -> None:
        if self.event_bus:
            self.event_bus.publish_agent_message_sent(payload)

    def _publish_handoff_requested(self, payload: AgentHandoffRequestedEvent) -> None:
        if self.event_bus:
            self.event_bus.publish_agent_handoff_requested(payload)

    def _publish_collaboration_started(self, thread: CollaborationThread) -> None:
        if not self.event_bus:
            return
        event = CollaborationThreadStartedEvent(
            thread_id=thread.id,
            subject=thread.subject,
            context_type=thread.context_type,
            context_id=thread.context_id,
            created_by_agent_id=thread.created_by_agent_id,
            participants=thread.participants or [],
            metadata=thread.metadata,
        )
        self.event_bus.publish_agent_collaboration_started(event)

    def _normalize_agents(self, agent_ids: List[str]) -> List[str]:
        normalized = {agent_id.strip(): None for agent_id in agent_ids if agent_id}
        return sorted(normalized.keys())

    def _normalize_tokens(self, values: List[str]) -> List[str]:
        return sorted(
            {value.strip().lower() for value in values if value and value.strip()}
        )

    def _body_preview(self, body: str, max_length: int = 160) -> str:
        text = (body or "").strip()
        if len(text) <= max_length:
            return text
        return f"{text[: max_length - 3]}..."
