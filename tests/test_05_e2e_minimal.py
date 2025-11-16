"""Minimal end-to-end flow test: create ticket → enqueue task → assign → execute."""

import os
from unittest.mock import Mock, patch

import pytest

from omoi_os.models.agent import Agent
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.agent_executor import AgentExecutor
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.task_queue import TaskQueueService


@pytest.fixture
def mock_agent_executor():
    """Create a mock AgentExecutor that simulates task execution."""
    executor = Mock(spec=AgentExecutor)
    executor.execute_task = Mock(return_value={
        "status": "finished",
        "event_count": 3,
        "cost": 0.10,
    })
    return executor


def test_e2e_minimal_flow(
    db_service: DatabaseService,
    task_queue_service: TaskQueueService,
    event_bus_service: EventBusService,
    mock_agent_executor: Mock,
):
    """Test complete flow: ticket → task → assign → execute."""
    # Step 1: Create a ticket
    with db_service.get_session() as session:
        ticket = Ticket(
            title="E2E Test Ticket",
            description="End-to-end test ticket",
            phase_id="PHASE_REQUIREMENTS",
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        ticket_id = ticket.id

    # Step 2: Enqueue a task for the ticket
    task = task_queue_service.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="analyze_requirements",
        description="Analyze requirements for E2E test ticket",
        priority="HIGH",
    )
    task_id = task.id

    # Verify task was created
    assert task.status == "pending"
    assert task.ticket_id == ticket_id

    # Step 3: Register an agent
    with db_service.get_session() as session:
        agent = Agent(
            agent_type="worker",
            phase_id="PHASE_REQUIREMENTS",
            status="idle",
            capabilities={"tools": ["bash", "file_editor"]},
        )
        session.add(agent)
        session.commit()
        agent_id = agent.id

    # Step 4: Assign task to agent
    task_queue_service.assign_task(task_id, agent_id)

    # Verify assignment
    with db_service.get_session() as session:
        task = session.get(Task, task_id)
        assert task.assigned_agent_id == agent_id
        assert task.status == "assigned"

    # Step 5: Publish TASK_ASSIGNED event
    assignment_event = SystemEvent(
        event_type="TASK_ASSIGNED",
        entity_type="task",
        entity_id=task_id,
        payload={"agent_id": agent_id},
    )
    event_bus_service.publish(assignment_event)

    # Step 6: Simulate worker execution (using mock)
    task_queue_service.update_task_status(task_id, "running")

    # Get task description from database (task is detached, so we need to re-query)
    with db_service.get_session() as session:
        task_obj = session.get(Task, task_id)
        task_description = task_obj.description or "" if task_obj else ""

    # Mock the agent executor execution
    result = mock_agent_executor.execute_task(task_description)

    # Step 7: Update task status to completed
    task_queue_service.update_task_status(
        task_id,
        "completed",
        result=result,
        conversation_id="conv-test-123",
    )

    # Step 8: Publish TASK_COMPLETED event
    completion_event = SystemEvent(
        event_type="TASK_COMPLETED",
        entity_type="task",
        entity_id=task_id,
        payload=result,
    )
    event_bus_service.publish(completion_event)

    # Step 9: Verify final state
    with db_service.get_session() as session:
        # Verify ticket status
        ticket = session.get(Ticket, ticket_id)
        assert ticket is not None

        # Verify task status
        task = session.get(Task, task_id)
        assert task.status == "completed"
        assert task.result == result
        assert task.conversation_id == "conv-test-123"
        assert task.completed_at is not None

        # Verify agent status
        agent = session.get(Agent, agent_id)
        assert agent.status == "idle"  # Should be idle after task completion


def test_e2e_task_failure_flow(
    db_service: DatabaseService,
    task_queue_service: TaskQueueService,
    event_bus_service: EventBusService,
):
    """Test E2E flow with task failure."""
    # Create ticket and task
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Failure Test Ticket",
            phase_id="PHASE_REQUIREMENTS",
            status="pending",
            priority="MEDIUM",
        )
        session.add(ticket)
        session.commit()
        ticket_id = ticket.id

    task = task_queue_service.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="test_task",
        description="Task that will fail",
        priority="MEDIUM",
    )

    # Register agent
    with db_service.get_session() as session:
        agent = Agent(
            agent_type="worker",
            phase_id="PHASE_REQUIREMENTS",
            status="idle",
        )
        session.add(agent)
        session.commit()
        agent_id = agent.id

    # Assign and start task
    task_queue_service.assign_task(task.id, agent_id)
    task_queue_service.update_task_status(task.id, "running")

    # Simulate failure
    error_message = "Task execution failed: timeout"
    task_queue_service.update_task_status(
        task.id,
        "failed",
        error_message=error_message,
    )

    # Publish failure event
    failure_event = SystemEvent(
        event_type="TASK_FAILED",
        entity_type="task",
        entity_id=task.id,
        payload={"error": error_message},
    )
    event_bus_service.publish(failure_event)

    # Verify failure state
    with db_service.get_session() as session:
        task = session.get(Task, task.id)
        assert task.status == "failed"
        assert task.error_message == error_message
        assert task.completed_at is not None


def test_e2e_multiple_tasks_per_ticket(
    db_service: DatabaseService,
    task_queue_service: TaskQueueService,
):
    """Test E2E flow with multiple tasks per ticket."""
    # Create ticket
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Multi-Task Ticket",
            phase_id="PHASE_REQUIREMENTS",
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        ticket_id = ticket.id

    # Enqueue multiple tasks
    task1 = task_queue_service.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="task1",
        description="First task",
        priority="HIGH",
    )

    task2 = task_queue_service.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="task2",
        description="Second task",
        priority="MEDIUM",
    )

    task3 = task_queue_service.enqueue_task(
        ticket_id=ticket_id,
        phase_id="PHASE_REQUIREMENTS",
        task_type="task3",
        description="Third task",
        priority="LOW",
    )

    # Verify all tasks are pending
    with db_service.get_session() as session:
        from sqlalchemy.orm import joinedload
        ticket = session.query(Ticket).options(joinedload(Ticket.tasks)).filter(Ticket.id == ticket_id).first()
        assert ticket is not None
        assert len(ticket.tasks) == 3

        # Verify priority ordering
        next_task = task_queue_service.get_next_task("PHASE_REQUIREMENTS")
        assert next_task.id == task1.id  # HIGH priority first

