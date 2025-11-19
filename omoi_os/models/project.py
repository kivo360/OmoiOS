"""Project model for multi-project support."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from omoi_os.models.ticket import Ticket
    from omoi_os.models.organization import Organization
    from omoi_os.models.user import User

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class Project(Base):
    """Project represents a collection of tickets and tasks."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: f"project-{uuid4()}"
    )
    
    # Organization relationship
    organization_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Creator
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # GitHub integration
    github_owner: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    github_repo: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    github_webhook_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    github_connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Project settings
    default_phase_id: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PHASE_BACKLOG"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active", index=True
    )  # active, archived, completed
    
    # Configuration
    settings: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="Project-specific settings (WIP limits, etc.)"
    )
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    
    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship(
        back_populates="projects"
    )
    creator: Mapped[Optional["User"]] = relationship(
        foreign_keys=[created_by]
    )
    tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket", back_populates="project", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        {"comment": "Projects organize tickets and tasks into logical groups"}
    )

