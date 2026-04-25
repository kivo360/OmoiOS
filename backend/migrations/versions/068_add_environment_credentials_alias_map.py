"""Add credentials alias-map column to environment_versions.

Adds a JSONB column to store credential alias mappings per environment version.
The credentials map allows binding named credentials (e.g., "anthropic", "github")
to actual credential binding IDs without storing secrets directly.

Structure: {"alias": {"kind": "bearer_secret|github_app|...", "binding_id": "uuid"}}

Revision ID: 068_add_environment_credentials_alias_map
Revises: 067_add_workspaces
Create Date: 2026-04-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "068_add_environment_credentials_alias_map"
down_revision: Union[str, None] = "067_add_workspaces"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add credentials column to environment_versions table."""
    inspector = sa.inspect(op.get_bind())
    columns = [col["name"] for col in inspector.get_columns("environment_versions")]

    if "credentials" in columns:
        return

    op.add_column(
        "environment_versions",
        sa.Column(
            "credentials",
            postgresql.JSONB(),
            nullable=True,
            server_default="{}",
            comment="Credential alias map: {alias: {kind, binding_id}}",
        ),
    )


def downgrade() -> None:
    """Remove credentials column from environment_versions table."""
    inspector = sa.inspect(op.get_bind())
    columns = [col["name"] for col in inspector.get_columns("environment_versions")]

    if "credentials" not in columns:
        return

    op.drop_column("environment_versions", "credentials")
