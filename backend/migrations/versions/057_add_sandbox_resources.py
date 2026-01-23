"""add_sandbox_resources

Revision ID: 057_add_sandbox_resources
Revises: 8ecd4525d261
Create Date: 2025-01-23

Adds sandbox_resources and sandbox_resource_metrics tables for tracking
CPU/memory/disk allocation and usage per sandbox worker.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "057_add_sandbox_resources"
down_revision: Union[str, Sequence[str], None] = "8ecd4525d261"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sandbox_resources and sandbox_resource_metrics tables."""
    # Create sandbox_resources table for current resource state
    op.create_table(
        "sandbox_resources",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("sandbox_id", sa.String(100), nullable=False),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("agent_id", sa.String(), nullable=True),
        # Allocation settings
        sa.Column("allocated_cpu_cores", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("allocated_memory_gb", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("allocated_disk_gb", sa.Integer(), nullable=False, server_default="8"),
        # Current usage metrics
        sa.Column("cpu_usage_percent", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("memory_usage_percent", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("memory_used_mb", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("disk_usage_percent", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("disk_used_gb", sa.Float(), nullable=False, server_default="0.0"),
        # Status and timestamps
        sa.Column("status", sa.String(50), nullable=False, server_default="creating"),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
            ondelete="SET NULL",
        ),
    )

    # Create indexes for sandbox_resources
    op.create_index(
        "ix_sandbox_resources_sandbox_id",
        "sandbox_resources",
        ["sandbox_id"],
        unique=True,
    )
    op.create_index(
        "ix_sandbox_resources_task_id",
        "sandbox_resources",
        ["task_id"],
    )
    op.create_index(
        "ix_sandbox_resources_agent_id",
        "sandbox_resources",
        ["agent_id"],
    )
    op.create_index(
        "ix_sandbox_resources_status",
        "sandbox_resources",
        ["status"],
    )

    # Create sandbox_resource_metrics table for time-series data
    op.create_table(
        "sandbox_resource_metrics",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("sandbox_id", sa.String(100), nullable=False),
        sa.Column("cpu_usage_percent", sa.Float(), nullable=False),
        sa.Column("memory_usage_percent", sa.Float(), nullable=False),
        sa.Column("memory_used_mb", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("disk_usage_percent", sa.Float(), nullable=False),
        sa.Column("disk_used_gb", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for sandbox_resource_metrics
    op.create_index(
        "ix_sandbox_resource_metrics_sandbox_id",
        "sandbox_resource_metrics",
        ["sandbox_id"],
    )
    op.create_index(
        "ix_sandbox_resource_metrics_recorded_at",
        "sandbox_resource_metrics",
        ["recorded_at"],
    )
    # Composite index for efficient time-series queries
    op.create_index(
        "ix_sandbox_resource_metrics_sandbox_time",
        "sandbox_resource_metrics",
        ["sandbox_id", "recorded_at"],
    )


def downgrade() -> None:
    """Drop sandbox_resources and sandbox_resource_metrics tables."""
    # Drop sandbox_resource_metrics indexes and table
    op.drop_index("ix_sandbox_resource_metrics_sandbox_time", table_name="sandbox_resource_metrics")
    op.drop_index("ix_sandbox_resource_metrics_recorded_at", table_name="sandbox_resource_metrics")
    op.drop_index("ix_sandbox_resource_metrics_sandbox_id", table_name="sandbox_resource_metrics")
    op.drop_table("sandbox_resource_metrics")

    # Drop sandbox_resources indexes and table
    op.drop_index("ix_sandbox_resources_status", table_name="sandbox_resources")
    op.drop_index("ix_sandbox_resources_agent_id", table_name="sandbox_resources")
    op.drop_index("ix_sandbox_resources_task_id", table_name="sandbox_resources")
    op.drop_index("ix_sandbox_resources_sandbox_id", table_name="sandbox_resources")
    op.drop_table("sandbox_resources")
