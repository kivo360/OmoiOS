"""Create sandbox_resource_allocations table for tracking resource allocations per sandbox.

Revision ID: 037_create_sandbox_resource_allocations
Revises: 036_task_sandbox_id
Create Date: 2026-01-23

Part of TKT-001: Database Models & Migrations for Resource Tracking.

This table stores the current and pending resource configuration for each sandbox,
supporting optimistic locking for concurrent modification detection (REQ-SRAD-REL-003).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "037_create_sandbox_resource_allocations"
down_revision: Union[str, None] = "036_task_sandbox_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sandbox_resource_allocations table."""
    op.create_table(
        "sandbox_resource_allocations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("sandbox_id", sa.String(length=255), nullable=False),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("agent_id", sa.String(), nullable=True),
        # Current resource allocation
        sa.Column("cpu_cores", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("memory_gb", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("disk_gb", sa.Float(), nullable=False, server_default="10.0"),
        # Pending resource changes
        sa.Column("pending_cpu_cores", sa.Float(), nullable=True),
        sa.Column("pending_memory_gb", sa.Float(), nullable=True),
        sa.Column("pending_disk_gb", sa.Float(), nullable=True),
        # Optimistic locking
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        # Status tracking
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        # Audit fields
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
    )

    # Create indexes for efficient querying
    op.create_index(
        "ix_sandbox_resource_allocations_sandbox_id",
        "sandbox_resource_allocations",
        ["sandbox_id"],
        unique=True,
    )
    op.create_index(
        "ix_sandbox_resource_allocations_task_id",
        "sandbox_resource_allocations",
        ["task_id"],
    )
    op.create_index(
        "ix_sandbox_resource_allocations_agent_id",
        "sandbox_resource_allocations",
        ["agent_id"],
    )
    op.create_index(
        "ix_sandbox_resource_allocations_status",
        "sandbox_resource_allocations",
        ["status"],
    )
    op.create_index(
        "ix_sandbox_resource_allocations_created_at",
        "sandbox_resource_allocations",
        ["created_at"],
    )


def downgrade() -> None:
    """Remove sandbox_resource_allocations table."""
    op.drop_index(
        "ix_sandbox_resource_allocations_created_at",
        table_name="sandbox_resource_allocations",
    )
    op.drop_index(
        "ix_sandbox_resource_allocations_status",
        table_name="sandbox_resource_allocations",
    )
    op.drop_index(
        "ix_sandbox_resource_allocations_agent_id",
        table_name="sandbox_resource_allocations",
    )
    op.drop_index(
        "ix_sandbox_resource_allocations_task_id",
        table_name="sandbox_resource_allocations",
    )
    op.drop_index(
        "ix_sandbox_resource_allocations_sandbox_id",
        table_name="sandbox_resource_allocations",
    )
    op.drop_table("sandbox_resource_allocations")
