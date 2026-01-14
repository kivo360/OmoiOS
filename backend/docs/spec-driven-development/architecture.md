# Spec-Driven Development Architecture

**Created**: 2025-01-11
**Updated**: 2025-01-13 (Added Target State diagrams and cross-references)
**Status**: Documentation of existing system + target architecture
**Purpose**: Trace complete flow of spec-driven development paths

---

## 🔄 Cross-Reference (2025-01-13)

**Sandbox Infrastructure Status**: The sandbox event system, message injection, and `spawn_for_phase()` are **100% implemented**. See `docs/design/sandbox-agents/IMPLEMENTATION_COMPLETE_STATUS.md`.

**What's Missing**: The API endpoints don't call the sandbox infrastructure. See [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) for fixes.

---

## System Overview

The spec-driven development system has two distinct execution paths that were built separately and serve different purposes.

---

## Path 1: Prompt Injection Path

This path injects a detailed prompt telling the agent HOW to create specs manually.

### Trigger Conditions

Both conditions must be true:
- `EXECUTION_MODE=exploration`
- `REQUIRE_SPEC_SKILL=true`

### Flow Trace

```
Command Page (workflow_mode="spec_driven")
    │
    ▼
tickets.py:460-472
    │ Sets execution_config:
    │   require_spec_skill: True
    │   selected_skill: "spec-driven-dev"
    │
    ▼
task_queue.py:175, 202
    │ Stores execution_config in Task model
    │
    ▼
orchestrator_worker.py:724-747
    │ Extracts require_spec_skill from task.execution_config
    │ Passes to daytona_spawner.spawn_for_task()
    │
    ▼
daytona_spawner.py:235, 250
    │ Sets environment variables:
    │   EXECUTION_MODE=exploration (for EXPLORATION_TASK_TYPES)
    │   REQUIRE_SPEC_SKILL=true
    │
    ▼
claude_sandbox_worker.py:1379, 1398-1399
    │ Reads environment variables:
    │   self.execution_mode = os.environ.get("EXECUTION_MODE")
    │   self.require_spec_skill = os.environ.get("REQUIRE_SPEC_SKILL")
    │
    ▼
claude_sandbox_worker.py:1553-1554
    │ Checks BOTH conditions:
    │   if execution_mode == "exploration" AND require_spec_skill:
    │
    ▼
claude_sandbox_worker.py:1573-1723
    │ Injects spec_driven_dev_prompt into system prompt
    │
    ▼
Agent receives prompt telling it to:
    - Explore codebase
    - Create EARS-format requirements
    - Design architecture
    - Break into tasks
    - (All manually driven by agent following prompt)
```

### Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `tickets.py` | 460-472 | Sets `require_spec_skill: True` |
| `task_queue.py` | 175, 202 | Stores `execution_config` |
| `orchestrator_worker.py` | 724-747 | Extracts and passes to spawner |
| `daytona_spawner.py` | 235, 250 | Sets env vars |
| `claude_sandbox_worker.py` | 1553-1554 | Condition check |
| `claude_sandbox_worker.py` | 1573-1723 | Prompt injection |

### What This Path Does

- Agent is TOLD what to do via detailed prompt
- Agent manually creates specs by calling APIs or writing files
- No automatic phase progression
- No quality gates between phases
- No checkpoint/resume support

---

## Path 2: SpecStateMachine Path

This path runs a programmatic multi-phase state machine that handles phase transitions automatically.

### Trigger Conditions

Both must be set:
- `SPEC_ID=<uuid>` (existing spec record)
- `SPEC_PHASE=<phase>` (explore/requirements/design/tasks/sync)

### Flow Trace (API Trigger)

```
POST /api/v1/specs/{spec_id}/execute
    │
    ▼
specs.py:1381-1416
    │ Calls run_spec_state_machine(spec_id, working_dir)
    │
    ▼
spec_state_machine.py
    │ SpecStateMachine.run()
    │
    ▼
Phases execute sequentially:
    EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC → COMPLETE
    │
    │ Each phase:
    │   1. Runs query() with phase-specific prompt
    │   2. Evaluator validates output (quality gate)
    │   3. Saves checkpoint to database
    │   4. Transitions to next phase
    │
    ▼
Spec record updated with results
```

### Flow Trace (Sandbox Trigger)

```
daytona_spawner.spawn_for_phase(spec_id, phase, ...)
    │
    ▼
daytona_spawner.py:812-825
    │ Sets environment variables:
    │   SPEC_ID=<spec_id>
    │   SPEC_PHASE=<phase>
    │   PROJECT_ID=<project_id>
    │   EXECUTION_MODE=exploration (or implementation for sync)
    │   REQUIRE_SPEC_SKILL=true
    │
    ▼
claude_sandbox_worker.py:4430
    │ Checks condition:
    │   if config.spec_phase AND config.spec_id:
    │
    ▼
claude_sandbox_worker.py:4431
    │ return await self._run_spec_state_machine()
    │
    ▼
claude_sandbox_worker.py:4211-4281
    │ _run_spec_state_machine():
    │   - Imports SpecStateMachine
    │   - Creates database session
    │   - Initializes state machine
    │   - Calls state_machine.run()
    │
    ▼
spec_state_machine.py runs phases within SINGLE sandbox
```

### Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `specs.py` | 1348-1439 | `/execute` endpoint |
| `spec_state_machine.py` | entire | State machine implementation |
| `daytona_spawner.py` | 750-920 | `spawn_for_phase()` |
| `claude_sandbox_worker.py` | 4211-4281 | `_run_spec_state_machine()` |
| `claude_sandbox_worker.py` | 4430-4431 | Trigger condition |

### State Machine Phases

```
┌─────────────────────────────────────────────────────────────┐
│                     SpecStateMachine                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  EXPLORE ──────► REQUIREMENTS ──────► DESIGN                │
│     │                  │                 │                  │
│     │ evaluator        │ evaluator       │ evaluator        │
│     │ (quality gate)   │ (quality gate)  │ (quality gate)   │
│     ▼                  ▼                 ▼                  │
│                                                             │
│  ────────────────► TASKS ──────────► SYNC ──────► COMPLETE  │
│                      │                 │                    │
│                      │ evaluator       │ evaluator          │
│                      │                 │                    │
│                      ▼                 ▼                    │
│                                                             │
│  Each phase:                                                │
│  1. Load context from previous phases                       │
│  2. Run query() with phase prompt                           │
│  3. Evaluator validates output                              │
│  4. Save checkpoint (for crash recovery)                    │
│  5. Transition to next phase                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### What This Path Does

- System drives phase progression automatically
- Evaluators validate quality between phases
- Checkpoints saved for crash recovery
- `spawn_for_phase()` only used for crash recovery (resume from checkpoint)
- Single sandbox runs all phases (not one sandbox per phase)

---

## Comparison

| Aspect | Prompt Injection | SpecStateMachine |
|--------|------------------|------------------|
| **Control** | Agent-driven (via prompt) | System-driven (code) |
| **Phases** | Agent follows prompt instructions | Automated state machine |
| **Quality Gates** | Manual (agent decides) | Evaluators between phases |
| **Recovery** | Manual restart | Checkpoint-based resume |
| **Requires** | Just task with `require_spec_skill` | Pre-existing `spec_id` |
| **Best For** | Initial exploration from scratch | Structured, recoverable workflows |

---

## Environment Variables Reference

| Variable | Set By | Used By | Purpose |
|----------|--------|---------|---------|
| `EXECUTION_MODE` | daytona_spawner | claude_sandbox_worker | "exploration" or "implementation" |
| `REQUIRE_SPEC_SKILL` | daytona_spawner | claude_sandbox_worker | "true" to inject prompt |
| `SPEC_ID` | daytona_spawner | claude_sandbox_worker | UUID of spec record |
| `SPEC_PHASE` | daytona_spawner | claude_sandbox_worker | Current phase name |
| `PHASE_CONTEXT_B64` | daytona_spawner | claude_sandbox_worker | Base64 encoded phase data |
| `OMOIOS_PROJECT_ID` | daytona_spawner | sandbox | Project ID for API calls |
| `OMOIOS_API_URL` | daytona_spawner | sandbox | Backend API URL |

---

## Database Models

### Spec Model (`omoi_os/models/spec.py`)

```python
class Spec(Base):
    id: str
    project_id: str
    title: str
    description: str
    status: str  # draft, executing, completed, failed
    phase: str   # current phase
    current_phase: str
    progress: int
    # ... requirements, design, tasks relationships
```

### SpecTask Model

```python
class SpecTask(Base):
    id: str
    spec_id: str  # FK to Spec
    title: str
    description: str
    phase: str
    priority: str
    status: str
    # ... execution tracking
```

### Ticket Model (NO spec_id currently)

```python
class Ticket(Base):
    id: str
    title: str
    description: str
    # NO spec_id field - this is a gap
```

---

## 🎯 TARGET STATE ARCHITECTURE (After Implementation)

This section shows how the system SHOULD work after implementing the fixes in [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md).

### Complete End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SPEC-DRIVEN DEVELOPMENT FLOW                        │
│                            (TARGET STATE - FIXED)                            │
└─────────────────────────────────────────────────────────────────────────────┘

                              USER INPUT
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ENTRY POINTS                                                                │
│  ┌─────────────┐    ┌──────────────────┐    ┌─────────────────────┐         │
│  │ Command     │    │ POST /specs      │    │ POST /specs/{id}    │         │
│  │ Page Input  │───►│ (create spec)    │───►│ /execute            │         │
│  │ (Cmd+K)     │    │                  │    │                     │         │
│  └─────────────┘    └──────────────────┘    └──────────┬──────────┘         │
└─────────────────────────────────────────────────────────│────────────────────┘
                                                          │
                                          ┌───────────────┴───────────────┐
                                          │  spawn_for_phase()            │
                                          │  (daytona_spawner.py:750)     │
                                          │                               │
                                          │  Sets: SPEC_ID, SPEC_PHASE    │
                                          │        PROJECT_ID, etc.       │
                                          └───────────────┬───────────────┘
                                                          │
                                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  SANDBOX ENVIRONMENT (Isolated)                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  claude_sandbox_worker.py                                              │  │
│  │                                                                        │  │
│  │  if config.spec_phase AND config.spec_id:                             │  │
│  │      await _run_spec_state_machine()   (line 4211)                    │  │
│  │                                                                        │  │
│  │  ┌────────────────────────────────────────────────────────────────┐   │  │
│  │  │                    SPEC STATE MACHINE                           │   │  │
│  │  │                                                                 │   │  │
│  │  │  EXPLORE ──► REQUIREMENTS ──► DESIGN ──► TASKS ──► SYNC       │   │  │
│  │  │     │              │            │          │          │        │   │  │
│  │  │     ▼              ▼            ▼          ▼          ▼        │   │  │
│  │  │  (eval)        (eval)       (eval)     (eval)     (eval)      │   │  │
│  │  │                                                      │         │   │  │
│  │  │                                                      ▼         │   │  │
│  │  │                                           SpecTaskExecutionSvc │   │  │
│  │  │                                           (NEW - wired in)     │   │  │
│  │  └────────────────────────────────────────────┬───────────────────┘   │  │
│  │                                               │                        │  │
│  │  ┌────────────────────────────────────────────┼───────────────────┐   │  │
│  │  │  EventReporter (NEW - reports to API)      │                   │   │  │
│  │  │  POST /api/v1/sandboxes/{id}/events        │                   │   │  │
│  │  │                                            │                   │   │  │
│  │  │  Events: phase_started, phase_complete,    │                   │   │  │
│  │  │          error, progress                   │                   │   │  │
│  │  └────────────────────────────────────────────┼───────────────────┘   │  │
│  └───────────────────────────────────────────────┼───────────────────────┘  │
└──────────────────────────────────────────────────│──────────────────────────┘
                                                   │
                                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  BRIDGE: SpecTaskExecutionService                                            │
│  (omoi_os/services/spec_task_execution.py)                                   │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  1. Creates bridging Ticket (if not exists)                            │ │
│  │     - ticket.user_id = spec.user_id (NEW)                              │ │
│  │     - ticket.spec_id stored in context (or FK)                         │ │
│  │                                                                         │ │
│  │  2. Converts SpecTask → Task                                           │ │
│  │     - For each SpecTask: create Task record                            │ │
│  │     - Task linked to Ticket                                            │ │
│  │                                                                         │ │
│  │  3. Tasks queued for execution                                         │ │
│  │     - TaskQueueService picks up Tasks                                  │ │
│  │     - OrchestratorWorker assigns to agents                             │ │
│  └──────────────────────────────────────────┬─────────────────────────────┘ │
└─────────────────────────────────────────────│───────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  EXECUTION: OrchestratorWorker → Daytona Sandboxes                          │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  orchestrator_worker.py                                                │ │
│  │                                                                         │ │
│  │  1. Poll TaskQueueService for ready tasks                              │ │
│  │  2. For each Task:                                                     │ │
│  │     - Spawn Daytona sandbox                                            │ │
│  │     - Clone GitHub repo (if project has repo)                          │ │
│  │     - Agent executes task                                              │ │
│  │     - Push changes, create PR                                          │ │
│  │  3. On completion:                                                     │ │
│  │     - Update SpecTask status via event                                 │ │
│  │     - Update Ticket progress                                           │ │
│  └──────────────────────────────────────────┬─────────────────────────────┘ │
└─────────────────────────────────────────────│───────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  COMPLETION: Spec Status Updates                                             │
│                                                                              │
│  When ALL Tasks complete:                                                    │
│  1. Ticket marked completed                                                  │
│  2. SpecTask records updated                                                 │
│  3. Spec.status = "completed"                                                │
│  4. GitHub PR ready for review                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Current vs Target State Comparison

```
CURRENT STATE (BROKEN):

POST /specs/{id}/execute
        │
        ▼
run_spec_state_machine()  ← Runs in API process! ❌
        │
        ▼
EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC → COMPLETE
                                            │
                                            ▼
                                    Creates SpecTask records
                                            │
                                            ▼
                                    DEAD END ❌ (Nothing happens)


TARGET STATE (FIXED):

POST /specs/{id}/execute
        │
        ▼
spawn_for_phase()  ← Spawns sandbox! ✅
        │
        ▼
[Sandbox] claude_sandbox_worker._run_spec_state_machine()
        │
        ▼
EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC
                                            │
        ┌───────────────────────────────────┘
        │
        ▼
SpecTaskExecutionService.execute_spec_tasks()  ← NEW wiring! ✅
        │
        ▼
Creates Ticket + Tasks
        │
        ▼
TaskQueueService → OrchestratorWorker → Daytona Sandboxes
        │
        ▼
EXECUTION (agents working on code)
        │
        ▼
COMPLETION (PR created, spec done)
```

### Key Components Requiring Changes

| Component | Current State | Target State | Change Required |
|-----------|--------------|--------------|-----------------|
| `specs.py:execute` | Calls `run_spec_state_machine()` | Calls `spawn_for_phase()` | Yes |
| `spec_state_machine.py:291` | Creates SpecTask via SpecSyncService | Also calls `execute_spec_tasks()` | Yes |
| `Spec` model | No `user_id` field | Has `user_id` field | Yes (migration) |
| `SpecStateMachine` | No EventReporter | Uses EventReporter | Yes |
| `Ticket.spec_id` | Stored in context JSON | Proper FK column | Optional |

### File Locations for Implementation

```
PHASE 1: Critical Wiring
├── omoi_os/api/routes/specs.py:1440-1514    → Change /execute to spawn sandbox
└── omoi_os/workers/spec_state_machine.py:291  → Add execute_spec_tasks() call in _execute_sync_phase

PHASE 2: User Ownership
├── omoi_os/models/spec.py                    → Add user_id FK
└── alembic/versions/xxx_add_spec_user_id.py  → Migration

PHASE 3: Real-Time UI
├── omoi_os/workers/spec_state_machine.py     → Add EventReporter usage
└── omoi_os/workers/spec_*.py phases          → Emit phase events

PHASE 4: Command Page
└── omoi_os/api/routes/specs.py               → Add /launch endpoint
```

### GitHub Integration Points (Task Execution)

The orchestrator already handles GitHub integration for task execution:

```
orchestrator_worker.py:530-629  ─►  GitHub Repo Clone
orchestrator_worker.py:1075-1170 ─►  PR Creation on Success

This works when:
1. Project has github_repo_url set
2. User has GitHub token connected
3. Task is picked up by orchestrator

This is NOT connected to spec execution yet - that's the gap.
```

---

## Summary: What Works vs What's Broken

### ✅ Working Components

1. **Spec State Machine** - All phases work correctly
2. **SpecTaskExecutionService** - Bridge fully implemented
3. **Sandbox Infrastructure** - `spawn_for_phase()` exists and works
4. **Task Execution** - Orchestrator → Daytona → Agent flow works
5. **GitHub Integration** - Clone, commit, PR creation works in task execution

### ❌ Broken Connections

1. `/execute` runs in API process, not sandbox
2. SYNC phase doesn't call SpecTaskExecutionService
3. Spec has no `user_id` → Tickets invisible on board
4. State machine doesn't emit real-time events

### 📋 Implementation Roadmap

See [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) for:
- Step-by-step fix instructions
- Code snippets for each change
- Verification checklists
- Estimated time per phase
