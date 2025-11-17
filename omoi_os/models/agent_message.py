"""Agent messaging and collaboration models."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class AgentMessage(Base):
    """Agent-to-agent message for collaboration and handoffs."""

    __tablename__ = "agent_messages"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    thread_id: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )  # Conversation thread identifier
    from_agent_id: Mapped[str] = mapped_column(
        String, ForeignKey("agents.id"), nullable=False, index=True
    )
    to_agent_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("agents.id"), nullable=True, index=True
    )  # None for broadcast
    message_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # request_handoff, send_message, broadcast, etc.
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # Additional context (task_id, ticket_id, etc.)
    
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class CollaborationThread(Base):
    """Collaboration thread tracking agent conversations."""

    __tablename__ = "collaboration_threads"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    thread_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # handoff, review, consultation
    ticket_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("tickets.id"), nullable=True, index=True
    )
    task_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("tasks.id"), nullable=True, index=True
    )
    participants: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False
    )  # List of agent IDs
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active"
    )  # active, resolved, abandoned
    thread_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

