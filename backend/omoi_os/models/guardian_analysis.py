"""SQLAlchemy ORM models for intelligent monitoring tables."""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional, Dict, Any
from uuid import uuid4, UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    Interval,
    String,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    pass


class GuardianAnalysis(Base):
    """SQLAlchemy ORM model for guardian_analyses table."""

    __tablename__ = "guardian_analyses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    current_phase: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    trajectory_aligned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    alignment_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    needs_steering: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    steering_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    steering_recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    trajectory_summary: Mapped[str] = mapped_column(Text, nullable=False)
    last_claude_message_marker: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    accumulated_goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_focus: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    session_duration: Mapped[Optional[timedelta]] = mapped_column(
        Interval, nullable=True
    )
    conversation_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        Index("idx_guardian_analyses_agent_created", "agent_id", "created_at"),
    )


class ConductorAnalysisModel(Base):
    """SQLAlchemy ORM model for conductor_analyses table."""

    __tablename__ = "conductor_analyses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    cycle_id: Mapped[UUID] = mapped_column(nullable=False)
    coherence_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    system_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    num_agents: Mapped[int] = mapped_column(Integer, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    termination_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    coordination_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationship to detected duplicates
    duplicates: Mapped[list["DetectedDuplicateModel"]] = relationship(
        "DetectedDuplicateModel",
        back_populates="conductor_analysis",
        cascade="all, delete-orphan",
    )


class DetectedDuplicateModel(Base):
    """SQLAlchemy ORM model for detected_duplicates table."""

    __tablename__ = "detected_duplicates"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    conductor_analysis_id: Mapped[UUID] = mapped_column(
        ForeignKey("conductor_analyses.id"), nullable=False, index=True
    )
    agent1_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    agent2_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    work_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resources: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    # Relationship back to conductor analysis
    conductor_analysis: Mapped["ConductorAnalysisModel"] = relationship(
        "ConductorAnalysisModel", back_populates="duplicates"
    )

    __table_args__ = (Index("idx_duplicates_agents", "agent1_id", "agent2_id"),)


class SteeringInterventionModel(Base):
    """SQLAlchemy ORM model for steering_interventions table."""

    __tablename__ = "steering_interventions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    steering_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )

    __table_args__ = (Index("idx_steering_agent_created", "agent_id", "created_at"),)
