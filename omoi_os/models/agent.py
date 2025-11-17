"""Agent model for agent registry."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.cost_record import CostRecord


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
    capabilities: Mapped[list[str]] = mapped_column(
        PG_ARRAY(String(100)), nullable=False, default=list
    )  # Tools, skills available to agent
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    health_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unknown", index=True
    )
    tags: Mapped[Optional[list[str]]] = mapped_column(
        PG_ARRAY(String(50)), nullable=True
    )
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    # Relationships
    cost_records: Mapped[list["CostRecord"]] = relationship(
        "CostRecord", back_populates="agent", cascade="all, delete-orphan"
    )
