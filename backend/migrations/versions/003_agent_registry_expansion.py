"""Agent registry expansion

Revision ID: 003_agent_registry
Revises: 002_phase1
Create Date: 2025-11-16

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_agent_registry"
down_revision: Union[str, None] = "002_phase1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Replace JSONB capabilities with text array
    op.drop_column("agents", "capabilities")
    op.add_column(
        "agents",
        sa.Column(
            "capabilities",
            postgresql.ARRAY(sa.String(length=100)),
            nullable=False,
            server_default="{}",
        ),
    )
    op.alter_column("agents", "capabilities", server_default=None)

    # Add capacity, health_status, and tags metadata
    op.add_column(
        "agents",
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "agents",
        sa.Column(
            "health_status",
            sa.String(length=50),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.add_column(
        "agents",
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String(length=50)),
            nullable=True,
        ),
    )
    op.alter_column("agents", "capacity", server_default=None)
    op.alter_column("agents", "health_status", server_default=None)

    # Indexes to accelerate capability/tag searches
    op.create_index(
        "ix_agents_health_status", "agents", ["health_status"], unique=False
    )
    op.create_index(
        "idx_agents_capabilities",
        "agents",
        ["capabilities"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "idx_agents_tags",
        "agents",
        ["tags"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("idx_agents_tags", table_name="agents")
    op.drop_index("idx_agents_capabilities", table_name="agents")
    op.drop_index("ix_agents_health_status", table_name="agents")

    op.drop_column("agents", "tags")
    op.drop_column("agents", "health_status")
    op.drop_column("agents", "capacity")
    op.drop_column("agents", "capabilities")

    op.add_column(
        "agents",
        sa.Column(
            "capabilities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
