"""Agent status transition audit log model."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class AgentStatusTransition(Base):
    """
    Audit log for agent status transitions per REQ-ALM-004.

    Records all status changes with timestamps, reasons, and initiators
    for compliance and debugging.
    """

    __tablename__ = "agent_status_transitions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(
        String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[str] = mapped_column(String(50), nullable=False)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # Agent ID or user ID that initiated transition
    task_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    transitioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    transition_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, nullable=True
    )  # Additional context (error details, metrics, etc.)

    def __repr__(self) -> str:
        return f"<AgentStatusTransition(agent_id={self.agent_id}, {self.from_status} → {self.to_status})>"

