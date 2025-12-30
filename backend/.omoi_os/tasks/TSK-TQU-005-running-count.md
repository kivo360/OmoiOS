---
id: TSK-TQU-005
title: Add get_running_count to TaskQueueService
parent_ticket: TKT-TQU-003
created: 2024-12-29
updated: 2024-12-29
status: pending
priority: HIGH
type: implementation
estimate: 1h
depends_on:
  - TSK-TQU-004
---

# TSK-TQU-005: Add get_running_count to TaskQueueService

## Description

Add method to count tasks in claimed/running status for a specific user.

## Acceptance Criteria

- [ ] get_running_count(user_id) returns int count
- [ ] Counts tasks with status IN ('claimed', 'running')
- [ ] Filters by user_id
- [ ] Async version available
- [ ] Unit test verifies count accuracy

## Implementation

Add to `omoi_os/services/task_queue.py`:

```python
async def get_running_count(self, user_id: str) -> int:
    """Count currently running agents for a user."""
    async with self.db.get_async_session() as session:
        result = await session.execute(
            select(func.count(Task.id))
            .where(Task.user_id == user_id)
            .where(Task.status.in_(['claimed', 'running']))
        )
        return result.scalar_one() or 0
```

## Dependencies

- TSK-TQU-004: PlanService (for integration testing)
