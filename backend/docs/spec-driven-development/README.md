# Spec-Driven Development Documentation

This directory contains documentation for the spec-driven development workflow system.

## Overview

Spec-driven development allows users to go from **idea → spec → tickets → automated execution**.

## ⚠️ GAPS IDENTIFIED (Not as bad as we thought!)

1. **SpecTask → Ticket Gap**: ~~SpecTasks never become Tickets~~ → **Bridge EXISTS but not wired!** See [impact-assessment.md](./impact-assessment.md)
2. **Sandbox Execution Bug**: `/execute` endpoint runs in API process, not sandbox. See [sandbox-execution.md](./sandbox-execution.md)
3. **No Event Reporting**: State machine doesn't report events for real-time UI. See [ui-and-events.md](./ui-and-events.md)
4. **⚠️ Ticket `user_id` Not Set**: Tickets without `user_id` won't show on **board view** (but WILL show in **ticket list**). See [ticket-field-gap.md](./ticket-field-gap.md)

**TL;DR**: The `SpecTaskExecutionService` at `omoi_os/services/spec_task_execution.py` has the bridge fully implemented. The state machine just doesn't call it!

**Visibility Clarification**:
- **Ticket List API** (`/api/v1/tickets`): Filters by `project_id` only → Tickets visible ✅
- **Board View API** (`/api/v1/board/view`): Filters by `project_id` AND `user_id` → Tickets without `user_id` invisible ⚠️

This may be intentional (board shows "my tickets", list shows "all project tickets").

## Documents

| Document | Description |
|----------|-------------|
| [impact-assessment.md](./impact-assessment.md) | **START HERE**: How fucked are we? (Not very!) |
| [ticket-field-gap.md](./ticket-field-gap.md) | **🔴 CRITICAL**: Tickets invisible on board - missing `user_id` |
| [skill-to-api-flow.md](./skill-to-api-flow.md) | **🔴 COMPLETE TRACE**: Both ticket creation paths and the `user_id` gap |
| [architecture.md](./architecture.md) | Complete system architecture and flow tracing |
| [phase-data-flow.md](./phase-data-flow.md) | What data is saved at each phase |
| [data-flow-gap.md](./data-flow-gap.md) | SpecTask → Ticket gap (bridge exists!) |
| [implementation-gaps.md](./implementation-gaps.md) | Current gaps and what needs to be built |
| [activation-guide.md](./activation-guide.md) | How to activate each workflow path |
| [command-page-integration.md](./command-page-integration.md) | Google-like entry point from command page |
| [sandbox-execution.md](./sandbox-execution.md) | **CRITICAL**: Sandbox vs API process execution issue |
| [ui-and-events.md](./ui-and-events.md) | Event reporting gap and UI improvements |

## The Correct Flow (What Should Happen)

```
User Idea (Command Page)
    │
    ▼
SPEC PHASES (Planning)
    │ EXPLORE → REQUIREMENTS → DESIGN → TASKS
    │
    ▼
SYNC Phase
    │ Creates: SpecRequirement, SpecAcceptanceCriterion, SpecTask
    │ MISSING: Should also create Ticket + Task records!
    │
    ▼
TICKET EXECUTION (Work)
    │ Tickets appear on kanban board
    │ Agents pick up Tasks and execute
    │
    ▼
FINAL SYNC
    │ When all tickets complete → Mark spec complete
    │
    ▼
DONE
```

## Current State (What Actually Happens)

```
SPEC PHASES
    │ EXPLORE → REQUIREMENTS → DESIGN → TASKS
    │
    ▼
SYNC Phase
    │ Creates: SpecRequirement, SpecAcceptanceCriterion, SpecTask
    │
    ▼
COMPLETE Phase
    │ Marks spec "completed"
    │
    ▼
DEAD END - SpecTasks never become Tickets!
    - Nothing on kanban board
    - No agents assigned
    - Work never happens
```

## Key Insight

**The planning domain (Spec) and execution domain (Ticket/Task) are NOT connected!**

- `Spec` → `SpecTask` (planning artifacts) ✅ EXISTS
- `SpecTask` → `Ticket` (execution work items) ❌ MISSING
- `Ticket` → `Spec` (completion tracking) ❌ MISSING

## Related Code

- `omoi_os/workers/spec_state_machine.py` - Multi-phase state machine
- `omoi_os/workers/claude_sandbox_worker.py` - Sandbox worker with state machine integration
- `omoi_os/services/daytona_spawner.py` - Sandbox spawning (including `spawn_for_phase`)
- `omoi_os/api/routes/specs.py` - Spec CRUD and execution endpoints
- `omoi_os/sandbox_skills/spec-driven-dev/SKILL.md` - Agent prompt for spec-driven work
