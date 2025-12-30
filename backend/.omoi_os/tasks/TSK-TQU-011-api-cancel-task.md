---
id: TSK-TQU-011
title: Implement DELETE /api/v1/tasks/{id} endpoint
parent_ticket: TKT-TQU-005
created: 2024-12-29
updated: 2024-12-29
status: pending
priority: HIGH
type: implementation
estimate: 1h
depends_on:
  - TSK-TQU-007
---

# TSK-TQU-011: Implement DELETE /api/v1/tasks/{id} endpoint

## Description

Create endpoint to cancel pending or running tasks, terminating sandbox if necessary.

## Acceptance Criteria

- [ ] DELETE /api/v1/tasks/{id} cancels task
- [ ] Validates task belongs to user
- [ ] Returns 404 if task not found
- [ ] Returns 400 if task already completed
- [ ] Terminates sandbox if task is running
- [ ] Marks task as failed with "Cancelled by user"
- [ ] Requires authentication
- [ ] API test via httpx

## Implementation

```python
@router.delete("/{task_id}")
async def cancel_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    task_queue: TaskQueueService = Depends(get_task_queue),
    spawner: DaytonaSpawnerService = Depends(get_spawner),
):
    """Cancel a pending or running task."""
    task = await task_queue.get_task(task_id)

    if not task or task.user_id != user_id:
        raise HTTPException(404, detail="Task not found")

    if task.status == "completed":
        raise HTTPException(400, detail="Task already completed")

    # Kill sandbox if running
    if task.status == "running" and task.sandbox_id:
        try:
            await spawner.terminate(task.sandbox_id)
        except Exception as e:
            logger.warning(f"Failed to terminate sandbox: {e}")

    await task_queue.mark_failed(task_id, "Cancelled by user")

    return {"cancelled": True}
```

## Dependencies

- TSK-TQU-007: mark_failed with usage tracking
