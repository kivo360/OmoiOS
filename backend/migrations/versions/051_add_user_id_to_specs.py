"""add_user_id_to_specs

Revision ID: 051_add_user_id_to_specs
Revises: 050_add_promo_codes
Create Date: 2025-01-14

Adds user_id field to specs table to track spec ownership.
This enables proper authentication and authorization for spec-driven development.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "051_add_user_id_to_specs"
down_revision: Union[str, Sequence[str], None] = "050_add_promo_codes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_id column to specs table."""
    # Add user_id column (nullable for existing specs without owner)
    op.add_column(
        "specs",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="User who created the spec",
        ),
    )

    # Create foreign key to users table
    op.create_foreign_key(
        "fk_specs_user_id",
        "specs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Create index for user_id lookups
    op.create_index(
        "ix_specs_user_id",
        "specs",
        ["user_id"],
    )


def downgrade() -> None:
    """Remove user_id column from specs table."""
    # Drop index first
    op.drop_index("ix_specs_user_id", table_name="specs")

    # Drop foreign key
    op.drop_constraint("fk_specs_user_id", "specs", type_="foreignkey")

    # Drop column
    op.drop_column("specs", "user_id")
