"""Subscription service for tier-based billing management.

Handles subscription lifecycle, tier changes, usage limits, and Stripe integration.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from omoi_os.models.subscription import (
    Subscription,
    SubscriptionStatus,
    SubscriptionTier,
    TIER_LIMITS,
)
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.stripe_service import StripeService, get_stripe_service
from omoi_os.utils.datetime import utc_now

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for subscription management.

    Responsibilities:
    - Create and manage subscriptions for organizations
    - Handle tier upgrades/downgrades with proration
    - Track usage limits per subscription
    - Integrate with Stripe for recurring billing
    - Handle lifetime and BYO tier special cases
    """

    def __init__(
        self,
        db: DatabaseService,
        stripe_service: Optional[StripeService] = None,
        event_bus: Optional[EventBusService] = None,
    ):
        self.db = db
        self.stripe = stripe_service or get_stripe_service()
        self.event_bus = event_bus

    # ========== Subscription Creation ==========

    def create_subscription(
        self,
        organization_id: UUID,
        billing_account_id: UUID,
        tier: SubscriptionTier = SubscriptionTier.FREE,
        trial_days: Optional[int] = None,
        session: Optional[Session] = None,
    ) -> Subscription:
        """Create a new subscription for an organization.

        Args:
            organization_id: Organization to create subscription for
            billing_account_id: Linked billing account
            tier: Initial subscription tier
            trial_days: Optional trial period in days
            session: Database session

        Returns:
            Created Subscription
        """

        def _create(sess: Session) -> Subscription:
            # Check for existing subscription
            existing = sess.execute(
                select(Subscription).where(
                    Subscription.organization_id == organization_id,
                    Subscription.status.in_(
                        [
                            SubscriptionStatus.ACTIVE.value,
                            SubscriptionStatus.TRIALING.value,
                            SubscriptionStatus.PAUSED.value,
                        ]
                    ),
                )
            ).scalar_one_or_none()

            if existing:
                raise ValueError(
                    f"Organization {organization_id} already has an active subscription"
                )

            # Get tier limits
            limits = TIER_LIMITS.get(tier, TIER_LIMITS[SubscriptionTier.FREE])

            # Create subscription
            now = utc_now()
            subscription = Subscription(
                id=uuid4(),
                organization_id=organization_id,
                billing_account_id=billing_account_id,
                tier=tier.value,
                status=SubscriptionStatus.ACTIVE.value,
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
                workflows_limit=limits["workflows_limit"],
                workflows_used=0,
                agents_limit=limits["agents_limit"],
                storage_limit_gb=limits["storage_limit_gb"],
                storage_used_gb=0.0,
                is_lifetime=(tier == SubscriptionTier.LIFETIME),
                is_byo=(tier == SubscriptionTier.BYO),
            )

            # Handle trial period
            if trial_days:
                subscription.status = SubscriptionStatus.TRIALING.value
                subscription.trial_start = now
                subscription.trial_end = now + timedelta(days=trial_days)
                subscription.current_period_end = subscription.trial_end

            sess.add(subscription)
            sess.flush()

            logger.info(
                f"Created {tier.value} subscription for organization {organization_id}"
            )

            # Publish event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="subscription.created",
                        entity_type="subscription",
                        entity_id=str(subscription.id),
                        payload={
                            "organization_id": str(organization_id),
                            "tier": tier.value,
                            "trial_days": trial_days,
                        },
                    )
                )

            return subscription

        if session:
            return _create(session)
        else:
            with self.db.get_session() as sess:
                subscription = _create(sess)
                sess.commit()
                return subscription

    def get_subscription(
        self,
        organization_id: UUID,
        session: Optional[Session] = None,
    ) -> Optional[Subscription]:
        """Get active subscription for an organization.

        Returns the most recently created active subscription if multiple exist.
        """

        def _get(sess: Session) -> Optional[Subscription]:
            result = sess.execute(
                select(Subscription)
                .where(
                    Subscription.organization_id == organization_id,
                    Subscription.status.in_(
                        [
                            SubscriptionStatus.ACTIVE.value,
                            SubscriptionStatus.TRIALING.value,
                            SubscriptionStatus.PAST_DUE.value,
                            SubscriptionStatus.PAUSED.value,
                        ]
                    ),
                )
                .order_by(Subscription.created_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()

        if session:
            return _get(session)
        else:
            with self.db.get_session() as sess:
                return _get(sess)

    def get_subscription_by_id(
        self,
        subscription_id: UUID,
        session: Optional[Session] = None,
    ) -> Optional[Subscription]:
        """Get subscription by ID."""

        def _get(sess: Session) -> Optional[Subscription]:
            result = sess.execute(
                select(Subscription).where(Subscription.id == subscription_id)
            )
            return result.scalar_one_or_none()

        if session:
            return _get(session)
        else:
            with self.db.get_session() as sess:
                return _get(sess)

    # ========== Usage Management ==========

    def can_use_workflow(
        self,
        organization_id: UUID,
        session: Optional[Session] = None,
    ) -> tuple[bool, str]:
        """Check if organization can execute a workflow.

        Returns:
            Tuple of (can_use, reason)
        """

        def _check(sess: Session) -> tuple[bool, str]:
            subscription = self.get_subscription(organization_id, sess)

            if not subscription:
                return False, "no_subscription"

            if not subscription.is_active:
                return False, f"subscription_{subscription.status}"

            if subscription.can_use_workflow():
                return True, "allowed"
            else:
                return False, "limit_reached"

        if session:
            return _check(session)
        else:
            with self.db.get_session() as sess:
                return _check(sess)

    def use_workflow(
        self,
        organization_id: UUID,
        session: Optional[Session] = None,
    ) -> bool:
        """Consume a workflow from the subscription.

        Returns:
            True if workflow was consumed, False if limit reached
        """

        def _use(sess: Session) -> bool:
            subscription = self.get_subscription(organization_id, sess)

            if not subscription:
                logger.warning(f"No subscription for org {organization_id}")
                return False

            if subscription.use_workflow():
                sess.flush()
                logger.debug(
                    f"Org {organization_id} used workflow. "
                    f"Remaining: {subscription.workflows_remaining}"
                )
                return True
            else:
                logger.warning(
                    f"Org {organization_id} workflow limit reached "
                    f"({subscription.workflows_used}/{subscription.workflows_limit})"
                )
                return False

        if session:
            return _use(session)
        else:
            with self.db.get_session() as sess:
                result = _use(sess)
                sess.commit()
                return result

    def reset_usage(
        self,
        subscription_id: UUID,
        session: Optional[Session] = None,
    ) -> Subscription:
        """Reset usage for a new billing period.

        Args:
            subscription_id: Subscription to reset
            session: Database session

        Returns:
            Updated Subscription
        """

        def _reset(sess: Session) -> Subscription:
            subscription = self.get_subscription_by_id(subscription_id, sess)
            if not subscription:
                raise ValueError(f"Subscription not found: {subscription_id}")

            subscription.reset_usage()

            # Update billing period
            now = utc_now()
            subscription.current_period_start = now
            subscription.current_period_end = now + timedelta(days=30)

            sess.flush()

            logger.info(f"Reset usage for subscription {subscription_id}")
            return subscription

        if session:
            return _reset(session)
        else:
            with self.db.get_session() as sess:
                subscription = _reset(sess)
                sess.commit()
                return subscription

    # ========== Tier Changes ==========

    def upgrade_tier(
        self,
        subscription_id: UUID,
        new_tier: SubscriptionTier,
        stripe_subscription_id: Optional[str] = None,
        stripe_price_id: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> Subscription:
        """Upgrade subscription to a new tier.

        Args:
            subscription_id: Subscription to upgrade
            new_tier: Target tier
            stripe_subscription_id: Stripe subscription ID if created
            stripe_price_id: Stripe price ID for the tier
            session: Database session

        Returns:
            Updated Subscription
        """

        def _upgrade(sess: Session) -> Subscription:
            subscription = self.get_subscription_by_id(subscription_id, sess)
            if not subscription:
                raise ValueError(f"Subscription not found: {subscription_id}")

            old_tier = subscription.tier
            subscription.upgrade_to_tier(new_tier)

            if stripe_subscription_id:
                subscription.stripe_subscription_id = stripe_subscription_id
            if stripe_price_id:
                subscription.stripe_price_id = stripe_price_id

            sess.flush()

            logger.info(
                f"Upgraded subscription {subscription_id} from {old_tier} to {new_tier.value}"
            )

            # Publish event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="subscription.upgraded",
                        entity_type="subscription",
                        entity_id=str(subscription_id),
                        payload={
                            "old_tier": old_tier,
                            "new_tier": new_tier.value,
                        },
                    )
                )

            return subscription

        if session:
            return _upgrade(session)
        else:
            with self.db.get_session() as sess:
                subscription = _upgrade(sess)
                sess.commit()
                return subscription

    def downgrade_tier(
        self,
        subscription_id: UUID,
        new_tier: SubscriptionTier,
        at_period_end: bool = True,
        session: Optional[Session] = None,
    ) -> Subscription:
        """Downgrade subscription to a lower tier.

        Args:
            subscription_id: Subscription to downgrade
            new_tier: Target tier
            at_period_end: If True, apply at end of current period
            session: Database session

        Returns:
            Updated Subscription
        """

        def _downgrade(sess: Session) -> Subscription:
            subscription = self.get_subscription_by_id(subscription_id, sess)
            if not subscription:
                raise ValueError(f"Subscription not found: {subscription_id}")

            old_tier = subscription.tier

            if at_period_end:
                # Store pending downgrade in config
                subscription.subscription_config = (
                    subscription.subscription_config or {}
                )
                subscription.subscription_config["pending_tier"] = new_tier.value
                logger.info(
                    f"Scheduled downgrade for subscription {subscription_id} "
                    f"from {old_tier} to {new_tier.value} at period end"
                )
            else:
                subscription.apply_tier_limits(new_tier)
                logger.info(
                    f"Downgraded subscription {subscription_id} "
                    f"from {old_tier} to {new_tier.value}"
                )

            sess.flush()

            # Publish event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="subscription.downgraded",
                        entity_type="subscription",
                        entity_id=str(subscription_id),
                        payload={
                            "old_tier": old_tier,
                            "new_tier": new_tier.value,
                            "at_period_end": at_period_end,
                        },
                    )
                )

            return subscription

        if session:
            return _downgrade(session)
        else:
            with self.db.get_session() as sess:
                subscription = _downgrade(sess)
                sess.commit()
                return subscription

    # ========== Subscription Lifecycle ==========

    def cancel_subscription(
        self,
        subscription_id: UUID,
        at_period_end: bool = True,
        session: Optional[Session] = None,
    ) -> Subscription:
        """Cancel a subscription.

        Args:
            subscription_id: Subscription to cancel
            at_period_end: If True, cancel at end of current period
            session: Database session

        Returns:
            Updated Subscription
        """

        def _cancel(sess: Session) -> Subscription:
            subscription = self.get_subscription_by_id(subscription_id, sess)
            if not subscription:
                raise ValueError(f"Subscription not found: {subscription_id}")

            subscription.cancel(at_period_end=at_period_end)
            sess.flush()

            logger.info(
                f"Canceled subscription {subscription_id} "
                f"(at_period_end={at_period_end})"
            )

            # Publish event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="subscription.canceled",
                        entity_type="subscription",
                        entity_id=str(subscription_id),
                        payload={
                            "at_period_end": at_period_end,
                        },
                    )
                )

            return subscription

        if session:
            return _cancel(session)
        else:
            with self.db.get_session() as sess:
                subscription = _cancel(sess)
                sess.commit()
                return subscription

    def reactivate_subscription(
        self,
        subscription_id: UUID,
        session: Optional[Session] = None,
    ) -> Subscription:
        """Reactivate a canceled subscription.

        Args:
            subscription_id: Subscription to reactivate
            session: Database session

        Returns:
            Updated Subscription
        """

        def _reactivate(sess: Session) -> Subscription:
            subscription = self.get_subscription_by_id(subscription_id, sess)
            if not subscription:
                raise ValueError(f"Subscription not found: {subscription_id}")

            subscription.reactivate()
            sess.flush()

            logger.info(f"Reactivated subscription {subscription_id}")

            # Publish event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="subscription.reactivated",
                        entity_type="subscription",
                        entity_id=str(subscription_id),
                    )
                )

            return subscription

        if session:
            return _reactivate(session)
        else:
            with self.db.get_session() as sess:
                subscription = _reactivate(sess)
                sess.commit()
                return subscription

    def pause_subscription(
        self,
        subscription_id: UUID,
        session: Optional[Session] = None,
    ) -> Subscription:
        """Pause a subscription."""

        def _pause(sess: Session) -> Subscription:
            subscription = self.get_subscription_by_id(subscription_id, sess)
            if not subscription:
                raise ValueError(f"Subscription not found: {subscription_id}")

            subscription.pause()
            sess.flush()

            logger.info(f"Paused subscription {subscription_id}")
            return subscription

        if session:
            return _pause(session)
        else:
            with self.db.get_session() as sess:
                subscription = _pause(sess)
                sess.commit()
                return subscription

    def resume_subscription(
        self,
        subscription_id: UUID,
        session: Optional[Session] = None,
    ) -> Subscription:
        """Resume a paused subscription."""

        def _resume(sess: Session) -> Subscription:
            subscription = self.get_subscription_by_id(subscription_id, sess)
            if not subscription:
                raise ValueError(f"Subscription not found: {subscription_id}")

            subscription.resume()
            sess.flush()

            logger.info(f"Resumed subscription {subscription_id}")
            return subscription

        if session:
            return _resume(session)
        else:
            with self.db.get_session() as sess:
                subscription = _resume(sess)
                sess.commit()
                return subscription

    # ========== Lifetime & BYO Special Handling ==========

    def create_lifetime_subscription(
        self,
        organization_id: UUID,
        billing_account_id: UUID,
        purchase_amount: float,
        session: Optional[Session] = None,
    ) -> Subscription:
        """Create a lifetime subscription from a one-time purchase.

        Args:
            organization_id: Organization to create subscription for
            billing_account_id: Linked billing account
            purchase_amount: Amount paid for lifetime access
            session: Database session

        Returns:
            Created lifetime Subscription
        """

        def _create(sess: Session) -> Subscription:
            # Create base subscription
            subscription = self.create_subscription(
                organization_id=organization_id,
                billing_account_id=billing_account_id,
                tier=SubscriptionTier.LIFETIME,
                session=sess,
            )

            # Set lifetime-specific fields
            subscription.is_lifetime = True
            subscription.lifetime_purchase_date = utc_now()
            subscription.lifetime_purchase_amount = purchase_amount

            # Lifetime subscriptions don't expire
            subscription.current_period_end = None

            sess.flush()

            logger.info(
                f"Created lifetime subscription for org {organization_id} "
                f"(${purchase_amount:.2f})"
            )

            return subscription

        if session:
            return _create(session)
        else:
            with self.db.get_session() as sess:
                subscription = _create(sess)
                sess.commit()
                return subscription

    def create_byo_subscription(
        self,
        organization_id: UUID,
        billing_account_id: UUID,
        configured_providers: list[str],
        session: Optional[Session] = None,
    ) -> Subscription:
        """Create a BYO (Bring Your Own) API key subscription.

        Args:
            organization_id: Organization to create subscription for
            billing_account_id: Linked billing account
            configured_providers: List of configured LLM providers
            session: Database session

        Returns:
            Created BYO Subscription
        """

        def _create(sess: Session) -> Subscription:
            # Create base subscription
            subscription = self.create_subscription(
                organization_id=organization_id,
                billing_account_id=billing_account_id,
                tier=SubscriptionTier.BYO,
                session=sess,
            )

            # Set BYO-specific fields
            subscription.is_byo = True
            subscription.byo_providers_configured = configured_providers

            sess.flush()

            logger.info(
                f"Created BYO subscription for org {organization_id} "
                f"(providers: {configured_providers})"
            )

            return subscription

        if session:
            return _create(session)
        else:
            with self.db.get_session() as sess:
                subscription = _create(sess)
                sess.commit()
                return subscription

    def update_byo_providers(
        self,
        subscription_id: UUID,
        providers: list[str],
        session: Optional[Session] = None,
    ) -> Subscription:
        """Update BYO providers list for a subscription."""

        def _update(sess: Session) -> Subscription:
            subscription = self.get_subscription_by_id(subscription_id, sess)
            if not subscription:
                raise ValueError(f"Subscription not found: {subscription_id}")

            if not subscription.is_byo:
                raise ValueError("Subscription is not a BYO tier")

            subscription.byo_providers_configured = providers
            sess.flush()

            logger.info(
                f"Updated BYO providers for subscription {subscription_id}: {providers}"
            )
            return subscription

        if session:
            return _update(session)
        else:
            with self.db.get_session() as sess:
                subscription = _update(sess)
                sess.commit()
                return subscription

    # ========== Stripe Integration Helpers ==========

    def sync_from_stripe(
        self,
        stripe_subscription_id: str,
        session: Optional[Session] = None,
    ) -> Subscription:
        """Sync subscription state from Stripe.

        Called by webhook handlers to update local state.

        Args:
            stripe_subscription_id: Stripe subscription ID to sync
            session: Database session

        Returns:
            Updated Subscription
        """

        def _sync(sess: Session) -> Subscription:
            # Get local subscription
            result = sess.execute(
                select(Subscription).where(
                    Subscription.stripe_subscription_id == stripe_subscription_id
                )
            )
            subscription = result.scalar_one_or_none()

            if not subscription:
                raise ValueError(
                    f"Subscription not found for Stripe ID: {stripe_subscription_id}"
                )

            # Get Stripe subscription
            stripe_sub = self.stripe.get_subscription(stripe_subscription_id)

            # Update local state
            subscription.status = self._map_stripe_status(stripe_sub.status)
            subscription.current_period_start = datetime.fromtimestamp(
                stripe_sub.current_period_start
            )
            subscription.current_period_end = datetime.fromtimestamp(
                stripe_sub.current_period_end
            )
            subscription.cancel_at_period_end = stripe_sub.cancel_at_period_end

            if stripe_sub.canceled_at:
                subscription.canceled_at = datetime.fromtimestamp(
                    stripe_sub.canceled_at
                )

            sess.flush()

            logger.info(f"Synced subscription {subscription.id} from Stripe")
            return subscription

        if session:
            return _sync(session)
        else:
            with self.db.get_session() as sess:
                subscription = _sync(sess)
                sess.commit()
                return subscription

    def _map_stripe_status(self, stripe_status: str) -> str:
        """Map Stripe subscription status to our status enum."""
        status_map = {
            "active": SubscriptionStatus.ACTIVE.value,
            "trialing": SubscriptionStatus.TRIALING.value,
            "past_due": SubscriptionStatus.PAST_DUE.value,
            "canceled": SubscriptionStatus.CANCELED.value,
            "paused": SubscriptionStatus.PAUSED.value,
            "incomplete": SubscriptionStatus.INCOMPLETE.value,
            "incomplete_expired": SubscriptionStatus.CANCELED.value,
            "unpaid": SubscriptionStatus.PAST_DUE.value,
        }
        return status_map.get(stripe_status, SubscriptionStatus.ACTIVE.value)


# Singleton instance
_subscription_service: Optional[SubscriptionService] = None


def get_subscription_service(db: DatabaseService) -> SubscriptionService:
    """Get or create the SubscriptionService singleton."""
    global _subscription_service
    if _subscription_service is None:
        _subscription_service = SubscriptionService(db)
    return _subscription_service
