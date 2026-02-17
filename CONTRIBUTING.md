# Contributing to OmoiOS

## Orientation

Before making changes, read these documents in order:

| Document | What it tells you |
|----------|-------------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design — planning, execution, discovery, readjustment systems, service map |
| [UI.md](UI.md) | Frontend routes, components, state management, design system |
| [backend/CLAUDE.md](backend/CLAUDE.md) | Backend conventions, database patterns, LLM service usage, testing |
| [CLAUDE.md](CLAUDE.md) | Monorepo structure, development commands, port configuration |

For AI coding agents, see [AGENTS.md](AGENTS.md).

## Local Setup

**Prerequisites**: Python 3.12+, Node.js 22+ with pnpm, Docker, [uv](https://docs.astral.sh/uv/), [just](https://github.com/casey/just)

```bash
git clone https://github.com/kivo360/OmoiOS.git && cd OmoiOS
docker-compose up -d postgres redis
cd backend && uv sync --group test --group dev
cd ../frontend && pnpm install
cp ../backend/.env.example ../backend/.env
cp .env.example .env.local
cd ../backend && uv run alembic upgrade head
just check && just test
```

## Monorepo Layout

```
senior_sandbox/
├── backend/                 # FastAPI + SQLAlchemy + Redis
│   ├── omoi_os/             # Main Python package
│   │   ├── api/routes/      # ~30 route files by domain
│   │   ├── services/        # Business logic services
│   │   ├── models/          # SQLAlchemy models (~60 tables)
│   │   └── config.py        # Settings (YAML + env)
│   ├── config/              # YAML settings (base.yaml, test.yaml)
│   └── tests/               # unit/, integration/, e2e/
├── frontend/                # Next.js 15 App Router
│   ├── app/                 # Route groups: (app), (auth), (dashboard)
│   ├── components/          # UI components (ShadCN + custom)
│   ├── hooks/               # ~30 React Query + Zustand hooks
│   ├── lib/api/             # API client by domain
│   └── providers/           # Context providers
├── subsystems/spec-sandbox/ # Spec execution runtime
├── docs/                    # 100+ documentation files
│   ├── proposals/           # OmoiOS Improvement Proposals (OIPs)
│   ├── page_flows/          # Page-by-page UI flow documentation
│   ├── user_journey/        # End-to-end user journey docs
│   └── architecture/        # System deep-dives (01-13)
└── Justfile                 # Task runner
```

## Making Changes

### Branch and PR workflow

1. Create a branch: `feat/`, `fix/`, `refactor/`, or `docs/` prefix
2. Make changes, following the conventions below
3. Run `just check` (lint + types) and `just test` (affected tests)
4. Open a PR against `main` with a clear title and description

### Useful commands

```bash
just --list          # See all commands
just dev-all         # Full stack with hot-reload
just test            # Affected tests only (fast, via testmon)
just test-all        # Full suite
just format          # Auto-format
just check           # Lint + type checks
```

## Conventions

### Backend (Python)

- **Formatting/linting**: ruff
- **Async**: Use `async/await` for all I/O
- **Datetime**: Always `omoi_os.utils.datetime.utc_now()`, never `datetime.utcnow()`
- **LLM calls**: Use `llm_service.structured_output()` with Pydantic models, never parse JSON manually
- **SQLAlchemy**: Never use `metadata` or `registry` as column names (reserved words)
- **Config**: Application settings in `config/*.yaml`, secrets in `.env` only
- **Settings classes**: Extend `OmoiBaseSettings` with `yaml_section` and `@lru_cache` factory

### Frontend (TypeScript)

- **Framework**: Next.js 15 App Router
- **UI components**: ShadCN UI (Radix + Tailwind). Check `components/ui/` before creating new primitives.
- **State**: React Query for server state, Zustand for client state
- **API calls**: Use the typed client in `lib/api/client.ts`, add new domain files to `lib/api/`
- **Hooks**: One hook per domain in `hooks/`. Follow existing patterns (e.g., `useProjects.ts`, `useSpecs.ts`).
- **Route structure**: Pages go in `app/(app)/` for authenticated routes, `app/(auth)/` for auth flows

### Testing

```bash
# Backend tests
just test              # Affected only (~10-30s)
just test-unit         # Unit tests
just test-integration  # Integration tests
```

- Place tests in `backend/tests/{unit,integration,e2e}/`
- Name: `test_<scenario>_<expected_outcome>`
- Pattern: Arrange-Act-Assert with pytest fixtures

### Database migrations

```bash
cd backend
uv run alembic revision -m "description of change"
uv run alembic upgrade head
```

## Proposing Features

For non-trivial features or architectural changes, write an OmoiOS Improvement Proposal (OIP):

1. Copy `docs/proposals/TEMPLATE.md` to `docs/proposals/oip-NNNN-short-title.md`
2. Fill in all sections (Abstract, Motivation, Specification, Rationale, Security)
3. Add to the status table in `docs/proposals/README.md`
4. Submit as a PR for discussion

See [docs/proposals/README.md](docs/proposals/README.md) for the full process and existing proposals.

## PR Checklist

- [ ] `just test` passes
- [ ] `just check` passes
- [ ] New functionality has tests
- [ ] No secrets or credentials in the diff
- [ ] Documentation updated if behavior changed

## Security

If you discover a security vulnerability, **do not** open a public issue. See [SECURITY.md](SECURITY.md).

## License

Contributions are licensed under the [Apache License 2.0](LICENSE).
