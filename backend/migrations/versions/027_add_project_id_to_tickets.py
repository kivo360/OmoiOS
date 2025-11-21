"""Add project_id to tickets table for Project relationship.

Revision ID: 027_add_project_id_to_tickets
Revises: 026_add_agent_logs_table
Create Date: 2025-11-19

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Import migration utilities
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from migration_utils import safe_add_column, safe_create_index, safe_create_foreign_key

# revision identifiers, used by Alembic.
revision: str = "027_add_project_id_to_tickets"
down_revision: Union[str, None] = "026_add_agent_logs_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add project_id column to tickets table."""
    safe_add_column(
        "tickets",
        sa.Column(
            "project_id",
            sa.String(),
            nullable=True,
            comment="Foreign key to projects table",
        ),
    )
    safe_create_index("ix_tickets_project_id", "tickets", ["project_id"])
    safe_create_foreign_key(
        "fk_tickets_project_id",
        "tickets",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove project_id column from tickets table."""
    op.drop_constraint("fk_tickets_project_id", "tickets", type_="foreignkey")
    op.drop_index("ix_tickets_project_id", table_name="tickets")
    op.drop_column("tickets", "project_id")
