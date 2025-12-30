---
id: TSK-TQU-009
title: Implement POST /api/v1/tasks endpoint
parent_ticket: TKT-TQU-005
created: 2024-12-29
updated: 2024-12-29
status: pending
priority: HIGH
type: implementation
estimate: 1h
depends_on:
  - TSK-TQU-005
---

# TSK-TQU-009: Implement POST /api/v1/tasks endpoint

## Description

Create endpoint for users to add tasks to the queue with limit checks.

## Acceptance Criteria

- [ ] POST /api/v1/tasks accepts TaskCreate body
- [ ] Validates pending count < 50
- [ ] Creates task with user_id from auth
- [ ] Returns TaskResponse with queue_position
- [ ] Returns 400 if too many pending tasks
- [ ] Requires authentication
- [ ] API test via httpx

## Implementation

```python
# api/routes/tasks.py

class TaskCreate(BaseModel):
    title: str
    description: str
    project_id: str
    priority: int = Field(default=3, ge=1, le=4)


@router.post("", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    user_id: str = Depends(get_current_user_id),
    task_queue: TaskQueueService = Depends(get_task_queue),
):
    """Create a new task and add to queue."""
    pending = await task_queue.get_pending_count(user_id)
    if pending >= 50:
        raise HTTPException(400, detail="Too many pending tasks (max 50)")

    new_task = await task_queue.create_task(
        user_id=user_id,
        project_id=task.project_id,
        title=task.title,
        description=task.description,
        priority=task.priority,
    )

    queue_position = await task_queue.get_queue_position(new_task.id)

    return TaskResponse(
        id=str(new_task.id),
        title=new_task.title,
        status=new_task.status,
        priority=new_task.priority,
        queue_position=queue_position,
        created_at=new_task.created_at,
    )
```

## Dependencies

- TSK-TQU-005: get_running_count (queue status check)
