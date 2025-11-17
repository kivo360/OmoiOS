"""Guardian action model for emergency intervention audit trail."""

from datetime import datetime
from enum import IntEnum
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class AuthorityLevel(IntEnum):
    """Authority hierarchy for agent actions.
    
    Higher values have more authority to override lower levels.
    """
    WORKER = 1
    WATCHDOG = 2
    MONITOR = 3
    GUARDIAN = 4
    SYSTEM = 5


class GuardianAction(Base):
    """GuardianAction records all emergency interventions for audit trail.
    
    Tracks who initiated an action, what authority level was required,
    whether it was approved, when it was executed, and if it was reverted.
    """

    __tablename__ = "guardian_actions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    
    # Action details
    action_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # cancel_task, reallocate_capacity, override_priority, spawn_agent
    
    target_entity: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # task_id, agent_id, or other entity identifier
    
    authority_level: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # AuthorityLevel value
    
    # Reason and audit
    reason: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Why this intervention was necessary
    
    initiated_by: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )  # Agent ID or user ID who initiated
    
    approved_by: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # If approval was required, who approved it
    
    # Execution tracking
    executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # When the intervention was executed
    
    reverted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # If reverted, when it was rolled back
    
    # Detailed audit log
    audit_log: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # Full details: before/after state, parameters, results
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

