"""Database models for agent collaboration threads, messages, and handoffs."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class CollaborationThread(Base):
    """Persistent conversation thread between agents."""

    __tablename__ = "collaboration_threads"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    context_type: Mapped[str] = mapped_column(String(50), nullable=False)
    context_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_by_agent_id: Mapped[str] = mapped_column(String, nullable=False)
    participants: Mapped[list[str]] = mapped_column(
        PG_ARRAY(String(100)), nullable=False, default=list
    )
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    messages = relationship(
        "CollaborationMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="CollaborationMessage.created_at",
    )


class CollaborationMessage(Base):
    """Individual agent-to-agent message entry."""

    __tablename__ = "collaboration_messages"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    thread_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("collaboration_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_agent_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    target_agent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    message_type: Mapped[str] = mapped_column(String(50), nullable=False, default="text")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )

    thread = relationship("CollaborationThread", back_populates="messages")


class AgentHandoffRequest(Base):
    """Handoff request metadata tracked alongside collaboration."""

    __tablename__ = "agent_handoff_requests"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    thread_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("collaboration_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requesting_agent_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    target_agent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    required_capabilities: Mapped[Optional[list[str]]] = mapped_column(
        PG_ARRAY(String(100)), nullable=True
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ticket_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    task_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    responded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    thread = relationship("CollaborationThread")
