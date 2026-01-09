"""User model for authentication and authorization."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.organization import Organization, OrganizationMembership
    from omoi_os.models.auth import Session, APIKey
    from omoi_os.models.user_credentials import UserCredential
    from omoi_os.models.user_onboarding import UserOnboarding


class User(Base):
    """User model for authentication and multi-tenant organizations."""

    __tablename__ = "users"

    # Identity
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(
        "name", String(255), nullable=True
    )  # DB column: name
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_super_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )

    # ABAC Attributes
    department: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    attributes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Waitlist
    waitlist_status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )  # 'pending', 'approved', 'none'
    waitlist_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Relationships
    memberships: Mapped[list["OrganizationMembership"]] = relationship(
        back_populates="user",
        foreign_keys="OrganizationMembership.user_id",
        cascade="all, delete-orphan",
    )
    owned_organizations: Mapped[list["Organization"]] = relationship(
        back_populates="owner", foreign_keys="Organization.owner_id"
    )
    api_keys: Mapped[list["APIKey"]] = relationship(
        back_populates="user",
        foreign_keys="APIKey.user_id",
        cascade="all, delete-orphan",
    )
    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    credentials: Mapped[list["UserCredential"]] = relationship(
        back_populates="user",
        foreign_keys="UserCredential.user_id",
        cascade="all, delete-orphan",
    )
    onboarding: Mapped[Optional["UserOnboarding"]] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    # Note: spawned_agents relationship not included due to Agent.id type mismatch
    # (Agent.id is VARCHAR, need UUID for FK relationship)

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_department", "department"),
        Index(
            "idx_users_is_super_admin",
            "is_super_admin",
            postgresql_where=text("is_super_admin = true"),
        ),
        Index("idx_users_deleted_at", "deleted_at"),
    )
