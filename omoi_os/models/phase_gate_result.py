"""Phase gate validation result model."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class PhaseGateResult(Base):
    """Stores validation outcome for phase gates."""

    __tablename__ = "phase_gate_results"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    ticket_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phase_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    gate_status: Mapped[str] = mapped_column(String(50), nullable=False)  # passed, failed
    validation_result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    validated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    validated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    blocking_reasons: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
    )
