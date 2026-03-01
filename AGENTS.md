# AGENTS.md — AI Coding Agent Guide for OmoiOS

This document helps AI coding agents (Claude Code, Cursor, Copilot Workspace, Windsurf, etc.) understand and contribute to OmoiOS efficiently.

## What is OmoiOS?

OmoiOS is a spec-driven, multi-agent orchestration system. Users describe a feature, OmoiOS plans it (requirements → design → tasks), executes it with autonomous AI agents in isolated sandboxes, and creates a PR. The core promise: "Start a feature before bed. Wake up to a PR."

**Production**: Frontend at `https://omoios.dev`, API at `https://api.omoios.dev`

## Read These First

| Document | Purpose | When to read |
|----------|---------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, service map, data flow | Before any backend work |
| [UI.md](UI.md) | Frontend routes, components, state, design system | Before any frontend work |
| [backend/CLAUDE.md](backend/CLAUDE.md) | Backend conventions, patterns, anti-patterns | Before writing Python |
| [CLAUDE.md](CLAUDE.md) | Monorepo structure, dev commands, ports | Always |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Branch conventions, PR process, testing | Before submitting changes |

## Repository Map

```
senior_sandbox/
├── backend/omoi_os/
│   ├── api/
│   │   ├── main.py              # FastAPI app + lifespan (25+ services initialized)
│   │   └── routes/              # 38 route files by domain
│   ├── services/                # Business logic (~40 service files)
│   │   ├── models/                  # SQLAlchemy 2.0 models (~77 model classes)
│   ├── workers/                 # Background workers (orchestrator, sandbox)
│   └── config.py                # OmoiBaseSettings (YAML + env)
│
├── backend/config/
│   ├── base.yaml                # Default application settings
│   └── test.yaml                # Test overrides
│
├── backend/tests/
│   ├── unit/                    # Fast isolated tests
│   ├── integration/             # Multi-component tests
│   └── e2e/                     # Full workflow tests
│
├── frontend/
│   ├── app/                     # Next.js 15 App Router
│   │   ├── (app)/               # Authenticated routes (command, projects, sandboxes, etc.)
│   │   ├── (auth)/              # Login, register, OAuth callback
│   │   └── (dashboard)/         # Root redirect to /command
│   ├── components/
│   │   ├── ui/                  # ShadCN primitives (40+) — do not modify
│   │   ├── layout/              # App shell (MainLayout, IconRail, ContextualPanel)
│   │   ├── panels/              # Sidebar panels (route-aware)
│   │   └── {domain}/            # Domain components (command, spec, sandbox, etc.)
│   │   ├── hooks/                   # 29 React Query + Zustand hooks (one per domain)
│   ├── lib/api/                 # HTTP client + domain-specific API functions
│   └── providers/               # Context providers (Query, Auth, Theme, PostHog)
│
├── subsystems/spec-sandbox/     # Spec execution runtime
├── docs/
│   ├── proposals/               # OmoiOS Improvement Proposals (OIPs)
│   │   ├── page_flows/              # 24 page-by-page UI flow docs
│   ├── user_journey/            # End-to-end user journey docs
│   │   └── architecture/            # 14 system deep-dive docs
└── Justfile                     # Task runner (just --list for all commands)
```

## Critical Rules

These rules prevent common mistakes. Violating them causes build failures or runtime crashes.

### Backend

1. **Never use `metadata` or `registry` as SQLAlchemy column names.** They are reserved by SQLAlchemy's declarative API and cause `InvalidRequestError` on import. Use `change_metadata`, `item_metadata`, etc.

2. **Always use `omoi_os.utils.datetime.utc_now()`** instead of `datetime.utcnow()`. The former returns timezone-aware datetimes compatible with the database.

3. **Use `structured_output()` for LLM calls that need structured data.** Never manually parse JSON from LLM responses.
   ```python
   from omoi_os.services.llm_service import get_llm_service
   llm = get_llm_service()
   result = await llm.structured_output(prompt="...", output_type=MyPydanticModel)
   ```

4. **Settings go in YAML, secrets go in .env.** Application settings in `config/base.yaml`, secret keys/passwords in `.env`. Settings classes extend `OmoiBaseSettings`.

5. **Two separate service initialization points exist.** `api/main.py` (API server) and `workers/orchestrator_worker.py` (background worker) initialize different service sets. They run as separate processes and do not share state. See the Service Availability Matrix in [ARCHITECTURE.md](ARCHITECTURE.md).

### Frontend

1. **Check `components/ui/` before creating new primitives.** 40+ ShadCN components are available. Don't reinvent Button, Card, Dialog, etc.

2. **One hook per domain in `hooks/`.** Follow the pattern in `useProjects.ts` or `useSpecs.ts`. Use React Query for server state.

3. **API calls go through `lib/api/client.ts`.** Add domain-specific files to `lib/api/` (e.g., `projects.ts`, `specs.ts`). Never call `fetch` directly.

4. **Route groups**: `(app)` for authenticated pages, `(auth)` for auth flows, root for public pages.

## Common Tasks

### Add a new API endpoint

1. Create or edit a route file in `backend/omoi_os/api/routes/`
2. Add the service method in `backend/omoi_os/services/`
3. Register the route in `backend/omoi_os/api/main.py` if it's a new router
4. Add tests in `backend/tests/`
5. Run `just test` to verify

### Add a new frontend page

1. Create `page.tsx` in the correct `frontend/app/` route group
2. Add a sidebar panel in `components/panels/` if needed, register in `ContextualPanel.tsx`
3. Create domain hooks in `hooks/` and API functions in `lib/api/`
4. Use existing ShadCN components from `components/ui/`

### Add a new database model

1. Create the model in `backend/omoi_os/models/`
2. Create an Alembic migration: `cd backend && uv run alembic revision -m "description"`
3. Apply it: `uv run alembic upgrade head`
4. Never use `metadata` or `registry` as column names

### Propose a feature

Write an OIP (OmoiOS Improvement Proposal) following the template in `docs/proposals/TEMPLATE.md`. See `docs/proposals/README.md` for the process.

## Development Commands

```bash
just --list          # All available commands
just dev-all         # Full stack with hot-reload
just test            # Affected tests only (via testmon)
just test-all        # Full test suite
just format          # Auto-format code
just check           # Lint + type checks
```

**Ports**: PostgreSQL 15432, Redis 16379, Backend API 18000, Frontend 3000

## Finding Things

| What you need | Where to look |
|---------------|---------------|
| API route for a feature | `backend/omoi_os/api/routes/` — files named by domain |
| Business logic | `backend/omoi_os/services/` — 40+ service files |
| Database schema | `backend/omoi_os/models/` — SQLAlchemy models |
| Frontend page | `frontend/app/(app)/` — route structure matches URL |
| React component | `frontend/components/{domain}/` — grouped by domain |
| Data fetching hook | `frontend/hooks/use{Domain}.ts` |
| API client function | `frontend/lib/api/{domain}.ts` |
| Type definitions | `frontend/lib/api/types.ts` |
| Page flow documentation | `docs/page_flows/` — 24 documented flows |
| User journey documentation | `docs/user_journey/` — end-to-end journey docs |
| Architecture deep-dives | `docs/architecture/01-*.md` through `14-*.md` |
| Improvement proposals | `docs/proposals/` — OIP system |
| Config settings | `backend/config/base.yaml` |
| Test examples | `backend/tests/unit/`, `backend/tests/integration/` |

## Architecture Summary

OmoiOS has four core systems:

1. **Planning** — Spec State Machine converts feature ideas through EXPLORE → PRD → REQUIREMENTS → DESIGN → TASKS → SYNC → COMPLETE. Each phase has an LLM evaluator (quality gate).

2. **Execution** — OrchestratorWorker dispatches tasks to Daytona sandboxes where ClaudeSandboxWorker runs using the Claude Agent SDK. Three modes: exploration, implementation, validation.

3. **Discovery** — DiscoveryService enables adaptive branching when agents find new requirements during execution. A Phase 3 agent can spawn Phase 1 investigation tasks.

4. **Readjustment** — MonitoringLoop runs Guardian (trajectory analysis, 60s), Conductor (coherence + duplicate detection, 5min), and Health Check (30s). Can redirect, refocus, or stop agents.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full diagram and deep-dive links.
