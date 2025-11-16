"""Test task queue service: enqueue, get_next_task, assign, update status."""

import pytest

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
    task_low = task_queue_service.enqueue_task(
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


def test_get_next_task_phase_filtering(task_queue_service: TaskQueueService, sample_ticket: Ticket):
    """Test get_next_task only returns tasks for specified phase."""
    # Create tasks in different phases
    task1 = task_queue_service.enqueue_task(
        ticket_id=sample_ticket.id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="task1",
        description="Requirements task",
        priority="HIGH",
    )

    task2 = task_queue_service.enqueue_task(
        ticket_id=sample_ticket.id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="task2",
        description="Implementation task",
        priority="HIGH",
    )

    # Get task for PHASE_REQUIREMENTS
    next_task = task_queue_service.get_next_task("PHASE_REQUIREMENTS")
    assert next_task is not None
    assert next_task.id == task1.id
    assert next_task.phase_id == "PHASE_REQUIREMENTS"

    # Get task for PHASE_IMPLEMENTATION
    next_task = task_queue_service.get_next_task("PHASE_IMPLEMENTATION")
    assert next_task is not None
    assert next_task.id == task2.id
    assert next_task.phase_id == "PHASE_IMPLEMENTATION"


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


def test_update_task_status_completed(task_queue_service: TaskQueueService, sample_task: Task):
    """Test updating task status to completed with result."""
    result = {"status": "success", "output": "Task completed"}

    task_queue_service.update_task_status(
        sample_task.id,
        "completed",
        result=result,
        conversation_id="conv-123",
    )

    with task_queue_service.db.get_session() as session:
        task = session.get(Task, sample_task.id)
        assert task.status == "completed"
        assert task.result == result
        assert task.conversation_id == "conv-123"
        assert task.completed_at is not None


def test_update_task_status_failed(task_queue_service: TaskQueueService, sample_task: Task):
    """Test updating task status to failed with error message."""
    error_message = "Task execution failed"

    task_queue_service.update_task_status(
        sample_task.id,
        "failed",
        error_message=error_message,
    )

    with task_queue_service.db.get_session() as session:
        task = session.get(Task, sample_task.id)
        assert task.status == "failed"
        assert task.error_message == error_message
        assert task.completed_at is not None


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

    # Create unassigned task
    task3 = task_queue_service.enqueue_task(
        ticket_id=sample_ticket.id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="task3",
        description="Task 3",
        priority="LOW",
    )

    # Get assigned tasks
    assigned = task_queue_service.get_assigned_tasks(agent_id)
    assert len(assigned) == 2
    assigned_ids = {t.id for t in assigned}
    assert task1.id in assigned_ids
    assert task2.id in assigned_ids
    assert task3.id not in assigned_ids

