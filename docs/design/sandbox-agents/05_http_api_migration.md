# HTTP API Migration Guide

> **Goal**: Replace MCP tool calls with HTTP calls for reliable sandbox-to-server communication.

## Quick Summary

| Category | MCP Tools | HTTP Exists | Need to Add |
|----------|-----------|-------------|-------------|
| Tickets | 12 | 8 | 4 |
| Tasks | 5 | 3 | 2 |
| Discovery | 3 | 0 | 3 |
| Collaboration | 4 | 4 | 0 |
| History | 3 | 0 | 3 |
| **Total** | **27** | **15** | **12** |

---

## Part 1: MCP → HTTP Mapping

### Tickets

| MCP Tool | HTTP Endpoint | Status |
|----------|---------------|--------|
| `create_ticket` | `POST /api/v1/tickets` | ✅ EXISTS |
| `get_ticket` | `GET /api/v1/tickets/{id}` | ✅ EXISTS |
| `get_tickets` | `GET /api/v1/tickets` | ✅ EXISTS |
| `update_ticket` | `PATCH /api/v1/tickets/{id}` | ❌ ADD |
| `change_ticket_status` | `POST /api/v1/tickets/{id}/transition` | ✅ EXISTS |
| `search_tickets` | `POST /api/v1/tickets/search` | ❌ ADD |
| `get_ticket_history` | `GET /api/v1/tickets/{id}/history` | ❌ ADD |
| `resolve_ticket` | `POST /api/v1/tickets/{id}/resolve` | ❌ ADD |
| `add_ticket_comment` | `POST /api/v1/tickets/{id}/comments` | ❌ ADD |
| `link_commit` | `POST /api/v1/tickets/{id}/commits` | ❌ ADD |
| `add_ticket_dependency` | `POST /api/v1/tickets/{id}/blockers` | ❌ ADD |
| `remove_ticket_dependency` | `DELETE /api/v1/tickets/{id}/blockers/{blocker_id}` | ❌ ADD |

### Tasks

| MCP Tool | HTTP Endpoint | Status |
|----------|---------------|--------|
| `get_task` | `GET /api/v1/tasks/{id}` | ✅ EXISTS |
| `create_task` | `POST /api/v1/tasks` | ❌ ADD |
| `update_task_status` | `PATCH /api/v1/tasks/{id}/status` | ❌ ADD |
| `register_conversation` | `POST /api/v1/tasks/{id}/register-conversation` | ✅ EXISTS |
| `report_agent_event` | `POST /api/v1/tasks/{id}/events` | ❌ ADD |

### Discovery

| MCP Tool | HTTP Endpoint | Status |
|----------|---------------|--------|
| `get_task_discoveries` | `GET /api/v1/tasks/{id}/discoveries` | ❌ ADD |
| `get_workflow_graph` | `GET /api/v1/tickets/{id}/workflow-graph` | ❌ ADD |
| `get_discoveries_by_type` | `GET /api/v1/discoveries?type={type}` | ❌ ADD |

### Collaboration (All Exist!)

| MCP Tool | HTTP Endpoint | Status |
|----------|---------------|--------|
| `send_message` | `POST /api/v1/collaboration/messages` | ✅ EXISTS |
| `get_messages` | `GET /api/v1/collaboration/threads/{id}/messages` | ✅ EXISTS |
| `broadcast_message` | `POST /api/v1/collaboration/broadcast` | ❌ ADD |
| `request_handoff` | `POST /api/v1/collaboration/handoff/request` | ✅ EXISTS |

### History

| MCP Tool | HTTP Endpoint | Status |
|----------|---------------|--------|
| `get_phase_history` | `GET /api/v1/tickets/{id}/phase-history` | ❌ ADD |
| `get_task_timeline` | `GET /api/v1/tasks/{id}/timeline` | ❌ ADD |
| `get_agent_trajectory` | `GET /api/v1/agents/{id}/trajectory` | ❌ ADD |

---

## Part 2: New HTTP Routes to Add

### File: `backend/omoi_os/api/routes/tickets.py`

Add these endpoints to the existing file:

```python
# ============================================================================
# NEW ENDPOINTS TO ADD
# ============================================================================

class UpdateTicketRequest(BaseModel):
    """Request for updating ticket fields."""
    updates: dict  # {field: value}
    agent_id: str
    comment: str | None = None


class SearchTicketsRequest(BaseModel):
    """Request for ticket search."""
    query: str
    search_type: str = "hybrid"  # semantic, keyword, hybrid
    workflow_id: str | None = None
    filters: dict = {}
    limit: int = 10


class AddCommentRequest(BaseModel):
    """Request for adding a comment."""
    agent_id: str
    comment_text: str
    comment_type: str = "general"


class LinkCommitRequest(BaseModel):
    """Request for linking a commit."""
    agent_id: str
    commit_sha: str
    commit_message: str | None = None


class ResolveTicketRequest(BaseModel):
    """Request for resolving a ticket."""
    agent_id: str
    resolution_comment: str
    commit_sha: str | None = None


class AddBlockerRequest(BaseModel):
    """Request for adding a blocker."""
    agent_id: str
    blocked_by_ticket_id: str


@router.patch("/{ticket_id}")
async def update_ticket(
    ticket_id: UUID,
    request: UpdateTicketRequest,
    db: DatabaseService = Depends(get_db_service),
):
    """Update ticket fields."""
    from omoi_os.ticketing.services.ticket_service import TicketService
    
    with db.get_session() as session:
        svc = TicketService(session)
        result = svc.update_ticket(
            ticket_id=str(ticket_id),
            agent_id=request.agent_id,
            updates=request.updates,
            update_comment=request.comment,
        )
        return result


@router.post("/search")
async def search_tickets(
    request: SearchTicketsRequest,
    db: DatabaseService = Depends(get_db_service),
):
    """Search tickets using semantic/keyword/hybrid search."""
    from omoi_os.ticketing.services.ticket_search_service import TicketSearchService
    
    with db.get_session() as session:
        svc = TicketSearchService(session)
        
        if request.search_type == "semantic":
            return svc.semantic_search(
                query_text=request.query,
                workflow_id=request.workflow_id,
                limit=request.limit,
                filters=request.filters,
            )
        elif request.search_type == "keyword":
            return svc.search_by_keywords(
                keywords=request.query,
                workflow_id=request.workflow_id,
                filters=request.filters,
            )
        else:  # hybrid
            return svc.hybrid_search(
                query_text=request.query,
                workflow_id=request.workflow_id,
                limit=request.limit,
                filters=request.filters,
            )


@router.get("/{ticket_id}/history")
async def get_ticket_history(
    ticket_id: UUID,
    db: DatabaseService = Depends(get_db_service),
):
    """Get ticket change history."""
    from omoi_os.ticketing.services.ticket_history_service import TicketHistoryService
    
    with db.get_session() as session:
        svc = TicketHistoryService(session)
        history = svc.get_ticket_history(ticket_id=str(ticket_id))
        return {"ticket_id": str(ticket_id), "history": history}


@router.post("/{ticket_id}/resolve")
async def resolve_ticket(
    ticket_id: UUID,
    request: ResolveTicketRequest,
    db: DatabaseService = Depends(get_db_service),
):
    """Resolve a ticket and unblock dependents."""
    from omoi_os.ticketing.services.ticket_service import TicketService
    
    with db.get_session() as session:
        svc = TicketService(session)
        result = svc.resolve_ticket(
            ticket_id=str(ticket_id),
            agent_id=request.agent_id,
            resolution_comment=request.resolution_comment,
            commit_sha=request.commit_sha,
        )
        return result


@router.post("/{ticket_id}/comments")
async def add_ticket_comment(
    ticket_id: UUID,
    request: AddCommentRequest,
    db: DatabaseService = Depends(get_db_service),
):
    """Add a comment to a ticket."""
    from omoi_os.ticketing.services.ticket_service import TicketService
    
    with db.get_session() as session:
        svc = TicketService(session)
        result = svc.add_comment(
            ticket_id=str(ticket_id),
            agent_id=request.agent_id,
            comment_text=request.comment_text,
            comment_type=request.comment_type,
        )
        return result


@router.post("/{ticket_id}/commits")
async def link_commit_to_ticket(
    ticket_id: UUID,
    request: LinkCommitRequest,
    db: DatabaseService = Depends(get_db_service),
):
    """Link a git commit to a ticket."""
    from omoi_os.ticketing.services.ticket_service import TicketService
    
    with db.get_session() as session:
        svc = TicketService(session)
        result = svc.link_commit(
            ticket_id=str(ticket_id),
            agent_id=request.agent_id,
            commit_sha=request.commit_sha,
            commit_message=request.commit_message,
        )
        return result


@router.post("/{ticket_id}/blockers")
async def add_ticket_blocker(
    ticket_id: UUID,
    request: AddBlockerRequest,
    db: DatabaseService = Depends(get_db_service),
):
    """Add a blocker dependency to a ticket."""
    # Implementation uses same logic as MCP add_ticket_dependency
    from omoi_os.ticketing.models import Ticket as TicketingTicket
    from omoi_os.ticketing.services.ticket_history_service import TicketHistoryService
    
    with db.get_session() as session:
        ticket = session.get(TicketingTicket, str(ticket_id))
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        blockers = (ticket.blocked_by_ticket_ids or {}).get("ids", [])
        if request.blocked_by_ticket_id not in blockers:
            blockers.append(request.blocked_by_ticket_id)
            ticket.blocked_by_ticket_ids = {"ids": blockers}
            
            history_svc = TicketHistoryService(session)
            history_svc.record_change(
                ticket_id=str(ticket_id),
                agent_id=request.agent_id,
                change_type="dependency_added",
                field_name="blocked_by_ticket_ids",
                old_value=None,
                new_value=request.blocked_by_ticket_id,
            )
            session.commit()
        
        return {"ticket_id": str(ticket_id), "blocked_by": blockers}


@router.delete("/{ticket_id}/blockers/{blocker_id}")
async def remove_ticket_blocker(
    ticket_id: UUID,
    blocker_id: str,
    agent_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Remove a blocker dependency from a ticket."""
    from omoi_os.ticketing.models import Ticket as TicketingTicket
    
    with db.get_session() as session:
        ticket = session.get(TicketingTicket, str(ticket_id))
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        blockers = (ticket.blocked_by_ticket_ids or {}).get("ids", [])
        blockers = [b for b in blockers if b != blocker_id]
        ticket.blocked_by_ticket_ids = {"ids": blockers} if blockers else None
        session.commit()
        
        return {"ticket_id": str(ticket_id), "blocked_by": blockers}


@router.get("/{ticket_id}/phase-history")
async def get_phase_history(
    ticket_id: UUID,
    db: DatabaseService = Depends(get_db_service),
):
    """Get phase transition history for a ticket."""
    from omoi_os.models.phase_history import PhaseHistory
    from sqlalchemy import select
    
    with db.get_session() as session:
        stmt = (
            select(PhaseHistory)
            .where(PhaseHistory.ticket_id == str(ticket_id))
            .order_by(PhaseHistory.created_at.asc())
        )
        history = list(session.execute(stmt).scalars().all())
        
        return {
            "ticket_id": str(ticket_id),
            "phase_history": [
                {
                    "from_phase": h.from_phase_id,
                    "to_phase": h.to_phase_id,
                    "reason": h.reason,
                    "created_at": h.created_at.isoformat() if h.created_at else None,
                }
                for h in history
            ],
        }


@router.get("/{ticket_id}/workflow-graph")
async def get_workflow_graph(
    ticket_id: UUID,
    db: DatabaseService = Depends(get_db_service),
    discovery_service = Depends(get_discovery_service),  # Add to dependencies
):
    """Get workflow branching graph for a ticket."""
    with db.get_session() as session:
        graph = discovery_service.get_workflow_graph(
            session=session,
            ticket_id=str(ticket_id),
        )
        return {"ticket_id": str(ticket_id), **graph}
```

### File: `backend/omoi_os/api/routes/tasks.py`

Add these endpoints to the existing file:

```python
# ============================================================================
# NEW ENDPOINTS TO ADD
# ============================================================================

class CreateTaskRequest(BaseModel):
    """Request for creating a task."""
    ticket_id: str
    phase_id: str
    description: str
    task_type: str = "implementation"
    priority: str = "MEDIUM"
    discovery_type: str | None = None
    source_task_id: str | None = None
    dependencies: list[str] = []


class UpdateTaskStatusRequest(BaseModel):
    """Request for updating task status."""
    status: str  # pending, running, completed, failed
    result: dict | None = None
    error_message: str | None = None


class ReportEventRequest(BaseModel):
    """Request for reporting an agent event."""
    agent_id: str
    event_type: str
    event_data: dict = {}


@router.post("")
async def create_task(
    request: CreateTaskRequest,
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
    discovery_service = Depends(get_discovery_service),
):
    """Create a new task with optional discovery tracking."""
    with db.get_session() as session:
        # Create the task
        deps_dict = {"depends_on": request.dependencies} if request.dependencies else None
        
        task = queue.enqueue_task(
            ticket_id=request.ticket_id,
            phase_id=request.phase_id,
            task_type=request.task_type,
            description=request.description,
            priority=request.priority,
            dependencies=deps_dict,
            session=session,
        )
        
        result = {
            "task_id": str(task.id),
            "ticket_id": request.ticket_id,
            "status": task.status,
        }
        
        # If this is a discovery-based task, record it
        if request.discovery_type and request.source_task_id and discovery_service:
            discovery, spawned = discovery_service.record_discovery_and_branch(
                session=session,
                source_task_id=request.source_task_id,
                discovery_type=request.discovery_type,
                description=request.description,
                spawn_phase_id=request.phase_id,
                spawn_description=request.description,
                spawn_priority=request.priority,
            )
            result["discovery_id"] = str(discovery.id)
        
        session.commit()
        return result


@router.patch("/{task_id}/status")
async def update_task_status(
    task_id: str,
    request: UpdateTaskStatusRequest,
    queue: TaskQueueService = Depends(get_task_queue),
):
    """Update task status and result."""
    queue.update_task_status(
        task_id=task_id,
        status=request.status,
        result=request.result,
        error_message=request.error_message,
    )
    return {"task_id": task_id, "status": request.status}


@router.post("/{task_id}/events")
async def report_agent_event(
    task_id: str,
    request: ReportEventRequest,
    db: DatabaseService = Depends(get_db_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """Report an agent event for Guardian observation."""
    from omoi_os.models.agent_log import AgentLog
    
    with db.get_session() as session:
        log_entry = AgentLog(
            agent_id=request.agent_id,
            log_type=request.event_type,
            message=request.event_data.get("message", "")[:500],
            details=request.event_data,
        )
        session.add(log_entry)
        session.commit()
    
    # Publish for real-time monitoring
    event_bus.publish(
        SystemEvent(
            event_type="AGENT_EVENT",
            entity_type="agent",
            entity_id=request.agent_id,
            payload={
                "task_id": task_id,
                "event_type": request.event_type,
                "event_data": request.event_data,
            },
        )
    )
    
    return {"success": True}


@router.get("/{task_id}/discoveries")
async def get_task_discoveries(
    task_id: str,
    db: DatabaseService = Depends(get_db_service),
    discovery_service = Depends(get_discovery_service),
):
    """Get discoveries made by a task."""
    with db.get_session() as session:
        discoveries = discovery_service.get_discoveries_by_task(
            session=session,
            task_id=task_id,
        )
        return {
            "task_id": task_id,
            "discoveries": [
                {
                    "discovery_id": str(d.id),
                    "discovery_type": d.discovery_type,
                    "description": d.description,
                    "spawned_task_ids": d.spawned_task_ids,
                }
                for d in discoveries
            ],
        }


@router.get("/{task_id}/timeline")
async def get_task_timeline(
    task_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Get execution timeline for a task."""
    from omoi_os.models.task import Task
    
    with db.get_session() as session:
        task = session.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        duration = None
        if task.started_at and task.completed_at:
            duration = (task.completed_at - task.started_at).total_seconds()
        
        return {
            "task_id": task_id,
            "status": task.status,
            "timing": {
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "duration_seconds": duration,
            },
            "execution": {
                "retry_count": task.retry_count,
                "error_message": task.error_message,
                "conversation_id": task.conversation_id,
            },
        }
```

### File: `backend/omoi_os/api/routes/collaboration.py`

Add this endpoint:

```python
# ============================================================================
# NEW ENDPOINT TO ADD
# ============================================================================

class BroadcastRequest(BaseModel):
    """Request for broadcasting a message."""
    sender_agent_id: str
    message: str
    message_type: str = "info"
    ticket_id: str | None = None
    task_id: str | None = None


@router.post("/collaboration/broadcast")
async def broadcast_message(
    request: BroadcastRequest,
    collab_service: CollaborationService = Depends(get_collaboration_service),
):
    """Broadcast a message to all active agents."""
    result = collab_service.broadcast_message(
        from_agent_id=request.sender_agent_id,
        message=request.message,
        message_type=request.message_type,
        ticket_id=request.ticket_id,
        task_id=request.task_id,
    )
    return result
```

### File: `backend/omoi_os/api/routes/agents.py`

Add this endpoint:

```python
# ============================================================================
# NEW ENDPOINT TO ADD
# ============================================================================

@router.get("/{agent_id}/trajectory")
async def get_agent_trajectory(
    agent_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Get agent's accumulated context and trajectory."""
    from omoi_os.services.trajectory_context import TrajectoryContext
    from omoi_os.models.agent import Agent
    
    with db.get_session() as session:
        agent = session.get(Agent, agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        trajectory_ctx = TrajectoryContext(db=db)
        
        try:
            context = trajectory_ctx.build_accumulated_context(agent_id=agent_id)
            summary = trajectory_ctx.get_trajectory_summary(agent_id)
            
            return {
                "agent_id": agent_id,
                "status": agent.status,
                "summary": summary,
                "overall_goal": context.get("overall_goal"),
                "current_focus": context.get("current_focus"),
                "constraints": context.get("constraints", []),
                "discovered_blockers": context.get("discovered_blockers", []),
            }
        except Exception:
            return {
                "agent_id": agent_id,
                "status": agent.status,
                "summary": f"Agent {agent_id[:8]}...",
            }
```

### File: `backend/omoi_os/api/routes/discoveries.py` (NEW FILE)

```python
"""Discovery API routes."""

from fastapi import APIRouter, Depends

from omoi_os.api.dependencies import get_db_service, get_discovery_service
from omoi_os.services.database import DatabaseService

router = APIRouter()


@router.get("")
async def get_discoveries_by_type(
    discovery_type: str,
    limit: int = 50,
    db: DatabaseService = Depends(get_db_service),
    discovery_service = Depends(get_discovery_service),
):
    """Get all discoveries of a specific type."""
    with db.get_session() as session:
        discoveries = discovery_service.get_discoveries_by_type(
            session=session,
            discovery_type=discovery_type,
            limit=limit,
        )
        return {
            "discovery_type": discovery_type,
            "count": len(discoveries),
            "discoveries": [
                {
                    "discovery_id": str(d.id),
                    "source_task_id": d.source_task_id,
                    "description": d.description,
                    "spawned_task_ids": d.spawned_task_ids,
                    "resolution_status": d.resolution_status,
                }
                for d in discoveries
            ],
        }
```

---

## Part 3: Agent SDK Tools (HTTP-based)

### OpenHands SDK Example

```python
"""OpenHands tools that use HTTP instead of MCP."""

import httpx
from typing import Any, Dict, Optional
from pydantic import Field
from openhands.sdk.tool import ToolDefinition, ToolExecutor
from openhands.sdk.tool.schema import Action, Observation


# Configuration
BACKEND_URL = "http://localhost:18000/api/v1"


class HTTPObservation(Observation):
    """Generic observation for HTTP responses."""
    success: bool
    data: Any = None
    error: Optional[str] = None


# ============================================================================
# GET TICKET
# ============================================================================

class GetTicketAction(Action):
    ticket_id: str = Field(..., description="ID of ticket to get")


class GetTicketExecutor(ToolExecutor[GetTicketAction, HTTPObservation]):
    def __call__(self, action: GetTicketAction, conversation: Any = None) -> HTTPObservation:
        try:
            response = httpx.get(f"{BACKEND_URL}/tickets/{action.ticket_id}")
            response.raise_for_status()
            return HTTPObservation(success=True, data=response.json())
        except Exception as e:
            return HTTPObservation(success=False, error=str(e))


# ============================================================================
# CREATE TASK
# ============================================================================

class CreateTaskAction(Action):
    ticket_id: str = Field(..., description="Ticket ID")
    phase_id: str = Field(..., description="Phase ID")
    description: str = Field(..., description="Task description")
    priority: str = Field(default="MEDIUM")


class CreateTaskExecutor(ToolExecutor[CreateTaskAction, HTTPObservation]):
    def __call__(self, action: CreateTaskAction, conversation: Any = None) -> HTTPObservation:
        try:
            response = httpx.post(
                f"{BACKEND_URL}/tasks",
                json={
                    "ticket_id": action.ticket_id,
                    "phase_id": action.phase_id,
                    "description": action.description,
                    "priority": action.priority,
                },
            )
            response.raise_for_status()
            return HTTPObservation(success=True, data=response.json())
        except Exception as e:
            return HTTPObservation(success=False, error=str(e))


# ============================================================================
# UPDATE TASK STATUS
# ============================================================================

class UpdateTaskStatusAction(Action):
    task_id: str = Field(..., description="Task ID")
    status: str = Field(..., description="New status")
    result: Optional[Dict] = Field(default=None)
    error_message: Optional[str] = Field(default=None)


class UpdateTaskStatusExecutor(ToolExecutor[UpdateTaskStatusAction, HTTPObservation]):
    def __call__(self, action: UpdateTaskStatusAction, conversation: Any = None) -> HTTPObservation:
        try:
            response = httpx.patch(
                f"{BACKEND_URL}/tasks/{action.task_id}/status",
                json={
                    "status": action.status,
                    "result": action.result,
                    "error_message": action.error_message,
                },
            )
            response.raise_for_status()
            return HTTPObservation(success=True, data=response.json())
        except Exception as e:
            return HTTPObservation(success=False, error=str(e))


# ============================================================================
# TOOL REGISTRATION
# ============================================================================

def get_http_tools():
    """Get all HTTP-based tools for registration."""
    return [
        ToolDefinition(
            name="get_ticket",
            description="Get ticket details by ID",
            action_type=GetTicketAction,
            observation_type=HTTPObservation,
            executor=GetTicketExecutor(),
        ),
        ToolDefinition(
            name="create_task",
            description="Create a new task",
            action_type=CreateTaskAction,
            observation_type=HTTPObservation,
            executor=CreateTaskExecutor(),
        ),
        ToolDefinition(
            name="update_task_status",
            description="Update task status",
            action_type=UpdateTaskStatusAction,
            observation_type=HTTPObservation,
            executor=UpdateTaskStatusExecutor(),
        ),
        # ... add more as needed
    ]
```

### Claude Agent SDK Example

```python
"""Claude Agent SDK tools that use HTTP instead of MCP."""

import httpx
from anthropic import Agent


# Configuration
BACKEND_URL = "http://localhost:18000/api/v1"


# ============================================================================
# TOOL FUNCTIONS (Claude uses simple functions with @tool decorator)
# ============================================================================

def get_ticket(ticket_id: str) -> dict:
    """Get ticket details by ID.
    
    Args:
        ticket_id: The UUID of the ticket to retrieve
        
    Returns:
        Ticket details including title, description, status, and priority
    """
    response = httpx.get(f"{BACKEND_URL}/tickets/{ticket_id}")
    response.raise_for_status()
    return response.json()


def create_task(
    ticket_id: str,
    phase_id: str,
    description: str,
    priority: str = "MEDIUM",
) -> dict:
    """Create a new task for a ticket.
    
    Args:
        ticket_id: ID of the ticket this task belongs to
        phase_id: Phase ID (e.g., "PHASE_IMPLEMENTATION")
        description: What the task should accomplish
        priority: LOW, MEDIUM, HIGH, or CRITICAL
        
    Returns:
        Created task details including task_id
    """
    response = httpx.post(
        f"{BACKEND_URL}/tasks",
        json={
            "ticket_id": ticket_id,
            "phase_id": phase_id,
            "description": description,
            "priority": priority,
        },
    )
    response.raise_for_status()
    return response.json()


def update_task_status(
    task_id: str,
    status: str,
    result: dict | None = None,
    error_message: str | None = None,
) -> dict:
    """Update the status of a task.
    
    Args:
        task_id: ID of the task to update
        status: New status (pending, running, completed, failed)
        result: Optional result data for completed tasks
        error_message: Optional error message for failed tasks
        
    Returns:
        Updated task status
    """
    response = httpx.patch(
        f"{BACKEND_URL}/tasks/{task_id}/status",
        json={
            "status": status,
            "result": result,
            "error_message": error_message,
        },
    )
    response.raise_for_status()
    return response.json()


def send_message(
    thread_id: str,
    from_agent_id: str,
    content: str,
    message_type: str = "info",
    to_agent_id: str | None = None,
) -> dict:
    """Send a message in a collaboration thread.
    
    Args:
        thread_id: ID of the thread to send message in
        from_agent_id: Your agent ID
        content: Message content
        message_type: Type of message (info, question, etc.)
        to_agent_id: Optional recipient for direct messages
        
    Returns:
        Sent message details
    """
    response = httpx.post(
        f"{BACKEND_URL}/collaboration/messages",
        json={
            "thread_id": thread_id,
            "from_agent_id": from_agent_id,
            "content": content,
            "message_type": message_type,
            "to_agent_id": to_agent_id,
        },
    )
    response.raise_for_status()
    return response.json()


def report_event(
    task_id: str,
    agent_id: str,
    event_type: str,
    event_data: dict,
) -> dict:
    """Report an agent event for monitoring.
    
    Args:
        task_id: ID of the current task
        agent_id: Your agent ID
        event_type: Type of event (action, observation, error, etc.)
        event_data: Event details
        
    Returns:
        Success status
    """
    response = httpx.post(
        f"{BACKEND_URL}/tasks/{task_id}/events",
        json={
            "agent_id": agent_id,
            "event_type": event_type,
            "event_data": event_data,
        },
    )
    response.raise_for_status()
    return response.json()


# ============================================================================
# AGENT SETUP
# ============================================================================

def create_agent_with_tools(agent_id: str, task_id: str):
    """Create a Claude agent with HTTP-based tools."""
    
    # Create tools list
    tools = [
        get_ticket,
        create_task,
        update_task_status,
        send_message,
        report_event,
    ]
    
    # Create agent (pseudo-code - actual API may vary)
    agent = Agent(
        model="claude-sonnet-4-20250514",
        tools=tools,
        system=f"""You are an AI agent working on tasks.
        Your agent ID is: {agent_id}
        Your current task ID is: {task_id}
        
        Use the provided tools to:
        - Get ticket/task information
        - Update task status as you progress
        - Report events for monitoring
        - Communicate with other agents
        """,
    )
    
    return agent
```

---

## Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    SANDBOX (Daytona)                        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Worker Script                                       │   │
│  │                                                      │   │
│  │  # Initialize                                        │   │
│  │  BACKEND_URL = "http://backend:18000/api/v1"        │   │
│  │                                                      │   │
│  │  # Agent tools use HTTP                              │   │
│  │  @tool                                               │   │
│  │  def get_ticket(ticket_id):                          │   │
│  │      return httpx.get(f"{URL}/tickets/{id}")        │   │
│  │                                                      │   │
│  │  @tool                                               │   │
│  │  def update_status(task_id, status):                │   │
│  │      return httpx.patch(f"{URL}/tasks/{id}/status") │   │
│  │                                                      │   │
│  │  # Agent uses tools naturally                        │   │
│  │  agent.run(tools=[get_ticket, update_status, ...])  │   │
│  └─────────────────────────────────────────────────────┘   │
│                              │                              │
└──────────────────────────────┼──────────────────────────────┘
                               │ HTTP (httpx/requests)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND SERVER                            │
│                                                              │
│  FastAPI Routes                                              │
│  ├── /api/v1/tickets/*     (15 endpoints)                   │
│  ├── /api/v1/tasks/*       (16 endpoints)                   │
│  ├── /api/v1/collaboration/* (10 endpoints)                 │
│  ├── /api/v1/agents/*      (+ trajectory)                   │
│  └── /api/v1/discoveries/* (new)                            │
│                              │                              │
│                              ▼                              │
│  Internal Services (unchanged)                              │
│  ├── TicketService                                          │
│  ├── TaskQueueService                                       │
│  ├── DiscoveryService                                       │
│  └── CollaborationService                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Checklist

### Phase 1: Add Missing HTTP Routes (1-2 hours)
- [ ] Add 8 new ticket endpoints to `routes/tickets.py`
- [ ] Add 5 new task endpoints to `routes/tasks.py`
- [ ] Add 1 new collaboration endpoint
- [ ] Add 1 new agent endpoint
- [ ] Create new `routes/discoveries.py`
- [ ] Register new router in `api/main.py`

### Phase 2: Create SDK Tools (1-2 hours)
- [ ] Create `backend/omoi_os/tools/http_tools.py` (OpenHands)
- [ ] Create `backend/omoi_os/tools/claude_http_tools.py` (Claude)
- [ ] Test tools against running backend

### Phase 3: Update Worker Scripts (30 min)
- [ ] Update sandbox worker to use HTTP tools
- [ ] Remove MCP client dependency from workers

---

## Key Benefits

1. **Reliability**: HTTP is stateless - no connection management issues
2. **Debugging**: Easy to test with curl, Postman, browser
3. **Simplicity**: Standard REST patterns everyone knows
4. **Retries**: Built-in retry logic with httpx/requests
5. **Logging**: Easy to log all requests/responses



