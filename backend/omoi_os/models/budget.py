"""Budget management models for cost control."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class BudgetScope(str, Enum):
    """Scope types for budget limits."""

    GLOBAL = "global"  # System-wide budget
    TICKET = "ticket"  # Per-ticket budget
    AGENT = "agent"  # Per-agent budget
    PHASE = "phase"  # Per-phase budget


class Budget(Base):
    """Budget limits and tracking for cost control.

    Supports different budget scopes (global, per-ticket, per-agent, per-phase).
    Triggers alerts when budget thresholds are reached.
    """

    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Budget scope
    scope_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # 'global', 'ticket', 'agent', 'phase'
    scope_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )  # ID of the scoped entity (null for global)

    # Budget amounts (in USD)
    limit_amount: Mapped[float] = mapped_column(
        Float, nullable=False
    )  # Maximum allowed spend
    spent_amount: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )  # Current spend
    remaining_amount: Mapped[float] = mapped_column(
        Float, nullable=False
    )  # Calculated: limit - spent

    # Time period
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )  # Null for indefinite

    # Alert configuration
    alert_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.8
    )  # Trigger alert at 80%
    alert_triggered: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Boolean flag

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    def __repr__(self) -> str:
        return (
            f"<Budget(id={self.id}, scope={self.scope_type}:{self.scope_id}, "
            f"limit=${self.limit_amount:.2f}, spent=${self.spent_amount:.2f}, "
            f"remaining=${self.remaining_amount:.2f})>"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "scope_type": self.scope_type,
            "scope_id": self.scope_id,
            "limit_amount": self.limit_amount,
            "spent_amount": self.spent_amount,
            "remaining_amount": self.remaining_amount,
            "period_start": (
                self.period_start.isoformat() if self.period_start else None
            ),
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "alert_threshold": self.alert_threshold,
            "alert_triggered": bool(self.alert_triggered),
            "utilization_percent": (
                (self.spent_amount / self.limit_amount * 100)
                if self.limit_amount > 0
                else 0
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def update_spent(self, amount: float) -> None:
        """Update spent amount and recalculate remaining."""
        self.spent_amount += amount
        self.remaining_amount = self.limit_amount - self.spent_amount

        # Check if alert threshold crossed
        if not self.alert_triggered and self.limit_amount > 0:
            utilization = self.spent_amount / self.limit_amount
            if utilization >= self.alert_threshold:
                self.alert_triggered = 1

    def is_exceeded(self) -> bool:
        """Check if budget limit has been exceeded."""
        return self.spent_amount >= self.limit_amount

    def remaining_percent(self) -> float:
        """Calculate remaining budget as percentage."""
        if self.limit_amount <= 0:
            return 0.0
        return (self.remaining_amount / self.limit_amount) * 100
