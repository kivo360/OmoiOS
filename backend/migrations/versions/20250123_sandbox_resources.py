"""create_sandbox_resources_table

Revision ID: a1b2c3d4e5f6
Revises: 8ecd4525d261
Create Date: 2025-01-23 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "8ecd4525d261"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sandbox_resources table for tracking resource allocation and usage."""
    op.create_table(
        "sandbox_resources",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("sandbox_id", sa.String(100), nullable=False),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("agent_id", sa.String(), nullable=True),
        # Allocation limits
        sa.Column(
            "cpu_allocated",
            sa.Float(),
            nullable=False,
            server_default="2.0",
            comment="CPU cores allocated",
        ),
        sa.Column(
            "memory_allocated_mb",
            sa.Integer(),
            nullable=False,
            server_default="4096",
            comment="Memory allocated in MB",
        ),
        sa.Column(
            "disk_allocated_gb",
            sa.Integer(),
            nullable=False,
            server_default="8",
            comment="Disk space allocated in GB",
        ),
        # Current usage metrics
        sa.Column(
            "cpu_usage_percent",
            sa.Float(),
            nullable=False,
            server_default="0.0",
            comment="Current CPU usage percentage (0-100)",
        ),
        sa.Column(
            "memory_usage_mb",
            sa.Float(),
            nullable=False,
            server_default="0.0",
            comment="Current memory usage in MB",
        ),
        sa.Column(
            "disk_usage_gb",
            sa.Float(),
            nullable=False,
            server_default="0.0",
            comment="Current disk usage in GB",
        ),
        # Status
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="active",
            comment="Resource status: active, paused, terminated",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Tracks resource allocation and usage for sandbox workers",
    )
    # Create indexes
    op.create_index(
        "ix_sandbox_resources_sandbox_id",
        "sandbox_resources",
        ["sandbox_id"],
        unique=True,
    )
    op.create_index(
        "ix_sandbox_resources_task_id", "sandbox_resources", ["task_id"]
    )
    op.create_index(
        "ix_sandbox_resources_agent_id", "sandbox_resources", ["agent_id"]
    )
    op.create_index(
        "ix_sandbox_resources_status", "sandbox_resources", ["status"]
    )


def downgrade() -> None:
    """Drop sandbox_resources table."""
    op.drop_index("ix_sandbox_resources_status", table_name="sandbox_resources")
    op.drop_index("ix_sandbox_resources_agent_id", table_name="sandbox_resources")
    op.drop_index("ix_sandbox_resources_task_id", table_name="sandbox_resources")
    op.drop_index("ix_sandbox_resources_sandbox_id", table_name="sandbox_resources")
    op.drop_table("sandbox_resources")
