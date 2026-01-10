---
id: TSK-021
title: Add delete repository API route
created: 2026-01-09
status: pending
priority: HIGH
type: implementation
parent_ticket: TKT-009
estimate: S
dependencies:
  depends_on:
    - TSK-019
  blocks: []
---

# TSK-021: Add delete repository API route

## Objective

Create the API endpoint for deleting GitHub repositories with confirmation.

## Deliverables

- [ ] Route added to `backend/omoi_os/api/routes/github.py`

## Implementation Notes

```python
# Add to backend/omoi_os/api/routes/github.py

from pydantic import BaseModel

class DeleteRepositoryRequest(BaseModel):
    confirm_name: str

class DeleteRepositoryResponse(BaseModel):
    message: str
    project_archived: bool

@router.delete("/repos/{owner}/{repo}", response_model=DeleteRepositoryResponse)
async def delete_repository(
    owner: str,
    repo: str,
    request: DeleteRepositoryRequest,
    github_token: str = Depends(get_github_token),
    current_user = Depends(get_current_user),
    db = Depends(get_db),
):
    """Delete a GitHub repository and archive the OmoiOS project."""

    # Verify confirmation
    if request.confirm_name != repo:
        raise HTTPException(
            status_code=400,
            detail="Confirmation name does not match repository name"
        )

    service = RepositoryService(github_token)

    try:
        # Attempt deletion
        await service.delete_repository(owner, repo)

        # Archive OmoiOS project
        project_service = ProjectService(db)
        project = await project_service.find_by_github_repo(owner, repo)
        if project:
            await project_service.archive_project(project.id)

        return DeleteRepositoryResponse(
            message=f"Repository '{owner}/{repo}' deleted successfully",
            project_archived=project is not None,
        )

    except PermissionError as e:
        if "delete_repo" in str(e):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "missing_scope",
                    "message": str(e),
                    "reauth_url": "/auth/github/reauthorize?scope=delete_repo"
                }
            )
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        await service.close()
```

## Done When

- [ ] DELETE /api/v1/github/repos/{owner}/{repo} works
- [ ] Requires confirmation name match
- [ ] Returns reauth URL if scope missing
- [ ] Archives associated OmoiOS project
- [ ] Tests pass
