"""create_user_onboarding_table

Revision ID: 046_create_user_onboarding
Revises: 045_add_dependencies_to_tickets
Create Date: 2025-01-09

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "046_create_user_onboarding"
down_revision: Union[str, Sequence[str], None] = "045_add_dependencies_to_tickets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_onboarding table."""
    op.create_table(
        "user_onboarding",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "current_step", sa.String(50), nullable=False, server_default="welcome"
        ),
        sa.Column(
            "completed_steps",
            postgresql.ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "completed_checklist_items",
            postgresql.ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "onboarding_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("sync_version", sa.Integer, nullable=False, server_default="1"),
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
    )

    # Create indexes
    op.create_index("idx_user_onboarding_user_id", "user_onboarding", ["user_id"])
    op.create_index(
        "idx_user_onboarding_completed",
        "user_onboarding",
        ["completed_at"],
        postgresql_where=sa.text("completed_at IS NOT NULL"),
    )


def downgrade() -> None:
    """Drop user_onboarding table."""
    op.drop_index("idx_user_onboarding_completed", table_name="user_onboarding")
    op.drop_index("idx_user_onboarding_user_id", table_name="user_onboarding")
    op.drop_table("user_onboarding")
