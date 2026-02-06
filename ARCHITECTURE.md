# OmoiOS Architecture: Dynamic Swarm Orchestration

> **This is the critical reference document for understanding OmoiOS.**
> Read this before diving into any specific component.

## Executive Summary

OmoiOS is an autonomous engineering platform that orchestrates multiple AI agents through a **spec-driven, discovery-enabled, self-adjusting workflow**. The system handles three core capabilities:

| Capability | System | Purpose |
|------------|--------|---------|
| **Plans** | Spec-Sandbox State Machine | Convert feature ideas into structured requirements, designs, and atomic tasks |
| **Discoveries** | DiscoveryService + Analyzer | Detect new work during execution and spawn adaptive branch tasks |
| **Readjustments** | MonitoringLoop + Guardian + Conductor | Monitor agent trajectories and intervene when goals drift |

---

## Architecture Overview

```txt
                                 ┌─────────────────────────────────────────┐
                                 │              User / Frontend            │
                                 │  (Specs, Tickets, Tasks, Monitoring)    │
                                 └────────────────────┬────────────────────┘
                                                      │
                                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                       API Layer                                          │
│                         FastAPI Routes + WebSocket Events                                │
└───────────────┬─────────────────────────────┬───────────────────────────┬───────────────┘
                │                             │                           │
                ▼                             ▼                           ▼
┌───────────────────────────┐   ┌─────────────────────────────┐   ┌─────────────────────────┐
│     PLANNING SYSTEM       │   │    EXECUTION SYSTEM         │   │   READJUSTMENT SYSTEM   │
│  ┌─────────────────────┐  │   │  ┌─────────────────────┐    │   │  ┌─────────────────────┐│
│  │  Spec-Sandbox       │  │   │  │ OrchestratorWorker  │    │   │  │   MonitoringLoop    ││
│  │  State Machine      │  │   │  │ (task dispatch)     │    │   │  │  ┌───────────────┐  ││
│  │                     │  │   │  └──────────┬──────────┘    │   │  │  │   Guardian    │  ││
│  │ EXPLORE → PRD →     │  │   │             │               │   │  │  │  (trajectory) │  ││
│  │ REQUIREMENTS →      │  │   │             ▼               │   │  │  └───────────────┘  ││
│  │ DESIGN → TASKS →    │  │   │  ┌─────────────────────┐    │   │  │  ┌───────────────┐  ││
│  │ SYNC               │  │   │  │  DaytonaSpawner     │    │   │  │  │   Conductor   │  ││
│  │                     │  │   │  │  (sandbox creation) │    │   │  │  │  (coherence)  │  ││
│  └─────────────────────┘  │   │  └──────────┬──────────┘    │   │  │  └───────────────┘  ││
│           │               │   │             │               │   │  └─────────────────────┘│
│           ▼               │   │             ▼               │   │            │            │
│  ┌─────────────────────┐  │   │  ┌─────────────────────┐    │   │            ▼            │
│  │  Phase Evaluators   │  │   │  │ ClaudeSandboxWorker │    │   │  ┌─────────────────────┐│
│  │  (quality gates)    │  │   │  │ + EventReporter     │    │   │  │  Steering           ││
│  └─────────────────────┘  │   │  │ + MessagePoller     │    │   │  │  Interventions      ││
│           │               │   │  │ + FileChangeTracker │    │   │  └─────────────────────┘│
│           ▼               │   │  └──────────┬──────────┘    │   └─────────────────────────┘
│  ┌─────────────────────┐  │   │             │               │
│  │  HTTPReporter       │  │   │             │ (discoveries) │
│  │  (event streaming)  │  │   │             ▼               │
│  └─────────────────────┘  │   │  ┌─────────────────────┐    │
└───────────────────────────┘   │  │  DiscoveryService   │    │
                                │  │  (adaptive branch)  │    │
                                │  └─────────────────────┘    │
                                └─────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   DATA LAYER                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │  MemoryService  │  │  ContextService │  │ SynthesisService│  │  DAG Merge      │     │
│  │  (pattern RAG)  │  │  (phase context)│  │ (parallel merge)│  │  System         │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│                                                                                          │
│                          PostgreSQL + pgvector + Redis                                   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: The Planning System

### Purpose

Convert a high-level feature idea into structured, executable work units.

### Location

```md
subsystems/spec-sandbox/src/spec_sandbox/
├── worker/state_machine.py      # Main orchestrator
├── prompts/phases.py            # Phase-specific prompts
├── evaluators/phases.py         # Quality gate evaluators
├── reporters/http.py            # Event streaming to backend
└── sync/service.py              # Sync artifacts to API
```

### Phase Flow

```md
EXPLORE → PRD → REQUIREMENTS → DESIGN → TASKS → SYNC → COMPLETE
   │        │         │           │        │       │
   ▼        ▼         ▼           ▼        ▼       ▼
 Codebase  Product   EARS      Architecture  TKT/TSK  Validation
 Analysis  Reqs Doc  Format    + API Specs   IDs      + Sync
```

### Phase Details

| Phase | Purpose | Output |
|-------|---------|--------|
| **EXPLORE** | Analyze codebase + gather discovery questions | `codebase_summary`, `tech_stack`, `discovery_questions`, `feature_summary` |
| **PRD** | Product Requirements Document | `goals`, `user_stories`, `scope`, `risks`, `success_metrics` |
| **REQUIREMENTS** | EARS-format formal requirements | `requirements[]` with `WHEN [trigger], THE SYSTEM SHALL [action]` |
| **DESIGN** | Architecture, API specs, data models | `components[]`, `data_models[]`, `api_endpoints[]`, `architecture_diagram` |
| **TASKS** | Tickets (TKT-NNN) and Tasks (TSK-NNN) | `tickets[]`, `tasks[]` with dependencies and estimates |
| **SYNC** | Validate traceability and sync to API | `coverage_matrix`, `traceability_stats`, `ready_for_execution` |

### Phase Evaluators (Quality Gates)

Each phase has an evaluator that scores the output (0.0 - 1.0). If score < threshold (0.7), the phase retries with feedback.

**Example: RequirementsEvaluator scoring:**

- `structure`: 20% - Required fields present
- `normative_language`: 20% - Uses SHALL/SHOULD/MAY
- `ears_format`: 15% - WHEN/SHALL patterns
- `acceptance_criteria`: 20% - 2+ criteria per requirement
- `id_format`: 5% - REQ-FEATURE-CATEGORY-NNN format

### Incremental Work Pattern (Critical)

All phases follow incremental writing to prevent data loss:

```python
# WRONG - One massive write at the end
[... do all analysis ...]
Write(entire_file)  # If this fails, everything is lost!

# CORRECT - Incremental writes
[... analyze first area ...]
Write(file, first_5_requirements)
[... analyze second area ...]
Edit(file, append next_5_requirements)  # Progress preserved
```

---

## Part 2: The Execution System

### Purpose

Execute tasks in isolated sandboxes with full audit trail.

### Location

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

### Execution Flow

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

### TaskContextBuilder Output

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

## Part 2A: Sandbox System (Deep Dive)

> **Implementation Status**: Backend 100% Complete | Frontend ~40%
>
> This section provides detailed file locations and implementation status for the sandbox execution system.
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
| `backend/omoi_os/workers/claude_sandbox_worker.py` | ~1362 | Main Claude Agent SDK worker with continuous iteration, spec validation, session resumption | ✅ Complete |
| `backend/omoi_os/workers/continuous_sandbox_worker.py` | ~982 | Iterative execution until completion; validates git status, runs tests, creates PRs | ✅ Complete |
| `backend/omoi_os/workers/sandbox_agent_worker.py` | ~548 | Long-running agent; polls for messages, reports events via HTTP | ✅ Complete |
| `backend/omoi_os/sandbox_worker.py` | ~461 | Legacy entrypoint for OpenHands SDK integration | ✅ Complete |

#### Services (Backend Orchestration)

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `backend/omoi_os/services/daytona_spawner.py` | ~1147 | Sandbox lifecycle, credentials, GitHub branch creation, skill enforcement | ✅ Complete |
| `backend/omoi_os/services/idle_sandbox_monitor.py` | ~827 | Detects idle/stuck sandboxes, extracts transcripts, terminates gracefully | ✅ Complete |
| `backend/omoi_os/services/sandbox_git_operations.py` | ~623 | Git operations inside sandboxes for DAG merge executor | ✅ Complete |

#### Workspace Adapters (Daytona Integration)

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `backend/omoi_os/workspace/daytona.py` | ~873 | Core Daytona workspace: command execution, file operations, git operations | ✅ Complete |
| `backend/omoi_os/workspace/daytona_sdk.py` | ~329 | SDK-compatible adapter for OpenHands Conversation class | ✅ Complete |
| `backend/omoi_os/workspace/daytona_executor.py` | ~182 | Routes SDK tool commands to Daytona instead of local | ✅ Complete |

#### API & Models

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `backend/omoi_os/api/routes/sandbox.py` | ~1336 | Event endpoints, message queue, spec phase sync | ✅ Complete |
| `backend/omoi_os/models/sandbox_event.py` | ~61 | Database model for sandbox events | ✅ Complete |

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

### Test Scripts

| Script | Purpose | Command |
|--------|---------|---------|
| `test_api_sandbox_spawn.py` | Full E2E API test | `uv run python scripts/test_api_sandbox_spawn.py` |
| `test_spawner_e2e.py` | DaytonaSpawner E2E | `uv run python scripts/test_spawner_e2e.py` |
| `query_sandbox_events.py` | Query events | `uv run python scripts/query_sandbox_events.py <id>` |
| `list_recent_sandboxes.py` | List sandboxes | `uv run python scripts/list_recent_sandboxes.py` |
| `cleanup_sandboxes.py` | Cleanup | `python scripts/cleanup_sandboxes.py --full-cleanup` |

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

## Part 3: The Discovery System

### Purpose

Enable adaptive workflow branching when agents discover new requirements during execution.

### Location

```
backend/omoi_os/services/
├── discovery.py           # Core discovery recording + branching
├── discovery_analyzer.py  # LLM-powered pattern analysis
```

### Hephaestus Pattern

**Key Insight**: Discovery-based branching **bypasses** `PhaseModel.allowed_transitions`. A Phase 3 validation agent can spawn Phase 1 investigation tasks.

```
Normal Transition:      PHASE_IMPLEMENTATION → PHASE_TESTING → PHASE_DEPLOYMENT

Discovery Branch:       PHASE_TESTING → (discovery) → PHASE_IMPLEMENTATION
                        ↑                              ↓
                        └──────────────────────────────┘
                              (can spawn ANY phase)
```

### Discovery Types

| Type | Trigger | Priority Boost |
|------|---------|----------------|
| `BUG_FOUND` | Agent finds bug during validation | Yes |
| `BLOCKER_IDENTIFIED` | Blocking dependency discovered | Yes |
| `MISSING_DEPENDENCY` | Required component missing | Yes |
| `OPTIMIZATION_OPPORTUNITY` | Performance improvement found | No |
| `DIAGNOSTIC_NO_RESULT` | Stuck workflow recovery | Yes |

### Discovery Flow

```python
# Agent discovers a bug during validation
discovery, spawned_task = discovery_service.record_discovery_and_branch(
    session=session,
    source_task_id="task-123",
    discovery_type=DiscoveryType.BUG_FOUND,
    description="Authentication fails for expired tokens",
    spawn_phase_id="PHASE_IMPLEMENTATION",  # Goes BACK to implementation
    spawn_description="Fix token expiration handling",
    priority_boost=True,  # MEDIUM → HIGH
)
# New task created and linked to discovery for traceability
```

### DiscoveryAnalyzerService

LLM-powered analysis of discovery patterns:

| Method | Purpose |
|--------|---------|
| `analyze_patterns()` | Find recurring patterns across discoveries |
| `predict_blockers()` | Predict likely blockers based on history |
| `recommend_agent()` | Suggest best agent type for a discovery |
| `summarize_workflow_health()` | Comprehensive health metrics |

**Example Output:**

```python
PatternAnalysisResult(
    patterns=[
        DiscoveryPattern(
            pattern_type="recurring_bug",
            description="Token handling issues",
            severity="high",
            affected_components=["AuthService", "TokenValidator"],
            suggested_action="Add comprehensive token tests",
            confidence=0.85
        )
    ],
    health_score=0.72,
    hotspots=["AuthService"],
    recommendations=["Add token expiration tests before deployment"]
)
```

---

## Part 4: The Readjustment System

### Purpose

Monitor agent trajectories and system coherence, intervening when agents drift from goals.

### Location

```
backend/omoi_os/services/
├── monitoring_loop.py         # Main orchestrator
├── intelligent_guardian.py    # Per-agent trajectory analysis
├── conductor.py               # System-wide coherence
├── validation_orchestrator.py # Validation agent management
```

### MonitoringLoop Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          MonitoringLoop                                  │
│                                                                          │
│  Three background loops:                                                 │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐   │
│  │  Guardian Loop    │  │  Conductor Loop   │  │  Health Check     │   │
│  │  (60s interval)   │  │  (5min interval)  │  │  (30s interval)   │   │
│  │                   │  │                   │  │                   │   │
│  │  Per-agent        │  │  System-wide      │  │  Alerts for       │   │
│  │  trajectory       │  │  coherence        │  │  critical states  │   │
│  │  analysis         │  │  + duplicates     │  │                   │   │
│  └───────────────────┘  └───────────────────┘  └───────────────────┘   │
│                                                                          │
│  Metrics tracked:                                                        │
│  - total_cycles, successful_cycles, failed_cycles                       │
│  - total_interventions                                                   │
│  - success_rate                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### IntelligentGuardian (Per-Agent Analysis)

**Analysis Output:**

```python
TrajectoryAnalysis(
    agent_id="agent-123",
    alignment_score=0.85,      # 0.0 - 1.0
    trajectory_aligned=True,   # On track for goal?
    needs_steering=False,      # Requires intervention?
    steering_type=None,        # "redirect", "refocus", "stop"
    steering_recommendation=None,
    trajectory_summary="Agent progressing on auth implementation",
    current_focus="Adding JWT validation",
    conversation_length=45,
    session_duration=timedelta(minutes=23),
)
```

**Steering Intervention Types:**

| Type | When | Action |
|------|------|--------|
| `redirect` | Agent going wrong direction | Inject message with new direction |
| `refocus` | Agent drifting from scope | Remind of original goal |
| `stop` | Agent causing harm | Terminate execution |

### ConductorService (System Coherence)

**Coherence Score Formula:**

```
coherence = base_alignment - trajectory_penalty - steering_penalty + bonuses

Where:
- base_alignment = average alignment across all agents
- trajectory_penalty = (unaligned_agents / total_agents) * 0.2
- steering_penalty = (agents_needing_steering / total_agents) * 0.1
- bonuses = efficiency_bonus + completion_bonus
```

**System Status Classification:**

| Status | Condition |
|--------|-----------|
| `critical` | coherence < 0.3 |
| `warning` | coherence < 0.5 |
| `inefficient` | coherence < 0.7 |
| `optimal` | coherence >= 0.9 |
| `normal` | otherwise |

**Duplicate Detection:**

```python
# LLM compares same-phase agent pairs
for agent_a, agent_b in pairwise(agents_in_phase):
    prompt = f"Are {agent_a.focus} and {agent_b.focus} duplicates?"
    if llm.is_duplicate(agent_a, agent_b):
        recommendations.append(f"Merge {agent_a.id} and {agent_b.id}")
```

### ValidationOrchestrator

**State Machine:**

```
pending → assigned → in_progress → under_review → validation_in_progress → done
                                        ↓                    ↓
                                   needs_work ←──────────────┘
                                        ↓
                              (after 2+ failures)
                                        ↓
                              DiagnosticService auto-spawn
```

---

## Part 4A: Worker System (Background Processes)

> **This section documents ALL background workers and loops that keep OmoiOS running.**
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
| **Spec State Machine** | `workers/spec_state_machine.py` | ~400 | DEPRECATED - see subsystems/spec-sandbox |

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

---

## Part 5: Memory & Context System

### Purpose

Learn from execution history and provide relevant context to new tasks.

### Location

```
backend/omoi_os/services/
├── memory.py                # Pattern learning + similarity search
├── context_service.py       # Cross-phase context aggregation
├── task_context_builder.py  # Full context assembly
├── synthesis_service.py     # Parallel task result merging
```

### MemoryService

**Memory Types:**

| Type | Examples |
|------|----------|
| `ERROR_FIX` | Bug fixes, error resolutions |
| `DECISION` | Design decisions made |
| `LEARNING` | New knowledge discovered |
| `WARNING` | Gotchas and cautions |
| `CODEBASE_KNOWLEDGE` | Architecture patterns |
| `DISCOVERY` | General discoveries |

**Search Modes:**

```python
# Hybrid search (default) - combines semantic + keyword with RRF
results = memory_service.search_similar(
    session=session,
    task_description="Implement JWT token refresh",
    search_mode="hybrid",  # "semantic", "keyword", or "hybrid"
    semantic_weight=0.6,
    keyword_weight=0.4,
    top_k=5,
    memory_types=["ERROR_FIX", "LEARNING"],  # Optional filter
)

# RRF Score = semantic_weight * (1 / (60 + sem_rank)) + keyword_weight * (1 / (60 + kw_rank))
```

### ContextService

**Aggregated Phase Context:**

```python
{
    "ticket_id": "ticket-123",
    "phase_id": "PHASE_IMPLEMENTATION",
    "tasks": [
        {"task_id": "task-1", "task_type": "backend", "summary": "..."},
    ],
    "decisions": ["Use PostgreSQL for storage", "JWT for auth"],
    "risks": ["Performance under load"],
    "notes": ["Consider rate limiting"],
    "artifacts": ["schema.sql", "api.yaml"],
    "summary": "Auto-generated phase summary"
}
```

### SynthesisService (Parallel Merge)

**Merge Strategies:**

| Strategy | Behavior |
|----------|----------|
| `combine` | Preserves all results from all sources |
| `union` | Later results override earlier for same keys |
| `intersection` | Only common keys across all sources |

**Join Point Flow:**

```
Task A ─────┐
            │
Task B ─────┼───→ SynthesisService ───→ Continuation Task
            │         │
Task C ─────┘         │
                      ▼
                synthesis_context = {
                    "_source_count": 3,
                    "_merge_strategy": "combine",
                    "_source_results": [A_result, B_result, C_result],
                    ...merged_data...
                }
```

---

## Part 6: DAG Merge System

### DAG Purpose

Coordinate parallel work branches and merge them back together.

### DAG Locations

```md
backend/omoi_os/services/
├── dependency_graph.py         # DAG visualization + critical path
├── coordination.py             # SYNC, SPLIT, JOIN, MERGE primitives
├── conflict_scorer.py          # git merge-tree dry-run scoring
├── convergence_merge_service.py # Multi-branch merge orchestration
├── agent_conflict_resolver.py  # LLM-powered conflict resolution
```

### Coordination Primitives

| Primitive | Purpose | Usage |
|-----------|---------|-------|
| `SYNC` | Wait for all predecessors | Before dependent work |
| `SPLIT` | Fork into parallel branches | Start parallel tasks |
| `JOIN` | Merge parallel results | After parallel tasks complete |
| `MERGE` | Git branch merge | Combine code changes |

### Conflict-Aware Merge Ordering

```python
# ConflictScorer uses git merge-tree for dry-run analysis
conflict_count = conflict_scorer.score_merge(
    base_branch="main",
    source_branch="feature-a",
    target_branch="feature-b"
)

# ConvergenceMergeService orders merges by least-conflicts-first
merge_order = convergence_service.compute_optimal_merge_order(
    branches=["feature-a", "feature-b", "feature-c"]
)
# Returns: ["feature-c", "feature-a", "feature-b"] (least conflicts first)
```

### AgentConflictResolver

When automatic merge fails, spawns an LLM agent to resolve:

```python
resolution = await resolver.resolve_conflicts(
    conflict_markers=[
        ConflictMarker(
            file="auth.py",
            line_start=45,
            line_end=52,
            ours="...",
            theirs="...",
            base="..."
        )
    ],
    context="Both branches modified JWT validation logic"
)
```

---

## Testing Requirements (Before Production)

### What Works (Needs Testing)

- [ ] Spec-Sandbox state machine (EXPLORE through SYNC)
- [ ] Phase evaluators and retry logic
- [ ] DaytonaSpawner sandbox creation
- [ ] ClaudeSandboxWorker execution modes
- [ ] TaskContextBuilder context assembly

### What Needs Integration Testing

- [ ] Full spec → tickets → tasks → execution flow
- [ ] Discovery branching during execution
- [ ] MonitoringLoop with real agents
- [ ] Parallel task execution with SynthesisService
- [ ] DAG merge with conflict resolution

### What Needs Load Testing

- [ ] MAX_CONCURRENT_TASKS_PER_PROJECT limits
- [ ] MemoryService hybrid search at scale
- [ ] EventBus throughput under load
- [ ] Guardian analysis with many agents

---

## Quick Reference: Key Files by System

### Planning

| File | Purpose |
|------|---------|
| `subsystems/spec-sandbox/src/spec_sandbox/worker/state_machine.py` | Main spec orchestrator |
| `subsystems/spec-sandbox/src/spec_sandbox/prompts/phases.py` | Phase prompts (1500 lines) |
| `subsystems/spec-sandbox/src/spec_sandbox/evaluators/phases.py` | Quality gates |

### Execution

| File | Purpose |
|------|---------|
| `backend/omoi_os/workers/orchestrator_worker.py` | Main task dispatch (~1150 lines) |
| `backend/omoi_os/services/daytona_spawner.py` | Sandbox lifecycle (~2500 lines) |
| `backend/omoi_os/workers/claude_sandbox_worker.py` | In-sandbox execution (~4300 lines) |

### Discovery

| File | Purpose |
|------|---------|
| `backend/omoi_os/services/discovery.py` | Core discovery + branching (~519 lines) |
| `backend/omoi_os/services/discovery_analyzer.py` | LLM pattern analysis (~515 lines) |

### Readjustment

| File | Purpose |
|------|---------|
| `backend/omoi_os/services/monitoring_loop.py` | Main orchestrator (~669 lines) |
| `backend/omoi_os/services/intelligent_guardian.py` | Per-agent analysis (~1122 lines) |
| `backend/omoi_os/services/conductor.py` | System coherence (~919 lines) |

### Memory & Context

| File | Purpose |
|------|---------|
| `backend/omoi_os/services/memory.py` | Pattern RAG (~868 lines) |
| `backend/omoi_os/services/context_service.py` | Phase context (~255 lines) |
| `backend/omoi_os/services/task_context_builder.py` | Full context assembly (~667 lines) |

---

## Glossary

| Term | Definition |
|------|------------|
| **Spec** | A feature specification that goes through EXPLORE → SYNC phases |
| **Ticket** | A work grouping (TKT-NNN) containing multiple tasks |
| **Task** | An atomic work unit (TSK-NNN) executable by an agent |
| **Discovery** | New work found during execution that spawns branch tasks |
| **Trajectory** | An agent's conversation and tool usage history |
| **Alignment** | How well an agent's trajectory matches its goal |
| **Coherence** | System-wide measure of agent coordination |
| **Synthesis** | Merging results from parallel predecessor tasks |
| **Phase Gate** | Quality evaluation that must pass to proceed |
| **EARS** | "Easy Approach to Requirements Syntax" format |

---

## Part 7: Integration Gaps & Known Issues

> **CRITICAL**: This section documents known integration gaps where features were coded but not properly wired together.
> These must be addressed before production deployment.

### Gap Summary

| Category | Issue | Severity |
|----------|-------|----------|
| **Orphaned Services** | 4 services with getters that are never called | 🔴 Critical |
| **Event System** | 153 event publishes vs 18 subscribes | 🔴 Critical |
| **DAG System** | CoordinationService not initialized in orchestrator | 🔴 Critical |
| **Test Coverage** | 20 integration tests for 100 services | 🟡 High |
| **TODO Items** | 51 TODO/FIXME comments in codebase | 🟡 High |

---

### Gap 1: Orphaned Services (Never Called)

These services have singleton getters that are **NEVER called** from production code:

| Service | Getter | File | Issue |
|---------|--------|------|-------|
| **OwnershipValidation** | `get_ownership_validation_service()` | `ownership_validation.py:543` | Only called in unit tests |
| **Synthesis** | `get_synthesis_service()` | `synthesis_service.py:527` | Only called in unit tests |
| **SpecTaskExecution** | `get_spec_task_execution_service()` | `spec_task_execution.py:854` | Only called in unit tests |
| **ConvergenceMerge** | `get_convergence_merge_service()` | `convergence_merge_service.py:676` | NEVER called anywhere |

**Why This Matters:**

- Features were coded but never integrated
- The DAG merge system (`ConvergenceMergeService`) is completely orphaned
- Parallel task coordination (`SynthesisService`) is partially wired but getter unused

**Fix Required:**

```python
# In orchestrator_worker.py init_services():

# 1. Initialize CoordinationService (creates JOIN events)
from omoi_os.services.coordination import CoordinationService
coordination_service = CoordinationService(db=db, queue=queue, event_bus=event_bus)

# 2. Initialize ConvergenceMergeService (handles git merges)
from omoi_os.services.convergence_merge_service import get_convergence_merge_service
convergence_merge = get_convergence_merge_service(db=db, event_bus=event_bus)

# SynthesisService is already initialized but needs CoordinationService to publish events
```

---

### Gap 2: Event System Gaps

**153 event types published** but only **18 subscriptions** exist.

#### Events Published Into the Void (No Subscribers)

| Event Type | Published In | Subscriber | Status |
|------------|--------------|------------|--------|
| `APPROVAL_CREATED` | approval.py | None | ❌ Lost |
| `APPROVAL_COMPLETED` | approval.py | None | ❌ Lost |
| `BUDGET_EXCEEDED` | budget_enforcer.py | None | ❌ Lost |
| `BUDGET_WARNING` | budget_enforcer.py | None | ❌ Lost |
| `COST_RECORDED` | cost_tracking.py | None | ❌ Lost |
| `MEMORY_PATTERN_STORED` | memory.py | None | ❌ Lost |
| `QUALITY_CHECK_*` | quality_checker.py | None | ❌ Lost |
| `WATCHDOG_*` | watchdog.py | None | ❌ Lost |
| `ALERT_*` | alerting.py | None | ❌ Lost |
| `COLLABORATION_*` | collaboration.py | None | ❌ Lost |
| `GITHUB_*` | github_integration.py | None | ❌ Lost |
| `SUBSCRIPTION_*` | subscription_service.py | None | ❌ Lost |
| `BILLING_*` | billing_service.py | None | ❌ Lost |

#### Events With Subscribers (Working)

| Event Type | Subscriber |
|------------|------------|
| `TASK_CREATED` | orchestrator_worker |
| `TASK_COMPLETED` | synthesis_service, spec_task_execution, phase_manager, phase_progression |
| `TASK_FAILED` | spec_task_execution |
| `TASK_STARTED` | phase_manager, phase_progression |
| `TASK_VALIDATION_FAILED` | orchestrator_worker |
| `TASK_VALIDATION_PASSED` | orchestrator_worker |
| `TICKET_CREATED` | orchestrator_worker |
| `SANDBOX_agent.completed` | orchestrator_worker |
| `SANDBOX_agent.failed` | orchestrator_worker |
| `SANDBOX_agent.error` | orchestrator_worker |
| `coordination.join.created` | synthesis_service |
| `synthesis.completed` | convergence_merge_service |
| `PHASE_TRANSITION` | phase_progression |

**Impact**: Most events are published but never consumed - wasted work and no reactive behavior.

---

### Gap 3: DAG System Not Wired

The DAG system has 4 services that should work together but aren't connected:

```
WHAT EXISTS:
┌─────────────────────────────────────────────────────────────────────────┐
│  DependencyGraphService  │  CoordinationService  │  SynthesisService    │
│  - Graph visualization   │  - SYNC, SPLIT, JOIN  │  - Merge results     │
│  - Critical path calc    │  - Creates events     │  - Listens for joins │
│                          │                       │                      │
│  ConvergenceMergeService │  ConflictScorer       │  AgentConflictResolver│
│  - Git branch merging    │  - Dry-run scoring    │  - LLM resolution    │
└─────────────────────────────────────────────────────────────────────────┘

WHAT'S CONNECTED:
┌─────────────────────────────────────────────────────────────────────────┐
│  orchestrator_worker.py                                                  │
│  ├── SynthesisService ✅ (initialized, subscribes to events)            │
│  ├── CoordinationService ❌ (NOT initialized, events not created)        │
│  └── ConvergenceMergeService ❌ (NOT initialized)                        │
│                                                                          │
│  spec_task_execution.py                                                  │
│  └── CoordinationService ✅ (initialized for spec execution only)        │
└─────────────────────────────────────────────────────────────────────────┘
```

**Consequence**:

- Tasks can only have basic `depends_on` dependencies
- No automatic result synthesis for non-spec tasks
- No git branch merge orchestration
- Parallel task coordination doesn't work outside spec flow

---

### Gap 4: Test Coverage Gaps

**20 integration test files** for **100 services** = ~20% coverage

#### Services WITH Integration Tests

| Test File | Services Tested |
|-----------|-----------------|
| `test_convergence_merge.py` | ConvergenceMergeService, ConflictScorer |
| `test_coordination_activation.py` | CoordinationService |
| `test_spec_task_execution_*.py` | SpecTaskExecutionService |
| `test_spec_sync_integration.py` | SpecSyncService |
| `test_validation_integration.py` | ValidationOrchestrator |
| `sandbox/*.py` (9 files) | Sandbox-related services |

#### Services WITHOUT Integration Tests (Critical)

| Service | Risk Level | Notes |
|---------|------------|-------|
| `MonitoringLoop` | 🔴 Critical | Orchestrates Guardian + Conductor |
| `IntelligentGuardian` | 🔴 Critical | Per-agent trajectory analysis |
| `ConductorService` | 🔴 Critical | System-wide coherence |
| `DiscoveryService` | 🔴 Critical | Workflow branching |
| `MemoryService` | 🟡 High | Pattern learning |
| `TaskContextBuilder` | 🟡 High | Context assembly |
| `PhaseProgressionService` | 🟡 High | Phase transitions |
| `OwnershipValidationService` | 🟡 High | File ownership |
| `AlertService` | 🟡 Medium | Alerting |
| `WatchdogService` | 🟡 Medium | Stuck detection |

---

### Gap 5: TODO/FIXME Items (51 Found)

#### Critical TODOs

| File | Line | TODO |
|------|------|------|
| `alerting.py` | 337 | `TODO: Implement actual email sending` |
| `alerting.py` | 346 | `TODO: Implement actual Slack webhook POST` |
| `alerting.py` | 355 | `TODO: Implement actual HTTP webhook POST` |
| `agent_registry.py` | 460 | `TODO: Implement version compatibility matrix` |
| `agent_registry.py` | 484 | `TODO: Implement resource availability check` |
| `restart_orchestrator.py` | 180 | `TODO: Implement cooldown tracking` |
| `restart_orchestrator.py` | 184 | `TODO: Implement restart attempt tracking` |
| `phase_progression_service.py` | 636 | `TODO: Check .omoi_os/specs/ directory` |
| `phase_progression_service.py` | 717 | `TODO: Integrate with parse_specs.py` |
| `billing.py` | 842-927 | `TODO: Add proper admin authentication check` (3 places) |

#### Medium Priority TODOs

| File | TODO |
|------|------|
| `memory.py:703` | Make extract_pattern async |
| `tickets.py:491` | Make embedding service async |
| `ticket_search_service.py:17` | Integrate with Qdrant |
| `auth.py:199` | Track logout in audit log |
| `auth.py:284` | Send email with reset link |
| `github.py:156` | Get webhook secret from project settings |
| `github.py:206` | Implement sync logic |

---

### Gap 6: API Routes Without Initialization

Some API routes import services that may not be initialized at startup:

| Route | Service Used | Initialization |
|-------|--------------|----------------|
| `/api/v1/graph/*` | DependencyGraphService | ⚠️ Created per-request |
| `/api/v1/specs/execute` | SpecTaskExecutionService | ⚠️ Created per-request |
| `/api/v1/memory/*` | MemoryService | ⚠️ Created per-request |

**Note**: Per-request initialization may cause performance issues under load.

---

### Recommended Fix Priority

#### Phase 1: Critical (Week 1)

1. [ ] Wire CoordinationService into orchestrator_worker.py
2. [ ] Wire ConvergenceMergeService into orchestrator_worker.py
3. [ ] Add subscribers for critical events (BUDGET_*, ALERT_*)
4. [ ] Fix admin auth TODOs in billing routes

#### Phase 2: High (Week 2-3)

1. [ ] Add integration tests for MonitoringLoop, Guardian, Conductor
2. [ ] Add integration tests for DiscoveryService
3. [ ] Implement alerting TODOs (email, Slack, webhooks)
4. [ ] Implement restart_orchestrator TODOs

#### Phase 3: Medium (Week 4+)

1. [ ] Add event subscribers for remaining orphaned events
2. [ ] Add integration tests for remaining untested services
3. [ ] Implement remaining TODO items
4. [ ] Performance test per-request service initialization

---

## Part 8: Service Initialization Map (CRITICAL REFERENCE)

> **This section maps EXACTLY where each service is initialized across the codebase.**
> Use this when wiring new services or debugging initialization issues.

### Two Initialization Points

OmoiOS has **two separate service initialization points** that don't share state:

| Location | File | Function | Purpose | Services Count |
|----------|------|----------|---------|----------------|
| **API Server** | `api/main.py` | `lifespan()` | FastAPI app startup | 25+ services |
| **Orchestrator Worker** | `workers/orchestrator_worker.py` | `init_services()` | Background worker | 9 services |

**⚠️ CRITICAL**: These run as **separate processes**. Services initialized in one are NOT available in the other.

---

### API Server Initialization (`api/main.py:656-830`)

```python
# Services initialized in API lifespan (lines 684-830)
# These are available to ALL API routes via global variables

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db, queue, event_bus, ...
    
    # === CORE INFRASTRUCTURE (lines 684-708) ===
    db = DatabaseService(connection_string=...)
    event_bus = EventBusService(redis_url=...)
    queue = TaskQueueService(db, event_bus=event_bus)
    agent_status_manager = AgentStatusManager(db, event_bus)
    approval_service = ApprovalService(db, event_bus)
    health_service = AgentHealthService(db, agent_status_manager)
    heartbeat_protocol_service = HeartbeatProtocolService(db, event_bus, agent_status_manager)
    registry_service = AgentRegistryService(db, event_bus, agent_status_manager)
    collaboration_service = CollaborationService(db, event_bus)
    lock_service = ResourceLockService(db)
    phase_gate_service = PhaseGateService(db)
    
    # === PHASE MANAGEMENT (lines 712-722) ===
    phase_manager = get_phase_manager(db=db, task_queue=queue, phase_gate=phase_gate_service, event_bus=event_bus)
    phase_manager.subscribe_to_events()  # CRITICAL: Subscribes to TASK_COMPLETED, etc.
    
    # === MONITORING (lines 724-730) ===
    monitor_service = MonitorService(db, event_bus)
    
    # === COST/BILLING (lines 733-734) ===
    cost_tracking_service = CostTrackingService(db, event_bus)
    budget_enforcer_service = BudgetEnforcerService(db, event_bus)
    
    # === DIAGNOSTIC SYSTEM (lines 737-769) ===
    phase_loader = PhaseLoader()
    billing_service = BillingService(db, event_bus)
    result_submission_service = ResultSubmissionService(db, event_bus, phase_loader, billing_service)
    embedding_service = EmbeddingService()
    memory_service = MemoryService(embedding_service, event_bus)
    discovery_service = DiscoveryService(event_bus)
    diagnostic_service = DiagnosticService(db=db, discovery=discovery_service, memory=memory_service, monitor=monitor_service, event_bus=event_bus)
    
    # === MCP SERVER (lines 772-780) ===
    initialize_mcp_services(db=db, event_bus=event_bus, task_queue=queue, discovery_service=discovery_service, collaboration_service=collaboration_service)
    
    # === VALIDATION (lines 783-791) ===
    validation_orchestrator = ValidationOrchestrator(db=db, agent_registry=registry_service, memory=memory_service, diagnostic=diagnostic_service, event_bus=event_bus)
    
    # === TICKET WORKFLOW (lines 794-799) ===
    ticket_workflow_orchestrator = TicketWorkflowOrchestrator(db=db, task_queue=queue, phase_gate=phase_gate_service, event_bus=event_bus)
    
    # === LLM SERVICE (lines 802-804) ===
    llm_service = get_llm_service()
    
    # === MONITORING LOOP (lines 807-830) ===
    monitoring_loop = MonitoringLoop(db=db, event_bus=event_bus, config=monitoring_config)
```

---

### Orchestrator Worker Initialization (`workers/orchestrator_worker.py:1263-1350`)

```python
# Services initialized in orchestrator worker (lines 1263-1350)
# These are available ONLY within the orchestrator worker process

async def init_services():
    global db, queue, event_bus, registry_service, task_analyzer
    
    # === CORE INFRASTRUCTURE (lines 1280-1296) ===
    db = DatabaseService(connection_string=app_settings.database.url)
    event_bus = EventBusService(redis_url=app_settings.redis.url)
    queue = TaskQueueService(db, event_bus=event_bus)
    registry_service = AgentRegistryService(db)
    
    # === TASK ANALYSIS (lines 1298-1300) ===
    task_analyzer = get_task_requirements_analyzer()
    
    # === PHASE MANAGEMENT (lines 1302-1331) ===
    phase_gate = PhaseGateService(db)
    workflow_orchestrator = TicketWorkflowOrchestrator(db=db, task_queue=queue, phase_gate=phase_gate, event_bus=event_bus)
    phase_progression = get_phase_progression_service(db=db, task_queue=queue, phase_gate=phase_gate, event_bus=event_bus)
    phase_progression.set_workflow_orchestrator(workflow_orchestrator)
    phase_progression.subscribe_to_events()  # CRITICAL: Hook 1 + Hook 2
    
    # === SYNTHESIS SERVICE (lines 1333-1348) ===
    synthesis_service = SynthesisService(db=db, event_bus=event_bus)
    synthesis_service.subscribe_to_events()  # Listens for coordination.join.created
    
    # ❌ MISSING: CoordinationService (creates join events) - NOT INITIALIZED
    # ❌ MISSING: ConvergenceMergeService (handles git merges) - NOT INITIALIZED
    # ❌ MISSING: OwnershipValidationService (prevents conflicts) - NOT INITIALIZED
```

---

### Service Initialization Comparison

| Service | API Server | Orchestrator Worker | Notes |
|---------|------------|---------------------|-------|
| **DatabaseService** | ✅ Line 685 | ✅ Line 1283 | Both have own connections |
| **EventBusService** | ✅ Line 696 | ✅ Line 1287 | Both have own Redis connections |
| **TaskQueueService** | ✅ Line 697 | ✅ Line 1291 | Both have own instances |
| **AgentRegistryService** | ✅ Line 706 | ✅ Line 1295 | Both have own instances |
| **PhaseGateService** | ✅ Line 709 | ✅ Line 1303 | Both have own instances |
| **PhaseManager** | ✅ Line 714 | ❌ Not init | API-only (routes use it) |
| **PhaseProgressionService** | ❌ Not init | ✅ Line 1319 | Worker-only (auto-advance) |
| **SynthesisService** | ❌ Not init | ✅ Line 1339 | Worker-only (result merging) |
| **CoordinationService** | ❌ Not init | ❌ **MISSING** | **NEVER INITIALIZED** |
| **ConvergenceMergeService** | ❌ Not init | ❌ **MISSING** | **NEVER INITIALIZED** |
| **OwnershipValidationService** | ❌ Not init | ❌ **MISSING** | **NEVER INITIALIZED** |
| **MonitoringLoop** | ✅ Line 819 | ❌ Not init | API-only (Guardian+Conductor) |
| **MemoryService** | ✅ Line 761 | ❌ Not init | API-only (pattern RAG) |
| **DiscoveryService** | ✅ Line 762 | ❌ Not init | API-only (adaptive branching) |
| **DiagnosticService** | ✅ Line 763 | ❌ Not init | API-only |
| **ValidationOrchestrator** | ✅ Line 785 | ❌ Not init | API-only |
| **BillingService** | ✅ Line 752 | ❌ Not init | API-only |
| **LLMService** | ✅ Line 804 | ❌ Not init | API-only |

---

## Part 9: Exact Code Changes for Integration Fixes

### Fix 1: Wire CoordinationService into Orchestrator Worker

**File:** `backend/omoi_os/workers/orchestrator_worker.py`  
**Location:** `init_services()` function, after line 1348

```python
# === ADD AFTER LINE 1348 (after SynthesisService initialization) ===

    # CoordinationService (creates coordination patterns: SYNC, SPLIT, JOIN, MERGE)
    # This service publishes coordination.join.created events that SynthesisService listens for
    from omoi_os.services.coordination import CoordinationService
    coordination_service = CoordinationService(
        db=db,
        queue=queue,
        event_bus=event_bus,
    )
    logger.info(
        "service_initialized",
        service="coordination_service",
        capabilities=["sync", "split", "join", "merge"],
    )
```

**Why This Matters:**

- Without CoordinationService, `coordination.join.created` events are NEVER published
- SynthesisService is listening but never receives events
- Parallel task result merging doesn't work

---

### Fix 2: Wire ConvergenceMergeService into Orchestrator Worker

**File:** `backend/omoi_os/workers/orchestrator_worker.py`  
**Location:** `init_services()` function, after CoordinationService

```python
# === ADD AFTER CoordinationService initialization ===

    # ConvergenceMergeService (handles git merging at DAG convergence points)
    # This service listens for coordination.synthesis.completed events and merges branches
    from omoi_os.services.convergence_merge_service import (
        get_convergence_merge_service,
        ConvergenceMergeConfig,
    )
    from omoi_os.services.agent_conflict_resolver import AgentConflictResolver
    
    # Initialize conflict resolver for LLM-based conflict resolution
    conflict_resolver = AgentConflictResolver(llm_service=get_llm_service())
    
    convergence_merge_service = get_convergence_merge_service(
        db=db,
        event_bus=event_bus,
        config=ConvergenceMergeConfig(
            max_conflicts_auto_resolve=10,  # Auto-resolve up to 10 conflicts
            enable_auto_push=False,          # Don't push automatically
        ),
        conflict_resolver=conflict_resolver,
    )
    convergence_merge_service.subscribe_to_events()  # Listen for synthesis.completed
    logger.info(
        "service_initialized",
        service="convergence_merge_service",
        capabilities=["branch_merge", "conflict_scoring", "llm_resolution"],
    )
```

**Why This Matters:**

- Without ConvergenceMergeService, git branches from parallel tasks are NEVER merged
- Convergence points in the DAG don't trigger code synthesis
- Parallel task coordination breaks at the git level

---

### Fix 3: Wire OwnershipValidationService into Orchestrator Worker

**File:** `backend/omoi_os/workers/orchestrator_worker.py`  
**Location:** `init_services()` function, before DaytonaSpawner is used

```python
# === ADD AFTER ConvergenceMergeService initialization ===

    # OwnershipValidationService (prevents parallel task file conflicts)
    # This service tracks which tasks own which files during parallel execution
    from omoi_os.services.ownership_validation import (
        get_ownership_validation_service,
    )
    ownership_service = get_ownership_validation_service(
        db=db,
        strict_mode=False,  # Start permissive, tighten after testing
    )
    logger.info(
        "service_initialized",
        service="ownership_validation",
        capabilities=["file_ownership", "conflict_detection"],
    )
```

**Why This Matters:**

- Without OwnershipValidationService, parallel tasks can edit the same files
- This causes merge conflicts and lost work
- The DAG system was designed to use this for conflict prevention

---

### Fix 4: Add Missing Event Subscribers

**File:** `backend/omoi_os/api/main.py`  
**Location:** `lifespan()` function, after monitoring_loop initialization (line 830)

```python
# === ADD AFTER monitoring_loop initialization ===

    # === BUDGET/COST EVENT HANDLING ===
    # Subscribe to budget events for alerting
    def handle_budget_exceeded(event_data):
        """Handle BUDGET_EXCEEDED events by triggering alerts."""
        payload = event_data.get("payload", {})
        project_id = payload.get("project_id")
        usage = payload.get("usage")
        limit = payload.get("limit")
        logger.warning(
            "budget_exceeded_alert",
            project_id=project_id,
            usage=usage,
            limit=limit,
        )
        # TODO: Trigger actual alerts via alerting service
    
    event_bus.subscribe("BUDGET_EXCEEDED", handle_budget_exceeded)
    event_bus.subscribe("BUDGET_WARNING", handle_budget_exceeded)  # Same handler for warnings
    
    # === QUALITY EVENT HANDLING ===
    def handle_quality_check(event_data):
        """Handle QUALITY_CHECK_* events for quality dashboards."""
        payload = event_data.get("payload", {})
        logger.info("quality_check_received", payload=payload)
        # Store in quality_metrics table for dashboard
    
    event_bus.subscribe("QUALITY_CHECK_PASSED", handle_quality_check)
    event_bus.subscribe("QUALITY_CHECK_FAILED", handle_quality_check)
    
    logger.info(
        "event_subscribers_registered",
        events=["BUDGET_EXCEEDED", "BUDGET_WARNING", "QUALITY_CHECK_*"],
    )
```

---

### Fix 5: Update orchestrator_loop to Use CoordinationService

**File:** `backend/omoi_os/workers/orchestrator_worker.py`  
**Location:** `orchestrator_loop()` function, when spawning tasks with dependencies

The orchestrator currently uses basic `depends_on` checking. To enable full DAG coordination:

```python
# === IN orchestrator_loop(), around line 430 ===
# When a task has multiple dependencies that could be parallel:

# CURRENT (basic dependency check):
task = queue.get_next_task_with_concurrency_limit(...)

# ENHANCED (with coordination):
# If task has dependencies that were parallel, check if synthesis is complete
task = queue.get_next_task_with_concurrency_limit(...)
if task and task.dependencies:
    depends_on = task.dependencies.get("depends_on", [])
    if len(depends_on) > 1:
        # Check if CoordinationService has a join registered for this task
        # If synthesis_context is not populated, the join isn't ready
        if not task.synthesis_context:
            # Skip this task - parallel dependencies not yet synthesized
            logger.debug(
                "task_waiting_for_synthesis",
                task_id=str(task.id),
                dependencies=depends_on,
            )
            continue
```

---

## Part 10: Integration Checklist for Future Agents

> **Copy this checklist when making changes to OmoiOS services.**

### Before Adding a New Service

- [ ] Determine which process needs it (API, Orchestrator, or both)
- [ ] Check if a singleton getter exists (e.g., `get_*_service()`)
- [ ] If singleton exists, check if it's actually called anywhere
- [ ] Plan where to initialize (see Part 8 for locations)

### When Initializing a Service

- [ ] Add import at top of file
- [ ] Initialize in correct order (dependencies first)
- [ ] If service publishes events, verify subscribers exist
- [ ] If service subscribes to events, call `.subscribe_to_events()`
- [ ] Add logger.info for initialization tracking
- [ ] Update this document if adding to core initialization

### When Adding Event Publishing

- [ ] Check if any service subscribes to this event type
- [ ] If no subscribers exist, document in Part 7 (Events Published Into Void)
- [ ] Consider adding a subscriber for the event
- [ ] Use consistent event naming (ENTITY_ACTION format)

### When Adding Event Subscribing

- [ ] Verify the event is actually published somewhere
- [ ] Call `event_bus.subscribe()` AFTER event_bus is initialized
- [ ] Test that events are received (use Redis CLI to publish test events)

### Testing Integration

```bash
# Test event flow
redis-cli PUBLISH events.TASK_COMPLETED '{"event_type":"TASK_COMPLETED","entity_type":"task","entity_id":"test-123","payload":{}}'

# Check service initialization
grep -r "service_initialized" backend/omoi_os/workers/ | wc -l

# Check event subscriptions
grep -r "event_bus.subscribe" backend/omoi_os/ | wc -l

# Check orphaned getters
grep -rn "^def get_.*_service" backend/omoi_os/services/ | while read line; do
  getter=$(echo "$line" | sed 's/.*def \(get_[^(]*\).*/\1/')
  count=$(grep -r "$getter" backend/omoi_os/ | grep -v "^def $getter" | wc -l)
  if [ "$count" -eq 0 ]; then
    echo "ORPHANED: $line"
  fi
done
```

---

## Part 11: Quick Reference Cards

### Card 1: Where to Initialize Services

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SERVICE INITIALIZATION LOCATIONS                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  API Routes need it?  ──────────→  api/main.py:lifespan()           │
│                                                                      │
│  Background worker needs it?  ──→  workers/orchestrator_worker.py   │
│                                    init_services()                   │
│                                                                      │
│  Both need it?  ────────────────→  Initialize in BOTH places        │
│                                    (they're separate processes!)     │
│                                                                      │
│  Per-request? (bad pattern) ────→  Review if should be singleton    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Card 2: Event Flow Verification

```
┌─────────────────────────────────────────────────────────────────────┐
│                      EVENT FLOW CHECKLIST                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. PUBLISHER                                                        │
│     - Where is event_bus.publish() called?                           │
│     - File: _________________ Line: _______                          │
│                                                                      │
│  2. SUBSCRIBER                                                       │
│     - Where is event_bus.subscribe() called?                         │
│     - File: _________________ Line: _______                          │
│     - Handler function: _________________                            │
│                                                                      │
│  3. REDIS CHANNEL                                                    │
│     - Channel name: events.{EVENT_TYPE}                              │
│     - Test: redis-cli SUBSCRIBE events.EVENT_TYPE                    │
│                                                                      │
│  4. VERIFICATION                                                     │
│     - [ ] Publisher initializes after event_bus                      │
│     - [ ] Subscriber calls subscribe() in initialization             │
│     - [ ] Handler function handles SystemEvent format                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Card 3: DAG System Integration

```
┌────────────────────────────────────────────────────────────────────-─┐
│                      DAG SYSTEM FLOW                                 │
├───────────────────────────────────────────────────────────────────-──┤
│                                                                      │
│  ┌──────────────────┐    coordination.join.created                   │
│  │CoordinationService│ ─────────────────────────────────┐            │
│  │  join_tasks()    │                                   │            │
│  │  split_task()    │                                   ▼            │
│  └──────────────────┘                         ┌──────────────────┐   │
│                                               │ SynthesisService │   │
│                                               │ _handle_join_*() │   │
│  ┌──────────────────┐    TASK_COMPLETED       │ tracks pending   │   │
│  │  TaskQueueService │ ──────────────────────→│ joins, merges    │   │
│  │  update_status() │                         │ results when     │   │
│  └──────────────────┘                         │ ready            │   │
│                                               └────────┬─────────┘   │
│                                                        │             │
│                              coordination.synthesis.completed        │
│                                                        │             │
│                                                        ▼             │
│                                         ┌────────────────────────┐   │
│                                         │ConvergenceMergeService │   │
│                                         │ merge_at_convergence() │   │
│                                         │ (git branch merging)   │   │
│                                         └────────────────────────┘   │
│                                                                      │
└────────────────────────────────────────────────────────────────────-─┘
```

---

## Next Steps

1. **Fix Integration Gaps**: Address Phase 1 critical gaps first (see Part 9)
2. **Verify Event Flow**: Use checklist in Part 10 to verify each event
3. **Test DAG System**: After wiring, test with parallel tasks
4. **Monitor Production**: Watch logs for `service_initialized` entries
5. **Update This Document**: Keep Part 8 current as services change
