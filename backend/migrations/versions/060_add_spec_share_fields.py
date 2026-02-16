"""Add share fields to specs table for viral loop sharing.

Revision ID: 060_add_spec_share_fields
Revises: 059_add_preview_sessions_table
Create Date: 2026-02-16
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "060_add_spec_share_fields"
down_revision = "059_add_preview_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "specs",
        sa.Column(
            "share_token",
            sa.String(32),
            nullable=True,
            unique=True,
            comment="URL-safe token for public showcase page (generated on share)",
        ),
    )
    op.add_column(
        "specs",
        sa.Column(
            "share_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether the spec is publicly viewable via showcase link",
        ),
    )
    op.add_column(
        "specs",
        sa.Column(
            "share_view_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Number of public showcase page views",
        ),
    )
    op.create_index("ix_specs_share_token", "specs", ["share_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_specs_share_token", table_name="specs")
    op.drop_column("specs", "share_view_count")
    op.drop_column("specs", "share_enabled")
    op.drop_column("specs", "share_token")
