"""Debug API routes for testing and development.

These endpoints provide visibility into system state and allow manual
triggering of various behaviors for testing purposes.

WARNING: These endpoints are intended for development/testing only.
In production, they should be protected or disabled.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from omoi_os.api.dependencies import (
    get_db_service,
    get_task_queue,
    get_phase_gate_service,
    get_event_bus_service,
    get_current_user,
)
from omoi_os.models.user import User
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.phase_gate import PhaseGateService
from omoi_os.services.event_bus import EventBusService

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================


class TaskQueueStats(BaseModel):
    """Task queue statistics."""

    pending_count: int
    running_count: int
    assigned_count: int
    claiming_count: int
    completed_count: int
    failed_count: int


class OrgAgentStats(BaseModel):
    """Agent stats for an organization."""

    organization_id: str
    agent_limit: int
    running_count: int
    available_slots: int
    can_spawn: bool
    reason: str


class PhaseGateStatus(BaseModel):
    """Phase gate status for a ticket."""

    ticket_id: str
    current_phase: Optional[str]
    can_advance: bool
    gate_requirements: dict
    artifacts_present: list
    missing_requirements: list


class EventBusStatus(BaseModel):
    """Event bus connection status."""

    connected: bool
    subscribed_events: list
    last_published: Optional[str]


class SystemHealthResponse(BaseModel):
    """Overall system health check."""

    database: bool
    event_bus: bool
    task_queue: bool
    phase_progression_active: bool


# =============================================================================
# Task Queue Debug Endpoints
# =============================================================================


@router.get("/tasks/stats", response_model=TaskQueueStats)
async def get_task_queue_stats(
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """Get global task queue statistics."""
    from omoi_os.models.task import Task
    from sqlalchemy import func

    with db.get_session() as session:
        stats = (
            session.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
        )
        counts = {status: count for status, count in stats}

    return TaskQueueStats(
        pending_count=counts.get("pending", 0),
        running_count=counts.get("running", 0),
        assigned_count=counts.get("assigned", 0),
        claiming_count=counts.get("claiming", 0),
        completed_count=counts.get("completed", 0),
        failed_count=counts.get("failed", 0),
    )


@router.get("/tasks/pending")
async def get_pending_tasks(
    limit: int = Query(default=50, le=200),
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """Get list of pending tasks with details."""
    from omoi_os.models.task import Task
    from omoi_os.models.ticket import Ticket

    with db.get_session() as session:
        tasks = (
            session.query(Task)
            .filter(Task.status == "pending")
            .order_by(Task.created_at.asc())
            .limit(limit)
            .all()
        )

        result = []
        for task in tasks:
            ticket = session.query(Ticket).filter(Ticket.id == task.ticket_id).first()
            result.append(
                {
                    "task_id": task.id,
                    "task_type": task.task_type,
                    "priority": task.priority,
                    "phase_id": task.phase_id,
                    "ticket_id": task.ticket_id,
                    "ticket_title": ticket.title if ticket else None,
                    "project_id": ticket.project_id if ticket else None,
                    "created_at": (
                        task.created_at.isoformat() if task.created_at else None
                    ),
                }
            )

    return {"count": len(result), "tasks": result}


@router.get("/tasks/running/{org_id}")
async def get_running_tasks_by_org(
    org_id: str,
    current_user: User = Depends(get_current_user),
    queue: TaskQueueService = Depends(get_task_queue),
):
    """Get count of running tasks for a specific organization."""
    count = queue.get_running_count_by_organization(org_id)
    return {"organization_id": org_id, "running_count": count}


# =============================================================================
# Agent Limit Debug Endpoints
# =============================================================================


@router.get("/agents/{org_id}/stats", response_model=OrgAgentStats)
async def get_org_agent_stats(
    org_id: str,
    current_user: User = Depends(get_current_user),
    queue: TaskQueueService = Depends(get_task_queue),
):
    """Get agent limit and usage stats for an organization."""
    limit = queue.get_agent_limit_for_organization(org_id)
    running = queue.get_running_count_by_organization(org_id)
    can_spawn, reason = queue.can_spawn_agent_for_organization(org_id)

    return OrgAgentStats(
        organization_id=org_id,
        agent_limit=limit,
        running_count=running,
        available_slots=max(0, limit - running),
        can_spawn=can_spawn,
        reason=reason,
    )


# =============================================================================
# Phase Gate Debug Endpoints
# =============================================================================


@router.get("/tickets/{ticket_id}/phase-gate-status", response_model=PhaseGateStatus)
async def get_phase_gate_status(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    phase_gate: PhaseGateService = Depends(get_phase_gate_service),
):
    """Get detailed phase gate status for a ticket."""
    from omoi_os.models.ticket import Ticket
    from omoi_os.models.phase_gate_artifact import PhaseGateArtifact

    with db.get_session() as session:
        ticket = session.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return PhaseGateStatus(
                ticket_id=ticket_id,
                current_phase=None,
                can_advance=False,
                gate_requirements={},
                artifacts_present=[],
                missing_requirements=["Ticket not found"],
            )

        current_phase = ticket.phase_id

        # Get artifacts for this ticket
        artifacts = (
            session.query(PhaseGateArtifact)
            .filter(PhaseGateArtifact.ticket_id == ticket_id)
            .all()
        )
        artifacts_present = [
            {
                "artifact_type": a.artifact_type,
                "phase_id": a.phase_id,
                "artifact_url": a.artifact_url,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in artifacts
        ]

    # Check if gate passes
    can_advance = (
        phase_gate.check_gate(ticket_id, current_phase) if current_phase else False
    )

    # Get requirements for current phase
    gate_requirements = (
        phase_gate.get_phase_requirements(current_phase) if current_phase else {}
    )

    # Determine what's missing
    required_artifacts = gate_requirements.get("required_artifacts", [])
    present_types = [a["artifact_type"] for a in artifacts_present]
    missing = [r for r in required_artifacts if r not in present_types]

    return PhaseGateStatus(
        ticket_id=ticket_id,
        current_phase=current_phase,
        can_advance=can_advance,
        gate_requirements=gate_requirements,
        artifacts_present=artifacts_present,
        missing_requirements=missing,
    )


@router.get("/tickets/{ticket_id}/tasks-by-phase")
async def get_ticket_tasks_by_phase(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """Get all tasks for a ticket grouped by phase."""
    from omoi_os.models.task import Task
    from collections import defaultdict

    with db.get_session() as session:
        tasks = (
            session.query(Task)
            .filter(Task.ticket_id == ticket_id)
            .order_by(Task.phase_id, Task.created_at)
            .all()
        )

        by_phase = defaultdict(list)
        for task in tasks:
            by_phase[task.phase_id].append(
                {
                    "task_id": task.id,
                    "task_type": task.task_type,
                    "status": task.status,
                    "priority": task.priority,
                    "created_at": (
                        task.created_at.isoformat() if task.created_at else None
                    ),
                    "completed_at": (
                        task.completed_at.isoformat() if task.completed_at else None
                    ),
                }
            )

    return {
        "ticket_id": ticket_id,
        "phases": dict(by_phase),
        "total_tasks": sum(len(tasks) for tasks in by_phase.values()),
    }


# =============================================================================
# Event Bus Debug Endpoints
# =============================================================================


@router.get("/event-bus/status", response_model=EventBusStatus)
async def get_event_bus_status(
    current_user: User = Depends(get_current_user),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """Get event bus connection status."""
    # Check if connected by trying a ping
    try:
        connected = event_bus._redis.ping() if hasattr(event_bus, "_redis") else False
    except Exception:
        connected = False

    return EventBusStatus(
        connected=connected,
        subscribed_events=[],  # Would need to track this in the event bus
        last_published=None,
    )


@router.post("/event-bus/test-publish")
async def test_event_publish(
    event_type: str = Query(default="TEST_EVENT"),
    current_user: User = Depends(get_current_user),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """Publish a test event to verify event bus is working."""
    from omoi_os.services.event_bus import SystemEvent
    from omoi_os.utils.datetime import utc_now

    event = SystemEvent(
        event_type=event_type,
        entity_type="debug",
        entity_id="test",
        payload={"test": True, "timestamp": utc_now().isoformat()},
    )
    event_bus.publish(event)

    return {"status": "published", "event_type": event_type}


# =============================================================================
# Phase Progression Debug Endpoints
# =============================================================================


@router.get("/phase-progression/status")
async def get_phase_progression_status(
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    task_queue: TaskQueueService = Depends(get_task_queue),
    phase_gate: PhaseGateService = Depends(get_phase_gate_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """Check if phase progression service is initialized and active."""
    from omoi_os.services.phase_progression_service import (
        get_phase_progression_service,
        PHASE_INITIAL_TASKS,
    )

    try:
        service = get_phase_progression_service(
            db=db,
            task_queue=task_queue,
            phase_gate=phase_gate,
            event_bus=event_bus,
        )

        return {
            "active": True,
            "workflow_orchestrator_set": service._workflow_orchestrator is not None,
            "phases_with_initial_tasks": list(PHASE_INITIAL_TASKS.keys()),
            "phase_task_counts": {
                phase: len(tasks) for phase, tasks in PHASE_INITIAL_TASKS.items()
            },
        }
    except Exception as e:
        return {
            "active": False,
            "error": str(e),
        }


@router.get("/phase-progression/initial-tasks")
async def get_phase_initial_tasks(
    current_user: User = Depends(get_current_user),
):
    """Get the initial tasks configuration for each phase."""
    from omoi_os.services.phase_progression_service import (
        PHASE_INITIAL_TASKS,
        PRD_GENERATION_TASK,
    )

    return {
        "phase_initial_tasks": PHASE_INITIAL_TASKS,
        "prd_generation_task": PRD_GENERATION_TASK,
    }


# =============================================================================
# System Health Check
# =============================================================================


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
    task_queue: TaskQueueService = Depends(get_task_queue),
    phase_gate: PhaseGateService = Depends(get_phase_gate_service),
):
    """Get overall system health status."""
    from omoi_os.services.phase_progression_service import get_phase_progression_service

    # Check database
    try:
        with db.get_session() as session:
            session.execute("SELECT 1")
        db_healthy = True
    except Exception:
        db_healthy = False

    # Check event bus
    try:
        event_bus_healthy = (
            event_bus._redis.ping() if hasattr(event_bus, "_redis") else False
        )
    except Exception:
        event_bus_healthy = False

    # Check phase progression
    try:
        get_phase_progression_service(
            db=db,
            task_queue=task_queue,
            phase_gate=phase_gate,
            event_bus=event_bus,
        )
        phase_progression_active = True
    except Exception:
        phase_progression_active = False

    return SystemHealthResponse(
        database=db_healthy,
        event_bus=event_bus_healthy,
        task_queue=True,  # If we got this far, it's working
        phase_progression_active=phase_progression_active,
    )
