"""
Specification Management API Routes

Provides endpoints for managing project specifications including:
- Specs CRUD operations
- Requirements with acceptance criteria
- Design artifacts
- Linked tasks
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from omoi_os.api.dependencies import get_db_service
from omoi_os.models.spec import (
    Spec as SpecModel,
    SpecRequirement as SpecRequirementModel,
    SpecAcceptanceCriterion as SpecCriterionModel,
    SpecTask as SpecTaskModel,
)
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now


router = APIRouter(prefix="/specs", tags=["specs"])


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


class RequirementUpdate(BaseModel):
    title: Optional[str] = None
    condition: Optional[str] = None
    action: Optional[str] = None
    status: Optional[str] = None


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
    with db.get_session() as session:
        query = session.query(SpecModel).filter(SpecModel.project_id == project_id)

        if status:
            query = query.filter(SpecModel.status == status)

        specs = query.order_by(SpecModel.created_at.desc()).all()

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
    with db.get_session() as session:
        new_spec = SpecModel(
            project_id=spec.project_id,
            title=spec.title,
            description=spec.description,
            status="draft",
            phase="Requirements",
        )

        session.add(new_spec)
        session.commit()
        session.refresh(new_spec)

        return _spec_to_response(new_spec)


@router.get("/{spec_id}", response_model=SpecResponse)
async def get_spec(
    spec_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Get a spec by ID."""
    with db.get_session() as session:
        spec = session.query(SpecModel).filter(SpecModel.id == spec_id).first()

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
    with db.get_session() as session:
        spec = session.query(SpecModel).filter(SpecModel.id == spec_id).first()

        if not spec:
            raise HTTPException(status_code=404, detail="Spec not found")

        if updates.title is not None:
            spec.title = updates.title
        if updates.description is not None:
            spec.description = updates.description
        if updates.status is not None:
            spec.status = updates.status
        if updates.phase is not None:
            spec.phase = updates.phase

        session.commit()
        session.refresh(spec)

        return _spec_to_response(spec)


@router.delete("/{spec_id}")
async def delete_spec(
    spec_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Delete a spec."""
    with db.get_session() as session:
        spec = session.query(SpecModel).filter(SpecModel.id == spec_id).first()

        if not spec:
            raise HTTPException(status_code=404, detail="Spec not found")

        session.delete(spec)
        session.commit()

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
    with db.get_session() as session:
        spec = session.query(SpecModel).filter(SpecModel.id == spec_id).first()

        if not spec:
            raise HTTPException(status_code=404, detail="Spec not found")

        new_req = SpecRequirementModel(
            spec_id=spec_id,
            title=req.title,
            condition=req.condition,
            action=req.action,
            status="pending",
        )

        session.add(new_req)
        session.commit()
        session.refresh(new_req)

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
    with db.get_session() as session:
        req = (
            session.query(SpecRequirementModel)
            .filter(
                SpecRequirementModel.id == req_id,
                SpecRequirementModel.spec_id == spec_id,
            )
            .first()
        )

        if not req:
            raise HTTPException(status_code=404, detail="Requirement not found")

        if updates.title is not None:
            req.title = updates.title
        if updates.condition is not None:
            req.condition = updates.condition
        if updates.action is not None:
            req.action = updates.action
        if updates.status is not None:
            req.status = updates.status

        session.commit()
        session.refresh(req)

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
    with db.get_session() as session:
        req = (
            session.query(SpecRequirementModel)
            .filter(
                SpecRequirementModel.id == req_id,
                SpecRequirementModel.spec_id == spec_id,
            )
            .first()
        )

        if not req:
            raise HTTPException(status_code=404, detail="Requirement not found")

        session.delete(req)
        session.commit()

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
    with db.get_session() as session:
        req = (
            session.query(SpecRequirementModel)
            .filter(
                SpecRequirementModel.id == req_id,
                SpecRequirementModel.spec_id == spec_id,
            )
            .first()
        )

        if not req:
            raise HTTPException(status_code=404, detail="Requirement not found")

        new_criterion = SpecCriterionModel(
            requirement_id=req_id,
            text=criterion.text,
            completed=False,
        )

        session.add(new_criterion)
        session.commit()
        session.refresh(new_criterion)

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
    with db.get_session() as session:
        criterion = (
            session.query(SpecCriterionModel)
            .filter(
                SpecCriterionModel.id == criterion_id,
                SpecCriterionModel.requirement_id == req_id,
            )
            .first()
        )

        if not criterion:
            raise HTTPException(status_code=404, detail="Criterion not found")

        if updates.text is not None:
            criterion.text = updates.text
        if updates.completed is not None:
            criterion.completed = updates.completed

        session.commit()
        session.refresh(criterion)

        return AcceptanceCriterion(
            id=criterion.id,
            text=criterion.text,
            completed=criterion.completed,
        )


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
    with db.get_session() as session:
        spec = session.query(SpecModel).filter(SpecModel.id == spec_id).first()

        if not spec:
            raise HTTPException(status_code=404, detail="Spec not found")

        spec.design = design.model_dump()
        session.commit()

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
    with db.get_session() as session:
        spec = session.query(SpecModel).filter(SpecModel.id == spec_id).first()

        if not spec:
            raise HTTPException(status_code=404, detail="Spec not found")

        new_task = SpecTaskModel(
            spec_id=spec_id,
            title=task.title,
            description=task.description,
            phase=task.phase,
            priority=task.priority,
            status="pending",
        )

        session.add(new_task)
        session.commit()
        session.refresh(new_task)

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
    with db.get_session() as session:
        spec = session.query(SpecModel).filter(SpecModel.id == spec_id).first()

        if not spec:
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
            for t in spec.tasks
        ]


# ============================================================================
# Approval Routes
# ============================================================================


@router.post("/{spec_id}/approve-requirements")
async def approve_requirements(
    spec_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Approve requirements and move to design phase."""
    with db.get_session() as session:
        spec = session.query(SpecModel).filter(SpecModel.id == spec_id).first()

        if not spec:
            raise HTTPException(status_code=404, detail="Spec not found")

        spec.requirements_approved = True
        spec.requirements_approved_at = utc_now()
        spec.status = "design"
        spec.phase = "Design"

        session.commit()

        return {"message": "Requirements approved, moved to Design phase"}


@router.post("/{spec_id}/approve-design")
async def approve_design(
    spec_id: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Approve design and move to execution phase."""
    with db.get_session() as session:
        spec = session.query(SpecModel).filter(SpecModel.id == spec_id).first()

        if not spec:
            raise HTTPException(status_code=404, detail="Spec not found")

        spec.design_approved = True
        spec.design_approved_at = utc_now()
        spec.status = "executing"
        spec.phase = "Implementation"

        session.commit()

        return {"message": "Design approved, moved to Implementation phase"}
