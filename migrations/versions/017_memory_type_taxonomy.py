"""Memory Type Taxonomy (REQ-MEM-TAX-001, REQ-MEM-TAX-002)

Revision ID: 017_memory_type_taxonomy
Revises: 016_ticket_human_approval
Create Date: 2025-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "017_memory_type_taxonomy"
down_revision: Union[str, None] = "016_ticket_human_approval"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add memory_type column to task_memories table (REQ-MEM-TAX-001, REQ-MEM-TAX-002)
    op.add_column(
        "task_memories",
        sa.Column(
            "memory_type",
            sa.String(50),
            nullable=False,
            server_default="discovery",
            comment="Memory type: error_fix, discovery, decision, learning, warning, codebase_knowledge (REQ-MEM-TAX-001)",
        ),
    )
    op.create_index(
        op.f("ix_task_memories_memory_type"), "task_memories", ["memory_type"], unique=False
    )

    # Add check constraint to enforce valid memory types (REQ-MEM-TAX-002)
    op.create_check_constraint(
        op.f("ck_task_memories_valid_memory_type"),
        "task_memories",
        sa.text(
            "memory_type IN ('error_fix', 'discovery', 'decision', 'learning', 'warning', 'codebase_knowledge')"
        ),
    )


def downgrade() -> None:
    # Remove check constraint
    op.drop_constraint(
        op.f("ck_task_memories_valid_memory_type"), "task_memories", type_="check"
    )

    # Remove index
    op.drop_index(op.f("ix_task_memories_memory_type"), table_name="task_memories")

    # Remove memory_type column
    op.drop_column("task_memories", "memory_type")

