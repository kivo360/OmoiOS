---
id: TKT-TQU-004
title: Orchestrator Worker Updates
feature: task-queue-user-limits
created: 2024-12-29
updated: 2024-12-29
status: open
priority: HIGH
phase: PHASE_IMPLEMENTATION
type: feature
requirements:
  - REQ-TQU-DUR-001
  - REQ-TQU-DUR-002
  - REQ-TQU-DUR-003
linked_design: designs/task-queue-user-limits.md
estimate: 4h
depends_on:
  - TKT-TQU-003
---

# TKT-TQU-004: Orchestrator Worker Updates

## Summary

Update OrchestratorWorker to use cross-user claiming, enforce per-user timeouts, and kill timed-out sandboxes.

## Acceptance Criteria

- [ ] Orchestrator uses claim_next_task_any_user() in main loop
- [ ] Timeout from user's plan passed to sandbox spawner
- [ ] Timeout check runs every 60 seconds
- [ ] Timed-out tasks: sandbox terminated, task marked failed
- [ ] Usage hours tracked even for timed-out tasks
- [ ] Graceful shutdown handles in-flight claims
- [ ] Integration test: queue 3 tasks, verify limits respected

## Technical Details

### Main Loop Updates
```python
async def run(self):
    while not self._shutdown:
        # Periodic timeout check
        if now - self._last_timeout_check > timedelta(seconds=60):
            await self._kill_timed_out_tasks()
            self._last_timeout_check = now

        # Claim across all users
        task = await self.task_queue.claim_next_task_any_user()
        if task:
            await self._process_task(task)
        else:
            await asyncio.sleep(self.poll_interval)
```

### Timeout Handling
```python
async def _kill_timed_out_tasks(self):
    running = await self.db.fetch("""
        SELECT t.*, u.max_task_duration_minutes
        FROM tasks t
        JOIN users u ON t.user_id = u.id
        WHERE t.status = 'running' AND t.started_at IS NOT NULL
    """)

    for task in running:
        max_duration = timedelta(minutes=task["max_task_duration_minutes"])
        if now - task["started_at"] > max_duration:
            await self.spawner.terminate(task["sandbox_id"])
            await self.task_queue.mark_failed(
                task["id"],
                f"Timeout: exceeded {task['max_task_duration_minutes']} minutes"
            )
```

## Dependencies

- TKT-TQU-003: TaskQueueService extensions (claim_next_task_any_user)

## Related

- Design: DESIGN-TQU-001
- Existing: omoi_os/workers/orchestrator_worker.py
