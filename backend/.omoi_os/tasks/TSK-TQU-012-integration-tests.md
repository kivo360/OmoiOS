---
id: TSK-TQU-012
title: Write integration tests for task queue flow
parent_ticket: TKT-TQU-006
created: 2024-12-29
updated: 2024-12-29
status: pending
priority: MEDIUM
type: test
estimate: 3h
depends_on:
  - TSK-TQU-008
  - TSK-TQU-009
  - TSK-TQU-010
  - TSK-TQU-011
---

# TSK-TQU-012: Write integration tests for task queue flow

## Description

Create comprehensive integration tests for the complete task queue flow with user limits.

## Acceptance Criteria

- [ ] Test basic flow: queue 3 tasks, verify sequential execution for free user
- [ ] Test timeout: task killed after exceeding duration
- [ ] Test monthly limits: claim rejected when hours exhausted
- [ ] Test multi-user fairness: tasks interleave between users
- [ ] Test cancellation: sandbox terminated, task marked failed
- [ ] Performance test: claiming < 100ms
- [ ] All tests pass in CI

## Test Cases

```python
# tests/integration/test_task_queue_user_limits.py

@pytest.mark.asyncio
async def test_free_user_single_concurrent(db, task_queue, plan_service):
    """Free users can only run 1 task at a time."""
    user = await create_user(db, plan_tier="free")

    # Queue 3 tasks
    task1 = await task_queue.create_task(user.id, "Task 1")
    task2 = await task_queue.create_task(user.id, "Task 2")
    task3 = await task_queue.create_task(user.id, "Task 3")

    # First claim succeeds
    claimed = await task_queue.claim_next_task_for_user(user.id)
    assert claimed.id == task1.id

    # Second claim fails (at limit)
    can_claim, reason = await plan_service.can_claim_task(user.id, running_count=1)
    assert not can_claim
    assert "1/1 agents running" in reason


@pytest.mark.asyncio
async def test_timeout_kills_sandbox(db, task_queue, spawner, orchestrator):
    """Tasks exceeding timeout are killed."""
    user = await create_user(db, max_task_duration_minutes=1)
    task = await task_queue.create_task(user.id, "Long task")

    # Start task
    await task_queue.claim_next_task_for_user(user.id)
    await task_queue.mark_running(task.id, "sandbox-123")

    # Simulate time passing
    task.started_at = utc_now() - timedelta(minutes=2)
    await db.commit()

    # Run timeout check
    await orchestrator._kill_timed_out_tasks()

    # Verify
    refreshed = await task_queue.get_task(task.id)
    assert refreshed.status == "failed"
    assert "Timeout" in refreshed.error_message
    spawner.terminate.assert_called_with("sandbox-123")
```

## Dependencies

- TSK-TQU-008: Orchestrator timeout (for timeout tests)
- TSK-TQU-009: Create task API (for API tests)
- TSK-TQU-010: Queue status API
- TSK-TQU-011: Cancel task API
