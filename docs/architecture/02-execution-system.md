# Part 2: The Execution System

> Extracted from [ARCHITECTURE.md](../../ARCHITECTURE.md) — see hub doc for full system overview.

## Purpose

Execute tasks in isolated sandboxes with full audit trail.

## Location

```
backend/omoi_os/
├── workers/
│   ├── orchestrator_worker.py      # Main dispatch loop
│   ├── claude_sandbox_worker.py    # In-sandbox execution
│   └── continuous_sandbox_worker.py # Iteration until complete
├── services/
│   ├── daytona_spawner.py          # Sandbox lifecycle
│   ├── task_queue_service.py       # Priority-based assignment
│   └── task_context_builder.py     # Context assembly
```

## Execution Flow

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        OrchestratorWorker                                  │
│                                                                            │
│  1. Poll TaskQueueService for next task                                    │
│  2. Analyze task requirements (LLM: execution_mode, git_requirements)      │
│  3. Check concurrency limits (MAX_CONCURRENT_TASKS_PER_PROJECT=5)          │
│  4. Spawn Daytona sandbox                                                  │
└──────────────────────────────────┬────────────────────────────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                         DaytonaSpawner                                     │
│                                                                            │
│  1. Validate ownership (prevent parallel conflicts)                        │
│  2. Create GitHub branch BEFORE sandbox creation                           │
│  3. Create Daytona sandbox with environment                                │
│  4. Upload Claude skills to sandbox                                        │
│  5. Clone repo, configure git credentials                                  │
│  6. Start worker script                                                    │
└──────────────────────────────────┬────────────────────────────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                       ClaudeSandboxWorker                                  │
│                                                                            │
│  Three execution modes:                                                    │
│  - exploration: Read-only analysis, stops early                            │
│  - implementation: Full file access, runs to completion                    │
│  - validation: Test execution, spawns fix tasks                            │
│                                                                            │
│  Components:                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐   │
│  │  EventReporter  │  │  MessagePoller  │  │   FileChangeTracker     │   │
│  │  (→ backend)    │  │  (← Guardian)   │  │   (unified diffs)       │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘   │
│                                                                            │
│  PostToolUse hooks track: tool calls, subagents, skills                   │
└──────────────────────────────────┬────────────────────────────────────────┘
                                   │
                                   │ "TASK_COMPLETE" signal
                                   ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                      Task Completion                                       │
│                                                                            │
│  1. PhaseManager.check_and_advance() - phase transitions                   │
│  2. SynthesisService - merge parallel results at joins                     │
│  3. ValidationOrchestrator - spawn validator if under_review               │
└───────────────────────────────────────────────────────────────────────────┘
```

## TaskContextBuilder Output

```python
FullTaskContext(
    # Task info
    task_id, task_type, task_description, task_priority, phase_id,

    # Ticket info
    ticket_id, ticket_title, ticket_description, ticket_context,

    # Spec info (if spec-driven)
    spec_id, spec_title, requirements[], design,

    # Current work
    current_spec_task, spec_tasks[],

    # Revision context (if failed validation)
    revision_feedback, revision_recommendations, validation_iteration,

    # Parallel merge results
    synthesis_context  # Merged results from predecessor JOIN
)
```

---

## Sandbox System (Deep Dive)

> **Implementation Status**: Backend 100% Complete | Frontend ~40%
>
> For design documentation, see `docs/design/sandbox-agents/` (21 design documents).

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SANDBOX EXECUTION FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  OrchestratorWorker                                                              │
│       │                                                                          │
│       ▼                                                                          │
│  DaytonaSpawnerService.spawn_for_task()                                          │
│       ├─ Create GitHub branch (BEFORE sandbox)                                   │
│       ├─ Generate credentials (JWT, OAuth tokens)                                │
│       ├─ Build environment variables                                             │
│       └─ Create Daytona sandbox                                                  │
│            │                                                                     │
│            ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐                │
│  │  ClaudeSandboxWorker (in Daytona)                           │                │
│  │       ├─ Poll for messages (MessagePoller)                  │                │
│  │       ├─ Execute task via Claude Agent SDK                  │                │
│  │       ├─ Report events via HTTP POST (EventReporter)        │                │
│  │       └─ Track file changes (FileChangeTracker)             │                │
│  └─────────────────────────────────────────────────────────────┘                │
│            │                                                                     │
│            ▼                                                                     │
│  Backend API (/api/v1/sandboxes/{id}/events)                                     │
│       ├─ Persist to sandbox_events table                                         │
│       ├─ Sync spec phase outputs                                                 │
│       ├─ Update task status                                                      │
│       └─ Publish to EventBus → Guardian, Frontend, IdleSandboxMonitor            │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Implementation Files

#### Workers (In-Sandbox Execution)

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `backend/omoi_os/workers/claude_sandbox_worker.py` | ~1362 | Main Claude Agent SDK worker with continuous iteration, spec validation, session resumption | Complete |
| `backend/omoi_os/workers/continuous_sandbox_worker.py` | ~982 | Iterative execution until completion; validates git status, runs tests, creates PRs | Complete |
| `backend/omoi_os/workers/sandbox_agent_worker.py` | ~548 | Long-running agent; polls for messages, reports events via HTTP | Complete |
| `backend/omoi_os/sandbox_worker.py` | ~461 | Legacy entrypoint for OpenHands SDK integration | Complete |

#### Services (Backend Orchestration)

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `backend/omoi_os/services/daytona_spawner.py` | ~1147 | Sandbox lifecycle, credentials, GitHub branch creation, skill enforcement | Complete |
| `backend/omoi_os/services/idle_sandbox_monitor.py` | ~827 | Detects idle/stuck sandboxes, extracts transcripts, terminates gracefully | Complete |
| `backend/omoi_os/services/sandbox_git_operations.py` | ~623 | Git operations inside sandboxes for DAG merge executor | Complete |

#### Workspace Adapters (Daytona Integration)

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `backend/omoi_os/workspace/daytona.py` | ~873 | Core Daytona workspace: command execution, file operations, git operations | Complete |
| `backend/omoi_os/workspace/daytona_sdk.py` | ~329 | SDK-compatible adapter for OpenHands Conversation class | Complete |
| `backend/omoi_os/workspace/daytona_executor.py` | ~182 | Routes SDK tool commands to Daytona instead of local | Complete |

#### API & Models

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `backend/omoi_os/api/routes/sandbox.py` | ~1336 | Event endpoints, message queue, spec phase sync | Complete |
| `backend/omoi_os/models/sandbox_event.py` | ~61 | Database model for sandbox events | Complete |

### Sandbox Lifecycle State Machine

```
┌──────────┐     spawn()      ┌──────────┐    agent starts   ┌──────────┐
│ PENDING  │ ───────────────► │ CREATING │ ────────────────► │ RUNNING  │
└──────────┘                  └──────────┘                   └──────────┘
     │                              │                              │
     │                              │ creation fails               │
     │                              ▼                              │
     │                        ┌──────────┐                        │
     │                        │  FAILED  │ ◄──────────────────────┤
     │                        └──────────┘   agent crashes/       │
     │                              ▲        timeout              │
     │                              │                              ▼
     │                              │                        ┌──────────┐
     │                              │                        │COMPLETING│
     │                              │                        └──────────┘
     │                              │                              │
     │                              │                              ▼
     │                              │                        ┌──────────┐
     └──────────────────────────────┴───────────────────────►│COMPLETED │
            manual cancel                                     └──────────┘
```

### Event Types

| Category | Events | Description |
|----------|--------|-------------|
| **Agent** | `agent.started`, `agent.thinking`, `agent.message`, `agent.completed`, `agent.error` | Agent lifecycle events |
| **Tools** | `agent.tool_use`, `agent.tool_completed`, `agent.user_tool_result` | Tool invocations and results |
| **Files** | `agent.file_edited`, `file.created`, `file.modified`, `file.deleted` | File change tracking with unified diffs |
| **Commands** | `command.started`, `command.output`, `command.completed` | Shell command execution |
| **Health** | `sandbox.heartbeat`, `sandbox.metrics` | Health checks (every 30s), cost/tokens tracking |

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/sandboxes/health` | GET | Health check |
| `/api/v1/sandboxes/{id}/events` | POST | Worker reports events |
| `/api/v1/sandboxes/{id}/events` | GET | Query persisted events |
| `/api/v1/sandboxes/{id}/trajectory` | GET | Trajectory with heartbeat aggregation |
| `/api/v1/sandboxes/{id}/messages` | POST | Queue message for worker (Guardian interventions) |
| `/api/v1/sandboxes/{id}/messages` | GET | Worker polls for messages |

### Environment Variables

```bash
# Daytona Configuration
DAYTONA_API_KEY=your_key
DAYTONA_SANDBOX_EXECUTION=true
SANDBOX_MEMORY_GB=4          # Memory allocation (default: 4)
SANDBOX_CPU=2                # CPU cores (default: 2)
SANDBOX_DISK_GB=8            # Disk space (default: 8)
SANDBOX_SNAPSHOT=ai-agent-dev-light  # Snapshot name

# Worker Configuration
CALLBACK_URL=https://api.omoios.dev/api/v1/sandboxes/{sandbox_id}/events
TASK_DESCRIPTION=task description
TASK_DATA_BASE64=base64_encoded_task_context

# Orchestrator
ORCHESTRATOR_ENABLED=true
MAX_CONCURRENT_TASKS_PER_PROJECT=5
```

### Design Documentation Reference

All sandbox design documents are in `docs/design/sandbox-agents/`:

| Document | Purpose |
|----------|---------|
| `01_architecture.md` | Core system architecture with database schema, WebSocket patterns |
| `02_gap_analysis.md` | What exists vs what's needed (verified 85% already built) |
| `IMPLEMENTATION_COMPLETE_STATUS.md` | Current status: Backend 100%, Frontend ~40% |
| `SANDBOX_AGENT_STATUS.md` | Working features, test results, configuration |
| `06_implementation_checklist.md` | Test-driven implementation with copy-pasteable code |
| `09_rich_activity_feed_architecture.md` | Future: tool events, file diffs, streaming |

---

## Worker System (Background Processes)

> Understanding these is critical for debugging and operational monitoring.

### Worker Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           WORKER SYSTEM OVERVIEW                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                    ORCHESTRATOR WORKER (orchestrator_worker.py)          │    │
│  │    Main process - task dispatch, sandbox spawning, cleanup               │    │
│  │                                                                          │    │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │    │
│  │  │orchestrator_loop│  │stale_task_loop │  │idle_sandbox_loop│          │    │
│  │  │  Poll tasks     │  │  Clean orphans │  │  Term idle      │          │    │
│  │  │  Spawn sandbox  │  │  (15s interval)│  │  (30s interval) │          │    │
│  │  │  (5s poll/event)│  └─────────────────┘  └─────────────────┘          │    │
│  │  └────────┬────────┘                                                    │    │
│  │           │ calls                                                       │    │
│  │           ▼                                                             │    │
│  │  ┌─────────────────────┐     ┌─────────────────────┐                   │    │
│  │  │  DaytonaSpawner     │────►│  IdleSandboxMonitor │                   │    │
│  │  │  (sandbox lifecycle)│     │  (idle detection)   │                   │    │
│  │  └─────────────────────┘     └─────────────────────┘                   │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                    MONITORING WORKER (monitoring_worker.py)              │    │
│  │    Background loops for health, diagnostics, anomalies                   │    │
│  │                                                                          │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐│    │
│  │  │heartbeat_loop│  │diagnostic    │  │anomaly_loop  │  │blocking_loop ││    │
│  │  │ Agent health │  │ Stuck flows  │  │ Agent scores │  │ Stuck ticket ││    │
│  │  │ (10s)        │  │ (60s)        │  │ (60s)        │  │ (5 min)      ││    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘│    │
│  │                                                                          │    │
│  │  ┌──────────────┐  ┌─────────────────────────────────────────────────┐ │    │
│  │  │approval_loop │  │         MonitoringLoop (nested)                 │ │    │
│  │  │ Timeouts     │  │  ┌────────────┐ ┌────────────┐ ┌────────────┐   │ │    │
│  │  │ (10s)        │  │  │ Guardian   │ │ Conductor  │ │ HealthChk  │   │ │    │
│  │  └──────────────┘  │  │ (60s)      │ │ (5 min)    │ │ (30s)      │   │ │    │
│  │                    │  └────────────┘ └────────────┘ └────────────┘   │ │    │
│  │                    └─────────────────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │              IN-SANDBOX WORKERS (run inside Daytona sandboxes)           │    │
│  │                                                                          │    │
│  │  ┌─────────────────────────┐  ┌─────────────────────────┐              │    │
│  │  │  ClaudeSandboxWorker    │  │  ContinuousSandboxWorker │              │    │
│  │  │  - EventReporter        │  │  - Extends base worker   │              │    │
│  │  │  - MessagePoller        │  │  - Iterates until done   │              │    │
│  │  │  - FileChangeTracker    │  │  - Git validation        │              │    │
│  │  │  - heartbeat (30s)      │  │  - Auto-retry logic      │              │    │
│  │  └─────────────────────────┘  └─────────────────────────┘              │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Worker Files Reference

| Worker | File | Lines | Purpose |
|--------|------|-------|---------|
| **Orchestrator** | `workers/orchestrator_worker.py` | ~1250 | Task dispatch, sandbox spawning, stale cleanup |
| **Monitoring** | `workers/monitoring_worker.py` | ~560 | Health, diagnostics, anomalies, blocking |
| **Claude Sandbox** | `workers/claude_sandbox_worker.py` | ~1362 | In-sandbox task execution |
| **Continuous Sandbox** | `workers/continuous_sandbox_worker.py` | ~982 | Iterative execution until complete |
| **Sandbox Agent** | `workers/sandbox_agent_worker.py` | ~548 | Long-running agent with polling |

### Background Loops Summary

| Loop | Worker | Interval | Purpose | Key Services Called |
|------|--------|----------|---------|---------------------|
| `orchestrator_loop` | Orchestrator | 5s / event | Poll tasks, spawn sandboxes | DaytonaSpawner, TaskQueueService |
| `stale_task_cleanup_loop` | Orchestrator | 15s | Clean orphaned tasks | TaskQueueService |
| `idle_sandbox_check_loop` | Orchestrator | 30s | Terminate idle sandboxes | IdleSandboxMonitor, DaytonaSpawner |
| `heartbeat_monitoring_loop` | Monitoring | 10s | Check agent heartbeats | HeartbeatProtocolService, RestartOrchestrator |
| `diagnostic_monitoring_loop` | Monitoring | 60s | Detect stuck workflows | DiagnosticService |
| `anomaly_monitoring_loop` | Monitoring | 60s | Detect agent anomalies | MonitorService, DiagnosticService |
| `blocking_detection_loop` | Monitoring | 5 min | Detect blocked tickets | TicketWorkflowOrchestrator |
| `approval_timeout_loop` | Monitoring | 10s | Check approval timeouts | ApprovalService |
| `_guardian_loop` | MonitoringLoop | 60s | Per-agent trajectory analysis | IntelligentGuardian |
| `_conductor_loop` | MonitoringLoop | 5 min | System coherence analysis | ConductorService |
| `_health_check_loop` | MonitoringLoop | 30s | Health check alerts | — |
| `heartbeat_loop` | ClaudeSandboxWorker | 30s | Report alive to backend | EventReporter |

### Worker-Service Interaction Map

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          SERVICE INTERACTION FLOW                             │
└──────────────────────────────────────────────────────────────────────────────┘

 OrchestratorWorker                          MonitoringWorker
       │                                            │
       │ ─────► DaytonaSpawner                      │ ─────► HeartbeatProtocolService
       │           │                                │           │
       │           │ creates                        │           │ missed heartbeats
       │           ▼                                │           ▼
       │        Sandbox ────────────────────────────┼────► RestartOrchestrator
       │           │                                │
       │           │ events                         │ ─────► DiagnosticService
       │           ▼                                │           │
       │     Backend API ◄──────────────────────────┼───────────┘
       │           │                                │
       │           │ events                         │ ─────► MonitorService
       │           ▼                                │           │
       │      EventBus ─────────────────────────────┼───────────┘
       │           │                                │
       │           │                                │
       ▼           ▼                                ▼
 IdleSandboxMonitor    IntelligentGuardian    ConductorService
       │                      │                     │
       │ terminates           │ analyzes            │ coherence
       ▼                      ▼                     ▼
    Sandbox              MessagePoller         Recommendations
   (cleanup)           (interventions)          (duplicates)
```

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ORCHESTRATOR_ENABLED` | `true` | Enable/disable orchestrator loop |
| `MAX_CONCURRENT_TASKS_PER_PROJECT` | `5` | Concurrency limit per project |
| `STALE_TASK_CLEANUP_ENABLED` | `true` | Enable stale task cleanup |
| `STALE_TASK_THRESHOLD_MINUTES` | `3` | Minutes before task considered stale |
| `IDLE_DETECTION_ENABLED` | `true` | Enable idle sandbox detection |
| `IDLE_THRESHOLD_MINUTES` | `10` | Minutes of inactivity before termination |
| `IDLE_CHECK_INTERVAL_SECONDS` | `30` | Interval for idle checks |

### Running Workers

```bash
# Start orchestrator worker (production)
python -m omoi_os.workers.orchestrator_worker

# Start monitoring worker (production)
python -m omoi_os.workers.monitoring_worker

# Both are typically started by the main API process in development
uvicorn omoi_os.api.main:app --reload
```

### Test Scripts

| Script | Purpose | Command |
|--------|---------|---------|
| `test_api_sandbox_spawn.py` | Full E2E API test | `uv run python scripts/test_api_sandbox_spawn.py` |
| `test_spawner_e2e.py` | DaytonaSpawner E2E | `uv run python scripts/test_spawner_e2e.py` |
| `query_sandbox_events.py` | Query events | `uv run python scripts/query_sandbox_events.py <id>` |
| `list_recent_sandboxes.py` | List sandboxes | `uv run python scripts/list_recent_sandboxes.py` |
| `cleanup_sandboxes.py` | Cleanup | `python scripts/cleanup_sandboxes.py --full-cleanup` |
