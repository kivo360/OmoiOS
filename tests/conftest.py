"""Pytest configuration and shared fixtures."""

import os
import tempfile
from typing import Generator

import pytest

from omoi_os.models.agent import Agent
from omoi_os.models.ticket import Ticket
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.task_queue import TaskQueueService


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Get test database URL from environment or use default."""
    return os.getenv(
        "DATABASE_URL_TEST",
        "postgresql+psycopg://postgres:postgres@localhost:15432/app_db_test",
    )


@pytest.fixture(scope="function")
def db_service(test_database_url: str) -> Generator[DatabaseService, None, None]:
    """
    Create a fresh database service for each test.

    Creates tables before test, drops them after.
    """
    # Extract database name from URL and create it if it doesn't exist
    from urllib.parse import urlparse
    from sqlalchemy import text
    
    parsed = urlparse(test_database_url)
    db_name = parsed.path.lstrip('/')
    
    # Connect to postgres database to create test database
    admin_url = test_database_url.rsplit('/', 1)[0] + '/postgres'
    try:
        admin_db = DatabaseService(admin_url)
        with admin_db.get_session() as session:
            # Check if database exists, create if not
            result = session.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
            ).fetchone()
            if not result:
                session.execute(text(f'CREATE DATABASE "{db_name}"'))
                session.commit()
    except Exception:
        # If we can't create the database, try to proceed anyway
        # (database might already exist or we don't have permissions)
        pass
    
    db = DatabaseService(test_database_url)
    db.create_tables()
    try:
        yield db
    finally:
        db.drop_tables()


@pytest.fixture
def task_queue_service(db_service: DatabaseService) -> TaskQueueService:
    """Create a task queue service with a test database."""
    return TaskQueueService(db_service)


@pytest.fixture
def redis_url() -> str:
    """Get Redis URL from environment or use fakeredis."""
    return os.getenv("REDIS_URL_TEST", "redis://localhost:16379")


@pytest.fixture
def event_bus_service(redis_url: str) -> EventBusService:
    """Create an event bus service."""
    return EventBusService(redis_url)


@pytest.fixture
def test_workspace_dir() -> str:
    """Create a temporary workspace directory for tests."""
    return tempfile.mkdtemp(prefix="omoi_test_workspace_")


@pytest.fixture
def sample_ticket(db_service: DatabaseService) -> Ticket:
    """Create a sample ticket for testing."""
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Ticket",
            description="Test description",
            phase_id="PHASE_REQUIREMENTS",
            status="pending",
            priority="MEDIUM",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        # Expunge so it can be used outside the session
        session.expunge(ticket)
        return ticket


@pytest.fixture
def sample_task(db_service: DatabaseService, sample_ticket: Ticket) -> Task:
    """Create a sample task for testing."""
    with db_service.get_session() as session:
        task = Task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_REQUIREMENTS",
            task_type="analyze_requirements",
            description="Test task description",
            priority="MEDIUM",
            status="pending",
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        # Expunge so it can be used outside the session
        session.expunge(task)
        return task


@pytest.fixture
def sample_agent(db_service: DatabaseService) -> Agent:
    """Create a sample agent for testing."""
    with db_service.get_session() as session:
        agent = Agent(
            agent_type="worker",
            phase_id="PHASE_REQUIREMENTS",
            status="idle",
            capabilities=["bash", "file_editor"],
            capacity=2,
            health_status="healthy",
            tags=["python"],
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)
        # Expunge so it can be used outside the session
        session.expunge(agent)
        return agent

