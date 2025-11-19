"""Organization models for multi-tenancy."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.user import User
    from omoi_os.models.agent import Agent
    from omoi_os.models.project import Project


class Organization(Base):
    """Organization for multi-tenant resource isolation."""

    __tablename__ = "organizations"

    # Identity
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Ownership
    owner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # Settings
    billing_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    org_attributes: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="ABAC attributes for organization-level policies"
    )

    # Resource Limits
    max_concurrent_agents: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_agent_runtime_hours: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now
    )

    # Relationships
    owner: Mapped["User"] = relationship(
        back_populates="owned_organizations",
        foreign_keys=[owner_id]
    )
    memberships: Mapped[list["OrganizationMembership"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    roles: Mapped[list["Role"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    projects: Mapped[list["Project"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        {"comment": "Organizations for multi-tenant resource isolation"}
    )


class OrganizationMembership(Base):
    """Join table for organization members (users and agents)."""

    __tablename__ = "organization_memberships"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    # Member (user OR agent, enforced by CHECK constraint)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    agent_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id"),
        nullable=False
    )

    # Audit
    invited_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        back_populates="memberships",
        foreign_keys=[user_id]
    )
    agent: Mapped[Optional["Agent"]] = relationship(
        back_populates="memberships",
        foreign_keys=[agent_id]
    )
    organization: Mapped["Organization"] = relationship(
        back_populates="memberships"
    )
    role: Mapped["Role"] = relationship()

    __table_args__ = (
        CheckConstraint(
            '(user_id IS NOT NULL AND agent_id IS NULL) OR '
            '(user_id IS NULL AND agent_id IS NOT NULL)',
            name='check_user_or_agent'
        ),
        Index("idx_user_org", "user_id", "organization_id",
              unique=True,
              postgresql_where=text("user_id IS NOT NULL")),
        Index("idx_agent_org", "agent_id", "organization_id",
              unique=True,
              postgresql_where=text("agent_id IS NOT NULL")),
        {"comment": "Organization membership for users and agents"}
    )


class Role(Base):
    """Role for RBAC permissions."""

    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    organization_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        comment="NULL for system roles, set for custom org roles"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    permissions: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Array of permission strings (e.g., ['org:read', 'project:*'])"
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True for predefined system roles"
    )

    # Role inheritance
    inherits_from: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship(
        back_populates="roles"
    )
    parent_role: Mapped[Optional["Role"]] = relationship(
        remote_side=[id],
        backref="child_roles"
    )

    __table_args__ = (
        Index("idx_org_role_name", "organization_id", "name", unique=True),
        Index("idx_roles_inherits", "inherits_from"),
        {"comment": "Roles for RBAC permission management"}
    )

