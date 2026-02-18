# Contributing to OmoiOS

## Ways to Contribute

Pick an entry point that matches your familiarity with the project:

| Contribution type | Scope | Where to start |
|-------------------|-------|----------------|
| **Fix a typo or docs error** | Single file | Open a PR directly — no issue needed |
| **Fix a bug** | Localized code change | Open or find a [GitHub issue](https://github.com/kivo360/OmoiOS/issues), reference it in your PR |
| **Small improvement** | Under ~100 lines, no new routes/tables | Open a [GitHub issue](https://github.com/kivo360/OmoiOS/issues) first so maintainers can weigh in |
| **New feature or architectural change** | New routes, models, services, or cross-cutting changes | Write an OIP (see [Proposing Features](#proposing-features) below) |

If you're unsure which category your change falls into, open an issue and ask.

## Orientation

Read the documents relevant to your change:

| Document | Read it when... |
|----------|-----------------|
| [UI.md](UI.md) | Touching frontend routes, components, or hooks |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Touching backend services, workflows, or system design |
| [backend/CLAUDE.md](backend/CLAUDE.md) | Writing backend code (conventions, patterns, gotchas) |
| [CLAUDE.md](CLAUDE.md) | Need monorepo layout, dev commands, or port configuration |

For AI coding agents, see [AGENTS.md](AGENTS.md).

## Local Setup

**Prerequisites**: Python 3.12+, Node.js 22+ with pnpm, Docker, [uv](https://docs.astral.sh/uv/), [just](https://github.com/casey/just)

All commands run from the repo root:

```bash
git clone https://github.com/kivo360/OmoiOS.git && cd OmoiOS

# Infrastructure
docker-compose up -d postgres redis

# Backend
uv sync --group test --group dev
cp backend/.env.example backend/.env
uv run alembic -c backend/alembic.ini upgrade head

# Frontend
cd frontend && pnpm install && cp .env.example .env.local && cd ..

# Verify everything works
just check && just test
```

### Environment variables

The `.env.example` files have working defaults for local Docker services (database, Redis). The only keys you need to fill in for basic development:

| Key | Where | Required for |
|-----|-------|-------------|
| `AUTH_JWT_SECRET_KEY` | `backend/.env` | Any auth flow. Generate with `openssl rand -hex 32` |
| `LLM_API_KEY` | `backend/.env` | LLM-dependent features (trajectory analysis, structured output) |
| `ANTHROPIC_API_KEY` | `backend/.env` | Claude-specific agent features |

Everything else (Sentry, PostHog, OAuth providers, Supabase) is optional for local development.

### Verify setup succeeded

After running the setup commands, confirm:

```bash
just test           # Should print "X passed" with zero failures
just frontend-build # Should complete without errors
```

If `just test` fails with a database connection error, check that Docker containers are running: `docker-compose ps`.

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

### Issue-first workflow

For anything beyond a typo fix, **open or reference a GitHub issue before writing code**:

1. Check [existing issues](https://github.com/kivo360/OmoiOS/issues) to avoid duplicates
2. Open an issue describing the problem or desired behavior
3. Wait for a maintainer to confirm the approach (especially for backend or cross-cutting changes)
4. Create a branch: `feat/`, `fix/`, `refactor/`, or `docs/` prefix
5. Make changes, following the conventions below
6. Run `just check` and `just test` (backend) plus `just frontend-check` (frontend)
7. Open a PR against `main` referencing the issue

### Commit messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/). Format:

```
<type>: <short description>

<optional body explaining why, not what>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `security`, `chore`

Examples from this repo:

```
feat: add OIP proposal skill for interactive proposal creation
fix: correct ApiError constructor call for 429 rate limit handling
security: require authentication on all explore API endpoints
docs: add OIP proposal system, rewrite contributor docs for AI agents
```

### Useful commands

```bash
# Overview
just --list               # See all commands

# Full stack
just dev-all              # Backend + frontend with hot-reload

# Backend
just check                # Ruff fix + format (auto-fixes issues)
just test                 # Affected tests only (fast, via testmon)
just test-all             # Full suite
just format               # Auto-format (same as check)
just lint                 # Ruff check only (no fixes)

# Frontend
just frontend-dev         # Dev server (port 3000)
just frontend-check       # Prettier format + TypeScript type check
just frontend-format      # Prettier format only
just frontend-type-check  # TypeScript only
just frontend-build       # Production build
cd frontend && pnpm test  # Vitest (unit tests)
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

**Backend** (pytest):

```bash
just test              # Affected only (~10-30s)
just test-unit         # Unit tests
just test-integration  # Integration tests
```

- Place tests in `backend/tests/{unit,integration,e2e}/`
- Name: `test_<scenario>_<expected_outcome>`
- Pattern: Arrange-Act-Assert with pytest fixtures

**Frontend** (Vitest):

```bash
cd frontend && pnpm test       # Watch mode
cd frontend && pnpm test:run   # Single run
```

- Place tests in `frontend/__tests__/` mirroring the source path
- Frontend test coverage is currently minimal — contributions here are welcome

### Database migrations

```bash
cd backend
uv run alembic revision -m "description of change"
uv run alembic upgrade head
```

## Proposing Features

Every new feature follows a three-step process, all captured in a single OmoiOS Improvement Proposal (OIP):

1. **Propose** — Describe the problem, who it affects, and the solution at a high level. The proposal's Motivation and Abstract sections cover this.
2. **Prototype** — Define how to validate the idea cheaply before committing to full integration. The Specification section should include a prototyping approach (e.g., feature flag, standalone route, `/try` endpoint) with concrete acceptance criteria.
3. **Integrate** — Lay out the production integration path: which existing files change, what new files are needed, database migrations, API endpoints, and how the feature connects to the rest of the system. This is the bulk of the Specification section.

All three steps live in a single OIP document so reviewers can evaluate the full lifecycle in one place.

### When you need an OIP vs. when you don't

| Needs an OIP | Does NOT need an OIP |
|-------------|---------------------|
| New route or page | Bug fix |
| New database table or migration | Documentation improvement |
| New backend service | Dependency update |
| Changes to auth, billing, or agent execution | Refactor that doesn't change behavior |
| Anything touching >5 files across frontend and backend | Adding tests for existing code |

When in doubt, open an issue and ask.

### Creating a proposal

**If you're using Claude Code**, run the `/oip-proposal` skill. It walks you through clarifying questions, researches the codebase for accurate file references, and writes the proposal for you.

**If you're writing manually:**

1. Copy `docs/proposals/TEMPLATE.md` to `docs/proposals/oip-NNNN-short-title.md`
2. Fill in all sections — make sure the Specification covers both the prototype plan and the integration plan
3. Add the new OIP to the status table in `docs/proposals/README.md`
4. Submit as a PR for discussion

See [docs/proposals/README.md](docs/proposals/README.md) for the full process, lifecycle, and existing proposals.

## PR Checklist

- [ ] References a GitHub issue (except for typo/docs fixes)
- [ ] Commit messages follow [Conventional Commits](#commit-messages) format
- [ ] `just check` passes (backend ruff fix + format)
- [ ] `just test` passes (backend)
- [ ] `just frontend-check` passes (if frontend changed)
- [ ] `just frontend-build` succeeds (if frontend changed)
- [ ] New functionality has tests
- [ ] No secrets or credentials in the diff
- [ ] Documentation updated if behavior changed

## Getting Help

- **Questions about contributing**: Open a [GitHub discussion](https://github.com/kivo360/OmoiOS/issues) or comment on a related issue
- **Bug reports**: [Open an issue](https://github.com/kivo360/OmoiOS/issues/new) with reproduction steps
- **Security vulnerabilities**: **Do not** open a public issue. Email security@omoios.dev — see [SECURITY.md](SECURITY.md) for details

## License

Contributions are licensed under the [Apache License 2.0](LICENSE). By submitting a pull request, you agree that your contributions will be licensed under the same terms.
