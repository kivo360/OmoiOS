"""Add dependencies column to tickets table for cross-ticket dependencies

Revision ID: 045_add_dependencies_to_tickets
Revises: 044_add_execution_config_to_tasks
Create Date: 2025-01-08

This migration adds the dependencies JSONB column to the tickets table.
This column stores ticket-to-ticket dependencies for spec-driven workflows.

Example value:
{
    "blocked_by": ["TKT-001", "TKT-002"],
    "blocks": ["TKT-003"]
}
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "045_add_dependencies_to_tickets"
down_revision: Union[str, None] = "044_add_execution_config_to_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add dependencies column to tickets table."""
    op.add_column(
        "tickets",
        sa.Column(
            "dependencies",
            JSONB,
            nullable=True,
            comment="Ticket dependencies: blocked_by and blocks other tickets",
        ),
    )


def downgrade() -> None:
    """Remove dependencies column from tickets table."""
    op.drop_column("tickets", "dependencies")
