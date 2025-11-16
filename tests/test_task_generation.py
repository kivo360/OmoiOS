"""Tests for phase-specific task generation."""

import pytest

from omoi_os.models.phases import Phase
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.task_generator import TaskGeneratorService


def test_get_templates_for_phase():
    """Test getting templates for a phase."""
    generator = TaskGeneratorService(None, None)
    templates = generator.get_templates_for_phase(Phase.REQUIREMENTS.value)
    
    assert len(templates) > 0
    assert all("task_type" in t for t in templates)
    assert all("description_template" in t for t in templates)
    assert all("priority" in t for t in templates)


def test_get_templates_for_all_phases():
    """Test that all phases have templates defined."""
    generator = TaskGeneratorService(None, None)
    
    for phase in Phase:
        templates = generator.get_templates_for_phase(phase.value)
        assert len(templates) > 0, f"No templates found for phase {phase.value}"


def test_generate_task_from_template(
    db_service: DatabaseService, task_queue_service: TaskQueueService
):
    """Test generating a single task from template."""
    # Create ticket
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Feature",
            description="Test",
            phase_id=Phase.REQUIREMENTS.value,
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        session.expunge(ticket)

    # Generate task from template
    generator = TaskGeneratorService(db_service, task_queue_service)
    template = {
        "task_type": "analyze_requirements",
        "description_template": "Analyze: {ticket_title}",
        "priority": "HIGH",
    }
    task = generator.generate_task_from_template(ticket, template)

    assert task is not None
    assert task.ticket_id == ticket.id
    assert "Test Feature" in task.description
    assert task.priority == "HIGH"
    assert task.task_type == "analyze_requirements"
    assert task.phase_id == ticket.phase_id
    assert task.status == "pending"


def test_generate_task_from_template_with_dependencies(
    db_service: DatabaseService, task_queue_service: TaskQueueService
):
    """Test generating a task with dependencies."""
    # Create ticket and dependency task
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Feature",
            description="Test",
            phase_id=Phase.REQUIREMENTS.value,
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        session.expunge(ticket)

    # Create a dependency task
    dep_task = task_queue_service.enqueue_task(
        ticket_id=ticket.id,
        phase_id=ticket.phase_id,
        task_type="dep_task",
        description="Dependency task",
        priority="HIGH",
    )

    # Generate task with dependencies
    generator = TaskGeneratorService(db_service, task_queue_service)
    template = {
        "task_type": "analyze_requirements",
        "description_template": "Analyze: {ticket_title}",
        "priority": "HIGH",
    }
    task = generator.generate_task_from_template(
        ticket, template, dependencies=[dep_task.id]
    )

    assert task is not None
    assert task.dependencies is not None
    assert "depends_on" in task.dependencies
    assert dep_task.id in task.dependencies["depends_on"]


def test_generate_phase_tasks(
    db_service: DatabaseService, task_queue_service: TaskQueueService
):
    """Test generating all tasks for a phase."""
    # Create ticket
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Feature",
            description="Test",
            phase_id=Phase.REQUIREMENTS.value,
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        ticket_id = ticket.id
        session.expunge(ticket)

    # Generate tasks
    generator = TaskGeneratorService(db_service, task_queue_service)
    tasks = generator.generate_phase_tasks(ticket_id, Phase.REQUIREMENTS.value)

    # Should generate at least 2 tasks for REQUIREMENTS phase
    assert len(tasks) >= 2
    assert all(task.ticket_id == ticket_id for task in tasks)
    assert all(task.phase_id == Phase.REQUIREMENTS.value for task in tasks)
    assert all(task.status == "pending" for task in tasks)


def test_generate_phase_tasks_for_all_phases(
    db_service: DatabaseService, task_queue_service: TaskQueueService
):
    """Test generating tasks for all phases."""
    # Create ticket for each phase
    for phase in Phase:
        with db_service.get_session() as session:
            ticket = Ticket(
                title=f"Test {phase.value}",
                description="Test",
                phase_id=phase.value,
                status="pending",
                priority="HIGH",
            )
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            ticket_id = ticket.id
            session.expunge(ticket)

        # Generate tasks
        generator = TaskGeneratorService(db_service, task_queue_service)
        tasks = generator.generate_phase_tasks(ticket_id, phase.value)

        assert len(tasks) > 0, f"No tasks generated for phase {phase.value}"
        assert all(task.phase_id == phase.value for task in tasks)


def test_template_variable_substitution(
    db_service: DatabaseService, task_queue_service: TaskQueueService
):
    """Test that template variables are substituted correctly."""
    # Create ticket with specific title
    with db_service.get_session() as session:
        ticket = Ticket(
            title="My Special Feature",
            description="Test",
            phase_id=Phase.IMPLEMENTATION.value,
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        session.expunge(ticket)

    generator = TaskGeneratorService(db_service, task_queue_service)
    template = {
        "task_type": "implement_feature",
        "description_template": "Implement: {ticket_title}",
        "priority": "HIGH",
    }
    task = generator.generate_task_from_template(ticket, template)

    assert "My Special Feature" in task.description
    assert task.description == "Implement: My Special Feature"


def test_generate_phase_tasks_ticket_not_found(
    db_service: DatabaseService, task_queue_service: TaskQueueService
):
    """Test generating tasks for non-existent ticket."""
    generator = TaskGeneratorService(db_service, task_queue_service)
    
    with pytest.raises(ValueError, match="Ticket not found"):
        generator.generate_phase_tasks("nonexistent-id", Phase.REQUIREMENTS.value)


def test_generate_phase_tasks_invalid_phase(
    db_service: DatabaseService, task_queue_service: TaskQueueService
):
    """Test generating tasks for invalid phase."""
    # Create ticket
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Feature",
            description="Test",
            phase_id=Phase.REQUIREMENTS.value,
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        ticket_id = ticket.id
        session.expunge(ticket)

    generator = TaskGeneratorService(db_service, task_queue_service)
    tasks = generator.generate_phase_tasks(ticket_id, "INVALID_PHASE")
    
    # Should return empty list for invalid phase
    assert len(tasks) == 0


def test_task_priorities_preserved(
    db_service: DatabaseService, task_queue_service: TaskQueueService
):
    """Test that task priorities from templates are preserved."""
    # Create ticket
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Feature",
            description="Test",
            phase_id=Phase.DEPLOYMENT.value,
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        ticket_id = ticket.id
        session.expunge(ticket)

    # Generate tasks for deployment phase
    generator = TaskGeneratorService(db_service, task_queue_service)
    tasks = generator.generate_phase_tasks(ticket_id, Phase.DEPLOYMENT.value)

    # Check that at least one task has CRITICAL priority (deploy_feature)
    priorities = [task.priority for task in tasks]
    assert "CRITICAL" in priorities


def test_multiple_variable_substitution(
    db_service: DatabaseService, task_queue_service: TaskQueueService
):
    """Test template with multiple variable substitutions."""
    # Create ticket
    with db_service.get_session() as session:
        ticket = Ticket(
            title="User Authentication",
            description="Add OAuth2 support",
            phase_id=Phase.TESTING.value,
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        session.expunge(ticket)

    generator = TaskGeneratorService(db_service, task_queue_service)
    template = {
        "task_type": "custom_test",
        "description_template": "Test {ticket_title} - Priority: {ticket_priority}",
        "priority": "HIGH",
    }
    task = generator.generate_task_from_template(ticket, template)

    assert "User Authentication" in task.description
    assert "HIGH" in task.description
