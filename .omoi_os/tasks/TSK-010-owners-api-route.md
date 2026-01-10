---
id: TSK-010
title: Add GitHub owner listing API route
created: 2026-01-09
status: pending
priority: HIGH
type: implementation
parent_ticket: TKT-007
estimate: S
dependencies:
  depends_on:
    - TSK-009
  blocks:
    - TSK-024
---

# TSK-010: Add GitHub owner listing API route

## Objective

Create the API endpoint that returns the list of GitHub accounts and organizations the user can create repositories in.

## Context

The frontend needs this to populate the owner selector dropdown. Personal account should always be first.

## Deliverables

- [ ] `backend/omoi_os/api/routes/github.py` - GitHub routes module
- [ ] Route registered in main app

## Implementation Notes

```python
# backend/omoi_os/api/routes/github.py

from fastapi import APIRouter, Depends, HTTPException
from omoi_os.services.repository_service import RepositoryService
from omoi_os.api.deps import get_current_user, get_github_token
from omoi_os.models.github import GitHubOwner
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/github", tags=["github"])

class ListOwnersResponse(BaseModel):
    owners: List[GitHubOwner]

@router.get("/owners", response_model=ListOwnersResponse)
async def list_owners(
    github_token: str = Depends(get_github_token),
    current_user = Depends(get_current_user),
):
    """List GitHub accounts and organizations user can create repos in."""
    service = RepositoryService(github_token)
    try:
        owners = await service.list_owners()
        return ListOwnersResponse(owners=owners)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await service.close()
```

```python
# Register in main.py or routes/__init__.py
from omoi_os.api.routes import github
app.include_router(github.router, prefix="/api/v1")
```

## Verification

```bash
# Test endpoint
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/github/owners
```

## Done When

- [ ] GET /api/v1/github/owners endpoint works
- [ ] Returns personal account + organizations
- [ ] Requires authentication
- [ ] Proper error handling
