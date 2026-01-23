"""Projects API routes for multi-project management."""

from datetime import datetime
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from omoi_os.api.dependencies import (
    get_current_user,
    get_db_service,
    get_event_bus_service,
)
from omoi_os.models.project import Project
from omoi_os.models.ticket import Ticket
from omoi_os.models.user import User
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.utils.datetime import utc_now

router = APIRouter()


# =============================================================================
# Spec-Driven Settings Models
# =============================================================================


class StrictnessLevel(str, Enum):
    """Strictness level for spec-driven development."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    STRICT = "strict"


class SpecDrivenSettingsResponse(BaseModel):
    """Response model for spec-driven settings."""

    enabled: bool = False
    coverage_threshold: int = Field(default=80, ge=0, le=100)
    strictness: StrictnessLevel = StrictnessLevel.MEDIUM
    auto_generate_tasks: bool = True
    require_design_approval: bool = True

    model_config = ConfigDict(from_attributes=True)


class SpecDrivenSettingsUpdate(BaseModel):
    """Request model for updating spec-driven settings."""

    enabled: Optional[bool] = None
    coverage_threshold: Optional[int] = Field(default=None, ge=0, le=100)
    strictness: Optional[StrictnessLevel] = None
    auto_generate_tasks: Optional[bool] = None
    require_design_approval: Optional[bool] = None


# Default spec-driven settings
DEFAULT_SPEC_DRIVEN_SETTINGS = {
    "enabled": False,
    "coverage_threshold": 80,
    "strictness": "medium",
    "auto_generate_tasks": True,
    "require_design_approval": True,
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
    with db.get_session() as session:
        # Check if project with same name exists
        existing = (
            session.query(Project).filter(Project.name == project_data.name).first()
        )
        if existing:
            raise HTTPException(
                status_code=409, detail="Project with this name already exists"
            )

        project = Project(
            name=project_data.name,
            description=project_data.description,
            default_phase_id=project_data.default_phase_id,
            github_owner=project_data.github_owner,
            github_repo=project_data.github_repo,
            github_connected=False,
            status="active",
            settings=project_data.settings or {},
        )

        session.add(project)
        session.commit()

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
    with db.get_session() as session:
        query = session.query(Project)

        if status:
            query = query.filter(Project.status == status)

        total = query.count()

        projects = (
            query.order_by(Project.created_at.desc()).limit(limit).offset(offset).all()
        )

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
    with db.get_session() as session:
        project = session.get(Project, project_id)
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
    with db.get_session() as session:
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Update fields
        if project_data.name is not None:
            project.name = project_data.name
        if project_data.description is not None:
            project.description = project_data.description
        if project_data.default_phase_id is not None:
            project.default_phase_id = project_data.default_phase_id
        if project_data.status is not None:
            project.status = project_data.status
        if project_data.github_owner is not None:
            project.github_owner = project_data.github_owner
        if project_data.github_repo is not None:
            project.github_repo = project_data.github_repo
        if project_data.github_connected is not None:
            project.github_connected = project_data.github_connected
        if project_data.settings is not None:
            project.settings = project_data.settings

        project.updated_at = utc_now()

        session.commit()

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
    with db.get_session() as session:
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Soft delete - set status to archived
        project.status = "archived"
        project.updated_at = utc_now()

        session.commit()

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
    with db.get_session() as session:
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get tickets for this project
        # Note: This assumes tickets will have project_id field in the future
        # For now, we'll return basic stats
        from sqlalchemy import func
        from omoi_os.ticketing.models import TicketCommit

        # Count tickets (when project_id is added to Ticket model)
        # For now, return placeholder stats
        total_tickets = 0
        tickets_by_status = {}
        tickets_by_phase = {}

        # Count commits (if we can link via tickets)
        total_commits = (
            session.query(func.count(TicketCommit.id))
            .join(Ticket, TicketCommit.ticket_id == Ticket.id)
            .scalar()
            or 0
        )

        # Count active agents (placeholder - would need project_id on Agent)
        active_agents = 0

        return ProjectStatsResponse(
            project_id=project_id,
            total_tickets=total_tickets,
            tickets_by_status=tickets_by_status,
            tickets_by_phase=tickets_by_phase,
            active_agents=active_agents,
            total_commits=total_commits,
        )


# =============================================================================
# Spec-Driven Settings Routes
# =============================================================================


@router.get(
    "/{project_id}/settings/spec-driven",
    response_model=SpecDrivenSettingsResponse,
)
async def get_spec_driven_settings(
    project_id: str,
    db: DatabaseService = Depends(get_db_service),
    current_user: User = Depends(get_current_user),
):
    """
    Get spec-driven settings for a project.

    Returns default settings if no settings have been configured.

    Args:
        project_id: Project ID
        db: Database service
        current_user: Authenticated user

    Returns:
        Spec-driven settings

    Raises:
        404: Project not found
    """
    with db.get_session() as session:
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get spec_driven settings from project settings, or use defaults
        settings = project.settings or {}
        spec_driven = settings.get("spec_driven", DEFAULT_SPEC_DRIVEN_SETTINGS.copy())

        # Ensure all default fields are present
        for key, value in DEFAULT_SPEC_DRIVEN_SETTINGS.items():
            if key not in spec_driven:
                spec_driven[key] = value

        return SpecDrivenSettingsResponse(**spec_driven)


@router.patch(
    "/{project_id}/settings/spec-driven",
    response_model=SpecDrivenSettingsResponse,
)
async def update_spec_driven_settings(
    project_id: str,
    settings_update: SpecDrivenSettingsUpdate,
    db: DatabaseService = Depends(get_db_service),
    event_bus: EventBusService = Depends(get_event_bus_service),
    current_user: User = Depends(get_current_user),
):
    """
    Update spec-driven settings for a project.

    Creates settings if they don't exist.

    Args:
        project_id: Project ID
        settings_update: Settings to update
        db: Database service
        event_bus: Event bus service
        current_user: Authenticated user

    Returns:
        Updated spec-driven settings

    Raises:
        404: Project not found
        400/422: Validation error
    """
    with db.get_session() as session:
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Initialize settings if none exist
        if project.settings is None:
            project.settings = {}

        # Get current spec_driven settings or defaults
        current_settings = project.settings.get(
            "spec_driven", DEFAULT_SPEC_DRIVEN_SETTINGS.copy()
        )

        # Update with provided values (only non-None values)
        update_data = settings_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                # Convert enum to string for storage
                if isinstance(value, StrictnessLevel):
                    current_settings[key] = value.value
                else:
                    current_settings[key] = value

        # Update project settings
        project.settings = {**project.settings, "spec_driven": current_settings}
        project.updated_at = utc_now()

        session.commit()
        session.refresh(project)

        # Emit event
        from omoi_os.services.event_bus import SystemEvent

        event_bus.publish(
            SystemEvent(
                event_type="PROJECT_SETTINGS_UPDATED",
                entity_type="project",
                entity_id=project.id,
                payload={"settings_type": "spec_driven", "changes": update_data},
            )
        )

        return SpecDrivenSettingsResponse(**current_settings)
