---
name: Process Separation via Docker
overview: Separate the orchestrator and monitoring loops into independent Docker containers, leaving the main FastAPI server clean and fast-starting.
todos:
  - id: create-workers-package
    content: Create backend/omoi_os/workers/ package with __init__.py
    status: pending
  - id: orchestrator-worker
    content: Create orchestrator_worker.py - standalone orchestrator loop runner
    status: completed
  - id: monitoring-worker
    content: Create monitoring_worker.py - standalone monitoring loops runner
    status: completed
  - id: docker-compose
    content: Update backend/docker-compose.yml - add orchestrator and monitoring services, add env vars to api
    status: completed
  - id: dockerfile
    content: Verify Dockerfile.worker exists and supports the new worker entry points
    status: pending
  - id: justfile-backend
    content: Add watch, watch-api, orchestrator, monitoring commands to backend/Justfile
    status: completed
  - id: justfile-root
    content: Add root-level wrappers to Justfile (watch, api-light, orchestrator, monitoring, dev-watch)
    status: completed
  - id: test-compose
    content: Test docker compose watch and verify all services communicate
    status: completed
---

# Separate Background Processes via Docker Compose

## Architecture

```mermaid
graph TB
    subgraph docker [Docker Compose Stack]
        api[API Server<br>FastAPI on :18000]
        orchestrator[Orchestrator Worker]
        monitoring[Monitoring Worker]
        redis[(Redis)]
        postgres[(PostgreSQL)]
    end
    
    client[Client/Browser] --> api
    api --> redis
    api --> postgres
    orchestrator --> redis
    orchestrator --> postgres
    orchestrator --> daytona[Daytona Cloud]
    monitoring --> redis
    monitoring --> postgres
```

## Files to Create

### 1. Orchestrator Worker Entry Point

**File:** [backend/omoi_os/workers/orchestrator_worker.py](backend/omoi_os/workers/orchestrator_worker.py)

Standalone script that runs only the orchestrator loop:

- Imports and runs `orchestrator_loop()` from main.py (or extracts it)
- Connects to shared Redis and PostgreSQL
- Handles graceful shutdown on SIGTERM

### 2. Monitoring Worker Entry Point  

**File:** [backend/omoi_os/workers/monitoring_worker.py](backend/omoi_os/workers/monitoring_worker.py)

Standalone script that runs all monitoring loops:

- `heartbeat_monitoring_loop()`
- `diagnostic_monitoring_loop()`
- `anomaly_monitoring_loop()`
- `blocking_detection_loop()`
- `approval_timeout_loop()`
- `IntelligentMonitoringLoop`

### 3. Update Existing Docker Compose (backend/docker-compose.yml)

The existing `backend/docker-compose.yml` already has watch support configured. We just need to add:

**Changes to api service** - add env vars to disable background loops:

```yaml
environment:
  # ... existing vars ...
  - ORCHESTRATOR_ENABLED=false
  - MONITORING_ENABLED=false  
  - MCP_ENABLED=false
  - DAYTONA_SANDBOX_EXECUTION=true
  - DAYTONA_API_KEY=${DAYTONA_API_KEY:-}
```

**New orchestrator service:**

```yaml
orchestrator:
  build:
    context: .
    dockerfile: Dockerfile.worker
  container_name: omoi_os_orchestrator
  environment:
    - DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/app_db
    - REDIS_URL=redis://redis:6379
    - PYTHONUNBUFFERED=1
    - DAYTONA_SANDBOX_EXECUTION=true
    - DAYTONA_API_KEY=${DAYTONA_API_KEY:-}
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
  command: python -m omoi_os.workers.orchestrator_worker
  develop:
    watch:
      - action: restart
        path: ./omoi_os/workers
      - action: restart
        path: ./omoi_os/services/daytona_spawner.py
  restart: unless-stopped
```

**New monitoring service:**

```yaml
monitoring:
  build:
    context: .
    dockerfile: Dockerfile.worker
  container_name: omoi_os_monitoring
  environment:
    - DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/app_db
    - REDIS_URL=redis://redis:6379
    - PYTHONUNBUFFERED=1
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
  command: python -m omoi_os.workers.monitoring_worker
  develop:
    watch:
      - action: restart
        path: ./omoi_os/workers
      - action: restart
        path: ./omoi_os/services/intelligent_guardian.py
  restart: unless-stopped
```

**Watch is already configured** in the existing file with `action: restart` for source changes.

### 4. Justfile Commands

**File:** [backend/Justfile](backend/Justfile) - Add new development commands:

```just
# ============================================================================
# Docker Compose Watch (Hot-Reload Development)
# ============================================================================

# Start all services with hot-reload (recommended for development)
[group('docker')]
watch:
    @echo "🚀 Starting all services with hot-reload..."
    @echo "   API: http://localhost:18000"
    @echo "   Press Ctrl+C to stop"
    docker compose watch

# Start only API + infrastructure (no background workers)
[group('docker')]
watch-api:
    @echo "🚀 Starting API with hot-reload (no workers)..."
    docker compose watch api postgres redis

# Start orchestrator worker only
[group('docker')]
watch-orchestrator:
    @echo "🚀 Starting orchestrator worker..."
    docker compose watch orchestrator postgres redis

# Start monitoring worker only  
[group('docker')]
watch-monitoring:
    @echo "🚀 Starting monitoring worker..."
    docker compose watch monitoring postgres redis

# ============================================================================
# Local Development (No Docker)
# ============================================================================

# Quick local API - all background loops disabled
[group('services')]
api-light port=api_port:
    @echo "🚀 Starting lightweight API (no background loops)..."
    MONITORING_ENABLED=false ORCHESTRATOR_ENABLED=false MCP_ENABLED=false \
    DAYTONA_SANDBOX_EXECUTION=true \
    uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port {{port}} --reload

# Start orchestrator as separate process (local, no Docker)
[group('services')]
orchestrator:
    @echo "🚀 Starting orchestrator worker..."
    uv run python -m omoi_os.workers.orchestrator_worker

# Start monitoring as separate process (local, no Docker)
[group('services')]
monitoring:
    @echo "🚀 Starting monitoring worker..."
    uv run python -m omoi_os.workers.monitoring_worker
```

**File:** [Justfile](Justfile) (root) - Add root-level wrappers:

```just
# ============================================================================
# Docker Compose Watch (Hot-Reload Development)
# ============================================================================

# Start all backend services with hot-reload
[group('docker')]
watch:
    cd {{backend_dir}} && docker compose watch

# Start only API + infrastructure (no background workers)
[group('docker')]
watch-api:
    cd {{backend_dir}} && docker compose watch api postgres redis

# Start orchestrator worker only
[group('docker')]
watch-orchestrator:
    cd {{backend_dir}} && docker compose watch orchestrator postgres redis

# Start monitoring worker only
[group('docker')]
watch-monitoring:
    cd {{backend_dir}} && docker compose watch monitoring postgres redis

# ============================================================================
# Separate Process Development (No Docker)
# ============================================================================

# Quick local API - all background loops disabled
[group('services')]
api-light port=api_port:
    cd {{backend_dir}} && MONITORING_ENABLED=false ORCHESTRATOR_ENABLED=false MCP_ENABLED=false \
    DAYTONA_SANDBOX_EXECUTION=true \
    uv run --active uvicorn omoi_os.api.main:app --host 0.0.0.0 --port {{port}} --reload

# Start orchestrator as separate process
[group('services')]
orchestrator:
    cd {{backend_dir}} && uv run --active python -m omoi_os.workers.orchestrator_worker

# Start monitoring as separate process
[group('services')]
monitoring:
    cd {{backend_dir}} && uv run --active python -m omoi_os.workers.monitoring_worker

# ============================================================================
# Full Stack Development
# ============================================================================

# Start everything: backend (docker watch) + frontend
[group('services')]
dev-watch:
    #!/usr/bin/env bash
    set -e
    echo "🚀 Starting full stack with hot-reload..."
    echo ""
    echo "Backend API: http://localhost:{{api_port}}"
    echo "Frontend: http://localhost:{{frontend_port}}"
    echo ""
    
    # Start backend in background
    cd {{backend_dir}} && docker compose watch &
    BACKEND_PID=$!
    
    # Wait for API to be ready
    echo "Waiting for backend..."
    sleep 5
    
    # Start frontend in foreground
    echo "Starting frontend..."
    cd {{frontend_dir}} && npm run dev -- -p {{frontend_port}}
    
    # Cleanup on exit
    kill $BACKEND_PID 2>/dev/null || true
```

## Key Changes to Existing Code

### [backend/omoi_os/api/main.py](backend/omoi_os/api/main.py)

- Keep the disable flags working (already done)
- Orchestrator/monitoring loops can be imported by standalone workers

### [backend/omoi_os/workers/__init__.py](backend/omoi_os/workers/__init__.py)

- Create workers package if it doesn't exist

## Development Workflow

**Start everything with hot-reload (recommended):**

```bash
cd backend
docker compose watch
```

This automatically:

- Syncs file changes to containers
- Restarts workers when code changes
- Uses uvicorn's --reload for the API (instant reload)

**Start everything without watch:**

```bash
cd backend
docker compose up
```

**Start just the API (for quick testing):**

```bash
cd backend
docker compose up api redis postgres
```

**Start with watch, only specific services:**

```bash
cd backend
docker compose watch api orchestrator
```

**Or without Docker (current approach):**

```bash
MONITORING_ENABLED=false ORCHESTRATOR_ENABLED=false MCP_ENABLED=false \
  uv run uvicorn omoi_os.api.main:app --reload
```

## Benefits

- API server starts instantly (no blocking background tasks)
- Each worker can be scaled independently
- Workers can crash/restart without affecting the API
- Clear separation of concerns
- Easy to add more workers later
- Hot-reload on file save with `docker compose watch`
- No manual restart needed during development