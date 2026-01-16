# Autonomous Execution Testing Guide

**Created**: 2025-01-15
**Status**: Ready
**Purpose**: Testing procedures for the autonomous execution feature

---

## Overview

This guide covers how to test the autonomous execution feature both locally and in production.

---

## Prerequisites

1. Backend running with migration applied:
   ```bash
   cd backend
   uv run alembic upgrade head
   uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. Redis running for event bus:
   ```bash
   docker-compose up -d redis
   # or
   redis-server
   ```

3. PostgreSQL running with test data

---

## Test 1: Enable Autonomous Mode via SQL

**Purpose:** Verify backend respects the flag

```sql
-- Enable autonomous mode for a specific project
UPDATE projects
SET autonomous_execution_enabled = true
WHERE id = 'your-project-id';

-- Verify the change
SELECT id, name, autonomous_execution_enabled
FROM projects
WHERE id = 'your-project-id';
```

---

## Test 2: Task Filtering Verification

**Purpose:** Verify orchestrator only picks tasks from autonomous projects

### Setup
1. Create two projects: one with autonomous enabled, one disabled
2. Create tasks in both projects

### Test Steps

```python
# In Python REPL or test file
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService

db = DatabaseService()
queue = TaskQueueService(db)

# This should only return tasks from autonomous projects
task = queue.get_next_task_with_concurrency_limit()
print(f"Task returned: {task}")
print(f"Task project: {task.ticket.project.name if task else 'None'}")
```

### Expected Result
- Tasks from non-autonomous projects should NOT be returned
- Tasks from autonomous projects should be returned

---

## Test 3: Task Completion Endpoint

**Purpose:** Verify endpoint updates task and finds unblocked tasks

### Request

```bash
curl -X POST "http://localhost:8000/api/v1/sandboxes/test-sandbox-123/task-complete" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "your-task-id",
    "success": true,
    "result": {
      "output": "Task completed successfully",
      "branch_name": "feature/test-branch"
    }
  }'
```

### Expected Response

```json
{
  "status": "accepted",
  "task_id": "your-task-id",
  "new_status": "completed",
  "unblocked_tasks": ["task-2", "task-3"]
}
```

### Verification

```sql
-- Check task was updated
SELECT id, status, result
FROM tasks
WHERE id = 'your-task-id';

-- Check unblocked tasks exist and are pending
SELECT id, status, dependencies
FROM tasks
WHERE id IN ('task-2', 'task-3');
```

---

## Test 4: DAG Dependency Chain

**Purpose:** Verify cascading unblocks work correctly

### Setup

Create a dependency chain:
```
Task A (no deps) → Task B (depends on A) → Task C (depends on B)
```

```sql
-- Create tasks with dependencies
INSERT INTO tasks (id, ticket_id, status, dependencies)
VALUES
  ('task-a', 'ticket-1', 'pending', '{}'),
  ('task-b', 'ticket-1', 'pending', '{"depends_on": ["task-a"]}'),
  ('task-c', 'ticket-1', 'pending', '{"depends_on": ["task-b"]}');
```

### Test Steps

1. Complete Task A via API
2. Verify Task B becomes unblocked
3. Complete Task B via API
4. Verify Task C becomes unblocked

### Expected Behavior

```
Initial:  A=pending, B=blocked, C=blocked
After A:  A=completed, B=unblocked (returned), C=blocked
After B:  A=completed, B=completed, C=unblocked (returned)
```

---

## Test 5: Parallel Task Unblocking

**Purpose:** Verify multiple tasks unblock simultaneously

### Setup

```
Task A → Task B (depends on A)
       → Task C (depends on A)
       → Task D (depends on A)
```

### Test

Complete Task A and verify B, C, D are all returned as unblocked.

```bash
curl -X POST "http://localhost:8000/api/v1/sandboxes/test/task-complete" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "task-a", "success": true}'
```

### Expected Response

```json
{
  "unblocked_tasks": ["task-b", "task-c", "task-d"]
}
```

---

## Test 6: Event Publishing

**Purpose:** Verify TASKS_UNBLOCKED event is published

### Setup

Subscribe to Redis events:

```bash
redis-cli SUBSCRIBE events:*
```

### Test

Complete a task that unblocks others.

### Expected Event

```json
{
  "event_type": "TASKS_UNBLOCKED",
  "entity_type": "task",
  "entity_id": "task-a",
  "payload": {
    "completed_task_id": "task-a",
    "unblocked_task_ids": ["task-b", "task-c"],
    "sandbox_id": "test-sandbox"
  }
}
```

---

## Test 7: Concurrency Limits Still Apply

**Purpose:** Verify autonomous mode respects project concurrency limits

### Setup

1. Set max concurrent tasks to 2 for a project
2. Create 5 tasks, all ready to run
3. Enable autonomous mode

### Expected Behavior

- Only 2 tasks should be spawned simultaneously
- When one completes, a 3rd should be spawned
- Concurrency limit is never exceeded

---

## Test 8: Failed Task Handling

**Purpose:** Verify failed tasks don't trigger cascading unblocks

```bash
curl -X POST "http://localhost:8000/api/v1/sandboxes/test/task-complete" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task-a",
    "success": false,
    "error_message": "Build failed: missing dependency"
  }'
```

### Expected Response

```json
{
  "status": "accepted",
  "task_id": "task-a",
  "new_status": "failed",
  "unblocked_tasks": []
}
```

Dependent tasks should remain blocked.

---

## Test 9: Integration Test Script

Create this test script for full integration testing:

```python
# tests/integration/test_autonomous_execution.py

import pytest
from uuid import uuid4

from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.models.project import Project
from omoi_os.models.ticket import Ticket
from omoi_os.models.task import Task


@pytest.fixture
def autonomous_project(db):
    """Create a project with autonomous execution enabled."""
    with db.get_session() as session:
        project = Project(
            id=f"test-project-{uuid4()}",
            name="Autonomous Test Project",
            autonomous_execution_enabled=True,
        )
        session.add(project)
        session.commit()
        return project


@pytest.fixture
def non_autonomous_project(db):
    """Create a project without autonomous execution."""
    with db.get_session() as session:
        project = Project(
            id=f"test-project-{uuid4()}",
            name="Manual Test Project",
            autonomous_execution_enabled=False,
        )
        session.add(project)
        session.commit()
        return project


def test_only_autonomous_tasks_returned(
    db, queue, autonomous_project, non_autonomous_project
):
    """Tasks from non-autonomous projects should not be returned."""
    # Create tasks in both projects
    # ... test implementation ...
    pass


def test_task_completion_triggers_unblock(db, queue, autonomous_project):
    """Completing a task should unblock dependent tasks."""
    # Create dependency chain
    # Complete task via endpoint
    # Verify unblocked tasks returned
    pass


def test_failed_task_no_unblock(db, queue, autonomous_project):
    """Failed tasks should not unblock dependents."""
    pass
```

---

## Test 10: Load Testing

**Purpose:** Verify system handles many autonomous projects

```python
# Create 100 projects with autonomous mode
# Create 10 tasks each
# Measure:
# - Time to get next task
# - Correct filtering
# - No race conditions
```

---

## Cleanup

After testing, reset test data:

```sql
-- Disable autonomous mode on all test projects
UPDATE projects
SET autonomous_execution_enabled = false
WHERE name LIKE '%Test%';

-- Or delete test projects entirely
DELETE FROM projects WHERE name LIKE '%Test%';
```

---

## Common Issues

### Issue: Tasks not being picked up

**Check:**
1. Is `autonomous_execution_enabled = true`?
2. Are dependencies satisfied?
3. Is `sandbox_id` NULL?
4. Is status `pending`?

```sql
SELECT t.id, t.status, t.sandbox_id, t.dependencies,
       p.autonomous_execution_enabled
FROM tasks t
JOIN tickets tk ON t.ticket_id = tk.id
JOIN projects p ON tk.project_id = p.id
WHERE t.status = 'pending';
```

### Issue: Unblocked tasks not returned

**Check:**
1. Are all dependencies actually completed?
2. Is the task still pending (not already claimed)?

```sql
SELECT t.id,
       t.dependencies->'depends_on' as depends_on,
       (SELECT COUNT(*)
        FROM tasks dep
        WHERE dep.id::text = ANY(
          SELECT jsonb_array_elements_text(t.dependencies->'depends_on')
        )
        AND dep.status = 'completed'
       ) as completed_deps
FROM tasks t
WHERE t.status = 'pending';
```

---

## Next Steps After Testing

1. Monitor logs for `autonomous_execution_enabled` filtering
2. Check Redis for TASKS_UNBLOCKED events
3. Verify frontend toggle works (after frontend implementation)
4. Run full E2E test with real Daytona sandboxes
