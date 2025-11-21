"""Collaboration and resource locking support (Roles 2 & 3)

Revision ID: 004_collab_locks
Revises: 003_phase_workflow
Create Date: 2025-11-17

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004_collab_locks"
down_revision: Union[str, None] = "003_phase_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Role 2: Agent Messaging & Collaboration
    op.create_table(
        "agent_messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("thread_id", sa.String(), nullable=False),
        sa.Column("from_agent_id", sa.String(), nullable=False),
        sa.Column("to_agent_id", sa.String(), nullable=True),
        sa.Column("message_type", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "message_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["from_agent_id"], ["agents.id"], name="fk_messages_from_agent"
        ),
        sa.ForeignKeyConstraint(
            ["to_agent_id"], ["agents.id"], name="fk_messages_to_agent"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_messages_thread_id", "agent_messages", ["thread_id"])
    op.create_index(
        "ix_agent_messages_from_agent_id", "agent_messages", ["from_agent_id"]
    )
    op.create_index("ix_agent_messages_to_agent_id", "agent_messages", ["to_agent_id"])
    op.create_index(
        "ix_agent_messages_message_type", "agent_messages", ["message_type"]
    )

    op.create_table(
        "collaboration_threads",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("thread_type", sa.String(length=50), nullable=False),
        sa.Column("ticket_id", sa.String(), nullable=True),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column(
            "participants", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="active"
        ),
        sa.Column(
            "thread_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["tickets.id"], name="fk_threads_ticket"
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], name="fk_threads_task"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_collaboration_threads_ticket_id", "collaboration_threads", ["ticket_id"]
    )
    op.create_index(
        "ix_collaboration_threads_task_id", "collaboration_threads", ["task_id"]
    )

    # Role 3: Resource Locking
    op.create_table(
        "resource_locks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("locked_by_task_id", sa.String(), nullable=False),
        sa.Column("locked_by_agent_id", sa.String(), nullable=False),
        sa.Column(
            "lock_mode",
            sa.String(length=20),
            nullable=False,
            server_default="exclusive",
        ),
        sa.Column(
            "acquired_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["locked_by_task_id"], ["tasks.id"], name="fk_locks_task"
        ),
        sa.ForeignKeyConstraint(
            ["locked_by_agent_id"], ["agents.id"], name="fk_locks_agent"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_resource_locks_resource_type", "resource_locks", ["resource_type"]
    )
    op.create_index("ix_resource_locks_resource_id", "resource_locks", ["resource_id"])
    op.create_index(
        "ix_resource_locks_task_id", "resource_locks", ["locked_by_task_id"]
    )
    op.create_index(
        "ix_resource_locks_agent_id", "resource_locks", ["locked_by_agent_id"]
    )

    # Composite index for fast lock queries
    op.create_index(
        "ix_resource_locks_type_id",
        "resource_locks",
        ["resource_type", "resource_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop resource locks
    op.drop_index("ix_resource_locks_type_id", table_name="resource_locks")
    op.drop_index("ix_resource_locks_agent_id", table_name="resource_locks")
    op.drop_index("ix_resource_locks_task_id", table_name="resource_locks")
    op.drop_index("ix_resource_locks_resource_id", table_name="resource_locks")
    op.drop_index("ix_resource_locks_resource_type", table_name="resource_locks")
    op.drop_table("resource_locks")

    # Drop collaboration threads
    op.drop_index(
        "ix_collaboration_threads_task_id", table_name="collaboration_threads"
    )
    op.drop_index(
        "ix_collaboration_threads_ticket_id", table_name="collaboration_threads"
    )
    op.drop_table("collaboration_threads")

    # Drop agent messages
    op.drop_index("ix_agent_messages_message_type", table_name="agent_messages")
    op.drop_index("ix_agent_messages_to_agent_id", table_name="agent_messages")
    op.drop_index("ix_agent_messages_from_agent_id", table_name="agent_messages")
    op.drop_index("ix_agent_messages_thread_id", table_name="agent_messages")
    op.drop_table("agent_messages")
