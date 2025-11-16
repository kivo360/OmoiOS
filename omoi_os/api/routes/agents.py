"""Agent health and monitoring API routes."""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from omoi_os.api.dependencies import (
    get_agent_health_service,
    get_agent_registry_service,
    get_db_service,
)
from omoi_os.models.agent import Agent
from omoi_os.services.agent_health import AgentHealthService
from omoi_os.services.agent_registry import AgentRegistryService
from omoi_os.services.database import DatabaseService

router = APIRouter()


def serialize_agent(agent: Agent) -> Dict:
    """Convert Agent ORM object into API-friendly dict."""
    return {
        "agent_id": agent.id,
        "agent_type": agent.agent_type,
        "phase_id": agent.phase_id,
        "status": agent.status,
        "capabilities": agent.capabilities or [],
        "capacity": agent.capacity,
        "health_status": agent.health_status,
        "tags": agent.tags or [],
        "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
    }


class AgentRegisterRequest(BaseModel):
    agent_type: str = Field(..., description="Type of agent (worker, monitor, etc.)")
    phase_id: Optional[str] = Field(None, description="Phase assignment for worker agents")
    capabilities: List[str] = Field(..., description="Declared capabilities")
    capacity: int = Field(1, ge=1, description="Concurrent tasks this agent can handle")
    status: str = Field("idle", description="Initial availability status")
    tags: Optional[List[str]] = Field(default=None, description="Optional metadata tags")


class AgentUpdateRequest(BaseModel):
    capabilities: Optional[List[str]] = None
    capacity: Optional[int] = Field(default=None, ge=1)
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    health_status: Optional[str] = None


class AgentAvailabilityRequest(BaseModel):
    available: bool = Field(..., description="True to mark agent idle/available")


class AgentDTO(BaseModel):
    agent_id: str
    agent_type: str
    phase_id: Optional[str]
    status: str
    capabilities: List[str]
    capacity: int
    health_status: str
    tags: List[str] = Field(default_factory=list)
    last_heartbeat: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(json_schema_extra={"example": {
        "agent_id": "uuid",
        "agent_type": "worker",
        "phase_id": "PHASE_IMPLEMENTATION",
        "status": "idle",
        "capabilities": ["analysis", "python"],
        "capacity": 2,
        "health_status": "healthy",
        "tags": ["python"],
        "last_heartbeat": "2025-11-16T23:10:00Z",
        "created_at": "2025-11-16T23:00:00Z",
    }})


class AgentMatchResponse(BaseModel):
    agent: AgentDTO
    match_score: float
    matched_capabilities: List[str]


@router.post("/agents/register", response_model=AgentDTO, status_code=201)
async def register_agent(
    request: AgentRegisterRequest,
    registry_service: AgentRegistryService = Depends(get_agent_registry_service),
):
    """Register a new agent with declared capabilities."""
    try:
        agent = registry_service.register_agent(
            agent_type=request.agent_type,
            phase_id=request.phase_id,
            capabilities=request.capabilities,
            capacity=request.capacity,
            status=request.status,
            tags=request.tags,
        )
        return AgentDTO(**serialize_agent(agent))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to register agent: {exc}") from exc


@router.patch("/agents/{agent_id}", response_model=AgentDTO)
async def update_agent(
    agent_id: str,
    request: AgentUpdateRequest,
    registry_service: AgentRegistryService = Depends(get_agent_registry_service),
):
    """Update agent capabilities, tags, or status."""
    try:
        agent = registry_service.update_agent(
            agent_id,
            capabilities=request.capabilities,
            capacity=request.capacity,
            status=request.status,
            tags=request.tags,
            health_status=request.health_status,
        )
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        return AgentDTO(**serialize_agent(agent))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update agent: {exc}") from exc


@router.post("/agents/{agent_id}/availability", response_model=AgentDTO)
async def toggle_agent_availability(
    agent_id: str,
    request: AgentAvailabilityRequest,
    registry_service: AgentRegistryService = Depends(get_agent_registry_service),
):
    """Toggle agent availability (idle vs maintenance)."""
    try:
        agent = registry_service.toggle_availability(agent_id, request.available)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        return AgentDTO(**serialize_agent(agent))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to toggle availability: {exc}") from exc


@router.get("/agents/search", response_model=List[AgentMatchResponse])
async def search_agents_endpoint(
    capabilities: Optional[List[str]] = Query(None, description="Required capabilities"),
    phase_id: Optional[str] = Query(None, description="Limit to a specific phase"),
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    limit: int = Query(5, ge=1, le=20),
    registry_service: AgentRegistryService = Depends(get_agent_registry_service),
):
    """Search for best-fit agents ranked by capability overlap."""
    try:
        matches = registry_service.search_agents(
            required_capabilities=capabilities or [],
            phase_id=phase_id,
            agent_type=agent_type,
            limit=limit,
        )
        return [
            AgentMatchResponse(
                agent=AgentDTO(**serialize_agent(match["agent"])),
                match_score=match["match_score"],
                matched_capabilities=match["matched_capabilities"],
            )
            for match in matches
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent search failed: {exc}") from exc


@router.get("/agents/best-fit", response_model=AgentMatchResponse)
async def get_best_fit_agent(
    capabilities: Optional[List[str]] = Query(None, description="Required capabilities"),
    phase_id: Optional[str] = Query(None),
    agent_type: Optional[str] = Query(None),
    registry_service: AgentRegistryService = Depends(get_agent_registry_service),
):
    """Return the single best-fit agent, if available."""
    try:
        match = registry_service.find_best_agent(
            required_capabilities=capabilities or [],
            phase_id=phase_id,
            agent_type=agent_type,
        )
        if not match:
            raise HTTPException(status_code=404, detail="No matching agent found")
        return AgentMatchResponse(
            agent=AgentDTO(**serialize_agent(match["agent"])),
            match_score=match["match_score"],
            matched_capabilities=match["matched_capabilities"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to find best-fit agent: {exc}") from exc


@router.get("/agents/health", response_model=List[Dict])
async def get_all_agents_health(
    timeout_seconds: Optional[int] = Query(None, description="Timeout in seconds for stale detection (default: 90)"),
    health_service: AgentHealthService = Depends(get_agent_health_service)
):
    """
    Get health status for all agents.

    Args:
        timeout_seconds: Custom timeout for stale detection
        health_service: Agent health service dependency

    Returns:
        List of health dictionaries for all agents
    """
    try:
        return health_service.get_all_agents_health(timeout_seconds)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agents health: {str(e)}")


@router.get("/agents/statistics", response_model=Dict)
async def get_agent_statistics(
    health_service: AgentHealthService = Depends(get_agent_health_service)
):
    """
    Get comprehensive statistics about all agents.

    Args:
        health_service: Agent health service dependency

    Returns:
        Dictionary containing agent statistics
    """
    try:
        return health_service.get_agent_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent statistics: {str(e)}")


@router.get("/agents/{agent_id}/health", response_model=Dict)
async def get_agent_health(
    agent_id: str,
    timeout_seconds: Optional[int] = Query(None, description="Timeout in seconds for stale detection (default: 90)"),
    health_service: AgentHealthService = Depends(get_agent_health_service)
):
    """
    Get health status for a specific agent.

    Args:
        agent_id: ID of the agent to check
        timeout_seconds: Custom timeout for stale detection
        health_service: Agent health service dependency

    Returns:
        Health dictionary for the specified agent
    """
    try:
        health_info = health_service.check_agent_health(agent_id, timeout_seconds)
        if health_info["status"] == "not_found":
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        return health_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent health: {str(e)}")


@router.post("/agents/{agent_id}/heartbeat", response_model=Dict)
async def emit_agent_heartbeat(
    agent_id: str,
    health_service: AgentHealthService = Depends(get_agent_health_service)
):
    """
    Emit a heartbeat for a specific agent (manual heartbeat).

    Args:
        agent_id: ID of the agent to emit heartbeat for
        health_service: Agent health service dependency

    Returns:
        Success status
    """
    try:
        success = health_service.emit_heartbeat(agent_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        # Get updated health info
        health_info = health_service.check_agent_health(agent_id)
        return {
            "success": True,
            "message": f"Heartbeat recorded for agent {agent_id}",
            "agent_health": health_info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to emit heartbeat: {str(e)}")


@router.get("/agents/stale", response_model=List[AgentDTO])
async def get_stale_agents(
    timeout_seconds: Optional[int] = Query(None, description="Timeout in seconds for stale detection (default: 90)"),
    health_service: AgentHealthService = Depends(get_agent_health_service)
):
    """
    Get list of stale agents.

    Args:
        timeout_seconds: Custom timeout for stale detection
        health_service: Agent health service dependency

    Returns:
        List of stale agent dictionaries
    """
    try:
        stale_agents = health_service.detect_stale_agents(timeout_seconds)
        return [AgentDTO(**serialize_agent(agent)) for agent in stale_agents]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stale agents: {str(e)}")


@router.post("/agents/cleanup-stale", response_model=Dict)
async def cleanup_stale_agents(
    timeout_seconds: Optional[int] = Query(None, description="Timeout in seconds for stale detection (default: 90)"),
    mark_as: str = Query("timeout", description="Status to mark stale agents with"),
    health_service: AgentHealthService = Depends(get_agent_health_service)
):
    """
    Mark stale agents with a specific status for cleanup tracking.

    Args:
        timeout_seconds: Custom timeout for stale detection
        mark_as: Status to mark stale agents with
        health_service: Agent health service dependency

    Returns:
        Number of agents marked for cleanup
    """
    try:
        count = health_service.cleanup_stale_agents(timeout_seconds, mark_as)
        return {
            "success": True,
            "marked_count": count,
            "timeout_seconds": timeout_seconds or 90,
            "marked_as": mark_as,
            "message": f"Marked {count} stale agents as '{mark_as}'"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup stale agents: {str(e)}")


@router.get("/agents", response_model=List[AgentDTO])
async def list_agents(
    db: DatabaseService = Depends(get_db_service)
):
    """
    Get list of all registered agents.

    Args:
        db: Database service dependency

    Returns:
        List of agent dictionaries
    """
    try:
        from omoi_os.models.agent import Agent

        with db.get_session() as session:
            agents = session.query(Agent).all()
            return [AgentDTO(**serialize_agent(agent)) for agent in agents]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")


@router.get("/agents/{agent_id}", response_model=AgentDTO)
async def get_agent(
    agent_id: str,
    db: DatabaseService = Depends(get_db_service)
):
    """
    Get details of a specific agent.

    Args:
        agent_id: ID of the agent to retrieve
        db: Database service dependency

    Returns:
        Agent dictionary
    """
    try:
        from omoi_os.models.agent import Agent

        with db.get_session() as session:
            agent = session.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

            return AgentDTO(**serialize_agent(agent))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent: {str(e)}")