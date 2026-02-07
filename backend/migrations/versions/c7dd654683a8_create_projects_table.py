"""create_projects_table

Revision ID: c7dd654683a8
Revises: 6c0ccdad63c9
Create Date: 2025-12-09 22:18:06.099360

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c7dd654683a8"
down_revision: Union[str, Sequence[str], None] = "6c0ccdad63c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create projects table."""
    op.create_table(
        "projects",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("github_owner", sa.String(255), nullable=True),
        sa.Column("github_repo", sa.String(255), nullable=True),
        sa.Column("github_webhook_secret", sa.String(255), nullable=True),
        sa.Column(
            "github_connected", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "default_phase_id",
            sa.String(50),
            nullable=False,
            server_default="PHASE_BACKLOG",
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="Projects organize tickets and tasks into logical groups",
    )
    op.create_index("ix_projects_name", "projects", ["name"])
    op.create_index("ix_projects_status", "projects", ["status"])
    op.create_index("ix_projects_organization_id", "projects", ["organization_id"])
    op.create_index("ix_projects_created_by", "projects", ["created_by"])
    op.create_index("ix_projects_created_at", "projects", ["created_at"])


def downgrade() -> None:
    """Drop projects table."""
    op.drop_index("ix_projects_created_at", table_name="projects")
    op.drop_index("ix_projects_created_by", table_name="projects")
    op.drop_index("ix_projects_organization_id", table_name="projects")
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_index("ix_projects_name", table_name="projects")
    op.drop_table("projects")
