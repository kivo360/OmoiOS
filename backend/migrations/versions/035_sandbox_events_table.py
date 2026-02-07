"""Add sandbox_events table for persisting agent events.

Revision ID: 035_sandbox_events_table
Revises: 034_fix_pgvector_dimensions
Create Date: 2025-12-13

Phase 4: Database Persistence for Sandbox Agents

This table stores events emitted by agents running in sandboxes,
enabling audit trails, debugging, and analytics.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "035_sandbox_events_table"
down_revision: Union[str, None] = "034_fix_pgvector_dimensions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sandbox_events table for event persistence."""
    op.create_table(
        "sandbox_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("sandbox_id", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("event_data", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "source", sa.String(length=50), nullable=False, server_default="agent"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for efficient querying
    op.create_index("ix_sandbox_events_sandbox_id", "sandbox_events", ["sandbox_id"])
    op.create_index("ix_sandbox_events_event_type", "sandbox_events", ["event_type"])
    op.create_index("ix_sandbox_events_source", "sandbox_events", ["source"])
    op.create_index("ix_sandbox_events_created_at", "sandbox_events", ["created_at"])


def downgrade() -> None:
    """Remove sandbox_events table."""
    op.drop_index("ix_sandbox_events_created_at", table_name="sandbox_events")
    op.drop_index("ix_sandbox_events_source", table_name="sandbox_events")
    op.drop_index("ix_sandbox_events_event_type", table_name="sandbox_events")
    op.drop_index("ix_sandbox_events_sandbox_id", table_name="sandbox_events")
    op.drop_table("sandbox_events")
