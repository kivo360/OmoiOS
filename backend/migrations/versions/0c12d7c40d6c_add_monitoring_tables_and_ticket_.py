"""add monitoring tables and ticket project column

Revision ID: 0c12d7c40d6c
Revises: 0c38fc9dec4b
Create Date: 2025-11-21 08:51:53.130991

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from migration_utils import (
    safe_create_table,
    safe_create_index,
    safe_drop_index,
    safe_drop_table,
    safe_add_column,
    safe_drop_column,
    safe_create_foreign_key,
    safe_drop_constraint,
    print_migration_summary,
)

# revision identifiers, used by Alembic.
revision: str = "0c12d7c40d6c"
down_revision: Union[str, Sequence[str], None] = "0c38fc9dec4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    print("\n🔄 Starting monitoring/ticket linkage migration...")
    print_migration_summary()

    # 1. Ensure conductor_analyses exists for monitoring loop
    print("\n📊 Ensuring conductor_analyses table exists...")
    safe_create_table(
        "conductor_analyses",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("cycle_id", sa.UUID(), nullable=False),
        sa.Column("coherence_score", sa.Float(), nullable=False),
        sa.Column("system_status", sa.String(length=32), nullable=False),
        sa.Column("num_agents", sa.Integer(), nullable=False),
        sa.Column(
            "duplicate_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "termination_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "coordination_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        comment="System-wide conductor analyses for intelligent monitoring coherence snapshots",
    )
    safe_create_index(
        "idx_conductor_analyses_created", "conductor_analyses", ["created_at"]
    )
    safe_create_index(
        "idx_conductor_analyses_coherence", "conductor_analyses", ["coherence_score"]
    )
    safe_create_index(
        "idx_conductor_analyses_status", "conductor_analyses", ["system_status"]
    )

    # 2. Add tickets.project_id linkage if missing
    print("\n🧩 Ensuring tickets.project_id exists...")
    safe_add_column(
        "tickets",
        sa.Column(
            "project_id",
            sa.String(),
            nullable=True,
            comment="Optional link to projects table",
        ),
    )
    safe_create_foreign_key(
        "fk_tickets_project",
        "tickets",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    safe_create_index("idx_tickets_project_id", "tickets", ["project_id"])

    print("\n✅ Monitoring/ticket linkage migration completed!")
    print_migration_summary()


def downgrade() -> None:
    """Downgrade schema."""
    print("\n🔄 Rolling back monitoring/ticket linkage migration...")

    print("\n🧩 Dropping tickets.project_id linkage...")
    safe_drop_index("idx_tickets_project_id", "tickets")
    safe_drop_constraint("fk_tickets_project", "tickets", type_="foreignkey")
    safe_drop_column("tickets", "project_id")

    print("\n📊 Dropping conductor_analyses artifacts...")
    safe_drop_index("idx_conductor_analyses_status", "conductor_analyses")
    safe_drop_index("idx_conductor_analyses_coherence", "conductor_analyses")
    safe_drop_index("idx_conductor_analyses_created", "conductor_analyses")
    safe_drop_table("conductor_analyses")

    print("\n✅ Rollback completed!")
    print_migration_summary()
