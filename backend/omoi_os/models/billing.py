"""Billing models for payment processing and invoicing.

Supports pay-per-workflow billing model with Stripe integration.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.organization import Organization
    from omoi_os.models.subscription import Subscription


class BillingAccountStatus(str, Enum):
    """Status of a billing account."""

    ACTIVE = "active"
    SUSPENDED = "suspended"  # Payment failed, in dunning
    CANCELED = "canceled"
    PENDING = "pending"  # Awaiting first payment method


class InvoiceStatus(str, Enum):
    """Status of an invoice."""

    DRAFT = "draft"
    OPEN = "open"  # Finalized, awaiting payment
    PAID = "paid"
    PAST_DUE = "past_due"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


class PaymentStatus(str, Enum):
    """Status of a payment attempt."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class BillingAccount(Base):
    """Billing account linked to an organization.

    Manages payment methods, credits, and billing preferences.
    Each organization has one billing account.
    """

    __tablename__ = "billing_accounts"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    # Organization link (one-to-one)
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Stripe integration
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    stripe_payment_method_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # Default payment method

    # Account status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=BillingAccountStatus.PENDING.value
    )

    # Free tier tracking
    free_workflows_remaining: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5
    )  # 5 free workflows per month for new users
    free_workflows_reset_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Prepaid credits (in USD)
    credit_balance: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )

    # Billing preferences
    auto_billing_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )  # Auto-charge for usage above free tier
    billing_email: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # Override org billing email

    # Tax information
    tax_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # VAT/GST number
    tax_exempt: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Address for tax calculation
    billing_address: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # {line1, line2, city, state, postal_code, country}

    # Usage statistics (cached for quick access)
    total_workflows_completed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_amount_spent: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        back_populates="billing_account"
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        back_populates="billing_account",
        cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="billing_account",
        cascade="all, delete-orphan"
    )
    subscription: Mapped[Optional["Subscription"]] = relationship(
        back_populates="billing_account",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        {"comment": "Billing accounts for organizations with Stripe integration"}
    )

    def __repr__(self) -> str:
        return (
            f"<BillingAccount(id={self.id}, org_id={self.organization_id}, "
            f"status={self.status}, credits=${self.credit_balance:.2f})>"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "stripe_customer_id": self.stripe_customer_id,
            "has_payment_method": self.stripe_payment_method_id is not None,
            "status": self.status,
            "free_workflows_remaining": self.free_workflows_remaining,
            "free_workflows_reset_at": self.free_workflows_reset_at.isoformat() if self.free_workflows_reset_at else None,
            "credit_balance": self.credit_balance,
            "auto_billing_enabled": self.auto_billing_enabled,
            "billing_email": self.billing_email,
            "tax_exempt": self.tax_exempt,
            "total_workflows_completed": self.total_workflows_completed,
            "total_amount_spent": self.total_amount_spent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def can_use_free_workflow(self) -> bool:
        """Check if account has free workflows available."""
        return self.free_workflows_remaining > 0

    def use_free_workflow(self) -> bool:
        """Consume a free workflow. Returns True if successful."""
        if self.free_workflows_remaining > 0:
            self.free_workflows_remaining -= 1
            return True
        return False

    def add_credits(self, amount: float) -> None:
        """Add credits to the account."""
        self.credit_balance += amount

    def use_credits(self, amount: float) -> float:
        """Use credits for payment. Returns amount actually used."""
        if self.credit_balance >= amount:
            self.credit_balance -= amount
            return amount
        else:
            used = self.credit_balance
            self.credit_balance = 0.0
            return used


class Invoice(Base):
    """Invoice for workflow usage charges.

    Generated for each billing period or on-demand for prepaid credits.
    """

    __tablename__ = "invoices"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    # Invoice number (human-readable)
    invoice_number: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )

    # Billing account link
    billing_account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("billing_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Optional ticket association (for per-workflow invoices)
    ticket_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Stripe integration
    stripe_invoice_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # Invoice status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=InvoiceStatus.DRAFT.value, index=True
    )

    # Billing period (for usage-based invoices)
    period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Amounts (in USD)
    subtotal: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    tax_amount: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    discount_amount: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    total: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, index=True
    )

    # Credits applied
    credits_applied: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    amount_due: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )  # total - credits_applied
    amount_paid: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )

    # Currency
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="usd"
    )

    # Line items (JSONB for flexibility)
    line_items: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list
    )  # [{description, quantity, unit_price, total, ticket_id?, task_id?}]

    # Invoice details
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )

    # Tax details
    tax_details: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # {tax_rate, jurisdiction, tax_type}

    # Important dates
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    finalized_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    voided_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    billing_account: Mapped["BillingAccount"] = relationship(
        back_populates="invoices"
    )
    ticket = relationship(
        "Ticket",
        foreign_keys=[ticket_id]
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_invoice_status_due", "status", "due_date"),
        {"comment": "Invoices for workflow usage billing"}
    )

    def __repr__(self) -> str:
        return (
            f"<Invoice(id={self.id}, number={self.invoice_number}, "
            f"status={self.status}, total=${self.total:.2f})>"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "invoice_number": self.invoice_number,
            "billing_account_id": str(self.billing_account_id),
            "ticket_id": str(self.ticket_id) if self.ticket_id else None,
            "stripe_invoice_id": self.stripe_invoice_id,
            "status": self.status,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "subtotal": self.subtotal,
            "tax_amount": self.tax_amount,
            "discount_amount": self.discount_amount,
            "total": self.total,
            "credits_applied": self.credits_applied,
            "amount_due": self.amount_due,
            "amount_paid": self.amount_paid,
            "currency": self.currency,
            "line_items": self.line_items,
            "description": self.description,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "finalized_at": self.finalized_at.isoformat() if self.finalized_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def add_line_item(
        self,
        description: str,
        unit_price: float,
        quantity: int = 1,
        ticket_id: str | None = None,
        task_id: str | None = None
    ) -> None:
        """Add a line item to the invoice."""
        line_item = {
            "description": description,
            "quantity": quantity,
            "unit_price": unit_price,
            "total": unit_price * quantity,
        }
        if ticket_id:
            line_item["ticket_id"] = ticket_id
        if task_id:
            line_item["task_id"] = task_id

        self.line_items = self.line_items + [line_item]
        self._recalculate_totals()

    def _recalculate_totals(self) -> None:
        """Recalculate invoice totals from line items."""
        self.subtotal = sum(item["total"] for item in self.line_items)
        self.total = self.subtotal + self.tax_amount - self.discount_amount
        self.amount_due = self.total - self.credits_applied - self.amount_paid

    def finalize(self) -> None:
        """Finalize the invoice (no more changes allowed)."""
        self._recalculate_totals()
        self.status = InvoiceStatus.OPEN.value
        self.finalized_at = utc_now()

    def mark_paid(self, amount: float | None = None) -> None:
        """Mark invoice as paid."""
        self.amount_paid = amount if amount is not None else self.amount_due
        self.amount_due = self.total - self.credits_applied - self.amount_paid
        if self.amount_due <= 0:
            self.status = InvoiceStatus.PAID.value
            self.paid_at = utc_now()

    def void(self) -> None:
        """Void the invoice."""
        self.status = InvoiceStatus.VOID.value
        self.voided_at = utc_now()


class Payment(Base):
    """Payment record for invoice charges.

    Tracks payment attempts and their status.
    """

    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    # Billing account link
    billing_account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("billing_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Invoice link (optional - credits purchase may not have invoice)
    invoice_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Stripe integration
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    stripe_charge_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # Payment details
    amount: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="usd"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PaymentStatus.PENDING.value, index=True
    )

    # Payment method info (snapshot at time of payment)
    payment_method_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # card, bank_transfer, etc.
    payment_method_last4: Mapped[Optional[str]] = mapped_column(
        String(4), nullable=True
    )  # Last 4 digits of card
    payment_method_brand: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # visa, mastercard, etc.

    # Error tracking for failed payments
    failure_code: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    failure_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )

    # Refund tracking
    refunded_amount: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    refund_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )

    # Description
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )

    # Extra payment data
    payment_data: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # Additional Stripe data

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    succeeded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    billing_account: Mapped["BillingAccount"] = relationship(
        back_populates="payments"
    )
    invoice: Mapped[Optional["Invoice"]] = relationship(
        back_populates="payments"
    )

    __table_args__ = (
        Index("idx_payment_status_created", "status", "created_at"),
        {"comment": "Payment records for invoice charges"}
    )

    def __repr__(self) -> str:
        return (
            f"<Payment(id={self.id}, amount=${self.amount:.2f}, "
            f"status={self.status})>"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "billing_account_id": str(self.billing_account_id),
            "invoice_id": str(self.invoice_id) if self.invoice_id else None,
            "stripe_payment_intent_id": self.stripe_payment_intent_id,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "payment_method_type": self.payment_method_type,
            "payment_method_last4": self.payment_method_last4,
            "payment_method_brand": self.payment_method_brand,
            "failure_code": self.failure_code,
            "failure_message": self.failure_message,
            "refunded_amount": self.refunded_amount,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "succeeded_at": self.succeeded_at.isoformat() if self.succeeded_at else None,
        }

    def mark_succeeded(self) -> None:
        """Mark payment as succeeded."""
        self.status = PaymentStatus.SUCCEEDED.value
        self.succeeded_at = utc_now()

    def mark_failed(self, code: str, message: str) -> None:
        """Mark payment as failed with error details."""
        self.status = PaymentStatus.FAILED.value
        self.failure_code = code
        self.failure_message = message

    def refund(self, amount: float | None = None, reason: str | None = None) -> None:
        """Process a refund."""
        refund_amount = amount if amount is not None else self.amount
        self.refunded_amount += refund_amount
        self.refund_reason = reason

        if self.refunded_amount >= self.amount:
            self.status = PaymentStatus.REFUNDED.value
        else:
            self.status = PaymentStatus.PARTIALLY_REFUNDED.value


class UsageRecord(Base):
    """Record of workflow usage for billing aggregation.

    Tracks individual workflow completions for billing purposes.
    """

    __tablename__ = "usage_records"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    # Billing account link
    billing_account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("billing_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # What was used
    ticket_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Usage type
    usage_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # workflow_completion, llm_tokens, etc.

    # Quantity and pricing
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    unit_price: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    total_price: Mapped[float] = mapped_column(
        Float, nullable=False
    )

    # Was free tier used?
    free_tier_used: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Invoice association (once billed)
    invoice_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    billed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )

    # Usage details
    usage_details: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # {input_tokens, output_tokens, model, duration_seconds, etc.}

    # Timestamps
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    billed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("idx_usage_unbilled", "billing_account_id", "billed"),
        Index("idx_usage_recorded", "billing_account_id", "recorded_at"),
        {"comment": "Usage records for workflow billing"}
    )

    def __repr__(self) -> str:
        return (
            f"<UsageRecord(id={self.id}, type={self.usage_type}, "
            f"quantity={self.quantity}, total=${self.total_price:.2f})>"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "billing_account_id": str(self.billing_account_id),
            "ticket_id": str(self.ticket_id) if self.ticket_id else None,
            "usage_type": self.usage_type,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total_price": self.total_price,
            "free_tier_used": self.free_tier_used,
            "invoice_id": str(self.invoice_id) if self.invoice_id else None,
            "billed": self.billed,
            "usage_details": self.usage_details,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "billed_at": self.billed_at.isoformat() if self.billed_at else None,
        }

    def mark_billed(self, invoice_id: UUID) -> None:
        """Mark usage as billed on an invoice."""
        self.invoice_id = invoice_id
        self.billed = True
        self.billed_at = utc_now()
