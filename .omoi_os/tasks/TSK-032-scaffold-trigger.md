---
id: TSK-032
title: Add scaffold trigger to project creation flow
created: 2026-01-09
status: pending
priority: CRITICAL
type: implementation
parent_ticket: TKT-011
estimate: M
dependencies:
  depends_on:
    - TSK-012
  blocks: []
---

# TSK-032: Add scaffold trigger to project creation flow

## Objective

After a repository is created, trigger the scaffolding process if the user provided a feature description.

## Context

This connects the repo creation flow to the existing spec-driven workflow, enabling the full "idea to shipped code" experience.

## Deliverables

- [ ] Update project creation to trigger scaffolding
- [ ] Background task for async scaffolding

## Implementation Notes

```python
# Update backend/omoi_os/api/routes/github.py - create_repository endpoint

from omoi_os.tasks.scaffolding import trigger_scaffolding

@router.post("/repos", response_model=CreateRepositoryResponse, status_code=201)
async def create_repository(
    request: CreateRepositoryRequest,
    background_tasks: BackgroundTasks,
    # ... other deps
):
    # ... existing creation logic ...

    # After project created, trigger scaffolding if description provided
    if request.auto_scaffold and request.feature_description:
        background_tasks.add_task(
            trigger_scaffolding,
            project_id=str(project.id),
            feature_description=request.feature_description,
            github_token=github_token,
        )

    return CreateRepositoryResponse(...)
```

```python
# backend/omoi_os/tasks/scaffolding.py

async def trigger_scaffolding(
    project_id: str,
    feature_description: str,
    github_token: str,
):
    """Trigger scaffolding workflow for a new project.

    1. Generate spec from feature description
    2. Create tickets and tasks
    3. Queue tasks for agent execution
    """
    from omoi_os.services.spec_service import SpecService
    from omoi_os.services.workflow_service import WorkflowService

    # Generate spec
    spec_service = SpecService()
    spec = await spec_service.generate_from_description(
        project_id=project_id,
        description=feature_description,
    )

    # Create workflow with tickets/tasks
    workflow_service = WorkflowService()
    workflow = await workflow_service.create_from_spec(
        project_id=project_id,
        spec=spec,
    )

    # Queue for execution
    await workflow_service.start_workflow(workflow.id)
```

## Done When

- [ ] Scaffolding triggers after repo creation
- [ ] Runs as background task (non-blocking)
- [ ] Connects to existing spec generation
- [ ] Errors are logged and reported
- [ ] Can be monitored in dashboard
