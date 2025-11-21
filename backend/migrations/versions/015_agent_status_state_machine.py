"""Agent Status State Machine (REQ-ALM-004)

Revision ID: 015_agent_status_state_machine
Revises: 014_dynamic_task_scoring
Create Date: 2025-01-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "015_agent_status_state_machine"
down_revision: Union[str, None] = "014_dynamic_task_scoring"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create agent_status_transitions table (REQ-ALM-004)
    op.create_table(
        "agent_status_transitions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "agent_id",
            sa.String(),
            nullable=False,
            comment="Foreign key to agents.id",
        ),
        sa.Column("from_status", sa.String(length=50), nullable=False),
        sa.Column("to_status", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "triggered_by",
            sa.String(length=255),
            nullable=True,
            comment="Agent ID or user ID that initiated transition",
        ),
        sa.Column(
            "task_id",
            sa.String(),
            nullable=True,
            comment="Optional task ID associated with transition",
        ),
        sa.Column(
            "transitioned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Additional context (error details, metrics, etc.)",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_status_transitions_agent_id"),
        "agent_status_transitions",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_status_transitions_to_status"),
        "agent_status_transitions",
        ["to_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_status_transitions_task_id"),
        "agent_status_transitions",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_status_transitions_transitioned_at"),
        "agent_status_transitions",
        ["transitioned_at"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_agent_status_transitions_agent_id_agents"),
        "agent_status_transitions",
        "agents",
        ["agent_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_agent_status_transitions_task_id_tasks"),
        "agent_status_transitions",
        "tasks",
        ["task_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Update existing agent status values to uppercase and map legacy values
    # REQ-ALM-004: statuses should be uppercase (SPAWNING, IDLE, RUNNING, etc.)
    # Map legacy lowercase values and special cases:
    # - "idle" -> "IDLE"
    # - "running" -> "RUNNING"
    # - "degraded" -> "DEGRADED"
    # - "failed" -> "FAILED"
    # - "terminated" -> "TERMINATED"
    # - "stale" -> "IDLE" (stale agents should become idle)
    # - "unresponsive" -> "DEGRADED" (unresponsive agents should be degraded)
    # - "maintenance" -> "IDLE" (maintenance mode should be idle)
    # - "quarantined" -> "QUARANTINED" (if exists)
    # - "spawning" -> "SPAWNING" (if exists)
    op.execute(
        """
        UPDATE agents
        SET status = CASE
            WHEN LOWER(status) = 'idle' THEN 'IDLE'
            WHEN LOWER(status) = 'running' THEN 'RUNNING'
            WHEN LOWER(status) = 'degraded' THEN 'DEGRADED'
            WHEN LOWER(status) = 'failed' THEN 'FAILED'
            WHEN LOWER(status) = 'terminated' THEN 'TERMINATED'
            WHEN LOWER(status) = 'quarantined' THEN 'QUARANTINED'
            WHEN LOWER(status) = 'spawning' THEN 'SPAWNING'
            WHEN LOWER(status) = 'stale' THEN 'IDLE'
            WHEN LOWER(status) = 'unresponsive' THEN 'DEGRADED'
            WHEN LOWER(status) = 'maintenance' THEN 'IDLE'
            ELSE UPPER(status)
        END
        WHERE status != UPPER(status)
           OR LOWER(status) IN ('stale', 'unresponsive', 'maintenance')
        """
    )

    # Add updated_at column to agents table if it doesn't exist
    # Check if column exists first (for backwards compatibility)
    inspector = sa.inspect(op.get_bind())
    columns = [col["name"] for col in inspector.get_columns("agents")]
    if "updated_at" not in columns:
        op.add_column(
            "agents",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
                comment="Last update timestamp for agent (REQ-ALM-004)",
            ),
        )

    # Add constraint to enforce valid status values (REQ-ALM-004)
    op.create_check_constraint(
        op.f("ck_agents_valid_status"),
        "agents",
        sa.text(
            "status IN ('SPAWNING', 'IDLE', 'RUNNING', 'DEGRADED', 'FAILED', 'QUARANTINED', 'TERMINATED')"
        ),
    )


def downgrade() -> None:
    # Remove check constraint
    op.drop_constraint(op.f("ck_agents_valid_status"), "agents", type_="check")

    # Revert status values to lowercase (best effort)
    op.execute(
        """
        UPDATE agents
        SET status = LOWER(status)
        """
    )

    # Drop foreign keys
    op.drop_constraint(
        op.f("fk_agent_status_transitions_task_id_tasks"),
        "agent_status_transitions",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_agent_status_transitions_agent_id_agents"),
        "agent_status_transitions",
        type_="foreignkey",
    )

    # Drop indexes
    op.drop_index(
        op.f("ix_agent_status_transitions_transitioned_at"),
        table_name="agent_status_transitions",
    )
    op.drop_index(
        op.f("ix_agent_status_transitions_task_id"),
        table_name="agent_status_transitions",
    )
    op.drop_index(
        op.f("ix_agent_status_transitions_to_status"),
        table_name="agent_status_transitions",
    )
    op.drop_index(
        op.f("ix_agent_status_transitions_agent_id"),
        table_name="agent_status_transitions",
    )

    # Drop table
    op.drop_table("agent_status_transitions")
