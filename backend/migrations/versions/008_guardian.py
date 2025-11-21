"""Guardian intervention system (Phase 5)

Revision ID: 008_guardian
Revises: 007_cost_tracking
Create Date: 2025-11-17

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "008_guardian"
down_revision: Union[str, None] = "007_cost_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Guardian actions audit trail
    op.create_table(
        "guardian_actions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("target_entity", sa.String(length=100), nullable=False),
        sa.Column("authority_level", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("initiated_by", sa.String(), nullable=False),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
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
        "ix_guardian_actions_action_type", "guardian_actions", ["action_type"]
    )
    op.create_index(
        "ix_guardian_actions_target_entity", "guardian_actions", ["target_entity"]
    )
    op.create_index(
        "ix_guardian_actions_initiated_by", "guardian_actions", ["initiated_by"]
    )
    
    # Composite index for audit trail queries (actions by entity)
    op.create_index(
        "ix_guardian_actions_entity_type",
        "guardian_actions",
        ["target_entity", "action_type"],
        unique=False,
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_guardian_actions_entity_type", table_name="guardian_actions")
    op.drop_index("ix_guardian_actions_initiated_by", table_name="guardian_actions")
    op.drop_index("ix_guardian_actions_target_entity", table_name="guardian_actions")
    op.drop_index("ix_guardian_actions_action_type", table_name="guardian_actions")
    
    # Drop table
    op.drop_table("guardian_actions")

