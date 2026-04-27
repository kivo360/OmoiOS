"""Add encrypted_value column to user_credentials table.

Revision ID: 061_add_encrypted_api_key
Revises: 060_add_spec_share_fields
Create Date: 2025-01-15

This migration:
1. Adds encrypted_value column to store encrypted API keys
2. Keeps existing api_key column for migration period
3. Backfills encrypted_value for existing credentials (if encryption key available)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "061_add_encrypted_api_key"
down_revision: Union[str, None] = "060_add_spec_share_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add encrypted_value column to user_credentials table."""
    # Add encrypted_value column (nullable initially for migration)
    op.add_column(
        "user_credentials",
        sa.Column(
            "encrypted_value",
            sa.Text(),
            nullable=True,
            comment="Encrypted API key (Fernet AES-256-GCM)",
        ),
    )

    # Add index for lookups
    op.create_index(
        "idx_user_credentials_encrypted",
        "user_credentials",
        ["encrypted_value"],
        postgresql_where=sa.text("encrypted_value IS NOT NULL"),
    )

    # Note: Backfill of existing credentials happens in application layer
    # via CredentialsService when credentials are accessed.
    # This avoids requiring encryption key during migration.


def downgrade() -> None:
    """Remove encrypted_value column."""
    op.drop_index("idx_user_credentials_encrypted", table_name="user_credentials")
    op.drop_column("user_credentials", "encrypted_value")
