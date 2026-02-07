"""Validation system tables and extensions (Phase 6 Squad C)

Revision ID: 010_validation_system
Revises: 009_diagnostic_system
Create Date: 2025-01-27

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "010_validation_system"
down_revision: Union[str, None] = "009_diagnostic_system"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ValidationReview table (REQ-VAL-DM-003)
    op.create_table(
        "validation_reviews",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("validator_agent_id", sa.String(), nullable=False),
        sa.Column("iteration_number", sa.Integer(), nullable=False),
        sa.Column("validation_passed", sa.Boolean(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "recommendations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["validator_agent_id"],
            ["agents.id"],
            ondelete="RESTRICT",
        ),
    )

    # Indexes for validation_reviews
    op.create_index(
        "ix_validation_reviews_task_id",
        "validation_reviews",
        ["task_id"],
    )
    op.create_index(
        "ix_validation_reviews_validator_agent_id",
        "validation_reviews",
        ["validator_agent_id"],
    )
    op.create_index(
        "ix_validation_reviews_task_iteration",
        "validation_reviews",
        ["task_id", "iteration_number"],
    )

    # Task model extensions (REQ-VAL-DM-001)
    op.add_column(
        "tasks",
        sa.Column(
            "validation_enabled", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "tasks",
        sa.Column(
            "validation_iteration", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "tasks",
        sa.Column("last_validation_feedback", sa.Text(), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("review_done", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Agent model extensions (REQ-VAL-DM-002)
    op.add_column(
        "agents",
        sa.Column(
            "kept_alive_for_validation",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    # Agent extensions
    op.drop_column("agents", "kept_alive_for_validation")

    # Task extensions
    op.drop_column("tasks", "review_done")
    op.drop_column("tasks", "last_validation_feedback")
    op.drop_column("tasks", "validation_iteration")
    op.drop_column("tasks", "validation_enabled")

    # ValidationReview table
    op.drop_index("ix_validation_reviews_task_iteration", "validation_reviews")
    op.drop_index("ix_validation_reviews_validator_agent_id", "validation_reviews")
    op.drop_index("ix_validation_reviews_task_id", "validation_reviews")
    op.drop_table("validation_reviews")
