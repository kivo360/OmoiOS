"""Credential access log model for audit trail.

This model tracks all access to credentials for security auditing.
Each create, read, delete, and inject operation is logged with
actor information and timestamps.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    pass


class CredentialAccessLog(Base):
    """Stores audit log entries for credential access.

    Tracks all operations on credentials for security auditing:
    - create: New credential created
    - read: Credential metadata accessed
    - delete: Credential deleted
    - inject: Credential value injected into sandbox

    Note: credential_binding_id is nullable to support logging
    list operations (which access multiple credentials).
    """

    __tablename__ = "credential_access_logs"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # Credential reference (nullable for list operations)
    credential_binding_id: Mapped[Optional[UUID]] = mapped_column(
        nullable=True,
        index=True,
        comment="Credential binding ID (null for list operations)",
    )

    # Sandbox session reference (nullable for user/admin operations)
    sandbox_session_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("sandbox_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Sandbox session that triggered this access (nullable)",
    )

    # Workspace reference
    workspace_id: Mapped[UUID] = mapped_column(
        nullable=False,
        index=True,
        comment="Workspace ID for scoping",
    )

    # Action type
    action: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Action: create, read, delete, inject",
    )

    # Actor (user ID or agent ID, nullable if unavailable)
    actor: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User ID or agent ID who performed the action",
    )

    # Access timestamp
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    # Additional metadata (NOT 'metadata' - reserved SQLAlchemy word)
    access_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        server_default="{}",
        comment="Additional metadata about the access",
    )

    __table_args__ = (
        # Index for workspace audit queries
        Index(
            "idx_credential_access_logs_workspace",
            "workspace_id",
            "accessed_at",
        ),
        # Index for credential-specific audit queries
        Index(
            "idx_credential_access_logs_binding",
            "credential_binding_id",
            "accessed_at",
        ),
        # Index for sandbox-session audit queries
        Index(
            "idx_credential_access_logs_sandbox_session",
            "sandbox_session_id",
        ),
        # Index for actor audit queries
        Index(
            "idx_credential_access_logs_actor",
            "actor",
            "accessed_at",
        ),
        {"comment": "Audit log for credential access operations"},
    )

    def __repr__(self) -> str:
        return (
            f"<CredentialAccessLog(id={self.id}, "
            f"credential_binding_id={self.credential_binding_id}, "
            f"action={self.action}, actor={self.actor})>"
        )
