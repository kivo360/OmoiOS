"""Phase workflow extensions for Stream G.

Revision ID: 003_phase_workflow
Revises: 002_phase1
Create Date: 2025-11-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "003_phase_workflow"
down_revision: Union[str, None] = "002_phase1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply phase gate artifacts and results tables."""
    op.create_table(
        "phase_gate_artifacts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("ticket_id", sa.String(), nullable=False),
        sa.Column("phase_id", sa.String(length=50), nullable=False),
        sa.Column("artifact_type", sa.String(length=100), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.Column(
            "artifact_content",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_by", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_gate_artifacts_ticket_phase",
        "phase_gate_artifacts",
        ["ticket_id", "phase_id"],
    )

    op.create_table(
        "phase_gate_results",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("ticket_id", sa.String(), nullable=False),
        sa.Column("phase_id", sa.String(length=50), nullable=False),
        sa.Column("gate_status", sa.String(length=50), nullable=False),
        sa.Column(
            "validation_result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validated_by", sa.String(length=255), nullable=True),
        sa.Column(
            "blocking_reasons",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_gate_results_ticket_phase",
        "phase_gate_results",
        ["ticket_id", "phase_id"],
    )


def downgrade() -> None:
    """Drop phase gate tables."""
    op.drop_index("idx_gate_results_ticket_phase", table_name="phase_gate_results")
    op.drop_table("phase_gate_results")
    op.drop_index("idx_gate_artifacts_ticket_phase", table_name="phase_gate_artifacts")
    op.drop_table("phase_gate_artifacts")
