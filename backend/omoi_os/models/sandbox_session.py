"""Sandbox session model for workspace-scoped session tokens.

Each sandbox session binds a session token to a specific workspace
and environment version. Tokens are stored as SHA-256 hashes —
the plaintext is returned to the caller exactly once at creation.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    pass


class SandboxSession(Base):
    """Stores hashed session tokens for sandbox workspace access.

    The plaintext token is never stored. Only the SHA-256 hash and
    an 8-character prefix (for log-friendly identification) are persisted.
    """

    __tablename__ = "sandbox_sessions"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # SHA-256 hash of the session token (64 hex chars)
    session_token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="SHA-256 hash of the session token",
    )

    # First 8 chars of the plaintext token for log-friendly display
    session_token_prefix: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="First 8 characters of the token for identification in logs",
    )

    # Workspace FK
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Workspace this session grants access to",
    )

    # Environment version FK
    environment_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("environment_versions.id"),
        nullable=False,
        index=True,
        comment="Environment version pinned for this session",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("now()"),
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Session expiry timestamp",
    )

    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Revocation timestamp (null if active)",
    )

    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Last time this session token was verified",
    )

    __table_args__ = (
        Index(
            "idx_sandbox_sessions_workspace",
            "workspace_id",
            "expires_at",
        ),
        Index(
            "idx_sandbox_sessions_env_version",
            "environment_version_id",
        ),
        {"comment": "Scoped session tokens for sandbox workspace access"},
    )

    def __repr__(self) -> str:
        return (
            f"<SandboxSession(id={self.id}, "
            f"prefix={self.session_token_prefix}..., "
            f"workspace_id={self.workspace_id})>"
        )
