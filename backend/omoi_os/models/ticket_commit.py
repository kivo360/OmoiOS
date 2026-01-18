"""TicketCommit model for tracking commits linked to tickets."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.ticket import Ticket


class TicketCommit(Base):
    """Model to track commits linked to tickets."""

    __tablename__ = "ticket_commits"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    ticket_id: Mapped[str] = mapped_column(
        String, ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    agent_id: Mapped[str] = mapped_column(String, index=True)

    commit_sha: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    commit_message: Mapped[str] = mapped_column(Text, nullable=False)
    commit_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    files_changed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    insertions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    deletions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    files_list: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    link_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationship to ticket
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="commits")

    __table_args__ = (
        Index("idx_unique_ticket_commit", "ticket_id", "commit_sha", unique=True),
    )
