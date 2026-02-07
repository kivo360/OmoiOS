"""High-level client for interacting with the Agent Registry service."""

from __future__ import annotations

from typing import Dict, List, Optional

from omoi_os.models.agent import Agent
from omoi_os.services.agent_registry import AgentRegistryService


def _serialize_agent(agent: Agent) -> Dict:
    return {
        "agent_id": agent.id,
        "agent_type": agent.agent_type,
        "phase_id": agent.phase_id,
        "status": agent.status,
        "capabilities": agent.capabilities or [],
        "capacity": agent.capacity,
        "health_status": agent.health_status,
        "tags": agent.tags or [],
        "last_heartbeat": (
            agent.last_heartbeat.isoformat() if agent.last_heartbeat else None
        ),
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
    }


class AgentRegistryClient:
    """Thin wrapper that exposes registry operations for other agents/services."""

    def __init__(self, registry_service: AgentRegistryService):
        self._registry = registry_service

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def register(
        self,
        *,
        agent_type: str,
        phase_id: Optional[str],
        capabilities: List[str],
        capacity: int = 1,
        tags: Optional[List[str]] = None,
    ) -> Dict:
        agent = self._registry.register_agent(
            agent_type=agent_type,
            phase_id=phase_id,
            capabilities=capabilities,
            capacity=capacity,
            tags=tags,
        )
        return _serialize_agent(agent)

    def update(
        self,
        agent_id: str,
        *,
        capabilities: Optional[List[str]] = None,
        capacity: Optional[int] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        health_status: Optional[str] = None,
    ) -> Optional[Dict]:
        agent = self._registry.update_agent(
            agent_id,
            capabilities=capabilities,
            capacity=capacity,
            status=status,
            tags=tags,
            health_status=health_status,
        )
        return _serialize_agent(agent) if agent else None

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def search_best_matches(
        self,
        *,
        required_capabilities: Optional[List[str]] = None,
        phase_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict]:
        matches = self._registry.search_agents(
            required_capabilities=required_capabilities or [],
            phase_id=phase_id,
            agent_type=agent_type,
            limit=limit,
        )
        return [
            {
                "agent": _serialize_agent(match["agent"]),
                "match_score": match["match_score"],
                "matched_capabilities": match["matched_capabilities"],
            }
            for match in matches
        ]

    def find_best_match(
        self,
        *,
        required_capabilities: Optional[List[str]] = None,
        phase_id: Optional[str] = None,
        agent_type: Optional[str] = None,
    ) -> Optional[Dict]:
        match = self._registry.find_best_agent(
            required_capabilities=required_capabilities or [],
            phase_id=phase_id,
            agent_type=agent_type,
        )
        if not match:
            return None
        return {
            "agent": _serialize_agent(match["agent"]),
            "match_score": match["match_score"],
            "matched_capabilities": match["matched_capabilities"],
        }
