"""Resource lock model for preventing conflicting task execution."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class ResourceLock(Base):
    """Resource lock prevents conflicting tasks from executing simultaneously."""

    __tablename__ = "resource_locks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    resource_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True, unique=True)
    task_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    lock_type: Mapped[str] = mapped_column(String(50), nullable=False, default="exclusive")  # exclusive, shared
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # Optimistic locking version
