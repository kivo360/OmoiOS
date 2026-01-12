# Implementation Gaps - Spec-Driven Development

**Created**: 2025-01-11
**Status**: Analysis
**Purpose**: Document what's missing to enable direct idea → spec → execution flow

## The Core Problem

**User wants**: Enter an idea in UI → System creates spec → State machine runs automatically

**What exists**: Two separate paths that don't connect:
1. Prompt injection tells agent to manually create specs
2. State machine requires a pre-existing spec_id

**The gap**: No automatic bridge from "user idea" to "running state machine"

---

## Current State

### What the Frontend Sends

```typescript
// frontend/lib/api/types.ts
export interface TicketCreate {
  title: string
  description?: string
  project_id?: string
  workflow_mode?: "quick" | "spec_driven"  // EXISTS
  generate_spec?: boolean                   // EXISTS but unused
  auto_spawn_sandbox?: boolean              // EXISTS but unused
  // ...
}
```

### What the Backend Does

```python
# tickets.py:460-464
if workflow_mode_for_task == "spec_driven":
    execution_config = {
        "require_spec_skill": True,        # Sets prompt injection
        "selected_skill": "spec-driven-dev",
    }
# DOES NOT:
# - Create a Spec record
# - Pass spec_id to the agent
# - Trigger state machine
```

---

## Gap Analysis

### Gap 1: No Direct Spec Creation from UI

**Current**: User must either:
- Create ticket → agent manually creates spec (via prompt)
- Use API directly: `POST /api/v1/specs` then `POST /api/v1/specs/{id}/execute`

**Needed**: UI entry point that:
- Takes idea (title + description)
- Creates Spec record immediately
- Optionally triggers state machine

### Gap 2: No Link Between Ticket and Spec

**Current**:
- `Ticket` model has no `spec_id` field
- No way to associate a ticket with its generated spec
- Tickets clutter kanban board even for spec work

**Needed**: Either:
- Add `spec_id` FK to Ticket model
- OR bypass tickets entirely for spec-driven work

### Gap 3: State Machine Requires Pre-Existing Spec

**Current**:
- `SpecStateMachine` needs `spec_id` to run
- `spawn_for_phase()` needs `spec_id`
- No automatic spec creation when state machine is triggered

**Needed**:
- Auto-create spec from user input
- Pass spec_id through the execution chain

### Gap 4: Frontend Has No Spec-First Entry Point

**Current**:
- Command page creates tickets
- Spec list page shows existing specs
- No "Create Spec and Run" flow

**Needed**:
- New UI component or page for spec-driven entry
- Could be as simple as a dialog that calls `/specs` + `/specs/{id}/execute`

---

## Proposed Solutions

### Option A: Bypass Tickets Entirely (Recommended)

Create a new "Spec Launcher" that skips tickets:

```
┌─────────────────────────────────────────────────────────┐
│                    Spec Launcher UI                     │
├─────────────────────────────────────────────────────────┤
│  Title: [_________________________________]             │
│  Description: [_____________________________]           │
│               [_____________________________]           │
│               [_____________________________]           │
│                                                         │
│  Project: [dropdown]                                    │
│                                                         │
│  [x] Auto-run state machine                            │
│                                                         │
│              [Cancel]  [Create & Execute]               │
└─────────────────────────────────────────────────────────┘
```

Flow:
```
1. User fills form
2. Frontend calls: POST /api/v1/specs
   Body: { title, description, project_id }
3. Backend creates Spec record
4. If auto-run checked:
   Frontend calls: POST /api/v1/specs/{id}/execute
5. State machine runs in background
6. User redirected to spec detail page to watch progress
```

**Pros**:
- No ticket clutter
- Uses existing endpoints
- Minimal backend changes
- State machine handles everything

**Cons**:
- New UI component needed
- No kanban visibility (might be desired)

### Option B: Auto-Spec on Ticket Creation

Modify ticket creation to auto-create spec:

```python
# tickets.py (modified)
if workflow_mode_for_task == "spec_driven":
    # Create spec from ticket
    spec = Spec(
        title=ticket.title,
        description=ticket.description,
        project_id=ticket.project_id,
        status="draft",
    )
    session.add(spec)
    await session.flush()  # Get spec.id

    # Link ticket to spec
    ticket.spec_id = spec.id

    # Pass spec_id to execution
    execution_config = {
        "require_spec_skill": True,
        "spec_id": spec.id,  # NEW
        "auto_execute": True,  # NEW
    }
```

Then modify spawner to trigger state machine:
```python
# orchestrator_worker.py or daytona_spawner.py
if execution_config.get("spec_id") and execution_config.get("auto_execute"):
    await spawner.spawn_for_phase(
        spec_id=execution_config["spec_id"],
        phase="explore",
        ...
    )
```

**Pros**:
- Works with existing command page
- Ticket provides audit trail
- Kanban shows spec-driven work

**Cons**:
- Requires migration (add spec_id to tickets)
- Still creates tickets (may not be desired)
- More complex changes

### Option C: Hybrid - New Endpoint

Create a dedicated endpoint:

```python
# specs.py (new endpoint)
@router.post("/launch", response_model=SpecLaunchResponse)
async def launch_spec(
    request: SpecLaunchRequest,  # title, description, project_id
    db: DatabaseService = Depends(get_db_service),
):
    """Create spec and immediately start execution."""
    # 1. Create spec
    spec = await create_spec(db, request)

    # 2. Start state machine
    asyncio.create_task(run_spec_state_machine(spec.id, ...))

    return SpecLaunchResponse(
        spec_id=spec.id,
        status="started",
        phase="explore",
    )
```

**Pros**:
- Single API call for complete flow
- Clean separation from tickets
- Easy to add to any UI

**Cons**:
- New endpoint to maintain
- Slightly redundant with existing endpoints

---

## Recommended Implementation Order

### Phase 1: Quick Win (Option C)
1. Add `POST /api/v1/specs/launch` endpoint
2. Frontend adds "Launch Spec" button/dialog
3. Calls new endpoint → redirects to spec detail

### Phase 2: Full Integration (Option A)
1. Build dedicated Spec Launcher page
2. Add real-time progress tracking
3. Add approval gates in UI

### Phase 3: Optional (Option B)
1. Add `spec_id` to Ticket model (if ticket tracking desired)
2. Auto-link tickets to specs
3. Update kanban to show spec status

---

## Files to Modify

### For Option C (Quick Win)

| File | Change |
|------|--------|
| `omoi_os/api/routes/specs.py` | Add `POST /launch` endpoint |
| `frontend/lib/api/specs.ts` | Add `launchSpec()` function |
| `frontend/hooks/useSpecs.ts` | Add `useLaunchSpec()` hook |
| `frontend/components/` | Add LaunchSpecDialog component |

### For Option B (Full Integration)

| File | Change |
|------|--------|
| `omoi_os/models/ticket.py` | Add `spec_id` FK |
| `migrations/` | New migration for spec_id |
| `omoi_os/api/routes/tickets.py` | Auto-create spec on spec_driven mode |
| `omoi_os/workers/orchestrator_worker.py` | Trigger state machine if spec_id present |

---

## Open Questions

1. **Should specs show on kanban?** Or separate view entirely?
2. **Approval gates**: UI for approving between phases?
3. **Multiple specs per project**: How to organize?
4. **Spec templates**: Pre-defined spec structures?
5. **Version control**: Export specs to git?
