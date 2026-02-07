"""Add agent_logs table for intelligent monitoring.

Revision ID: 026_add_agent_logs_table
Revises: 025_supabase_auth_integration
Create Date: 2025-11-19

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "026_add_agent_logs_table"
down_revision: Union[str, None] = "025_supabase_auth_integration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create agent_logs table for trajectory analysis and monitoring."""
    op.create_table(
        "agent_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("log_type", sa.String(length=50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
    )

    # Create indexes
    op.create_index("ix_agent_logs_agent_id", "agent_logs", ["agent_id"])
    op.create_index("ix_agent_logs_log_type", "agent_logs", ["log_type"])
    op.create_index("ix_agent_logs_created_at", "agent_logs", ["created_at"])


def downgrade() -> None:
    """Remove agent_logs table."""
    op.drop_index("ix_agent_logs_created_at", table_name="agent_logs")
    op.drop_index("ix_agent_logs_log_type", table_name="agent_logs")
    op.drop_index("ix_agent_logs_agent_id", table_name="agent_logs")
    op.drop_table("agent_logs")
