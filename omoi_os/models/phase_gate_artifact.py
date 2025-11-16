"""Phase gate artifact model."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class PhaseGateArtifact(Base):
    """Artifacts collected for validating phase gates."""

    __tablename__ = "phase_gate_artifacts"

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
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    artifact_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    artifact_content: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    collected_by: Mapped[str] = mapped_column(String(255), nullable=False)
