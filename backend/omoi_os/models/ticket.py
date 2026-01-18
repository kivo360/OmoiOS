"""Ticket model for workflow orchestration."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from omoi_os.models.task import Task
    from omoi_os.models.phase_history import PhaseHistory
    from omoi_os.models.playbook_entry import PlaybookEntry
    from omoi_os.models.playbook_change import PlaybookChange
    from omoi_os.models.project import Project
    from omoi_os.models.ticket_pull_request import TicketPullRequest
    from omoi_os.models.ticket_commit import TicketCommit

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

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
        String(50), nullable=False, index=True, default=lambda: "backlog"
    )  # backlog, analyzing, building, building-done, testing, done (REQ-TKT-SM-001)
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # CRITICAL, HIGH, MEDIUM, LOW
    previous_phase_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )

    # Blocking overlay mechanism (REQ-TKT-SM-001, REQ-TKT-BL-001)
    is_blocked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Blocked overlay flag (used alongside current status)",
    )
    blocked_reason: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Blocker classification: dependency, waiting_on_clarification, failing_checks, environment (REQ-TKT-BL-002)",
    )
    blocked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when ticket was marked as blocked",
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

    # Ticket dependencies for spec-driven workflows
    # Format: {"blocked_by": ["TKT-001", "TKT-002"], "blocks": ["TKT-003"]}
    dependencies: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Ticket dependencies: blocked_by and blocks other tickets",
    )

    # Embedding for semantic search and duplicate detection
    # Dimension must match EmbeddingSettings.dimensions (default 1536)
    embedding_vector: Mapped[Optional[list[float]]] = mapped_column(
        Vector(1536), nullable=True
    )

    # Approval fields (REQ-THA-005)
    approval_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="approved",
        index=True,
        comment="Approval status: pending_review, approved, rejected, timed_out (REQ-THA-001)",
    )
    approval_deadline_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Deadline for approval timeout (REQ-THA-005)",
    )
    requested_by_agent_id: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        index=True,
        comment="Agent ID that requested this ticket (REQ-THA-005)",
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for rejection if ticket was rejected (REQ-THA-005)",
    )

    # User ownership - required for filtering user's tickets
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who created/owns this ticket",
    )

    # Project relationship
    project_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    project: Mapped[Optional["Project"]] = relationship(
        "Project", back_populates="tickets"
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="ticket", cascade="all, delete-orphan"
    )
    phase_history: Mapped[list["PhaseHistory"]] = relationship(
        "PhaseHistory",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="PhaseHistory.created_at",
    )
    playbook_entries: Mapped[list["PlaybookEntry"]] = relationship(
        "PlaybookEntry",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    playbook_changes: Mapped[list["PlaybookChange"]] = relationship(
        "PlaybookChange",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    pull_requests: Mapped[list["TicketPullRequest"]] = relationship(
        "TicketPullRequest",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    commits: Mapped[list["TicketCommit"]] = relationship(
        "TicketCommit",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
