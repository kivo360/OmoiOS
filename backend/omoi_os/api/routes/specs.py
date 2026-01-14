"""
Specification Management API Routes

Provides endpoints for managing project specifications including:
- Specs CRUD operations
- Requirements with acceptance criteria
- Design artifacts
- Linked tasks
"""

import logging
from datetime import datetime
from typing import Optional, List, Any, Dict
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from omoi_os.api.dependencies import (
    get_db_service,
    get_current_user,
    verify_project_access,
    verify_spec_access,
)
from omoi_os.models.project import Project
from omoi_os.models.user import User
from omoi_os.models.spec import (
    Spec as SpecModel,
    SpecRequirement as SpecRequirementModel,
    SpecAcceptanceCriterion as SpecCriterionModel,
    SpecTask as SpecTaskModel,
    SpecVersion as SpecVersionModel,
)
from omoi_os.services.billing_service import BillingService, get_billing_service
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/specs", tags=["specs"])


# ============================================================================
# Async Database Helpers (Non-blocking)
# ============================================================================


async def _list_project_specs_async(
    db: DatabaseService,
    project_id: str,
    status: Optional[str] = None,
) -> List[SpecModel]:
    """List specs for a project (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        query = (
            select(SpecModel)
            .filter(SpecModel.project_id == project_id)
            .options(
                selectinload(SpecModel.requirements).selectinload(
                    SpecRequirementModel.criteria
                ),
                selectinload(SpecModel.tasks),
            )
        )
        if status:
            query = query.filter(SpecModel.status == status)
        query = query.order_by(SpecModel.created_at.desc())
        result = await session.execute(query)
        specs = result.scalars().all()
        return specs


async def _create_spec_async(
    db: DatabaseService,
    project_id: str,
    title: str,
    description: Optional[str],
    user_id: Optional[UUID] = None,
) -> SpecModel:
    """Create a new spec (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        new_spec = SpecModel(
            project_id=project_id,
            title=title,
            description=description,
            status="draft",
            phase="Requirements",
            user_id=user_id,
        )
        session.add(new_spec)
        await session.commit()
        await session.refresh(new_spec)

        # Re-query with eager loading to avoid DetachedInstanceError
        # when accessing relationships after session closes
        result = await session.execute(
            select(SpecModel)
            .filter(SpecModel.id == new_spec.id)
            .options(
                selectinload(SpecModel.requirements).selectinload(
                    SpecRequirementModel.criteria
                ),
                selectinload(SpecModel.tasks),
            )
        )
        return result.scalar_one()


async def _get_spec_async(
    db: DatabaseService, spec_id: str
) -> Optional[SpecModel]:
    """Get a spec by ID (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(
            select(SpecModel)
            .filter(SpecModel.id == spec_id)
            .options(
                selectinload(SpecModel.requirements).selectinload(
                    SpecRequirementModel.criteria
                ),
                selectinload(SpecModel.tasks),
            )
        )
        spec = result.scalar_one_or_none()
        return spec


async def _update_spec_async(
    db: DatabaseService,
    spec_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    phase: Optional[str] = None,
) -> Optional[SpecModel]:
    """Update a spec (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(
            select(SpecModel)
            .filter(SpecModel.id == spec_id)
            .options(
                selectinload(SpecModel.requirements).selectinload(
                    SpecRequirementModel.criteria
                ),
                selectinload(SpecModel.tasks),
            )
        )
        spec = result.scalar_one_or_none()
        if not spec:
            return None

        if title is not None:
            spec.title = title
        if description is not None:
            spec.description = description
        if status is not None:
            spec.status = status
        if phase is not None:
            spec.phase = phase

        await session.commit()

        # Re-query with eager loading to avoid DetachedInstanceError
        # when accessing relationships after session closes
        result = await session.execute(
            select(SpecModel)
            .filter(SpecModel.id == spec_id)
            .options(
                selectinload(SpecModel.requirements).selectinload(
                    SpecRequirementModel.criteria
                ),
                selectinload(SpecModel.tasks),
            )
        )
        return result.scalar_one_or_none()


async def _delete_spec_async(db: DatabaseService, spec_id: str) -> bool:
    """Delete a spec (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(
            select(SpecModel).filter(SpecModel.id == spec_id)
        )
        spec = result.scalar_one_or_none()
        if not spec:
            return False

        await session.delete(spec)
        await session.commit()
        return True


async def _add_requirement_async(
    db: DatabaseService,
    spec_id: str,
    title: str,
    condition: str,
    action: str,
    linked_design: Optional[str] = None,
) -> Optional[SpecRequirementModel]:
    """Add a requirement to a spec (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        # Verify spec exists
        result = await session.execute(
            select(SpecModel).filter(SpecModel.id == spec_id)
        )
        spec = result.scalar_one_or_none()
        if not spec:
            return None

        new_req = SpecRequirementModel(
            spec_id=spec_id,
            title=title,
            condition=condition,
            action=action,
            status="pending",
            linked_design=linked_design,
        )
        session.add(new_req)
        await session.commit()
        await session.refresh(new_req)
        return new_req


async def _update_requirement_async(
    db: DatabaseService,
    spec_id: str,
    req_id: str,
    title: Optional[str] = None,
    condition: Optional[str] = None,
    action: Optional[str] = None,
    status: Optional[str] = None,
    linked_design: Optional[str] = None,
) -> Optional[SpecRequirementModel]:
    """Update a requirement (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(
            select(SpecRequirementModel)
            .filter(
                SpecRequirementModel.id == req_id,
                SpecRequirementModel.spec_id == spec_id,
            )
            .options(selectinload(SpecRequirementModel.criteria))
        )
        req = result.scalar_one_or_none()
        if not req:
            return None

        if title is not None:
            req.title = title
        if condition is not None:
            req.condition = condition
        if action is not None:
            req.action = action
        if status is not None:
            req.status = status
        if linked_design is not None:
            req.linked_design = linked_design

        await session.commit()
        await session.refresh(req)
        return req


async def _delete_requirement_async(
    db: DatabaseService, spec_id: str, req_id: str
) -> bool:
    """Delete a requirement (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(
            select(SpecRequirementModel).filter(
                SpecRequirementModel.id == req_id,
                SpecRequirementModel.spec_id == spec_id,
            )
        )
        req = result.scalar_one_or_none()
        if not req:
            return False

        await session.delete(req)
        await session.commit()
        return True


async def _add_criterion_async(
    db: DatabaseService,
    spec_id: str,
    req_id: str,
    text: str,
) -> Optional[SpecCriterionModel]:
    """Add a criterion to a requirement (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        # Verify requirement exists
        result = await session.execute(
            select(SpecRequirementModel).filter(
                SpecRequirementModel.id == req_id,
                SpecRequirementModel.spec_id == spec_id,
            )
        )
        req = result.scalar_one_or_none()
        if not req:
            return None

        new_criterion = SpecCriterionModel(
            requirement_id=req_id,
            text=text,
            completed=False,
        )
        session.add(new_criterion)
        await session.commit()
        await session.refresh(new_criterion)
        return new_criterion


async def _update_criterion_async(
    db: DatabaseService,
    criterion_id: str,
    req_id: str,
    text: Optional[str] = None,
    completed: Optional[bool] = None,
) -> Optional[SpecCriterionModel]:
    """Update a criterion (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(
            select(SpecCriterionModel).filter(
                SpecCriterionModel.id == criterion_id,
                SpecCriterionModel.requirement_id == req_id,
            )
        )
        criterion = result.scalar_one_or_none()
        if not criterion:
            return None

        if text is not None:
            criterion.text = text
        if completed is not None:
            criterion.completed = completed

        await session.commit()
        await session.refresh(criterion)
        return criterion


async def _delete_criterion_async(
    db: DatabaseService,
    criterion_id: str,
    req_id: str,
) -> bool:
    """Delete a criterion (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(
            select(SpecCriterionModel).filter(
                SpecCriterionModel.id == criterion_id,
                SpecCriterionModel.requirement_id == req_id,
            )
        )
        criterion = result.scalar_one_or_none()
        if not criterion:
            return False

        await session.delete(criterion)
        await session.commit()
        return True


async def _update_design_async(
    db: DatabaseService, spec_id: str, design: Dict[str, Any]
) -> Optional[SpecModel]:
    """Update spec design (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(
            select(SpecModel).filter(SpecModel.id == spec_id)
        )
        spec = result.scalar_one_or_none()
        if not spec:
            return None

        spec.design = design
        await session.commit()
        return spec


async def _add_task_async(
    db: DatabaseService,
    spec_id: str,
    title: str,
    description: Optional[str],
    phase: str,
    priority: str,
) -> Optional[SpecTaskModel]:
    """Add a task to a spec (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        # Verify spec exists
        result = await session.execute(
            select(SpecModel).filter(SpecModel.id == spec_id)
        )
        spec = result.scalar_one_or_none()
        if not spec:
            return None

        new_task = SpecTaskModel(
            spec_id=spec_id,
            title=title,
            description=description,
            phase=phase,
            priority=priority,
            status="pending",
        )
        session.add(new_task)
        await session.commit()
        await session.refresh(new_task)
        return new_task


async def _list_spec_tasks_async(
    db: DatabaseService, spec_id: str
) -> Optional[List[SpecTaskModel]]:
    """List tasks for a spec (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(
            select(SpecModel)
            .filter(SpecModel.id == spec_id)
            .options(selectinload(SpecModel.tasks))
        )
        spec = result.scalar_one_or_none()
        if not spec:
            return None
        return spec.tasks


async def _update_task_async(
    db: DatabaseService,
    spec_id: str,
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    phase: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    assigned_agent: Optional[str] = None,
) -> Optional[SpecTaskModel]:
    """Update a task (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(
            select(SpecTaskModel).filter(
                SpecTaskModel.id == task_id,
                SpecTaskModel.spec_id == spec_id,
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            return None

        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if phase is not None:
            task.phase = phase
        if priority is not None:
            task.priority = priority
        if status is not None:
            task.status = status
        if assigned_agent is not None:
            task.assigned_agent = assigned_agent

        await session.commit()
        await session.refresh(task)
        return task


async def _delete_task_async(
    db: DatabaseService, spec_id: str, task_id: str
) -> bool:
    """Delete a task (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(
            select(SpecTaskModel).filter(
                SpecTaskModel.id == task_id,
                SpecTaskModel.spec_id == spec_id,
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            return False

        await session.delete(task)
        await session.commit()
        return True


async def _approve_requirements_async(db: DatabaseService, spec_id: str) -> bool:
    """Approve requirements (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(
            select(SpecModel).filter(SpecModel.id == spec_id)
        )
        spec = result.scalar_one_or_none()
        if not spec:
            return False

        spec.requirements_approved = True
        spec.requirements_approved_at = utc_now()
        spec.status = "design"
        spec.phase = "Design"
        await session.commit()
        return True


async def _approve_design_async(db: DatabaseService, spec_id: str) -> bool:
    """Approve design (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(
            select(SpecModel).filter(SpecModel.id == spec_id)
        )
        spec = result.scalar_one_or_none()
        if not spec:
            return False

        spec.design_approved = True
        spec.design_approved_at = utc_now()
        spec.status = "executing"
        spec.phase = "Implementation"
        await session.commit()
        return True


async def _create_spec_version_async(
    db: DatabaseService,
    spec_id: str,
    change_type: str,
    change_summary: str,
    change_details: Optional[Dict[str, Any]] = None,
    created_by: Optional[str] = None,
) -> Optional[SpecVersionModel]:
    """Create a version history entry for a spec (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        # Get the spec to create a snapshot
        result = await session.execute(
            select(SpecModel).filter(SpecModel.id == spec_id)
        )
        spec = result.scalar_one_or_none()
        if not spec:
            return None

        # Get the next version number
        version_result = await session.execute(
            select(SpecVersionModel)
            .filter(SpecVersionModel.spec_id == spec_id)
            .order_by(SpecVersionModel.version_number.desc())
            .limit(1)
        )
        latest_version = version_result.scalar_one_or_none()
        next_version = (latest_version.version_number + 1) if latest_version else 1

        # Create snapshot of current state
        snapshot = {
            "title": spec.title,
            "description": spec.description,
            "status": spec.status,
            "phase": spec.phase,
            "progress": spec.progress,
            "requirements_approved": spec.requirements_approved,
            "design_approved": spec.design_approved,
        }

        new_version = SpecVersionModel(
            spec_id=spec_id,
            version_number=next_version,
            change_type=change_type,
            change_summary=change_summary,
            change_details=change_details,
            created_by=created_by,
            snapshot=snapshot,
        )
        session.add(new_version)
        await session.commit()
        await session.refresh(new_version)
        return new_version


async def _list_spec_versions_async(
    db: DatabaseService,
    spec_id: str,
    limit: int = 20,
) -> List[SpecVersionModel]:
    """List version history for a spec (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        result = await session.execute(
            select(SpecVersionModel)
            .filter(SpecVersionModel.spec_id == spec_id)
            .order_by(SpecVersionModel.created_at.desc())
            .limit(limit)
        )
        versions = result.scalars().all()
        return list(versions)


# ============================================================================
# Billing Enforcement Helpers
# ============================================================================


async def _get_organization_id_for_spec(
    db: DatabaseService, spec_id: str
) -> Optional[UUID]:
    """Get the organization ID for a spec via its project.

    Returns None if spec or project not found, or if project has no organization.
    """
    async with db.get_async_session() as session:
        # Get spec with project
        result = await session.execute(
            select(SpecModel).filter(SpecModel.id == spec_id)
        )
        spec = result.scalar_one_or_none()
        if not spec:
            return None

        # Get project to find organization
        project_result = await session.execute(
            select(Project).filter(Project.id == spec.project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project or not project.organization_id:
            return None

        return project.organization_id


async def _check_billing_for_spec_execution(
    db: DatabaseService, spec_id: str
) -> tuple[bool, str]:
    """Check if spec execution is allowed based on billing status.

    Returns:
        Tuple of (can_execute, reason/error_message)
    """
    # Get organization ID for this spec
    org_id = await _get_organization_id_for_spec(db, spec_id)

    if not org_id:
        # No organization linked - block execution for safety
        # This prevents specs without proper org setup from consuming resources
        logger.warning(f"Spec {spec_id} has no linked organization - blocking execution")
        return False, "Spec is not linked to an organization. Please ensure your project is properly set up."

    # Check billing status
    billing_service = get_billing_service(db)
    can_execute, reason = billing_service.can_execute_workflow(org_id)

    if not can_execute:
        logger.warning(
            f"Billing check failed for spec {spec_id} (org: {org_id}): {reason}"
        )

    return can_execute, reason


# ============================================================================
# Pydantic Models
# ============================================================================


class AcceptanceCriterion(BaseModel):
    id: str
    text: str
    completed: bool = False

    model_config = ConfigDict(from_attributes=True)


class Requirement(BaseModel):
    id: str
    title: str
    condition: str  # EARS "WHEN" clause
    action: str  # EARS "THE SYSTEM SHALL" clause
    criteria: list[AcceptanceCriterion] = []
    linked_design: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed

    model_config = ConfigDict(from_attributes=True)


class ApiEndpoint(BaseModel):
    method: str
    endpoint: str
    description: str


class DesignArtifact(BaseModel):
    architecture: Optional[str] = None
    data_model: Optional[str] = None
    api_spec: list[ApiEndpoint] = []


class SpecTask(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    phase: str
    priority: str
    status: str = "pending"
    assigned_agent: Optional[str] = None
    dependencies: list[str] = []
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class SpecExecution(BaseModel):
    overall_progress: float = 0
    test_coverage: float = 0
    tests_total: int = 0
    tests_passing: int = 0
    active_agents: int = 0
    commits: int = 0
    lines_added: int = 0
    lines_removed: int = 0


class SpecCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    project_id: str


class SpecUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = None
    phase: Optional[str] = None


class SpecResponse(BaseModel):
    id: str
    project_id: str
    title: str
    description: Optional[str] = None
    status: str  # draft, requirements, design, executing, completed
    phase: str  # Requirements, Design, Implementation, Testing, Done
    progress: float = 0
    test_coverage: float = 0
    active_agents: int = 0
    linked_tickets: int = 0
    requirements: list[Requirement] = []
    design: Optional[DesignArtifact] = None
    tasks: list[SpecTask] = []
    execution: Optional[SpecExecution] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SpecListResponse(BaseModel):
    specs: list[SpecResponse]
    total: int


class RequirementCreate(BaseModel):
    title: str
    condition: str
    action: str
    linked_design: Optional[str] = None  # Link to design section/ID


class RequirementUpdate(BaseModel):
    title: Optional[str] = None
    condition: Optional[str] = None
    action: Optional[str] = None
    status: Optional[str] = None
    linked_design: Optional[str] = None  # Link to design section/ID


class CriterionCreate(BaseModel):
    text: str


class CriterionUpdate(BaseModel):
    text: Optional[str] = None
    completed: Optional[bool] = None


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    phase: str = "Implementation"
    priority: str = "medium"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    phase: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_agent: Optional[str] = None


class SpecVersionResponse(BaseModel):
    id: str
    spec_id: str
    version_number: int
    change_type: str
    change_summary: str
    change_details: Optional[dict] = None
    created_by: Optional[str] = None
    snapshot: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SpecVersionListResponse(BaseModel):
    versions: list[SpecVersionResponse]
    total: int


class SpecExecuteRequest(BaseModel):
    """Request body for spec execution."""

    working_directory: Optional[str] = Field(
        None,
        description="Working directory for file operations. Defaults to current directory.",
    )
    enable_embeddings: bool = Field(
        True,
        description="Whether to enable embedding service for semantic deduplication.",
    )


class SpecExecuteResponse(BaseModel):
    """Response for spec execution."""

    spec_id: str
    status: str  # started, failed
    message: str
    current_phase: Optional[str] = None


class SpecPhaseDataResponse(BaseModel):
    """Response containing spec phase data."""

    spec_id: str
    current_phase: str
    phase_data: Dict[str, Any] = {}
    phase_attempts: Dict[str, int] = {}
    last_checkpoint_at: Optional[datetime] = None
    last_error: Optional[str] = None


class SpecSyncStatsResponse(BaseModel):
    """Response containing sync statistics."""

    requirements_created: int = 0
    requirements_skipped: int = 0
    criteria_created: int = 0
    criteria_skipped: int = 0
    tasks_created: int = 0
    tasks_skipped: int = 0
    errors: List[str] = []


# ============================================================================
# Helper Functions
# ============================================================================


def _spec_to_response(spec: SpecModel) -> SpecResponse:
    """Convert database Spec model to response."""
    requirements = []
    for req in spec.requirements:
        criteria = [
            AcceptanceCriterion(
                id=c.id,
                text=c.text,
                completed=c.completed,
            )
            for c in req.criteria
        ]
        requirements.append(
            Requirement(
                id=req.id,
                title=req.title,
                condition=req.condition,
                action=req.action,
                criteria=criteria,
                linked_design=req.linked_design,
                status=req.status,
            )
        )

    tasks = [
        SpecTask(
            id=t.id,
            title=t.title,
            description=t.description,
            phase=t.phase,
            priority=t.priority,
            status=t.status,
            assigned_agent=t.assigned_agent,
            dependencies=t.dependencies or [],
            estimated_hours=t.estimated_hours,
            actual_hours=t.actual_hours,
        )
        for t in spec.tasks
    ]

    design = None
    if spec.design:
        design = DesignArtifact(
            architecture=spec.design.get("architecture"),
            data_model=spec.design.get("data_model"),
            api_spec=[ApiEndpoint(**ep) for ep in spec.design.get("api_spec", [])],
        )

    execution = None
    if spec.execution:
        execution = SpecExecution(**spec.execution)

    return SpecResponse(
        id=spec.id,
        project_id=spec.project_id,
        title=spec.title,
        description=spec.description,
        status=spec.status,
        phase=spec.phase,
        progress=spec.progress,
        test_coverage=spec.test_coverage,
        active_agents=spec.active_agents,
        linked_tickets=spec.linked_tickets,
        requirements=requirements,
        design=design,
        tasks=tasks,
        execution=execution,
        created_at=spec.created_at,
        updated_at=spec.updated_at,
    )


# ============================================================================
# API Routes
# ============================================================================


@router.get("/project/{project_id}", response_model=SpecListResponse)
async def list_project_specs(
    project_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    _: str = Depends(verify_project_access),  # Verify access to project
):
    """List all specs for a project."""
    # Use async database operations (non-blocking)
    specs = await _list_project_specs_async(db, project_id, status)
    return SpecListResponse(
        specs=[_spec_to_response(s) for s in specs],
        total=len(specs),
    )


@router.post("", response_model=SpecResponse)
async def create_spec(
    spec: SpecCreate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """Create a new specification."""
    # Verify user has access to the project
    await verify_project_access(spec.project_id, current_user, db)

    # Use async database operations (non-blocking)
    new_spec = await _create_spec_async(
        db, spec.project_id, spec.title, spec.description, user_id=current_user.id
    )

    # Create initial version history entry
    await _create_spec_version_async(
        db,
        new_spec.id,
        change_type="created",
        change_summary=f"Specification '{spec.title}' created",
        created_by=str(current_user.id),
    )

    return _spec_to_response(new_spec)


@router.get("/{spec_id}", response_model=SpecResponse)
async def get_spec(
    spec_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    _: str = Depends(verify_spec_access),  # Verify access to spec
):
    """Get a spec by ID."""
    # Use async database operations (non-blocking)
    spec = await _get_spec_async(db, spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")
    return _spec_to_response(spec)


@router.patch("/{spec_id}", response_model=SpecResponse)
async def update_spec(
    spec_id: str,
    updates: SpecUpdate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    _: str = Depends(verify_spec_access),  # Verify access to spec
):
    """Update a spec."""
    # Get current state before update for change tracking
    old_spec = await _get_spec_async(db, spec_id)
    if not old_spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    # Use async database operations (non-blocking)
    spec = await _update_spec_async(
        db, spec_id, updates.title, updates.description, updates.status, updates.phase
    )
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    # Build change details
    change_details: Dict[str, Any] = {}
    change_parts = []
    if updates.title is not None and updates.title != old_spec.title:
        change_details["title"] = {"old": old_spec.title, "new": updates.title}
        change_parts.append("title")
    if updates.description is not None and updates.description != old_spec.description:
        change_details["description"] = {"old": old_spec.description, "new": updates.description}
        change_parts.append("description")
    if updates.status is not None and updates.status != old_spec.status:
        change_details["status"] = {"old": old_spec.status, "new": updates.status}
        change_parts.append("status")
    if updates.phase is not None and updates.phase != old_spec.phase:
        change_details["phase"] = {"old": old_spec.phase, "new": updates.phase}
        change_parts.append("phase")

    # Create version history entry if there were changes
    if change_parts:
        change_type = "phase_changed" if "phase" in change_parts else "updated"
        change_summary = f"Updated {', '.join(change_parts)}"
        await _create_spec_version_async(
            db,
            spec_id,
            change_type=change_type,
            change_summary=change_summary,
            change_details=change_details,
        )

    return _spec_to_response(spec)


@router.delete("/{spec_id}")
async def delete_spec(
    spec_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    _: str = Depends(verify_spec_access),  # Verify access to spec
):
    """Delete a spec."""
    # Use async database operations (non-blocking)
    deleted = await _delete_spec_async(db, spec_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Spec not found")
    return {"message": "Spec deleted successfully"}


# ============================================================================
# Requirements Routes
# ============================================================================


@router.post("/{spec_id}/requirements", response_model=Requirement)
async def add_requirement(
    spec_id: str,
    req: RequirementCreate,
    db: DatabaseService = Depends(get_db_service),
):
    """Add a requirement to a spec."""
    # Use async database operations (non-blocking)
    new_req = await _add_requirement_async(
        db, spec_id, req.title, req.condition, req.action, req.linked_design
    )
    if not new_req:
        raise HTTPException(status_code=404, detail="Spec not found")

    return Requirement(
        id=new_req.id,
        title=new_req.title,
        condition=new_req.condition,
        action=new_req.action,
        criteria=[],
        linked_design=new_req.linked_design,
        status=new_req.status,
    )


@router.patch("/{spec_id}/requirements/{req_id}", response_model=Requirement)
async def update_requirement(
    spec_id: str,
    req_id: str,
    updates: RequirementUpdate,
    db: DatabaseService = Depends(get_db_service),
):
    """Update a requirement."""
    # Use async database operations (non-blocking)
    req = await _update_requirement_async(
        db, spec_id, req_id, updates.title, updates.condition, updates.action,
        updates.status, updates.linked_design
    )
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    criteria = [
        AcceptanceCriterion(id=c.id, text=c.text, completed=c.completed)
        for c in req.criteria
    ]

    return Requirement(
        id=req.id,
        title=req.title,
        condition=req.condition,
        action=req.action,
        criteria=criteria,
        linked_design=req.linked_design,
        status=req.status,
    )


@router.delete("/{spec_id}/requirements/{req_id}")
async def delete_requirement(
    spec_id: str,
    req_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Delete a requirement."""
    # Use async database operations (non-blocking)
    deleted = await _delete_requirement_async(db, spec_id, req_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return {"message": "Requirement deleted successfully"}


# ============================================================================
# Acceptance Criteria Routes
# ============================================================================


@router.post(
    "/{spec_id}/requirements/{req_id}/criteria", response_model=AcceptanceCriterion
)
async def add_criterion(
    spec_id: str,
    req_id: str,
    criterion: CriterionCreate,
    db: DatabaseService = Depends(get_db_service),
):
    """Add an acceptance criterion to a requirement."""
    # Use async database operations (non-blocking)
    new_criterion = await _add_criterion_async(db, spec_id, req_id, criterion.text)
    if not new_criterion:
        raise HTTPException(status_code=404, detail="Requirement not found")

    return AcceptanceCriterion(
        id=new_criterion.id,
        text=new_criterion.text,
        completed=new_criterion.completed,
    )


@router.patch("/{spec_id}/requirements/{req_id}/criteria/{criterion_id}")
async def update_criterion(
    spec_id: str,
    req_id: str,
    criterion_id: str,
    updates: CriterionUpdate,
    db: DatabaseService = Depends(get_db_service),
):
    """Update an acceptance criterion."""
    # Use async database operations (non-blocking)
    criterion = await _update_criterion_async(
        db, criterion_id, req_id, updates.text, updates.completed
    )
    if not criterion:
        raise HTTPException(status_code=404, detail="Criterion not found")

    return AcceptanceCriterion(
        id=criterion.id,
        text=criterion.text,
        completed=criterion.completed,
    )


@router.delete("/{spec_id}/requirements/{req_id}/criteria/{criterion_id}")
async def delete_criterion(
    spec_id: str,
    req_id: str,
    criterion_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Delete an acceptance criterion."""
    # Use async database operations (non-blocking)
    deleted = await _delete_criterion_async(db, criterion_id, req_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Criterion not found")
    return {"message": "Criterion deleted successfully"}


# ============================================================================
# Design Routes
# ============================================================================


@router.put("/{spec_id}/design", response_model=DesignArtifact)
async def update_design(
    spec_id: str,
    design: DesignArtifact,
    db: DatabaseService = Depends(get_db_service),
):
    """Update the design for a spec."""
    # Use async database operations (non-blocking)
    spec = await _update_design_async(db, spec_id, design.model_dump())
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")
    return design


# ============================================================================
# Tasks Routes
# ============================================================================


@router.post("/{spec_id}/tasks", response_model=SpecTask)
async def add_task(
    spec_id: str,
    task: TaskCreate,
    db: DatabaseService = Depends(get_db_service),
):
    """Add a task to a spec."""
    # Use async database operations (non-blocking)
    new_task = await _add_task_async(
        db, spec_id, task.title, task.description, task.phase, task.priority
    )
    if not new_task:
        raise HTTPException(status_code=404, detail="Spec not found")

    return SpecTask(
        id=new_task.id,
        title=new_task.title,
        description=new_task.description,
        phase=new_task.phase,
        priority=new_task.priority,
        status=new_task.status,
        assigned_agent=new_task.assigned_agent,
        dependencies=new_task.dependencies or [],
        estimated_hours=new_task.estimated_hours,
        actual_hours=new_task.actual_hours,
    )


@router.get("/{spec_id}/tasks", response_model=list[SpecTask])
async def list_spec_tasks(
    spec_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """List tasks for a spec."""
    # Use async database operations (non-blocking)
    tasks = await _list_spec_tasks_async(db, spec_id)
    if tasks is None:
        raise HTTPException(status_code=404, detail="Spec not found")

    return [
        SpecTask(
            id=t.id,
            title=t.title,
            description=t.description,
            phase=t.phase,
            priority=t.priority,
            status=t.status,
            assigned_agent=t.assigned_agent,
            dependencies=t.dependencies or [],
            estimated_hours=t.estimated_hours,
            actual_hours=t.actual_hours,
        )
        for t in tasks
    ]


@router.patch("/{spec_id}/tasks/{task_id}", response_model=SpecTask)
async def update_task(
    spec_id: str,
    task_id: str,
    updates: TaskUpdate,
    db: DatabaseService = Depends(get_db_service),
):
    """Update a task."""
    # Use async database operations (non-blocking)
    task = await _update_task_async(
        db,
        spec_id,
        task_id,
        title=updates.title,
        description=updates.description,
        phase=updates.phase,
        priority=updates.priority,
        status=updates.status,
        assigned_agent=updates.assigned_agent,
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return SpecTask(
        id=task.id,
        title=task.title,
        description=task.description,
        phase=task.phase,
        priority=task.priority,
        status=task.status,
        assigned_agent=task.assigned_agent,
        dependencies=task.dependencies or [],
        estimated_hours=task.estimated_hours,
        actual_hours=task.actual_hours,
    )


@router.delete("/{spec_id}/tasks/{task_id}")
async def delete_task(
    spec_id: str,
    task_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Delete a task."""
    # Use async database operations (non-blocking)
    deleted = await _delete_task_async(db, spec_id, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}


# ============================================================================
# Approval Routes
# ============================================================================


@router.post("/{spec_id}/approve-requirements")
async def approve_requirements(
    spec_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Approve requirements and move to design phase."""
    # Use async database operations (non-blocking)
    approved = await _approve_requirements_async(db, spec_id)
    if not approved:
        raise HTTPException(status_code=404, detail="Spec not found")

    # Create version history entry for requirements approval
    await _create_spec_version_async(
        db,
        spec_id,
        change_type="requirements_approved",
        change_summary="Requirements approved, moved to Design phase",
    )

    return {"message": "Requirements approved, moved to Design phase"}


@router.post("/{spec_id}/approve-design")
async def approve_design(
    spec_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Approve design and move to execution phase."""
    # Use async database operations (non-blocking)
    approved = await _approve_design_async(db, spec_id)
    if not approved:
        raise HTTPException(status_code=404, detail="Spec not found")

    # Create version history entry for design approval
    await _create_spec_version_async(
        db,
        spec_id,
        change_type="design_approved",
        change_summary="Design approved, moved to Implementation phase",
    )

    return {"message": "Design approved, moved to Implementation phase"}


# ============================================================================
# Version History Routes
# ============================================================================


@router.get("/{spec_id}/versions", response_model=SpecVersionListResponse)
async def list_spec_versions(
    spec_id: str,
    limit: int = Query(20, ge=1, le=100, description="Maximum number of versions to return"),
    db: DatabaseService = Depends(get_db_service),
):
    """List version history for a spec."""
    versions = await _list_spec_versions_async(db, spec_id, limit)

    return SpecVersionListResponse(
        versions=[
            SpecVersionResponse(
                id=v.id,
                spec_id=v.spec_id,
                version_number=v.version_number,
                change_type=v.change_type,
                change_summary=v.change_summary,
                change_details=v.change_details,
                created_by=v.created_by,
                snapshot=v.snapshot,
                created_at=v.created_at,
            )
            for v in versions
        ],
        total=len(versions),
    )


# ============================================================================
# Execution Routes
# ============================================================================


@router.post("/{spec_id}/execute", response_model=SpecExecuteResponse)
async def execute_spec(
    spec_id: str,
    request: SpecExecuteRequest = SpecExecuteRequest(),
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    _: str = Depends(verify_spec_access),  # Verify access to spec
):
    """
    Execute the spec-driven development workflow via Daytona sandbox.

    This spawns a Daytona sandbox that runs the state machine which
    orchestrates the multi-phase spec generation workflow:
    EXPLORE -> REQUIREMENTS -> DESIGN -> TASKS -> SYNC -> COMPLETE

    Each phase:
    - Runs inside an isolated Daytona sandbox
    - Has access to codebase tools (Glob, Read, Grep)
    - Saves to database before proceeding
    - Can be resumed from any checkpoint
    - Has validation gates with retry

    The sandbox runs asynchronously and updates the spec's phase_data
    and current_phase as it progresses.

    Args:
        spec_id: ID of the spec to execute.
        request: Execution configuration options.

    Returns:
        SpecExecuteResponse with execution status.
    """
    from omoi_os.services.daytona_spawner import DaytonaSpawnerService
    from omoi_os.services.event_bus import get_event_bus

    # Verify spec exists
    spec = await _get_spec_async(db, spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

    # BILLING GATE: Check if organization can execute workflows
    can_execute, billing_reason = await _check_billing_for_spec_execution(db, spec_id)
    if not can_execute:
        raise HTTPException(
            status_code=402,  # Payment Required
            detail=f"Execution blocked: {billing_reason}",
        )

    # Check if spec is already executing
    if spec.status == "executing":
        return SpecExecuteResponse(
            spec_id=spec_id,
            status="already_running",
            message="Spec execution is already in progress",
            current_phase=spec.current_phase,
        )

    # Update spec status to executing
    await _update_spec_async(db, spec_id, status="executing")

    # Create version history entry for execution start
    await _create_spec_version_async(
        db,
        spec_id,
        change_type="phase_changed",
        change_summary="Spec execution started",
        change_details={"action": "execute", "phase": spec.current_phase or "explore"},
    )

    # Get the current phase to resume from
    current_phase = spec.current_phase or "explore"

    # Get accumulated phase data for context
    phase_context = spec.phase_data or {}

    # Get any saved transcript for session resumption
    resume_transcript = None
    if spec.session_transcripts:
        resume_transcript = spec.session_transcripts.get(current_phase)

    try:
        # Initialize event bus (optional)
        event_bus = None
        try:
            event_bus = get_event_bus()
        except Exception:
            pass

        # Spawn Daytona sandbox for the spec phase execution
        spawner = DaytonaSpawnerService(db=db, event_bus=event_bus)
        sandbox_id = await spawner.spawn_for_phase(
            spec_id=spec_id,
            phase=current_phase,
            project_id=spec.project_id,
            phase_context=phase_context,
            resume_transcript=resume_transcript,
            extra_env={
                "ENABLE_EMBEDDINGS": "1" if request.enable_embeddings else "0",
            },
        )

        logger.info(
            f"Spawned sandbox {sandbox_id} for spec {spec_id} phase {current_phase}"
        )

        return SpecExecuteResponse(
            spec_id=spec_id,
            status="started",
            message=f"Spec execution started in sandbox {sandbox_id}",
            current_phase=current_phase,
        )

    except Exception as e:
        # Revert status on spawn failure
        await _update_spec_async(db, spec_id, status="failed")
        logger.error(f"Failed to spawn sandbox for spec {spec_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start execution: {e}",
        )


@router.get("/{spec_id}/phase-data", response_model=SpecPhaseDataResponse)
async def get_spec_phase_data(
    spec_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get the current phase data for a spec.

    This returns the accumulated outputs from each phase of the
    spec-driven development workflow, including:
    - explore: Codebase exploration results
    - requirements: Generated EARS-format requirements
    - design: Technical design artifacts
    - tasks: Implementation task breakdown
    - sync: Sync status and statistics

    Also includes phase_attempts (retry counts per phase) and
    any errors that occurred during execution.
    """
    async with db.get_async_session() as session:
        result = await session.execute(
            select(SpecModel).filter(SpecModel.id == spec_id)
        )
        spec = result.scalar_one_or_none()

        if not spec:
            raise HTTPException(status_code=404, detail="Spec not found")

        return SpecPhaseDataResponse(
            spec_id=spec.id,
            current_phase=spec.current_phase or "explore",
            phase_data=spec.phase_data or {},
            phase_attempts=spec.phase_attempts or {},
            last_checkpoint_at=spec.last_checkpoint_at,
            last_error=spec.last_error,
        )


@router.post("/{spec_id}/sync", response_model=SpecSyncStatsResponse)
async def sync_spec_data(
    spec_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """
    Manually trigger sync of phase data to database.

    This endpoint allows manually syncing the requirements, tasks,
    and acceptance criteria from phase_data to the database with
    deduplication. This is useful when:

    1. The automatic SYNC phase was skipped or failed
    2. Phase data was modified and needs to be re-synced
    3. Testing the sync functionality independently

    The sync service uses deduplication to prevent duplicate entities:
    - Hash-based: Fast exact-match check using SHA256 of normalized content
    - Semantic: Embedding similarity check via pgvector cosine distance

    Returns sync statistics including counts of created/skipped entities.
    """
    from omoi_os.services.embedding import get_embedding_service
    from omoi_os.services.spec_sync import get_spec_sync_service

    # Initialize embedding service (optional - graceful fallback if unavailable)
    embedding_service = None
    try:
        embedding_service = get_embedding_service()
    except Exception:
        pass  # Hash-only deduplication will be used

    # Initialize sync service
    sync_service = get_spec_sync_service(
        db=db,
        embedding_service=embedding_service,
    )

    # Execute sync
    sync_result = await sync_service.sync_spec(spec_id=spec_id)

    if not sync_result.success:
        raise HTTPException(
            status_code=400,
            detail=f"Sync failed: {sync_result.message}",
        )

    return SpecSyncStatsResponse(
        requirements_created=sync_result.stats.requirements_created,
        requirements_skipped=sync_result.stats.requirements_skipped,
        criteria_created=sync_result.stats.criteria_created,
        criteria_skipped=sync_result.stats.criteria_skipped,
        tasks_created=sync_result.stats.tasks_created,
        tasks_skipped=sync_result.stats.tasks_skipped,
        errors=sync_result.stats.errors,
    )


# ============================================================================
# Task Execution Routes
# ============================================================================


class ExecuteTasksRequest(BaseModel):
    """Request to execute spec tasks via sandbox system."""

    task_ids: Optional[List[str]] = Field(
        None,
        description="Optional list of specific SpecTask IDs to execute. "
        "If not provided, all pending tasks will be executed.",
    )


class ExecuteTasksResponse(BaseModel):
    """Response from task execution initiation."""

    success: bool
    message: str
    tasks_created: int = 0
    tasks_skipped: int = 0
    ticket_id: Optional[str] = None
    errors: List[str] = []


class TaskExecutionStatusResponse(BaseModel):
    """Response for task execution status."""

    spec_id: str
    total_tasks: int
    status_counts: Dict[str, int]
    progress: float
    is_complete: bool


class CriterionStatus(BaseModel):
    """Status of an individual acceptance criterion."""

    id: str
    text: str
    completed: bool


class RequirementCriteriaStatus(BaseModel):
    """Criteria status for a single requirement."""

    requirement_title: str
    total: int
    completed: int
    criteria: List[CriterionStatus]


class CriteriaStatusResponse(BaseModel):
    """Response for acceptance criteria status."""

    spec_id: str
    total_criteria: int
    completed_criteria: int
    completion_percentage: float
    all_complete: bool
    by_requirement: Dict[str, RequirementCriteriaStatus]


@router.post("/{spec_id}/execute-tasks", response_model=ExecuteTasksResponse)
async def execute_spec_tasks(
    spec_id: str,
    request: ExecuteTasksRequest = ExecuteTasksRequest(),
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    _: str = Depends(verify_spec_access),  # Verify access to spec
):
    """
    Execute SpecTasks via the sandbox system.

    This endpoint converts SpecTasks to executable Tasks and enqueues them
    for execution via Daytona sandboxes. The spec must have design_approved=True
    before tasks can be executed.

    Flow:
    1. Creates/finds a bridging Ticket for the Spec
    2. Converts pending SpecTasks to Tasks linked to that Ticket
    3. TaskQueueService and OrchestratorWorker pick up and execute via Daytona
    4. Task completion events update SpecTask status automatically

    Args:
        spec_id: ID of the spec whose tasks to execute
        request: Optional specific task IDs to execute (executes all pending if omitted)

    Returns:
        ExecuteTasksResponse with creation stats and ticket ID
    """
    from omoi_os.services.spec_task_execution import SpecTaskExecutionService
    from omoi_os.services.event_bus import get_event_bus

    # BILLING GATE: Check if organization can execute workflows
    can_execute, billing_reason = await _check_billing_for_spec_execution(db, spec_id)
    if not can_execute:
        raise HTTPException(
            status_code=402,  # Payment Required
            detail=f"Task execution blocked: {billing_reason}",
        )

    # Initialize service with event bus for completion tracking
    event_bus = None
    try:
        event_bus = get_event_bus()
    except Exception:
        pass  # Event bus optional

    service = SpecTaskExecutionService(db=db, event_bus=event_bus)

    # Subscribe to completions if event bus available
    if event_bus:
        service.subscribe_to_completions()

    # Execute tasks
    result = await service.execute_spec_tasks(
        spec_id=spec_id,
        task_ids=request.task_ids,
    )

    if not result.success:
        raise HTTPException(
            status_code=400,
            detail=result.message,
        )

    return ExecuteTasksResponse(
        success=result.success,
        message=result.message,
        tasks_created=result.stats.tasks_created,
        tasks_skipped=result.stats.tasks_skipped,
        ticket_id=result.stats.ticket_id,
        errors=result.stats.errors,
    )


@router.get("/{spec_id}/execution-status", response_model=TaskExecutionStatusResponse)
async def get_execution_status(
    spec_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get execution status for a spec's tasks.

    Returns task counts by status (pending, in_progress, completed, blocked)
    and overall progress percentage.

    Args:
        spec_id: ID of the spec to get status for

    Returns:
        TaskExecutionStatusResponse with status counts and progress
    """
    from omoi_os.services.spec_task_execution import SpecTaskExecutionService

    service = SpecTaskExecutionService(db=db)
    status = await service.get_execution_status(spec_id)

    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])

    return TaskExecutionStatusResponse(
        spec_id=status["spec_id"],
        total_tasks=status["total_tasks"],
        status_counts=status["status_counts"],
        progress=status["progress"],
        is_complete=status["is_complete"],
    )


@router.get("/{spec_id}/criteria-status", response_model=CriteriaStatusResponse)
async def get_criteria_status(
    spec_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """
    Get acceptance criteria status for a spec.

    Returns completion status for all criteria organized by requirement,
    including total counts and completion percentage.

    Args:
        spec_id: ID of the spec to get criteria status for

    Returns:
        CriteriaStatusResponse with criteria completion details
    """
    from omoi_os.services.spec_acceptance_validator import get_spec_acceptance_validator

    validator = get_spec_acceptance_validator(db=db)
    status = await validator.get_spec_criteria_status(spec_id)

    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])

    # Convert by_requirement dict to use RequirementCriteriaStatus model
    by_requirement = {}
    for req_id, req_data in status.get("by_requirement", {}).items():
        by_requirement[req_id] = RequirementCriteriaStatus(
            requirement_title=req_data["requirement_title"],
            total=req_data["total"],
            completed=req_data["completed"],
            criteria=[
                CriterionStatus(
                    id=c["id"],
                    text=c["text"],
                    completed=c["completed"],
                )
                for c in req_data["criteria"]
            ],
        )

    return CriteriaStatusResponse(
        spec_id=status["spec_id"],
        total_criteria=status["total_criteria"],
        completed_criteria=status["completed_criteria"],
        completion_percentage=status["completion_percentage"],
        all_complete=status["all_complete"],
        by_requirement=by_requirement,
    )


# ============================================================================
# Spec Events Endpoint (Phase 3: Event Reporting)
# ============================================================================


class SpecEventItem(BaseModel):
    """Individual sandbox event for a spec."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    sandbox_id: str
    spec_id: Optional[str] = None
    event_type: str
    event_data: dict
    source: str
    created_at: datetime


class SpecEventsResponse(BaseModel):
    """Response for spec events query."""

    spec_id: str
    events: List[SpecEventItem]
    total_count: int
    has_more: bool


@router.get("/{spec_id}/events", response_model=SpecEventsResponse)
async def get_spec_events(
    spec_id: str,
    limit: int = Query(default=100, le=500, ge=1, description="Max events to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    event_type: Optional[str] = Query(default=None, description="Filter by event type"),
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    _: str = Depends(verify_spec_access),
):
    """
    Get sandbox events for a spec.

    Returns events from all sandboxes associated with this spec,
    ordered by creation time (newest first). Useful for monitoring
    spec-driven development progress.

    Args:
        spec_id: ID of the spec to get events for
        limit: Maximum number of events to return (default: 100, max: 500)
        offset: Pagination offset (default: 0)
        event_type: Optional filter by event type (e.g., 'agent.tool_use')

    Returns:
        SpecEventsResponse with events and pagination info
    """
    from sqlalchemy import func

    from omoi_os.models.sandbox_event import SandboxEvent

    async with db.get_async_session() as session:
        # Build base filter for this spec
        base_filter = SandboxEvent.spec_id == spec_id
        if event_type:
            base_filter = base_filter & (SandboxEvent.event_type == event_type)

        # Get total count
        count_result = await session.execute(
            select(func.count(SandboxEvent.id)).filter(base_filter)
        )
        total_count = count_result.scalar() or 0

        # Get paginated results, ordered by created_at desc (newest first)
        result = await session.execute(
            select(SandboxEvent)
            .filter(base_filter)
            .order_by(SandboxEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        events = result.scalars().all()

        return SpecEventsResponse(
            spec_id=spec_id,
            events=[
                SpecEventItem(
                    id=str(e.id),
                    sandbox_id=e.sandbox_id,
                    spec_id=e.spec_id,
                    event_type=e.event_type,
                    event_data=e.event_data or {},
                    source=e.source,
                    created_at=e.created_at,
                )
                for e in events
            ],
            total_count=total_count,
            has_more=offset + len(events) < total_count,
        )


# ============================================================================
# PR Creation Endpoints (GitHub Integration)
# ============================================================================


class SpecCreatePRRequest(BaseModel):
    """Request to create a PR for a spec."""

    force: bool = Field(default=False, description="Create PR even if tasks incomplete")


class SpecCreatePRResponse(BaseModel):
    """Response from PR creation."""

    spec_id: str
    success: bool
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    branch_name: Optional[str] = None
    error: Optional[str] = None
    already_exists: bool = False


@router.post("/{spec_id}/create-branch", response_model=SpecCreatePRResponse)
async def create_spec_branch(
    spec_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    _: str = Depends(verify_spec_access),
):
    """
    Create a git branch for a spec.

    This creates a feature branch for spec work. The branch name follows
    the format: spec/{spec_id_prefix}-{title_slug}

    Should be called when spec execution starts, but can also be called
    manually to prepare a branch ahead of time.

    Args:
        spec_id: ID of the spec

    Returns:
        SpecCreatePRResponse with branch_name if successful
    """
    from omoi_os.services.spec_completion_service import get_spec_completion_service
    from omoi_os.services.event_bus import get_event_bus

    event_bus = None
    try:
        event_bus = get_event_bus()
    except Exception:
        pass

    completion_service = get_spec_completion_service(db, event_bus)
    result = await completion_service.create_branch_for_spec(
        spec_id=spec_id,
        user_id=current_user.id,
    )

    if result.get("success"):
        return SpecCreatePRResponse(
            spec_id=spec_id,
            success=True,
            branch_name=result.get("branch_name"),
        )
    else:
        return SpecCreatePRResponse(
            spec_id=spec_id,
            success=False,
            error=result.get("error"),
        )


@router.post("/{spec_id}/create-pr", response_model=SpecCreatePRResponse)
async def create_spec_pr(
    spec_id: str,
    request: SpecCreatePRRequest = SpecCreatePRRequest(),
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
    _: str = Depends(verify_spec_access),
):
    """
    Create a pull request for a spec.

    This creates a PR from the spec's branch to the project's default branch.
    By default, requires all spec tasks to be completed. Use force=true to
    create PR even with incomplete tasks.

    The PR includes:
    - Title: feat: {spec.title}
    - Body: Spec description and completed tasks checklist
    - Branch: spec/{spec_id_prefix}-{title_slug}

    Args:
        spec_id: ID of the spec
        request: Optional request with force flag

    Returns:
        SpecCreatePRResponse with pr_number and pr_url if successful
    """
    from omoi_os.services.spec_completion_service import get_spec_completion_service
    from omoi_os.services.event_bus import get_event_bus

    event_bus = None
    try:
        event_bus = get_event_bus()
    except Exception:
        pass

    completion_service = get_spec_completion_service(db, event_bus)
    result = await completion_service.create_pr_for_spec(
        spec_id=spec_id,
        force=request.force,
    )

    if result.get("success"):
        return SpecCreatePRResponse(
            spec_id=spec_id,
            success=True,
            pr_number=result.get("pr_number"),
            pr_url=result.get("pr_url"),
            already_exists=result.get("already_exists", False),
        )
    else:
        return SpecCreatePRResponse(
            spec_id=spec_id,
            success=False,
            error=result.get("error"),
        )


# ============================================================================
# Spec Launch Endpoint (Phase 4: Command Page Integration)
# ============================================================================


class SpecLaunchRequest(BaseModel):
    """Request to launch a new spec (create and optionally execute)."""

    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    project_id: str
    auto_execute: bool = Field(default=True, description="Start execution immediately after creation")


class SpecLaunchResponse(BaseModel):
    """Response from spec launch."""

    spec_id: str
    status: str  # "created" or "executing"
    current_phase: Optional[str] = None
    sandbox_id: Optional[str] = None
    message: str


@router.post("/launch", response_model=SpecLaunchResponse)
async def launch_spec(
    request: SpecLaunchRequest,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Create a new spec and optionally start execution.

    This is the primary entry point for the command page's spec-driven mode.
    It combines spec creation with optional immediate execution, providing
    a streamlined workflow for users.

    Args:
        request: Launch request with title, description, project_id, and auto_execute flag

    Returns:
        SpecLaunchResponse with spec_id, status, and optional sandbox_id
    """
    # 0. Verify project access from request body
    await verify_project_access(request.project_id, current_user, db)

    # 1. Check billing
    billing = await get_billing_service()
    can_execute, billing_reason = await billing.can_execute_spec(current_user.id)
    if not can_execute and request.auto_execute:
        raise HTTPException(status_code=402, detail=f"Execution blocked: {billing_reason}")

    # 2. Create spec
    spec = await _create_spec_async(
        db=db,
        project_id=request.project_id,
        title=request.title,
        description=request.description,
        user_id=current_user.id,
    )

    # 3. If not auto-executing, return created spec
    if not request.auto_execute:
        return SpecLaunchResponse(
            spec_id=spec.id,
            status="created",
            current_phase=spec.current_phase,
            message="Spec created (not executing)",
        )

    # 4. Start execution in sandbox
    try:
        # Update status to executing
        await _update_spec_async(db, spec.id, status="executing")

        # Spawn sandbox
        from omoi_os.services.daytona_spawner import DaytonaSpawnerService
        from omoi_os.services.event_bus import get_event_bus

        event_bus = None
        try:
            event_bus = get_event_bus()
        except Exception:
            pass

        spawner = DaytonaSpawnerService(db=db, event_bus=event_bus)

        sandbox_id = await spawner.spawn_for_phase(
            spec_id=spec.id,
            phase=spec.current_phase or "explore",
            project_id=request.project_id,
            phase_context={
                "title": request.title,
                "description": request.description,
            },
        )

        return SpecLaunchResponse(
            spec_id=spec.id,
            status="executing",
            current_phase=spec.current_phase or "explore",
            sandbox_id=sandbox_id,
            message="Spec created and execution started",
        )

    except Exception as e:
        # Revert status on failure
        await _update_spec_async(db, spec.id, status="draft")
        logger.error(f"Failed to launch spec execution: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Spec created but execution failed to start: {str(e)}",
        )


