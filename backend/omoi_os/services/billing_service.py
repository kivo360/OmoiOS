"""Billing service for invoice generation and usage tracking.

Handles the business logic for billing, connecting sandbox usage
to payment processing via Stripe.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from omoi_os.models.billing import (
    BillingAccount,
    BillingAccountStatus,
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentStatus,
    UsageRecord,
)
from omoi_os.models.organization import Organization
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.stripe_service import (
    StripeService,
    get_stripe_service,
    load_stripe_settings,
)
from omoi_os.utils.datetime import utc_now

logger = logging.getLogger(__name__)


class BillingService:
    """Service for billing operations and invoice management.

    Responsibilities:
    - Create and manage billing accounts for organizations
    - Track workflow usage and apply free tier
    - Generate invoices for usage
    - Process payments via Stripe
    - Handle prepaid credits
    - Manage dunning for failed payments
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
        self.settings = load_stripe_settings()

    # ========== Billing Account Management ==========

    def get_or_create_billing_account(
        self,
        organization_id: UUID,
        session: Optional[Session] = None,
    ) -> BillingAccount:
        """Get or create a billing account for an organization.

        Args:
            organization_id: Organization to get/create billing account for
            session: Database session (creates new if not provided)

        Returns:
            BillingAccount for the organization
        """

        def _get_or_create(sess: Session) -> BillingAccount:
            # Try to get existing account
            result = sess.execute(
                select(BillingAccount).where(
                    BillingAccount.organization_id == organization_id
                )
            )
            account = result.scalar_one_or_none()

            if account:
                return account

            # Get organization details
            org_result = sess.execute(
                select(Organization).where(Organization.id == organization_id)
            )
            org = org_result.scalar_one_or_none()
            if not org:
                raise ValueError(f"Organization not found: {organization_id}")

            # Create Stripe customer if Stripe is configured
            stripe_customer_id = None
            if self.stripe.is_configured:
                try:
                    customer = self.stripe.create_customer(
                        email=org.billing_email or f"billing+{org.slug}@example.com",
                        name=org.name,
                        organization_id=organization_id,
                    )
                    stripe_customer_id = customer.id
                except Exception as e:
                    logger.warning(f"Failed to create Stripe customer: {e}")

            # Create billing account
            account = BillingAccount(
                id=uuid4(),
                organization_id=organization_id,
                stripe_customer_id=stripe_customer_id,
                status=BillingAccountStatus.PENDING.value,
                free_workflows_remaining=self.settings.free_workflows_per_month,
                free_workflows_reset_at=self._next_month_start(),
                billing_email=org.billing_email,
            )
            sess.add(account)
            sess.flush()

            logger.info(f"Created billing account for organization: {organization_id}")
            return account

        if session:
            return _get_or_create(session)
        else:
            with self.db.get_session() as sess:
                account = _get_or_create(sess)
                sess.commit()
                return account

    def get_billing_account(
        self,
        organization_id: UUID,
        session: Optional[Session] = None,
    ) -> Optional[BillingAccount]:
        """Get billing account for an organization."""

        def _get(sess: Session) -> Optional[BillingAccount]:
            result = sess.execute(
                select(BillingAccount).where(
                    BillingAccount.organization_id == organization_id
                )
            )
            return result.scalar_one_or_none()

        if session:
            return _get(session)
        else:
            with self.db.get_session() as sess:
                return _get(sess)

    def update_billing_account_status(
        self,
        billing_account_id: UUID,
        status: BillingAccountStatus,
        session: Optional[Session] = None,
    ) -> BillingAccount:
        """Update billing account status."""

        def _update(sess: Session) -> BillingAccount:
            result = sess.execute(
                select(BillingAccount).where(BillingAccount.id == billing_account_id)
            )
            account = result.scalar_one_or_none()
            if not account:
                raise ValueError(f"Billing account not found: {billing_account_id}")

            account.status = status.value
            sess.flush()

            logger.info(
                f"Updated billing account {billing_account_id} status to: {status}"
            )
            return account

        if session:
            return _update(session)
        else:
            with self.db.get_session() as sess:
                account = _update(sess)
                sess.commit()
                return account

    # ========== Usage Tracking ==========

    def record_workflow_usage(
        self,
        organization_id: UUID,
        ticket_id: UUID,
        usage_details: Optional[dict] = None,
        session: Optional[Session] = None,
    ) -> UsageRecord:
        """Record usage for a completed workflow.

        Applies free tier if available, otherwise records billable usage.

        Args:
            organization_id: Organization that completed the workflow
            ticket_id: Ticket/workflow that was completed
            usage_details: Additional details (tokens, duration, etc.)
            session: Database session

        Returns:
            Created UsageRecord
        """

        def _record(sess: Session) -> UsageRecord:
            # Get or create billing account
            account = self.get_or_create_billing_account(organization_id, sess)

            # Check and reset free tier if needed
            self._check_free_tier_reset(account, sess)

            # Determine if this uses free tier
            free_tier_used = False
            unit_price = self.settings.workflow_price_usd
            total_price = unit_price

            if account.can_use_free_workflow():
                account.use_free_workflow()
                free_tier_used = True
                total_price = 0.0
                logger.info(
                    f"Used free workflow for org {organization_id}. "
                    f"Remaining: {account.free_workflows_remaining}"
                )

            # Create usage record
            usage_record = UsageRecord(
                id=uuid4(),
                billing_account_id=account.id,
                ticket_id=ticket_id,
                usage_type="workflow_completion",
                quantity=1,
                unit_price=unit_price,
                total_price=total_price,
                free_tier_used=free_tier_used,
                usage_details=usage_details or {},
                recorded_at=utc_now(),
            )
            sess.add(usage_record)

            # Update account statistics
            account.total_workflows_completed += 1
            if not free_tier_used:
                account.total_amount_spent += total_price

            sess.flush()

            # Publish usage event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="billing.usage_recorded",
                        entity_type="usage_record",
                        entity_id=str(usage_record.id),
                        payload={
                            "organization_id": str(organization_id),
                            "ticket_id": str(ticket_id),
                            "free_tier_used": free_tier_used,
                            "total_price": total_price,
                        },
                    )
                )

            return usage_record

        if session:
            return _record(session)
        else:
            with self.db.get_session() as sess:
                record = _record(sess)
                sess.commit()
                return record

    def get_unbilled_usage(
        self,
        billing_account_id: UUID,
        session: Optional[Session] = None,
    ) -> list[UsageRecord]:
        """Get all unbilled usage records for a billing account."""

        def _get(sess: Session) -> list[UsageRecord]:
            result = sess.execute(
                select(UsageRecord).where(
                    UsageRecord.billing_account_id == billing_account_id,
                    UsageRecord.billed is False,
                    UsageRecord.free_tier_used is False,  # Only billable usage
                )
            )
            return list(result.scalars().all())

        if session:
            return _get(session)
        else:
            with self.db.get_session() as sess:
                return _get(sess)

    # ========== Invoice Management ==========

    def generate_invoice(
        self,
        billing_account_id: UUID,
        session: Optional[Session] = None,
    ) -> Optional[Invoice]:
        """Generate an invoice for unbilled usage.

        Args:
            billing_account_id: Billing account to generate invoice for
            session: Database session

        Returns:
            Created Invoice or None if no billable usage
        """

        def _generate(sess: Session) -> Optional[Invoice]:
            # Get unbilled usage
            usage_records = self.get_unbilled_usage(billing_account_id, sess)

            if not usage_records:
                logger.debug(f"No unbilled usage for account: {billing_account_id}")
                return None

            # Get billing account
            result = sess.execute(
                select(BillingAccount).where(BillingAccount.id == billing_account_id)
            )
            account = result.scalar_one()

            # Create invoice
            invoice_number = self._generate_invoice_number()
            invoice = Invoice(
                id=uuid4(),
                invoice_number=invoice_number,
                billing_account_id=billing_account_id,
                status=InvoiceStatus.DRAFT.value,
                period_start=min(r.recorded_at for r in usage_records),
                period_end=utc_now(),
                currency="usd",
                line_items=[],
                due_date=utc_now() + timedelta(days=7),
            )

            # Add line items for usage
            for usage in usage_records:
                invoice.add_line_item(
                    description="Workflow Completion",
                    unit_price=usage.unit_price,
                    quantity=usage.quantity,
                    ticket_id=str(usage.ticket_id) if usage.ticket_id else None,
                )

            # Apply credits if available
            if account.credit_balance > 0 and invoice.total > 0:
                credits_to_apply = min(account.credit_balance, invoice.total)
                invoice.credits_applied = credits_to_apply
                account.credit_balance -= credits_to_apply
                invoice._recalculate_totals()

            # Finalize invoice
            invoice.finalize()

            # Mark usage as billed
            for usage in usage_records:
                usage.mark_billed(invoice.id)

            sess.add(invoice)
            sess.flush()

            logger.info(
                f"Generated invoice {invoice_number} for ${invoice.total:.2f} "
                f"({len(usage_records)} workflow(s))"
            )

            # Publish invoice event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="billing.invoice_generated",
                        entity_type="invoice",
                        entity_id=str(invoice.id),
                        payload={
                            "invoice_number": invoice_number,
                            "total": invoice.total,
                            "amount_due": invoice.amount_due,
                            "billing_account_id": str(billing_account_id),
                        },
                    )
                )

            return invoice

        if session:
            return _generate(session)
        else:
            with self.db.get_session() as sess:
                invoice = _generate(sess)
                sess.commit()
                return invoice

    def get_invoice(
        self,
        invoice_id: UUID,
        session: Optional[Session] = None,
    ) -> Optional[Invoice]:
        """Get an invoice by ID."""

        def _get(sess: Session) -> Optional[Invoice]:
            result = sess.execute(select(Invoice).where(Invoice.id == invoice_id))
            return result.scalar_one_or_none()

        if session:
            return _get(session)
        else:
            with self.db.get_session() as sess:
                return _get(sess)

    def list_invoices(
        self,
        billing_account_id: UUID,
        status: Optional[InvoiceStatus] = None,
        limit: int = 50,
        session: Optional[Session] = None,
    ) -> list[Invoice]:
        """List invoices for a billing account."""

        def _list(sess: Session) -> list[Invoice]:
            query = select(Invoice).where(
                Invoice.billing_account_id == billing_account_id
            )
            if status:
                query = query.where(Invoice.status == status.value)
            query = query.order_by(Invoice.created_at.desc()).limit(limit)

            result = sess.execute(query)
            return list(result.scalars().all())

        if session:
            return _list(session)
        else:
            with self.db.get_session() as sess:
                return _list(sess)

    # ========== Payment Processing ==========

    def process_invoice_payment(
        self,
        invoice_id: UUID,
        payment_method_id: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> Payment:
        """Process payment for an invoice.

        Args:
            invoice_id: Invoice to pay
            payment_method_id: Specific payment method to use
            session: Database session

        Returns:
            Created Payment record
        """

        def _process(sess: Session) -> Payment:
            # Get invoice
            result = sess.execute(select(Invoice).where(Invoice.id == invoice_id))
            invoice = result.scalar_one_or_none()
            if not invoice:
                raise ValueError(f"Invoice not found: {invoice_id}")

            if invoice.status == InvoiceStatus.PAID.value:
                raise ValueError(f"Invoice already paid: {invoice_id}")

            if invoice.amount_due <= 0:
                raise ValueError(f"Invoice has no amount due: {invoice_id}")

            # Get billing account
            result = sess.execute(
                select(BillingAccount).where(
                    BillingAccount.id == invoice.billing_account_id
                )
            )
            account = result.scalar_one()

            if not account.stripe_customer_id:
                raise ValueError("Billing account has no Stripe customer")

            # Create payment record
            payment = Payment(
                id=uuid4(),
                billing_account_id=account.id,
                invoice_id=invoice.id,
                amount=invoice.amount_due,
                currency=invoice.currency,
                status=PaymentStatus.PENDING.value,
            )
            sess.add(payment)
            sess.flush()

            # Process payment via Stripe
            try:
                amount_cents = int(invoice.amount_due * 100)
                stripe_payment = self.stripe.charge_customer_directly(
                    customer_id=account.stripe_customer_id,
                    amount_cents=amount_cents,
                    description=f"Invoice {invoice.invoice_number}",
                    payment_method_id=payment_method_id
                    or account.stripe_payment_method_id,
                    metadata={
                        "invoice_id": str(invoice.id),
                        "invoice_number": invoice.invoice_number,
                    },
                )

                # Update payment with Stripe details
                payment.stripe_payment_intent_id = stripe_payment.id
                payment.stripe_charge_id = stripe_payment.latest_charge
                payment.payment_method_type = "card"  # TODO: Get from Stripe
                payment.mark_succeeded()

                # Mark invoice as paid
                invoice.mark_paid(invoice.amount_due)

                # Update account status if was suspended
                if account.status == BillingAccountStatus.SUSPENDED.value:
                    account.status = BillingAccountStatus.ACTIVE.value

                logger.info(f"Payment succeeded for invoice {invoice.invoice_number}")

            except Exception as e:
                # Payment failed
                error_message = str(e)
                payment.mark_failed(
                    code="payment_failed",
                    message=error_message,
                )
                invoice.status = InvoiceStatus.PAST_DUE.value

                logger.warning(
                    f"Payment failed for invoice {invoice.invoice_number}: {error_message}"
                )

                # Publish payment failed event
                if self.event_bus:
                    self.event_bus.publish(
                        SystemEvent(
                            event_type="billing.payment_failed",
                            entity_type="payment",
                            entity_id=str(payment.id),
                            payload={
                                "invoice_id": str(invoice.id),
                                "error": error_message,
                            },
                        )
                    )

            sess.flush()
            return payment

        if session:
            return _process(session)
        else:
            with self.db.get_session() as sess:
                payment = _process(sess)
                sess.commit()
                return payment

    def add_credits(
        self,
        billing_account_id: UUID,
        amount_usd: float,
        reason: str = "credit_purchase",
        session: Optional[Session] = None,
    ) -> BillingAccount:
        """Add credits to a billing account.

        Args:
            billing_account_id: Account to add credits to
            amount_usd: Amount of credits to add in USD
            reason: Reason for adding credits

        Returns:
            Updated BillingAccount
        """

        def _add(sess: Session) -> BillingAccount:
            result = sess.execute(
                select(BillingAccount).where(BillingAccount.id == billing_account_id)
            )
            account = result.scalar_one_or_none()
            if not account:
                raise ValueError(f"Billing account not found: {billing_account_id}")

            account.add_credits(amount_usd)
            sess.flush()

            logger.info(
                f"Added ${amount_usd:.2f} credits to account {billing_account_id}"
            )

            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="billing.credits_added",
                        entity_type="billing_account",
                        entity_id=str(billing_account_id),
                        payload={
                            "amount": amount_usd,
                            "reason": reason,
                            "new_balance": account.credit_balance,
                        },
                    )
                )

            return account

        if session:
            return _add(session)
        else:
            with self.db.get_session() as sess:
                account = _add(sess)
                sess.commit()
                return account

    # ========== Checkout Sessions ==========

    def create_credit_checkout(
        self,
        organization_id: UUID,
        amount_usd: float,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> dict:
        """Create a checkout session for purchasing credits.

        Args:
            organization_id: Organization purchasing credits
            amount_usd: Amount of credits to purchase
            success_url: Redirect URL on success
            cancel_url: Redirect URL on cancel

        Returns:
            dict with checkout_url and session_id
        """
        with self.db.get_session() as sess:
            account = self.get_or_create_billing_account(organization_id, sess)
            sess.commit()

            if not account.stripe_customer_id:
                raise ValueError("Billing account has no Stripe customer")

            checkout = self.stripe.create_credit_purchase_session(
                customer_id=account.stripe_customer_id,
                credit_amount_usd=amount_usd,
                success_url=success_url,
                cancel_url=cancel_url,
                organization_id=organization_id,
            )

            return {
                "checkout_url": checkout.url,
                "session_id": checkout.id,
            }

    def create_customer_portal_url(self, organization_id: UUID) -> str:
        """Create a Stripe Customer Portal URL for managing billing.

        Args:
            organization_id: Organization to create portal for

        Returns:
            Portal URL
        """
        with self.db.get_session() as sess:
            account = self.get_billing_account(organization_id, sess)
            if not account:
                raise ValueError(
                    f"No billing account for organization: {organization_id}"
                )

            if not account.stripe_customer_id:
                raise ValueError("Billing account has no Stripe customer")

            portal = self.stripe.create_portal_session(account.stripe_customer_id)
            return portal.url

    # ========== Usage Enforcement ==========

    def can_execute_workflow(
        self,
        organization_id: UUID,
        session: Optional[Session] = None,
    ) -> tuple[bool, str]:
        """Check if an organization can execute a workflow.

        Checks in order:
        1. Active subscription with available workflow quota
        2. Free tier workflows remaining
        3. Prepaid credits available
        4. Account not suspended

        Args:
            organization_id: Organization to check

        Returns:
            Tuple of (can_execute, reason)
        """
        from omoi_os.models.subscription import (
            Subscription,
            SubscriptionStatus,
            SubscriptionTier,
            TIER_LIMITS,
        )

        def _check(sess: Session) -> tuple[bool, str]:
            # Get billing account
            account = self.get_billing_account(organization_id, sess)
            if not account:
                # No billing account yet - allow with free tier
                return True, "new_account"

            # Check if account is suspended
            if account.status == BillingAccountStatus.SUSPENDED.value:
                return (
                    False,
                    "Account suspended due to payment issues. Please update your payment method.",
                )

            # Check for active subscription
            sub_result = sess.execute(
                select(Subscription).where(
                    Subscription.organization_id == organization_id,
                    Subscription.status.in_(
                        [
                            SubscriptionStatus.ACTIVE.value,
                            SubscriptionStatus.TRIALING.value,
                        ]
                    ),
                )
            )
            subscription = sub_result.scalar_one_or_none()

            if subscription:
                # Get tier limits
                try:
                    tier = SubscriptionTier(subscription.tier)
                except ValueError:
                    tier = SubscriptionTier.FREE
                limits = TIER_LIMITS.get(tier, TIER_LIMITS[SubscriptionTier.FREE])
                workflow_limit = limits.get("workflows_limit", 0)

                # Unlimited workflows for enterprise
                if workflow_limit == -1:
                    return True, "enterprise_unlimited"

                # Check monthly usage against limit
                if subscription.workflows_used < workflow_limit:
                    return True, "subscription_quota"

                # Subscription quota exhausted - check for overage credits
                if account.credit_balance >= self.settings.workflow_price_usd:
                    return True, "overage_credits"

                return (
                    False,
                    f"Monthly workflow limit ({workflow_limit}) reached. Add credits or upgrade your plan.",
                )

            # No subscription - check free tier
            self._check_free_tier_reset(account, sess)
            if account.can_use_free_workflow():
                return True, "free_tier"

            # Check prepaid credits
            if account.credit_balance >= self.settings.workflow_price_usd:
                return True, "prepaid_credits"

            return (
                False,
                "No free workflows remaining. Please add credits or subscribe to a plan.",
            )

        if session:
            return _check(session)
        else:
            with self.db.get_session() as sess:
                return _check(sess)

    def check_and_reserve_workflow(
        self,
        organization_id: UUID,
        ticket_id: UUID,
        session: Optional[Session] = None,
    ) -> tuple[bool, str]:
        """Check if workflow can be executed and reserve quota.

        This is the main entry point for workflow execution enforcement.
        Called before starting a workflow to ensure billing is in order.

        Args:
            organization_id: Organization executing the workflow
            ticket_id: Ticket/workflow being executed

        Returns:
            Tuple of (can_execute, reason)
        """
        from omoi_os.models.subscription import (
            Subscription,
            SubscriptionStatus,
        )

        def _check_and_reserve(sess: Session) -> tuple[bool, str]:
            # First check if execution is allowed
            can_execute, reason = self.can_execute_workflow(organization_id, sess)

            if not can_execute:
                logger.warning(
                    f"Workflow execution blocked for org {organization_id}: {reason}"
                )
                # Publish blocked event for monitoring
                if self.event_bus:
                    self.event_bus.publish(
                        SystemEvent(
                            event_type="billing.workflow_blocked",
                            entity_type="organization",
                            entity_id=str(organization_id),
                            payload={
                                "ticket_id": str(ticket_id),
                                "reason": reason,
                            },
                        )
                    )
                return False, reason

            # If using subscription, increment the usage counter
            if reason == "subscription_quota":
                sub_result = sess.execute(
                    select(Subscription).where(
                        Subscription.organization_id == organization_id,
                        Subscription.status.in_(
                            [
                                SubscriptionStatus.ACTIVE.value,
                                SubscriptionStatus.TRIALING.value,
                            ]
                        ),
                    )
                )
                subscription = sub_result.scalar_one_or_none()
                if subscription:
                    subscription.workflows_used += 1
                    sess.flush()

            logger.info(
                f"Workflow execution allowed for org {organization_id} "
                f"(ticket: {ticket_id}, billing_type: {reason})"
            )
            return True, reason

        if session:
            return _check_and_reserve(session)
        else:
            with self.db.get_session() as sess:
                result = _check_and_reserve(sess)
                sess.commit()
                return result

    def get_usage_summary(
        self,
        organization_id: UUID,
        session: Optional[Session] = None,
    ) -> dict:
        """Get a summary of usage and limits for an organization.

        Returns:
            Dict with usage summary including:
            - subscription_tier
            - workflows_used
            - workflows_limit
            - free_workflows_remaining
            - credit_balance
            - can_execute
        """
        from omoi_os.models.subscription import (
            Subscription,
            SubscriptionStatus,
            SubscriptionTier,
            TIER_LIMITS,
        )

        def _get_summary(sess: Session) -> dict:
            account = self.get_billing_account(organization_id, sess)

            summary = {
                "subscription_tier": None,
                "workflows_used": 0,
                "workflows_limit": 0,
                "free_workflows_remaining": 0,
                "credit_balance": 0.0,
                "can_execute": False,
                "reason": "",
            }

            if not account:
                # No account yet - use free tier defaults
                summary["subscription_tier"] = "free"
                summary["free_workflows_remaining"] = (
                    self.settings.free_workflows_per_month
                )
                summary["can_execute"] = True
                summary["reason"] = "new_account"
                return summary

            summary["free_workflows_remaining"] = account.free_workflows_remaining
            summary["credit_balance"] = account.credit_balance

            # Check for subscription
            sub_result = sess.execute(
                select(Subscription).where(
                    Subscription.organization_id == organization_id,
                    Subscription.status.in_(
                        [
                            SubscriptionStatus.ACTIVE.value,
                            SubscriptionStatus.TRIALING.value,
                        ]
                    ),
                )
            )
            subscription = sub_result.scalar_one_or_none()

            if subscription:
                summary["subscription_tier"] = subscription.tier
                summary["workflows_used"] = subscription.workflows_used

                try:
                    tier = SubscriptionTier(subscription.tier)
                except ValueError:
                    tier = SubscriptionTier.FREE
                limits = TIER_LIMITS.get(tier, TIER_LIMITS[SubscriptionTier.FREE])
                summary["workflows_limit"] = limits.get("workflows_limit", 0)
            else:
                summary["subscription_tier"] = "pay_as_you_go"
                summary["workflows_limit"] = self.settings.free_workflows_per_month

            can_execute, reason = self.can_execute_workflow(organization_id, sess)
            summary["can_execute"] = can_execute
            summary["reason"] = reason

            return summary

        if session:
            return _get_summary(session)
        else:
            with self.db.get_session() as sess:
                return _get_summary(sess)

    # ========== Helper Methods ==========

    def _check_free_tier_reset(self, account: BillingAccount, session: Session) -> None:
        """Check if free tier should be reset for a new month."""
        now = utc_now()
        if account.free_workflows_reset_at and now >= account.free_workflows_reset_at:
            account.free_workflows_remaining = self.settings.free_workflows_per_month
            account.free_workflows_reset_at = self._next_month_start()
            logger.info(f"Reset free tier for account: {account.id}")

    def _next_month_start(self) -> datetime:
        """Get the start of next month."""
        now = utc_now()
        if now.month == 12:
            return now.replace(
                year=now.year + 1,
                month=1,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
        else:
            return now.replace(
                month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
            )

    def _generate_invoice_number(self) -> str:
        """Generate a unique invoice number."""
        now = utc_now()
        unique_part = str(uuid4())[:8].upper()
        return f"INV-{now.year}{now.month:02d}-{unique_part}"


# Singleton instance
_billing_service: Optional[BillingService] = None


def get_billing_service(db: DatabaseService) -> BillingService:
    """Get or create the BillingService singleton."""
    global _billing_service
    if _billing_service is None:
        _billing_service = BillingService(db)
    return _billing_service
