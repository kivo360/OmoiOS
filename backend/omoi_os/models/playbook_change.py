"""Playbook change model for ACE workflow audit trail (REQ-MEM-ACE-003, REQ-MEM-DM-007)."""

import uuid
from typing import TYPE_CHECKING, Optional, Dict, Any

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from whenever import Instant

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.ticket import Ticket
    from omoi_os.models.playbook_entry import PlaybookEntry


class PlaybookChange(Base):
    """
    Playbook change record for audit trail (REQ-MEM-ACE-003, REQ-MEM-DM-007).

    All modifications to the playbook are recorded here with operation type,
    old/new content, delta, reason, and related memory ID.
    """

    __tablename__ = "playbook_changes"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    ticket_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Ticket (project) this change belongs to",
    )
    playbook_entry_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("playbook_entries.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Entry that was changed (null for add operations on deleted entries)",
    )

    # Operation type (REQ-MEM-DM-007)
    operation: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Operation type: add, update, delete (REQ-MEM-DM-007)",
    )

    # Content changes (REQ-MEM-DM-007)
    old_content: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Old content before change (REQ-MEM-DM-007)"
    )
    new_content: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="New content after change (REQ-MEM-DM-007)"
    )

    # Structured delta (REQ-MEM-DM-007)
    delta: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="Structured delta representation (REQ-MEM-DM-007)"
    )

    # Audit fields (REQ-MEM-DM-007)
    reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Reason for change (REQ-MEM-DM-007)"
    )
    related_memory_id: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        index=True,
        comment="Memory ID that triggered this change (REQ-MEM-DM-007)",
    )
    changed_at: Mapped[Instant] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
        comment="When this change was made (REQ-MEM-DM-007)",
    )
    changed_by: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, comment="Agent ID that made this change (REQ-MEM-DM-007)"
    )

    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="playbook_changes")
    entry: Mapped[Optional["PlaybookEntry"]] = relationship(
        "PlaybookEntry", back_populates="changes"
    )

    def __repr__(self) -> str:
        return (
            f"<PlaybookChange(id={self.id}, ticket_id={self.ticket_id}, "
            f"operation={self.operation}, changed_at={self.changed_at})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "playbook_entry_id": self.playbook_entry_id,
            "operation": self.operation,
            "old_content": self.old_content,
            "new_content": self.new_content,
            "delta": self.delta,
            "reason": self.reason,
            "related_memory_id": self.related_memory_id,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
            "changed_by": self.changed_by,
        }
