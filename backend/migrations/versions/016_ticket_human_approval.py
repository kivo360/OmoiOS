"""Ticket Human Approval (REQ-THA-001, REQ-THA-005)

Revision ID: 016_ticket_human_approval
Revises: 015_agent_status_state_machine
Create Date: 2025-01-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "016_ticket_human_approval"
down_revision: Union[str, None] = "015_agent_status_state_machine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add approval_status column to tickets table (REQ-THA-001, REQ-THA-005)
    op.add_column(
        "tickets",
        sa.Column(
            "approval_status",
            sa.String(50),
            nullable=False,
            server_default="approved",
            comment="Approval status: pending_review, approved, rejected, timed_out (REQ-THA-001)",
        ),
    )
    op.create_index(
        op.f("ix_tickets_approval_status"), "tickets", ["approval_status"], unique=False
    )

    # Add approval_deadline_at column to tickets table (REQ-THA-005)
    op.add_column(
        "tickets",
        sa.Column(
            "approval_deadline_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Deadline for approval timeout (REQ-THA-005)",
        ),
    )
    op.create_index(
        op.f("ix_tickets_approval_deadline_at"),
        "tickets",
        ["approval_deadline_at"],
        unique=False,
    )

    # Add requested_by_agent_id column to tickets table (REQ-THA-005)
    op.add_column(
        "tickets",
        sa.Column(
            "requested_by_agent_id",
            sa.String(),
            nullable=True,
            index=True,
            comment="Agent ID that requested this ticket (REQ-THA-005)",
        ),
    )

    # Add rejection_reason column to tickets table (REQ-THA-005)
    op.add_column(
        "tickets",
        sa.Column(
            "rejection_reason",
            sa.Text(),
            nullable=True,
            comment="Reason for rejection if ticket was rejected (REQ-THA-005)",
        ),
    )


def downgrade() -> None:
    # Remove rejection_reason column
    op.drop_column("tickets", "rejection_reason")

    # Remove requested_by_agent_id column
    op.drop_index(op.f("ix_tickets_requested_by_agent_id"), table_name="tickets")
    op.drop_column("tickets", "requested_by_agent_id")

    # Remove approval_deadline_at column
    op.drop_index(op.f("ix_tickets_approval_deadline_at"), table_name="tickets")
    op.drop_column("tickets", "approval_deadline_at")

    # Remove approval_status column
    op.drop_index(op.f("ix_tickets_approval_status"), table_name="tickets")
    op.drop_column("tickets", "approval_status")
