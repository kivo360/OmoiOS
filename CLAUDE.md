# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Package Management (UV)
```bash
# Install dependencies
uv sync

# Install test dependencies
uv sync --group test

# Install dev dependencies (includes OpenHands server/workspace)
uv sync --group dev

# Run commands with uv
uv run python -m omoi_os.worker
uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 8000 --reload
uv run alembic upgrade head
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_task_dependencies.py

# Run tests with coverage
uv run pytest --cov=omoi_os --cov-report=html

# Run specific test markers
uv run pytest -m unit          # Unit tests only
uv run pytest -m integration   # Integration tests only
uv run pytest -m e2e          # End-to-end tests only

# Run single test
uv run pytest tests/test_task_queue.py::TestTaskQueueService::test_enqueue_task -v
```

### Database Operations
```bash
# Run migrations
uv run alembic upgrade head

# Create new migration
uv run alembic revision -m "description"

# Rollback migration
uv run alembic downgrade -1

# View migration history
uv run alembic history
```

### Docker Development
```bash
# Start all services
docker-compose up -d

# Start specific services
docker-compose up -d postgres redis

# View logs
docker-compose logs -f api
docker-compose logs -f worker

# Rebuild and restart
docker-compose up -d --build
```

### API Development
```bash
# Start API server (local development)
uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 8000 --reload

# API Documentation (when server is running)
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

### Smoke Test
```bash
# Verify minimal E2E flow works
uv run python scripts/smoke_test.py
```

## Architecture Overview

OmoiOS is a multi-agent orchestration system built on top of the OpenHands Software Agent SDK with the following key architectural components:

### Core Services Architecture
- **DatabaseService**: PostgreSQL connection management with SQLAlchemy ORM, provides session context managers for safe database operations
- **TaskQueueService**: Priority-based task assignment and lifecycle management, supports task dependencies, retries, timeouts, and cancellation
- **EventBusService**: Redis-based pub/sub system for real-time event broadcasting across agents and components
- **AgentHealthService**: Agent heartbeat monitoring, stale detection (90s timeout), and health statistics
- **AgentExecutor**: Wrapper around OpenHands SDK that executes tasks in isolated workspace environments

### Data Flow Patterns
1. **Ticket Creation**: Tickets are created via API and automatically split into Phase-based tasks
2. **Task Assignment**: Background orchestrator loop polls TaskQueueService and assigns tasks to registered agents based on priority and dependencies
3. **Agent Execution**: Workers pick up assigned tasks, emit heartbeats every 30s, execute via OpenHands in isolated workspaces, and publish completion events
4. **Event Broadcasting**: All state changes (task created, assigned, completed, failed, retried, timed out) are published as Redis events for real-time monitoring

### Phase-Based Development Model
- **PHASE_INITIAL**: Initial project setup and scaffolding
- **PHASE_IMPLEMENTATION**: Feature implementation and development
- **PHASE_INTEGRATION**: System integration and testing
- **PHASE_REFACTORING**: Code cleanup and optimization

### Agent Enhancement Features (Phase 1)
- **Task Dependencies**: JSONB-based dependency graph with circular dependency detection
- **Error Handling**: Exponential backoff retries (1s, 2s, 4s, 8s + jitter) with smart error classification
- **Health Monitoring**: 30-second heartbeats, automatic stale detection, comprehensive health statistics
- **Timeout Management**: Configurable task timeouts, background monitoring (10s intervals), API-based cancellation

### Database Schema Design
- **PostgreSQL 18+** with vector extensions for future AI-powered features
- **JSONB fields** for flexible task dependencies and configuration storage
- **GIN indexes** on JSONB fields for efficient query performance
- **Timezone-aware datetime handling** using `whenever` library with `utc_now()` utility

### Port Configuration (to avoid conflicts)
- PostgreSQL: 15432 (default 5432 + 10000)
- Redis: 16379 (default 6379 + 10000)
- API: 18000 (default 8000 + 10000)

### Environment Configuration
- Uses Pydantic Settings with automatic .env file loading
- Separate settings classes for LLM, Database, and Redis configurations
- Default OpenHands model: `openhands/claude-sonnet-4-5-20250929`

## Important Implementation Details

### Datetime Handling
Always use `omoi_os.utils.datetime.utc_now()` for timezone-aware datetime objects. The `whenever` library provides proper UTC handling while maintaining SQLAlchemy compatibility. Never use `datetime.utcnow()` as it creates offset-naive datetimes.

### Database Session Management
Use the DatabaseService context manager pattern:
```python
with db.get_session() as session:
    # Database operations here
    session.commit()  # Auto-commits on context exit
```

### 🚨 CRITICAL: SQLAlchemy Reserved Keywords
**NEVER use reserved attribute names in SQLAlchemy models** - they cause import failures and runtime errors:

**Forbidden Attribute Names (ABSOLUTELY NEVER USE):**
- `metadata` - Reserved by SQLAlchemy's Declarative API
- `registry` - Reserved by SQLAlchemy's internal registry system
- `declared_attr` - Reserved by SQLAlchemy's declarative system

**Safe Alternatives:**
- Instead of `metadata`, use: `change_metadata`, `item_metadata`, `config_data`, `extra_data`
- Instead of `registry`, use: `agent_registry`, `service_registry`
- Instead of `declared_attr`, use: `custom_field`, `dynamic_attribute`

**Why This Matters:**
- Using `metadata` in model classes causes `sqlalchemy.exc.InvalidRequestError`
- This error blocks server startup and makes the application unusable
- The error occurs during model definition, not during database operations
- This affects ALL models that inherit from `Base`

**Example of What NOT To Do:**
```python
# ❌ THIS WILL CRASH YOUR APPLICATION
class TicketHistory(Base):
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB)  # CRASHES!
```

**Example of What To Do:**
```python
# ✅ THIS WORKS CORRECTLY
class TicketHistory(Base):
    change_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)  # Safe!
```

### Error Classification in Retries
The system distinguishes between retryable errors (network timeouts, temporary failures) and permanent errors (permission denied, syntax errors, authentication failures).

### Event Publishing Pattern
All significant state changes should publish events via EventBusService:
```python
event_bus.publish(SystemEvent(
    event_type="TASK_COMPLETED",
    entity_type="task",
    entity_id=str(task.id),
    payload={"result": result, "agent_id": agent_id}
))
```

### Agent Registration Pattern
Workers must register themselves and emit heartbeats:
```python
agent_id = register_agent(db, agent_type="worker", phase_id="PHASE_IMPLEMENTATION")
heartbeat_manager = HeartbeatManager(agent_id, health_service)
heartbeat_manager.start()
```

## Testing Strategy

### Test Organization
- **test_01_database.py**: Model validation, CRUD operations, migrations
- **test_02_task_queue.py**: Task queue service logic and priority handling
- **test_03_event_bus.py**: Event publishing and subscription patterns
- **test_04_agent_executor.py**: OpenHands integration (mocked)
- **test_05_e2e_minimal.py**: End-to-end workflow verification
- **test_*.py**: Feature-specific tests (dependencies, retries, health, timeout)

### Test Database
Tests use fakeredis by default to avoid Redis dependencies. Set `REDIS_URL_TEST` to use real Redis for integration tests.

### Phase 1 Feature Tests
- `test_task_dependencies.py`: Task dependency resolution and circular detection
- `test_retry_logic.py`: Exponential backoff and error classification (23 tests)
- `test_agent_health.py`: Heartbeat management and health monitoring (14 tests)
- `test_task_timeout.py`: Timeout detection and cancellation functionality

## Migration Strategy

Database migrations follow semantic versioning. Phase 1 enhancements are in migration `002_phase_1_enhancements.py` which added:
- `dependencies` (JSONB) for task dependency graphs
- `retry_count` and `max_retries` for error handling
- `timeout_seconds` for task timeout management

Always test migrations on both fresh databases and existing data.