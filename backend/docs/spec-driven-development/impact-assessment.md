# Impact Assessment - How Fucked Are We?

**Created**: 2025-01-11
**Status**: GOOD NEWS / BAD NEWS
**Purpose**: Assess damage and what needs to be fixed

---

## TL;DR: NOT AS FUCKED AS WE THOUGHT

The bridge **ALREADY EXISTS** - it's just not wired up automatically!

---

## What We Found

### The Missing Link EXISTS

There's a service at `omoi_os/services/spec_task_execution.py` called `SpecTaskExecutionService` that does EXACTLY what we thought was missing:

```python
class SpecTaskExecutionService:
    """Service for converting and executing SpecTasks via sandbox system.

    This service:
    1. Creates a bridging Ticket for a Spec (if not exists)
    2. Converts pending SpecTasks to executable Tasks
    3. Tasks are then picked up by TaskQueueService and executed via Daytona
    4. Listens for Task completion events to update SpecTask status
    """
```

### There's an API Endpoint

```
POST /api/v1/specs/{spec_id}/execute-tasks
```

This endpoint:
1. Calls `SpecTaskExecutionService.execute_spec_tasks()`
2. Creates bridging Ticket
3. Converts SpecTask → Task
4. Tasks get picked up by orchestrator

### The ACTUAL Gap

The problem is simpler than we thought:

```
State Machine:
    EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC → COMPLETE
                                                │
                                                ▼
                                           (SYNC creates SpecTask records)
                                                │
                                                ▼
                                           COMPLETE (marks spec done)
                                                │
                                                ▼
                                           DEAD END


What SHOULD happen:
    EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC → EXECUTE → COMPLETE
                                                │         │
                                                ▼         ▼
                                           (SYNC)  (Execute tasks!)
                                                         │
                                                         ▼
                                                POST /execute-tasks
                                                         │
                                                         ▼
                                                SpecTaskExecutionService
                                                         │
                                                         ▼
                                                Creates Tickets + Tasks
                                                         │
                                                         ▼
                                                Orchestrator picks up
```

---

## What's ACTUALLY Working

### ✅ WORKING: Spec State Machine (Phases 1-5)

- EXPLORE phase: Works, explores codebase
- REQUIREMENTS phase: Works, generates EARS requirements
- DESIGN phase: Works, generates architecture
- TASKS phase: Works, generates task breakdown
- SYNC phase: Works, creates SpecRequirement + SpecAcceptanceCriterion + SpecTask records

### ✅ WORKING: Ticket → Task → Agent Execution

- Tickets created via API/command page get Tasks created
- TaskQueueService picks up Tasks
- OrchestratorWorker spawns Daytona sandboxes
- Agents execute tasks

### ✅ WORKING: SpecTask → Ticket/Task Bridge (when called!)

- `POST /specs/{id}/execute-tasks` endpoint exists
- `SpecTaskExecutionService` converts SpecTask → Task
- Completion events update SpecTask status

### ✅ WORKING: UI for Spec Detail

- Shows requirements, design, tasks tabs
- Polls execution status
- Shows progress metrics

---

## What's NOT Working (The Actual Gaps)

### ❌ GAP 1: State Machine Doesn't Auto-Execute

**Problem**: After SYNC phase completes, the state machine marks the spec as "completed" without actually executing the tasks.

**The Fix**: Either:
- Add an EXECUTE phase after SYNC
- Have SYNC phase call `SpecTaskExecutionService.execute_spec_tasks()`
- Require manual "Start Execution" button in UI

### ❌ GAP 2: COMPLETE Means "Planning Done" Not "Execution Done"

**Problem**: `spec.status = "completed"` gets set after SYNC, but that just means planning is done - execution hasn't started!

**The Fix**: Rename statuses:
- `planning_complete` - State machine done
- `executing` - Tasks running
- `completed` - All tasks done

### ❌ GAP 3: No Ticket.spec_id Foreign Key

**Problem**: Tickets created by SpecTaskExecutionService store spec_id in `context` JSON, not as a proper FK.

**The Fix**: Add `spec_id` column to Ticket model for proper tracking.

### ❌ GAP 4: Sandbox Execution Bug (Still Valid)

**Problem**: `POST /specs/{id}/execute` runs state machine in API process, not sandbox.

**The Fix**: Call `spawn_for_phase()` instead.

### ❌ GAP 5: No Event Reporting (Still Valid)

**Problem**: State machine doesn't report events for real-time UI.

**The Fix**: Pass EventReporter to state machine.

---

## Severity Assessment

| Gap | Severity | Effort to Fix |
|-----|----------|---------------|
| State machine doesn't auto-execute | **HIGH** | LOW - Just add one call |
| Status naming confusion | MEDIUM | LOW - Rename |
| No Ticket.spec_id FK | LOW | LOW - Add column + migration |
| Sandbox execution bug | **CRITICAL** | MEDIUM - Already documented |
| No event reporting | MEDIUM | MEDIUM - Already documented |

---

## The Good News

1. **No rewrite needed** - All the pieces exist
2. **Bridge service is done** - SpecTaskExecutionService is fully implemented
3. **API endpoints exist** - `/execute-tasks`, `/execution-status`
4. **Ticket/Task execution works** - Independently tested and working

---

## The Bad News

1. **The pieces aren't connected** - State machine doesn't call the bridge
2. **Status naming is confusing** - "completed" means two different things
3. **Still have sandbox execution bug** - Could damage backend codebase
4. **Still have no real-time updates** - UI has to poll

---

## Recommended Fix Priority

### Priority 1: Wire Up the Bridge (1 hour)

Add to `spec_sync.py` or create new EXECUTE phase:

```python
# After SYNC phase creates SpecTask records:
from omoi_os.services.spec_task_execution import SpecTaskExecutionService

service = SpecTaskExecutionService(db=db, event_bus=event_bus)
result = await service.execute_spec_tasks(spec_id=spec.id)
```

### Priority 2: Fix Status Naming (30 min)

- `draft` → Initial state
- `executing_planning` → State machine running
- `planning_complete` → State machine done, SpecTasks created
- `executing_tasks` → Tasks running via orchestrator
- `completed` → All tasks done

### Priority 3: Fix Sandbox Execution (1 hour)

Already documented in `sandbox-execution.md`.

### Priority 4: Add Event Reporting (2 hours)

Already documented in `ui-and-events.md`.

---

## Conclusion

**We're not fucked.**

The system is 90% complete. The bridge exists and works - it's just not automatically called by the state machine. This is a wiring issue, not a fundamental design flaw.

The state machine design is sound:
- EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC all work
- SYNC creates the SpecTask records needed for execution
- SpecTaskExecutionService converts SpecTask → Task → Agent execution

We just need to:
1. Call `SpecTaskExecutionService.execute_spec_tasks()` after SYNC
2. Fix the status naming to avoid confusion
3. Fix the sandbox execution bug (already documented)
4. Add event reporting for real-time UI (already documented)

**Estimated total fix time: 4-6 hours of coding** (after documentation review)
