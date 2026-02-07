"""add_title_and_updated_at_to_tasks

Revision ID: 9f4e5dc42483
Revises: 037_claude_session_transcripts
Create Date: 2025-12-19 15:28:15.197412

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "9f4e5dc42483"
down_revision: Union[str, Sequence[str], None] = "037_claude_session_transcripts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add title and updated_at columns to tasks table."""
    # Add title column
    op.add_column(
        "tasks",
        sa.Column(
            "title", sa.String(500), nullable=True, comment="Human-readable task title"
        ),
    )

    # Add updated_at column with default value set to created_at for existing rows
    op.add_column(
        "tasks",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp of last update to this task",
        ),
    )

    # Set updated_at to created_at for existing rows
    op.execute("UPDATE tasks SET updated_at = created_at WHERE updated_at IS NULL")

    # Now make updated_at NOT NULL
    op.alter_column("tasks", "updated_at", nullable=False)


def downgrade() -> None:
    """Remove title and updated_at columns from tasks table."""
    op.drop_column("tasks", "updated_at")
    op.drop_column("tasks", "title")
