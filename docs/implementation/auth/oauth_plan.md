# OAuth Implementation Plan

> **Goal**: Implement an extensible OAuth authentication system with generic provider architecture (Strategy Pattern), full GitHub OAuth with repository access, and agent tools for autonomous GitHub operations.

## Overview

This plan implements:
1. **Generic OAuth Provider System** - Strategy Pattern allowing any OAuth 2.0 provider
2. **GitHub OAuth** - With `repo` scope for full repository access
3. **GitHub API Service** - List repos, read files, create PRs
4. **Agent Tools** - Autonomous GitHub operations for agents

---

## Task Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PHASE 1: Foundation                          │
├─────────────────────────────────────────────────────────────────────┤
│  Task 1: Create OAuth Provider Base Classes (no deps)               │
│  Task 6: Update Config with OAuth Settings (no deps)                │
│  Task 13: Create Frontend OAuth Callback Page (no deps)             │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PHASE 2: Provider Implementations                 │
├─────────────────────────────────────────────────────────────────────┤
│  Task 2: GitHub Provider ─┐                                          │
│  Task 3: Google Provider  ├──▶ Task 5: Provider Registry            │
│  Task 4: GitLab Provider ─┘                                          │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PHASE 3: Core Services                          │
├─────────────────────────────────────────────────────────────────────┤
│  Task 7: OAuth Service (depends on Registry + Config)               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌─────────────────────────────┐   ┌─────────────────────────────────┐
│  Task 8: OAuth API Routes    │   │  Task 9: GitHub API Service      │
└─────────────────────────────┘   └─────────────────────────────────┘
            │                               │
            │                     ┌─────────┴─────────┐
            │                     ▼                   ▼
            │       ┌─────────────────────┐  ┌─────────────────────┐
            │       │ Task 10: GitHub     │  │ Task 12: GitHub     │
            │       │ Repository Routes   │  │ Tools for Agents    │
            │       └─────────────────────┘  └─────────────────────┘
            │                     │
            └──────────┬──────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     PHASE 4: Integration                             │
├─────────────────────────────────────────────────────────────────────┤
│  Task 11: Register New Routers in Main App                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Files Summary

### New Files to Create (10)

| File | Purpose |
|------|---------|
| `backend/omoi_os/services/oauth/__init__.py` | Provider registry and exports |
| `backend/omoi_os/services/oauth/base.py` | Base class + OAuthUserInfo dataclass |
| `backend/omoi_os/services/oauth/github.py` | GitHub OAuth provider |
| `backend/omoi_os/services/oauth/google.py` | Google OAuth provider |
| `backend/omoi_os/services/oauth/gitlab.py` | GitLab OAuth provider |
| `backend/omoi_os/services/oauth_service.py` | Main OAuth orchestration service |
| `backend/omoi_os/services/github_api.py` | GitHub API service for repo operations |
| `backend/omoi_os/api/routes/oauth.py` | OAuth API routes |
| `backend/omoi_os/api/routes/github_repos.py` | GitHub repository API routes |
| `backend/omoi_os/tools/github_tools.py` | Agent-friendly GitHub tools |

### Files to Modify (3)

| File | Change |
|------|--------|
| `backend/omoi_os/config.py` | Add OAuth settings to AuthSettings class |
| `backend/omoi_os/api/main.py` | Register oauth and github_repos routers |
| `backend/config/base.yaml` | Add OAuth configuration section |

### Frontend (1)

| File | Purpose |
|------|---------|
| `frontend/app/(auth)/callback/page.tsx` | OAuth redirect callback handler |

---

## Environment Variables

```bash
# Required for GitHub OAuth
AUTH_GITHUB_CLIENT_ID=your_github_client_id
AUTH_GITHUB_CLIENT_SECRET=your_github_client_secret

# Optional for other providers
AUTH_GOOGLE_CLIENT_ID=your_google_client_id
AUTH_GOOGLE_CLIENT_SECRET=your_google_client_secret
AUTH_GITLAB_CLIENT_ID=your_gitlab_client_id
AUTH_GITLAB_CLIENT_SECRET=your_gitlab_client_secret

# Redirect URI (frontend callback URL)
AUTH_OAUTH_REDIRECT_URI=http://localhost:3000/auth/callback
```

---

## Detailed Task Specifications

### Task 1: Create OAuth Provider Base Classes

**File**: `backend/omoi_os/services/oauth/base.py`

**Description**: Create the foundation for the extensible OAuth provider system using the Strategy Pattern.

**Implementation**:

```python
"""Base OAuth provider classes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlencode
import secrets

import httpx


@dataclass
class OAuthUserInfo:
    """Standardized user information from OAuth providers."""
    
    provider: str
    provider_user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    access_token: str = ""
    refresh_token: Optional[str] = None
    raw_data: dict = field(default_factory=dict)


class OAuthProvider(ABC):
    """Abstract base class for OAuth 2.0 providers."""
    
    name: str = "base"
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
    
    @property
    @abstractmethod
    def authorization_url(self) -> str:
        """OAuth authorization endpoint URL."""
        pass
    
    @property
    @abstractmethod
    def token_url(self) -> str:
        """OAuth token endpoint URL."""
        pass
    
    @property
    @abstractmethod
    def default_scopes(self) -> list[str]:
        """Default OAuth scopes to request."""
        pass
    
    def get_auth_url(
        self,
        state: Optional[str] = None,
        scopes: Optional[list[str]] = None,
    ) -> tuple[str, str]:
        """
        Generate OAuth authorization URL.
        
        Returns:
            Tuple of (authorization_url, state)
        """
        if state is None:
            state = secrets.token_urlsafe(32)
        
        if scopes is None:
            scopes = self.default_scopes
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "response_type": "code",
            **self._get_extra_auth_params(),
        }
        
        return f"{self.authorization_url}?{urlencode(params)}", state
    
    def _get_extra_auth_params(self) -> dict:
        """Override to add provider-specific auth parameters."""
        return {}
    
    @abstractmethod
    async def exchange_code(self, code: str) -> Optional[OAuthUserInfo]:
        """
        Exchange authorization code for user info.
        
        Args:
            code: Authorization code from OAuth callback
            
        Returns:
            OAuthUserInfo if successful, None otherwise
        """
        pass
    
    async def _fetch_token(self, code: str) -> Optional[dict]:
        """
        Exchange code for access token.
        
        Args:
            code: Authorization code
            
        Returns:
            Token response dict or None
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
            
            if response.status_code == 200:
                return response.json()
            
            return None
```

**Verification**: File created with `OAuthUserInfo` dataclass and `OAuthProvider` ABC. All abstract methods defined. Type hints present.

---

### Task 2: Implement GitHub OAuth Provider

**File**: `backend/omoi_os/services/oauth/github.py`

**Description**: GitHub OAuth provider with repository access scopes (`read:user`, `user:email`, `repo`, `read:org`).

**Implementation**:

```python
"""GitHub OAuth provider."""

from typing import Optional

import httpx

from .base import OAuthProvider, OAuthUserInfo


class GitHubProvider(OAuthProvider):
    """GitHub OAuth 2.0 provider with repository access."""
    
    name = "github"
    
    @property
    def authorization_url(self) -> str:
        return "https://github.com/login/oauth/authorize"
    
    @property
    def token_url(self) -> str:
        return "https://github.com/login/oauth/access_token"
    
    @property
    def default_scopes(self) -> list[str]:
        return [
            "read:user",    # Read user profile
            "user:email",   # Access email addresses
            "repo",         # Full control of private and public repos
            "read:org",     # Read org membership
        ]
    
    async def exchange_code(self, code: str) -> Optional[OAuthUserInfo]:
        """Exchange code for GitHub user info."""
        token_data = await self._fetch_token(code)
        if not token_data or "access_token" not in token_data:
            return None
        
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        
        async with httpx.AsyncClient() as client:
            # Fetch user profile
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }
            
            user_response = await client.get(
                "https://api.github.com/user",
                headers=headers,
            )
            
            if user_response.status_code != 200:
                return None
            
            user_data = user_response.json()
            
            # Get granted scopes from response headers
            granted_scopes = user_response.headers.get("X-OAuth-Scopes", "")
            
            # Fetch email if not in profile
            email = user_data.get("email")
            if not email:
                email_response = await client.get(
                    "https://api.github.com/user/emails",
                    headers=headers,
                )
                
                if email_response.status_code == 200:
                    emails = email_response.json()
                    # Find primary verified email
                    for e in emails:
                        if e.get("primary") and e.get("verified"):
                            email = e.get("email")
                            break
                    # Fallback to first verified email
                    if not email:
                        for e in emails:
                            if e.get("verified"):
                                email = e.get("email")
                                break
            
            return OAuthUserInfo(
                provider=self.name,
                provider_user_id=str(user_data["id"]),
                email=email,
                name=user_data.get("name") or user_data.get("login"),
                avatar_url=user_data.get("avatar_url"),
                access_token=access_token,
                refresh_token=refresh_token,
                raw_data={
                    **user_data,
                    "granted_scopes": granted_scopes,
                    "login": user_data.get("login"),
                },
            )
```

**Verification**: `GitHubProvider` class with correct scopes. `exchange_code()` fetches user profile and email. Returns populated `OAuthUserInfo`.

---

### Task 3: Implement Google OAuth Provider

**File**: `backend/omoi_os/services/oauth/google.py`

**Description**: Google OAuth provider for optional Google authentication.

**Implementation**:

```python
"""Google OAuth provider."""

from typing import Optional

import httpx

from .base import OAuthProvider, OAuthUserInfo


class GoogleProvider(OAuthProvider):
    """Google OAuth 2.0 provider."""
    
    name = "google"
    
    @property
    def authorization_url(self) -> str:
        return "https://accounts.google.com/o/oauth2/v2/auth"
    
    @property
    def token_url(self) -> str:
        return "https://oauth2.googleapis.com/token"
    
    @property
    def default_scopes(self) -> list[str]:
        return [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ]
    
    def _get_extra_auth_params(self) -> dict:
        """Request offline access for refresh token."""
        return {
            "access_type": "offline",
            "prompt": "consent",
        }
    
    async def exchange_code(self, code: str) -> Optional[OAuthUserInfo]:
        """Exchange code for Google user info."""
        token_data = await self._fetch_token(code)
        if not token_data or "access_token" not in token_data:
            return None
        
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        
        async with httpx.AsyncClient() as client:
            # Fetch user info
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code != 200:
                return None
            
            user_data = response.json()
            
            return OAuthUserInfo(
                provider=self.name,
                provider_user_id=user_data["id"],
                email=user_data.get("email"),
                name=user_data.get("name"),
                avatar_url=user_data.get("picture"),
                access_token=access_token,
                refresh_token=refresh_token,
                raw_data=user_data,
            )
```

**Verification**: `GoogleProvider` with correct endpoints and scopes. Returns valid `OAuthUserInfo`.

---

### Task 4: Implement GitLab OAuth Provider

**File**: `backend/omoi_os/services/oauth/gitlab.py`

**Description**: GitLab OAuth provider with support for custom GitLab instances.

**Implementation**:

```python
"""GitLab OAuth provider."""

from typing import Optional

import httpx

from .base import OAuthProvider, OAuthUserInfo


class GitLabProvider(OAuthProvider):
    """GitLab OAuth 2.0 provider with custom instance support."""
    
    name = "gitlab"
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        base_url: str = "https://gitlab.com",
    ):
        super().__init__(client_id, client_secret, redirect_uri)
        self.base_url = base_url.rstrip("/")
    
    @property
    def authorization_url(self) -> str:
        return f"{self.base_url}/oauth/authorize"
    
    @property
    def token_url(self) -> str:
        return f"{self.base_url}/oauth/token"
    
    @property
    def default_scopes(self) -> list[str]:
        return ["read_user", "email"]
    
    async def exchange_code(self, code: str) -> Optional[OAuthUserInfo]:
        """Exchange code for GitLab user info."""
        token_data = await self._fetch_token(code)
        if not token_data or "access_token" not in token_data:
            return None
        
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        
        async with httpx.AsyncClient() as client:
            # Fetch user info
            response = await client.get(
                f"{self.base_url}/api/v4/user",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code != 200:
                return None
            
            user_data = response.json()
            
            return OAuthUserInfo(
                provider=self.name,
                provider_user_id=str(user_data["id"]),
                email=user_data.get("email"),
                name=user_data.get("name") or user_data.get("username"),
                avatar_url=user_data.get("avatar_url"),
                access_token=access_token,
                refresh_token=refresh_token,
                raw_data=user_data,
            )
```

**Verification**: `GitLabProvider` with configurable `base_url`. Works for gitlab.com and self-hosted.

---

### Task 5: Create OAuth Provider Registry

**File**: `backend/omoi_os/services/oauth/__init__.py`

**Description**: Provider registry that maps names to implementations.

**Implementation**:

```python
"""OAuth provider registry and exports."""

from typing import Optional, Type

from .base import OAuthProvider, OAuthUserInfo
from .github import GitHubProvider
from .google import GoogleProvider
from .gitlab import GitLabProvider


# Provider registry
PROVIDERS: dict[str, Type[OAuthProvider]] = {
    "github": GitHubProvider,
    "google": GoogleProvider,
    "gitlab": GitLabProvider,
}


def get_provider(
    name: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    **kwargs,
) -> Optional[OAuthProvider]:
    """
    Get an OAuth provider instance by name.
    
    Args:
        name: Provider name (github, google, gitlab)
        client_id: OAuth client ID
        client_secret: OAuth client secret
        redirect_uri: OAuth redirect URI
        **kwargs: Additional provider-specific arguments
        
    Returns:
        Provider instance or None if not found
    """
    provider_class = PROVIDERS.get(name.lower())
    if provider_class is None:
        return None
    
    return provider_class(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        **kwargs,
    )


def list_providers() -> list[str]:
    """Get list of registered provider names."""
    return list(PROVIDERS.keys())


def register_provider(name: str, provider_class: Type[OAuthProvider]) -> None:
    """Register a new OAuth provider."""
    PROVIDERS[name.lower()] = provider_class


__all__ = [
    "OAuthProvider",
    "OAuthUserInfo",
    "GitHubProvider",
    "GoogleProvider",
    "GitLabProvider",
    "PROVIDERS",
    "get_provider",
    "list_providers",
    "register_provider",
]
```

**Verification**: Registry exports all providers. `get_provider()` returns correct instance. `list_providers()` returns all names.

---

### Task 6: Update Config with OAuth Settings

**File**: `backend/omoi_os/config.py` (MODIFY)

**Description**: Add OAuth configuration to `AuthSettings` class.

**Changes to add inside AuthSettings class**:

```python
# Add these fields to the AuthSettings class:

# OAuth provider credentials
github_client_id: Optional[str] = None
github_client_secret: Optional[str] = None
google_client_id: Optional[str] = None
google_client_secret: Optional[str] = None
gitlab_client_id: Optional[str] = None
gitlab_client_secret: Optional[str] = None
gitlab_base_url: str = "https://gitlab.com"

# OAuth redirect URI
oauth_redirect_uri: str = "http://localhost:3000/auth/callback"

def get_provider_config(self, provider: str) -> Optional[dict]:
    """Get OAuth config for a provider."""
    configs = {
        "github": {
            "client_id": self.github_client_id,
            "client_secret": self.github_client_secret,
        },
        "google": {
            "client_id": self.google_client_id,
            "client_secret": self.google_client_secret,
        },
        "gitlab": {
            "client_id": self.gitlab_client_id,
            "client_secret": self.gitlab_client_secret,
            "base_url": self.gitlab_base_url,
        },
    }
    config = configs.get(provider.lower())
    if config and config.get("client_id") and config.get("client_secret"):
        return config
    return None
```

**File**: `backend/config/base.yaml` (MODIFY)

**Add under `auth:` section**:

```yaml
auth:
  # ... existing settings ...
  
  # OAuth provider credentials
  github_client_id: null
  github_client_secret: null
  google_client_id: null
  google_client_secret: null
  gitlab_client_id: null
  gitlab_client_secret: null
  gitlab_base_url: https://gitlab.com
  
  # OAuth redirect URI
  oauth_redirect_uri: http://localhost:3000/auth/callback
```

**Verification**: `AuthSettings` has all OAuth fields. `get_provider_config()` returns correct config.

---

### Task 7: Implement OAuth Service

**File**: `backend/omoi_os/services/oauth_service.py`

**Description**: Main OAuth service coordinating providers and user management.

**Implementation**:

```python
"""OAuth service for managing authentication flows."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select

from omoi_os.config import get_app_settings
from omoi_os.models.user import User
from omoi_os.services.database import DatabaseService
from omoi_os.services.oauth import get_provider, list_providers, OAuthUserInfo


# In-memory state storage (use Redis in production)
_oauth_states: dict[str, str] = {}


class OAuthService:
    """Service for OAuth authentication flows."""
    
    def __init__(self, db: DatabaseService):
        self.db = db
        self.settings = get_app_settings().auth
    
    def get_available_providers(self) -> list[dict]:
        """Get list of configured OAuth providers."""
        providers = []
        for name in list_providers():
            config = self.settings.get_provider_config(name)
            providers.append({
                "name": name,
                "enabled": config is not None,
            })
        return providers
    
    def get_auth_url(self, provider_name: str) -> tuple[str, str]:
        """
        Get OAuth authorization URL for a provider.
        
        Args:
            provider_name: Name of the OAuth provider
            
        Returns:
            Tuple of (auth_url, state)
            
        Raises:
            ValueError: If provider not configured
        """
        config = self.settings.get_provider_config(provider_name)
        if not config:
            raise ValueError(f"Provider '{provider_name}' not configured")
        
        provider = get_provider(
            name=provider_name,
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            redirect_uri=f"{self.settings.oauth_redirect_uri.rsplit('/', 1)[0]}/api/v1/auth/oauth/{provider_name}/callback",
            **{k: v for k, v in config.items() if k not in ("client_id", "client_secret")},
        )
        
        auth_url, state = provider.get_auth_url()
        
        # Store state for verification
        _oauth_states[state] = provider_name
        
        return auth_url, state
    
    def verify_state(self, state: str, provider_name: str) -> bool:
        """Verify OAuth state parameter."""
        stored_provider = _oauth_states.pop(state, None)
        return stored_provider == provider_name
    
    async def handle_callback(
        self,
        provider_name: str,
        code: str,
    ) -> Optional[OAuthUserInfo]:
        """
        Handle OAuth callback and exchange code for user info.
        
        Args:
            provider_name: Name of the OAuth provider
            code: Authorization code from callback
            
        Returns:
            OAuthUserInfo if successful, None otherwise
        """
        config = self.settings.get_provider_config(provider_name)
        if not config:
            return None
        
        provider = get_provider(
            name=provider_name,
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            redirect_uri=f"{self.settings.oauth_redirect_uri.rsplit('/', 1)[0]}/api/v1/auth/oauth/{provider_name}/callback",
            **{k: v for k, v in config.items() if k not in ("client_id", "client_secret")},
        )
        
        return await provider.exchange_code(code)
    
    def get_or_create_user(self, oauth_info: OAuthUserInfo) -> User:
        """
        Get existing user or create new one from OAuth info.
        
        Stores OAuth tokens in user.attributes.
        
        Args:
            oauth_info: User info from OAuth provider
            
        Returns:
            User instance
        """
        with self.db.get_session() as session:
            # Try to find by provider user ID
            provider_key = f"{oauth_info.provider}_user_id"
            
            # First check if user exists with this OAuth ID
            users = session.execute(
                select(User).where(User.email == oauth_info.email)
            ).scalars().all()
            
            user = None
            for u in users:
                attrs = u.attributes or {}
                if attrs.get(provider_key) == oauth_info.provider_user_id:
                    user = u
                    break
            
            # If no user with OAuth ID, try by email
            if not user and oauth_info.email:
                user = session.execute(
                    select(User).where(User.email == oauth_info.email)
                ).scalar_one_or_none()
            
            if user:
                # Update existing user
                attrs = user.attributes or {}
                attrs[f"{oauth_info.provider}_user_id"] = oauth_info.provider_user_id
                attrs[f"{oauth_info.provider}_access_token"] = oauth_info.access_token
                if oauth_info.refresh_token:
                    attrs[f"{oauth_info.provider}_refresh_token"] = oauth_info.refresh_token
                if oauth_info.raw_data.get("login"):
                    attrs[f"{oauth_info.provider}_username"] = oauth_info.raw_data["login"]
                user.attributes = attrs
                
                # Update profile if empty
                if not user.full_name and oauth_info.name:
                    user.full_name = oauth_info.name
                if not user.avatar_url and oauth_info.avatar_url:
                    user.avatar_url = oauth_info.avatar_url
            else:
                # Create new user
                user = User(
                    email=oauth_info.email,
                    full_name=oauth_info.name,
                    avatar_url=oauth_info.avatar_url,
                    is_active=True,
                    email_verified=True,  # OAuth emails are verified
                    attributes={
                        f"{oauth_info.provider}_user_id": oauth_info.provider_user_id,
                        f"{oauth_info.provider}_access_token": oauth_info.access_token,
                        f"{oauth_info.provider}_refresh_token": oauth_info.refresh_token,
                        f"{oauth_info.provider}_username": oauth_info.raw_data.get("login"),
                    },
                )
                session.add(user)
            
            session.commit()
            session.refresh(user)
            
            return user
```

**Verification**: `OAuthService` implemented with all methods. Uses provider registry. Tokens stored in attributes.

---

### Task 8: Create OAuth API Routes

**File**: `backend/omoi_os/api/routes/oauth.py`

**Description**: FastAPI routes for OAuth flows.

**Implementation**:

```python
"""OAuth API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from omoi_os.api.dependencies import get_db_service
from omoi_os.config import get_app_settings
from omoi_os.services.auth_service import AuthService
from omoi_os.services.database import DatabaseService
from omoi_os.services.oauth_service import OAuthService


router = APIRouter()


class ProviderInfo(BaseModel):
    """OAuth provider info."""
    name: str
    enabled: bool


class ProvidersResponse(BaseModel):
    """List of OAuth providers."""
    providers: list[ProviderInfo]


def get_oauth_service(
    db: DatabaseService = Depends(get_db_service),
) -> OAuthService:
    """Get OAuth service instance."""
    return OAuthService(db)


def get_auth_service(
    db: DatabaseService = Depends(get_db_service),
) -> AuthService:
    """Get auth service instance."""
    return AuthService(db)


@router.get("/oauth/providers", response_model=ProvidersResponse)
async def list_providers(
    oauth_service: OAuthService = Depends(get_oauth_service),
):
    """List available OAuth providers."""
    providers = oauth_service.get_available_providers()
    return ProvidersResponse(
        providers=[ProviderInfo(**p) for p in providers]
    )


@router.get("/oauth/{provider}")
async def start_oauth(
    provider: str,
    oauth_service: OAuthService = Depends(get_oauth_service),
):
    """
    Start OAuth flow for a provider.
    
    Redirects user to provider's authorization page.
    """
    try:
        auth_url, state = oauth_service.get_auth_url(provider)
        return RedirectResponse(url=auth_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    error: str = Query(None),
    oauth_service: OAuthService = Depends(get_oauth_service),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Handle OAuth callback.
    
    Exchanges code for user info, creates/updates user, and redirects to frontend.
    """
    settings = get_app_settings().auth
    frontend_url = settings.oauth_redirect_uri
    
    # Handle OAuth error
    if error:
        return RedirectResponse(url=f"{frontend_url}?error={error}")
    
    # Verify state
    if not oauth_service.verify_state(state, provider):
        return RedirectResponse(url=f"{frontend_url}?error=invalid_state")
    
    # Exchange code for user info
    oauth_info = await oauth_service.handle_callback(provider, code)
    if not oauth_info:
        return RedirectResponse(url=f"{frontend_url}?error=oauth_failed")
    
    # Get or create user
    user = oauth_service.get_or_create_user(oauth_info)
    
    # Generate JWT tokens
    access_token = auth_service.create_access_token(user.id)
    refresh_token = auth_service.create_refresh_token(user.id)
    
    # Redirect to frontend with tokens
    redirect_url = (
        f"{frontend_url}"
        f"?access_token={access_token}"
        f"&refresh_token={refresh_token}"
        f"&provider={provider}"
    )
    
    return RedirectResponse(url=redirect_url)
```

**Verification**: All routes implemented. OAuth flow works end-to-end. JWT tokens generated.

---

### Task 9: Implement GitHub API Service

**File**: `backend/omoi_os/services/github_api.py`

**Description**: GitHub API service for repository operations.

**Implementation**:

```python
"""GitHub API service for repository operations."""

from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID
import base64

import httpx
from sqlalchemy import select

from omoi_os.models.user import User
from omoi_os.services.database import DatabaseService


@dataclass
class GitHubRepo:
    """GitHub repository info."""
    id: int
    name: str
    full_name: str
    owner: str
    description: Optional[str]
    private: bool
    html_url: str
    clone_url: str
    default_branch: str
    language: Optional[str]
    stargazers_count: int
    forks_count: int


@dataclass
class GitHubBranch:
    """GitHub branch info."""
    name: str
    sha: str
    protected: bool


@dataclass
class GitHubFile:
    """GitHub file info."""
    name: str
    path: str
    sha: str
    size: int
    type: str  # "file" or "dir"
    content: Optional[str] = None  # Base64 decoded content
    encoding: Optional[str] = None


class GitHubAPIService:
    """Service for GitHub API operations using user OAuth tokens."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, db: DatabaseService):
        self.db = db
    
    def _get_user_token(self, user: User) -> Optional[str]:
        """Get GitHub access token from user attributes."""
        attrs = user.attributes or {}
        return attrs.get("github_access_token")
    
    async def _get_user_token_by_id(self, user_id: UUID) -> Optional[str]:
        """Get GitHub access token by user ID."""
        with self.db.get_session() as session:
            user = session.get(User, user_id)
            if user:
                return self._get_user_token(user)
        return None
    
    def _headers(self, token: str) -> dict:
        """Get request headers with auth token."""
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    
    async def list_user_repos(
        self,
        user_id: UUID,
        visibility: str = "all",
        sort: str = "updated",
        per_page: int = 30,
        page: int = 1,
    ) -> List[GitHubRepo]:
        """
        List repositories for the authenticated user.
        
        Args:
            user_id: User ID
            visibility: all, public, or private
            sort: created, updated, pushed, full_name
            per_page: Results per page (max 100)
            page: Page number
        """
        token = await self._get_user_token_by_id(user_id)
        if not token:
            return []
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/user/repos",
                headers=self._headers(token),
                params={
                    "visibility": visibility,
                    "sort": sort,
                    "per_page": per_page,
                    "page": page,
                },
            )
            
            if response.status_code != 200:
                return []
            
            repos = response.json()
            return [
                GitHubRepo(
                    id=r["id"],
                    name=r["name"],
                    full_name=r["full_name"],
                    owner=r["owner"]["login"],
                    description=r.get("description"),
                    private=r["private"],
                    html_url=r["html_url"],
                    clone_url=r["clone_url"],
                    default_branch=r.get("default_branch", "main"),
                    language=r.get("language"),
                    stargazers_count=r.get("stargazers_count", 0),
                    forks_count=r.get("forks_count", 0),
                )
                for r in repos
            ]
    
    async def get_repo(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
    ) -> Optional[GitHubRepo]:
        """Get repository details."""
        token = await self._get_user_token_by_id(user_id)
        if not token:
            return None
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}",
                headers=self._headers(token),
            )
            
            if response.status_code != 200:
                return None
            
            r = response.json()
            return GitHubRepo(
                id=r["id"],
                name=r["name"],
                full_name=r["full_name"],
                owner=r["owner"]["login"],
                description=r.get("description"),
                private=r["private"],
                html_url=r["html_url"],
                clone_url=r["clone_url"],
                default_branch=r.get("default_branch", "main"),
                language=r.get("language"),
                stargazers_count=r.get("stargazers_count", 0),
                forks_count=r.get("forks_count", 0),
            )
    
    async def list_branches(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        per_page: int = 30,
        page: int = 1,
    ) -> List[GitHubBranch]:
        """List repository branches."""
        token = await self._get_user_token_by_id(user_id)
        if not token:
            return []
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/branches",
                headers=self._headers(token),
                params={"per_page": per_page, "page": page},
            )
            
            if response.status_code != 200:
                return []
            
            branches = response.json()
            return [
                GitHubBranch(
                    name=b["name"],
                    sha=b["commit"]["sha"],
                    protected=b.get("protected", False),
                )
                for b in branches
            ]
    
    async def get_file_content(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        path: str,
        ref: Optional[str] = None,
    ) -> Optional[GitHubFile]:
        """Get file content from repository."""
        token = await self._get_user_token_by_id(user_id)
        if not token:
            return None
        
        params = {}
        if ref:
            params["ref"] = ref
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/contents/{path}",
                headers=self._headers(token),
                params=params,
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            # Handle file content
            content = None
            if data.get("content") and data.get("encoding") == "base64":
                content = base64.b64decode(data["content"]).decode("utf-8")
            
            return GitHubFile(
                name=data["name"],
                path=data["path"],
                sha=data["sha"],
                size=data.get("size", 0),
                type=data["type"],
                content=content,
                encoding=data.get("encoding"),
            )
    
    async def list_directory(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        path: str = "",
        ref: Optional[str] = None,
    ) -> List[dict]:
        """List directory contents."""
        token = await self._get_user_token_by_id(user_id)
        if not token:
            return []
        
        params = {}
        if ref:
            params["ref"] = ref
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/contents/{path}",
                headers=self._headers(token),
                params=params,
            )
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            
            # If single file, wrap in list
            if isinstance(data, dict):
                data = [data]
            
            return [
                {
                    "name": item["name"],
                    "path": item["path"],
                    "type": item["type"],
                    "size": item.get("size", 0),
                    "sha": item["sha"],
                }
                for item in data
            ]
    
    async def get_tree(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        tree_sha: str = "HEAD",
        recursive: bool = True,
    ) -> List[dict]:
        """Get repository file tree."""
        token = await self._get_user_token_by_id(user_id)
        if not token:
            return []
        
        async with httpx.AsyncClient() as client:
            params = {}
            if recursive:
                params["recursive"] = "1"
            
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/git/trees/{tree_sha}",
                headers=self._headers(token),
                params=params,
            )
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            return [
                {
                    "path": item["path"],
                    "type": item["type"],  # blob or tree
                    "sha": item["sha"],
                    "size": item.get("size"),
                }
                for item in data.get("tree", [])
            ]
    
    async def create_or_update_file(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: Optional[str] = None,
        sha: Optional[str] = None,
    ) -> dict:
        """Create or update a file in the repository."""
        token = await self._get_user_token_by_id(user_id)
        if not token:
            return {"error": "No GitHub token"}
        
        # Encode content to base64
        encoded_content = base64.b64encode(content.encode()).decode()
        
        data = {
            "message": message,
            "content": encoded_content,
        }
        
        if branch:
            data["branch"] = branch
        if sha:
            data["sha"] = sha  # Required for updates
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.BASE_URL}/repos/{owner}/{repo}/contents/{path}",
                headers=self._headers(token),
                json=data,
            )
            
            return response.json()
    
    async def create_branch(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        branch_name: str,
        from_sha: str,
    ) -> dict:
        """Create a new branch."""
        token = await self._get_user_token_by_id(user_id)
        if not token:
            return {"error": "No GitHub token"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/repos/{owner}/{repo}/git/refs",
                headers=self._headers(token),
                json={
                    "ref": f"refs/heads/{branch_name}",
                    "sha": from_sha,
                },
            )
            
            return response.json()
    
    async def create_pull_request(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: Optional[str] = None,
        draft: bool = False,
    ) -> dict:
        """Create a pull request."""
        token = await self._get_user_token_by_id(user_id)
        if not token:
            return {"error": "No GitHub token"}
        
        data = {
            "title": title,
            "head": head,
            "base": base,
            "draft": draft,
        }
        
        if body:
            data["body"] = body
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/repos/{owner}/{repo}/pulls",
                headers=self._headers(token),
                json=data,
            )
            
            return response.json()
```

**Verification**: All operations implemented. Uses user token from attributes. Proper error handling.

---

### Task 10: Create GitHub Repository API Routes

**File**: `backend/omoi_os/api/routes/github_repos.py`

**Description**: FastAPI routes for GitHub repository operations.

**Implementation**:

```python
"""GitHub repository API routes."""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from omoi_os.api.dependencies import get_db_service, get_current_user
from omoi_os.models.user import User
from omoi_os.services.database import DatabaseService
from omoi_os.services.github_api import GitHubAPIService, GitHubRepo, GitHubBranch, GitHubFile


router = APIRouter()


# Response models
class RepoResponse(BaseModel):
    id: int
    name: str
    full_name: str
    owner: str
    description: Optional[str]
    private: bool
    html_url: str
    clone_url: str
    default_branch: str
    language: Optional[str]
    stargazers_count: int
    forks_count: int


class BranchResponse(BaseModel):
    name: str
    sha: str
    protected: bool


class FileResponse(BaseModel):
    name: str
    path: str
    sha: str
    size: int
    type: str
    content: Optional[str] = None


class DirectoryItemResponse(BaseModel):
    name: str
    path: str
    type: str
    size: int
    sha: str


class TreeItemResponse(BaseModel):
    path: str
    type: str
    sha: str
    size: Optional[int] = None


def get_github_api_service(
    db: DatabaseService = Depends(get_db_service),
) -> GitHubAPIService:
    """Get GitHub API service instance."""
    return GitHubAPIService(db)


@router.get("/repos", response_model=List[RepoResponse])
async def list_repos(
    visibility: str = Query("all", regex="^(all|public|private)$"),
    sort: str = Query("updated", regex="^(created|updated|pushed|full_name)$"),
    per_page: int = Query(30, ge=1, le=100),
    page: int = Query(1, ge=1),
    current_user: User = Depends(get_current_user),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """List repositories for the authenticated user."""
    # Check if user has GitHub token
    if not (current_user.attributes or {}).get("github_access_token"):
        raise HTTPException(
            status_code=400,
            detail="GitHub not connected. Please authenticate with GitHub first.",
        )
    
    repos = await github_service.list_user_repos(
        user_id=current_user.id,
        visibility=visibility,
        sort=sort,
        per_page=per_page,
        page=page,
    )
    
    return [
        RepoResponse(
            id=r.id,
            name=r.name,
            full_name=r.full_name,
            owner=r.owner,
            description=r.description,
            private=r.private,
            html_url=r.html_url,
            clone_url=r.clone_url,
            default_branch=r.default_branch,
            language=r.language,
            stargazers_count=r.stargazers_count,
            forks_count=r.forks_count,
        )
        for r in repos
    ]


@router.get("/repos/{owner}/{repo}", response_model=RepoResponse)
async def get_repo(
    owner: str,
    repo: str,
    current_user: User = Depends(get_current_user),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """Get repository details."""
    result = await github_service.get_repo(
        user_id=current_user.id,
        owner=owner,
        repo=repo,
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    return RepoResponse(
        id=result.id,
        name=result.name,
        full_name=result.full_name,
        owner=result.owner,
        description=result.description,
        private=result.private,
        html_url=result.html_url,
        clone_url=result.clone_url,
        default_branch=result.default_branch,
        language=result.language,
        stargazers_count=result.stargazers_count,
        forks_count=result.forks_count,
    )


@router.get("/repos/{owner}/{repo}/branches", response_model=List[BranchResponse])
async def list_branches(
    owner: str,
    repo: str,
    per_page: int = Query(30, ge=1, le=100),
    page: int = Query(1, ge=1),
    current_user: User = Depends(get_current_user),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """List repository branches."""
    branches = await github_service.list_branches(
        user_id=current_user.id,
        owner=owner,
        repo=repo,
        per_page=per_page,
        page=page,
    )
    
    return [
        BranchResponse(name=b.name, sha=b.sha, protected=b.protected)
        for b in branches
    ]


@router.get("/repos/{owner}/{repo}/contents/{path:path}", response_model=FileResponse)
async def get_file_content(
    owner: str,
    repo: str,
    path: str,
    ref: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """Get file content from repository."""
    result = await github_service.get_file_content(
        user_id=current_user.id,
        owner=owner,
        repo=repo,
        path=path,
        ref=ref,
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        name=result.name,
        path=result.path,
        sha=result.sha,
        size=result.size,
        type=result.type,
        content=result.content,
    )


@router.get("/repos/{owner}/{repo}/directory", response_model=List[DirectoryItemResponse])
async def list_directory(
    owner: str,
    repo: str,
    path: str = Query(""),
    ref: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """List directory contents."""
    items = await github_service.list_directory(
        user_id=current_user.id,
        owner=owner,
        repo=repo,
        path=path,
        ref=ref,
    )
    
    return [DirectoryItemResponse(**item) for item in items]


@router.get("/repos/{owner}/{repo}/tree", response_model=List[TreeItemResponse])
async def get_tree(
    owner: str,
    repo: str,
    tree_sha: str = Query("HEAD"),
    recursive: bool = Query(True),
    current_user: User = Depends(get_current_user),
    github_service: GitHubAPIService = Depends(get_github_api_service),
):
    """Get repository file tree."""
    items = await github_service.get_tree(
        user_id=current_user.id,
        owner=owner,
        repo=repo,
        tree_sha=tree_sha,
        recursive=recursive,
    )
    
    return [TreeItemResponse(**item) for item in items]
```

**Verification**: All routes with authentication. Returns correct data structures. Error handling for edge cases.

---

### Task 11: Register New Routers in Main App

**File**: `backend/omoi_os/api/main.py` (MODIFY)

**Description**: Register the OAuth and GitHub repos routers.

**Changes**:

1. Add imports at the top with other route imports:
```python
from omoi_os.api.routes import oauth, github_repos
```

2. Register routers after the existing auth router (around line 856):
```python
# OAuth routes
app.include_router(oauth.router, prefix="/api/v1/auth", tags=["OAuth"])

# GitHub Repository routes (authenticated)
app.include_router(github_repos.router, prefix="/api/v1/github", tags=["GitHub Repos"])
```

**Verification**: Both routers registered. No conflicts. API docs show new endpoints.

---

### Task 12: Create GitHub Tools for Agents

**File**: `backend/omoi_os/tools/github_tools.py`

**Description**: Agent-friendly tools wrapping the GitHub API service.

**Implementation**:

```python
"""GitHub tools for agent operations.

These tools allow agents to interact with GitHub repositories
on behalf of users who have connected their GitHub accounts.
"""

from typing import Optional, List
from uuid import UUID

from omoi_os.services.database import DatabaseService
from omoi_os.services.github_api import GitHubAPIService


class GitHubTools:
    """
    Agent-friendly GitHub tools.
    
    These tools wrap the GitHubAPIService to provide simplified
    methods for common GitHub operations.
    
    Initialize with a user_id to bind all operations to that user's
    GitHub token.
    """
    
    def __init__(self, db: DatabaseService, user_id: UUID):
        """
        Initialize GitHub tools for a specific user.
        
        Args:
            db: Database service instance
            user_id: UUID of the user whose GitHub token to use
        """
        self.db = db
        self.user_id = user_id
        self._api = GitHubAPIService(db)
    
    async def list_repos(
        self,
        visibility: str = "all",
        limit: int = 30,
    ) -> List[dict]:
        """
        List repositories for the connected GitHub account.
        
        Args:
            visibility: Filter by visibility (all, public, private)
            limit: Maximum number of repos to return
            
        Returns:
            List of repository dictionaries with name, full_name,
            description, private, html_url, default_branch
        """
        repos = await self._api.list_user_repos(
            user_id=self.user_id,
            visibility=visibility,
            per_page=limit,
        )
        
        return [
            {
                "name": r.name,
                "full_name": r.full_name,
                "description": r.description,
                "private": r.private,
                "html_url": r.html_url,
                "default_branch": r.default_branch,
                "language": r.language,
            }
            for r in repos
        ]
    
    async def read_file(
        self,
        owner: str,
        repo: str,
        path: str,
        branch: Optional[str] = None,
    ) -> Optional[str]:
        """
        Read file content from a repository.
        
        Args:
            owner: Repository owner (username or org)
            repo: Repository name
            path: File path within the repository
            branch: Branch name (optional, defaults to default branch)
            
        Returns:
            File content as string, or None if not found
        """
        result = await self._api.get_file_content(
            user_id=self.user_id,
            owner=owner,
            repo=repo,
            path=path,
            ref=branch,
        )
        
        return result.content if result else None
    
    async def list_files(
        self,
        owner: str,
        repo: str,
        path: str = "",
        branch: Optional[str] = None,
    ) -> List[dict]:
        """
        List files in a repository directory.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: Directory path (empty for root)
            branch: Branch name (optional)
            
        Returns:
            List of file/directory dictionaries with name, path, type
        """
        items = await self._api.list_directory(
            user_id=self.user_id,
            owner=owner,
            repo=repo,
            path=path,
            ref=branch,
        )
        
        return [
            {
                "name": item["name"],
                "path": item["path"],
                "type": item["type"],
                "size": item.get("size", 0),
            }
            for item in items
        ]
    
    async def get_repo_tree(
        self,
        owner: str,
        repo: str,
        branch: Optional[str] = None,
    ) -> List[dict]:
        """
        Get full file tree for a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name (optional, defaults to HEAD)
            
        Returns:
            List of all files with path and type
        """
        tree_sha = branch or "HEAD"
        items = await self._api.get_tree(
            user_id=self.user_id,
            owner=owner,
            repo=repo,
            tree_sha=tree_sha,
            recursive=True,
        )
        
        return [
            {
                "path": item["path"],
                "type": "file" if item["type"] == "blob" else "dir",
                "size": item.get("size"),
            }
            for item in items
        ]
    
    async def write_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: Optional[str] = None,
    ) -> dict:
        """
        Create or update a file in a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            content: File content
            message: Commit message
            branch: Branch name (optional)
            
        Returns:
            Result dictionary with commit info
        """
        # Check if file exists to get SHA for update
        existing = await self._api.get_file_content(
            user_id=self.user_id,
            owner=owner,
            repo=repo,
            path=path,
            ref=branch,
        )
        
        sha = existing.sha if existing else None
        
        result = await self._api.create_or_update_file(
            user_id=self.user_id,
            owner=owner,
            repo=repo,
            path=path,
            content=content,
            message=message,
            branch=branch,
            sha=sha,
        )
        
        return result
    
    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head_branch: str,
        base_branch: str,
        body: Optional[str] = None,
    ) -> dict:
        """
        Create a pull request.
        
        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            head_branch: Source branch with changes
            base_branch: Target branch to merge into
            body: PR description (optional)
            
        Returns:
            PR info dictionary with number, html_url, state
        """
        result = await self._api.create_pull_request(
            user_id=self.user_id,
            owner=owner,
            repo=repo,
            title=title,
            head=head_branch,
            base=base_branch,
            body=body,
        )
        
        return {
            "number": result.get("number"),
            "html_url": result.get("html_url"),
            "state": result.get("state"),
            "title": result.get("title"),
        }
```

**Verification**: `GitHubTools` class with all methods. User ID bound at construction. Clean dict returns.

---

### Task 13: Create Frontend OAuth Callback Page

**File**: `frontend/app/(auth)/callback/page.tsx`

**Description**: Handle OAuth redirect and store tokens.

**Implementation**:

```tsx
'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/contexts/auth-context';

export default function OAuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState<string>('');

  useEffect(() => {
    const handleCallback = async () => {
      // Check for error
      const error = searchParams.get('error');
      if (error) {
        setStatus('error');
        setErrorMessage(error);
        setTimeout(() => router.push(`/login?error=${error}`), 2000);
        return;
      }

      // Get tokens from URL
      const accessToken = searchParams.get('access_token');
      const refreshToken = searchParams.get('refresh_token');
      const provider = searchParams.get('provider');

      if (!accessToken || !refreshToken) {
        setStatus('error');
        setErrorMessage('No tokens received');
        setTimeout(() => router.push('/login?error=no_tokens'), 2000);
        return;
      }

      try {
        // Store tokens
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);

        // Fetch user info and update auth context
        const response = await fetch('/api/v1/auth/me', {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        });

        if (response.ok) {
          const user = await response.json();
          login(user, accessToken);
          setStatus('success');
          
          // Redirect to main app
          setTimeout(() => router.push('/command'), 1000);
        } else {
          throw new Error('Failed to fetch user info');
        }
      } catch (err) {
        setStatus('error');
        setErrorMessage('Authentication failed');
        setTimeout(() => router.push('/login?error=auth_failed'), 2000);
      }
    };

    handleCallback();
  }, [searchParams, router, login]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="text-center">
        {status === 'loading' && (
          <>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Completing sign in...
            </h2>
          </>
        )}
        
        {status === 'success' && (
          <>
            <div className="text-green-500 text-5xl mb-4">✓</div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Sign in successful!
            </h2>
            <p className="text-gray-500 mt-2">Redirecting...</p>
          </>
        )}
        
        {status === 'error' && (
          <>
            <div className="text-red-500 text-5xl mb-4">✗</div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Sign in failed
            </h2>
            <p className="text-gray-500 mt-2">{errorMessage}</p>
            <p className="text-gray-400 text-sm mt-2">Redirecting to login...</p>
          </>
        )}
      </div>
    </div>
  );
}
```

**Verification**: Handles success and error cases. Tokens stored correctly. Proper redirects.

---

## Testing Checklist

### Unit Tests
- [ ] Provider URL generation for each provider
- [ ] OAuth state management
- [ ] User creation/update logic
- [ ] Token storage in user attributes

### Integration Tests
- [ ] OAuth callback handling (mocked providers)
- [ ] GitHub API service methods (mocked GitHub API)
- [ ] Full OAuth flow with mocked responses

### Manual Testing
1. Create GitHub OAuth App in GitHub Developer Settings
2. Set `AUTH_GITHUB_CLIENT_ID` and `AUTH_GITHUB_CLIENT_SECRET`
3. Test full login flow
4. Verify repository listing works
5. Test file reading

---

## Security Considerations

1. **Token Storage**: OAuth tokens stored in `user.attributes` JSONB field (encrypted at rest)
2. **State Parameter**: Random state prevents CSRF attacks
3. **Token Refresh**: Consider implementing token refresh for long-lived sessions
4. **Scope Validation**: Verify granted scopes match requested scopes
5. **Production**: Use Redis for state storage instead of in-memory dict

---

## Future Enhancements

1. **Token Refresh**: Implement automatic token refresh for expired tokens
2. **Webhook Events**: Add GitHub webhook handling for real-time updates
3. **Additional Providers**: Add Microsoft Azure AD, Bitbucket, etc.
4. **Rate Limiting**: Implement rate limit handling for GitHub API
5. **Caching**: Cache repository lists and file trees

---

## Quick Start

```bash
# 1. Set environment variables
export AUTH_GITHUB_CLIENT_ID=your_client_id
export AUTH_GITHUB_CLIENT_SECRET=your_client_secret
export AUTH_OAUTH_REDIRECT_URI=http://localhost:3000/auth/callback

# 2. Start backend
cd backend
uv run uvicorn omoi_os.api.main:app --reload

# 3. Start frontend
cd frontend
npm run dev

# 4. Test OAuth
# Navigate to http://localhost:3000/login
# Click "Sign in with GitHub"
```
