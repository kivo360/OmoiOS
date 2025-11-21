"""Add tsvector column for hybrid search (REQ-MEM-SEARCH-001)

Revision ID: 024_add_tsvector_for_hybrid_search
Revises: 023_agent_registration_enhancements
Create Date: 2025-01-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "024_add_tsvector_for_hybrid_search"
down_revision: Union[str, None] = "023_agent_registration_enhancements"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    # Add tsvector column for full-text search (REQ-MEM-SEARCH-001)
    # This is a generated column that combines execution_summary, goal, result, and feedback
    op.execute("""
        ALTER TABLE task_memories
        ADD COLUMN content_tsv tsvector
        GENERATED ALWAYS AS (
            to_tsvector('english',
                coalesce(execution_summary, '') || ' ' ||
                coalesce(goal, '') || ' ' ||
                coalesce(result, '') || ' ' ||
                coalesce(feedback, '')
            )
        ) STORED;
    """)
    
    # Create GIN index for fast full-text search
    op.create_index(
        "ix_task_memories_content_tsv",
        "task_memories",
        ["content_tsv"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    # Drop index
    op.drop_index("ix_task_memories_content_tsv", table_name="task_memories", postgresql_using="gin")
    
    # Drop tsvector column
    op.drop_column("task_memories", "content_tsv")

