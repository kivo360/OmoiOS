"""add_promo_codes

Revision ID: 050_add_promo_codes
Revises: 049_add_spec_deduplication_vectors
Create Date: 2025-01-11

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "050_add_promo_codes"
down_revision: Union[str, Sequence[str], None] = "049_add_spec_deduplication_vectors"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create promo_codes and promo_code_redemptions tables."""

    # Create promo_codes table
    op.create_table(
        "promo_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column(
            "discount_type", sa.String(50), nullable=False, server_default="percentage"
        ),
        sa.Column("discount_value", sa.Integer, nullable=False, server_default="0"),
        sa.Column("trial_days", sa.Integer, nullable=True),
        sa.Column("max_uses", sa.Integer, nullable=True),
        sa.Column("current_uses", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "applicable_tiers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("grant_tier", sa.String(50), nullable=True),
        sa.Column("grant_duration_months", sa.Integer, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "promo_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        comment="Promotional codes for discounts and payment bypass",
    )

    # Create indexes for promo_codes
    op.create_index("idx_promo_code_code", "promo_codes", ["code"])
    op.create_index("idx_promo_code_created_at", "promo_codes", ["created_at"])
    op.create_index(
        "idx_promo_code_active_valid",
        "promo_codes",
        ["is_active", "valid_until"],
    )

    # Create promo_code_redemptions table
    op.create_table(
        "promo_code_redemptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "promo_code_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("promo_codes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "subscription_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subscriptions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("discount_type_applied", sa.String(50), nullable=False),
        sa.Column("discount_value_applied", sa.Integer, nullable=False),
        sa.Column("tier_granted", sa.String(50), nullable=True),
        sa.Column("duration_months_granted", sa.Integer, nullable=True),
        sa.Column(
            "redeemed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        comment="Records of promo code redemptions",
    )

    # Create indexes for promo_code_redemptions
    op.create_index(
        "idx_redemption_promo_code_id",
        "promo_code_redemptions",
        ["promo_code_id"],
    )
    op.create_index(
        "idx_redemption_user_id",
        "promo_code_redemptions",
        ["user_id"],
    )
    op.create_index(
        "idx_redemption_org_id",
        "promo_code_redemptions",
        ["organization_id"],
    )
    op.create_index(
        "idx_redemption_subscription_id",
        "promo_code_redemptions",
        ["subscription_id"],
    )
    op.create_index(
        "idx_redemption_redeemed_at",
        "promo_code_redemptions",
        ["redeemed_at"],
    )
    op.create_index(
        "idx_redemption_user_code",
        "promo_code_redemptions",
        ["user_id", "promo_code_id"],
    )


def downgrade() -> None:
    """Drop promo_codes and promo_code_redemptions tables."""
    # Drop redemptions table first (has foreign key to promo_codes)
    op.drop_index("idx_redemption_user_code", table_name="promo_code_redemptions")
    op.drop_index("idx_redemption_redeemed_at", table_name="promo_code_redemptions")
    op.drop_index("idx_redemption_subscription_id", table_name="promo_code_redemptions")
    op.drop_index("idx_redemption_org_id", table_name="promo_code_redemptions")
    op.drop_index("idx_redemption_user_id", table_name="promo_code_redemptions")
    op.drop_index("idx_redemption_promo_code_id", table_name="promo_code_redemptions")
    op.drop_table("promo_code_redemptions")

    # Drop promo_codes table
    op.drop_index("idx_promo_code_active_valid", table_name="promo_codes")
    op.drop_index("idx_promo_code_created_at", table_name="promo_codes")
    op.drop_index("idx_promo_code_code", table_name="promo_codes")
    op.drop_table("promo_codes")
