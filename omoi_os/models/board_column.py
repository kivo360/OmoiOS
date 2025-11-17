"""Board column model for Kanban visualization."""

from typing import Optional, List, Dict, Any

from sqlalchemy import String, Integer, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base


class BoardColumn(Base):
    """
    Kanban board column configuration.

    Maps workflow phases to visual board columns with WIP limits
    and progression rules.
    """

    __tablename__ = "board_columns"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        comment="Column ID (e.g., 'analyzing', 'building')",
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Display name (e.g., '🔍 Analyzing')"
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Column purpose description"
    )
    sequence_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Left-to-right order on the board (0-based)",
    )
    phase_mapping: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Which phase IDs map to this column (array of phase IDs)",
    )
    wip_limit: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Work-in-progress limit (null = unlimited)",
    )
    is_terminal: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this is an end column (done/blocked)",
    )
    auto_transition_to: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Column ID to auto-transition to on completion (null = manual)",
    )
    color_theme: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Visual theme: blue, green, yellow, red, gray",
    )

    def __repr__(self) -> str:
        return (
            f"<BoardColumn(id={self.id}, name={self.name}, "
            f"order={self.sequence_order}, wip={self.wip_limit})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "sequence_order": self.sequence_order,
            "phase_mapping": self.phase_mapping,
            "wip_limit": self.wip_limit,
            "is_terminal": self.is_terminal,
            "auto_transition_to": self.auto_transition_to,
            "color_theme": self.color_theme,
        }

    def includes_phase(self, phase_id: str) -> bool:
        """Check if a phase maps to this column."""
        return phase_id in self.phase_mapping

    def can_accept_more_work(self, current_count: int) -> bool:
        """Check if column can accept more tickets (WIP limit check)."""
        if self.wip_limit is None:
            return True
        return current_count < self.wip_limit
