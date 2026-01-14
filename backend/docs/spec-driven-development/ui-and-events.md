# UI and Events - Spec-Driven Development

**Created**: 2025-01-11
**Status**: Gap Analysis
**Purpose**: Document UI functionality and event reporting gaps

---

## Event Reporting Architecture

### Current Sandbox Event System

The existing sandbox system has robust event reporting:

```
claude_sandbox_worker.py
    │
    ▼
EventReporter class (line 2473)
    │ Posts events via HTTP to:
    │ POST /api/v1/sandboxes/{sandbox_id}/events
    │
    ▼
Backend stores events in database
    │
    ▼
Frontend polls via:
    │ GET /api/v1/sandboxes/{sandbox_id}/events
    │ GET /api/v1/sandboxes/{sandbox_id}/trajectory
    │
    ▼
Real-time UI updates
```

### Event Types Reported by Sandbox

From `claude_sandbox_worker.py`:
- `agent.started` - Agent begins execution
- `agent.tool_completed` - Tool execution complete
- `agent.subagent_completed` - Subagent finished
- `agent.skill_completed` - Skill execution done
- `agent.heartbeat` - Periodic health check
- `agent.error` - Error occurred
- `agent.completed` - Agent finished

### State Machine Event Gap

**PROBLEM**: The `_run_spec_state_machine()` method does NOT use `EventReporter`:

```python
# claude_sandbox_worker.py:4211-4281
async def _run_spec_state_machine(self) -> int:
    # ... runs SpecStateMachine.run()
    # NO EventReporter usage!
    # NO event reporting to backend!
```

The state machine:
- Logs to console (`logger.info`)
- Updates database directly
- Does NOT report events via HTTP

**This means**: No real-time UI updates during state machine execution!

---

## Current UI State

### Spec Detail Page (`/projects/[id]/specs/[specId]`)

**What exists**:
- Requirements tab with CRUD operations
- Design tab with architecture/data model display
- Tasks tab with task management
- Execution tab with progress metrics
- Sidebar with metadata

**Execution tab polling** (lines 143-151):
```typescript
// Polls every 5s when spec.status === "executing"
const { data: executionStatus } = useExecutionStatus(specId, {
  enabled: isExecuting,
  refetchInterval: isExecuting ? 5000 : false,
})
const { data: criteriaStatus } = useCriteriaStatus(specId, {
  enabled: isExecuting,
  refetchInterval: isExecuting ? 5000 : false,
})
```

**What's shown during execution**:
- Task progress percentage
- Criteria completion percentage
- Active agents count
- Status counts (pending/in_progress/completed)
- Criteria breakdown by requirement

### What's Missing in UI

| Feature | Status | Notes |
|---------|--------|-------|
| Real-time phase progress | Missing | No WebSocket/SSE for phase updates |
| Agent trajectory viewer | Missing | Sandbox has it, specs don't |
| Phase transition notifications | Missing | No toast/alerts when phase changes |
| Error details display | Missing | Failures shown but no details |
| Live log streaming | Missing | No console output visible |
| Sandbox link | Missing | Can't navigate to sandbox for spec |

---

## Required Changes

### 1. Add Event Reporting to State Machine

```python
# In SpecStateMachine class
class SpecStateMachine:
    def __init__(self, ..., event_reporter: Optional[EventReporter] = None):
        self.event_reporter = event_reporter

    async def _report_event(self, event_type: str, data: dict):
        if self.event_reporter:
            await self.event_reporter.report(
                f"spec.{event_type}",
                {
                    "spec_id": self.spec_id,
                    "phase": self.current_phase,
                    **data
                }
            )

    async def _run_phase(self, phase: SpecPhase):
        await self._report_event("phase_started", {"phase": phase.value})
        # ... run phase ...
        await self._report_event("phase_completed", {
            "phase": phase.value,
            "duration": duration,
            "eval_score": result.eval_score,
        })
```

### 2. Pass EventReporter to State Machine

```python
# claude_sandbox_worker.py:_run_spec_state_machine()
async def _run_spec_state_machine(self) -> int:
    # Create event reporter for spec events
    async with EventReporter(self.config) as reporter:
        state_machine = SpecStateMachine(
            spec_id=self.config.spec_id,
            db_session=db_session,
            working_directory=self.config.cwd,
            event_reporter=reporter,  # NEW
        )
        return await state_machine.run()
```

### 3. New Spec Event Types

| Event Type | Payload | When |
|------------|---------|------|
| `spec.execution_started` | `{spec_id, starting_phase}` | Execution begins |
| `spec.phase_started` | `{spec_id, phase, attempt}` | Phase begins |
| `spec.phase_completed` | `{spec_id, phase, duration, eval_score}` | Phase passes evaluator |
| `spec.phase_failed` | `{spec_id, phase, error, attempt}` | Phase fails evaluator |
| `spec.phase_retry` | `{spec_id, phase, attempt, max_attempts}` | Phase retrying |
| `spec.execution_completed` | `{spec_id, success, total_duration}` | All phases done |
| `spec.sync_started` | `{spec_id, items_to_sync}` | SYNC phase begins |
| `spec.sync_completed` | `{spec_id, items_synced}` | SYNC phase done |

### 4. API Endpoint for Spec Events

```python
# New endpoint in specs.py
@router.get("/{spec_id}/events")
async def get_spec_events(
    spec_id: str,
    limit: int = 50,
    offset: int = 0,
    db: DatabaseService = Depends(get_db_service),
):
    """Get events for a spec execution."""
    # Query sandbox_events using the spec_id FK column
    async with db.get_async_session() as session:
        stmt = select(SandboxEvent).where(
            SandboxEvent.spec_id == spec_id
        ).order_by(SandboxEvent.created_at.desc()).limit(limit).offset(offset)
        result = await session.execute(stmt)
        events = result.scalars().all()
    return SpecEventsResponse(spec_id=spec_id, events=[...], total=len(events))
```

### 5. Frontend Changes

#### Add Real-Time Event Polling

```typescript
// useSpecs.ts - new hook
export function useSpecEvents(
  specId: string | undefined,
  options?: { enabled?: boolean; refetchInterval?: number }
) {
  return useQuery<SpecEventsResponse>({
    queryKey: specsKeys.events(specId!),
    queryFn: () => getSpecEvents(specId!),
    enabled: options?.enabled ?? !!specId,
    refetchInterval: options?.refetchInterval,
  })
}
```

#### Add Phase Progress Component

```typescript
// components/spec/PhaseProgress.tsx
export function PhaseProgress({ specId }: { specId: string }) {
  const phases = ["explore", "requirements", "design", "tasks", "sync"]
  const { data: spec } = useSpec(specId)

  return (
    <div className="flex items-center gap-2">
      {phases.map((phase, idx) => {
        const isComplete = /* check spec.phase_data */
        const isCurrent = spec?.current_phase === phase
        const isPending = !isComplete && !isCurrent

        return (
          <div key={phase} className="flex items-center">
            <div className={cn(
              "w-8 h-8 rounded-full flex items-center justify-center",
              isComplete && "bg-green-500",
              isCurrent && "bg-blue-500 animate-pulse",
              isPending && "bg-gray-300"
            )}>
              {isComplete ? <Check /> : idx + 1}
            </div>
            {idx < phases.length - 1 && (
              <div className={cn(
                "w-8 h-0.5",
                isComplete ? "bg-green-500" : "bg-gray-300"
              )} />
            )}
          </div>
        )
      })}
    </div>
  )
}
```

#### Add Event Timeline Component

```typescript
// components/spec/EventTimeline.tsx
export function EventTimeline({ specId }: { specId: string }) {
  const { data: events } = useSpecEvents(specId, {
    enabled: true,
    refetchInterval: 2000, // Poll every 2s
  })

  return (
    <div className="space-y-2">
      {events?.events.map(event => (
        <div key={event.id} className="flex items-start gap-2 text-sm">
          <span className="text-muted-foreground">
            {formatTime(event.timestamp)}
          </span>
          <Badge variant={getVariantForEventType(event.type)}>
            {event.type}
          </Badge>
          <span>{event.message}</span>
        </div>
      ))}
    </div>
  )
}
```

---

## UI Improvements Needed

### Execution Tab Enhancements

1. **Phase Progress Bar**
   - Visual indicator: EXPLORE ──► REQUIREMENTS ──► DESIGN ──► TASKS ──► SYNC
   - Show current phase highlighted
   - Show completed phases with checkmarks

2. **Live Event Feed**
   - Stream of events as they happen
   - Filter by event type
   - Auto-scroll with pause option

3. **Phase Output Viewer**
   - Expandable sections for each phase's output
   - Requirements in formatted display
   - Design artifacts with diagrams
   - Task breakdown table

4. **Sandbox Link**
   - When a sandbox is spawned for spec, show link
   - Navigate to sandbox trajectory view
   - See detailed agent activity

### Command Page Enhancements

1. **Spec-Driven Mode**
   - Clear explanation of what happens
   - Progress indicator after submission
   - Link to spec detail page

2. **Project Selection**
   - Required for spec-driven mode
   - Shows which codebase will be used

---

## Database Schema Considerations

### ✅ DECISION: Use Existing sandbox_events (Option A)

**Rationale**: Don't repeat ourselves - leverage existing event infrastructure.

**Current Model** (`omoi_os/models/sandbox_event.py:21-52`):
```python
class SandboxEvent(Base):
    __tablename__ = "sandbox_events"

    id: str              # UUID
    sandbox_id: str      # The sandbox that generated this event
    event_type: str      # e.g., 'agent.started', 'agent.tool_use'
    event_data: dict     # JSONB payload with event-specific data
    source: str          # 'agent', 'guardian', 'system'
    created_at: datetime
```

**Required Change**: Add `spec_id` column to link events to specs.

```sql
-- Migration: Add spec_id to sandbox_events
ALTER TABLE sandbox_events ADD COLUMN spec_id VARCHAR REFERENCES specs(id);
CREATE INDEX idx_sandbox_events_spec_id ON sandbox_events(spec_id) WHERE spec_id IS NOT NULL;
```

**Model Update** (`omoi_os/models/sandbox_event.py`):
```python
# Add to SandboxEvent class:
spec_id: Mapped[Optional[str]] = mapped_column(
    String,
    ForeignKey("specs.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
    comment="Spec ID if this event is from spec execution"
)
```

### New Spec-Specific Event Types

The state machine will emit these new event types (stored in existing `sandbox_events` table):

| Event Type | source | Payload | UI Display |
|------------|--------|---------|------------|
| `spec.execution_started` | `system` | `{spec_id, starting_phase}` | "Execution started" |
| `spec.phase_started` | `system` | `{spec_id, phase, attempt}` | Phase indicator activates |
| `spec.phase_completed` | `system` | `{spec_id, phase, duration, eval_score}` | Phase checkmark |
| `spec.phase_failed` | `system` | `{spec_id, phase, error, attempt}` | Phase error indicator |
| `spec.phase_retry` | `system` | `{spec_id, phase, attempt, max_attempts}` | Retry count badge |
| `spec.execution_completed` | `system` | `{spec_id, success, total_duration}` | Success/failure banner |
| `spec.sync_started` | `system` | `{spec_id, items_to_sync}` | "Syncing N items..." |
| `spec.sync_completed` | `system` | `{spec_id, items_synced}` | "Synced N items" |
| `spec.tasks_queued` | `system` | `{spec_id, task_count, ticket_id}` | "N tasks queued" |

These events will display differently in the UI than regular agent events - showing phase progress, evaluator scores, and task execution status.

---

## Summary of Gaps

| Component | Gap | Priority |
|-----------|-----|----------|
| SpecStateMachine | No EventReporter | HIGH |
| Backend | No spec events endpoint | HIGH |
| Frontend | No phase progress UI | MEDIUM |
| Frontend | No event timeline | MEDIUM |
| Frontend | No sandbox link | LOW |
| Command Page | No spec redirect | HIGH |
| WebSocket | No real-time push | LOW (polling OK) |

---

## Files to Modify

| File | Change |
|------|--------|
| `spec_state_machine.py` | Add event reporting |
| `claude_sandbox_worker.py` | Pass EventReporter to state machine |
| `specs.py` | Add `/events` endpoint |
| `frontend/hooks/useSpecs.ts` | Add `useSpecEvents` hook |
| `frontend/lib/api/specs.ts` | Add `getSpecEvents` function |
| `frontend/app/.../specs/[specId]/page.tsx` | Add phase progress, event timeline |
