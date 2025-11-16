"""Ticket model for workflow orchestration."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

if TYPE_CHECKING:
    from omoi_os.models.task import Task
    from omoi_os.models.phase_history import PhaseHistory

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class Ticket(Base):
    """Ticket represents a workflow request that generates multiple tasks."""

    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phase_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # pending, in_progress, completed, failed
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # CRITICAL, HIGH, MEDIUM, LOW
    previous_phase_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    context: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    context_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="ticket", cascade="all, delete-orphan"
    )
    phase_history: Mapped[list["PhaseHistory"]] = relationship(
        "PhaseHistory",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="PhaseHistory.created_at",
    )
