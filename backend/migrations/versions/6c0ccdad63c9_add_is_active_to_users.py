"""add_is_active_to_users

Revision ID: 6c0ccdad63c9
Revises: e501a87d0d23
Create Date: 2025-12-09 21:56:45.634817

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "6c0ccdad63c9"
down_revision: Union[str, Sequence[str], None] = "e501a87d0d23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_active column to users table."""
    # Add is_active column with default value of true
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
    )


def downgrade() -> None:
    """Remove is_active column from users table."""
    op.drop_column("users", "is_active")
