"""Dynamic Task Scoring (REQ-TQM-PRI-002, REQ-TQM-PRI-003, REQ-TQM-DM-001)

Revision ID: 014_dynamic_task_scoring
Revises: 013_ticket_state_machine
Create Date: 2025-01-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "014_dynamic_task_scoring"
down_revision: Union[str, None] = "013_ticket_state_machine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add score field to tasks table (REQ-TQM-PRI-002)
    op.add_column(
        "tasks",
        sa.Column(
            "score",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.0"),
            comment="Dynamic scheduling score computed from priority, age, deadline, blocker count, and retry penalty (REQ-TQM-PRI-002)",
        ),
    )
    op.create_index(op.f("ix_tasks_score"), "tasks", ["score"], unique=False)

    # Add deadline_at field to tasks table (REQ-TQM-PRI-003, REQ-TQM-DM-001)
    op.add_column(
        "tasks",
        sa.Column(
            "deadline_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Optional SLA deadline for this task (REQ-TQM-PRI-003)",
        ),
    )
    op.create_index(
        op.f("ix_tasks_deadline_at"), "tasks", ["deadline_at"], unique=False
    )

    # Add parent_task_id field to tasks table (REQ-TQM-DM-001)
    op.add_column(
        "tasks",
        sa.Column(
            "parent_task_id",
            sa.String(),
            nullable=True,
            comment="Parent task ID for branching and sub-tasks (REQ-TQM-DM-001)",
        ),
    )
    op.create_index(
        op.f("ix_tasks_parent_task_id"), "tasks", ["parent_task_id"], unique=False
    )
    op.create_foreign_key(
        op.f("fk_tasks_parent_task_id_tasks"),
        "tasks",
        "tasks",
        ["parent_task_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Remove foreign key constraint
    op.drop_constraint(
        op.f("fk_tasks_parent_task_id_tasks"), "tasks", type_="foreignkey"
    )

    # Remove indexes
    op.drop_index(op.f("ix_tasks_parent_task_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_deadline_at"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_score"), table_name="tasks")

    # Remove columns
    op.drop_column("tasks", "parent_task_id")
    op.drop_column("tasks", "deadline_at")
    op.drop_column("tasks", "score")
