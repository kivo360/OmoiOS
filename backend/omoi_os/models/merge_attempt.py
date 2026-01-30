"""MergeAttempt model for audit trail of merge operations at convergence points.

Phase A: Foundation for DAG Merge Executor integration.

Tracks merge attempts when parallel tasks complete and their code changes
need to be merged before a continuation task can start. This provides:
- Audit trail for debugging merge failures
- Visibility into LLM conflict resolution decisions
- Metrics on real conflict patterns over time
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class MergeStatus(str, Enum):
    """Status of a merge attempt."""
    PENDING = "pending"         # Waiting for merge to start
    IN_PROGRESS = "in_progress" # Merge in progress
    COMPLETED = "completed"     # Merge completed successfully
    CONFLICT = "conflict"       # Conflicts detected, needs resolution
    RESOLVING = "resolving"     # LLM resolution in progress
    RESOLVED = "resolved"       # Conflicts resolved by LLM
    FAILED = "failed"           # Merge failed (after retries)
    MANUAL = "manual"           # Flagged for manual intervention


class MergeAttempt(Base):
    """MergeAttempt tracks merge operations at convergence points.

    When parallel tasks complete and a continuation task depends on all of them,
    a MergeAttempt is created to track the merging of their code changes into
    the ticket branch.

    Attributes:
        id: Unique merge attempt identifier (UUID)
        task_id: The continuation task that triggered this merge
        ticket_id: The ticket whose branch is being merged to
        spec_id: The spec containing the parallel tasks

        source_task_ids: List of parallel task IDs whose changes are being merged
        incoming_branches: Git branches to merge (if task-level branching)
        target_branch: Branch to merge into (usually ticket branch)

        merge_order: Ordered list of task IDs by conflict score (least first)
        conflict_scores: Dict mapping task_id -> conflict count from dry-run
        total_conflicts: Total number of conflicts across all merges

        status: Current status of the merge attempt
        success: Whether the merge completed successfully
        error_message: Error message if merge failed

        llm_invocations: Number of times LLM was called for conflict resolution
        llm_resolution_log: Detailed log of LLM decisions for each conflict
        llm_tokens_used: Total tokens used for conflict resolution
        llm_cost_usd: Estimated cost of LLM resolution

        created_at: When the merge attempt was initiated
        started_at: When merge actually started (after scheduling)
        completed_at: When merge finished (success or failure)
    """

    __tablename__ = "merge_attempts"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )

    # Related entities
    task_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Continuation task that triggered this merge",
    )
    ticket_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Ticket whose branch is target of merge",
    )
    spec_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("specs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Spec containing the parallel tasks",
    )

    # Merge sources
    source_task_ids: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        comment="List of parallel task IDs whose changes are being merged",
    )
    incoming_branches: Mapped[Optional[list[str]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Git branches to merge (if using task-level branches)",
    )
    target_branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Target branch for merge (usually ticket branch)",
    )

    # Conflict scoring and ordering
    merge_order: Mapped[Optional[list[str]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Task IDs in merge order (least conflicts first)",
    )
    conflict_scores: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Dict mapping task_id -> conflict count from dry-run",
    )
    total_conflicts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total number of conflicts detected",
    )

    # Status and outcome
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=MergeStatus.PENDING.value,
        index=True,
    )
    success: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        comment="Whether merge completed successfully (null if in progress)",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if merge failed",
    )

    # LLM conflict resolution tracking
    llm_invocations: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of LLM calls for conflict resolution",
    )
    llm_resolution_log: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Detailed log of LLM decisions: {file_path: {ours, theirs, resolved, reasoning}}",
    )
    llm_tokens_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total tokens consumed by LLM resolution",
    )
    llm_cost_usd: Mapped[float] = mapped_column(
        Integer,  # Store as cents to avoid float precision issues
        nullable=False,
        default=0,
        comment="Estimated cost of LLM resolution in cents",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When merge execution actually started",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When merge finished (success or failure)",
    )

    # Relationships (TYPE_CHECKING imports would go here if needed)
    # task: Mapped["Task"] = relationship("Task", back_populates="merge_attempts")
    # ticket: Mapped["Ticket"] = relationship("Ticket")

    def __repr__(self) -> str:
        return (
            f"<MergeAttempt(id={self.id[:8]}, task_id={self.task_id[:8]}, "
            f"status={self.status}, conflicts={self.total_conflicts})>"
        )

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate duration of merge attempt in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def has_conflicts(self) -> bool:
        """Check if this merge attempt has/had conflicts."""
        return self.total_conflicts > 0

    @property
    def required_llm_resolution(self) -> bool:
        """Check if LLM was needed for conflict resolution."""
        return self.llm_invocations > 0
