# Autonomous Execution Feature

**Created**: 2025-01-15
**Status**: Implementation Ready
**Purpose**: Enable project-level toggle for automatic task spawning when tasks become unblocked

---

## Overview

The Autonomous Execution feature allows projects to automatically spawn and execute tasks when they become unblocked (all dependencies completed). This is controlled by a per-project toggle that enables "fire and forget" autonomous operation.

### User Story
As a user, I want to toggle a project into "autonomous mode" so that when tasks complete and unblock other tasks, the system automatically spawns those newly unblocked tasks without manual intervention.

---

## Backend Implementation (COMPLETED)

### 1. Database Schema Change

**Migration:** `054_add_autonomous_execution_toggle.py`

```sql
ALTER TABLE projects
ADD COLUMN autonomous_execution_enabled BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX ix_projects_autonomous_execution_enabled
ON projects (autonomous_execution_enabled);
```

**Model Change:** `omoi_os/models/project.py`

```python
autonomous_execution_enabled: Mapped[bool] = mapped_column(
    Boolean, default=False, nullable=False, index=True
)
```

### 2. Task Completion Endpoint

**Endpoint:** `POST /api/v1/sandboxes/{sandbox_id}/task-complete`

**Location:** `omoi_os/api/routes/sandbox.py:1911-2059`

This endpoint allows sandboxes to report task completion and triggers DAG re-evaluation:

```python
class TaskCompleteRequest(BaseModel):
    task_id: str
    success: bool = True
    result: Optional[dict] = None
    error_message: Optional[str] = None

class TaskCompleteResponse(BaseModel):
    status: str
    task_id: str
    new_status: str
    unblocked_tasks: list[str]  # Newly unblocked task IDs
```

**Flow:**
1. Sandbox calls endpoint with task completion data
2. Task status updated to `completed` or `failed`
3. DAG is re-evaluated to find tasks that are now unblocked
4. `TASKS_UNBLOCKED` event is published
5. Response includes list of unblocked task IDs

### 3. Orchestrator Filtering

**Location:** `omoi_os/services/task_queue.py`

Two methods modified to respect the `autonomous_execution_enabled` flag:

- `get_next_task_with_concurrency_limit` (line 1814-1821)
- `get_next_validation_task_with_concurrency_limit` (line 1952-1959)

Tasks from projects where `autonomous_execution_enabled=False` are skipped.

### 4. New Method for Autonomous Tasks

**Method:** `get_unblocked_tasks_for_autonomous_projects_async`

**Location:** `omoi_os/services/task_queue.py:1291-1378`

```python
async def get_unblocked_tasks_for_autonomous_projects_async(
    self,
    project_id: Optional[str] = None,
    limit: int = 50,
) -> list[Task]:
    """
    Get all unblocked tasks from projects with autonomous_execution_enabled=True.
    """
```

---

## Frontend Implementation (TODO)

### UI Location

Based on the screenshot, the toggle should be:
- **Location:** Top-right of Kanban board header, next to "Start Processing" button
- **Visual:** The "Start Processing" button should change appearance when autonomous mode is enabled
- **Behavior:** When enabled, the system auto-spawns tasks; when disabled, user clicks "Start Processing" manually

### Implementation Files to Modify

1. **Board Page:** `frontend/app/(app)/board/[projectId]/page.tsx`
   - Add autonomous mode toggle button
   - Modify "Start Processing" button appearance based on mode
   - Subscribe to autonomous mode changes via WebSocket

2. **Project Settings:** `frontend/app/(app)/projects/[id]/settings/page.tsx`
   - Add toggle in "Agent Defaults" section
   - Use existing `Switch` component pattern

3. **API Types:** `frontend/lib/api/types.ts`
   - Add `autonomous_execution_enabled?: boolean` to `ProjectUpdate`

4. **Project Hooks:** `frontend/hooks/useProjects.ts`
   - Add mutation for toggling autonomous mode

### Suggested UI Pattern

```tsx
// In board header, replace/modify "Start Processing" button
{project.autonomous_execution_enabled ? (
  <Button
    variant="outline"
    onClick={() => toggleAutonomousMode(false)}
    className="border-green-500 text-green-600"
  >
    <Pause className="mr-2 h-4 w-4" />
    Autonomous: ON
    <Badge variant="secondary" className="ml-2 bg-green-100 text-green-800">
      {runningTaskCount}
    </Badge>
  </Button>
) : (
  <Button
    variant="default"
    onClick={() => toggleAutonomousMode(true)}
    className="bg-green-600 hover:bg-green-700"
  >
    <Play className="mr-2 h-4 w-4" />
    Start Processing
    {processableTickets.length > 0 && (
      <Badge variant="secondary" className="ml-2">
        {processableTickets.length}
      </Badge>
    )}
  </Button>
)}
```

---

## API Endpoint (Backend TODO)

Create a dedicated endpoint for toggling autonomous mode:

**Endpoint:** `PATCH /api/v1/projects/{project_id}/autonomous-execution`

```python
class AutonomousExecutionRequest(BaseModel):
    enabled: bool

@router.patch("/{project_id}/autonomous-execution")
async def toggle_autonomous_execution(
    project_id: str,
    request: AutonomousExecutionRequest,
) -> Project:
    """Toggle autonomous execution for a project."""
    # Update project.autonomous_execution_enabled
    # Publish event for WebSocket subscribers
    # Return updated project
```

---

## WebSocket Events

### Existing Events to Leverage
- `TASK_COMPLETED` - when tasks finish
- `TASK_STATUS_CHANGED` - when task status changes
- `SANDBOX_SPAWNED` - when new sandbox starts

### New Event Needed
- `AUTONOMOUS_MODE_CHANGED` - when project autonomous mode toggles

```python
event_bus.publish(SystemEvent(
    event_type="AUTONOMOUS_MODE_CHANGED",
    entity_type="project",
    entity_id=project_id,
    payload={"enabled": True}
))
```

---

## Testing Guide

See: `docs/implementation/autonomous_execution_testing.md`

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │  Kanban Board    │    │  Project Settings│                   │
│  │                  │    │                  │                   │
│  │ [Toggle Button]──┼───►│ [Switch Toggle]  │                   │
│  │                  │    │                  │                   │
│  └────────┬─────────┘    └──────────────────┘                   │
│           │                                                      │
│           ▼                                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    WebSocket Connection                     │ │
│  │  Events: TASK_COMPLETED, AUTONOMOUS_MODE_CHANGED, etc.      │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          BACKEND                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   API Endpoints                           │   │
│  │  PATCH /projects/{id}/autonomous-execution                │   │
│  │  POST /sandboxes/{id}/task-complete                       │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │               TaskQueueService                            │   │
│  │  - get_next_task_with_concurrency_limit()                 │   │
│  │  - get_unblocked_tasks_for_autonomous_projects_async()    │   │
│  │  - Filters by autonomous_execution_enabled                │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │               Orchestrator Worker                         │   │
│  │  - Polls for tasks from autonomous projects               │   │
│  │  - Spawns sandboxes for unblocked tasks                   │   │
│  │  - Respects concurrency limits                            │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  Daytona Sandbox                          │   │
│  │  - Executes task                                          │   │
│  │  - Calls /task-complete when done                         │   │
│  │  - DAG re-evaluated, new tasks unblocked                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- [Spec Sandbox Subsystem Strategy](../architecture/spec_sandbox_subsystem_strategy.md)
- [Task Queue Service](../../backend/omoi_os/services/task_queue.py)
- [Orchestrator Worker](../../backend/omoi_os/workers/orchestrator_worker.py)
- [Sandbox API Routes](../../backend/omoi_os/api/routes/sandbox.py)
