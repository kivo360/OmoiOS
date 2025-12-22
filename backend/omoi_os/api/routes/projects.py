"""Projects API routes for multi-project management."""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func

from omoi_os.api.dependencies import get_db_service, get_event_bus_service
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
    name: str,
    description: Optional[str],
    default_phase_id: str,
    github_owner: Optional[str],
    github_repo: Optional[str],
    settings: Optional[dict],
) -> Project:
    """Create a new project (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        # Check if project with same name exists
        result = await session.execute(
            select(Project).filter(Project.name == name)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError("Project with this name already exists")

        project = Project(
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
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Tuple[List[Project], int]:
    """List projects (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        query = select(Project)
        if status:
            query = query.filter(Project.status == status)

        # Get total count
        count_result = await session.execute(
            select(func.count(Project.id)).filter(
                Project.status == status if status else True
            )
        )
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
    from omoi_os.ticketing.models import TicketCommit

    async with db.get_async_session() as session:
        result = await session.execute(
            select(Project).filter(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return None

        # Count commits
        commit_result = await session.execute(
            select(func.count(TicketCommit.id))
            .select_from(TicketCommit)
            .join(Ticket, TicketCommit.ticket_id == Ticket.id)
        )
        total_commits = commit_result.scalar() or 0

        return {
            "project_id": project_id,
            "total_tickets": 0,  # Placeholder
            "tickets_by_status": {},  # Placeholder
            "tickets_by_phase": {},  # Placeholder
            "active_agents": 0,  # Placeholder
            "total_commits": total_commits,
        }


class ProjectCreate(BaseModel):
    """Request model for creating a project."""

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
    db: DatabaseService = Depends(get_db_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """
    Create a new project.

    Args:
        project_data: Project creation data
        db: Database service
        event_bus: Event bus service

    Returns:
        Created project
    """
    try:
        # Use async database operations (non-blocking)
        project = await _create_project_async(
            db,
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
    db: DatabaseService = Depends(get_db_service),
):
    """
    List all projects.

    Args:
        status: Optional status filter
        limit: Maximum number of projects to return
        offset: Number of projects to skip
        db: Database service

    Returns:
        List of projects
    """
    # Use async database operations (non-blocking)
    projects, total = await _list_projects_async(db, status, limit, offset)

    return ProjectListResponse(
        projects=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get project by ID.

    Args:
        project_id: Project ID
        db: Database service

    Returns:
        Project details
    """
    # Use async database operations (non-blocking)
    project = await _get_project_async(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    db: DatabaseService = Depends(get_db_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """
    Update project.

    Args:
        project_id: Project ID
        project_data: Project update data
        db: Database service
        event_bus: Event bus service

    Returns:
        Updated project
    """
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
    db: DatabaseService = Depends(get_db_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
):
    """
    Delete project (soft delete by setting status to archived).

    Args:
        project_id: Project ID
        db: Database service
        event_bus: Event bus service

    Returns:
        Success message
    """
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
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get project statistics.

    Args:
        project_id: Project ID
        db: Database service

    Returns:
        Project statistics
    """
    # Use async database operations (non-blocking)
    stats = await _get_project_stats_async(db, project_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectStatsResponse(**stats)
