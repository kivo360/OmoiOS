"""Monitoring and observability tables (Phase 4)

Revision ID: 005_monitoring
Revises: 004_collab_locks
Create Date: 2025-11-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005_monitoring"
down_revision: Union[str, None] = "004_collab_locks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Monitor anomalies table
    op.create_table(
        "monitor_anomalies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("metric_name", sa.String(), nullable=False),
        sa.Column("anomaly_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("baseline_value", sa.Float(), nullable=False),
        sa.Column("observed_value", sa.Float(), nullable=False),
        sa.Column("deviation_percent", sa.Float(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_monitor_anomalies_metric_name", "monitor_anomalies", ["metric_name"])
    op.create_index("ix_monitor_anomalies_severity", "monitor_anomalies", ["severity"])
    op.create_index("ix_monitor_anomalies_detected_at", "monitor_anomalies", ["detected_at"])

    # Alerts table
    op.create_table(
        "alerts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("rule_id", sa.String(), nullable=False),
        sa.Column("metric_name", sa.String(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("current_value", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", sa.String(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_rule_id", "alerts", ["rule_id"])
    op.create_index("ix_alerts_metric_name", "alerts", ["metric_name"])
    op.create_index("ix_alerts_severity", "alerts", ["severity"])
    op.create_index("ix_alerts_triggered_at", "alerts", ["triggered_at"])


def downgrade() -> None:
    op.drop_index("ix_alerts_triggered_at", table_name="alerts")
    op.drop_index("ix_alerts_severity", table_name="alerts")
    op.drop_index("ix_alerts_metric_name", table_name="alerts")
    op.drop_index("ix_alerts_rule_id", table_name="alerts")
    op.drop_table("alerts")

    op.drop_index("ix_monitor_anomalies_detected_at", table_name="monitor_anomalies")
    op.drop_index("ix_monitor_anomalies_severity", table_name="monitor_anomalies")
    op.drop_index("ix_monitor_anomalies_metric_name", table_name="monitor_anomalies")
    op.drop_table("monitor_anomalies")

