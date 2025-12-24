"""Add sandbox_id and billing_account_id to cost_records

Revision ID: 041_cost_record_billing_integration
Revises: 040_subscriptions_table
Create Date: 2025-12-24

Links cost tracking to sandbox execution and billing for:
- Tracking costs per sandbox (via sandbox_id)
- Aggregating costs per organization (via billing_account_id)
- Supporting subscription usage limits
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "041_cost_record_billing_integration"
down_revision: Union[str, None] = "040_subscriptions_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add sandbox_id column
    op.add_column(
        "cost_records",
        sa.Column("sandbox_id", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_cost_records_sandbox_id", "cost_records", ["sandbox_id"]
    )

    # Add billing_account_id column with foreign key (UUID to match billing_accounts.id)
    op.add_column(
        "cost_records",
        sa.Column("billing_account_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_cost_records_billing_account_id",
        "cost_records",
        "billing_accounts",
        ["billing_account_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_cost_records_billing_account_id", "cost_records", ["billing_account_id"]
    )


def downgrade() -> None:
    # Drop billing_account_id
    op.drop_index("ix_cost_records_billing_account_id", table_name="cost_records")
    op.drop_constraint(
        "fk_cost_records_billing_account_id", "cost_records", type_="foreignkey"
    )
    op.drop_column("cost_records", "billing_account_id")

    # Drop sandbox_id
    op.drop_index("ix_cost_records_sandbox_id", table_name="cost_records")
    op.drop_column("cost_records", "sandbox_id")
