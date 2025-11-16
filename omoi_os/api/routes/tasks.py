"""Task API routes."""

from typing import List

from fastapi import APIRouter, HTTPException, Depends

from omoi_os.api.dependencies import get_db_service, get_task_queue
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService

router = APIRouter()


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
