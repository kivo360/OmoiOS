"""Add synthesis_context and owned_files to tasks table.

These fields support parallel task coordination:
- synthesis_context: Merged context from parallel predecessor tasks (injected by SynthesisService)
- owned_files: Glob patterns for files this task can modify (for ownership validation)

Revision ID: 057
Revises: 8ecd4525d261
Create Date: 2025-01-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "057_synthesis_ownership"
down_revision: Union[str, None] = "8ecd4525d261"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add synthesis_context and owned_files columns to tasks table."""
    # synthesis_context: Merged context from parallel predecessor tasks
    op.add_column(
        "tasks",
        sa.Column(
            "synthesis_context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Merged context from parallel predecessor tasks (injected by SynthesisService when joins complete)",
        ),
    )

    # owned_files: Glob patterns for files this task can modify
    op.add_column(
        "tasks",
        sa.Column(
            "owned_files",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Glob patterns for files this task can modify (e.g., ['src/services/user/**', 'tests/user/**'])",
        ),
    )


def downgrade() -> None:
    """Remove synthesis_context and owned_files columns."""
    op.drop_column("tasks", "owned_files")
    op.drop_column("tasks", "synthesis_context")
