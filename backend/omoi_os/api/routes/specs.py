"""
Specification Management API Routes

Provides endpoints for managing project specifications including:
- Specs CRUD operations
- Requirements with acceptance criteria
- Design artifacts
- Linked tasks
"""

from datetime import datetime
from typing import Optional, List, Any, Dict

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from omoi_os.api.dependencies import get_db_service
from omoi_os.models.spec import (
    Spec as SpecModel,
    SpecRequirement as SpecRequirementModel,
    SpecAcceptanceCriterion as SpecCriterionModel,
    SpecTask as SpecTaskModel,
    SpecVersion as SpecVersionModel,
)
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now


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
) -> SpecModel:
    """Create a new spec (ASYNC - non-blocking)."""
    async with db.get_async_session() as session:
        new_spec = SpecModel(
            project_id=project_id,
            title=title,
            description=description,
            status="draft",
            phase="Requirements",
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
    db: DatabaseService = Depends(get_db_service),
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
    db: DatabaseService = Depends(get_db_service),
):
    """Create a new specification."""
    # Use async database operations (non-blocking)
    new_spec = await _create_spec_async(
        db, spec.project_id, spec.title, spec.description
    )

    # Create initial version history entry
    await _create_spec_version_async(
        db,
        new_spec.id,
        change_type="created",
        change_summary=f"Specification '{spec.title}' created",
    )

    return _spec_to_response(new_spec)


@router.get("/{spec_id}", response_model=SpecResponse)
async def get_spec(
    spec_id: str,
    db: DatabaseService = Depends(get_db_service),
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
    db: DatabaseService = Depends(get_db_service),
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
    db: DatabaseService = Depends(get_db_service),
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
    db: DatabaseService = Depends(get_db_service),
):
    """
    Execute the spec-driven development workflow.

    This starts the state machine which orchestrates the multi-phase
    spec generation workflow:
    EXPLORE -> REQUIREMENTS -> DESIGN -> TASKS -> SYNC -> COMPLETE

    Each phase:
    - Runs as a separate Agent SDK session
    - Has access to codebase tools (Glob, Read, Grep)
    - Saves to database before proceeding
    - Can be resumed from any checkpoint
    - Has validation gates with retry

    The workflow runs asynchronously and updates the spec's phase_data
    and current_phase as it progresses.

    Args:
        spec_id: ID of the spec to execute.
        request: Execution configuration options.

    Returns:
        SpecExecuteResponse with execution status.
    """
    import asyncio
    import os

    from omoi_os.workers.spec_state_machine import run_spec_state_machine

    # Verify spec exists
    spec = await _get_spec_async(db, spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")

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

    # Determine working directory
    working_dir = request.working_directory or os.getcwd()

    # Run the state machine asynchronously (fire and forget)
    # The state machine will update the database as it progresses
    async def run_execution():
        try:
            success = await run_spec_state_machine(
                spec_id=spec_id,
                working_directory=working_dir,
                enable_embeddings=request.enable_embeddings,
            )
            if not success:
                # Update spec status on failure
                await _update_spec_async(db, spec_id, status="failed")
        except Exception as e:
            # Update spec status on error
            await _update_spec_async(db, spec_id, status="failed")
            # Log the error (in production, use proper logging)
            import logging
            logging.getLogger(__name__).error(f"Spec execution failed: {e}")

    # Start the execution in the background
    asyncio.create_task(run_execution())

    return SpecExecuteResponse(
        spec_id=spec_id,
        status="started",
        message="Spec execution started successfully",
        current_phase=spec.current_phase or "explore",
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
    db: DatabaseService = Depends(get_db_service),
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
