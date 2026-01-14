"""add_spec_pr_tracking_fields

Revision ID: 053_add_spec_pr_tracking_fields
Revises: 052_add_spec_id_to_sandbox_events
Create Date: 2025-01-14

Adds GitHub/PR tracking fields to specs table for auto PR creation
after spec completion.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "053_add_spec_pr_tracking_fields"
down_revision: Union[str, Sequence[str], None] = "052_add_spec_id_to_sandbox_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add PR tracking fields to specs table."""
    # Add branch_name column
    op.add_column(
        "specs",
        sa.Column(
            "branch_name",
            sa.String(255),
            nullable=True,
            comment="Git branch name for this spec (e.g., spec/abc123-feature-name)",
        ),
    )

    # Add pull_request_url column
    op.add_column(
        "specs",
        sa.Column(
            "pull_request_url",
            sa.String(500),
            nullable=True,
            comment="GitHub PR URL after spec completion",
        ),
    )

    # Add pull_request_number column
    op.add_column(
        "specs",
        sa.Column(
            "pull_request_number",
            sa.Integer(),
            nullable=True,
            comment="GitHub PR number for tracking",
        ),
    )


def downgrade() -> None:
    """Remove PR tracking fields from specs table."""
    op.drop_column("specs", "pull_request_number")
    op.drop_column("specs", "pull_request_url")
    op.drop_column("specs", "branch_name")
