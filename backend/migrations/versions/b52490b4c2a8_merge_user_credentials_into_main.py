"""merge_user_credentials_into_main

Revision ID: b52490b4c2a8
Revises: 036_task_sandbox_id, user_credentials_001
Create Date: 2025-12-13 13:57:39.857107

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "b52490b4c2a8"
down_revision: Union[str, Sequence[str], None] = (
    "036_task_sandbox_id",
    "user_credentials_001",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
