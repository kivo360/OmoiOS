---
id: TSK-TQU-010
title: Implement GET /api/v1/tasks/queue-status endpoint
parent_ticket: TKT-TQU-005
created: 2024-12-29
updated: 2024-12-29
status: pending
priority: HIGH
type: implementation
estimate: 1h
depends_on:
  - TSK-TQU-004
  - TSK-TQU-005
---

# TSK-TQU-010: Implement GET /api/v1/tasks/queue-status endpoint

## Description

Create endpoint that returns user's current queue status including running count, pending count, limits, and monthly usage.

## Acceptance Criteria

- [ ] GET /api/v1/tasks/queue-status returns QueueStatus
- [ ] Includes running, pending counts
- [ ] Includes max_concurrent from plan
- [ ] Includes can_start_more boolean
- [ ] Includes monthly_hours_used and monthly_hours_limit
- [ ] Requires authentication
- [ ] API test via httpx

## Implementation

```python
class QueueStatus(BaseModel):
    running: int
    pending: int
    max_concurrent: int
    can_start_more: bool
    monthly_hours_used: float
    monthly_hours_limit: Optional[int] = None


@router.get("/queue-status", response_model=QueueStatus)
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

    return QueueStatus(
        running=running,
        pending=pending,
        max_concurrent=limits.max_concurrent_agents,
        can_start_more=running < limits.max_concurrent_agents,
        monthly_hours_used=hours_used,
        monthly_hours_limit=limits.monthly_agent_hours,
    )
```

## Dependencies

- TSK-TQU-004: PlanService (for limits and usage)
- TSK-TQU-005: get_running_count
