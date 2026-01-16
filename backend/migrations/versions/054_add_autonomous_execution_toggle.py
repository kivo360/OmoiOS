"""add_autonomous_execution_toggle

Revision ID: 054_add_autonomous_execution_toggle
Revises: 053_add_spec_pr_tracking_fields
Create Date: 2025-01-15

Adds autonomous_execution_enabled toggle to projects table.
When enabled, the orchestrator will automatically spawn tasks
for the project when they become unblocked (all dependencies completed).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "054_add_autonomous_execution_toggle"
down_revision: Union[str, Sequence[str], None] = "053_add_spec_pr_tracking_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add autonomous_execution_enabled column to projects table."""
    op.add_column(
        "projects",
        sa.Column(
            "autonomous_execution_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="When enabled, orchestrator auto-spawns unblocked tasks",
        ),
    )

    # Add index for efficient querying of autonomous projects
    op.create_index(
        "ix_projects_autonomous_execution_enabled",
        "projects",
        ["autonomous_execution_enabled"],
    )


def downgrade() -> None:
    """Remove autonomous_execution_enabled column from projects table."""
    op.drop_index("ix_projects_autonomous_execution_enabled", table_name="projects")
    op.drop_column("projects", "autonomous_execution_enabled")
