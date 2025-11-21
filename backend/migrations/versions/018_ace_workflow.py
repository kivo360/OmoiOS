"""ACE Workflow (REQ-MEM-ACE-001, REQ-MEM-ACE-002, REQ-MEM-ACE-003)

Revision ID: 018_ace_workflow
Revises: 017_memory_type_taxonomy
Create Date: 2025-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "018_ace_workflow"
down_revision: Union[str, None] = "017_memory_type_taxonomy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ACE workflow fields to task_memories table (REQ-MEM-ACE-001)
    op.add_column(
        "task_memories",
        sa.Column(
            "goal",
            sa.Text(),
            nullable=True,
            comment="What the agent was trying to accomplish (REQ-MEM-ACE-001)",
        ),
    )
    op.add_column(
        "task_memories",
        sa.Column(
            "result",
            sa.Text(),
            nullable=True,
            comment="What actually happened (REQ-MEM-ACE-001)",
        ),
    )
    op.add_column(
        "task_memories",
        sa.Column(
            "feedback",
            sa.Text(),
            nullable=True,
            comment="Output from environment (stdout, stderr, test results) (REQ-MEM-ACE-001)",
        ),
    )
    op.add_column(
        "task_memories",
        sa.Column(
            "tool_usage",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Tools used during task execution (REQ-MEM-ACE-001)",
        ),
    )

    # Create playbook_entries table (REQ-MEM-ACE-003)
    op.create_table(
        "playbook_entries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "ticket_id",
            sa.String(),
            nullable=False,
            comment="Ticket (project) this playbook entry belongs to",
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
            comment="Playbook entry content (REQ-MEM-ACE-003)",
        ),
        sa.Column(
            "category",
            sa.String(length=100),
            nullable=True,
            comment="Category: dependencies, architecture, gotchas, patterns, etc.",
        ),
        sa.Column(
            "embedding",
            postgresql.ARRAY(sa.Float()),
            nullable=True,
            comment="1536-dimensional embedding vector for similarity search",
        ),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String(length=100)),
            nullable=True,
            comment="Tags for filtering and categorization",
        ),
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Priority level (higher = more important)",
        ),
        sa.Column(
            "supporting_memory_ids",
            postgresql.ARRAY(sa.String()),
            nullable=True,
            comment="Memory IDs that support this playbook entry",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="When this entry was created",
        ),
        sa.Column(
            "created_by",
            sa.String(),
            nullable=True,
            comment="Agent ID that created this entry",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="When this entry was last updated",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Whether this entry is active (soft delete)",
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_playbook_entries_ticket_id"), "playbook_entries", ["ticket_id"], unique=False
    )
    op.create_index(
        op.f("ix_playbook_entries_category"), "playbook_entries", ["category"], unique=False
    )
    op.create_index(
        op.f("ix_playbook_entries_priority"), "playbook_entries", ["priority"], unique=False
    )
    op.create_index(
        op.f("ix_playbook_entries_created_at"), "playbook_entries", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_playbook_entries_is_active"), "playbook_entries", ["is_active"], unique=False
    )

    # Create playbook_changes table (REQ-MEM-DM-007)
    op.create_table(
        "playbook_changes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "ticket_id",
            sa.String(),
            nullable=False,
            comment="Ticket (project) this change belongs to",
        ),
        sa.Column(
            "playbook_entry_id",
            sa.String(),
            nullable=True,
            comment="Entry that was changed (null for add operations on deleted entries)",
        ),
        sa.Column(
            "operation",
            sa.String(length=50),
            nullable=False,
            comment="Operation type: add, update, delete (REQ-MEM-DM-007)",
        ),
        sa.Column(
            "old_content",
            sa.Text(),
            nullable=True,
            comment="Old content before change (REQ-MEM-DM-007)",
        ),
        sa.Column(
            "new_content",
            sa.Text(),
            nullable=True,
            comment="New content after change (REQ-MEM-DM-007)",
        ),
        sa.Column(
            "delta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Structured delta representation (REQ-MEM-DM-007)",
        ),
        sa.Column(
            "reason",
            sa.Text(),
            nullable=True,
            comment="Reason for change (REQ-MEM-DM-007)",
        ),
        sa.Column(
            "related_memory_id",
            sa.String(),
            nullable=True,
            comment="Memory ID that triggered this change (REQ-MEM-DM-007)",
        ),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="When this change was made (REQ-MEM-DM-007)",
        ),
        sa.Column(
            "changed_by",
            sa.String(),
            nullable=True,
            comment="Agent ID that made this change (REQ-MEM-DM-007)",
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["playbook_entry_id"],
            ["playbook_entries.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_playbook_changes_ticket_id"), "playbook_changes", ["ticket_id"], unique=False
    )
    op.create_index(
        op.f("ix_playbook_changes_playbook_entry_id"),
        "playbook_changes",
        ["playbook_entry_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_playbook_changes_operation"), "playbook_changes", ["operation"], unique=False
    )
    op.create_index(
        op.f("ix_playbook_changes_related_memory_id"),
        "playbook_changes",
        ["related_memory_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_playbook_changes_changed_at"), "playbook_changes", ["changed_at"], unique=False
    )

    # Add check constraint for valid operation values (REQ-MEM-DM-007)
    op.create_check_constraint(
        op.f("ck_playbook_changes_valid_operation"),
        "playbook_changes",
        sa.text("operation IN ('add', 'update', 'delete')"),
    )


def downgrade() -> None:
    # Remove check constraint
    op.drop_constraint(
        op.f("ck_playbook_changes_valid_operation"), "playbook_changes", type_="check"
    )

    # Drop playbook_changes table
    op.drop_index(op.f("ix_playbook_changes_changed_at"), table_name="playbook_changes")
    op.drop_index(
        op.f("ix_playbook_changes_related_memory_id"), table_name="playbook_changes"
    )
    op.drop_index(op.f("ix_playbook_changes_operation"), table_name="playbook_changes")
    op.drop_index(
        op.f("ix_playbook_changes_playbook_entry_id"), table_name="playbook_changes"
    )
    op.drop_index(op.f("ix_playbook_changes_ticket_id"), table_name="playbook_changes")
    op.drop_table("playbook_changes")

    # Drop playbook_entries table
    op.drop_index(op.f("ix_playbook_entries_is_active"), table_name="playbook_entries")
    op.drop_index(op.f("ix_playbook_entries_created_at"), table_name="playbook_entries")
    op.drop_index(op.f("ix_playbook_entries_priority"), table_name="playbook_entries")
    op.drop_index(op.f("ix_playbook_entries_category"), table_name="playbook_entries")
    op.drop_index(op.f("ix_playbook_entries_ticket_id"), table_name="playbook_entries")
    op.drop_table("playbook_entries")

    # Remove ACE workflow fields from task_memories
    op.drop_column("task_memories", "tool_usage")
    op.drop_column("task_memories", "feedback")
    op.drop_column("task_memories", "result")
    op.drop_column("task_memories", "goal")

