"""Add credential bindings and access logs tables.

Revision ID: 064_add_credential_bindings
Revises: 063_add_artifacts
Create Date: 2025-04-23

This migration:
1. Creates the credential_bindings table for encrypted credential storage
2. Creates the credential_access_logs table for audit trails
3. Adds indexes for workspace queries and unique constraints
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "064_add_credential_bindings"
down_revision: Union[str, None] = "063_add_artifacts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create credential bindings and access logs tables."""
    # Create credential_bindings table
    op.create_table(
        "credential_bindings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "kind",
            sa.String(32),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "encrypted_value",
            sa.Text,
            nullable=False,
        ),
        sa.Column(
            "config",
            postgresql.JSONB(),
            nullable=True,
            server_default="{}",
        ),
        sa.Column(
            "version",
            sa.Integer,
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "rotated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "kind",
            "name",
            name="uq_credential_binding_workspace_kind_name",
        ),
        comment="Encrypted credentials bound to workspaces",
    )

    # Create indexes for credential_bindings
    op.create_index(
        "idx_credential_bindings_workspace",
        "credential_bindings",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "idx_credential_bindings_kind",
        "credential_bindings",
        ["kind", "workspace_id"],
    )

    # Create credential_access_logs table
    op.create_table(
        "credential_access_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "credential_binding_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "action",
            sa.String(32),
            nullable=False,
        ),
        sa.Column(
            "actor",
            sa.String(255),
            nullable=True,
        ),
        sa.Column(
            "accessed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "access_metadata",
            postgresql.JSONB(),
            nullable=True,
            server_default="{}",
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Audit log for credential access operations",
    )

    # Create indexes for credential_access_logs
    op.create_index(
        "idx_credential_access_logs_workspace",
        "credential_access_logs",
        ["workspace_id", "accessed_at"],
    )
    op.create_index(
        "idx_credential_access_logs_binding",
        "credential_access_logs",
        ["credential_binding_id", "accessed_at"],
    )
    op.create_index(
        "idx_credential_access_logs_actor",
        "credential_access_logs",
        ["actor", "accessed_at"],
    )


def downgrade() -> None:
    """Drop credential bindings and access logs tables."""
    # Drop indexes first (reverse order)
    op.drop_index(
        "idx_credential_access_logs_actor", table_name="credential_access_logs"
    )
    op.drop_index(
        "idx_credential_access_logs_binding", table_name="credential_access_logs"
    )
    op.drop_index(
        "idx_credential_access_logs_workspace", table_name="credential_access_logs"
    )
    op.drop_table("credential_access_logs")

    op.drop_index("idx_credential_bindings_kind", table_name="credential_bindings")
    op.drop_index("idx_credential_bindings_workspace", table_name="credential_bindings")
    op.drop_table("credential_bindings")
