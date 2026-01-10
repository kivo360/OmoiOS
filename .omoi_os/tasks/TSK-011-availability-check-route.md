---
id: TSK-011
title: Add repo availability check API route
created: 2026-01-09
status: pending
priority: HIGH
type: implementation
parent_ticket: TKT-007
estimate: S
dependencies:
  depends_on:
    - TSK-009
  blocks: []
---

# TSK-011: Add repo availability check API route

## Objective

Create the API endpoint that checks if a repository name is available and suggests alternatives if not.

## Context

The frontend will call this endpoint as the user types to show real-time availability feedback.

## Deliverables

- [ ] Route added to `backend/omoi_os/api/routes/github.py`

## Implementation Notes

```python
# Add to backend/omoi_os/api/routes/github.py

class CheckAvailabilityResponse(BaseModel):
    available: bool
    name: str
    owner: str
    suggestion: Optional[str] = None

@router.get("/repos/{owner}/{repo}/available", response_model=CheckAvailabilityResponse)
async def check_availability(
    owner: str,
    repo: str,
    github_token: str = Depends(get_github_token),
    current_user = Depends(get_current_user),
):
    """Check if repository name is available."""
    service = RepositoryService(github_token)
    try:
        available, suggestion = await service.check_availability(owner, repo)
        return CheckAvailabilityResponse(
            available=available,
            name=repo,
            owner=owner,
            suggestion=suggestion,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await service.close()
```

## Verification

```bash
# Test availability check
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/github/repos/kivo360/test-repo/available

# Expected: {"available": true, "name": "test-repo", "owner": "kivo360", "suggestion": null}
```

## Done When

- [ ] GET /api/v1/github/repos/{owner}/{repo}/available works
- [ ] Returns available=true if name is free
- [ ] Returns available=false with suggestion if taken
- [ ] Requires authentication
