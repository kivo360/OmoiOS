"""Watchdog Service (REQ-WATCHDOG-001)

Revision ID: 021_watchdog_service
Revises: 020_merge_guardian_and_mcp
Create Date: 2025-01-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "021_watchdog_service"
down_revision: Union[str, None] = "020_merge_guardian_and_mcp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Watchdog actions audit trail per REQ-WATCHDOG-001
    # Check if table already exists (for manual table creation scenarios)
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if "watchdog_actions" not in existing_tables:
        op.create_table(
            "watchdog_actions",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("action_type", sa.String(length=50), nullable=False),
            sa.Column("target_agent_id", sa.String(), nullable=False),
            sa.Column("remediation_policy", sa.String(length=100), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("initiated_by", sa.String(), nullable=False),
            sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("success", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("escalated_to_guardian", sa.String(length=10), nullable=False, server_default="false"),
            sa.Column("guardian_action_id", sa.String(), nullable=True),
            sa.Column(
                "audit_log", postgresql.JSONB(astext_type=sa.Text()), nullable=True
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        
        # Indexes for efficient queries
        op.create_index(
            "ix_watchdog_actions_action_type", "watchdog_actions", ["action_type"]
        )
        op.create_index(
            "ix_watchdog_actions_target_agent_id", "watchdog_actions", ["target_agent_id"]
        )
        op.create_index(
            "ix_watchdog_actions_initiated_by", "watchdog_actions", ["initiated_by"]
        )
        op.create_index(
            "ix_watchdog_actions_guardian_action_id", "watchdog_actions", ["guardian_action_id"]
        )
        
        # Composite index for remediation history queries
        op.create_index(
            "ix_watchdog_actions_agent_policy",
            "watchdog_actions",
            ["target_agent_id", "remediation_policy"],
            unique=False,
        )
    else:
        # Table exists, just ensure indexes exist
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("watchdog_actions")]
        
        if "ix_watchdog_actions_action_type" not in existing_indexes:
            op.create_index(
                "ix_watchdog_actions_action_type", "watchdog_actions", ["action_type"]
            )
        if "ix_watchdog_actions_target_agent_id" not in existing_indexes:
            op.create_index(
                "ix_watchdog_actions_target_agent_id", "watchdog_actions", ["target_agent_id"]
            )
        if "ix_watchdog_actions_initiated_by" not in existing_indexes:
            op.create_index(
                "ix_watchdog_actions_initiated_by", "watchdog_actions", ["initiated_by"]
            )
        if "ix_watchdog_actions_guardian_action_id" not in existing_indexes:
            op.create_index(
                "ix_watchdog_actions_guardian_action_id", "watchdog_actions", ["guardian_action_id"]
            )
        if "ix_watchdog_actions_agent_policy" not in existing_indexes:
            op.create_index(
                "ix_watchdog_actions_agent_policy",
                "watchdog_actions",
                ["target_agent_id", "remediation_policy"],
                unique=False,
            )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_watchdog_actions_agent_policy", table_name="watchdog_actions")
    op.drop_index("ix_watchdog_actions_guardian_action_id", table_name="watchdog_actions")
    op.drop_index("ix_watchdog_actions_initiated_by", table_name="watchdog_actions")
    op.drop_index("ix_watchdog_actions_target_agent_id", table_name="watchdog_actions")
    op.drop_index("ix_watchdog_actions_action_type", table_name="watchdog_actions")
    
    # Drop table
    op.drop_table("watchdog_actions")
