"""Task API routes."""

from typing import List

from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel

from omoi_os.api.dependencies import (
    get_db_service,
    get_task_queue,
    get_event_bus_service,
)
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.reasoning_listener import log_reasoning_event

router = APIRouter()


class CancelTaskRequest(BaseModel):
    """Request model for task cancellation."""

    reason: str = "cancelled_by_request"


class TaskTimeoutRequest(BaseModel):
    """Request model for setting task timeout."""

    timeout_seconds: int


class AddDependenciesRequest(BaseModel):
    """Request model for adding dependencies."""

    depends_on: List[str]


class SetDependenciesRequest(BaseModel):
    """Request model for setting all dependencies."""

    depends_on: List[str]


class RegisterConversationRequest(BaseModel):
    """Request model for registering a conversation from sandbox."""

    conversation_id: str
    sandbox_id: str = ""
    persistence_dir: str = ""


class AgentEventRequest(BaseModel):
    """Request model for agent event from sandbox."""

    task_id: str
    agent_id: str
    event_type: str
    event_data: dict = {}


@router.post("/{task_id}/register-conversation")
async def register_conversation(
    task_id: str,
    request: RegisterConversationRequest,
    db: DatabaseService = Depends(get_db_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """Register conversation ID from sandbox worker for Guardian observation."""
    with db.get_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        task.conversation_id = request.conversation_id
        task.persistence_dir = request.persistence_dir
        task.sandbox_id = request.sandbox_id
        session.commit()

        # Publish event for Guardian
        event_bus.publish(
            SystemEvent(
                event_type="CONVERSATION_REGISTERED",
                entity_type="task",
                entity_id=task_id,
                payload={
                    "conversation_id": request.conversation_id,
                    "sandbox_id": request.sandbox_id,
                },
            )
        )

        return {
            "success": True,
            "task_id": task_id,
            "conversation_id": request.conversation_id,
        }


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
            "title": task.title,
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
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat()
            if task.completed_at
            else None,
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
                "title": task.title,
                "description": task.description,
                "priority": task.priority,
                "status": task.status,
                "assigned_agent_id": task.assigned_agent_id,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
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
            "blocked_tasks": [
                {"id": t.id, "description": t.description, "status": t.status}
                for t in blocked_tasks
            ],
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


@router.post("/{task_id}/dependencies", response_model=dict)
async def add_task_dependencies(
    task_id: str,
    request: AddDependenciesRequest = Body(...),
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """
    Add dependencies to a task.

    Args:
        task_id: Task UUID
        request: Dependencies to add
        db: Database service
        queue: Task queue service
        event_bus: Event bus service

    Returns:
        Updated task dependencies
    """
    with db.get_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Get current dependencies
        current_deps = task.dependencies or {}
        current_depends_on = set(current_deps.get("depends_on", []))

        # Add new dependencies
        new_depends_on = set(request.depends_on)
        combined_depends_on = list(current_depends_on | new_depends_on)

        # Check for circular dependencies
        cycle = queue.detect_circular_dependencies(task_id, combined_depends_on)
        if cycle:
            raise HTTPException(
                status_code=400,
                detail=f"Circular dependency detected: {' -> '.join(cycle)}",
            )

        # Verify all dependency tasks exist
        dependency_tasks = session.query(Task).filter(Task.id.in_(new_depends_on)).all()
        if len(dependency_tasks) != len(new_depends_on):
            found_ids = {t.id for t in dependency_tasks}
            missing = new_depends_on - found_ids
            raise HTTPException(
                status_code=404,
                detail=f"Dependency tasks not found: {', '.join(missing)}",
            )

        # Update dependencies
        task.dependencies = {"depends_on": combined_depends_on}
        session.commit()
        session.refresh(task)

        # Publish event
        event_bus.publish(
            SystemEvent(
                event_type="TASK_DEPENDENCY_UPDATED",
                entity_type="task",
                entity_id=task_id,
                payload={
                    "depends_on": combined_depends_on,
                    "added": list(new_depends_on),
                },
            )
        )

        return {
            "task_id": task_id,
            "depends_on": combined_depends_on,
            "dependencies_complete": queue.check_dependencies_complete(task_id),
        }


@router.put("/{task_id}/dependencies", response_model=dict)
async def set_task_dependencies(
    task_id: str,
    request: SetDependenciesRequest = Body(...),
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """
    Replace all dependencies for a task.

    Args:
        task_id: Task UUID
        request: New dependencies to set
        db: Database service
        queue: Task queue service
        event_bus: Event bus service

    Returns:
        Updated task dependencies
    """
    with db.get_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Check for circular dependencies
        cycle = queue.detect_circular_dependencies(task_id, request.depends_on)
        if cycle:
            raise HTTPException(
                status_code=400,
                detail=f"Circular dependency detected: {' -> '.join(cycle)}",
            )

        # Verify all dependency tasks exist
        if request.depends_on:
            dependency_tasks = (
                session.query(Task).filter(Task.id.in_(request.depends_on)).all()
            )
            if len(dependency_tasks) != len(request.depends_on):
                found_ids = {t.id for t in dependency_tasks}
                missing = set(request.depends_on) - found_ids
                raise HTTPException(
                    status_code=404,
                    detail=f"Dependency tasks not found: {', '.join(missing)}",
                )

        # Get old dependencies for event
        old_depends_on = []
        if task.dependencies:
            old_depends_on = task.dependencies.get("depends_on", [])

        # Update dependencies
        if request.depends_on:
            task.dependencies = {"depends_on": request.depends_on}
        else:
            task.dependencies = None

        session.commit()
        session.refresh(task)

        # Publish event
        event_bus.publish(
            SystemEvent(
                event_type="TASK_DEPENDENCY_UPDATED",
                entity_type="task",
                entity_id=task_id,
                payload={
                    "depends_on": request.depends_on,
                    "old_depends_on": old_depends_on,
                },
            )
        )

        return {
            "task_id": task_id,
            "depends_on": request.depends_on,
            "dependencies_complete": queue.check_dependencies_complete(task_id),
        }


@router.delete("/{task_id}/dependencies/{depends_on_task_id}", response_model=dict)
async def remove_task_dependency(
    task_id: str,
    depends_on_task_id: str,
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """
    Remove a specific dependency from a task.

    Args:
        task_id: Task UUID
        depends_on_task_id: Task ID to remove from dependencies
        db: Database service
        queue: Task queue service
        event_bus: Event bus service

    Returns:
        Updated task dependencies
    """
    with db.get_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if not task.dependencies:
            raise HTTPException(status_code=400, detail="Task has no dependencies")

        depends_on = task.dependencies.get("depends_on", [])
        if depends_on_task_id not in depends_on:
            raise HTTPException(
                status_code=404,
                detail=f"Task {depends_on_task_id} is not a dependency of {task_id}",
            )

        # Remove the dependency
        updated_depends_on = [
            dep_id for dep_id in depends_on if dep_id != depends_on_task_id
        ]

        if updated_depends_on:
            task.dependencies = {"depends_on": updated_depends_on}
        else:
            task.dependencies = None

        session.commit()
        session.refresh(task)

        # Publish event
        event_bus.publish(
            SystemEvent(
                event_type="TASK_DEPENDENCY_UPDATED",
                entity_type="task",
                entity_id=task_id,
                payload={
                    "depends_on": updated_depends_on,
                    "removed": [depends_on_task_id],
                },
            )
        )

        return {
            "task_id": task_id,
            "depends_on": updated_depends_on,
            "dependencies_complete": queue.check_dependencies_complete(task_id),
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

    # Log reasoning event for task cancellation
    log_reasoning_event(
        db=queue.db,
        entity_type="task",
        entity_id=task_id,
        event_type="error",
        title="Task Cancelled",
        description=f"Task cancelled: {request.reason}",
        details={"reason": request.reason, "cancelled_by": "api"},
        decision={
            "type": "cancel",
            "action": "Stop task execution",
            "reasoning": request.reason,
        },
    )

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
                detail="Cannot set timeout for completed or failed tasks",
            )

        task.timeout_seconds = request.timeout_seconds
        session.commit()
        session.refresh(task)

        return {
            "task_id": task_id,
            "timeout_seconds": task.timeout_seconds,
            "status": task.status,
        }


@router.post("/{task_id}/generate-title", response_model=dict)
async def generate_task_title(
    task_id: str,
    context: str | None = Body(None, embed=True),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Generate a human-readable title for a task using LLM.

    Uses the TitleGenerationService with gpt-oss-20b model to create
    a concise, action-oriented title. If the task already has a description,
    the title will be generated from that. Otherwise, both title and
    description will be generated.

    Args:
        task_id: Task UUID
        context: Optional additional context for title generation
        db: Database service

    Returns:
        Task with generated title
    """
    from omoi_os.services.task_queue import generate_task_title as gen_title

    with db.get_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        task_type = task.task_type
        description = task.description

    # Generate title asynchronously
    title = await gen_title(
        task_id=task_id,
        db=db,
        task_type=task_type,
        description=description,
        context=context,
    )

    if not title:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate title for task",
        )

    # Reload the task to get updated title and description
    with db.get_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        return {
            "task_id": task_id,
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type,
        }


@router.post("/generate-titles", response_model=dict)
async def generate_titles_batch(
    limit: int = Body(10, embed=True),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Generate titles for tasks that don't have one yet (batch operation).

    This is useful for backfilling titles on existing tasks.

    Args:
        limit: Maximum number of tasks to process (default 10)
        db: Database service

    Returns:
        Results of batch title generation
    """
    from omoi_os.services.task_queue import generate_task_title as gen_title

    with db.get_session() as session:
        # Find tasks without titles
        tasks = (
            session.query(Task)
            .filter(Task.title.is_(None))
            .limit(limit)
            .all()
        )

        task_info = [
            {
                "id": task.id,
                "task_type": task.task_type,
                "description": task.description,
            }
            for task in tasks
        ]

    results = {"processed": 0, "succeeded": 0, "failed": 0, "tasks": []}

    for info in task_info:
        results["processed"] += 1
        title = await gen_title(
            task_id=info["id"],
            db=db,
            task_type=info["task_type"],
            description=info["description"],
        )
        if title:
            results["succeeded"] += 1
            results["tasks"].append({"task_id": info["id"], "title": title})
        else:
            results["failed"] += 1
            results["tasks"].append({"task_id": info["id"], "title": None, "error": "Generation failed"})

    return results
