"""Reasoning chain models for tracking agent decisions and discoveries."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class ReasoningEvent(Base):
    """Tracks agent reasoning events, decisions, and discoveries for any entity."""

    __tablename__ = "reasoning_events"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: f"evt-{uuid4().hex[:8]}"
    )

    # Entity reference (polymorphic - can reference ticket, spec, task, etc.)
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of entity: ticket, spec, task, etc.",
    )
    entity_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
        comment="ID of the referenced entity",
    )

    # Event type
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Event type: ticket_created, task_spawned, discovery, agent_decision, blocking_added, code_change, error",
    )

    # Core event data
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    agent: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Agent that triggered the event"
    )

    # Complex data stored as JSONB
    details: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Event-specific details (context, reasoning, discovery_type, etc.)",
    )
    evidence: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        comment="Supporting evidence (type, content, link)",
    )
    decision: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Decision made (type, action, reasoning)",
    )

    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
        comment="When the event occurred",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = {
        "comment": "Stores agent reasoning events and decisions for entities"
    }
