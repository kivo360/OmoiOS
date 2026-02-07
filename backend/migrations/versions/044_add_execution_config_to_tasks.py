"""Add execution_config column to tasks table for skill selection

Revision ID: 044_add_execution_config_to_tasks
Revises: 043_add_user_id_to_tickets
Create Date: 2025-01-07

This migration adds the execution_config JSONB column to the tasks table.
This column stores skill selection and other execution-time settings from
the frontend, enabling features like spec-driven-dev skill enforcement.

Example value:
{
    "require_spec_skill": true,
    "selected_skill": "spec-driven-dev"
}
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "044_add_execution_config_to_tasks"
down_revision: Union[str, None] = "043_add_user_id_to_tickets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add execution_config column to tasks table."""
    op.add_column(
        "tasks",
        sa.Column(
            "execution_config",
            JSONB,
            nullable=True,
            comment="Execution config from frontend: skill selection, spawn options",
        ),
    )


def downgrade() -> None:
    """Remove execution_config column from tasks table."""
    op.drop_column("tasks", "execution_config")
