"""Diagnostic system and result submission tables

Revision ID: 009_diagnostic_system
Revises: 008_guardian
Create Date: 2025-11-17

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "009_diagnostic_system"
down_revision: Union[str, None] = "008_guardian"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agent results table (task-level results)
    op.create_table(
        "agent_results",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("markdown_content", sa.Text(), nullable=False),
        sa.Column("markdown_file_path", sa.Text(), nullable=False),
        sa.Column("result_type", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "verification_status",
            sa.String(length=20),
            nullable=False,
            server_default="unverified",
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by_validation_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"], ["agents.id"], name="fk_agent_results_agent"
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["tasks.id"], name="fk_agent_results_task"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_results_agent_id", "agent_results", ["agent_id"])
    op.create_index("ix_agent_results_task_id", "agent_results", ["task_id"])
    op.create_index("ix_agent_results_result_type", "agent_results", ["result_type"])
    op.create_index(
        "ix_agent_results_verification_status",
        "agent_results",
        ["verification_status"],
    )
    op.create_index("ix_agent_results_created_at", "agent_results", ["created_at"])

    # Workflow results table (workflow-level results)
    op.create_table(
        "workflow_results",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workflow_id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("markdown_file_path", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="pending_validation",
        ),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validation_feedback", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["workflow_id"], ["tickets.id"], name="fk_workflow_results_ticket"
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"], ["agents.id"], name="fk_workflow_results_agent"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workflow_results_workflow_id", "workflow_results", ["workflow_id"]
    )
    op.create_index("ix_workflow_results_agent_id", "workflow_results", ["agent_id"])
    op.create_index("ix_workflow_results_status", "workflow_results", ["status"])
    op.create_index(
        "ix_workflow_results_created_at", "workflow_results", ["created_at"]
    )

    # Diagnostic runs table
    op.create_table(
        "diagnostic_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workflow_id", sa.String(), nullable=False),
        sa.Column("diagnostic_agent_id", sa.String(), nullable=True),
        sa.Column("diagnostic_task_id", sa.String(), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_tasks_at_trigger", sa.Integer(), nullable=False),
        sa.Column("done_tasks_at_trigger", sa.Integer(), nullable=False),
        sa.Column("failed_tasks_at_trigger", sa.Integer(), nullable=False),
        sa.Column("time_since_last_task_seconds", sa.Integer(), nullable=False),
        sa.Column(
            "tasks_created_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "tasks_created_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("workflow_goal", sa.Text(), nullable=True),
        sa.Column(
            "phases_analyzed", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "agents_reviewed", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="created",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["workflow_id"], ["tickets.id"], name="fk_diagnostic_runs_ticket"
        ),
        sa.ForeignKeyConstraint(
            ["diagnostic_agent_id"],
            ["agents.id"],
            name="fk_diagnostic_runs_agent",
        ),
        sa.ForeignKeyConstraint(
            ["diagnostic_task_id"], ["tasks.id"], name="fk_diagnostic_runs_task"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_diagnostic_runs_workflow_id", "diagnostic_runs", ["workflow_id"]
    )
    op.create_index(
        "ix_diagnostic_runs_triggered_at", "diagnostic_runs", ["triggered_at"]
    )
    op.create_index("ix_diagnostic_runs_status", "diagnostic_runs", ["status"])


def downgrade() -> None:
    # Drop diagnostic runs
    op.drop_index("ix_diagnostic_runs_status", table_name="diagnostic_runs")
    op.drop_index("ix_diagnostic_runs_triggered_at", table_name="diagnostic_runs")
    op.drop_index("ix_diagnostic_runs_workflow_id", table_name="diagnostic_runs")
    op.drop_table("diagnostic_runs")

    # Drop workflow results
    op.drop_index("ix_workflow_results_created_at", table_name="workflow_results")
    op.drop_index("ix_workflow_results_status", table_name="workflow_results")
    op.drop_index("ix_workflow_results_agent_id", table_name="workflow_results")
    op.drop_index("ix_workflow_results_workflow_id", table_name="workflow_results")
    op.drop_table("workflow_results")

    # Drop agent results
    op.drop_index("ix_agent_results_created_at", table_name="agent_results")
    op.drop_index("ix_agent_results_verification_status", table_name="agent_results")
    op.drop_index("ix_agent_results_result_type", table_name="agent_results")
    op.drop_index("ix_agent_results_task_id", table_name="agent_results")
    op.drop_index("ix_agent_results_agent_id", table_name="agent_results")
    op.drop_table("agent_results")
