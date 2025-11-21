"""Agent Health Service for monitoring agent heartbeats and status."""

from datetime import timedelta
from typing import Dict, List, Optional

from sqlalchemy import or_

from omoi_os.models.agent import Agent
from omoi_os.models.agent_status import AgentStatus
from omoi_os.services.agent_status_manager import AgentStatusManager
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now


class AgentHealthService:
    """Service for monitoring agent health and managing heartbeats."""

    def __init__(self, db: DatabaseService, status_manager: Optional[AgentStatusManager] = None):
        """
        Initialize AgentHealthService.

        Args:
            db: Database service instance
            status_manager: Optional status manager for state machine enforcement
        """
        self.db = db
        self.status_manager = status_manager

    def emit_heartbeat(self, agent_id: str) -> bool:
        """
        Emit a heartbeat for an agent, updating its last_heartbeat timestamp.

        Args:
            agent_id: ID of the agent to update

        Returns:
            True if heartbeat was recorded successfully, False if agent not found
        """
        with self.db.get_session() as session:
            agent = session.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                return False

            # Update heartbeat and restore status if it was stale (legacy) or DEGRADED
            agent.last_heartbeat = utc_now()
            if agent.status in ["stale", "STALE"]:
                # Use status manager if available, otherwise direct update
                agent_id_for_status = agent.id
                session.expunge(agent)
                session.commit()
                if self.status_manager:
                    try:
                        self.status_manager.transition_status(
                            agent_id_for_status,
                            to_status=AgentStatus.IDLE.value,
                            initiated_by="agent_health_service",
                            reason="Heartbeat received, recovering from stale state",
                        )
                    except Exception:
                        # Fallback: direct update
                        with self.db.get_session() as session:
                            agent = session.get(Agent, agent_id_for_status)
                            if agent:
                                agent.status = AgentStatus.IDLE.value
                                session.commit()
                else:
                    with self.db.get_session() as session:
                        agent = session.get(Agent, agent_id_for_status)
                        if agent:
                            agent.status = AgentStatus.IDLE.value
                            session.commit()
            else:
                agent.health_status = "healthy"

            session.commit()
            return True

    def check_agent_health(
        self, agent_id: str, timeout_seconds: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Check the health status of a specific agent.

        Args:
            agent_id: ID of the agent to check
            timeout_seconds: Custom timeout in seconds (defaults to 90)

        Returns:
            Dictionary containing health information
        """
        if timeout_seconds is None:
            timeout_seconds = 90

        with self.db.get_session() as session:
            agent = session.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                return {
                    "agent_id": agent_id,
                    "status": "not_found",
                    "healthy": False,
                    "last_heartbeat": None,
                    "time_since_last_heartbeat": None,
                    "health_status": "unknown",
                }

            now = utc_now()
            last_heartbeat = agent.last_heartbeat

            if not last_heartbeat:
                # Agent has never sent a heartbeat
                return {
                    "agent_id": agent_id,
                    "status": agent.status,
                    "healthy": False,
                    "last_heartbeat": None,
                    "time_since_last_heartbeat": None,
                    "message": "No heartbeat recorded",
                    "health_status": agent.health_status or "unknown",
                }

            time_since_last_heartbeat = now - last_heartbeat
            is_stale = time_since_last_heartbeat > timedelta(seconds=timeout_seconds)

            # Update agent status if it's stale but not marked as such
            if is_stale and agent.status != "stale":
                agent.status = "stale"
                agent.health_status = "stale"
                session.commit()
            elif not is_stale and agent.health_status != "healthy":
                agent.health_status = "healthy"
                session.commit()

            return {
                "agent_id": agent_id,
                "status": agent.status,
                "healthy": not is_stale,
                "last_heartbeat": last_heartbeat.isoformat()
                if last_heartbeat
                else None,
                "time_since_last_heartbeat": time_since_last_heartbeat.total_seconds(),
                "timeout_seconds": timeout_seconds,
                "agent_type": agent.agent_type,
                "phase_id": agent.phase_id,
                "health_status": agent.health_status,
            }

    def detect_stale_agents(self, timeout_seconds: Optional[int] = None) -> List[Agent]:
        """
        Detect agents that have not sent a heartbeat within the timeout period.

        Args:
            timeout_seconds: Custom timeout in seconds (defaults to 90)

        Returns:
            List of stale Agent objects
        """
        if timeout_seconds is None:
            timeout_seconds = 90

        cutoff_time = utc_now() - timedelta(seconds=timeout_seconds)

        with self.db.get_session() as session:
            # Find agents with no heartbeat or last heartbeat before cutoff
            stale_agents = (
                session.query(Agent)
                .filter(
                    or_(
                        Agent.last_heartbeat.is_(None),
                        Agent.last_heartbeat < cutoff_time,
                    )
                )
                .all()
            )

            # Update their status to stale if not already
            for agent in stale_agents:
                if agent.status != "stale":
                    agent.status = "stale"
                agent.health_status = "stale"

            session.commit()
            return stale_agents

    def get_all_agents_health(
        self, timeout_seconds: Optional[int] = None
    ) -> List[Dict[str, any]]:
        """
        Get health status for all agents.

        Args:
            timeout_seconds: Custom timeout in seconds (defaults to 90)

        Returns:
            List of health dictionaries for all agents
        """
        if timeout_seconds is None:
            timeout_seconds = 90

        with self.db.get_session() as session:
            agents = session.query(Agent).all()

            health_results = []
            now = utc_now()
            cutoff_time = now - timedelta(seconds=timeout_seconds)

            for agent in agents:
                last_heartbeat = agent.last_heartbeat
                time_since_last_heartbeat = None

                if last_heartbeat:
                    time_since_last_heartbeat = (now - last_heartbeat).total_seconds()
                    is_stale = last_heartbeat < cutoff_time
                else:
                    is_stale = True  # No heartbeat means stale

                # Update agent status if needed
                current_status = agent.status
                if is_stale and current_status != "stale":
                    agent.status = "stale"
                    agent.health_status = "stale"
                elif not is_stale and current_status == "stale":
                    agent.status = "idle"
                    agent.health_status = "healthy"
                elif not is_stale and not agent.health_status:
                    agent.health_status = "healthy"

                health_results.append(
                    {
                        "agent_id": agent.id,
                        "agent_type": agent.agent_type,
                        "phase_id": agent.phase_id,
                        "status": agent.status,
                        "healthy": not is_stale,
                        "last_heartbeat": last_heartbeat.isoformat()
                        if last_heartbeat
                        else None,
                        "time_since_last_heartbeat": time_since_last_heartbeat,
                        "timeout_seconds": timeout_seconds,
                        "capabilities": agent.capabilities,
                        "created_at": agent.created_at.isoformat()
                        if agent.created_at
                        else None,
                        "health_status": agent.health_status or "healthy"
                        if not is_stale
                        else "stale",
                    }
                )

            session.commit()
            return health_results

    def cleanup_stale_agents(
        self, timeout_seconds: Optional[int] = None, mark_as: str = "timeout"
    ) -> int:
        """
        Mark stale agents with a specific status for cleanup tracking.

        Args:
            timeout_seconds: Custom timeout in seconds (defaults to 90)
            mark_as: Status to mark stale agents with (default: "timeout")

        Returns:
            Number of agents marked for cleanup
        """
        if timeout_seconds is None:
            timeout_seconds = 90

        cutoff_time = utc_now() - timedelta(seconds=timeout_seconds)

        with self.db.get_session() as session:
            # Find agents that are stale
            stale_agents = (
                session.query(Agent)
                .filter(
                    or_(
                        Agent.last_heartbeat.is_(None),
                        Agent.last_heartbeat < cutoff_time,
                    )
                )
                .all()
            )

            # Mark them with specified status
            count = 0
            for agent in stale_agents:
                if agent.status not in ["terminated", mark_as]:
                    agent.status = mark_as
                    agent.health_status = mark_as
                    count += 1

            session.commit()
            return count

    def get_agent_statistics(self) -> Dict[str, any]:
        """
        Get comprehensive statistics about all agents.

        Returns:
            Dictionary containing agent statistics
        """
        with self.db.get_session() as session:
            agents = session.query(Agent).all()

            stats = {
                "total_agents": len(agents),
                "by_status": {},
                "by_type": {},
                "by_phase": {},
                "health_summary": {
                    "healthy": 0,
                    "unhealthy": 0,
                    "unknown": 0,  # No heartbeat recorded
                },
                "recent_heartbeats": {
                    "last_5_minutes": 0,
                    "last_hour": 0,
                    "last_24_hours": 0,
                },
            }

            now = utc_now()
            time_5min_ago = now - timedelta(minutes=5)
            time_1hour_ago = now - timedelta(hours=1)
            time_24hours_ago = now - timedelta(hours=24)
            cutoff_time = now - timedelta(seconds=90)

            for agent in agents:
                # Status statistics
                status = agent.status
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

                # Type statistics
                agent_type = agent.agent_type
                stats["by_type"][agent_type] = stats["by_type"].get(agent_type, 0) + 1

                # Phase statistics
                phase = agent.phase_id or "no_phase"
                stats["by_phase"][phase] = stats["by_phase"].get(phase, 0) + 1

                # Health summary
                last_heartbeat = agent.last_heartbeat
                # Determine health based on heartbeat recency
                is_healthy = last_heartbeat and last_heartbeat >= cutoff_time

                if is_healthy:
                    stats["health_summary"]["healthy"] += 1
                elif agent.health_status in ["stale", "timeout", "unresponsive"]:
                    stats["health_summary"]["unhealthy"] += 1
                else:
                    stats["health_summary"]["unknown"] += 1

                # Recent heartbeat statistics
                if last_heartbeat:
                    if last_heartbeat >= time_5min_ago:
                        stats["recent_heartbeats"]["last_5_minutes"] += 1
                    if last_heartbeat >= time_1hour_ago:
                        stats["recent_heartbeats"]["last_hour"] += 1
                    if last_heartbeat >= time_24hours_ago:
                        stats["recent_heartbeats"]["last_24_hours"] += 1

            return stats
