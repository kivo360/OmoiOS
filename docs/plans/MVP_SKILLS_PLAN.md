# MVP Skills Implementation Plan

**Created**: 2025-12-26
**Status**: Active - Start Tomorrow
**Purpose**: Simplify MVP by using Claude Agent skills to orchestrate ticket/task flow instead of complex supervision code

---

## Context & Decision

### What We're Deferring
- Discovery spawning (`discovery.py:record_discovery_and_branch`)
- Diagnostic auto-recovery (`discovery.py:spawn_diagnostic_recovery`)
- Guardian auto-steering interventions
- Adaptive monitoring loop
- Memory-based learning patterns

### What We're Disabling
- **`monitoring_worker.py`** - The entire monitoring worker with its 6 concurrent loops:
  - Heartbeat monitoring (agent health)
  - Diagnostic monitoring (stuck workflows)
  - Anomaly monitoring (agent anomalies)
  - Blocking detection (stuck tickets)
  - Approval timeout (ticket approvals)
  - Intelligent Monitoring Loop (Guardian + Conductor)

  **Why:** Too complex for MVP. These features are half-baked and add unnecessary complexity.
  The orchestrator worker (`orchestrator_worker.py`) handles what we actually need.

### Why
These "interconnected workflow" features are cool but half-baked. They consume development time without delivering core MVP value. We can add them back once the foundation is solid.

### MVP Core Flow
```
User describes feature → Skill 1 creates tickets/tasks via API →
Orchestrator auto-assigns tasks to sandboxes → Work executes →
Sandbox auto-reports completion → Ticket auto-transitions through Kanban → Done
```

**Key Simplification:** The orchestrator worker already handles automatic task→sandbox assignment!

---

## Workflow Progression Strategy

### The Gap: Who Moves Tickets Through Kanban?

After work completes in a sandbox, the ticket needs to progress through phases:
`backlog → analyzing → building → building-done → testing → done`

**Decision: Option 2 - Sandbox Auto-Reports Completion**

When a sandbox completes its task, it calls the API to auto-transition the ticket. This keeps it simple without needing a separate orchestration skill.

### How It Works (Grounded to Existing Architecture)

**Reference:** `docs/design/sandbox-agents/04_communication_patterns.md`

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SANDBOX WORKFLOW COMPLETION FLOW                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Sandbox completes task work                                             │
│     └─ Agent finishes implementing feature/fix                              │
│                                                                             │
│  2. Worker script calls result submission                                   │
│     POST /api/v1/sandbox/task/{task_id}/results                             │
│     { status: "completed", summary: "...", files_changed: [...] }           │
│                                                                             │
│  3. Backend processes result                                                │
│     a. Mark task as "completed"                                             │
│     b. Check if ALL tasks for ticket's current phase are done               │
│     c. If yes → Call auto-transition                                        │
│                                                                             │
│  4. Auto-transition ticket to next phase                                    │
│     POST /api/v1/board/auto-transition/{ticket_id}                          │
│     Ticket moves: building → building-done → testing                        │
│                                                                             │
│  5. Event published for frontend visibility                                 │
│     event_bus.publish(TICKET_TRANSITIONED, {...})                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Existing Infrastructure (Already Built!)

**Reference:** `docs/design/sandbox-agents/IMPLEMENTATION_COMPLETE_STATUS.md`

| Component | Status | Location |
|-----------|--------|----------|
| Task result submission | DONE | `sandbox.py` - POST `/task/{task_id}/results` |
| Auto-transition endpoint | DONE | `board.py` - POST `/auto-transition/{ticket_id}` |
| Event bus publishing | DONE | `EventBusService` |
| Worker script result reporting | DONE | `claude_sandbox_worker.py:submit_results()` |

### What We Need to Wire Up

The pieces exist but may not be fully connected. Verify/implement:

1. **Worker → Result API**: Worker calls `POST /api/v1/sandbox/task/{task_id}/results`
2. **Result API → Task Status**: Marks task as `completed`
3. **Task Completion → Ticket Check**: Checks if phase tasks are all done
4. **Phase Complete → Auto-Transition**: Calls `POST /api/v1/board/auto-transition/{ticket_id}`

### Sandbox Communication Pattern (Reference)

**From:** `docs/design/sandbox-agents/04_communication_patterns.md`

```python
# Worker script pattern (already implemented in claude_sandbox_worker.py)
client = SandboxClient()

# ... do work ...

# Submit results - this triggers the chain
client.submit_results(
      status="completed",
      summary="Implemented the feature",
      files_changed=[{"path": "src/foo.ts", "action": "modified"}],
)
```

### API Endpoints for Workflow Progression

All of these EXIST (per API inventory above):

| Endpoint | Purpose | Status |
|----------|---------|--------|
| `POST /api/v1/sandbox/task/{id}/results` | Worker submits completion | DONE |
| `POST /api/v1/board/auto-transition/{ticket_id}` | Move ticket to next phase | DONE |
| `POST /api/v1/tickets/{id}/progress` | Alternative: explicit progress call | DONE |
| `GET /api/v1/board/view` | Frontend sees updated board | DONE |

### No Third Skill Needed!

The workflow progression is handled by:
1. **Sandbox worker** calls result API when done
2. **Backend service** checks task completion and triggers ticket transition
3. **Event bus** notifies frontend of changes

This is infrastructure, not a skill. The skill-based approach is for user-initiated actions.

---

## API Endpoint Inventory (from OpenAPI spec)

### Tickets API - ALL COMPLETE
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/tickets` | GET | DONE | List tickets with filters |
| `/api/v1/tickets` | POST | DONE | Create ticket (with dedup check, approval gate) |
| `/api/v1/tickets/{ticket_id}` | GET | DONE | Get single ticket |
| `/api/v1/tickets/{ticket_id}/transition` | POST | DONE | Transition ticket status |
| `/api/v1/tickets/{ticket_id}/progress` | POST | DONE | Auto-progress to next phase |
| `/api/v1/tickets/{ticket_id}/block` | POST | DONE | Mark ticket blocked |
| `/api/v1/tickets/{ticket_id}/unblock` | POST | DONE | Unblock ticket |
| `/api/v1/tickets/{ticket_id}/regress` | POST | DONE | Regress to previous phase |
| `/api/v1/tickets/{ticket_id}/context` | GET | DONE | Get aggregated context |
| `/api/v1/tickets/{ticket_id}/update-context` | POST | DONE | Update context |
| `/api/v1/tickets/approve` | POST | DONE | Approve pending ticket |
| `/api/v1/tickets/reject` | POST | DONE | Reject pending ticket |
| `/api/v1/tickets/check-duplicates` | POST | DONE | Check for duplicate tickets |
| `/api/v1/tickets/detect-blocking` | POST | DONE | Detect blocked tickets |
| `/api/v1/tickets/pending-review-count` | GET | DONE | Count pending tickets |
| `/api/v1/tickets/approval-status` | GET | DONE | Get approval status |

### Tasks API - ALL COMPLETE
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/tasks` | GET | DONE | List tasks with filters (status, phase_id, has_sandbox) |
| `/api/v1/tasks/{task_id}` | GET | DONE | Get single task |
| `/api/v1/tasks/{task_id}/dependencies` | GET | DONE | Get task dependencies |
| `/api/v1/tasks/{task_id}/dependencies` | POST | DONE | Add dependencies |
| `/api/v1/tasks/{task_id}/dependencies` | PUT | DONE | Set/replace dependencies |
| `/api/v1/tasks/{task_id}/dependencies/{id}` | DELETE | DONE | Remove dependency |
| `/api/v1/tasks/{task_id}/check-circular` | POST | DONE | Check for circular deps |
| `/api/v1/tasks/{task_id}/cancel` | POST | DONE | Cancel running task |
| `/api/v1/tasks/{task_id}/timeout-status` | GET | DONE | Get timeout status |
| `/api/v1/tasks/{task_id}/set-timeout` | POST | DONE | Set task timeout |
| `/api/v1/tasks/{task_id}/generate-title` | POST | DONE | Generate title via LLM |
| `/api/v1/tasks/{task_id}/register-conversation` | POST | DONE | Register sandbox conversation |
| `/api/v1/tasks/timed-out` | GET | DONE | List timed-out tasks |
| `/api/v1/tasks/cancellable` | GET | DONE | List cancellable tasks |
| `/api/v1/tasks/cleanup-timed-out` | POST | DONE | Mark timed-out as failed |
| `/api/v1/tasks/generate-titles` | POST | DONE | Batch generate titles |

### Specs API - ALL COMPLETE
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/specs` | POST | DONE | Create spec |
| `/api/v1/specs/project/{project_id}` | GET | DONE | List project specs |
| `/api/v1/specs/{spec_id}` | GET | DONE | Get spec |
| `/api/v1/specs/{spec_id}` | PATCH | DONE | Update spec |
| `/api/v1/specs/{spec_id}` | DELETE | DONE | Delete spec |
| `/api/v1/specs/{spec_id}/requirements` | POST | DONE | Add requirement |
| `/api/v1/specs/{spec_id}/requirements/{req_id}` | PATCH | DONE | Update requirement |
| `/api/v1/specs/{spec_id}/requirements/{req_id}` | DELETE | DONE | Delete requirement |
| `/api/v1/specs/{spec_id}/requirements/{req_id}/criteria` | POST | DONE | Add acceptance criterion |
| `/api/v1/specs/{spec_id}/requirements/{req_id}/criteria/{id}` | PATCH | DONE | Update criterion |
| `/api/v1/specs/{spec_id}/design` | PUT | DONE | Update design section |
| `/api/v1/specs/{spec_id}/approve-requirements` | POST | DONE | Approve requirements |
| `/api/v1/specs/{spec_id}/approve-design` | POST | DONE | Approve design |
| `/api/v1/specs/{spec_id}/tasks` | POST | DONE | Add task to spec |
| `/api/v1/specs/{spec_id}/tasks` | GET | DONE | List spec tasks |

### Board/Kanban API - ALL COMPLETE
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/board/view` | GET | DONE | Get full board view |
| `/api/v1/board/move` | POST | DONE | Move ticket between columns |
| `/api/v1/board/column/{phase_id}` | GET | DONE | Get specific column |
| `/api/v1/board/stats` | GET | DONE | Get column statistics |
| `/api/v1/board/wip-violations` | GET | DONE | Check WIP limit violations |
| `/api/v1/board/auto-transition/{ticket_id}` | POST | DONE | Auto-transition ticket |

### Sandboxes API - PARTIAL
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/sandboxes/health` | GET | DONE | Get sandbox health status |
| `/api/v1/sandboxes/{sandbox_id}/events` | GET | DONE | Get sandbox events |
| `/api/v1/sandboxes/{sandbox_id}/events` | POST | DONE | Post sandbox event |
| `/api/v1/sandboxes/{sandbox_id}/messages` | GET | DONE | Get sandbox messages |
| `/api/v1/sandboxes/{sandbox_id}/messages` | POST | DONE | Post message to sandbox |
| `/api/v1/sandboxes/{sandbox_id}/trajectory` | GET | DONE | Get sandbox trajectory |
| `/api/v1/sandboxes/{sandbox_id}/task` | GET | DONE | Get task for sandbox |
| `GET /api/v1/sandboxes` | - | **MISSING** | List all sandboxes |
| `POST /api/v1/sandboxes` | - | **MISSING** | Spawn new sandbox |
| `DELETE /api/v1/sandboxes/{id}` | - | **MISSING** | Stop/delete sandbox |
| `GET /api/v1/sandboxes/capacity` | - | **MISSING** | Check available capacity |

### Agents API - TO DEPRECATE (per user request)
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/agents/*` | ALL | DEPRECATE | Agent management endpoints |

### Other Relevant APIs - ALL COMPLETE
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/projects` | CRUD | DONE | Project management |
| `/api/v1/github/*` | ALL | DONE | GitHub integration |
| `/api/v1/graph/dependency-graph/*` | GET | DONE | Dependency graph visualization |
| `/api/v1/phases/*` | ALL | DONE | Phase gate management |
| `/api/v1/results/*` | ALL | DONE | Result submission |

---

## Skills to Build (MVP Simplified!)

**Original Plan:** 2 Skills
**Updated Plan:** 1 Skill + Existing Orchestrator

The orchestrator worker (`backend/omoi_os/workers/orchestrator_worker.py`) already handles automatic task→sandbox assignment, so we only need to build one skill!

### Skill 1: `spec-to-tickets` (Extend existing `spec-driven-dev`)

**Purpose:** Takes spec/feature description → Creates tickets + tasks via API

**Input:** Feature description from command palette or panel

**EXISTING SKILL FOUND:** `.claude/skills/spec-driven-dev/`

The `spec-driven-dev` skill already implements the full 6-phase workflow:
```
1. Understand Feature → 2. Research (DeepWiki/Context7) → 3. Requirements Doc
                                                                    ↓
6. Tasks (Children) ← 5. Tickets (Work Items) ← 4. Design Doc
```

**Current behavior:** Writes to `.omoi_os/` files (markdown)
**Needed behavior:** Call API endpoints instead

**What needs to change:**
1. Instead of writing `.omoi_os/tickets/TKT-001.md` → call `POST /api/v1/tickets`
2. Instead of writing `.omoi_os/tasks/TSK-001.md` → call `POST /api/v1/specs/{id}/tasks`
3. Keep the same templates/logic, just change the output target

**Existing skill assets:**
- `SKILL.md` - Full workflow documentation
- `references/requirements_template.md` - Requirements format
- `references/design_template.md` - Design doc format
- `references/ticket_template.md` - Ticket structure
- `references/task_template.md` - Task structure
- `references/claude_sdk_patterns.md` - Agent SDK patterns
- `scripts/init_feature.py` - Directory setup
- `scripts/generate_ids.py` - ID generation
- `scripts/validate_specs.py` - Validation

**API Endpoints Needed:**
- [x] `POST /api/v1/tickets` - Create ticket (EXISTS)
- [x] `POST /api/v1/specs` - Create spec (EXISTS)
- [x] `POST /api/v1/specs/{spec_id}/tasks` - Add tasks (EXISTS)
- [x] `POST /api/v1/specs/{spec_id}/requirements` - Add requirements (EXISTS)
- [x] `GET /api/v1/board/view` - Verify ticket appears (EXISTS)

**Prototype Steps:**
1. [x] Review existing spec templates in `.claude/skills/spec-driven-dev/` (DONE - skill exists!)
2. [ ] Map ticket_template.md fields → TicketCreate API schema
3. [ ] Map task_template.md fields → Task API schema
4. [ ] Test API: Create ticket via curl/httpie
5. [ ] Test API: Add tasks to spec via curl/httpie
6. [ ] Extend skill OR create wrapper that calls API instead of writing files
7. [ ] Verify tickets/tasks appear in Kanban UI

---

### ~~Skill 2: `queue-assignment`~~ → **NOT NEEDED FOR MVP!**

**Status:** ✅ ALREADY IMPLEMENTED by `orchestrator_worker.py`

**Discovery:** The background orchestrator loop already handles automatic task→sandbox assignment!

**How It Works (Already Built):**

`backend/omoi_os/workers/orchestrator_worker.py` runs 4 concurrent loops:
1. **Heartbeat Loop** - Agent heartbeat every 30s
2. **Orchestrator Loop** - Polls pending tasks → spawns sandboxes → assigns tasks
3. **Idle Sandbox Check** - Terminates idle sandboxes
4. **Stale Cleanup** - Cleans up stale sandboxes

**The Orchestrator Loop Does Exactly What Skill 2 Was Designed For:**

```python
# From orchestrator_worker.py:orchestrator_loop()

# 1. Get next pending task
task = queue.get_next_task(phase_id=None)

# 2. Spawn sandbox for task
sandbox_id = await daytona_spawner.spawn_for_task(
    task_id=task_id,
    agent_id=agent_id,
    ...
)

# 3. Update task with sandbox info
queue.assign_task(task.id, agent_id)
task_obj.sandbox_id = sandbox_id
```

**Why This Is Better for MVP:**
- ✅ **Automatic** - No user intervention needed
- ✅ **Already tested** - Been working in production
- ✅ **Simpler** - One less skill to build
- ✅ **Consistent** - Same behavior every time

**Manual Control (Future Enhancement):**
If we later want manual user-triggered assignment:
- Add `POST /api/v1/sandboxes/spawn-for-task/{task_id}` endpoint
- Create a simple `queue-assignment` skill that calls it
- But this is NOT needed for MVP

---

## Existing Code to Leverage

### Spec-Driven Skill (ALREADY EXISTS!)
Location: `.claude/skills/spec-driven-dev/`
- **SKILL.md** - Full 6-phase workflow (Understand → Research → Requirements → Design → Tickets → Tasks)
- **references/** - Templates for requirements, design, tickets, tasks
- **scripts/** - ID generation, validation, initialization
- **Status:** Just needs API integration instead of file writes

### API Routes (ALL EXIST)
Location: `backend/omoi_os/api/routes/`
- `tickets.py` - Ticket CRUD - COMPLETE
- `tasks.py` - Task CRUD - COMPLETE
- `specs.py` - Spec management - COMPLETE
- `board.py` - Kanban operations - COMPLETE

### Services (ALL EXIST)
- `ticket_workflow.py` - Ticket state machine
- `task_queue.py` - Task assignment logic
- `board.py` - Kanban board operations
- `phase_gate.py` - Phase transition validation

### Sandbox Management (COMPLETE FOR MVP!)
- `workspace_manager.py` - Workspace/sandbox creation - EXISTS
- `daytona_spawner.py` - Sandbox spawning - EXISTS
- `orchestrator_worker.py` - **Automatic task→sandbox assignment - EXISTS!**
  - Polls pending tasks, spawns sandboxes, assigns tasks automatically
  - No additional endpoints needed for MVP
- Sandbox API routes - List/spawn/capacity endpoints optional (for future manual control)

---

## Tomorrow's Checklist

### Morning: Skill 1 Prototype (spec-to-tickets)

- [x] Review existing spec templates (DONE - `.claude/skills/spec-driven-dev/` has full workflow!)
- [x] Verify ticket API endpoints work (they exist per OpenAPI)
- [x] Verify spec API endpoints work (they exist per OpenAPI)
- [ ] Read `references/ticket_template.md` → map fields to TicketCreate schema
- [ ] Read `references/task_template.md` → map fields to Task schema
- [ ] Test manually: `curl -X POST /api/v1/tickets ...`
- [ ] Test manually: `curl -X POST /api/v1/specs/{id}/tasks ...`
- [ ] Decide: Extend `spec-driven-dev` skill OR create new wrapper
- [ ] Add API calls to replace file writes
- [x] Verify tickets/tasks appear in Kanban UI

### Afternoon: ~~Skill 2 Prototype~~ → Verify Orchestrator (Already Built!)

**Good news:** The orchestrator already handles automatic task→sandbox assignment!

- [ ] **Verify orchestrator is running:**
  - [ ] Check `orchestrator_worker.py` is started
  - [ ] Verify orchestrator loop is polling for tasks
- [ ] **Test the automatic flow:**
  - [ ] Create a pending task via API
  - [ ] Watch orchestrator pick it up
  - [ ] Verify sandbox spawns for task
  - [ ] Check task status updates in UI
- [ ] **If manual control is needed later:**
  - Document as future enhancement (not MVP blocker)

### End of Day: Workflow Verification

- [ ] Skill 1 (spec-to-tickets) working as prototype
- [ ] Orchestrator automatically assigns tasks (verify existing behavior)
- [ ] Plan UI integration (command palette or panel)
- [ ] **Verify workflow progression chain:**
  - [ ] Worker script calls `POST /api/v1/sandbox/task/{id}/results` on completion
  - [ ] Result API marks task as `completed`
  - [ ] Service checks if all phase tasks are done
  - [ ] If yes, calls `POST /api/v1/board/auto-transition/{ticket_id}`
  - [ ] Ticket moves to next phase automatically
  - [ ] Frontend receives event update

---

## What's Missing (Summary) - SIMPLIFIED!

### Skill 1: spec-to-tickets
**MOSTLY DONE** - Existing `spec-driven-dev` skill has full workflow!
- [x] 6-phase workflow (Understand → Research → Requirements → Design → Tickets → Tasks)
- [x] Templates for all artifact types
- [x] All API endpoints exist
- [ ] Just need to add API calls instead of file writes

### ~~Skill 2: queue-assignment~~ → **NOT NEEDED!**
**ALREADY IMPLEMENTED** by `orchestrator_worker.py`!

The orchestrator loop already:
- ✅ Polls for pending tasks
- ✅ Spawns sandboxes via DaytonaSpawner
- ✅ Assigns tasks to sandboxes
- ✅ Handles idle sandbox termination

**No new endpoints or skills needed for automatic task assignment!**

---

## Success Criteria

**Skill 1 works when:**
- I can describe a feature
- Tickets + tasks appear in Kanban backlog
- Tasks have correct phases and dependencies

**~~Skill 2~~ Orchestrator works when:** (Already implemented!)
- Pending tasks are automatically picked up
- Sandboxes are spawned for tasks
- Status updates visible in UI
- ✅ This should already be working - just verify!

---

## Future (After MVP Stable)

Once these skills work and MVP is released:
1. Re-enable discovery spawning
2. Add Guardian auto-steering
3. Implement adaptive monitoring
4. Add memory-based learning

But NOT until the foundation is solid and tested.

---

## Reference Documents

### Sandbox-Agent Architecture (Grounding Sources)

These docs contain the complete sandbox architecture - use them for implementation details:

| Document | Purpose | Key Sections |
|----------|---------|--------------|
| `docs/design/sandbox-agents/01_architecture.md` | High-level architecture | Sandbox lifecycle state machine, Event types, API endpoints |
| `docs/design/sandbox-agents/04_communication_patterns.md` | HTTP/WS patterns | Worker script patterns, Security model, Rate limiting |
| `docs/design/sandbox-agents/IMPLEMENTATION_COMPLETE_STATUS.md` | What's built | Backend 100%, Frontend 40%, E2E test scripts |

### Key Architecture Points

**Sandbox Lifecycle States** (from `01_architecture.md`):
```
PENDING → CREATING → RUNNING → COMPLETING → COMPLETED → TERMINATED
                         ↓
                      FAILED
```

**Event Types** (sandbox → server → frontend):
- `agent.started`, `agent.thinking`, `agent.message`, `agent.tool_use`, `agent.completed`
- `file.created`, `file.modified`, `file.deleted`
- `command.started`, `command.output`, `command.completed`
- `sandbox.heartbeat`, `sandbox.metrics`

**Worker Script Location**: `backend/omoi_os/workers/claude_sandbox_worker.py` (1428 lines)

**DaytonaSpawnerService**: `backend/omoi_os/services/daytona_spawner.py` (2476 lines)

---

## Notes

- Skills interact with API only (no direct DB access)
- User stays in control (triggers assignments manually)
- Simple sandbox management (count running vs max)
- Can copy patterns from other codebase as needed
- **Agents API marked for deprecation** - use Sandboxes terminology going forward
- **Workflow progression is automatic** - sandbox reports completion → ticket auto-transitions
