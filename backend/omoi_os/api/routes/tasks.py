"""Task API routes."""

from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from sqlalchemy import select

from omoi_os.api.dependencies import (
    get_db_service,
    get_task_queue,
    get_event_bus_service,
    get_current_user,
    verify_task_access,
    verify_ticket_access,
    get_accessible_project_ids,
)
from omoi_os.models.user import User
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.reasoning_listener import log_reasoning_event

router = APIRouter()


# ============================================================================
# Async Database Helpers (Non-blocking)
# ============================================================================


async def _register_conversation_async(
    db: DatabaseService,
    task_id: str,
    conversation_id: str,
    persistence_dir: str,
    sandbox_id: str,
) -> Task:
    """Register conversation for a task (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(select(Task).filter(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return None

        task.conversation_id = conversation_id
        task.persistence_dir = persistence_dir
        task.sandbox_id = sandbox_id
        await session.commit()
        return task


async def _get_task_async(db: DatabaseService, task_id: str) -> Optional[Task]:
    """Get a task by ID (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(select(Task).filter(Task.id == task_id))
        task = result.scalar_one_or_none()
        return task


async def _list_tasks_async(
    db: DatabaseService,
    status: Optional[str] = None,
    phase_id: Optional[str] = None,
    has_sandbox: Optional[bool] = None,
    limit: int = 100,
) -> List[Task]:
    """List tasks with filters (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        query = select(Task)
        if status:
            query = query.filter(Task.status == status)
        if phase_id:
            query = query.filter(Task.phase_id == phase_id)
        if has_sandbox is True:
            query = query.filter(Task.sandbox_id.isnot(None))
        elif has_sandbox is False:
            query = query.filter(Task.sandbox_id.is_(None))

        query = query.order_by(Task.created_at.desc()).limit(limit)
        result = await session.execute(query)
        tasks = result.scalars().all()
        return tasks


async def _get_task_dependencies_async(
    db: DatabaseService, task_id: str
) -> Optional[Dict[str, Any]]:
    """Get task dependencies info (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(select(Task).filter(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return None

        depends_on = []
        if task.dependencies:
            depends_on = task.dependencies.get("depends_on", [])

        return {"task": task, "depends_on": depends_on}


async def _add_task_dependencies_async(
    db: DatabaseService,
    task_id: str,
    new_depends_on: set,
    combined_depends_on: list,
) -> Optional[Task]:
    """Add dependencies to a task (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(select(Task).filter(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return None

        # Verify all dependency tasks exist
        dep_result = await session.execute(
            select(Task).filter(Task.id.in_(new_depends_on))
        )
        dependency_tasks = dep_result.scalars().all()
        if len(dependency_tasks) != len(new_depends_on):
            found_ids = {t.id for t in dependency_tasks}
            missing = new_depends_on - found_ids
            raise ValueError(f"Dependency tasks not found: {', '.join(missing)}")

        task.dependencies = {"depends_on": combined_depends_on}
        await session.commit()
        await session.refresh(task)
        return task


async def _set_task_dependencies_async(
    db: DatabaseService,
    task_id: str,
    depends_on: list,
) -> Optional[Dict[str, Any]]:
    """Set all dependencies for a task (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(select(Task).filter(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return None

        # Verify all dependency tasks exist
        if depends_on:
            dep_result = await session.execute(
                select(Task).filter(Task.id.in_(depends_on))
            )
            dependency_tasks = dep_result.scalars().all()
            if len(dependency_tasks) != len(depends_on):
                found_ids = {t.id for t in dependency_tasks}
                missing = set(depends_on) - found_ids
                raise ValueError(f"Dependency tasks not found: {', '.join(missing)}")

        # Get old dependencies
        old_depends_on = []
        if task.dependencies:
            old_depends_on = task.dependencies.get("depends_on", [])

        # Update
        if depends_on:
            task.dependencies = {"depends_on": depends_on}
        else:
            task.dependencies = None

        await session.commit()
        await session.refresh(task)
        return {"task": task, "old_depends_on": old_depends_on}


async def _remove_task_dependency_async(
    db: DatabaseService,
    task_id: str,
    depends_on_task_id: str,
) -> Optional[Dict[str, Any]]:
    """Remove a dependency from a task (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(select(Task).filter(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return None

        if not task.dependencies:
            raise ValueError("Task has no dependencies")

        depends_on = task.dependencies.get("depends_on", [])
        if depends_on_task_id not in depends_on:
            raise ValueError(
                f"Task {depends_on_task_id} is not a dependency of {task_id}"
            )

        # Remove the dependency
        updated_depends_on = [
            dep_id for dep_id in depends_on if dep_id != depends_on_task_id
        ]

        if updated_depends_on:
            task.dependencies = {"depends_on": updated_depends_on}
        else:
            task.dependencies = None

        await session.commit()
        await session.refresh(task)
        return {"task": task, "updated_depends_on": updated_depends_on}


async def _set_task_timeout_async(
    db: DatabaseService,
    task_id: str,
    timeout_seconds: int,
) -> Optional[Task]:
    """Set timeout for a task (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(select(Task).filter(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return None

        if task.status not in ["pending", "assigned", "running"]:
            raise ValueError("Cannot set timeout for completed or failed tasks")

        task.timeout_seconds = timeout_seconds
        await session.commit()
        await session.refresh(task)
        return task


async def _get_tasks_without_titles_async(
    db: DatabaseService, limit: int
) -> List[Dict[str, Any]]:
    """Get tasks without titles (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(
            select(Task).filter(Task.title.is_(None)).limit(limit)
        )
        tasks = result.scalars().all()
        return [
            {
                "id": task.id,
                "task_type": task.task_type,
                "description": task.description,
            }
            for task in tasks
        ]


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
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """
    Register conversation ID from sandbox worker for Guardian observation.

    Requires authentication and verifies user has access to the task's ticket.
    """
    # Verify user has access to this task
    await verify_task_access(task_id, current_user, db)
    # Use async database operations (non-blocking)
    task = await _register_conversation_async(
        db,
        task_id,
        request.conversation_id,
        request.persistence_dir,
        request.sandbox_id,
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

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
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get task by ID.

    Requires authentication and verifies user has access to the task's ticket.

    Args:
        task_id: Task UUID
        current_user: Authenticated user
        db: Database service

    Returns:
        Task information
    """
    # Verify user has access to this task
    await verify_task_access(task_id, current_user, db)

    # Use async database operations (non-blocking)
    task = await _get_task_async(db, task_id)
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
        "sandbox_id": task.sandbox_id,
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


class TaskUpdateRequest(BaseModel):
    """Request model for updating a task."""

    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


@router.patch("/{task_id}", response_model=dict)
async def update_task(
    task_id: str,
    update: TaskUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Update task by ID.

    Requires authentication and verifies user has access to the task's ticket.

    Args:
        task_id: Task UUID
        update: Fields to update
        current_user: Authenticated user
        db: Database service

    Returns:
        Updated task information
    """
    # Verify user has access to this task
    await verify_task_access(task_id, current_user, db)

    async with db.get_async_session() as session:
        result = await session.execute(
            select(Task).filter(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Update only provided fields
        update_data = update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(task, field, value)

        await session.commit()
        await session.refresh(task)

        return {
            "id": task.id,
            "ticket_id": task.ticket_id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }


@router.get("", response_model=List[dict])
async def list_tasks(
    status: str | None = None,
    phase_id: str | None = None,
    has_sandbox: bool | None = None,
    ticket_id: str | None = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """
    List tasks with optional filtering.

    Requires authentication. Only returns tasks from projects the user has access to
    (multi-tenant filtering via Task → Ticket → Project → Organization chain).

    Args:
        status: Filter by status (pending, assigned, running, completed, failed)
        phase_id: Filter by phase ID
        has_sandbox: Filter to only tasks with a sandbox_id (True) or without (False)
        ticket_id: Filter by ticket ID
        limit: Maximum number of tasks to return (default 100)
        current_user: Authenticated user
        db: Database service

    Returns:
        List of tasks for the user's accessible projects
    """
    from omoi_os.models.ticket import Ticket

    # Get user's accessible project IDs for multi-tenant filtering
    accessible_project_ids = await get_accessible_project_ids(current_user, db)

    # If user has no accessible projects, return empty
    if not accessible_project_ids:
        return []

    async with db.get_async_session() as session:
        # Join Task → Ticket to filter by accessible projects
        query = (
            select(Task)
            .join(Ticket, Task.ticket_id == Ticket.id)
            .filter(Ticket.project_id.in_([str(pid) for pid in accessible_project_ids]))
        )

        # Apply optional filters
        if ticket_id:
            # Verify user has access to the specific ticket
            await verify_ticket_access(ticket_id, current_user, db)
            query = query.filter(Task.ticket_id == ticket_id)
        if status:
            query = query.filter(Task.status == status)
        if phase_id:
            query = query.filter(Task.phase_id == phase_id)
        if has_sandbox is True:
            query = query.filter(Task.sandbox_id.isnot(None))
        elif has_sandbox is False:
            query = query.filter(Task.sandbox_id.is_(None))

        query = query.order_by(Task.created_at.desc()).limit(limit)
        result = await session.execute(query)
        tasks = result.scalars().all()

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
                "sandbox_id": task.sandbox_id,
                "assigned_agent_id": task.assigned_agent_id,
                "created_at": task.created_at.isoformat(),
            }
            for task in tasks
        ]


class ExecutionConfig(BaseModel):
    """Execution configuration for sandbox spawning."""

    require_spec_skill: bool = False  # Force spec-driven-dev skill usage
    selected_skill: Optional[str] = None  # Skill name selected from frontend dropdown


class TaskCreate(BaseModel):
    """Request model for creating a task."""

    ticket_id: str
    title: str
    description: str
    task_type: str = "implementation"
    priority: str = "MEDIUM"
    phase_id: str = "PHASE_IMPLEMENTATION"
    dependencies: Optional[Dict[str, Any]] = None  # {"depends_on": ["task_id_1"]}
    execution_config: Optional[ExecutionConfig] = None  # Skill selection from frontend


@router.post("", response_model=dict, status_code=201)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
):
    """
    Create a new task for a ticket.

    Requires authentication and verifies user has access to the ticket.

    This endpoint allows direct task creation for testing and spec-driven development.

    Args:
        task_data: Task creation data including ticket_id, title, description
        current_user: Authenticated user
        db: Database service
        queue: Task queue service for task creation

    Returns:
        Created task with ID and details
    """
    # Verify user has access to the ticket this task will belong to
    await verify_ticket_access(task_data.ticket_id, current_user, db)

    try:
        # Convert execution_config to dict for JSONB storage
        execution_config_dict = None
        if task_data.execution_config:
            execution_config_dict = task_data.execution_config.model_dump(mode="json")

        task = queue.enqueue_task(
            ticket_id=task_data.ticket_id,
            phase_id=task_data.phase_id,
            task_type=task_data.task_type,
            description=task_data.description,
            priority=task_data.priority,
            dependencies=task_data.dependencies,
            title=task_data.title,
            execution_config=execution_config_dict,
        )

        return {
            "id": task.id,
            "ticket_id": task.ticket_id,
            "phase_id": task.phase_id,
            "task_type": task.task_type,
            "title": task.title,
            "description": task.description,
            "priority": task.priority,
            "status": task.status,
            "dependencies": task.dependencies,
            "execution_config": task.execution_config,
            "created_at": task.created_at.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{task_id}/dependencies", response_model=dict)
async def get_task_dependencies(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
):
    """
    Get task dependencies information.

    Requires authentication and verifies user has access to the task's ticket.

    Args:
        task_id: Task UUID
        current_user: Authenticated user
        db: Database service
        queue: Task queue service

    Returns:
        Dependencies information including depends_on and blocked tasks
    """
    # Verify user has access to this task
    await verify_task_access(task_id, current_user, db)
    # Use async database operations (non-blocking)
    result = await _get_task_dependencies_async(db, task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")

    depends_on = result["depends_on"]

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
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
):
    """
    Check for circular dependencies.

    Requires authentication and verifies user has access to the task's ticket.

    Args:
        task_id: Task UUID
        depends_on: List of task IDs this task depends on
        current_user: Authenticated user
        db: Database service
        queue: Task queue service

    Returns:
        Information about circular dependencies if found
    """
    # Verify user has access to this task
    await verify_task_access(task_id, current_user, db)
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
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """
    Add dependencies to a task.

    Requires authentication and verifies user has access to the task's ticket.

    Args:
        task_id: Task UUID
        request: Dependencies to add
        current_user: Authenticated user
        db: Database service
        queue: Task queue service
        event_bus: Event bus service

    Returns:
        Updated task dependencies
    """
    # Verify user has access to this task
    await verify_task_access(task_id, current_user, db)
    # First get the current dependencies using async
    result = await _get_task_dependencies_async(db, task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")

    current_depends_on = set(result["depends_on"])
    new_depends_on = set(request.depends_on)
    combined_depends_on = list(current_depends_on | new_depends_on)

    # Check for circular dependencies
    cycle = queue.detect_circular_dependencies(task_id, combined_depends_on)
    if cycle:
        raise HTTPException(
            status_code=400,
            detail=f"Circular dependency detected: {' -> '.join(cycle)}",
        )

    # Use async database operations (non-blocking)
    try:
        task = await _add_task_dependencies_async(
            db, task_id, new_depends_on, combined_depends_on
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

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
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """
    Replace all dependencies for a task.

    Requires authentication and verifies user has access to the task's ticket.

    Args:
        task_id: Task UUID
        request: New dependencies to set
        current_user: Authenticated user
        db: Database service
        queue: Task queue service
        event_bus: Event bus service

    Returns:
        Updated task dependencies
    """
    # Verify user has access to this task
    await verify_task_access(task_id, current_user, db)
    # Check for circular dependencies
    cycle = queue.detect_circular_dependencies(task_id, request.depends_on)
    if cycle:
        raise HTTPException(
            status_code=400,
            detail=f"Circular dependency detected: {' -> '.join(cycle)}",
        )

    # Use async database operations (non-blocking)
    try:
        result = await _set_task_dependencies_async(db, task_id, request.depends_on)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not result:
        raise HTTPException(status_code=404, detail="Task not found")

    old_depends_on = result["old_depends_on"]

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
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """
    Remove a specific dependency from a task.

    Requires authentication and verifies user has access to the task's ticket.

    Args:
        task_id: Task UUID
        depends_on_task_id: Task ID to remove from dependencies
        current_user: Authenticated user
        db: Database service
        queue: Task queue service
        event_bus: Event bus service

    Returns:
        Updated task dependencies
    """
    # Verify user has access to this task
    await verify_task_access(task_id, current_user, db)
    # Use async database operations (non-blocking)
    try:
        result = await _remove_task_dependency_async(db, task_id, depends_on_task_id)
    except ValueError as e:
        if "no dependencies" in str(e).lower():
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=404, detail=str(e))

    if not result:
        raise HTTPException(status_code=404, detail="Task not found")

    updated_depends_on = result["updated_depends_on"]

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
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
):
    """
    Cancel a running task.

    Requires authentication and verifies user has access to the task's ticket.

    Args:
        task_id: Task UUID
        request: Cancellation request with optional reason
        current_user: Authenticated user
        db: Database service
        queue: Task queue service

    Returns:
        Cancellation result
    """
    # Verify user has access to this task
    await verify_task_access(task_id, current_user, db)
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
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    queue: TaskQueueService = Depends(get_task_queue),
):
    """
    Get timeout status for a task.

    Requires authentication and verifies user has access to the task's ticket.

    Args:
        task_id: Task UUID
        current_user: Authenticated user
        db: Database service
        queue: Task queue service

    Returns:
        Timeout status information
    """
    # Verify user has access to this task
    await verify_task_access(task_id, current_user, db)
    status = queue.get_task_timeout_status(task_id)

    if not status.get("exists"):
        raise HTTPException(status_code=404, detail="Task not found")

    return status


@router.get("/timed-out", response_model=List[dict])
async def get_timed_out_tasks(
    current_user: User = Depends(get_current_user),
    queue: TaskQueueService = Depends(get_task_queue),
):
    """
    Get all tasks that have exceeded their timeout.

    Requires authentication.

    Args:
        current_user: Authenticated user
        queue: Task queue service

    Returns:
        List of timed-out tasks
    """
    # Note: This returns all timed-out tasks. In a proper multi-tenant implementation,
    # this should be filtered to only tasks the user can access.
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
    current_user: User = Depends(get_current_user),
    queue: TaskQueueService = Depends(get_task_queue),
):
    """
    Get all tasks that can be cancelled.

    Requires authentication.

    Args:
        agent_id: Optional agent ID to filter by
        current_user: Authenticated user
        queue: Task queue service

    Returns:
        List of cancellable tasks
    """
    # Note: This returns all cancellable tasks. In a proper multi-tenant implementation,
    # this should be filtered to only tasks the user can access.
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
    current_user: User = Depends(get_current_user),
    queue: TaskQueueService = Depends(get_task_queue),
):
    """
    Mark all timed-out tasks as failed.

    Requires authentication.

    Args:
        current_user: Authenticated user
        queue: Task queue service

    Returns:
        Cleanup results
    """
    # Note: This cleans up all timed-out tasks. In a proper multi-tenant implementation,
    # this should be restricted to admin users or filtered by accessible tasks.
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
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Set timeout for a task.

    Requires authentication and verifies user has access to the task's ticket.

    Args:
        task_id: Task UUID
        request: Timeout request with seconds
        current_user: Authenticated user
        db: Database service

    Returns:
        Updated task information
    """
    # Verify user has access to this task
    await verify_task_access(task_id, current_user, db)
    # Use async database operations (non-blocking)
    try:
        task = await _set_task_timeout_async(db, task_id, request.timeout_seconds)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task_id,
        "timeout_seconds": task.timeout_seconds,
        "status": task.status,
    }


@router.post("/{task_id}/generate-title", response_model=dict)
async def generate_task_title(
    task_id: str,
    context: str | None = Body(None, embed=True),
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Generate a human-readable title for a task using LLM.

    Requires authentication and verifies user has access to the task's ticket.

    Uses the TitleGenerationService with gpt-oss-20b model to create
    a concise, action-oriented title. If the task already has a description,
    the title will be generated from that. Otherwise, both title and
    description will be generated.

    Args:
        task_id: Task UUID
        context: Optional additional context for title generation
        current_user: Authenticated user
        db: Database service

    Returns:
        Task with generated title
    """
    # Verify user has access to this task
    await verify_task_access(task_id, current_user, db)
    from omoi_os.services.task_queue import generate_task_title as gen_title

    # Use async database operations (non-blocking)
    task = await _get_task_async(db, task_id)
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
    task = await _get_task_async(db, task_id)
    return {
        "task_id": task_id,
        "title": task.title,
        "description": task.description,
        "task_type": task.task_type,
    }


@router.post("/generate-titles", response_model=dict)
async def generate_titles_batch(
    limit: int = Body(10, embed=True),
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Generate titles for tasks that don't have one yet (batch operation).

    Requires authentication. This is useful for backfilling titles on existing tasks.

    Args:
        limit: Maximum number of tasks to process (default 10)
        current_user: Authenticated user
        db: Database service

    Returns:
        Results of batch title generation
    """
    # Note: This generates titles for all tasks without titles. In a proper multi-tenant
    # implementation, this should be restricted to admin users or filtered by accessible tasks.
    from omoi_os.services.task_queue import generate_task_title as gen_title

    # Use async database operations (non-blocking)
    task_info = await _get_tasks_without_titles_async(db, limit)

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
            results["tasks"].append(
                {"task_id": info["id"], "title": None, "error": "Generation failed"}
            )

    return results
