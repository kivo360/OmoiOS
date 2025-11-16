"""Scheduler API routes for parallel execution and task assignment."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from omoi_os.api.dependencies import get_db, get_event_bus
from omoi_os.services.agent_registry import AgentRegistryService
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.resource_lock import ResourceLockService
from omoi_os.services.scheduler import SchedulerService
from omoi_os.services.task_queue import TaskQueueService

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


def get_scheduler_service(
    db: DatabaseService = Depends(get_db),
    event_bus: EventBusService = Depends(get_event_bus),
) -> SchedulerService:
    """Get scheduler service instance."""
    task_queue = TaskQueueService(db)
    registry = AgentRegistryService(db, event_bus)
    lock_service = ResourceLockService(db, event_bus=event_bus)
    return SchedulerService(db, task_queue, registry, lock_service, event_bus)


@router.get("/ready-tasks")
def get_ready_tasks(
    phase_id: Optional[str] = Query(None, description="Filter by phase ID"),
    limit: Optional[int] = Query(None, description="Maximum number of tasks to return"),
    required_capabilities: Optional[str] = Query(
        None, description="Comma-separated list of required capabilities"
    ),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    """
    Get batch of ready tasks using DAG evaluation.

    Returns tasks that are ready for execution (dependencies completed, not locked).
    """
    capabilities_list = None
    if required_capabilities:
        capabilities_list = [c.strip() for c in required_capabilities.split(",")]

    tasks = scheduler.get_ready_tasks(
        phase_id=phase_id,
        limit=limit,
        required_capabilities=capabilities_list,
    )

    return {
        "ready_count": len(tasks),
        "tasks": [
            {
                "id": task.id,
                "ticket_id": task.ticket_id,
                "phase_id": task.phase_id,
                "task_type": task.task_type,
                "description": task.description,
                "priority": task.priority,
                "status": task.status,
                "dependencies": task.dependencies,
            }
            for task in tasks
        ],
    }


@router.post("/assign")
def assign_tasks(
    phase_id: Optional[str] = Query(None, description="Filter by phase ID"),
    limit: Optional[int] = Query(None, description="Maximum number of tasks to assign"),
    required_capabilities: Optional[str] = Query(
        None, description="Comma-separated list of required capabilities"
    ),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    """
    Schedule ready tasks and assign them to best-fit agents.

    Returns assignment results with task and agent information.
    """
    capabilities_list = None
    if required_capabilities:
        capabilities_list = [c.strip() for c in required_capabilities.split(",")]

    assignments = scheduler.schedule_and_assign(
        phase_id=phase_id,
        limit=limit,
        required_capabilities=capabilities_list,
    )

    # Actually assign tasks to agents
    task_queue = TaskQueueService(scheduler.db)
    assigned_count = 0
    for assignment in assignments:
        if assignment["assigned"] and assignment["agent_id"]:
            task_queue.assign_task(assignment["task_id"], assignment["agent_id"])
            assigned_count += 1

    return {
        "assignments_made": assigned_count,
        "total_ready": len(assignments),
        "assignments": [
            {
                "task_id": a["task_id"],
                "agent_id": a["agent_id"],
                "assigned": a["assigned"],
                "task": {
                    "id": a["task"].id,
                    "ticket_id": a["task"].ticket_id,
                    "phase_id": a["task"].phase_id,
                    "task_type": a["task"].task_type,
                    "description": a["task"].description,
                    "priority": a["task"].priority,
                },
            }
            for a in assignments
        ],
    }


@router.get("/dag-status")
def get_dag_status(
    phase_id: Optional[str] = Query(None, description="Filter by phase ID"),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    """
    Get DAG status showing task dependencies and ready/blocked states.
    """
    from omoi_os.models.task import Task

    with scheduler.db.get_session() as session:
        query = session.query(Task).filter(Task.status == "pending")
        if phase_id:
            query = query.filter(Task.phase_id == phase_id)

        all_tasks = query.all()

        # Build dependency graph
        task_info = {}
        for task in all_tasks:
            depends_on = []
            if task.dependencies:
                depends_on = task.dependencies.get("depends_on", [])

            # Check if ready
            is_ready = scheduler._check_dependencies_complete(session, task)

            task_info[task.id] = {
                "id": task.id,
                "description": task.description,
                "priority": task.priority,
                "depends_on": depends_on,
                "is_ready": is_ready,
                "status": task.status,
            }

        return {
            "phase_id": phase_id,
            "total_pending": len(all_tasks),
            "ready_count": sum(1 for info in task_info.values() if info["is_ready"]),
            "blocked_count": sum(1 for info in task_info.values() if not info["is_ready"]),
            "tasks": list(task_info.values()),
        }
