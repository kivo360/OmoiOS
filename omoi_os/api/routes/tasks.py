"""Task API routes."""

from typing import List

from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel

from omoi_os.api.dependencies import get_db_service, get_task_queue
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService

router = APIRouter()


class CancelTaskRequest(BaseModel):
    """Request model for task cancellation."""
    reason: str = "cancelled_by_request"


class TaskTimeoutRequest(BaseModel):
    """Request model for setting task timeout."""
    timeout_seconds: int


@router.get("/{task_id}", response_model=dict)
async def get_task(
    task_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get task by ID.

    Args:
        task_id: Task UUID
        db: Database service

    Returns:
        Task information
    """
    with db.get_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return {
            "id": task.id,
            "ticket_id": task.ticket_id,
            "phase_id": task.phase_id,
            "task_type": task.task_type,
            "description": task.description,
            "priority": task.priority,
            "status": task.status,
            "assigned_agent_id": task.assigned_agent_id,
            "conversation_id": task.conversation_id,
            "result": task.result,
            "error_message": task.error_message,
            "dependencies": task.dependencies,
            "timeout_seconds": task.timeout_seconds,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }


@router.get("", response_model=List[dict])
async def list_tasks(
    status: str | None = None,
    phase_id: str | None = None,
    db: DatabaseService = Depends(get_db_service),
):
    """
    List tasks with optional filtering.

    Args:
        status: Filter by status (pending, assigned, running, completed, failed)
        phase_id: Filter by phase ID
        db: Database service

    Returns:
        List of tasks
    """
    with db.get_session() as session:
        query = session.query(Task)
        if status:
            query = query.filter(Task.status == status)
        if phase_id:
            query = query.filter(Task.phase_id == phase_id)

        tasks = query.all()
        return [
            {
                "id": task.id,
                "ticket_id": task.ticket_id,
                "phase_id": task.phase_id,
                "task_type": task.task_type,
                "description": task.description,
                "priority": task.priority,
                "status": task.status,
                "assigned_agent_id": task.assigned_agent_id,
                "created_at": task.created_at.isoformat(),
            }
            for task in tasks
        ]


@router.get("/{task_id}/dependencies", response_model=dict)
async def get_task_dependencies(
    task_id: str,
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
):
    """
    Get task dependencies information.

    Args:
        task_id: Task UUID
        db: Database service
        queue: Task queue service

    Returns:
        Dependencies information including depends_on and blocked tasks
    """
    with db.get_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        depends_on = []
        if task.dependencies:
            depends_on = task.dependencies.get("depends_on", [])
        
        # Get blocked tasks (tasks that depend on this one)
        blocked_tasks = queue.get_blocked_tasks(task_id)
        
        # Check if dependencies are complete
        dependencies_complete = queue.check_dependencies_complete(task_id)
        
        return {
            "task_id": task_id,
            "depends_on": depends_on,
            "dependencies_complete": dependencies_complete,
            "blocked_tasks": [{"id": t.id, "description": t.description, "status": t.status} for t in blocked_tasks],
        }


@router.post("/{task_id}/check-circular", response_model=dict)
async def check_circular_dependencies(
    task_id: str,
    depends_on: list[str],
    queue: TaskQueueService = Depends(get_task_queue),
):
    """
    Check for circular dependencies.

    Args:
        task_id: Task UUID
        depends_on: List of task IDs this task depends on
        queue: Task queue service

    Returns:
        Information about circular dependencies if found
    """
    cycle = queue.detect_circular_dependencies(task_id, depends_on)
    
    if cycle:
        return {
            "has_circular_dependency": True,
            "cycle": cycle,
        }
    
    return {
        "has_circular_dependency": False,
        "cycle": None,
    }


# Task Timeout & Cancellation Endpoints (Agent D)


@router.post("/{task_id}/cancel", response_model=dict)
async def cancel_task(
    task_id: str,
    request: CancelTaskRequest = Body(...),
    queue: TaskQueueService = Depends(get_task_queue),
):
    """
    Cancel a running task.

    Args:
        task_id: Task UUID
        request: Cancellation request with optional reason
        queue: Task queue service

    Returns:
        Cancellation result
    """
    success = queue.cancel_task(task_id, request.reason)

    if not success:
        raise HTTPException(status_code=404, detail="Task not found or not cancellable")

    return {
        "task_id": task_id,
        "cancelled": True,
        "reason": request.reason,
    }


@router.get("/{task_id}/timeout-status", response_model=dict)
async def get_task_timeout_status(
    task_id: str,
    queue: TaskQueueService = Depends(get_task_queue),
):
    """
    Get timeout status for a task.

    Args:
        task_id: Task UUID
        queue: Task queue service

    Returns:
        Timeout status information
    """
    status = queue.get_task_timeout_status(task_id)

    if not status.get("exists"):
        raise HTTPException(status_code=404, detail="Task not found")

    return status


@router.get("/timed-out", response_model=List[dict])
async def get_timed_out_tasks(
    queue: TaskQueueService = Depends(get_task_queue),
):
    """
    Get all tasks that have exceeded their timeout.

    Args:
        queue: Task queue service

    Returns:
        List of timed-out tasks
    """
    tasks = queue.get_timed_out_tasks()

    return [
        {
            "id": task.id,
            "ticket_id": task.ticket_id,
            "phase_id": task.phase_id,
            "task_type": task.task_type,
            "description": task.description,
            "priority": task.priority,
            "status": task.status,
            "assigned_agent_id": task.assigned_agent_id,
            "timeout_seconds": task.timeout_seconds,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "elapsed_time": queue.get_task_elapsed_time(task.id),
        }
        for task in tasks
    ]


@router.get("/cancellable", response_model=List[dict])
async def get_cancellable_tasks(
    agent_id: str | None = None,
    queue: TaskQueueService = Depends(get_task_queue),
):
    """
    Get all tasks that can be cancelled.

    Args:
        agent_id: Optional agent ID to filter by
        queue: Task queue service

    Returns:
        List of cancellable tasks
    """
    tasks = queue.get_cancellable_tasks(agent_id)

    return [
        {
            "id": task.id,
            "ticket_id": task.ticket_id,
            "phase_id": task.phase_id,
            "task_type": task.task_type,
            "description": task.description,
            "priority": task.priority,
            "status": task.status,
            "assigned_agent_id": task.assigned_agent_id,
            "timeout_seconds": task.timeout_seconds,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "elapsed_time": queue.get_task_elapsed_time(task.id),
            "time_remaining": None,
        }
        for task in tasks
    ]


@router.post("/cleanup-timed-out", response_model=dict)
async def cleanup_timed_out_tasks(
    queue: TaskQueueService = Depends(get_task_queue),
):
    """
    Mark all timed-out tasks as failed.

    Args:
        queue: Task queue service

    Returns:
        Cleanup results
    """
    timed_out_tasks = queue.get_timed_out_tasks()
    cleaned_count = 0

    for task in timed_out_tasks:
        success = queue.mark_task_timeout(task.id)
        if success:
            cleaned_count += 1

    return {
        "cleaned_count": cleaned_count,
        "total_timed_out": len(timed_out_tasks),
    }


@router.post("/{task_id}/set-timeout", response_model=dict)
async def set_task_timeout(
    task_id: str,
    request: TaskTimeoutRequest = Body(...),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Set timeout for a task.

    Args:
        task_id: Task UUID
        request: Timeout request with seconds
        db: Database service

    Returns:
        Updated task information
    """
    with db.get_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Only allow setting timeout for pending/assigned/running tasks
        if task.status not in ["pending", "assigned", "running"]:
            raise HTTPException(
                status_code=400,
                detail="Cannot set timeout for completed or failed tasks"
            )

        task.timeout_seconds = request.timeout_seconds
        session.commit()
        session.refresh(task)

        return {
            "task_id": task_id,
            "timeout_seconds": task.timeout_seconds,
            "status": task.status,
        }
