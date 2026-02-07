"""Anomaly detection system (REQ-FT-AN-001, REQ-FT-AN-002)

Revision ID: 012_anomaly_detection
Revises: 011_enhanced_heartbeat
Create Date: 2025-01-27

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "012_anomaly_detection"
down_revision: Union[str, None] = "011_enhanced_heartbeat"
branch_labels: Union[str, Sequence[str]] = None
depends_on: Union[str, Sequence[str]] = None


def upgrade() -> None:
    # Add anomaly_score and consecutive_anomalous_readings to agents table (REQ-FT-AN-001)
    op.add_column(
        "agents",
        sa.Column(
            "anomaly_score",
            sa.Float(),
            nullable=True,
            index=True,
            comment="Composite anomaly score (0-1) from latency, error rate, resource skew, queue impact",
        ),
    )
    op.add_column(
        "agents",
        sa.Column(
            "consecutive_anomalous_readings",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Count of consecutive readings with anomaly_score >= threshold",
        ),
    )

    # Create agent_baselines table (REQ-FT-AN-002)
    op.create_table(
        "agent_baselines",
        sa.Column(
            "id",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "agent_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "phase_id",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "latency_ms",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.0"),
            comment="Baseline latency in milliseconds",
        ),
        sa.Column(
            "latency_std",
            sa.Float(),
            nullable=False,
            server_default=sa.text("1.0"),
            comment="Standard deviation of latency",
        ),
        sa.Column(
            "error_rate",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.0"),
            comment="Baseline error rate (0-1)",
        ),
        sa.Column(
            "cpu_usage_percent",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.0"),
            comment="Baseline CPU usage percentage",
        ),
        sa.Column(
            "memory_usage_mb",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.0"),
            comment="Baseline memory usage in MB",
        ),
        sa.Column(
            "additional_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Additional baseline metrics",
        ),
        sa.Column(
            "sample_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Number of samples used to compute baseline",
        ),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_baselines_agent_type"),
        "agent_baselines",
        ["agent_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_baselines_phase_id"),
        "agent_baselines",
        ["phase_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_baselines_last_updated"),
        "agent_baselines",
        ["last_updated"],
        unique=False,
    )


def downgrade() -> None:
    # Drop agent_baselines table
    op.drop_index(op.f("ix_agent_baselines_last_updated"), table_name="agent_baselines")
    op.drop_index(op.f("ix_agent_baselines_phase_id"), table_name="agent_baselines")
    op.drop_index(op.f("ix_agent_baselines_agent_type"), table_name="agent_baselines")
    op.drop_table("agent_baselines")

    # Remove anomaly detection fields from agents table
    op.drop_column("agents", "consecutive_anomalous_readings")
    op.drop_column("agents", "anomaly_score")
