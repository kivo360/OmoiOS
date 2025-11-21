"""Enhanced heartbeat protocol (REQ-ALM-002, REQ-FT-HB-003)

Revision ID: 011_enhanced_heartbeat
Revises: 010_validation_system
Create Date: 2025-01-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "011_enhanced_heartbeat"
down_revision: Union[str, None] = "010_validation_system"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enhanced heartbeat protocol fields (REQ-ALM-002, REQ-FT-HB-003)
    op.add_column(
        "agents",
        sa.Column(
            "sequence_number",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Monotonically increasing sequence number for heartbeat",
        ),
    )
    op.add_column(
        "agents",
        sa.Column(
            "last_expected_sequence",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Last expected sequence number (for gap detection)",
        ),
    )
    op.add_column(
        "agents",
        sa.Column(
            "consecutive_missed_heartbeats",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Count of consecutive missed heartbeats (for escalation ladder)",
        ),
    )


def downgrade() -> None:
    # Remove enhanced heartbeat protocol fields
    op.drop_column("agents", "consecutive_missed_heartbeats")
    op.drop_column("agents", "last_expected_sequence")
    op.drop_column("agents", "sequence_number")

