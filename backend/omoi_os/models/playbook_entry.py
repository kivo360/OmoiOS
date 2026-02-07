"""Playbook entry model for ACE workflow (REQ-MEM-ACE-003)."""

import uuid
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from sqlalchemy import (
    String,
    Text,
    Boolean,
    Integer,
    Float,
    DateTime,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from whenever import Instant

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.ticket import Ticket
    from omoi_os.models.playbook_change import PlaybookChange


class PlaybookEntry(Base):
    """
    Playbook entry storing knowledge bullets for tickets (REQ-MEM-ACE-003).

    Playbook entries are automatically created and updated by the Curator phase
    of the ACE workflow. They store patterns, gotchas, best practices, and
    other learnings from task executions.
    """

    __tablename__ = "playbook_entries"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    ticket_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Ticket (project) this playbook entry belongs to",
    )

    # Content
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Playbook entry content (REQ-MEM-ACE-003)"
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Category: dependencies, architecture, gotchas, patterns, etc.",
    )

    # Embedding for semantic search (REQ-MEM-ACE-002)
    embedding: Mapped[Optional[List[float]]] = mapped_column(
        ARRAY(Float, dimensions=1),
        nullable=True,
        comment="1536-dimensional embedding vector for similarity search",
    )

    # Metadata
    tags: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String(100)),
        nullable=True,
        comment="Tags for filtering and categorization",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        index=True,
        comment="Priority level (higher = more important)",
    )

    # Links to memories that support this entry (REQ-MEM-ACE-002)
    supporting_memory_ids: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Memory IDs that support this playbook entry",
    )

    # Lifecycle
    created_at: Mapped[Instant] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
        comment="When this entry was created",
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, comment="Agent ID that created this entry"
    )
    updated_at: Mapped[Instant] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        comment="When this entry was last updated",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this entry is active (soft delete)",
    )

    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="playbook_entries")
    changes: Mapped[List["PlaybookChange"]] = relationship(
        "PlaybookChange", back_populates="entry", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<PlaybookEntry(id={self.id}, ticket_id={self.ticket_id}, "
            f"category={self.category}, is_active={self.is_active})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "content": self.content,
            "category": self.category,
            "tags": self.tags,
            "priority": self.priority,
            "supporting_memory_ids": self.supporting_memory_ids,
            "has_embedding": self.embedding is not None,
            "embedding_dimensions": (len(self.embedding) if self.embedding else 0),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
        }
