"""Specification models for project requirement and design management."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.project import Project


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
