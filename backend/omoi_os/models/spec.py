"""Specification models for project requirement and design management."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.project import Project
    from omoi_os.models.user import User
    from omoi_os.models.ticket import Ticket


class Spec(Base):
    """Specification represents a project specification with requirements and design."""

    __tablename__ = "specs"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: f"spec-{uuid4()}"
    )
    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who created the spec",
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft",
        index=True,
        comment="draft, requirements, design, executing, completed",
    )
    archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether the spec is archived (soft delete)",
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the spec was archived",
    )
    phase: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Requirements",
        comment="Requirements, Design, Implementation, Testing, Done",
    )

    # Progress metrics
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    test_coverage: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    active_agents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    linked_tickets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Design artifact (stored as JSONB)
    design: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Design artifact: {architecture, data_model, api_spec}",
    )

    # Execution metrics (stored as JSONB)
    execution: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Execution metrics: {overall_progress, test_coverage, tests_total, etc.}",
    )

    # Approval tracking
    requirements_approved: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    requirements_approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    design_approved: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    design_approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # State machine phase tracking
    current_phase: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="explore",
        index=True,
        comment="State machine phase: explore, requirements, design, tasks, sync, complete",
    )
    phase_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Accumulated phase outputs: {explore: {...}, requirements: {...}, ...}",
    )
    session_transcripts: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Base64-encoded transcripts per phase for session resumption",
    )
    last_checkpoint_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the last checkpoint was saved",
    )
    last_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Last error message from phase execution",
    )
    phase_attempts: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Retry attempts per phase: {explore: 1, requirements: 2, ...}",
    )

    # Context metadata (for tracking source ticket, workflow mode, etc.)
    spec_context: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Context metadata: {source_ticket_id, workflow_mode, ...}",
    )

    # GitHub/PR tracking for spec completion
    branch_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Git branch name for this spec (e.g., spec/abc123-feature-name)",
    )
    pull_request_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="GitHub PR URL after spec completion",
    )
    pull_request_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="GitHub PR number for tracking",
    )

    # Deduplication support (pgvector for efficient similarity search)
    embedding_vector: Mapped[Optional[list[float]]] = mapped_column(
        Vector(1536),  # pgvector native type for cosine similarity
        nullable=True,
        comment="Embedding vector (1536 dims) for semantic deduplication within project",
    )
    content_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="SHA256 hash of normalized title+description for exact match dedup",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="specs")
    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id],
        lazy="select",
    )
    requirements: Mapped[list["SpecRequirement"]] = relationship(
        "SpecRequirement",
        back_populates="spec",
        cascade="all, delete-orphan",
        order_by="SpecRequirement.created_at",
    )
    tasks: Mapped[list["SpecTask"]] = relationship(
        "SpecTask",
        back_populates="spec",
        cascade="all, delete-orphan",
        order_by="SpecTask.created_at",
    )
    versions: Mapped[list["SpecVersion"]] = relationship(
        "SpecVersion",
        back_populates="spec",
        cascade="all, delete-orphan",
        order_by="SpecVersion.created_at.desc()",
    )
    tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        back_populates="spec",
    )


class SpecRequirement(Base):
    """Requirement within a specification using EARS format."""

    __tablename__ = "spec_requirements"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: f"req-{uuid4()}"
    )
    spec_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    condition: Mapped[str] = mapped_column(
        Text, nullable=False, comment="EARS 'WHEN' clause"
    )
    action: Mapped[str] = mapped_column(
        Text, nullable=False, comment="EARS 'THE SYSTEM SHALL' clause"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
        comment="pending, in_progress, completed",
    )
    linked_design: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Reference to design component"
    )

    # Deduplication support (pgvector for efficient similarity search)
    embedding_vector: Mapped[Optional[list[float]]] = mapped_column(
        Vector(1536),  # pgvector native type for cosine similarity
        nullable=True,
        comment="Embedding vector (1536 dims) for semantic deduplication within spec",
    )
    content_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="SHA256 hash of normalized condition+action for exact match dedup",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    spec: Mapped["Spec"] = relationship("Spec", back_populates="requirements")
    criteria: Mapped[list["SpecAcceptanceCriterion"]] = relationship(
        "SpecAcceptanceCriterion",
        back_populates="requirement",
        cascade="all, delete-orphan",
        order_by="SpecAcceptanceCriterion.created_at",
    )


class SpecAcceptanceCriterion(Base):
    """Acceptance criterion for a requirement."""

    __tablename__ = "spec_acceptance_criteria"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: f"crit-{uuid4()}"
    )
    requirement_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("spec_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Deduplication support (hash only - criteria are short)
    content_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="SHA256 hash of normalized text for exact match dedup within requirement",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    requirement: Mapped["SpecRequirement"] = relationship(
        "SpecRequirement", back_populates="criteria"
    )


class SpecTask(Base):
    """Task linked to a specification."""

    __tablename__ = "spec_tasks"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: f"spec-task-{uuid4()}"
    )
    spec_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phase: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
        comment="pending, in_progress, completed, blocked",
    )
    assigned_agent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    dependencies: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, default=list
    )
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Deduplication support (pgvector for efficient similarity search)
    embedding_vector: Mapped[Optional[list[float]]] = mapped_column(
        Vector(1536),  # pgvector native type for cosine similarity
        nullable=True,
        comment="Embedding vector (1536 dims) for semantic deduplication within spec",
    )
    content_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="SHA256 hash of normalized title+description for exact match dedup",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    spec: Mapped["Spec"] = relationship("Spec", back_populates="tasks")


class SpecVersion(Base):
    """Version history entry for a specification."""

    __tablename__ = "spec_versions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: f"spec-ver-{uuid4()}"
    )
    spec_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    change_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="created, updated, requirements_approved, design_approved, phase_changed",
    )
    change_summary: Mapped[str] = mapped_column(Text, nullable=False)
    change_details: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Detailed change information: {field: {old, new}}",
    )
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Snapshot of key fields at this version
    snapshot: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Snapshot of spec state at this version",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    # Relationships
    spec: Mapped["Spec"] = relationship("Spec", back_populates="versions")
