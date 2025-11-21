"""Resource locking model for preventing conflicting task execution."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class ResourceLock(Base):
    """Resource lock to prevent conflicting task operations."""

    __tablename__ = "resource_locks"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    resource_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # file, database, service, etc.
    resource_id: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )  # Specific resource identifier
    locked_by_task_id: Mapped[str] = mapped_column(
        String, ForeignKey("tasks.id"), nullable=False, index=True
    )
    locked_by_agent_id: Mapped[str] = mapped_column(
        String, ForeignKey("agents.id"), nullable=False, index=True
    )
    lock_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="exclusive"
    )  # exclusive, shared

    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # Optional expiration for automatic cleanup
    released_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
