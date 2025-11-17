"""Agent collaboration messaging and handoff tables.

Revision ID: 004_agent_collab
Revises: 003_agent_registry, 003_phase_workflow
Create Date: 2025-11-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004_agent_collab"
down_revision: Union[str, Sequence[str], None] = ("003_agent_registry", "003_phase_workflow")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "collaboration_threads",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("context_type", sa.String(length=50), nullable=False),
        sa.Column("context_id", sa.String(), nullable=False),
        sa.Column("created_by_agent_id", sa.String(), nullable=False),
        sa.Column(
            "participants",
            postgresql.ARRAY(sa.String(length=100)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.alter_column("collaboration_threads", "participants", server_default=None)
    op.create_index(
        "ix_collab_threads_context_id", "collaboration_threads", ["context_id"], unique=False
    )
    op.create_index(
        "ix_collab_threads_updated_at", "collaboration_threads", ["updated_at"], unique=False
    )

    op.create_table(
        "collaboration_messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("thread_id", sa.String(), nullable=False),
        sa.Column("sender_agent_id", sa.String(), nullable=False),
        sa.Column("target_agent_id", sa.String(), nullable=True),
        sa.Column("message_type", sa.String(length=50), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["thread_id"], ["collaboration_threads.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_collab_messages_thread", "collaboration_messages", ["thread_id"], unique=False
    )
    op.create_index(
        "ix_collab_messages_created_at",
        "collaboration_messages",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "agent_handoff_requests",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("thread_id", sa.String(), nullable=False),
        sa.Column("requesting_agent_id", sa.String(), nullable=False),
        sa.Column("target_agent_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "required_capabilities",
            postgresql.ARRAY(sa.String(length=100)),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("ticket_id", sa.String(), nullable=True),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["thread_id"], ["collaboration_threads.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_handoffs_thread", "agent_handoff_requests", ["thread_id"], unique=False
    )
    op.create_index(
        "ix_handoffs_status", "agent_handoff_requests", ["status"], unique=False
    )
    op.create_index(
        "ix_handoffs_ticket", "agent_handoff_requests", ["ticket_id"], unique=False
    )
    op.create_index(
        "ix_handoffs_task", "agent_handoff_requests", ["task_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_handoffs_task", table_name="agent_handoff_requests")
    op.drop_index("ix_handoffs_ticket", table_name="agent_handoff_requests")
    op.drop_index("ix_handoffs_status", table_name="agent_handoff_requests")
    op.drop_index("ix_handoffs_thread", table_name="agent_handoff_requests")
    op.drop_table("agent_handoff_requests")

    op.drop_index("ix_collab_messages_created_at", table_name="collaboration_messages")
    op.drop_index("ix_collab_messages_thread", table_name="collaboration_messages")
    op.drop_table("collaboration_messages")

    op.drop_index("ix_collab_threads_updated_at", table_name="collaboration_threads")
    op.drop_index("ix_collab_threads_context_id", table_name="collaboration_threads")
    op.drop_table("collaboration_threads")
