"""Initial foundation models

Revision ID: 001_initial
Revises:
Create Date: 2025-11-16

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fix alembic_version table column length to support long revision IDs
    # Alembic creates this table automatically, but with VARCHAR(32) which is too short
    # This is done after Alembic creates the table, so we need to handle it carefully
    try:
        conn = op.get_bind()
        inspector = inspect(conn)
        if "alembic_version" in inspector.get_table_names():
            # Check current column type and alter if needed
            columns = {col["name"]: col for col in inspector.get_columns("alembic_version")}
            if "version_num" in columns:
                current_type = str(columns["version_num"]["type"])
                if "32" in current_type or "VARCHAR(32)" in current_type.upper():
                    op.alter_column("alembic_version", "version_num", type_=sa.String(255))
    except Exception as e:
        # If inspection fails, continue with migration - alembic_version will be handled later
        print(f"Note: Could not alter alembic_version column: {e}")

    # Create tickets table
    print("DEBUG: About to create tickets table...")
    op.create_table(
        "tickets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("phase_id", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tickets_phase_id"), "tickets", ["phase_id"], unique=False)
    op.create_index(op.f("ix_tickets_priority"), "tickets", ["priority"], unique=False)
    op.create_index(op.f("ix_tickets_status"), "tickets", ["status"], unique=False)
    
    # Verify table was created
    try:
        conn = op.get_bind()
        inspector = inspect(conn)
        if "tickets" in inspector.get_table_names():
            print("DEBUG: tickets table created successfully")
        else:
            print("DEBUG: ERROR - tickets table NOT found after creation!")
    except Exception as e:
        print(f"DEBUG: Could not verify tickets table: {e}")

    # Create tasks table
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("ticket_id", sa.String(), nullable=False),
        sa.Column("phase_id", sa.String(length=50), nullable=False),
        sa.Column("task_type", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("assigned_agent_id", sa.String(), nullable=True),
        sa.Column("conversation_id", sa.String(length=255), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tasks_assigned_agent_id"), "tasks", ["assigned_agent_id"], unique=False
    )
    op.create_index(op.f("ix_tasks_phase_id"), "tasks", ["phase_id"], unique=False)
    op.create_index(op.f("ix_tasks_priority"), "tasks", ["priority"], unique=False)
    op.create_index(op.f("ix_tasks_status"), "tasks", ["status"], unique=False)
    op.create_index(op.f("ix_tasks_ticket_id"), "tasks", ["ticket_id"], unique=False)

    # Create agents table
    op.create_table(
        "agents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("agent_type", sa.String(length=50), nullable=False),
        sa.Column("phase_id", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agents_agent_type"), "agents", ["agent_type"], unique=False
    )
    op.create_index(op.f("ix_agents_phase_id"), "agents", ["phase_id"], unique=False)
    op.create_index(op.f("ix_agents_status"), "agents", ["status"], unique=False)

    # Create events table
    op.create_table(
        "events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", sa.String(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_events_event_type"), "events", ["event_type"], unique=False
    )
    op.create_index(op.f("ix_events_timestamp"), "events", ["timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_events_timestamp"), table_name="events")
    op.drop_index(op.f("ix_events_event_type"), table_name="events")
    op.drop_table("events")
    op.drop_index(op.f("ix_agents_status"), table_name="agents")
    op.drop_index(op.f("ix_agents_phase_id"), table_name="agents")
    op.drop_index(op.f("ix_agents_agent_type"), table_name="agents")
    op.drop_table("agents")
    op.drop_index(op.f("ix_tasks_ticket_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_status"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_priority"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_phase_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_assigned_agent_id"), table_name="tasks")
    op.drop_table("tasks")
    op.drop_index(op.f("ix_tickets_status"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_priority"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_phase_id"), table_name="tickets")
    op.drop_table("tickets")
