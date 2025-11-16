"""Agent model for agent registry."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class Agent(Base):
    """Agent represents a registered worker, monitor, watchdog, or guardian agent."""

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    agent_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # worker, monitor, watchdog, guardian
    phase_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )  # For worker agents: which phase they handle
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # idle, running, degraded, failed
    capabilities: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # Tools, skills available to agent
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
