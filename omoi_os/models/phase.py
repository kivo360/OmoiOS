"""Phase model for workflow phase definitions."""

from typing import Optional, Dict, Any

from sqlalchemy import String, Integer, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base


class PhaseModel(Base):
    """
    Defines workflow phases with metadata and configuration.

    This table stores the actual phase definitions that tickets and tasks
    reference via their phase_id fields.
    """

    __tablename__ = "phases"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        comment="Phase ID (e.g., PHASE_IMPLEMENTATION)",
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Human-readable phase name"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Phase description and purpose"
    )
    sequence_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Order in the phase sequence (0-based)",
    )
    allowed_transitions: Mapped[Optional[list[str]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of phase IDs that can be transitioned to",
    )
    is_terminal: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this is a terminal phase (DONE, BLOCKED)",
    )
    configuration: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Phase-specific configuration (timeouts, requirements, etc.)",
    )

    def __repr__(self) -> str:
        return f"<Phase(id={self.id}, name={self.name}, order={self.sequence_order})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "sequence_order": self.sequence_order,
            "allowed_transitions": self.allowed_transitions or [],
            "is_terminal": self.is_terminal,
            "configuration": self.configuration or {},
        }

    def can_transition_to(self, target_phase_id: str) -> bool:
        """Check if transition to target phase is allowed."""
        if not self.allowed_transitions:
            return False
        return target_phase_id in self.allowed_transitions
