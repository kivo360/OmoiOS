# Authentication System Implementation Plan

**Status**: Draft  
**Created**: 2025-11-19  
**Priority**: P0 (Foundation)

## Overview

Comprehensive implementation plan for building the authentication and authorization system from scratch using SQLAlchemy. This replaces the Supabase approach with a fully self-hosted solution.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend Layer                        │
│  Login, Register, OAuth, Dashboard, Agent Terminal          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                     │
│  Auth Endpoints, OAuth, GitHub, Agent Management             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Auth Service │  │ OAuth Service│  │ GitHub Service│     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │Authorization │  │ Agent Service│  │ Streaming    │     │
│  │  Service     │  │              │  │  Service     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   Database Layer (PostgreSQL)                │
│  Users, Organizations, Roles, Policies, Agents, Projects    │
└─────────────────────────────────────────────────────────────┘
```

## Phase 0: Foundation (Week 1)

### Step 1: Update User Model

Modify existing `omoi_os/models/user.py`:

```python
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from omoi_os.models.organization import Organization, OrganizationMembership
    from omoi_os.models.auth import Session, APIKey
    from omoi_os.models.project import Project
    from omoi_os.models.ticket import Ticket

class User(Base):
    __tablename__ = "users"
    
    # Identity
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    
    # ABAC Attributes
    department: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    attributes: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
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
        cascade="all, delete-orphan"
    )
    owned_organizations: Mapped[list["Organization"]] = relationship(
        back_populates="owner"
    )
    api_keys: Mapped[list["APIKey"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
```

### Step 2: Create New Models

**File**: `omoi_os/models/organization.py`

```python
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4
from datetime import datetime

if TYPE_CHECKING:
    from omoi_os.models.user import User
    from omoi_os.models.agent import Agent
    from omoi_os.models.project import Project
    from omoi_os.models.policy import Policy

class Organization(Base):
    __tablename__ = "organizations"
    
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Ownership
    owner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id")
    )
    
    # Settings
    billing_email: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSONB)
    attributes: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Resource Limits (for agents)
    max_concurrent_agents: Mapped[int] = mapped_column(Integer, default=5)
    max_agent_runtime_hours: Mapped[float] = mapped_column(Float, default=100.0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    
    # Relationships
    owner: Mapped["User"] = relationship(back_populates="owned_organizations")
    memberships: Mapped[list["OrganizationMembership"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    roles: Mapped[list["Role"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    policies: Mapped[list["Policy"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    projects: Mapped[list["Project"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )

class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    
    # Member (user OR agent, enforced by CHECK constraint)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    agent_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        index=True
    )
    
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    role_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("roles.id")
    )
    
    # Audit
    invited_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id")
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship(back_populates="memberships")
    agent: Mapped[Optional["Agent"]] = relationship(back_populates="memberships")
    organization: Mapped["Organization"] = relationship(back_populates="memberships")
    role: Mapped["Role"] = relationship()
    
    __table_args__ = (
        CheckConstraint(
            '(user_id IS NOT NULL AND agent_id IS NULL) OR '
            '(user_id IS NULL AND agent_id IS NOT NULL)',
            name='check_user_or_agent'
        ),
        Index("idx_user_org", "user_id", "organization_id", unique=True,
              postgresql_where=text("user_id IS NOT NULL")),
        Index("idx_agent_org", "agent_id", "organization_id", unique=True,
              postgresql_where=text("agent_id IS NOT NULL")),
    )

class Role(Base):
    __tablename__ = "roles"
    
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    permissions: Mapped[list[str]] = mapped_column(JSONB)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Role inheritance
    inherits_from: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="SET NULL")
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
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
    )
```

**File**: `omoi_os/models/auth.py`

```python
# Session and APIKey models
class Session(Base):
    __tablename__ = "sessions"
    
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    
    # Owner (user OR agent)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    agent_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        index=True
    )
    
    organization_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    
    # Key Data
    name: Mapped[str] = mapped_column(String(255))
    key_prefix: Mapped[str] = mapped_column(String(16), index=True)
    hashed_key: Mapped[str] = mapped_column(String(255), unique=True)
    scopes: Mapped[list[str]] = mapped_column(JSONB)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship(back_populates="api_keys")
    agent: Mapped[Optional["Agent"]] = relationship(back_populates="api_keys")
    
    __table_args__ = (
        CheckConstraint(
            '(user_id IS NOT NULL AND agent_id IS NULL) OR '
            '(user_id IS NULL AND agent_id IS NOT NULL)',
            name='check_key_user_or_agent'
        ),
    )
```

### Step 3: Create Migration

**File**: `migrations/versions/030_auth_system_foundation.py`

```python
"""Auth system foundation: organizations, roles, sessions, api keys

Revision ID: 030_auth_system_foundation
Revises: 029_xxx
Create Date: 2025-11-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime

# revision identifiers
revision = '030_auth_system_foundation'
down_revision = '029_xxx'  # Update with latest migration
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Modify users table
    op.add_column('users', sa.Column('hashed_password', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('full_name', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('is_verified', sa.Boolean, default=False))
    op.add_column('users', sa.Column('is_super_admin', sa.Boolean, default=False))
    op.add_column('users', sa.Column('department', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('attributes', postgresql.JSONB, nullable=True))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))
    
    # Rename existing fields
    op.alter_column('users', 'name', new_column_name='full_name_temp')
    op.alter_column('users', 'user_metadata', new_column_name='attributes_temp')
    op.alter_column('users', 'last_sign_in_at', new_column_name='last_login_at_temp')
    
    # Copy data
    op.execute("UPDATE users SET full_name = full_name_temp WHERE full_name_temp IS NOT NULL")
    op.execute("UPDATE users SET attributes = attributes_temp WHERE attributes_temp IS NOT NULL")
    op.execute("UPDATE users SET last_login_at = last_login_at_temp WHERE last_login_at_temp IS NOT NULL")
    op.execute("UPDATE users SET is_verified = (email_confirmed_at IS NOT NULL)")
    
    # Drop temp columns
    op.drop_column('users', 'full_name_temp')
    op.drop_column('users', 'attributes_temp')
    op.drop_column('users', 'last_login_at_temp')
    
    # Add indexes
    op.create_index('idx_users_department', 'users', ['department'])
    op.create_index('idx_users_is_super_admin', 'users', ['is_super_admin'], 
                    postgresql_where=sa.text('is_super_admin = true'))
    
    # 2. Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('billing_email', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('settings', postgresql.JSONB, nullable=True),
        sa.Column('attributes', postgresql.JSONB, nullable=True),
        sa.Column('max_concurrent_agents', sa.Integer, default=5),
        sa.Column('max_agent_runtime_hours', sa.Float, default=100.0),
        sa.Column('created_at', sa.DateTime(timezone=True), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=datetime.utcnow,
                  onupdate=datetime.utcnow),
    )
    
    op.create_index('idx_organizations_owner', 'organizations', ['owner_id'])
    
    # 3. Create roles table
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('permissions', postgresql.JSONB, nullable=False),
        sa.Column('is_system', sa.Boolean, default=False),
        sa.Column('inherits_from', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('roles.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), default=datetime.utcnow),
    )
    
    op.create_index('idx_org_role_name', 'roles', 
                    ['organization_id', 'name'], unique=True)
    op.create_index('idx_roles_inherits', 'roles', ['inherits_from'])
    
    # 4. Create organization_memberships table
    op.create_table(
        'organization_memberships',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id', ondelete='CASCADE'), 
                  nullable=False, index=True),
        sa.Column('role_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('roles.id'), nullable=False),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=datetime.utcnow,
                  onupdate=datetime.utcnow),
        sa.CheckConstraint(
            '(user_id IS NOT NULL AND agent_id IS NULL) OR '
            '(user_id IS NULL AND agent_id IS NOT NULL)',
            name='check_user_or_agent'
        ),
    )
    
    op.create_index('idx_user_org', 'organization_memberships', 
                    ['user_id', 'organization_id'], unique=True,
                    postgresql_where=sa.text("user_id IS NOT NULL"))
    op.create_index('idx_agent_org', 'organization_memberships',
                    ['agent_id', 'organization_id'], unique=True,
                    postgresql_where=sa.text("agent_id IS NOT NULL"))
    
    # 5. Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), 
                  nullable=False, index=True),
        sa.Column('token_hash', sa.String(255), unique=True, index=True, nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), default=datetime.utcnow),
    )
    
    # 6. Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('key_prefix', sa.String(16), index=True, nullable=False),
        sa.Column('hashed_key', sa.String(255), unique=True, nullable=False),
        sa.Column('scopes', postgresql.JSONB, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), default=datetime.utcnow),
        sa.CheckConstraint(
            '(user_id IS NOT NULL AND agent_id IS NULL) OR '
            '(user_id IS NULL AND agent_id IS NOT NULL)',
            name='check_key_user_or_agent'
        ),
    )
    
    op.create_index('idx_api_keys_user', 'api_keys', ['user_id'],
                    postgresql_where=sa.text("user_id IS NOT NULL"))
    op.create_index('idx_api_keys_agent', 'api_keys', ['agent_id'],
                    postgresql_where=sa.text("agent_id IS NOT NULL"))
    
    # 7. Seed system roles
    op.execute("""
        INSERT INTO roles (id, name, description, permissions, is_system, organization_id)
        VALUES 
            (gen_random_uuid(), 'owner', 'Organization owner with full control',
             '["org:*", "project:*", "document:*", "ticket:*", "task:*", "agent:*"]'::jsonb,
             true, NULL),
            (gen_random_uuid(), 'admin', 'Administrator with management permissions',
             '["org:read", "org:write", "org:members:*", "project:*", "document:*", "ticket:*", "task:*", "agent:read"]'::jsonb,
             true, NULL),
            (gen_random_uuid(), 'member', 'Standard organization member',
             '["org:read", "project:read", "project:write", "document:read", "document:write", "ticket:read", "ticket:write", "task:read", "task:write", "agent:read"]'::jsonb,
             true, NULL),
            (gen_random_uuid(), 'viewer', 'Read-only access',
             '["org:read", "project:read", "document:read", "ticket:read", "task:read", "agent:read"]'::jsonb,
             true, NULL),
            (gen_random_uuid(), 'agent_executor', 'Role for AI agents',
             '["project:read", "document:read", "document:write", "ticket:read", "ticket:write", "task:read", "task:write", "task:complete:execute", "project:git:write"]'::jsonb,
             true, NULL)
        ON CONFLICT DO NOTHING
    """)

def downgrade() -> None:
    op.drop_table('api_keys')
    op.drop_table('sessions')
    op.drop_table('organization_memberships')
    op.drop_table('roles')
    op.drop_table('organizations')
    
    # Revert user changes
    op.drop_column('users', 'hashed_password')
    op.drop_column('users', 'is_verified')
    op.drop_column('users', 'is_super_admin')
    op.drop_column('users', 'department')
    op.drop_column('users', 'attributes')
    op.drop_column('users', 'last_login_at')
```

### Step 4: Create Auth Service

**File**: `omoi_os/services/auth_service.py`

```python
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID
import secrets
import hashlib

from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr

from omoi_os.models.user import User
from omoi_os.models.auth import Session, APIKey
from omoi_os.models.organization import Organization, OrganizationMembership, Role
from omoi_os.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    """Authentication service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return pwd_context.hash(password)
    
    def verify_password(self, plain: str, hashed: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(plain, hashed)
    
    def create_access_token(
        self,
        user_id: UUID,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        payload = {
            "sub": str(user_id),
            "exp": expire,
            "type": "access"
        }
        
        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
    
    def create_refresh_token(self, user_id: UUID) -> str:
        """Create JWT refresh token."""
        expire = datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        
        payload = {
            "sub": str(user_id),
            "exp": expire,
            "type": "refresh"
        }
        
        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
    
    async def register_user(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None
    ) -> User:
        """Register a new user."""
        # Check if user exists
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")
        
        # Create user
        user = User(
            email=email,
            hashed_password=self.hash_password(password),
            full_name=full_name,
            is_verified=False,
            is_active=True
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def authenticate_user(
        self,
        email: str,
        password: str
    ) -> Optional[User]:
        """Authenticate user by email and password."""
        result = await self.db.execute(
            select(User).where(User.email == email, User.is_active == True)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        if not self.verify_password(password, user.hashed_password):
            return None
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        await self.db.commit()
        
        return user
```

### Step 5: Create API Endpoints

**File**: `omoi_os/api/routes/auth.py` (update existing)

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from omoi_os.services.database import get_db
from omoi_os.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

@router.post("/register", response_model=dict)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user."""
    auth_service = AuthService(db)
    
    try:
        user = await auth_service.register_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name
        )
        
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name
        }
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Login user."""
    auth_service = AuthService(db)
    
    user = await auth_service.authenticate_user(
        email=request.email,
        password=request.password
    )
    
    if not user:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid credentials"
        )
    
    # Create tokens
    access_token = auth_service.create_access_token(user.id)
    refresh_token = auth_service.create_refresh_token(user.id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
```

---

## Implementation Order

### Day 1-2: Database Models
1. Update User model
2. Create Organization, OrganizationMembership, Role models
3. Create Session, APIKey models
4. Create and run migration 030

### Day 3-4: Auth Service
1. Password hashing service
2. JWT token service
3. User registration
4. User authentication
5. Session management

### Day 5-6: Organization API
1. Create organization endpoint
2. List organizations
3. Invite members
4. Manage roles
5. Permission middleware

### Day 7: Testing
1. Unit tests for auth service
2. Integration tests for full flow
3. API endpoint tests

---

## Next Phases Preview

### Phase 1: Agent Support
- Agent model with OpenHands integration
- Agent spawning and lifecycle
- Task assignment to agents
- Agent execution logging

### Phase 2: ABAC System
- Policy model
- Policy evaluation engine
- Advanced authorization

### Phase 3: OAuth
- Provider configuration
- OAuth flow implementation
- Token management

### Phase 4: GitHub App
- Installation handling
- Repository operations
- Webhook processing

---

## Security Considerations

### Password Security
- Minimum 8 characters
- Require: uppercase, lowercase, digit
- Use bcrypt with cost factor 12
- Never log passwords
- Rate limit login attempts

### Token Security
- Short-lived access tokens (15min)
- Refresh tokens stored hashed
- Rotate refresh tokens on use
- Invalidate on logout
- HTTPS only in production

### API Key Security
- Hash full keys (SHA-256)
- Store only prefix in plaintext
- Scope limitation
- Expiration support
- Revocation support

### Authorization Security
- Check permissions on every request
- Cache authorization decisions (5min max)
- Audit all permission changes
- Explicit deny overrides allow

