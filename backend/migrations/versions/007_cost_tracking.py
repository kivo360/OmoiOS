"""Cost tracking and budget enforcement (Phase 5 - Cost Squad)

Revision ID: 007_cost_tracking
Revises: 006_memory_learning
Create Date: 2025-11-17

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "007_cost_tracking"
down_revision: Union[str, None] = "006_memory_learning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cost records table - tracks LLM API costs per task/agent
    op.create_table(
        "cost_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.String(), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "completion_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prompt_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("completion_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cost_records_task_id", "cost_records", ["task_id"])
    op.create_index("ix_cost_records_agent_id", "cost_records", ["agent_id"])
    op.create_index("ix_cost_records_provider", "cost_records", ["provider"])
    op.create_index("ix_cost_records_model", "cost_records", ["model"])
    op.create_index("ix_cost_records_total_cost", "cost_records", ["total_cost"])
    op.create_index("ix_cost_records_recorded_at", "cost_records", ["recorded_at"])

    # Budgets table - budget limits and tracking
    op.create_table(
        "budgets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scope_type", sa.String(length=20), nullable=False),
        sa.Column("scope_id", sa.String(length=50), nullable=True),
        sa.Column("limit_amount", sa.Float(), nullable=False),
        sa.Column("spent_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("remaining_amount", sa.Float(), nullable=False),
        sa.Column(
            "period_start",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("alert_threshold", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("alert_triggered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_budgets_scope_type", "budgets", ["scope_type"])
    op.create_index("ix_budgets_scope_id", "budgets", ["scope_id"])
    op.create_index("ix_budgets_period_start", "budgets", ["period_start"])
    op.create_index("ix_budgets_period_end", "budgets", ["period_end"])


def downgrade() -> None:
    op.drop_index("ix_budgets_period_end", table_name="budgets")
    op.drop_index("ix_budgets_period_start", table_name="budgets")
    op.drop_index("ix_budgets_scope_id", table_name="budgets")
    op.drop_index("ix_budgets_scope_type", table_name="budgets")
    op.drop_table("budgets")

    op.drop_index("ix_cost_records_recorded_at", table_name="cost_records")
    op.drop_index("ix_cost_records_total_cost", table_name="cost_records")
    op.drop_index("ix_cost_records_model", table_name="cost_records")
    op.drop_index("ix_cost_records_provider", table_name="cost_records")
    op.drop_index("ix_cost_records_agent_id", table_name="cost_records")
    op.drop_index("ix_cost_records_task_id", table_name="cost_records")
    op.drop_table("cost_records")
