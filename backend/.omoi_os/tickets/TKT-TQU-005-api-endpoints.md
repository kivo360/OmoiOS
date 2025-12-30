---
id: TKT-TQU-005
title: API Endpoints
feature: task-queue-user-limits
created: 2024-12-29
updated: 2024-12-29
status: open
priority: HIGH
phase: PHASE_IMPLEMENTATION
type: feature
requirements:
  - REQ-TQU-API-001
  - REQ-TQU-QUEUE-004
  - REQ-TQU-SEC-001
  - REQ-TQU-SEC-002
linked_design: designs/task-queue-user-limits.md
estimate: 4h
depends_on:
  - TKT-TQU-003
---

# TKT-TQU-005: API Endpoints

## Summary

Create REST API endpoints for task management, queue status, and user limits.

## Acceptance Criteria

- [ ] POST /api/v1/tasks - Create task with limit checks
- [ ] GET /api/v1/tasks - List user's tasks with optional status filter
- [ ] DELETE /api/v1/tasks/{id} - Cancel pending/running task
- [ ] GET /api/v1/tasks/queue-status - Return QueueStatus
- [ ] POST /api/v1/tasks/{id}/complete - Sandbox callback for completion
- [ ] GET /api/v1/users/me/limits - Return UserLimits
- [ ] All endpoints require authentication
- [ ] Proper error responses (400, 403, 404)
- [ ] API tests via curl/httpx

## Technical Details

### New Endpoints

```python
# api/routes/tasks.py

@router.post("", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    user_id: str = Depends(get_current_user_id),
    task_queue: TaskQueueService = Depends(get_task_queue),
):
    """Create a new task and add to queue."""
    pending = await task_queue.get_pending_count(user_id)
    if pending >= 50:
        raise HTTPException(400, "Too many pending tasks (max 50)")
    # ... create task

@router.get("/queue-status")
async def get_queue_status(
    user_id: str = Depends(get_current_user_id),
    task_queue: TaskQueueService = Depends(get_task_queue),
    plan_service: PlanService = Depends(get_plan_service),
):
    """Get user's queue status and limits."""
    limits = await plan_service.get_limits(user_id)
    running = await task_queue.get_running_count(user_id)
    pending = await task_queue.get_pending_count(user_id)
    hours_used = await plan_service.get_monthly_hours_used(user_id)
    return QueueStatus(...)

@router.delete("/{task_id}")
async def cancel_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    task_queue: TaskQueueService = Depends(get_task_queue),
    spawner: DaytonaSpawnerService = Depends(get_spawner),
):
    """Cancel a pending or running task."""
    # Verify ownership, kill sandbox if running, mark failed
```

### Response Models
- TaskResponse, QueueStatus, UserLimits (from design doc)

## Dependencies

- TKT-TQU-003: TaskQueueService extensions (for queue operations)

## Related

- Design: DESIGN-TQU-001
- Existing: omoi_os/api/routes/tasks.py
