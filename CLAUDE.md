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

---

## Documentation Standards (ENFORCED)

### Before Creating ANY Documentation

1. **Check if it exists**:
   ```bash
   grep -r "topic" docs/ --include="*.md"
   ```

2. **Choose correct category**:
   - Requirements (what) → `docs/requirements/{category}/`
   - Design (how) → `docs/design/{category}/`
   - ADR (why) → `docs/architecture/`
   - Status → `docs/implementation/`

3. **Follow naming convention**:
   - ✅ `memory_system.md` (snake_case)
   - ❌ `MemorySystem.md` (CamelCase)
   - ❌ `memory-system.md` (hyphens)

4. **Include metadata**:
   ```markdown
   # Document Title
   
   **Created**: 2025-11-20
   **Status**: Draft | Review | Approved
   **Purpose**: One-sentence description
   ```

5. **Validate before commit**:
   ```bash
   just validate-docs
   ```

### Document Organization Rules

```
✅ DO:
- Categorize by purpose (requirements/, design/, architecture/)
- Use snake_case filenames
- Include metadata header
- Link to related docs
- Keep docs DRY (Don't Repeat Yourself)

❌ DON'T:
- Create docs in root without categorization
- Use CamelCase, hyphens, or spaces in filenames
- Duplicate information across documents
- Leave docs without status or purpose
- Create orphaned docs without cross-references
```

### See Also
- `docs/DOCUMENTATION_STANDARDS.md` - Complete documentation guide
- `scripts/validate_docs.py` - Documentation validation tool

## Testing Strategy

### Test Organization (ENFORCED)

Tests are organized by type in a hierarchical structure:

```
tests/
├── unit/           # Fast, isolated tests (< 1s each)
├── integration/    # Multi-component tests (< 10s each)
├── e2e/           # Full workflow tests (< 60s each)
├── performance/    # Load and benchmark tests
├── fixtures/       # Shared test fixtures
└── helpers/        # Test utilities and builders
```

### Testing Commands (Use Justfile)

```bash
# Quick feedback (only affected tests)
just test

# Full test suite
just test-all

# Category-specific
just test-unit         # Unit tests only
just test-integration  # Integration tests
just test-e2e          # End-to-end tests

# With coverage
just test-coverage     # HTML coverage report
```

### Test File Naming Convention (ENFORCED)

```python
# ✅ CORRECT
tests/unit/services/test_task_queue_service.py
tests/integration/workflows/test_ace_workflow_integration.py
tests/e2e/test_full_ticket_lifecycle.py

# ❌ WRONG
tests/test_01_database.py           # No numbered prefixes
tests/TaskQueueTest.py              # No CamelCase
tests/test_tqs.py                   # No abbreviations
tests/unit/test_task_queue.py       # Missing component suffix
```

### Test Structure Requirements

```python
"""Test {feature} {component}.

Tests Requirements: REQ-{PREFIX}-001, REQ-{PREFIX}-002
"""

import pytest


@pytest.fixture
def feature_instance():
    """Create test instance."""
    return Feature()


class Test{Feature}:
    """Test suite for {feature}."""
    
    @pytest.mark.unit
    def test_{scenario}_success(self, feature_instance):
        """Test {scenario} succeeds when {condition}."""
        # Arrange - Act - Assert pattern
```

### Pytest-Testmon (Smart Test Execution)

The project uses pytest-testmon to run only tests affected by code changes:

```bash
# Development: Only run affected tests (95% faster!)
just test              # ~10-30 seconds

# CI/Full suite: Run all tests
just test-all          # ~5-10 minutes
```

**How it works**: Testmon tracks which code each test depends on. When you change a file, it only runs tests that touch that code.

### Test Configuration (YAML-First)

Test settings come from `config/test.yaml` (NOT .env):

```yaml
# config/test.yaml
monitoring:
  guardian_interval_seconds: 1  # Fast for tests
  
worker:
  concurrency: 1  # Single worker for predictability
  
features:
  enable_mcp_tools: false  # Disable external tools
```

Only secrets/URLs in `.env.test`:
```bash
DATABASE_URL_TEST=postgresql://...
LLM_API_KEY=test-key-mock
OMOIOS_ENV=test
```

---

## Configuration Management (ENFORCED)

### YAML for Settings, .env for Secrets

**Rule**: Application settings go in YAML, secrets go in .env files.

#### ✅ YAML Files (Version Controlled)

```yaml
# config/base.yaml
task_queue:
  age_ceiling: 3600      # Business setting
  w_p: 0.45             # Algorithm weight

monitoring:
  guardian_interval_seconds: 60
  auto_steering_enabled: false

auth:
  jwt_algorithm: HS256  # Algorithm choice (not secret)
  access_token_expire_minutes: 15
```

#### ✅ .env Files (Gitignored - Secrets Only)

```bash
# .env (NEVER commit to git)
DATABASE_URL=postgresql://user:password@host/db
LLM_API_KEY=sk-ant-...
AUTH_JWT_SECRET_KEY=super-secret-key
GITHUB_TOKEN=ghp_...
```

### Configuration Pattern (OmoiBaseSettings)

Every configuration section MUST use this pattern:

```python
from omoi_os.config import OmoiBaseSettings
from pydantic_settings import SettingsConfigDict
from functools import lru_cache


class FeatureSettings(OmoiBaseSettings):
    """Feature configuration from YAML."""
    
    yaml_section = "feature"  # Section in config/*.yaml
    model_config = SettingsConfigDict(
        env_prefix="FEATURE_",  # Environment variable prefix
        extra="ignore"
    )
    
    # Settings (loaded from YAML, can be overridden by env vars)
    setting_name: int = 60
    another_setting: str = "default"
    
    # Secrets (MUST come from environment variables)
    api_key: Optional[str] = None  # From FEATURE_API_KEY env var


@lru_cache(maxsize=1)
def load_feature_settings() -> FeatureSettings:
    """Load feature settings (cached)."""
    return FeatureSettings()
```

### Configuration Checklist (Before Adding Settings)

- [ ] Is this a secret/password/token? → Use .env ONLY
- [ ] Is this a business setting? → Use YAML
- [ ] Does a Settings class exist? → Use it
- [ ] Need new Settings class? → Extend OmoiBaseSettings
- [ ] Add to config/base.yaml with default value
- [ ] Add to config/test.yaml with test value (if different)
- [ ] Register in CONFIG_REGISTRY (if exists)
- [ ] Document in config/README.md
- [ ] NEVER hardcode values in code

### ❌ Configuration Anti-Patterns

```python
# ❌ WRONG: Hardcoded value
def process_task():
    timeout = 60  # Never hardcode!
    

# ❌ WRONG: Secret in YAML
# config/base.yaml
llm:
  api_key: sk-ant-...  # NEVER put secrets in YAML!


# ❌ WRONG: Setting in .env
# .env
TASK_QUEUE_AGE_CEILING=3600  # Settings belong in YAML!


# ❌ WRONG: Custom env loading
def get_env_files():  # Don't create custom loaders
    return [".env"]


# ✅ CORRECT: Use Settings class
from omoi_os.config import load_feature_settings

def process_task():
    settings = load_feature_settings()
    timeout = settings.timeout_seconds  # From YAML
```

---

## Migration Strategy

Database migrations follow semantic versioning. Phase 1 enhancements are in migration `002_phase_1_enhancements.py` which added:
- `dependencies` (JSONB) for task dependency graphs
- `retry_count` and `max_retries` for error handling
- `timeout_seconds` for task timeout management

Always test migrations on both fresh databases and existing data.