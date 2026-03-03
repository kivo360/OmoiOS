# OmoiOS Installation Runbook (AI-Executable)

You are an AI agent setting up OmoiOS on a developer's machine. This document gives you everything: system understanding, exact commands, config file semantics, Docker architecture, environment variables, and failure recovery. Follow each phase in order. Verify before advancing.

---

## System Overview

OmoiOS is a monorepo with three main parts:

```
OmoiOS/
├── backend/          Python 3.12+ — FastAPI API server, workers, migrations
├── frontend/         Node.js 22+ — Next.js 15 App Router
├── Justfile          Command runner — all dev commands go through this
├── docker-compose.yml   Full-stack orchestration (builds everything in Docker)
├── .env.example      Root env template
└── backend/
    ├── docker-compose.yml   Dev-mode compose (Postgres, Redis, API, workers with hot-reload)
    ├── Dockerfile.api       Multi-stage: builds the FastAPI server
    ├── Dockerfile.worker    Multi-stage: builds the Taskiq background worker
    ├── config/base.yaml     Default application settings (version controlled)
    ├── config/local.yaml    Local dev overlay — disables external services
    ├── .env.example         Backend-specific env template
    └── docker/initdb/01_extensions.sql   Runs on first Postgres start
```

**There are TWO docker-compose files.** This is important:

| File | Purpose | When to use |
|------|---------|-------------|
| `docker-compose.yml` (root) | Full stack — builds ALL containers from Dockerfiles | `docker compose up` from project root. Runs everything in Docker. |
| `backend/docker-compose.yml` | Dev infrastructure + hot-reload | `just docker-up` / `just watch`. Only runs Postgres + Redis in containers; you run API/frontend locally. |

**For local development, use `backend/docker-compose.yml` (via `just` commands).** The root compose is for Docker-only setups or CI.

---

## Tool Chain

These are the six tools required. The AI must install any that are missing.

### 1. Docker (24+)

Docker runs PostgreSQL and Redis. On Linux, you need Docker Engine (not Desktop). On macOS, you need Docker Desktop.

**Check:** `docker --version && docker info >/dev/null 2>&1`

If `docker --version` works but `docker info` fails, the daemon isn't running.

**Install — macOS:**
```bash
brew install --cask docker
open -a Docker
# Wait for daemon:
for i in $(seq 1 60); do docker info >/dev/null 2>&1 && break || sleep 1; done
```

**Install — Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl start docker && sudo systemctl enable docker
sudo usermod -aG docker $USER
newgrp docker
```

**Install — Fedora/RHEL:**
```bash
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl start docker && sudo systemctl enable docker
sudo usermod -aG docker $USER
newgrp docker
```

**Install — Arch:**
```bash
sudo pacman -Sy --needed --noconfirm docker docker-compose
sudo systemctl start docker && sudo systemctl enable docker
sudo usermod -aG docker $USER
newgrp docker
```

**Critical Linux note:** `sudo usermod -aG docker $USER` requires a re-login to take effect. `newgrp docker` is a workaround for the current shell. If Docker commands still fail with "permission denied", the user must log out and back in.

---

### 2. Python (3.12+)

**Check:** `python3 --version`

**Install — macOS:** `brew install python@3.12`
**Install — Ubuntu/Debian:** `sudo apt-get install -y python3.12 python3.12-venv python3.12-dev`
**Install — Fedora:** `sudo dnf install -y python3.12 python3.12-devel`
**Install — Arch:** `sudo pacman -Sy --needed --noconfirm python`

---

### 3. Node.js (22+)

**Check:** `node --version`

**Install — macOS:** `brew install node`
**Install — Ubuntu/Debian:**
```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
```
**Install — Fedora:**
```bash
curl -fsSL https://rpm.nodesource.com/setup_22.x | sudo bash -
sudo dnf install -y nodejs
```
**Install — Arch:** `sudo pacman -Sy --needed --noconfirm nodejs`

---

### 4. uv (Python package manager)

**Check:** `uv --version`

**Install — all platforms:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After install, uv lives in `~/.local/bin/`. Make sure it's on PATH:
```bash
source $HOME/.local/bin/env 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"
```

If the shell doesn't pick it up, add `export PATH="$HOME/.local/bin:$PATH"` to `~/.bashrc` or `~/.zshrc`.

---

### 5. pnpm (Node.js package manager)

**Check:** `pnpm --version`

**Install — all platforms (via corepack, preferred):**
```bash
corepack enable
corepack prepare pnpm@latest --activate
```

If corepack isn't available (older Node.js): `npm install -g pnpm`

---

### 6. just (command runner)

`just` is the single entry point for every dev command. The project's `Justfile` has 100+ recipes. **Nothing in this project should be run without `just` unless this document explicitly says otherwise.**

**Check:** `just --version`

**Pick the install method that matches the user's platform and package manager:**

#### Cross-Platform

| Package Manager | Command |
|----------------|---------|
| Cargo (Rust) | `cargo install just` |
| Conda | `conda install -c conda-forge just` |
| Homebrew | `brew install just` |
| Nix | `nix-env -iA nixpkgs.just` |
| npm | `npm install -g rust-just` |
| pipx | `pipx install rust-just` |
| Snap | `sudo snap install --edge --classic just` |
| asdf | `asdf plugin add just && asdf install just latest` |
| arkade | `arkade get just` |
| Installer script | `curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh \| bash -s -- --to /usr/local/bin` |

If `/usr/local/bin` requires sudo, install to user-local instead:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to ~/.local/bin
export PATH="$HOME/.local/bin:$PATH"
```

#### macOS

| Package Manager | Command |
|----------------|---------|
| Homebrew | `brew install just` |
| MacPorts | `port install just` |

#### Linux

| Distro | Package Manager | Command |
|--------|----------------|---------|
| Alpine | apk | `apk add just` |
| Arch | pacman | `pacman -S just` |
| Debian 13+ / Ubuntu 24.04+ | apt | `apt install just` |
| Fedora | dnf | `dnf install just` |
| Gentoo | Portage | `emerge -av dev-build/just` |
| NixOS | Nix | `nix-env -iA nixos.just` |
| openSUSE | Zypper | `zypper in just` |
| Solus | eopkg | `eopkg install just` |
| Void | XBPS | `xbps-install -S just` |

#### Windows

| Package Manager | Command |
|----------------|---------|
| Chocolatey | `choco install just` |
| Scoop | `scoop install just` |
| winget | `winget install --id Casey.Just --exact` |

#### BSD

| OS | Command |
|----|---------|
| FreeBSD | `pkg install just` |
| OpenBSD | `pkg_add just` |

**Verify `just` can read the project Justfile:**
```bash
cd /path/to/OmoiOS && just --list | head -5
```

This must show recipe names. If it shows "No justfile found", you're in the wrong directory.

---

### Verification Gate

Run all of these. All must pass before continuing.

```bash
docker --version          # Docker 24+
docker info >/dev/null 2>&1 && echo "daemon: ok" || echo "daemon: FAILED"
python3 --version         # Python 3.12+
node --version            # v22+
uv --version              # uv 0.4+
pnpm --version            # 9+
just --version            # just 1+
```

**STOP** if any check fails. Fix it before proceeding.

---

## Phase 1: Clone and Enter Project

```bash
git clone https://github.com/kivo360/OmoiOS.git
cd OmoiOS
```

Verify:
```bash
test -f Justfile && test -f .env.example && test -d backend && test -d frontend && echo "OK" || echo "FAIL"
```

---

## Phase 2: Run Quickstart

The project has a single command that handles everything from Phase 3–7 below:

```bash
just quickstart
```

**What `just quickstart` does internally (in this order):**
1. Copies `.env.example` → `.env.local` (root) if it doesn't exist
2. Copies `frontend/.env.example` → `frontend/.env.local` if it doesn't exist
3. Runs `docker compose up -d --wait postgres redis` from `backend/` — starts Postgres 18 and Redis 7
4. Runs `uv sync --group test` from `backend/` — installs all Python dependencies into `.venv/`
5. Runs `uv run python -m alembic upgrade head` from `backend/` — applies all 70+ database migrations
6. Runs `pnpm install` from `frontend/` — installs all Node.js dependencies

**If `just quickstart` succeeds, skip to Phase 8.**

If it fails, use Phases 3–7 below to debug and complete manually.

---

## Phase 3: Environment Files

There are three `.env.example` files. Each needs a `.env.local` copy:

```bash
# Root — used by root docker-compose.yml
cp .env.example .env.local

# Frontend — used by Next.js
cp frontend/.env.example frontend/.env.local
```

The `backend/.env.example` is more detailed but the root `.env.local` is what's actually loaded at runtime (Pydantic Settings searches up from `backend/` to the project root).

### Understanding the env files

**Priority order:** Environment variables > `.env.local` > `.env` > `config/*.yaml` defaults

**The root `.env.local` is the only file you need to edit.** It controls both Docker Compose and the backend. The frontend `.env.local` has sensible defaults already.

### Environment variable reference

These are the variables in `.env.local`. Grouped by whether the system works without them.

**Required for the stack to start (already set with defaults):**

| Variable | Default | What it does |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:15432/omoi_os` | PostgreSQL connection. The Docker containers use `app_db` as the DB name. Use whatever matches your Docker compose. | <!-- pragma: allowlist secret -->
| `REDIS_URL` | `redis://localhost:16379` | Redis connection. |
| `OMOIOS_ENV` | `local` | Which `config/*.yaml` overlay to load. Use `local` for dev. |

**Optional — AI features require at least one:**

| Variable | How to get it | What it enables |
|----------|--------------|-----------------|
| `LLM_API_KEY` | Sign up at the LLM provider (Fireworks AI, OpenAI-compatible) | Structured LLM outputs, spec generation, title generation |
| `LLM_FIREWORKS_API_KEY` | https://fireworks.ai/ → API Keys | Same as above (Fireworks-specific) |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/ → API Keys | Claude Agent SDK — used by sandbox workers for autonomous coding |
| `OPENAI_API_KEY` | https://platform.openai.com/ → API Keys | Embeddings (alternative to Fireworks) |

**Optional — feature-specific:**

| Variable | How to get it | What it enables |
|----------|--------------|-----------------|
| `GITHUB_TOKEN` | https://github.com/settings/tokens → Generate new token (classic), scopes: `repo` | GitHub integration — branch management, PR creation |
| `DAYTONA_API_KEY` | https://app.daytona.io/ → Settings → API Keys | Daytona sandbox execution — isolated workspaces for agents |
| `AUTH_JWT_SECRET_KEY` | `openssl rand -hex 32` | JWT signing. Dev default works. Generate a real one for production. |
| `AUTH_GITHUB_CLIENT_ID` / `AUTH_GITHUB_CLIENT_SECRET` | https://github.com/settings/developers → New OAuth App | GitHub OAuth login |
| `AUTH_GOOGLE_CLIENT_ID` / `AUTH_GOOGLE_CLIENT_SECRET` | https://console.cloud.google.com/apis/credentials | Google OAuth login |
| `STRIPE_API_KEY` / `STRIPE_WEBHOOK_SECRET` | https://dashboard.stripe.com/apikeys | Billing / subscriptions |

**Important: The app starts and runs without ANY optional keys.** The dashboard, API, task management, and database all work. AI-powered features (spec generation, agent execution) require LLM keys.

### Setting variables for the user

If the user provides API keys, write them into `.env.local`:

```bash
# Example: user provided an Anthropic key
sed -i 's/^ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=sk-ant-xxxxx/' .env.local

# Or append if the variable isn't in the file:
echo 'ANTHROPIC_API_KEY=sk-ant-xxxxx' >> .env.local
```

On macOS, `sed -i` requires `sed -i ''` (empty extension):
```bash
sed -i '' 's/^ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=sk-ant-xxxxx/' .env.local
```

---

## Phase 4: Docker Services

### What gets started

The dev Docker Compose (`backend/docker-compose.yml`) runs:

| Service | Image | Container Name | Port | Health Check |
|---------|-------|----------------|------|-------------|
| PostgreSQL 18 + pgvector + vchord | `tensorchord/vchord-suite:pg18-latest` | `omoi_os_postgres` | `15432:5432` | `pg_isready` every 5s |
| Redis 7 | `redis:7-alpine` | `omoi_os_redis` | `16379:6379` | `redis-cli ping` every 5s |

PostgreSQL auto-runs `backend/docker/initdb/01_extensions.sql` on first start, which creates:
- `vector` extension (pgvector for embeddings)
- `pg_trgm` extension (trigram text search)
- `fuzzystrmatch` extension (fuzzy matching)
- `vchord` extension (if available in the image)

### Start services

```bash
cd backend && docker compose up -d --wait postgres redis && cd ..
```

The `--wait` flag blocks until both containers pass health checks.

### Verify

```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep omoi_os
```

Expected:
```
omoi_os_postgres   Up X seconds (healthy)
omoi_os_redis      Up X seconds (healthy)
```

Both must show `(healthy)`.

### Failure recovery

**Port 15432 in use:**
```bash
lsof -i :15432
# or
ss -tlnp | grep 15432
```
Kill the conflicting process or change the port in `backend/docker-compose.yml`.

**Container keeps restarting:**
```bash
cd backend && docker compose logs postgres
cd backend && docker compose logs redis
```

**Nuclear reset (destroys all data):**
```bash
cd backend && docker compose down -v && docker compose up -d --wait postgres redis
```

---

## Phase 5: Backend Dependencies

```bash
cd backend && uv sync --group test && cd ..
```

This creates a `.venv/` at the project root (not inside `backend/` — uv workspaces put it at the workspace root). Installs ~450 packages.

### Verify

```bash
cd backend && uv run python -c "import omoi_os; print('OK')" && cd ..
```

Must print `OK`.

### Failure recovery

**Resolver conflict:** `cd backend && uv sync --group test --refresh`
**Wrong Python version:** `uv python install 3.12 && uv sync --group test`

---

## Phase 6: Database Migrations

```bash
cd backend && uv run python -m alembic upgrade head && cd ..
```

This runs 70+ Alembic migration files, creating all tables, indexes, and constraints.

### Verify

```bash
cd backend && uv run python -m alembic current && cd ..
```

Must print a hash followed by `(head)`.

### Failure recovery

**"No module named 'whenever'":** Phase 5 didn't complete. Re-run `uv sync`.
**"Connection refused on port 15432":** Phase 4 didn't complete. Check `docker ps`.
**"Relation already exists":** Migrations already ran. This is fine — `upgrade head` is idempotent.

---

## Phase 7: Frontend Dependencies

```bash
cd frontend && pnpm install && cd ..
```

### Verify

```bash
test -d frontend/node_modules/.pnpm && echo "OK" || echo "FAIL"
```

### Failure recovery

**Lockfile mismatch:** `cd frontend && rm -rf node_modules && pnpm install`
**corepack issues:** `corepack enable && corepack prepare pnpm@latest --activate && cd frontend && pnpm install`

---

## Phase 8: Verify Installation

Run the built-in health checker:

```bash
just bootstrap
```

This checks Python, Node.js, Docker, uv, PostgreSQL connectivity, Redis connectivity, dependencies, and migrations. All required checks must show `✅`.

---

## Phase 9: Start the Application

**Recommended — start everything in one terminal:**
```bash
just dev-all
```

This starts the backend API on `:18000` and the frontend on `:3000`.

**Alternative — separate terminals for more control:**

| Terminal | Command | What it runs |
|----------|---------|-------------|
| 1 | `just backend-api` | FastAPI on http://localhost:18000 |
| 2 | `just frontend-dev` | Next.js on http://localhost:3000 |

**Alternative — Docker hot-reload for backend:**

| Terminal | Command | What it runs |
|----------|---------|-------------|
| 1 | `just watch` | Backend services in Docker with file sync |
| 2 | `just frontend-dev` | Next.js locally |

### Verify the stack is running

```bash
# Backend health
curl -sf http://localhost:18000/health | head -c 200 && echo

# Backend API docs reachable
curl -sf -o /dev/null -w "%{http_code}" http://localhost:18000/docs

# Frontend reachable
curl -sf -o /dev/null -w "%{http_code}" http://localhost:3000
```

All must return `200`. If the backend returns connection refused, wait 10 seconds — the server needs a moment to start.

---

## Configuration Deep Dive

### YAML Config System

The backend uses a layered YAML config system:

```
config/base.yaml     ← Default settings (always loaded)
config/local.yaml    ← Overlay for OMOIOS_ENV=local (loaded on top of base)
config/test.yaml     ← Overlay for OMOIOS_ENV=test
```

**`config/local.yaml` is the key file for local development.** It sets:

```yaml
llm:
  mode: "null"          # No LLM calls — prevents errors when no API key is set
git:
  provider: "local"     # Use local git, not GitHub API
sandbox:
  provider: "local"     # Local sandboxes, not Daytona
orchestrator:
  dry_run: true         # Don't actually spawn sandboxes
monitoring:
  replay_mode: true     # Replay mode for monitoring
```

This means **local dev works without any external API keys by default.** The `local.yaml` overlay disables everything that needs external services.

If the user provides API keys (e.g., `LLM_API_KEY`), they can switch to `OMOIOS_ENV=development` in `.env.local` to enable real LLM calls. Or they can edit `config/local.yaml` to change `llm.mode` from `"null"` to `"live"`.

### Config precedence (highest to lowest)

1. Environment variables (e.g., `LLM_API_KEY=xxx`)
2. `.env.local` file
3. `.env` file
4. `config/{OMOIOS_ENV}.yaml` overlay
5. `config/base.yaml` defaults

---

## Docker Architecture

### Backend Dockerfiles

| Dockerfile | What it builds | Entrypoint |
|-----------|---------------|------------|
| `Dockerfile.api` | FastAPI server (2-stage: builder + runtime) | `docker-entrypoint.sh` → runs migrations → starts gunicorn/uvicorn |
| `Dockerfile.worker` | Taskiq background worker | `taskiq worker omoi_os.tasks.broker:broker` |
| `Dockerfile.scheduler` | Scheduled job runner | Cron-like task execution |
| `Dockerfile.cloud-agent` | Cloud agent worker | Agent execution in cloud |

### Frontend Dockerfile

4-stage build:
1. **deps** — installs pnpm + `pnpm install --frozen-lockfile`
2. **dev** — development image with hot-reload (`pnpm dev`)
3. **builder** — runs `pnpm build` to create production bundle
4. **runner** — minimal production image running `node server.js`

The root `docker-compose.yml` uses `target: dev` for the frontend, so it runs in dev mode.

### Root docker-compose.yml (full stack)

Starts everything in containers:

| Service | Image/Build | Port | Depends On |
|---------|------------|------|-----------|
| `postgres` | `pgvector/pgvector:pg16` | `15432:5432` | — |
| `redis` | `redis:7-alpine` | `16379:6379` | — |
| `backend` | Builds `Dockerfile.api` | `18000:8000` | postgres (healthy), redis (healthy) |
| `worker` | Builds `Dockerfile.worker` | — | postgres, redis, backend |
| `frontend` | Builds `frontend/Dockerfile` (dev target) | `3000:3000` | backend |

**Environment variables inside Docker containers use internal hostnames** (`postgres:5432`, `redis:6379`) because containers talk to each other on the Docker network, not through host ports.

### Backend docker-compose.yml (dev mode)

Used by `just docker-up`, `just watch`, etc. Has `develop.watch` blocks for hot-reload:

| Service | Purpose | Hot-reload |
|---------|---------|-----------|
| `postgres` | Database | — |
| `redis` | Cache/queue | — |
| `api` | FastAPI server | Syncs `omoi_os/api`, `omoi_os/services`, `omoi_os/models`, `omoi_os/config` → restarts. Rebuilds on `pyproject.toml`/`uv.lock` changes. |
| `worker` | Background tasks | Syncs `omoi_os/` → restarts |
| `orchestrator` | Task assignment + sandbox spawning | Syncs workers, services, models, config → restarts |
| `monitoring` | Health monitoring loops | Syncs workers, services, models, config → restarts |

### docker-entrypoint.sh (API container)

The API container's entrypoint script:
1. Runs `python -m alembic upgrade head` (auto-migrates on start)
2. Auto-detects CPU cores, calculates worker count: `2 * cores + 1` (capped at 32)
3. If `RELOAD_MODE=true`: starts uvicorn with `--reload` (single worker)
4. If `RELOAD_MODE=false` (default): starts gunicorn with uvicorn workers

---

## `just` Command Reference

These are the commands the AI and user will use daily. Grouped by purpose.

### Setup & Health

| Command | What it does |
|---------|-------------|
| `just quickstart` | One-command setup: env files, Docker, deps, migrations, frontend |
| `just bootstrap` | Check all dependencies and configuration health |
| `just status` | Check which services are running (port + health checks) |
| `just install` | Install all dependencies (backend + frontend) |

### Running Services

| Command | What it does |
|---------|-------------|
| `just dev-all` | Start API + frontend together |
| `just backend-api` | Start only the FastAPI server (`:18000`) |
| `just frontend-dev` | Start only the Next.js dev server (`:3000`) |
| `just watch` | Start all backend services in Docker with hot-reload |
| `just watch-api` | Start only API + infrastructure in Docker |
| `just stop-all` | Stop all running services |
| `just restart-all` | Stop then start everything |

### Docker

| Command | What it does |
|---------|-------------|
| `just docker-up` | Start Postgres + Redis containers |
| `just docker-down` | Stop all Docker containers |
| `just docker-logs` | View container logs (optionally: `just docker-logs postgres`) |
| `just docker-rebuild` | Rebuild and restart containers |
| `just docker-clean` | Remove volumes and rebuild (destroys data) |

### Database

| Command | What it does |
|---------|-------------|
| `just db-migrate` | Apply all pending Alembic migrations |
| `just db-current` | Show current migration version |
| `just db-history` | Show migration history |
| `just db-revision "description"` | Create a new migration file |
| `just db-downgrade` | Rollback one migration |

### Testing

| Command | What it does |
|---------|-------------|
| `just test` | Run unit tests (fast, no external deps) |
| `just test-affected` | Run tests affected by your code changes (testmon) |
| `just test-all` | Full test suite (no testmon, all tests) |
| `just test-unit` | Unit tests only (verbose) |
| `just test-integration` | Integration tests only |
| `just test-match "keyword"` | Tests matching a keyword |
| `just test-watch` | Watch mode — re-runs on changes |
| `just test-coverage` | Generate HTML coverage report |

### Code Quality

| Command | What it does |
|---------|-------------|
| `just check` | Auto-fix lint + format (ruff) |
| `just lint` | Lint only (no auto-fix) |
| `just format` | Format only |
| `just frontend-check` | Frontend format + type check |

---

## Final Verification Checklist

After installation, confirm all of these:

```bash
# 1. Docker services healthy
docker ps | grep -E "omoi_os_(postgres|redis)" | grep -c healthy
# Expected: 2

# 2. Backend deps installed
cd backend && uv run python -c "import omoi_os; print('backend: ok')" && cd ..

# 3. Migrations applied
cd backend && uv run python -m alembic current 2>&1 | grep -c "(head)" && cd ..
# Expected: 1

# 4. Frontend deps installed
test -d frontend/node_modules/.pnpm && echo "frontend: ok"

# 5. Health check
just bootstrap 2>&1 | tail -5

# 6. Stack starts
just dev-all &
sleep 15
curl -sf http://localhost:18000/health && echo " api: ok"
curl -sf -o /dev/null -w "frontend: %{http_code}\n" http://localhost:3000
kill %1 2>/dev/null
```

---

## Idempotency

This entire runbook is safe to re-run at any point. Every step either checks before acting or is inherently idempotent:
- `cp` only runs if target doesn't exist
- `docker compose up -d` is a no-op if containers are already running
- `uv sync` resolves and skips already-installed packages
- `alembic upgrade head` skips already-applied migrations
- `pnpm install` uses lockfile and skips if `node_modules` is current

If the user says "something's broken, start over":
```bash
just docker-clean          # Nuke Docker volumes
just clean-all             # Clean Python/test caches
just quickstart            # Re-run from scratch
```
