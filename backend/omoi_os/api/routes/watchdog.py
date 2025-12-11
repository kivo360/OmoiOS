"""Watchdog remediation API routes per REQ-WATCHDOG-001."""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from omoi_os.models.watchdog_action import WatchdogAction
from omoi_os.services.watchdog import WatchdogService

router = APIRouter()


def get_watchdog_service() -> WatchdogService:
    """Get WatchdogService with dependencies."""
    from omoi_os.api.dependencies import (
        get_database_service,
        get_agent_registry_service,
        get_restart_orchestrator,
        get_guardian_service,
        get_event_bus_service,
        get_agent_status_manager,
    )
    
    try:
        db = get_database_service()
        agent_registry = get_agent_registry_service()
        restart_orchestrator = get_restart_orchestrator()
        guardian_service = get_guardian_service()
        event_bus = get_event_bus_service()
        status_manager = get_agent_status_manager()
        
        return WatchdogService(
            db=db,
            agent_registry=agent_registry,
            restart_orchestrator=restart_orchestrator,
            guardian_service=guardian_service,
            event_bus=event_bus,
            status_manager=status_manager,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to initialize WatchdogService: {e}") from e


def serialize_watchdog_action(action: WatchdogAction) -> Dict:
    """Convert WatchdogAction ORM object into API-friendly dict."""
    return {
        "action_id": action.id,
        "action_type": action.action_type,
        "target_agent_id": action.target_agent_id,
        "remediation_policy": action.remediation_policy,
        "reason": action.reason,
        "initiated_by": action.initiated_by,
        "executed_at": action.executed_at.isoformat() if action.executed_at else None,
        "success": action.success,
        "escalated_to_guardian": action.escalated_to_guardian == "true" if isinstance(action.escalated_to_guardian, str) else action.escalated_to_guardian,
        "guardian_action_id": action.guardian_action_id,
        "audit_log": action.audit_log,
        "created_at": action.created_at.isoformat() if action.created_at else None,
    }


# Request/Response Models

class ExecuteRemediationRequest(BaseModel):
    """Request to execute remediation action."""
    agent_id: str = Field(..., description="ID of monitor agent to remediate")
    policy_name: str = Field(..., description="Name of remediation policy to apply")
    reason: str = Field(..., description="Reason for remediation")
    watchdog_agent_id: str = Field(..., description="ID of watchdog agent executing action")


class WatchdogActionDTO(BaseModel):
    """Watchdog action response model."""
    action_id: str
    action_type: str
    target_agent_id: str
    remediation_policy: str
    reason: str
    initiated_by: str
    executed_at: Optional[str]
    success: str
    escalated_to_guardian: bool
    guardian_action_id: Optional[str]
    audit_log: Optional[Dict]
    created_at: Optional[str]

    model_config = ConfigDict(json_schema_extra={"example": {
        "action_id": "uuid",
        "action_type": "restart",
        "target_agent_id": "agent-uuid",
        "remediation_policy": "monitor_restart",
        "reason": "Monitor agent missed 3 consecutive heartbeats",
        "initiated_by": "watchdog-agent-001",
        "executed_at": "2025-01-30T12:00:00Z",
        "success": "success",
        "escalated_to_guardian": False,
        "guardian_action_id": None,
        "audit_log": {},
        "created_at": "2025-01-30T12:00:00Z",
    }})


class MonitorStatusResponse(BaseModel):
    """Response for monitor agent status check."""
    issues: List[Dict]
    total_monitors: int
    healthy_monitors: int
    unhealthy_monitors: int


# API Routes

@router.get("/monitor-status", response_model=MonitorStatusResponse)
def get_monitor_status(
    watchdog_service: WatchdogService = Depends(get_watchdog_service),
):
    """Get status of all monitor agents.
    
    Returns list of detected issues with monitor agents.
    """
    issues = watchdog_service.monitor_monitor_agents()
    
    # Count healthy vs unhealthy
    from omoi_os.services.database import get_database_service
    from omoi_os.models.agent import Agent
    from omoi_os.models.agent_status import AgentStatus
    
    db = get_database_service()
    with db.get_session() as session:
        all_monitors = (
            session.query(Agent)
            .filter(Agent.agent_type == "monitor")
            .all()
        )
        healthy = [
            m for m in all_monitors
            if m.status in [AgentStatus.IDLE.value, AgentStatus.RUNNING.value]
            and m.id not in [issue["agent_id"] for issue in issues]
        ]
    
    return MonitorStatusResponse(
        issues=issues,
        total_monitors=len(all_monitors),
        healthy_monitors=len(healthy),
        unhealthy_monitors=len(issues),
    )


@router.post("/execute-remediation", response_model=WatchdogActionDTO)
def execute_remediation(
    request: ExecuteRemediationRequest,
    watchdog_service: WatchdogService = Depends(get_watchdog_service),
):
    """Execute remediation action for a monitor agent.
    
    Applies the specified remediation policy to the target agent.
    """
    action = watchdog_service.execute_remediation(
        agent_id=request.agent_id,
        policy_name=request.policy_name,
        reason=request.reason,
        watchdog_agent_id=request.watchdog_agent_id,
    )
    
    if not action:
        raise HTTPException(
            status_code=404,
            detail=f"Policy '{request.policy_name}' not found or agent '{request.agent_id}' not found"
        )
    
    return WatchdogActionDTO(**serialize_watchdog_action(action))


@router.get("/remediation-history", response_model=List[WatchdogActionDTO])
def get_remediation_history(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of actions to return"),
    watchdog_service: WatchdogService = Depends(get_watchdog_service),
):
    """Get remediation action history.
    
    Returns list of past remediation actions, optionally filtered by agent.
    """
    actions = watchdog_service.get_remediation_history(agent_id=agent_id, limit=limit)
    return [WatchdogActionDTO(**serialize_watchdog_action(action)) for action in actions]


@router.get("/policies", response_model=Dict[str, Dict])
def get_policies(
    watchdog_service: WatchdogService = Depends(get_watchdog_service),
):
    """Get all loaded remediation policies.
    
    Returns dictionary of policy name to policy configuration.
    """
    return watchdog_service.get_policies()

