"""User credentials model for storing external API keys.

This model stores API keys for external services (Anthropic, OpenAI, etc.)
that users can provide to use their own accounts instead of the system default.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.user import User


class UserCredential(Base):
    """Stores external API credentials for users.

    This allows users to provide their own API keys for services like:
    - Anthropic (Claude)
    - OpenAI
    - Z.AI or other Anthropic-compatible providers

    The credentials are stored encrypted and can have custom configuration
    like base URLs for proxy services.
    """

    __tablename__ = "user_credentials"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    # User relationship
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Provider identification
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Service provider: anthropic, openai, z_ai, etc.",
    )

    # Credential name (optional, for display)
    name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="User-friendly name for this credential",
    )

    # API credentials
    # NOTE: In production, these should be encrypted at rest
    api_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The API key or token",
    )

    # Optional configuration
    base_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Custom base URL (for proxies like Z.AI)",
    )

    model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Default model to use with this credential",
    )

    # Extended configuration as JSON
    config_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Additional provider-specific configuration",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is the default credential for this provider",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationship
    user: Mapped["User"] = relationship(
        back_populates="credentials",
        foreign_keys=[user_id],
    )

    __table_args__ = (
        # Unique constraint: one default per user per provider
        Index(
            "idx_user_credentials_default",
            "user_id",
            "provider",
            unique=True,
            postgresql_where=text("is_default = true"),
        ),
        # Index for lookups
        Index("idx_user_credentials_user_provider", "user_id", "provider"),
        Index(
            "idx_user_credentials_active",
            "user_id",
            "is_active",
            postgresql_where=text("is_active = true"),
        ),
        {"comment": "User credentials for external API services"},
    )

    def __repr__(self) -> str:
        return (
            f"<UserCredential(id={self.id}, user_id={self.user_id}, "
            f"provider={self.provider}, name={self.name})>"
        )
