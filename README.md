# OmoiOS - Autonomous Engineering Execution Platform

**OmoiOS is an autonomous engineering execution dashboard that turns feature requests into real shipped code.** Engineering teams connect a GitHub repository, describe what they want built, and OmoiOS automatically plans the work using a spec-driven approach, discovers tasks as it progresses, builds features, tests them, and creates PRs—all while teams monitor progress in real time.

## Product Vision

OmoiOS enables engineering teams to scale development without scaling headcount. Users describe what they want built in natural language, and the system autonomously:

1. **Analyzes** the codebase to understand context
2. **Plans** using a spec-driven workflow (Requirements → Design → Tasks → Execution)
3. **Discovers** new tasks as it works (dependencies, optimizations, missing components)
4. **Executes** autonomously with multiple AI agents working in parallel
5. **Verifies** work with property-based testing and integration tests
6. **Monitors** agent behavior to ensure they're helping reach desired goals
7. **Adapts** monitoring strategies by learning from successful and failed workflows
8. **Presents** results for approval at strategic phase gates

**Key Value Proposition**: The AI handles nuances, corrects itself, verifies work, and discovers new tasks autonomously. Agents discover, verify, and monitor each other to ensure alignment with goals—without requiring explicit instructions for every scenario. The adaptive monitoring loop learns how things work and adapts strategies automatically. Users only need to monitor at strategic points (phase gates, PR reviews), not micromanage every step.

For complete product vision, see [docs/product_vision.md](docs/product_vision.md).

## Overview

OmoiOS is a spec-driven, multi-agent orchestration system built on top of the OpenHands Software Agent SDK. It provides:

### Core Capabilities
- **Spec-Driven Workflow**: Requirements → Design → Tasks → Execution with structured artifacts
- **Task Queue Management**: Priority-based task assignment and tracking with dependency resolution
- **Event Bus**: System-wide event publishing and subscription via Redis for real-time updates
- **Agent Registry**: Registration and lifecycle management of worker agents with health monitoring
- **Agent Discovery**: Agents discover new requirements, dependencies, optimizations, and issues as they work
- **Agent Verification**: Agents verify each other's work through property-based testing and spec compliance
- **Mutual Agent Monitoring**: Guardian agents monitor trajectories, Conductor ensures system-wide coherence, agents monitor each other
- **Adaptive Monitoring Loop**: Continuous monitoring that learns patterns and adapts strategies without explicit programming
- **OpenHands Integration**: Wrapper around OpenHands SDK for agent execution in isolated workspaces
- **REST API**: FastAPI-based API for ticket and task management
- **Web Dashboard**: Real-time monitoring dashboard with Kanban board, dependency graphs, and spec workspace

## Prerequisites

- Python 3.12+
- PostgreSQL 18+ (with vector extensions)
- Redis 7+
- Docker and Docker Compose (for containerized development)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd senior_sandbox
```

2. Install dependencies using UV:
```bash
uv sync
```

3. Install test dependencies:
```bash
uv sync --group test
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

Required environment variables:
- `LLM_API_KEY`: API key for LLM provider (e.g., Anthropic)
- `DATABASE_URL`: PostgreSQL connection string (default: `postgresql+psycopg://postgres:postgres@localhost:15432/app_db`)
- `REDIS_URL`: Redis connection string (default: `redis://localhost:16379`)

## Development Setup

### Using Docker Compose

1. Start services:
```bash
docker-compose up -d
```

This will start:
- PostgreSQL on port `15432`
- Redis on port `16379`
- API server on port `18000`
- Worker service

2. Run database migrations:
```bash
uv run alembic upgrade head
```

3. Run the smoke test to verify setup:
```bash
uv run python scripts/smoke_test.py
```

### Local Development

1. Start PostgreSQL and Redis (or use Docker Compose):
```bash
docker-compose up -d postgres redis
```

2. Run migrations:
```bash
uv run alembic upgrade head
```

3. Start the API server:
```bash
uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 8000 --reload
```

4. Start the worker (in a separate terminal):
```bash
uv run python -m omoi_os.worker
```

## Testing

### Running Tests

Run all tests:
```bash
uv run pytest
```

Run specific test file:
```bash
uv run pytest tests/test_01_database.py
```

Run with coverage:
```bash
uv run pytest --cov=omoi_os --cov-report=html
```

### Test Structure

- `tests/test_01_database.py`: Database layer tests (models, CRUD, migrations)
- `tests/test_02_task_queue.py`: Task queue service tests
- `tests/test_03_event_bus.py`: Event bus service tests
- `tests/test_04_agent_executor.py`: Agent executor tests (mocked OpenHands)
- `tests/test_05_e2e_minimal.py`: End-to-end flow tests

### Test Configuration

Tests use a separate test database. Set `DATABASE_URL_TEST` environment variable to override:
```bash
export DATABASE_URL_TEST="postgresql+psycopg://postgres:postgres@localhost:15432/app_db_test"
```

For event bus tests, you can use fakeredis (default) or a real Redis instance:
```bash
export REDIS_URL_TEST="redis://localhost:16379"
```

## Project Structure

```
omoi_os/
├── api/              # FastAPI application
│   ├── main.py       # Application entry point
│   ├── routes/       # API route handlers
│   └── dependencies.py  # Dependency injection
├── models/           # SQLAlchemy models
│   ├── ticket.py     # Ticket model
│   ├── task.py       # Task model
│   ├── agent.py      # Agent model
│   └── event.py      # Event model
├── services/         # Business logic services
│   ├── database.py   # Database service
│   ├── task_queue.py # Task queue service
│   ├── event_bus.py  # Event bus service
│   └── agent_executor.py  # OpenHands wrapper
├── worker.py         # Worker service entry point
└── config.py         # Configuration management

tests/
├── conftest.py       # Pytest fixtures
├── test_01_database.py
├── test_02_task_queue.py
├── test_03_event_bus.py
├── test_04_agent_executor.py
└── test_05_e2e_minimal.py

scripts/
└── smoke_test.py     # Smoke test script
```

## API Documentation

Once the API server is running, visit:
- Swagger UI: http://localhost:18000/docs
- ReDoc: http://localhost:18000/redoc

## Port Configuration

To avoid port conflicts, OmoiOS uses non-standard ports:
- PostgreSQL: `15432` (default: 5432)
- Redis: `16379` (default: 6379)
- API: `18000` (default: 8000)

This follows the project rule: `default_port + 10000`.

## License

[Add your license here]

