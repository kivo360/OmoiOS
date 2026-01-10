---
id: TSK-012
title: Add create repository API route
created: 2026-01-09
status: pending
priority: CRITICAL
type: implementation
parent_ticket: TKT-007
estimate: M
dependencies:
  depends_on:
    - TSK-009
    - TSK-010
  blocks:
    - TSK-015
    - TSK-032
---

# TSK-012: Add create repository API route

## Objective

Create the main API endpoint for creating new GitHub repositories and linking them to OmoiOS projects.

## Context

This is the core endpoint that creates the repo, applies templates, creates the project, and optionally triggers scaffolding.

## Deliverables

- [ ] Route added to `backend/omoi_os/api/routes/github.py`
- [ ] Integration with ProjectService

## Implementation Notes

```python
# Add to backend/omoi_os/api/routes/github.py

from omoi_os.services.project_service import ProjectService
from omoi_os.models.github import CreateRepositoryRequest, CreateRepositoryResponse

@router.post("/repos", response_model=CreateRepositoryResponse, status_code=201)
async def create_repository(
    request: CreateRepositoryRequest,
    github_token: str = Depends(get_github_token),
    current_user = Depends(get_current_user),
    db = Depends(get_db),
):
    """Create a new GitHub repository and link to OmoiOS project."""
    repo_service = RepositoryService(github_token)

    try:
        # 1. Determine if org or personal
        owners = await repo_service.list_owners()
        owner_info = next((o for o in owners if o.login == request.owner), None)
        if not owner_info:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot create repositories in {request.owner}"
            )

        is_org = owner_info.type == "Organization"

        # 2. Check availability first
        available, _ = await repo_service.check_availability(request.owner, request.name)
        if not available:
            raise HTTPException(
                status_code=400,
                detail=f"Repository '{request.name}' already exists"
            )

        # 3. Create the repository
        repo = await repo_service.create_repository(request, is_org)

        # 4. Create OmoiOS project
        project_service = ProjectService(db)
        project = await project_service.create_project(
            user_id=str(current_user.id),
            name=request.name,
            github_repo_url=repo["html_url"],
            github_repo_id=repo["id"],
            github_owner=request.owner,
            github_owner_type=owner_info.type.lower(),
            repo_created_by_omoios=True,
            repo_template_used=request.template.value,
        )

        return CreateRepositoryResponse(
            id=repo["id"],
            name=repo["name"],
            full_name=repo["full_name"],
            html_url=repo["html_url"],
            clone_url=repo["clone_url"],
            default_branch=repo["default_branch"],
            project_id=str(project.id),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await repo_service.close()
```

## Verification

```bash
# Test create repository
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-api", "owner": "kivo360", "visibility": "private"}' \
  http://localhost:8000/api/v1/github/repos
```

## Done When

- [ ] POST /api/v1/github/repos creates repository
- [ ] Repository created in correct account/org
- [ ] OmoiOS project created and linked
- [ ] Returns complete response with project_id
- [ ] Proper error handling for all failure cases
