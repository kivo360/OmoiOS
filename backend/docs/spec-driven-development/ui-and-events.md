# UI and Events - Spec-Driven Development

**Created**: 2025-01-11
**Updated**: 2026-01-18
**Status**: ✅ Implemented
**Purpose**: Document UI functionality and event reporting for spec-driven workflow

---

## Overview

The spec-driven development workflow is **fully implemented** with:

1. **Spec-Sandbox Event Reporting** - SpecStateMachine emits comprehensive events via HTTPReporter
2. **Backend Event Persistence** - Events stored in `sandbox_events` table with `spec_id` FK
3. **Real-Time UI Updates** - Polling (5s) + WebSocket via EventBus
4. **Frontend Components** - PhaseProgress, EventTimeline, spec detail page

---

## Event Reporting Architecture

### Spec-Sandbox → Backend Flow

```
spec-sandbox (Daytona)
    │
    ▼
SpecStateMachine
    │ Emits events via Reporter abstraction
    │
    ▼
HTTPReporter
    │ POST /api/v1/sandboxes/{sandbox_id}/events
    │ (Bearer token auth)
    │
    ▼
Backend (sandbox.py:create_sandbox_event)
    ├─► persist_sandbox_event_async() → sandbox_events table
    ├─► broadcast_sandbox_event() → EventBus (Redis pub/sub)
    └─► _update_spec_phase_data() → Spec.phase_data (on agent.completed)
    │
    ▼
Frontend
    ├─► Polling: GET /api/v1/specs/{spec_id}/events (5s interval)
    └─► WebSocket: /api/v1/ws/events (EventBus subscription)
```

### Reporter Abstraction

The `spec-sandbox` subsystem uses a Reporter abstraction (`subsystems/spec-sandbox/src/spec_sandbox/reporters/`):

| Reporter | Use Case | Output |
|----------|----------|--------|
| `ArrayReporter` | Unit tests | In-memory list |
| `JSONLReporter` | Local debugging | Append-only file |
| `HTTPReporter` | Production (Daytona) | HTTP POST to backend |

---

## Event Types

### Lifecycle Events

| Event Type | Description | Payload |
|------------|-------------|---------|
| `spec.execution_started` | Spec execution begins | `{title, description, phases}` |
| `spec.execution_completed` | All phases completed successfully | `{phases_completed, markdown_artifacts, ticket_creation}` |
| `spec.execution_failed` | Spec execution failed | `{failed_phase, error}` |

### Phase Events

| Event Type | Description | Payload |
|------------|-------------|---------|
| `spec.phase_started` | A phase begins execution | `{phase}` |
| `spec.phase_completed` | A phase completed successfully | `{phase, eval_score, duration_seconds, retry_count}` |
| `spec.phase_failed` | A phase failed | `{phase, reason, eval_feedback, error}` |
| `spec.phase_retry` | A phase is being retried | `{phase, retry_count, max_retries, reason}` |

### Execution Events

| Event Type | Description | Payload |
|------------|-------------|---------|
| `spec.heartbeat` | Periodic health check | `{phases_completed, current_phase}` |
| `spec.progress` | Progress update within a phase | `{message, eval_passed?, eval_details?}` |

### Artifact Events

| Event Type | Description | Payload |
|------------|-------------|---------|
| `spec.artifact_created` | A file artifact was generated | `{artifact_type, path}` |
| `spec.requirements_generated` | Requirements markdown generated | `{path, requirement_count}` |
| `spec.design_generated` | Design markdown generated | `{path, component_count}` |
| `spec.tasks_generated` | Tasks markdown generated | `{path, task_count}` |

### Sync Phase Events

| Event Type | Description | Payload |
|------------|-------------|---------|
| `spec.sync_started` | SYNC phase begins | `{items_to_sync}` |
| `spec.sync_completed` | SYNC phase done | `{items_synced}` |
| `spec.tasks_queued` | Tasks queued for execution | `{task_count}` |

### Ticket Creation Events

| Event Type | Description | Payload |
|------------|-------------|---------|
| `spec.tickets_creation_started` | Ticket creation begins | `{ticket_count, task_count}` |
| `spec.tickets_creation_completed` | Ticket creation done | `{tickets_created, tasks_created, errors}` |
| `spec.ticket_created` | Individual ticket created | `{ticket_id, title}` |
| `spec.task_created` | Individual task created | `{task_id, title, ticket_id}` |

### Backend Sync Event

| Event Type | Description | Payload |
|------------|-------------|---------|
| `agent.completed` | Signals backend to update Spec model | `{spec_id, success, phase_data, phases_completed?, failed_phase?, error?}` |

**Note**: The `agent.completed` event is critical for backend integration. When the backend receives this event with a `spec_id` and `phase_data`, it calls `_update_spec_phase_data()` to persist the phase outputs to the Spec model. This event uses the `agent.` prefix to match the existing sandbox event handling in the backend.

---

## Event Schema

All events follow the unified `Event` schema from `spec_sandbox.schemas.events`:

```python
class Event(BaseModel):
    event_type: str          # Event type identifier (see tables above)
    timestamp: datetime      # ISO format UTC timestamp
    spec_id: str             # Required - links event to spec
    phase: Optional[str]     # "explore", "requirements", "design", "tasks", "sync"
    data: Optional[dict]     # Event-specific payload
```

Events are serialized to JSON for transport and storage:

```json
{
  "event_type": "spec.phase_completed",
  "timestamp": "2025-01-16T14:30:00Z",
  "spec_id": "550e8400-e29b-41d4-a716-446655440000",
  "phase": "requirements",
  "data": {
    "eval_score": 0.92,
    "duration_seconds": 45.3,
    "retry_count": 0
  }
}
```

---

## Backend Implementation

### Event Persistence

Events are stored in the `sandbox_events` table with `spec_id` FK:

```python
# omoi_os/models/sandbox_event.py
class SandboxEvent(Base):
    __tablename__ = "sandbox_events"

    id: str              # UUID
    sandbox_id: str      # The sandbox that generated this event
    spec_id: str         # FK to specs table (nullable)
    event_type: str      # e.g., 'spec.phase_completed'
    event_data: dict     # JSONB payload
    source: str          # 'agent', 'worker', 'system'
    created_at: datetime
```

### Spec Events Endpoint

```python
# omoi_os/api/routes/specs.py:1936
@router.get("/{spec_id}/events", response_model=SpecEventsResponse)
async def get_spec_events(
    spec_id: str,
    limit: int = 50,
    offset: int = 0,
    event_types: Optional[List[str]] = Query(None),
    db: DatabaseService = Depends(get_db_service),
):
    """Get events for a spec execution."""
```

### Phase Data Update

When `agent.completed` is received with `phase_data`:

```python
# omoi_os/api/routes/sandbox.py:236
async def _update_spec_phase_data(
    db: DatabaseService,
    spec_id: str,
    phase_data: dict,
    success: bool = True,
) -> None:
    """Update spec's phase_data when a spec sandbox completes."""
    # Merges phase_data with existing data (supports incremental execution)
```

### EventBus Broadcasting

All events are broadcast via Redis pub/sub:

```python
# omoi_os/api/routes/sandbox.py:230
def broadcast_sandbox_event(sandbox_id, event_type, event_data, source):
    bus = get_event_bus()
    system_event = _create_system_event(sandbox_id, event_type, event_data, source)
    bus.publish(system_event)
```

Frontend can subscribe via WebSocket at `/api/v1/ws/events`.

---

## Frontend Implementation

### Spec Detail Page

Location: `frontend/app/(app)/projects/[id]/specs/[specId]/page.tsx`

**Features**:
- Requirements tab with CRUD operations
- Design tab with architecture/data model display
- Tasks tab with task management
- Execution tab with progress metrics and event timeline
- Sidebar with metadata and phase progress

**Polling** (when `status === "executing"`):
```typescript
// Polls spec every 5s during execution
const { data: spec } = useSpec(specId, {
  refetchInterval: (query) => {
    const specData = query.state.data
    return specData?.status === "executing" ? 5000 : false
  },
})
```

### PhaseProgress Component

Location: `frontend/components/spec/PhaseProgress.tsx`

Visual stepper showing: EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC

```typescript
<PhaseProgress
  currentPhase={spec.current_phase}
  status={spec.status}
  size="sm"
/>
```

Also available as `PhaseProgressInline` for compact display.

### EventTimeline Component

Location: `frontend/components/spec/EventTimeline.tsx`

Real-time event feed with:
- Event type badges with appropriate colors
- Timestamps
- Event data display
- Auto-refresh during execution

```typescript
<EventTimeline
  specId={specId}
  isExecuting={isExecuting}
  maxHeight="400px"
/>
```

### useSpecEvents Hook

Location: `frontend/hooks/useSpecs.ts:503`

```typescript
export function useSpecEvents(
  specId: string | undefined,
  options?: {
    enabled?: boolean
    refetchInterval?: number
    event_types?: string[]
    limit?: number
  }
) {
  return useQuery<SpecEventsResponse>({
    queryKey: specsKeys.events(specId!, params),
    queryFn: () => getSpecEvents(specId!, params),
    enabled: options?.enabled ?? !!specId,
    refetchInterval: options?.refetchInterval,
  })
}
```

---

## Real-Time Updates

### Polling (Primary)

The frontend uses React Query's `refetchInterval` for real-time updates:

- **Spec data**: 5s polling when `status === "executing"`
- **Events**: 2s polling when executing (configurable)

### WebSocket (Available)

WebSocket support is available via EventBus:

1. Backend broadcasts events to Redis pub/sub
2. WebSocket endpoint at `/api/v1/ws/events` subscribes to EventBus
3. Frontend can connect for instant updates (no polling delay)

**Current Status**: Polling is the primary method; WebSocket is available but frontend uses polling for simplicity.

---

## Testing

### Manual Testing

1. Create a spec-driven ticket:
```bash
curl -X POST "http://localhost:18000/api/v1/tickets" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test spec-driven workflow",
    "description": "Testing events",
    "project_id": "your-project-id",
    "workflow_mode": "spec_driven"
  }'
```

2. Watch events in UI at `/projects/{id}/specs/{specId}`

3. Check events via API:
```bash
curl "http://localhost:18000/api/v1/specs/{spec_id}/events" \
  -H "Authorization: Bearer $TOKEN"
```

### Integration Tests

Location: `tests/integration/test_spec_driven_workflow.py`

---

## File Reference

| Component | Location |
|-----------|----------|
| SpecStateMachine | `subsystems/spec-sandbox/src/spec_sandbox/worker/state_machine.py` |
| HTTPReporter | `subsystems/spec-sandbox/src/spec_sandbox/reporters/http.py` |
| Event Schema | `subsystems/spec-sandbox/src/spec_sandbox/schemas/events.py` |
| Backend Events Handler | `backend/omoi_os/api/routes/sandbox.py` |
| Spec Events Endpoint | `backend/omoi_os/api/routes/specs.py:1936` |
| PhaseProgress | `frontend/components/spec/PhaseProgress.tsx` |
| EventTimeline | `frontend/components/spec/EventTimeline.tsx` |
| useSpecEvents Hook | `frontend/hooks/useSpecs.ts:503` |
| Spec Detail Page | `frontend/app/(app)/projects/[id]/specs/[specId]/page.tsx` |
