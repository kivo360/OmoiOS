"""Task discovery model for tracking adaptive workflow branching."""

import uuid
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from whenever import Instant

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.task import Task


class TaskDiscovery(Base):
    """
    Records agent discoveries that spawn new branches in the workflow.

    Inspired by Hephaestus pattern: track WHY workflows branch and WHAT
    agents discovered that led to new work being created.

    Examples:
    - Bug discovered during validation → spawn fix task
    - Optimization opportunity found → spawn investigation
    - Ambiguity detected → spawn clarification task
    - New component discovered → spawn implementation task
    """

    __tablename__ = "task_discoveries"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Task that made the discovery",
    )
    discovery_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type: bug, optimization, clarification_needed, new_component, etc.",
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False, comment="What was discovered"
    )
    spawned_task_ids: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Array of task IDs spawned from this discovery",
    )
    discovered_at: Mapped[Instant] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
        comment="When the discovery was made",
    )
    priority_boost: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether discovery warranted priority escalation",
    )
    resolution_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="open",
        index=True,
        comment="Status: open, in_progress, resolved, invalid",
    )
    discovery_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional discovery metadata (evidence, context, etc.)",
    )

    # Relationships
    source_task: Mapped["Task"] = relationship(
        "Task", foreign_keys=[source_task_id], back_populates="discoveries"
    )

    def __repr__(self) -> str:
        return (
            f"<TaskDiscovery(id={self.id}, type={self.discovery_type}, "
            f"spawned={len(self.spawned_task_ids)})>"
        )

    def add_spawned_task(self, task_id: str) -> None:
        """Add a task ID to the spawned tasks list."""
        if not self.spawned_task_ids:
            self.spawned_task_ids = []
        if task_id not in self.spawned_task_ids:
            self.spawned_task_ids = self.spawned_task_ids + [
                task_id
            ]  # Create new list for JSONB mutation tracking

    def mark_resolved(self) -> None:
        """Mark discovery as resolved."""
        self.resolution_status = "resolved"

    def mark_invalid(self) -> None:
        """Mark discovery as invalid (false positive)."""
        self.resolution_status = "invalid"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "source_task_id": self.source_task_id,
            "discovery_type": self.discovery_type,
            "description": self.description,
            "spawned_task_ids": self.spawned_task_ids,
            "spawned_count": len(self.spawned_task_ids),
            "discovered_at": (
                self.discovered_at.isoformat() if self.discovered_at else None
            ),
            "priority_boost": self.priority_boost,
            "resolution_status": self.resolution_status,
            "metadata": self.discovery_metadata or {},
        }


# Discovery type constants for consistency
class DiscoveryType:
    """Common discovery types for task branching."""

    BUG_FOUND = "bug"
    OPTIMIZATION_OPPORTUNITY = "optimization"
    CLARIFICATION_NEEDED = "clarification_needed"
    NEW_COMPONENT = "new_component"
    SECURITY_ISSUE = "security_issue"
    PERFORMANCE_ISSUE = "performance_issue"
    MISSING_REQUIREMENT = "missing_requirement"
    INTEGRATION_ISSUE = "integration_issue"
    TECHNICAL_DEBT = "technical_debt"

    # Diagnostic types
    DIAGNOSTIC_STUCK = "diagnostic_stuck"
    DIAGNOSTIC_NO_RESULT = "diagnostic_no_result"
    DIAGNOSTIC_VALIDATION_LOOP = "diagnostic_validation_loop"
