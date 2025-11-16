"""Task API routes."""

from typing import List

from fastapi import APIRouter, HTTPException

from omoi_os.api.main import db
from omoi_os.models.task import Task

router = APIRouter()


@router.get("/tasks/{task_id}", response_model=dict)
async def get_task(task_id: str):
    """
    Get task by ID.

    Args:
        task_id: Task UUID

    Returns:
        Task information
    """
    if not db:
        raise HTTPException(status_code=500, detail="Services not initialized")

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
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }


@router.get("/tasks", response_model=List[dict])
async def list_tasks(status: str | None = None, phase_id: str | None = None):
    """
    List tasks with optional filtering.

    Args:
        status: Filter by status (pending, assigned, running, completed, failed)
        phase_id: Filter by phase ID

    Returns:
        List of tasks
    """
    if not db:
        raise HTTPException(status_code=500, detail="Services not initialized")

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
