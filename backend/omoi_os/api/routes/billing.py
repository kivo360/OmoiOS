"""Billing API routes for payment processing and invoice management."""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, Field

from omoi_os.api.dependencies import get_database_service
from omoi_os.services.billing_service import BillingService, get_billing_service
from omoi_os.services.database import DatabaseService
from omoi_os.services.stripe_service import get_stripe_service, StripeService

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


# ========== Dependency Injection ==========

def get_billing_service_dep(
    db: DatabaseService = Depends(get_database_service),
) -> BillingService:
    """Get billing service instance."""
    return get_billing_service(db)


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
