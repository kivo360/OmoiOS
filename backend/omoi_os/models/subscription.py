"""Subscription model for recurring billing with tier-based limits.

Manages subscription tiers (Starter, Pro, Team, Enterprise, Lifetime, BYO)
with usage limits and Stripe integration.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.billing import BillingAccount
    from omoi_os.models.organization import Organization


class SubscriptionTier(str, Enum):
    """Available subscription tiers."""

    FREE = "free"  # Default free tier (5 workflows/month, 1 agent)
    PRO = "pro"  # $50/month - 100 workflows, 5 agents, BYO keys
    TEAM = "team"  # $150/month - 500 workflows, 10 agents, BYO keys
    ENTERPRISE = "enterprise"  # Custom - Unlimited
    LIFETIME = (
        "lifetime"  # $299 one-time - 50 workflows/month, 5 agents, early BYO access
    )


class SubscriptionStatus(str, Enum):
    """Status of a subscription."""

    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    PAUSED = "paused"
    INCOMPLETE = "incomplete"  # Awaiting payment confirmation


# Tier configuration - defines limits for each tier
# Pricing: Starter $0, Pro $299, Team $999, Enterprise custom
TIER_LIMITS = {
    SubscriptionTier.FREE: {
        "workflows_limit": 5,
        "agents_limit": 1,
        "storage_limit_gb": 2,
        "price_monthly": 0,
        "byo_keys": False,
    },
    SubscriptionTier.PRO: {
        "workflows_limit": 50,
        "agents_limit": 3,
        "storage_limit_gb": 50,
        "price_monthly": 299,
        "byo_keys": True,
    },
    SubscriptionTier.TEAM: {
        "workflows_limit": -1,  # Unlimited
        "agents_limit": 10,
        "storage_limit_gb": 500,
        "price_monthly": 999,
        "byo_keys": True,
    },
    SubscriptionTier.ENTERPRISE: {
        "workflows_limit": -1,  # Unlimited
        "agents_limit": -1,  # Unlimited
        "storage_limit_gb": -1,  # Unlimited
        "price_monthly": 0,  # Custom pricing (contact sales)
        "byo_keys": True,
    },
    SubscriptionTier.LIFETIME: {
        "workflows_limit": 50,
        "agents_limit": 5,
        "storage_limit_gb": 50,
        "price_monthly": 0,  # One-time $499 payment
        "price_one_time": 499,
        "byo_keys": True,
    },
}


class Subscription(Base):
    """Subscription for an organization.

    Manages tier-based access with usage limits and Stripe integration.
    Each organization has one active subscription at a time.
    """

    __tablename__ = "subscriptions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Organization link
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Billing account link
    billing_account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("billing_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Stripe integration
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    stripe_price_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_product_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Subscription details
    tier: Mapped[str] = mapped_column(
        String(50), nullable=False, default=SubscriptionTier.FREE.value, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=SubscriptionStatus.ACTIVE.value, index=True
    )

    # Billing cycle
    current_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    canceled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Trial tracking
    trial_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trial_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Usage limits for current period (can override tier defaults)
    workflows_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    workflows_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    agents_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    storage_limit_gb: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    storage_used_gb: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Lifetime-specific fields
    is_lifetime: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lifetime_purchase_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lifetime_purchase_amount: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )

    # BYO-specific fields
    is_byo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    byo_providers_configured: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True
    )  # ["anthropic", "openai", etc.]

    # Additional configuration
    subscription_config: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # Custom limits, features, etc.

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="subscription")
    billing_account: Mapped["BillingAccount"] = relationship(
        back_populates="subscription"
    )

    __table_args__ = (
        Index("idx_subscription_org_status", "organization_id", "status"),
        Index("idx_subscription_period_end", "current_period_end", "status"),
        {"comment": "Subscriptions with tier-based limits and Stripe integration"},
    )

    def __repr__(self) -> str:
        return (
            f"<Subscription(id={self.id}, org_id={self.organization_id}, "
            f"tier={self.tier}, status={self.status})>"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "billing_account_id": str(self.billing_account_id),
            "stripe_subscription_id": self.stripe_subscription_id,
            "tier": self.tier,
            "status": self.status,
            "current_period_start": (
                self.current_period_start.isoformat()
                if self.current_period_start
                else None
            ),
            "current_period_end": (
                self.current_period_end.isoformat() if self.current_period_end else None
            ),
            "cancel_at_period_end": self.cancel_at_period_end,
            "trial_start": self.trial_start.isoformat() if self.trial_start else None,
            "trial_end": self.trial_end.isoformat() if self.trial_end else None,
            "workflows_limit": self.workflows_limit,
            "workflows_used": self.workflows_used,
            "workflows_remaining": self.workflows_remaining,
            "agents_limit": self.agents_limit,
            "storage_limit_gb": self.storage_limit_gb,
            "storage_used_gb": self.storage_used_gb,
            "is_lifetime": self.is_lifetime,
            "is_byo": self.is_byo,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def workflows_remaining(self) -> int:
        """Get remaining workflows for this period."""
        if self.workflows_limit == -1:  # Unlimited
            return -1
        return max(0, self.workflows_limit - self.workflows_used)

    @property
    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self.status in [
            SubscriptionStatus.ACTIVE.value,
            SubscriptionStatus.TRIALING.value,
        ]

    @property
    def is_unlimited_workflows(self) -> bool:
        """Check if subscription has unlimited workflows."""
        return self.workflows_limit == -1

    def can_use_workflow(self) -> bool:
        """Check if a workflow can be used."""
        if not self.is_active:
            return False
        if self.is_unlimited_workflows:
            return True
        return self.workflows_remaining > 0

    def use_workflow(self) -> bool:
        """Consume a workflow. Returns True if successful."""
        if not self.can_use_workflow():
            return False
        if not self.is_unlimited_workflows:
            self.workflows_used += 1
        return True

    def reset_usage(self) -> None:
        """Reset usage for new billing period."""
        self.workflows_used = 0

    def apply_tier_limits(self, tier: SubscriptionTier) -> None:
        """Apply default limits from tier configuration."""
        limits = TIER_LIMITS.get(tier, TIER_LIMITS[SubscriptionTier.FREE])
        self.tier = tier.value
        self.workflows_limit = limits["workflows_limit"]
        self.agents_limit = limits["agents_limit"]
        self.storage_limit_gb = limits["storage_limit_gb"]

        # Set special flags
        self.is_lifetime = tier == SubscriptionTier.LIFETIME
        # BYO is now a feature available on Pro/Team/Enterprise/Lifetime, not a separate tier
        self.is_byo = tier in (
            SubscriptionTier.PRO,
            SubscriptionTier.TEAM,
            SubscriptionTier.ENTERPRISE,
            SubscriptionTier.LIFETIME,
        )

    def upgrade_to_tier(self, new_tier: SubscriptionTier) -> None:
        """Upgrade subscription to a new tier."""
        self.apply_tier_limits(new_tier)
        self.updated_at = utc_now()

    def cancel(self, at_period_end: bool = True) -> None:
        """Cancel the subscription."""
        if at_period_end:
            self.cancel_at_period_end = True
        else:
            self.status = SubscriptionStatus.CANCELED.value
            self.canceled_at = utc_now()

    def reactivate(self) -> None:
        """Reactivate a canceled subscription."""
        self.status = SubscriptionStatus.ACTIVE.value
        self.cancel_at_period_end = False
        self.canceled_at = None

    def pause(self) -> None:
        """Pause the subscription."""
        self.status = SubscriptionStatus.PAUSED.value

    def resume(self) -> None:
        """Resume a paused subscription."""
        self.status = SubscriptionStatus.ACTIVE.value
