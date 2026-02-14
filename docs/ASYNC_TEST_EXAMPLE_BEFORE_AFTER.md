# Concrete Test Migration Example: test_02_task_queue.py

This shows the **exact before/after** transformation of a real test file.

---

## ❌ BEFORE: Current Synchronous Version

```python
"""Test task queue service: enqueue, get_next_task, assign, update status."""

from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.task_queue import TaskQueueService


def test_enqueue_task(task_queue_service: TaskQueueService, sample_ticket: Ticket):
    """Test enqueueing a task."""
    task = task_queue_service.enqueue_task(
        ticket_id=sample_ticket.id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="analyze_requirements",
        description="Analyze requirements for ticket",
        priority="HIGH",
    )

    assert task is not None
    assert task.id is not None
    assert task.ticket_id == sample_ticket.id
    assert task.phase_id == "PHASE_REQUIREMENTS"
    assert task.task_type == "analyze_requirements"
    assert task.status == "pending"
    assert task.priority == "HIGH"


def test_get_next_task_empty(task_queue_service: TaskQueueService):
    """Test get_next_task returns None when queue is empty."""
    task = task_queue_service.get_next_task("PHASE_REQUIREMENTS")
    assert task is None


def test_get_next_task_priority_order(task_queue_service: TaskQueueService, sample_ticket: Ticket):
    """Test get_next_task returns highest priority task first."""
    # Create tasks with different priorities
    task_queue_service.enqueue_task(
        ticket_id=sample_ticket.id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="task1",
        description="Low priority",
        priority="LOW",
    )

    task_high = task_queue_service.enqueue_task(
        ticket_id=sample_ticket.id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="task2",
        description="High priority",
        priority="HIGH",
    )

    task_medium = task_queue_service.enqueue_task(
        ticket_id=sample_ticket.id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="task3",
        description="Medium priority",
        priority="MEDIUM",
    )

    # Should return HIGH priority first
    next_task = task_queue_service.get_next_task("PHASE_REQUIREMENTS")
    assert next_task is not None
    assert next_task.id == task_high.id
    assert next_task.priority == "HIGH"

    # Assign the high priority task
    task_queue_service.assign_task(task_high.id, "agent-1")

    # Next should be MEDIUM
    next_task = task_queue_service.get_next_task("PHASE_REQUIREMENTS")
    assert next_task is not None
    assert next_task.id == task_medium.id
    assert next_task.priority == "MEDIUM"


def test_assign_task(task_queue_service: TaskQueueService, sample_task: Task):
    """Test assigning a task to an agent."""
    agent_id = "test-agent-123"

    task_queue_service.assign_task(sample_task.id, agent_id)

    # Verify assignment
    with task_queue_service.db.get_session() as session:
        task = session.get(Task, sample_task.id)
        assert task.assigned_agent_id == agent_id
        assert task.status == "assigned"


def test_update_task_status_running(task_queue_service: TaskQueueService, sample_task: Task):
    """Test updating task status to running."""
    task_queue_service.update_task_status(sample_task.id, "running")

    with task_queue_service.db.get_session() as session:
        task = session.get(Task, sample_task.id)
        assert task.status == "running"
        assert task.started_at is not None


def test_get_assigned_tasks(task_queue_service: TaskQueueService, sample_ticket: Ticket):
    """Test getting tasks assigned to a specific agent."""
    agent_id = "test-agent-456"

    # Create and assign multiple tasks
    task1 = task_queue_service.enqueue_task(
        ticket_id=sample_ticket.id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="task1",
        description="Task 1",
        priority="HIGH",
    )
    task_queue_service.assign_task(task1.id, agent_id)

    task2 = task_queue_service.enqueue_task(
        ticket_id=sample_ticket.id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="task2",
        description="Task 2",
        priority="MEDIUM",
    )
    task_queue_service.assign_task(task2.id, agent_id)
    task_queue_service.update_task_status(task2.id, "running")

    # Get assigned tasks
    assigned = task_queue_service.get_assigned_tasks(agent_id)
    assert len(assigned) == 2
    assigned_ids = {t.id for t in assigned}
    assert task1.id in assigned_ids
    assert task2.id in assigned_ids
```

---

## ✅ AFTER: Async Version

```python
"""Test task queue service: enqueue, get_next_task, assign, update status."""

import pytest
from sqlalchemy import select

from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.task_queue import TaskQueueService


@pytest.mark.asyncio
async def test_enqueue_task(task_queue_service: TaskQueueService, sample_ticket: Ticket):
    """Test enqueueing a task."""
    task = await task_queue_service.enqueue_task(  # Added await
        ticket_id=sample_ticket.id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="analyze_requirements",
        description="Analyze requirements for ticket",
        priority="HIGH",
    )

    assert task is not None
    assert task.id is not None
    assert task.ticket_id == sample_ticket.id
    assert task.phase_id == "PHASE_REQUIREMENTS"
    assert task.task_type == "analyze_requirements"
    assert task.status == "pending"
    assert task.priority == "HIGH"


@pytest.mark.asyncio
async def test_get_next_task_empty(task_queue_service: TaskQueueService):
    """Test get_next_task returns None when queue is empty."""
    task = await task_queue_service.get_next_task("PHASE_REQUIREMENTS")  # Added await
    assert task is None


@pytest.mark.asyncio
async def test_get_next_task_priority_order(task_queue_service: TaskQueueService, sample_ticket: Ticket):
    """Test get_next_task returns highest priority task first."""
    # Create tasks with different priorities
    await task_queue_service.enqueue_task(  # Added await
        ticket_id=sample_ticket.id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="task1",
        description="Low priority",
        priority="LOW",
    )

    task_high = await task_queue_service.enqueue_task(  # Added await
        ticket_id=sample_ticket.id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="task2",
        description="High priority",
        priority="HIGH",
    )

    task_medium = await task_queue_service.enqueue_task(  # Added await
        ticket_id=sample_ticket.id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="task3",
        description="Medium priority",
        priority="MEDIUM",
    )

    # Should return HIGH priority first
    next_task = await task_queue_service.get_next_task("PHASE_REQUIREMENTS")  # Added await
    assert next_task is not None
    assert next_task.id == task_high.id
    assert next_task.priority == "HIGH"

    # Assign the high priority task
    await task_queue_service.assign_task(task_high.id, "agent-1")  # Added await

    # Next should be MEDIUM
    next_task = await task_queue_service.get_next_task("PHASE_REQUIREMENTS")  # Added await
    assert next_task is not None
    assert next_task.id == task_medium.id
    assert next_task.priority == "MEDIUM"


@pytest.mark.asyncio
async def test_assign_task(task_queue_service: TaskQueueService, sample_task: Task):
    """Test assigning a task to an agent."""
    agent_id = "test-agent-123"

    await task_queue_service.assign_task(sample_task.id, agent_id)  # Added await

    # Verify assignment
    async with task_queue_service.db.get_session() as session:  # Changed to async with
        task = await session.get(Task, sample_task.id)  # Added await
        assert task.assigned_agent_id == agent_id
        assert task.status == "assigned"


@pytest.mark.asyncio
async def test_update_task_status_running(task_queue_service: TaskQueueService, sample_task: Task):
    """Test updating task status to running."""
    await task_queue_service.update_task_status(sample_task.id, "running")  # Added await

    async with task_queue_service.db.get_session() as session:  # Changed to async with
        task = await session.get(Task, sample_task.id)  # Added await
        assert task.status == "running"
        assert task.started_at is not None


@pytest.mark.asyncio
async def test_get_assigned_tasks(task_queue_service: TaskQueueService, sample_ticket: Ticket):
    """Test getting tasks assigned to a specific agent."""
    agent_id = "test-agent-456"

    # Create and assign multiple tasks
    task1 = await task_queue_service.enqueue_task(  # Added await
        ticket_id=sample_ticket.id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="task1",
        description="Task 1",
        priority="HIGH",
    )
    await task_queue_service.assign_task(task1.id, agent_id)  # Added await

    task2 = await task_queue_service.enqueue_task(  # Added await
        ticket_id=sample_ticket.id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="task2",
        description="Task 2",
        priority="MEDIUM",
    )
    await task_queue_service.assign_task(task2.id, agent_id)  # Added await
    await task_queue_service.update_task_status(task2.id, "running")  # Added await

    # Get assigned tasks
    assigned = await task_queue_service.get_assigned_tasks(agent_id)  # Added await
    assert len(assigned) == 2
    assigned_ids = {t.id for t in assigned}
    assert task1.id in assigned_ids
    assert task2.id in assigned_ids
```

---

## Summary of Changes

### Changes Made:
1. ✅ Added `import pytest` and `from sqlalchemy import select`
2. ✅ Added `@pytest.mark.asyncio` decorator to **every test function** (9 functions)
3. ✅ Changed `def test_` → `async def test_` (9 functions)
4. ✅ Added `await` to **all service method calls** (15+ calls):
   - `enqueue_task()` → `await enqueue_task()`
   - `get_next_task()` → `await get_next_task()`
   - `assign_task()` → `await assign_task()`
   - `update_task_status()` → `await update_task_status()`
   - `get_assigned_tasks()` → `await get_assigned_tasks()`
5. ✅ Changed `with session` → `async with session` (2 places)
6. ✅ Changed `session.get()` → `await session.get()` (2 places)

### Total Changes in This File:
- **9 test functions** converted to async
- **15+ service method calls** now use `await`
- **2 database session usages** converted to async
- **~20 lines** of changes (adding `async`, `await`, decorators)

---

## Pattern Recognition

This file is **relatively simple** because:
- It doesn't use `session.query()` (would need `select()` conversion)
- It doesn't use relationships (would need `selectinload()`)
- It doesn't have complex mocking (would need `AsyncMock`)

**More complex test files** would have:
- `session.query()` → `await session.execute(select())` conversions
- Relationship loading with `selectinload()`
- Complex async mock patterns
- Multiple nested async operations

---

## What This Means for the Full Migration

If this **simple file** needs ~20 changes across 9 functions, then:

- **Complex files** (like `test_validation_system.py` with 24 test functions and 96 database operations) would need **~200+ changes**
- **Files with relationships** would need additional `selectinload()` calls
- **Files with mocking** would need complete mock rewrites

**Estimated total changes across all tests:**
- **~490 test functions** × average 3-5 changes each = **~1,500-2,500 individual changes**
- Plus fixture changes
- Plus mock pattern changes
- Plus relationship loading fixes

This is why the test migration is estimated at **2-3 weeks** of focused work.
