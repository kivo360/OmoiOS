# OmoiOS - Autonomous Engineering Platform

**Spec-driven multi-agent orchestration system that scales development without scaling headcount.**

OmoiOS orchestrates multiple AI agents through adaptive, phase-based workflows where agents automatically discover and spawn new work branches as they work—enabling workflows that adapt to reality rather than following rigid plans.

---

## Monorepo Architecture

This project uses **uv workspaces** for unified Python dependency management across all packages.

```
senior_sandbox/
├── pyproject.toml        # Root workspace config (uv workspaces)
├── uv.lock               # Single lock file for all packages
│
├── backend/              # Python FastAPI backend (omoi-os)
│   ├── pyproject.toml    # Backend dependencies + sandbox-runtime ref
│   ├── omoi_os/          # Main Python package
│   └── CLAUDE.md         # Backend development guide
│
├── frontend/             # Next.js 15 frontend
│   ├── package.json      # NPM dependencies
│   └── src/app/          # App Router pages (40+)
│
├── subsystems/           # Workspace member packages
│   └── sandbox-runtime/  # Lightweight spec execution runtime
│       └── pyproject.toml
│
├── docs/                 # Shared documentation (30,000+ lines)
├── containers/           # Docker configurations
├── scripts/              # Development & deployment scripts
└── docker-compose.yml    # Full stack orchestration
```

### UV Workspace Configuration

The root `pyproject.toml` defines the workspace:

```toml
[tool.uv.workspace]
members = [
    "backend",
    "subsystems/*"
]
```

**How it works:**
- All Python packages share a single `uv.lock` for reproducible builds
- `backend` (omoi-os) depends on `sandbox-runtime` via workspace reference
- Run `uv sync` from root to install all workspace dependencies
- Requires Python 3.12+

**Dependency flow:**
```
backend/pyproject.toml:
  dependencies = [
    "sandbox-runtime",  # Workspace reference
    ...
  ]

  [tool.uv.sources]
  sandbox-runtime = { workspace = true }
```

---

## Quick Start

### Option 1: Full Stack (Docker)

```bash
# Start all services (PostgreSQL, Redis, Backend API, Frontend)
docker-compose up

# Services:
# - Backend API: http://localhost:18000
# - Frontend: http://localhost:3000
# - PostgreSQL: localhost:15432
# - Redis: localhost:16379
```

### Option 2: Manual Setup

**Backend (Python FastAPI):**
```bash
cd backend

# Install all workspace dependencies
uv sync

# Run database migrations
uv run alembic upgrade head

# Start API server
uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 8000 --reload

# Visit: http://localhost:8000/docs (Swagger UI)
```

**Frontend (Next.js 15):**
```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev

# Visit: http://localhost:3000
```

---

## Architecture Deep Dive

### Backend (`backend/`)

**Tech Stack:**
| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | FastAPI 0.104+ | Async web framework |
| Database | PostgreSQL 16 + pgvector | Data storage + vector search |
| Cache/Queue | Redis 7 + Taskiq | Caching + background jobs |
| ORM | SQLAlchemy 2.0+ | Database access |
| LLM | Anthropic Claude (claude-agent-sdk) | AI agent backbone |
| Sandbox | Daytona | Isolated workspace execution |
| Auth | Supabase + JWT | Authentication |
| Observability | Sentry + OpenTelemetry + Logfire | Monitoring |

**Core Services (80+):**
- `OrchestratorWorker` - Primary task executor
- `SpecStateMachine` - Multi-phase spec workflow (EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC)
- `TaskQueueService` - Priority-based task assignment with dependency tracking
- `AgentHealthService` - Heartbeat monitoring (30s intervals, 90s timeout)
- `EventBusService` - Redis pub/sub for real-time state changes
- `IntelligentGuardian` - LLM-powered trajectory analysis
- `DiscoveryService` - Workflow branching and task discovery

**API Structure:**
- 35 route modules (~20,500 lines)
- 57 SQLAlchemy models
- 64 database migrations

### Frontend (`frontend/`)

**Tech Stack:**
| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | Next.js 15 (App Router) | React framework with SSR |
| UI | ShadCN UI (Radix + Tailwind) | Component library |
| State | Zustand + React Query | Client + server state |
| Real-Time | WebSocket | Live updates |
| Graphs | React Flow v12 | Dependency visualization |
| Terminal | xterm.js | Agent workspace terminal |

**Page Architecture (40+ pages):**
- **Dashboard**: Home, projects overview, activity timeline
- **Specs & Tasks**: Spec workspace, kanban board, task details
- **Agents**: Agent list, workspace terminal, spawn interface
- **Monitoring**: Health dashboard, trajectories, interventions
- **Settings**: Profile, security, integrations, billing

### Subsystems (`subsystems/`)

**sandbox-runtime:**
- Lightweight Python package for spec execution
- Zero external dependencies (standalone)
- Used by backend via workspace reference

```python
# In backend code:
from sandbox_runtime import ...
```

---

## Key Workflows

### 1. Spec-Driven Development
```
User submits spec
    → API creates Spec record
    → SpecStateMachine runs phases:
        EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC
    → Each phase generates outputs stored in DB
    → Frontend displays specs in workspace
```

### 2. Task Execution
```
Task created
    → TaskQueueService assigns to agent
    → OrchestratorWorker spawns Daytona sandbox
    → Agent executes, sends heartbeats (30s)
    → EventBusService publishes progress
    → Frontend updates via WebSocket
```

### 3. Multi-Agent Coordination
```
Guardian monitors agent trajectories
    → LLM analyzes alignment to goals
    → Conductor computes system coherence
    → Discovery finds new work branches
    → Monitoring loop learns from successes/failures
```

---

## Development

### Backend Commands

```bash
cd backend

# Dependencies
uv sync                    # Install all dependencies
uv sync --group dev        # Include dev tools
uv sync --group test       # Include test tools

# Database
uv run alembic upgrade head           # Run migrations
uv run alembic revision -m "message"  # Create migration
uv run alembic downgrade -1           # Rollback

# Testing
uv run pytest                         # All tests
uv run pytest --cov=omoi_os           # With coverage
uv run pytest -m unit                 # Unit tests only

# Workers
uv run python -m omoi_os.workers.orchestrator_worker  # Main worker
taskiq worker omoi_os.tasks.broker:broker             # Task queue
```

### Frontend Commands

```bash
cd frontend

npm run dev      # Development server
npm run build    # Production build
npm run test     # Run tests
npm run lint     # Lint check
```

### Docker Commands

```bash
# Full stack
docker-compose up

# Specific services
docker-compose up postgres redis    # Just infrastructure
docker-compose up -d --build backend  # Rebuild backend

# Logs
docker-compose logs -f backend
```

---

## Port Configuration

To avoid conflicts with local services, all ports are offset by 10000:

| Service | Port | Default |
|---------|------|---------|
| PostgreSQL | 15432 | 5432 |
| Redis | 16379 | 6379 |
| Backend API | 18000 | 8000 |
| Frontend | 3000 | 3000 |

---

## Documentation

**Product Specifications:**
- `docs/app_overview.md` - Product concept (2-sentence summary)
- `docs/product_vision.md` - Complete vision statement
- `docs/page_architecture.md` - All 40+ pages detailed
- `docs/design_system.md` - Complete design system

**Implementation Guides:**
- `docs/frontend_implementation_guide.md` - Build Next.js frontend
- `docs/FRONTEND_PACKAGE.md` - Complete frontend code index
- `backend/CLAUDE.md` - Backend development guide (comprehensive)

**Architecture:**
- `docs/design/frontend/` - Frontend architecture & patterns
- `docs/design/workflows/` - Workflow system design
- `docs/requirements/monitoring/` - Monitoring architecture
- `docs/architecture/` - Architecture Decision Records (ADRs)

---

## Features

- **Spec-Driven Workflows**: Requirements → Design → Tasks → Execution
- **Adaptive Phase System**: Agents spawn tasks in any phase via discovery
- **Real-Time Kanban Board**: Tickets move through phases automatically
- **Multi-Agent Coordination**: Parallel agents with collective memory
- **Phase Gate Approvals**: Quality validation at each phase
- **Discovery Branching**: Workflows adapt based on agent discoveries
- **Workspace Isolation**: Each agent gets isolated Git workspace
- **Intelligent Guardian**: LLM-powered trajectory analysis and intervention

---

## Project Status

| Component | Status | Details |
|-----------|--------|---------|
| Backend | Production-ready | 57 models, 80+ services, 277+ tests |
| Frontend | Ready to assemble | 40+ pages, scaffolds complete |
| Documentation | Complete | 30,000+ lines |
| Subsystems | Active development | sandbox-runtime integrated |

---

## Production Deployment

**Automatic Deployments:**

Both frontend and backend deploy automatically when you push to the `main` branch:

```bash
git add .
git commit -m "your changes"
git push origin main
# → Frontend deploys to Vercel automatically
# → Backend deploys to Railway automatically
```

**Production URLs:**
- Frontend: `https://omoios.dev`
- Backend API: `https://api.omoios.dev`

**Manual Deployment (if needed):**

Backend (Docker):
```bash
cd backend
docker build -f Dockerfile.api -t omoios-api .
docker run -p 8000:8000 omoios-api
```

Frontend (Vercel):
```bash
cd frontend
vercel deploy
```

---

## Learn More

- [Product Vision](docs/product_vision.md)
- [Phase System](docs/design/workflows/omoios_phase_system_comparison.md)
- [Frontend Package](docs/FRONTEND_PACKAGE.md)
- [Mission Control Design](docs/design/frontend/mission_control_exploration.md)
- [Monitoring Architecture](docs/requirements/monitoring/monitoring_architecture.md)
