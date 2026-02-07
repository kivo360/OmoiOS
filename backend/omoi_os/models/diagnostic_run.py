"""Diagnostic run model for workflow stuck detection and recovery."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class DiagnosticRun(Base):
    """Diagnostic intervention tracking.

    Records when the diagnostic agent was triggered to analyze and recover
    a stuck workflow. Tracks what conditions triggered it, what analysis
    was performed, and what recovery tasks were created.
    """

    __tablename__ = "diagnostic_runs"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    workflow_id: Mapped[str] = mapped_column(
        String, ForeignKey("tickets.id"), nullable=False, index=True
    )
    diagnostic_agent_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("agents.id"), nullable=True
    )
    diagnostic_task_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("tasks.id"), nullable=True
    )

    # Trigger context
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    total_tasks_at_trigger: Mapped[int] = mapped_column(Integer, nullable=False)
    done_tasks_at_trigger: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_tasks_at_trigger: Mapped[int] = mapped_column(Integer, nullable=False)
    time_since_last_task_seconds: Mapped[int] = mapped_column(Integer, nullable=False)

    # Recovery tracking
    tasks_created_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tasks_created_ids: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # Array of task IDs created by diagnostic

    # Analysis storage
    workflow_goal: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # From result_criteria config
    phases_analyzed: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # Phase status snapshot
    agents_reviewed: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # Recent agent summaries
    diagnosis: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Diagnostic agent's analysis

    # Lifecycle
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="created", index=True
    )  # created, running, completed, failed

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
