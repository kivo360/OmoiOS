"""User onboarding model for tracking onboarding progress."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Index, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.user import User


class UserOnboarding(Base):
    """User onboarding status and progress tracking."""

    __tablename__ = "user_onboarding"

    # Identity
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Progress tracking
    current_step: Mapped[str] = mapped_column(
        String(50), nullable=False, default="welcome"
    )
    completed_steps: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=[], nullable=False
    )
    completed_checklist_items: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=[], nullable=False
    )

    # Completion status
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Onboarding data (GitHub connection, selected repo, plan, etc.)
    onboarding_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Sync version for client-server sync
    sync_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="onboarding")

    @property
    def is_completed(self) -> bool:
        """Check if onboarding is completed."""
        return self.completed_at is not None

    __table_args__ = (
        Index("idx_user_onboarding_user_id", "user_id"),
        Index(
            "idx_user_onboarding_completed",
            "completed_at",
            postgresql_where="completed_at IS NOT NULL",
        ),
    )
