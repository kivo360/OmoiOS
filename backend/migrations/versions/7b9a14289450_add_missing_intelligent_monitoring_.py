"""Add missing intelligent monitoring tables

Revision ID: 7b9a14289450
Revises: 028_add_persistence_dir_to_tasks
Create Date: 2025-11-19 11:08:59.562968

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.exc import NoSuchTableError


# revision identifiers, used by Alembic.
revision: str = "7b9a14289450"
down_revision: Union[str, Sequence[str], None] = "028_add_persistence_dir_to_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector: Inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {col["name"] for col in inspector.get_columns(table_name)}
    except NoSuchTableError:
        return False


def _index_exists(inspector: Inspector, table_name: str, index_name: str) -> bool:
    try:
        return index_name in {idx["name"] for idx in inspector.get_indexes(table_name)}
    except NoSuchTableError:
        return False


def _ensure_index(
    inspector: Inspector,
    table_name: str,
    index_name: str,
    columns: list[str],
    **kwargs,
) -> None:
    if not _table_exists(inspector, table_name):
        return
    if not _index_exists(inspector, table_name, index_name):
        op.create_index(index_name, table_name, columns, **kwargs)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Conductor system analyses (system coherence snapshots)
    if not _table_exists(inspector, "conductor_analyses"):
        op.create_table(
            "conductor_analyses",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("cycle_id", sa.UUID(), nullable=False),
            sa.Column("coherence_score", sa.Float(), nullable=False),
            sa.Column("system_status", sa.String(length=32), nullable=False),
            sa.Column("num_agents", sa.Integer(), nullable=False),
            sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("termination_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("coordination_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
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
        )
        inspector = sa.inspect(bind)

    _ensure_index(inspector, "conductor_analyses", "idx_conductor_analyses_created", ["created_at"])
    _ensure_index(inspector, "conductor_analyses", "idx_conductor_analyses_coherence", ["coherence_score"])
    _ensure_index(inspector, "conductor_analyses", "idx_conductor_analyses_status", ["system_status"])

    # Guardian trajectory analyses (agent-level monitoring)
    if not _table_exists(inspector, "guardian_analyses"):
        op.create_table(
            "guardian_analyses",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("agent_id", sa.String(length=255), nullable=False),
            sa.Column("current_phase", sa.String(length=64), nullable=True),
            sa.Column("trajectory_aligned", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("alignment_score", sa.Float(), nullable=False),
            sa.Column("needs_steering", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
        )
        inspector = sa.inspect(bind)

    _ensure_index(
        inspector, "guardian_analyses", "idx_guardian_analyses_agent_created", ["agent_id", "created_at"]
    )
    _ensure_index(inspector, "guardian_analyses", "idx_guardian_analyses_alignment", ["alignment_score"])
    _ensure_index(inspector, "guardian_analyses", "idx_guardian_analyses_needs_steering", ["needs_steering"])

    # Duplicate detection output referencing conductor analyses
    if not _table_exists(inspector, "detected_duplicates"):
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
            sa.ForeignKeyConstraint(["conductor_analysis_id"], ["conductor_analyses.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)

    _ensure_index(inspector, "detected_duplicates", "idx_duplicates_cycle", ["conductor_analysis_id"])
    _ensure_index(inspector, "detected_duplicates", "idx_duplicates_agents", ["agent1_id", "agent2_id"])
    _ensure_index(inspector, "detected_duplicates", "idx_duplicates_similarity", ["similarity_score"])

    # Steering interventions audit
    if not _table_exists(inspector, "steering_interventions"):
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
        )
        inspector = sa.inspect(bind)

    _ensure_index(inspector, "steering_interventions", "idx_steering_agent_created", ["agent_id", "created_at"])
    _ensure_index(inspector, "steering_interventions", "idx_steering_type", ["steering_type"])
    _ensure_index(inspector, "steering_interventions", "idx_steering_actor_type", ["actor_type"])

    # Monitoring vectors for semantic similarity (PGVector)
    if not _table_exists(inspector, "monitoring_vectors"):
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
        )
        inspector = sa.inspect(bind)

    _ensure_index(inspector, "monitoring_vectors", "idx_monitoring_vectors_entity", ["entity_type", "entity_id"])
    _ensure_index(
        inspector,
        "monitoring_vectors",
        "idx_monitoring_vectors_embedding",
        ["embedding"],
        postgresql_using="gin",
    )

    # Monitoring audit log (compliance trail)
    if not _table_exists(inspector, "monitoring_audit_log"):
        op.create_table(
            "monitoring_audit_log",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("actor_type", sa.String(length=32), nullable=False),
            sa.Column("actor_id", sa.String(length=255), nullable=True),
            sa.Column("target_agent_ids", postgresql.ARRAY(sa.String()), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)

    _ensure_index(inspector, "monitoring_audit_log", "idx_monitoring_audit_created", ["created_at"])
    _ensure_index(inspector, "monitoring_audit_log", "idx_monitoring_audit_event_type", ["event_type"])

    # Monitoring metadata on tasks for diagnostics
    if not _column_exists(inspector, "tasks", "monitoring_notes"):
        op.add_column("tasks", sa.Column("monitoring_notes", sa.Text(), nullable=True))
        inspector = sa.inspect(bind)
    if not _column_exists(inspector, "tasks", "discovery_impact"):
        op.add_column("tasks", sa.Column("discovery_impact", sa.String(length=32), nullable=True))
        inspector = sa.inspect(bind)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _column_exists(inspector, "tasks", "discovery_impact"):
        op.drop_column("tasks", "discovery_impact")
        inspector = sa.inspect(bind)
    if _column_exists(inspector, "tasks", "monitoring_notes"):
        op.drop_column("tasks", "monitoring_notes")
        inspector = sa.inspect(bind)

    for table in (
        "monitoring_audit_log",
        "monitoring_vectors",
        "steering_interventions",
        "detected_duplicates",
        "guardian_analyses",
        "conductor_analyses",
    ):
        inspector = sa.inspect(bind)
        if _table_exists(inspector, table):
            op.drop_table(table)
