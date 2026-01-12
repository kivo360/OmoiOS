# Spec-Driven Development Architecture

**Created**: 2025-01-11
**Status**: Documentation of existing system
**Purpose**: Trace complete flow of spec-driven development paths

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
