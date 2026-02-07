"""Guardian intervention API routes for emergency actions."""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from omoi_os.models.guardian_action import AuthorityLevel, GuardianAction
from omoi_os.services.guardian import GuardianService

router = APIRouter()


def serialize_guardian_action(action: GuardianAction) -> Dict:
    """Convert GuardianAction ORM object into API-friendly dict."""
    return {
        "action_id": action.id,
        "action_type": action.action_type,
        "target_entity": action.target_entity,
        "authority_level": action.authority_level,
        "authority_name": AuthorityLevel(action.authority_level).name,
        "reason": action.reason,
        "initiated_by": action.initiated_by,
        "approved_by": action.approved_by,
        "executed_at": action.executed_at.isoformat() if action.executed_at else None,
        "reverted_at": action.reverted_at.isoformat() if action.reverted_at else None,
        "audit_log": action.audit_log,
        "created_at": action.created_at.isoformat() if action.created_at else None,
    }


# Request/Response Models


class CancelTaskRequest(BaseModel):
    """Request to emergency cancel a task."""

    task_id: str = Field(..., description="ID of task to cancel")
    reason: str = Field(..., description="Explanation for emergency cancellation")
    initiated_by: str = Field(..., description="Agent/user ID initiating action")
    authority: int = Field(
        default=AuthorityLevel.GUARDIAN,
        ge=1,
        le=5,
        description="Authority level (4=GUARDIAN, 5=SYSTEM)",
    )


class ReallocateCapacityRequest(BaseModel):
    """Request to reallocate agent capacity."""

    from_agent_id: str = Field(..., description="Source agent ID")
    to_agent_id: str = Field(..., description="Target agent ID")
    capacity: int = Field(..., ge=1, description="Amount of capacity to transfer")
    reason: str = Field(..., description="Explanation for reallocation")
    initiated_by: str = Field(..., description="Agent/user ID initiating action")
    authority: int = Field(
        default=AuthorityLevel.GUARDIAN, ge=1, le=5, description="Authority level"
    )


class OverridePriorityRequest(BaseModel):
    """Request to override task priority."""

    task_id: str = Field(..., description="ID of task to boost")
    new_priority: str = Field(
        ..., description="New priority (CRITICAL, HIGH, MEDIUM, LOW)"
    )
    reason: str = Field(..., description="Explanation for priority override")
    initiated_by: str = Field(..., description="Agent/user ID initiating action")
    authority: int = Field(
        default=AuthorityLevel.GUARDIAN, ge=1, le=5, description="Authority level"
    )


class RevertInterventionRequest(BaseModel):
    """Request to revert a guardian intervention."""

    reason: str = Field(..., description="Explanation for reversion")
    initiated_by: str = Field(..., description="Agent/user ID initiating reversion")


class GuardianActionDTO(BaseModel):
    """Guardian action response model."""

    action_id: str
    action_type: str
    target_entity: str
    authority_level: int
    authority_name: str
    reason: str
    initiated_by: str
    approved_by: Optional[str]
    executed_at: Optional[str]
    reverted_at: Optional[str]
    audit_log: Optional[Dict]
    created_at: Optional[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "action_id": "uuid",
                "action_type": "cancel_task",
                "target_entity": "task-uuid",
                "authority_level": 4,
                "authority_name": "GUARDIAN",
                "reason": "Emergency: agent failure during critical task",
                "initiated_by": "guardian-agent-1",
                "approved_by": None,
                "executed_at": "2025-11-17T10:30:00Z",
                "reverted_at": None,
                "audit_log": {
                    "before": {"status": "running"},
                    "after": {"status": "failed"},
                },
                "created_at": "2025-11-17T10:30:00Z",
            }
        }
    )


# Dependency injection helper
def get_guardian_service() -> GuardianService:
    """Get guardian service instance."""
    from omoi_os.api.dependencies import get_db_service, get_event_bus

    db = get_db_service()
    event_bus = get_event_bus()
    return GuardianService(db=db, event_bus=event_bus)


# Routes


@router.post(
    "/intervention/cancel-task",
    response_model=GuardianActionDTO,
    status_code=200,
    summary="Emergency cancel a running task",
)
def cancel_task(
    request: CancelTaskRequest,
    guardian_service: GuardianService = Depends(get_guardian_service),
) -> GuardianActionDTO:
    """Emergency task cancellation.

    Requires GUARDIAN authority level (4) or higher.
    Used for critical failures where immediate intervention is needed.

    **Authority Levels:**
    - 1: WORKER
    - 2: WATCHDOG
    - 3: MONITOR
    - 4: GUARDIAN (required)
    - 5: SYSTEM
    """
    try:
        authority = AuthorityLevel(request.authority)
        action = guardian_service.emergency_cancel_task(
            task_id=request.task_id,
            reason=request.reason,
            initiated_by=request.initiated_by,
            authority=authority,
        )

        if not action:
            raise HTTPException(
                status_code=404, detail=f"Task {request.task_id} not found"
            )

        return GuardianActionDTO(**serialize_guardian_action(action))

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/intervention/reallocate",
    response_model=GuardianActionDTO,
    status_code=200,
    summary="Reallocate agent capacity",
)
def reallocate_capacity(
    request: ReallocateCapacityRequest,
    guardian_service: GuardianService = Depends(get_guardian_service),
) -> GuardianActionDTO:
    """Reallocate capacity from one agent to another.

    Requires GUARDIAN authority level (4) or higher.
    Typically used to steal resources from low-priority work for critical tasks.
    """
    try:
        authority = AuthorityLevel(request.authority)
        action = guardian_service.reallocate_agent_capacity(
            from_agent_id=request.from_agent_id,
            to_agent_id=request.to_agent_id,
            capacity=request.capacity,
            reason=request.reason,
            initiated_by=request.initiated_by,
            authority=authority,
        )

        if not action:
            raise HTTPException(
                status_code=404,
                detail=f"Agent(s) not found: {request.from_agent_id} or {request.to_agent_id}",
            )

        return GuardianActionDTO(**serialize_guardian_action(action))

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/intervention/override-priority",
    response_model=GuardianActionDTO,
    status_code=200,
    summary="Override task priority in queue",
)
def override_priority(
    request: OverridePriorityRequest,
    guardian_service: GuardianService = Depends(get_guardian_service),
) -> GuardianActionDTO:
    """Override task priority for emergency escalation.

    Requires GUARDIAN authority level (4) or higher.
    Used to boost critical tasks ahead of normal queue order.
    """
    try:
        authority = AuthorityLevel(request.authority)
        action = guardian_service.override_task_priority(
            task_id=request.task_id,
            new_priority=request.new_priority.upper(),
            reason=request.reason,
            initiated_by=request.initiated_by,
            authority=authority,
        )

        if not action:
            raise HTTPException(
                status_code=404, detail=f"Task {request.task_id} not found"
            )

        return GuardianActionDTO(**serialize_guardian_action(action))

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/actions",
    response_model=List[GuardianActionDTO],
    status_code=200,
    summary="Get guardian action audit trail",
)
def get_actions(
    limit: int = Query(
        default=100, ge=1, le=1000, description="Maximum actions to return"
    ),
    action_type: Optional[str] = Query(
        default=None, description="Filter by action type"
    ),
    target_entity: Optional[str] = Query(
        default=None, description="Filter by target entity"
    ),
    guardian_service: GuardianService = Depends(get_guardian_service),
) -> List[GuardianActionDTO]:
    """Get audit trail of all guardian interventions.

    Returns actions sorted by most recent first.
    """
    actions = guardian_service.get_actions(
        limit=limit,
        action_type=action_type,
        target_entity=target_entity,
    )

    return [
        GuardianActionDTO(**serialize_guardian_action(action)) for action in actions
    ]


@router.get(
    "/actions/{action_id}",
    response_model=GuardianActionDTO,
    status_code=200,
    summary="Get specific guardian action details",
)
def get_action(
    action_id: str,
    guardian_service: GuardianService = Depends(get_guardian_service),
) -> GuardianActionDTO:
    """Get detailed information about a specific guardian action."""
    action = guardian_service.get_action(action_id)

    if not action:
        raise HTTPException(status_code=404, detail=f"Action {action_id} not found")

    return GuardianActionDTO(**serialize_guardian_action(action))


@router.post(
    "/actions/{action_id}/revert",
    status_code=200,
    summary="Revert a guardian intervention",
)
def revert_intervention(
    action_id: str,
    request: RevertInterventionRequest,
    guardian_service: GuardianService = Depends(get_guardian_service),
) -> Dict:
    """Revert a previous guardian intervention.

    Marks the action as reverted and publishes revert event.
    Does not automatically restore previous state - that requires separate actions.
    """
    success = guardian_service.revert_intervention(
        action_id=action_id,
        reason=request.reason,
        initiated_by=request.initiated_by,
    )

    if not success:
        raise HTTPException(
            status_code=404, detail=f"Action {action_id} not found or already reverted"
        )

    return {
        "action_id": action_id,
        "reverted": True,
        "reason": request.reason,
        "reverted_by": request.initiated_by,
    }
