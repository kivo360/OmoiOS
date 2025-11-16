"""Agent registry service for CRUD, capability updates, and discovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import and_

from omoi_os.models.agent import Agent
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent


@dataclass(frozen=True)
class AgentMatch:
    """Discovery result wrapper."""

    agent: Agent
    match_score: float
    matched_capabilities: List[str]


class AgentRegistryService:
    """Capability-aware agent registry and discovery service."""

    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
    ):
        self.db = db
        self.event_bus = event_bus

    # ---------------------------------------------------------------------
    # CRUD
    # ---------------------------------------------------------------------

    def register_agent(
        self,
        *,
        agent_type: str,
        phase_id: Optional[str],
        capabilities: List[str],
        capacity: int = 1,
        status: str = "idle",
        tags: Optional[List[str]] = None,
    ) -> Agent:
        """Register a new agent in the registry."""
        normalized_caps = self._normalize_tokens(capabilities)
        normalized_tags = self._normalize_tokens(tags or [])

        with self.db.get_session() as session:
            agent = Agent(
                agent_type=agent_type,
                phase_id=phase_id,
                status=status,
                capabilities=normalized_caps,
                capacity=max(1, capacity),
                tags=normalized_tags or None,
            )
            session.add(agent)
            session.commit()
            session.refresh(agent)

            self._publish_capability_event(agent.id, agent.capabilities)
            return agent

    def update_agent(
        self,
        agent_id: str,
        *,
        capabilities: Optional[List[str]] = None,
        capacity: Optional[int] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        health_status: Optional[str] = None,
    ) -> Optional[Agent]:
        """Update mutable agent metadata."""
        with self.db.get_session() as session:
            agent = session.get(Agent, agent_id)
            if not agent:
                return None

            capabilities_changed = False

            if capabilities is not None:
                normalized_caps = self._normalize_tokens(capabilities)
                if normalized_caps != agent.capabilities:
                    agent.capabilities = normalized_caps
                    capabilities_changed = True

            if tags is not None:
                normalized_tags = self._normalize_tokens(tags)
                agent.tags = normalized_tags or None

            if capacity is not None:
                agent.capacity = max(1, capacity)

            if status is not None:
                agent.status = status

            if health_status is not None:
                agent.health_status = health_status

            session.commit()
            session.refresh(agent)

            if capabilities_changed:
                self._publish_capability_event(agent.id, agent.capabilities)

            return agent

    def toggle_availability(self, agent_id: str, available: bool) -> Optional[Agent]:
        """Mark an agent as available (idle) or unavailable (maintenance)."""
        new_status = "idle" if available else "maintenance"
        return self.update_agent(agent_id, status=new_status)

    # ---------------------------------------------------------------------
    # Discovery
    # ---------------------------------------------------------------------

    def search_agents(
        self,
        *,
        required_capabilities: Optional[List[str]] = None,
        phase_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        limit: int = 5,
        include_degraded: bool = False,
    ) -> List[dict]:
        """Search for agents ranked by capability overlap and availability."""
        required = self._normalize_tokens(required_capabilities or [])

        with self.db.get_session() as session:
            query = session.query(Agent)
            filters = []
            if phase_id:
                filters.append(Agent.phase_id == phase_id)
            if agent_type:
                filters.append(Agent.agent_type == agent_type)
            if not include_degraded:
                filters.append(Agent.status.notin_(["terminated", "quarantined"]))

            if filters:
                query = query.filter(and_(*filters))

            agents = query.all()

        matches: List[dict] = []
        for agent in agents:
            match = self._calculate_match(agent, required)
            matches.append(
                {
                    "agent": agent,
                    "match_score": match.match_score,
                    "matched_capabilities": match.matched_capabilities,
                }
            )

        matches.sort(key=lambda item: item["match_score"], reverse=True)
        return matches[:limit]

    def find_best_agent(
        self,
        *,
        required_capabilities: Optional[List[str]] = None,
        phase_id: Optional[str] = None,
        agent_type: Optional[str] = None,
    ) -> Optional[dict]:
        """Return the top-ranked agent for the given criteria."""
        matches = self.search_agents(
            required_capabilities=required_capabilities,
            phase_id=phase_id,
            agent_type=agent_type,
            limit=1,
        )
        return matches[0] if matches else None

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------

    def _calculate_match(self, agent: Agent, required: List[str]) -> AgentMatch:
        agent_caps = self._normalize_tokens(agent.capabilities or [])
        overlap = sorted(set(required) & set(agent_caps))
        coverage = len(overlap) / len(required) if required else 0.0

        availability_bonus = 0.2 if agent.status == "idle" else 0.0
        health_bonus = 0.2 if agent.health_status == "healthy" else 0.0
        capacity_bonus = min(agent.capacity, 5) * 0.05

        score = coverage + availability_bonus + health_bonus + capacity_bonus
        return AgentMatch(agent=agent, match_score=score, matched_capabilities=overlap)

    def _normalize_tokens(self, values: List[str]) -> List[str]:
        return [value.strip().lower() for value in values if value and value.strip()]

    def _publish_capability_event(self, agent_id: str, capabilities: List[str]) -> None:
        if not self.event_bus:
            return

        event = SystemEvent(
            event_type="agent.capability.updated",
            entity_type="agent",
            entity_id=agent_id,
            payload={
                "agent_id": agent_id,
                "capabilities": capabilities,
            },
        )
        self.event_bus.publish(event)
