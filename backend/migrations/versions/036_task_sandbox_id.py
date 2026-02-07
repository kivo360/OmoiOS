"""Add sandbox_id field to tasks table.

Phase 6: Guardian Integration - enables routing interventions
to sandbox agents via message injection API instead of direct
OpenHands conversation access.

Revision ID: 036_task_sandbox_id
Revises: 035_sandbox_events_table
Create Date: 2025-12-13
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "036_task_sandbox_id"
down_revision = "035_sandbox_events_table"
branch_labels = None
depends_on = None


def upgrade():
    """Add sandbox_id column to tasks table."""
    op.add_column(
        "tasks",
        sa.Column(
            "sandbox_id",
            sa.String(255),
            nullable=True,
            comment="Daytona sandbox ID for remote agent execution (Phase 6: Guardian routing)",
        ),
    )
    # Add index for efficient lookup
    op.create_index(
        "ix_tasks_sandbox_id",
        "tasks",
        ["sandbox_id"],
        unique=False,
    )


def downgrade():
    """Remove sandbox_id column from tasks table."""
    op.drop_index("ix_tasks_sandbox_id", table_name="tasks")
    op.drop_column("tasks", "sandbox_id")
