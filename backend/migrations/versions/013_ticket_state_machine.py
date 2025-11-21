"""Ticket State Machine (REQ-TKT-SM-001, REQ-TKT-BL-001, REQ-TKT-BL-002)

Revision ID: 013_ticket_state_machine
Revises: 012_anomaly_detection
Create Date: 2025-01-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "013_ticket_state_machine"
down_revision: Union[str, None] = "012_anomaly_detection"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add blocking overlay fields to tickets table (REQ-TKT-SM-001, REQ-TKT-BL-001, REQ-TKT-BL-002)
    op.add_column(
        "tickets",
        sa.Column(
            "is_blocked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Blocked overlay flag (used alongside current status)",
        ),
    )
    op.create_index(
        op.f("ix_tickets_is_blocked"), "tickets", ["is_blocked"], unique=False
    )
    op.add_column(
        "tickets",
        sa.Column(
            "blocked_reason",
            sa.String(length=100),
            nullable=True,
            comment="Blocker classification: dependency, waiting_on_clarification, failing_checks, environment",
        ),
    )
    op.add_column(
        "tickets",
        sa.Column(
            "blocked_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when ticket was marked as blocked",
        ),
    )

    # Update existing tickets to use new status values
    # Map old status values to new Kanban states
    # pending -> backlog
    # in_progress -> building
    # completed -> done
    # failed -> blocked (if appropriate) or leave as-is
    op.execute(
        """
        UPDATE tickets
        SET status = CASE
            WHEN status = 'pending' THEN 'backlog'
            WHEN status = 'in_progress' THEN 'building'
            WHEN status = 'completed' THEN 'done'
            WHEN status = 'failed' THEN 'building'
            ELSE status
        END
        """
    )


def downgrade() -> None:
    # Remove blocking overlay fields
    op.drop_column("tickets", "blocked_at")
    op.drop_column("tickets", "blocked_reason")
    op.drop_index(op.f("ix_tickets_is_blocked"), table_name="tickets")
    op.drop_column("tickets", "is_blocked")

    # Revert status values to old format
    op.execute(
        """
        UPDATE tickets
        SET status = CASE
            WHEN status = 'backlog' THEN 'pending'
            WHEN status = 'analyzing' THEN 'in_progress'
            WHEN status = 'building' THEN 'in_progress'
            WHEN status = 'building-done' THEN 'in_progress'
            WHEN status = 'testing' THEN 'in_progress'
            WHEN status = 'done' THEN 'completed'
            ELSE status
        END
        """
    )

