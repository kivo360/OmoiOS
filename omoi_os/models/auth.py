"""Authentication models for sessions and API keys."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.user import User
    from omoi_os.models.agent import Agent


class Session(Base):
    """User session for web/mobile authentication."""

    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Token data
    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="SHA-256 hash of session token"
    )

    # Client info
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Expiration
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")

    __table_args__ = (
        Index("idx_sessions_user", "user_id"),
        Index("idx_sessions_token_hash", "token_hash"),
        Index("idx_sessions_expires", "expires_at"),
        {"comment": "User sessions for web/mobile clients"}
    )


class APIKey(Base):
    """API key for programmatic access (users and agents)."""

    __tablename__ = "api_keys"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    # Owner (user OR agent, enforced by CHECK constraint)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    agent_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="VARCHAR to match agents.id type"
    )

    organization_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True
    )

    # Key data
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User-defined label for the key"
    )
    key_prefix: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        index=True,
        comment="First 8-16 chars for identification (e.g., 'sk_live_abc')"
    )
    hashed_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="SHA-256 hash of full API key"
    )
    scopes: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Permission scopes for this key"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        back_populates="api_keys",
        foreign_keys=[user_id]
    )
    agent: Mapped[Optional["Agent"]] = relationship(
        back_populates="api_keys",
        foreign_keys=[agent_id]
    )

    __table_args__ = (
        CheckConstraint(
            '(user_id IS NOT NULL AND agent_id IS NULL) OR '
            '(user_id IS NULL AND agent_id IS NOT NULL)',
            name='check_key_user_or_agent'
        ),
        Index("idx_api_keys_user", "user_id",
              postgresql_where=text("user_id IS NOT NULL")),
        Index("idx_api_keys_agent", "agent_id",
              postgresql_where=text("agent_id IS NOT NULL")),
        Index("idx_api_keys_prefix", "key_prefix"),
        Index("idx_api_keys_hash", "hashed_key"),
        Index("idx_api_keys_active", "is_active",
              postgresql_where=text("is_active = true")),
        {"comment": "API keys for programmatic access"}
    )

