"""Add reasoning and explore tables

Revision ID: 033_add_reasoning_and_explore
Revises: 032_add_specs_tables
Create Date: 2025-12-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "033_add_reasoning_and_explore"
down_revision = "032_add_specs_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create reasoning_events table
    op.create_table(
        "reasoning_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "entity_type",
            sa.String(50),
            nullable=False,
            comment="Type of entity: ticket, spec, task, etc.",
        ),
        sa.Column(
            "entity_id",
            sa.String(),
            nullable=False,
            comment="ID of the referenced entity",
        ),
        sa.Column(
            "event_type",
            sa.String(50),
            nullable=False,
            comment="Event type: ticket_created, task_spawned, discovery, agent_decision, blocking_added, code_change, error",
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "agent",
            sa.String(100),
            nullable=True,
            comment="Agent that triggered the event",
        ),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Event-specific details (context, reasoning, discovery_type, etc.)",
        ),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Supporting evidence (type, content, link)",
        ),
        sa.Column(
            "decision",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Decision made (type, action, reasoning)",
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="When the event occurred",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Stores agent reasoning events and decisions for entities",
    )
    op.create_index(
        op.f("ix_reasoning_events_entity_type"),
        "reasoning_events",
        ["entity_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reasoning_events_entity_id"),
        "reasoning_events",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reasoning_events_event_type"),
        "reasoning_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reasoning_events_timestamp"),
        "reasoning_events",
        ["timestamp"],
        unique=False,
    )

    # Create explore_conversations table
    op.create_table(
        "explore_conversations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column(
            "last_message",
            sa.Text(),
            nullable=True,
            comment="Preview of last message for listing",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Code exploration conversation sessions",
    )
    op.create_index(
        op.f("ix_explore_conversations_project_id"),
        "explore_conversations",
        ["project_id"],
        unique=False,
    )

    # Create explore_messages table
    op.create_table(
        "explore_messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("conversation_id", sa.String(), nullable=False),
        sa.Column(
            "role",
            sa.String(20),
            nullable=False,
            comment="Message role: user or assistant",
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["explore_conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Messages in code exploration conversations",
    )
    op.create_index(
        op.f("ix_explore_messages_conversation_id"),
        "explore_messages",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_explore_messages_conversation_id"), table_name="explore_messages"
    )
    op.drop_table("explore_messages")

    op.drop_index(
        op.f("ix_explore_conversations_project_id"), table_name="explore_conversations"
    )
    op.drop_table("explore_conversations")

    op.drop_index(op.f("ix_reasoning_events_timestamp"), table_name="reasoning_events")
    op.drop_index(op.f("ix_reasoning_events_event_type"), table_name="reasoning_events")
    op.drop_index(op.f("ix_reasoning_events_entity_id"), table_name="reasoning_events")
    op.drop_index(
        op.f("ix_reasoning_events_entity_type"), table_name="reasoning_events"
    )
    op.drop_table("reasoning_events")
