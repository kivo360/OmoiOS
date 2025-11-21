"""Task model for task queue management."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.cost_record import CostRecord
    from omoi_os.models.ticket import Ticket
    from omoi_os.models.task_memory import TaskMemory
    from omoi_os.models.task_discovery import TaskDiscovery
    from omoi_os.models.quality_metric import QualityMetric
    from omoi_os.models.validation_review import ValidationReview


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
    score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, index=True,
        comment="Dynamic scheduling score computed from priority, age, deadline, blocker count, and retry penalty (REQ-TQM-PRI-002)"
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # pending, assigned, running, completed, failed
    assigned_agent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    conversation_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # OpenHands conversation ID
    persistence_dir: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True,
        comment="OpenHands conversation persistence directory for resumption and intervention delivery"
    )
    result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Task result/output
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dependencies: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Task dependencies: {"depends_on": ["task_id_1", "task_id_2"]}
    required_capabilities: Mapped[Optional[list[str]]] = mapped_column(
        JSONB, nullable=True,
        comment="Required capabilities: ['python', 'fastapi', 'postgres'] (REQ-TQM-ASSIGN-001)"
    )  # Required agent capabilities for this task

    # Retry fields for error handling
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # Current retry attempt count
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)  # Maximum allowed retries

    # Timeout field for cancellation
    timeout_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Timeout in seconds

    # Dynamic scoring fields (REQ-TQM-PRI-002, REQ-TQM-DM-001)
    deadline_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True,
        comment="Optional SLA deadline for this task (REQ-TQM-PRI-003)"
    )
    parent_task_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True,
        comment="Parent task ID for branching and sub-tasks (REQ-TQM-DM-001)"
    )

    # Validation fields (REQ-VAL-DM-001)
    validation_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # Enables validation for this task
    validation_iteration: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Current validation iteration counter
    last_validation_feedback: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Last feedback text provided by validator
    review_done: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # Whether the latest validation cycle has completed successfully

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="tasks")
    memories: Mapped[list["TaskMemory"]] = relationship(
        "TaskMemory", back_populates="task", cascade="all, delete-orphan"
    )
    cost_records: Mapped[list["CostRecord"]] = relationship(
        "CostRecord", back_populates="task", cascade="all, delete-orphan"
    )
    discoveries: Mapped[list["TaskDiscovery"]] = relationship(
        "TaskDiscovery",
        foreign_keys="[TaskDiscovery.source_task_id]",
        back_populates="source_task",
        cascade="all, delete-orphan",
    )
    quality_metrics: Mapped[list["QualityMetric"]] = relationship(
        "QualityMetric", back_populates="task", cascade="all, delete-orphan"
    )
    validation_reviews: Mapped[list["ValidationReview"]] = relationship(
        "ValidationReview", back_populates="task", cascade="all, delete-orphan"
    )
