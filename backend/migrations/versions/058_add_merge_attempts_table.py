"""Add merge_attempts table for convergence merge audit trail.

Revision ID: 058_add_merge_attempts
Revises: 057_add_synthesis_and_ownership_fields
Create Date: 2026-01-30

Phase A: Foundation for DAG Merge Executor integration.
Tracks merge attempts at convergence points for audit trail and debugging.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "058_add_merge_attempts"
down_revision = "057_synthesis_ownership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create merge_attempts table."""
    op.create_table(
        "merge_attempts",
        # Primary key
        sa.Column("id", sa.String(), primary_key=True),
        # Related entities
        sa.Column(
            "task_id",
            sa.String(),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="Continuation task that triggered this merge",
        ),
        sa.Column(
            "ticket_id",
            sa.String(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="Ticket whose branch is target of merge",
        ),
        sa.Column(
            "spec_id",
            sa.String(),
            sa.ForeignKey("specs.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="Spec containing the parallel tasks",
        ),
        # Merge sources
        sa.Column(
            "source_task_ids",
            postgresql.JSONB(),
            nullable=False,
            comment="List of parallel task IDs whose changes are being merged",
        ),
        sa.Column(
            "incoming_branches",
            postgresql.JSONB(),
            nullable=True,
            comment="Git branches to merge (if using task-level branches)",
        ),
        sa.Column(
            "target_branch",
            sa.String(255),
            nullable=False,
            comment="Target branch for merge (usually ticket branch)",
        ),
        # Conflict scoring and ordering
        sa.Column(
            "merge_order",
            postgresql.JSONB(),
            nullable=True,
            comment="Task IDs in merge order (least conflicts first)",
        ),
        sa.Column(
            "conflict_scores",
            postgresql.JSONB(),
            nullable=True,
            comment="Dict mapping task_id -> conflict count from dry-run",
        ),
        sa.Column(
            "total_conflicts",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="Total number of conflicts detected",
        ),
        # Status and outcome
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            default="pending",
            index=True,
        ),
        sa.Column(
            "success",
            sa.Boolean(),
            nullable=True,
            comment="Whether merge completed successfully (null if in progress)",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Error message if merge failed",
        ),
        # LLM conflict resolution tracking
        sa.Column(
            "llm_invocations",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="Number of LLM calls for conflict resolution",
        ),
        sa.Column(
            "llm_resolution_log",
            postgresql.JSONB(),
            nullable=True,
            comment="Detailed log of LLM decisions for each conflict",
        ),
        sa.Column(
            "llm_tokens_used",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="Total tokens consumed by LLM resolution",
        ),
        sa.Column(
            "llm_cost_usd",
            sa.Integer(),
            nullable=False,
            default=0,
            comment="Estimated cost of LLM resolution in cents",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When merge execution actually started",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When merge finished (success or failure)",
        ),
    )

    # Create indexes for common queries
    op.create_index(
        "ix_merge_attempts_task_status",
        "merge_attempts",
        ["task_id", "status"],
    )
    op.create_index(
        "ix_merge_attempts_ticket_created",
        "merge_attempts",
        ["ticket_id", "created_at"],
    )


def downgrade() -> None:
    """Drop merge_attempts table."""
    op.drop_index("ix_merge_attempts_ticket_created", table_name="merge_attempts")
    op.drop_index("ix_merge_attempts_task_status", table_name="merge_attempts")
    op.drop_table("merge_attempts")
