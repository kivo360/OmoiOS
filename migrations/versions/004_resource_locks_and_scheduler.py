"""Resource locks and scheduler support for parallel execution.

Revision ID: 004_resource_locks
Revises: 003_phase_workflow
Create Date: 2025-11-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "004_resource_locks"
down_revision: Union[str, None] = "003_phase_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create resource_locks table for preventing conflicting task execution."""
    op.create_table(
        "resource_locks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("resource_key", sa.String(length=255), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("lock_type", sa.String(length=50), nullable=False, server_default="exclusive"),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resource_locks_resource_key", "resource_locks", ["resource_key"], unique=True)
    op.create_index("ix_resource_locks_task_id", "resource_locks", ["task_id"])
    op.create_index("ix_resource_locks_agent_id", "resource_locks", ["agent_id"])


def downgrade() -> None:
    """Drop resource_locks table."""
    op.drop_index("ix_resource_locks_agent_id", table_name="resource_locks")
    op.drop_index("ix_resource_locks_task_id", table_name="resource_locks")
    op.drop_index("ix_resource_locks_resource_key", table_name="resource_locks")
    op.drop_table("resource_locks")
