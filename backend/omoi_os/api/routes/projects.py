"""Projects API routes for multi-project management."""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func

from omoi_os.api.dependencies import (
    get_db_service,
    get_event_bus_service,
    get_current_user,
    get_user_organization_ids,
    verify_project_access,
    verify_organization_access,
)
from omoi_os.models.user import User
from uuid import UUID
from omoi_os.models.project import Project
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.utils.datetime import utc_now

router = APIRouter()


# ============================================================================
# Async Database Helpers (Non-blocking)
# ============================================================================


async def _create_project_async(
    db: DatabaseService,
    organization_id: UUID,
    name: str,
    description: Optional[str],
    default_phase_id: str,
    github_owner: Optional[str],
    github_repo: Optional[str],
    settings: Optional[dict],
) -> Project:
    """Create a new project within an organization (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        # Check if project with same name exists within the organization
        result = await session.execute(
            select(Project).filter(
                Project.name == name,
                Project.organization_id == organization_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError("Project with this name already exists in this organization")

        project = Project(
            organization_id=organization_id,
            name=name,
            description=description,
            default_phase_id=default_phase_id,
            github_owner=github_owner,
            github_repo=github_repo,
            github_connected=False,
            status="active",
            settings=settings or {},
        )

        session.add(project)
        await session.commit()
        await session.refresh(project)
        return project


async def _list_projects_async(
    db: DatabaseService,
    organization_ids: list,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Tuple[List[Project], int]:
    """List projects filtered by user's accessible organizations (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        # Base query - filter by accessible organizations
        query = select(Project)

        # Filter to only projects in user's orgs (multi-tenant filtering)
        if organization_ids:
            query = query.filter(Project.organization_id.in_(organization_ids))
        else:
            # User has no orgs, return empty
            return [], 0

        if status:
            query = query.filter(Project.status == status)

        # Get total count with same filters
        count_query = select(func.count(Project.id))
        if organization_ids:
            count_query = count_query.filter(Project.organization_id.in_(organization_ids))
        if status:
            count_query = count_query.filter(Project.status == status)

        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        # Get projects
        query = query.order_by(Project.created_at.desc()).limit(limit).offset(offset)
        result = await session.execute(query)
        projects = result.scalars().all()
        return projects, total


async def _get_project_async(
    db: DatabaseService, project_id: str
) -> Optional[Project]:
    """Get a project by ID (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(
            select(Project).filter(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        return project


async def _update_project_async(
    db: DatabaseService,
    project_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    default_phase_id: Optional[str] = None,
    status: Optional[str] = None,
    github_owner: Optional[str] = None,
    github_repo: Optional[str] = None,
    github_connected: Optional[bool] = None,
    settings: Optional[dict] = None,
    autonomous_execution_enabled: Optional[bool] = None,
) -> Optional[Project]:
    """Update a project (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(
            select(Project).filter(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return None

        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if default_phase_id is not None:
            project.default_phase_id = default_phase_id
        if status is not None:
            project.status = status
        if github_owner is not None:
            project.github_owner = github_owner
        if github_repo is not None:
            project.github_repo = github_repo
        if github_connected is not None:
            project.github_connected = github_connected
        if settings is not None:
            project.settings = settings
        if autonomous_execution_enabled is not None:
            project.autonomous_execution_enabled = autonomous_execution_enabled

        project.updated_at = utc_now()
        await session.commit()
        await session.refresh(project)
        return project


async def _delete_project_async(
    db: DatabaseService, project_id: str
) -> Optional[Project]:
    """Soft delete a project (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(
            select(Project).filter(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return None

        project.status = "archived"
        project.updated_at = utc_now()
        await session.commit()
        await session.refresh(project)
        return project


async def _get_project_stats_async(
    db: DatabaseService, project_id: str
) -> Optional[Dict[str, Any]]:
    """Get project stats (ASYNC - non-blocking)."""
    from omoi_os.models.ticket_commit import TicketCommit
    from omoi_os.models.agent import Agent
    from omoi_os.models.task import Task

    async with db.get_async_session() as session:
        # Verify project exists
        result = await session.execute(
            select(Project).filter(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return None

        # Count total tickets for this project
        ticket_count_result = await session.execute(
            select(func.count(Ticket.id)).where(Ticket.project_id == project_id)
        )
        total_tickets = ticket_count_result.scalar() or 0

        # Count tickets by status
        status_result = await session.execute(
            select(Ticket.status, func.count(Ticket.id))
            .where(Ticket.project_id == project_id)
            .group_by(Ticket.status)
        )
        tickets_by_status = {row[0]: row[1] for row in status_result.fetchall()}

        # Count tickets by phase
        phase_result = await session.execute(
            select(Ticket.phase_id, func.count(Ticket.id))
            .where(Ticket.project_id == project_id)
            .group_by(Ticket.phase_id)
        )
        tickets_by_phase = {row[0]: row[1] for row in phase_result.fetchall()}

        # Count active agents working on this project's tasks
        # An agent is "active" for a project if they have a task assigned from a ticket in this project
        # Task statuses: pending, assigned, running, completed, failed
        active_agents_result = await session.execute(
            select(func.count(func.distinct(Task.assigned_agent_id)))
            .select_from(Task)
            .join(Ticket, Task.ticket_id == Ticket.id)
            .where(
                Ticket.project_id == project_id,
                Task.assigned_agent_id.isnot(None),
                Task.status.in_(["assigned", "running"]),
            )
        )
        active_agents = active_agents_result.scalar() or 0

        # Count commits linked to tickets in this project
        commit_result = await session.execute(
            select(func.count(TicketCommit.id))
            .select_from(TicketCommit)
            .join(Ticket, TicketCommit.ticket_id == Ticket.id)
            .where(Ticket.project_id == project_id)
        )
        total_commits = commit_result.scalar() or 0

        return {
            "project_id": project_id,
            "total_tickets": total_tickets,
            "tickets_by_status": tickets_by_status,
            "tickets_by_phase": tickets_by_phase,
            "active_agents": active_agents,
            "total_commits": total_commits,
        }


class ProjectCreate(BaseModel):
    """Request model for creating a project."""

    organization_id: UUID  # Required - projects must belong to an organization
    name: str
    description: Optional[str] = None
    default_phase_id: str = "PHASE_BACKLOG"
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None
    settings: Optional[dict] = None


class ProjectUpdate(BaseModel):
    """Request model for updating a project."""

    name: Optional[str] = None
    description: Optional[str] = None
    default_phase_id: Optional[str] = None
    status: Optional[str] = None
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None
    github_connected: Optional[bool] = None
    settings: Optional[dict] = None
    autonomous_execution_enabled: Optional[bool] = None


class ProjectResponse(BaseModel):
    """Response model for project."""

    id: str
    name: str
    description: Optional[str] = None
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None
    github_connected: bool
    default_phase_id: str
    status: str
    settings: Optional[dict] = None
    autonomous_execution_enabled: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    """Response model for project list."""

    projects: list[ProjectResponse]
    total: int


class ProjectStatsResponse(BaseModel):
    """Response model for project statistics."""

    project_id: str
    total_tickets: int
    tickets_by_status: dict[str, int]
    tickets_by_phase: dict[str, int]
    active_agents: int
    total_commits: int


@router.post("", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """
    Create a new project within an organization.

    Requires authentication and verifies the user has access to the target organization.

    Args:
        project_data: Project creation data (must include organization_id)
        current_user: Authenticated user
        db: Database service
        event_bus: Event bus service

    Returns:
        Created project
    """
    # Verify user has access to the target organization (multi-tenant check)
    await verify_organization_access(project_data.organization_id, current_user, db)

    try:
        # Use async database operations (non-blocking)
        project = await _create_project_async(
            db,
            organization_id=project_data.organization_id,
            name=project_data.name,
            description=project_data.description,
            default_phase_id=project_data.default_phase_id,
            github_owner=project_data.github_owner,
            github_repo=project_data.github_repo,
            settings=project_data.settings,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Emit event
    from omoi_os.services.event_bus import SystemEvent

    event_bus.publish(
        SystemEvent(
            event_type="PROJECT_CREATED",
            entity_type="project",
            entity_id=project.id,
            payload={
                "name": project.name,
                "github_owner": project.github_owner,
                "github_repo": project.github_repo,
            },
        )
    )

    return ProjectResponse.model_validate(project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    status: Optional[str] = Query(
        None, description="Filter by status (active, archived, completed)"
    ),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """
    List all projects the current user has access to.

    Projects are filtered to only include those belonging to organizations
    the user is a member of (multi-tenant filtering).

    Args:
        status: Optional status filter
        limit: Maximum number of projects to return
        offset: Number of projects to skip
        current_user: Authenticated user
        db: Database service

    Returns:
        List of projects the user can access
    """
    # Get user's accessible organization IDs for multi-tenant filtering
    org_ids = await get_user_organization_ids(current_user, db)

    # Use async database operations with org filtering (non-blocking)
    projects, total = await _list_projects_async(db, org_ids, status, limit, offset)

    return ProjectListResponse(
        projects=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get project by ID.

    Requires authentication and verifies the user has access to the project's organization.

    Args:
        project_id: Project ID
        current_user: Authenticated user
        db: Database service

    Returns:
        Project details
    """
    # Verify user has access to this project (multi-tenant check)
    await verify_project_access(project_id, current_user, db)

    # Use async database operations (non-blocking)
    project = await _get_project_async(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """
    Update project.

    Requires authentication and verifies the user has access to the project's organization.

    Args:
        project_id: Project ID
        project_data: Project update data
        current_user: Authenticated user
        db: Database service
        event_bus: Event bus service

    Returns:
        Updated project
    """
    # Verify user has access to this project (multi-tenant check)
    await verify_project_access(project_id, current_user, db)

    # Use async database operations (non-blocking)
    project = await _update_project_async(
        db,
        project_id,
        name=project_data.name,
        description=project_data.description,
        default_phase_id=project_data.default_phase_id,
        status=project_data.status,
        github_owner=project_data.github_owner,
        github_repo=project_data.github_repo,
        github_connected=project_data.github_connected,
        settings=project_data.settings,
        autonomous_execution_enabled=project_data.autonomous_execution_enabled,
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Emit event
    from omoi_os.services.event_bus import SystemEvent

    event_bus.publish(
        SystemEvent(
            event_type="PROJECT_UPDATED",
            entity_type="project",
            entity_id=project.id,
            payload={"changes": project_data.model_dump(exclude_unset=True)},
        )
    )

    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """
    Delete project (soft delete by setting status to archived).

    Requires authentication and verifies the user has access to the project's organization.

    Args:
        project_id: Project ID
        current_user: Authenticated user
        db: Database service
        event_bus: Event bus service

    Returns:
        Success message
    """
    # Verify user has access to this project (multi-tenant check)
    await verify_project_access(project_id, current_user, db)

    # Use async database operations (non-blocking)
    project = await _delete_project_async(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Emit event
    from omoi_os.services.event_bus import SystemEvent

    event_bus.publish(
        SystemEvent(
            event_type="PROJECT_ARCHIVED",
            entity_type="project",
            entity_id=project.id,
        )
    )

    return {"success": True, "message": "Project archived"}


@router.get("/{project_id}/stats", response_model=ProjectStatsResponse)
async def get_project_stats(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get project statistics.

    Requires authentication and verifies the user has access to the project's organization.

    Args:
        project_id: Project ID
        current_user: Authenticated user
        db: Database service

    Returns:
        Project statistics
    """
    # Verify user has access to this project (multi-tenant check)
    await verify_project_access(project_id, current_user, db)

    # Use async database operations (non-blocking)
    stats = await _get_project_stats_async(db, project_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectStatsResponse(**stats)
