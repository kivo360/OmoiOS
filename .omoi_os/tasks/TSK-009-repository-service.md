---
id: TSK-009
title: Implement RepositoryService class
created: 2026-01-09
status: pending
priority: CRITICAL
type: implementation
parent_ticket: TKT-007
estimate: M
dependencies:
  depends_on: []
  blocks:
    - TSK-010
    - TSK-011
    - TSK-012
---

# TSK-009: Implement RepositoryService class

## Objective

Create the core `RepositoryService` class that handles all GitHub repository operations: listing owners, checking availability, and creating repositories.

## Context

This is the foundation for the create-repository feature. All API routes and other services will depend on this class.

## Deliverables

- [ ] `backend/omoi_os/services/repository_service.py` - Main service class
- [ ] `backend/omoi_os/models/github.py` - Pydantic models for requests/responses

## Implementation Notes

```python
# backend/omoi_os/services/repository_service.py

import httpx
from typing import Optional, List
from omoi_os.models.github import GitHubOwner, CreateRepositoryRequest

class RepositoryService:
    """Service for GitHub repository operations."""

    GITHUB_API_BASE = "https://api.github.com"
    API_VERSION = "2022-11-28"

    def __init__(self, github_token: str):
        self.github_token = github_token
        self.client = httpx.AsyncClient(
            base_url=self.GITHUB_API_BASE,
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": self.API_VERSION
            },
            timeout=30.0
        )

    async def list_owners(self) -> List[GitHubOwner]:
        """List accounts/orgs user can create repos in."""
        # Get authenticated user first
        user_resp = await self.client.get("/user")
        user_resp.raise_for_status()
        user = user_resp.json()

        owners = [GitHubOwner(
            login=user["login"],
            id=user["id"],
            type="User",
            avatar_url=user.get("avatar_url")
        )]

        # Get organizations user belongs to
        orgs_resp = await self.client.get("/user/orgs")
        orgs_resp.raise_for_status()

        for org in orgs_resp.json():
            # Check membership to see if user can create repos
            owners.append(GitHubOwner(
                login=org["login"],
                id=org["id"],
                type="Organization",
                avatar_url=org.get("avatar_url")
            ))

        return owners

    async def check_availability(
        self, owner: str, name: str
    ) -> tuple[bool, Optional[str]]:
        """Check if repo name is available. Returns (available, suggestion)."""
        resp = await self.client.get(f"/repos/{owner}/{name}")

        if resp.status_code == 404:
            return True, None
        elif resp.status_code == 200:
            # Name taken, suggest alternative
            for i in range(2, 10):
                alt_name = f"{name}-{i}"
                alt_resp = await self.client.get(f"/repos/{owner}/{alt_name}")
                if alt_resp.status_code == 404:
                    return False, alt_name
            return False, None
        else:
            resp.raise_for_status()

    async def create_repository(
        self, request: CreateRepositoryRequest, is_org: bool = False
    ) -> dict:
        """Create a new GitHub repository."""
        payload = {
            "name": request.name,
            "description": request.description or "",
            "private": request.visibility == "private",
            "auto_init": True,
        }

        url = f"/orgs/{request.owner}/repos" if is_org else "/user/repos"

        resp = await self.client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
```

```python
# backend/omoi_os/models/github.py

from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum

class RepoVisibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"

class RepoTemplate(str, Enum):
    EMPTY = "empty"
    NEXTJS = "nextjs"
    FASTAPI = "fastapi"
    REACT_VITE = "react-vite"
    PYTHON_PACKAGE = "python-package"

class GitHubOwner(BaseModel):
    login: str
    id: int
    type: Literal["User", "Organization"]
    avatar_url: Optional[str] = None

class CreateRepositoryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=350)
    visibility: RepoVisibility = RepoVisibility.PRIVATE
    owner: str
    template: RepoTemplate = RepoTemplate.EMPTY
    auto_scaffold: bool = True
    feature_description: Optional[str] = None

class CreateRepositoryResponse(BaseModel):
    id: int
    name: str
    full_name: str
    html_url: str
    clone_url: str
    default_branch: str
    project_id: str
```

## Verification

```bash
# Run unit tests
uv run pytest tests/unit/services/test_repository_service.py -v
```

## Done When

- [ ] RepositoryService class implemented with all methods
- [ ] Pydantic models defined
- [ ] httpx client configured with proper headers
- [ ] Error handling for common GitHub API errors
- [ ] Type hints on all methods
