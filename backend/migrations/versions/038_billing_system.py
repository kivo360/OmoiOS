"""Billing system tables for payment processing

Revision ID: 038_billing_system
Revises: 037_claude_session_transcripts
Create Date: 2025-12-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "038_billing_system"
down_revision: Union[str, None] = "037_claude_session_transcripts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Billing accounts table - one per organization
    op.create_table(
        "billing_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Stripe integration
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_payment_method_id", sa.String(length=255), nullable=True),
        # Account status
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        # Free tier tracking
        sa.Column("free_workflows_remaining", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("free_workflows_reset_at", sa.DateTime(timezone=True), nullable=True),
        # Prepaid credits (USD)
        sa.Column("credit_balance", sa.Float(), nullable=False, server_default="0.0"),
        # Billing preferences
        sa.Column("auto_billing_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("billing_email", sa.String(length=255), nullable=True),
        # Tax information
        sa.Column("tax_id", sa.String(length=100), nullable=True),
        sa.Column("tax_exempt", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("billing_address", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Usage statistics (cached)
        sa.Column("total_workflows_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_amount_spent", sa.Float(), nullable=False, server_default="0.0"),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id"),
        sa.UniqueConstraint("stripe_customer_id"),
        comment="Billing accounts for organizations with Stripe integration",
    )
    op.create_index("ix_billing_accounts_organization_id", "billing_accounts", ["organization_id"])
    op.create_index("ix_billing_accounts_stripe_customer_id", "billing_accounts", ["stripe_customer_id"])
    op.create_index("ix_billing_accounts_created_at", "billing_accounts", ["created_at"])

    # Invoices table
    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_number", sa.String(length=50), nullable=False),
        sa.Column("billing_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Stripe integration
        sa.Column("stripe_invoice_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_payment_intent_id", sa.String(length=255), nullable=True),
        # Invoice status
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        # Billing period
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        # Amounts (USD)
        sa.Column("subtotal", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("tax_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("discount_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("credits_applied", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("amount_due", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("amount_paid", sa.Float(), nullable=False, server_default="0.0"),
        # Currency
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="usd"),
        # Line items (JSONB)
        sa.Column(
            "line_items",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        # Invoice details
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("tax_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Important dates
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["billing_account_id"],
            ["billing_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_number"),
        sa.UniqueConstraint("stripe_invoice_id"),
        comment="Invoices for workflow usage billing",
    )
    op.create_index("ix_invoices_invoice_number", "invoices", ["invoice_number"])
    op.create_index("ix_invoices_billing_account_id", "invoices", ["billing_account_id"])
    op.create_index("ix_invoices_ticket_id", "invoices", ["ticket_id"])
    op.create_index("ix_invoices_stripe_invoice_id", "invoices", ["stripe_invoice_id"])
    op.create_index("ix_invoices_status", "invoices", ["status"])
    op.create_index("ix_invoices_total", "invoices", ["total"])
    op.create_index("ix_invoices_due_date", "invoices", ["due_date"])
    op.create_index("ix_invoices_created_at", "invoices", ["created_at"])
    op.create_index("ix_invoices_status_due", "invoices", ["status", "due_date"])

    # Payments table
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("billing_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Stripe integration
        sa.Column("stripe_payment_intent_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_charge_id", sa.String(length=255), nullable=True),
        # Payment details
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="usd"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        # Payment method info (snapshot)
        sa.Column("payment_method_type", sa.String(length=50), nullable=True),
        sa.Column("payment_method_last4", sa.String(length=4), nullable=True),
        sa.Column("payment_method_brand", sa.String(length=50), nullable=True),
        # Error tracking
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        # Refund tracking
        sa.Column("refunded_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("refund_reason", sa.Text(), nullable=True),
        # Description
        sa.Column("description", sa.Text(), nullable=True),
        # Extra payment data
        sa.Column("payment_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("succeeded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["billing_account_id"],
            ["billing_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_payment_intent_id"),
        comment="Payment records for invoice charges",
    )
    op.create_index("ix_payments_billing_account_id", "payments", ["billing_account_id"])
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"])
    op.create_index("ix_payments_stripe_payment_intent_id", "payments", ["stripe_payment_intent_id"])
    op.create_index("ix_payments_status", "payments", ["status"])
    op.create_index("ix_payments_created_at", "payments", ["created_at"])
    op.create_index("ix_payments_status_created", "payments", ["status", "created_at"])

    # Usage records table
    op.create_table(
        "usage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("billing_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Usage type
        sa.Column("usage_type", sa.String(length=50), nullable=False),
        # Quantity and pricing
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("total_price", sa.Float(), nullable=False),
        # Was free tier used?
        sa.Column("free_tier_used", sa.Boolean(), nullable=False, server_default="false"),
        # Invoice association
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("billed", sa.Boolean(), nullable=False, server_default="false"),
        # Usage details
        sa.Column("usage_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Timestamps
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("billed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["billing_account_id"],
            ["billing_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Usage records for workflow billing",
    )
    op.create_index("ix_usage_records_billing_account_id", "usage_records", ["billing_account_id"])
    op.create_index("ix_usage_records_ticket_id", "usage_records", ["ticket_id"])
    op.create_index("ix_usage_records_usage_type", "usage_records", ["usage_type"])
    op.create_index("ix_usage_records_invoice_id", "usage_records", ["invoice_id"])
    op.create_index("ix_usage_records_billed", "usage_records", ["billed"])
    op.create_index("ix_usage_records_recorded_at", "usage_records", ["recorded_at"])
    op.create_index("ix_usage_records_unbilled", "usage_records", ["billing_account_id", "billed"])
    op.create_index("ix_usage_records_recorded", "usage_records", ["billing_account_id", "recorded_at"])


def downgrade() -> None:
    # Drop usage_records table
    op.drop_index("ix_usage_records_recorded", table_name="usage_records")
    op.drop_index("ix_usage_records_unbilled", table_name="usage_records")
    op.drop_index("ix_usage_records_recorded_at", table_name="usage_records")
    op.drop_index("ix_usage_records_billed", table_name="usage_records")
    op.drop_index("ix_usage_records_invoice_id", table_name="usage_records")
    op.drop_index("ix_usage_records_usage_type", table_name="usage_records")
    op.drop_index("ix_usage_records_ticket_id", table_name="usage_records")
    op.drop_index("ix_usage_records_billing_account_id", table_name="usage_records")
    op.drop_table("usage_records")

    # Drop payments table
    op.drop_index("ix_payments_status_created", table_name="payments")
    op.drop_index("ix_payments_created_at", table_name="payments")
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_index("ix_payments_stripe_payment_intent_id", table_name="payments")
    op.drop_index("ix_payments_invoice_id", table_name="payments")
    op.drop_index("ix_payments_billing_account_id", table_name="payments")
    op.drop_table("payments")

    # Drop invoices table
    op.drop_index("ix_invoices_status_due", table_name="invoices")
    op.drop_index("ix_invoices_created_at", table_name="invoices")
    op.drop_index("ix_invoices_due_date", table_name="invoices")
    op.drop_index("ix_invoices_total", table_name="invoices")
    op.drop_index("ix_invoices_status", table_name="invoices")
    op.drop_index("ix_invoices_stripe_invoice_id", table_name="invoices")
    op.drop_index("ix_invoices_ticket_id", table_name="invoices")
    op.drop_index("ix_invoices_billing_account_id", table_name="invoices")
    op.drop_index("ix_invoices_invoice_number", table_name="invoices")
    op.drop_table("invoices")

    # Drop billing_accounts table
    op.drop_index("ix_billing_accounts_created_at", table_name="billing_accounts")
    op.drop_index("ix_billing_accounts_stripe_customer_id", table_name="billing_accounts")
    op.drop_index("ix_billing_accounts_organization_id", table_name="billing_accounts")
    op.drop_table("billing_accounts")
