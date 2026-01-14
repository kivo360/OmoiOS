# Spec-Driven Development Documentation

This directory contains documentation for the spec-driven development workflow system.

## Overview

Spec-driven development allows users to go from **idea → spec → tickets → automated execution**.

---

## 🔄 Cross-Reference with Sandbox Infrastructure (2025-01-13)

**IMPORTANT**: The sandbox infrastructure documented in `docs/design/sandbox-agents/` is **100% implemented** on the backend. This includes:
- ✅ Event callback endpoints (`sandbox.py:365`)
- ✅ Message injection (`sandbox.py:758,803`)
- ✅ Guardian sandbox intervention (`intelligent_guardian.py:693-887`)
- ✅ Idle sandbox monitoring (`idle_sandbox_monitor.py`)
- ✅ Worker spec mode support (`claude_sandbox_worker.py:4211-4431`)
- ✅ `spawn_for_phase()` method (`daytona_spawner.py:750`)

**The gaps documented below are SPEC-SPECIFIC** - they describe how the spec-driven workflow needs to better USE the existing sandbox infrastructure, not rebuild it.

See: `docs/design/sandbox-agents/IMPLEMENTATION_COMPLETE_STATUS.md` for full backend status.

---

## 📊 Implementation Status At-a-Glance

| Component | Status | What Exists | What's Missing |
|-----------|--------|-------------|----------------|
| **State Machine** | ✅ 100% | All 6 phases work (EXPLORE→REQUIREMENTS→DESIGN→TASKS→SYNC→COMPLETE) | Nothing |
| **SpecTaskExecutionService** | ✅ 100% | Converts SpecTask→Ticket/Task, handles dependencies | Nothing |
| **Sandbox Infrastructure** | ✅ 100% | `spawn_for_phase()`, EventReporter, callbacks | Nothing |
| **Wiring: State Machine → Bridge** | ✅ 100% | Calls `execute_spec_tasks()` after SYNC | Nothing |
| **Wiring: API → Sandbox** | ✅ 100% | `/execute` calls `spawn_for_phase()` | Nothing |
| **Spec.user_id** | ✅ 100% | Model field + migration (051) + auth on routes | Nothing |
| **Event Reporting** | ✅ 100% | `spec_id` on SandboxEvent + `/events` endpoint | Nothing |
| **Command Page /launch** | ✅ 100% | `POST /specs/launch` endpoint | Nothing |
| **GitHub Integration** | ✅ 100% | Credentials flow + PR tracking + SpecCompletionService | Nothing |

**TL;DR**: Core spec-driven workflow is **fully wired and complete**!

---

## ✅ GAPS RESOLVED (2025-01-14)

1. ~~**SpecTask → Ticket Gap**~~: ✅ **FIXED** - State machine now calls `execute_spec_tasks()` after SYNC
2. ~~**Sandbox Execution Bug**~~: ✅ **FIXED** - `/execute` now calls `spawn_for_phase()`
3. ~~**No Event Reporting**~~: ✅ **FIXED** - `spec_id` added to SandboxEvent, `/events` endpoint added
4. ~~**Ticket `user_id` Not Set**~~: ✅ **FIXED** - `user_id` passed from Spec to Ticket creation
5. ~~**GitHub Integration**~~: ✅ **FIXED** - See details below

**TL;DR**: The spec-driven workflow is now **fully complete**!

## ✅ GitHub Integration Complete (2025-01-14)

All GitHub integration gaps have been resolved:

| Gap | Status | Implementation |
|-----|--------|----------------|
| **Project → GitHub Repo** | ✅ **EXISTED** | `Project.github_owner`, `Project.github_repo` fields already present |
| **User → GitHub Token** | ✅ **EXISTED** | `CredentialsService.get_github_credentials()` fetches from `User.attributes.github_access_token` |
| **Sandbox GitHub Env Vars** | ✅ **FIXED** | `spawn_for_phase()` now fetches user credentials and passes `GITHUB_TOKEN`, `GITHUB_REPO`, etc. |
| **PR Tracking Fields** | ✅ **FIXED** | Added `Spec.branch_name`, `Spec.pull_request_url`, `Spec.pull_request_number` (migration 053) |
| **Auto PR Creation** | ✅ **FIXED** | `SpecCompletionService` with `create_branch_for_spec()`, `create_pr_for_spec()` methods |
| **API Endpoints** | ✅ **FIXED** | `POST /specs/{id}/create-branch`, `POST /specs/{id}/create-pr` |

See [github-integration-gap.md](./github-integration-gap.md) for full details on what was implemented.

## Documents

### 📋 Implementation Guide

| Document | Description |
|----------|-------------|
| **[IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md)** | **🚀 START HERE FOR IMPLEMENTATION**: Complete step-by-step guide with exact file locations, code changes, and verification checklists |
| **[TESTING_GUIDE.md](./TESTING_GUIDE.md)** | **🧪 TESTING REFERENCE**: How to test each phase - unit tests, integration tests, API tests, UI/browser prompts, local sandbox testing |

### 📊 Architecture & Analysis

| Document | Description |
|----------|-------------|
| [architecture.md](./architecture.md) | Complete system architecture, flow diagrams, and target state |
| [impact-assessment.md](./impact-assessment.md) | Gap assessment: How fucked are we? (Not very!) |

### 🟢 Gap Documentation (All Resolved)

| Document | Description | Status |
|----------|-------------|--------|
| [ticket-field-gap.md](./ticket-field-gap.md) | Tickets invisible on board - missing `user_id` | ✅ FIXED |
| [sandbox-execution.md](./sandbox-execution.md) | `/execute` runs in API process, not sandbox | ✅ FIXED |
| [data-flow-gap.md](./data-flow-gap.md) | SpecTask → Ticket gap (bridge exists but not wired!) | ✅ FIXED |
| [ui-and-events.md](./ui-and-events.md) | Event reporting gap and real-time UI updates | ✅ FIXED |
| [github-integration-gap.md](./github-integration-gap.md) | GitHub integration missing for spec execution | ✅ FIXED |

### 🔮 Future Features (Design Only)

| Document | Description | Status |
|----------|-------------|--------|
| [spec-comments-feature.md](./spec-comments-feature.md) | Human-agent collaboration via discussion threads | 📝 DESIGN |

### 📚 Reference Documentation

| Document | Description |
|----------|-------------|
| **[COMPREHENSIVE_STATUS.md](./COMPREHENSIVE_STATUS.md)** | **📊 COMPLETE STATUS**: Full implementation status including frontend audit (2025-01-14) |
| [skill-to-api-flow.md](./skill-to-api-flow.md) | Complete trace of both ticket creation paths |
| [phase-data-flow.md](./phase-data-flow.md) | What data is saved at each phase |
| [implementation-gaps.md](./implementation-gaps.md) | Historical: Original gaps analysis (all resolved) |
| [activation-guide.md](./activation-guide.md) | How to activate each workflow path |
| [command-page-integration.md](./command-page-integration.md) | Google-like entry point from command page |

## The Flow (Now Working! ✅)

```
User Idea (Command Page or POST /specs/launch)
    │
    ▼
POST /specs/launch (or POST /specs/{id}/execute)
    │ Creates Spec with user_id
    │ Calls spawn_for_phase()
    │
    ▼
SANDBOX EXECUTION
    │ Daytona sandbox created with SPEC_ID, SPEC_PHASE env vars
    │ claude_sandbox_worker detects spec mode
    │ Calls _run_spec_state_machine()
    │
    ▼
SPEC PHASES (Planning)
    │ EXPLORE → REQUIREMENTS → DESIGN → TASKS
    │
    ▼
SYNC Phase
    │ Creates: SpecRequirement, SpecAcceptanceCriterion, SpecTask
    │ ✅ THEN calls SpecTaskExecutionService.execute_spec_tasks()
    │
    ▼
TICKET/TASK CREATION
    │ Tickets created with user_id (visible on board!)
    │ Tasks created for agents
    │
    ▼
TICKET EXECUTION (Work)
    │ Tickets appear on kanban board
    │ Agents pick up Tasks and execute
    │
    ▼
DONE
```

## Key Insight

**The planning domain (Spec) and execution domain (Ticket/Task) are now connected!**

- `Spec` → `SpecTask` (planning artifacts) ✅ EXISTS
- `SpecTask` → `Ticket` (execution work items) ✅ WIRED via `SpecTaskExecutionService`
- `SandboxEvent.spec_id` → Spec (event tracking) ✅ WIRED

## ⚠️ IMPORTANT: Terminology (Avoid Confusion!)

**There are TWO different "Task" concepts - don't confuse them!**

### Planning Domain (Spec System)

| Entity | Purpose | Created When | Location |
|--------|---------|--------------|----------|
| **Spec** | Top-level specification | User creates via API | `models/spec.py` |
| **SpecRequirement** | EARS-format requirement | SYNC phase | `models/spec.py` |
| **SpecAcceptanceCriterion** | Test criteria for requirement | SYNC phase | `models/spec.py` |
| **SpecTask** | Planning artifact - work breakdown | SYNC phase | `models/spec.py` |

### Execution Domain (Ticket System)

| Entity | Purpose | Created When | Location |
|--------|---------|--------------|----------|
| **Ticket** | Work item on kanban board | `SpecTaskExecutionService` | `models/ticket.py` |
| **Task** | Executable unit for agents | Created with Ticket | `models/task.py` |

### The Naming Collisions

**1. "SpecTask" vs "Task"**
```
❗ "SpecTask" ≠ "Task"

SpecTask = Planning artifact (what needs to be done)
    │
    │ SpecTaskExecutionService converts this to:
    ▼
Task = Execution unit (agent picks this up and does it)
```

**2. "Phase" - Two Different Concepts!**
```
State Machine Phases (Spec planning) - defined in SpecPhase enum:
  EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC → COMPLETE

  Note: COMPLETE is a real phase that calls mark_complete() to set
        spec.status = "completed". It's NOT just the end of SYNC.

Ticket/Task Phases (Kanban workflow):
  PHASE_INITIAL → PHASE_IMPLEMENTATION → PHASE_INTEGRATION → PHASE_REFACTORING
```

These are UNRELATED! State machine phases control the spec planning flow. Ticket phases control where work appears on the kanban board.

**3. "Status" vs "Phase" for Specs**
```
spec.status = "draft" | "executing" | "completed" | "failed"
spec.current_phase = "explore" | "requirements" | "design" | "tasks" | "sync" | "complete"

Status = Overall lifecycle state (is the spec being worked on?)
Phase = Which planning step is currently running
```

### Entity Flow

```
Spec
 │
 ├── SpecRequirement (N)
 │      └── SpecAcceptanceCriterion (N)
 │
 └── SpecTask (N)  ──► converted to ──►  Ticket  ──►  Task
     (planning)                         (kanban)    (agent executes)
```

---

## Related Code

- `omoi_os/workers/spec_state_machine.py` - Multi-phase state machine
- `omoi_os/workers/claude_sandbox_worker.py` - Sandbox worker with state machine integration
- `omoi_os/services/daytona_spawner.py` - Sandbox spawning (including `spawn_for_phase`)
- `omoi_os/services/spec_task_execution.py` - **Bridge**: Converts SpecTask → Ticket/Task
- `omoi_os/api/routes/specs.py` - Spec CRUD and execution endpoints
- `omoi_os/sandbox_skills/spec-driven-dev/SKILL.md` - Agent prompt for spec-driven work
