"""TicketPullRequest model for tracking PRs linked to tickets."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.ticket import Ticket


class TicketPullRequest(Base):
    """Model to track PRs linked to tickets for automatic task completion on merge."""

    __tablename__ = "ticket_pull_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    ticket_id: Mapped[str] = mapped_column(
        String, ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )

    # GitHub PR identifiers
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pr_title: Mapped[str] = mapped_column(String(500), nullable=False)
    pr_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Branch information
    head_branch: Mapped[str] = mapped_column(String(200), nullable=False)
    base_branch: Mapped[str] = mapped_column(String(200), nullable=False)

    # Repository information
    repo_owner: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    repo_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # PR state (open, merged, closed)
    state: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open", index=True
    )
    html_url: Mapped[str] = mapped_column(String(500), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    merged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # GitHub user who opened the PR
    github_user: Mapped[str] = mapped_column(String(200), nullable=False)

    # Merge commit SHA (populated when merged)
    merge_commit_sha: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Relationship to ticket
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="pull_requests")

    __table_args__ = (
        Index("idx_unique_ticket_pr", "ticket_id", "pr_number", unique=True),
        Index("idx_pr_repo", "repo_owner", "repo_name", "pr_number"),
    )
