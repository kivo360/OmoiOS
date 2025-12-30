---
id: TSK-TQU-007
title: Add usage hour tracking to mark_completed/mark_failed
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

# TSK-TQU-007: Add usage hour tracking to mark_completed/mark_failed

## Description

Modify mark_completed and mark_failed methods to calculate and add usage hours to user's monthly total.

## Acceptance Criteria

- [ ] mark_completed calculates hours from started_at to completed_at
- [ ] mark_completed calls plan_service.add_usage_hours
- [ ] mark_failed also tracks hours (even failed tasks count)
- [ ] Hours rounded to 2 decimal places
- [ ] Unit test verifies hours accumulate correctly

## Implementation

Modify in `omoi_os/services/task_queue.py`:

```python
async def mark_completed(
    self,
    task_id: str,
    summary: Optional[str] = None,
    files_changed: Optional[list] = None,
) -> None:
    """Mark task as successfully completed."""
    from omoi_os.utils.datetime import utc_now

    async with self.db.get_async_session() as session:
        result = await session.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            return

        now = utc_now()
        task.status = "completed"
        task.completed_at = now
        if summary:
            task.result_summary = summary
        if files_changed:
            task.files_changed = files_changed

        await session.commit()

        # Track usage hours
        if task.started_at and task.user_id:
            duration = now - task.started_at
            hours = round(duration.total_seconds() / 3600, 2)
            await self.plan_service.add_usage_hours(task.user_id, hours)
```

## Dependencies

- TSK-TQU-004: PlanService (for add_usage_hours method)
