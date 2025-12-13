# Sandbox Agent Communication Patterns

**Created**: 2025-12-12  
**Status**: Planning Document  
**Purpose**: Define reliable communication patterns between sandbox agents and the backend

---

## Problem Statement

Using MCP (Model Context Protocol) for all agent-backend communication creates reliability issues:

1. **Network Fragility**: MCP connections can fail, causing cascading issues
2. **Blocking Operations**: If MCP gets stuck, agents can't report progress or get tasks
3. **Complexity**: MCP adds overhead for simple CRUD operations
4. **Debugging**: MCP issues are harder to diagnose than HTTP failures

---

## Solution: Hybrid Communication

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    COMMUNICATION PATTERN SEPARATION                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────┐                      ┌─────────────────────┐      │
│  │   Sandbox Agent     │                      │      Backend        │      │
│  │   (Daytona)         │                      │      Server         │      │
│  └─────────────────────┘                      └─────────────────────┘      │
│           │                                            │                    │
│           │                                            │                    │
│           ├─── HTTP (REST API) ───────────────────────►│                    │
│           │    • Get assigned tasks                    │                    │
│           │    • Update task status                    │                    │
│           │    • Report progress/events                │                    │
│           │    • Submit results                        │                    │
│           │    • Heartbeats                            │                    │
│           │                                            │                    │
│           ├─── MCP (Tools Only) ──────────────────────►│                    │
│           │    • AI-specific tool invocations          │                    │
│           │    • Complex reasoning operations          │                    │
│           │    • (Optional, can be removed entirely)   │                    │
│           │                                            │                    │
│           ◄─── WebSocket (Events) ────────────────────┤                    │
│                • Real-time notifications               │                    │
│                • Task assignments                      │                    │
│                • System broadcasts                     │                    │
│                                                        │                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## HTTP API for Sandbox Agents

### Base URL
```
{BACKEND_URL}/api/v1/sandbox
```

### Authentication
Sandbox agents authenticate using a **sandbox token** issued when the sandbox is created:
```
Authorization: Bearer {sandbox_token}
```

---

### Endpoints

#### 1. Get Assigned Task

```http
GET /api/v1/sandbox/task
Authorization: Bearer {sandbox_token}
```

**Response:**
```json
{
  "task_id": "task-abc123",
  "ticket_id": "TICKET-456",
  "title": "Implement dark mode toggle",
  "description": "Add a dark mode toggle to the settings page...",
  "type": "feature",
  "priority": "medium",
  "context": {
    "project_id": "proj-xyz",
    "github_repo": "owner/repo",
    "branch_name": "feature/TICKET-456-dark-mode",
    "relevant_files": ["src/components/Settings.tsx"]
  },
  "constraints": {
    "time_limit_minutes": 60,
    "allowed_tools": ["read_file", "write_file", "bash"]
  }
}
```

#### 2. Update Task Status

```http
PATCH /api/v1/sandbox/task/{task_id}/status
Authorization: Bearer {sandbox_token}
Content-Type: application/json

{
  "status": "in_progress",  // "pending", "in_progress", "completed", "failed", "blocked"
  "message": "Starting implementation..."
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "task-abc123",
  "status": "in_progress",
  "updated_at": "2025-12-12T10:30:00Z"
}
```

#### 3. Report Progress

```http
POST /api/v1/sandbox/task/{task_id}/progress
Authorization: Bearer {sandbox_token}
Content-Type: application/json

{
  "event_type": "step_completed",  // "step_completed", "file_modified", "error", "info"
  "message": "Created Settings.tsx component",
  "details": {
    "files_modified": ["src/components/Settings.tsx"],
    "lines_added": 45,
    "lines_removed": 0
  },
  "progress_percent": 50
}
```

**Response:**
```json
{
  "success": true,
  "event_id": "evt-123"
}
```

#### 4. Submit Results

```http
POST /api/v1/sandbox/task/{task_id}/results
Authorization: Bearer {sandbox_token}
Content-Type: application/json

{
  "status": "completed",  // "completed", "failed", "partial"
  "summary": "Implemented dark mode toggle with user preference persistence",
  "files_changed": [
    {
      "path": "src/components/Settings.tsx",
      "action": "created",
      "lines_added": 45
    },
    {
      "path": "src/hooks/useTheme.ts",
      "action": "modified",
      "lines_added": 12,
      "lines_removed": 3
    }
  ],
  "commits": [
    {
      "sha": "abc123",
      "message": "feat: add dark mode toggle"
    }
  ],
  "tests_passed": true,
  "notes": "Ready for review"
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "task-abc123",
  "next_action": "create_pr"  // or "await_review", "continue", null
}
```

#### 5. Heartbeat

```http
POST /api/v1/sandbox/heartbeat
Authorization: Bearer {sandbox_token}
Content-Type: application/json

{
  "sandbox_id": "sandbox-xyz",
  "task_id": "task-abc123",
  "status": "active",
  "metrics": {
    "cpu_percent": 45,
    "memory_mb": 512,
    "uptime_seconds": 3600
  }
}
```

**Response:**
```json
{
  "success": true,
  "commands": []  // Optional commands from backend: ["pause", "resume", "abort"]
}
```

#### 6. Request Human Review

```http
POST /api/v1/sandbox/task/{task_id}/review
Authorization: Bearer {sandbox_token}
Content-Type: application/json

{
  "reason": "merge_conflict",
  "description": "Encountered merge conflict in Settings.tsx that requires human decision",
  "context": {
    "conflicting_files": ["src/components/Settings.tsx"],
    "options": [
      {"id": "keep_ours", "description": "Keep the agent's changes"},
      {"id": "keep_theirs", "description": "Keep the main branch changes"},
      {"id": "manual", "description": "Resolve manually"}
    ]
  },
  "blocking": true
}
```

---

## Worker Script HTTP Client

```python
# sandbox_worker.py - HTTP client for sandbox agents

import os
import httpx
from typing import Optional, Any
from pydantic import BaseModel


class SandboxClient:
    """HTTP client for sandbox agent communication."""
    
    def __init__(self):
        self.base_url = os.environ["BACKEND_URL"]
        self.token = os.environ["SANDBOX_TOKEN"]
        self.sandbox_id = os.environ["SANDBOX_ID"]
        self.task_id: Optional[str] = None
        
        self.client = httpx.Client(
            base_url=f"{self.base_url}/api/v1/sandbox",
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=30.0,
        )
    
    def get_task(self) -> dict:
        """Fetch the assigned task."""
        response = self.client.get("/task")
        response.raise_for_status()
        task = response.json()
        self.task_id = task["task_id"]
        return task
    
    def update_status(self, status: str, message: str = "") -> dict:
        """Update task status."""
        response = self.client.patch(
            f"/task/{self.task_id}/status",
            json={"status": status, "message": message}
        )
        response.raise_for_status()
        return response.json()
    
    def report_progress(
        self,
        event_type: str,
        message: str,
        details: Optional[dict] = None,
        progress_percent: Optional[int] = None,
    ) -> dict:
        """Report progress event."""
        payload = {
            "event_type": event_type,
            "message": message,
        }
        if details:
            payload["details"] = details
        if progress_percent is not None:
            payload["progress_percent"] = progress_percent
            
        response = self.client.post(
            f"/task/{self.task_id}/progress",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def submit_results(
        self,
        status: str,
        summary: str,
        files_changed: list[dict],
        commits: list[dict] = [],
        tests_passed: bool = True,
        notes: str = "",
    ) -> dict:
        """Submit task results."""
        response = self.client.post(
            f"/task/{self.task_id}/results",
            json={
                "status": status,
                "summary": summary,
                "files_changed": files_changed,
                "commits": commits,
                "tests_passed": tests_passed,
                "notes": notes,
            }
        )
        response.raise_for_status()
        return response.json()
    
    def heartbeat(self, metrics: Optional[dict] = None) -> dict:
        """Send heartbeat."""
        response = self.client.post(
            "/heartbeat",
            json={
                "sandbox_id": self.sandbox_id,
                "task_id": self.task_id,
                "status": "active",
                "metrics": metrics or {},
            }
        )
        response.raise_for_status()
        return response.json()
    
    def request_review(
        self,
        reason: str,
        description: str,
        context: dict,
        blocking: bool = True,
    ) -> dict:
        """Request human review."""
        response = self.client.post(
            f"/task/{self.task_id}/review",
            json={
                "reason": reason,
                "description": description,
                "context": context,
                "blocking": blocking,
            }
        )
        response.raise_for_status()
        return response.json()


# Usage in worker script
client = SandboxClient()

# Get task
task = client.get_task()
print(f"Working on: {task['title']}")

# Update status
client.update_status("in_progress", "Starting work...")

# Report progress
client.report_progress(
    event_type="step_completed",
    message="Analyzed codebase structure",
    progress_percent=20
)

# ... do work ...

# Submit results
client.submit_results(
    status="completed",
    summary="Implemented the feature",
    files_changed=[{"path": "src/foo.ts", "action": "modified"}],
)
```

---

## Backend Routes

```python
# backend/omoi_os/api/routes/sandbox.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from omoi_os.api.dependencies import get_sandbox_from_token
from omoi_os.services.task_service import TaskService
from omoi_os.services.event_bus import EventBusService


router = APIRouter(prefix="/sandbox", tags=["sandbox"])


class StatusUpdate(BaseModel):
    status: str
    message: str = ""


class ProgressEvent(BaseModel):
    event_type: str
    message: str
    details: Optional[dict] = None
    progress_percent: Optional[int] = None


class ResultSubmission(BaseModel):
    status: str
    summary: str
    files_changed: list[dict]
    commits: list[dict] = []
    tests_passed: bool = True
    notes: str = ""


class Heartbeat(BaseModel):
    sandbox_id: str
    task_id: Optional[str] = None
    status: str
    metrics: dict = {}


class ReviewRequest(BaseModel):
    reason: str
    description: str
    context: dict
    blocking: bool = True


@router.get("/task")
async def get_assigned_task(
    sandbox = Depends(get_sandbox_from_token),
    task_service: TaskService = Depends(),
):
    """Get the task assigned to this sandbox."""
    task = await task_service.get_task_for_sandbox(sandbox.id)
    if not task:
        raise HTTPException(status_code=404, detail="No task assigned")
    return task


@router.patch("/task/{task_id}/status")
async def update_task_status(
    task_id: str,
    update: StatusUpdate,
    sandbox = Depends(get_sandbox_from_token),
    task_service: TaskService = Depends(),
    event_bus: EventBusService = Depends(),
):
    """Update task status."""
    # Verify sandbox owns this task
    await task_service.verify_sandbox_owns_task(sandbox.id, task_id)
    
    result = await task_service.update_status(
        task_id=task_id,
        status=update.status,
        message=update.message,
    )
    
    # Broadcast event
    event_bus.publish_task_event(
        task_id=task_id,
        event_type="STATUS_CHANGED",
        data={"status": update.status, "message": update.message},
    )
    
    return result


@router.post("/task/{task_id}/progress")
async def report_progress(
    task_id: str,
    event: ProgressEvent,
    sandbox = Depends(get_sandbox_from_token),
    task_service: TaskService = Depends(),
    event_bus: EventBusService = Depends(),
):
    """Report progress on a task."""
    await task_service.verify_sandbox_owns_task(sandbox.id, task_id)
    
    result = await task_service.record_progress(
        task_id=task_id,
        event_type=event.event_type,
        message=event.message,
        details=event.details,
        progress_percent=event.progress_percent,
    )
    
    # Broadcast to subscribers
    event_bus.publish_task_event(
        task_id=task_id,
        event_type="PROGRESS",
        data={
            "event_type": event.event_type,
            "message": event.message,
            "progress_percent": event.progress_percent,
        },
    )
    
    return result


@router.post("/task/{task_id}/results")
async def submit_results(
    task_id: str,
    results: ResultSubmission,
    sandbox = Depends(get_sandbox_from_token),
    task_service: TaskService = Depends(),
    event_bus: EventBusService = Depends(),
):
    """Submit task results."""
    await task_service.verify_sandbox_owns_task(sandbox.id, task_id)
    
    result = await task_service.submit_results(
        task_id=task_id,
        status=results.status,
        summary=results.summary,
        files_changed=results.files_changed,
        commits=results.commits,
        tests_passed=results.tests_passed,
        notes=results.notes,
    )
    
    event_bus.publish_task_event(
        task_id=task_id,
        event_type="RESULTS_SUBMITTED",
        data={"status": results.status, "summary": results.summary},
    )
    
    return result


@router.post("/heartbeat")
async def heartbeat(
    data: Heartbeat,
    sandbox = Depends(get_sandbox_from_token),
    task_service: TaskService = Depends(),
):
    """Receive heartbeat from sandbox."""
    await task_service.record_heartbeat(
        sandbox_id=data.sandbox_id,
        task_id=data.task_id,
        status=data.status,
        metrics=data.metrics,
    )
    
    # Check for pending commands
    commands = await task_service.get_pending_commands(data.sandbox_id)
    
    return {"success": True, "commands": commands}


@router.post("/task/{task_id}/review")
async def request_review(
    task_id: str,
    request: ReviewRequest,
    sandbox = Depends(get_sandbox_from_token),
    task_service: TaskService = Depends(),
    event_bus: EventBusService = Depends(),
):
    """Request human review for a task."""
    await task_service.verify_sandbox_owns_task(sandbox.id, task_id)
    
    result = await task_service.request_review(
        task_id=task_id,
        reason=request.reason,
        description=request.description,
        context=request.context,
        blocking=request.blocking,
    )
    
    event_bus.publish_task_event(
        task_id=task_id,
        event_type="REVIEW_REQUESTED",
        data={
            "reason": request.reason,
            "description": request.description,
            "blocking": request.blocking,
        },
    )
    
    return result
```

---

## Benefits of HTTP over MCP

| Aspect | HTTP | MCP |
|--------|------|-----|
| **Reliability** | Battle-tested, simple retry logic | Complex connection management |
| **Debugging** | Standard HTTP tools (curl, Postman) | Requires MCP-specific tooling |
| **Timeouts** | Easy to configure per-request | Connection-level, harder to manage |
| **Load Balancing** | Standard infrastructure | Requires sticky sessions |
| **Error Handling** | HTTP status codes are universal | Custom error propagation |
| **Caching** | HTTP caching headers | Not applicable |
| **Monitoring** | Standard APM tools | Custom instrumentation needed |

---

## When to Still Use MCP

MCP is still valuable for:

1. **AI Tool Invocations**: When the agent needs to call complex tools that benefit from MCP's structured approach
2. **Streaming Responses**: Long-running operations with streaming output
3. **IDE Integration**: If agents interact with IDEs that speak MCP

For this project, **MCP is optional** - all critical functionality works via HTTP.

---

## Migration Path

If currently using MCP for everything:

1. **Phase 1**: Add HTTP endpoints alongside MCP
2. **Phase 2**: Update worker scripts to use HTTP for task/status operations
3. **Phase 3**: Keep MCP only for tool invocations (or remove entirely)
4. **Phase 4**: Deprecate MCP task management endpoints

---

## Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COMMUNICATION SUMMARY                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  USE HTTP FOR:                        USE WEBSOCKET FOR:                    │
│  ├─ Getting tasks                     ├─ Real-time events to frontend      │
│  ├─ Updating status                   ├─ Task assignment notifications     │
│  ├─ Reporting progress                └─ Live progress updates             │
│  ├─ Submitting results                                                     │
│  ├─ Heartbeats                        USE MCP FOR (OPTIONAL):              │
│  └─ Requesting review                 └─ AI tool invocations only          │
│                                                                             │
│  HTTP is:                                                                   │
│  ├─ More reliable                                                          │
│  ├─ Easier to debug                                                        │
│  ├─ Simpler to implement                                                   │
│  └─ Industry standard                                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Hook-Based Message Injection Pattern

### Why Hooks?

The polling-based pattern (GET `/messages` after each turn) introduces latency. For time-sensitive interventions like Guardian steering, we need **immediate injection**.

### Pattern: PreToolUse Hook Injection

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HOOK-BASED INJECTION FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Guardian/User enqueues intervention                                     │
│     POST /api/v1/sandboxes/{id}/interventions                              │
│     { message, source, priority, inject_mode: "immediate" }                 │
│                                                                             │
│  2. Server stores in fast-access storage (Redis)                            │
│     LPUSH sandbox:{id}:interventions {...}                                  │
│                                                                             │
│  3. Agent about to execute tool → PreToolUse hook fires                    │
│                                                                             │
│  4. Hook checks for pending interventions                                   │
│     a. In-memory queue (instant)                                            │
│     b. Server poll (every N calls, fills in-memory queue)                   │
│                                                                             │
│  5. If intervention found:                                                  │
│     Claude: Return {reason, systemMessage} → Claude receives context       │
│     OpenHands: Call conversation.send_message() → Agent sees on next iter  │
│                                                                             │
│  TIMING: Intervention delivered BEFORE tool executes                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### API Addition

```http
POST /api/v1/sandboxes/{sandbox_id}/interventions
Authorization: Bearer {sandbox_token}

{
  "message": "Focus on the API endpoint, not the tests",
  "source": "guardian",
  "priority": "normal",
  "inject_mode": "immediate"
}
```

**Response:**
```json
{
  "id": "int-abc123",
  "status": "queued",
  "inject_mode": "immediate",
  "estimated_delivery_ms": 50
}
```

### Backward Compatibility

The existing `/messages` endpoint continues to work for polling-based injection.
The new `/interventions` endpoint is optimized for hook-based immediate injection.
