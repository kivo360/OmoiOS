"""Add spec_versions table for version history tracking

Revision ID: 047_add_spec_versions
Revises: 046_create_user_onboarding
Create Date: 2025-01-09

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "047_add_spec_versions"
down_revision = "046_create_user_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create spec_versions table for version history tracking."""
    op.create_table(
        "spec_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("spec_id", sa.String(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "change_type",
            sa.String(length=50),
            nullable=False,
            comment="created, updated, requirements_approved, design_approved, phase_changed",
        ),
        sa.Column("change_summary", sa.Text(), nullable=False),
        sa.Column(
            "change_details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Detailed change information: {field: {old, new}}",
        ),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column(
            "snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Snapshot of spec state at this version",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["spec_id"],
            ["specs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_spec_versions_spec_id",
        "spec_versions",
        ["spec_id"],
        unique=False,
    )
    op.create_index(
        "ix_spec_versions_created_at",
        "spec_versions",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop spec_versions table."""
    op.drop_index("ix_spec_versions_created_at", table_name="spec_versions")
    op.drop_index("ix_spec_versions_spec_id", table_name="spec_versions")
    op.drop_table("spec_versions")
