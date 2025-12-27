"""Add waitlist_status to users table

Revision ID: 042_add_waitlist_status
Revises: 041_cost_record_billing_integration
Create Date: 2025-12-27

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "042_add_waitlist_status"
down_revision: Union[str, None] = "041_cost_record_billing_integration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add waitlist_status column to users table."""
    # Add waitlist_status column
    # Values: 'pending' (on waitlist), 'approved' (can access app), 'none' (not on waitlist/legacy)
    op.add_column(
        "users",
        sa.Column(
            "waitlist_status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
    )

    # Add index for querying waitlist users
    op.create_index(
        "idx_users_waitlist_status",
        "users",
        ["waitlist_status"],
    )

    # Add waitlist signup metadata (referral source, etc.)
    op.add_column(
        "users",
        sa.Column(
            "waitlist_metadata",
            sa.JSON(),
            nullable=True,
        ),
    )

    # Set existing users to 'approved' so they're not blocked
    op.execute("UPDATE users SET waitlist_status = 'approved' WHERE waitlist_status = 'pending'")


def downgrade() -> None:
    """Remove waitlist_status column from users table."""
    op.drop_index("idx_users_waitlist_status", table_name="users")
    op.drop_column("users", "waitlist_metadata")
    op.drop_column("users", "waitlist_status")
