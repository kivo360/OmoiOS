"""add egress to environment_versions

Revision ID: f8543c803e5f
Revises: 070_session_envelope_and_acls
Create Date: 2026-04-24 03:18:46.673345

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f8543c803e5f"
down_revision: Union[str, Sequence[str], None] = "070_session_envelope_and_acls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add egress JSONB column to environment_versions."""
    op.add_column(
        "environment_versions",
        sa.Column(
            "egress",
            sa.dialects.postgresql.JSONB(),
            nullable=True,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    """Drop egress column from environment_versions."""
    op.drop_column("environment_versions", "egress")
