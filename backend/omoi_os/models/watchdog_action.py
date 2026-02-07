"""Watchdog action model for remediation audit trail."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class WatchdogAction(Base):
    """WatchdogAction records all remediation actions for audit trail.

    Tracks remediation actions taken by watchdog agents:
    - Restart failed monitor agents
    - Failover to backup monitors
    - Escalate to Guardian when remediation fails
    """

    __tablename__ = "watchdog_actions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )

    # Action details
    action_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # restart, failover, escalate, quarantine

    target_agent_id: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )  # ID of the monitor agent being remediated

    remediation_policy: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # Name of the policy that triggered this action

    # Reason and audit
    reason: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Why this remediation was necessary

    initiated_by: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )  # Watchdog agent ID that initiated the action

    # Execution tracking
    executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # When the remediation was executed

    success: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, success, failed, escalated

    escalated_to_guardian: Mapped[str] = mapped_column(
        String(10), nullable=False, default="false"
    )  # Whether this was escalated to Guardian (stored as string for compatibility)

    guardian_action_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, index=True
    )  # If escalated, the GuardianAction ID

    # Detailed audit log
    audit_log: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # Full details: before/after state, policy config, results

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
