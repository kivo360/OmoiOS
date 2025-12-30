---
id: TSK-TQU-008
title: Add timeout detection loop to orchestrator
parent_ticket: TKT-TQU-004
created: 2024-12-29
updated: 2024-12-29
status: pending
priority: HIGH
type: implementation
estimate: 2h
depends_on:
  - TSK-TQU-006
  - TSK-TQU-007
---

# TSK-TQU-008: Add timeout detection loop to orchestrator

## Description

Update OrchestratorWorker to periodically check for and kill timed-out tasks.

## Acceptance Criteria

- [ ] _kill_timed_out_tasks() method added
- [ ] Timeout check runs every 60 seconds
- [ ] Joins tasks with users to get max_task_duration_minutes
- [ ] Terminates sandbox for timed-out tasks
- [ ] Marks task failed with timeout reason
- [ ] Tracks usage hours for timed-out tasks
- [ ] Integration test verifies timeout handling

## Implementation

Add to `omoi_os/workers/orchestrator_worker.py`:

```python
from datetime import timedelta

class OrchestratorWorker:
    def __init__(self, ...):
        ...
        self.timeout_check_interval = 60.0
        self._last_timeout_check = datetime.min

    async def run(self):
        while not self._shutdown:
            try:
                # Periodic timeout check
                now = utc_now()
                if (now - self._last_timeout_check).total_seconds() > self.timeout_check_interval:
                    await self._kill_timed_out_tasks()
                    self._last_timeout_check = now

                # Claim and process
                task = await self.task_queue.claim_next_task_any_user()
                if task:
                    await self._process_task(task)
                else:
                    await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Orchestrator error: {e}")
                await asyncio.sleep(self.poll_interval)

    async def _kill_timed_out_tasks(self):
        """Find and kill tasks that have exceeded their time limit."""
        running = await self.db.fetch("""
            SELECT t.*, u.max_task_duration_minutes
            FROM tasks t
            JOIN users u ON t.user_id = u.id
            WHERE t.status = 'running'
            AND t.started_at IS NOT NULL
        """)

        now = utc_now()
        killed = 0

        for task in running:
            max_duration = timedelta(minutes=task["max_task_duration_minutes"])
            if now - task["started_at"] > max_duration:
                logger.info(f"Killing timed-out task: {task['id']}")

                if task["sandbox_id"]:
                    try:
                        await self.spawner.terminate(task["sandbox_id"])
                    except Exception as e:
                        logger.warning(f"Failed to terminate sandbox: {e}")

                await self.task_queue.mark_failed(
                    task["id"],
                    f"Timeout: exceeded {task['max_task_duration_minutes']} minutes"
                )
                killed += 1

        if killed:
            logger.info(f"Killed {killed} timed-out tasks")
```

## Dependencies

- TSK-TQU-006: claim_next_task_any_user (main loop uses this)
- TSK-TQU-007: mark_failed with usage tracking
