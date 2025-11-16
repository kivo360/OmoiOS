"""Tests for parallel execution, DAG scheduling, and resource locking."""

import time
from uuid import uuid4

import pytest

from omoi_os.models.task import Task
from omoi_os.services.agent_registry import AgentRegistryService
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.resource_lock import LockAcquisitionError, ResourceLockService
from omoi_os.services.scheduler import SchedulerService
from omoi_os.services.task_queue import TaskQueueService


@pytest.fixture
def lock_service(db_service: DatabaseService, event_bus: EventBusService) -> ResourceLockService:
    """Create resource lock service."""
    return ResourceLockService(db_service, event_bus=event_bus)


@pytest.fixture
def scheduler_service(
    db_service: DatabaseService,
    task_queue: TaskQueueService,
    event_bus: EventBusService,
    lock_service: ResourceLockService,
) -> SchedulerService:
    """Create scheduler service."""
    registry = AgentRegistryService(db_service, event_bus)
    return SchedulerService(db_service, task_queue, registry, lock_service, event_bus)


def test_lock_acquisition(lock_service: ResourceLockService):
    """Test basic lock acquisition and release."""
    resource_key = f"test_resource_{uuid4()}"
    task_id = str(uuid4())
    agent_id = str(uuid4())

    # Acquire lock
    lock = lock_service.acquire_lock(resource_key, task_id, agent_id)
    assert lock.resource_key == resource_key
    assert lock.task_id == task_id
    assert lock.agent_id == agent_id

    # Check that resource is locked
    assert lock_service.is_locked(resource_key) is True

    # Release lock
    released = lock_service.release_lock(lock.id, agent_id)
    assert released is True

    # Check that resource is no longer locked
    assert lock_service.is_locked(resource_key) is False


def test_lock_conflict(lock_service: ResourceLockService):
    """Test that conflicting locks are prevented."""
    resource_key = f"test_resource_{uuid4()}"
    task_id_1 = str(uuid4())
    task_id_2 = str(uuid4())
    agent_id = str(uuid4())

    # Acquire first lock
    lock1 = lock_service.acquire_lock(resource_key, task_id_1, agent_id)

    # Try to acquire conflicting lock (should fail)
    with pytest.raises(LockAcquisitionError):
        lock_service.acquire_lock(resource_key, task_id_2, agent_id, max_retries=1)

    # Release first lock
    lock_service.release_lock(lock1.id, agent_id)

    # Now second lock should succeed
    lock2 = lock_service.acquire_lock(resource_key, task_id_2, agent_id)
    assert lock2.task_id == task_id_2


def test_lock_expiration(lock_service: ResourceLockService):
    """Test that expired locks are cleaned up."""
    resource_key = f"test_resource_{uuid4()}"
    task_id = str(uuid4())
    agent_id = str(uuid4())

    # Acquire lock with short TTL
    lock = lock_service.acquire_lock(resource_key, task_id, agent_id, ttl_seconds=1)
    assert lock_service.is_locked(resource_key) is True

    # Wait for expiration
    time.sleep(2)

    # Lock should be expired and cleaned up
    assert lock_service.is_locked(resource_key) is False


def test_lock_cleanup_expired(lock_service: ResourceLockService):
    """Test cleanup of expired locks."""
    resource_key_1 = f"test_resource_{uuid4()}"
    resource_key_2 = f"test_resource_{uuid4()}"
    task_id = str(uuid4())
    agent_id = str(uuid4())

    # Create locks with short TTL
    lock_service.acquire_lock(resource_key_1, task_id, agent_id, ttl_seconds=1)
    lock_service.acquire_lock(resource_key_2, task_id, agent_id, ttl_seconds=1)

    # Wait for expiration
    time.sleep(2)

    # Cleanup expired locks
    cleaned = lock_service.cleanup_expired_locks()
    assert cleaned >= 2


def test_dag_scheduling_simple(scheduler_service: SchedulerService, db_service: DatabaseService):
    """Test DAG scheduling with simple dependency chain."""
    ticket_id = str(uuid4())

    # Create tasks: task1 -> task2 -> task3
    task1 = scheduler_service.task_queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="test",
        description="Task 1",
        priority="HIGH",
    )

    task2 = scheduler_service.task_queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="test",
        description="Task 2",
        priority="HIGH",
        dependencies={"depends_on": [task1.id]},
    )

    task3 = scheduler_service.task_queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="test",
        description="Task 3",
        priority="HIGH",
        dependencies={"depends_on": [task2.id]},
    )

    # Get ready tasks (should only return task1)
    ready_tasks = scheduler_service.get_ready_tasks(phase_id="PHASE_IMPLEMENTATION")
    ready_ids = {t.id for t in ready_tasks}
    assert task1.id in ready_ids
    assert task2.id not in ready_ids
    assert task3.id not in ready_ids

    # Complete task1
    scheduler_service.task_queue.update_task_status(task1.id, "completed")

    # Now task2 should be ready
    ready_tasks = scheduler_service.get_ready_tasks(phase_id="PHASE_IMPLEMENTATION")
    ready_ids = {t.id for t in ready_tasks}
    assert task2.id in ready_ids
    assert task3.id not in ready_ids

    # Complete task2
    scheduler_service.task_queue.update_task_status(task2.id, "completed")

    # Now task3 should be ready
    ready_tasks = scheduler_service.get_ready_tasks(phase_id="PHASE_IMPLEMENTATION")
    ready_ids = {t.id for t in ready_tasks}
    assert task3.id in ready_ids


def test_dag_scheduling_parallel(scheduler_service: SchedulerService):
    """Test DAG scheduling with parallel branches."""
    ticket_id = str(uuid4())

    # Create tasks: task1 -> [task2, task3] -> task4
    task1 = scheduler_service.task_queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="test",
        description="Task 1",
        priority="HIGH",
    )

    task2 = scheduler_service.task_queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="test",
        description="Task 2",
        priority="HIGH",
        dependencies={"depends_on": [task1.id]},
    )

    task3 = scheduler_service.task_queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="test",
        description="Task 3",
        priority="HIGH",
        dependencies={"depends_on": [task1.id]},
    )

    task4 = scheduler_service.task_queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="test",
        description="Task 4",
        priority="HIGH",
        dependencies={"depends_on": [task2.id, task3.id]},
    )

    # Initially only task1 is ready
    ready_tasks = scheduler_service.get_ready_tasks(phase_id="PHASE_IMPLEMENTATION")
    ready_ids = {t.id for t in ready_tasks}
    assert task1.id in ready_ids
    assert task4.id not in ready_ids

    # Complete task1
    scheduler_service.task_queue.update_task_status(task1.id, "completed")

    # Now task2 and task3 should both be ready (parallel)
    ready_tasks = scheduler_service.get_ready_tasks(phase_id="PHASE_IMPLEMENTATION")
    ready_ids = {t.id for t in ready_tasks}
    assert task2.id in ready_ids
    assert task3.id in ready_ids
    assert task4.id not in ready_ids

    # Complete task2 and task3
    scheduler_service.task_queue.update_task_status(task2.id, "completed")
    scheduler_service.task_queue.update_task_status(task3.id, "completed")

    # Now task4 should be ready
    ready_tasks = scheduler_service.get_ready_tasks(phase_id="PHASE_IMPLEMENTATION")
    ready_ids = {t.id for t in ready_tasks}
    assert task4.id in ready_ids


def test_lock_fairness(lock_service: ResourceLockService):
    """Test that locks are fairly acquired under contention."""
    resource_key = f"test_resource_{uuid4()}"
    task_id_1 = str(uuid4())
    task_id_2 = str(uuid4())
    agent_id = str(uuid4())

    # Acquire first lock
    lock1 = lock_service.acquire_lock(resource_key, task_id_1, agent_id)

    # Try to acquire second lock with retries
    # This tests the backoff mechanism
    start_time = time.time()
    try:
        lock_service.acquire_lock(resource_key, task_id_2, agent_id, max_retries=2, base_backoff=0.1)
        assert False, "Should have raised LockAcquisitionError"
    except LockAcquisitionError:
        pass  # Expected

    elapsed = time.time() - start_time
    # Should have waited for backoff delays
    assert elapsed >= 0.1  # At least one backoff delay

    # Release first lock
    lock_service.release_lock(lock1.id, agent_id)

    # Now second lock should succeed quickly
    start_time = time.time()
    lock2 = lock_service.acquire_lock(resource_key, task_id_2, agent_id)
    elapsed = time.time() - start_time
    assert elapsed < 0.1  # Should be fast now
    assert lock2.task_id == task_id_2


def test_scheduler_priority_ordering(scheduler_service: SchedulerService):
    """Test that scheduler returns tasks in priority order."""
    ticket_id = str(uuid4())

    # Create tasks with different priorities
    low_task = scheduler_service.task_queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="test",
        description="Low priority",
        priority="LOW",
    )

    high_task = scheduler_service.task_queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="test",
        description="High priority",
        priority="HIGH",
    )

    critical_task = scheduler_service.task_queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="test",
        description="Critical priority",
        priority="CRITICAL",
    )

    # Get ready tasks
    ready_tasks = scheduler_service.get_ready_tasks(phase_id="PHASE_IMPLEMENTATION")

    # Should be ordered by priority: CRITICAL > HIGH > LOW
    assert len(ready_tasks) >= 3
    priorities = [t.priority for t in ready_tasks[:3]]
    assert priorities[0] == "CRITICAL"
    assert priorities[1] == "HIGH"
    assert priorities[2] == "LOW"


def test_release_locks_for_task(lock_service: ResourceLockService):
    """Test releasing all locks for a task."""
    resource_key_1 = f"test_resource_{uuid4()}"
    resource_key_2 = f"test_resource_{uuid4()}"
    task_id = str(uuid4())
    agent_id = str(uuid4())

    # Acquire multiple locks for same task
    lock1 = lock_service.acquire_lock(resource_key_1, task_id, agent_id)
    lock2 = lock_service.acquire_lock(resource_key_2, task_id, agent_id)

    assert lock_service.is_locked(resource_key_1) is True
    assert lock_service.is_locked(resource_key_2) is True

    # Release all locks for task
    released_count = lock_service.release_locks_for_task(task_id, agent_id)
    assert released_count == 2

    assert lock_service.is_locked(resource_key_1) is False
    assert lock_service.is_locked(resource_key_2) is False
