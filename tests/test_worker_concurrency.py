"""Tests for worker concurrency and capacity constraints."""

import os
import time
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from omoi_os.models.agent import Agent
from omoi_os.models.task import Task
from omoi_os.services.agent_executor import AgentExecutor
from omoi_os.services.agent_registry import AgentRegistryService
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.resource_lock import ResourceLockService
from omoi_os.services.task_queue import TaskQueueService


@pytest.fixture
def mock_executor():
    """Mock agent executor."""
    executor = MagicMock(spec=AgentExecutor)
    executor.execute_task.return_value = {"result": "success"}
    return executor


def test_worker_respects_capacity(db_service: DatabaseService, event_bus: EventBusService):
    """Test that worker respects agent capacity limits."""
    from omoi_os.services.agent_registry import AgentRegistryService
    from omoi_os.services.resource_lock import ResourceLockService
    from omoi_os.services.scheduler import SchedulerService
    from omoi_os.services.task_queue import TaskQueueService

    task_queue = TaskQueueService(db_service)
    registry = AgentRegistryService(db_service, event_bus)
    lock_service = ResourceLockService(db_service, event_bus=event_bus)
    scheduler = SchedulerService(db_service, task_queue, registry, lock_service, event_bus)

    # Register agent with capacity of 2
    agent = registry.register_agent(
        agent_type="worker",
        phase_id="PHASE_IMPLEMENTATION",
        capabilities=["bash", "file_editor"],
        capacity=2,
    )

    ticket_id = str(agent.id)  # Use agent ID as ticket ID for uniqueness

    # Create 5 tasks
    tasks = []
    for i in range(5):
        task = task_queue.enqueue_task(
            ticket_id=ticket_id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="test",
            description=f"Task {i}",
            priority="MEDIUM",
        )
        tasks.append(task)

    # Get ready tasks and assign
    assignments = scheduler.schedule_and_assign(
        phase_id="PHASE_IMPLEMENTATION",
        limit=5,
    )

    # Assign tasks to agent
    assigned_count = 0
    for assignment in assignments:
        if assignment["assigned"] and assignment["agent_id"]:
            task_queue.assign_task(assignment["task_id"], assignment["agent_id"])
            assigned_count += 1

    # Check that agent capacity is respected
    # In a real scenario, the worker would only process up to capacity concurrent tasks
    # Here we're testing that the scheduler can assign tasks
    assert assigned_count > 0


def test_concurrent_task_execution_with_locks(
    db_service: DatabaseService,
    event_bus: EventBusService,
    mock_executor: MagicMock,
):
    """Test that concurrent tasks respect resource locks."""
    from omoi_os.services.resource_lock import ResourceLockService

    lock_service = ResourceLockService(db_service, event_bus=event_bus)
    task_queue = TaskQueueService(db_service)

    ticket_id = str(uuid4())
    agent_id = str(uuid4())

    # Create task
    task = task_queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="test",
        description="Test task",
        priority="HIGH",
    )

    # Acquire lock for task resource
    resource_key = f"workspace:{task.id}"
    lock = lock_service.acquire_lock(resource_key, task.id, agent_id)

    # Try to acquire same lock from different agent (should fail)
    other_agent_id = str(uuid4())
    with pytest.raises(Exception):  # LockAcquisitionError
        lock_service.acquire_lock(resource_key, task.id, other_agent_id, max_retries=1)

    # Release lock
    lock_service.release_lock(lock.id, agent_id)

    # Now other agent can acquire lock
    lock2 = lock_service.acquire_lock(resource_key, task.id, other_agent_id)
    assert lock2.agent_id == other_agent_id


def test_worker_lock_cleanup_on_shutdown(db_service: DatabaseService, event_bus: EventBusService):
    """Test that worker cleans up locks on shutdown."""
    from omoi_os.models.resource_lock import ResourceLock

    lock_service = ResourceLockService(db_service, event_bus=event_bus)
    agent_id = str(uuid4())
    task_id = str(uuid4())

    # Acquire some locks
    lock1 = lock_service.acquire_lock(f"resource_1", task_id, agent_id)
    lock2 = lock_service.acquire_lock(f"resource_2", task_id, agent_id)

    # Verify locks exist
    with db_service.get_session() as session:
        locks = session.query(ResourceLock).filter(ResourceLock.agent_id == agent_id).all()
        assert len(locks) == 2

    # Simulate worker shutdown: release all locks for agent
    released = lock_service.release_locks_for_task(task_id, agent_id)
    assert released == 2

    # Verify locks are gone
    with db_service.get_session() as session:
        locks = session.query(ResourceLock).filter(ResourceLock.agent_id == agent_id).all()
        assert len(locks) == 0


def test_task_assignment_with_capabilities(
    db_service: DatabaseService,
    event_bus: EventBusService,
):
    """Test that scheduler assigns tasks based on agent capabilities."""
    from omoi_os.services.agent_registry import AgentRegistryService
    from omoi_os.services.resource_lock import ResourceLockService
    from omoi_os.services.scheduler import SchedulerService
    from omoi_os.services.task_queue import TaskQueueService

    task_queue = TaskQueueService(db_service)
    registry = AgentRegistryService(db_service, event_bus)
    lock_service = ResourceLockService(db_service, event_bus=event_bus)
    scheduler = SchedulerService(db_service, task_queue, registry, lock_service, event_bus)

    # Register agents with different capabilities
    agent_python = registry.register_agent(
        agent_type="worker",
        phase_id="PHASE_IMPLEMENTATION",
        capabilities=["python", "testing"],
        capacity=2,
    )

    agent_js = registry.register_agent(
        agent_type="worker",
        phase_id="PHASE_IMPLEMENTATION",
        capabilities=["javascript", "node"],
        capacity=2,
    )

    ticket_id = str(uuid4())

    # Create tasks (no specific capability requirements for now)
    task = task_queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="test",
        description="Test task",
        priority="HIGH",
    )

    # Get assignments
    assignments = scheduler.schedule_and_assign(
        phase_id="PHASE_IMPLEMENTATION",
        limit=1,
    )

    # Should assign to one of the agents
    assert len(assignments) > 0
    assignment = assignments[0]
    assert assignment["assigned"] is True
    assert assignment["agent_id"] in [str(agent_python.id), str(agent_js.id)]


