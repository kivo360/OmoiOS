"""Merge Guardian and MCP branches

Revision ID: 020_merge_guardian_and_mcp
Revises: 006_guardian, 019_mcp_server_integration
Create Date: 2025-01-30

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "020_merge_guardian_and_mcp"
down_revision: Union[str, Sequence[str], None] = (
    "006_guardian",
    "019_mcp_server_integration",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge migration - no schema changes, just resolves branch heads."""
    pass


def downgrade() -> None:
    """Merge migration - no schema changes."""
    pass
