"""Add persistence_dir to tasks table for OpenHands conversation resumption.

Revision ID: 028_add_persistence_dir_to_tasks
Revises: 027_add_project_id_to_tickets
Create Date: 2025-11-19

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "028_add_persistence_dir_to_tasks"
down_revision: Union[str, None] = "027_add_project_id_to_tickets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add persistence_dir column to tasks table."""
    op.add_column(
        "tasks",
        sa.Column(
            "persistence_dir",
            sa.String(500),
            nullable=True,
            comment="OpenHands conversation persistence directory for resumption and intervention delivery",
        ),
    )


def downgrade() -> None:
    """Remove persistence_dir column from tasks table."""
    op.drop_column("tasks", "persistence_dir")

