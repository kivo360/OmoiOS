# OmoiOS Backend

Python FastAPI backend for autonomous agent orchestration.

## Quick Start

```bash
# Install dependencies
uv sync

# Run migrations
uv run alembic upgrade head

# Start API server
uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 8000 --reload

# API docs: http://localhost:8000/docs
```

## Development

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=omoi_os --cov-report=html

# Run specific test
uv run pytest tests/test_task_queue.py -v

# Apply code formatting
uv run ruff check .
uv run black .
```

## Environment Variables

Create `.env` file:
```bash
DATABASE_URL=postgresql://omoios:omoios@localhost:15432/omoios
REDIS_URL=redis://localhost:16379
LLM_API_KEY=your-api-key
OMOIOS_ENV=development
```

## Database Connection (Scripts & Tests)

Always use `get_app_settings()` for database connections - never hardcode connection strings:

```python
from omoi_os.config import get_app_settings
from omoi_os.services.database import DatabaseService

settings = get_app_settings()
db = DatabaseService(connection_string=settings.database.url)

with db.get_session() as session:
    # Your database operations here
    pass
```

This automatically loads from `.env` / `.env.local` files with proper precedence.

## Documentation

**Start here**: [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Complete system architecture overview

Additional documentation in `../docs/`:
- Architecture: `../docs/design/`
- Requirements: `../docs/requirements/`
- Implementation: `../docs/implementation/`

## Docker

```bash
# Build
docker build -f Dockerfile.api -t omoios-api .

# Run
docker-compose up
```

## AI Instructions

See `CLAUDE.md` for AI pair-programming instructions.

