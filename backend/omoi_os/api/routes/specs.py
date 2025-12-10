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
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from omoi_os.api.dependencies import get_db_service


router = APIRouter(prefix="/specs", tags=["specs"])


# ============================================================================
# Pydantic Models
# ============================================================================


class AcceptanceCriterion(BaseModel):
    id: str
    text: str
    completed: bool = False


class Requirement(BaseModel):
    id: str
    title: str
    condition: str  # EARS "WHEN" clause
    action: str  # EARS "THE SYSTEM SHALL" clause
    criteria: list[AcceptanceCriterion] = []
    linked_design: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed


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
    description: str
    phase: str
    priority: str
    status: str = "pending"
    assigned_agent: Optional[str] = None
    dependencies: list[str] = []
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None


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

    class Config:
        from_attributes = True


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


# ============================================================================
# In-Memory Storage (replace with database models later)
# ============================================================================

_specs_store: dict[str, dict] = {}


def _get_spec_response(spec_data: dict) -> SpecResponse:
    """Convert stored spec data to response model."""
    return SpecResponse(
        id=spec_data["id"],
        project_id=spec_data["project_id"],
        title=spec_data["title"],
        description=spec_data.get("description"),
        status=spec_data.get("status", "draft"),
        phase=spec_data.get("phase", "Requirements"),
        progress=spec_data.get("progress", 0),
        test_coverage=spec_data.get("test_coverage", 0),
        active_agents=spec_data.get("active_agents", 0),
        linked_tickets=spec_data.get("linked_tickets", 0),
        requirements=spec_data.get("requirements", []),
        design=spec_data.get("design"),
        tasks=spec_data.get("tasks", []),
        execution=spec_data.get("execution"),
        created_at=spec_data["created_at"],
        updated_at=spec_data["updated_at"],
    )


# ============================================================================
# API Routes
# ============================================================================


@router.get("/project/{project_id}", response_model=SpecListResponse)
async def list_project_specs(
    project_id: str,
    status: Optional[str] = None,
    db=Depends(get_db_service),
):
    """List all specs for a project."""
    specs = [
        _get_spec_response(s)
        for s in _specs_store.values()
        if s["project_id"] == project_id
        and (status is None or s.get("status") == status)
    ]
    return SpecListResponse(specs=specs, total=len(specs))


@router.post("", response_model=SpecResponse)
async def create_spec(
    spec: SpecCreate,
    db=Depends(get_db_service),
):
    """Create a new specification."""
    now = datetime.utcnow()
    spec_id = f"spec-{uuid4().hex[:8]}"

    spec_data = {
        "id": spec_id,
        "project_id": spec.project_id,
        "title": spec.title,
        "description": spec.description,
        "status": "draft",
        "phase": "Requirements",
        "progress": 0,
        "test_coverage": 0,
        "active_agents": 0,
        "linked_tickets": 0,
        "requirements": [],
        "design": None,
        "tasks": [],
        "execution": None,
        "created_at": now,
        "updated_at": now,
    }

    _specs_store[spec_id] = spec_data
    return _get_spec_response(spec_data)


@router.get("/{spec_id}", response_model=SpecResponse)
async def get_spec(
    spec_id: str,
    db=Depends(get_db_service),
):
    """Get a spec by ID."""
    if spec_id not in _specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    return _get_spec_response(_specs_store[spec_id])


@router.patch("/{spec_id}", response_model=SpecResponse)
async def update_spec(
    spec_id: str,
    updates: SpecUpdate,
    db=Depends(get_db_service),
):
    """Update a spec."""
    if spec_id not in _specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    spec_data = _specs_store[spec_id]

    if updates.title is not None:
        spec_data["title"] = updates.title
    if updates.description is not None:
        spec_data["description"] = updates.description
    if updates.status is not None:
        spec_data["status"] = updates.status
    if updates.phase is not None:
        spec_data["phase"] = updates.phase

    spec_data["updated_at"] = datetime.utcnow()

    return _get_spec_response(spec_data)


@router.delete("/{spec_id}")
async def delete_spec(
    spec_id: str,
    db=Depends(get_db_service),
):
    """Delete a spec."""
    if spec_id not in _specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    del _specs_store[spec_id]
    return {"message": "Spec deleted successfully"}


# ============================================================================
# Requirements Routes
# ============================================================================


@router.post("/{spec_id}/requirements", response_model=Requirement)
async def add_requirement(
    spec_id: str,
    req: RequirementCreate,
    db=Depends(get_db_service),
):
    """Add a requirement to a spec."""
    if spec_id not in _specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    spec_data = _specs_store[spec_id]
    req_id = f"REQ-{str(len(spec_data['requirements']) + 1).zfill(3)}"

    new_req = Requirement(
        id=req_id,
        title=req.title,
        condition=req.condition,
        action=req.action,
        criteria=[],
        linked_design=None,
        status="pending",
    )

    spec_data["requirements"].append(new_req.model_dump())
    spec_data["updated_at"] = datetime.utcnow()

    return new_req


@router.patch("/{spec_id}/requirements/{req_id}", response_model=Requirement)
async def update_requirement(
    spec_id: str,
    req_id: str,
    updates: RequirementUpdate,
    db=Depends(get_db_service),
):
    """Update a requirement."""
    if spec_id not in _specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    spec_data = _specs_store[spec_id]

    for req in spec_data["requirements"]:
        if req["id"] == req_id:
            if updates.title is not None:
                req["title"] = updates.title
            if updates.condition is not None:
                req["condition"] = updates.condition
            if updates.action is not None:
                req["action"] = updates.action
            if updates.status is not None:
                req["status"] = updates.status

            spec_data["updated_at"] = datetime.utcnow()
            return Requirement(**req)

    raise HTTPException(status_code=404, detail="Requirement not found")


@router.delete("/{spec_id}/requirements/{req_id}")
async def delete_requirement(
    spec_id: str,
    req_id: str,
    db=Depends(get_db_service),
):
    """Delete a requirement."""
    if spec_id not in _specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    spec_data = _specs_store[spec_id]
    spec_data["requirements"] = [
        r for r in spec_data["requirements"] if r["id"] != req_id
    ]
    spec_data["updated_at"] = datetime.utcnow()

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
    db=Depends(get_db_service),
):
    """Add an acceptance criterion to a requirement."""
    if spec_id not in _specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    spec_data = _specs_store[spec_id]

    for req in spec_data["requirements"]:
        if req["id"] == req_id:
            criteria_count = len(req.get("criteria", []))
            criterion_id = f"AC-{str(criteria_count + 1).zfill(3)}"

            new_criterion = AcceptanceCriterion(
                id=criterion_id,
                text=criterion.text,
                completed=False,
            )

            if "criteria" not in req:
                req["criteria"] = []
            req["criteria"].append(new_criterion.model_dump())

            spec_data["updated_at"] = datetime.utcnow()
            return new_criterion

    raise HTTPException(status_code=404, detail="Requirement not found")


@router.patch("/{spec_id}/requirements/{req_id}/criteria/{criterion_id}")
async def update_criterion(
    spec_id: str,
    req_id: str,
    criterion_id: str,
    updates: CriterionUpdate,
    db=Depends(get_db_service),
):
    """Update an acceptance criterion."""
    if spec_id not in _specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    spec_data = _specs_store[spec_id]

    for req in spec_data["requirements"]:
        if req["id"] == req_id:
            for criterion in req.get("criteria", []):
                if criterion["id"] == criterion_id:
                    if updates.text is not None:
                        criterion["text"] = updates.text
                    if updates.completed is not None:
                        criterion["completed"] = updates.completed

                    spec_data["updated_at"] = datetime.utcnow()
                    return AcceptanceCriterion(**criterion)

    raise HTTPException(status_code=404, detail="Criterion not found")


# ============================================================================
# Design Routes
# ============================================================================


@router.put("/{spec_id}/design", response_model=DesignArtifact)
async def update_design(
    spec_id: str,
    design: DesignArtifact,
    db=Depends(get_db_service),
):
    """Update the design for a spec."""
    if spec_id not in _specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    spec_data = _specs_store[spec_id]
    spec_data["design"] = design.model_dump()
    spec_data["updated_at"] = datetime.utcnow()

    return design


# ============================================================================
# Tasks Routes
# ============================================================================


@router.post("/{spec_id}/tasks", response_model=SpecTask)
async def add_task(
    spec_id: str,
    task_title: str,
    task_description: str,
    task_phase: str = "IMPLEMENTATION",
    task_priority: str = "MEDIUM",
    db=Depends(get_db_service),
):
    """Add a task to a spec."""
    if spec_id not in _specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    spec_data = _specs_store[spec_id]
    task_count = len(spec_data.get("tasks", []))
    task_id = f"TASK-{str(task_count + 1).zfill(3)}"

    new_task = SpecTask(
        id=task_id,
        title=task_title,
        description=task_description,
        phase=task_phase,
        priority=task_priority,
        status="pending",
        dependencies=[],
    )

    if "tasks" not in spec_data:
        spec_data["tasks"] = []
    spec_data["tasks"].append(new_task.model_dump())
    spec_data["updated_at"] = datetime.utcnow()

    return new_task


@router.get("/{spec_id}/tasks", response_model=list[SpecTask])
async def list_spec_tasks(
    spec_id: str,
    db=Depends(get_db_service),
):
    """List tasks for a spec."""
    if spec_id not in _specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    spec_data = _specs_store[spec_id]
    return [SpecTask(**t) for t in spec_data.get("tasks", [])]


# ============================================================================
# Approval Routes
# ============================================================================


@router.post("/{spec_id}/approve-requirements")
async def approve_requirements(
    spec_id: str,
    db=Depends(get_db_service),
):
    """Approve requirements and move to design phase."""
    if spec_id not in _specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    spec_data = _specs_store[spec_id]
    spec_data["status"] = "design"
    spec_data["phase"] = "Design"
    spec_data["updated_at"] = datetime.utcnow()

    return {"message": "Requirements approved, moved to Design phase"}


@router.post("/{spec_id}/approve-design")
async def approve_design(
    spec_id: str,
    db=Depends(get_db_service),
):
    """Approve design and move to execution phase."""
    if spec_id not in _specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    spec_data = _specs_store[spec_id]
    spec_data["status"] = "executing"
    spec_data["phase"] = "Implementation"
    spec_data["updated_at"] = datetime.utcnow()

    return {"message": "Design approved, moved to Implementation phase"}
