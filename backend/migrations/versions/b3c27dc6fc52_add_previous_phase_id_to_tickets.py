"""Add previous_phase_id to tickets table.

Revision ID: b3c27dc6fc52
Revises: 0c12d7c40d6c
Create Date: 2025-11-21 10:56:37.119276

This migration adds the missing previous_phase_id column to the tickets table.
The column tracks the previous phase when a ticket transitions between phases.
"""

from typing import Sequence, Union

import sqlalchemy as sa

# Import migration utilities
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from migration_utils import (
    safe_add_column,
    safe_create_index,
    safe_drop_index,
    safe_drop_column,
)


# revision identifiers, used by Alembic.
revision: str = "b3c27dc6fc52"
down_revision: Union[str, Sequence[str], None] = "0c12d7c40d6c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add previous_phase_id column to tickets table."""
    # Add previous_phase_id column to tickets table
    safe_add_column(
        "tickets",
        sa.Column(
            "previous_phase_id",
            sa.String(length=50),
            nullable=True,
            comment="Previous phase ID when ticket transitions between phases",
        ),
    )
    # Create index on previous_phase_id for efficient queries
    safe_create_index(
        "ix_tickets_previous_phase_id",
        "tickets",
        ["previous_phase_id"],
    )


def downgrade() -> None:
    """Remove previous_phase_id column from tickets table."""
    safe_drop_index("ix_tickets_previous_phase_id", "tickets")
    safe_drop_column("tickets", "previous_phase_id")
