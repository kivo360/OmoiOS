"""Sandbox Event model for persisting agent events from sandbox execution.

Phase 4: Database Persistence for Sandbox Agents

IMPORTANT: Do NOT use 'metadata' as an attribute name - it's reserved by SQLAlchemy!
Use 'event_data' or similar for any JSON data fields.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class SandboxEvent(Base):
    """SandboxEvent represents an event emitted by an agent running in a sandbox.

    Events include tool usage, status updates, errors, and other agent activities.
    These are persisted for audit trails, debugging, and analytics.

    Attributes:
        id: Unique event identifier (UUID)
        sandbox_id: ID of the sandbox that generated this event
        spec_id: Optional ID of the spec this event is associated with
        event_type: Type of event (e.g., 'agent.started', 'agent.tool_use')
        event_data: JSON payload with event-specific data
        source: Source of the event ('agent', 'guardian', 'system')
        created_at: Timestamp when the event was recorded
    """

    __tablename__ = "sandbox_events"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    sandbox_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    spec_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("specs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Spec this event is associated with (for spec-driven development)",
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="agent", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )

    def __repr__(self) -> str:
        return f"<SandboxEvent(id={self.id}, sandbox_id={self.sandbox_id}, event_type={self.event_type})>"
