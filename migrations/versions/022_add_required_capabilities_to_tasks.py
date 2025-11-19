"""Add Required Capabilities to Tasks (REQ-TQM-ASSIGN-001)

Revision ID: 022_add_required_capabilities_to_tasks
Revises: 021_watchdog_service
Create Date: 2025-01-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "022_add_required_capabilities_to_tasks"
down_revision: Union[str, None] = "021_watchdog_service"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add required_capabilities field to tasks table (REQ-TQM-ASSIGN-001)
    op.add_column(
        "tasks",
        sa.Column(
            "required_capabilities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Required capabilities: ['python', 'fastapi', 'postgres'] (REQ-TQM-ASSIGN-001)",
        ),
    )
    
    # Create GIN index for efficient capability matching queries
    op.create_index(
        "ix_tasks_required_capabilities",
        "tasks",
        ["required_capabilities"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    # Drop index
    op.drop_index("ix_tasks_required_capabilities", table_name="tasks")
    
    # Drop column
    op.drop_column("tasks", "required_capabilities")

