# Spec-Driven Development - Implementation Roadmap

**Created**: 2025-01-13
**Status**: COMPREHENSIVE ACTION PLAN
**Purpose**: Consolidated roadmap with exact file locations, code changes, and verification steps

---

## Executive Summary

The spec-driven development workflow is **~80% complete**. The major infrastructure exists, but key pieces are not wired together. This document provides the exact implementation steps needed to complete the system.

### What's Working
- ✅ Sandbox infrastructure (100% complete - see `docs/design/sandbox-agents/IMPLEMENTATION_COMPLETE_STATUS.md`)
- ✅ SpecStateMachine with 5 phases (EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC)
- ✅ SpecTaskExecutionService bridge (`POST /specs/{id}/execute-tasks`)
- ✅ Worker spec mode support (`claude_sandbox_worker.py:4211-4431`)
- ✅ Event callback & message injection (`sandbox.py:365,758,803`)
- ✅ `spawn_for_phase()` method (`daytona_spawner.py:750`)

### What's NOT Working
- ❌ `/specs/{id}/execute` runs in API process, not sandbox
- ❌ State machine doesn't call `SpecTaskExecutionService` after SYNC
- ❌ Spec model has no `user_id` (tickets invisible on board)
- ❌ State machine doesn't emit events (no real-time UI updates)
- ❌ No `/specs/launch` endpoint (command page can't trigger spec flow)

---

## Implementation Phases

### Phase 1: Critical Wiring (Estimated: 2-4 hours)

**Goal**: Make the state machine actually execute tasks after planning.

#### Task 1.1: Wire SpecTaskExecutionService to State Machine

**File**: `backend/omoi_os/workers/spec_state_machine.py` (line 291: `_execute_sync_phase`)

**Change**: After SYNC phase completes successfully, call the task execution service.

```python
# In SpecStateMachine class, modify _execute_sync_phase() at line 291:
# Add this AFTER sync_service.sync() succeeds but BEFORE returning:

from omoi_os.services.spec_task_execution import SpecTaskExecutionService

async def _execute_sync_phase(self, spec: Any) -> PhaseResult:
    """Execute the SYNC phase using SpecSyncService."""
    # ... existing sync logic (lines 291-370) ...

    # After sync_result.success, ADD THIS:
    if sync_result.success:
        # NEW: After syncing, execute the tasks
        try:
            from omoi_os.services.spec_task_execution import SpecTaskExecutionService
            task_service = SpecTaskExecutionService(db=self.db_service, event_bus=self.event_bus)
            execution_result = await task_service.execute_spec_tasks(spec_id=self.spec_id)
            logger.info(f"[SYNC] Task execution initiated: {execution_result}")
        except Exception as e:
            logger.error(f"[SYNC] Task execution failed: {e}")
            # Don't fail the sync phase, just log the error

    return PhaseResult(...)
```

**Verification**:
1. Create a spec via API
2. Execute the spec via `POST /specs/{id}/execute`
3. Check that `Ticket` records are created after SYNC completes
4. Check that `Task` records are created and queued

---

#### Task 1.2: Fix `/execute` Endpoint to Use Sandbox

**File**: `backend/omoi_os/api/routes/specs.py` (lines 1440-1514)

**Current (WRONG)**:
```python
success = await run_spec_state_machine(
    spec_id=spec_id,
    working_directory=working_dir,  # Uses os.getcwd()!
    ...
)
```

**Change to**:
```python
@router.post("/{spec_id}/execute", response_model=SpecExecuteResponse)
async def execute_spec(
    spec_id: str,
    request: SpecExecuteRequest = SpecExecuteRequest(),
    db: DatabaseService = Depends(get_db_service),
    current_user: User = Depends(get_current_user),  # ADD authentication
):
    spec = await _get_spec_async(db, spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    if not spec.project_id:
        raise HTTPException(status_code=400, detail="Spec must have project_id")

    # Billing check (existing)
    can_execute, billing_reason = await _check_billing_for_spec_execution(db, spec_id)
    if not can_execute:
        raise HTTPException(status_code=402, detail=f"Execution blocked: {billing_reason}")

    # Check if already executing
    if spec.status == "executing":
        return SpecExecuteResponse(
            spec_id=spec_id,
            status="already_running",
            message="Spec execution is already in progress",
            current_phase=spec.current_phase,
        )

    # Update status
    await _update_spec_async(db, spec_id, status="executing")

    # SPAWN SANDBOX instead of running directly
    from omoi_os.services.daytona_spawner import get_daytona_spawner
    spawner = get_daytona_spawner()

    sandbox_id = await spawner.spawn_for_phase(
        spec_id=spec_id,
        phase=spec.current_phase or "explore",
        project_id=spec.project_id,
        phase_context={
            "title": spec.title,
            "description": spec.description,
        },
    )

    return SpecExecuteResponse(
        spec_id=spec_id,
        status="started",
        message=f"Spec execution started in sandbox {sandbox_id}",
        current_phase=spec.current_phase or "explore",
        sandbox_id=sandbox_id,  # Return sandbox ID for tracking
    )
```

**Also update** `SpecExecuteResponse` to include `sandbox_id`:
```python
class SpecExecuteResponse(BaseModel):
    spec_id: str
    status: str
    message: str
    current_phase: Optional[str] = None
    sandbox_id: Optional[str] = None  # ADD THIS
```

**Verification**:
1. Call `POST /specs/{id}/execute`
2. Verify a Daytona sandbox is created (check logs)
3. Verify sandbox has `SPEC_ID` and `SPEC_PHASE` env vars
4. Verify state machine runs INSIDE sandbox, not API process

---

### Phase 2: User Ownership (Estimated: 2-3 hours)

**Goal**: Tickets created from specs appear on user's board.

**⚠️ CRITICAL DEPENDENCY**: Phase 1 tickets will be INVISIBLE on the board until Phase 2 is complete! You can code Phase 1, but you cannot verify it works in the UI without Phase 2.

**⚠️ TASK ORDER MATTERS**: Tasks must be done in this EXACT order:
1. Task 2.1: Add auth to routes FIRST (so we know current_user)
2. Task 2.2: Add user_id to model (now we have a user to assign)
3. Task 2.3: Create migration
4. Task 2.4: Pass user_id to tickets

#### Task 2.1: Add Auth to Spec Routes (DO THIS FIRST!)

**File**: `backend/omoi_os/api/routes/specs.py`

**Why First?** Without authentication, we don't know WHO is creating the spec, so we can't set `user_id`.

Find all routes that CREATE specs and add `current_user`:

```python
from omoi_os.api.auth import get_current_user

@router.post("", response_model=SpecResponse)
async def create_spec(
    spec: SpecCreate,
    db: DatabaseService = Depends(get_db_service),
    current_user: User = Depends(get_current_user),  # ADD THIS
):
    # user_id will be set in Task 2.3 after model is updated
    # ... rest of creation logic
```

#### Task 2.2: Add `user_id` to Spec Model

**File**: `backend/omoi_os/models/spec.py`

```python
from uuid import UUID
from sqlalchemy import ForeignKey

class Spec(Base):
    # ... existing fields ...

    # NEW: Track spec ownership
    user_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who created/owns this spec"
    )
```

#### Task 2.3: Create Migration and Update Route

**File**: `backend/alembic/versions/xxx_add_spec_user_id.py`

Generate with: `uv run alembic revision -m "add_spec_user_id"`

```python
"""Add user_id to specs table

Revision ID: (auto-generated timestamp)
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('specs', sa.Column('user_id', sa.UUID(), nullable=True))
    op.create_index('idx_specs_user_id', 'specs', ['user_id'])
    op.create_foreign_key(
        'fk_specs_user_id',
        'specs', 'users',
        ['user_id'], ['id'],
        ondelete='SET NULL'
    )

def downgrade():
    op.drop_constraint('fk_specs_user_id', 'specs', type_='foreignkey')
    op.drop_index('idx_specs_user_id', table_name='specs')
    op.drop_column('specs', 'user_id')
```

Then update the route to actually SET user_id:

**File**: `backend/omoi_os/api/routes/specs.py` (same file as Task 2.1)

```python
@router.post("", response_model=SpecResponse)
async def create_spec(
    spec: SpecCreate,
    db: DatabaseService = Depends(get_db_service),
    current_user: User = Depends(get_current_user),
):
    spec_data = spec.model_dump()
    spec_data["user_id"] = current_user.id  # NOW we can set this
    # ... rest of creation logic
```

#### Task 2.4: Pass `user_id` to Ticket Creation

**File**: `backend/omoi_os/services/spec_task_execution.py` (line 314-328)

```python
ticket = Ticket(
    id=str(uuid4()),
    title=f"[Spec] {spec.title}",
    description=spec.description,
    phase_id="PHASE_IMPLEMENTATION",
    status="building",
    priority="MEDIUM",
    project_id=spec.project_id,
    user_id=spec.user_id,  # ADD THIS LINE
    context={...},
)
```

**Verification**:
1. Create spec as authenticated user
2. Verify `spec.user_id` is set
3. Execute spec tasks
4. Verify created tickets have `user_id`
5. Open board as same user
6. Verify tickets are visible

---

### Phase 3: Real-Time UI Updates (Estimated: 3-4 hours)

**Goal**: Frontend shows live progress as phases complete.

#### Task 3.0: Add `spec_id` to SandboxEvent Model (DECISION: Use existing table)

**Rationale**: Don't create a new table - leverage existing `sandbox_events` infrastructure.

**File**: `backend/omoi_os/models/sandbox_event.py` (line 21-52)

```python
# Add to SandboxEvent class after line 48:
spec_id: Mapped[Optional[str]] = mapped_column(
    String,
    ForeignKey("specs.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
    comment="Spec ID if this event is from spec execution"
)
```

**Migration**: `backend/alembic/versions/xxx_add_spec_id_to_sandbox_events.py`

```python
"""Add spec_id to sandbox_events table

Revision ID: xxx
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('sandbox_events', sa.Column('spec_id', sa.String(), nullable=True))
    op.create_index('idx_sandbox_events_spec_id', 'sandbox_events', ['spec_id'],
                    postgresql_where=sa.text('spec_id IS NOT NULL'))
    op.create_foreign_key(
        'fk_sandbox_events_spec_id',
        'sandbox_events', 'specs',
        ['spec_id'], ['id'],
        ondelete='SET NULL'
    )

def downgrade():
    op.drop_constraint('fk_sandbox_events_spec_id', 'sandbox_events', type_='foreignkey')
    op.drop_index('idx_sandbox_events_spec_id', table_name='sandbox_events')
    op.drop_column('sandbox_events', 'spec_id')
```

**New Spec Event Types** (stored in `sandbox_events` with `source='system'`):
- `spec.execution_started` - Execution begins
- `spec.phase_started` - Phase begins
- `spec.phase_completed` - Phase passes evaluator
- `spec.phase_failed` - Phase fails evaluator
- `spec.execution_completed` - All phases done
- `spec.tasks_queued` - Tasks created and queued

---

#### Task 3.1: Add EventReporter to State Machine

**EventReporter Location**: `backend/omoi_os/workers/claude_sandbox_worker.py:2473`

**What EventReporter Does**:
- Posts events via HTTP to `/api/v1/sandboxes/{sandbox_id}/events`
- Uses `CALLBACK_URL` env var set by `spawn_for_phase()` to know the API URL
- Is an async context manager (`async with EventReporter(config) as reporter:`)
- The `config` must have `sandbox_id` and `callback_url` attributes

**Import**: `from omoi_os.workers.claude_sandbox_worker import EventReporter`
(or `from omoi_os.workers import EventReporter` via `__init__.py`)

**File**: `backend/omoi_os/workers/spec_state_machine.py`

```python
class SpecStateMachine:
    def __init__(
        self,
        spec_id: str,
        db_session: AsyncSession,
        working_directory: str,
        model: str = "claude-sonnet-4-20250514",
        event_reporter: Optional["EventReporter"] = None,  # ADD THIS
    ):
        self.event_reporter = event_reporter
        # ... rest of init

    async def _report_event(self, event_type: str, data: dict):
        """Report spec event to backend."""
        if self.event_reporter:
            await self.event_reporter.report(
                event_type=f"spec.{event_type}",
                data={
                    "spec_id": self.spec_id,
                    "phase": self.current_phase,
                    **data,
                }
            )

    async def _run_phase(self, phase: SpecPhase) -> PhaseResult:
        await self._report_event("phase_started", {"phase": phase.value})

        try:
            result = await self._execute_phase(phase)
            await self._report_event("phase_completed", {
                "phase": phase.value,
                "duration": result.duration,
                "eval_score": result.eval_score,
            })
            return result
        except Exception as e:
            await self._report_event("phase_failed", {
                "phase": phase.value,
                "error": str(e),
            })
            raise
```

#### Task 3.2: Pass EventReporter from Worker

**File**: `backend/omoi_os/workers/claude_sandbox_worker.py` (line 4240-4270)

```python
async def _run_spec_state_machine(self) -> int:
    # ... existing setup ...

    # Create event reporter for spec events
    async with EventReporter(self.config) as reporter:
        state_machine = SpecStateMachine(
            spec_id=self.config.spec_id,
            db_session=db_session,
            working_directory=self.config.cwd,
            model=self.config.model,
            event_reporter=reporter,  # ADD THIS
        )
        return await state_machine.run()
```

#### Task 3.3: Add Spec Events Endpoint

**File**: `backend/omoi_os/api/routes/specs.py`

```python
@router.get("/{spec_id}/events", response_model=SpecEventsResponse)
async def get_spec_events(
    spec_id: str,
    limit: int = 50,
    offset: int = 0,
    db: DatabaseService = Depends(get_db_service),
):
    """Get events for a spec execution."""
    # Query sandbox_events using the spec_id FK column (not JSONB)
    async with db.get_async_session() as session:
        stmt = select(SandboxEvent).where(
            SandboxEvent.spec_id == spec_id  # Uses the FK column
        ).order_by(SandboxEvent.created_at.desc()).limit(limit).offset(offset)
        result = await session.execute(stmt)
        events = result.scalars().all()

    return SpecEventsResponse(
        spec_id=spec_id,
        events=[
            SpecEventItem(
                id=e.id,
                event_type=e.event_type,
                event_data=e.event_data,
                source=e.source,
                created_at=e.created_at,
            )
            for e in events
        ],
        total=len(events),
    )
```

#### Task 3.4: Frontend Event Hook

**File**: `frontend/hooks/useSpecs.ts`

```typescript
export function useSpecEvents(
  specId: string | undefined,
  options?: { enabled?: boolean; refetchInterval?: number }
) {
  return useQuery<SpecEventsResponse>({
    queryKey: specsKeys.events(specId!),
    queryFn: () => getSpecEvents(specId!),
    enabled: options?.enabled ?? !!specId,
    refetchInterval: options?.refetchInterval ?? 2000,
  })
}
```

**Verification**:
1. Execute a spec
2. Open spec detail page
3. Verify events appear in real-time
4. Verify phase progress updates live

---

### Phase 4: Command Page Integration (Estimated: 2-3 hours)

**Goal**: User can type idea → System creates spec → Execution starts automatically.

#### Task 4.1: Add `/specs/launch` Endpoint

**File**: `backend/omoi_os/api/routes/specs.py`

```python
class SpecLaunchRequest(BaseModel):
    title: str
    description: str
    project_id: str
    auto_execute: bool = True

class SpecLaunchResponse(BaseModel):
    spec_id: str
    status: str  # "created" or "executing"
    current_phase: Optional[str] = None
    sandbox_id: Optional[str] = None
    message: str

@router.post("/launch", response_model=SpecLaunchResponse)
async def launch_spec(
    request: SpecLaunchRequest,
    db: DatabaseService = Depends(get_db_service),
    current_user: User = Depends(get_current_user),
):
    """Create spec and optionally start execution in sandbox."""
    # 1. Create spec
    spec = Spec(
        title=request.title,
        description=request.description,
        project_id=request.project_id,
        user_id=current_user.id,
        status="draft" if not request.auto_execute else "executing",
        current_phase="explore",
    )

    async with db.get_async_session() as session:
        session.add(spec)
        await session.commit()
        await session.refresh(spec)
        spec_id = spec.id

    # 2. Spawn sandbox if auto_execute
    if request.auto_execute:
        from omoi_os.services.daytona_spawner import get_daytona_spawner
        spawner = get_daytona_spawner()

        sandbox_id = await spawner.spawn_for_phase(
            spec_id=spec_id,
            phase="explore",
            project_id=request.project_id,
            phase_context={
                "title": request.title,
                "description": request.description,
            },
        )

        return SpecLaunchResponse(
            spec_id=spec_id,
            status="executing",
            current_phase="explore",
            sandbox_id=sandbox_id,
            message="Spec created and execution started",
        )

    return SpecLaunchResponse(
        spec_id=spec_id,
        status="created",
        message="Spec created (not executing)",
    )
```

#### Task 4.2: Frontend API Function

**File**: `frontend/lib/api/specs.ts`

```typescript
export interface SpecLaunchRequest {
  title: string
  description: string
  project_id: string
  auto_execute?: boolean
}

export interface SpecLaunchResponse {
  spec_id: string
  status: "created" | "executing"
  current_phase?: string
  sandbox_id?: string
  message: string
}

export async function launchSpec(
  request: SpecLaunchRequest
): Promise<SpecLaunchResponse> {
  return apiRequest<SpecLaunchResponse>("/api/v1/specs/launch", {
    method: "POST",
    body: request,
  })
}
```

#### Task 4.3: Update Command Page

**File**: `frontend/app/(app)/command/page.tsx`

```typescript
async function handleSubmit(data: CommandFormData) {
  if (data.workflowMode === "spec_driven") {
    // Direct spec launch - no ticket
    const response = await launchSpec({
      title: data.title,
      description: data.description,
      project_id: data.projectId,
      auto_execute: true,
    })

    // Redirect to spec detail page
    router.push(`/projects/${data.projectId}/specs/${response.spec_id}`)
  } else {
    // Quick task - existing ticket flow
    const ticket = await createTicket(data)
    router.push(`/tickets/${ticket.id}`)
  }
}
```

**Verification**:
1. Go to command page
2. Select "Spec-Driven" mode
3. Enter idea and submit
4. Verify redirect to spec detail page
5. Verify execution starts automatically
6. Verify phases progress in real-time

---

## Complete File List

### Backend Files to Create

| File | Purpose |
|------|---------|
| `alembic/versions/xxx_add_spec_user_id.py` | Migration: Add `user_id` to specs table |
| `alembic/versions/xxx_add_spec_id_to_sandbox_events.py` | Migration: Add `spec_id` to sandbox_events table |

### Backend Files to Modify

| File | Lines | Change |
|------|-------|--------|
| `omoi_os/models/spec.py` | ~line 50 | Add `user_id` field |
| `omoi_os/api/routes/specs.py` | 1440-1514 | Fix `/execute` to spawn sandbox |
| `omoi_os/api/routes/specs.py` | ~line 958 | Add auth to `create_spec` |
| `omoi_os/api/routes/specs.py` | NEW | Add `/launch` endpoint |
| `omoi_os/api/routes/specs.py` | NEW | Add `/events` endpoint |
| `omoi_os/workers/spec_state_machine.py` | __init__ | Add EventReporter param |
| `omoi_os/workers/spec_state_machine.py` | _run_phase | Add event reporting |
| `omoi_os/workers/spec_state_machine.py` | line 291 (_execute_sync_phase) | Call SpecTaskExecutionService |
| `omoi_os/workers/claude_sandbox_worker.py` | 4240-4270 | Pass EventReporter to state machine |
| `omoi_os/services/spec_task_execution.py` | 314-328 | Add `user_id` to ticket |
| `omoi_os/models/sandbox_event.py` | after line 48 | Add `spec_id` FK field |

### Frontend Files to Create

| File | Purpose |
|------|---------|
| `frontend/lib/api/specs.ts` | Add `launchSpec()` function |
| `frontend/hooks/useSpecs.ts` | Add `useLaunchSpec()` and `useSpecEvents()` hooks |

### Frontend Files to Modify

| File | Change |
|------|--------|
| `frontend/app/(app)/command/page.tsx` | Call launchSpec for spec_driven mode |
| `frontend/app/(app)/projects/[id]/specs/[specId]/page.tsx` | Add phase progress, event timeline |

---

## Verification Checklist

### Phase 1: Critical Wiring
- [ ] State machine calls SpecTaskExecutionService after SYNC
- [ ] `/execute` spawns Daytona sandbox instead of running directly
- [ ] Sandbox receives `SPEC_ID` and `SPEC_PHASE` env vars
- [ ] State machine runs inside sandbox, not API process

### Phase 2: User Ownership
- [ ] Spec model has `user_id` field
- [ ] Migration created and applied
- [ ] Spec routes require authentication
- [ ] Created specs have `user_id` set
- [ ] Tickets created from specs have `user_id`
- [ ] Tickets appear on user's board

### Phase 3: Real-Time UI
- [ ] State machine emits events
- [ ] Events stored in database
- [ ] `/specs/{id}/events` endpoint returns events
- [ ] Frontend polls events and updates UI
- [ ] Phase progress shown in real-time

### Phase 4: Command Page
- [ ] `/specs/launch` endpoint exists
- [ ] Frontend calls launch for spec_driven mode
- [ ] Redirect to spec detail page works
- [ ] Execution starts automatically
- [ ] User can watch phases progress

---

## Known Dependencies

```
Phase 1 (Critical Wiring)
    │
    └── Can be done independently

Phase 2 (User Ownership)
    │
    ├── Requires: Migration for user_id
    │
    └── Blocks: Tickets appearing on board

Phase 3 (Real-Time UI)
    │
    ├── Requires: Phase 1 (sandbox execution)
    │
    └── Optional: Can work without this

Phase 4 (Command Page)
    │
    ├── Requires: Phase 1 (sandbox execution)
    ├── Requires: Phase 2 (user_id for ticket visibility)
    │
    └── Best done last
```

---

## Related Documentation

- [sandbox-execution.md](./sandbox-execution.md) - Details on sandbox vs API execution
- [ui-and-events.md](./ui-and-events.md) - Event reporting design
- [impact-assessment.md](./impact-assessment.md) - Assessment of existing gaps
- [command-page-integration.md](./command-page-integration.md) - UI entry point design
- [skill-to-api-flow.md](./skill-to-api-flow.md) - CLI sync path and user_id gap
- [ticket-field-gap.md](./ticket-field-gap.md) - Why tickets are invisible
- `docs/design/sandbox-agents/IMPLEMENTATION_COMPLETE_STATUS.md` - Sandbox infrastructure status
