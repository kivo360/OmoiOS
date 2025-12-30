---
id: TKT-TQU-003
title: TaskQueueService Extensions
feature: task-queue-user-limits
created: 2024-12-29
updated: 2024-12-29
status: open
priority: HIGH
phase: PHASE_IMPLEMENTATION
type: feature
requirements:
  - REQ-TQU-CONC-004
  - REQ-TQU-QUEUE-001
  - REQ-TQU-QUEUE-002
  - REQ-TQU-QUEUE-003
  - REQ-TQU-USAGE-001
  - REQ-TQU-USAGE-002
linked_design: designs/task-queue-user-limits.md
estimate: 6h
depends_on:
  - TKT-TQU-002
---

# TKT-TQU-003: TaskQueueService Extensions

## Summary

Extend existing TaskQueueService with user-based claiming, running count tracking, queue position, and usage hour tracking on completion.

## Acceptance Criteria

- [ ] get_running_count(user_id) returns count of claimed/running tasks
- [ ] claim_next_task_for_user(user_id) claims respecting user limits
- [ ] claim_next_task_any_user() claims across all users fairly
- [ ] get_pending_count(user_id) returns pending task count
- [ ] get_queue_position(task_id) returns position in user's queue
- [ ] mark_completed() updates monthly_agent_hours_used
- [ ] mark_failed() updates monthly_agent_hours_used
- [ ] Atomic claiming prevents race conditions
- [ ] Integration tests with PlanService

## Technical Details

### New Methods
```python
async def get_running_count(self, user_id: str) -> int:
    """Count tasks in claimed/running status for user."""

async def claim_next_task_any_user(self) -> Optional[Task]:
    """
    Claim next available task across all users.
    Respects per-user limits, prioritizes users with fewer running agents.
    """

async def get_queue_position(self, task_id: str) -> Optional[int]:
    """Get position of task in user's queue (by priority then created_at)."""
```

### Modified Methods
- mark_completed(): Calculate hours, call plan_service.add_usage_hours()
- mark_failed(): Calculate hours, call plan_service.add_usage_hours()

### SQL for Cross-User Claiming
```sql
WITH user_running AS (
    SELECT user_id, COUNT(*) as running_count
    FROM tasks
    WHERE status IN ('claimed', 'running')
    GROUP BY user_id
),
user_pending AS (
    SELECT DISTINCT user_id
    FROM tasks
    WHERE status = 'pending'
)
SELECT up.user_id, u.max_concurrent_agents,
       COALESCE(ur.running_count, 0) as running
FROM user_pending up
JOIN users u ON up.user_id = u.id
LEFT JOIN user_running ur ON up.user_id = ur.user_id
WHERE COALESCE(ur.running_count, 0) < u.max_concurrent_agents
ORDER BY COALESCE(ur.running_count, 0) ASC
LIMIT 10
```

## Dependencies

- TKT-TQU-002: PlanService (for limits and usage tracking)

## Related

- Design: DESIGN-TQU-001
- Existing: omoi_os/services/task_queue.py
