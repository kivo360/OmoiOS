# Part 13: API Route Catalog

> Summary doc — this is the primary API reference for all backend routes.

## Overview

OmoiOS exposes a **FastAPI** REST API at `https://api.omoios.dev` with routes organized by domain. All protected routes require JWT authentication via `Authorization: Bearer <token>` header.

## Route Files

All routes are in `backend/omoi_os/api/routes/`:

### Core Resources

| File | Prefix | Purpose |
|------|--------|---------|
| `auth.py` | `/api/v1/auth` | Login, register, refresh, verify email, password reset |
| `oauth.py` | `/api/v1/oauth` | GitHub/Google OAuth flows |
| `users.py` | `/api/v1/users` | User profile management |
| `organizations.py` | `/api/v1/organizations` | Organization CRUD, member management |
| `projects.py` | `/api/v1/projects` | Project CRUD, settings |
| `specs.py` | `/api/v1/specs` | Spec CRUD, phase management, execution |
| `tickets.py` | `/api/v1/tickets` | Ticket CRUD, status transitions, search |
| `tasks.py` | `/api/v1/tasks` | Task CRUD, assignment, status updates |

### Workflow Management

| File | Prefix | Purpose |
|------|--------|---------|
| `phases.py` | `/api/v1/phases` | Phase management, gate configuration |
| `board.py` | `/api/v1/board` | Kanban board views, ticket ordering |
| `graph.py` | `/api/v1/graph` | Dependency graph visualization, critical path |
| `results.py` | `/api/v1/results` | Task result submission and retrieval |
| `branch_workflow.py` | `/api/v1/branch-workflow` | Git branch lifecycle management |
| `collaboration.py` | `/api/v1/collaboration` | Agent collaboration channels |

### Agent & Sandbox

| File | Prefix | Purpose |
|------|--------|---------|
| `agents.py` | `/api/v1/agents` | Agent registration, status, capabilities |
| `sandbox.py` | `/api/v1/sandboxes` | Sandbox events, messages, trajectory |

### Monitoring & Quality

| File | Prefix | Purpose |
|------|--------|---------|
| `monitor.py` | `/api/v1/monitor` | Monitoring metrics, anomaly data |
| `guardian.py` | `/api/v1/guardian` | Guardian analysis results |
| `watchdog.py` | `/api/v1/watchdog` | Watchdog alerts and policies |
| `diagnostic.py` | `/api/v1/diagnostic` | Diagnostic run management |
| `quality.py` | `/api/v1/quality` | Quality check results |
| `validation.py` | `/api/v1/validation` | Validation review management |
| `alerts.py` | `/api/v1/alerts` | Alert configuration and history |

### Version Control

| File | Prefix | Purpose |
|------|--------|---------|
| `commits.py` | `/api/v1/commits` | Commit history linked to tickets |
| `github.py` | `/api/v1/github` | GitHub webhook receiver |
| `github_repos.py` | `/api/v1/github/repos` | Repository listing and management |

### Infrastructure

| File | Prefix | Purpose |
|------|--------|---------|
| `events.py` | `/api/v1/events` | WebSocket event streaming |
| `mcp.py` | `/api/v1/mcp` | MCP server management, tool registry |
| `memory.py` | `/api/v1/memory` | Memory search, pattern management |
| `reasoning.py` | `/api/v1/reasoning` | Agent reasoning chain access |

### Billing & Business

| File | Prefix | Purpose |
|------|--------|---------|
| `billing.py` | `/api/v1/billing` | Stripe checkout, portal, usage, invoices |
| `costs.py` | `/api/v1/costs` | Cost tracking per workflow/agent |
| `onboarding.py` | `/api/v1/onboarding` | User onboarding progress |
| `analytics_proxy.py` | `/api/v1/analytics` | Analytics data proxy |

### Developer Tools

| File | Prefix | Purpose |
|------|--------|---------|
| `debug.py` | `/api/v1/debug` | Debug endpoints (dev only) |
| `explore.py` | `/api/v1/explore` | AI-assisted codebase exploration |

## Key Patterns

### Authentication

```python
# Protected route
@router.get("/protected")
async def protected_route(user: User = Depends(get_current_user)):
    ...

# Optional auth
@router.get("/public-or-private")
async def flexible_route(user: Optional[User] = Depends(get_current_user_optional)):
    ...

# Role-required
@router.get("/admin-only")
async def admin_route(user: User = Depends(require_role("admin"))):
    ...
```

### Service Initialization

Most services are initialized in `api/main.py:lifespan()` and accessed via global variables. Some services (noted in [Integration Gaps](14-integration-gaps.md#gap-6-api-routes-without-initialization)) are created per-request, which may cause performance issues.

## Port Configuration

| Service | Port | Note |
|---------|------|------|
| Backend API | 18000 | +10000 offset from standard |
| PostgreSQL | 15432 | +10000 offset |
| Redis | 16379 | +10000 offset |
| Frontend | 3000 | Standard |

## API Documentation

FastAPI auto-generates interactive API docs:
- **Swagger UI**: `https://api.omoios.dev/docs`
- **ReDoc**: `https://api.omoios.dev/redoc`
