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
    # Enhanced with Hephaestus-inspired done definitions, outputs, and prompts
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
        # Hephaestus-inspired enhancements
        sa.Column(
            "done_definitions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Concrete, verifiable completion criteria (array of strings)",
        ),
        sa.Column(
            "expected_outputs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Expected artifacts: [{type: 'file', pattern: 'src/*.py', required: true}]",
        ),
        sa.Column(
            "phase_prompt",
            sa.Text(),
            nullable=True,
            comment="Phase-level system prompt/instructions for agents",
        ),
        sa.Column(
            "next_steps_guide",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Guidance on what happens after phase completion (array of strings)",
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
    op.execute("""
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
        """)

    # Create board_columns table (Kanban visualization)
    op.create_table(
        "board_columns",
        sa.Column("id", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column(
            "phase_mapping",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="Which phase IDs map to this column",
        ),
        sa.Column(
            "wip_limit",
            sa.Integer(),
            nullable=True,
            comment="Work-in-progress limit (null = unlimited)",
        ),
        sa.Column(
            "is_terminal",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether this is an end column",
        ),
        sa.Column(
            "auto_transition_to",
            sa.String(50),
            nullable=True,
            comment="Column to auto-transition to on completion",
        ),
        sa.Column(
            "color_theme",
            sa.String(50),
            nullable=True,
            comment="Visual theme color",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_board_columns_sequence_order",
        "board_columns",
        ["sequence_order"],
        unique=False,
    )

    # Populate board_columns with default Kanban layout
    op.execute("""
        INSERT INTO board_columns (id, name, description, sequence_order, phase_mapping, wip_limit, is_terminal, auto_transition_to, color_theme) VALUES
        ('backlog', '📋 Backlog', 'Tickets awaiting analysis', 0,
         '["PHASE_BACKLOG"]'::jsonb, null, false, null, 'gray'),
        ('analyzing', '🔍 Analyzing', 'Requirements analysis and design', 1,
         '["PHASE_REQUIREMENTS", "PHASE_DESIGN"]'::jsonb, 5, false, null, 'blue'),
        ('building', '🔨 Building', 'Active implementation work', 2,
         '["PHASE_IMPLEMENTATION"]'::jsonb, 10, false, 'testing', 'yellow'),
        ('testing', '🧪 Testing', 'Validation and quality assurance', 3,
         '["PHASE_TESTING"]'::jsonb, 8, false, null, 'blue'),
        ('deploying', '🚀 Deploying', 'Ready for deployment', 4,
         '["PHASE_DEPLOYMENT"]'::jsonb, 3, false, 'done', 'green'),
        ('done', '✅ Done', 'Completed tickets', 5,
         '["PHASE_DONE"]'::jsonb, null, true, null, 'green'),
        ('blocked', '🚫 Blocked', 'Blocked by dependencies', 6,
         '["PHASE_BLOCKED"]'::jsonb, null, true, null, 'red')
        """)

    # Create task_discoveries table (Hephaestus-inspired discovery tracking)
    op.create_table(
        "task_discoveries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "source_task_id",
            sa.String(),
            nullable=False,
            comment="Task that made the discovery",
        ),
        sa.Column(
            "discovery_type",
            sa.String(50),
            nullable=False,
            comment="Type: bug, optimization, clarification_needed, new_component, etc.",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
            comment="What was discovered",
        ),
        sa.Column(
            "spawned_task_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="Array of task IDs spawned from this discovery",
        ),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When the discovery was made",
        ),
        sa.Column(
            "priority_boost",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether discovery warranted priority escalation",
        ),
        sa.Column(
            "resolution_status",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'open'"),
            comment="Status: open, in_progress, resolved, invalid",
        ),
        sa.Column(
            "discovery_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Additional discovery metadata (evidence, context, etc.)",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["source_task_id"],
            ["tasks.id"],
            name="fk_task_discoveries_source_task_id",
            ondelete="CASCADE",
        ),
    )

    # Create indexes for task_discoveries
    op.create_index(
        "ix_task_discoveries_source_task_id",
        "task_discoveries",
        ["source_task_id"],
        unique=False,
    )
    op.create_index(
        "ix_task_discoveries_discovery_type",
        "task_discoveries",
        ["discovery_type"],
        unique=False,
    )
    op.create_index(
        "ix_task_discoveries_discovered_at",
        "task_discoveries",
        ["discovered_at"],
        unique=False,
    )
    op.create_index(
        "ix_task_discoveries_resolution_status",
        "task_discoveries",
        ["resolution_status"],
        unique=False,
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

    # Create quality_metrics table (Phase 5 Quality Squad)
    op.create_table(
        "quality_metrics",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "task_id",
            sa.String(),
            nullable=False,
            comment="Task being measured",
        ),
        sa.Column(
            "metric_type",
            sa.String(50),
            nullable=False,
            comment="Type: coverage, lint, complexity, security, performance",
        ),
        sa.Column(
            "metric_name",
            sa.String(100),
            nullable=False,
            comment="Specific metric name",
        ),
        sa.Column("value", sa.Float(), nullable=False, comment="Measured value"),
        sa.Column("threshold", sa.Float(), nullable=True, comment="Required threshold"),
        sa.Column(
            "passed",
            sa.Boolean(),
            nullable=False,
            comment="Whether threshold was met",
        ),
        sa.Column(
            "measured_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When measurement was taken",
        ),
        sa.Column(
            "measurement_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Additional measurement context",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name="fk_quality_metrics_task_id",
            ondelete="CASCADE",
        ),
    )

    # Create indexes for quality_metrics
    op.create_index(
        "ix_quality_metrics_task_id", "quality_metrics", ["task_id"], unique=False
    )
    op.create_index(
        "ix_quality_metrics_metric_type",
        "quality_metrics",
        ["metric_type"],
        unique=False,
    )
    op.create_index(
        "ix_quality_metrics_passed", "quality_metrics", ["passed"], unique=False
    )
    op.create_index(
        "ix_quality_metrics_measured_at",
        "quality_metrics",
        ["measured_at"],
        unique=False,
    )

    # Create quality_gates table
    op.create_table(
        "quality_gates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "phase_id",
            sa.String(50),
            nullable=False,
            comment="Phase this gate applies to",
        ),
        sa.Column(
            "gate_type",
            sa.String(50),
            nullable=False,
            comment="Type: quality, ml_prediction, custom",
        ),
        sa.Column("name", sa.String(200), nullable=False, comment="Gate name"),
        sa.Column(
            "requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Requirements: {min_test_coverage: 80, max_lint_errors: 0}",
        ),
        sa.Column(
            "predictor_model",
            sa.String(100),
            nullable=True,
            comment="ML predictor model name",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Whether gate is active",
        ),
        sa.Column(
            "failure_action",
            sa.String(50),
            nullable=True,
            server_default=sa.text("'block'"),
            comment="Action on failure: block, warn, log",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for quality_gates
    op.create_index(
        "ix_quality_gates_phase_id", "quality_gates", ["phase_id"], unique=False
    )
    op.create_index(
        "ix_quality_gates_gate_type", "quality_gates", ["gate_type"], unique=False
    )
    op.create_index(
        "ix_quality_gates_enabled", "quality_gates", ["enabled"], unique=False
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("quality_gates")
    op.drop_table("quality_metrics")
    op.drop_table("learned_patterns")
    op.drop_table("task_memories")
    op.drop_table("task_discoveries")
    op.drop_table("board_columns")
    op.drop_table("phases")
