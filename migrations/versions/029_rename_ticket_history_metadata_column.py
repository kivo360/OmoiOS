"""Rename ticket_history.metadata to metadata_json.

Revision ID: 029_rename_ticket_history_metadata_column
Revises: 028_add_persistence_dir_to_tasks
Create Date: 2025-11-20
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "029_rename_ticket_history_metadata_column"
down_revision: Union[str, None] = "028_add_persistence_dir_to_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename ticket_history.metadata to metadata_json."""
    op.alter_column(
        "ticket_history",
        "metadata",
        new_column_name="metadata_json",
        existing_type=postgresql.JSONB(),
    )


def downgrade() -> None:
    """Revert ticket_history.metadata_json back to metadata."""
    op.alter_column(
        "ticket_history",
        "metadata_json",
        new_column_name="metadata",
        existing_type=postgresql.JSONB(),
    )
