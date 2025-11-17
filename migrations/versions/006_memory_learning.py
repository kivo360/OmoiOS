"""Add memory and learning tables with vector embeddings

Revision ID: 006_memory_learning
Revises: 005_monitoring
Create Date: 2025-11-17

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "006_memory_learning"
down_revision: Union[str, None] = "005_monitoring"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create phases table (foundational - should have been in earlier migration)
    op.create_table(
        "phases",
        sa.Column("id", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column(
            "allowed_transitions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="List of phase IDs that can be transitioned to",
        ),
        sa.Column(
            "is_terminal",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether this is a terminal phase",
        ),
        sa.Column(
            "configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Phase-specific configuration",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_phases_sequence_order", "phases", ["sequence_order"], unique=False
    )

    # Populate phases table with default workflow phases
    op.execute(
        """
        INSERT INTO phases (id, name, description, sequence_order, allowed_transitions, is_terminal, configuration) VALUES
        ('PHASE_BACKLOG', 'Backlog', 'Initial ticket triage and prioritization', 0, 
         '["PHASE_REQUIREMENTS", "PHASE_BLOCKED"]'::jsonb, false, '{}'::jsonb),
        ('PHASE_REQUIREMENTS', 'Requirements Analysis', 'Gather and analyze requirements', 1,
         '["PHASE_DESIGN", "PHASE_BLOCKED"]'::jsonb, false, '{}'::jsonb),
        ('PHASE_DESIGN', 'Design', 'Create technical design and architecture', 2,
         '["PHASE_IMPLEMENTATION", "PHASE_BLOCKED"]'::jsonb, false, '{}'::jsonb),
        ('PHASE_IMPLEMENTATION', 'Implementation', 'Develop and implement features', 3,
         '["PHASE_TESTING", "PHASE_BLOCKED"]'::jsonb, false, '{}'::jsonb),
        ('PHASE_TESTING', 'Testing', 'Test and validate implementation', 4,
         '["PHASE_DEPLOYMENT", "PHASE_IMPLEMENTATION", "PHASE_BLOCKED"]'::jsonb, false, '{}'::jsonb),
        ('PHASE_DEPLOYMENT', 'Deployment', 'Deploy to production', 5,
         '["PHASE_DONE", "PHASE_BLOCKED"]'::jsonb, false, '{}'::jsonb),
        ('PHASE_DONE', 'Done', 'Ticket completed', 6,
         '[]'::jsonb, true, '{}'::jsonb),
        ('PHASE_BLOCKED', 'Blocked', 'Ticket blocked by external dependencies', 7,
         '["PHASE_BACKLOG", "PHASE_REQUIREMENTS", "PHASE_DESIGN", "PHASE_IMPLEMENTATION", "PHASE_TESTING"]'::jsonb, 
         true, '{}'::jsonb)
        """
    )

    # Create task_memories table
    op.create_table(
        "task_memories",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("execution_summary", sa.Text(), nullable=False),
        sa.Column(
            "context_embedding",
            postgresql.ARRAY(sa.Float(), dimensions=1),
            nullable=True,
            comment="1536-dimensional embedding vector",
        ),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column(
            "error_patterns",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Error patterns extracted from failed executions",
        ),
        sa.Column(
            "learned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "reused_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
            comment="Number of times this memory was used for context",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name="fk_task_memories_task_id",
            ondelete="CASCADE",
        ),
    )

    # Create indexes for task_memories
    op.create_index(
        "ix_task_memories_task_id", "task_memories", ["task_id"], unique=False
    )
    op.create_index(
        "ix_task_memories_success", "task_memories", ["success"], unique=False
    )
    op.create_index(
        "ix_task_memories_learned_at", "task_memories", ["learned_at"], unique=False
    )

    # Create learned_patterns table
    op.create_table(
        "learned_patterns",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "pattern_type",
            sa.String(50),
            nullable=False,
            comment="Type of pattern: success, failure, optimization",
        ),
        sa.Column(
            "task_type_pattern",
            sa.String(),
            nullable=False,
            comment="Regex or template matching task descriptions",
        ),
        sa.Column(
            "success_indicators",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="List of indicators that suggest success",
        ),
        sa.Column(
            "failure_indicators",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="List of indicators that suggest failure",
        ),
        sa.Column(
            "recommended_context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Context recommendations for matching tasks",
        ),
        sa.Column(
            "embedding",
            postgresql.ARRAY(sa.Float(), dimensions=1),
            nullable=True,
            comment="1536-dimensional pattern embedding",
        ),
        sa.Column(
            "confidence_score",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.5"),
            comment="Confidence score (0.0 to 1.0)",
        ),
        sa.Column(
            "usage_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
            comment="Number of times this pattern was applied",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for learned_patterns
    op.create_index(
        "ix_learned_patterns_pattern_type",
        "learned_patterns",
        ["pattern_type"],
        unique=False,
    )
    op.create_index(
        "ix_learned_patterns_confidence",
        "learned_patterns",
        ["confidence_score"],
        unique=False,
    )
    op.create_index(
        "ix_learned_patterns_usage",
        "learned_patterns",
        ["usage_count"],
        unique=False,
    )

    # Create GIN indexes for JSONB columns
    op.create_index(
        "ix_task_memories_error_patterns_gin",
        "task_memories",
        ["error_patterns"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_learned_patterns_success_indicators_gin",
        "learned_patterns",
        ["success_indicators"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_learned_patterns_failure_indicators_gin",
        "learned_patterns",
        ["failure_indicators"],
        unique=False,
        postgresql_using="gin",
    )

    # Note: Vector similarity indexes (ivfflat/hnsw) should be created after
    # some data is loaded, as they require training data. We'll add them via
    # a separate manual SQL script or in the service layer on first use.
    # Example for future use:
    # CREATE INDEX ON task_memories USING ivfflat (context_embedding vector_cosine_ops)
    # WITH (lists = 100);


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("learned_patterns")
    op.drop_table("task_memories")
    op.drop_table("phases")
