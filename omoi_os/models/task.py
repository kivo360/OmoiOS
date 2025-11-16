"""Task model for task queue management."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.ticket import Ticket


class Task(Base):
    """Task represents a single work unit that can be assigned to an agent."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    ticket_id: Mapped[str] = mapped_column(
        String, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    phase_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)  # analyze_requirements, implement_feature, etc.
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # CRITICAL, HIGH, MEDIUM, LOW
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # pending, assigned, running, completed, failed
    assigned_agent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    conversation_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # OpenHands conversation ID
    result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Task result/output
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="tasks")
