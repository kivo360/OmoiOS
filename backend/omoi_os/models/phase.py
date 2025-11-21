"""Phase model for workflow phase definitions."""

from typing import Optional, Dict, Any, List

from sqlalchemy import String, Integer, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base


class PhaseModel(Base):
    """
    Defines workflow phases with metadata and configuration.

    Enhanced with Hephaestus-style done definitions, expected outputs,
    and phase-specific instructions for adaptive workflow orchestration.
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
    allowed_transitions: Mapped[Optional[List[str]]] = mapped_column(
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

    # Hephaestus-inspired enhancements
    done_definitions: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Concrete, verifiable completion criteria (Hephaestus pattern)",
    )
    expected_outputs: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Expected artifacts: [{type: 'file', pattern: 'src/*.py', required: true}]",
    )
    phase_prompt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Phase-level system prompt/instructions for agents (Additional Notes)",
    )
    next_steps_guide: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Guidance on what happens after this phase completes",
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
            "done_definitions": self.done_definitions or [],
            "expected_outputs": self.expected_outputs or [],
            "phase_prompt": self.phase_prompt,
            "next_steps_guide": self.next_steps_guide or [],
            "configuration": self.configuration or {},
        }

    def can_transition_to(self, target_phase_id: str) -> bool:
        """Check if transition to target phase is allowed."""
        if not self.allowed_transitions:
            return False
        return target_phase_id in self.allowed_transitions

    def is_done_criteria_met(
        self, completed_criteria: List[str]
    ) -> tuple[bool, List[str]]:
        """
        Check if all done definitions are met.

        Args:
            completed_criteria: List of criteria that have been completed.

        Returns:
            Tuple of (all_met: bool, missing: List[str])
        """
        if not self.done_definitions:
            return True, []

        missing = [
            criterion
            for criterion in self.done_definitions
            if criterion not in completed_criteria
        ]

        return len(missing) == 0, missing

    def get_required_outputs(self) -> List[Dict[str, Any]]:
        """Get list of required outputs for this phase."""
        if not self.expected_outputs:
            return []

        return [
            output for output in self.expected_outputs if output.get("required", True)
        ]
