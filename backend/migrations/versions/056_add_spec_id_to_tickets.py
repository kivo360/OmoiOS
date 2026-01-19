"""add_spec_id_to_tickets

Revision ID: 056_add_spec_id_to_tickets
Revises: 055_add_ticket_pull_requests
Create Date: 2025-01-19

Adds spec_id column to tickets table to link tickets with specifications.
This enables spec-driven development where tickets are associated with specs.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "056_add_spec_id_to_tickets"
down_revision: Union[str, Sequence[str], None] = "055_add_ticket_pull_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add spec_id column to tickets table."""
    op.add_column(
        "tickets",
        sa.Column(
            "spec_id",
            sa.String(),
            nullable=True,
            comment="Linked specification for spec-driven development",
        ),
    )
    op.create_foreign_key(
        "fk_tickets_spec_id",
        "tickets",
        "specs",
        ["spec_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_tickets_spec_id",
        "tickets",
        ["spec_id"],
    )


def downgrade() -> None:
    """Remove spec_id column from tickets table."""
    op.drop_index("ix_tickets_spec_id", table_name="tickets")
    op.drop_constraint("fk_tickets_spec_id", "tickets", type_="foreignkey")
    op.drop_column("tickets", "spec_id")
