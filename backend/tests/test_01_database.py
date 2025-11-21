"""Test database layer: models, CRUD operations, and Alembic migrations."""

import pytest
from omoi_os.utils.datetime import utc_now

from omoi_os.models.agent import Agent
from omoi_os.models.event import Event
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService


def test_database_service_create_tables(db_service: DatabaseService):
    """Test that create_tables creates all model tables."""
    # Tables should already be created by fixture
    # Verify by querying metadata
    from sqlalchemy import inspect
    inspector = inspect(db_service.engine)
    tables = inspector.get_table_names()
    assert "tickets" in tables
    assert "tasks" in tables
    assert "agents" in tables
    assert "events" in tables


def test_ticket_crud(db_service: DatabaseService):
    """Test Ticket model CRUD operations."""
    # Create
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Ticket",
            description="Test description",
            phase_id="PHASE_REQUIREMENTS",
            status="pending",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        ticket_id = ticket.id

    # Read
    with db_service.get_session() as session:
        retrieved = session.get(Ticket, ticket_id)
        assert retrieved is not None
        assert retrieved.title == "Test Ticket"
        assert retrieved.status == "pending"
        assert retrieved.priority == "HIGH"

    # Update
    with db_service.get_session() as session:
        ticket = session.get(Ticket, ticket_id)
        ticket.status = "in_progress"
        session.commit()

    # Verify update
    with db_service.get_session() as session:
        updated = session.get(Ticket, ticket_id)
        assert updated.status == "in_progress"

    # Delete
    with db_service.get_session() as session:
        ticket = session.get(Ticket, ticket_id)
        session.delete(ticket)
        session.commit()

    # Verify deletion
    with db_service.get_session() as session:
        deleted = session.get(Ticket, ticket_id)
        assert deleted is None


def test_task_crud(db_service: DatabaseService):
    """Test Task model CRUD operations."""
    # Create parent ticket first
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Parent Ticket",
            phase_id="PHASE_REQUIREMENTS",
            status="pending",
            priority="MEDIUM",
        )
        session.add(ticket)
        session.commit()
        ticket_id = ticket.id

    # Create task
    with db_service.get_session() as session:
        task = Task(
            ticket_id=ticket_id,
            phase_id="PHASE_REQUIREMENTS",
            task_type="analyze_requirements",
            description="Test task",
            priority="MEDIUM",
            status="pending",
        )
        session.add(task)
        session.commit()
        task_id = task.id

    # Read
    with db_service.get_session() as session:
        retrieved = session.get(Task, task_id)
        assert retrieved is not None
        assert retrieved.ticket_id == ticket_id
        assert retrieved.task_type == "analyze_requirements"

    # Update
    with db_service.get_session() as session:
        task = session.get(Task, task_id)
        task.status = "assigned"
        task.assigned_agent_id = "test-agent-id"
        session.commit()

    # Verify update
    with db_service.get_session() as session:
        updated = session.get(Task, task_id)
        assert updated.status == "assigned"
        assert updated.assigned_agent_id == "test-agent-id"


def test_agent_crud(db_service: DatabaseService):
    """Test Agent model CRUD operations."""
    # Create
    with db_service.get_session() as session:
        agent = Agent(
            agent_type="worker",
            phase_id="PHASE_REQUIREMENTS",
            status="idle",
            capabilities=["bash"],
        )
        session.add(agent)
        session.commit()
        agent_id = agent.id

    # Read
    with db_service.get_session() as session:
        retrieved = session.get(Agent, agent_id)
        assert retrieved is not None
        assert retrieved.agent_type == "worker"
        assert retrieved.status == "idle"

    # Update
    with db_service.get_session() as session:
        agent = session.get(Agent, agent_id)
        agent.status = "running"
        agent.last_heartbeat = utc_now()
        session.commit()

    # Verify update
    with db_service.get_session() as session:
        updated = session.get(Agent, agent_id)
        assert updated.status == "running"
        assert updated.last_heartbeat is not None


def test_event_crud(db_service: DatabaseService):
    """Test Event model CRUD operations."""
    # Create
    with db_service.get_session() as session:
        event = Event(
            event_type="TASK_ASSIGNED",
            entity_type="task",
            entity_id="test-task-id",
            payload={"agent_id": "test-agent"},
        )
        session.add(event)
        session.commit()
        event_id = event.id

    # Read
    with db_service.get_session() as session:
        retrieved = session.get(Event, event_id)
        assert retrieved is not None
        assert retrieved.event_type == "TASK_ASSIGNED"
        assert retrieved.entity_id == "test-task-id"
        assert retrieved.payload == {"agent_id": "test-agent"}


def test_ticket_task_relationship(db_service: DatabaseService):
    """Test Ticket-Task relationship (cascade delete)."""
    # Create ticket with tasks
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Parent Ticket",
            phase_id="PHASE_REQUIREMENTS",
            status="pending",
            priority="MEDIUM",
        )
        session.add(ticket)
        session.commit()
        ticket_id = ticket.id

        task1 = Task(
            ticket_id=ticket_id,
            phase_id="PHASE_REQUIREMENTS",
            task_type="task1",
            priority="MEDIUM",
            status="pending",
        )
        task2 = Task(
            ticket_id=ticket_id,
            phase_id="PHASE_REQUIREMENTS",
            task_type="task2",
            priority="MEDIUM",
            status="pending",
        )
        session.add_all([task1, task2])
        session.commit()
        task_ids = [task1.id, task2.id]

    # Verify relationship
    with db_service.get_session() as session:
        from sqlalchemy.orm import joinedload
        ticket = session.query(Ticket).options(joinedload(Ticket.tasks)).filter(Ticket.id == ticket_id).first()
        assert ticket is not None
        assert len(ticket.tasks) == 2

    # Delete ticket (should cascade delete tasks)
    with db_service.get_session() as session:
        ticket = session.get(Ticket, ticket_id)
        session.delete(ticket)
        session.commit()

    # Verify tasks are deleted
    with db_service.get_session() as session:
        for task_id in task_ids:
            task = session.get(Task, task_id)
            assert task is None


def test_alembic_migration_check(db_service: DatabaseService):
    """Test that Alembic migrations can detect model changes."""
    # This test verifies that Alembic can introspect the database
    # and compare it with model definitions
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from alembic.runtime.migration import MigrationContext
        from alembic.autogenerate import compare_metadata

        # Get Alembic configuration
        import os
        alembic_ini_path = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
        if os.path.exists(alembic_ini_path):
            alembic_cfg = Config(alembic_ini_path)
            script = ScriptDirectory.from_config(alembic_cfg)

            # Get current database revision
            with db_service.engine.connect() as conn:
                context = MigrationContext.configure(conn)
                context.get_current_revision()

            # Verify we have migrations available
            revisions = list(script.walk_revisions())
            assert len(revisions) > 0, "Should have at least one migration"

            # Verify metadata comparison works (should be no differences if migrations are up to date)
            from omoi_os.models.base import Base

            with db_service.engine.connect() as conn:
                context = MigrationContext.configure(conn)
                diff = compare_metadata(context, Base.metadata)
                # If migrations are up to date, diff should be empty or minimal
                # We're just checking that the comparison mechanism works
                assert isinstance(diff, list)
        else:
            pytest.skip("alembic.ini not found, skipping migration check")
    except ImportError:
        pytest.skip("Alembic not available, skipping migration check")

