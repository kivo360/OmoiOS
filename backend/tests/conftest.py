"""Pytest configuration and shared fixtures."""

import os
import tempfile
from typing import Generator
from uuid import uuid4

# =============================================================================
# CRITICAL: Set test environment BEFORE importing any omoi_os modules
# This prevents the slow ML embedding model from loading during tests
# =============================================================================
os.environ.setdefault("EMBEDDING_PROVIDER", "fireworks")  # Skip local model loading
os.environ.setdefault("TESTING", "true")

import pytest
from fastapi.testclient import TestClient

from omoi_os.models.agent import Agent
from omoi_os.models.ticket import Ticket
from omoi_os.models.task import Task
from omoi_os.models.user import User
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.task_queue import TaskQueueService


# =============================================================================
# API CLIENT FIXTURES
# =============================================================================


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a FastAPI test client (unauthenticated).

    The app's lifespan respects TESTING=true (set above) and skips:
    - Background monitoring loops (heartbeat, diagnostic, anomaly, etc.)
    - MCP server startup

    This allows testing endpoints without hanging on background tasks.
    """
    from omoi_os.api.main import app

    # Now safe to enter lifespan because TESTING=true disables background loops
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def test_user(db_service: DatabaseService) -> User:
    """Create a test user in the database.

    Returns a User object that can be used for authentication tests.
    The password is 'TestPass123!' before hashing.
    """
    from omoi_os.services.auth_service import AuthService

    auth_service = AuthService(
        db=db_service,
        jwt_secret="test-secret-key-for-testing-only",
        jwt_algorithm="HS256",
        access_token_expire_minutes=15,
        refresh_token_expire_days=7,
    )

    with db_service.get_session() as session:
        user = User(
            id=uuid4(),
            email=f"testuser_{uuid4().hex[:8]}@example.com",
            full_name="Test User",
            hashed_password=auth_service.hash_password("TestPass123!"),
            is_active=True,
            is_verified=True,
            is_super_admin=False,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


@pytest.fixture
def admin_user(db_service: DatabaseService) -> User:
    """Create a test admin user in the database."""
    from omoi_os.services.auth_service import AuthService

    auth_service = AuthService(
        db=db_service,
        jwt_secret="test-secret-key-for-testing-only",
        jwt_algorithm="HS256",
        access_token_expire_minutes=15,
        refresh_token_expire_days=7,
    )

    with db_service.get_session() as session:
        user = User(
            id=uuid4(),
            email=f"admin_{uuid4().hex[:8]}@example.com",
            full_name="Admin User",
            hashed_password=auth_service.hash_password("AdminPass123!"),
            is_active=True,
            is_verified=True,
            is_super_admin=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


@pytest.fixture
def auth_token(db_service: DatabaseService, test_user: User) -> str:
    """Get a valid JWT access token for the test user.

    Use this when you need just the token string.
    """
    from omoi_os.services.auth_service import AuthService

    auth_service = AuthService(
        db=db_service,
        jwt_secret="test-secret-key-for-testing-only",
        jwt_algorithm="HS256",
        access_token_expire_minutes=15,
        refresh_token_expire_days=7,
    )
    return auth_service.create_access_token(test_user.id)


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    """Get authorization headers with Bearer token.

    Use this with the regular client fixture:
        response = client.get("/api/v1/auth/me", headers=auth_headers)
    """
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def authenticated_client(
    client: TestClient, auth_headers: dict
) -> Generator[TestClient, None, None]:
    """TestClient with authentication headers pre-configured.

    All requests made with this client will include the auth token.
    Note: This creates a real user and token in the test database.
    """
    # Store original headers
    original_headers = client.headers.copy()

    # Add auth headers
    client.headers.update(auth_headers)

    yield client

    # Restore original headers
    client.headers = original_headers


@pytest.fixture
def mock_user() -> User:
    """Create a mock user object (not persisted to database).

    Use this with mock_authenticated_client for fast unit tests
    that don't need real database users.
    """
    from datetime import datetime, timezone

    return User(
        id=uuid4(),
        email="mockuser@example.com",
        full_name="Mock User",
        hashed_password="not-a-real-hash",
        is_active=True,
        is_verified=True,
        is_super_admin=False,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_authenticated_client(
    client: TestClient,
    mock_user: User,
) -> Generator[TestClient, None, None]:
    """TestClient with mocked authentication (no real JWT).

    This overrides the get_current_user dependency to return mock_user
    directly, bypassing JWT validation. Fastest option for unit tests.

    Example:
        def test_protected_route(mock_authenticated_client):
            response = mock_authenticated_client.get("/api/v1/auth/me")
            assert response.status_code == 200
    """
    from omoi_os.api.main import app
    from omoi_os.api.dependencies import get_current_user

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    yield client

    # Clean up override
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Get test database URL from environment or use default."""
    return os.getenv(
        "DATABASE_URL_TEST",
        "postgresql+psycopg://postgres:postgres@localhost:15432/app_db",
    )


@pytest.fixture(scope="function")
def db_service(test_database_url: str) -> Generator[DatabaseService, None, None]:
    """
    Create a fresh database service for each test.

    Creates tables before test, drops them after.
    Uses session-isolated data - tests run in transactions that are rolled back.
    """
    # Extract database name from URL and create it if it doesn't exist
    from urllib.parse import urlparse
    from sqlalchemy import text

    parsed = urlparse(test_database_url)
    db_name = parsed.path.lstrip("/")

    # Connect to postgres database to create test database
    admin_url = test_database_url.rsplit("/", 1)[0] + "/postgres"
    admin_db = None
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
    finally:
        # Dispose admin connection
        if admin_db:
            admin_db.engine.dispose()

    db = DatabaseService(test_database_url)
    db.create_tables()
    try:
        yield db
    finally:
        # Clean up: dispose engine first (releases connections), then drop
        db.engine.dispose()
        # Skip drop_tables to avoid blocking on lock wait
        # Tables will be recreated fresh via create_tables() in next test


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
def collaboration_service(
    db_service: DatabaseService, event_bus_service: EventBusService
):
    """Create a collaboration service."""
    from omoi_os.services.collaboration import CollaborationService

    return CollaborationService(db_service, event_bus_service)


@pytest.fixture
def lock_service(db_service: DatabaseService):
    """Create a resource lock service."""
    from omoi_os.services.resource_lock import ResourceLockService

    return ResourceLockService(db_service)


@pytest.fixture
def monitor_service(db_service: DatabaseService, event_bus_service: EventBusService):
    """Create a monitor service."""
    from omoi_os.services.monitor import MonitorService

    return MonitorService(db_service, event_bus_service)


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


# =============================================================================
# SANDBOX SYSTEM FIXTURES
# =============================================================================


@pytest.fixture
def sample_sandbox_event() -> dict:
    """Standard sandbox event payload for testing."""
    return {
        "event_type": "agent.tool_use",
        "event_data": {
            "tool": "bash",
            "command": "npm install",
            "exit_code": 0,
        },
        "source": "agent",
    }


@pytest.fixture
def sample_message() -> dict:
    """Standard message payload for testing."""
    return {
        "content": "Please focus on authentication first.",
        "message_type": "user_message",
    }


@pytest.fixture
def sandbox_id() -> str:
    """Generate unique sandbox ID for test isolation."""
    return f"test-sandbox-{uuid4().hex[:8]}"


@pytest.fixture
def sample_task_with_sandbox(
    db_service: DatabaseService, sample_ticket: Ticket
) -> Task:
    """Create a task WITH sandbox_id for sandbox mode tests."""
    with db_service.get_session() as session:
        task = Task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Test task in sandbox mode",
            status="running",
            sandbox_id=f"sandbox-{uuid4().hex[:8]}",
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        session.expunge(task)
        return task
