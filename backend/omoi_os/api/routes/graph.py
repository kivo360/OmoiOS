"""Dependency graph API routes."""

from typing import Dict, Any
from fastapi import APIRouter, Query, Depends, HTTPException

from omoi_os.api.dependencies import get_db_service, get_task_queue
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.dependency_graph import DependencyGraphService
from omoi_os.models.task import Task

router = APIRouter()


@router.get("/dependency-graph/ticket/{ticket_id}")
async def get_ticket_dependency_graph(
    ticket_id: str,
    include_resolved: bool = Query(True, description="Include completed tasks"),
    include_discoveries: bool = Query(True, description="Include discovery nodes"),
    db: DatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    """
    Get dependency graph for a ticket.

    Returns graph with nodes (tasks, discoveries) and edges (dependencies).

    Args:
        ticket_id: Ticket ID to build graph for
        include_resolved: Whether to include completed tasks
        include_discoveries: Whether to include discovery nodes
        db: Database service

    Returns:
        {
            "nodes": [...],
            "edges": [...],
            "metadata": {...}
        }
    """
    graph_service = DependencyGraphService(db)
    return graph_service.build_ticket_graph(
        ticket_id=ticket_id,
        include_resolved=include_resolved,
        include_discoveries=include_discoveries,
    )


@router.get("/dependency-graph/project/{project_id}")
async def get_project_dependency_graph(
    project_id: str,
    include_resolved: bool = Query(True),
    db: DatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    """
    Get dependency graph for entire project.

    Args:
        project_id: Project ID (currently unused, gets all tickets)
        include_resolved: Whether to include completed tasks
        db: Database service

    Returns:
        Graph structure with nodes and edges
    """
    graph_service = DependencyGraphService(db)
    return graph_service.build_project_graph(
        project_id=project_id, include_resolved=include_resolved
    )


@router.get("/dependency-graph/task/{task_id}/blocked")
async def get_blocked_tasks(
    task_id: str,
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
) -> Dict[str, Any]:
    """
    Get all tasks blocked by this task (i.e., tasks that depend on this task).

    Args:
        task_id: Task ID
        db: Database service
        queue: Task queue service

    Returns:
        {
            "task_id": "...",
            "blocked_tasks": [...],
            "blocked_count": 2
        }
    """
    blocked = queue.get_blocked_tasks(task_id)
    return {
        "task_id": task_id,
        "blocked_tasks": [
            {
                "id": t.id,
                "description": t.description,
                "status": t.status,
                "priority": t.priority,
                "phase_id": t.phase_id,
            }
            for t in blocked
        ],
        "blocked_count": len(blocked),
    }


@router.get("/dependency-graph/task/{task_id}/blocking")
async def get_blocking_tasks(
    task_id: str,
    db: DatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    """
    Get all tasks that block this task (dependencies).

    Args:
        task_id: Task ID
        db: Database service

    Returns:
        {
            "task_id": "...",
            "blocking_tasks": [...],
            "all_dependencies_complete": true
        }
    """
    with db.get_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        depends_on = []
        if task.dependencies:
            depends_on = task.dependencies.get("depends_on", [])

        blocking_tasks = []
        if depends_on:
            blocking = session.query(Task).filter(Task.id.in_(depends_on)).all()
            blocking_tasks = [
                {
                    "id": t.id,
                    "description": t.description,
                    "status": t.status,
                    "priority": t.priority,
                    "phase_id": t.phase_id,
                    "is_complete": t.status == "completed",
                }
                for t in blocking
            ]

        return {
            "task_id": task_id,
            "blocking_tasks": blocking_tasks,
            "all_dependencies_complete": (
                all(t["is_complete"] for t in blocking_tasks)
                if blocking_tasks
                else True
            ),
        }
