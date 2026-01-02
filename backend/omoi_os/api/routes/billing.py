"""Billing API routes for payment processing and invoice management."""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, Field

from omoi_os.api.dependencies import get_database_service
from omoi_os.services.billing_service import BillingService, get_billing_service
from omoi_os.services.cost_tracking import CostTrackingService
from omoi_os.services.database import DatabaseService
from omoi_os.services.stripe_service import get_stripe_service, StripeService
from omoi_os.services.subscription_service import SubscriptionService, get_subscription_service
from omoi_os.models.subscription import SubscriptionTier

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== Request/Response Models ==========

class BillingAccountResponse(BaseModel):
    """Response model for billing account."""
    id: str
    organization_id: str
    stripe_customer_id: Optional[str]
    has_payment_method: bool
    status: str
    free_workflows_remaining: int
    free_workflows_reset_at: Optional[datetime]
    credit_balance: float
    auto_billing_enabled: bool
    billing_email: Optional[str]
    tax_exempt: bool
    total_workflows_completed: int
    total_amount_spent: float
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class InvoiceResponse(BaseModel):
    """Response model for invoice."""
    id: str
    invoice_number: str
    billing_account_id: str
    ticket_id: Optional[str]
    stripe_invoice_id: Optional[str]
    status: str
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    subtotal: float
    tax_amount: float
    discount_amount: float
    total: float
    credits_applied: float
    amount_due: float
    amount_paid: float
    currency: str
    line_items: list[dict]
    description: Optional[str]
    due_date: Optional[datetime]
    finalized_at: Optional[datetime]
    paid_at: Optional[datetime]
    created_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class PaymentResponse(BaseModel):
    """Response model for payment."""
    id: str
    billing_account_id: str
    invoice_id: Optional[str]
    stripe_payment_intent_id: Optional[str]
    amount: float
    currency: str
    status: str
    payment_method_type: Optional[str]
    payment_method_last4: Optional[str]
    payment_method_brand: Optional[str]
    failure_code: Optional[str]
    failure_message: Optional[str]
    refunded_amount: float
    description: Optional[str]
    created_at: Optional[datetime]
    succeeded_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class UsageRecordResponse(BaseModel):
    """Response model for usage record."""
    id: str
    billing_account_id: str
    ticket_id: Optional[str]
    usage_type: str
    quantity: int
    unit_price: float
    total_price: float
    free_tier_used: bool
    invoice_id: Optional[str]
    billed: bool
    usage_details: Optional[dict]
    recorded_at: Optional[datetime]
    billed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class CreditPurchaseRequest(BaseModel):
    """Request to purchase credits."""
    amount_usd: float = Field(..., gt=0, le=1000, description="Amount to purchase (USD)")
    success_url: Optional[str] = Field(None, description="Custom success redirect URL")
    cancel_url: Optional[str] = Field(None, description="Custom cancel redirect URL")


class LifetimePurchaseRequest(BaseModel):
    """Request to purchase lifetime subscription."""
    success_url: Optional[str] = Field(None, description="Custom success redirect URL")
    cancel_url: Optional[str] = Field(None, description="Custom cancel redirect URL")


class CheckoutResponse(BaseModel):
    """Response for checkout session creation."""
    checkout_url: str
    session_id: str


class PortalResponse(BaseModel):
    """Response for customer portal."""
    portal_url: str


class PaymentMethodRequest(BaseModel):
    """Request to attach a payment method."""
    payment_method_id: str = Field(..., description="Stripe payment method ID from frontend")
    set_as_default: bool = Field(True, description="Set as default payment method")


class PaymentMethodResponse(BaseModel):
    """Response for payment method."""
    id: str
    type: str
    card_brand: Optional[str]
    card_last4: Optional[str]
    is_default: bool


class PayInvoiceRequest(BaseModel):
    """Request to pay an invoice."""
    payment_method_id: Optional[str] = Field(None, description="Specific payment method to use")


class StripeConfigResponse(BaseModel):
    """Response with Stripe publishable key for frontend."""
    publishable_key: Optional[str]
    is_configured: bool


class SubscriptionResponse(BaseModel):
    """Response model for subscription."""
    id: str
    organization_id: str
    billing_account_id: str
    tier: str
    status: str
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool
    canceled_at: Optional[datetime]
    trial_start: Optional[datetime]
    trial_end: Optional[datetime]
    workflows_limit: int
    workflows_used: int
    workflows_remaining: int
    agents_limit: int
    storage_limit_gb: int
    storage_used_gb: float
    is_lifetime: bool
    lifetime_purchase_date: Optional[datetime]
    lifetime_purchase_amount: Optional[float]
    is_byo: bool
    byo_providers_configured: Optional[list[str]]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class CostBreakdownItem(BaseModel):
    """Model breakdown in cost summary."""
    provider: str
    model: str
    cost: float
    tokens: int
    records: int


class CostSummaryResponse(BaseModel):
    """Response model for cost summary."""
    scope_type: str
    scope_id: Optional[str]
    total_cost: float
    total_tokens: int
    record_count: int
    breakdown: list[CostBreakdownItem]


class CostRecordResponse(BaseModel):
    """Response model for individual cost record."""
    id: str
    task_id: str
    agent_id: Optional[str]
    sandbox_id: Optional[str]
    billing_account_id: Optional[str]
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_cost: float
    completion_cost: float
    total_cost: float
    recorded_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ========== Dependency Injection ==========

def get_billing_service_dep(
    db: DatabaseService = Depends(get_database_service),
) -> BillingService:
    """Get billing service instance."""
    return get_billing_service(db)


def get_subscription_service_dep(
    db: DatabaseService = Depends(get_database_service),
) -> SubscriptionService:
    """Get subscription service instance."""
    return get_subscription_service(db)


def get_cost_tracking_service_dep(
    db: DatabaseService = Depends(get_database_service),
) -> CostTrackingService:
    """Get cost tracking service instance."""
    return CostTrackingService(db)


# ========== API Endpoints ==========

@router.get("/config", response_model=StripeConfigResponse)
async def get_stripe_config(
    stripe: StripeService = Depends(get_stripe_service),
):
    """
    Get Stripe configuration for frontend.

    Returns the publishable key needed for Stripe.js integration.
    """
    return StripeConfigResponse(
        publishable_key=stripe.settings.publishable_key,
        is_configured=stripe.is_configured,
    )


@router.get("/account/{organization_id}", response_model=BillingAccountResponse)
async def get_billing_account(
    organization_id: UUID,
    billing_service: BillingService = Depends(get_billing_service_dep),
):
    """
    Get or create billing account for an organization.

    Creates a new billing account if one doesn't exist.
    """
    account = billing_service.get_or_create_billing_account(organization_id)
    return BillingAccountResponse(**account.to_dict())


@router.post("/account/{organization_id}/payment-method", response_model=PaymentMethodResponse)
async def attach_payment_method(
    organization_id: UUID,
    request: PaymentMethodRequest,
    billing_service: BillingService = Depends(get_billing_service_dep),
    stripe: StripeService = Depends(get_stripe_service),
):
    """
    Attach a payment method to the billing account.

    The payment_method_id should be obtained from Stripe.js on the frontend.
    """
    account = billing_service.get_billing_account(organization_id)
    if not account:
        raise HTTPException(status_code=404, detail="Billing account not found")

    if not account.stripe_customer_id:
        raise HTTPException(status_code=400, detail="Billing account has no Stripe customer")

    try:
        payment_method = stripe.attach_payment_method(
            customer_id=account.stripe_customer_id,
            payment_method_id=request.payment_method_id,
            set_as_default=request.set_as_default,
        )

        # Update billing account with payment method ID
        with billing_service.db.get_session() as sess:
            from sqlalchemy import select
            from omoi_os.models.billing import BillingAccount, BillingAccountStatus

            result = sess.execute(
                select(BillingAccount).where(BillingAccount.id == account.id)
            )
            db_account = result.scalar_one()
            db_account.stripe_payment_method_id = payment_method.id

            # Activate account if it was pending
            if db_account.status == BillingAccountStatus.PENDING.value:
                db_account.status = BillingAccountStatus.ACTIVE.value

            sess.commit()

        return PaymentMethodResponse(
            id=payment_method.id,
            type=payment_method.type,
            card_brand=payment_method.card.brand if payment_method.card else None,
            card_last4=payment_method.card.last4 if payment_method.card else None,
            is_default=request.set_as_default,
        )
    except Exception as e:
        logger.error(f"Failed to attach payment method: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/account/{organization_id}/payment-methods", response_model=list[PaymentMethodResponse])
async def list_payment_methods(
    organization_id: UUID,
    billing_service: BillingService = Depends(get_billing_service_dep),
    stripe: StripeService = Depends(get_stripe_service),
):
    """
    List all payment methods for the billing account.
    """
    account = billing_service.get_billing_account(organization_id)
    if not account:
        raise HTTPException(status_code=404, detail="Billing account not found")

    if not account.stripe_customer_id:
        return []

    try:
        payment_methods = stripe.list_payment_methods(account.stripe_customer_id)
        return [
            PaymentMethodResponse(
                id=pm.id,
                type=pm.type,
                card_brand=pm.card.brand if pm.card else None,
                card_last4=pm.card.last4 if pm.card else None,
                is_default=pm.id == account.stripe_payment_method_id,
            )
            for pm in payment_methods
        ]
    except Exception as e:
        logger.error(f"Failed to list payment methods: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/account/{organization_id}/payment-methods/{payment_method_id}")
async def remove_payment_method(
    organization_id: UUID,
    payment_method_id: str,
    billing_service: BillingService = Depends(get_billing_service_dep),
    stripe: StripeService = Depends(get_stripe_service),
):
    """
    Remove a payment method from the billing account.
    """
    account = billing_service.get_billing_account(organization_id)
    if not account:
        raise HTTPException(status_code=404, detail="Billing account not found")

    try:
        stripe.detach_payment_method(payment_method_id)

        # Clear default if this was the default
        if account.stripe_payment_method_id == payment_method_id:
            with billing_service.db.get_session() as sess:
                from sqlalchemy import select
                from omoi_os.models.billing import BillingAccount

                result = sess.execute(
                    select(BillingAccount).where(BillingAccount.id == account.id)
                )
                db_account = result.scalar_one()
                db_account.stripe_payment_method_id = None
                sess.commit()

        return {"status": "success", "message": "Payment method removed"}
    except Exception as e:
        logger.error(f"Failed to remove payment method: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ========== Credit Purchase ==========

@router.post("/account/{organization_id}/credits/checkout", response_model=CheckoutResponse)
async def create_credit_checkout(
    organization_id: UUID,
    request: CreditPurchaseRequest,
    billing_service: BillingService = Depends(get_billing_service_dep),
):
    """
    Create a Stripe Checkout session to purchase prepaid credits.

    Returns a checkout URL to redirect the user to.
    """
    try:
        result = billing_service.create_credit_checkout(
            organization_id=organization_id,
            amount_usd=request.amount_usd,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )
        return CheckoutResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create credit checkout: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


# ========== Subscription Management ==========

@router.get("/account/{organization_id}/subscription", response_model=Optional[SubscriptionResponse])
async def get_subscription(
    organization_id: UUID,
    subscription_service: SubscriptionService = Depends(get_subscription_service_dep),
):
    """
    Get the active subscription for an organization.

    Returns null if no active subscription exists.
    """
    subscription = subscription_service.get_subscription(organization_id)
    if not subscription:
        return None

    return SubscriptionResponse(
        id=str(subscription.id),
        organization_id=str(subscription.organization_id),
        billing_account_id=str(subscription.billing_account_id),
        tier=subscription.tier,
        status=subscription.status,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        canceled_at=subscription.canceled_at,
        trial_start=subscription.trial_start,
        trial_end=subscription.trial_end,
        workflows_limit=subscription.workflows_limit,
        workflows_used=subscription.workflows_used,
        workflows_remaining=subscription.workflows_remaining,
        agents_limit=subscription.agents_limit,
        storage_limit_gb=subscription.storage_limit_gb,
        storage_used_gb=subscription.storage_used_gb,
        is_lifetime=subscription.is_lifetime,
        lifetime_purchase_date=subscription.lifetime_purchase_date,
        lifetime_purchase_amount=subscription.lifetime_purchase_amount,
        is_byo=subscription.is_byo,
        byo_providers_configured=subscription.byo_providers_configured,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at,
    )


@router.post("/account/{organization_id}/subscription/cancel")
async def cancel_subscription(
    organization_id: UUID,
    at_period_end: bool = True,
    subscription_service: SubscriptionService = Depends(get_subscription_service_dep),
):
    """
    Cancel the organization's subscription.

    By default, cancels at the end of the current billing period.
    Set at_period_end=False for immediate cancellation.
    """
    subscription = subscription_service.get_subscription(organization_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")

    subscription_service.cancel_subscription(subscription.id, at_period_end=at_period_end)
    return {"status": "success", "message": "Subscription canceled"}


@router.post("/account/{organization_id}/subscription/reactivate")
async def reactivate_subscription(
    organization_id: UUID,
    subscription_service: SubscriptionService = Depends(get_subscription_service_dep),
):
    """
    Reactivate a canceled subscription (before period end).
    """
    subscription = subscription_service.get_subscription(organization_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")

    if not subscription.cancel_at_period_end:
        raise HTTPException(status_code=400, detail="Subscription is not pending cancellation")

    subscription_service.reactivate_subscription(subscription.id)
    return {"status": "success", "message": "Subscription reactivated"}


# ========== Subscription Checkout ==========

class SubscriptionCheckoutRequest(BaseModel):
    """Request to create subscription checkout session."""
    tier: str = Field(..., description="Subscription tier: 'pro' or 'team'")
    success_url: Optional[str] = Field(None, description="Custom success redirect URL")
    cancel_url: Optional[str] = Field(None, description="Custom cancel redirect URL")


# Tier pricing configuration - matches landing page
TIER_PRICES = {
    "pro": {
        "price_usd": 50,
        "name": "OmoiOS Pro",
        "description": "5 concurrent agents, 100 workflows/month, BYO API keys",
    },
    "team": {
        "price_usd": 150,
        "name": "OmoiOS Team",
        "description": "10 concurrent agents, 500 workflows/month, BYO API keys, team collaboration",
    },
}


@router.post("/account/{organization_id}/subscription/checkout", response_model=CheckoutResponse)
async def create_subscription_checkout(
    organization_id: UUID,
    request: SubscriptionCheckoutRequest,
    billing_service: BillingService = Depends(get_billing_service_dep),
    subscription_service: SubscriptionService = Depends(get_subscription_service_dep),
    stripe: StripeService = Depends(get_stripe_service),
):
    """
    Create a Stripe Checkout session for a subscription tier (Pro or Team).

    This creates a recurring subscription, not a one-time payment.
    """
    tier = request.tier.lower()

    if tier not in TIER_PRICES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier. Must be one of: {', '.join(TIER_PRICES.keys())}"
        )

    tier_config = TIER_PRICES[tier]

    # Check for existing paid subscription
    existing = subscription_service.get_subscription(organization_id)
    if existing and existing.is_lifetime:
        raise HTTPException(status_code=400, detail="Organization already has a lifetime subscription")
    if existing and existing.tier in ["pro", "team"] and existing.status == "active":
        raise HTTPException(
            status_code=400,
            detail="Organization already has an active paid subscription. Use the customer portal to change plans."
        )

    # Get or create billing account
    account = billing_service.get_or_create_billing_account(organization_id)

    # Create Stripe checkout session for subscription
    try:
        success_url = request.success_url or f"{stripe.settings.frontend_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = request.cancel_url or f"{stripe.settings.frontend_url}/billing/cancel"

        session = stripe.stripe.checkout.Session.create(
            mode="subscription",  # Recurring subscription
            customer=account.stripe_customer_id,
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": int(tier_config["price_usd"] * 100),  # In cents
                        "recurring": {
                            "interval": "month",
                        },
                        "product_data": {
                            "name": tier_config["name"],
                            "description": tier_config["description"],
                        },
                    },
                    "quantity": 1,
                }
            ],
            metadata={
                "subscription_checkout": "true",
                "tier": tier,
                "organization_id": str(organization_id),
                "billing_account_id": str(account.id),
            },
            success_url=success_url,
            cancel_url=cancel_url,
        )

        return CheckoutResponse(checkout_url=session.url, session_id=session.id)
    except Exception as e:
        logger.error(f"Failed to create subscription checkout: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


# ========== Lifetime Purchase ==========

# Lifetime pricing configuration (should match pricing_strategy.md)
LIFETIME_PRICE_USD = 299.0
LIFETIME_STRIPE_PRICE_ID = "price_lifetime_omoios"  # Configure in Stripe dashboard


@router.post("/account/{organization_id}/lifetime/checkout", response_model=CheckoutResponse)
async def create_lifetime_checkout(
    organization_id: UUID,
    request: LifetimePurchaseRequest,
    billing_service: BillingService = Depends(get_billing_service_dep),
    subscription_service: SubscriptionService = Depends(get_subscription_service_dep),
    stripe: StripeService = Depends(get_stripe_service),
):
    """
    Create a Stripe Checkout session to purchase lifetime subscription.

    Lifetime subscription provides:
    - Unlimited workflows per month
    - Priority support
    - All Pro features permanently
    - One-time $499 payment (no recurring charges)
    """
    # Check for existing lifetime subscription
    existing = subscription_service.get_subscription(organization_id)
    if existing and existing.is_lifetime:
        raise HTTPException(status_code=400, detail="Organization already has a lifetime subscription")

    # Get or create billing account
    account = billing_service.get_or_create_billing_account(organization_id)

    # Create Stripe checkout session for one-time payment
    try:
        success_url = request.success_url or f"{stripe.settings.frontend_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = request.cancel_url or f"{stripe.settings.frontend_url}/billing/cancel"

        session = stripe.stripe.checkout.Session.create(
            mode="payment",  # One-time payment, not subscription
            customer=account.stripe_customer_id,
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": int(LIFETIME_PRICE_USD * 100),  # In cents
                        "product_data": {
                            "name": "OmoiOS Lifetime Subscription",
                            "description": "One-time purchase for lifetime access to OmoiOS Pro features",
                        },
                    },
                    "quantity": 1,
                }
            ],
            metadata={
                "lifetime_purchase": "true",
                "organization_id": str(organization_id),
                "billing_account_id": str(account.id),
                "purchase_amount": str(LIFETIME_PRICE_USD),
            },
            success_url=success_url,
            cancel_url=cancel_url,
        )

        return CheckoutResponse(checkout_url=session.url, session_id=session.id)
    except Exception as e:
        logger.error(f"Failed to create lifetime checkout: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


# ========== Customer Portal ==========

@router.post("/account/{organization_id}/portal", response_model=PortalResponse)
async def create_customer_portal(
    organization_id: UUID,
    billing_service: BillingService = Depends(get_billing_service_dep),
):
    """
    Create a Stripe Customer Portal session.

    The portal allows customers to manage payment methods and view billing history.
    Returns a portal URL to redirect the user to.
    """
    try:
        portal_url = billing_service.create_customer_portal_url(organization_id)
        return PortalResponse(portal_url=portal_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create customer portal: {e}")
        raise HTTPException(status_code=500, detail="Failed to create portal session")


# ========== Invoices ==========

@router.get("/account/{organization_id}/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    organization_id: UUID,
    status: Optional[str] = None,
    limit: int = 50,
    billing_service: BillingService = Depends(get_billing_service_dep),
):
    """
    List invoices for an organization.

    Optionally filter by status: draft, open, paid, past_due, void.
    """
    account = billing_service.get_billing_account(organization_id)
    if not account:
        raise HTTPException(status_code=404, detail="Billing account not found")

    from omoi_os.models.billing import InvoiceStatus

    invoice_status = None
    if status:
        try:
            invoice_status = InvoiceStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    invoices = billing_service.list_invoices(
        billing_account_id=account.id,
        status=invoice_status,
        limit=limit,
    )

    return [InvoiceResponse(**inv.to_dict()) for inv in invoices]


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: UUID,
    billing_service: BillingService = Depends(get_billing_service_dep),
):
    """
    Get a specific invoice by ID.
    """
    invoice = billing_service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return InvoiceResponse(**invoice.to_dict())


@router.post("/invoices/{invoice_id}/pay", response_model=PaymentResponse)
async def pay_invoice(
    invoice_id: UUID,
    request: PayInvoiceRequest = None,
    billing_service: BillingService = Depends(get_billing_service_dep),
):
    """
    Pay an invoice.

    Uses the default payment method unless a specific one is provided.
    """
    try:
        payment = billing_service.process_invoice_payment(
            invoice_id=invoice_id,
            payment_method_id=request.payment_method_id if request else None,
        )
        return PaymentResponse(**payment.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to process payment: {e}")
        raise HTTPException(status_code=500, detail="Payment processing failed")


@router.post("/account/{organization_id}/invoices/generate", response_model=Optional[InvoiceResponse])
async def generate_invoice(
    organization_id: UUID,
    billing_service: BillingService = Depends(get_billing_service_dep),
):
    """
    Generate an invoice for unbilled usage.

    Returns the created invoice or null if no billable usage.
    """
    account = billing_service.get_billing_account(organization_id)
    if not account:
        raise HTTPException(status_code=404, detail="Billing account not found")

    invoice = billing_service.generate_invoice(account.id)

    if not invoice:
        return None

    return InvoiceResponse(**invoice.to_dict())


# ========== Usage ==========

@router.get("/account/{organization_id}/usage", response_model=list[UsageRecordResponse])
async def get_usage(
    organization_id: UUID,
    billed: Optional[bool] = None,
    billing_service: BillingService = Depends(get_billing_service_dep),
):
    """
    Get usage records for an organization.

    Optionally filter by billed status.
    """
    account = billing_service.get_billing_account(organization_id)
    if not account:
        raise HTTPException(status_code=404, detail="Billing account not found")

    from sqlalchemy import select
    from omoi_os.models.billing import UsageRecord

    with billing_service.db.get_session() as sess:
        query = select(UsageRecord).where(
            UsageRecord.billing_account_id == account.id
        )

        if billed is not None:
            query = query.where(UsageRecord.billed == billed)

        query = query.order_by(UsageRecord.recorded_at.desc()).limit(100)

        result = sess.execute(query)
        records = list(result.scalars().all())

        return [UsageRecordResponse(**r.to_dict()) for r in records]


# ========== Stripe Webhooks ==========

@router.post("/webhooks/stripe")
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
    billing_service: BillingService = Depends(get_billing_service_dep),
    stripe: StripeService = Depends(get_stripe_service),
):
    """
    Handle Stripe webhook events.

    Processes events like:
    - payment_intent.succeeded
    - payment_intent.payment_failed
    - checkout.session.completed
    - customer.subscription.* (if subscriptions are used)
    """
    payload = await request.body()

    try:
        event = stripe.verify_webhook(payload, stripe_signature)
    except ValueError as e:
        logger.error(f"Webhook verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook payload")
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    event_data = event["data"]["object"]

    logger.info(f"Processing Stripe webhook: {event_type}")

    try:
        if event_type == "checkout.session.completed":
            # Handle successful checkout (credit purchase)
            await _handle_checkout_completed(event_data, billing_service)

        elif event_type == "payment_intent.succeeded":
            # Handle successful payment
            await _handle_payment_succeeded(event_data, billing_service)

        elif event_type == "payment_intent.payment_failed":
            # Handle failed payment
            await _handle_payment_failed(event_data, billing_service)

        elif event_type == "charge.refunded":
            # Handle refund
            await _handle_refund(event_data, billing_service)

        elif event_type == "customer.subscription.created":
            # Handle new subscription from Stripe
            await _handle_subscription_created(event_data, billing_service)

        elif event_type == "customer.subscription.updated":
            # Handle subscription update (tier change, renewal, etc.)
            await _handle_subscription_updated(event_data, billing_service)

        elif event_type == "customer.subscription.deleted":
            # Handle subscription cancellation
            await _handle_subscription_deleted(event_data, billing_service)

        elif event_type == "invoice.paid":
            # Handle subscription invoice paid (reset usage for new period)
            await _handle_subscription_invoice_paid(event_data, billing_service)

        elif event_type == "invoice.payment_failed":
            # Handle subscription payment failure (start dunning)
            await _handle_subscription_invoice_failed(event_data, billing_service)

        else:
            logger.debug(f"Unhandled webhook event type: {event_type}")

    except Exception as e:
        logger.error(f"Error processing webhook {event_type}: {e}")
        # Don't raise - return 200 to prevent Stripe retries for processing errors
        # The event should be logged for investigation

    return {"status": "received"}


async def _handle_checkout_completed(event_data: dict, billing_service: BillingService):
    """Handle checkout.session.completed event."""
    metadata = event_data.get("metadata", {})

    # Check if this is a subscription checkout (Pro/Team)
    if metadata.get("subscription_checkout") == "true":
        organization_id = metadata.get("organization_id")
        billing_account_id = metadata.get("billing_account_id")
        tier = metadata.get("tier", "pro")
        stripe_subscription_id = event_data.get("subscription")  # Stripe subscription ID

        if organization_id and billing_account_id:
            subscription_service = get_subscription_service(billing_service.db)

            # Cancel any existing free subscription first
            existing = subscription_service.get_subscription(UUID(organization_id))
            if existing and existing.tier == "free":
                subscription_service.cancel_subscription(existing.id, at_period_end=False)

            # Create the new paid subscription
            from omoi_os.models.subscription import SubscriptionTier
            tier_enum = SubscriptionTier.PRO if tier == "pro" else SubscriptionTier.TEAM

            subscription = subscription_service.create_subscription(
                organization_id=UUID(organization_id),
                billing_account_id=UUID(billing_account_id),
                tier=tier_enum,
            )

            # Link to Stripe subscription
            if stripe_subscription_id:
                with billing_service.db.get_session() as sess:
                    from sqlalchemy import select
                    from omoi_os.models.subscription import Subscription

                    result = sess.execute(
                        select(Subscription).where(Subscription.id == subscription.id)
                    )
                    sub = result.scalar_one_or_none()
                    if sub:
                        sub.stripe_subscription_id = stripe_subscription_id
                        sess.commit()

            logger.info(f"Created {tier} subscription for org {organization_id}")
        return

    # Check if this is a lifetime purchase
    if metadata.get("lifetime_purchase") == "true":
        organization_id = metadata.get("organization_id")
        billing_account_id = metadata.get("billing_account_id")
        purchase_amount = float(metadata.get("purchase_amount", LIFETIME_PRICE_USD))

        if organization_id and billing_account_id:
            subscription_service = get_subscription_service(billing_service.db)

            # Cancel any existing subscription first
            existing = subscription_service.get_subscription(UUID(organization_id))
            if existing and not existing.is_lifetime:
                subscription_service.cancel_subscription(existing.id, at_period_end=False)

            # Create lifetime subscription
            subscription_service.create_lifetime_subscription(
                organization_id=UUID(organization_id),
                billing_account_id=UUID(billing_account_id),
                purchase_amount=purchase_amount,
            )
            logger.info(f"Created lifetime subscription for org {organization_id} (${purchase_amount:.2f})")
        return

    # Check if this is a credit purchase
    if metadata.get("credit_purchase") == "true":
        credit_amount = float(metadata.get("credit_amount_usd", 0))
        organization_id = metadata.get("organization_id")

        if credit_amount > 0 and organization_id:
            billing_service.add_credits(
                billing_account_id=UUID(organization_id),
                amount_usd=credit_amount,
                reason="stripe_checkout",
            )
            logger.info(f"Added ${credit_amount:.2f} credits from checkout for org {organization_id}")


async def _handle_payment_succeeded(event_data: dict, billing_service: BillingService):
    """Handle payment_intent.succeeded event."""
    metadata = event_data.get("metadata", {})

    invoice_id = metadata.get("invoice_id")

    if invoice_id:
        # Update invoice status
        with billing_service.db.get_session() as sess:
            from sqlalchemy import select
            from omoi_os.models.billing import Invoice, InvoiceStatus

            result = sess.execute(
                select(Invoice).where(Invoice.id == UUID(invoice_id))
            )
            invoice = result.scalar_one_or_none()

            if invoice and invoice.status != InvoiceStatus.PAID.value:
                invoice.mark_paid(event_data.get("amount_received", 0) / 100)
                sess.commit()
                logger.info(f"Marked invoice {invoice_id} as paid from webhook")


async def _handle_payment_failed(event_data: dict, billing_service: BillingService):
    """Handle payment_intent.payment_failed event."""
    metadata = event_data.get("metadata", {})
    invoice_id = metadata.get("invoice_id")

    if invoice_id:
        with billing_service.db.get_session() as sess:
            from sqlalchemy import select
            from omoi_os.models.billing import Invoice, InvoiceStatus

            result = sess.execute(
                select(Invoice).where(Invoice.id == UUID(invoice_id))
            )
            invoice = result.scalar_one_or_none()

            if invoice:
                invoice.status = InvoiceStatus.PAST_DUE.value
                sess.commit()
                logger.warning(f"Marked invoice {invoice_id} as past due from webhook")


async def _handle_refund(event_data: dict, billing_service: BillingService):
    """Handle charge.refunded event."""
    # Find and update the payment record
    payment_intent_id = event_data.get("payment_intent")
    refund_amount = event_data.get("amount_refunded", 0) / 100  # Convert from cents

    if payment_intent_id:
        with billing_service.db.get_session() as sess:
            from sqlalchemy import select
            from omoi_os.models.billing import Payment

            result = sess.execute(
                select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
            )
            payment = result.scalar_one_or_none()

            if payment:
                payment.refund(refund_amount)
                sess.commit()
                logger.info(f"Recorded refund of ${refund_amount:.2f} for payment {payment.id}")


# ========== Subscription Webhook Handlers ==========

async def _handle_subscription_created(event_data: dict, billing_service: BillingService):
    """Handle customer.subscription.created event.

    Creates or updates local subscription record when subscription is created in Stripe.
    """
    from datetime import datetime
    from sqlalchemy import select
    from omoi_os.models.billing import BillingAccount
    from omoi_os.models.subscription import Subscription, SubscriptionStatus, SubscriptionTier, TIER_LIMITS
    from uuid import uuid4

    stripe_subscription_id = event_data.get("id")
    stripe_customer_id = event_data.get("customer")
    stripe_price_id = event_data.get("items", {}).get("data", [{}])[0].get("price", {}).get("id")
    stripe_product_id = event_data.get("items", {}).get("data", [{}])[0].get("price", {}).get("product")
    metadata = event_data.get("metadata", {})

    with billing_service.db.get_session() as sess:
        # Find billing account by Stripe customer ID
        result = sess.execute(
            select(BillingAccount).where(BillingAccount.stripe_customer_id == stripe_customer_id)
        )
        account = result.scalar_one_or_none()

        if not account:
            logger.warning(f"No billing account found for Stripe customer: {stripe_customer_id}")
            return

        # Determine tier from metadata or product
        tier_value = metadata.get("tier", "starter")
        try:
            tier = SubscriptionTier(tier_value)
        except ValueError:
            tier = SubscriptionTier.STARTER

        limits = TIER_LIMITS.get(tier, TIER_LIMITS[SubscriptionTier.FREE])

        # Check for existing subscription
        existing = sess.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_subscription_id
            )
        ).scalar_one_or_none()

        if existing:
            logger.info(f"Subscription already exists for Stripe ID: {stripe_subscription_id}")
            return

        # Create new subscription
        subscription = Subscription(
            id=uuid4(),
            organization_id=account.organization_id,
            billing_account_id=account.id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_price_id=stripe_price_id,
            stripe_product_id=stripe_product_id,
            tier=tier.value,
            status=SubscriptionStatus.ACTIVE.value if event_data.get("status") == "active" else SubscriptionStatus.TRIALING.value,
            current_period_start=datetime.fromtimestamp(event_data.get("current_period_start", 0)) if event_data.get("current_period_start") else None,
            current_period_end=datetime.fromtimestamp(event_data.get("current_period_end", 0)) if event_data.get("current_period_end") else None,
            workflows_limit=limits["workflows_limit"],
            workflows_used=0,
            agents_limit=limits["agents_limit"],
            storage_limit_gb=limits["storage_limit_gb"],
        )

        # Handle trial
        if event_data.get("trial_start"):
            subscription.trial_start = datetime.fromtimestamp(event_data["trial_start"])
        if event_data.get("trial_end"):
            subscription.trial_end = datetime.fromtimestamp(event_data["trial_end"])

        sess.add(subscription)
        sess.commit()

        logger.info(f"Created subscription {subscription.id} for org {account.organization_id} (tier: {tier.value})")


async def _handle_subscription_updated(event_data: dict, billing_service: BillingService):
    """Handle customer.subscription.updated event.

    Updates local subscription when Stripe subscription is modified.
    """
    from datetime import datetime
    from sqlalchemy import select
    from omoi_os.models.subscription import Subscription, SubscriptionStatus, SubscriptionTier, TIER_LIMITS

    stripe_subscription_id = event_data.get("id")
    metadata = event_data.get("metadata", {})

    with billing_service.db.get_session() as sess:
        result = sess.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.warning(f"Subscription not found for Stripe ID: {stripe_subscription_id}")
            return

        # Update status
        stripe_status = event_data.get("status")
        status_map = {
            "active": SubscriptionStatus.ACTIVE.value,
            "trialing": SubscriptionStatus.TRIALING.value,
            "past_due": SubscriptionStatus.PAST_DUE.value,
            "canceled": SubscriptionStatus.CANCELED.value,
            "paused": SubscriptionStatus.PAUSED.value,
            "incomplete": SubscriptionStatus.INCOMPLETE.value,
        }
        subscription.status = status_map.get(stripe_status, SubscriptionStatus.ACTIVE.value)

        # Update period
        if event_data.get("current_period_start"):
            subscription.current_period_start = datetime.fromtimestamp(event_data["current_period_start"])
        if event_data.get("current_period_end"):
            subscription.current_period_end = datetime.fromtimestamp(event_data["current_period_end"])

        subscription.cancel_at_period_end = event_data.get("cancel_at_period_end", False)

        if event_data.get("canceled_at"):
            subscription.canceled_at = datetime.fromtimestamp(event_data["canceled_at"])

        # Update tier if changed
        new_tier_value = metadata.get("tier")
        if new_tier_value and new_tier_value != subscription.tier:
            try:
                new_tier = SubscriptionTier(new_tier_value)
                limits = TIER_LIMITS.get(new_tier, TIER_LIMITS[SubscriptionTier.FREE])
                subscription.tier = new_tier.value
                subscription.workflows_limit = limits["workflows_limit"]
                subscription.agents_limit = limits["agents_limit"]
                subscription.storage_limit_gb = limits["storage_limit_gb"]
                logger.info(f"Updated subscription {subscription.id} tier to {new_tier.value}")
            except ValueError:
                pass

        sess.commit()
        logger.info(f"Updated subscription {subscription.id} (status: {subscription.status})")


async def _handle_subscription_deleted(event_data: dict, billing_service: BillingService):
    """Handle customer.subscription.deleted event.

    Marks local subscription as canceled when Stripe subscription is deleted.
    """
    from sqlalchemy import select
    from omoi_os.models.subscription import Subscription, SubscriptionStatus
    from omoi_os.utils.datetime import utc_now

    stripe_subscription_id = event_data.get("id")

    with billing_service.db.get_session() as sess:
        result = sess.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.warning(f"Subscription not found for Stripe ID: {stripe_subscription_id}")
            return

        subscription.status = SubscriptionStatus.CANCELED.value
        subscription.canceled_at = utc_now()

        sess.commit()
        logger.info(f"Canceled subscription {subscription.id}")


async def _handle_subscription_invoice_paid(event_data: dict, billing_service: BillingService):
    """Handle invoice.paid event for subscription renewals.

    Resets usage counters for the new billing period.
    """
    from sqlalchemy import select
    from omoi_os.models.subscription import Subscription

    # Check if this is a subscription invoice
    subscription_id = event_data.get("subscription")
    if not subscription_id:
        return  # Not a subscription invoice

    with billing_service.db.get_session() as sess:
        result = sess.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.warning(f"Subscription not found for Stripe ID: {subscription_id}")
            return

        # Reset usage for new period
        subscription.reset_usage()

        sess.commit()
        logger.info(f"Reset usage for subscription {subscription.id} (invoice paid)")


async def _handle_subscription_invoice_failed(event_data: dict, billing_service: BillingService):
    """Handle invoice.payment_failed event for subscriptions.

    Marks subscription as past_due and may trigger dunning.
    """
    from sqlalchemy import select
    from omoi_os.models.subscription import Subscription, SubscriptionStatus
    from omoi_os.models.billing import BillingAccount, BillingAccountStatus

    # Check if this is a subscription invoice
    subscription_id = event_data.get("subscription")
    if not subscription_id:
        return  # Not a subscription invoice

    with billing_service.db.get_session() as sess:
        result = sess.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.warning(f"Subscription not found for Stripe ID: {subscription_id}")
            return

        # Update subscription status
        subscription.status = SubscriptionStatus.PAST_DUE.value

        # Also update billing account status
        result = sess.execute(
            select(BillingAccount).where(
                BillingAccount.id == subscription.billing_account_id
            )
        )
        account = result.scalar_one_or_none()

        if account:
            account.status = BillingAccountStatus.SUSPENDED.value

        sess.commit()
        logger.warning(
            f"Subscription {subscription.id} marked past_due due to payment failure"
        )


# ========== Cost Tracking Endpoints ==========

@router.get(
    "/account/{organization_id}/costs/summary",
    response_model=CostSummaryResponse,
    summary="Get cost summary for billing account",
    description="Returns aggregated costs grouped by provider and model for a billing account.",
)
async def get_billing_account_cost_summary(
    organization_id: UUID,
    billing_service: BillingService = Depends(get_billing_service_dep),
    cost_service: CostTrackingService = Depends(get_cost_tracking_service_dep),
) -> CostSummaryResponse:
    """Get cost summary for a billing account."""
    # Get billing account for organization
    account = billing_service.get_billing_account(organization_id)
    if not account:
        raise HTTPException(status_code=404, detail="Billing account not found")

    # Get cost summary
    summary = cost_service.get_cost_summary(
        scope_type="billing_account",
        scope_id=str(account.id),
    )

    # Transform breakdown to response model
    breakdown = [
        CostBreakdownItem(
            provider=item["provider"],
            model=item["model"],
            cost=item["cost"],
            tokens=item["tokens"],
            records=item["records"],
        )
        for item in summary.get("breakdown", [])
    ]

    return CostSummaryResponse(
        scope_type=summary["scope_type"],
        scope_id=summary.get("scope_id"),
        total_cost=summary["total_cost"],
        total_tokens=summary["total_tokens"],
        record_count=summary["record_count"],
        breakdown=breakdown,
    )


@router.get(
    "/account/{organization_id}/costs",
    response_model=list[CostRecordResponse],
    summary="Get cost records for billing account",
    description="Returns all cost records for a billing account.",
)
async def get_billing_account_costs(
    organization_id: UUID,
    billing_service: BillingService = Depends(get_billing_service_dep),
    cost_service: CostTrackingService = Depends(get_cost_tracking_service_dep),
) -> list[CostRecordResponse]:
    """Get cost records for a billing account."""
    # Get billing account for organization
    account = billing_service.get_billing_account(organization_id)
    if not account:
        raise HTTPException(status_code=404, detail="Billing account not found")

    # Get cost records
    records = cost_service.get_billing_account_costs(str(account.id))

    return [
        CostRecordResponse(
            id=str(record.id),
            task_id=record.task_id,
            agent_id=record.agent_id,
            sandbox_id=record.sandbox_id,
            billing_account_id=record.billing_account_id,
            provider=record.provider,
            model=record.model,
            prompt_tokens=record.prompt_tokens,
            completion_tokens=record.completion_tokens,
            total_tokens=record.total_tokens,
            prompt_cost=record.prompt_cost,
            completion_cost=record.completion_cost,
            total_cost=record.total_cost,
            recorded_at=record.recorded_at,
        )
        for record in records
    ]
