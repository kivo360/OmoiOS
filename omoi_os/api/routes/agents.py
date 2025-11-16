"""Agent health and monitoring API routes."""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from omoi_os.api.dependencies import get_agent_health_service, get_db_service
from omoi_os.services.agent_health import AgentHealthService
from omoi_os.services.database import DatabaseService

router = APIRouter()


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


@router.get("/agents/stale", response_model=List[Dict])
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
        return [
            {
                "agent_id": agent.id,
                "agent_type": agent.agent_type,
                "phase_id": agent.phase_id,
                "status": agent.status,
                "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
                "created_at": agent.created_at.isoformat() if agent.created_at else None,
                "capabilities": agent.capabilities,
            }
            for agent in stale_agents
        ]
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


@router.get("/agents", response_model=List[Dict])
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
            return [
                {
                    "agent_id": agent.id,
                    "agent_type": agent.agent_type,
                    "phase_id": agent.phase_id,
                    "status": agent.status,
                    "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
                    "created_at": agent.created_at.isoformat() if agent.created_at else None,
                    "capabilities": agent.capabilities,
                }
                for agent in agents
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")


@router.get("/agents/{agent_id}", response_model=Dict)
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

            return {
                "agent_id": agent.id,
                "agent_type": agent.agent_type,
                "phase_id": agent.phase_id,
                "status": agent.status,
                "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
                "created_at": agent.created_at.isoformat() if agent.created_at else None,
                "capabilities": agent.capabilities,
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent: {str(e)}")