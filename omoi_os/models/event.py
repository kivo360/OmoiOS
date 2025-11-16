"""Event model for system-wide event logging."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base


class Event(Base):
    """Event represents a system-wide orchestration event (not OpenHands conversation events)."""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # TASK_ASSIGNED, TASK_COMPLETED, etc.
    entity_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # ticket, task, agent
    entity_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )
