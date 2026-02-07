"""Phase history model tracking ticket transitions."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.ticket import Ticket


class PhaseHistory(Base):
    """Track ticket phase transitions."""

    __tablename__ = "phase_history"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    ticket_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_phase: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_phase: Mapped[str] = mapped_column(String(50), nullable=False)
    transition_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transitioned_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    artifacts: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )

    ticket: Mapped["Ticket"] = relationship(
        "Ticket", back_populates="phase_history", lazy="joined"
    )


__all__ = ["PhaseHistory"]
