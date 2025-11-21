# OmoiOS - Autonomous Engineering Platform

**Spec-driven multi-agent orchestration system that scales development without scaling headcount.**

OmoiOS orchestrates multiple AI agents through adaptive, phase-based workflows where agents automatically discover and spawn new work branches as they work—enabling workflows that adapt to reality rather than following rigid plans.

---

## Monorepo Structure

```
senior_sandbox/
├── backend/          # Python FastAPI backend
├── frontend/         # Next.js 15 frontend
└── docs/             # Shared documentation
```

---

## Quick Start

### Backend (Python FastAPI)

```bash
cd backend

# Install dependencies
uv sync

# Run migrations
uv run alembic upgrade head

# Start API
uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 8000 --reload

# Visit: http://localhost:8000/docs
```

### Frontend (Next.js 15)

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev

# Visit: http://localhost:3000
```

### Full Stack (Docker)

```bash
# Start all services (PostgreSQL, Redis, Backend API, Frontend)
docker-compose up

# Backend: http://localhost:18000
# Frontend: http://localhost:3000
```

---

## Documentation

**Product Specifications:**
- `docs/app_overview.md` - Product concept (2-sentence summary)
- `docs/page_architecture.md` - All 40+ pages detailed
- `docs/design_system.md` - Complete design system

**Implementation Guides:**
- `docs/frontend_implementation_guide.md` - Build Next.js frontend
- `docs/FRONTEND_PACKAGE.md` - Complete frontend code index
- `backend/CLAUDE.md` - Backend development guide

**Architecture:**
- `docs/design/frontend/` - Frontend architecture
- `docs/design/workflows/` - Workflow system design
- `docs/requirements/` - System requirements

---

## Features

- ✅ **Spec-Driven Workflows**: Requirements → Design → Tasks → Execution
- ✅ **Adaptive Phase System**: Agents spawn tasks in any phase via discovery
- ✅ **Real-Time Kanban Board**: Tickets move through phases automatically
- ✅ **Multi-Agent Coordination**: Parallel agents with collective memory
- ✅ **Phase Gate Approvals**: Quality validation at each phase
- ✅ **Discovery Branching**: Workflows adapt based on agent discoveries
- ✅ **Workspace Isolation**: Each agent gets isolated Git workspace

---

## Development

**Backend Tests:**
```bash
cd backend
uv run pytest
uv run pytest --cov=omoi_os
```

**Frontend Tests:**
```bash
cd frontend
npm test
npm run build  # Test production build
```

---

## Deployment

**Backend** (Deploy to any Python host):
```bash
cd backend
docker build -f Dockerfile.api -t omoios-api .
docker run -p 8000:8000 omoios-api
```

**Frontend** (Deploy to Vercel):
```bash
cd frontend
vercel deploy
```

---

## Project Status

- ✅ Backend: Production-ready (23 tables, 20 services, 277 tests)
- 🚧 Frontend: Ready to assemble from scaffolds (15,000 lines ready)
- ✅ Documentation: Complete (30,000+ lines)

---

## Learn More

- [Product Vision](docs/product_vision.md)
- [Phase System](docs/design/workflows/omoios_phase_system_comparison.md)
- [Frontend Package](docs/FRONTEND_PACKAGE.md)
- [Mission Control Design](docs/design/frontend/mission_control_exploration.md)
