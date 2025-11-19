# Supabase Authentication Integration Plan

**Created**: 2025-01-30  
**Status**: Implementation Plan  
**Purpose**: Comprehensive plan for integrating Supabase authentication with OmoiOS

---

## Executive Summary

This plan outlines the integration of Supabase authentication into the OmoiOS system, including:
- Database user replication from `auth.users` to `public.users`
- Supabase Python SDK integration
- FastAPI authentication middleware
- JWT token verification
- User management API endpoints
- Integration with existing routes

---

## 1. Supabase Connection Details

**Provided Credentials:**
- **Supabase URL**: `https://ogqsxfcnpmcslmqfombp.supabase.co`
- **Publishable Key**: `sb_publishable_Q8raBOkqd5TDYJ8L-zCxtQ_F_ttoHRy`
- **Secret Key**: `sb_secret_OoXIDSzsqxxIYxhW17mTrg_IH5G1XAG`
- **PostgreSQL Password**: `gtR8fVhhZz3Fcv6g`
- **PostgreSQL Connection**: `postgresql://postgres.ogqsxfcnpmcslmqfombp:gtR8fVhhZz3Fcv6g@aws-1-us-east-1.pooler.supabase.com:6543/postgres`

**Note**: The connection string uses the pooler on port 6543. For direct connections, use port 5432.

---

## 2. Architecture Overview

### 2.1 Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Supabase Client (@supabase/supabase-js)            │   │
│  │  • signInWithPassword()                              │   │
│  │  • signUp()                                          │   │
│  │  • signOut()                                          │   │
│  │  • getSession() → JWT Token                          │   │
│  └──────────────────┬───────────────────────────────────┘   │
└──────────────────────┼───────────────────────────────────────┘
                       │
                       │ JWT Token in Authorization Header
                       │
┌──────────────────────▼───────────────────────────────────────┐
│              FastAPI Backend                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Supabase Auth Middleware                            │   │
│  │  • Verify JWT Token                                  │   │
│  │  • Extract user_id from token                        │   │
│  │  • Load user from public.users                       │   │
│  │  • Inject user into request context                  │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                       │                                        │
│  ┌────────────────────▼───────────────────────────────────┐   │
│  │  API Routes (Protected)                                │   │
│  │  • Use Depends(get_current_user)                      │   │
│  │  • Access user via request state                     │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       │
┌──────────────────────▼───────────────────────────────────────┐
│              Supabase PostgreSQL                             │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │  auth.users      │      │  public.users    │            │
│  │  (Supabase Auth) │ ────▶│  (Replicated)    │            │
│  │                  │      │                  │            │
│  │  • id (UUID)     │      │  • id (UUID)     │            │
│  │  • email         │      │  • email         │            │
│  │  • encrypted_pwd │      │  • name          │            │
│  │  • created_at    │      │  • role          │            │
│  │  • updated_at    │      │  • metadata      │            │
│  └──────────────────┘      └──────────────────┘            │
│         │                            │                       │
│         └─────────── Trigger ─────────┘                       │
│                    (Auto-sync)                                │
└───────────────────────────────────────────────────────────────┘
```

### 2.2 Component Structure

```
omoi_os/
├── config.py                    # Add SupabaseSettings
├── models/
│   └── user.py                  # User model (public.users)
├── services/
│   ├── supabase_auth.py         # Supabase client & JWT verification
│   └── user_service.py          # User management service
├── api/
│   ├── dependencies.py          # Add get_current_user dependency
│   ├── middleware/
│   │   └── auth.py               # FastAPI auth middleware
│   └── routes/
│       └── auth.py               # Auth endpoints (login, signup, etc.)
└── migrations/
    └── versions/
        └── XXX_supabase_auth.py  # User replication migration
```

---

## 3. Database Schema Design

### 3.1 User Replication Strategy

**Approach**: Use PostgreSQL triggers to automatically replicate `auth.users` to `public.users`

**Benefits**:
- Real-time synchronization
- No application-level sync logic needed
- Handles user creation, updates, and deletions
- Works with Supabase Auth webhooks

### 3.2 public.users Table Schema

```sql
CREATE TABLE public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    email_confirmed_at TIMESTAMPTZ,
    phone TEXT,
    phone_confirmed_at TIMESTAMPTZ,
    
    -- User profile fields
    name TEXT,
    avatar_url TEXT,
    role TEXT DEFAULT 'user',  -- user, admin, project_manager, developer, viewer
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_sign_in_at TIMESTAMPTZ,
    
    -- Soft delete
    deleted_at TIMESTAMPTZ,
    
    -- Indexes
    CONSTRAINT users_email_key UNIQUE (email)
);

CREATE INDEX idx_users_email ON public.users(email);
CREATE INDEX idx_users_role ON public.users(role);
CREATE INDEX idx_users_deleted_at ON public.users(deleted_at) WHERE deleted_at IS NULL;
```

### 3.3 Replication Trigger

```sql
-- Function to handle user replication
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (
        id,
        email,
        email_confirmed_at,
        phone,
        phone_confirmed_at,
        created_at,
        updated_at,
        last_sign_in_at,
        metadata
    )
    VALUES (
        NEW.id,
        NEW.email,
        NEW.email_confirmed_at,
        NEW.phone,
        NEW.phone_confirmed_at,
        NEW.created_at,
        NEW.updated_at,
        NEW.last_sign_in_at,
        COALESCE(NEW.raw_user_meta_data, '{}'::jsonb)
    )
    ON CONFLICT (id) DO UPDATE
    SET
        email = EXCLUDED.email,
        email_confirmed_at = EXCLUDED.email_confirmed_at,
        phone = EXCLUDED.phone,
        phone_confirmed_at = EXCLUDED.phone_confirmed_at,
        updated_at = EXCLUDED.updated_at,
        last_sign_in_at = EXCLUDED.last_sign_in_at,
        metadata = EXCLUDED.metadata;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger on auth.users insert/update
CREATE TRIGGER on_auth_user_created
    AFTER INSERT OR UPDATE ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- Function to handle user deletion (soft delete)
CREATE OR REPLACE FUNCTION public.handle_user_deleted()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.users
    SET deleted_at = NOW()
    WHERE id = OLD.id;
    
    RETURN OLD;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger on auth.users delete
CREATE TRIGGER on_auth_user_deleted
    AFTER DELETE ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_user_deleted();
```

### 3.4 Row Level Security (RLS)

```sql
-- Enable RLS on public.users
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Policy: Users can read their own profile
CREATE POLICY "Users can view own profile"
    ON public.users
    FOR SELECT
    USING (auth.uid() = id);

-- Policy: Users can update their own profile
CREATE POLICY "Users can update own profile"
    ON public.users
    FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- Policy: Service role can do anything (for backend operations)
CREATE POLICY "Service role full access"
    ON public.users
    FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');
```

---

## 4. Supabase Python SDK Integration

### 4.1 Installation

Add to `pyproject.toml`:
```toml
dependencies = [
    # ... existing dependencies ...
    "supabase>=2.0.0,<3",
]
```

### 4.2 Configuration

**Add to `omoi_os/config.py`:**

```python
class SupabaseSettings(BaseSettings):
    """Supabase configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="SUPABASE_",
        env_file=(".env",),
        env_file_encoding="utf-8",
    )

    url: str  # SUPABASE_URL
    anon_key: str  # SUPABASE_ANON_KEY (publishable key)
    service_role_key: str  # SUPABASE_SERVICE_ROLE_KEY (secret key)
    
    # Database connection (for direct PostgreSQL access)
    db_url: Optional[str] = None  # SUPABASE_DB_URL (optional, for direct DB access)


def load_supabase_settings() -> SupabaseSettings:
    return SupabaseSettings()
```

**Environment Variables:**
```bash
SUPABASE_URL=https://ogqsxfcnpmcslmqfombp.supabase.co
SUPABASE_ANON_KEY=sb_publishable_Q8raBOkqd5TDYJ8L-zCxtQ_F_ttoHRy
SUPABASE_SERVICE_ROLE_KEY=sb_secret_OoXIDSzsqxxIYxhW17mTrg_IH5G1XAG
SUPABASE_DB_URL=postgresql://postgres.ogqsxfcnpmcslmqfombp:gtR8fVhhZz3Fcv6g@aws-1-us-east-1.pooler.supabase.com:6543/postgres
```

### 4.3 Supabase Client Service

**Create `omoi_os/services/supabase_auth.py`:**

```python
"""Supabase authentication service."""

from typing import Optional
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

from omoi_os.config import SupabaseSettings, load_supabase_settings


class SupabaseAuthService:
    """Service for Supabase authentication and user management."""

    def __init__(self, settings: Optional[SupabaseSettings] = None):
        """
        Initialize Supabase client.

        Args:
            settings: Optional Supabase settings (defaults to loading from env)
        """
        self.settings = settings or load_supabase_settings()
        
        # Client for admin operations (uses service role key)
        self.admin_client: Client = create_client(
            self.settings.url,
            self.settings.service_role_key,
            options=ClientOptions(
                auto_refresh_token=False,
                persist_session=False,
            ),
        )
        
        # Client for user operations (uses anon key)
        # This is typically used on the frontend, but available here for server-side user ops
        self.client: Client = create_client(
            self.settings.url,
            self.settings.anon_key,
        )

    def verify_jwt_token(self, token: str) -> Optional[dict]:
        """
        Verify JWT token and return user info.

        Args:
            token: JWT token from Authorization header

        Returns:
            User info dict if valid, None otherwise
        """
        try:
            # Use admin client to verify token
            response = self.admin_client.auth.get_user(token)
            if response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "user_metadata": response.user.user_metadata or {},
                }
        except Exception:
            return None
        
        return None

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """
        Get user by ID using admin client.

        Args:
            user_id: User UUID

        Returns:
            User dict or None
        """
        try:
            response = self.admin_client.auth.admin.get_user_by_id(user_id)
            if response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "user_metadata": response.user.user_metadata or {},
                    "created_at": response.user.created_at,
                    "last_sign_in_at": response.user.last_sign_in_at,
                }
        except Exception:
            return None
        
        return None

    def create_user(
        self,
        email: str,
        password: str,
        user_metadata: Optional[dict] = None,
    ) -> Optional[dict]:
        """
        Create user via admin API.

        Args:
            email: User email
            password: User password
            user_metadata: Optional user metadata

        Returns:
            Created user dict or None
        """
        try:
            response = self.admin_client.auth.admin.create_user(
                {
                    "email": email,
                    "password": password,
                    "email_confirm": True,  # Auto-confirm email
                    "user_metadata": user_metadata or {},
                }
            )
            if response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "user_metadata": response.user.user_metadata or {},
                }
        except Exception:
            return None
        
        return None
```

---

## 5. User Model

**Create `omoi_os/models/user.py`:**

```python
"""User model for public.users table."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class User(Base):
    """User model representing replicated auth.users data."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        comment="References auth.users.id"
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    email_confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phone_confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Profile fields
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, default="user", index=True
    )  # user, admin, project_manager, developer, viewer
    
    # Metadata
    metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    last_sign_in_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
        Index("idx_users_deleted_at", "deleted_at"),
        {"comment": "Replicated from auth.users via trigger"},
    )
```

---

## 6. FastAPI Authentication Middleware

### 6.1 Authentication Dependency

**Add to `omoi_os/api/dependencies.py`:**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from omoi_os.models.user import User
from omoi_os.services.supabase_auth import SupabaseAuthService
from omoi_os.services.database import DatabaseService

security = HTTPBearer()


def get_supabase_auth_service() -> SupabaseAuthService:
    """Get Supabase auth service instance."""
    from omoi_os.services.supabase_auth import SupabaseAuthService
    from omoi_os.config import load_supabase_settings
    
    settings = load_supabase_settings()
    return SupabaseAuthService(settings)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase_auth: SupabaseAuthService = Depends(get_supabase_auth_service),
    db: DatabaseService = Depends(get_db_service),
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials
        supabase_auth: Supabase auth service
        db: Database service

    Returns:
        Authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    
    # Verify JWT token
    user_info = supabase_auth.verify_jwt_token(token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Load user from public.users
    with db.get_session() as session:
        user = session.get(User, user_info["id"])
        if not user or user.deleted_at:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    supabase_auth: SupabaseAuthService = Depends(get_supabase_auth_service),
    db: DatabaseService = Depends(get_db_service),
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.

    Useful for endpoints that work with or without authentication.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, supabase_auth, db)
    except HTTPException:
        return None
```

### 6.2 Optional: FastAPI Middleware for Request Context

**Create `omoi_os/api/middleware/auth.py`:**

```python
"""Authentication middleware for FastAPI."""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional

from omoi_os.services.supabase_auth import SupabaseAuthService
from omoi_os.config import load_supabase_settings


class SupabaseAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to extract and verify JWT tokens."""

    def __init__(self, app, supabase_auth: Optional[SupabaseAuthService] = None):
        super().__init__(app)
        self.supabase_auth = supabase_auth or SupabaseAuthService(
            load_supabase_settings()
        )

    async def dispatch(self, request: Request, call_next):
        """Process request and add user info to state if authenticated."""
        # Skip auth for public endpoints
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            user_info = self.supabase_auth.verify_jwt_token(token)
            if user_info:
                request.state.user_id = user_info["id"]
                request.state.user_email = user_info["email"]
        
        response = await call_next(request)
        return response
```

---

## 7. Auth API Routes

**Create `omoi_os/api/routes/auth.py`:**

```python
"""Authentication API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional

from omoi_os.api.dependencies import (
    get_current_user,
    get_supabase_auth_service,
    get_db_service,
)
from omoi_os.models.user import User
from omoi_os.services.supabase_auth import SupabaseAuthService
from omoi_os.services.database import DatabaseService

router = APIRouter()


class SignUpRequest(BaseModel):
    """Request model for user signup."""

    email: EmailStr
    password: str
    name: Optional[str] = None


class SignInRequest(BaseModel):
    """Request model for user signin."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Response model for user."""

    id: str
    email: str
    name: Optional[str] = None
    role: str
    avatar_url: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


@router.post("/signup", response_model=UserResponse)
async def signup(
    request: SignUpRequest,
    supabase_auth: SupabaseAuthService = Depends(get_supabase_auth_service),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Create a new user account.

    Note: This endpoint uses Supabase admin API to create users.
    For production, consider using Supabase Auth directly from frontend.
    """
    # Create user via Supabase
    user_data = supabase_auth.create_user(
        email=request.email,
        password=request.password,
        user_metadata={"name": request.name} if request.name else None,
    )
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create user",
        )
    
    # Wait for trigger to replicate to public.users, then fetch
    with db.get_session() as session:
        user = session.get(User, user_data["id"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User created but not found in database",
            )
        
        return UserResponse.model_validate(user)


@router.post("/signin", response_model=dict)
async def signin(
    request: SignInRequest,
    supabase_auth: SupabaseAuthService = Depends(get_supabase_auth_service),
):
    """
    Sign in user and return JWT token.

    Note: This endpoint uses Supabase client. For production,
    consider handling sign-in directly from frontend.
    """
    try:
        response = supabase_auth.client.auth.sign_in_with_password(
            {
                "email": request.email,
                "password": request.password,
            }
        )
        
        if not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type": "bearer",
            "expires_in": response.session.expires_in,
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "user_metadata": response.user.user_metadata or {},
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        ) from e


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current authenticated user information."""
    return UserResponse.model_validate(current_user)


@router.post("/signout")
async def signout(
    current_user: User = Depends(get_current_user),
    supabase_auth: SupabaseAuthService = Depends(get_supabase_auth_service),
):
    """Sign out current user."""
    # Supabase handles signout on client side
    # This endpoint is mainly for logging/auditing
    return {"message": "Signed out successfully"}


@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    supabase_auth: SupabaseAuthService = Depends(get_supabase_auth_service),
):
    """Refresh access token using refresh token."""
    try:
        response = supabase_auth.client.auth.refresh_session(refresh_token)
        
        if not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type": "bearer",
            "expires_in": response.session.expires_in,
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
```

---

## 8. Integration with Existing Routes

### 8.1 Protecting Routes

**Example: Protect Projects API**

```python
# omoi_os/api/routes/projects.py

from omoi_os.api.dependencies import get_current_user
from omoi_os.models.user import User

@router.post("", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),  # Add auth requirement
    db: DatabaseService = Depends(get_db_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """Create a new project (requires authentication)."""
    # ... existing code ...
    # Now you have access to current_user.id, current_user.email, etc.
```

### 8.2 Optional Authentication

**Example: Public endpoints with optional user context**

```python
from omoi_os.api.dependencies import get_current_user_optional

@router.get("/public-data")
async def get_public_data(
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Public endpoint that provides enhanced data if user is authenticated."""
    if current_user:
        # Return personalized data
        return {"data": "personalized", "user_id": current_user.id}
    else:
        # Return public data
        return {"data": "public"}
```

### 8.3 Role-Based Authorization

**Add to `omoi_os/api/dependencies.py`:**

```python
from typing import List
from fastapi import HTTPException, status

def require_role(allowed_roles: List[str]):
    """
    Dependency factory for role-based authorization.

    Usage:
        @router.post("/admin-only")
        async def admin_endpoint(
            current_user: User = Depends(require_role(["admin"]))
        ):
            ...
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of these roles: {', '.join(allowed_roles)}",
            )
        return current_user
    
    return role_checker
```

**Usage:**
```python
@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(require_role(["admin", "project_manager"])),
    db: DatabaseService = Depends(get_db_service),
):
    """Delete project (requires admin or project_manager role)."""
    # ... implementation ...
```

---

## 9. Database Migration

### 9.1 Migration File

**Create `migrations/versions/XXX_supabase_auth_integration.py`:**

```python
"""Add Supabase auth integration: user replication and triggers.

Revision ID: supabase_auth_001
Revises: <previous_revision>
Create Date: 2025-01-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


def upgrade():
    # Create public.users table
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("email_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("phone_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="user"),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_sign_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create indexes
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_role", "users", ["role"])
    op.create_index("idx_users_deleted_at", "users", ["deleted_at"])
    
    # Create replication function
    op.execute("""
        CREATE OR REPLACE FUNCTION public.handle_new_user()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO public.users (
                id, email, email_confirmed_at, phone, phone_confirmed_at,
                created_at, updated_at, last_sign_in_at, metadata
            )
            VALUES (
                NEW.id,
                NEW.email,
                NEW.email_confirmed_at,
                NEW.phone,
                NEW.phone_confirmed_at,
                NEW.created_at,
                NEW.updated_at,
                NEW.last_sign_in_at,
                COALESCE(NEW.raw_user_meta_data, '{}'::jsonb)
            )
            ON CONFLICT (id) DO UPDATE
            SET
                email = EXCLUDED.email,
                email_confirmed_at = EXCLUDED.email_confirmed_at,
                phone = EXCLUDED.phone,
                phone_confirmed_at = EXCLUDED.phone_confirmed_at,
                updated_at = EXCLUDED.updated_at,
                last_sign_in_at = EXCLUDED.last_sign_in_at,
                metadata = EXCLUDED.metadata;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # Create deletion function
    op.execute("""
        CREATE OR REPLACE FUNCTION public.handle_user_deleted()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE public.users
            SET deleted_at = NOW()
            WHERE id = OLD.id;
            
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # Create triggers
    op.execute("""
        CREATE TRIGGER on_auth_user_created
            AFTER INSERT OR UPDATE ON auth.users
            FOR EACH ROW
            EXECUTE FUNCTION public.handle_new_user();
    """)
    
    op.execute("""
        CREATE TRIGGER on_auth_user_deleted
            AFTER DELETE ON auth.users
            FOR EACH ROW
            EXECUTE FUNCTION public.handle_user_deleted();
    """)
    
    # Enable RLS
    op.execute("ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;")
    
    # Create RLS policies
    op.execute("""
        CREATE POLICY "Users can view own profile"
            ON public.users
            FOR SELECT
            USING (auth.uid() = id);
    """)
    
    op.execute("""
        CREATE POLICY "Users can update own profile"
            ON public.users
            FOR UPDATE
            USING (auth.uid() = id)
            WITH CHECK (auth.uid() = id);
    """)
    
    op.execute("""
        CREATE POLICY "Service role full access"
            ON public.users
            FOR ALL
            USING (auth.jwt()->>'role' = 'service_role');
    """)
    
    # Backfill existing users (if any exist in auth.users)
    op.execute("""
        INSERT INTO public.users (
            id, email, email_confirmed_at, phone, phone_confirmed_at,
            created_at, updated_at, last_sign_in_at, metadata
        )
        SELECT
            id,
            email,
            email_confirmed_at,
            phone,
            phone_confirmed_at,
            created_at,
            updated_at,
            last_sign_in_at,
            COALESCE(raw_user_meta_data, '{}'::jsonb)
        FROM auth.users
        ON CONFLICT (id) DO NOTHING;
    """)


def downgrade():
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;")
    op.execute("DROP TRIGGER IF EXISTS on_auth_user_deleted ON auth.users;")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS public.handle_new_user();")
    op.execute("DROP FUNCTION IF EXISTS public.handle_user_deleted();")
    
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS \"Users can view own profile\" ON public.users;")
    op.execute("DROP POLICY IF EXISTS \"Users can update own profile\" ON public.users;")
    op.execute("DROP POLICY IF EXISTS \"Service role full access\" ON public.users;")
    
    # Drop table
    op.drop_table("users")
```

---

## 10. Configuration Updates

### 10.1 Update Database Connection

**Option A: Use Supabase PostgreSQL directly**

Update `DATABASE_URL` in `.env`:
```bash
DATABASE_URL=postgresql+psycopg://postgres.ogqsxfcnpmcslmqfombp:gtR8fVhhZz3Fcv6g@aws-1-us-east-1.pooler.supabase.com:6543/postgres
```

**Option B: Keep local PostgreSQL for development, Supabase for production**

Update `omoi_os/config.py`:
```python
class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        env_file=(".env",),
        env_file_encoding="utf-8",
    )

    url: str = "postgresql+psycopg://postgres:postgres@localhost:15432/app_db"
    
    # Supabase connection (optional override)
    supabase_url: Optional[str] = None  # If set, uses Supabase instead
```

### 10.2 Environment Variables

**Add to `.env` file:**
```bash
# Supabase Configuration
SUPABASE_URL=https://ogqsxfcnpmcslmqfombp.supabase.co
SUPABASE_ANON_KEY=sb_publishable_Q8raBOkqd5TDYJ8L-zCxtQ_F_ttoHRy
SUPABASE_SERVICE_ROLE_KEY=sb_secret_OoXIDSzsqxxIYxhW17mTrg_IH5G1XAG

# Optional: Use Supabase PostgreSQL directly
# DATABASE_URL=postgresql+psycopg://postgres.ogqsxfcnpmcslmqfombp:gtR8fVhhZz3Fcv6g@aws-1-us-east-1.pooler.supabase.com:6543/postgres
```

---

## 11. Implementation Steps

### Phase 1: Setup & Configuration (Day 1)
1. ✅ Add `supabase` to `pyproject.toml` dependencies
2. ✅ Create `SupabaseSettings` in `omoi_os/config.py`
3. ✅ Add environment variables to `.env`
4. ✅ Create `SupabaseAuthService` in `omoi_os/services/supabase_auth.py`
5. ✅ Test Supabase client connection

### Phase 2: Database Schema (Day 1-2)
1. ✅ Create `User` model in `omoi_os/models/user.py`
2. ✅ Create Alembic migration for `public.users` table
3. ✅ Add replication triggers and functions
4. ✅ Add RLS policies
5. ✅ Run migration and verify trigger works

### Phase 3: Authentication Middleware (Day 2)
1. ✅ Create `get_current_user` dependency in `omoi_os/api/dependencies.py`
2. ✅ Create `get_current_user_optional` for optional auth
3. ✅ Create `require_role` dependency factory
4. ✅ Test JWT verification

### Phase 4: Auth API Routes (Day 2-3)
1. ✅ Create `omoi_os/api/routes/auth.py`
2. ✅ Implement `/auth/signup` endpoint
3. ✅ Implement `/auth/signin` endpoint
4. ✅ Implement `/auth/me` endpoint
5. ✅ Implement `/auth/signout` endpoint
6. ✅ Register routes in `main.py`

### Phase 5: Integration (Day 3)
1. ✅ Protect existing routes (Projects, Commits, GitHub)
2. ✅ Add user context to protected endpoints
3. ✅ Update Project model to include `created_by_user_id`
4. ✅ Test end-to-end authentication flow

### Phase 6: Testing & Documentation (Day 3-4)
1. ✅ Write unit tests for auth service
2. ✅ Write integration tests for auth endpoints
3. ✅ Test user replication trigger
4. ✅ Document authentication flow
5. ✅ Update API documentation

---

## 12. Security Considerations

### 12.1 JWT Token Verification
- ✅ Verify token signature using Supabase JWT secret
- ✅ Check token expiration
- ✅ Validate token issuer (Supabase project)
- ✅ Handle token refresh flow

### 12.2 Row Level Security
- ✅ Enable RLS on all user-accessible tables
- ✅ Create policies for user data access
- ✅ Service role bypass for backend operations

### 12.3 API Key Management
- ✅ Never expose service role key in frontend
- ✅ Use anon key for client-side operations
- ✅ Store keys in environment variables
- ✅ Rotate keys periodically

### 12.4 Password Security
- ✅ Supabase handles password hashing (bcrypt)
- ✅ Enforce password policies via Supabase settings
- ✅ Support password reset flow

---

## 13. Testing Strategy

### 13.1 Unit Tests
- Test JWT verification
- Test user creation
- Test user lookup
- Test role checking

### 13.2 Integration Tests
- Test signup flow
- Test signin flow
- Test protected endpoints
- Test user replication trigger

### 13.3 E2E Tests
- Test complete auth flow (signup → signin → protected endpoint)
- Test token refresh
- Test role-based access

---

## 14. Migration Checklist

- [ ] Add `supabase` dependency to `pyproject.toml`
- [ ] Create `SupabaseSettings` in config
- [ ] Add environment variables
- [ ] Create `User` model
- [ ] Create Alembic migration
- [ ] Run migration on Supabase database
- [ ] Verify trigger replication works
- [ ] Create `SupabaseAuthService`
- [ ] Create auth dependencies
- [ ] Create auth routes
- [ ] Register routes in `main.py`
- [ ] Protect existing routes
- [ ] Test authentication flow
- [ ] Update documentation

---

## 15. Next Steps After Implementation

1. **Frontend Integration**: Update frontend to use Supabase client for auth
2. **User Profile Management**: Add profile update endpoints
3. **Role Management**: Add admin endpoints for role assignment
4. **OAuth Integration**: Add GitHub/Google OAuth via Supabase
5. **Password Reset**: Implement password reset flow
6. **Email Verification**: Handle email confirmation flow
7. **Session Management**: Add session tracking and management

---

## 16. Example Usage

### 16.1 Protected Endpoint

```python
from omoi_os.api.dependencies import get_current_user
from omoi_os.models.user import User

@router.post("/projects")
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),  # Requires auth
    db: DatabaseService = Depends(get_db_service),
):
    """Create project - requires authentication."""
    # current_user.id, current_user.email, current_user.role available
    project = Project(
        name=project_data.name,
        # ... other fields ...
    )
    # Could add: project.created_by_user_id = current_user.id
    return project
```

### 16.2 Role-Based Endpoint

```python
from omoi_os.api.dependencies import require_role

@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(require_role(["admin", "project_manager"])),
    db: DatabaseService = Depends(get_db_service),
):
    """Delete project - requires admin or project_manager role."""
    # Only admins and project managers can access this
```

### 16.3 Optional Auth Endpoint

```python
from omoi_os.api.dependencies import get_current_user_optional

@router.get("/public-data")
async def get_data(
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Public endpoint with optional user context."""
    if current_user:
        return {"data": "personalized", "user": current_user.email}
    return {"data": "public"}
```

---

## 17. Troubleshooting

### Common Issues

1. **Trigger not firing**: Check trigger exists and is enabled
2. **JWT verification fails**: Verify Supabase URL and keys are correct
3. **User not found**: Check if user exists in `auth.users` and trigger ran
4. **RLS blocking queries**: Ensure service role key is used for backend operations
5. **Connection issues**: Verify database connection string and network access

---

## Conclusion

This plan provides a complete roadmap for integrating Supabase authentication into OmoiOS. The key components are:

1. **Database replication** via triggers (automatic sync)
2. **Supabase Python SDK** for JWT verification and user management
3. **FastAPI dependencies** for route protection
4. **User model** in public schema for application use
5. **Auth API routes** for signup/signin
6. **Role-based authorization** for fine-grained access control

The implementation follows Supabase best practices and integrates seamlessly with the existing FastAPI architecture.

