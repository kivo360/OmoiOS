"""add_spec_context_column

Revision ID: 88c08d730f8c
Revises: 054_add_autonomous_execution_toggle
Create Date: 2026-01-18 10:42:20.357632

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "88c08d730f8c"
down_revision: Union[str, Sequence[str], None] = "054_add_autonomous_execution_toggle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add spec_context JSONB column to specs table."""
    op.add_column(
        "specs",
        sa.Column(
            "spec_context",
            JSONB,
            nullable=False,
            server_default="{}",
            comment="Context metadata: {source_ticket_id, workflow_mode, ...}",
        ),
    )


def downgrade() -> None:
    """Remove spec_context column from specs table."""
    op.drop_column("specs", "spec_context")
