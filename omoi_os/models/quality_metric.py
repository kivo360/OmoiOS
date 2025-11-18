"""Quality metric model for advanced quality validation."""

import uuid
from typing import TYPE_CHECKING, Optional, Dict, Any

from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from whenever import Instant

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.task import Task


class QualityMetric(Base):
    """
    Records quality measurements for task executions.

    Tracks code quality metrics like test coverage, lint scores,
    complexity, and custom quality checks.
    """

    __tablename__ = "quality_metrics"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Task being measured",
    )
    metric_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type: coverage, lint, complexity, security, performance",
    )
    metric_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Specific metric name"
    )
    value: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Measured value"
    )
    threshold: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Required threshold"
    )
    passed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, index=True, comment="Whether threshold was met"
    )
    measured_at: Mapped[Instant] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
        comment="When measurement was taken",
    )
    measurement_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional measurement context (tool versions, config, etc.)",
    )

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="quality_metrics")

    def __repr__(self) -> str:
        return (
            f"<QualityMetric(id={self.id}, type={self.metric_type}, "
            f"name={self.metric_name}, value={self.value}, passed={self.passed})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "metric_type": self.metric_type,
            "metric_name": self.metric_name,
            "value": self.value,
            "threshold": self.threshold,
            "passed": self.passed,
            "measured_at": self.measured_at.isoformat() if self.measured_at else None,
            "metadata": self.measurement_metadata or {},
        }


# Metric type constants
class MetricType:
    """Common quality metric types."""

    COVERAGE = "coverage"
    LINT = "lint"
    COMPLEXITY = "complexity"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"

