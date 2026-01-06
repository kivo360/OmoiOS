"""Add user_id to tickets table for user ownership filtering

Revision ID: 043_add_user_id_to_tickets
Revises: 042_add_waitlist_status
Create Date: 2025-01-06

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "043_add_user_id_to_tickets"
down_revision: Union[str, None] = "042_add_waitlist_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_id column to tickets table for user ownership filtering."""
    # Add user_id column to tickets (UUID to match users.id type)
    op.add_column(
        "tickets",
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            nullable=True,
            comment="User who created/owns this ticket",
        ),
    )

    # Add foreign key constraint separately
    op.create_foreign_key(
        "fk_tickets_user_id",
        "tickets",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Create index for efficient filtering by user
    op.create_index(
        "ix_tickets_user_id",
        "tickets",
        ["user_id"],
    )


def downgrade() -> None:
    """Remove user_id column from tickets table."""
    op.drop_index("ix_tickets_user_id", table_name="tickets")
    op.drop_constraint("fk_tickets_user_id", "tickets", type_="foreignkey")
    op.drop_column("tickets", "user_id")
