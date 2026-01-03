"""Stripe integration service for payment processing.

Handles customer management, payment intents, subscriptions, and webhook processing.
Follows PCI compliance best practices by never handling raw card data on the server.
"""

import logging
from typing import Optional
from uuid import UUID

import stripe
from stripe import StripeError, InvalidRequestError, CardError, SignatureVerificationError

from omoi_os.config import OmoiBaseSettings, get_env_files
from pydantic_settings import SettingsConfigDict
from functools import lru_cache

logger = logging.getLogger(__name__)


class StripeSettings(OmoiBaseSettings):
    """Stripe configuration settings."""

    yaml_section = "billing"
    model_config = SettingsConfigDict(
        env_prefix="STRIPE_",
        env_file=get_env_files(),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # API keys (from environment only - never in YAML)
    api_key: Optional[str] = None  # STRIPE_API_KEY
    webhook_secret: Optional[str] = None  # STRIPE_WEBHOOK_SECRET
    publishable_key: Optional[str] = None  # STRIPE_PUBLISHABLE_KEY

    # Billing configuration (from YAML)
    currency: str = "usd"
    workflow_price_usd: float = 10.0  # $10 per workflow completion
    free_workflows_per_month: int = 5

    # URLs
    success_url: str = "http://localhost:3000/billing/success"
    cancel_url: str = "http://localhost:3000/billing/cancel"
    portal_return_url: str = "http://localhost:3000/billing"


@lru_cache(maxsize=1)
def load_stripe_settings() -> StripeSettings:
    """Load Stripe settings (cached)."""
    return StripeSettings()


class StripeService:
    """Service for Stripe payment processing.

    Responsibilities:
    - Create and manage Stripe customers
    - Process payments via Payment Intents
    - Create checkout sessions for hosted payment flow
    - Handle subscriptions and prepaid credits
    - Process refunds
    - Verify and handle webhooks
    """

    def __init__(self, settings: Optional[StripeSettings] = None):
        self.settings = settings or load_stripe_settings()

        # Configure Stripe API key
        if self.settings.api_key:
            stripe.api_key = self.settings.api_key
        else:
            logger.warning("Stripe API key not configured - payment processing disabled")

    @property
    def is_configured(self) -> bool:
        """Check if Stripe is properly configured."""
        return bool(self.settings.api_key)

    # ========== Customer Management ==========

    def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        organization_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> stripe.Customer:
        """Create a Stripe customer.

        Args:
            email: Customer email address
            name: Customer/organization name
            organization_id: OmoiOS organization ID for linking
            metadata: Additional metadata to store

        Returns:
            Created Stripe customer object
        """
        customer_metadata = metadata or {}
        if organization_id:
            customer_metadata["organization_id"] = str(organization_id)

        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=customer_metadata,
            )
            logger.info(f"Created Stripe customer: {customer.id}")
            return customer
        except StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e.user_message}")
            raise

    def get_customer(self, customer_id: str) -> Optional[stripe.Customer]:
        """Retrieve a Stripe customer by ID."""
        try:
            return stripe.Customer.retrieve(customer_id)
        except InvalidRequestError:
            logger.warning(f"Customer not found: {customer_id}")
            return None
        except StripeError as e:
            logger.error(f"Failed to retrieve customer: {e.user_message}")
            raise

    def update_customer(
        self,
        customer_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> stripe.Customer:
        """Update a Stripe customer."""
        update_params = {}
        if email:
            update_params["email"] = email
        if name:
            update_params["name"] = name
        if metadata:
            update_params["metadata"] = metadata

        try:
            customer = stripe.Customer.modify(customer_id, **update_params)
            logger.info(f"Updated Stripe customer: {customer_id}")
            return customer
        except StripeError as e:
            logger.error(f"Failed to update customer: {e.user_message}")
            raise

    # ========== Payment Methods ==========

    def attach_payment_method(
        self,
        customer_id: str,
        payment_method_id: str,
        set_as_default: bool = True,
    ) -> stripe.PaymentMethod:
        """Attach a payment method to a customer.

        Args:
            customer_id: Stripe customer ID
            payment_method_id: Payment method ID from frontend
            set_as_default: Whether to set as default payment method

        Returns:
            Attached payment method
        """
        try:
            # Attach payment method to customer
            payment_method = stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id,
            )

            # Set as default if requested
            if set_as_default:
                stripe.Customer.modify(
                    customer_id,
                    invoice_settings={
                        "default_payment_method": payment_method_id
                    }
                )

            logger.info(f"Attached payment method {payment_method_id} to customer {customer_id}")
            return payment_method
        except StripeError as e:
            logger.error(f"Failed to attach payment method: {e.user_message}")
            raise

    def list_payment_methods(
        self,
        customer_id: str,
        payment_type: str = "card",
    ) -> list[stripe.PaymentMethod]:
        """List payment methods for a customer."""
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type=payment_type,
            )
            return payment_methods.data
        except StripeError as e:
            logger.error(f"Failed to list payment methods: {e.user_message}")
            raise

    def detach_payment_method(self, payment_method_id: str) -> stripe.PaymentMethod:
        """Detach a payment method from a customer."""
        try:
            payment_method = stripe.PaymentMethod.detach(payment_method_id)
            logger.info(f"Detached payment method: {payment_method_id}")
            return payment_method
        except StripeError as e:
            logger.error(f"Failed to detach payment method: {e.user_message}")
            raise

    # ========== Checkout Sessions (Hosted Payment Flow) ==========

    def create_checkout_session(
        self,
        customer_id: str,
        amount_cents: int,
        description: str,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> stripe.checkout.Session:
        """Create a Stripe Checkout Session for one-time payment.

        This is the simplest way to accept payments with minimal PCI burden.
        Redirects user to Stripe-hosted payment page.

        Args:
            customer_id: Stripe customer ID
            amount_cents: Amount in cents (e.g., 1000 for $10.00)
            description: Description for the payment
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancel
            metadata: Additional metadata (e.g., invoice_id, ticket_id)

        Returns:
            Checkout session with URL to redirect user to
        """
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": self.settings.currency,
                        "product_data": {
                            "name": description,
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=success_url or self.settings.success_url,
                cancel_url=cancel_url or self.settings.cancel_url,
                metadata=metadata or {},
            )
            logger.info(f"Created checkout session: {session.id}")
            return session
        except StripeError as e:
            logger.error(f"Failed to create checkout session: {e.user_message}")
            raise

    def create_credit_purchase_session(
        self,
        customer_id: str,
        credit_amount_usd: float,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        organization_id: Optional[UUID] = None,
    ) -> stripe.checkout.Session:
        """Create a checkout session for purchasing prepaid credits.

        Args:
            customer_id: Stripe customer ID
            credit_amount_usd: Amount of credits to purchase in USD
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancel
            organization_id: Organization buying credits

        Returns:
            Checkout session for credit purchase
        """
        amount_cents = int(credit_amount_usd * 100)

        metadata = {"credit_purchase": "true", "credit_amount_usd": str(credit_amount_usd)}
        if organization_id:
            metadata["organization_id"] = str(organization_id)

        return self.create_checkout_session(
            customer_id=customer_id,
            amount_cents=amount_cents,
            description=f"Prepaid Credits - ${credit_amount_usd:.2f}",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
        )

    def create_subscription_checkout_session(
        self,
        customer_id: str,
        price_id: Optional[str] = None,
        price_data: Optional[dict] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        metadata: Optional[dict] = None,
        idempotency_key: Optional[str] = None,
    ) -> stripe.checkout.Session:
        """Create a Stripe Checkout Session for subscription.

        Args:
            customer_id: Stripe customer ID
            price_id: Existing Stripe price ID (preferred)
            price_data: Dynamic price data if no price_id (name, description, unit_amount, interval)
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancel
            metadata: Additional metadata
            idempotency_key: Optional key to prevent duplicate sessions

        Returns:
            Checkout session with URL to redirect user to
        """
        try:
            line_item = {}
            if price_id:
                line_item = {"price": price_id, "quantity": 1}
            elif price_data:
                line_item = {
                    "price_data": {
                        "currency": self.settings.currency,
                        "unit_amount": price_data["unit_amount"],
                        "recurring": {"interval": price_data.get("interval", "month")},
                        "product_data": {
                            "name": price_data["name"],
                            "description": price_data.get("description", ""),
                        },
                    },
                    "quantity": 1,
                }
            else:
                raise ValueError("Either price_id or price_data must be provided")

            # Build create params
            create_params = {
                "customer": customer_id,
                "line_items": [line_item],
                "mode": "subscription",
                "success_url": success_url or self.settings.success_url,
                "cancel_url": cancel_url or self.settings.cancel_url,
                "metadata": metadata or {},
                # Allow customers to reuse saved payment methods instead of always adding new cards
                "payment_method_collection": "if_required",
                "saved_payment_method_options": {
                    "payment_method_save": "enabled",
                },
            }

            # Use idempotency key if provided to prevent duplicate sessions
            if idempotency_key:
                session = stripe.checkout.Session.create(
                    **create_params,
                    idempotency_key=idempotency_key,
                )
            else:
                session = stripe.checkout.Session.create(**create_params)

            logger.info(f"Created subscription checkout session: {session.id}")
            return session
        except StripeError as e:
            logger.error(f"Failed to create subscription checkout session: {e.user_message}")
            raise

    # ========== Payment Intents (Custom UI Flow) ==========

    def create_payment_intent(
        self,
        customer_id: str,
        amount_cents: int,
        metadata: Optional[dict] = None,
    ) -> stripe.PaymentIntent:
        """Create a payment intent for custom checkout UI.

        The client_secret returned should be sent to the frontend
        to complete the payment using Stripe.js.

        Args:
            customer_id: Stripe customer ID
            amount_cents: Amount in cents
            metadata: Additional metadata

        Returns:
            PaymentIntent with client_secret for frontend
        """
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=self.settings.currency,
                customer=customer_id,
                automatic_payment_methods={
                    "enabled": True,
                },
                metadata=metadata or {},
            )
            logger.info(f"Created payment intent: {intent.id}")
            return intent
        except StripeError as e:
            logger.error(f"Failed to create payment intent: {e.user_message}")
            raise

    def retrieve_payment_intent(self, payment_intent_id: str) -> stripe.PaymentIntent:
        """Retrieve a payment intent by ID."""
        try:
            return stripe.PaymentIntent.retrieve(payment_intent_id)
        except StripeError as e:
            logger.error(f"Failed to retrieve payment intent: {e.user_message}")
            raise

    def charge_customer_directly(
        self,
        customer_id: str,
        amount_cents: int,
        description: str,
        payment_method_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> stripe.PaymentIntent:
        """Charge a customer using their saved payment method.

        Useful for automated billing where user isn't present.

        Args:
            customer_id: Stripe customer ID
            amount_cents: Amount to charge in cents
            description: Description for the charge
            payment_method_id: Specific payment method to use (uses default if not provided)
            metadata: Additional metadata

        Returns:
            Confirmed PaymentIntent
        """
        try:
            # Get default payment method if not specified
            if not payment_method_id:
                customer = stripe.Customer.retrieve(customer_id)
                payment_method_id = customer.invoice_settings.get("default_payment_method")
                if not payment_method_id:
                    raise ValueError("Customer has no default payment method")

            # Create and confirm payment intent
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=self.settings.currency,
                customer=customer_id,
                payment_method=payment_method_id,
                off_session=True,  # Customer not present
                confirm=True,  # Confirm immediately
                description=description,
                metadata=metadata or {},
            )

            logger.info(f"Charged customer {customer_id} for {amount_cents} cents: {intent.id}")
            return intent
        except CardError as e:
            # Card was declined
            logger.warning(f"Card declined for customer {customer_id}: {e.user_message}")
            raise
        except StripeError as e:
            logger.error(f"Failed to charge customer: {e.user_message}")
            raise

    # ========== Billing Portal ==========

    def create_portal_session(
        self,
        customer_id: str,
        return_url: Optional[str] = None,
    ) -> stripe.billing_portal.Session:
        """Create a Stripe Customer Portal session.

        The portal allows customers to manage their payment methods
        and view billing history.

        Args:
            customer_id: Stripe customer ID
            return_url: URL to return to after portal session

        Returns:
            Portal session with URL to redirect user to
        """
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url or self.settings.portal_return_url,
            )
            logger.info(f"Created portal session for customer: {customer_id}")
            return session
        except StripeError as e:
            logger.error(f"Failed to create portal session: {e.user_message}")
            raise

    # ========== Refunds ==========

    def create_refund(
        self,
        payment_intent_id: str,
        amount_cents: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> stripe.Refund:
        """Create a refund for a payment.

        Args:
            payment_intent_id: Payment intent to refund
            amount_cents: Amount to refund (full refund if not specified)
            reason: Reason for refund ('duplicate', 'fraudulent', 'requested_by_customer')

        Returns:
            Created refund object
        """
        refund_params = {
            "payment_intent": payment_intent_id,
        }

        if amount_cents:
            refund_params["amount"] = amount_cents

        if reason:
            refund_params["reason"] = reason

        try:
            refund = stripe.Refund.create(**refund_params)
            logger.info(f"Created refund: {refund.id} for payment intent: {payment_intent_id}")
            return refund
        except StripeError as e:
            logger.error(f"Failed to create refund: {e.user_message}")
            raise

    # ========== Webhook Verification ==========

    def verify_webhook(self, payload: bytes, signature: str) -> stripe.Event:
        """Verify and parse a Stripe webhook event.

        Args:
            payload: Raw webhook payload bytes
            signature: Stripe-Signature header value

        Returns:
            Verified Stripe event object

        Raises:
            ValueError: If webhook secret is not configured
            SignatureVerificationError: If signature is invalid
        """
        if not self.settings.webhook_secret:
            raise ValueError("Stripe webhook secret not configured")

        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.settings.webhook_secret,
            )
            logger.debug(f"Verified webhook event: {event.type}")
            return event
        except SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise

    # ========== Invoices ==========

    def create_invoice(
        self,
        customer_id: str,
        description: str,
        amount_cents: int,
        metadata: Optional[dict] = None,
        auto_advance: bool = True,
    ) -> stripe.Invoice:
        """Create a Stripe invoice.

        Args:
            customer_id: Stripe customer ID
            description: Invoice description
            amount_cents: Amount in cents
            metadata: Additional metadata
            auto_advance: Whether to auto-finalize and send the invoice

        Returns:
            Created invoice
        """
        try:
            # Create an invoice item first
            stripe.InvoiceItem.create(
                customer=customer_id,
                amount=amount_cents,
                currency=self.settings.currency,
                description=description,
            )

            # Create the invoice
            invoice = stripe.Invoice.create(
                customer=customer_id,
                auto_advance=auto_advance,
                metadata=metadata or {},
            )

            logger.info(f"Created invoice: {invoice.id}")
            return invoice
        except StripeError as e:
            logger.error(f"Failed to create invoice: {e.user_message}")
            raise

    def pay_invoice(self, invoice_id: str) -> stripe.Invoice:
        """Pay an invoice using the customer's default payment method."""
        try:
            invoice = stripe.Invoice.pay(invoice_id)
            logger.info(f"Paid invoice: {invoice_id}")
            return invoice
        except StripeError as e:
            logger.error(f"Failed to pay invoice: {e.user_message}")
            raise

    def retrieve_invoice(self, invoice_id: str) -> stripe.Invoice:
        """Retrieve an invoice by ID."""
        try:
            return stripe.Invoice.retrieve(invoice_id)
        except StripeError as e:
            logger.error(f"Failed to retrieve invoice: {e.user_message}")
            raise

    def list_customer_invoices(
        self,
        customer_id: str,
        limit: int = 50,
        status: Optional[str] = None,
    ) -> list[stripe.Invoice]:
        """List invoices for a customer from Stripe.

        Args:
            customer_id: Stripe customer ID
            limit: Maximum number of invoices to return
            status: Optional filter by status (draft, open, paid, uncollectible, void)

        Returns:
            List of Stripe invoice objects
        """
        try:
            params = {
                "customer": customer_id,
                "limit": limit,
            }
            if status:
                params["status"] = status

            invoices = stripe.Invoice.list(**params)
            logger.info(f"Listed {len(invoices.data)} invoices for customer {customer_id}")
            return list(invoices.data)
        except StripeError as e:
            logger.error(f"Failed to list invoices for customer {customer_id}: {e.user_message}")
            raise


# Singleton instance for easy access
_stripe_service: Optional[StripeService] = None


def get_stripe_service() -> StripeService:
    """Get or create the StripeService singleton."""
    global _stripe_service
    if _stripe_service is None:
        _stripe_service = StripeService()
    return _stripe_service
