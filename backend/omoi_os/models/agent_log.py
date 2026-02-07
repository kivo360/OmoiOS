"""Agent log model for trajectory analysis and monitoring."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class AgentLog(Base):
    """Agent log entries for trajectory analysis and monitoring.

    Stores agent output, events, and activity logs for use by
    the intelligent monitoring system.
    """

    __tablename__ = "agent_logs"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    agent_id: Mapped[str] = mapped_column(
        String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    log_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # input, output, error, exception, intervention, etc.
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # Additional structured context
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )

    def __repr__(self) -> str:
        return f"<AgentLog(agent_id={self.agent_id}, type={self.log_type}, created_at={self.created_at})>"
