"""Promo code model for discount codes and payment bypass.

Manages promotional codes that can be applied during checkout to provide
discounts, trial extensions, or complete payment bypass.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.user import User


class PromoCodeType(str, Enum):
    """Type of discount the promo code provides."""

    PERCENTAGE = "percentage"  # e.g., 50% off
    FIXED_AMOUNT = "fixed_amount"  # e.g., $20 off
    FULL_BYPASS = "full_bypass"  # Complete payment bypass (free access)
    TRIAL_EXTENSION = "trial_extension"  # Extend trial period


class PromoCode(Base):
    """Promotional code for discounts and payment bypass.

    Supports various discount types including percentage off, fixed amount,
    complete payment bypass, and trial extensions.
    """

    __tablename__ = "promo_codes"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    # The actual code users enter (case-insensitive, stored uppercase)
    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )

    # Human-readable description for admin purposes
    description: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )

    # Discount configuration
    discount_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default=PromoCodeType.PERCENTAGE.value
    )
    discount_value: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Percentage (0-100) or cents for fixed amount

    # For trial extensions - number of days to add
    trial_days: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )

    # Usage limits
    max_uses: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True  # null = unlimited
    )
    current_uses: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # Validity period
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    valid_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True  # null = no expiration
    )

    # Plan restrictions (which tiers this code applies to)
    # e.g., ["pro", "team"] or null for all plans
    applicable_tiers: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True
    )

    # Tier to grant for full_bypass codes
    # e.g., "pro" to give them pro tier for free
    grant_tier: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )

    # Duration for full_bypass codes (months, null = lifetime)
    grant_duration_months: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Creator tracking
    created_by_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Additional configuration
    promo_config: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # Extensible for future features

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    created_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[created_by_id]
    )
    redemptions: Mapped[list["PromoCodeRedemption"]] = relationship(
        back_populates="promo_code", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_promo_code_active_valid", "is_active", "valid_until"),
        {"comment": "Promotional codes for discounts and payment bypass"}
    )

    def __repr__(self) -> str:
        return (
            f"<PromoCode(code={self.code}, type={self.discount_type}, "
            f"uses={self.current_uses}/{self.max_uses or 'unlimited'})>"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "code": self.code,
            "description": self.description,
            "discount_type": self.discount_type,
            "discount_value": self.discount_value,
            "trial_days": self.trial_days,
            "max_uses": self.max_uses,
            "current_uses": self.current_uses,
            "uses_remaining": self.uses_remaining,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "applicable_tiers": self.applicable_tiers,
            "grant_tier": self.grant_tier,
            "grant_duration_months": self.grant_duration_months,
            "is_active": self.is_active,
            "is_valid": self.is_valid,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @property
    def uses_remaining(self) -> Optional[int]:
        """Get remaining uses for this code."""
        if self.max_uses is None:
            return None  # Unlimited
        return max(0, self.max_uses - self.current_uses)

    @property
    def is_valid(self) -> bool:
        """Check if promo code is currently valid."""
        if not self.is_active:
            return False

        now = utc_now()

        # Check validity period
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False

        # Check usage limits
        if self.max_uses is not None and self.current_uses >= self.max_uses:
            return False

        return True

    def can_apply_to_tier(self, tier: str) -> bool:
        """Check if this code can be applied to a specific tier."""
        if not self.is_valid:
            return False
        if self.applicable_tiers is None:
            return True  # No restrictions
        return tier.lower() in [t.lower() for t in self.applicable_tiers]

    def redeem(self) -> bool:
        """Increment usage count. Returns True if successful."""
        if not self.is_valid:
            return False
        self.current_uses += 1
        self.updated_at = utc_now()
        return True


class PromoCodeRedemption(Base):
    """Record of a promo code being redeemed by a user.

    Tracks when, by whom, and for what subscription a code was used.
    """

    __tablename__ = "promo_code_redemptions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    # Links
    promo_code_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("promo_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    organization_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    subscription_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Snapshot of what was applied
    discount_type_applied: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    discount_value_applied: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    tier_granted: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    duration_months_granted: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )

    # Timestamps
    redeemed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )

    # Relationships
    promo_code: Mapped["PromoCode"] = relationship(
        back_populates="redemptions"
    )
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("idx_redemption_user_code", "user_id", "promo_code_id"),
        {"comment": "Records of promo code redemptions"}
    )

    def __repr__(self) -> str:
        return (
            f"<PromoCodeRedemption(code_id={self.promo_code_id}, "
            f"user_id={self.user_id}, at={self.redeemed_at})>"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "promo_code_id": str(self.promo_code_id),
            "user_id": str(self.user_id),
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "subscription_id": str(self.subscription_id) if self.subscription_id else None,
            "discount_type_applied": self.discount_type_applied,
            "discount_value_applied": self.discount_value_applied,
            "tier_granted": self.tier_granted,
            "duration_months_granted": self.duration_months_granted,
            "redeemed_at": self.redeemed_at.isoformat() if self.redeemed_at else None,
        }
