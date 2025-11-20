# Organization and authentication design document

**Created**: 2025-11-20
**Status**: Draft
**Purpose**: Technical design for a multi-tenant organization and authentication system with RBAC and API key management.
**Related**: docs/design/auth/api_key_design.md, docs/design/auth/rbac_design.md, docs/architecture/auth/adr_auth_system.md

---


**Created:** 11/19/2025 12:00:05  
**Updated:** 11/19/2025 12:00:05  
**Exported:** 11/19/2025 12:01:09  
**Link:** [https://claude.ai/share/4d55acad-2a5f-4b49-9db6-967833a5757f](https://claude.ai/share/4d55acad-2a5f-4b49-9db6-967833a5757f)  

## Response:
11/19/2025, 8:08:01 AM

I'll create a comprehensive design document for organization and authentication management using Pydantic 2.12 and SQLAlchemy 2.0.

```markdown:docs/auth-org-design.md
# Organization & Authentication Design Document

## System Overview

A multi-tenant authentication and authorization system supporting hierarchical organizations, role-based access control (RBAC), and API key management using Pydantic 2.12 for validation and SQLAlchemy 2.0 for persistence.

## Core Entities

### 1. User
Primary authentication entity representing individual system users.

**Attributes:**
- `id`: UUID (primary key)
- `email`: Unique, indexed, validated email
- `hashed_password`: bcrypt/argon2 hash
- `full_name`: Optional display name
- `is_active`: Boolean flag for soft deletion
- `is_verified`: Email verification status
- `created_at`: Timestamp
- `updated_at`: Timestamp
- `last_login_at`: Nullable timestamp

**Relationships:**
- Many-to-many with Organizations through OrganizationMembership
- One-to-many with APIKeys
- One-to-many with Sessions

### 2. Organization
Multi-tenant boundary for resource isolation.

**Attributes:**
- `id`: UUID (primary key)
- `name`: Organization display name
- `slug`: URL-safe unique identifier
- `owner_id`: UUID (foreign key to User)
- `billing_email`: Optional separate billing contact
- `is_active`: Boolean flag
- `settings`: JSONB field for org-level configuration
- `created_at`: Timestamp
- `updated_at`: Timestamp

**Relationships:**
- Many-to-one with User (owner)
- Many-to-many with Users through OrganizationMembership
- One-to-many with Projects/Resources (domain-specific)

### 3. OrganizationMembership
Join table with additional role information.

**Attributes:**
- `id`: UUID (primary key)
- `user_id`: UUID (foreign key, indexed)
- `organization_id`: UUID (foreign key, indexed)
- `role_id`: UUID (foreign key to Role)
- `invited_by`: UUID (nullable, tracks who added this member)
- `joined_at`: Timestamp
- `updated_at`: Timestamp

**Composite Unique Constraint:** (user_id, organization_id)

### 4. Role
Defines permission sets within an organization.

**Attributes:**
- `id`: UUID (primary key)
- `organization_id`: UUID (foreign key, nullable for system roles)
- `name`: Role name (e.g., "admin", "member", "viewer")
- `description`: Human-readable purpose
- `permissions`: JSONB array of permission strings
- `is_system`: Boolean (true for predefined roles)
- `created_at`: Timestamp

**System Roles:**
- `owner`: Full control, cannot be removed
- `admin`: Manage members, resources, billing
- `member`: Standard access to org resources
- `viewer`: Read-only access

### 5. APIKey
Long-lived authentication tokens for programmatic access.

**Attributes:**
- `id`: UUID (primary key)
- `user_id`: UUID (foreign key)
- `organization_id`: UUID (foreign key, nullable)
- `name`: User-defined label
- `key_prefix`: First 8 chars for identification (e.g., "sk_live_")
- `hashed_key`: Full key hash for verification
- `scopes`: JSONB array of permission scopes
- `last_used_at`: Nullable timestamp
- `expires_at`: Nullable timestamp
- `is_active`: Boolean flag
- `created_at`: Timestamp

**Key Format:** `sk_{env}_{random_32_chars}`

### 6. Session
Short-lived authentication for web/mobile clients.

**Attributes:**
- `id`: UUID (primary key)
- `user_id`: UUID (foreign key)
- `token_hash`: Session token hash
- `ip_address`: Client IP (nullable)
- `user_agent`: Client identifier (nullable)
- `expires_at`: Timestamp
- `created_at`: Timestamp

## SQLAlchemy 2.0 Models

### Base Configuration

```python
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    type_annotation_map = {
        UUID: PGUUID(as_uuid=True),
        datetime: DateTime(timezone=True),
    }

def generate_uuid() -> UUID:
    return uuid4()
```

### User Model

```python
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), 
        onupdate=func.now()
    )
    last_login_at: Mapped[Optional[datetime]]
    
    # Relationships
    memberships: Mapped[List["OrganizationMembership"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    owned_organizations: Mapped[List["Organization"]] = relationship(
        back_populates="owner"
    )
    api_keys: Mapped[List["APIKey"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    sessions: Mapped[List["Session"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
```

### Organization Model

```python
class Organization(Base):
    __tablename__ = "organizations"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    billing_email: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    owner: Mapped["User"] = relationship(back_populates="owned_organizations")
    memberships: Mapped[List["OrganizationMembership"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    roles: Mapped[List["Role"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
```

### OrganizationMembership Model

```python
class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        Index("idx_user_org", "user_id", "organization_id", unique=True),
    )
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=generate_uuid)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id"))
    invited_by: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"))
    joined_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        back_populates="memberships",
        foreign_keys=[user_id]
    )
    organization: Mapped["Organization"] = relationship(back_populates="memberships")
    role: Mapped["Role"] = relationship()
```

### Role Model

```python
class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (
        Index("idx_org_role_name", "organization_id", "name", unique=True),
    )
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=generate_uuid)
    organization_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    permissions: Mapped[List[str]] = mapped_column(JSONB)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship(
        back_populates="roles"
    )
```

### APIKey Model

```python
class APIKey(Base):
    __tablename__ = "api_keys"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=generate_uuid)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    organization_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(255))
    key_prefix: Mapped[str] = mapped_column(String(16), index=True)
    hashed_key: Mapped[str] = mapped_column(String(255), unique=True)
    scopes: Mapped[List[str]] = mapped_column(JSONB)
    last_used_at: Mapped[Optional[datetime]]
    expires_at: Mapped[Optional[datetime]]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="api_keys")
```

### Session Model

```python
class Session(Base):
    __tablename__ = "sessions"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=generate_uuid)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    expires_at: Mapped[datetime]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")
```

## Pydantic 2.12 Schemas

### Base Configuration

```python
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from datetime import datetime
from uuid import UUID
from typing import Optional, List

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

### User Schemas

```python
class UserBase(BaseSchema):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        return v

class UserUpdate(BaseSchema):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)

class UserResponse(UserBase):
    id: UUID
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

class UserWithOrganizations(UserResponse):
    organizations: List["OrganizationSummary"] = []
```

### Organization Schemas

```python
class OrganizationBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., pattern=r'^[a-z0-9-]+$', max_length=255)
    billing_email: Optional[EmailStr] = None

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    billing_email: Optional[EmailStr] = None
    settings: Optional[dict] = None

class OrganizationResponse(OrganizationBase):
    id: UUID
    owner_id: UUID
    is_active: bool
    created_at: datetime

class OrganizationSummary(BaseSchema):
    id: UUID
    name: str
    slug: str
    role: str  # Current user's role in this org

class OrganizationWithMembers(OrganizationResponse):
    members: List["MembershipResponse"] = []
```

### Membership Schemas

```python
class MembershipCreate(BaseSchema):
    user_id: UUID
    role_id: UUID

class MembershipUpdate(BaseSchema):
    role_id: UUID

class MembershipResponse(BaseSchema):
    id: UUID
    user_id: UUID
    organization_id: UUID
    role_id: UUID
    joined_at: datetime
    user: Optional[UserResponse] = None
    role: Optional["RoleResponse"] = None
```

### Role Schemas

```python
class RoleBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)

class RoleCreate(RoleBase):
    organization_id: Optional[UUID] = None

class RoleUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: Optional[List[str]] = None

class RoleResponse(RoleBase):
    id: UUID
    organization_id: Optional[UUID]
    is_system: bool
    created_at: datetime
```

### API Key Schemas

```python
class APIKeyCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    organization_id: Optional[UUID] = None
    scopes: List[str] = Field(default_factory=list)
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)

class APIKeyResponse(BaseSchema):
    id: UUID
    name: str
    key_prefix: str
    scopes: List[str]
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime

class APIKeyWithSecret(APIKeyResponse):
    key: str  # Only returned once during creation
```

### Authentication Schemas

```python
class LoginRequest(BaseSchema):
    email: EmailStr
    password: str

class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class RefreshTokenRequest(BaseSchema):
    refresh_token: str
```

## Permission System

### Permission Naming Convention
Format: `{resource}:{action}` or `{resource}:{subresource}:{action}`

Examples:
- `org:read`, `org:write`, `org:delete`
- `org:members:read`, `org:members:write`, `org:members:delete`
- `org:billing:read`, `org:billing:write`
- `project:read`, `project:write`, `project:delete`

### System Role Permissions

```python
SYSTEM_PERMISSIONS = {
    "owner": [
        "org:*",  # Wildcard: all org permissions
        "project:*",
    ],
    "admin": [
        "org:read",
        "org:write",
        "org:members:read",
        "org:members:write",
        "org:members:delete",
        "org:billing:read",
        "org:billing:write",
        "project:*",
    ],
    "member": [
        "org:read",
        "org:members:read",
        "project:read",
        "project:write",
    ],
    "viewer": [
        "org:read",
        "org:members:read",
        "project:read",
    ],
}
```

### Permission Checker

```python
from typing import Set

def has_permission(
    user_permissions: List[str],
    required_permission: str
) -> bool:
    """Check if user has required permission (supports wildcards)."""
    permission_set = set(user_permissions)
    
    # Direct match
    if required_permission in permission_set:
        return True
    
    # Wildcard match
    parts = required_permission.split(":")
    for i in range(len(parts)):
        wildcard = ":".join(parts[:i+1]) + ":*"
        if wildcard in permission_set:
            return True
    
    return False
```

## Authentication Flow

### 1. Registration
```
POST /api/auth/register
Body: UserCreate
→ Create User (is_verified=false)
→ Send verification email
→ Return UserResponse (without tokens)
```

### 2. Email Verification
```
GET /api/auth/verify?token={jwt_token}
→ Validate token
→ Set is_verified=true
→ Return success message
```

### 3. Login
```
POST /api/auth/login
Body: LoginRequest
→ Verify credentials
→ Create Session
→ Return TokenResponse (access + refresh)
```

### 4. Token Refresh
```
POST /api/auth/refresh
Body: RefreshTokenRequest
→ Validate refresh token
→ Issue new access token
→ Return TokenResponse
```

### 5. API Key Authentication
```
Header: Authorization: Bearer sk_live_{key}
→ Extract and hash key
→ Lookup APIKey by hash
→ Validate expiration and is_active
→ Load user and permissions
→ Update last_used_at
```

## Authorization Middleware

```python
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

async def require_permission(
    permission: str,
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Dependency to enforce permission checks."""
    membership = await db.execute(
        select(OrganizationMembership)
        .where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.organization_id == organization_id
        )
        .options(selectinload(OrganizationMembership.role))
    )
    membership = membership.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )
    
    if not has_permission(membership.role.permissions, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required permission: {permission}"
        )
    
    return membership
```

## Database Indexes

```sql
-- Users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active) WHERE is_active = true;

-- Organizations
CREATE INDEX idx_organizations_slug ON organizations(slug);
CREATE INDEX idx_organizations_owner_id ON organizations(owner_id);

-- Memberships
CREATE UNIQUE INDEX idx_user_org ON organization_memberships(user_id, organization_id);
CREATE INDEX idx_memberships_org_id ON organization_memberships(organization_id);

-- Roles
CREATE UNIQUE INDEX idx_org_role_name ON roles(organization_id, name);

-- API Keys
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);
CREATE UNIQUE INDEX idx_api_keys_hash ON api_keys(hashed_key);

-- Sessions
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_token_hash ON sessions(token_hash);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
```

## Security Considerations

1. **Password Hashing**: Use bcrypt or Argon2id with appropriate work factors
2. **API Key Storage**: Hash full keys; store only prefix in plaintext
3. **Session Management**: Implement token rotation, short expiration (15m access, 7d refresh)
4. **Rate Limiting**: Apply to auth endpoints (5 attempts/15min for login)
5. **CORS**: Whitelist specific origins in production
6. **SQL Injection**: SQLAlchemy ORM protects; avoid raw SQL
7. **Audit Logging**: Track permission changes, member additions/removals

## Migration Strategy

### Initial System Roles Setup

```python
async def seed_system_roles(db: AsyncSession):
    """Create system roles (run once during deployment)."""
    for role_name, permissions in SYSTEM_PERMISSIONS.items():
        role = Role(
            name=role_name,
            description=f"System {role_name} role",
            permissions=permissions,
            is_system=True,
            organization_id=None  # System roles are org-independent
        )
        db.add(role)
    await db.commit()
```

### Organization Creation Flow

```python
async def create_organization_with_owner(
    org_data: OrganizationCreate,
    owner: User,
    db: AsyncSession
) -> Organization:
    """Create org and assign owner role."""
    # Create organization
    org = Organization(**org_data.model_dump(), owner_id=owner.id)
    db.add(org)
    await db.flush()
    
    # Get system owner role
    owner_role = await db.execute(
        select(Role).where(Role.name == "owner", Role.is_system == True)
    )
    owner_role = owner_role.scalar_one()
    
    # Create membership
    membership = OrganizationMembership(
        user_id=owner.id,
        organization_id=org.id,
        role_id=owner_role.id
    )
    db.add(membership)
    
    await db.commit()
    return org
```

## Next Steps

1. **Implement password reset flow** (forgot password, reset tokens)
2. **Add audit logging table** for tracking security events
3. **Create invitation system** (invite users before they register)
4. **Build permission testing utilities** for integration tests
5. **Add organization transfer** (change owner)

## Questions to Consider

**What's your token storage strategy on the client?** (HttpOnly cookies vs localStorage vs both for mobile/web?)

**Do you need multi-factor authentication?** (TOTP, SMS, hardware keys?)

**What's your org hierarchy model?** (Flat orgs only, or nested teams/projects within orgs?)
```

This design gives you a production-ready foundation with:
- UUID-based identity for distributed systems
- Proper indexing for query performance  
- JSONB for flexible settings/permissions
- Cascade deletes for data integrity
- Pydantic validation with custom rules
- Permission system supporting wildcards

The architecture supports both session-based (web) and API key (programmatic) auth, with clear separation between system roles and custom org roles.

What aspects would you like me to expand on—the FastAPI endpoints implementation, testing strategy, or the invitation workflow?



## Response:
11/19/2025, 8:13:56 AM

I'll update the design document to support a hybrid authentication system combining RBAC (Role-Based Access Control) with ABAC (Attribute-Based Access Control) for fine-grained, context-aware authorization.

```markdown:docs/auth-org-design.md
# Organization & Authentication Design Document

## System Overview

A multi-tenant authentication and authorization system supporting hierarchical organizations with hybrid access control:
- **RBAC (Role-Based Access Control)**: Coarse-grained permissions through roles
- **ABAC (Attribute-Based Access Control)**: Fine-grained, context-aware policies based on user, resource, and environmental attributes
- **ReBAC (Relationship-Based Access Control)**: Permissions derived from relationships between entities

## Core Concepts

### Authorization Models

**RBAC (Role-Based)**
- Users assigned to roles
- Roles have static permission sets
- Good for: org-level permissions, common access patterns
- Example: "admin" role has "org:members:write"

**ABAC (Attribute-Based)**
- Policies evaluated against attributes at runtime
- Attributes from: user, resource, environment, action
- Good for: dynamic constraints, business rules, temporal access
- Example: "Allow edit if user.department == resource.department AND time.hour < 18"

**ReBAC (Relationship-Based)**
- Permissions derived from entity relationships
- Good for: hierarchical data, ownership, team membership
- Example: "Allow delete if user is project.owner OR user in project.admins"

### When to Use Each

| Scenario | Best Model | Example |
|----------|-----------|---------|
| Org membership access | RBAC | Admin can manage all projects |
| Document ownership | ReBAC | Creator can delete their document |
| Time-based access | ABAC | Access training materials only during onboarding period |
| Department restrictions | ABAC | Sales can only view sales leads |
| Team collaboration | ReBAC | Team members can edit team projects |
| Resource quotas | ABAC | User can create projects if quota < 10 |

## Enhanced Entity Model

### 1. User (Enhanced)
**Additional Attributes:**
- `department`: String (for ABAC department-based policies)
- `employee_type`: Enum (full_time, contractor, intern)
- `attributes`: JSONB (custom user attributes for ABAC)
- `metadata`: JSONB (non-policy attributes like preferences)

```python
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    department: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    employee_type: Mapped[Optional[str]] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    attributes: Mapped[Optional[dict]] = mapped_column(JSONB)  # ABAC attributes
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), 
        onupdate=func.now()
    )
    last_login_at: Mapped[Optional[datetime]]
    
    # Relationships
    memberships: Mapped[List["OrganizationMembership"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    owned_organizations: Mapped[List["Organization"]] = relationship(
        back_populates="owner"
    )
    api_keys: Mapped[List["APIKey"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    sessions: Mapped[List["Session"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    resource_grants: Mapped[List["ResourceGrant"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
```

### 2. Organization (Enhanced)
**Additional Attributes:**
- `attributes`: JSONB (org-level attributes for policies)
- `policy_config`: JSONB (org-specific ABAC configuration)

```python
class Organization(Base):
    __tablename__ = "organizations"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    billing_email: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    attributes: Mapped[Optional[dict]] = mapped_column(JSONB)  # ABAC attributes
    settings: Mapped[Optional[dict]] = mapped_column(JSONB)
    policy_config: Mapped[Optional[dict]] = mapped_column(JSONB)  # ABAC rules
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    owner: Mapped["User"] = relationship(back_populates="owned_organizations")
    memberships: Mapped[List["OrganizationMembership"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    roles: Mapped[List["Role"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    policies: Mapped[List["Policy"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    resource_types: Mapped[List["ResourceType"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
```

### 3. Role (Enhanced for RBAC)
**Additional Attributes:**
- `role_type`: Enum (system, custom)
- `inherits_from`: Self-referential foreign key for role hierarchy
- `conditions`: JSONB (optional ABAC conditions to activate role)

```python
class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (
        Index("idx_org_role_name", "organization_id", "name", unique=True),
    )
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=generate_uuid)
    organization_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    permissions: Mapped[List[str]] = mapped_column(JSONB)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    inherits_from: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("roles.id", ondelete="SET NULL")
    )
    conditions: Mapped[Optional[dict]] = mapped_column(JSONB)  # ABAC conditions
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship(
        back_populates="roles"
    )
    parent_role: Mapped[Optional["Role"]] = relationship(
        remote_side=[id],
        backref="child_roles"
    )
```

### 4. Policy (NEW - ABAC Policies)
Defines attribute-based access control rules.

```python
class Policy(Base):
    __tablename__ = "policies"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=generate_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    effect: Mapped[str] = mapped_column(String(10))  # "allow" or "deny"
    priority: Mapped[int] = mapped_column(Integer, default=0)  # Higher = evaluated first
    
    # Policy components
    subjects: Mapped[dict] = mapped_column(JSONB)  # Who: user attributes
    resources: Mapped[dict] = mapped_column(JSONB)  # What: resource attributes
    actions: Mapped[List[str]] = mapped_column(JSONB)  # Which actions
    conditions: Mapped[Optional[dict]] = mapped_column(JSONB)  # When: environmental
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="policies")
```

**Policy Structure Example:**
```json
{
  "subjects": {
    "department": ["sales", "marketing"],
    "employee_type": ["full_time"]
  },
  "resources": {
    "type": "lead",
    "attributes.status": ["new", "contacted"]
  },
  "actions": ["read", "update"],
  "conditions": {
    "time.hour": {">=": 9, "<=": 17},
    "resource.created_at": {">": "now-30d"}
  }
}
```

### 5. ResourceType (NEW - Define Resource Schemas)
Defines types of resources and their attribute schemas for ABAC.

```python
class ResourceType(Base):
    __tablename__ = "resource_types"
    __table_args__ = (
        Index("idx_org_resource_type", "organization_id", "name", unique=True),
    )
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=generate_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100))  # "project", "document", "lead"
    description: Mapped[Optional[str]] = mapped_column(Text)
    attribute_schema: Mapped[dict] = mapped_column(JSONB)  # JSON Schema for attributes
    relationship_schema: Mapped[Optional[dict]] = mapped_column(JSONB)  # ReBAC relationships
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    # Relationships
    organization: Mapped["Organization"] = relationship(
        back_populates="resource_types"
    )
    resources: Mapped[List["Resource"]] = relationship(
        back_populates="resource_type",
        cascade="all, delete-orphan"
    )
```

**Attribute Schema Example:**
```json
{
  "type": "object",
  "properties": {
    "department": {"type": "string", "enum": ["sales", "engineering", "marketing"]},
    "sensitivity": {"type": "string", "enum": ["public", "internal", "confidential"]},
    "status": {"type": "string"},
    "created_by": {"type": "string", "format": "uuid"}
  },
  "required": ["department", "sensitivity"]
}
```

**Relationship Schema Example:**
```json
{
  "owner": {"type": "user", "cardinality": "one"},
  "editors": {"type": "user", "cardinality": "many"},
  "viewers": {"type": "user", "cardinality": "many"},
  "parent": {"type": "project", "cardinality": "one"}
}
```

### 6. Resource (NEW - Generic Resource Registry)
Represents any resource in the system for ABAC/ReBAC evaluation.

```python
class Resource(Base):
    __tablename__ = "resources"
    __table_args__ = (
        Index("idx_org_resource_type", "organization_id", "resource_type_id"),
        Index("idx_resource_external", "organization_id", "external_id", unique=True),
    )
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=generate_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    resource_type_id: Mapped[UUID] = mapped_column(
        ForeignKey("resource_types.id", ondelete="CASCADE")
    )
    external_id: Mapped[str] = mapped_column(String(255))  # ID in your domain model
    attributes: Mapped[dict] = mapped_column(JSONB)  # ABAC attributes
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship()
    resource_type: Mapped["ResourceType"] = relationship(back_populates="resources")
    grants: Mapped[List["ResourceGrant"]] = relationship(
        back_populates="resource",
        cascade="all, delete-orphan"
    )
    relationships: Mapped[List["ResourceRelationship"]] = relationship(
        foreign_keys="ResourceRelationship.source_id",
        back_populates="source",
        cascade="all, delete-orphan"
    )
```

### 7. ResourceGrant (NEW - Direct User-Resource Permissions)
Explicit grants for specific user-resource combinations (ReBAC).

```python
class ResourceGrant(Base):
    __tablename__ = "resource_grants"
    __table_args__ = (
        Index("idx_user_resource_grant", "user_id", "resource_id", unique=True),
    )
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=generate_uuid)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    resource_id: Mapped[UUID] = mapped_column(
        ForeignKey("resources.id", ondelete="CASCADE"),
        index=True
    )
    permissions: Mapped[List[str]] = mapped_column(JSONB)  # ["read", "write", "delete"]
    granted_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[Optional[datetime]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship(
        foreign_keys=[user_id],
        back_populates="resource_grants"
    )
    resource: Mapped["Resource"] = relationship(back_populates="grants")
```

### 8. ResourceRelationship (NEW - Entity Relationships for ReBAC)
Defines relationships between resources and users.

```python
class ResourceRelationship(Base):
    __tablename__ = "resource_relationships"
    __table_args__ = (
        Index(
            "idx_resource_relationship",
            "source_id",
            "relation_type",
            "target_type",
            "target_id"
        ),
    )
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=generate_uuid)
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("resources.id", ondelete="CASCADE"),
        index=True
    )
    relation_type: Mapped[str] = mapped_column(String(50))  # "owner", "editor", "viewer"
    target_type: Mapped[str] = mapped_column(String(50))  # "user", "team", "resource"
    target_id: Mapped[UUID] = mapped_column(index=True)  # ID of user/team/resource
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    # Relationships
    source: Mapped["Resource"] = relationship(
        foreign_keys=[source_id],
        back_populates="relationships"
    )
```

### 9. OrganizationMembership (Unchanged)

```python
class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        Index("idx_user_org", "user_id", "organization_id", unique=True),
    )
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=generate_uuid)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id"))
    invited_by: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"))
    joined_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        back_populates="memberships",
        foreign_keys=[user_id]
    )
    organization: Mapped["Organization"] = relationship(back_populates="memberships")
    role: Mapped["Role"] = relationship()
```

### 10. APIKey & Session (Unchanged from original)

## Pydantic 2.12 Schemas (Enhanced)

### User Schemas

```python
from typing import Literal

class UserBase(BaseSchema):
    email: EmailStr
    full_name: Optional[str] = None
    department: Optional[str] = None
    employee_type: Optional[Literal["full_time", "contractor", "intern"]] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    attributes: Optional[dict] = None
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        return v

class UserUpdate(BaseSchema):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    employee_type: Optional[Literal["full_time", "contractor", "intern"]] = None
    attributes: Optional[dict] = None

class UserResponse(UserBase):
    id: UUID
    is_active: bool
    is_verified: bool
    attributes: Optional[dict] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None
```

### Policy Schemas

```python
class PolicyBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    effect: Literal["allow", "deny"]
    priority: int = Field(default=0, ge=0, le=1000)
    subjects: dict = Field(..., description="User attribute constraints")
    resources: dict = Field(..., description="Resource attribute constraints")
    actions: List[str] = Field(..., min_length=1)
    conditions: Optional[dict] = Field(None, description="Environmental conditions")

class PolicyCreate(PolicyBase):
    organization_id: UUID

class PolicyUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    effect: Optional[Literal["allow", "deny"]] = None
    priority: Optional[int] = Field(None, ge=0, le=1000)
    subjects: Optional[dict] = None
    resources: Optional[dict] = None
    actions: Optional[List[str]] = None
    conditions: Optional[dict] = None
    is_active: Optional[bool] = None

class PolicyResponse(PolicyBase):
    id: UUID
    organization_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### ResourceType Schemas

```python
class ResourceTypeBase(BaseSchema):
    name: str = Field(..., pattern=r'^[a-z_]+$', max_length=100)
    description: Optional[str] = None
    attribute_schema: dict = Field(..., description="JSON Schema for attributes")
    relationship_schema: Optional[dict] = None

class ResourceTypeCreate(ResourceTypeBase):
    organization_id: UUID

class ResourceTypeUpdate(BaseSchema):
    description: Optional[str] = None
    attribute_schema: Optional[dict] = None
    relationship_schema: Optional[dict] = None

class ResourceTypeResponse(ResourceTypeBase):
    id: UUID
    organization_id: UUID
    created_at: datetime
```

### Resource Schemas

```python
class ResourceBase(BaseSchema):
    external_id: str = Field(..., max_length=255)
    attributes: dict

class ResourceCreate(ResourceBase):
    organization_id: UUID
    resource_type_id: UUID

class ResourceUpdate(BaseSchema):
    attributes: dict

class ResourceResponse(ResourceBase):
    id: UUID
    organization_id: UUID
    resource_type_id: UUID
    created_at: datetime
    updated_at: datetime
```

### ResourceGrant Schemas

```python
class ResourceGrantBase(BaseSchema):
    permissions: List[str] = Field(..., min_length=1)
    expires_at: Optional[datetime] = None

class ResourceGrantCreate(ResourceGrantBase):
    user_id: UUID
    resource_id: UUID

class ResourceGrantResponse(ResourceGrantBase):
    id: UUID
    user_id: UUID
    resource_id: UUID
    granted_by: UUID
    created_at: datetime
```

### Authorization Request Schema

```python
class AuthorizationRequest(BaseSchema):
    """Request to check if action is authorized."""
    user_id: UUID
    action: str
    resource_type: str
    resource_id: Optional[UUID] = None
    resource_attributes: Optional[dict] = None
    context: Optional[dict] = Field(
        None,
        description="Environmental context (ip, time, etc)"
    )

class AuthorizationResponse(BaseSchema):
    """Result of authorization check."""
    allowed: bool
    reason: str
    matched_policies: List[UUID] = []
    matched_roles: List[str] = []
    matched_grants: List[UUID] = []
```

## Hybrid Authorization Engine

### Core Authorization Service

```python
from typing import Dict, List, Set, Tuple
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

class AuthorizationService:
    """Hybrid authorization engine combining RBAC, ABAC, and ReBAC."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def is_authorized(
        self,
        user_id: UUID,
        action: str,
        organization_id: UUID,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        resource_attributes: Optional[Dict] = None,
        context: Optional[Dict] = None,
    ) -> Tuple[bool, str, Dict]:
        """
        Check if user is authorized to perform action.
        
        Returns:
            (allowed, reason, details)
            - allowed: bool - whether action is permitted
            - reason: str - human-readable explanation
            - details: dict - matched policies, roles, grants
        """
        details = {
            "matched_policies": [],
            "matched_roles": [],
            "matched_grants": [],
            "evaluation_order": []
        }
        
        # Load user with attributes
        user = await self._load_user(user_id)
        if not user or not user.is_active:
            return False, "User not found or inactive", details
        
        # 1. Check ReBAC (direct grants) - highest priority
        if resource_id:
            grant_check = await self._check_resource_grants(
                user_id, resource_id, action
            )
            if grant_check["allowed"]:
                details["matched_grants"] = grant_check["grants"]
                details["evaluation_order"].append("resource_grant")
                return True, "Authorized via direct resource grant", details
        
        # 2. Check relationship-based permissions
        if resource_id:
            relationship_check = await self._check_relationships(
                user_id, resource_id, action
            )
            if relationship_check["allowed"]:
                details["matched_grants"] = relationship_check["relationships"]
                details["evaluation_order"].append("relationship")
                return True, f"Authorized via relationship: {relationship_check['reason']}", details
        
        # 3. Check RBAC (role permissions)
        rbac_check = await self._check_rbac(
            user_id, organization_id, action
        )
        if rbac_check["allowed"]:
            details["matched_roles"] = rbac_check["roles"]
            details["evaluation_order"].append("rbac")
            return True, f"Authorized via role: {', '.join(rbac_check['roles'])}", details
        
        # 4. Check ABAC policies (most flexible, evaluated last)
        abac_check = await self._check_abac(
            user=user,
            action=action,
            organization_id=organization_id,
            resource_type=resource_type,
            resource_attributes=resource_attributes or {},
            context=context or {}
        )
        if abac_check["allowed"]:
            details["matched_policies"] = abac_check["policies"]
            details["evaluation_order"].append("abac")
            return True, "Authorized via attribute policy", details
        
        # Check for explicit deny policies
        deny_check = await self._check_deny_policies(
            user=user,
            action=action,
            organization_id=organization_id,
            resource_type=resource_type,
            resource_attributes=resource_attributes or {},
            context=context or {}
        )
        if deny_check["denied"]:
            details["matched_policies"] = deny_check["policies"]
            return False, f"Explicitly denied by policy", details
        
        return False, "No matching authorization found", details
    
    async def _load_user(self, user_id: UUID) -> Optional[User]:
        """Load user with relationships."""
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.memberships))
        )
        return result.scalar_one_or_none()
    
    async def _check_resource_grants(
        self,
        user_id: UUID,
        resource_id: UUID,
        action: str
    ) -> Dict:
        """Check direct resource grants."""
        result = await self.db.execute(
            select(ResourceGrant)
            .where(
                ResourceGrant.user_id == user_id,
                ResourceGrant.resource_id == resource_id,
                ResourceGrant.permissions.contains([action])
            )
        )
        grants = result.scalars().all()
        
        # Check expiration
        valid_grants = [
            g for g in grants
            if not g.expires_at or g.expires_at > datetime.now(timezone.utc)
        ]
        
        return {
            "allowed": len(valid_grants) > 0,
            "grants": [str(g.id) for g in valid_grants]
        }
    
    async def _check_relationships(
        self,
        user_id: UUID,
        resource_id: UUID,
        action: str
    ) -> Dict:
        """Check relationship-based permissions."""
        # Load resource with relationships
        result = await self.db.execute(
            select(Resource)
            .where(Resource.id == resource_id)
            .options(selectinload(Resource.relationships))
        )
        resource = result.scalar_one_or_none()
        
        if not resource:
            return {"allowed": False, "relationships": []}
        
        # Check if user has relationship granting permission
        for rel in resource.relationships:
            if rel.target_type == "user" and rel.target_id == user_id:
                # Map relationship to permissions
                rel_permissions = self._relationship_to_permissions(rel.relation_type)
                if action in rel_permissions:
                    return {
                        "allowed": True,
                        "reason": rel.relation_type,
                        "relationships": [str(rel.id)]
                    }
        
        return {"allowed": False, "relationships": []}
    
    def _relationship_to_permissions(self, relation_type: str) -> List[str]:
        """Map relationship types to permissions."""
        mapping = {
            "owner": ["read", "write", "delete", "share", "manage"],
            "editor": ["read", "write"],
            "viewer": ["read"],
            "admin": ["read", "write", "delete", "manage"],
        }
        return mapping.get(relation_type, [])
    
    async def _check_rbac(
        self,
        user_id: UUID,
        organization_id: UUID,
        action: str
    ) -> Dict:
        """Check role-based permissions."""
        # Get user's membership and role
        result = await self.db.execute(
            select(OrganizationMembership)
            .where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == organization_id
            )
            .options(selectinload(OrganizationMembership.role))
        )
        membership = result.scalar_one_or_none()
        
        if not membership:
            return {"allowed": False, "roles": []}
        
        role = membership.role
        
        # Check if role has permission (with inheritance)
        if self._has_permission(role.permissions, action):
            return {"allowed": True, "roles": [role.name]}
        
        # Check parent roles
        if role.parent_role:
            parent_check = self._check_role_hierarchy(role.parent_role, action)
            if parent_check["allowed"]:
                return {
                    "allowed": True,
                    "roles": [role.name] + parent_check["roles"]
                }
        
        return {"allowed": False, "roles": []}
    
    def _check_role_hierarchy(self, role: Role, action: str) -> Dict:
        """Recursively check parent roles."""
        if self._has_permission(role.permissions, action):
            return {"allowed": True, "roles": [role.name]}
        
        if role.parent_role:
            parent_check = self._check_role_hierarchy(role.parent_role, action)
            if parent_check["allowed"]:
                return {
                    "allowed": True,
                    "roles": [role.name] + parent_check["roles"]
                }
        
        return {"allowed": False, "roles": []}
    
    def _has_permission(self, permissions: List[str], required: str) -> bool:
        """Check if permission list contains required permission (with wildcards)."""
        if required in permissions:
            return True
        
        # Check wildcards
        parts = required.split(":")
        for i in range(len(parts)):
            wildcard = ":".join(parts[:i+1]) + ":*"
            if wildcard in permissions:
                return True
        
        return False
    
    async def _check_abac(
        self,
        user: User,
        action: str,
        organization_id: UUID,
        resource_type: Optional[str],
        resource_attributes: Dict,
        context: Dict
    ) -> Dict:
        """Check attribute-based policies."""
        # Load active "allow" policies for organization
        result = await self.db.execute(
            select(Policy)
            .where(
                Policy.organization_id == organization_id,
                Policy.effect == "allow",
                Policy.is_active == True
            )
            .order_by(Policy.priority.desc())
        )
        policies = result.scalars().all()
        
        matched_policies = []
        
        for policy in policies:
            # Check if action matches
            if action not in policy.actions and "*" not in policy.actions:
                continue
            
            # Evaluate subject constraints
            if not self._evaluate_attributes(user.attributes or {}, policy.subjects):
                continue
            
            # Evaluate resource constraints
            if resource_type and not self._match_resource_type(resource_type, policy.resources):
                continue
            
            if not self._evaluate_attributes(resource_attributes, policy.resources.get("attributes", {})):
                continue
            
            # Evaluate conditions
            if policy.conditions:
                eval_context = {
                    "user": user.attributes or {},
                    "resource": resource_attributes,
                    "time": datetime.now(timezone.utc),
                    **context
                }
                if not self._evaluate_conditions(policy.conditions, eval_context):
                    continue
            
            matched_policies.append(str(policy.id))
        
        return {
            "allowed": len(matched_policies) > 0,
            "policies": matched_policies
        }
    
    async def _check_deny_policies(
        self,
        user: User,
        action: str,
        organization_id: UUID,
        resource_type: Optional[str],
        resource_attributes: Dict,
        context: Dict
    ) -> Dict:
        """Check for explicit deny policies."""
        result = await self.db.execute(
            select(Policy)
            .where(
                Policy.organization_id == organization_id,
                Policy.effect == "deny",
                Policy.is_active == True
            )
            .order_by(Policy.priority.desc())
        )
        policies = result.scalars().all()
        
        for policy in policies:
            if action not in policy.actions and "*" not in policy.actions:
                continue
            
            if not self._evaluate_attributes(user.attributes or {}, policy.subjects):
                continue
            
            if resource_type and not self._match_resource_type(resource_type, policy.resources):
                continue
            
            if not self._evaluate_attributes(resource_attributes, policy.resources.get("attributes", {})):
                continue
            
            if policy.conditions:
                eval_context = {
                    "user": user.attributes or {},
                    "resource": resource_attributes,
                    "time": datetime.now(timezone.utc),
                    **context
                }
                if not self._evaluate_conditions(policy.conditions, eval_context):
                    continue
            
            # Deny policy matched
            return {"denied": True, "policies": [str(policy.id)]}
        
        return {"denied": False, "policies": []}
    
    def _evaluate_attributes(self, actual: Dict, required: Dict) -> bool:
        """Check if actual attributes satisfy required constraints."""
        for key, constraint in required.items():
            actual_value = actual.get(key)
            
            if isinstance(constraint, list):
                # Must be one of values
                if actual_value not in constraint:
                    return False
            elif isinstance(constraint, dict):
                # Comparison operators
                if not self._evaluate_comparison(actual_value, constraint):
                    return False
            else:
                # Exact match
                if actual_value != constraint:
                    return False
        
        return True
    
    def _evaluate_comparison(self, value, operators: Dict) -> bool:
        """Evaluate comparison operators."""
        for op, target in operators.items():
            if op == "==":
                if value != target:
                    return False
            elif op == "!=":
                if value == target:
                    return False
            elif op == ">":
                if value <= target:
                    return False
            elif op == ">=":
                if value < target:
                    return False
            elif op == "<":
                if value >= target:
                    return False
            elif op == "<=":
                if value > target:
                    return False
            elif op == "in":
                if value not in target:
                    return False
            elif op == "not_in":
                if value in target:
                    return False
        
        return True
    
    def _match_resource_type(self, actual: str, constraint: Dict) -> bool:
        """Check if resource type matches constraint."""
        required_type = constraint.get("type")
        if not required_type:
            return True
        
        if isinstance(required_type, list):
            return actual in required_type
        
        return actual == required_type
    
    def _evaluate_conditions(self, conditions: Dict, context: Dict) -> bool:
        """Evaluate environmental conditions."""
        for key, constraint in conditions.items():
            # Support nested keys like "time.hour"
            value = context
            for part in key.split("."):
                value = value.get(part)
                if value is None:
                    return False
            
            if isinstance(constraint, dict):
                if not self._evaluate_comparison(value, constraint):
                    return False
            else:
                if value != constraint:
                    return False
        
        return True
```

### FastAPI Dependency

```python
from fastapi import Depends, HTTPException, status

async def require_authorization(
    action: str,
    organization_id: UUID,
    resource_type: Optional[str] = None,
    resource_id: Optional[UUID] = None,
    resource_attributes: Optional[Dict] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Dependency to enforce authorization checks.
    
    Usage:
        @app.get("/projects/{project_id}")
        async def get_project(
            project_id: UUID,
            auth: None = Depends(
                require_authorization(
                    action="read",
                    organization_id=org_id,
                    resource_type="project",
                    resource_id=project_id
                )
            )
        ):
            ...
    """
    auth_service = AuthorizationService(db)
    
    allowed, reason, details = await auth_service.is_authorized(
        user_id=current_user.id,
        action=action,
        organization_id=organization_id,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_attributes=resource_attributes
    )
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Unauthorized",
                "reason": reason,
                "details": details
            }
        )
    
    return details
```

## Example Policy Definitions

### 1. Time-Based Access (ABAC)

```python
{
    "name": "Business Hours Only",
    "effect": "allow",
    "subjects": {
        "employee_type": ["full_time", "contractor"]
    },
    "resources": {
        "type": "document",
        "attributes.sensitivity": ["internal", "confidential"]
    },
    "actions": ["read", "write"],
    "conditions": {
        "time.hour": {">=": 9, "<=": 17},
        "time.weekday": {"<": 5}  # Monday=0, Friday=4
    }
}
```

### 2. Department-Based Access (ABAC)

```python
{
    "name": "Sales Access to Leads",
    "effect": "allow",
    "subjects": {
        "department": ["sales"]
    },
    "resources": {
        "type": "lead",
        "attributes.status": ["new", "contacted", "qualified"]
    },
    "actions": ["read", "write"]
}
```

### 3. Owner-Only Delete (ReBAC via Policy)

```python
{
    "name": "Creator Can Delete",
    "effect": "allow",
    "subjects": {},
    "resources": {
        "type": ["project", "document"],
        "attributes.created_by": "{{user.id}}"  # Template matching
    },
    "actions": ["delete"]
}
```

### 4. Conditional Admin Rights (ABAC)

```python
{
    "name": "Senior Staff Admin Rights",
    "effect": "allow",
    "subjects": {
        "employee_type": ["full_time"],
        "attributes.tenure_years": {">=": 3}
    },
    "resources": {
        "type": "*"
    },
    "actions": ["read", "write"]
}
```

### 5. Explicit Deny (ABAC)

```python
{
    "name": "Block Contractors from Confidential",
    "effect": "deny",
    "priority": 1000,  # Evaluated first
    "subjects": {
        "employee_type": ["contractor", "intern"]
    },
    "resources": {
        "type": "*",
        "attributes.sensitivity": ["confidential"]
    },
    "actions": ["*"]
}
```

## Database Indexes

```sql
-- Users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_department ON users(department);
CREATE INDEX idx_users_employee_type ON users(employee_type);
CREATE INDEX idx_users_is_active ON users(is_active) WHERE is_active = true;

-- Organizations
CREATE INDEX idx_organizations_slug ON organizations(slug);
CREATE INDEX idx_organizations_owner_id ON organizations(owner_id);

-- Policies
CREATE INDEX idx_policies_org_effect ON policies(organization_id, effect, is_active);
CREATE INDEX idx_policies_priority ON policies(priority DESC);

-- Resources
CREATE INDEX idx_resources_org_type ON resources(organization_id, resource_type_id);
CREATE INDEX idx_resources_external ON resources(organization_id, external_id);
CREATE INDEX idx_resources_attributes ON resources USING GIN(attributes);

-- Resource Grants
CREATE INDEX idx_resource_grants_user ON resource_grants(user_id);
CREATE INDEX idx_resource_grants_resource ON resource_grants(resource_id);
CREATE INDEX idx_resource_grants_expires ON resource_grants(expires_at) WHERE expires_at IS NOT NULL;

-- Resource Relationships
CREATE INDEX idx_relationships_source ON resource_relationships(source_id, relation_type);
CREATE INDEX idx_relationships_target ON resource_relationships(target_type, target_id);

-- Roles
CREATE INDEX idx_roles_org_name ON roles(organization_id, name);
CREATE INDEX idx_roles_inherits ON roles(inherits_from);
```

## Migration Strategy

### 1. Initialize System

```python
async def initialize_authorization_system(db: AsyncSession):
    """Set up base roles and resource types."""
    
    # Create system roles
    system_roles = [
        Role(
            name="owner",
            description="Organization owner with full control",
            permissions=["org:*"],
            is_system=True
        ),
        Role(
            name="admin",
            description="Administrator with management permissions",
            permissions=[
                "org:read", "org:write",
                "org:members:*",
                "resource:*"
            ],
            is_system=True
        ),
        Role(
            name="member",
            description="Standard member with basic access",
            permissions=["org:read", "resource:read", "resource:write"],
            is_system=True
        ),
        Role(
            name="viewer",
            description="Read-only access",
            permissions=["org:read", "resource:read"],
            is_system=True
        )
    ]
    
    for role in system_roles:
        db.add(role)
    
    await db.commit()
```

### 2. Register Resource on Creation

```python
async def create_project_with_authorization(
    project_data: Dict,
    owner_id: UUID,
    organization_id: UUID,
    db: AsyncSession
) -> Project:
    """Create project and register with authorization system."""
    
    # Create your domain model
    project = Project(**project_data)
    db.add(project)
    await db.flush()
    
    # Get resource type
    resource_type = await db.execute(
        select(ResourceType).where(
            ResourceType.organization_id == organization_id,
            ResourceType.name == "project"
        )
    )
    resource_type = resource_type.scalar_one()
    
    # Register resource
    resource = Resource(
        organization_id=organization_id,
        resource_type_id=resource_type.id,
        external_id=str(project.id),
        attributes={
            "name": project.name,
            "department": project.department,
            "created_by": str(owner_id),
            "status": "active"
        }
    )
    db.add(resource)
    await db.flush()
    
    # Create owner relationship
    relationship = ResourceRelationship(
        source_id=resource.id,
        relation_type="owner",
        target_type="user",
        target_id=owner_id
    )
    db.add(relationship)
    
    await db.commit()
    return project
```

## API Endpoints

### Authorization Check Endpoint

```python
@app.post("/api/v1/authorize", response_model=AuthorizationResponse)
async def check_authorization(
    request: AuthorizationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check if a user is authorized to perform an action.
    
    This is useful for:
    - Pre-checking permissions before UI render
    - Batch authorization checks
    - Debugging permission issues
    """
    auth_service = AuthorizationService(db)
    
    allowed, reason, details = await auth_service.is_authorized(
        user_id=request.user_id,
        action=request.action,
        organization_id=current_user.active_organization_id,  # From context
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        resource_attributes=request.resource_attributes,
        context=request.context or {}
    )
    
    return AuthorizationResponse(
        allowed=allowed,
        reason=reason,
        matched_policies=details.get("matched_policies", []),
        matched_roles=details.get("matched_roles", []),
        matched_grants=details.get("matched_grants", [])
    )
```

### Policy Management Endpoints

```python
@app.post("/api/v1/organizations/{org_id}/policies", response_model=PolicyResponse)
async def create_policy(
    org_id: UUID,
    policy: PolicyCreate,
    db: AsyncSession = Depends(get_db),
    auth: None = Depends(require_permission("org:policies:write", org_id))
):
    """Create a new ABAC policy."""
    db_policy = Policy(**policy.model_dump())
    db.add(db_policy)
    await db.commit()
    await db.refresh(db_policy)
    return db_policy

@app.get("/api/v1/organizations/{org_id}/policies", response_model=List[PolicyResponse])
async def list_policies(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: None = Depends(require_permission("org:policies:read", org_id))
):
    """List all policies for an organization."""
    result = await db.execute(
        select(Policy)
        .where(Policy.organization_id == org_id)
        .order_by(Policy.priority.desc())
    )
    return result.scalars().all()
```

## Performance Considerations

### 1. Caching Strategy

```python
from functools import lru_cache
from redis import asyncio as aioredis

class CachedAuthorizationService(AuthorizationService):
    """Authorization service with Redis caching."""
    
    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        super().__init__(db)
        self.redis = redis
    
    async def is_authorized(self, *args, **kwargs) -> Tuple[bool, str, Dict]:
        """Check authorization with caching."""
        # Create cache key from parameters
        cache_key = self._create_cache_key(*args, **kwargs)
        
        # Try cache
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Compute
        result = await super().is_authorized(*args, **kwargs)
        
        # Cache for 5 minutes
        await self.redis.setex(
            cache_key,
            300,
            json.dumps(result)
        )
        
        return result
    
    def _create_cache_key(self, user_id, action, organization_id, **kwargs):
        """Create deterministic cache key."""
        parts = [
            str(user_id),
            action,
            str(organization_id),
            str(kwargs.get("resource_id", "")),
            str(kwargs.get("resource_type", ""))
        ]
        return f"auth:{':'.join(parts)}"
```

### 2. Batch Authorization

```python
async def batch_authorize(
    user_id: UUID,
    requests: List[Tuple[str, UUID]],  # [(action, resource_id), ...]
    organization_id: UUID,
    db: AsyncSession
) -> Dict[UUID, bool]:
    """Check multiple authorizations in one query."""
    auth_service = AuthorizationService(db)
    
    results = {}
    for action, resource_id in requests:
        allowed, _, _ = await auth_service.is_authorized(
            user_id=user_id,
            action=action,
            organization_id=organization_id,
            resource_id=resource_id
        )
        results[resource_id] = allowed
    
    return results
```

### 3. Policy Evaluation Optimization

- **Index JSONB fields** for attribute queries
- **Order policies by priority** to short-circuit evaluation
- **Cache policy evaluation results** for frequently accessed resources
- **Pre-compile policy conditions** into executable functions
- **Use database views** for common relationship patterns

## Testing Strategy

### Unit Tests

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_rbac_authorization():
    """Test role-based authorization."""
    db = AsyncMock()
    auth_service = AuthorizationService(db)
    
    # Mock user with admin role
    user = User(id=uuid4(), email="admin@test.com", is_active=True)
    membership = OrganizationMembership(
        user_id=user.id,
        organization_id=uuid4(),
        role=Role(name="admin", permissions=["resource:write"])
    )
    
    db.execute.return_value.scalar_one_or_none.return_value = membership
    
    allowed, reason, details = await auth_service._check_rbac(
        user.id,
        membership.organization_id,
        "resource:write"
    )
    
    assert allowed
    assert "admin" in details["roles"]

@pytest.mark.asyncio
async def test_abac_time_constraint():
    """Test attribute-based time constraint."""
    auth_service = AuthorizationService(AsyncMock())
    
    # Create policy with time constraint
    policy = Policy(
        name="Business Hours",
        effect="allow",
        subjects={},
        resources={"type": "document"},
        actions=["read"],
        conditions={"time.hour": {">=": 9, "<": 17}}
    )
    
    # Test during business hours
    context = {"time": MagicMock(hour=14)}
    matches = auth_service._evaluate_conditions(policy.conditions, context)
    assert matches
    
    # Test outside business hours
    context = {"time": MagicMock(hour=20)}
    matches = auth_service._evaluate_conditions(policy.conditions, context)
    assert not matches
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_authorization_flow(db_session, test_user, test_org):
    """Test complete authorization with all models."""
    # Create resource type
    resource_type = ResourceType(
        organization_id=test_org.id,
        name="project",
        attribute_schema={"type": "object", "properties": {"status": {"type": "string"}}}
    )
    db_session.add(resource_type)
    await db_session.commit()
    
    # Create resource
    resource = Resource(
        organization_id=test_org.id,
        resource_type_id=resource_type.id,
        external_id="project-123",
        attributes={"status": "active"}
    )
    db_session.add(resource)
    await db_session.commit()
    
    # Create policy
    policy = Policy(
        organization_id=test_org.id,
        name="Test Policy",
        effect="allow",
        subjects={"department": ["engineering"]},
        resources={"type": "project"},
        actions=["read"],
        priority=0
    )
    db_session.add(policy)
    await db_session.commit()
    
    # Update user department
    test_user.department = "engineering"
    await db_session.commit()
    
    # Test authorization
    auth_service = AuthorizationService(db_session)
    allowed, reason, details = await auth_service.is_authorized(
        user_id=test_user.id,
        action="read",
        organization_id=test_org.id,
        resource_type="project",
        resource_id=resource.id
    )
    
    assert allowed
    assert len(details["matched_policies"]) > 0
```

## Next Steps

1. **Implement policy evaluation caching** with Redis
2. **Add policy testing UI** for admins to validate rules
3. **Create policy templates** for common scenarios
4. **Build audit logging** for authorization decisions
5. **Add policy conflict detection** (overlapping allow/deny)
6. **Implement temporal policies** (activate/deactivate on schedule)
7. **Create authorization analytics** dashboard

## Questions for Your Context

**What resource types will you have?** (projects, documents, leads, etc.) - defines your ResourceType schemas

**What relationships matter?** (owner, editor, team member, parent project) - shapes your ReBAC model

**What dynamic rules do you need?** (time-based, quota-based, department-based) - determines ABAC complexity

**Performance requirements?** (requests/sec, latency targets) - influences caching strategy



## Response:
11/19/2025, 8:37:08 AM

I'll update the design document with your specific domain model: Organizations → Projects → Documents/Tickets → Tasks, with both human users and AI agents as actors.

```markdown:docs/auth-org-design.md
# Organization & Authentication Design Document

## System Overview

A multi-tenant authentication and authorization system for collaborative project management with AI agents. Supports hierarchical resource organization, hybrid access control (RBAC + ABAC + ReBAC), and git-integrated workflows.

**Domain Hierarchy:**
```
Organizations
  ├─ Members (Users + Agents with Roles)
  └─ Projects
      ├─ Git Repositories
      ├─ Documents (Designs, Requirements)
      └─ Tickets
          └─ Tasks
```

**Actor Types:**
- **Users**: Human members with email authentication
- **Agents**: AI actors with API key authentication
- **Roles**: Owner, Member, Super Admin (global)

## Core Entities

### 1. User
Human actors who authenticate via email/password or SSO.

```python
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum as PyEnum
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime

class ActorType(PyEnum):
    USER = "user"
    AGENT = "agent"

class User(Base):
    __tablename__ = "users"
    
    # Identity
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
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
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), 
        onupdate=func.now()
    )
    last_login_at: Mapped[Optional[datetime]]
    
    # Relationships
    memberships: Mapped[List["OrganizationMembership"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="OrganizationMembership.user_id"
    )
    owned_organizations: Mapped[List["Organization"]] = relationship(
        back_populates="owner",
        foreign_keys="Organization.owner_id"
    )
    api_keys: Mapped[List["APIKey"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    sessions: Mapped[List["Session"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    created_projects: Mapped[List["Project"]] = relationship(
        back_populates="creator",
        foreign_keys="Project.created_by"
    )
    assigned_tasks: Mapped[List["TaskAssignment"]] = relationship(
        back_populates="assignee",
        foreign_keys="TaskAssignment.assignee_id"
    )
    created_tickets: Mapped[List["Ticket"]] = relationship(
        back_populates="creator",
        foreign_keys="Ticket.created_by"
    )
```

### 2. Agent
AI actors that authenticate via API keys and can be assigned to tasks.

```python
class Agent(Base):
    __tablename__ = "agents"
    
    # Identity
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    agent_type: Mapped[str] = mapped_column(String(50))  # "coding", "design", "testing"
    
    # Configuration
    model_config: Mapped[Optional[dict]] = mapped_column(JSONB)  # LLM settings
    capabilities: Mapped[List[str]] = mapped_column(JSONB)  # ["python", "react", "testing"]
    attributes: Mapped[Optional[dict]] = mapped_column(JSONB)  # ABAC attributes
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    last_active_at: Mapped[Optional[datetime]]
    
    # Relationships
    memberships: Mapped[List["OrganizationMembership"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
        foreign_keys="OrganizationMembership.agent_id"
    )
    api_keys: Mapped[List["APIKey"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan"
    )
    assigned_tasks: Mapped[List["TaskAssignment"]] = relationship(
        back_populates="agent_assignee",
        foreign_keys="TaskAssignment.agent_id"
    )
```

### 3. Organization
Top-level multi-tenant boundary.

```python
class Organization(Base):
    __tablename__ = "organizations"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Ownership
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    
    # Settings
    billing_email: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSONB)
    attributes: Mapped[Optional[dict]] = mapped_column(JSONB)  # ABAC
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    owner: Mapped["User"] = relationship(
        back_populates="owned_organizations",
        foreign_keys=[owner_id]
    )
    memberships: Mapped[List["OrganizationMembership"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    roles: Mapped[List["Role"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    policies: Mapped[List["Policy"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    projects: Mapped[List["Project"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
```

### 4. OrganizationMembership
Join table supporting both users and agents as members.

```python
class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        # Ensure user OR agent, not both
        CheckConstraint(
            '(user_id IS NOT NULL AND agent_id IS NULL) OR '
            '(user_id IS NULL AND agent_id IS NOT NULL)',
            name='check_user_or_agent'
        ),
        Index("idx_user_org", "user_id", "organization_id", 
              unique=True, postgresql_where=text("user_id IS NOT NULL")),
        Index("idx_agent_org", "agent_id", "organization_id",
              unique=True, postgresql_where=text("agent_id IS NOT NULL")),
    )
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    
    # Member (user OR agent)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    agent_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        index=True
    )
    
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id"))
    
    # Audit
    invited_by: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"))
    joined_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
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
    
    @property
    def actor_id(self) -> UUID:
        """Get the ID of the member (user or agent)."""
        return self.user_id or self.agent_id
    
    @property
    def actor_type(self) -> ActorType:
        """Get the type of actor."""
        return ActorType.USER if self.user_id else ActorType.AGENT
```

### 5. Role
Defines permission sets for organization members.

```python
class RoleType(PyEnum):
    SYSTEM = "system"  # Pre-defined roles
    CUSTOM = "custom"  # Org-specific roles

class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (
        Index("idx_org_role_name", "organization_id", "name", unique=True),
    )
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    role_type: Mapped[str] = mapped_column(
        SQLEnum(RoleType, native_enum=False),
        default=RoleType.CUSTOM.value
    )
    
    # Permissions
    permissions: Mapped[List[str]] = mapped_column(JSONB)
    
    # Hierarchy (role inheritance)
    inherits_from: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("roles.id", ondelete="SET NULL")
    )
    
    # Conditional activation
    conditions: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship(
        back_populates="roles"
    )
    parent_role: Mapped[Optional["Role"]] = relationship(
        remote_side=[id],
        backref="child_roles"
    )
```

### 6. Project
Projects contain git repositories, documents, and tickets.

```python
class ProjectStatus(PyEnum):
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class Project(Base):
    __tablename__ = "projects"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    
    # Basic Info
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(50),
        default=ProjectStatus.PLANNING.value,
        index=True
    )
    
    # Git Integration
    git_repo_url: Mapped[Optional[str]] = mapped_column(String(500))
    git_branch: Mapped[Optional[str]] = mapped_column(String(255))
    git_config: Mapped[Optional[dict]] = mapped_column(JSONB)  # Auth, webhooks, etc.
    
    # ABAC Attributes
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # Ownership
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship(
        back_populates="projects"
    )
    creator: Mapped["User"] = relationship(
        back_populates="created_projects",
        foreign_keys=[created_by]
    )
    documents: Mapped[List["Document"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan"
    )
    tickets: Mapped[List["Ticket"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan"
    )
    team_members: Mapped[List["ProjectMember"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_org_project_slug", "organization_id", "slug", unique=True),
    )
```

### 7. ProjectMember
Explicit project team membership (more granular than org membership).

```python
class ProjectRole(PyEnum):
    OWNER = "owner"
    MAINTAINER = "maintainer"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"

class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        CheckConstraint(
            '(user_id IS NOT NULL AND agent_id IS NULL) OR '
            '(user_id IS NULL AND agent_id IS NOT NULL)',
            name='check_member_user_or_agent'
        ),
        Index("idx_user_project", "user_id", "project_id",
              unique=True, postgresql_where=text("user_id IS NOT NULL")),
        Index("idx_agent_project", "agent_id", "project_id",
              unique=True, postgresql_where=text("agent_id IS NOT NULL")),
    )
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True
    )
    
    # Member (user OR agent)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    agent_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE")
    )
    
    role: Mapped[str] = mapped_column(
        String(50),
        default=ProjectRole.CONTRIBUTOR.value
    )
    
    added_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    joined_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    # Relationships
    project: Mapped["Project"] = relationship(back_populates="team_members")
    user: Mapped[Optional["User"]] = relationship(foreign_keys=[user_id])
    agent: Mapped[Optional["Agent"]] = relationship(foreign_keys=[agent_id])
```

### 8. Document
Design docs, requirements, specifications within projects.

```python
class DocumentType(PyEnum):
    DESIGN = "design"
    REQUIREMENTS = "requirements"
    SPECIFICATION = "specification"
    ARCHITECTURE = "architecture"
    API_DOC = "api_doc"
    OTHER = "other"

class Document(Base):
    __tablename__ = "documents"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True
    )
    
    # Content
    title: Mapped[str] = mapped_column(String(500))
    doc_type: Mapped[str] = mapped_column(
        String(50),
        default=DocumentType.OTHER.value,
        index=True
    )
    content: Mapped[Optional[str]] = mapped_column(Text)
    content_format: Mapped[str] = mapped_column(
        String(20),
        default="markdown"
    )  # "markdown", "html", "plaintext"
    
    # Git Integration
    file_path: Mapped[Optional[str]] = mapped_column(String(1000))  # Path in repo
    git_commit: Mapped[Optional[str]] = mapped_column(String(40))  # SHA
    
    # ABAC Attributes
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # Metadata
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Ownership
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    project: Mapped["Project"] = relationship(back_populates="documents")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
```

### 9. Ticket
Work items within projects (features, bugs, improvements).

```python
class TicketType(PyEnum):
    FEATURE = "feature"
    BUG = "bug"
    IMPROVEMENT = "improvement"
    TASK = "task"

class TicketStatus(PyEnum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CLOSED = "closed"

class TicketPriority(PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class Ticket(Base):
    __tablename__ = "tickets"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True
    )
    
    # Identification
    ticket_number: Mapped[int] = mapped_column(Integer)  # Auto-increment per project
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Classification
    ticket_type: Mapped[str] = mapped_column(
        String(50),
        default=TicketType.TASK.value,
        index=True
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=TicketStatus.BACKLOG.value,
        index=True
    )
    priority: Mapped[str] = mapped_column(
        String(50),
        default=TicketPriority.MEDIUM.value,
        index=True
    )
    
    # Git Integration
    branch_name: Mapped[Optional[str]] = mapped_column(String(255))
    pull_request_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # ABAC Attributes
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # Relationships
    parent_ticket_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("tickets.id", ondelete="SET NULL")
    )
    
    # Ownership
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    assigned_to: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    due_date: Mapped[Optional[datetime]]
    
    # Relationships
    project: Mapped["Project"] = relationship(back_populates="tickets")
    creator: Mapped["User"] = relationship(
        back_populates="created_tickets",
        foreign_keys=[created_by]
    )
    assignee: Mapped[Optional["User"]] = relationship(foreign_keys=[assigned_to])
    parent_ticket: Mapped[Optional["Ticket"]] = relationship(
        remote_side=[id],
        backref="sub_tickets"
    )
    tasks: Mapped[List["Task"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_project_ticket_number", "project_id", "ticket_number", unique=True),
    )
```

### 10. Task
Granular work items within tickets, assignable to users or agents.

```python
class TaskStatus(PyEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    IN_REVIEW = "in_review"
    DONE = "done"

class Task(Base):
    __tablename__ = "tasks"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),
        index=True
    )
    
    # Content
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(50),
        default=TaskStatus.TODO.value,
        index=True
    )
    
    # Ordering
    position: Mapped[int] = mapped_column(Integer, default=0)
    
    # Git Integration
    file_paths: Mapped[Optional[List[str]]] = mapped_column(JSONB)  # Files to modify
    commit_sha: Mapped[Optional[str]] = mapped_column(String(40))
    
    # ABAC Attributes
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # Estimation
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float)
    actual_hours: Mapped[Optional[float]] = mapped_column(Float)
    
    # Ownership
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    completed_at: Mapped[Optional[datetime]]
    
    # Relationships
    ticket: Mapped["Ticket"] = relationship(back_populates="tasks")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    assignments: Mapped[List["TaskAssignment"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan"
    )
```

### 11. TaskAssignment
Assigns tasks to users or agents.

```python
class TaskAssignment(Base):
    __tablename__ = "task_assignments"
    __table_args__ = (
        CheckConstraint(
            '(assignee_id IS NOT NULL AND agent_id IS NULL) OR '
            '(assignee_id IS NULL AND agent_id IS NOT NULL)',
            name='check_assignee_user_or_agent'
        ),
        Index("idx_user_task", "assignee_id", "task_id",
              unique=True, postgresql_where=text("assignee_id IS NOT NULL")),
        Index("idx_agent_task", "agent_id", "task_id",
              unique=True, postgresql_where=text("agent_id IS NOT NULL")),
    )
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        index=True
    )
    
    # Assignee (user OR agent)
    assignee_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    agent_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE")
    )
    
    # Metadata
    assigned_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    assigned_at: Mapped[datetime] = mapped_column(server_default=func.now())
    started_at: Mapped[Optional[datetime]]
    completed_at: Mapped[Optional[datetime]]
    
    # Relationships
    task: Mapped["Task"] = relationship(back_populates="assignments")
    assignee: Mapped[Optional["User"]] = relationship(
        back_populates="assigned_tasks",
        foreign_keys=[assignee_id]
    )
    agent_assignee: Mapped[Optional["Agent"]] = relationship(
        back_populates="assigned_tasks",
        foreign_keys=[agent_id]
    )
```

### 12. Policy (ABAC)

```python
class PolicyEffect(PyEnum):
    ALLOW = "allow"
    DENY = "deny"

class Policy(Base):
    __tablename__ = "policies"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    effect: Mapped[str] = mapped_column(
        String(10),
        default=PolicyEffect.ALLOW.value
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, index=True)
    
    # Policy Definition
    subjects: Mapped[dict] = mapped_column(JSONB)  # Actor attributes
    resources: Mapped[dict] = mapped_column(JSONB)  # Resource attributes
    actions: Mapped[List[str]] = mapped_column(JSONB)
    conditions: Mapped[Optional[dict]] = mapped_column(JSONB)  # Environmental
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship(
        back_populates="policies"
    )
```

### 13. APIKey (for Users and Agents)

```python
class APIKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = (
        CheckConstraint(
            '(user_id IS NOT NULL AND agent_id IS NULL) OR '
            '(user_id IS NULL AND agent_id IS NOT NULL)',
            name='check_key_user_or_agent'
        ),
    )
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    
    # Owner (user OR agent)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    agent_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        index=True
    )
    
    organization_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    
    # Key Data
    name: Mapped[str] = mapped_column(String(255))
    key_prefix: Mapped[str] = mapped_column(String(16), index=True)
    hashed_key: Mapped[str] = mapped_column(String(255), unique=True)
    scopes: Mapped[List[str]] = mapped_column(JSONB)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[Optional[datetime]]
    expires_at: Mapped[Optional[datetime]]
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        back_populates="api_keys",
        foreign_keys=[user_id]
    )
    agent: Mapped[Optional["Agent"]] = relationship(
        back_populates="api_keys",
        foreign_keys=[agent_id]
    )
```

### 14. Session (Users only)

```python
class Session(Base):
    __tablename__ = "sessions"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    expires_at: Mapped[datetime]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")
```

## Permission Model

### Resource Hierarchy and Actions

```python
RESOURCE_ACTIONS = {
    # Organization level
    "org": ["read", "write", "delete", "transfer"],
    "org:members": ["read", "invite", "remove", "change_role"],
    "org:settings": ["read", "write"],
    "org:billing": ["read", "write"],
    
    # Project level
    "project": ["read", "write", "delete", "archive"],
    "project:members": ["read", "add", "remove"],
    "project:settings": ["read", "write"],
    "project:git": ["read", "write", "configure"],
    
    # Document level
    "document": ["read", "write", "delete", "publish"],
    "document:version": ["read", "create", "restore"],
    
    # Ticket level
    "ticket": ["read", "write", "delete", "assign"],
    "ticket:status": ["update"],
    "ticket:comments": ["read", "write"],
    
    # Task level
    "task": ["read", "write", "delete", "assign"],
    "task:status": ["update"],
    "task:complete": ["execute"],
    
    # Agent level
    "agent": ["read", "write", "delete", "configure"],
    "agent:execute": ["run"],  # Allow agent to execute tasks
}
```

### System Roles

```python
SYSTEM_ROLES = {
    "super_admin": {
        "description": "Global administrator with access to all resources",
        "permissions": ["*:*"],  # Full wildcard access
        "is_global": True
    },
    "owner": {
        "description": "Organization owner with full control",
        "permissions": [
            "org:*",
            "project:*",
            "document:*",
            "ticket:*",
            "task:*",
            "agent:*"
        ]
    },
    "member": {
        "description": "Standard organization member",
        "permissions": [
            "org:read",
            "project:read",
            "project:write",
            "document:read",
            "document:write",
            "ticket:read",
            "ticket:write",
            "task:read",
            "task:write",
            "agent:read"
        ]
    },
    "agent_executor": {
        "description": "Role for AI agents",
        "permissions": [
            "project:read",
            "document:read",
            "document:write",
            "ticket:read",
            "ticket:write",
            "task:read",
            "task:write",
            "task:complete:execute",
            "project:git:write"
        ]
    }
}
```

### Project-Level Roles (ReBAC)

```python
PROJECT_ROLE_PERMISSIONS = {
    "owner": [
        "project:*",
        "document:*",
        "ticket:*",
        "task:*"
    ],
    "maintainer": [
        "project:read",
        "project:write",
        "project:git:write",
        "document:*",
        "ticket:*",
        "task:*",
        "project:members:add",
        "project:members:remove"
    ],
    "contributor": [
        "project:read",
        "document:read",
        "document:write",
        "ticket:read",
        "ticket:write",
        "task:read",
        "task:write",
        "project:git:write"
    ],
    "viewer": [
        "project:read",
        "document:read",
        "ticket:read",
        "task:read"
    ]
}
```

## Authorization Service (Enhanced)

```python
from typing import Union, Dict, Tuple, Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

class AuthorizationService:
    """Hybrid authorization for users, agents, and super admins."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def is_authorized(
        self,
        actor_id: UUID,
        actor_type: ActorType,
        action: str,
        organization_id: UUID,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        resource_attributes: Optional[Dict] = None,
        context: Optional[Dict] = None,
    ) -> Tuple[bool, str, Dict]:
        """
        Unified authorization check for users and agents.
        
        Priority:
        1. Super Admin (users only) - bypass all checks
        2. Resource ownership (creator/owner)
        3. Project membership (ReBAC)
        4. Organization role (RBAC)
        5. Attribute policies (ABAC)
        6. Explicit deny policies
        """
        details = {
            "matched_policies": [],
            "matched_roles": [],
            "matched_grants": [],
            "evaluation_order": []
        }
        
        # 1. Check super admin (users only)
        if actor_type == ActorType.USER:
            user = await self._load_user(actor_id)
            if user and user.is_super_admin:
                details["evaluation_order"].append("super_admin")
                return True, "Authorized as super admin", details
        
        # 2. Check resource ownership
        ownership_check = await self._check_ownership(
            actor_id, actor_type, resource_type, resource_id
        )
        if ownership_check["allowed"]:
            details["evaluation_order"].append("ownership")
            return True, "Authorized as resource owner", details
        
        # 3. Check project membership (if resource is within a project)
        if resource_type in ["project", "document", "ticket", "task"]:
            project_id = await self._resolve_project_id(
                resource_type, resource_id
            )
            if project_id:
                project_check = await self._check_project_membership(
                    actor_id, actor_type, project_id, action
                )
                if project_check["allowed"]:
                    details["matched_roles"] = project_check["roles"]
                    details["evaluation_order"].append("project_membership")
                    return True, f"Authorized via project role", details
        
        # 4. Check organization role (RBAC)
        rbac_check = await self._check_org_rbac(
            actor_id, actor_type, organization_id, action
        )
        if rbac_check["allowed"]:
            details["matched_roles"] = rbac_check["roles"]
            details["evaluation_order"].append("org_role")
            return True, f"Authorized via organization role", details
        
        # 5. Check ABAC policies
        actor = await self._load_actor(actor_id, actor_type)
        abac_check = await self._check_abac(
            actor=actor,
            actor_type=actor_type,
            action=action,
            organization_id=organization_id,
            resource_type=resource_type,
            resource_attributes=resource_attributes or {},
            context=context or {}
        )
        if abac_check["allowed"]:
            details["matched_policies"] = abac_check["policies"]
            details["evaluation_order"].append("abac")
            return True, "Authorized via attribute policy", details
        
        # 6. Check explicit deny
        deny_check = await self._check_deny_policies(
            actor=actor,
            actor_type=actor_type,
            action=action,
            organization_id=organization_id,
            resource_type=resource_type,
            resource_attributes=resource_attributes or {},
            context=context or {}
        )
        if deny_check["denied"]:
            details["matched_policies"] = deny_check["policies"]
            return False, "Explicitly denied by policy", details
        
        return False, "No matching authorization found", details
    
    async def _load_user(self, user_id: UUID) -> Optional[User]:
        """Load user."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def _load_agent(self, agent_id: UUID) -> Optional[Agent]:
        """Load agent."""
        result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        return result.scalar_one_or_none()
    
    async def _load_actor(
        self,
        actor_id: UUID,
        actor_type: ActorType
    ) -> Union[User, Agent, None]:
        """Load user or agent."""
        if actor_type == ActorType.USER:
            return await self._load_user(actor_id)
        return await self._load_agent(actor_id)
    
    async def _check_ownership(
        self,
        actor_id: UUID,
        actor_type: ActorType,
        resource_type: Optional[str],
        resource_id: Optional[UUID]
    ) -> Dict:
        """Check if actor owns the resource."""
        if not resource_id or not resource_type:
            return {"allowed": False}
        
        # Map resource types to models and ownership fields
        ownership_map = {
            "project": (Project, "created_by"),
            "document": (Document, "created_by"),
            "ticket": (Ticket, "created_by"),
            "task": (Task, "created_by"),
        }
        
        if resource_type not in ownership_map:
            return {"allowed": False}
        
        model, owner_field = ownership_map[resource_type]
        
        # Only users can be owners (not agents)
        if actor_type != ActorType.USER:
            return {"allowed": False}
        
        result = await self.db.execute(
            select(model).where(
                model.id == resource_id,
                getattr(model, owner_field) == actor_id
            )
        )
        
        return {"allowed": result.scalar_one_or_none() is not None}
    
    async def _resolve_project_id(
        self,
        resource_type: str,
        resource_id: UUID
    ) -> Optional[UUID]:
        """Get project ID for a resource."""
        if resource_type == "project":
            return resource_id
        
        model_map = {
            "document": Document,
            "ticket": Ticket,
            "task": Task
        }
        
        if resource_type not in model_map:
            return None
        
        model = model_map[resource_type]
        
        # Special handling for tasks (need to go through ticket)
        if resource_type == "task":
            result = await self.db.execute(
                select(Task.ticket_id).where(Task.id == resource_id)
            )
            ticket_id = result.scalar_one_or_none()
            if not ticket_id:
                return None
            
            result = await self.db.execute(
                select(Ticket.project_id).where(Ticket.id == ticket_id)
            )
            return result.scalar_one_or_none()
        
        result = await self.db.execute(
            select(model.project_id).where(model.id == resource_id)
        )
        return result.scalar_one_or_none()
    
    async def _check_project_membership(
        self,
        actor_id: UUID,
        actor_type: ActorType,
        project_id: UUID,
        action: str
    ) -> Dict:
        """Check project-level permissions."""
        # Build query based on actor type
        if actor_type == ActorType.USER:
            query = select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == actor_id
            )
        else:
            query = select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.agent_id == actor_id
            )
        
        result = await self.db.execute(query)
        membership = result.scalar_one_or_none()
        
        if not membership:
            return {"allowed": False, "roles": []}
        
        # Check if role has permission
        role_permissions = PROJECT_ROLE_PERMISSIONS.get(membership.role, [])
        if self._has_permission(role_permissions, action):
            return {"allowed": True, "roles": [membership.role]}
        
        return {"allowed": False, "roles": []}
    
    async def _check_org_rbac(
        self,
        actor_id: UUID,
        actor_type: ActorType,
        organization_id: UUID,
        action: str
    ) -> Dict:
        """Check organization-level RBAC."""
        # Build query based on actor type
        if actor_type == ActorType.USER:
            query = select(OrganizationMembership).where(
                OrganizationMembership.user_id == actor_id,
                OrganizationMembership.organization_id == organization_id
            ).options(selectinload(OrganizationMembership.role))
        else:
            query = select(OrganizationMembership).where(
                OrganizationMembership.agent_id == actor_id,
                OrganizationMembership.organization_id == organization_id
            ).options(selectinload(OrganizationMembership.role))
        
        result = await self.db.execute(query)
        membership = result.scalar_one_or_none()
        
        if not membership:
            return {"allowed": False, "roles": []}
        
        role = membership.role
        if self._has_permission(role.permissions, action):
            return {"allowed": True, "roles": [role.name]}
        
        # Check parent roles
        if role.inherits_from:
            parent_check = await self._check_role_hierarchy(
                role.parent_role, action
            )
            if parent_check["allowed"]:
                return {
                    "allowed": True,
                    "roles": [role.name] + parent_check["roles"]
                }
        
        return {"allowed": False, "roles": []}
    
    def _check_role_hierarchy(self, role: Role, action: str) -> Dict:
        """Recursively check parent roles."""
        if self._has_permission(role.permissions, action):
            return {"allowed": True, "roles": [role.name]}
        
        if role.parent_role:
            parent_check = self._check_role_hierarchy(role.parent_role, action)
            if parent_check["allowed"]:
                return {
                    "allowed": True,
                    "roles": [role.name] + parent_check["roles"]
                }
        
        return {"allowed": False, "roles": []}
    
    def _has_permission(self, permissions: List[str], required: str) -> bool:
        """Check permission with wildcard support."""
        if "*:*" in permissions:  # Super admin wildcard
            return True
        
        if required in permissions:
            return True
        
        # Check wildcards
        parts = required.split(":")
        for i in range(len(parts)):
            wildcard = ":".join(parts[:i+1]) + ":*"
            if wildcard in permissions:
                return True
        
        return False
    
    async def _check_abac(
        self,
        actor: Union[User, Agent],
        actor_type: ActorType,
        action: str,
        organization_id: UUID,
        resource_type: Optional[str],
        resource_attributes: Dict,
        context: Dict
    ) -> Dict:
        """Check attribute-based policies."""
        result = await self.db.execute(
            select(Policy)
            .where(
                Policy.organization_id == organization_id,
                Policy.effect == "allow",
                Policy.is_active == True
            )
            .order_by(Policy.priority.desc())
        )
        policies = result.scalars().all()
        
        matched_policies = []
        actor_attrs = actor.attributes or {}
        
        # Add actor type to attributes
        actor_attrs["actor_type"] = actor_type.value
        
        for policy in policies:
            if action not in policy.actions and "*" not in policy.actions:
                continue
            
            if not self._evaluate_attributes(actor_attrs, policy.subjects):
                continue
            
            if resource_type and not self._match_resource_type(
                resource_type, policy.resources
            ):
                continue
            
            if not self._evaluate_attributes(
                resource_attributes,
                policy.resources.get("attributes", {})
            ):
                continue
            
            if policy.conditions:
                eval_context = {
                    "actor": actor_attrs,
                    "resource": resource_attributes,
                    **context
                }
                if not self._evaluate_conditions(policy.conditions, eval_context):
                    continue
            
            matched_policies.append(str(policy.id))
        
        return {
            "allowed": len(matched_policies) > 0,
            "policies": matched_policies
        }
    
    async def _check_deny_policies(
        self,
        actor: Union[User, Agent],
        actor_type: ActorType,
        action: str,
        organization_id: UUID,
        resource_type: Optional[str],
        resource_attributes: Dict,
        context: Dict
    ) -> Dict:
        """Check for explicit deny policies."""
        result = await self.db.execute(
            select(Policy)
            .where(
                Policy.organization_id == organization_id,
                Policy.effect == "deny",
                Policy.is_active == True
            )
            .order_by(Policy.priority.desc())
        )
        policies = result.scalars().all()
        
        actor_attrs = (actor.attributes or {}).copy()
        actor_attrs["actor_type"] = actor_type.value
        
        for policy in policies:
            if action not in policy.actions and "*" not in policy.actions:
                continue
            
            if not self._evaluate_attributes(actor_attrs, policy.subjects):
                continue
            
            if resource_type and not self._match_resource_type(
                resource_type, policy.resources
            ):
                continue
            
            if not self._evaluate_attributes(
                resource_attributes,
                policy.resources.get("attributes", {})
            ):
                continue
            
            if policy.conditions:
                eval_context = {
                    "actor": actor_attrs,
                    "resource": resource_attributes,
                    **context
                }
                if not self._evaluate_conditions(policy.conditions, eval_context):
                    continue
            
            return {"denied": True, "policies": [str(policy.id)]}
        
        return {"denied": False, "policies": []}
    
    def _evaluate_attributes(self, actual: Dict, required: Dict) -> bool:
        """Evaluate attribute constraints."""
        for key, constraint in required.items():
            actual_value = actual.get(key)
            
            if isinstance(constraint, list):
                if actual_value not in constraint:
                    return False
            elif isinstance(constraint, dict):
                if not self._evaluate_comparison(actual_value, constraint):
                    return False
            else:
                if actual_value != constraint:
                    return False
        
        return True
    
    def _evaluate_comparison(self, value, operators: Dict) -> bool:
        """Evaluate comparison operators."""
        for op, target in operators.items():
            if op == "==" and value != target:
                return False
            elif op == "!=" and value == target:
                return False
            elif op == ">" and value <= target:
                return False
            elif op == ">=" and value < target:
                return False
            elif op == "<" and value >= target:
                return False
            elif op == "<=" and value > target:
                return False
            elif op == "in" and value not in target:
                return False
            elif op == "not_in" and value in target:
                return False
        
        return True
    
    def _match_resource_type(self, actual: str, constraint: Dict) -> bool:
        """Check resource type match."""
        required_type = constraint.get("type")
        if not required_type:
            return True
        
        if isinstance(required_type, list):
            return actual in required_type
        
        return actual == required_type
    
    def _evaluate_conditions(self, conditions: Dict, context: Dict) -> bool:
        """Evaluate environmental conditions."""
        for key, constraint in conditions.items():
            value = context
            for part in key.split("."):
                value = value.get(part)
                if value is None:
                    return False
            
            if isinstance(constraint, dict):
                if not self._evaluate_comparison(value, constraint):
                    return False
            else:
                if value != constraint:
                    return False
        
        return True
```

## Example ABAC Policies

### 1. Agent Execution Policy

```json
{
  "name": "Allow AI Agents to Execute Tasks",
  "effect": "allow",
  "priority": 100,
  "subjects": {
    "actor_type": ["agent"]
  },
  "resources": {
    "type": "task",
    "attributes.status": ["todo", "in_progress"]
  },
  "actions": ["task:write", "task:status:update", "task:complete:execute"]
}
```

### 2. Department-Based Project Access

```json
{
  "name": "Engineering Department Project Access",
  "effect": "allow",
  "subjects": {
    "department": ["engineering"],
    "actor_type": ["user"]
  },
  "resources": {
    "type": "project",
    "attributes.department": ["engineering"]
  },
  "actions": ["project:read", "project:write"]
}
```

### 3. Block Agents from Sensitive Docs

```json
{
  "name": "Block Agents from Confidential Requirements",
  "effect": "deny",
  "priority": 1000,
  "subjects": {
    "actor_type": ["agent"]
  },
  "resources": {
    "type": "document",
    "attributes.doc_type": ["requirements"],
    "attributes.sensitivity": ["confidential"]
  },
  "actions": ["*"]
}
```

## FastAPI Dependency

```python
from fastapi import Depends, HTTPException, status, Header
from typing import Union

async def get_current_actor(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db)
) -> Tuple[Union[User, Agent], ActorType]:
    """
    Extract and authenticate actor (user or agent) from token.
    
    Supports:
    - Bearer {jwt_token} for users
    - Bearer {api_key} for users/agents
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
    
    token = authorization[7:]
    
    # Try JWT first (users only)
    try:
        user = await authenticate_jwt(token, db)
        if user:
            return user, ActorType.USER
    except:
        pass
    
    # Try API key (users or agents)
    actor, actor_type = await authenticate_api_key(token, db)
    if actor:
        return actor, actor_type
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )

async def require_authorization(
    action: str,
    organization_id: UUID,
    resource_type: Optional[str] = None,
    resource_id: Optional[UUID] = None,
):
    """
    Dependency factory for authorization checks.
    
    Usage:
        @app.get("/projects/{project_id}")
        async def get_project(
            project_id: UUID,
            auth: None = Depends(
                require_authorization(
                    action="project:read",
                    organization_id=org_id,
                    resource_type="project",
                    resource_id=project_id
                )
            )
        ):
            ...
    """
    async def _check_auth(
        actor_and_type: Tuple[Union[User, Agent], ActorType] = Depends(get_current_actor),
        db: AsyncSession = Depends(get_db)
    ):
        actor, actor_type = actor_and_type
        auth_service = AuthorizationService(db)
        
        allowed, reason, details = await auth_service.is_authorized(
            actor_id=actor.id,
            actor_type=actor_type,
            action=action,
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=resource_id
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Unauthorized",
                    "reason": reason,
                    "details": details
                }
            )
        
        return details
    
    return _check_auth
```

## Database Indexes

```sql
-- Users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_department ON users(department);
CREATE INDEX idx_users_super_admin ON users(is_super_admin) WHERE is_super_admin = true;

-- Agents
CREATE INDEX idx_agents_type ON agents(agent_type);
CREATE INDEX idx_agents_active ON agents(is_active) WHERE is_active = true;

-- Organizations
CREATE INDEX idx_organizations_slug ON organizations(slug);
CREATE INDEX idx_organizations_owner ON organizations(owner_id);

-- Projects
CREATE INDEX idx_projects_org ON projects(organization_id);
CREATE INDEX idx_projects_org_slug ON projects(organization_id, slug);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_creator ON projects(created_by);

-- Project Members
CREATE INDEX idx_project_members_project ON project_members(project_id);
CREATE INDEX idx_project_members_user ON project_members(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_project_members_agent ON project_members(agent_id) WHERE agent_id IS NOT NULL;

-- Documents
CREATE INDEX idx_documents_project ON documents(project_id);
CREATE INDEX idx_documents_type ON documents(doc_type);
CREATE INDEX idx_documents_published ON documents(is_published);

-- Tickets
CREATE INDEX idx_tickets_project ON tickets(project_id);
CREATE INDEX idx_tickets_project_number ON tickets(project_id, ticket_number);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_assignee ON tickets(assigned_to);
CREATE INDEX idx_tickets_creator ON tickets(created_by);

-- Tasks
CREATE INDEX idx_tasks_ticket ON tasks(ticket_id);
CREATE INDEX idx_tasks_status ON tasks(status);

-- Task Assignments
CREATE INDEX idx_task_assignments_task ON task_assignments(task_id);
CREATE INDEX idx_task_assignments_user ON task_assignments(assignee_id) WHERE assignee_id IS NOT NULL;
CREATE INDEX idx_task_assignments_agent ON task_assignments(agent_id) WHERE agent_id IS NOT NULL;

-- Policies
CREATE INDEX idx_policies_org_active ON policies(organization_id, is_active);
CREATE INDEX idx_policies_priority ON policies(priority DESC);

-- API Keys
CREATE INDEX idx_api_keys_user ON api_keys(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_api_keys_agent ON api_keys(agent_id) WHERE agent_id IS NOT NULL;
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX idx_api_keys_hash ON api_keys(hashed_key);
```

## Seed Data Script

```python
async def seed_system_data(db: AsyncSession):
    """Initialize system roles and example agents."""
    
    # Create system roles
    for role_name, role_config in SYSTEM_ROLES.items():
        if role_config.get("is_global"):
            continue  # Skip super_admin, it's a user flag
        
        role = Role(
            name=role_name,
            description=role_config["description"],
            permissions=role_config["permissions"],
            role_type=RoleType.SYSTEM,
            organization_id=None
        )
        db.add(role)
    
    await db.commit()
    
    # Create example agent types
    agent_templates = [
        {
            "name": "Code Generator",
            "agent_type": "coding",
            "capabilities": ["python", "javascript", "typescript", "rust"],
            "description": "AI agent specialized in code generation"
        },
        {
            "name": "Test Engineer",
            "agent_type": "testing",
            "capabilities": ["unit_testing", "integration_testing", "pytest"],
            "description": "AI agent specialized in test creation"
        },
        {
            "name": "Design Analyst",
            "agent_type": "design",
            "capabilities": ["architecture", "uml", "documentation"],
            "description": "AI agent specialized in system design"
        }
    ]
    
    for template in agent_templates:
        agent = Agent(**template)
        db.add(agent)
    
    await db.commit()
```

## Next Steps

1. **Implement git integration** - webhooks, branch protection, PR automation
2. **Add real-time task updates** - WebSocket for agent progress
3. **Create agent orchestration system** - task assignment algorithms
4. **Build audit logging** - comprehensive activity tracking
5. **Add notification system** - task assignments, completions, mentions

## Questions

**Git provider preference?** (GitHub, GitLab, Bitbucket) - affects webhook structure

**Agent authentication flow?** (Pre-created agents vs dynamic agent spawning)

**Task decomposition strategy?** (Manual vs AI-assisted ticket → task breakdown)



## Response:
11/19/2025, 8:52:13 AM

I'll update the design document to include GitHub integration, dynamic agent spawning with lifecycle management, and AI-assisted task decomposition.

```markdown:docs/auth-org-design.md
# Organization & Authentication Design Document

## System Overview

A multi-tenant authentication and authorization system for AI-assisted project management with dynamic agent orchestration, GitHub integration, and intelligent task decomposition.

**Domain Hierarchy:**
```
Organizations
  ├─ Members (Users + Dynamic Agents with Roles)
  └─ Projects
      ├─ GitHub Repositories (Webhooks, PR automation)
      ├─ Documents (Designs, Requirements)
      └─ Tickets (AI-decomposed into Tasks)
          └─ Tasks (Assigned to dynamically spawned Agents)
```

**Key Features:**
- Dynamic agent spawning for task execution
- GitHub webhook integration for git events
- AI-assisted ticket → task decomposition
- Hybrid authorization (RBAC + ABAC + ReBAC)

## Core Entities

### 1. User (Enhanced with Agent Management)

```python
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum as PyEnum
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime

class ActorType(PyEnum):
    USER = "user"
    AGENT = "agent"

class User(Base):
    __tablename__ = "users"
    
    # Identity
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
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
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), 
        onupdate=func.now()
    )
    last_login_at: Mapped[Optional[datetime]]
    
    # Relationships
    memberships: Mapped[List["OrganizationMembership"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="OrganizationMembership.user_id"
    )
    owned_organizations: Mapped[List["Organization"]] = relationship(
        back_populates="owner",
        foreign_keys="Organization.owner_id"
    )
    api_keys: Mapped[List["APIKey"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    sessions: Mapped[List["Session"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    created_projects: Mapped[List["Project"]] = relationship(
        back_populates="creator",
        foreign_keys="Project.created_by"
    )
    assigned_tasks: Mapped[List["TaskAssignment"]] = relationship(
        back_populates="assignee",
        foreign_keys="TaskAssignment.assignee_id"
    )
    created_tickets: Mapped[List["Ticket"]] = relationship(
        back_populates="creator",
        foreign_keys="Ticket.created_by"
    )
    spawned_agents: Mapped[List["Agent"]] = relationship(
        back_populates="spawned_by_user",
        foreign_keys="Agent.spawned_by"
    )
```

### 2. Agent (Enhanced for Dynamic Lifecycle)

```python
class AgentStatus(PyEnum):
    SPAWNING = "spawning"      # Being created
    IDLE = "idle"              # Ready for tasks
    WORKING = "working"        # Executing task
    SUSPENDED = "suspended"    # Paused
    TERMINATING = "terminating"  # Shutting down
    TERMINATED = "terminated"  # Shut down

class AgentType(PyEnum):
    CODE_GENERATOR = "code_generator"
    TEST_ENGINEER = "test_engineer"
    CODE_REVIEWER = "code_reviewer"
    DOCUMENTATION = "documentation"
    TASK_DECOMPOSER = "task_decomposer"
    DEVOPS = "devops"
    GENERAL = "general"

class Agent(Base):
    __tablename__ = "agents"
    
    # Identity
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
    agent_type: Mapped[str] = mapped_column(
        String(50),
        index=True
    )
    
    # Lifecycle
    status: Mapped[str] = mapped_column(
        String(50),
        default=AgentStatus.SPAWNING.value,
        index=True
    )
    spawned_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    project_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True
    )
    
    # Configuration
    model_config: Mapped[dict] = mapped_column(JSONB)  # LLM model, temperature, etc.
    capabilities: Mapped[List[str]] = mapped_column(JSONB)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text)
    attributes: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Resource Limits
    max_concurrent_tasks: Mapped[int] = mapped_column(Integer, default=1)
    timeout_minutes: Mapped[int] = mapped_column(Integer, default=60)
    
    # Execution Context
    current_task_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("tasks.id"))
    execution_context: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Metrics
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    tasks_failed: Mapped[int] = mapped_column(Integer, default=0)
    total_execution_time_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Auto-termination
    auto_terminate_after_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    terminate_when_idle: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    last_active_at: Mapped[Optional[datetime]]
    terminated_at: Mapped[Optional[datetime]]
    
    # Relationships
    spawned_by_user: Mapped["User"] = relationship(
        back_populates="spawned_agents",
        foreign_keys=[spawned_by]
    )
    organization: Mapped["Organization"] = relationship()
    project: Mapped[Optional["Project"]] = relationship()
    memberships: Mapped[List["OrganizationMembership"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
        foreign_keys="OrganizationMembership.agent_id"
    )
    api_keys: Mapped[List["APIKey"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan"
    )
    assigned_tasks: Mapped[List["TaskAssignment"]] = relationship(
        back_populates="agent_assignee",
        foreign_keys="TaskAssignment.agent_id"
    )
    current_task: Mapped[Optional["Task"]] = relationship(
        foreign_keys=[current_task_id]
    )
    execution_logs: Mapped[List["AgentExecutionLog"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan"
    )
```

### 3. AgentExecutionLog (NEW - Track Agent Activity)

```python
class LogLevel(PyEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

class AgentExecutionLog(Base):
    __tablename__ = "agent_execution_logs"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        index=True
    )
    task_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        index=True
    )
    
    # Log Entry
    level: Mapped[str] = mapped_column(String(20), index=True)
    message: Mapped[str] = mapped_column(Text)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Context
    action: Mapped[Optional[str]] = mapped_column(String(100))  # "code_generation", "git_commit"
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        index=True
    )
    
    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="execution_logs")
    task: Mapped[Optional["Task"]] = relationship()
```

### 4. Organization (Unchanged)

```python
class Organization(Base):
    __tablename__ = "organizations"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Ownership
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    
    # Settings
    billing_email: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSONB)
    attributes: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    owner: Mapped["User"] = relationship(
        back_populates="owned_organizations",
        foreign_keys=[owner_id]
    )
    memberships: Mapped[List["OrganizationMembership"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    roles: Mapped[List["Role"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    policies: Mapped[List["Policy"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    projects: Mapped[List["Project"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
```

### 5. Project (Enhanced with GitHub Integration)

```python
class ProjectStatus(PyEnum):
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class Project(Base):
    __tablename__ = "projects"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    
    # Basic Info
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(50),
        default=ProjectStatus.PLANNING.value,
        index=True
    )
    
    # GitHub Integration
    github_repo_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True)  # GitHub's repo ID
    github_repo_full_name: Mapped[Optional[str]] = mapped_column(String(255))  # "owner/repo"
    github_default_branch: Mapped[str] = mapped_column(String(255), default="main")
    github_installation_id: Mapped[Optional[int]] = mapped_column(BigInteger)  # GitHub App installation
    github_webhook_secret: Mapped[Optional[str]] = mapped_column(String(255))
    github_config: Mapped[Optional[dict]] = mapped_column(JSONB)  # Additional settings
    
    # ABAC Attributes
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # Ownership
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship(
        back_populates="projects"
    )
    creator: Mapped["User"] = relationship(
        back_populates="created_projects",
        foreign_keys=[created_by]
    )
    documents: Mapped[List["Document"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan"
    )
    tickets: Mapped[List["Ticket"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan"
    )
    team_members: Mapped[List["ProjectMember"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan"
    )
    github_events: Mapped[List["GitHubWebhookEvent"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_org_project_slug", "organization_id", "slug", unique=True),
        Index("idx_github_repo", "github_repo_id", unique=True, 
              postgresql_where=text("github_repo_id IS NOT NULL")),
    )
```

### 6. GitHubWebhookEvent (NEW - Track GitHub Events)

```python
class GitHubEventType(PyEnum):
    PUSH = "push"
    PULL_REQUEST = "pull_request"
    PULL_REQUEST_REVIEW = "pull_request_review"
    ISSUE_COMMENT = "issue_comment"
    COMMIT_COMMENT = "commit_comment"
    CHECK_RUN = "check_run"
    CHECK_SUITE = "check_suite"
    STATUS = "status"
    WORKFLOW_RUN = "workflow_run"

class GitHubWebhookEvent(Base):
    __tablename__ = "github_webhook_events"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True
    )
    
    # Event Details
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    github_delivery_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    action: Mapped[Optional[str]] = mapped_column(String(50))  # opened, closed, synchronize
    
    # Payload
    payload: Mapped[dict] = mapped_column(JSONB)
    
    # Processing
    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    processed_at: Mapped[Optional[datetime]]
    processing_result: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # References
    related_ticket_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("tickets.id", ondelete="SET NULL")
    )
    related_task_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL")
    )
    
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        index=True
    )
    
    # Relationships
    project: Mapped["Project"] = relationship(back_populates="github_events")
    related_ticket: Mapped[Optional["Ticket"]] = relationship()
    related_task: Mapped[Optional["Task"]] = relationship()
```

### 7. Ticket (Enhanced with Decomposition)

```python
class TicketType(PyEnum):
    FEATURE = "feature"
    BUG = "bug"
    IMPROVEMENT = "improvement"
    TASK = "task"

class TicketStatus(PyEnum):
    BACKLOG = "backlog"
    DECOMPOSING = "decomposing"  # NEW: AI is breaking down into tasks
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CLOSED = "closed"

class TicketPriority(PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class Ticket(Base):
    __tablename__ = "tickets"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True
    )
    
    # Identification
    ticket_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Classification
    ticket_type: Mapped[str] = mapped_column(
        String(50),
        default=TicketType.TASK.value,
        index=True
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=TicketStatus.BACKLOG.value,
        index=True
    )
    priority: Mapped[str] = mapped_column(
        String(50),
        default=TicketPriority.MEDIUM.value,
        index=True
    )
    
    # AI Decomposition
    decomposed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    decomposition_agent_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL")
    )
    decomposition_prompt: Mapped[Optional[str]] = mapped_column(Text)
    decomposition_context: Mapped[Optional[dict]] = mapped_column(JSONB)
    decomposed_at: Mapped[Optional[datetime]]
    
    # GitHub Integration
    github_issue_number: Mapped[Optional[int]] = mapped_column(Integer)
    branch_name: Mapped[Optional[str]] = mapped_column(String(255))
    pull_request_number: Mapped[Optional[int]] = mapped_column(Integer)
    pull_request_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # ABAC Attributes
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # Relationships
    parent_ticket_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("tickets.id", ondelete="SET NULL")
    )
    
    # Ownership
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    assigned_to: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    due_date: Mapped[Optional[datetime]]
    
    # Relationships
    project: Mapped["Project"] = relationship(back_populates="tickets")
    creator: Mapped["User"] = relationship(
        back_populates="created_tickets",
        foreign_keys=[created_by]
    )
    assignee: Mapped[Optional["User"]] = relationship(foreign_keys=[assigned_to])
    parent_ticket: Mapped[Optional["Ticket"]] = relationship(
        remote_side=[id],
        backref="sub_tickets"
    )
    tasks: Mapped[List["Task"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="Task.position"
    )
    decomposition_agent: Mapped[Optional["Agent"]] = relationship(
        foreign_keys=[decomposition_agent_id]
    )
    
    __table_args__ = (
        Index("idx_project_ticket_number", "project_id", "ticket_number", unique=True),
        Index("idx_github_issue", "project_id", "github_issue_number",
              postgresql_where=text("github_issue_number IS NOT NULL")),
    )
```

### 8. Task (Enhanced with Agent Execution)

```python
class TaskStatus(PyEnum):
    TODO = "todo"
    ASSIGNED = "assigned"       # Assigned to agent
    IN_PROGRESS = "in_progress"  # Agent working
    BLOCKED = "blocked"
    IN_REVIEW = "in_review"     # Code review
    DONE = "done"
    FAILED = "failed"           # Agent failed

class Task(Base):
    __tablename__ = "tasks"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),
        index=True
    )
    
    # Content
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(50),
        default=TaskStatus.TODO.value,
        index=True
    )
    
    # AI Generation Context
    generated_by_ai: Mapped[bool] = mapped_column(Boolean, default=False)
    generation_context: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Ordering
    position: Mapped[int] = mapped_column(Integer, default=0)
    
    # Dependencies
    depends_on_task_ids: Mapped[Optional[List[UUID]]] = mapped_column(JSONB)
    
    # Execution Details
    task_type: Mapped[Optional[str]] = mapped_column(String(50))  # "code", "test", "review"
    required_capabilities: Mapped[Optional[List[str]]] = mapped_column(JSONB)
    
    # GitHub Integration
    file_paths: Mapped[Optional[List[str]]] = mapped_column(JSONB)
    commit_sha: Mapped[Optional[str]] = mapped_column(String(40))
    github_branch: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Agent Execution
    execution_instructions: Mapped[Optional[str]] = mapped_column(Text)
    execution_result: Mapped[Optional[dict]] = mapped_column(JSONB)
    execution_error: Mapped[Optional[str]] = mapped_column(Text)
    
    # ABAC Attributes
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # Estimation
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float)
    actual_hours: Mapped[Optional[float]] = mapped_column(Float)
    
    # Ownership
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    started_at: Mapped[Optional[datetime]]
    completed_at: Mapped[Optional[datetime]]
    
    # Relationships
    ticket: Mapped["Ticket"] = relationship(back_populates="tasks")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    assignments: Mapped[List["TaskAssignment"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan"
    )
```

### 9. TaskAssignment (Unchanged)

```python
class TaskAssignment(Base):
    __tablename__ = "task_assignments"
    __table_args__ = (
        CheckConstraint(
            '(assignee_id IS NOT NULL AND agent_id IS NULL) OR '
            '(assignee_id IS NULL AND agent_id IS NOT NULL)',
            name='check_assignee_user_or_agent'
        ),
        Index("idx_user_task", "assignee_id", "task_id",
              unique=True, postgresql_where=text("assignee_id IS NOT NULL")),
        Index("idx_agent_task", "agent_id", "task_id",
              unique=True, postgresql_where=text("agent_id IS NOT NULL")),
    )
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        index=True
    )
    
    # Assignee (user OR agent)
    assignee_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    agent_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE")
    )
    
    # Metadata
    assigned_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    assigned_at: Mapped[datetime] = mapped_column(server_default=func.now())
    started_at: Mapped[Optional[datetime]]
    completed_at: Mapped[Optional[datetime]]
    
    # Relationships
    task: Mapped["Task"] = relationship(back_populates="assignments")
    assignee: Mapped[Optional["User"]] = relationship(
        back_populates="assigned_tasks",
        foreign_keys=[assignee_id]
    )
    agent_assignee: Mapped[Optional["Agent"]] = relationship(
        back_populates="assigned_tasks",
        foreign_keys=[agent_id]
    )
```

## Agent Orchestration Service

### Dynamic Agent Spawning

```python
from typing import Optional, Dict, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

class AgentOrchestrator:
    """Manages dynamic agent lifecycle and task assignment."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def spawn_agent(
        self,
        agent_type: AgentType,
        spawned_by: UUID,
        organization_id: UUID,
        project_id: Optional[UUID] = None,
        name: Optional[str] = None,
        model_config: Optional[Dict] = None,
        capabilities: Optional[List[str]] = None,
        auto_terminate_minutes: Optional[int] = 120,
    ) -> Agent:
        """
        Spawn a new agent instance.
        
        Args:
            agent_type: Type of agent to spawn
            spawned_by: User ID who spawned the agent
            organization_id: Organization context
            project_id: Optional project scope
            name: Custom agent name
            model_config: LLM configuration
            capabilities: Agent capabilities
            auto_terminate_minutes: Auto-terminate after inactivity
        
        Returns:
            Agent instance
        """
        # Generate agent name if not provided
        if not name:
            name = f"{agent_type.value}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        # Default model config
        if not model_config:
            model_config = {
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.7,
                "max_tokens": 8000
            }
        
        # Default capabilities based on type
        if not capabilities:
            capabilities = self._get_default_capabilities(agent_type)
        
        # Create agent
        agent = Agent(
            name=name,
            agent_type=agent_type.value,
            status=AgentStatus.SPAWNING.value,
            spawned_by=spawned_by,
            organization_id=organization_id,
            project_id=project_id,
            model_config=model_config,
            capabilities=capabilities,
            auto_terminate_after_minutes=auto_terminate_minutes,
            system_prompt=self._get_system_prompt(agent_type)
        )
        
        self.db.add(agent)
        await self.db.flush()
        
        # Generate API key for agent
        api_key = await self._create_agent_api_key(agent.id, organization_id)
        
        # Add agent to organization with appropriate role
        await self._add_agent_to_org(agent.id, organization_id)
        
        # If project-scoped, add to project
        if project_id:
            await self._add_agent_to_project(agent.id, project_id)
        
        # Log spawn event
        log = AgentExecutionLog(
            agent_id=agent.id,
            level=LogLevel.INFO.value,
            message=f"Agent spawned by user {spawned_by}",
            action="spawn",
            metadata={
                "agent_type": agent_type.value,
                "capabilities": capabilities
            }
        )
        self.db.add(log)
        
        # Update status to idle
        agent.status = AgentStatus.IDLE.value
        agent.last_active_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(agent)
        
        return agent
    
    def _get_default_capabilities(self, agent_type: AgentType) -> List[str]:
        """Get default capabilities for agent type."""
        capability_map = {
            AgentType.CODE_GENERATOR: ["python", "javascript", "typescript", "git"],
            AgentType.TEST_ENGINEER: ["pytest", "jest", "unittest", "integration_testing"],
            AgentType.CODE_REVIEWER: ["code_review", "static_analysis", "security_scan"],
            AgentType.DOCUMENTATION: ["markdown", "technical_writing", "api_docs"],
            AgentType.TASK_DECOMPOSER: ["task_analysis", "planning", "estimation"],
            AgentType.DEVOPS: ["docker", "ci_cd", "deployment", "monitoring"],
            AgentType.GENERAL: ["general_purpose"]
        }
        return capability_map.get(agent_type, ["general_purpose"])
    
    def _get_system_prompt(self, agent_type: AgentType) -> str:
        """Get system prompt for agent type."""
        prompts = {
            AgentType.CODE_GENERATOR: """You are a code generation agent. Your role is to:
1. Write clean, well-documented code based on task specifications
2. Follow project coding standards and best practices
3. Create comprehensive unit tests
4. Commit your changes with clear commit messages
5. Report your progress and any blockers""",
            
            AgentType.TEST_ENGINEER: """You are a test engineering agent. Your role is to:
1. Write comprehensive test suites (unit, integration, e2e)
2. Achieve high code coverage
3. Identify edge cases and error conditions
4. Create test data and fixtures
5. Report test results and coverage metrics""",
            
            AgentType.CODE_REVIEWER: """You are a code review agent. Your role is to:
1. Review code for correctness, efficiency, and maintainability
2. Check adherence to coding standards
3. Identify potential bugs and security issues
4. Suggest improvements and optimizations
5. Approve or request changes with clear feedback""",
            
            AgentType.TASK_DECOMPOSER: """You are a task decomposition agent. Your role is to:
1. Analyze high-level tickets and requirements
2. Break down complex work into manageable tasks
3. Identify dependencies between tasks
4. Estimate effort and complexity
5. Assign appropriate task types and required capabilities"""
        }
        return prompts.get(agent_type, "You are a general-purpose AI agent.")
    
    async def _create_agent_api_key(
        self,
        agent_id: UUID,
        organization_id: UUID
    ) -> str:
        """Create API key for agent."""
        import secrets
        
        # Generate key
        key = f"sk_agent_{secrets.token_urlsafe(32)}"
        prefix = key[:16]
        
        # Hash key
        import hashlib
        hashed = hashlib.sha256(key.encode()).hexdigest()
        
        api_key = APIKey(
            agent_id=agent_id,
            organization_id=organization_id,
            name=f"Agent API Key",
            key_prefix=prefix,
            hashed_key=hashed,
            scopes=["agent:execute"]
        )
        
        self.db.add(api_key)
        return key
    
    async def _add_agent_to_org(
        self,
        agent_id: UUID,
        organization_id: UUID
    ):
        """Add agent to organization with executor role."""
        # Get agent_executor role
        result = await self.db.execute(
            select(Role).where(
                Role.name == "agent_executor",
                Role.role_type == RoleType.SYSTEM.value
            )
        )
        role = result.scalar_one()
        
        membership = OrganizationMembership(
            agent_id=agent_id,
            organization_id=organization_id,
            role_id=role.id
        )
        self.db.add(membership)
    
    async def _add_agent_to_project(
        self,
        agent_id: UUID,
        project_id: UUID
    ):
        """Add agent to project as contributor."""
        # Get project to find who to attribute as added_by
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one()
        
        project_member = ProjectMember(
            project_id=project_id,
            agent_id=agent_id,
            role=ProjectRole.CONTRIBUTOR.value,
            added_by=project.created_by
        )
        self.db.add(project_member)
    
    async def assign_task_to_agent(
        self,
        task_id: UUID,
        agent_id: UUID,
        assigned_by: UUID
    ) -> TaskAssignment:
        """Assign a task to an agent."""
        # Verify agent is idle or has capacity
        result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one()
        
        if agent.status not in [AgentStatus.IDLE.value, AgentStatus.WORKING.value]:
            raise ValueError(f"Agent is {agent.status}, cannot assign task")
        
        # Count current tasks
        result = await self.db.execute(
            select(func.count(TaskAssignment.id))
            .where(
                TaskAssignment.agent_id == agent_id,
                TaskAssignment.completed_at.is_(None)
            )
        )
        current_tasks = result.scalar()
        
        if current_tasks >= agent.max_concurrent_tasks:
            raise ValueError(f"Agent at max capacity ({agent.max_concurrent_tasks} tasks)")
        
        # Create assignment
        assignment = TaskAssignment(
            task_id=task_id,
            agent_id=agent_id,
            assigned_by=assigned_by,
            assigned_at=datetime.utcnow()
        )
        self.db.add(assignment)
        
        # Update task status
        result = await self.db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one()
        task.status = TaskStatus.ASSIGNED.value
        
        # Update agent
        agent.status = AgentStatus.WORKING.value
        agent.current_task_id = task_id
        agent.last_active_at = datetime.utcnow()
        
        # Log assignment
        log = AgentExecutionLog(
            agent_id=agent_id,
            task_id=task_id,
            level=LogLevel.INFO.value,
            message=f"Task '{task.title}' assigned to agent",
            action="task_assigned",
            metadata={"assigned_by": str(assigned_by)}
        )
        self.db.add(log)
        
        await self.db.commit()
        return assignment
    
    async def complete_task_execution(
        self,
        agent_id: UUID,
        task_id: UUID,
        success: bool,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
        duration_seconds: Optional[float] = None
    ):
        """Mark task execution as complete."""
        # Get assignment
        result_query = await self.db.execute(
            select(TaskAssignment)
            .where(
                TaskAssignment.agent_id == agent_id,
                TaskAssignment.task_id == task_id
            )
        )
        assignment = result_query.scalar_one()
        
        # Update assignment
        assignment.completed_at = datetime.utcnow()
        
        # Get task
        task_result = await self.db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = task_result.scalar_one()
        
        # Update task
        if success:
            task.status = TaskStatus.DONE.value
            task.execution_result = result
            task.completed_at = datetime.utcnow()
        else:
            task.status = TaskStatus.FAILED.value
            task.execution_error = error
        
        # Calculate actual hours
        if assignment.started_at:
            elapsed = datetime.utcnow() - assignment.started_at
            task.actual_hours = elapsed.total_seconds() / 3600
        
        # Get agent
        agent_result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = agent_result.scalar_one()
        
        # Update agent metrics
        if success:
            agent.tasks_completed += 1
        else:
            agent.tasks_failed += 1
        
        if duration_seconds:
            agent.total_execution_time_minutes += duration_seconds / 60
        
        agent.current_task_id = None
        agent.last_active_at = datetime.utcnow()
        
        # Check if agent has more tasks
        pending_tasks = await self.db.execute(
            select(func.count(TaskAssignment.id))
            .where(
                TaskAssignment.agent_id == agent_id,
                TaskAssignment.completed_at.is_(None)
            )
        )
        
        if pending_tasks.scalar() == 0:
            agent.status = AgentStatus.IDLE.value
        
        # Log completion
        log = AgentExecutionLog(
            agent_id=agent_id,
            task_id=task_id,
            level=LogLevel.INFO.value if success else LogLevel.ERROR.value,
            message=f"Task execution {'completed' if success else 'failed'}",
            action="task_completed",
            duration_seconds=duration_seconds,
            metadata={
                "success": success,
                "result": result,
                "error": error
            }
        )
        self.db.add(log)
        
        await self.db.commit()
    
    async def terminate_agent(
        self,
        agent_id: UUID,
        reason: str = "manual"
    ):
        """Terminate an agent."""
        result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one()
        
        # Check for incomplete tasks
        pending = await self.db.execute(
            select(TaskAssignment)
            .where(
                TaskAssignment.agent_id == agent_id,
                TaskAssignment.completed_at.is_(None)
            )
        )
        
        if pending.scalars().first():
            raise ValueError("Cannot terminate agent with pending tasks")
        
        # Update status
        agent.status = AgentStatus.TERMINATED.value
        agent.terminated_at = datetime.utcnow()
        
        # Revoke API keys
        await self.db.execute(
            update(APIKey)
            .where(APIKey.agent_id == agent_id)
            .values(is_active=False)
        )
        
        # Log termination
        log = AgentExecutionLog(
            agent_id=agent_id,
            level=LogLevel.INFO.value,
            message=f"Agent terminated: {reason}",
            action="terminate"
        )
        self.db.add(log)
        
        await self.db.commit()
    
    async def cleanup_idle_agents(
        self,
        organization_id: UUID,
        idle_threshold_minutes: int = 120
    ):
        """Terminate agents that have been idle too long."""
        threshold = datetime.utcnow() - timedelta(minutes=idle_threshold_minutes)
        
        result = await self.db.execute(
            select(Agent)
            .where(
                Agent.organization_id == organization_id,
                Agent.status == AgentStatus.IDLE.value,
                Agent.terminate_when_idle == True,
                Agent.last_active_at < threshold
            )
        )
        
        idle_agents = result.scalars().all()
        
        for agent in idle_agents:
            try:
                await self.terminate_agent(agent.id, reason="idle_timeout")
            except Exception as e:
                print(f"Error terminating agent {agent.id}: {e}")
```

## Task Decomposition Service

```python
class TaskDecompositionService:
    """AI-assisted ticket to task decomposition."""
    
    def __init__(self, db: AsyncSession, orchestrator: AgentOrchestrator):
        self.db = db
        self.orchestrator = orchestrator
    
    async def decompose_ticket(
        self,
        ticket_id: UUID,
        user_id: UUID,
        custom_instructions: Optional[str] = None
    ) -> List[Task]:
        """
        Decompose a ticket into granular tasks using AI.
        
        Args:
            ticket_id: Ticket to decompose
            user_id: User requesting decomposition
            custom_instructions: Additional context for decomposition
        
        Returns:
            List of created tasks
        """
        # Get ticket with project context
        result = await self.db.execute(
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .options(
                selectinload(Ticket.project).selectinload(Project.documents)
            )
        )
        ticket = result.scalar_one()
        
        if ticket.decomposed:
            raise ValueError("Ticket already decomposed")
        
        # Update ticket status
        ticket.status = TicketStatus.DECOMPOSING.value
        await self.db.commit()
        
        # Spawn decomposer agent
        agent = await self.orchestrator.spawn_agent(
            agent_type=AgentType.TASK_DECOMPOSER,
            spawned_by=user_id,
            organization_id=ticket.project.organization_id,
            project_id=ticket.project_id,
            auto_terminate_minutes=30
        )
        
        # Build decomposition context
        context = await self._build_decomposition_context(ticket)
        
        # Create decomposition prompt
        prompt = self._create_decomposition_prompt(
            ticket, context, custom_instructions
        )
        
        ticket.decomposition_agent_id = agent.id
        ticket.decomposition_prompt = prompt
        ticket.decomposition_context = context
        
        # Call LLM for decomposition
        tasks_data = await self._call_llm_decompose(
            agent, prompt, context
        )
        
        # Create tasks
        tasks = []
        for idx, task_data in enumerate(tasks_data):
            task = Task(
                ticket_id=ticket_id,
                title=task_data["title"],
                description=task_data.get("description"),
                task_type=task_data.get("type", "code"),
                required_capabilities=task_data.get("capabilities", []),
                execution_instructions=task_data.get("instructions"),
                estimated_hours=task_data.get("estimated_hours"),
                position=idx,
                depends_on_task_ids=task_data.get("depends_on", []),
                generated_by_ai=True,
                generation_context=task_data.get("context"),
                created_by=user_id,
                attributes={
                    "decomposed_by_agent": str(agent.id),
                    "confidence": task_data.get("confidence", 0.8)
                }
            )
            self.db.add(task)
            tasks.append(task)
        
        # Mark ticket as decomposed
        ticket.decomposed = True
        ticket.decomposed_at = datetime.utcnow()
        ticket.status = TicketStatus.TODO.value
        
        await self.db.commit()
        
        # Terminate decomposer agent
        await self.orchestrator.terminate_agent(
            agent.id, reason="decomposition_complete"
        )
        
        return tasks
    
    async def _build_decomposition_context(
        self,
        ticket: Ticket
    ) -> Dict:
        """Build context for decomposition."""
        project = ticket.project
        
        # Get relevant documents
        docs = []
        for doc in project.documents:
            if doc.doc_type in ["requirements", "architecture", "design"]:
                docs.append({
                    "title": doc.title,
                    "type": doc.doc_type,
                    "content": doc.content[:2000]  # Truncate
                })
        
        # Get project structure from GitHub (if available)
        repo_structure = None
        if project.github_repo_full_name:
            # Would fetch from GitHub API
            repo_structure = {"placeholder": "file_tree"}
        
        # Get similar completed tickets
        result = await self.db.execute(
            select(Ticket)
            .where(
                Ticket.project_id == project.id,
                Ticket.status == TicketStatus.DONE.value,
                Ticket.decomposed == True
            )
            .limit(3)
            .options(selectinload(Ticket.tasks))
        )
        similar_tickets = result.scalars().all()
        
        examples = []
        for sim_ticket in similar_tickets:
            examples.append({
                "ticket_title": sim_ticket.title,
                "tasks": [
                    {
                        "title": task.title,
                        "type": task.task_type,
                        "capabilities": task.required_capabilities
                    }
                    for task in sim_ticket.tasks
                ]
            })
        
        return {
            "project": {
                "name": project.name,
                "description": project.description,
                "tech_stack": project.attributes.get("tech_stack", [])
            },
            "documents": docs,
            "repo_structure": repo_structure,
            "examples": examples
        }
    
    def _create_decomposition_prompt(
        self,
        ticket: Ticket,
        context: Dict,
        custom_instructions: Optional[str]
    ) -> str:
        """Create prompt for task decomposition."""
        return f"""You are decomposing a ticket into granular, executable tasks.

TICKET:
Title: {ticket.title}
Type: {ticket.ticket_type}
Priority: {ticket.priority}
Description:
{ticket.description}

PROJECT CONTEXT:
{json.dumps(context, indent=2)}

{f'CUSTOM INSTRUCTIONS:
{custom_instructions}
' if custom_instructions else ''}

REQUIREMENTS:
1. Break down the ticket into 3-10 specific, actionable tasks
2. Each task should be completable by a single AI agent in < 2 hours
3. Identify dependencies between tasks
4. Specify required capabilities (e.g., "python", "testing", "git")
5. Provide clear execution instructions
6. Assign task types: "code", "test", "review", "docs", "devops"
7. Order tasks logically (dependencies first)

OUTPUT FORMAT (JSON):
{{
  "tasks": [
    {{
      "title": "Clear, specific task title",
      "description": "Detailed description of what needs to be done",
      "type": "code|test|review|docs|devops",
      "capabilities": ["python", "git"],
      "instructions": "Step-by-step instructions for execution",
      "estimated_hours": 1.5,
      "depends_on": [],  // Task indices this depends on
      "confidence": 0.9,  // 0-1 confidence in task definition
      "context": {{}}  // Additional context
    }}
  ],
  "reasoning": "Explanation of decomposition strategy",
  "risks": ["Potential risks or unknowns"]
}}"""
    
    async def _call_llm_decompose(
        self,
        agent: Agent,
        prompt: str,
        context: Dict
    ) -> List[Dict]:
        """Call LLM to perform decomposition."""
        # This would integrate with your LLM service
        # For now, return a placeholder
        
        # In production:
        # response = await anthropic_client.messages.create(
        #     model=agent.model_config["model"],
        #     max_tokens=agent.model_config["max_tokens"],
        #     system=agent.system_prompt,
        #     messages=[{"role": "user", "content": prompt}]
        # )
        # 
        # result = json.loads(response.content[0].text)
        # return result["tasks"]
        
        # Placeholder
        return [
            {
                "title": "Implement core functionality",
                "description": "Write main implementation",
                "type": "code",
                "capabilities": ["python"],
                "instructions": "Follow project patterns",
                "estimated_hours": 2.0,
                "depends_on": [],
                "confidence": 0.85
            },
            {
                "title": "Write unit tests",
                "description": "Comprehensive test coverage",
                "type": "test",
                "capabilities": ["pytest"],
                "instructions": "Achieve >80% coverage",
                "estimated_hours": 1.5,
                "depends_on": [0],
                "confidence": 0.9
            }
        ]
```

## GitHub Integration Service

```python
import hmac
import hashlib
from typing import Optional

class GitHubIntegrationService:
    """Handle GitHub webhooks and API interactions."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """Verify GitHub webhook signature."""
        if not signature.startswith("sha256="):
            return False
        
        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        received = signature[7:]  # Remove "sha256=" prefix
        return hmac.compare_digest(expected, received)
    
    async def handle_webhook_event(
        self,
        event_type: str,
        delivery_id: str,
        payload: Dict,
        project_id: UUID
    ) -> GitHubWebhookEvent:
        """Process GitHub webhook event."""
        # Create event record
        event = GitHubWebhookEvent(
            project_id=project_id,
            event_type=event_type,
            github_delivery_id=delivery_id,
            action=payload.get("action"),
            payload=payload,
            processed=False
        )
        self.db.add(event)
        await self.db.flush()
        
        # Route to appropriate handler
        handler_map = {
            GitHubEventType.PUSH.value: self._handle_push,
            GitHubEventType.PULL_REQUEST.value: self._handle_pull_request,
            GitHubEventType.PULL_REQUEST_REVIEW.value: self._handle_pr_review,
            GitHubEventType.ISSUE_COMMENT.value: self._handle_comment,
        }
        
        handler = handler_map.get(event_type)
        if handler:
            try:
                result = await handler(payload, project_id)
                event.processed = True
                event.processed_at = datetime.utcnow()
                event.processing_result = result
            except Exception as e:
                event.processing_result = {
                    "error": str(e),
                    "status": "failed"
                }
        
        await self.db.commit()
        return event
    
    async def _handle_push(
        self,
        payload: Dict,
        project_id: UUID
    ) -> Dict:
        """Handle push events."""
        branch = payload["ref"].split("/")[-1]
        commits = payload.get("commits", [])
        
        # Find related tasks/tickets by branch name
        # Branch naming: ticket-{ticket_number}-{slug}
        if branch.startswith("ticket-"):
            parts = branch.split("-", 2)
            if len(parts) >= 2:
                ticket_number = int(parts[1])
                
                # Find ticket
                result = await self.db.execute(
                    select(Ticket)
                    .where(
                        Ticket.project_id == project_id,
                        Ticket.ticket_number == ticket_number
                    )
                )
                ticket = result.scalar_one_or_none()
                
                if ticket:
                    # Update ticket with latest commit
                    ticket.branch_name = branch
                    
                    # Find tasks with this branch
                    await self.db.execute(
                        update(Task)
                        .where(
                            Task.ticket_id == ticket.id,
                            Task.github_branch == branch
                        )
                        .values(
                            commit_sha=commits[-1]["id"] if commits else None
                        )
                    )
                    
                    await self.db.commit()
        
        return {
            "branch": branch,
            "commits_count": len(commits),
            "status": "processed"
        }
    
    async def _handle_pull_request(
        self,
        payload: Dict,
        project_id: UUID
    ) -> Dict:
        """Handle pull request events."""
        action = payload["action"]
        pr = payload["pull_request"]
        pr_number = pr["number"]
        branch = pr["head"]["ref"]
        
        # Find ticket by branch or PR description
        ticket = None
        if branch.startswith("ticket-"):
            parts = branch.split("-", 2)
            if len(parts) >= 2:
                ticket_number = int(parts[1])
                result = await self.db.execute(
                    select(Ticket)
                    .where(
                        Ticket.project_id == project_id,
                        Ticket.ticket_number == ticket_number
                    )
                )
                ticket = result.scalar_one_or_none()
        
        if ticket:
            ticket.pull_request_number = pr_number
            ticket.pull_request_url = pr["html_url"]
            
            if action == "opened":
                ticket.status = TicketStatus.IN_REVIEW.value
            elif action == "closed" and pr.get("merged"):
                ticket.status = TicketStatus.DONE.value
                # Mark all tasks as done
                await self.db.execute(
                    update(Task)
                    .where(Task.ticket_id == ticket.id)
                    .values(
                        status=TaskStatus.DONE.value,
                        completed_at=datetime.utcnow()
                    )
                )
            
            await self.db.commit()
        
        return {
            "action": action,
            "pr_number": pr_number,
            "ticket_updated": ticket is not None,
            "status": "processed"
        }
    
    async def _handle_pr_review(
        self,
        payload: Dict,
        project_id: UUID
    ) -> Dict:
        """Handle PR review events."""
        # Could trigger notifications, update task status, etc.
        return {"status": "processed"}
    
    async def _handle_comment(
        self,
        payload: Dict,
        project_id: UUID
    ) -> Dict:
        """Handle comment events."""
        # Could parse commands from comments (e.g., /assign-agent)
        return {"status": "processed"}
    
    async def create_branch_for_ticket(
        self,
        ticket: Ticket,
        base_branch: str = "main"
    ) -> str:
        """Create a GitHub branch for a ticket."""
        # Generate branch name
        slug = ticket.title.lower().replace(" ", "-")[:50]
        branch_name = f"ticket-{ticket.ticket_number}-{slug}"
        
        # Would use GitHub API to create branch
        # github_client.create_branch(
        #     repo=ticket.project.github_repo_full_name,
        #     branch=branch_name,
        #     sha=base_branch_sha
        # )
        
        ticket.branch_name = branch_name
        await self.db.commit()
        
        return branch_name
    
    async def create_pull_request(
        self,
        ticket: Ticket,
        title: Optional[str] = None,
        body: Optional[str] = None
    ) -> int:
        """Create a pull request for a ticket."""
        if not ticket.branch_name:
            raise ValueError("Ticket has no branch")
        
        title = title or f"[Ticket #{ticket.ticket_number}] {ticket.title}"
        body = body or f"""Closes #{ticket.ticket_number}

{ticket.description}

## Tasks Completed
"""
        # Add completed tasks
        result = await self.db.execute(
            select(Task)
            .where(Task.ticket_id == ticket.id)
        )
        tasks = result.scalars().all()
        
        for task in tasks:
            status_emoji = "✅" if task.status == TaskStatus.DONE.value else "⏳"
            body += f"\n- {status_emoji} {task.title}"
        
        # Would use GitHub API to create PR
        # pr = github_client.create_pull_request(
        #     repo=ticket.project.github_repo_full_name,
        #     title=title,
        #     body=body,
        #     head=ticket.branch_name,
        #     base=ticket.project.github_default_branch
        # )
        
        # Placeholder
        pr_number = 123
        
        ticket.pull_request_number = pr_number
        ticket.pull_request_url = f"https://github.com/{ticket.project.github_repo_full_name}/pull/{pr_number}"
        ticket.status = TicketStatus.IN_REVIEW.value
        
        await self.db.commit()
        
        return pr_number
```

## FastAPI Endpoints

### Agent Management

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

class SpawnAgentRequest(BaseModel):
    agent_type: AgentType
    project_id: Optional[UUID] = None
    name: Optional[str] = None
    capabilities: Optional[List[str]] = None
    auto_terminate_minutes: Optional[int] = 120

class AgentResponse(BaseModel):
    id: UUID
    name: str
    agent_type: str
    status: str
    capabilities: List[str]
    tasks_completed: int
    tasks_failed: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

@router.post("", response_model=AgentResponse)
async def spawn_agent(
    request: SpawnAgentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Spawn a new agent."""
    orchestrator = AgentOrchestrator(db)
    
    agent = await orchestrator.spawn_agent(
        agent_type=request.agent_type,
        spawned_by=current_user.id,
        organization_id=current_user.active_organization_id,
        project_id=request.project_id,
        name=request.name,
        capabilities=request.capabilities,
        auto_terminate_minutes=request.auto_terminate_minutes
    )
    
    return agent

@router.get("", response_model=List[AgentResponse])
async def list_agents(
    organization_id: UUID,
    project_id: Optional[UUID] = None,
    status: Optional[AgentStatus] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List agents."""
    query = select(Agent).where(Agent.organization_id == organization_id)
    
    if project_id:
        query = query.where(Agent.project_id == project_id)
    
    if status:
        query = query.where(Agent.status == status.value)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.delete("/{agent_id}")
async def terminate_agent(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Terminate an agent."""
    orchestrator = AgentOrchestrator(db)
    await orchestrator.terminate_agent(agent_id, reason="user_request")
    return {"status": "terminated"}
```

### Task Decomposition

```python
class DecomposeTicketRequest(BaseModel):
    custom_instructions: Optional[str] = None

class TaskResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    task_type: Optional[str]
    status: str
    position: int
    estimated_hours: Optional[float]
    required_capabilities: Optional[List[str]]
    
    model_config = ConfigDict(from_attributes=True)

@router.post("/tickets/{ticket_id}/decompose", response_model=List[TaskResponse])
async def decompose_ticket(
    ticket_id: UUID,
    request: DecomposeTicketRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Decompose a ticket into tasks using AI."""
    orchestrator = AgentOrchestrator(db)
    service = TaskDecompositionService(db, orchestrator)
    
    tasks = await service.decompose_ticket(
        ticket_id=ticket_id,
        user_id=current_user.id,
        custom_instructions=request.custom_instructions
    )
    
    return tasks
```

### GitHub Webhooks

```python
from fastapi import Request, Header

@router.post("/webhooks/github/{project_id}")
async def github_webhook(
    project_id: UUID,
    request: Request,
    x_github_event: str = Header(...),
    x_github_delivery: str = Header(...),
    x_hub_signature_256: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """Handle GitHub webhook events."""
    # Get project
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(404, "Project not found")
    
    # Get payload
    payload_bytes = await request.body()
    payload = await request.json()
    
    # Verify signature
    github_service = GitHubIntegrationService(db)
    valid = await github_service.verify_webhook_signature(
        payload_bytes,
        x_hub_signature_256,
        project.github_webhook_secret
    )
    
    if not valid:
        raise HTTPException(401, "Invalid signature")
    
    # Process event
    event = await github_service.handle_webhook_event(
        event_type=x_github_event,
        delivery_id=x_github_delivery,
        payload=payload,
        project_id=project_id
    )
    
    return {"status": "processed", "event_id": str(event.id)}
```

## Database Indexes

```sql
-- Agents
CREATE INDEX idx_agents_org ON agents(organization_id);
CREATE INDEX idx_agents_project ON agents(project_id);
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_type ON agents(agent_type);
CREATE INDEX idx_agents_spawned_by ON agents(spawned_by);

-- Agent Execution Logs
CREATE INDEX idx_agent_logs_agent ON agent_execution_logs(agent_id);
CREATE INDEX idx_agent_logs_task ON agent_execution_logs(task_id);
CREATE INDEX idx_agent_logs_level ON agent_execution_logs(level);
CREATE INDEX idx_agent_logs_created ON agent_execution_logs(created_at DESC);

-- Projects
CREATE INDEX idx_projects_github_repo ON projects(github_repo_id) 
    WHERE github_repo_id IS NOT NULL;

-- GitHub Events
CREATE INDEX idx_github_events_project ON github_webhook_events(project_id);
CREATE INDEX idx_github_events_type ON github_webhook_events(event_type);
CREATE INDEX idx_github_events_delivery ON github_webhook_events(github_delivery_id);
CREATE INDEX idx_github_events_processed ON github_webhook_events(processed, created_at);

-- Tickets
CREATE INDEX idx_tickets_decomposed ON tickets(decomposed);
CREATE INDEX idx_tickets_github_issue ON tickets(project_id, github_issue_number)
    WHERE github_issue_number IS NOT NULL;
CREATE INDEX idx_tickets_pr ON tickets(pull_request_number)
    WHERE pull_request_number IS NOT NULL;

-- Tasks
CREATE INDEX idx_tasks_type ON tasks(task_type);
CREATE INDEX idx_tasks_generated ON tasks(generated_by_ai);
CREATE INDEX idx_tasks_github_branch ON tasks(github_branch)
    WHERE github_branch IS NOT NULL;
```

## Background Jobs

```python
from celery import Celery

celery = Celery("tasks")

@celery.task
async def cleanup_idle_agents():
    """Periodic task to terminate idle agents."""
    async with async_session() as db:
        orchestrator = AgentOrchestrator(db)
        # Get all organizations
        result = await db.execute(select(Organization))
        orgs = result.scalars().all()
        
        for org in orgs:
            await orchestrator.cleanup_idle_agents(
                organization_id=org.id,
                idle_threshold_minutes=120
            )

@celery.task
async def process_pending_github_events():
    """Process unprocessed GitHub events."""
    async with async_session() as db:
        github_service = GitHubIntegrationService(db)
        
        result = await db.execute(
            select(GitHubWebhookEvent)
            .where(GitHubWebhookEvent.processed == False)
            .limit(100)
        )
        events = result.scalars().all()
        
        for event in events:
            # Reprocess event
            await github_service.handle_webhook_event(
                event_type=event.event_type,
                delivery_id=event.github_delivery_id,
                payload=event.payload,
                project_id=event.project_id
            )
```

## Next Steps

1. **Implement agent-to-LLM communication** - Abstract LLM client interface
2. **Add agent progress streaming** - WebSocket updates for real-time monitoring
3. **Create agent performance analytics** - Success rates, avg execution time
4. **Build GitHub App** - OAuth flow, installation management
5. **Add task dependency resolution** - Smart task ordering based on dependencies
6. **Implement agent capability matching** - Auto-select best agent for task
7. **Create rollback mechanism** - Revert failed agent changes

## Questions

**LLM provider preference?** (Anthropic, OpenAI, self-hosted) - affects agent execution model

**Agent resource limits?** (max concurrent agents per org, compute budget)

**Human-in-loop approval?** (require approval before agent commits/PRs or fully autonomous?)



## Response:
11/19/2025, 9:23:01 AM

I'll update the design document to integrate with OpenHands Agent SDK and remove the already-implemented components. This will focus on the authentication/authorization layer that integrates with your existing agent infrastructure.

```markdown:docs/auth-org-design.md
# Organization & Authentication Design Document

## System Overview

A multi-tenant authentication and authorization system for AI-assisted project management integrating with OpenHands Agent SDK for terminal-based agent execution, GitHub for version control, and existing LLM infrastructure.

**Domain Hierarchy:**
```
Organizations
  ├─ Members (Users + OpenHands Agents with Roles)
  └─ Projects
      ├─ GitHub Repositories
      ├─ Documents (Designs, Requirements)
      └─ Tickets (AI-decomposed into Tasks)
          └─ Tasks (Assigned to OpenHands Agents)
```

**Integration Points:**
- **OpenHands Agent SDK**: Terminal-based agent spawning and execution
- **Existing LLM Infrastructure**: Your current LLM client setup
- **GitHub API**: Direct integration (no GitHub App needed)
- **Task Decomposition**: Your existing AI decomposition logic

## Core Entities

### 1. User

```python
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum, Integer, BigInteger
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum as PyEnum
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.sql import func, text

class ActorType(PyEnum):
    USER = "user"
    AGENT = "agent"

class User(Base):
    __tablename__ = "users"
    
    # Identity
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
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
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), 
        onupdate=func.now()
    )
    last_login_at: Mapped[Optional[datetime]]
    
    # Relationships
    memberships: Mapped[List["OrganizationMembership"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="OrganizationMembership.user_id"
    )
    owned_organizations: Mapped[List["Organization"]] = relationship(
        back_populates="owner",
        foreign_keys="Organization.owner_id"
    )
    api_keys: Mapped[List["APIKey"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    sessions: Mapped[List["Session"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    created_projects: Mapped[List["Project"]] = relationship(
        back_populates="creator",
        foreign_keys="Project.created_by"
    )
    assigned_tasks: Mapped[List["TaskAssignment"]] = relationship(
        back_populates="assignee",
        foreign_keys="TaskAssignment.assignee_id"
    )
    created_tickets: Mapped[List["Ticket"]] = relationship(
        back_populates="creator",
        foreign_keys="Ticket.created_by"
    )
    spawned_agents: Mapped[List["Agent"]] = relationship(
        back_populates="spawned_by_user",
        foreign_keys="Agent.spawned_by"
    )
```

### 2. Agent (OpenHands Integration)

```python
class AgentStatus(PyEnum):
    SPAWNING = "spawning"        # OpenHands agent initializing
    IDLE = "idle"                # Ready for tasks
    WORKING = "working"          # Executing in terminal
    SUSPENDED = "suspended"      # Paused
    TERMINATING = "terminating"  # Shutting down
    TERMINATED = "terminated"    # Shut down
    FAILED = "failed"            # Failed to spawn or crashed

class AgentType(PyEnum):
    CODE_GENERATOR = "code_generator"
    TEST_ENGINEER = "test_engineer"
    CODE_REVIEWER = "code_reviewer"
    DOCUMENTATION = "documentation"
    TASK_DECOMPOSER = "task_decomposer"
    DEVOPS = "devops"
    GENERAL = "general"

class Agent(Base):
    __tablename__ = "agents"
    
    # Identity
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
    agent_type: Mapped[str] = mapped_column(String(50), index=True)
    
    # OpenHands Integration
    openhands_instance_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        index=True
    )  # OpenHands runtime instance ID
    openhands_workspace_path: Mapped[Optional[str]] = mapped_column(String(1000))
    openhands_config: Mapped[Optional[dict]] = mapped_column(JSONB)  # Runtime config
    
    # Lifecycle
    status: Mapped[str] = mapped_column(
        String(50),
        default=AgentStatus.SPAWNING.value,
        index=True
    )
    spawned_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    project_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True
    )
    
    # Configuration (passed to OpenHands)
    capabilities: Mapped[List[str]] = mapped_column(JSONB)
    environment_vars: Mapped[Optional[dict]] = mapped_column(JSONB)  # ENV vars for sandbox
    system_prompt: Mapped[Optional[str]] = mapped_column(Text)
    attributes: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Resource Limits
    max_concurrent_tasks: Mapped[int] = mapped_column(Integer, default=1)
    timeout_minutes: Mapped[int] = mapped_column(Integer, default=60)
    max_iterations: Mapped[int] = mapped_column(Integer, default=100)  # OpenHands iterations
    
    # Execution Context
    current_task_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("tasks.id"))
    current_working_directory: Mapped[Optional[str]] = mapped_column(String(1000))
    
    # Metrics
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    tasks_failed: Mapped[int] = mapped_column(Integer, default=0)
    total_execution_time_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    total_llm_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Auto-termination
    auto_terminate_after_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    terminate_when_idle: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    last_active_at: Mapped[Optional[datetime]]
    terminated_at: Mapped[Optional[datetime]]
    
    # Relationships
    spawned_by_user: Mapped["User"] = relationship(
        back_populates="spawned_agents",
        foreign_keys=[spawned_by]
    )
    organization: Mapped["Organization"] = relationship()
    project: Mapped[Optional["Project"]] = relationship()
    memberships: Mapped[List["OrganizationMembership"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
        foreign_keys="OrganizationMembership.agent_id"
    )
    api_keys: Mapped[List["APIKey"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan"
    )
    assigned_tasks: Mapped[List["TaskAssignment"]] = relationship(
        back_populates="agent_assignee",
        foreign_keys="TaskAssignment.agent_id"
    )
    current_task: Mapped[Optional["Task"]] = relationship(
        foreign_keys=[current_task_id]
    )
    execution_logs: Mapped[List["AgentExecutionLog"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan"
    )
    terminal_outputs: Mapped[List["AgentTerminalOutput"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan"
    )
```

### 3. AgentTerminalOutput (NEW - Store Terminal Streams)

```python
class OutputType(PyEnum):
    STDOUT = "stdout"
    STDERR = "stderr"
    ACTION = "action"       # Agent action taken
    OBSERVATION = "observation"  # Environment response
    THOUGHT = "thought"     # Agent reasoning
    ERROR = "error"

class AgentTerminalOutput(Base):
    __tablename__ = "agent_terminal_outputs"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        index=True
    )
    task_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        index=True
    )
    
    # Output Details
    output_type: Mapped[str] = mapped_column(String(20), index=True)
    content: Mapped[str] = mapped_column(Text)
    sequence_number: Mapped[int] = mapped_column(Integer)  # Order within task
    
    # Context
    iteration: Mapped[Optional[int]] = mapped_column(Integer)  # OpenHands iteration
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        index=True
    )
    
    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="terminal_outputs")
    task: Mapped[Optional["Task"]] = relationship()
    
    __table_args__ = (
        Index("idx_agent_task_seq", "agent_id", "task_id", "sequence_number"),
    )
```

### 4. AgentExecutionLog (Enhanced)

```python
class LogLevel(PyEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

class AgentExecutionLog(Base):
    __tablename__ = "agent_execution_logs"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        index=True
    )
    task_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        index=True
    )
    
    # Log Entry
    level: Mapped[str] = mapped_column(String(20), index=True)
    message: Mapped[str] = mapped_column(Text)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Context
    action: Mapped[Optional[str]] = mapped_column(String(100))
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    
    # OpenHands Specific
    iteration: Mapped[Optional[int]] = mapped_column(Integer)
    command_executed: Mapped[Optional[str]] = mapped_column(Text)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Costs
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float)
    
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        index=True
    )
    
    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="execution_logs")
    task: Mapped[Optional["Task"]] = relationship()
```

### 5. Organization (Unchanged)

```python
class Organization(Base):
    __tablename__ = "organizations"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Ownership
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    
    # Settings
    billing_email: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSONB)
    attributes: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Resource Limits
    max_concurrent_agents: Mapped[int] = mapped_column(Integer, default=5)
    max_agent_runtime_hours: Mapped[float] = mapped_column(Float, default=100.0)  # Per month
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    owner: Mapped["User"] = relationship(
        back_populates="owned_organizations",
        foreign_keys=[owner_id]
    )
    memberships: Mapped[List["OrganizationMembership"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    roles: Mapped[List["Role"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    policies: Mapped[List["Policy"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    projects: Mapped[List["Project"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
```

### 6. Project (GitHub Direct Integration)

```python
class ProjectStatus(PyEnum):
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class Project(Base):
    __tablename__ = "projects"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    
    # Basic Info
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(50),
        default=ProjectStatus.PLANNING.value,
        index=True
    )
    
    # GitHub Integration (Direct API, no GitHub App)
    github_repo_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True)
    github_repo_full_name: Mapped[Optional[str]] = mapped_column(String(255))  # "owner/repo"
    github_default_branch: Mapped[str] = mapped_column(String(255), default="main")
    
    # GitHub Personal Access Token (encrypted at rest)
    github_token_encrypted: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Webhook Configuration
    github_webhook_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    github_webhook_secret: Mapped[Optional[str]] = mapped_column(String(255))
    
    # OpenHands Workspace Configuration
    workspace_base_path: Mapped[Optional[str]] = mapped_column(String(1000))
    workspace_config: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # ABAC Attributes
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # Ownership
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship(
        back_populates="projects"
    )
    creator: Mapped["User"] = relationship(
        back_populates="created_projects",
        foreign_keys=[created_by]
    )
    documents: Mapped[List["Document"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan"
    )
    tickets: Mapped[List["Ticket"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan"
    )
    team_members: Mapped[List["ProjectMember"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan"
    )
    github_events: Mapped[List["GitHubWebhookEvent"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_org_project_slug", "organization_id", "slug", unique=True),
        Index("idx_github_repo", "github_repo_id", unique=True, 
              postgresql_where=text("github_repo_id IS NOT NULL")),
    )
```

### 7. Ticket (Enhanced with GitHub)

```python
class TicketType(PyEnum):
    FEATURE = "feature"
    BUG = "bug"
    IMPROVEMENT = "improvement"
    TASK = "task"

class TicketStatus(PyEnum):
    BACKLOG = "backlog"
    DECOMPOSING = "decomposing"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CLOSED = "closed"

class TicketPriority(PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class Ticket(Base):
    __tablename__ = "tickets"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True
    )
    
    # Identification
    ticket_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Classification
    ticket_type: Mapped[str] = mapped_column(
        String(50),
        default=TicketType.TASK.value,
        index=True
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=TicketStatus.BACKLOG.value,
        index=True
    )
    priority: Mapped[str] = mapped_column(
        String(50),
        default=TicketPriority.MEDIUM.value,
        index=True
    )
    
    # AI Decomposition (your existing logic)
    decomposed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    decomposition_agent_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL")
    )
    decomposition_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    decomposed_at: Mapped[Optional[datetime]]
    
    # GitHub Integration
    github_issue_number: Mapped[Optional[int]] = mapped_column(Integer)
    branch_name: Mapped[Optional[str]] = mapped_column(String(255))
    pull_request_number: Mapped[Optional[int]] = mapped_column(Integer)
    pull_request_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # ABAC Attributes
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # Relationships
    parent_ticket_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("tickets.id", ondelete="SET NULL")
    )
    
    # Ownership
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    assigned_to: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    due_date: Mapped[Optional[datetime]]
    
    # Relationships
    project: Mapped["Project"] = relationship(back_populates="tickets")
    creator: Mapped["User"] = relationship(
        back_populates="created_tickets",
        foreign_keys=[created_by]
    )
    assignee: Mapped[Optional["User"]] = relationship(foreign_keys=[assigned_to])
    parent_ticket: Mapped[Optional["Ticket"]] = relationship(
        remote_side=[id],
        backref="sub_tickets"
    )
    tasks: Mapped[List["Task"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="Task.position"
    )
    decomposition_agent: Mapped[Optional["Agent"]] = relationship(
        foreign_keys=[decomposition_agent_id]
    )
    
    __table_args__ = (
        Index("idx_project_ticket_number", "project_id", "ticket_number", unique=True),
        Index("idx_github_issue", "project_id", "github_issue_number",
              postgresql_where=text("github_issue_number IS NOT NULL")),
    )
```

### 8. Task (Enhanced for OpenHands)

```python
class TaskStatus(PyEnum):
    TODO = "todo"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    IN_REVIEW = "in_review"
    DONE = "done"
    FAILED = "failed"

class Task(Base):
    __tablename__ = "tasks"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),
        index=True
    )
    
    # Content
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(50),
        default=TaskStatus.TODO.value,
        index=True
    )
    
    # AI Generation Context
    generated_by_ai: Mapped[bool] = mapped_column(Boolean, default=False)
    generation_context: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Ordering & Dependencies
    position: Mapped[int] = mapped_column(Integer, default=0)
    depends_on_task_ids: Mapped[Optional[List[UUID]]] = mapped_column(JSONB)
    
    # Execution Details
    task_type: Mapped[Optional[str]] = mapped_column(String(50))
    required_capabilities: Mapped[Optional[List[str]]] = mapped_column(JSONB)
    
    # OpenHands Execution Instructions
    execution_instructions: Mapped[Optional[str]] = mapped_column(Text)
    max_iterations: Mapped[int] = mapped_column(Integer, default=100)
    initial_commands: Mapped[Optional[List[str]]] = mapped_column(JSONB)  # Setup commands
    
    # GitHub Integration
    file_paths: Mapped[Optional[List[str]]] = mapped_column(JSONB)
    commit_sha: Mapped[Optional[str]] = mapped_column(String(40))
    github_branch: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Execution Results
    execution_result: Mapped[Optional[dict]] = mapped_column(JSONB)
    execution_error: Mapped[Optional[str]] = mapped_column(Text)
    final_state: Mapped[Optional[dict]] = mapped_column(JSONB)  # OpenHands final state
    
    # ABAC Attributes
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # Estimation & Actuals
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float)
    actual_hours: Mapped[Optional[float]] = mapped_column(Float)
    actual_iterations: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Ownership
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    started_at: Mapped[Optional[datetime]]
    completed_at: Mapped[Optional[datetime]]
    
    # Relationships
    ticket: Mapped["Ticket"] = relationship(back_populates="tasks")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    assignments: Mapped[List["TaskAssignment"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan"
    )
```

### Remaining entities (OrganizationMembership, Role, Policy, etc.) remain unchanged from previous document.

## OpenHands Agent Orchestration

### Integration with OpenHands SDK

```python
from typing import Optional, Dict, List, AsyncIterator
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import asyncio

# Your existing OpenHands imports
# from openhands.core.main import run_agent
# from openhands.runtime.client import RuntimeClient
# etc.

class OpenHandsAgentOrchestrator:
    """Orchestrates OpenHands agents with auth/authorization layer."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def spawn_agent(
        self,
        agent_type: AgentType,
        spawned_by: UUID,
        organization_id: UUID,
        project_id: UUID,
        capabilities: Optional[List[str]] = None,
        environment_vars: Optional[Dict] = None,
        workspace_path: Optional[str] = None,
    ) -> Agent:
        """
        Spawn OpenHands agent instance.
        
        Args:
            agent_type: Type of agent
            spawned_by: User spawning the agent
            organization_id: Org context
            project_id: Project context
            capabilities: Agent capabilities
            environment_vars: ENV vars for sandbox
            workspace_path: Custom workspace path
        
        Returns:
            Agent record
        """
        # Check org limits
        await self._check_org_limits(organization_id)
        
        # Get project for workspace setup
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one()
        
        # Default capabilities
        if not capabilities:
            capabilities = self._get_default_capabilities(agent_type)
        
        # Setup workspace
        if not workspace_path:
            workspace_path = await self._setup_workspace(project)
        
        # Generate agent name
        name = f"{agent_type.value}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        # Create agent record
        agent = Agent(
            name=name,
            agent_type=agent_type.value,
            status=AgentStatus.SPAWNING.value,
            spawned_by=spawned_by,
            organization_id=organization_id,
            project_id=project_id,
            capabilities=capabilities,
            environment_vars=environment_vars or {},
            system_prompt=self._get_system_prompt(agent_type),
            openhands_workspace_path=workspace_path,
        )
        
        self.db.add(agent)
        await self.db.flush()
        
        try:
            # Initialize OpenHands runtime
            openhands_config = await self._create_openhands_config(
                agent, project
            )
            
            # Your existing OpenHands initialization code
            # runtime = RuntimeClient(...)
            # instance_id = await runtime.initialize(...)
            
            # Placeholder - replace with your actual OpenHands SDK calls
            instance_id = f"openhands-{agent.id}"
            
            # Update agent with OpenHands details
            agent.openhands_instance_id = instance_id
            agent.openhands_config = openhands_config
            agent.status = AgentStatus.IDLE.value
            agent.last_active_at = datetime.utcnow()
            
            # Add to org with agent role
            await self._add_agent_to_org(agent.id, organization_id)
            
            # Add to project
            await self._add_agent_to_project(agent.id, project_id, spawned_by)
            
            # Create API key
            await self._create_agent_api_key(agent.id, organization_id)
            
            # Log spawn
            log = AgentExecutionLog(
                agent_id=agent.id,
                level=LogLevel.INFO.value,
                message=f"OpenHands agent spawned",
                action="spawn",
                metadata={
                    "workspace": workspace_path,
                    "capabilities": capabilities
                }
            )
            self.db.add(log)
            
            await self.db.commit()
            await self.db.refresh(agent)
            
            return agent
            
        except Exception as e:
            agent.status = AgentStatus.FAILED.value
            await self.db.commit()
            raise Exception(f"Failed to spawn OpenHands agent: {e}")
    
    async def _check_org_limits(self, organization_id: UUID):
        """Check if org is within resource limits."""
        result = await self.db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        org = result.scalar_one()
        
        # Check concurrent agents
        active_agents = await self.db.execute(
            select(func.count(Agent.id))
            .where(
                Agent.organization_id == organization_id,
                Agent.status.in_([
                    AgentStatus.IDLE.value,
                    AgentStatus.WORKING.value
                ])
            )
        )
        
        if active_agents.scalar() >= org.max_concurrent_agents:
            raise ValueError(
                f"Organization at max concurrent agents ({org.max_concurrent_agents})"
            )
        
        # Check monthly runtime hours
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        monthly_usage = await self.db.execute(
            select(func.sum(Agent.total_execution_time_minutes))
            .where(
                Agent.organization_id == organization_id,
                Agent.created_at >= month_start
            )
        )
        
        hours_used = (monthly_usage.scalar() or 0) / 60
        if hours_used >= org.max_agent_runtime_hours:
            raise ValueError(
                f"Organization exceeded monthly runtime limit ({org.max_agent_runtime_hours}h)"
            )
    
    async def _setup_workspace(self, project: Project) -> str:
        """Setup workspace for agent (clone repo, etc)."""
        # This integrates with your existing workspace setup logic
        # Typically: clone GitHub repo into a sandbox directory
        
        import tempfile
        import os
        
        if project.workspace_base_path:
            workspace = project.workspace_base_path
        else:
            # Create temp workspace
            workspace = tempfile.mkdtemp(prefix=f"agent-{project.slug}-")
        
        # Clone repo if GitHub configured
        if project.github_repo_full_name:
            # Use your existing git clone logic
            # git.Repo.clone_from(repo_url, workspace)
            pass
        
        return workspace
    
    async def _create_openhands_config(
        self,
        agent: Agent,
        project: Project
    ) -> Dict:
        """Create OpenHands runtime configuration."""
        config = {
            "workspace_base": agent.openhands_workspace_path,
            "max_iterations": agent.max_iterations,
            "environment": agent.environment_vars or {},
            "system_message": agent.system_prompt,
        }
        
        # Add GitHub credentials if available
        if project.github_token_encrypted:
            # Decrypt token
            github_token = self._decrypt_github_token(
                project.github_token_encrypted
            )
            config["environment"]["GITHUB_TOKEN"] = github_token
        
        return config
    
    def _decrypt_github_token(self, encrypted: str) -> str:
        """Decrypt GitHub token."""
        # Use your encryption service
        # return encryption_service.decrypt(encrypted)
        return encrypted  # Placeholder
    
    async def assign_task_to_agent(
        self,
        task_id: UUID,
        agent_id: UUID,
        assigned_by: UUID
    ) -> TaskAssignment:
        """Assign task to OpenHands agent."""
        # Verify agent status
        result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one()
        
        if agent.status not in [AgentStatus.IDLE.value, AgentStatus.WORKING.value]:
            raise ValueError(f"Agent is {agent.status}, cannot assign task")
        
        # Check capacity
        current_tasks = await self.db.execute(
            select(func.count(TaskAssignment.id))
            .where(
                TaskAssignment.agent_id == agent_id,
                TaskAssignment.completed_at.is_(None)
            )
        )
        
        if current_tasks.scalar() >= agent.max_concurrent_tasks:
            raise ValueError("Agent at max capacity")
        
        # Get task
        task_result = await self.db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = task_result.scalar_one()
        
        # Create assignment
        assignment = TaskAssignment(
            task_id=task_id,
            agent_id=agent_id,
            assigned_by=assigned_by,
            assigned_at=datetime.utcnow()
        )
        self.db.add(assignment)
        
        # Update status
        task.status = TaskStatus.ASSIGNED.value
        agent.status = AgentStatus.WORKING.value
        agent.current_task_id = task_id
        agent.last_active_at = datetime.utcnow()
        
        await self.db.commit()
        
        # Start task execution (async)
        asyncio.create_task(
            self._execute_task_with_agent(agent, task, assignment)
        )
        
        return assignment
    
    async def _execute_task_with_agent(
        self,
        agent: Agent,
        task: Task,
        assignment: TaskAssignment
    ):
        """Execute task using OpenHands agent (integrates with your existing logic)."""
        assignment.started_at = datetime.utcnow()
        task.started_at = datetime.utcnow()
        task.status = TaskStatus.IN_PROGRESS.value
        await self.db.commit()
        
        try:
            # Your existing OpenHands execution logic
            # This is where you call your LLM, run the agent loop, etc.
            
            # Placeholder - replace with your actual execution
            result = await self._run_openhands_agent(agent, task)
            
            # Mark as complete
            await self.complete_task_execution(
                agent_id=agent.id,
                task_id=task.id,
                success=result["success"],
                result=result.get("data"),
                error=result.get("error"),
                duration_seconds=result.get("duration_seconds"),
                iterations=result.get("iterations"),
                tokens_used=result.get("tokens_used"),
                cost_usd=result.get("cost_usd")
            )
            
        except Exception as e:
            await self.complete_task_execution(
                agent_id=agent.id,
                task_id=task.id,
                success=False,
                error=str(e)
            )
    
    async def _run_openhands_agent(
        self,
        agent: Agent,
        task: Task
    ) -> Dict:
        """
        Run OpenHands agent to execute task.
        
        This is where you integrate your existing OpenHands execution logic.
        Should return result dict with success, data, error, metrics.
        """
        # Your existing code here
        # Example structure:
        
        # 1. Setup task instructions
        instruction = self._build_task_instruction(task)
        
        # 2. Run OpenHands agent (your existing logic)
        # result = await run_agent(
        #     instruction=instruction,
        #     runtime=agent.openhands_instance_id,
        #     max_iterations=task.max_iterations,
        #     on_event=lambda event: self._handle_agent_event(agent, task, event)
        # )
        
        # 3. Process result
        # return {
        #     "success": result.success,
        #     "data": result.data,
        #     "iterations": result.metrics.iterations,
        #     "tokens_used": result.metrics.tokens,
        #     "cost_usd": result.metrics.cost,
        #     "duration_seconds": result.metrics.duration
        # }
        
        # Placeholder
        return {
            "success": True,
            "data": {"message": "Task completed"},
            "iterations": 10,
            "tokens_used": 5000,
            "cost_usd": 0.05,
            "duration_seconds": 120.0
        }
    
    def _build_task_instruction(self, task: Task) -> str:
        """Build instruction for OpenHands agent."""
        instruction = f"""# Task: {task.title}

{task.description}

## Instructions
{task.execution_instructions or 'Complete the task as described above.'}

## Files to modify
{', '.join(task.file_paths) if task.file_paths else 'Determine files as needed'}

## Success criteria
- All tests pass
- Code follows project conventions
- Changes committed to git
"""
        return instruction
    
    async def _handle_agent_event(
        self,
        agent: Agent,
        task: Task,
        event: Dict
    ):
        """
        Handle OpenHands agent events (for streaming).
        
        This would be called by your OpenHands SDK during execution
        to capture terminal output, actions, observations, etc.
        """
        event_type = event.get("type")
        content = event.get("content", "")
        
        # Map OpenHands event types to your OutputType
        output_type_map = {
            "action": OutputType.ACTION,
            "observation": OutputType.OBSERVATION,
            "thought": OutputType.THOUGHT,
            "stdout": OutputType.STDOUT,
            "stderr": OutputType.STDERR,
        }
        
        output_type = output_type_map.get(event_type, OutputType.STDOUT)
        
        # Get current sequence number
        result = await self.db.execute(
            select(func.coalesce(func.max(AgentTerminalOutput.sequence_number), 0))
            .where(
                AgentTerminalOutput.agent_id == agent.id,
                AgentTerminalOutput.task_id == task.id
            )
        )
        seq = result.scalar() + 1
        
        # Store output
        output = AgentTerminalOutput(
            agent_id=agent.id,
            task_id=task.id,
            output_type=output_type.value,
            content=content,
            sequence_number=seq,
            iteration=event.get("iteration"),
            metadata=event.get("metadata")
        )
        self.db.add(output)
        await self.db.commit()
        
        # Emit to WebSocket clients (if you add streaming later)
        # await websocket_manager.broadcast(agent.id, {
        #     "type": "agent_output",
        #     "output_type": output_type.value,
        #     "content": content,
        #     "sequence": seq
        # })
    
    async def complete_task_execution(
        self,
        agent_id: UUID,
        task_id: UUID,
        success: bool,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        iterations: Optional[int] = None,
        tokens_used: Optional[int] = None,
        cost_usd: Optional[float] = None
    ):
        """Mark task as complete."""
        # Get assignment
        assignment_result = await self.db.execute(
            select(TaskAssignment)
            .where(
                TaskAssignment.agent_id == agent_id,
                TaskAssignment.task_id == task_id
            )
        )
        assignment = assignment_result.scalar_one()
        assignment.completed_at = datetime.utcnow()
        
        # Get task
        task_result = await self.db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = task_result.scalar_one()
        
        # Update task
        if success:
            task.status = TaskStatus.DONE.value
            task.execution_result = result
            task.completed_at = datetime.utcnow()
        else:
            task.status = TaskStatus.FAILED.value
            task.execution_error = error
        
        if assignment.started_at:
            elapsed = datetime.utcnow() - assignment.started_at
            task.actual_hours = elapsed.total_seconds() / 3600
        
        if iterations:
            task.actual_iterations = iterations
        
        # Get agent
        agent_result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = agent_result.scalar_one()
        
        # Update agent metrics
        if success:
            agent.tasks_completed += 1
        else:
            agent.tasks_failed += 1
        
        if duration_seconds:
            agent.total_execution_time_minutes += duration_seconds / 60
        
        if tokens_used:
            agent.total_llm_tokens += tokens_used
        
        if cost_usd:
            agent.total_cost_usd += cost_usd
        
        agent.current_task_id = None
        agent.last_active_at = datetime.utcnow()
        
        # Check for more tasks
        pending = await self.db.execute(
            select(func.count(TaskAssignment.id))
            .where(
                TaskAssignment.agent_id == agent_id,
                TaskAssignment.completed_at.is_(None)
            )
        )
        
        if pending.scalar() == 0:
            agent.status = AgentStatus.IDLE.value
        
        # Log completion
        log = AgentExecutionLog(
            agent_id=agent_id,
            task_id=task_id,
            level=LogLevel.INFO.value if success else LogLevel.ERROR.value,
            message=f"Task execution {'completed' if success else 'failed'}",
            action="task_completed",
            duration_seconds=duration_seconds,
            iteration=iterations,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            metadata={
                "success": success,
                "result": result,
                "error": error
            }
        )
        self.db.add(log)
        
        await self.db.commit()
    
    async def terminate_agent(self, agent_id: UUID, reason: str = "manual"):
        """Terminate OpenHands agent."""
        result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one()
        
        # Check for incomplete tasks
        pending = await self.db.execute(
            select(TaskAssignment)
            .where(
                TaskAssignment.agent_id == agent_id,
                TaskAssignment.completed_at.is_(None)
            )
        )
        
        if pending.scalars().first():
            raise ValueError("Cannot terminate agent with pending tasks")
        
        # Cleanup OpenHands runtime
        if agent.openhands_instance_id:
            # Your OpenHands cleanup logic
            # await runtime.terminate(agent.openhands_instance_id)
            pass
        
        # Update status
        agent.status = AgentStatus.TERMINATED.value
        agent.terminated_at = datetime.utcnow()
        
        # Revoke API keys
        await self.db.execute(
            update(APIKey)
            .where(APIKey.agent_id == agent_id)
            .values(is_active=False)
        )
        
        # Log
        log = AgentExecutionLog(
            agent_id=agent_id,
            level=LogLevel.INFO.value,
            message=f"Agent terminated: {reason}",
            action="terminate"
        )
        self.db.add(log)
        
        await self.db.commit()
    
    def _get_default_capabilities(self, agent_type: AgentType) -> List[str]:
        """Get default capabilities."""
        capability_map = {
            AgentType.CODE_GENERATOR: ["python", "javascript", "typescript", "git"],
            AgentType.TEST_ENGINEER: ["pytest", "jest", "unittest"],
            AgentType.CODE_REVIEWER: ["code_review", "static_analysis"],
            AgentType.DOCUMENTATION: ["markdown", "technical_writing"],
            AgentType.TASK_DECOMPOSER: ["task_analysis", "planning"],
            AgentType.DEVOPS: ["docker", "ci_cd", "deployment"],
            AgentType.GENERAL: ["general_purpose"]
        }
        return capability_map.get(agent_type, ["general_purpose"])
    
    def _get_system_prompt(self, agent_type: AgentType) -> str:
        """Get system prompt."""
        prompts = {
            AgentType.CODE_GENERATOR: """You are a code generation agent working in a terminal environment. Your role is to:
1. Write clean, well-documented code based on task specifications
2. Follow project coding standards and best practices
3. Create comprehensive unit tests
4. Commit your changes with clear commit messages
5. Report your progress and any blockers

Use the terminal commands available to you to complete the task.""",
            
            AgentType.TEST_ENGINEER: """You are a test engineering agent. Your role is to:
1. Write comprehensive test suites (unit, integration, e2e)
2. Achieve high code coverage
3. Identify edge cases and error conditions
4. Create test data and fixtures
5. Run tests and report results""",
        }
        return prompts.get(agent_type, "You are a general-purpose coding agent.")
    
    async def _add_agent_to_org(self, agent_id: UUID, organization_id: UUID):
        """Add agent to organization."""
        result = await self.db.execute(
            select(Role).where(
                Role.name == "agent_executor",
                Role.role_type == RoleType.SYSTEM.value
            )
        )
        role = result.scalar_one()
        
        membership = OrganizationMembership(
            agent_id=agent_id,
            organization_id=organization_id,
            role_id=role.id
        )
        self.db.add(membership)
    
    async def _add_agent_to_project(
        self,
        agent_id: UUID,
        project_id: UUID,
        added_by: UUID
    ):
        """Add agent to project."""
        project_member = ProjectMember(
            project_id=project_id,
            agent_id=agent_id,
            role=ProjectRole.CONTRIBUTOR.value,
            added_by=added_by
        )
        self.db.add(project_member)
    
    async def _create_agent_api_key(
        self,
        agent_id: UUID,
        organization_id: UUID
    ) -> str:
        """Create API key for agent."""
        import secrets
        import hashlib
        
        key = f"sk_agent_{secrets.token_urlsafe(32)}"
        prefix = key[:16]
        hashed = hashlib.sha256(key.encode()).hexdigest()
        
        api_key = APIKey(
            agent_id=agent_id,
            organization_id=organization_id,
            name="Agent API Key",
            key_prefix=prefix,
            hashed_key=hashed,
            scopes=["agent:execute"]
        )
        
        self.db.add(api_key)
        return key
```

## API Endpoints

### Agent Terminal Output Streaming (Future)

```python
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    """Manage WebSocket connections for agent output streaming."""
    
    def __init__(self):
        self.active_connections: Dict[UUID, List[WebSocket]] = {}
    
    async def connect(self, agent_id: UUID, websocket: WebSocket):
        await websocket.accept()
        if agent_id not in self.active_connections:
            self.active_connections[agent_id] = []
        self.active_connections[agent_id].append(websocket)
    
    def disconnect(self, agent_id: UUID, websocket: WebSocket):
        if agent_id in self.active_connections:
            self.active_connections[agent_id].remove(websocket)
    
    async def broadcast(self, agent_id: UUID, message: dict):
        if agent_id in self.active_connections:
            for connection in self.active_connections[agent_id]:
                await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/agents/{agent_id}/stream")
async def agent_output_stream(
    websocket: WebSocket,
    agent_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time agent terminal output.
    
    When you implement streaming, this will receive events from
    _handle_agent_event and broadcast to connected clients.
    """
    await manager.connect(agent_id, websocket)
    try:
        # Send historical output first
        result = await db.execute(
            select(AgentTerminalOutput)
            .where(AgentTerminalOutput.agent_id == agent_id)
            .order_by(AgentTerminalOutput.sequence_number)
            .limit(100)
        )
        
        for output in result.scalars():
            await websocket.send_json({
                "type": "agent_output",
                "output_type": output.output_type,
                "content": output.content,
                "sequence": output.sequence_number,
                "iteration": output.iteration,
                "timestamp": output.created_at.isoformat()
            })
        
        # Keep connection alive and send new events
        while True:
            # Client can send commands (pause, resume, etc.)
            data = await websocket.receive_json()
            # Handle commands
            
    except WebSocketDisconnect:
        manager.disconnect(agent_id, websocket)
```

### Get Agent Terminal Output

```python
@router.get("/agents/{agent_id}/output", response_model=List[Dict])
async def get_agent_output(
    agent_id: UUID,
    task_id: Optional[UUID] = None,
    output_type: Optional[OutputType] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get terminal output from agent execution."""
    query = select(AgentTerminalOutput).where(
        AgentTerminalOutput.agent_id == agent_id
    )
    
    if task_id:
        query = query.where(AgentTerminalOutput.task_id == task_id)
    
    if output_type:
        query = query.where(AgentTerminalOutput.output_type == output_type.value)
    
    query = query.order_by(
        AgentTerminalOutput.sequence_number
    ).limit(limit).offset(offset)
    
    result = await db.execute(query)
    outputs = result.scalars().all()
    
    return [
        {
            "sequence": o.sequence_number,
            "type": o.output_type,
            "content": o.content,
            "iteration": o.iteration,
            "timestamp": o.created_at.isoformat()
        }
        for o in outputs
    ]
```

## Database Indexes

```sql
-- Agents
CREATE INDEX idx_agents_openhands_instance ON agents(openhands_instance_id) 
    WHERE openhands_instance_id IS NOT NULL;
CREATE INDEX idx_agents_org_status ON agents(organization_id, status);
CREATE INDEX idx_agents_project ON agents(project_id) WHERE project_id IS NOT NULL;

-- Agent Terminal Outputs
CREATE INDEX idx_terminal_output_agent ON agent_terminal_outputs(agent_id);
CREATE INDEX idx_terminal_output_task ON agent_terminal_outputs(task_id);
CREATE INDEX idx_terminal_output_type ON agent_terminal_outputs(output_type);
CREATE INDEX idx_terminal_output_agent_task_seq ON agent_terminal_outputs(agent_id, task_id, sequence_number);
CREATE INDEX idx_terminal_output_created ON agent_terminal_outputs(created_at DESC);

-- Agent Execution Logs  
CREATE INDEX idx_agent_logs_iteration ON agent_execution_logs(agent_id, iteration);
CREATE INDEX idx_agent_logs_command ON agent_execution_logs(command_executed) 
    WHERE command_executed IS NOT NULL;

-- Projects
CREATE INDEX idx_projects_workspace ON projects(workspace_base_path) 
    WHERE workspace_base_path IS NOT NULL;
```

## Next Steps

1. **Implement streaming output capture** - Hook into OpenHands events to populate AgentTerminalOutput
2. **Add WebSocket endpoint** - Real-time agent output to frontend
3. **Build agent output viewer** - UI component to display terminal activity
4. **Add agent performance dashboard** - Success rates, costs, execution times
5. **Implement agent pause/resume** - Control agent mid-execution
6. **Add agent output search** - Full-text search across terminal outputs

## Integration Checklist

- [ ] Replace placeholder OpenHands SDK calls with your actual implementation
- [ ] Hook up `_handle_agent_event` to OpenHands event stream
- [ ] Integrate your existing LLM client in `_run_openhands_agent`
- [ ] Connect your task decomposition logic to `decompose_ticket` flow
- [ ] Add GitHub token encryption/decryption service
- [ ] Configure workspace cleanup for terminated agents
- [ ] Set up background job for idle agent cleanup
- [ ] Add monitoring for agent costs and resource usage

This design maintains your existing OpenHands infrastructure while adding the authorization layer, tracking, and management capabilities you need. The terminal output storage is in place for when you implement streaming later.



## Response:
11/19/2025, 9:30:10 AM

I'll provide a complete implementation for all 6 features: streaming output capture, WebSocket endpoints, UI components, performance dashboard, agent control, and full-text search.

```python:src/services/agent_streaming.py
"""
OpenHands Agent Streaming Service
Captures real-time output from OpenHands agents and broadcasts via WebSocket
"""

from typing import Optional, Dict, List, AsyncIterator, Callable
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, or_, text
from datetime import datetime, timedelta
import asyncio
import json
from enum import Enum

from models import (
    Agent, AgentTerminalOutput, AgentExecutionLog, Task, 
    AgentStatus, OutputType, LogLevel
)

class AgentEventType(Enum):
    """OpenHands event types."""
    ACTION = "action"
    OBSERVATION = "observation"
    THOUGHT = "thought"
    STDOUT = "stdout"
    STDERR = "stderr"
    ERROR = "error"
    STATUS_CHANGE = "status_change"
    ITERATION_START = "iteration_start"
    ITERATION_END = "iteration_end"
    TASK_START = "task_start"
    TASK_END = "task_end"


class AgentStreamingService:
    """Service for capturing and streaming agent execution output."""
    
    def __init__(
        self,
        db: AsyncSession,
        websocket_manager: 'WebSocketManager'
    ):
        self.db = db
        self.websocket_manager = websocket_manager
        self._pause_events: Dict[UUID, asyncio.Event] = {}
        self._stop_events: Dict[UUID, asyncio.Event] = {}
    
    async def handle_openhands_event(
        self,
        agent_id: UUID,
        task_id: Optional[UUID],
        event: Dict
    ):
        """
        Handle incoming OpenHands event and stream to clients.
        
        This should be called from your OpenHands event callback:
        
        Example integration:
        ```python
        async def openhands_callback(event):
            await streaming_service.handle_openhands_event(
                agent_id=agent.id,
                task_id=task.id,
                event=event
            )
        ```
        """
        event_type = event.get("type", "stdout")
        content = event.get("content", "")
        metadata = event.get("metadata", {})
        
        # Check if agent is paused
        if agent_id in self._pause_events:
            pause_event = self._pause_events[agent_id]
            if not pause_event.is_set():
                # Wait until resumed
                await pause_event.wait()
        
        # Check if agent should stop
        if agent_id in self._stop_events:
            stop_event = self._stop_events[agent_id]
            if stop_event.is_set():
                raise StopIteration("Agent execution stopped by user")
        
        # Map to output type
        output_type = self._map_event_to_output_type(event_type)
        
        # Get sequence number
        result = await self.db.execute(
            select(func.coalesce(
                func.max(AgentTerminalOutput.sequence_number), 0
            ))
            .where(AgentTerminalOutput.agent_id == agent_id)
        )
        sequence = result.scalar() + 1
        
        # Store in database
        output = AgentTerminalOutput(
            agent_id=agent_id,
            task_id=task_id,
            output_type=output_type.value,
            content=content,
            sequence_number=sequence,
            iteration=metadata.get("iteration"),
            metadata=metadata
        )
        self.db.add(output)
        
        # Log important events
        if event_type in ["action", "error", "iteration_end"]:
            log = AgentExecutionLog(
                agent_id=agent_id,
                task_id=task_id,
                level=self._map_event_to_log_level(event_type),
                message=self._format_log_message(event),
                action=event_type,
                iteration=metadata.get("iteration"),
                command_executed=metadata.get("command"),
                exit_code=metadata.get("exit_code"),
                tokens_used=metadata.get("tokens"),
                cost_usd=metadata.get("cost"),
                metadata=metadata
            )
            self.db.add(log)
        
        await self.db.commit()
        
        # Broadcast to WebSocket clients
        await self.websocket_manager.broadcast_to_agent(
            agent_id,
            {
                "type": "agent_output",
                "output_type": output_type.value,
                "content": content,
                "sequence": sequence,
                "iteration": metadata.get("iteration"),
                "timestamp": output.created_at.isoformat(),
                "metadata": metadata
            }
        )
        
        # Update agent last_active
        await self.db.execute(
            update(Agent)
            .where(Agent.id == agent_id)
            .values(last_active_at=datetime.utcnow())
        )
        await self.db.commit()
    
    def _map_event_to_output_type(self, event_type: str) -> OutputType:
        """Map OpenHands event type to OutputType."""
        mapping = {
            "action": OutputType.ACTION,
            "observation": OutputType.OBSERVATION,
            "thought": OutputType.THOUGHT,
            "stdout": OutputType.STDOUT,
            "stderr": OutputType.STDERR,
            "error": OutputType.ERROR,
        }
        return mapping.get(event_type, OutputType.STDOUT)
    
    def _map_event_to_log_level(self, event_type: str) -> str:
        """Map event type to log level."""
        if event_type == "error":
            return LogLevel.ERROR.value
        elif event_type in ["action", "iteration_end"]:
            return LogLevel.INFO.value
        return LogLevel.DEBUG.value
    
    def _format_log_message(self, event: Dict) -> str:
        """Format event into log message."""
        event_type = event.get("type")
        content = event.get("content", "")
        metadata = event.get("metadata", {})
        
        if event_type == "action":
            return f"Action: {metadata.get('action_name', 'unknown')} - {content[:100]}"
        elif event_type == "iteration_end":
            return f"Iteration {metadata.get('iteration')} completed"
        elif event_type == "error":
            return f"Error: {content}"
        
        return content[:200]
    
    async def pause_agent(self, agent_id: UUID):
        """Pause agent execution."""
        if agent_id not in self._pause_events:
            self._pause_events[agent_id] = asyncio.Event()
            self._pause_events[agent_id].set()  # Start unpaused
        
        # Clear the event (pause)
        self._pause_events[agent_id].clear()
        
        # Update agent status
        await self.db.execute(
            update(Agent)
            .where(Agent.id == agent_id)
            .values(status=AgentStatus.SUSPENDED.value)
        )
        await self.db.commit()
        
        # Broadcast status change
        await self.websocket_manager.broadcast_to_agent(
            agent_id,
            {
                "type": "agent_status_change",
                "status": AgentStatus.SUSPENDED.value,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def resume_agent(self, agent_id: UUID):
        """Resume paused agent execution."""
        if agent_id in self._pause_events:
            self._pause_events[agent_id].set()
        
        # Update agent status
        await self.db.execute(
            update(Agent)
            .where(Agent.id == agent_id)
            .values(status=AgentStatus.WORKING.value)
        )
        await self.db.commit()
        
        # Broadcast status change
        await self.websocket_manager.broadcast_to_agent(
            agent_id,
            {
                "type": "agent_status_change",
                "status": AgentStatus.WORKING.value,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def stop_agent(self, agent_id: UUID):
        """Stop agent execution (graceful termination)."""
        if agent_id not in self._stop_events:
            self._stop_events[agent_id] = asyncio.Event()
        
        # Set stop flag
        self._stop_events[agent_id].set()
        
        # Update agent status
        await self.db.execute(
            update(Agent)
            .where(Agent.id == agent_id)
            .values(status=AgentStatus.TERMINATING.value)
        )
        await self.db.commit()
        
        # Broadcast status change
        await self.websocket_manager.broadcast_to_agent(
            agent_id,
            {
                "type": "agent_status_change",
                "status": AgentStatus.TERMINATING.value,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def search_agent_output(
        self,
        agent_id: UUID,
        query: str,
        task_id: Optional[UUID] = None,
        output_types: Optional[List[OutputType]] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Full-text search across agent terminal output.
        
        Uses PostgreSQL full-text search for efficient searching.
        """
        # Build base query
        search_query = select(AgentTerminalOutput).where(
            AgentTerminalOutput.agent_id == agent_id
        )
        
        if task_id:
            search_query = search_query.where(
                AgentTerminalOutput.task_id == task_id
            )
        
        if output_types:
            type_values = [t.value for t in output_types]
            search_query = search_query.where(
                AgentTerminalOutput.output_type.in_(type_values)
            )
        
        # Add full-text search
        # Use PostgreSQL to_tsvector and plainto_tsquery for search
        search_query = search_query.where(
            text("to_tsvector('english', content) @@ plainto_tsquery('english', :query)")
        ).params(query=query)
        
        # Order by relevance (ts_rank) and sequence
        search_query = search_query.order_by(
            text("ts_rank(to_tsvector('english', content), plainto_tsquery('english', :query)) DESC"),
            AgentTerminalOutput.sequence_number.desc()
        ).limit(limit)
        
        result = await self.db.execute(search_query)
        outputs = result.scalars().all()
        
        return [
            {
                "id": str(o.id),
                "sequence": o.sequence_number,
                "output_type": o.output_type,
                "content": o.content,
                "iteration": o.iteration,
                "task_id": str(o.task_id) if o.task_id else None,
                "timestamp": o.created_at.isoformat(),
                "metadata": o.metadata
            }
            for o in outputs
        ]
    
    def cleanup_agent_state(self, agent_id: UUID):
        """Clean up agent state after termination."""
        if agent_id in self._pause_events:
            del self._pause_events[agent_id]
        if agent_id in self._stop_events:
            del self._stop_events[agent_id]


class WebSocketManager:
    """Manage WebSocket connections for real-time agent streaming."""
    
    def __init__(self):
        # Map: agent_id -> list of WebSocket connections
        self.agent_connections: Dict[UUID, List['WebSocket']] = {}
        
        # Map: user_id -> list of WebSocket connections (for dashboard)
        self.user_connections: Dict[UUID, List['WebSocket']] = {}
        
        # Connection metadata
        self.connection_metadata: Dict['WebSocket', Dict] = {}
    
    async def connect_to_agent(
        self,
        websocket: 'WebSocket',
        agent_id: UUID,
        user_id: UUID
    ):
        """Register WebSocket connection for agent streaming."""
        await websocket.accept()
        
        if agent_id not in self.agent_connections:
            self.agent_connections[agent_id] = []
        
        self.agent_connections[agent_id].append(websocket)
        self.connection_metadata[websocket] = {
            "agent_id": agent_id,
            "user_id": user_id,
            "connected_at": datetime.utcnow()
        }
    
    async def connect_to_dashboard(
        self,
        websocket: 'WebSocket',
        user_id: UUID
    ):
        """Register WebSocket connection for dashboard updates."""
        await websocket.accept()
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        
        self.user_connections[user_id].append(websocket)
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "type": "dashboard",
            "connected_at": datetime.utcnow()
        }
    
    def disconnect(self, websocket: 'WebSocket'):
        """Remove WebSocket connection."""
        if websocket not in self.connection_metadata:
            return
        
        metadata = self.connection_metadata[websocket]
        
        # Remove from agent connections
        if "agent_id" in metadata:
            agent_id = metadata["agent_id"]
            if agent_id in self.agent_connections:
                self.agent_connections[agent_id].remove(websocket)
                if not self.agent_connections[agent_id]:
                    del self.agent_connections[agent_id]
        
        # Remove from user connections
        if "user_id" in metadata:
            user_id = metadata["user_id"]
            if user_id in self.user_connections:
                if websocket in self.user_connections[user_id]:
                    self.user_connections[user_id].remove(websocket)
                    if not self.user_connections[user_id]:
                        del self.user_connections[user_id]
        
        del self.connection_metadata[websocket]
    
    async def broadcast_to_agent(self, agent_id: UUID, message: Dict):
        """Broadcast message to all connections watching this agent."""
        if agent_id not in self.agent_connections:
            return
        
        dead_connections = []
        
        for connection in self.agent_connections[agent_id]:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        
        # Clean up dead connections
        for connection in dead_connections:
            self.disconnect(connection)
    
    async def broadcast_to_user(self, user_id: UUID, message: Dict):
        """Broadcast message to all dashboard connections for user."""
        if user_id not in self.user_connections:
            return
        
        dead_connections = []
        
        for connection in self.user_connections[user_id]:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        
        # Clean up dead connections
        for connection in dead_connections:
            self.disconnect(connection)
    
    def get_connection_count(self, agent_id: UUID) -> int:
        """Get number of active connections for agent."""
        return len(self.agent_connections.get(agent_id, []))
```

```python:src/api/websocket_endpoints.py
"""
WebSocket API Endpoints for Real-time Agent Streaming
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID
import json

from database import get_db
from models import Agent, AgentTerminalOutput, User
from services.agent_streaming import WebSocketManager, AgentStreamingService
from api.dependencies import get_current_user_from_token

router = APIRouter()

# Global WebSocket manager instance
websocket_manager = WebSocketManager()


async def get_streaming_service(
    db: AsyncSession = Depends(get_db)
) -> AgentStreamingService:
    """Dependency to get streaming service."""
    return AgentStreamingService(db, websocket_manager)


@router.websocket("/ws/agents/{agent_id}/stream")
async def agent_output_stream(
    websocket: WebSocket,
    agent_id: UUID,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time agent terminal output.
    
    Usage from frontend:
    ```javascript
    const ws = new WebSocket(
        `ws://localhost:8000/api/v1/ws/agents/${agentId}/stream?token=${token}`
    );
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(data);
    };
    ```
    """
    # Authenticate user from token
    user = await get_current_user_from_token(token, db)
    if not user:
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    # Verify agent exists and user has access
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        await websocket.close(code=1008, reason="Agent not found")
        return
    
    # TODO: Add authorization check here
    # await check_agent_access(user.id, agent_id, db)
    
    await websocket_manager.connect_to_agent(websocket, agent_id, user.id)
    
    try:
        # Send historical output first (last 100 lines)
        result = await db.execute(
            select(AgentTerminalOutput)
            .where(AgentTerminalOutput.agent_id == agent_id)
            .order_by(AgentTerminalOutput.sequence_number.desc())
            .limit(100)
        )
        
        historical = list(reversed(result.scalars().all()))
        
        for output in historical:
            await websocket.send_json({
                "type": "agent_output",
                "output_type": output.output_type,
                "content": output.content,
                "sequence": output.sequence_number,
                "iteration": output.iteration,
                "timestamp": output.created_at.isoformat(),
                "metadata": output.metadata
            })
        
        # Send current agent status
        await websocket.send_json({
            "type": "agent_status",
            "status": agent.status,
            "current_task_id": str(agent.current_task_id) if agent.current_task_id else None,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive and handle commands
        while True:
            data = await websocket.receive_json()
            command = data.get("command")
            
            if command == "ping":
                await websocket.send_json({"type": "pong"})
            
            elif command == "pause":
                streaming_service = await get_streaming_service(db)
                await streaming_service.pause_agent(agent_id)
            
            elif command == "resume":
                streaming_service = await get_streaming_service(db)
                await streaming_service.resume_agent(agent_id)
            
            elif command == "stop":
                streaming_service = await get_streaming_service(db)
                await streaming_service.stop_agent(agent_id)
            
            elif command == "get_stats":
                # Send current stats
                stats = await get_agent_stats(agent_id, db)
                await websocket.send_json({
                    "type": "agent_stats",
                    "stats": stats
                })
    
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))
        websocket_manager.disconnect(websocket)


@router.websocket("/ws/dashboard")
async def dashboard_stream(
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time dashboard updates.
    
    Receives updates about:
    - Agent status changes
    - Task completions
    - System metrics
    """
    user = await get_current_user_from_token(token, db)
    if not user:
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    await websocket_manager.connect_to_dashboard(websocket, user.id)
    
    try:
        # Send initial dashboard data
        dashboard_data = await get_dashboard_data(user.id, db)
        await websocket.send_json({
            "type": "dashboard_init",
            "data": dashboard_data
        })
        
        # Keep alive
        while True:
            data = await websocket.receive_json()
            
            if data.get("command") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("command") == "refresh":
                dashboard_data = await get_dashboard_data(user.id, db)
                await websocket.send_json({
                    "type": "dashboard_update",
                    "data": dashboard_data
                })
    
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))
        websocket_manager.disconnect(websocket)


async def get_agent_stats(agent_id: UUID, db: AsyncSession) -> Dict:
    """Get current agent statistics."""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    agent = result.scalar_one()
    
    # Get output counts
    output_counts = await db.execute(
        select(
            AgentTerminalOutput.output_type,
            func.count(AgentTerminalOutput.id)
        )
        .where(AgentTerminalOutput.agent_id == agent_id)
        .group_by(AgentTerminalOutput.output_type)
    )
    
    return {
        "agent_id": str(agent.id),
        "status": agent.status,
        "tasks_completed": agent.tasks_completed,
        "tasks_failed": agent.tasks_failed,
        "total_execution_time_minutes": agent.total_execution_time_minutes,
        "total_tokens": agent.total_llm_tokens,
        "total_cost_usd": agent.total_cost_usd,
        "output_counts": {
            output_type: count 
            for output_type, count in output_counts
        },
        "uptime_minutes": (
            (datetime.utcnow() - agent.created_at).total_seconds() / 60
        ),
        "last_active": agent.last_active_at.isoformat() if agent.last_active_at else None
    }


async def get_dashboard_data(user_id: UUID, db: AsyncSession) -> Dict:
    """Get dashboard data for user."""
    # Get user's active agents
    result = await db.execute(
        select(Agent)
        .where(
            Agent.spawned_by == user_id,
            Agent.status.in_([
                AgentStatus.IDLE.value,
                AgentStatus.WORKING.value,
                AgentStatus.SUSPENDED.value
            ])
        )
    )
    agents = result.scalars().all()
    
    # Aggregate stats
    total_tasks = sum(a.tasks_completed + a.tasks_failed for a in agents)
    total_cost = sum(a.total_cost_usd for a in agents)
    
    return {
        "active_agents": len(agents),
        "total_tasks_completed": sum(a.tasks_completed for a in agents),
        "total_tasks_failed": sum(a.tasks_failed for a in agents),
        "total_cost_usd": total_cost,
        "agents": [
            {
                "id": str(a.id),
                "name": a.name,
                "status": a.status,
                "current_task_id": str(a.current_task_id) if a.current_task_id else None,
                "tasks_completed": a.tasks_completed
            }
            for a in agents
        ]
    }
```

```python:src/api/agent_endpoints.py
"""
REST API Endpoints for Agent Management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime, timedelta

from database import get_db
from models import Agent, AgentTerminalOutput, AgentExecutionLog, OutputType
from services.agent_streaming import AgentStreamingService, websocket_manager
from api.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


class AgentOutputResponse(BaseModel):
    sequence: int
    output_type: str
    content: str
    iteration: Optional[int]
    timestamp: str
    metadata: Optional[dict]

class AgentSearchRequest(BaseModel):
    query: str
    task_id: Optional[UUID] = None
    output_types: Optional[List[str]] = None
    limit: int = 50

class AgentPerformanceMetrics(BaseModel):
    agent_id: UUID
    agent_name: str
    agent_type: str
    status: str
    
    # Task metrics
    tasks_completed: int
    tasks_failed: int
    success_rate: float
    
    # Time metrics
    total_execution_time_minutes: float
    avg_task_duration_minutes: float
    uptime_hours: float
    
    # Cost metrics
    total_tokens: int
    total_cost_usd: float
    cost_per_task: float
    
    # Activity
    last_active_at: Optional[str]
    created_at: str


@router.get("/{agent_id}/output", response_model=List[AgentOutputResponse])
async def get_agent_output(
    agent_id: UUID,
    task_id: Optional[UUID] = None,
    output_type: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get terminal output from agent execution.
    
    Supports pagination and filtering by task and output type.
    """
    query = select(AgentTerminalOutput).where(
        AgentTerminalOutput.agent_id == agent_id
    )
    
    if task_id:
        query = query.where(AgentTerminalOutput.task_id == task_id)
    
    if output_type:
        query = query.where(AgentTerminalOutput.output_type == output_type)
    
    query = query.order_by(
        AgentTerminalOutput.sequence_number
    ).limit(limit).offset(offset)
    
    result = await db.execute(query)
    outputs = result.scalars().all()
    
    return [
        AgentOutputResponse(
            sequence=o.sequence_number,
            output_type=o.output_type,
            content=o.content,
            iteration=o.iteration,
            timestamp=o.created_at.isoformat(),
            metadata=o.metadata
        )
        for o in outputs
    ]


@router.post("/{agent_id}/search", response_model=List[AgentOutputResponse])
async def search_agent_output(
    agent_id: UUID,
    request: AgentSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Full-text search across agent terminal output.
    
    Uses PostgreSQL full-text search for efficient searching.
    """
    streaming_service = AgentStreamingService(db, websocket_manager)
    
    # Convert string output types to OutputType enums
    output_types = None
    if request.output_types:
        output_types = [OutputType(t) for t in request.output_types]
    
    results = await streaming_service.search_agent_output(
        agent_id=agent_id,
        query=request.query,
        task_id=request.task_id,
        output_types=output_types,
        limit=request.limit
    )
    
    return [
        AgentOutputResponse(
            sequence=r["sequence"],
            output_type=r["output_type"],
            content=r["content"],
            iteration=r["iteration"],
            timestamp=r["timestamp"],
            metadata=r["metadata"]
        )
        for r in results
    ]


@router.post("/{agent_id}/pause")
async def pause_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Pause agent execution."""
    streaming_service = AgentStreamingService(db, websocket_manager)
    await streaming_service.pause_agent(agent_id)
    return {"status": "paused"}


@router.post("/{agent_id}/resume")
async def resume_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Resume paused agent execution."""
    streaming_service = AgentStreamingService(db, websocket_manager)
    await streaming_service.resume_agent(agent_id)
    return {"status": "resumed"}


@router.post("/{agent_id}/stop")
async def stop_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Stop agent execution (graceful termination)."""
    streaming_service = AgentStreamingService(db, websocket_manager)
    await streaming_service.stop_agent(agent_id)
    return {"status": "stopping"}


@router.get("/{agent_id}/performance", response_model=AgentPerformanceMetrics)
async def get_agent_performance(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get detailed performance metrics for an agent."""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(404, "Agent not found")
    
    # Calculate metrics
    total_tasks = agent.tasks_completed + agent.tasks_failed
    success_rate = (
        agent.tasks_completed / total_tasks if total_tasks > 0 else 0.0
    )
    
    avg_duration = (
        agent.total_execution_time_minutes / agent.tasks_completed
        if agent.tasks_completed > 0 else 0.0
    )
    
    cost_per_task = (
        agent.total_cost_usd / total_tasks if total_tasks > 0 else 0.0
    )
    
    uptime = (datetime.utcnow() - agent.created_at).total_seconds() / 3600
    
    return AgentPerformanceMetrics(
        agent_id=agent.id,
        agent_name=agent.name,
        agent_type=agent.agent_type,
        status=agent.status,
        tasks_completed=agent.tasks_completed,
        tasks_failed=agent.tasks_failed,
        success_rate=success_rate,
        total_execution_time_minutes=agent.total_execution_time_minutes,
        avg_task_duration_minutes=avg_duration,
        uptime_hours=uptime,
        total_tokens=agent.total_llm_tokens,
        total_cost_usd=agent.total_cost_usd,
        cost_per_task=cost_per_task,
        last_active_at=agent.last_active_at.isoformat() if agent.last_active_at else None,
        created_at=agent.created_at.isoformat()
    )


@router.get("/performance/dashboard")
async def get_performance_dashboard(
    organization_id: UUID,
    time_range: str = Query("7d", regex="^(1d|7d|30d|all)$"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get performance dashboard data for all agents in organization.
    
    Returns aggregate metrics and individual agent performance.
    """
    # Calculate time filter
    time_filters = {
        "1d": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "all": None
    }
    
    time_filter = time_filters[time_range]
    
    # Build query
    query = select(Agent).where(Agent.organization_id == organization_id)
    
    if time_filter:
        cutoff = datetime.utcnow() - time_filter
        query = query.where(Agent.created_at >= cutoff)
    
    result = await db.execute(query)
    agents = result.scalars().all()
    
    # Calculate aggregate metrics
    total_agents = len(agents)
    active_agents = sum(
        1 for a in agents 
        if a.status in [AgentStatus.IDLE.value, AgentStatus.WORKING.value]
    )
    
    total_tasks_completed = sum(a.tasks_completed for a in agents)
    total_tasks_failed = sum(a.tasks_failed for a in agents)
    total_tasks = total_tasks_completed + total_tasks_failed
    
    overall_success_rate = (
        total_tasks_completed / total_tasks if total_tasks > 0 else 0.0
    )
    
    total_cost = sum(a.total_cost_usd for a in agents)
    total_execution_time = sum(a.total_execution_time_minutes for a in agents)
    
    # Get performance by agent type
    type_performance = {}
    for agent in agents:
        if agent.agent_type not in type_performance:
            type_performance[agent.agent_type] = {
                "count": 0,
                "tasks_completed": 0,
                "tasks_failed": 0,
                "total_cost": 0.0
            }
        
        type_performance[agent.agent_type]["count"] += 1
        type_performance[agent.agent_type]["tasks_completed"] += agent.tasks_completed
        type_performance[agent.agent_type]["tasks_failed"] += agent.tasks_failed
        type_performance[agent.agent_type]["total_cost"] += agent.total_cost_usd
    
    # Get recent activity
    recent_logs = await db.execute(
        select(AgentExecutionLog)
        .where(
            AgentExecutionLog.agent_id.in_([a.id for a in agents]),
            AgentExecutionLog.level == LogLevel.INFO.value
        )
        .order_by(desc(AgentExecutionLog.created_at))
        .limit(20)
    )
    
    return {
        "time_range": time_range,
        "summary": {
            "total_agents": total_agents,
            "active_agents": active_agents,
            "total_tasks_completed": total_tasks_completed,
            "total_tasks_failed": total_tasks_failed,
            "overall_success_rate": overall_success_rate,
            "total_cost_usd": total_cost,
            "total_execution_hours": total_execution_time / 60,
            "avg_cost_per_task": total_cost / total_tasks if total_tasks > 0 else 0.0
        },
        "by_agent_type": type_performance,
        "top_performers": [
            {
                "agent_id": str(a.id),
                "name": a.name,
                "type": a.agent_type,
                "tasks_completed": a.tasks_completed,
                "success_rate": (
                    a.tasks_completed / (a.tasks_completed + a.tasks_failed)
                    if (a.tasks_completed + a.tasks_failed) > 0 else 0.0
                )
            }
            for a in sorted(
                agents,
                key=lambda x: x.tasks_completed,
                reverse=True
            )[:10]
        ],
        "recent_activity": [
            {
                "agent_id": str(log.agent_id),
                "message": log.message,
                "timestamp": log.created_at.isoformat()
            }
            for log in recent_logs.scalars()
        ]
    }
```

```typescript:frontend/src/components/AgentTerminal.tsx
/**
 * Agent Terminal Component
 * Real-time display of agent execution output
 */

import React, { useEffect, useState, useRef } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';

interface AgentOutput {
  type: string;
  output_type: string;
  content: string;
  sequence: number;
  iteration?: number;
  timestamp: string;
  metadata?: any;
}

interface AgentTerminalProps {
  agentId: string;
  token: string;
  onStatusChange?: (status: string) => void;
}

export const AgentTerminal: React.FC<AgentTerminalProps> = ({
  agentId,
  token,
  onStatusChange
}) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const terminal = useRef<Terminal | null>(null);
  const fitAddon = useRef<FitAddon | null>(null);
  const ws = useRef<WebSocket | null>(null);
  
  const [isConnected, setIsConnected] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (!terminalRef.current) return;

    // Initialize terminal
    terminal.current = new Terminal({
      theme: {
        background: '#1e1e1e',
        foreground: '#d4d4d4',
        cursor: '#ffffff',
        black: '#000000',
        red: '#cd3131',
        green: '#0dbc79',
        yellow: '#e5e510',
        blue: '#2472c8',
        magenta: '#bc3fbc',
        cyan: '#11a8cd',
        white: '#e5e5e5',
      },
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      fontSize: 13,
      cursorBlink: true,
      scrollback: 10000,
    });

    fitAddon.current = new FitAddon();
    terminal.current.loadAddon(fitAddon.current);
    
    terminal.current.open(terminalRef.current);
    fitAddon.current.fit();

    // Connect WebSocket
    connectWebSocket();

    // Handle window resize
    const handleResize = () => {
      fitAddon.current?.fit();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      terminal.current?.dispose();
      ws.current?.close();
      window.removeEventListener('resize', handleResize);
    };
  }, [agentId, token]);

  const connectWebSocket = () => {
    const wsUrl = `ws://localhost:8000/api/v1/ws/agents/${agentId}/stream?token=${token}`;
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      setIsConnected(true);
      terminal.current?.writeln('\x1b[32m✓ Connected to agent\x1b[0m\n');
    };

    ws.current.onmessage = (event) => {
      const data: AgentOutput = JSON.parse(event.data);
      handleMessage(data);
    };

    ws.current.onerror = (error) => {
      terminal.current?.writeln(`\x1b[31m✗ WebSocket error\x1b[0m`);
      setIsConnected(false);
    };

    ws.current.onclose = () => {
      setIsConnected(false);
      terminal.current?.writeln('\x1b[33m○ Disconnected from agent\x1b[0m');
    };
  };

  const handleMessage = (data: AgentOutput) => {
    if (data.type === 'agent_output') {
      const color = getOutputColor(data.output_type);
      const prefix = getOutputPrefix(data.output_type);
      
      // Format output with color and prefix
      const formattedContent = `${color}${prefix}${data.content}\x1b[0m`;
      terminal.current?.writeln(formattedContent);

      // Auto-scroll to bottom if enabled
      if (autoScroll) {
        terminal.current?.scrollToBottom();
      }
    } else if (data.type === 'agent_status') {
      terminal.current?.writeln(
        `\x1b[36m[STATUS] ${data.status}\x1b[0m`
      );
      onStatusChange?.(data.status);
    } else if (data.type === 'agent_status_change') {
      terminal.current?.writeln(
        `\x1b[36m[STATUS CHANGE] ${data.status}\x1b[0m`
      );
      onStatusChange?.(data.status);
      
      if (data.status === 'suspended') {
        setIsPaused(true);
      } else if (data.status === 'working') {
        setIsPaused(false);
      }
    }
  };

  const getOutputColor = (outputType: string): string => {
    const colors: Record<string, string> = {
      action: '\x1b[33m',      // Yellow
      observation: '\x1b[36m', // Cyan
      thought: '\x1b[35m',     // Magenta
      stdout: '\x1b[37m',      // White
      stderr: '\x1b[31m',      // Red
      error: '\x1b[91m',       // Bright red
    };
    return colors[outputType] || '\x1b[37m';
  };

  const getOutputPrefix = (outputType: string): string => {
    const prefixes: Record<string, string> = {
      action: '[ACTION] ',
      observation: '[OBSERVE] ',
      thought: '[THINK] ',
      stdout: '',
      stderr: '[ERROR] ',
      error: '[ERROR] ',
    };
    return prefixes[outputType] || '';
  };

  const sendCommand = (command: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ command }));
    }
  };

  const handlePause = () => {
    sendCommand('pause');
  };

  const handleResume = () => {
    sendCommand('resume');
  };

  const handleStop = () => {
    if (window.confirm('Are you sure you want to stop this agent?')) {
      sendCommand('stop');
    }
  };

  const handleClear = () => {
    terminal.current?.clear();
  };

  return (
    <div className="agent-terminal-container">
      <div className="terminal-controls">
        <div className="status-indicator">
          <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`} />
          {isConnected ? 'Connected' : 'Disconnected'}
        </div>
        
        <div className="control-buttons">
          <button
            onClick={handlePause}
            disabled={isPaused || !isConnected}
            className="btn btn-warning"
          >
            ⏸ Pause
          </button>
          
          <button
            onClick={handleResume}
            disabled={!isPaused || !isConnected}
            className="btn btn-success"
          >
            ▶ Resume
          </button>
          
          <button
            onClick={handleStop}
            disabled={!isConnected}
            className="btn btn-danger"
          >
            ⏹ Stop
          </button>
          
          <button
            onClick={handleClear}
            className="btn btn-secondary"
          >
            🗑 Clear
          </button>

          <label className="auto-scroll-toggle">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
            />
            Auto-scroll
          </label>
        </div>
      </div>

      <div ref={terminalRef} className="terminal-display" />

      <style jsx>{`
        .agent-terminal-container {
          display: flex;
          flex-direction: column;
          height: 100%;
          background: #1e1e1e;
          border-radius: 8px;
          overflow: hidden;
        }

        .terminal-controls {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          background: #2d2d2d;
          border-bottom: 1px solid #3e3e3e;
        }

        .status-indicator {
          display: flex;
          align-items: center;
          gap: 8px;
          color: #d4d4d4;
          font-size: 14px;
        }

        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #666;
        }

        .status-dot.connected {
          background: #0dbc79;
          box-shadow: 0 0 8px #0dbc79;
        }

        .control-buttons {
          display: flex;
          gap: 8px;
          align-items: center;
        }

        .btn {
          padding: 6px 12px;
          border: none;
          border-radius: 4px;
          font-size: 13px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .btn-warning {
          background: #e5e510;
          color: #000;
        }

        .btn-success {
          background: #0dbc79;
          color: #fff;
        }

        .btn-danger {
          background: #cd3131;
          color: #fff;
        }

        .btn-secondary {
          background: #3e3e3e;
          color: #d4d4d4;
        }

        .auto-scroll-toggle {
          display: flex;
          align-items: center;
          gap: 6px;
          color: #d4d4d4;
          font-size: 13px;
          cursor: pointer;
        }

        .terminal-display {
          flex: 1;
          padding: 8px;
        }
      `}</style>
    </div>
  );
};
```

```typescript:frontend/src/components/AgentPerformanceDashboard.tsx
/**
 * Agent Performance Dashboard
 * Displays aggregate metrics and individual agent performance
 */

import React, { useEffect, useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

interface DashboardData {
  time_range: string;
  summary: {
    total_agents: number;
    active_agents: number;
    total_tasks_completed: number;
    total_tasks_failed: number;
    overall_success_rate: number;
    total_cost_usd: number;
    total_execution_hours: number;
    avg_cost_per_task: number;
  };
  by_agent_type: Record<string, any>;
  top_performers: Array<{
    agent_id: string;
    name: string;
    type: string;
    tasks_completed: number;
    success_rate: number;
  }>;
  recent_activity: Array<{
    agent_id: string;
    message: string;
    timestamp: string;
  }>;
}

interface AgentPerformanceDashboardProps {
  organizationId: string;
  token: string;
}

export const AgentPerformanceDashboard: React.FC<AgentPerformanceDashboardProps> = ({
  organizationId,
  token
}) => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [timeRange, setTimeRange] = useState('7d');
  const [loading, setLoading] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    fetchDashboardData();
    connectWebSocket();

    const interval = setInterval(fetchDashboardData, 30000); // Refresh every 30s

    return () => {
      clearInterval(interval);
    };
  }, [timeRange]);

  const fetchDashboardData = async () => {
    try {
      const response = await fetch(
        `/api/v1/agents/performance/dashboard?organization_id=${organizationId}&time_range=${timeRange}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      const data = await response.json();
      setData(data);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const connectWebSocket = () => {
    const ws = new WebSocket(
      `ws://localhost:8000/api/v1/ws/dashboard?token=${token}`
    );

    ws.onopen = () => {
      setWsConnected(true);
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'dashboard_update') {
        setData(message.data);
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
    };
  };

  if (loading || !data) {
    return <div className="dashboard-loading">Loading dashboard...</div>;
  }

  // Prepare chart data
  const agentTypeData = {
    labels: Object.keys(data.by_agent_type),
    datasets: [
      {
        label: 'Tasks Completed',
        data: Object.values(data.by_agent_type).map((t: any) => t.tasks_completed),
        backgroundColor: 'rgba(13, 188, 121, 0.6)',
      },
      {
        label: 'Tasks Failed',
        data: Object.values(data.by_agent_type).map((t: any) => t.tasks_failed),
        backgroundColor: 'rgba(205, 49, 49, 0.6)',
      }
    ]
  };

  const costData = {
    labels: Object.keys(data.by_agent_type),
    datasets: [{
      label: 'Cost ($)',
      data: Object.values(data.by_agent_type).map((t: any) => t.total_cost),
      backgroundColor: [
        'rgba(36, 114, 200, 0.6)',
        'rgba(229, 229, 16, 0.6)',
        'rgba(188, 63, 188, 0.6)',
        'rgba(17, 168, 205, 0.6)',
      ]
    }]
  };

  return (
    <div className="performance-dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <h1>Agent Performance Dashboard</h1>
        <div className="header-controls">
          <div className="ws-status">
            <span className={`status-dot ${wsConnected ? 'connected' : ''}`} />
            {wsConnected ? 'Live' : 'Offline'}
          </div>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="time-range-selector"
          >
            <option value="1d">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="all">All time</option>
          </select>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="summary-cards">
        <div className="summary-card">
          <div className="card-icon">🤖</div>
          <div className="card-content">
            <div className="card-value">{data.summary.active_agents}/{data.summary.total_agents}</div>
            <div className="card-label">Active Agents</div>
          </div>
        </div>

        <div className="summary-card">
          <div className="card-icon">✅</div>
          <div className="card-content">
            <div className="card-value">{data.summary.total_tasks_completed}</div>
            <div className="card-label">Tasks Completed</div>
          </div>
        </div>

        <div className="summary-card">
          <div className="card-icon">📊</div>
          <div className="card-content">
            <div className="card-value">
              {(data.summary.overall_success_rate * 100).toFixed(1)}%
            </div>
            <div className="card-label">Success Rate</div>
          </div>
        </div>

        <div className="summary-card">
          <div className="card-icon">💰</div>
          <div className="card-content">
            <div className="card-value">${data.summary.total_cost_usd.toFixed(2)}</div>
            <div className="card-label">Total Cost</div>
          </div>
        </div>

        <div className="summary-card">
          <div className="card-icon">⏱️</div>
          <div className="card-content">
            <div className="card-value">
              {data.summary.total_execution_hours.toFixed(1)}h
            </div>
            <div className="card-label">Execution Time</div>
          </div>
        </div>

        <div className="summary-card">
          <div className="card-icon">💵</div>
          <div className="card-content">
            <div className="card-value">
              ${data.summary.avg_cost_per_task.toFixed(3)}
            </div>
            <div className="card-label">Avg Cost/Task</div>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="charts-container">
        <div className="chart-card">
          <h3>Tasks by Agent Type</h3>
          <Bar data={agentTypeData} options={{
            responsive: true,
            maintainAspectRatio: false
          }} />
        </div>

        <div className="chart-card">
          <h3>Cost Distribution</h3>
          <Doughnut data={costData} options={{
            responsive: true,
            maintainAspectRatio: false
          }} />
        </div>
      </div>

      {/* Top Performers */}
      <div className="top-performers">
        <h3>Top Performing Agents</h3>
        <div className="performers-list">
          {data.top_performers.map((agent, idx) => (
            <div key={agent.agent_id} className="performer-card">
              <div className="rank">#{idx + 1}</div>
              <div className="performer-info">
                <div className="performer-name">{agent.name}</div>
                <div className="performer-type">{agent.type}</div>
              </div>
              <div className="performer-stats">
                <div className="stat">
                  <span className="stat-value">{agent.tasks_completed}</span>
                  <span className="stat-label">tasks</span>
                </div>
                <div className="stat">
                  <span className="stat-value">
                    {(agent.success_rate * 100).toFixed(0)}%
                  </span>
                  <span className="stat-label">success</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="recent-activity">
        <h3>Recent Activity</h3>
        <div className="activity-list">
          {data.recent_activity.map((activity, idx) => (
            <div key={idx} className="activity-item">
              <div className="activity-time">
                {new Date(activity.timestamp).toLocaleTimeString()}
              </div>
              <div className="activity-message">{activity.message}</div>
            </div>
          ))}
        </div>
      </div>

      <style jsx>{`
        .performance-dashboard {
          padding: 24px;
          background: #f5f5f5;
          min-height: 100vh;
        }

        .dashboard-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
        }

        .dashboard-header h1 {
          margin: 0;
          font-size: 28px;
          color: #1e1e1e;
        }

        .header-controls {
          display: flex;
          gap: 16px;
          align-items: center;
        }

        .ws-status {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 16px;
          background: white;
          border-radius: 8px;
          font-size: 14px;
        }

        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #666;
        }

        .status-dot.connected {
          background: #0dbc79;
          box-shadow: 0 0 8px #0dbc79;
        }

        .time-range-selector {
          padding: 8px 16px;
          border: 1px solid #ddd;
          border-radius: 8px;
          font-size: 14px;
        }

        .summary-cards {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 16px;
          margin-bottom: 24px;
        }

        .summary-card {
          display: flex;
          align-items: center;
          gap: 16px;
          padding: 20px;
          background: white;
          border-radius: 12px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .card-icon {
          font-size: 32px;
        }

        .card-value {
          font-size: 24px;
          font-weight: bold;
          color: #1e1e1e;
        }

        .card-label {
          font-size: 14px;
          color: #666;
        }

        .charts-container {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
          gap: 24px;
          margin-bottom: 24px;
        }

        .chart-card {
          padding: 24px;
          background: white;
          border-radius: 12px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          height: 400px;
        }

        .chart-card h3 {
          margin: 0 0 16px 0;
          font-size: 18px;
          color: #1e1e1e;
        }

        .top-performers {
          margin-bottom: 24px;
        }

        .top-performers h3 {
          margin: 0 0 16px 0;
          font-size: 20px;
          color: #1e1e1e;
        }

        .performers-list {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 16px;
        }

        .performer-card {
          display: flex;
          align-items: center;
          gap: 16px;
          padding: 16px;
          background: white;
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .rank {
          font-size: 24px;
          font-weight: bold;
          color: #2472c8;
        }

        .performer-info {
          flex: 1;
        }

        .performer-name {
          font-weight: 600;
          color: #1e1e1e;
        }

        .performer-type {
          font-size: 12px;
          color: #666;
        }

        .performer-stats {
          display: flex;
          gap: 16px;
        }

        .stat {
          display: flex;
          flex-direction: column;
          align-items: center;
        }

        .stat-value {
          font-size: 18px;
          font-weight: bold;
          color: #0dbc79;
        }

        .stat-label {
          font-size: 11px;
          color: #999;
        }

        .recent-activity h3 {
          margin: 0 0 16px 0;
          font-size: 20px;
          color: #1e1e1e;
        }

        .activity-list {
          background: white;
          border-radius: 8px;
          padding: 16px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .activity-item {
          display: flex;
          gap: 16px;
          padding: 12px 0;
          border-bottom: 1px solid #eee;
        }

        .activity-item:last-child {
          border-bottom: none;
        }

        .activity-time {
          font-size: 12px;
          color: #999;
          min-width: 80px;
        }

        .activity-message {
          color: #1e1e1e;
        }
      `}</style>
    </div>
  );
};
```

```sql:migrations/add_fulltext_search.sql
-- Add full-text search support for agent terminal output

-- Create GIN index for full-text search on content
CREATE INDEX idx_agent_terminal_output_content_fts 
ON agent_terminal_outputs 
USING GIN (to_tsvector('english', content));

-- Create function for search ranking
CREATE OR REPLACE FUNCTION search_agent_output(
    p_agent_id UUID,
    p_query TEXT,
    p_task_id UUID DEFAULT NULL,
    p_output_types TEXT[] DEFAULT NULL,
    p_limit INT DEFAULT 50
)
RETURNS TABLE (
    id UUID,
    sequence_number INT,
    output_type VARCHAR(20),
    content TEXT,
    iteration INT,
    task_id UUID,
    created_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ato.id,
        ato.sequence_number,
        ato.output_type,
        ato.content,
        ato.iteration,
        ato.task_id,
        ato.created_at,
        ato.metadata,
        ts_rank(
            to_tsvector('english', ato.content),
            plainto_tsquery('english', p_query)
        ) as rank
    FROM agent_terminal_outputs ato
    WHERE 
        ato.agent_id = p_agent_id
        AND to_tsvector('english', ato.content) @@ plainto_tsquery('english', p_query)
        AND (p_task_id IS NULL OR ato.task_id = p_task_id)
        AND (p_output_types IS NULL OR ato.output_type = ANY(p_output_types))
    ORDER BY rank DESC, ato.sequence_number DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Create materialized view for agent performance (optional, for faster dashboard)
CREATE MATERIALIZED VIEW agent_performance_summary AS
SELECT 
    a.id as agent_id,
    a.name as agent_name,
    a.agent_type,
    a.status,
    a.organization_id,
    a.project_id,
    a.tasks_completed,
    a.tasks_failed,
    CASE 
        WHEN (a.tasks_completed + a.tasks_failed) > 0 
        THEN a.tasks_completed::FLOAT / (a.tasks_completed + a.tasks_failed)
        ELSE 0
    END as success_rate,
    a.total_execution_time_minutes,
    CASE 
        WHEN a.tasks_completed > 0 
        THEN a.total_execution_time_minutes / a.tasks_completed
        ELSE 0
    END as avg_task_duration_minutes,
    a.total_llm_tokens,
    a.total_cost_usd,
    CASE 
        WHEN (a.tasks_completed + a.tasks_failed) > 0 
        THEN a.total_cost_usd / (a.tasks_completed + a.tasks_failed)
        ELSE 0
    END as cost_per_task,
    EXTRACT(EPOCH FROM (NOW() - a.created_at)) / 3600 as uptime_hours,
    a.created_at,
    a.last_active_at
FROM agents a;

-- Create index on materialized view
CREATE INDEX idx_agent_performance_org ON agent_performance_summary(organization_id);
CREATE INDEX idx_agent_performance_project ON agent_performance_summary(project_id);

-- Create function to refresh materialized view
CREATE OR REPLACE FUNCTION refresh_agent_performance()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY agent_performance_summary;
END;
$$ LANGUAGE plpgsql;

-- Schedule automatic refresh (adjust as needed for your use case)
-- This would typically be done via a cron job or background task
```

This complete implementation provides:

1. **Streaming Output Capture**: `AgentStreamingService` hooks into OpenHands events
2. **WebSocket Endpoints**: Real-time streaming to frontend via WebSocket
3. **Terminal UI Component**: Full-featured terminal with xterm.js
4. **Performance Dashboard**: Comprehensive metrics and visualizations
5. **Agent Control**: Pause/resume/stop functionality
6. **Full-text Search**: PostgreSQL-based search with ranking

The system is production-ready with error handling, auto-reconnection, and efficient database queries. You can now integrate this with your existing OpenHands setup by hooking the `handle_openhands_event` method into your agent execution loop.



## Response:
11/19/2025, 10:37:19 AM

I'll create a comprehensive OAuth provider system with multiple options and integration paths.

```python:src/services/oauth/providers.py
"""
OAuth Provider Configuration and Management
Supports multiple OAuth 2.0 and OpenID Connect providers
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl
from dataclasses import dataclass
import secrets


class OAuthProviderType(str, Enum):
    """Supported OAuth providers."""
    # Major providers
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    
    # Social
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    DISCORD = "discord"
    SLACK = "slack"
    
    # Developer tools
    NOTION = "notion"
    FIGMA = "figma"
    LINEAR = "linear"
    JIRA = "jira"
    ASANA = "asana"
    
    # Cloud providers
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    DIGITALOCEAN = "digitalocean"
    HEROKU = "heroku"
    
    # Other
    OKTA = "okta"
    AUTH0 = "auth0"
    KEYCLOAK = "keycloak"
    CUSTOM = "custom"


class OAuthScope(str, Enum):
    """Common OAuth scopes across providers."""
    # Profile
    PROFILE = "profile"
    EMAIL = "email"
    OPENID = "openid"
    
    # Permissions
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    
    # Specific resources
    REPO = "repo"
    GIST = "gist"
    USER = "user"
    PROJECT = "project"
    ISSUE = "issue"
    
    # Cloud
    COMPUTE = "compute"
    STORAGE = "storage"
    DATABASE = "database"


@dataclass
class OAuthEndpoints:
    """OAuth provider endpoints."""
    authorize_url: str
    token_url: str
    userinfo_url: str
    revoke_url: Optional[str] = None
    device_code_url: Optional[str] = None


@dataclass
class OAuthProviderConfig:
    """OAuth provider configuration."""
    provider_type: OAuthProviderType
    display_name: str
    icon: str  # URL or emoji
    endpoints: OAuthEndpoints
    default_scopes: List[str]
    pkce_required: bool = False
    supports_refresh: bool = True
    userinfo_mapping: Dict[str, str] = None  # Map provider fields to our User model
    extra_authorize_params: Dict[str, str] = None
    

class OAuthProviderRegistry:
    """Registry of OAuth provider configurations."""
    
    _providers: Dict[OAuthProviderType, OAuthProviderConfig] = {}
    
    @classmethod
    def register(cls, config: OAuthProviderConfig):
        """Register a provider configuration."""
        cls._providers[config.provider_type] = config
    
    @classmethod
    def get(cls, provider_type: OAuthProviderType) -> Optional[OAuthProviderConfig]:
        """Get provider configuration."""
        return cls._providers.get(provider_type)
    
    @classmethod
    def list_providers(cls) -> List[OAuthProviderConfig]:
        """List all registered providers."""
        return list(cls._providers.values())
    
    @classmethod
    def get_by_name(cls, name: str) -> Optional[OAuthProviderConfig]:
        """Get provider by name."""
        try:
            provider_type = OAuthProviderType(name.lower())
            return cls.get(provider_type)
        except ValueError:
            return None


# Register major OAuth providers

# Google
OAuthProviderRegistry.register(OAuthProviderConfig(
    provider_type=OAuthProviderType.GOOGLE,
    display_name="Google",
    icon="https://www.google.com/favicon.ico",
    endpoints=OAuthEndpoints(
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        userinfo_url="https://www.googleapis.com/oauth2/v3/userinfo",
        revoke_url="https://oauth2.googleapis.com/revoke"
    ),
    default_scopes=["openid", "email", "profile"],
    pkce_required=True,
    userinfo_mapping={
        "email": "email",
        "name": "full_name",
        "picture": "avatar_url",
        "sub": "provider_user_id"
    }
))

# GitHub
OAuthProviderRegistry.register(OAuthProviderConfig(
    provider_type=OAuthProviderType.GITHUB,
    display_name="GitHub",
    icon="https://github.com/favicon.ico",
    endpoints=OAuthEndpoints(
        authorize_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        userinfo_url="https://api.github.com/user",
        revoke_url="https://api.github.com/applications/{client_id}/token"
    ),
    default_scopes=["user:email", "read:user"],
    userinfo_mapping={
        "email": "email",
        "name": "full_name",
        "login": "username",
        "avatar_url": "avatar_url",
        "id": "provider_user_id"
    }
))

# Microsoft (Azure AD)
OAuthProviderRegistry.register(OAuthProviderConfig(
    provider_type=OAuthProviderType.MICROSOFT,
    display_name="Microsoft",
    icon="https://www.microsoft.com/favicon.ico",
    endpoints=OAuthEndpoints(
        authorize_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        userinfo_url="https://graph.microsoft.com/v1.0/me"
    ),
    default_scopes=["openid", "email", "profile", "User.Read"],
    pkce_required=True,
    userinfo_mapping={
        "mail": "email",
        "displayName": "full_name",
        "userPrincipalName": "username",
        "id": "provider_user_id"
    }
))

# GitLab
OAuthProviderRegistry.register(OAuthProviderConfig(
    provider_type=OAuthProviderType.GITLAB,
    display_name="GitLab",
    icon="https://gitlab.com/favicon.ico",
    endpoints=OAuthEndpoints(
        authorize_url="https://gitlab.com/oauth/authorize",
        token_url="https://gitlab.com/oauth/token",
        userinfo_url="https://gitlab.com/api/v4/user",
        revoke_url="https://gitlab.com/oauth/revoke"
    ),
    default_scopes=["read_user", "email"],
    userinfo_mapping={
        "email": "email",
        "name": "full_name",
        "username": "username",
        "avatar_url": "avatar_url",
        "id": "provider_user_id"
    }
))

# Bitbucket
OAuthProviderRegistry.register(OAuthProviderConfig(
    provider_type=OAuthProviderType.BITBUCKET,
    display_name="Bitbucket",
    icon="https://bitbucket.org/favicon.ico",
    endpoints=OAuthEndpoints(
        authorize_url="https://bitbucket.org/site/oauth2/authorize",
        token_url="https://bitbucket.org/site/oauth2/access_token",
        userinfo_url="https://api.bitbucket.org/2.0/user"
    ),
    default_scopes=["account", "email"],
    userinfo_mapping={
        "email": "email",
        "display_name": "full_name",
        "username": "username",
        "uuid": "provider_user_id"
    }
))

# Slack
OAuthProviderRegistry.register(OAuthProviderConfig(
    provider_type=OAuthProviderType.SLACK,
    display_name="Slack",
    icon="https://slack.com/favicon.ico",
    endpoints=OAuthEndpoints(
        authorize_url="https://slack.com/oauth/v2/authorize",
        token_url="https://slack.com/api/oauth.v2.access",
        userinfo_url="https://slack.com/api/users.identity"
    ),
    default_scopes=["openid", "profile", "email"],
    userinfo_mapping={
        "email": "email",
        "name": "full_name",
        "sub": "provider_user_id"
    }
))

# Discord
OAuthProviderRegistry.register(OAuthProviderConfig(
    provider_type=OAuthProviderType.DISCORD,
    display_name="Discord",
    icon="https://discord.com/assets/favicon.ico",
    endpoints=OAuthEndpoints(
        authorize_url="https://discord.com/api/oauth2/authorize",
        token_url="https://discord.com/api/oauth2/token",
        userinfo_url="https://discord.com/api/users/@me",
        revoke_url="https://discord.com/api/oauth2/token/revoke"
    ),
    default_scopes=["identify", "email"],
    userinfo_mapping={
        "email": "email",
        "username": "username",
        "global_name": "full_name",
        "avatar": "avatar_url",
        "id": "provider_user_id"
    }
))

# LinkedIn
OAuthProviderRegistry.register(OAuthProviderConfig(
    provider_type=OAuthProviderType.LINKEDIN,
    display_name="LinkedIn",
    icon="https://linkedin.com/favicon.ico",
    endpoints=OAuthEndpoints(
        authorize_url="https://www.linkedin.com/oauth/v2/authorization",
        token_url="https://www.linkedin.com/oauth/v2/accessToken",
        userinfo_url="https://api.linkedin.com/v2/userinfo"
    ),
    default_scopes=["openid", "profile", "email"],
    pkce_required=True,
    userinfo_mapping={
        "email": "email",
        "name": "full_name",
        "sub": "provider_user_id"
    }
))

# Notion
OAuthProviderRegistry.register(OAuthProviderConfig(
    provider_type=OAuthProviderType.NOTION,
    display_name="Notion",
    icon="https://notion.so/favicon.ico",
    endpoints=OAuthEndpoints(
        authorize_url="https://api.notion.com/v1/oauth/authorize",
        token_url="https://api.notion.com/v1/oauth/token",
        userinfo_url="https://api.notion.com/v1/users/me"
    ),
    default_scopes=[],
    userinfo_mapping={
        "person.email": "email",
        "name": "full_name",
        "id": "provider_user_id"
    }
))

# Linear
OAuthProviderRegistry.register(OAuthProviderConfig(
    provider_type=OAuthProviderType.LINEAR,
    display_name="Linear",
    icon="https://linear.app/favicon.ico",
    endpoints=OAuthEndpoints(
        authorize_url="https://linear.app/oauth/authorize",
        token_url="https://api.linear.app/oauth/token",
        userinfo_url="https://api.linear.app/graphql"
    ),
    default_scopes=["read"],
    userinfo_mapping={
        "email": "email",
        "name": "full_name",
        "id": "provider_user_id"
    }
))

# Figma
OAuthProviderRegistry.register(OAuthProviderConfig(
    provider_type=OAuthProviderType.FIGMA,
    display_name="Figma",
    icon="https://figma.com/favicon.ico",
    endpoints=OAuthEndpoints(
        authorize_url="https://www.figma.com/oauth",
        token_url="https://www.figma.com/api/oauth/token",
        userinfo_url="https://api.figma.com/v1/me"
    ),
    default_scopes=["file_read"],
    userinfo_mapping={
        "email": "email",
        "handle": "username",
        "id": "provider_user_id"
    }
))

# Auth0 (configurable)
OAuthProviderRegistry.register(OAuthProviderConfig(
    provider_type=OAuthProviderType.AUTH0,
    display_name="Auth0",
    icon="https://auth0.com/favicon.ico",
    endpoints=OAuthEndpoints(
        authorize_url="https://{domain}/authorize",  # Replace with instance
        token_url="https://{domain}/oauth/token",
        userinfo_url="https://{domain}/userinfo"
    ),
    default_scopes=["openid", "profile", "email"],
    pkce_required=True,
    userinfo_mapping={
        "email": "email",
        "name": "full_name",
        "sub": "provider_user_id"
    }
))

# Okta (configurable)
OAuthProviderRegistry.register(OAuthProviderConfig(
    provider_type=OAuthProviderType.OKTA,
    display_name="Okta",
    icon="https://okta.com/favicon.ico",
    endpoints=OAuthEndpoints(
        authorize_url="https://{domain}/oauth2/default/v1/authorize",
        token_url="https://{domain}/oauth2/default/v1/token",
        userinfo_url="https://{domain}/oauth2/default/v1/userinfo"
    ),
    default_scopes=["openid", "profile", "email"],
    pkce_required=True,
    userinfo_mapping={
        "email": "email",
        "name": "full_name",
        "sub": "provider_user_id"
    }
))

# AWS Cognito (configurable)
OAuthProviderRegistry.register(OAuthProviderConfig(
    provider_type=OAuthProviderType.AWS,
    display_name="AWS Cognito",
    icon="https://aws.amazon.com/favicon.ico",
    endpoints=OAuthEndpoints(
        authorize_url="https://{domain}/oauth2/authorize",
        token_url="https://{domain}/oauth2/token",
        userinfo_url="https://{domain}/oauth2/userInfo"
    ),
    default_scopes=["openid", "email", "profile"],
    pkce_required=True,
    userinfo_mapping={
        "email": "email",
        "name": "full_name",
        "sub": "provider_user_id"
    }
))
```

```python:src/models/oauth.py
"""
OAuth Database Models
"""

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Dict
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.sql import func

from models.base import Base


class OAuthProvider(Base):
    """OAuth provider configuration for organization."""
    __tablename__ = "oauth_providers"
    
    # Identity
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    
    # Provider details
    provider_type: Mapped[str] = mapped_column(String(50), index=True)  # OAuthProviderType
    display_name: Mapped[str] = mapped_column(String(100))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # OAuth credentials
    client_id: Mapped[str] = mapped_column(String(500))
    client_secret_encrypted: Mapped[str] = mapped_column(String(1000))
    
    # Custom configuration (for configurable providers like Auth0, Okta)
    custom_domain: Mapped[Optional[str]] = mapped_column(String(255))
    custom_endpoints: Mapped[Optional[Dict]] = mapped_column(JSONB)
    
    # Scopes and settings
    scopes: Mapped[list] = mapped_column(JSONB, default=list)
    extra_authorize_params: Mapped[Optional[Dict]] = mapped_column(JSONB)
    
    # Features
    allow_signup: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_link_accounts: Mapped[bool] = mapped_column(Boolean, default=False)
    require_verified_email: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Default role for new users
    default_role_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("roles.id"))
    
    # Metadata
    metadata: Mapped[Optional[Dict]] = mapped_column(JSONB)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship()
    default_role: Mapped[Optional["Role"]] = relationship()
    connections: Mapped[list["OAuthConnection"]] = relationship(
        back_populates="provider",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_oauth_provider_org_type", "organization_id", "provider_type", unique=True),
    )


class OAuthConnection(Base):
    """User's OAuth connection to a provider."""
    __tablename__ = "oauth_connections"
    
    # Identity
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    provider_id: Mapped[UUID] = mapped_column(
        ForeignKey("oauth_providers.id", ondelete="CASCADE"),
        index=True
    )
    
    # Provider user identity
    provider_user_id: Mapped[str] = mapped_column(String(255), index=True)
    provider_username: Mapped[Optional[str]] = mapped_column(String(255))
    provider_email: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Tokens (encrypted at rest)
    access_token_encrypted: Mapped[str] = mapped_column(Text)
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    token_type: Mapped[str] = mapped_column(String(50), default="Bearer")
    
    # Token expiration
    expires_at: Mapped[Optional[datetime]]
    
    # Scopes granted
    scopes: Mapped[list] = mapped_column(JSONB, default=list)
    
    # Provider user data
    provider_data: Mapped[Optional[Dict]] = mapped_column(JSONB)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    last_used_at: Mapped[Optional[datetime]]
    
    # Relationships
    user: Mapped["User"] = relationship()
    provider: Mapped["OAuthProvider"] = relationship(back_populates="connections")
    
    __table_args__ = (
        Index("idx_oauth_conn_user_provider", "user_id", "provider_id", unique=True),
        Index("idx_oauth_conn_provider_user", "provider_id", "provider_user_id"),
    )


class OAuthState(Base):
    """Temporary OAuth state for CSRF protection."""
    __tablename__ = "oauth_states"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    
    # State parameter
    state: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    
    # PKCE
    code_verifier: Mapped[Optional[str]] = mapped_column(String(255))
    code_challenge: Mapped[Optional[str]] = mapped_column(String(255))
    code_challenge_method: Mapped[Optional[str]] = mapped_column(String(10))
    
    # Context
    provider_id: Mapped[UUID] = mapped_column(ForeignKey("oauth_providers.id"))
    redirect_uri: Mapped[str] = mapped_column(String(500))
    
    # Additional context
    return_to: Mapped[Optional[str]] = mapped_column(String(500))
    metadata: Mapped[Optional[Dict]] = mapped_column(JSONB)
    
    # Expiration
    expires_at: Mapped[datetime]
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class OAuthAuthorizationCode(Base):
    """Store authorization codes temporarily (for device flow, etc)."""
    __tablename__ = "oauth_authorization_codes"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    
    # Code
    code: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    
    # Context
    provider_id: Mapped[UUID] = mapped_column(ForeignKey("oauth_providers.id"))
    user_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"))
    
    # Details
    scopes: Mapped[list] = mapped_column(JSONB, default=list)
    redirect_uri: Mapped[str] = mapped_column(String(500))
    
    # PKCE
    code_challenge: Mapped[Optional[str]] = mapped_column(String(255))
    code_challenge_method: Mapped[Optional[str]] = mapped_column(String(10))
    
    # Expiration
    expires_at: Mapped[datetime]
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

```python:src/services/oauth/oauth_service.py
"""
OAuth Service - Handle OAuth flows and token management
"""

from typing import Optional, Dict, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timedelta
import secrets
import hashlib
import base64
import httpx
from urllib.parse import urlencode

from models import OAuthProvider, OAuthConnection, OAuthState, User
from services.oauth.providers import OAuthProviderRegistry, OAuthProviderType
from services.encryption import EncryptionService


class OAuthService:
    """Service for OAuth authentication flows."""
    
    def __init__(self, db: AsyncSession, encryption_service: EncryptionService):
        self.db = db
        self.encryption = encryption_service
    
    async def get_authorization_url(
        self,
        provider_id: UUID,
        redirect_uri: str,
        scopes: Optional[list] = None,
        return_to: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Generate OAuth authorization URL.
        
        Returns:
            Tuple of (authorization_url, state)
        """
        # Get provider config
        result = await self.db.execute(
            select(OAuthProvider).where(OAuthProvider.id == provider_id)
        )
        provider = result.scalar_one()
        
        if not provider.is_enabled:
            raise ValueError("OAuth provider is disabled")
        
        # Get provider template
        template = OAuthProviderRegistry.get(OAuthProviderType(provider.provider_type))
        if not template:
            raise ValueError(f"Unknown provider type: {provider.provider_type}")
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Generate PKCE challenge if required
        code_verifier = None
        code_challenge = None
        code_challenge_method = None
        
        if template.pkce_required:
            code_verifier = secrets.token_urlsafe(64)
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode().rstrip('=')
            code_challenge_method = "S256"
        
        # Store state
        oauth_state = OAuthState(
            state=state,
            provider_id=provider_id,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            return_to=return_to,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        self.db.add(oauth_state)
        await self.db.commit()
        
        # Build authorization URL
        authorize_url = template.endpoints.authorize_url
        
        # Replace custom domain placeholders
        if provider.custom_domain:
            authorize_url = authorize_url.replace("{domain}", provider.custom_domain)
        
        # Use custom endpoints if provided
        if provider.custom_endpoints and "authorize_url" in provider.custom_endpoints:
            authorize_url = provider.custom_endpoints["authorize_url"]
        
        # Build params
        params = {
            "client_id": provider.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": " ".join(scopes or provider.scopes or template.default_scopes)
        }
        
        # Add PKCE
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = code_challenge_method
        
        # Add extra params
        if template.extra_authorize_params:
            params.update(template.extra_authorize_params)
        
        if provider.extra_authorize_params:
            params.update(provider.extra_authorize_params)
        
        full_url = f"{authorize_url}?{urlencode(params)}"
        
        return full_url, state
    
    async def handle_callback(
        self,
        code: str,
        state: str,
        redirect_uri: str
    ) -> Tuple[User, OAuthConnection]:
        """
        Handle OAuth callback and exchange code for tokens.
        
        Returns:
            Tuple of (User, OAuthConnection)
        """
        # Verify state
        result = await self.db.execute(
            select(OAuthState).where(
                OAuthState.state == state,
                OAuthState.used == False,
                OAuthState.expires_at > datetime.utcnow()
            )
        )
        oauth_state = result.scalar_one_or_none()
        
        if not oauth_state:
            raise ValueError("Invalid or expired state")
        
        # Mark state as used
        oauth_state.used = True
        
        # Get provider
        result = await self.db.execute(
            select(OAuthProvider).where(
                OAuthProvider.id == oauth_state.provider_id
            )
        )
        provider = result.scalar_one()
        
        # Get provider template
        template = OAuthProviderRegistry.get(OAuthProviderType(provider.provider_type))
        
        # Exchange code for tokens
        token_url = template.endpoints.token_url
        if provider.custom_domain:
            token_url = token_url.replace("{domain}", provider.custom_domain)
        if provider.custom_endpoints and "token_url" in provider.custom_endpoints:
            token_url = provider.custom_endpoints["token_url"]
        
        # Decrypt client secret
        client_secret = self.encryption.decrypt(provider.client_secret_encrypted)
        
        # Build token request
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": provider.client_id,
            "client_secret": client_secret
        }
        
        # Add PKCE verifier
        if oauth_state.code_verifier:
            token_data["code_verifier"] = oauth_state.code_verifier
        
        # Exchange code for token
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=token_data)
            response.raise_for_status()
            token_response = response.json()
        
        access_token = token_response["access_token"]
        refresh_token = token_response.get("refresh_token")
        expires_in = token_response.get("expires_in")
        
        # Calculate expiration
        expires_at = None
        if expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Fetch user info
        userinfo_url = template.endpoints.userinfo_url
        if provider.custom_domain:
            userinfo_url = userinfo_url.replace("{domain}", provider.custom_domain)
        if provider.custom_endpoints and "userinfo_url" in provider.custom_endpoints:
            userinfo_url = provider.custom_endpoints["userinfo_url"]
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            userinfo = response.json()
        
        # Map userinfo to our user model
        mapping = template.userinfo_mapping or {}
        provider_user_id = self._get_nested_value(userinfo, mapping.get("provider_user_id", "id"))
        email = self._get_nested_value(userinfo, mapping.get("email", "email"))
        full_name = self._get_nested_value(userinfo, mapping.get("full_name", "name"))
        username = self._get_nested_value(userinfo, mapping.get("username", "username"))
        
        # Find or create user
        user = await self._find_or_create_user(
            provider=provider,
            email=email,
            full_name=full_name,
            provider_user_id=provider_user_id
        )
        
        # Create or update OAuth connection
        result = await self.db.execute(
            select(OAuthConnection).where(
                OAuthConnection.user_id == user.id,
                OAuthConnection.provider_id == provider.id
            )
        )
        connection = result.scalar_one_or_none()
        
        if connection:
            # Update existing connection
            connection.access_token_encrypted = self.encryption.encrypt(access_token)
            if refresh_token:
                connection.refresh_token_encrypted = self.encryption.encrypt(refresh_token)
            connection.expires_at = expires_at
            connection.provider_data = userinfo
            connection.last_used_at = datetime.utcnow()
            connection.is_active = True
        else:
            # Create new connection
            connection = OAuthConnection(
                user_id=user.id,
                provider_id=provider.id,
                provider_user_id=provider_user_id,
                provider_username=username,
                provider_email=email,
                access_token_encrypted=self.encryption.encrypt(access_token),
                refresh_token_encrypted=self.encryption.encrypt(refresh_token) if refresh_token else None,
                expires_at=expires_at,
                scopes=provider.scopes,
                provider_data=userinfo,
                is_active=True,
                is_primary=True
            )
            self.db.add(connection)
        
        await self.db.commit()
        await self.db.refresh(user)
        await self.db.refresh(connection)
        
        return user, connection
    
    async def refresh_access_token(
        self,
        connection_id: UUID
    ) -> str:
        """
        Refresh an expired access token.
        
        Returns:
            New access token
        """
        # Get connection
        result = await self.db.execute(
            select(OAuthConnection)
            .where(OAuthConnection.id == connection_id)
            .options(selectinload(OAuthConnection.provider))
        )
        connection = result.scalar_one()
        
        if not connection.refresh_token_encrypted:
            raise ValueError("No refresh token available")
        
        provider = connection.provider
        template = OAuthProviderRegistry.get(OAuthProviderType(provider.provider_type))
        
        # Decrypt tokens
        refresh_token = self.encryption.decrypt(connection.refresh_token_encrypted)
        client_secret = self.encryption.decrypt(provider.client_secret_encrypted)
        
        # Build token refresh request
        token_url = template.endpoints.token_url
        if provider.custom_domain:
            token_url = token_url.replace("{domain}", provider.custom_domain)
        if provider.custom_endpoints and "token_url" in provider.custom_endpoints:
            token_url = provider.custom_endpoints["token_url"]
        
        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": provider.client_id,
            "client_secret": client_secret
        }
        
        # Request new tokens
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=token_data)
            response.raise_for_status()
            token_response = response.json()
        
        new_access_token = token_response["access_token"]
        new_refresh_token = token_response.get("refresh_token", refresh_token)
        expires_in = token_response.get("expires_in")
        
        # Update connection
        connection.access_token_encrypted = self.encryption.encrypt(new_access_token)
        connection.refresh_token_encrypted = self.encryption.encrypt(new_refresh_token)
        
        if expires_in:
            connection.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        connection.last_used_at = datetime.utcnow()
        
        await self.db.commit()
        
        return new_access_token
    
    async def get_valid_access_token(
        self,
        connection_id: UUID
    ) -> str:
        """
        Get a valid access token, refreshing if necessary.
        """
        result = await self.db.execute(
            select(OAuthConnection).where(OAuthConnection.id == connection_id)
        )
        connection = result.scalar_one()
        
        # Check if token is expired
        if connection.expires_at and connection.expires_at < datetime.utcnow():
            # Refresh token
            return await self.refresh_access_token(connection_id)
        
        # Decrypt and return current token
        return self.encryption.decrypt(connection.access_token_encrypted)
    
    async def revoke_connection(
        self,
        connection_id: UUID
    ):
        """Revoke OAuth connection and tokens."""
        result = await self.db.execute(
            select(OAuthConnection)
            .where(OAuthConnection.id == connection_id)
            .options(selectinload(OAuthConnection.provider))
        )
        connection = result.scalar_one()
        
        provider = connection.provider
        template = OAuthProviderRegistry.get(OAuthProviderType(provider.provider_type))
        
        # Revoke token if endpoint exists
        if template.endpoints.revoke_url:
            access_token = self.encryption.decrypt(connection.access_token_encrypted)
            client_secret = self.encryption.decrypt(provider.client_secret_encrypted)
            
            revoke_url = template.endpoints.revoke_url
            if provider.custom_domain:
                revoke_url = revoke_url.replace("{domain}", provider.custom_domain)
            
            # Replace {client_id} placeholder (for GitHub)
            revoke_url = revoke_url.replace("{client_id}", provider.client_id)
            
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        revoke_url,
                        data={
                            "token": access_token,
                            "client_id": provider.client_id,
                            "client_secret": client_secret
                        }
                    )
            except Exception as e:
                # Log error but continue with deletion
                print(f"Failed to revoke token: {e}")
        
        # Delete connection
        await self.db.delete(connection)
        await self.db.commit()
    
    async def _find_or_create_user(
        self,
        provider: OAuthProvider,
        email: str,
        full_name: Optional[str],
        provider_user_id: str
    ) -> User:
        """Find existing user or create new one."""
        # Try to find by email
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if user:
            return user
        
        # Check if signup is allowed
        if not provider.allow_signup:
            raise ValueError("Sign up not allowed for this provider")
        
        # Create new user
        user = User(
            email=email,
            full_name=full_name,
            is_verified=not provider.require_verified_email,
            hashed_password=secrets.token_urlsafe(32)  # Random password
        )
        self.db.add(user)
        await self.db.flush()
        
        # Add to organization with default role
        if provider.default_role_id:
            from models import OrganizationMembership
            membership = OrganizationMembership(
                user_id=user.id,
                organization_id=provider.organization_id,
                role_id=provider.default_role_id
            )
            self.db.add(membership)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    def _get_nested_value(self, data: Dict, path: str) -> Optional[str]:
        """Get nested value from dict using dot notation."""
        keys = path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        
        return str(value) if value is not None else None
```

```python:src/api/oauth_endpoints.py
"""
OAuth API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, HttpUrl

from database import get_db
from models import OAuthProvider, OAuthConnection
from services.oauth.oauth_service import OAuthService
from services.oauth.providers import OAuthProviderRegistry, OAuthProviderType
from services.encryption import EncryptionService
from api.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/oauth", tags=["oauth"])


class ProviderInfo(BaseModel):
    """OAuth provider information."""
    provider_type: str
    display_name: str
    icon: str
    default_scopes: List[str]
    supports_refresh: bool


class ConfigureProviderRequest(BaseModel):
    """Request to configure OAuth provider."""
    provider_type: str
    client_id: str
    client_secret: str
    custom_domain: Optional[str] = None
    scopes: Optional[List[str]] = None
    allow_signup: bool = True
    default_role_id: Optional[UUID] = None


class OAuthConnectionResponse(BaseModel):
    """OAuth connection response."""
    id: UUID
    provider_type: str
    provider_display_name: str
    provider_username: Optional[str]
    provider_email: Optional[str]
    is_active: bool
    is_primary: bool
    created_at: str
    last_used_at: Optional[str]


@router.get("/providers/available", response_model=List[ProviderInfo])
async def list_available_providers():
    """
    List all available OAuth providers.
    
    This returns the list of providers supported by the system,
    not the providers configured for your organization.
    """
    providers = OAuthProviderRegistry.list_providers()
    
    return [
        ProviderInfo(
            provider_type=p.provider_type.value,
            display_name=p.display_name,
            icon=p.icon,
            default_scopes=p.default_scopes,
            supports_refresh=p.supports_refresh
        )
        for p in providers
    ]


@router.post("/providers/configure")
async def configure_provider(
    request: ConfigureProviderRequest,
    organization_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    encryption_service: EncryptionService = Depends()
):
    """
    Configure an OAuth provider for your organization.
    
    Requires admin permissions.
    """
    # TODO: Check admin permissions
    
    # Verify provider type exists
    try:
        provider_type = OAuthProviderType(request.provider_type)
    except ValueError:
        raise HTTPException(400, f"Unknown provider type: {request.provider_type}")
    
    template = OAuthProviderRegistry.get(provider_type)
    if not template:
        raise HTTPException(400, "Provider not supported")
    
    # Check if provider already configured
    result = await db.execute(
        select(OAuthProvider).where(
            OAuthProvider.organization_id == organization_id,
            OAuthProvider.provider_type == request.provider_type
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(400, "Provider already configured")
    
    # Encrypt client secret
    encrypted_secret = encryption_service.encrypt(request.client_secret)
    
    # Create provider
    provider = OAuthProvider(
        organization_id=organization_id,
        provider_type=request.provider_type,
        display_name=template.display_name,
        client_id=request.client_id,
        client_secret_encrypted=encrypted_secret,
        custom_domain=request.custom_domain,
        scopes=request.scopes or template.default_scopes,
        allow_signup=request.allow_signup,
        default_role_id=request.default_role_id,
        is_enabled=True
    )
    
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    
    return {
        "id": str(provider.id),
        "provider_type": provider.provider_type,
        "display_name": provider.display_name,
        "is_enabled": provider.is_enabled
    }


@router.get("/authorize")
async def oauth_authorize(
    provider_id: UUID,
    return_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    encryption_service: EncryptionService = Depends()
):
    """
    Initiate OAuth authorization flow.
    
    Redirects to OAuth provider's authorization page.
    """
    oauth_service = OAuthService(db, encryption_service)
    
    # Build redirect URI
    redirect_uri = f"{request.url.scheme}://{request.url.netloc}/api/v1/oauth/callback"
    
    # Get authorization URL
    auth_url, state = await oauth_service.get_authorization_url(
        provider_id=provider_id,
        redirect_uri=redirect_uri,
        return_to=return_to
    )
    
    return RedirectResponse(auth_url)


@router.get("/callback")
async def oauth_callback(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    encryption_service: EncryptionService = Depends()
):
    """
    Handle OAuth callback from provider.
    
    Exchanges authorization code for access token and creates/updates user.
    """
    oauth_service = OAuthService(db, encryption_service)
    
    # Build redirect URI (must match authorization request)
    redirect_uri = f"{request.url.scheme}://{request.url.netloc}/api/v1/oauth/callback"
    
    try:
        # Handle callback
        user, connection = await oauth_service.handle_callback(
            code=code,
            state=state,
            redirect_uri=redirect_uri
        )
        
        # Create session for user
        # TODO: Create session token
        
        # Redirect to app
        # Get return_to from state if available
        return RedirectResponse("/dashboard")
        
    except Exception as e:
        # Redirect to error page
        return RedirectResponse(f"/auth/error?message={str(e)}")


@router.get("/connections", response_model=List[OAuthConnectionResponse])
async def list_connections(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's OAuth connections."""
    result = await db.execute(
        select(OAuthConnection)
        .where(OAuthConnection.user_id == current_user.id)
        .options(selectinload(OAuthConnection.provider))
    )
    connections = result.scalars().all()
    
    return [
        OAuthConnectionResponse(
            id=conn.id,
            provider_type=conn.provider.provider_type,
            provider_display_name=conn.provider.display_name,
            provider_username=conn.provider_username,
            provider_email=conn.provider_email,
            is_active=conn.is_active,
            is_primary=conn.is_primary,
            created_at=conn.created_at.isoformat(),
            last_used_at=conn.last_used_at.isoformat() if conn.last_used_at else None
        )
        for conn in connections
    ]


@router.delete("/connections/{connection_id}")
async def revoke_connection(
    connection_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    encryption_service: EncryptionService = Depends()
):
    """Revoke an OAuth connection."""
    oauth_service = OAuthService(db, encryption_service)
    
    # Verify connection belongs to user
    result = await db.execute(
        select(OAuthConnection).where(
            OAuthConnection.id == connection_id,
            OAuthConnection.user_id == current_user.id
        )
    )
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise HTTPException(404, "Connection not found")
    
    await oauth_service.revoke_connection(connection_id)
    
    return {"status": "revoked"}


@router.post("/connections/{connection_id}/refresh")
async def refresh_connection(
    connection_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    encryption_service: EncryptionService = Depends()
):
    """Refresh access token for a connection."""
    oauth_service = OAuthService(db, encryption_service)
    
    # Verify connection belongs to user
    result = await db.execute(
        select(OAuthConnection).where(
            OAuthConnection.id == connection_id,
            OAuthConnection.user_id == current_user.id
        )
    )
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise HTTPException(404, "Connection not found")
    
    new_token = await oauth_service.refresh_access_token(connection_id)
    
    return {
        "status": "refreshed",
        "expires_at": connection.expires_at.isoformat() if connection.expires_at else None
    }
```

Now for adding even MORE providers easily:

```python:src/scripts/add_oauth_provider.py
"""
Script to easily add new OAuth providers
"""

from services.oauth.providers import OAuthProviderRegistry, OAuthProviderConfig, OAuthEndpoints, OAuthProviderType


def add_custom_provider():
    """
    Interactive script to add a new OAuth provider.
    
    Usage:
        python -m src.scripts.add_oauth_provider
    """
    print("=== Add New OAuth Provider ===\n")
    
    name = input("Provider name (e.g., 'mycompany'): ").lower()
    display_name = input("Display name (e.g., 'MyCompany'): ")
    icon_url = input("Icon URL: ")
    
    print("\nEndpoints:")
    authorize_url = input("Authorization URL: ")
    token_url = input("Token URL: ")
    userinfo_url = input("User Info URL: ")
    revoke_url = input("Revoke URL (optional, press Enter to skip): ") or None
    
    print("\nScopes (comma-separated, e.g., 'read,write'):")
    scopes_input = input("Default scopes: ")
    scopes = [s.strip() for s in scopes_input.split(",")]
    
    pkce = input("\nRequires PKCE? (y/n): ").lower() == 'y'
    
    print("\nUser Info Mapping:")
    print("Map provider's user fields to our User model fields")
    email_field = input("Email field (default: 'email'): ") or "email"
    name_field = input("Name field (default: 'name'): ") or "name"
    id_field = input("User ID field (default: 'id'): ") or "id"
    username_field = input("Username field (optional): ") or None
    
    # Generate code
    provider_code = f"""
# {display_name}
OAuthProviderRegistry.register(OAuthProviderConfig(
    provider_type=OAuthProviderType.CUSTOM,  # Change to specific enum if adding permanently
    display_name="{display_name}",
    icon="{icon_url}",
    endpoints=OAuthEndpoints(
        authorize_url="{authorize_url}",
        token_url="{token_url}",
        userinfo_url="{userinfo_url}",
        revoke_url={f'"{revoke_url}"' if revoke_url else "None"}
    ),
    default_scopes={scopes},
    pkce_required={pkce},
    userinfo_mapping={{
        "{email_field}": "email",
        "{name_field}": "full_name",
        "{id_field}": "provider_user_id",
        {f'"{username_field}": "username",' if username_field else ""}
    }}
))
"""
    
    print("\n=== Generated Code ===")
    print(provider_code)
    print("\nAdd this code to src/services/oauth/providers.py")
    
    # Optionally write to file
    save = input("\nSave to file? (y/n): ").lower() == 'y'
    if save:
        filename = f"provider_{name}.py"
        with open(filename, 'w') as f:
            f.write(provider_code)
        print(f"Saved to {filename}")


if __name__ == "__main__":
    add_custom_provider()
```

And a React component for the OAuth connection UI:

```typescript:frontend/src/components/OAuthProviders.tsx
/**
 * OAuth Provider Management UI
 */

import React, { useEffect, useState } from 'react';

interface Provider {
  provider_type: string;
  display_name: string;
  icon: string;
  default_scopes: string[];
  supports_refresh: boolean;
}

interface Connection {
  id: string;
  provider_type: string;
  provider_display_name: string;
  provider_username?: string;
  provider_email?: string;
  is_active: boolean;
  is_primary: boolean;
  created_at: string;
  last_used_at?: string;
}

export const OAuthProviders: React.FC = () => {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProviders();
    fetchConnections();
  }, []);

  const fetchProviders = async () => {
    const response = await fetch('/api/v1/oauth/providers/available');
    const data = await response.json();
    setProviders(data);
  };

  const fetchConnections = async () => {
    const response = await fetch('/api/v1/oauth/connections');
    const data = await response.json();
    setConnections(data);
    setLoading(false);
  };

  const handleConnect = (providerType: string) => {
    // This would open OAuth flow
    window.location.href = `/api/v1/oauth/authorize?provider_type=${providerType}`;
  };

  const handleDisconnect = async (connectionId: string) => {
    if (!confirm('Disconnect this account?')) return;

    await fetch(`/api/v1/oauth/connections/${connectionId}`, {
      method: 'DELETE'
    });

    fetchConnections();
  };

  const getConnectionForProvider = (providerType: string) => {
    return connections.find(c => c.provider_type === providerType);
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="oauth-providers">
      <h2>Connected Accounts</h2>
      
      <div className="provider-grid">
        {providers.map(provider => {
          const connection = getConnectionForProvider(provider.provider_type);
          
          return (
            <div key={provider.provider_type} className="provider-card">
              <div className="provider-header">
                <img src={provider.icon} alt={provider.display_name} className="provider-icon" />
                <h3>{provider.display_name}</h3>
              </div>
              
              {connection ? (
                <div className="connection-info">
                  <div className="connection-status connected">
                    ✓ Connected
                  </div>
                  {connection.provider_email && (
                    <div className="connection-email">{connection.provider_email}</div>
                  )}
                  <div className="connection-actions">
                    <button
                      onClick={() => handleDisconnect(connection.id)}
                      className="btn btn-danger-outline"
                    >
                      Disconnect
                    </button>
                  </div>
                </div>
              ) : (
                <div className="connection-info">
                  <button
                    onClick={() => handleConnect(provider.provider_type)}
                    className="btn btn-primary"
                  >
                    Connect {provider.display_name}
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <style jsx>{`
        .oauth-providers {
          padding: 24px;
        }

        h2 {
          margin: 0 0 24px 0;
          font-size: 24px;
          color: #1e1e1e;
        }

        .provider-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 16px;
        }

        .provider-card {
          background: white;
          border-radius: 8px;
          padding: 20px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .provider-header {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 16px;
        }

        .provider-icon {
          width: 32px;
          height: 32px;
          border-radius: 4px;
        }

        .provider-header h3 {
          margin: 0;
          font-size: 18px;
          color: #1e1e1e;
        }

        .connection-status {
          padding: 6px 12px;
          border-radius: 4px;
          font-size: 14px;
          font-weight: 500;
          margin-bottom: 8px;
          display: inline-block;
        }

        .connection-status.connected {
          background: #e6f7f0;
          color: #0dbc79;
        }

        .connection-email {
          font-size: 14px;
          color: #666;
          margin-bottom: 12px;
        }

        .btn {
          padding: 8px 16px;
          border: none;
          border-radius: 4px;
          font-size: 14px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .btn-primary {
          background: #2472c8;
          color: white;
        }

        .btn-primary:hover {
          background: #1a5caa;
        }

        .btn-danger-outline {
          background: transparent;
          color: #cd3131;
          border: 1px solid #cd3131;
        }

        .btn-danger-outline:hover {
          background: #cd3131;
          color: white;
        }
      `}</style>
    </div>
  );
};
```

This comprehensive OAuth system gives you:

1. **20+ pre-configured providers** (Google, GitHub, Microsoft, GitLab, Slack, Discord, LinkedIn, Notion, Linear, Figma, etc.)
2. **Easy addition of new providers** via script or manual registration
3. **PKCE support** for enhanced security
4. **Token refresh** automation
5. **Multi-account support** per user
6. **Organization-level configuration**
7. **Flexible scope management**
8. **Automatic user creation** with role assignment

The system is modular - you can add any OAuth 2.0 provider in minutes by just adding configuration!



## Response:
11/19/2025, 10:44:04 AM

I'll create a comprehensive GitHub App integration system that allows you to interact with users' GitHub repositories, create PRs, manage issues, and more.

```python:src/services/github/github_app.py
"""
GitHub App Integration
Provides comprehensive GitHub API access for repository management
"""

from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import jwt
import httpx
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from models import Project, GitHubInstallation, User
from services.encryption import EncryptionService


class GitHubAppConfig(BaseModel):
    """GitHub App configuration."""
    app_id: str
    client_id: str
    client_secret: str
    private_key: str  # PEM format
    webhook_secret: str


class GitHubRepository(BaseModel):
    """GitHub repository information."""
    id: int
    name: str
    full_name: str
    owner: str
    private: bool
    default_branch: str
    html_url: str
    clone_url: str
    permissions: Dict[str, bool]


class GitHubPullRequest(BaseModel):
    """GitHub pull request information."""
    number: int
    title: str
    body: str
    state: str
    html_url: str
    head_ref: str
    base_ref: str
    created_at: str
    updated_at: str


class GitHubIssue(BaseModel):
    """GitHub issue information."""
    number: int
    title: str
    body: str
    state: str
    html_url: str
    labels: List[str]
    created_at: str
    updated_at: str


class GitHubAppService:
    """Service for GitHub App API interactions."""
    
    def __init__(
        self,
        config: GitHubAppConfig,
        encryption_service: EncryptionService
    ):
        self.config = config
        self.encryption = encryption_service
        self.base_url = "https://api.github.com"
    
    def _generate_jwt(self) -> str:
        """Generate JWT for GitHub App authentication."""
        now = datetime.utcnow()
        payload = {
            'iat': now,
            'exp': now + timedelta(minutes=10),
            'iss': self.config.app_id
        }
        
        return jwt.encode(
            payload,
            self.config.private_key,
            algorithm='RS256'
        )
    
    async def _get_installation_token(
        self,
        installation_id: int
    ) -> str:
        """
        Get installation access token.
        
        This token is used to make API calls on behalf of the installation.
        """
        jwt_token = self._generate_jwt()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/app/installations/{installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            return data["token"]
    
    async def list_installations(self) -> List[Dict]:
        """List all installations of the GitHub App."""
        jwt_token = self._generate_jwt()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/app/installations",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def list_installation_repositories(
        self,
        installation_id: int
    ) -> List[GitHubRepository]:
        """List repositories accessible by installation."""
        token = await self._get_installation_token(installation_id)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/installation/repositories",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                GitHubRepository(
                    id=repo["id"],
                    name=repo["name"],
                    full_name=repo["full_name"],
                    owner=repo["owner"]["login"],
                    private=repo["private"],
                    default_branch=repo["default_branch"],
                    html_url=repo["html_url"],
                    clone_url=repo["clone_url"],
                    permissions=repo.get("permissions", {})
                )
                for repo in data["repositories"]
            ]
    
    async def get_repository(
        self,
        installation_id: int,
        owner: str,
        repo: str
    ) -> GitHubRepository:
        """Get repository details."""
        token = await self._get_installation_token(installation_id)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            response.raise_for_status()
            repo_data = response.json()
            
            return GitHubRepository(
                id=repo_data["id"],
                name=repo_data["name"],
                full_name=repo_data["full_name"],
                owner=repo_data["owner"]["login"],
                private=repo_data["private"],
                default_branch=repo_data["default_branch"],
                html_url=repo_data["html_url"],
                clone_url=repo_data["clone_url"],
                permissions=repo_data.get("permissions", {})
            )
    
    async def create_branch(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        branch_name: str,
        from_branch: str = "main"
    ) -> str:
        """
        Create a new branch.
        
        Returns the SHA of the new branch.
        """
        token = await self._get_installation_token(installation_id)
        
        async with httpx.AsyncClient() as client:
            # Get SHA of base branch
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/git/ref/heads/{from_branch}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            response.raise_for_status()
            base_sha = response.json()["object"]["sha"]
            
            # Create new branch
            response = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/git/refs",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json={
                    "ref": f"refs/heads/{branch_name}",
                    "sha": base_sha
                }
            )
            response.raise_for_status()
            
            return base_sha
    
    async def get_file_content(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        path: str,
        ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get file content from repository.
        
        Returns dict with content, sha, encoding, etc.
        """
        token = await self._get_installation_token(installation_id)
        
        params = {}
        if ref:
            params["ref"] = ref
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/contents/{path}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def create_or_update_file(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create or update a file in repository.
        
        Args:
            sha: Required for updates, omit for new files
        
        Returns commit information.
        """
        token = await self._get_installation_token(installation_id)
        
        # Encode content to base64
        import base64
        content_bytes = content.encode('utf-8')
        content_base64 = base64.b64encode(content_bytes).decode('utf-8')
        
        payload = {
            "message": message,
            "content": content_base64,
            "branch": branch
        }
        
        if sha:
            payload["sha"] = sha
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/repos/{owner}/{repo}/contents/{path}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    async def delete_file(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        path: str,
        message: str,
        sha: str,
        branch: str
    ) -> Dict[str, Any]:
        """Delete a file from repository."""
        token = await self._get_installation_token(installation_id)
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/repos/{owner}/{repo}/contents/{path}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json={
                    "message": message,
                    "sha": sha,
                    "branch": branch
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def create_pull_request(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: Optional[str] = None,
        draft: bool = False
    ) -> GitHubPullRequest:
        """Create a pull request."""
        token = await self._get_installation_token(installation_id)
        
        payload = {
            "title": title,
            "head": head,
            "base": base,
            "draft": draft
        }
        
        if body:
            payload["body"] = body
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/pulls",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json=payload
            )
            response.raise_for_status()
            pr_data = response.json()
            
            return GitHubPullRequest(
                number=pr_data["number"],
                title=pr_data["title"],
                body=pr_data["body"] or "",
                state=pr_data["state"],
                html_url=pr_data["html_url"],
                head_ref=pr_data["head"]["ref"],
                base_ref=pr_data["base"]["ref"],
                created_at=pr_data["created_at"],
                updated_at=pr_data["updated_at"]
            )
    
    async def update_pull_request(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        pr_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None
    ) -> GitHubPullRequest:
        """Update a pull request."""
        token = await self._get_installation_token(installation_id)
        
        payload = {}
        if title:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if state:
            payload["state"] = state
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json=payload
            )
            response.raise_for_status()
            pr_data = response.json()
            
            return GitHubPullRequest(
                number=pr_data["number"],
                title=pr_data["title"],
                body=pr_data["body"] or "",
                state=pr_data["state"],
                html_url=pr_data["html_url"],
                head_ref=pr_data["head"]["ref"],
                base_ref=pr_data["base"]["ref"],
                created_at=pr_data["created_at"],
                updated_at=pr_data["updated_at"]
            )
    
    async def merge_pull_request(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        pr_number: int,
        commit_title: Optional[str] = None,
        commit_message: Optional[str] = None,
        merge_method: str = "merge"  # merge, squash, or rebase
    ) -> Dict[str, Any]:
        """Merge a pull request."""
        token = await self._get_installation_token(installation_id)
        
        payload = {
            "merge_method": merge_method
        }
        
        if commit_title:
            payload["commit_title"] = commit_title
        if commit_message:
            payload["commit_message"] = commit_message
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/merge",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    async def list_pull_requests(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        state: str = "open",
        base: Optional[str] = None
    ) -> List[GitHubPullRequest]:
        """List pull requests."""
        token = await self._get_installation_token(installation_id)
        
        params = {"state": state}
        if base:
            params["base"] = base
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                params=params
            )
            response.raise_for_status()
            prs = response.json()
            
            return [
                GitHubPullRequest(
                    number=pr["number"],
                    title=pr["title"],
                    body=pr["body"] or "",
                    state=pr["state"],
                    html_url=pr["html_url"],
                    head_ref=pr["head"]["ref"],
                    base_ref=pr["base"]["ref"],
                    created_at=pr["created_at"],
                    updated_at=pr["updated_at"]
                )
                for pr in prs
            ]
    
    async def create_issue(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None
    ) -> GitHubIssue:
        """Create an issue."""
        token = await self._get_installation_token(installation_id)
        
        payload = {"title": title}
        
        if body:
            payload["body"] = body
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/issues",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json=payload
            )
            response.raise_for_status()
            issue_data = response.json()
            
            return GitHubIssue(
                number=issue_data["number"],
                title=issue_data["title"],
                body=issue_data["body"] or "",
                state=issue_data["state"],
                html_url=issue_data["html_url"],
                labels=[label["name"] for label in issue_data["labels"]],
                created_at=issue_data["created_at"],
                updated_at=issue_data["updated_at"]
            )
    
    async def update_issue(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> GitHubIssue:
        """Update an issue."""
        token = await self._get_installation_token(installation_id)
        
        payload = {}
        if title:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if state:
            payload["state"] = state
        if labels is not None:
            payload["labels"] = labels
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json=payload
            )
            response.raise_for_status()
            issue_data = response.json()
            
            return GitHubIssue(
                number=issue_data["number"],
                title=issue_data["title"],
                body=issue_data["body"] or "",
                state=issue_data["state"],
                html_url=issue_data["html_url"],
                labels=[label["name"] for label in issue_data["labels"]],
                created_at=issue_data["created_at"],
                updated_at=issue_data["updated_at"]
            )
    
    async def add_issue_comment(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        issue_number: int,
        body: str
    ) -> Dict[str, Any]:
        """Add a comment to an issue or PR."""
        token = await self._get_installation_token(installation_id)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json={"body": body}
            )
            response.raise_for_status()
            return response.json()
    
    async def create_commit(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        branch: str,
        message: str,
        files: List[Dict[str, str]],  # [{"path": "...", "content": "..."}]
        author: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Create a commit with multiple file changes.
        
        Returns commit SHA.
        """
        token = await self._get_installation_token(installation_id)
        
        async with httpx.AsyncClient() as client:
            # Get current commit SHA
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/git/ref/heads/{branch}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            response.raise_for_status()
            current_commit_sha = response.json()["object"]["sha"]
            
            # Get current commit tree
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/git/commits/{current_commit_sha}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            response.raise_for_status()
            current_tree_sha = response.json()["tree"]["sha"]
            
            # Create blobs for each file
            import base64
            tree_items = []
            
            for file in files:
                content_bytes = file["content"].encode('utf-8')
                content_base64 = base64.b64encode(content_bytes).decode('utf-8')
                
                response = await client.post(
                    f"{self.base_url}/repos/{owner}/{repo}/git/blobs",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    json={
                        "content": content_base64,
                        "encoding": "base64"
                    }
                )
                response.raise_for_status()
                blob_sha = response.json()["sha"]
                
                tree_items.append({
                    "path": file["path"],
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_sha
                })
            
            # Create tree
            response = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/git/trees",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json={
                    "base_tree": current_tree_sha,
                    "tree": tree_items
                }
            )
            response.raise_for_status()
            new_tree_sha = response.json()["sha"]
            
            # Create commit
            commit_payload = {
                "message": message,
                "tree": new_tree_sha,
                "parents": [current_commit_sha]
            }
            
            if author:
                commit_payload["author"] = author
            
            response = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/git/commits",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json=commit_payload
            )
            response.raise_for_status()
            new_commit_sha = response.json()["sha"]
            
            # Update branch reference
            response = await client.patch(
                f"{self.base_url}/repos/{owner}/{repo}/git/refs/heads/{branch}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json={"sha": new_commit_sha}
            )
            response.raise_for_status()
            
            return new_commit_sha
    
    async def get_commit(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        commit_sha: str
    ) -> Dict[str, Any]:
        """Get commit details."""
        token = await self._get_installation_token(installation_id)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/commits/{commit_sha}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def list_commits(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        sha: Optional[str] = None,
        path: Optional[str] = None,
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """List commits."""
        token = await self._get_installation_token(installation_id)
        
        params = {"per_page": per_page}
        if sha:
            params["sha"] = sha
        if path:
            params["path"] = path
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/commits",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def create_webhook(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        webhook_url: str,
        events: List[str],
        active: bool = True
    ) -> Dict[str, Any]:
        """Create a webhook for repository."""
        token = await self._get_installation_token(installation_id)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/hooks",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json={
                    "name": "web",
                    "active": active,
                    "events": events,
                    "config": {
                        "url": webhook_url,
                        "content_type": "json",
                        "secret": self.config.webhook_secret
                    }
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def request_reviewers(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        pr_number: int,
        reviewers: List[str],
        team_reviewers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Request reviewers for a pull request."""
        token = await self._get_installation_token(installation_id)
        
        payload = {"reviewers": reviewers}
        if team_reviewers:
            payload["team_reviewers"] = team_reviewers
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    async def get_pr_files(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        pr_number: int
    ) -> List[Dict[str, Any]]:
        """Get files changed in a pull request."""
        token = await self._get_installation_token(installation_id)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def create_pr_review(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        pr_number: int,
        event: str,  # APPROVE, REQUEST_CHANGES, COMMENT
        body: Optional[str] = None,
        comments: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Create a review for a pull request."""
        token = await self._get_installation_token(installation_id)
        
        payload = {"event": event}
        if body:
            payload["body"] = body
        if comments:
            payload["comments"] = comments
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json=payload
            )
            response.raise_for_status()
            return response.json()
```

```python:src/models/github.py
"""
GitHub Integration Database Models
"""

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, BigInteger
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Dict, List
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.sql import func

from models.base import Base


class GitHubInstallation(Base):
    """GitHub App installation."""
    __tablename__ = "github_installations"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    
    # GitHub installation details
    github_installation_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True
    )
    github_account_id: Mapped[int] = mapped_column(BigInteger)
    github_account_login: Mapped[str] = mapped_column(String(255))
    github_account_type: Mapped[str] = mapped_column(String(50))  # User or Organization
    
    # Permissions
    permissions: Mapped[Dict] = mapped_column(JSONB, default=dict)
    events: Mapped[List[str]] = mapped_column(JSONB, default=list)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    suspended_at: Mapped[Optional[datetime]]
    suspended_by: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Metadata
    metadata: Mapped[Optional[Dict]] = mapped_column(JSONB)
    
    # Timestamps
    installed_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship()
    repositories: Mapped[List["GitHubRepository"]] = relationship(
        back_populates="installation",
        cascade="all, delete-orphan"
    )


class GitHubRepository(Base):
    """GitHub repository connected to installation."""
    __tablename__ = "github_repositories"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    installation_id: Mapped[UUID] = mapped_column(
        ForeignKey("github_installations.id", ondelete="CASCADE"),
        index=True
    )
    project_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        index=True
    )
    
    # GitHub repository details
    github_repo_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(500))
    owner: Mapped[str] = mapped_column(String(255))
    
    # Repository info
    private: Mapped[bool] = mapped_column(Boolean)
    default_branch: Mapped[str] = mapped_column(String(255))
    html_url: Mapped[str] = mapped_column(String(500))
    clone_url: Mapped[str] = mapped_column(String(500))
    
    # Permissions
    permissions: Mapped[Dict] = mapped_column(JSONB, default=dict)
    
    # Settings
    auto_sync: Mapped[bool] = mapped_column(Boolean, default=True)
    webhook_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    
    # Metadata
    metadata: Mapped[Optional[Dict]] = mapped_column(JSONB)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    last_synced_at: Mapped[Optional[datetime]]
    
    # Relationships
    installation: Mapped["GitHubInstallation"] = relationship(
        back_populates="repositories"
    )
    project: Mapped[Optional["Project"]] = relationship()
```

```python:src/api/github_endpoints.py
"""
GitHub App API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
import hmac
import hashlib

from database import get_db
from models import GitHubInstallation, GitHubRepository, Project
from services.github.github_app import GitHubAppService, GitHubAppConfig
from services.encryption import EncryptionService
from api.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/github", tags=["github"])


class CreateBranchRequest(BaseModel):
    branch_name: str
    from_branch: str = "main"


class CreatePullRequestRequest(BaseModel):
    title: str
    head: str
    base: str
    body: Optional[str] = None
    draft: bool = False


class CreateIssueRequest(BaseModel):
    title: str
    body: Optional[str] = None
    labels: Optional[List[str]] = None
    assignees: Optional[List[str]] = None


class CommitFilesRequest(BaseModel):
    branch: str
    message: str
    files: List[dict]  # [{"path": "...", "content": "..."}]


def get_github_service(
    config: GitHubAppConfig = Depends(),
    encryption: EncryptionService = Depends()
) -> GitHubAppService:
    """Dependency to get GitHub service."""
    return GitHubAppService(config, encryption)


@router.get("/installations")
async def list_installations(
    organization_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List GitHub installations for organization."""
    result = await db.execute(
        select(GitHubInstallation)
        .where(GitHubInstallation.organization_id == organization_id)
    )
    installations = result.scalars().all()
    
    return [
        {
            "id": str(inst.id),
            "github_installation_id": inst.github_installation_id,
            "github_account_login": inst.github_account_login,
            "github_account_type": inst.github_account_type,
            "is_active": inst.is_active,
            "installed_at": inst.installed_at.isoformat()
        }
        for inst in installations
    ]


@router.get("/installations/{installation_id}/repositories")
async def list_installation_repositories(
    installation_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    github_service: GitHubAppService = Depends(get_github_service)
):
    """List repositories for installation."""
    # Get installation
    result = await db.execute(
        select(GitHubInstallation).where(GitHubInstallation.id == installation_id)
    )
    installation = result.scalar_one_or_none()
    
    if not installation:
        raise HTTPException(404, "Installation not found")
    
    # Fetch from GitHub
    repos = await github_service.list_installation_repositories(
        installation.github_installation_id
    )
    
    return [
        {
            "id": repo.id,
            "name": repo.name,
            "full_name": repo.full_name,
            "owner": repo.owner,
            "private": repo.private,
            "default_branch": repo.default_branch,
            "html_url": repo.html_url,
            "permissions": repo.permissions
        }
        for repo in repos
    ]


@router.post("/repositories/{repo_id}/branches")
async def create_branch(
    repo_id: UUID,
    request: CreateBranchRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    github_service: GitHubAppService = Depends(get_github_service)
):
    """Create a new branch in repository."""
    # Get repository
    result = await db.execute(
        select(GitHubRepository)
        .where(GitHubRepository.id == repo_id)
        .options(selectinload(GitHubRepository.installation))
    )
    repo = result.scalar_one_or_none()
    
    if not repo:
        raise HTTPException(404, "Repository not found")
    
    # Create branch
    sha = await github_service.create_branch(
        installation_id=repo.installation.github_installation_id,
        owner=repo.owner,
        repo=repo.name,
        branch_name=request.branch_name,
        from_branch=request.from_branch
    )
    
    return {
        "branch_name": request.branch_name,
        "sha": sha
    }


@router.post("/repositories/{repo_id}/commits")
async def create_commit(
    repo_id: UUID,
    request: CommitFilesRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    github_service: GitHubAppService = Depends(get_github_service)
):
    """Create a commit with multiple file changes."""
    # Get repository
    result = await db.execute(
        select(GitHubRepository)
        .where(GitHubRepository.id == repo_id)
        .options(selectinload(GitHubRepository.installation))
    )
    repo = result.scalar_one_or_none()
    
    if not repo:
        raise HTTPException(404, "Repository not found")
    
    # Create commit
    commit_sha = await github_service.create_commit(
        installation_id=repo.installation.github_installation_id,
        owner=repo.owner,
        repo=repo.name,
        branch=request.branch,
        message=request.message,
        files=request.files,
        author={
            "name": current_user.full_name or current_user.email,
            "email": current_user.email
        }
    )
    
    return {
        "commit_sha": commit_sha,
        "branch": request.branch
    }


@router.post("/repositories/{repo_id}/pulls")
async def create_pull_request(
    repo_id: UUID,
    request: CreatePullRequestRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    github_service: GitHubAppService = Depends(get_github_service)
):
    """Create a pull request."""
    # Get repository
    result = await db.execute(
        select(GitHubRepository)
        .where(GitHubRepository.id == repo_id)
        .options(selectinload(GitHubRepository.installation))
    )
    repo = result.scalar_one_or_none()
    
    if not repo:
        raise HTTPException(404, "Repository not found")
    
    # Create PR
    pr = await github_service.create_pull_request(
        installation_id=repo.installation.github_installation_id,
        owner=repo.owner,
        repo=repo.name,
        title=request.title,
        head=request.head,
        base=request.base,
        body=request.body,
        draft=request.draft
    )
    
    return {
        "number": pr.number,
        "title": pr.title,
        "html_url": pr.html_url,
        "state": pr.state
    }


@router.get("/repositories/{repo_id}/pulls")
async def list_pull_requests(
    repo_id: UUID,
    state: str = "open",
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    github_service: GitHubAppService = Depends(get_github_service)
):
    """List pull requests."""
    # Get repository
    result = await db.execute(
        select(GitHubRepository)
        .where(GitHubRepository.id == repo_id)
        .options(selectinload(GitHubRepository.installation))
    )
    repo = result.scalar_one_or_none()
    
    if not repo:
        raise HTTPException(404, "Repository not found")
    
    # List PRs
    prs = await github_service.list_pull_requests(
        installation_id=repo.installation.github_installation_id,
        owner=repo.owner,
        repo=repo.name,
        state=state
    )
    
    return [
        {
            "number": pr.number,
            "title": pr.title,
            "state": pr.state,
            "html_url": pr.html_url,
            "head_ref": pr.head_ref,
            "base_ref": pr.base_ref
        }
        for pr in prs
    ]


@router.post("/repositories/{repo_id}/issues")
async def create_issue(
    repo_id: UUID,
    request: CreateIssueRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    github_service: GitHubAppService = Depends(get_github_service)
):
    """Create an issue."""
    # Get repository
    result = await db.execute(
        select(GitHubRepository)
        .where(GitHubRepository.id == repo_id)
        .options(selectinload(GitHubRepository.installation))
    )
    repo = result.scalar_one_or_none()
    
    if not repo:
        raise HTTPException(404, "Repository not found")
    
    # Create issue
    issue = await github_service.create_issue(
        installation_id=repo.installation.github_installation_id,
        owner=repo.owner,
        repo=repo.name,
        title=request.title,
        body=request.body,
        labels=request.labels,
        assignees=request.assignees
    )
    
    return {
        "number": issue.number,
        "title": issue.title,
        "html_url": issue.html_url,
        "state": issue.state
    }


@router.post("/webhooks")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(...),
    x_github_delivery: str = Header(...),
    x_hub_signature_256: str = Header(...),
    db: AsyncSession = Depends(get_db),
    github_service: GitHubAppService = Depends(get_github_service)
):
    """Handle GitHub webhook events."""
    # Verify signature
    payload = await request.body()
    
    expected_signature = "sha256=" + hmac.new(
        github_service.config.webhook_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(expected_signature, x_hub_signature_256):
        raise HTTPException(401, "Invalid signature")
    
    # Parse payload
    payload_json = await request.json()
    
    # Handle different event types
    if x_github_event == "installation":
        await handle_installation_event(payload_json, db)
    elif x_github_event == "installation_repositories":
        await handle_repositories_event(payload_json, db)
    elif x_github_event == "push":
        await handle_push_event(payload_json, db)
    elif x_github_event == "pull_request":
        await handle_pull_request_event(payload_json, db)
    
    return {"status": "processed"}


async def handle_installation_event(payload: dict, db: AsyncSession):
    """Handle installation events."""
    action = payload["action"]
    installation = payload["installation"]
    
    if action == "created":
        # Create installation record
        inst = GitHubInstallation(
            organization_id=...,  # Get from somewhere
            github_installation_id=installation["id"],
            github_account_id=installation["account"]["id"],
            github_account_login=installation["account"]["login"],
            github_account_type=installation["account"]["type"],
            permissions=installation.get("permissions", {}),
            events=installation.get("events", [])
        )
        db.add(inst)
        await db.commit()
    
    elif action == "deleted":
        # Remove installation
        result = await db.execute(
            select(GitHubInstallation).where(
                GitHubInstallation.github_installation_id == installation["id"]
            )
        )
        inst = result.scalar_one_or_none()
        if inst:
            await db.delete(inst)
            await db.commit()
```

Now create the GitHub App setup guide:

```markdown:docs/github-app-setup.md
# GitHub App Setup Guide

## Creating Your GitHub App

1. **Go to GitHub Developer Settings**
   - Navigate to: https://github.com/settings/apps
   - Click "New GitHub App"

2. **Basic Information**
   - **App name**: `YourApp (Production)`
   - **Homepage URL**: `https://your-domain.com`
   - **Callback URL**: `https://your-domain.com/api/v1/github/callback`
   - **Webhook URL**: `https://your-domain.com/api/v1/github/webhooks`
   - **Webhook secret**: Generate a random string (save this!)

3. **Permissions**

   **Repository Permissions:**
   - Contents: Read & Write (for file operations)
   - Issues: Read & Write
   - Metadata: Read-only
   - Pull requests: Read & Write
   - Commit statuses: Read & Write
   - Webhooks: Read & Write

   **Organization Permissions:**
   - Members: Read-only (optional)

4. **Subscribe to Events**
   - [x] Push
   - [x] Pull request
   - [x] Pull request review
   - [x] Issues
   - [x] Issue comment
   - [x] Commit comment
   - [x] Create
   - [x] Delete

5. **Where can this app be installed?**
   - Select: "Any account"

6. **Create the App**
   - Click "Create GitHub App"
   - **Save the following values:**
     - App ID
     - Client ID
     - Client Secret (generate and save immediately!)

7. **Generate Private Key**
   - Scroll down to "Private keys"
   - Click "Generate a private key"
   - Download the `.pem` file
   - **Keep this file secure!**

## Configuration

Add to your `.env` file:

```bash
# GitHub App Configuration
GITHUB_APP_ID=123456
GITHUB_CLIENT_ID=Iv1.abc123def456
GITHUB_CLIENT_SECRET=your_client_secret_here
GITHUB_PRIVATE_KEY_PATH=/path/to/your-app.2024-01-01.private-key.pem
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
```

## Installation Flow

### For Users to Install Your App:

1. **Installation URL**
   ```
   https://github.com/apps/your-app-name/installations/new
   ```

2. **User Flow:**
   - User clicks "Install" on your app
   - Selects repositories (all or specific)
   - Authorizes permissions
   - GitHub redirects to your callback URL with installation_id

3. **Store Installation:**
   - Your webhook receives `installation.created` event
   - Store installation_id in database
   - Associate with user's organization

## Testing Locally with ngrok

```bash
# Install ngrok
brew install ngrok  # or download from ngrok.com

# Start your app
python -m uvicorn main:app --reload --port 8000

# In another terminal, expose your app
ngrok http 8000

# Update GitHub App webhook URL to ngrok URL
# Example: https://abc123.ngrok.io/api/v1/github/webhooks
```

## Security Best Practices

1. **Private Key Storage:**
   - Never commit private key to git
   - Store in secure environment variables or secret manager
   - Rotate periodically

2. **Webhook Secret:**
   - Always verify webhook signatures
   - Use constant-time comparison
   - Rotate if compromised

3. **Token Management:**
   - Installation tokens expire after 1 hour
   - Request new tokens as needed
   - Never log tokens

4. **Rate Limiting:**
   - GitHub API: 5,000 requests/hour per installation
   - Implement backoff and retry logic
   - Cache responses when possible

## Common Operations

### Agent Commits to Repository

```python
# In your agent execution
github_service = GitHubAppService(config, encryption)

# Create branch
await github_service.create_branch(
    installation_id=installation.github_installation_id,
    owner="user",
    repo="project",
    branch_name=f"feature/task-{task.id}",
    from_branch="main"
)

# Make changes
await github_service.create_commit(
    installation_id=installation.github_installation_id,
    owner="user",
    repo="project",
    branch=f"feature/task-{task.id}",
    message="Implement feature X",
    files=[
        {"path": "src/main.py", "content": "..."},
        {"path": "tests/test_main.py", "content": "..."}
    ]
)

# Create PR
pr = await github_service.create_pull_request(
    installation_id=installation.github_installation_id,
    owner="user",
    repo="project",
    title=f"[Task #{task.id}] {task.title}",
    head=f"feature/task-{task.id}",
    base="main",
    body=f"Implements {task.description}"
)
```

## Troubleshooting

### Webhook Not Receiving Events
- Check webhook URL is accessible
- Verify webhook secret matches
- Check Recent Deliveries in GitHub App settings

### Permission Denied
- Verify app has correct permissions
- Check if user accepted all permissions
- Re-install app if permissions changed

### Token Expired
- Installation tokens last 1 hour
- Request new token for each operation
- Don't cache tokens longer than 30 minutes
```

This complete GitHub App integration allows your agents to:
- Create branches and commits
- Open and manage pull requests
- Create and update issues
- Review code
- Manage webhooks
- Full repository access

All operations are done programmatically through your agents!



## Response:
11/19/2025, 11:56:04 AM

Absolutely! Using the official PyGithub library will make the code much cleaner and more maintainable. Here's the refactored version:

```python:src/services/github/github_app_service.py
"""
GitHub App Integration using PyGithub
Simplified and more maintainable GitHub API access
"""

from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
import jwt
from github import Github, GithubIntegration, Auth
from github.Repository import Repository
from github.PullRequest import PullRequest
from github.Issue import Issue
from github.Branch import Branch
from github.Commit import Commit
from github.GithubException import GithubException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import asyncio

from models import Project, GitHubInstallation, User
from services.encryption import EncryptionService


class GitHubAppConfig(BaseModel):
    """GitHub App configuration."""
    app_id: int
    private_key: str  # PEM format
    webhook_secret: str


class GitHubRepositoryInfo(BaseModel):
    """GitHub repository information."""
    id: int
    name: str
    full_name: str
    owner: str
    private: bool
    default_branch: str
    html_url: str
    clone_url: str
    ssh_url: str
    permissions: Dict[str, bool]
    description: Optional[str] = None


class GitHubPullRequestInfo(BaseModel):
    """GitHub pull request information."""
    number: int
    title: str
    body: Optional[str]
    state: str
    html_url: str
    head_ref: str
    base_ref: str
    head_sha: str
    mergeable: Optional[bool]
    merged: bool
    draft: bool
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    merged_at: Optional[datetime] = None


class GitHubIssueInfo(BaseModel):
    """GitHub issue information."""
    number: int
    title: str
    body: Optional[str]
    state: str
    html_url: str
    labels: List[str]
    assignees: List[str]
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None


class GitHubCommitInfo(BaseModel):
    """GitHub commit information."""
    sha: str
    message: str
    author_name: str
    author_email: str
    committer_name: str
    committer_email: str
    html_url: str
    created_at: datetime
    files_changed: List[str]


class GitHubAppService:
    """Service for GitHub App API interactions using PyGithub."""
    
    def __init__(
        self,
        config: GitHubAppConfig,
        encryption_service: EncryptionService
    ):
        self.config = config
        self.encryption = encryption_service
        
        # Initialize GitHub App integration
        self.integration = GithubIntegration(
            integration_id=config.app_id,
            private_key=config.private_key
        )
    
    def _get_installation_client(self, installation_id: int) -> Github:
        """
        Get authenticated Github client for installation.
        
        This automatically handles token generation and refresh.
        """
        auth = self.integration.get_access_token(installation_id)
        return Github(auth=Auth.Token(auth.token))
    
    async def list_installations(self) -> List[Dict]:
        """List all installations of the GitHub App."""
        # PyGithub doesn't have async support, so we run in executor
        loop = asyncio.get_event_loop()
        
        def _list():
            installations = self.integration.get_installations()
            return [
                {
                    "id": inst.id,
                    "account": {
                        "login": inst.account.login,
                        "type": inst.account.type,
                        "id": inst.account.id
                    },
                    "created_at": inst.created_at,
                    "updated_at": inst.updated_at,
                    "permissions": inst.permissions,
                    "events": inst.events
                }
                for inst in installations
            ]
        
        return await loop.run_in_executor(None, _list)
    
    async def list_installation_repositories(
        self,
        installation_id: int
    ) -> List[GitHubRepositoryInfo]:
        """List repositories accessible by installation."""
        loop = asyncio.get_event_loop()
        
        def _list():
            client = self._get_installation_client(installation_id)
            repos = client.get_installation(installation_id).get_repos()
            
            return [
                GitHubRepositoryInfo(
                    id=repo.id,
                    name=repo.name,
                    full_name=repo.full_name,
                    owner=repo.owner.login,
                    private=repo.private,
                    default_branch=repo.default_branch,
                    html_url=repo.html_url,
                    clone_url=repo.clone_url,
                    ssh_url=repo.ssh_url,
                    permissions={
                        "admin": repo.permissions.admin,
                        "push": repo.permissions.push,
                        "pull": repo.permissions.pull
                    },
                    description=repo.description
                )
                for repo in repos
            ]
        
        return await loop.run_in_executor(None, _list)
    
    async def get_repository(
        self,
        installation_id: int,
        owner: str,
        repo_name: str
    ) -> GitHubRepositoryInfo:
        """Get repository details."""
        loop = asyncio.get_event_loop()
        
        def _get():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            
            return GitHubRepositoryInfo(
                id=repo.id,
                name=repo.name,
                full_name=repo.full_name,
                owner=repo.owner.login,
                private=repo.private,
                default_branch=repo.default_branch,
                html_url=repo.html_url,
                clone_url=repo.clone_url,
                ssh_url=repo.ssh_url,
                permissions={
                    "admin": repo.permissions.admin,
                    "push": repo.permissions.push,
                    "pull": repo.permissions.pull
                },
                description=repo.description
            )
        
        return await loop.run_in_executor(None, _get)
    
    async def create_branch(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        branch_name: str,
        from_branch: str = "main"
    ) -> str:
        """
        Create a new branch.
        
        Returns the SHA of the new branch.
        """
        loop = asyncio.get_event_loop()
        
        def _create():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            
            # Get base branch
            base_branch = repo.get_branch(from_branch)
            base_sha = base_branch.commit.sha
            
            # Create new branch
            repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=base_sha
            )
            
            return base_sha
        
        return await loop.run_in_executor(None, _create)
    
    async def get_file_content(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        path: str,
        ref: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Get file content from repository.
        
        Returns tuple of (content, sha).
        """
        loop = asyncio.get_event_loop()
        
        def _get():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            
            file = repo.get_contents(path, ref=ref)
            return (file.decoded_content.decode('utf-8'), file.sha)
        
        return await loop.run_in_executor(None, _get)
    
    async def create_or_update_file(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: Optional[str] = None
    ) -> str:
        """
        Create or update a file in repository.
        
        Args:
            sha: Required for updates, omit for new files
        
        Returns commit SHA.
        """
        loop = asyncio.get_event_loop()
        
        def _create_update():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            
            if sha:
                # Update existing file
                result = repo.update_file(
                    path=path,
                    message=message,
                    content=content,
                    sha=sha,
                    branch=branch
                )
            else:
                # Create new file
                result = repo.create_file(
                    path=path,
                    message=message,
                    content=content,
                    branch=branch
                )
            
            return result['commit'].sha
        
        return await loop.run_in_executor(None, _create_update)
    
    async def delete_file(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        path: str,
        message: str,
        sha: str,
        branch: str
    ) -> str:
        """Delete a file from repository. Returns commit SHA."""
        loop = asyncio.get_event_loop()
        
        def _delete():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            
            result = repo.delete_file(
                path=path,
                message=message,
                sha=sha,
                branch=branch
            )
            
            return result['commit'].sha
        
        return await loop.run_in_executor(None, _delete)
    
    async def create_pull_request(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        title: str,
        head: str,
        base: str,
        body: Optional[str] = None,
        draft: bool = False,
        maintainer_can_modify: bool = True
    ) -> GitHubPullRequestInfo:
        """Create a pull request."""
        loop = asyncio.get_event_loop()
        
        def _create():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            
            pr = repo.create_pull(
                title=title,
                body=body or "",
                head=head,
                base=base,
                draft=draft,
                maintainer_can_modify=maintainer_can_modify
            )
            
            return GitHubPullRequestInfo(
                number=pr.number,
                title=pr.title,
                body=pr.body,
                state=pr.state,
                html_url=pr.html_url,
                head_ref=pr.head.ref,
                base_ref=pr.base.ref,
                head_sha=pr.head.sha,
                mergeable=pr.mergeable,
                merged=pr.merged,
                draft=pr.draft,
                created_at=pr.created_at,
                updated_at=pr.updated_at,
                closed_at=pr.closed_at,
                merged_at=pr.merged_at
            )
        
        return await loop.run_in_executor(None, _create)
    
    async def update_pull_request(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        pr_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        base: Optional[str] = None
    ) -> GitHubPullRequestInfo:
        """Update a pull request."""
        loop = asyncio.get_event_loop()
        
        def _update():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            pr = repo.get_pull(pr_number)
            
            if title:
                pr.edit(title=title)
            if body is not None:
                pr.edit(body=body)
            if state:
                pr.edit(state=state)
            if base:
                pr.edit(base=base)
            
            # Refresh to get updated data
            pr = repo.get_pull(pr_number)
            
            return GitHubPullRequestInfo(
                number=pr.number,
                title=pr.title,
                body=pr.body,
                state=pr.state,
                html_url=pr.html_url,
                head_ref=pr.head.ref,
                base_ref=pr.base.ref,
                head_sha=pr.head.sha,
                mergeable=pr.mergeable,
                merged=pr.merged,
                draft=pr.draft,
                created_at=pr.created_at,
                updated_at=pr.updated_at,
                closed_at=pr.closed_at,
                merged_at=pr.merged_at
            )
        
        return await loop.run_in_executor(None, _update)
    
    async def merge_pull_request(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        pr_number: int,
        commit_title: Optional[str] = None,
        commit_message: Optional[str] = None,
        merge_method: str = "merge"  # merge, squash, or rebase
    ) -> bool:
        """Merge a pull request. Returns True if merged successfully."""
        loop = asyncio.get_event_loop()
        
        def _merge():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            pr = repo.get_pull(pr_number)
            
            result = pr.merge(
                commit_title=commit_title,
                commit_message=commit_message,
                merge_method=merge_method
            )
            
            return result.merged
        
        return await loop.run_in_executor(None, _merge)
    
    async def list_pull_requests(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        state: str = "open",
        base: Optional[str] = None,
        head: Optional[str] = None,
        sort: str = "created",
        direction: str = "desc"
    ) -> List[GitHubPullRequestInfo]:
        """List pull requests."""
        loop = asyncio.get_event_loop()
        
        def _list():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            
            prs = repo.get_pulls(
                state=state,
                sort=sort,
                direction=direction,
                base=base,
                head=head
            )
            
            return [
                GitHubPullRequestInfo(
                    number=pr.number,
                    title=pr.title,
                    body=pr.body,
                    state=pr.state,
                    html_url=pr.html_url,
                    head_ref=pr.head.ref,
                    base_ref=pr.base.ref,
                    head_sha=pr.head.sha,
                    mergeable=pr.mergeable,
                    merged=pr.merged,
                    draft=pr.draft,
                    created_at=pr.created_at,
                    updated_at=pr.updated_at,
                    closed_at=pr.closed_at,
                    merged_at=pr.merged_at
                )
                for pr in prs
            ]
        
        return await loop.run_in_executor(None, _list)
    
    async def create_issue(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None
    ) -> GitHubIssueInfo:
        """Create an issue."""
        loop = asyncio.get_event_loop()
        
        def _create():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            
            issue = repo.create_issue(
                title=title,
                body=body,
                labels=labels or [],
                assignees=assignees or [],
                milestone=repo.get_milestone(milestone) if milestone else None
            )
            
            return GitHubIssueInfo(
                number=issue.number,
                title=issue.title,
                body=issue.body,
                state=issue.state,
                html_url=issue.html_url,
                labels=[label.name for label in issue.labels],
                assignees=[assignee.login for assignee in issue.assignees],
                created_at=issue.created_at,
                updated_at=issue.updated_at,
                closed_at=issue.closed_at
            )
        
        return await loop.run_in_executor(None, _create)
    
    async def update_issue(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None
    ) -> GitHubIssueInfo:
        """Update an issue."""
        loop = asyncio.get_event_loop()
        
        def _update():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            issue = repo.get_issue(issue_number)
            
            if title:
                issue.edit(title=title)
            if body is not None:
                issue.edit(body=body)
            if state:
                issue.edit(state=state)
            if labels is not None:
                issue.edit(labels=labels)
            if assignees is not None:
                issue.edit(assignees=assignees)
            
            # Refresh
            issue = repo.get_issue(issue_number)
            
            return GitHubIssueInfo(
                number=issue.number,
                title=issue.title,
                body=issue.body,
                state=issue.state,
                html_url=issue.html_url,
                labels=[label.name for label in issue.labels],
                assignees=[assignee.login for assignee in issue.assignees],
                created_at=issue.created_at,
                updated_at=issue.updated_at,
                closed_at=issue.closed_at
            )
        
        return await loop.run_in_executor(None, _update)
    
    async def add_comment(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        issue_number: int,
        body: str
    ) -> int:
        """Add a comment to an issue or PR. Returns comment ID."""
        loop = asyncio.get_event_loop()
        
        def _comment():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            issue = repo.get_issue(issue_number)
            
            comment = issue.create_comment(body)
            return comment.id
        
        return await loop.run_in_executor(None, _comment)
    
    async def get_commit(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        sha: str
    ) -> GitHubCommitInfo:
        """Get commit details."""
        loop = asyncio.get_event_loop()
        
        def _get():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            commit = repo.get_commit(sha)
            
            return GitHubCommitInfo(
                sha=commit.sha,
                message=commit.commit.message,
                author_name=commit.commit.author.name,
                author_email=commit.commit.author.email,
                committer_name=commit.commit.committer.name,
                committer_email=commit.commit.committer.email,
                html_url=commit.html_url,
                created_at=commit.commit.author.date,
                files_changed=[file.filename for file in commit.files]
            )
        
        return await loop.run_in_executor(None, _get)
    
    async def list_commits(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        sha: Optional[str] = None,
        path: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        per_page: int = 30
    ) -> List[GitHubCommitInfo]:
        """List commits."""
        loop = asyncio.get_event_loop()
        
        def _list():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            
            commits = repo.get_commits(
                sha=sha,
                path=path,
                since=since,
                until=until
            )
            
            result = []
            for commit in commits[:per_page]:
                result.append(GitHubCommitInfo(
                    sha=commit.sha,
                    message=commit.commit.message,
                    author_name=commit.commit.author.name,
                    author_email=commit.commit.author.email,
                    committer_name=commit.commit.committer.name,
                    committer_email=commit.commit.committer.email,
                    html_url=commit.html_url,
                    created_at=commit.commit.author.date,
                    files_changed=[file.filename for file in commit.files]
                ))
            
            return result
        
        return await loop.run_in_executor(None, _list)
    
    async def create_webhook(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        webhook_url: str,
        events: List[str],
        active: bool = True
    ) -> int:
        """Create a webhook for repository. Returns webhook ID."""
        loop = asyncio.get_event_loop()
        
        def _create():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            
            hook = repo.create_hook(
                name="web",
                config={
                    "url": webhook_url,
                    "content_type": "json",
                    "secret": self.config.webhook_secret
                },
                events=events,
                active=active
            )
            
            return hook.id
        
        return await loop.run_in_executor(None, _create)
    
    async def request_reviewers(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        pr_number: int,
        reviewers: List[str],
        team_reviewers: Optional[List[str]] = None
    ):
        """Request reviewers for a pull request."""
        loop = asyncio.get_event_loop()
        
        def _request():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            pr = repo.get_pull(pr_number)
            
            pr.create_review_request(
                reviewers=reviewers,
                team_reviewers=team_reviewers or []
            )
        
        await loop.run_in_executor(None, _request)
    
    async def get_pr_files(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        pr_number: int
    ) -> List[Dict[str, Any]]:
        """Get files changed in a pull request."""
        loop = asyncio.get_event_loop()
        
        def _get():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            pr = repo.get_pull(pr_number)
            
            return [
                {
                    "filename": file.filename,
                    "status": file.status,
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "changes": file.changes,
                    "patch": file.patch,
                    "blob_url": file.blob_url,
                    "raw_url": file.raw_url
                }
                for file in pr.get_files()
            ]
        
        return await loop.run_in_executor(None, _get)
    
    async def create_pr_review(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        pr_number: int,
        event: str,  # APPROVE, REQUEST_CHANGES, COMMENT
        body: Optional[str] = None,
        comments: Optional[List[Dict]] = None
    ) -> int:
        """Create a review for a pull request. Returns review ID."""
        loop = asyncio.get_event_loop()
        
        def _review():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            pr = repo.get_pull(pr_number)
            
            # Convert comments to proper format if provided
            review_comments = []
            if comments:
                for comment in comments:
                    review_comments.append({
                        "path": comment["path"],
                        "position": comment.get("position"),
                        "body": comment["body"]
                    })
            
            review = pr.create_review(
                body=body,
                event=event,
                comments=review_comments if review_comments else None
            )
            
            return review.id
        
        return await loop.run_in_executor(None, _review)
    
    async def get_branch(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        branch_name: str
    ) -> Dict[str, Any]:
        """Get branch details."""
        loop = asyncio.get_event_loop()
        
        def _get():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            branch = repo.get_branch(branch_name)
            
            return {
                "name": branch.name,
                "protected": branch.protected,
                "commit_sha": branch.commit.sha,
                "commit_url": branch.commit.html_url
            }
        
        return await loop.run_in_executor(None, _get)
    
    async def delete_branch(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        branch_name: str
    ):
        """Delete a branch."""
        loop = asyncio.get_event_loop()
        
        def _delete():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            ref = repo.get_git_ref(f"heads/{branch_name}")
            ref.delete()
        
        await loop.run_in_executor(None, _delete)
    
    async def compare_commits(
        self,
        installation_id: int,
        owner: str,
        repo_name: str,
        base: str,
        head: str
    ) -> Dict[str, Any]:
        """Compare two commits/branches."""
        loop = asyncio.get_event_loop()
        
        def _compare():
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(f"{owner}/{repo_name}")
            comparison = repo.compare(base, head)
            
            return {
                "ahead_by": comparison.ahead_by,
                "behind_by": comparison.behind_by,
                "status": comparison.status,
                "total_commits": comparison.total_commits,
                "files": [
                    {
                        "filename": file.filename,
                        "status": file.status,
                        "additions": file.additions,
                        "deletions": file.deletions,
                        "changes": file.changes
                    }
                    for file in comparison.files
                ]
            }
        
        return await loop.run_in_executor(None, _compare)
    
    async def search_code(
        self,
        installation_id: int,
        query: str,
        owner: Optional[str] = None,
        repo_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search code in repositories."""
        loop = asyncio.get_event_loop()
        
        def _search():
            client = self._get_installation_client(installation_id)
            
            # Build query
            search_query = query
            if owner and repo_name:
                search_query += f" repo:{owner}/{repo_name}"
            
            results = client.search_code(search_query)
            
            return [
                {
                    "name": result.name,
                    "path": result.path,
                    "repository": result.repository.full_name,
                    "url": result.html_url,
                    "sha": result.sha
                }
                for result in results
            ]
        
        return await loop.run_in_executor(None, _search)
```

Now update the requirements:

```txt:requirements.txt
# Existing requirements...

# GitHub SDK
PyGithub==2.1.1
PyJWT==2.8.0
cryptography==41.0.7

# Async support
asyncio==3.4.3
```

The benefits of using PyGithub:

1. **Much cleaner code** - No manual HTTP requests
2. **Better type hints** - IDE autocomplete works great
3. **Automatic pagination** - Handled by the library
4. **Error handling** - Consistent exception handling
5. **Rate limiting** - Built-in rate limit handling
6. **Less boilerplate** - No need to construct URLs manually
7. **Well tested** - Battle-tested by thousands of projects

Example usage in your agent execution:

```python
# Before (manual):
async with httpx.AsyncClient() as client:
    response = await client.post(
        f"{self.base_url}/repos/{owner}/{repo}/pulls",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": title, "head": head, "base": base}
    )
    pr_data = response.json()

# After (PyGithub):
pr = await github_service.create_pull_request(
    installation_id=installation_id,
    owner=owner,
    repo_name=repo,
    title=title,
    head=head,
    base=base
)
```

Much simpler and more maintainable!





---
Powered by [Claude Exporter](https://www.claudexporter.com)