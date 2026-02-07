"""Agent status manager for state machine enforcement per REQ-ALM-004."""

from typing import Optional

from omoi_os.models.agent import Agent
from omoi_os.models.agent_status import AgentStatus, is_valid_transition
from omoi_os.models.agent_status_transition import AgentStatusTransition
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now


class InvalidTransitionError(Exception):
    """Raised when an invalid agent status transition is attempted."""


class AgentStatusManager:
    """
    Agent status manager per REQ-ALM-004.

    Enforces agent status state machine transitions, records audit logs,
    and emits AGENT_STATUS_CHANGED events.
    """

    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
    ):
        """
        Initialize agent status manager.

        Args:
            db: Database service
            event_bus: Optional event bus for publishing events
        """
        self.db = db
        self.event_bus = event_bus

    def transition_status(
        self,
        agent_id: str,
        to_status: str,
        initiated_by: Optional[str] = None,
        reason: Optional[str] = None,
        task_id: Optional[str] = None,
        force: bool = False,
        metadata: Optional[dict] = None,
    ) -> Agent:
        """
        Transition agent to new status with validation per REQ-ALM-004.

        Args:
            agent_id: Agent ID
            to_status: Target status (must be valid AgentStatus value)
            initiated_by: Agent or user ID initiating transition
            reason: Optional reason for transition
            task_id: Optional task ID associated with transition
            force: Skip validation if True (guardian override)
            metadata: Optional additional context (error details, metrics, etc.)

        Returns:
            Updated agent

        Raises:
            ValueError: If agent not found
            InvalidTransitionError: If transition is not valid
        """
        # Validate to_status is a valid AgentStatus
        if to_status not in [status.value for status in AgentStatus]:
            raise ValueError(f"Invalid status: {to_status}")

        with self.db.get_session() as session:
            agent = session.get(Agent, agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")

            from_status = agent.status

            # Validate transition unless forced
            if not force:
                if not is_valid_transition(from_status, to_status):
                    raise InvalidTransitionError(
                        f"Invalid transition from {from_status} to {to_status} "
                        f"for agent {agent_id}"
                    )

            # Update status
            agent.status = to_status
            agent.updated_at = utc_now()

            # Record transition in audit log
            transition = AgentStatusTransition(
                agent_id=agent.id,
                from_status=from_status,
                to_status=to_status,
                reason=reason,
                triggered_by=initiated_by,
                task_id=task_id,
                transition_metadata=metadata,
            )
            session.add(transition)

            session.commit()
            session.refresh(agent)
            session.expunge(agent)

            # Publish AGENT_STATUS_CHANGED event per REQ-ALM-004
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="AGENT_STATUS_CHANGED",
                        entity_type="agent",
                        entity_id=str(agent.id),
                        payload={
                            "agent_id": str(agent.id),
                            "previous_status": from_status,
                            "new_status": to_status,
                            "reason": reason,
                            "task_id": task_id,
                            "triggered_by": initiated_by,
                            "timestamp": utc_now().isoformat(),
                        },
                    )
                )

            return agent

    def get_transition_history(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> list[AgentStatusTransition]:
        """
        Get status transition history for an agent.

        Args:
            agent_id: Agent ID
            limit: Maximum number of transitions to return

        Returns:
            List of status transitions, most recent first
        """
        with self.db.get_session() as session:
            transitions = (
                session.query(AgentStatusTransition)
                .filter(AgentStatusTransition.agent_id == agent_id)
                .order_by(AgentStatusTransition.transitioned_at.desc())
                .limit(limit)
                .all()
            )
            # Expunge all transitions for use outside session
            for transition in transitions:
                session.expunge(transition)
            return transitions
