"""Event model and typed collaboration event schemas."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class Event(Base):
    """Event represents a system-wide orchestration event (not OpenHands conversation events)."""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # TASK_ASSIGNED, TASK_COMPLETED, etc.
    entity_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # ticket, task, agent
    entity_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )


class AgentCollaborationTopics:
    """Centralized topic constants for collaboration events."""

    MESSAGE_SENT = "agent.message.sent"
    HANDOFF_REQUESTED = "agent.handoff.requested"
    COLLABORATION_STARTED = "agent.collab.started"


@dataclass(frozen=True)
class AgentMessageEvent:
    """Schema for agent.message.sent payloads."""

    message_id: str
    thread_id: str
    sender_agent_id: str
    target_agent_id: Optional[str]
    message_type: str
    body_preview: str
    metadata: Optional[dict] = None


@dataclass(frozen=True)
class AgentHandoffRequestedEvent:
    """Schema for agent.handoff.requested payloads."""

    handoff_id: str
    thread_id: str
    requesting_agent_id: str
    target_agent_id: Optional[str]
    status: str
    required_capabilities: List[str]
    reason: Optional[str] = None
    task_id: Optional[str] = None
    ticket_id: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass(frozen=True)
class CollaborationThreadStartedEvent:
    """Schema for agent.collab.started payloads."""

    thread_id: str
    subject: str
    context_type: str
    context_id: str
    created_by_agent_id: str
    participants: List[str]
    metadata: Optional[dict] = None
