"""Subscriptions table for tier-based billing

Revision ID: 040_subscriptions_table
Revises: 039_add_tasks_embedding_vector
Create Date: 2025-12-24

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "040_subscriptions_table"
down_revision: Union[str, None] = "039_add_tasks_embedding_vector"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Subscriptions table - manages tier-based access with usage limits
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        # Organization link
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Billing account link
        sa.Column("billing_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Stripe integration
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_price_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_product_id", sa.String(length=255), nullable=True),
        # Subscription details
        sa.Column("tier", sa.String(length=50), nullable=False, server_default="free"),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="active"
        ),
        # Billing cycle
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "cancel_at_period_end", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        # Trial tracking
        sa.Column("trial_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        # Usage limits for current period
        sa.Column("workflows_limit", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("workflows_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("agents_limit", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("storage_limit_gb", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("storage_used_gb", sa.Float(), nullable=False, server_default="0.0"),
        # Lifetime-specific fields
        sa.Column("is_lifetime", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("lifetime_purchase_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lifetime_purchase_amount", sa.Float(), nullable=True),
        # BYO-specific fields
        sa.Column("is_byo", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "byo_providers_configured",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),  # ["anthropic", "openai", etc.]
        # Additional configuration
        sa.Column(
            "subscription_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),  # Custom limits, features, etc.
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
        # Foreign keys
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["billing_account_id"],
            ["billing_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_subscription_id"),
        comment="Subscriptions with tier-based limits and Stripe integration",
    )

    # Indexes for common queries
    op.create_index(
        "ix_subscriptions_organization_id", "subscriptions", ["organization_id"]
    )
    op.create_index(
        "ix_subscriptions_billing_account_id", "subscriptions", ["billing_account_id"]
    )
    op.create_index(
        "ix_subscriptions_stripe_subscription_id",
        "subscriptions",
        ["stripe_subscription_id"],
    )
    op.create_index("ix_subscriptions_tier", "subscriptions", ["tier"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    op.create_index("ix_subscriptions_created_at", "subscriptions", ["created_at"])
    op.create_index(
        "ix_subscriptions_current_period_end", "subscriptions", ["current_period_end"]
    )
    # Composite indexes for common queries
    op.create_index(
        "idx_subscription_org_status", "subscriptions", ["organization_id", "status"]
    )
    op.create_index(
        "idx_subscription_period_end", "subscriptions", ["current_period_end", "status"]
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_subscription_period_end", table_name="subscriptions")
    op.drop_index("idx_subscription_org_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_current_period_end", table_name="subscriptions")
    op.drop_index("ix_subscriptions_created_at", table_name="subscriptions")
    op.drop_index("ix_subscriptions_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_tier", table_name="subscriptions")
    op.drop_index("ix_subscriptions_stripe_subscription_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_billing_account_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_organization_id", table_name="subscriptions")

    # Drop table
    op.drop_table("subscriptions")
