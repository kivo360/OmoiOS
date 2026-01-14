"""add_spec_id_to_sandbox_events

Revision ID: 052_add_spec_id_to_sandbox_events
Revises: 051_add_user_id_to_specs
Create Date: 2025-01-14

Adds spec_id field to sandbox_events table to enable filtering
events by spec for spec-driven development UI.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "052_add_spec_id_to_sandbox_events"
down_revision: Union[str, Sequence[str], None] = "051_add_user_id_to_specs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add spec_id column to sandbox_events table."""
    # Add spec_id column (nullable for existing events without spec)
    op.add_column(
        "sandbox_events",
        sa.Column(
            "spec_id",
            sa.String(),
            nullable=True,
            comment="Spec this event is associated with (for spec-driven development)",
        ),
    )

    # Create foreign key to specs table
    op.create_foreign_key(
        "fk_sandbox_events_spec_id",
        "sandbox_events",
        "specs",
        ["spec_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Create index for spec_id lookups
    op.create_index(
        "ix_sandbox_events_spec_id",
        "sandbox_events",
        ["spec_id"],
    )


def downgrade() -> None:
    """Remove spec_id column from sandbox_events table."""
    # Drop index first
    op.drop_index("ix_sandbox_events_spec_id", table_name="sandbox_events")

    # Drop foreign key
    op.drop_constraint("fk_sandbox_events_spec_id", "sandbox_events", type_="foreignkey")

    # Drop column
    op.drop_column("sandbox_events", "spec_id")
