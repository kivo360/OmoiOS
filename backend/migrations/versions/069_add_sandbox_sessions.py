"""Add sandbox_sessions table and FK on credential_access_logs.

Creates the sandbox_sessions table for workspace-scoped session tokens.
Adds a nullable sandbox_session_id foreign key to credential_access_logs
so audit entries can reference the session that triggered the access.

Revision ID: 069_add_sandbox_sessions
Revises: 068_add_environment_credentials_alias_map
Create Date: 2026-04-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "069_add_sandbox_sessions"
down_revision: Union[str, None] = "068_add_environment_credentials_alias_map"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sandbox_sessions table and add FK to credential_access_logs."""
    inspector = sa.inspect(op.get_bind())

    # --- sandbox_sessions table ---
    if "sandbox_sessions" not in inspector.get_table_names():
        op.create_table(
            "sandbox_sessions",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column(
                "session_token_hash",
                sa.String(64),
                nullable=False,
                comment="SHA-256 hash of the session token",
            ),
            sa.Column(
                "session_token_prefix",
                sa.String(16),
                nullable=False,
                comment="First 8 characters of the token for identification in logs",
            ),
            sa.Column(
                "workspace_id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
                comment="Workspace this session grants access to",
            ),
            sa.Column(
                "environment_version_id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
                comment="Environment version pinned for this session",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "expires_at",
                sa.DateTime(timezone=True),
                nullable=False,
                comment="Session expiry timestamp",
            ),
            sa.Column(
                "revoked_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="Revocation timestamp (null if active)",
            ),
            sa.Column(
                "last_used_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="Last time this session token was verified",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("session_token_hash"),
            sa.ForeignKeyConstraint(
                ["workspace_id"],
                ["workspaces.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["environment_version_id"],
                ["environment_versions.id"],
            ),
            comment="Scoped session tokens for sandbox workspace access",
        )
        op.create_index(
            "idx_sandbox_sessions_workspace",
            "sandbox_sessions",
            ["workspace_id", "expires_at"],
        )
        op.create_index(
            "idx_sandbox_sessions_env_version",
            "sandbox_sessions",
            ["environment_version_id"],
        )

    # --- Add sandbox_session_id FK to credential_access_logs ---
    cal_columns = {c["name"] for c in inspector.get_columns("credential_access_logs")}
    if "sandbox_session_id" not in cal_columns:
        op.add_column(
            "credential_access_logs",
            sa.Column(
                "sandbox_session_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
                comment="Sandbox session that triggered this access (nullable)",
            ),
        )
        op.create_foreign_key(
            "fk_credential_access_logs_sandbox_session",
            "credential_access_logs",
            "sandbox_sessions",
            ["sandbox_session_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(
            "idx_credential_access_logs_sandbox_session",
            "credential_access_logs",
            ["sandbox_session_id"],
        )


def downgrade() -> None:
    """Remove FK from credential_access_logs and drop sandbox_sessions."""
    inspector = sa.inspect(op.get_bind())

    cal_columns = {c["name"] for c in inspector.get_columns("credential_access_logs")}
    if "sandbox_session_id" in cal_columns:
        op.drop_index(
            "idx_credential_access_logs_sandbox_session",
            table_name="credential_access_logs",
        )
        op.drop_constraint(
            "fk_credential_access_logs_sandbox_session",
            "credential_access_logs",
            type_="foreignkey",
        )
        op.drop_column("credential_access_logs", "sandbox_session_id")

    if "sandbox_sessions" in inspector.get_table_names():
        op.drop_index(
            "idx_sandbox_sessions_env_version",
            table_name="sandbox_sessions",
        )
        op.drop_index(
            "idx_sandbox_sessions_workspace",
            table_name="sandbox_sessions",
        )
        op.drop_table("sandbox_sessions")
