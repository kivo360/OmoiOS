"""merge heads 069+072+egress

Revision ID: a531fd3140dc
Revises: 069_add_sandbox_sessions, 072_environment_version_ports_and_volume, f8543c803e5f
Create Date: 2026-04-24 08:47:26.722017

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "a531fd3140dc"
down_revision: Union[str, Sequence[str], None] = (
    "069_add_sandbox_sessions",
    "072_environment_version_ports_and_volume",
    "f8543c803e5f",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
