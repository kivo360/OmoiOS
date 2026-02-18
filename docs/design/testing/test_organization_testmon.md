# Test Organization & Pytest-Testmon Integration Plan

**Created**: 2025-11-20
**Status**: Implementation Plan
**Purpose**: Reorganize test suite for better maintainability and integrate pytest-testmon for intelligent test execution

---

## Current Issues

1. **Flat structure** - All 57 test files in single `tests/` directory
2. **Inconsistent naming** - Mix of numbered (`test_01_`) and descriptive names
3. **No clear categorization** - Hard to run specific test suites
4. **Duplicate fixtures** - Many test files define similar fixtures
5. **No test monitoring** - All tests run every time, even for unchanged code

---

## Proposed Directory Structure

```
tests/
├── conftest.py                      # Root fixtures (db_service, event_bus, etc.)
├── pytest.ini                       # Moved from root (better organization)
├── __init__.py
│
├── unit/                            # Unit tests (fast, isolated)
│   ├── conftest.py                  # Unit-specific fixtures
│   ├── __init__.py
│   │
│   ├── models/                      # Model tests
│   │   ├── __init__.py
│   │   ├── test_ticket_model.py
│   │   ├── test_task_model.py
│   │   ├── test_agent_model.py
│   │   └── test_state_machines.py  # Ticket/Agent state machines
│   │
│   ├── services/                    # Service unit tests
│   │   ├── __init__.py
│   │   ├── test_database_service.py
│   │   ├── test_task_queue_service.py
│   │   ├── test_event_bus_service.py
│   │   ├── test_agent_health_service.py
│   │   ├── test_retry_logic.py
│   │   ├── test_timeout_logic.py
│   │   └── test_validation_service.py
│   │
│   ├── utils/                       # Utility tests
│   │   ├── __init__.py
│   │   ├── test_datetime_utils.py
│   │   └── test_helpers.py
│   │
│   └── auth/                        # Auth unit tests
│       ├── __init__.py
│       ├── test_auth_service.py
│       └── test_authorization_service.py
│
├── integration/                     # Integration tests (multi-component)
│   ├── conftest.py                  # Integration fixtures
│   ├── __init__.py
│   │
│   ├── core/                        # Core system integration
│   │   ├── __init__.py
│   │   ├── test_task_queue_with_db.py
│   │   ├── test_event_bus_with_redis.py
│   │   └── test_agent_executor_integration.py
│   │
│   ├── workflows/                   # Workflow tests
│   │   ├── __init__.py
│   │   ├── test_ace_workflow.py
│   │   ├── test_ticket_workflow.py
│   │   ├── test_validation_workflow.py
│   │   └── test_collaboration_workflow.py
│   │
│   ├── monitoring/                  # Monitoring system integration
│   │   ├── __init__.py
│   │   ├── test_intelligent_monitoring.py
│   │   ├── test_guardian_policies.py
│   │   ├── test_heartbeat_protocol.py
│   │   └── test_anomaly_detection.py
│   │
│   ├── memory/                      # Memory system integration
│   │   ├── __init__.py
│   │   ├── test_memory_service.py
│   │   ├── test_similarity_search.py
│   │   └── test_pattern_learning.py
│   │
│   ├── gateway/                     # LLM Gateway integration
│   │   ├── __init__.py
│   │   ├── test_fireworks_gateway.py
│   │   ├── test_pydantic_ai_gateway.py
│   │   └── test_llm_service.py
│   │
│   └── api/                         # API integration tests
│       ├── __init__.py
│       ├── test_websocket_events.py
│       ├── test_board_api.py
│       └── test_phase_api.py
│
├── e2e/                             # End-to-end tests (full workflows)
│   ├── conftest.py                  # E2E fixtures
│   ├── __init__.py
│   │
│   ├── test_minimal_flow.py         # Minimal E2E smoke test
│   ├── test_parallel_execution.py   # Parallel agent workflow
│   ├── test_full_ticket_lifecycle.py
│   └── test_diagnostic_runs.py
│
├── performance/                     # Performance/load tests
│   ├── __init__.py
│   ├── test_worker_concurrency.py
│   ├── test_budget_enforcement.py
│   └── test_dynamic_task_scoring.py
│
├── fixtures/                        # Shared fixture modules
│   ├── __init__.py
│   ├── agents.py                    # Agent fixtures
│   ├── tickets.py                   # Ticket fixtures
│   ├── tasks.py                     # Task fixtures
│   ├── database.py                  # Database fixtures
│   └── mocks.py                     # Mock objects
│
└── helpers/                         # Test utilities
    ├── __init__.py
    ├── assertions.py                # Custom assertions
    ├── builders.py                  # Test data builders
    └── matchers.py                  # Custom matchers
```

---

## Migration Mapping

### Current → New Structure

| Current File | New Location | Category |
|--------------|--------------|----------|
| `test_01_database.py` | `unit/services/test_database_service.py` | Unit |
| `test_02_task_queue.py` | `unit/services/test_task_queue_service.py` | Unit |
| `test_03_event_bus.py` | `unit/services/test_event_bus_service.py` | Unit |
| `test_04_agent_executor.py` | `integration/core/test_agent_executor_integration.py` | Integration |
| `test_05_e2e_minimal.py` | `e2e/test_minimal_flow.py` | E2E |
| `test_agent_health.py` | `unit/services/test_agent_health_service.py` | Unit |
| `test_retry_logic.py` | `unit/services/test_retry_logic.py` | Unit |
| `test_task_timeout.py` | `unit/services/test_timeout_logic.py` | Unit |
| `test_auth_service.py` | `unit/auth/test_auth_service.py` | Unit |
| `test_authorization_service.py` | `unit/auth/test_authorization_service.py` | Unit |
| `test_ace_workflow.py` | `integration/workflows/test_ace_workflow.py` | Integration |
| `test_intelligent_monitoring.py` | `integration/monitoring/test_intelligent_monitoring.py` | Integration |
| `test_guardian.py` | `integration/monitoring/test_guardian_policies.py` | Integration |
| `test_memory.py` | `integration/memory/test_memory_service.py` | Integration |
| `test_websocket_events.py` | `integration/api/test_websocket_events.py` | Integration |
| `test_e2e_parallel.py` | `e2e/test_parallel_execution.py` | E2E |
| `test_worker_concurrency.py` | `performance/test_worker_concurrency.py` | Performance |

---

## Configuration Strategy for Tests

### YAML Configuration (Application Settings)

All test configuration goes in `config/test.yaml`:

```yaml
# config/test.yaml
# Test environment configuration (fast intervals, disabled features)

monitoring:
  guardian_interval_seconds: 1
  conductor_interval_seconds: 2
  health_check_interval_seconds: 1
  auto_steering_enabled: false

task_queue:
  age_ceiling: 60
  sla_urgency_window: 10
  starvation_limit: 120

worker:
  concurrency: 1
  heartbeat_interval_seconds: 1

features:
  enable_mcp_tools: false
  enable_github_sync: false
  enable_guardian: false  # Disable in most tests

testing:
  strict_mode: true
  fail_fast: false
  use_fakeredis: true
```

### Environment Variables (Secrets & URLs Only)

Only secrets and URLs go in `.env.test`:

```bash
# .env.test (GITIGNORED)
# pragma: allowlist secret
DATABASE_URL_TEST=postgresql+psycopg://postgres:postgres@localhost:15432/app_db_test
REDIS_URL_TEST=redis://localhost:16379/1
LLM_API_KEY=test-key-mock
AUTH_JWT_SECRET_KEY=test-secret-key
OMOIOS_ENV=test
```

### Test Fixtures Using YAML Config

```python
# tests/conftest.py

import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Ensure test environment configuration is loaded."""
    os.environ['OMOIOS_ENV'] = 'test'
    yield


@pytest.fixture(scope="function", autouse=True)
def clear_settings_cache():
    """Clear cached settings before each test."""
    from omoi_os.config import load_monitoring_settings, load_task_queue_settings

    # Clear LRU caches so tests get fresh config
    load_monitoring_settings.cache_clear()
    load_task_queue_settings.cache_clear()

    yield
```

---

## Pytest-Testmon Integration

### Installation

```bash
# Add pytest-testmon to test dependencies
uv add --group test pytest-testmon

# Add other recommended plugins
uv add --group test pytest-xdist    # Parallel execution
uv add --group test pytest-sugar    # Better output
uv add --group test pytest-timeout  # Timeout protection
uv add --group test pytest-randomly # Random order
```

### Updated pytest.ini

```ini
[pytest]
# Test discovery patterns
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Test paths
testpaths = tests

# Markers for test categorization
markers =
    unit: Unit tests for individual components (fast, isolated)
    integration: Integration tests for component interactions (moderate speed)
    e2e: End-to-end tests for full workflows (slow)
    performance: Performance and load tests (very slow)
    slow: Tests that take a long time to run
    requires_db: Tests that require a database connection
    requires_redis: Tests that require a Redis connection
    requires_llm: Tests that require LLM service
    smoke: Quick smoke tests for CI/CD
    critical: Critical path tests that must pass

# Output options
addopts =
    -v
    --strict-markers
    --tb=short
    --cov=omoi_os
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
    # Testmon options
    --testmon
    --suppress-no-test-exit-code

# Testmon configuration
[testmon]
# Track test execution and code changes
datafile = .testmondata
# Only run tests affected by code changes
changed_only = true

# Coverage options
[coverage:run]
source = omoi_os
omit =
    */tests/*
    */migrations/*
    */__pycache__/*
    */external/*

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstractmethod
    @abc.abstractmethod

# Minimum coverage thresholds
precision = 2
skip_covered = false
skip_empty = false
```

---

## Enhanced Conftest Structure

### Root conftest.py

```python
"""Root pytest configuration and shared fixtures.

Uses YAML configuration from config/test.yaml for all settings.
Only uses .env.test for secrets and URLs.
"""

import os
import tempfile
from typing import Generator
import pytest

from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.config import (
    load_database_settings,
    load_redis_settings,
    load_monitoring_settings,
    load_task_queue_settings,
)


# ============================================================================
# Session-scoped fixtures (expensive, shared across all tests)
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Ensure test environment is active.
    This loads config/test.yaml and .env.test
    """
    os.environ['OMOIOS_ENV'] = 'test'
    yield


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """
    Get test database URL from .env.test
    Falls back to default if not set.
    """
    return os.getenv(
        "DATABASE_URL_TEST",
        "postgresql+psycopg://postgres:postgres@localhost:15432/app_db_test",
    )


@pytest.fixture(scope="session")
def test_redis_url() -> str:
    """
    Get test Redis URL from .env.test
    Falls back to default if not set.
    """
    return os.getenv(
        "REDIS_URL_TEST",
        "redis://localhost:16379/1"
    )


# ============================================================================
# Function-scoped fixtures (fresh for each test)
# ============================================================================

@pytest.fixture(scope="function", autouse=True)
def clear_config_cache():
    """
    Clear settings cache before each test.
    Ensures tests get fresh configuration from YAML.
    """
    # Clear all settings caches
    load_database_settings.cache_clear()
    load_redis_settings.cache_clear()
    load_monitoring_settings.cache_clear()
    load_task_queue_settings.cache_clear()

    yield


@pytest.fixture(scope="function")
def db_service(test_database_url: str) -> Generator[DatabaseService, None, None]:
    """
    Create a fresh database service for each test.
    Uses URL from .env.test, but all other settings from config/test.yaml
    """
    from urllib.parse import urlparse
    from sqlalchemy import text

    parsed = urlparse(test_database_url)
    db_name = parsed.path.lstrip('/')

    admin_url = test_database_url.rsplit('/', 1)[0] + '/postgres'
    try:
        admin_db = DatabaseService(admin_url)
        with admin_db.get_session() as session:
            result = session.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
            ).fetchone()
            if not result:
                session.execute(text(f'CREATE DATABASE "{db_name}"'))
                session.commit()
    except Exception:
        pass

    db = DatabaseService(test_database_url)
    db.create_tables()
    try:
        yield db
    finally:
        db.drop_tables()


@pytest.fixture
def task_queue_service(db_service: DatabaseService) -> TaskQueueService:
    """
    Create a task queue service.
    Loads settings from config/test.yaml automatically.
    """
    return TaskQueueService(db_service)


@pytest.fixture
def event_bus_service(test_redis_url: str) -> EventBusService:
    """
    Create an event bus service.
    Uses Redis URL from .env.test
    """
    return EventBusService(test_redis_url)


# ============================================================================
# Configuration override helpers
# ============================================================================

@pytest.fixture
def override_monitoring_config(monkeypatch):
    """
    Helper to override monitoring settings in tests.

    Usage:
        def test_fast_monitoring(override_monitoring_config):
            override_monitoring_config(guardian_interval_seconds=0.1)
    """
    def _override(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setenv(f'MONITORING_{key.upper()}', str(value))
        load_monitoring_settings.cache_clear()

    return _override


@pytest.fixture
def override_task_queue_config(monkeypatch):
    """
    Helper to override task queue settings in tests.

    Usage:
        def test_custom_weights(override_task_queue_config):
            override_task_queue_config(w_p=0.5, w_a=0.3)
    """
    def _override(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setenv(f'TASK_QUEUE_{key.upper()}', str(value))
        load_task_queue_settings.cache_clear()

    return _override


# ============================================================================
# Pytest hooks for better reporting
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Ensure test environment is set
    os.environ['OMOIOS_ENV'] = 'test'

    config.addinivalue_line(
        "markers", "wip: Tests that are work in progress"
    )
    config.addinivalue_line(
        "markers", "skip_ci: Tests to skip in CI environment"
    )
    config.addinivalue_line(
        "markers", "requires_llm: Tests that require real LLM API"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on path."""
    for item in items:
        # Auto-mark based on directory
        if "unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e/" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.slow)
        elif "performance/" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)

        # Auto-mark database requirements
        if "db_service" in item.fixturenames:
            item.add_marker(pytest.mark.requires_db)

        # Auto-mark Redis requirements
        if "event_bus_service" in item.fixturenames or "redis" in str(item.fixturenames):
            item.add_marker(pytest.mark.requires_redis)


def pytest_sessionstart(session):
    """
    Called before test collection.
    Verify test configuration is loaded correctly.
    """
    # Verify test environment is set
    assert os.getenv('OMOIOS_ENV') == 'test', "OMOIOS_ENV must be 'test'"

    # Verify config/test.yaml exists
    from pathlib import Path
    test_config = Path("config/test.yaml")
    if not test_config.exists():
        pytest.exit(
            "config/test.yaml not found. Please create test configuration.",
            returncode=1
        )
```

### tests/fixtures/database.py

```python
"""Database-related fixtures."""

import pytest
from typing import Generator

from omoi_os.models.agent import Agent
from omoi_os.models.ticket import Ticket
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now


@pytest.fixture
def sample_ticket(db_service: DatabaseService) -> Ticket:
    """Create a sample ticket."""
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
        session.expunge(ticket)
        return ticket


@pytest.fixture
def sample_task(db_service: DatabaseService, sample_ticket: Ticket) -> Task:
    """Create a sample task."""
    with db_service.get_session() as session:
        task = Task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_REQUIREMENTS",
            task_type="analyze_requirements",
            description="Test task",
            priority="MEDIUM",
            status="pending",
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        session.expunge(task)
        return task


@pytest.fixture
def sample_agent(db_service: DatabaseService) -> Agent:
    """Create a sample agent."""
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
        session.expunge(agent)
        return agent
```

### tests/fixtures/mocks.py

```python
"""Mock objects and utilities."""

from unittest.mock import Mock, MagicMock, AsyncMock
import pytest


def create_mock_db_session():
    """Create a properly mocked database session with context manager."""
    mock_session = Mock()
    mock_context_manager = Mock()
    mock_context_manager.__enter__ = Mock(return_value=mock_session)
    mock_context_manager.__exit__ = Mock(return_value=None)
    return mock_session, mock_context_manager


@pytest.fixture
def mock_db():
    """Mock DatabaseService."""
    mock_db = Mock(spec=DatabaseService)
    mock_session, mock_context = create_mock_db_session()
    mock_db.get_session.return_value = mock_context
    return mock_db


@pytest.fixture
def mock_event_bus():
    """Mock EventBusService."""
    mock = Mock(spec=EventBusService)
    mock.publish = Mock()
    mock.subscribe = Mock()
    return mock


@pytest.fixture
def mock_llm_service():
    """Mock LLMService."""
    mock = AsyncMock()
    mock.generate_completion = AsyncMock(return_value="Mock LLM response")
    return mock


@pytest.fixture
def mock_agent_executor():
    """Mock AgentExecutor."""
    executor = Mock()
    executor.execute_task = Mock(return_value={
        "success": True,
        "output": "Test output",
        "exit_code": 0,
    })
    return executor
```

### tests/helpers/builders.py

```python
"""Test data builders for creating complex test objects."""

from datetime import datetime, timedelta
from typing import Optional
from omoi_os.models.ticket import Ticket
from omoi_os.models.task import Task
from omoi_os.models.agent import Agent
from omoi_os.utils.datetime import utc_now


class TicketBuilder:
    """Builder for creating test tickets with fluent API."""

    def __init__(self):
        self._title = "Test Ticket"
        self._description = "Test description"
        self._phase_id = "PHASE_REQUIREMENTS"
        self._status = "pending"
        self._priority = "MEDIUM"
        self._created_at = utc_now()

    def with_title(self, title: str) -> 'TicketBuilder':
        self._title = title
        return self

    def with_description(self, description: str) -> 'TicketBuilder':
        self._description = description
        return self

    def with_phase(self, phase_id: str) -> 'TicketBuilder':
        self._phase_id = phase_id
        return self

    def with_status(self, status: str) -> 'TicketBuilder':
        self._status = status
        return self

    def with_priority(self, priority: str) -> 'TicketBuilder':
        self._priority = priority
        return self

    def in_progress(self) -> 'TicketBuilder':
        self._status = "in_progress"
        return self

    def high_priority(self) -> 'TicketBuilder':
        self._priority = "HIGH"
        return self

    def build(self) -> Ticket:
        """Build the ticket."""
        return Ticket(
            title=self._title,
            description=self._description,
            phase_id=self._phase_id,
            status=self._status,
            priority=self._priority,
            created_at=self._created_at,
        )


class TaskBuilder:
    """Builder for creating test tasks."""

    def __init__(self, ticket_id: Optional[str] = None):
        self._ticket_id = ticket_id or "test-ticket-id"
        self._phase_id = "PHASE_REQUIREMENTS"
        self._task_type = "analyze_requirements"
        self._description = "Test task"
        self._priority = "MEDIUM"
        self._status = "pending"

    def for_ticket(self, ticket_id: str) -> 'TaskBuilder':
        self._ticket_id = ticket_id
        return self

    def with_type(self, task_type: str) -> 'TaskBuilder':
        self._task_type = task_type
        return self

    def with_status(self, status: str) -> 'TaskBuilder':
        self._status = status
        return self

    def assigned(self) -> 'TaskBuilder':
        self._status = "assigned"
        return self

    def completed(self) -> 'TaskBuilder':
        self._status = "done"
        return self

    def build(self) -> Task:
        """Build the task."""
        return Task(
            ticket_id=self._ticket_id,
            phase_id=self._phase_id,
            task_type=self._task_type,
            description=self._description,
            priority=self._priority,
            status=self._status,
        )


# Usage in tests:
# ticket = TicketBuilder().with_title("Auth Implementation").high_priority().in_progress().build()
# task = TaskBuilder(ticket.id).assigned().build()
```

---

## Pytest-Testmon Usage

### Basic Commands

```bash
# First run: Collect baseline
uv run pytest --testmon

# Subsequent runs: Only run affected tests
uv run pytest --testmon

# Run all tests (ignore testmon)
uv run pytest --no-testmon

# Run specific category with testmon
uv run pytest tests/unit/ --testmon
uv run pytest -m unit --testmon
uv run pytest -m "unit and not slow" --testmon

# Clear testmon data and start fresh
uv run pytest --testmon-nocache

# Show which tests would run without actually running
uv run pytest --testmon-noselect

# Run only failed tests with testmon
uv run pytest --lf --testmon
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: app_db_test
        ports:
          - 15432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        ports:
          - 16379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for testmon

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install UV
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv sync --group test

      - name: Create .env.test
        run: |
          cat > .env.test << EOF
# pragma: allowlist secret
DATABASE_URL_TEST=postgresql+psycopg://postgres:postgres@localhost:15432/app_db_test
          REDIS_URL_TEST=redis://localhost:16379/1
          LLM_API_KEY=test-key-mock
          AUTH_JWT_SECRET_KEY=test-secret-ci-${{ github.sha }}
          OMOIOS_ENV=test
          EOF

      - name: Verify config/test.yaml exists
        run: |
          if [ ! -f config/test.yaml ]; then
            echo "Error: config/test.yaml not found"
            exit 1
          fi

      - name: Cache testmon data
        uses: actions/cache@v3
        with:
          path: .testmondata
          key: testmon-${{ github.sha }}
          restore-keys: |
            testmon-${{ github.base_ref }}-
            testmon-main-

      - name: Run tests with testmon
        run: uv run pytest --testmon --cov
        env:
          OMOIOS_ENV: test

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

## Test Execution Strategy

### Development Workflow

```bash
# 1. Quick feedback loop (only changed tests)
uv run pytest --testmon -x  # Stop on first failure

# 2. Run specific category
uv run pytest tests/unit/ --testmon
uv run pytest -m "unit and not slow" --testmon

# 3. Full test suite (before commit)
uv run pytest --no-testmon

# 4. Integration tests only
uv run pytest tests/integration/ --testmon

# 5. Critical path tests
uv run pytest -m critical --testmon
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash

# Run only affected tests before commit
uv run pytest --testmon -x -q

if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Commit aborted."
    exit 1
fi

echo "✅ All affected tests passed."
```

---

## Migration Plan

### Phase 1: Setup (Low Risk)
1. Install pytest-testmon
2. Update pytest.ini configuration
3. Run baseline test collection
4. Verify testmon is working

### Phase 2: Create New Structure (Parallel Work)
1. Create new directory structure
2. Create category-specific conftest files
3. Extract shared fixtures to fixtures/
4. Create test helpers and builders

### Phase 3: Migrate Tests (Incremental)
1. Start with unit tests (lowest risk)
2. Move integration tests
3. Move E2E tests
4. Update imports and paths
5. Run full suite to verify

### Phase 4: Cleanup
1. Remove old test files
2. Update documentation
3. Update CI/CD workflows
4. Train team on new structure

---

## Additional Pytest Plugins

```bash
# Recommended plugins for better test experience
uv add --group test pytest-testmon        # Smart test execution
uv add --group test pytest-xdist          # Parallel test execution
uv add --group test pytest-sugar          # Better output formatting
uv add --group test pytest-timeout        # Timeout protection
uv add --group test pytest-mock           # Better mocking
uv add --group test pytest-randomly       # Random test order
uv add --group test pytest-benchmark      # Performance benchmarking
uv add --group test pytest-env            # Environment variable management
uv add --group test pytest-asyncio        # Async test support (already have)
```

### Enhanced Test Commands

```bash
# Parallel execution with testmon
uv run pytest --testmon -n auto  # Use all CPU cores

# With timeout protection
uv run pytest --testmon --timeout=300  # 5 min timeout per test

# Random order to catch test dependencies
uv run pytest --testmon --randomly-seed=last

# Benchmark mode
uv run pytest tests/performance/ --benchmark-only

# Generate HTML report
uv run pytest --testmon --html=report.html --self-contained-html
```

---

## Makefile Targets

```makefile
# Makefile

.PHONY: test test-unit test-integration test-e2e test-all test-changed test-fast

# Test commands
test-changed:
	uv run pytest --testmon -x

test-unit:
	uv run pytest tests/unit/ --testmon -v

test-integration:
	uv run pytest tests/integration/ --testmon -v

test-e2e:
	uv run pytest tests/e2e/ --testmon -v

test-performance:
	uv run pytest tests/performance/ --testmon -v

test-all:
	uv run pytest --no-testmon --cov

test-fast:
	uv run pytest -m "unit and not slow" --testmon -x

test-parallel:
	uv run pytest --testmon -n auto

test-coverage:
	uv run pytest --no-testmon --cov --cov-report=html
	open htmlcov/index.html

test-clean:
	rm -rf .testmondata .pytest_cache htmlcov .coverage
```

---

## Benefits of Reorganization

### 1. Faster Test Execution
- **Testmon**: Only runs tests affected by code changes (50-90% time savings)
- **Parallel execution**: Use all CPU cores with pytest-xdist
- **Category filtering**: Run only relevant test categories

### 2. Better Organization
- **Clear structure**: Easy to find tests for specific components
- **Logical grouping**: Related tests are co-located
- **Scalable**: Easy to add new tests in appropriate categories

### 3. Improved Developer Experience
- **Quick feedback**: Run only affected tests during development
- **Targeted testing**: Run specific categories (unit vs integration)
- **Better navigation**: Clear file paths indicate test purpose

### 4. Easier Maintenance
- **Shared fixtures**: No duplication across test files
- **Test builders**: Consistent test data creation
- **Custom assertions**: Reusable assertion helpers

---

## Expected Performance Improvements

### Current (57 test files, ~500 tests)
- Full suite: ~5-10 minutes
- Repeated runs: Same time every time
- Cannot target specific areas easily

### With Testmon + Organization
- First run: ~5-10 minutes (baseline)
- Code change (1 service): ~30 seconds (only affected tests)
- Code change (model): ~1-2 minutes (related tests)
- Unit tests only: ~1-2 minutes
- Full suite (CI): Same as current

### Time Savings
- **Development**: 80-90% reduction in test execution time
- **CI/CD**: 50-70% reduction with caching
- **Pre-commit**: Only affected tests (~10-30 seconds)

---

## Makefile for Test Execution

Create `Makefile` in project root:

```makefile
.PHONY: test test-unit test-integration test-e2e test-all test-quick test-parallel test-coverage test-clean test-rebuild

# Quick development feedback (affected tests only)
test:
	OMOIOS_ENV=test uv run pytest --testmon -x

test-quick:
	OMOIOS_ENV=test uv run pytest --testmon -x -q

# Category-specific tests
test-unit:
	OMOIOS_ENV=test uv run pytest tests/unit/ --testmon -v

test-integration:
	OMOIOS_ENV=test uv run pytest tests/integration/ --testmon -v

test-e2e:
	OMOIOS_ENV=test uv run pytest tests/e2e/ --testmon -v

test-performance:
	OMOIOS_ENV=test uv run pytest tests/performance/ --testmon -v

# Full suite (CI/pre-push)
test-all:
	OMOIOS_ENV=test uv run pytest --no-testmon --cov

# Fast tests only
test-fast:
	OMOIOS_ENV=test uv run pytest -m "unit and not slow" --testmon -x -n auto

# Parallel execution
test-parallel:
	OMOIOS_ENV=test uv run pytest --testmon -n auto

# Coverage report
test-coverage:
	OMOIOS_ENV=test uv run pytest --no-testmon --cov --cov-report=html
	@echo "Opening coverage report..."
	open htmlcov/index.html || xdg-open htmlcov/index.html

# Failed tests only
test-failed:
	OMOIOS_ENV=test uv run pytest --lf --testmon -x

# Rebuild testmon cache
test-rebuild:
	rm -rf .testmondata
	OMOIOS_ENV=test uv run pytest --testmon

# Clean all test artifacts
test-clean:
	rm -rf .testmondata .pytest_cache htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Smoke test (critical path)
test-smoke:
	OMOIOS_ENV=test uv run pytest -m critical --testmon -x

# Dry run (show what would execute)
test-dry:
	OMOIOS_ENV=test uv run pytest --testmon --collect-only

# Help
test-help:
	@echo "Test Commands:"
	@echo "  make test          - Run affected tests (quick feedback)"
	@echo "  make test-unit     - Run unit tests only"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-e2e      - Run end-to-end tests"
	@echo "  make test-all      - Run ALL tests (full suite)"
	@echo "  make test-fast     - Run fast tests in parallel"
	@echo "  make test-parallel - Run affected tests in parallel"
	@echo "  make test-coverage - Generate HTML coverage report"
	@echo "  make test-failed   - Re-run only failed tests"
	@echo "  make test-rebuild  - Rebuild testmon cache"
	@echo "  make test-clean    - Clean all test artifacts"
```

---

This plan provides a clear path to reorganizing tests, implementing intelligent test execution with pytest-testmon, and using YAML-first configuration.
