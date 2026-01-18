# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OmoiOS is a spec-driven, multi-agent orchestration system that scales development without scaling headcount. It combines autonomous agent execution with structured workflows (Requirements → Design → Tasks → Execution) using the Claude Agent SDK and OpenHands SDK.

**Production URLs:**
- Frontend: `https://omoios.dev`
- Backend API: `https://api.omoios.dev`

## Monorepo Structure

This project uses **uv workspaces** for unified Python dependency management:

```
senior_sandbox/
├── pyproject.toml          # Root workspace config
├── uv.lock                  # Single lock file for all packages
├── backend/                 # FastAPI backend (omoi-os package)
│   ├── omoi_os/             # Main Python package
│   └── CLAUDE.md            # Backend-specific guide (detailed)
├── frontend/                # Next.js 15 frontend
├── subsystems/
│   └── spec-sandbox/        # Spec execution runtime
├── docs/                    # Documentation (30,000+ lines)
├── scripts/                 # Development scripts
└── Justfile                 # Task runner (see `just --list`)
```

## Development Commands

### Quick Start (Recommended: Use Justfile)

```bash
# Show all available commands
just --list

# Full stack development (Docker with hot-reload)
just watch                    # Backend services with hot-reload
just frontend-dev             # Frontend dev server
just dev-all                  # Everything at once

# Testing
just test                     # Run affected tests only (testmon)
just test-all                 # Full test suite
just test-coverage            # With HTML coverage report

# Code quality
just format                   # Format code
just lint                     # Lint check
just check                    # All quality checks
```

### Manual Commands (Backend)

```bash
cd backend

# Dependencies (uv sync from root handles workspaces)
uv sync                       # Install all
uv sync --group test          # Include test deps

# API server
uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 18000 --reload

# Database
uv run alembic upgrade head   # Run migrations
uv run alembic revision -m "description"  # Create migration

# Testing
uv run pytest                 # All tests
uv run pytest tests/path/test_file.py::TestClass::test_method -v  # Single test
```

### Manual Commands (Frontend)

```bash
cd frontend
pnpm install                  # Install dependencies
pnpm dev                      # Dev server (port 3000)
pnpm build                    # Production build
pnpm lint                     # Lint check
```

## Architecture Highlights

### Backend Tech Stack
- **Framework**: FastAPI 0.104+ with async
- **Database**: PostgreSQL 16 + pgvector (SQLAlchemy 2.0+)
- **Cache/Queue**: Redis 7 + Taskiq
- **LLM**: Claude Agent SDK, Anthropic Claude
- **Sandbox**: Daytona for isolated workspace execution
- **Auth**: Supabase + JWT
- **Observability**: Sentry + OpenTelemetry + Logfire

### Frontend Tech Stack
- **Framework**: Next.js 15 (App Router)
- **UI**: ShadCN UI (Radix + Tailwind)
- **State**: Zustand (client) + React Query (server)
- **Graphs**: React Flow v12, @xyflow/react
- **Terminal**: xterm.js

### Core Services
- **SpecStateMachine**: Multi-phase spec workflow (EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC)
- **TaskQueueService**: Priority-based task assignment with dependencies
- **AgentHealthService**: 30s heartbeats, 90s timeout
- **EventBusService**: Redis pub/sub for real-time state
- **IntelligentGuardian**: LLM-powered trajectory analysis

### Port Configuration
| Service | Port | Note |
|---------|------|------|
| PostgreSQL | 15432 | +10000 offset |
| Redis | 16379 | +10000 offset |
| Backend API | 18000 | +10000 offset |
| Frontend | 3000 | Standard |

## Critical Rules

### SQLAlchemy Reserved Keywords (NEVER USE)
- `metadata` - Use `change_metadata`, `item_metadata`, `config_data`
- `registry` - Use `agent_registry`, `service_registry`

### LLM Service Usage
Always use `structured_output()` for LLM responses needing structured data:
```python
from omoi_os.services.llm_service import get_llm_service
from pydantic import BaseModel

class AnalysisResult(BaseModel):
    score: float
    summary: str

llm = get_llm_service()
result = await llm.structured_output(prompt="...", output_type=AnalysisResult)
result_dict = result.model_dump(mode='json')  # For JSONB storage
```

### Datetime Handling
Always use `omoi_os.utils.datetime.utc_now()` - never `datetime.utcnow()`.

### Configuration Pattern
- **YAML**: Application settings (version controlled in `config/*.yaml`)
- **.env**: Secrets only (DATABASE_URL, API keys) - never committed

## Testing

Tests use pytest-testmon for smart execution (only affected tests):

```bash
just test              # Fast: affected tests only (~10-30s)
just test-all          # Full suite (~5-10 min)
just test-unit         # Unit tests
just test-integration  # Integration tests
```

Test configuration: `backend/config/test.yaml` (NOT .env)

## Documentation

Key docs for understanding the system:
- `backend/CLAUDE.md` - Comprehensive backend guide
- `docs/product_vision.md` - Complete product vision
- `docs/design/frontend/` - Frontend architecture
- `docs/requirements/monitoring/` - Monitoring architecture

## Subsystems

### spec-sandbox
Lightweight spec execution runtime used by backend:
```python
from spec_sandbox import ...  # Via workspace reference
```

CLI: `spec-sandbox` (see `subsystems/spec-sandbox/`)
