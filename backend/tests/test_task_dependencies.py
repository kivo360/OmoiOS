"""Tests for task dependencies and blocking functionality."""

from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService


def test_enqueue_task_with_dependencies(db_service: DatabaseService):
    """Test enqueueing a task with dependencies."""
    queue = TaskQueueService(db_service)

    # Create ticket
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Ticket",
            phase_id="PHASE_IMPLEMENTATION",
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.flush()
        ticket_id = ticket.id

    # Create first task (no dependencies)
    task1 = queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="setup",
        description="Setup task",
        priority="HIGH",
    )

    # Create second task that depends on first
    task2 = queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="implement",
        description="Implementation task",
        priority="HIGH",
        dependencies={"depends_on": [task1.id]},
    )

    assert task2.dependencies == {"depends_on": [task1.id]}
    assert task1.dependencies is None


def test_get_next_task_respects_dependencies(db_service: DatabaseService):
    """Test that get_next_task only returns tasks with completed dependencies."""
    queue = TaskQueueService(db_service)

    # Create ticket
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Ticket",
            phase_id="PHASE_IMPLEMENTATION",
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.flush()
        ticket_id = ticket.id

    # Create task with no dependencies
    task1 = queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="setup",
        description="Setup task",
        priority="MEDIUM",
    )

    # Create task that depends on task1
    task2 = queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="implement",
        description="Implementation task",
        priority="HIGH",  # Higher priority but blocked
        dependencies={"depends_on": [task1.id]},
    )

    # get_next_task should return task1 (no dependencies), not task2 (blocked)
    next_task = queue.get_next_task("PHASE_IMPLEMENTATION")
    assert next_task is not None
    assert next_task.id == task1.id

    # Complete task1
    queue.update_task_status(task1.id, "completed")

    # Now task2 should be available
    next_task = queue.get_next_task("PHASE_IMPLEMENTATION")
    assert next_task is not None
    assert next_task.id == task2.id


def test_check_dependencies_complete(db_service: DatabaseService):
    """Test checking if dependencies are complete."""
    queue = TaskQueueService(db_service)

    # Create ticket
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Ticket",
            phase_id="PHASE_IMPLEMENTATION",
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.flush()
        ticket_id = ticket.id

    # Create dependency task
    task1 = queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="setup",
        description="Setup task",
        priority="HIGH",
    )

    # Create dependent task
    task2 = queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="implement",
        description="Implementation task",
        priority="HIGH",
        dependencies={"depends_on": [task1.id]},
    )

    # Dependencies should be incomplete
    assert queue.check_dependencies_complete(task2.id) is False

    # Complete dependency
    queue.update_task_status(task1.id, "completed")

    # Dependencies should now be complete
    assert queue.check_dependencies_complete(task2.id) is True


def test_get_blocked_tasks(db_service: DatabaseService):
    """Test getting tasks blocked by a specific task."""
    queue = TaskQueueService(db_service)

    # Create ticket
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Ticket",
            phase_id="PHASE_IMPLEMENTATION",
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.flush()
        ticket_id = ticket.id

    # Create blocking task
    task1 = queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="setup",
        description="Setup task",
        priority="HIGH",
    )

    # Create tasks that depend on task1
    task2 = queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="implement",
        description="Implementation task 1",
        priority="HIGH",
        dependencies={"depends_on": [task1.id]},
    )

    task3 = queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="implement",
        description="Implementation task 2",
        priority="MEDIUM",
        dependencies={"depends_on": [task1.id]},
    )

    # Get blocked tasks
    blocked = queue.get_blocked_tasks(task1.id)
    assert len(blocked) == 2
    blocked_ids = {t.id for t in blocked}
    assert task2.id in blocked_ids
    assert task3.id in blocked_ids


def test_detect_circular_dependencies(db_service: DatabaseService):
    """Test circular dependency detection."""
    queue = TaskQueueService(db_service)

    # Create ticket
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Ticket",
            phase_id="PHASE_IMPLEMENTATION",
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.flush()
        ticket_id = ticket.id

    # Create tasks
    task1 = queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="task1",
        description="Task 1",
        priority="HIGH",
    )

    task2 = queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="task2",
        description="Task 2",
        priority="HIGH",
    )

    task3 = queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="task3",
        description="Task 3",
        priority="HIGH",
    )

    # Create circular dependency: task1 -> task2 -> task3 -> task1
    with db_service.get_session() as session:
        task1_obj = session.query(Task).filter(Task.id == task1.id).first()
        task1_obj.dependencies = {"depends_on": [task2.id]}
        task2_obj = session.query(Task).filter(Task.id == task2.id).first()
        task2_obj.dependencies = {"depends_on": [task3.id]}
        task3_obj = session.query(Task).filter(Task.id == task3.id).first()
        task3_obj.dependencies = {"depends_on": [task1.id]}
        session.commit()

    # Detect circular dependency starting from task1
    cycle = queue.detect_circular_dependencies(task1.id, [task2.id])
    assert cycle is not None
    assert len(cycle) >= 3  # Should include at least task1, task2, task3


def test_multiple_dependencies(db_service: DatabaseService):
    """Test task with multiple dependencies."""
    queue = TaskQueueService(db_service)

    # Create ticket
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Ticket",
            phase_id="PHASE_IMPLEMENTATION",
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.flush()
        ticket_id = ticket.id

    # Create multiple dependency tasks
    task1 = queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="setup1",
        description="Setup task 1",
        priority="HIGH",
    )

    task2 = queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="setup2",
        description="Setup task 2",
        priority="HIGH",
    )

    # Create task that depends on both
    task3 = queue.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_IMPLEMENTATION",
        task_type="implement",
        description="Implementation task",
        priority="HIGH",
        dependencies={"depends_on": [task1.id, task2.id]},
    )

    # Dependencies should be incomplete
    assert queue.check_dependencies_complete(task3.id) is False

    # Complete one dependency
    queue.update_task_status(task1.id, "completed")
    assert queue.check_dependencies_complete(task3.id) is False

    # Complete both dependencies
    queue.update_task_status(task2.id, "completed")
    assert queue.check_dependencies_complete(task3.id) is True
