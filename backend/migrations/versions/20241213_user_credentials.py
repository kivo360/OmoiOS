"""Add user_credentials table for external API keys.

Revision ID: user_credentials_001
Revises:
Create Date: 2024-12-13

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "user_credentials_001"
down_revision: Union[str, None] = None  # Set to latest migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_credentials",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "provider",
            sa.String(50),
            nullable=False,
            comment="Service provider: anthropic, openai, z_ai, etc.",
        ),
        sa.Column(
            "name",
            sa.String(100),
            nullable=True,
            comment="User-friendly name for this credential",
        ),
        sa.Column("api_key", sa.Text(), nullable=False, comment="The API key or token"),
        sa.Column(
            "base_url",
            sa.String(500),
            nullable=True,
            comment="Custom base URL (for proxies like Z.AI)",
        ),
        sa.Column(
            "model",
            sa.String(100),
            nullable=True,
            comment="Default model to use with this credential",
        ),
        sa.Column(
            "config_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Additional provider-specific configuration",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="Whether this is the default credential for this provider",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        comment="User credentials for external API services",
    )

    # Indexes
    op.create_index(
        "idx_user_credentials_user_provider",
        "user_credentials",
        ["user_id", "provider"],
    )
    op.create_index(
        "idx_user_credentials_default",
        "user_credentials",
        ["user_id", "provider"],
        unique=True,
        postgresql_where=sa.text("is_default = true"),
    )
    op.create_index(
        "idx_user_credentials_active",
        "user_credentials",
        ["user_id", "is_active"],
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index("idx_user_credentials_active", table_name="user_credentials")
    op.drop_index("idx_user_credentials_default", table_name="user_credentials")
    op.drop_index("idx_user_credentials_user_provider", table_name="user_credentials")
    op.drop_table("user_credentials")
