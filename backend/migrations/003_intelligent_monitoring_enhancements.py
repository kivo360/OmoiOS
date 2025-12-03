"""Intelligent monitoring enhancements for trajectory-based analysis.

This migration adds tables for:
- Guardian trajectory analyses with LLM-powered agent understanding
- Conductor system coherence analyses and duplicate detection
- Steering intervention tracking and audit trails
- Vector search capabilities for semantic similarity

Revision ID: 003
Revises: 001_phase_1_enhancements, 002_async_sqlalchemy_migration_plan
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "003_intelligent_monitoring_enhancements"
down_revision = "002_async_sqlalchemy_migration_plan"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add intelligent monitoring tables."""

    # Guardian trajectory analyses table
    op.create_table(
        "guardian_analyses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.String(length=255), nullable=False),
        sa.Column("current_phase", sa.String(length=64), nullable=True),
        sa.Column("trajectory_aligned", sa.Boolean(), nullable=False, default=True),
        sa.Column("alignment_score", sa.Float(), nullable=False),
        sa.Column("needs_steering", sa.Boolean(), nullable=False, default=False),
        sa.Column("steering_type", sa.String(length=64), nullable=True),
        sa.Column("steering_recommendation", sa.Text(), nullable=True),
        sa.Column("trajectory_summary", sa.Text(), nullable=False),
        sa.Column("last_claude_message_marker", sa.Text(), nullable=True),
        sa.Column("accumulated_goal", sa.Text(), nullable=True),
        sa.Column("current_focus", sa.String(length=128), nullable=True),
        sa.Column("session_duration", sa.Interval(), nullable=True),
        sa.Column("conversation_length", sa.Integer(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.Index("idx_guardian_analyses_agent_created", "agent_id", "created_at"),
        sa.Index("idx_guardian_analyses_alignment", "alignment_score"),
        sa.Index("idx_guardian_analyses_needs_steering", "needs_steering"),
    )
    op.create_index(
        "idx_guardian_analyses_agent_created",
        "guardian_analyses",
        ["agent_id", "created_at"],
    )
    op.create_index(
        "idx_guardian_analyses_alignment", "guardian_analyses", ["alignment_score"]
    )
    op.create_index(
        "idx_guardian_analyses_needs_steering", "guardian_analyses", ["needs_steering"]
    )

    # Conductor system analyses table
    op.create_table(
        "conductor_analyses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("cycle_id", sa.UUID(), nullable=False),
        sa.Column("coherence_score", sa.Float(), nullable=False),
        sa.Column("system_status", sa.String(length=32), nullable=False),
        sa.Column("num_agents", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, default=0),
        sa.Column("termination_count", sa.Integer(), nullable=False, default=0),
        sa.Column("coordination_count", sa.Integer(), nullable=False, default=0),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.Index("idx_conductor_analyses_created", "created_at"),
        sa.Index("idx_conductor_analyses_coherence", "coherence_score"),
        sa.Index("idx_conductor_analyses_status", "system_status"),
    )
    op.create_index(
        "idx_conductor_analyses_created", "conductor_analyses", ["created_at"]
    )
    op.create_index(
        "idx_conductor_analyses_coherence", "conductor_analyses", ["coherence_score"]
    )
    op.create_index(
        "idx_conductor_analyses_status", "conductor_analyses", ["system_status"]
    )

    # Detected duplicates table
    op.create_table(
        "detected_duplicates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conductor_analysis_id", sa.UUID(), nullable=False),
        sa.Column("agent1_id", sa.String(length=255), nullable=False),
        sa.Column("agent2_id", sa.String(length=255), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("work_description", sa.Text(), nullable=True),
        sa.Column("resources", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["conductor_analysis_id"],
            ["conductor_analyses.id"],
        ),
        sa.Index("idx_duplicates_cycle", "conductor_analysis_id"),
        sa.Index("idx_duplicates_agents", "agent1_id", "agent2_id"),
        sa.Index("idx_duplicates_similarity", "similarity_score"),
    )
    op.create_index(
        "idx_duplicates_cycle", "detected_duplicates", ["conductor_analysis_id"]
    )
    op.create_index(
        "idx_duplicates_agents", "detected_duplicates", ["agent1_id", "agent2_id"]
    )
    op.create_index(
        "idx_duplicates_similarity", "detected_duplicates", ["similarity_score"]
    )

    # Steering interventions table
    op.create_table(
        "steering_interventions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.String(length=255), nullable=False),
        sa.Column("steering_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("idx_steering_agent_created", "agent_id", "created_at"),
        sa.Index("idx_steering_type", "steering_type"),
        sa.Index("idx_steering_actor_type", "actor_type"),
    )
    op.create_index(
        "idx_steering_agent_created",
        "steering_interventions",
        ["agent_id", "created_at"],
    )
    op.create_index("idx_steering_type", "steering_interventions", ["steering_type"])
    op.create_index("idx_steering_actor_type", "steering_interventions", ["actor_type"])

    # Vector search table for semantic similarity (PGVector integration)
    op.create_table(
        "monitoring_vectors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("embedding", postgresql.VECTOR(1536), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("idx_monitoring_vectors_entity", "entity_type", "entity_id"),
        sa.Index(
            "idx_monitoring_vectors_embedding", "embedding", postgresql_using="gin"
        ),
    )
    op.create_index(
        "idx_monitoring_vectors_entity",
        "monitoring_vectors",
        ["entity_type", "entity_id"],
    )
    op.execute(
        "CREATE INDEX idx_monitoring_vectors_embedding ON monitoring_vectors USING gin (embedding)"
    )

    # Monitoring audit log for compliance
    op.create_table(
        "monitoring_audit_log",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=True),
        sa.Column("target_agent_ids", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("idx_monitoring_audit_created", "created_at"),
        sa.Index("idx_monitoring_audit_event_type", "event_type"),
    )
    op.create_index(
        "idx_monitoring_audit_created", "monitoring_audit_log", ["created_at"]
    )
    op.create_index(
        "idx_monitoring_audit_event_type", "monitoring_audit_log", ["event_type"]
    )

    # Add monitoring configuration to agents table
    op.add_column("agents", "anomaly_score", sa.Float(), nullable=True, default=0.0)
    op.add_column(
        "agents",
        "consecutive_anomalous_readings",
        sa.Integer(),
        nullable=True,
        default=0,
    )

    # Add monitoring fields to tasks table
    op.add_column("tasks", "monitoring_notes", sa.Text(), nullable=True)
    op.add_column("tasks", "discovery_impact", sa.String(length=32), nullable=True)


def downgrade() -> None:
    """Remove intelligent monitoring tables."""

    # Remove monitoring fields from tasks and agents
    op.drop_column("tasks", "discovery_impact")
    op.drop_column("tasks", "monitoring_notes")
    op.drop_column("agents", "consecutive_anomalous_readings")
    op.drop_column("agents", "anomaly_score")

    # Drop tables in reverse order
    op.drop_table("monitoring_audit_log")
    op.drop_table("monitoring_vectors")
    op.drop_table("steering_interventions")
    op.drop_table("detected_duplicates")
    op.drop_table("conductor_analyses")
    op.drop_table("guardian_analyses")
