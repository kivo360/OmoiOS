"""add conductor analyses and ticket project column

Revision ID: 0c38fc9dec4b
Revises: 031_workspace_isolation_system
Create Date: 2025-11-21 08:40:12.008181

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "0c38fc9dec4b"
down_revision: Union[str, Sequence[str], None] = "031_workspace_isolation_system"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
