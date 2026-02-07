"""Validation review model for validation system."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.agent import Agent
    from omoi_os.models.task import Task


class ValidationReview(Base):
    """Validation review artifact for task validation iterations."""

    __tablename__ = "validation_reviews"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    task_id: Mapped[str] = mapped_column(
        String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    validator_agent_id: Mapped[str] = mapped_column(
        String, ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    iteration_number: Mapped[int] = mapped_column(Integer, nullable=False)
    validation_passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    recommendations: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True
    )  # List of strings
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="validation_reviews")
    validator_agent: Mapped["Agent"] = relationship(
        "Agent", foreign_keys=[validator_agent_id]
    )
