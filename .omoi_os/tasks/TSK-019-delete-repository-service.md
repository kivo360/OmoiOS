---
id: TSK-019
title: Add delete method to RepositoryService
created: 2026-01-09
status: pending
priority: HIGH
type: implementation
parent_ticket: TKT-009
estimate: S
dependencies:
  depends_on:
    - TSK-009
  blocks:
    - TSK-021
---

# TSK-019: Add delete method to RepositoryService

## Objective

Add the delete_repository method to RepositoryService for deleting GitHub repositories.

## Deliverables

- [ ] Update `backend/omoi_os/services/repository_service.py`

## Implementation Notes

```python
# Add to RepositoryService class

async def delete_repository(self, owner: str, repo: str) -> bool:
    """Delete a GitHub repository.

    Raises:
        PermissionError: If token lacks delete_repo scope
    """
    resp = await self.client.delete(f"/repos/{owner}/{repo}")

    if resp.status_code == 204:
        return True
    elif resp.status_code == 403:
        scopes = await self.check_scopes()
        if "delete_repo" not in scopes:
            raise PermissionError(
                "GitHub token is missing 'delete_repo' scope. "
                "Please re-authorize with delete permissions."
            )
        raise PermissionError("Cannot delete repository - permission denied")
    elif resp.status_code == 404:
        raise ValueError(f"Repository {owner}/{repo} not found")
    else:
        resp.raise_for_status()

async def check_scopes(self) -> list[str]:
    """Check OAuth scopes of current token."""
    resp = await self.client.get("/user")
    resp.raise_for_status()
    scopes_header = resp.headers.get("X-OAuth-Scopes", "")
    return [s.strip() for s in scopes_header.split(",") if s.strip()]
```

## Done When

- [ ] delete_repository method added
- [ ] check_scopes method added
- [ ] Proper error handling for missing scope
- [ ] Unit tests for delete scenarios
