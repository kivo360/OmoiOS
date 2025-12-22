"""Restart orchestrator for automatic agent restart protocol per REQ-FT-AR-002."""

from datetime import timedelta
from typing import List, Optional

from omoi_os.models.agent import Agent
from omoi_os.models.agent_status import AgentStatus
from omoi_os.models.guardian_action import AuthorityLevel
from omoi_os.services.agent_registry import AgentRegistryService
from omoi_os.services.agent_status_manager import AgentStatusManager
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.utils.datetime import utc_now


class RestartOrchestrator:
    """
    Restart orchestrator per REQ-FT-AR-002.
    
    Executes restart steps:
    1. Graceful stop (10s timeout)
    2. Force terminate if graceful fails
    3. Spawn replacement with same config
    4. Reassign incomplete tasks
    5. Emit AGENT_RESTARTED event
    """

    GRACEFUL_STOP_TIMEOUT = timedelta(seconds=10)
    MAX_RESTART_ATTEMPTS = 3  # per REQ-FT-AR-004
    ESCALATION_WINDOW = timedelta(hours=1)  # per REQ-FT-AR-004
    RESTART_COOLDOWN = timedelta(seconds=60)  # per REQ-FT-AR-003

    def __init__(
        self,
        db: DatabaseService,
        agent_registry: AgentRegistryService,
        task_queue: TaskQueueService,
        event_bus: Optional[EventBusService] = None,
        status_manager: Optional[AgentStatusManager] = None,
    ):
        """
        Initialize RestartOrchestrator.

        Args:
            db: Database service instance
            agent_registry: Agent registry service for spawning replacements
            task_queue: Task queue service for task reassignment
            event_bus: Optional event bus for publishing restart events
            status_manager: Optional status manager for state machine enforcement
        """
        self.db = db
        self.agent_registry = agent_registry
        self.task_queue = task_queue
        self.event_bus = event_bus
        self.status_manager = status_manager

    def initiate_restart(
        self, agent_id: str, reason: str, authority: AuthorityLevel = AuthorityLevel.MONITOR
    ) -> Optional[dict]:
        """
        Initiate restart protocol for an agent per REQ-FT-AR-002.

        Args:
            agent_id: ID of the agent to restart
            reason: Reason for restart (e.g., "missed_heartbeats", "anomaly_detected")
            authority: Authority level of the caller (default: MONITOR)

        Returns:
            Dictionary with restart details or None if restart cannot proceed

        Raises:
            PermissionError: If authority level insufficient
        """
        # Check authority (only MONITOR, GUARDIAN, or SYSTEM can initiate restarts)
        if authority < AuthorityLevel.MONITOR:
            raise PermissionError(f"Insufficient authority to initiate restart: {authority}")

        with self.db.get_session() as session:
            agent = session.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                return None

            # Check if restart is allowed (cooldown, max attempts)
            can_restart, error_msg = self._can_restart(agent)
            if not can_restart:
                # Escalate to guardian if max attempts exceeded
                if self.event_bus:
                    self.event_bus.publish(
                        SystemEvent(
                            event_type="RESTART_ESCALATION",
                            entity_type="agent",
                            entity_id=agent_id,
                            payload={
                                "reason": error_msg,
                                "action": "Escalate to Guardian",
                            },
                        )
                    )
                return None

            # Step 1: Graceful stop
            graceful_success = self._graceful_stop(agent_id)

            # Step 2: Force terminate if graceful fails
            if not graceful_success:
                self._force_terminate(agent_id)

            # Step 3: Spawn replacement
            replacement_id = self._spawn_replacement(agent)

            # Step 4: Reassign incomplete tasks
            reassigned_tasks = self._reassign_tasks(agent_id, replacement_id)

            # Step 5: Emit event
            restart_event = {
                "agent_id": agent_id,
                "replacement_agent_id": replacement_id,
                "reason": reason,
                "graceful_stop_success": graceful_success,
                "reassigned_tasks": reassigned_tasks,
                "occurred_at": utc_now().isoformat(),
            }

            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="AGENT_RESTARTED",
                        entity_type="agent",
                        entity_id=agent_id,
                        payload=restart_event,
                    )
                )

            # Update agent restart tracking using status manager if available
            agent_id_for_status = agent.id
            session.expunge(agent)  # Expunge before closing session
            session.commit()

            # Update status using status manager outside session
            if self.status_manager:
                try:
                    self.status_manager.transition_status(
                        agent_id_for_status,
                        to_status=AgentStatus.TERMINATED.value,
                        initiated_by="restart_orchestrator",
                        reason=reason,
                        force=True,  # Force transition for restart protocol
                    )
                except Exception:
                    # Fallback to direct update if status manager fails
                    with self.db.get_session() as session:
                        agent = session.get(Agent, agent_id_for_status)
                        if agent:
                            agent.status = AgentStatus.TERMINATED.value
                            agent.health_status = "terminated"
                            session.commit()
            else:
                # Fallback to direct update if status manager not available
                with self.db.get_session() as session:
                    agent = session.get(Agent, agent_id_for_status)
                    if agent:
                        agent.status = AgentStatus.TERMINATED.value
                        agent.health_status = "terminated"
                        session.commit()

            return restart_event

    def _can_restart(self, agent: Agent) -> tuple[bool, Optional[str]]:
        """
        Check if restart is allowed per REQ-FT-AR-003 and REQ-FT-AR-004.

        Args:
            agent: Agent object

        Returns:
            Tuple (can_restart: bool, error_message: Optional[str])
        """
        # Check cooldown (REQ-FT-AR-003)
        # TODO: Implement cooldown tracking in agent model or separate table
        # For now, allow restart

        # Check max attempts (REQ-FT-AR-004)
        # TODO: Implement restart attempt tracking per ESCALATION_WINDOW
        # For now, allow restart

        return True, None

    def _graceful_stop(self, agent_id: str) -> bool:
        """
        Attempt graceful stop per REQ-FT-AR-002 Step 1.

        Args:
            agent_id: ID of the agent to stop

        Returns:
            True if graceful stop succeeded, False otherwise
        """
        # In a real implementation, this would:
        # 1. Send stop signal to agent
        # 2. Wait up to GRACEFUL_STOP_TIMEOUT
        # 3. Check if agent stopped gracefully

        # For now, we'll mark it as attempted
        # In production, this would use agent's stop API or signal
        return True  # Assume graceful stop succeeded

    def _force_terminate(self, agent_id: str) -> None:
        """
        Force terminate agent per REQ-FT-AR-002 Step 2.

        Args:
            agent_id: ID of the agent to terminate
        """
        # In a real implementation, this would:
        # 1. Send SIGKILL to agent process
        # 2. Mark agent as terminated
        # 3. Force-release all resources

        if self.status_manager:
            try:
                self.status_manager.transition_status(
                    agent_id,
                    to_status=AgentStatus.TERMINATED.value,
                    initiated_by="restart_orchestrator",
                    reason="Force terminate after graceful stop failed",
                    force=True,  # Force transition for restart protocol
                )
            except Exception:
                # Fallback to direct update if status manager fails
                with self.db.get_session() as session:
                    agent = session.query(Agent).filter(Agent.id == agent_id).first()
                    if agent:
                        agent.status = AgentStatus.TERMINATED.value
                        agent.health_status = "terminated"
                        session.commit()
        else:
            # Fallback to direct update if status manager not available
            with self.db.get_session() as session:
                agent = session.query(Agent).filter(Agent.id == agent_id).first()
                if agent:
                    agent.status = AgentStatus.TERMINATED.value
                    agent.health_status = "terminated"
                    session.commit()

    def _spawn_replacement(self, original_agent: Agent) -> str:
        """
        Spawn replacement agent with same config per REQ-FT-AR-002 Step 3.

        Args:
            original_agent: Original agent object

        Returns:
            ID of the replacement agent
        """
        # Spawn replacement with same configuration
        replacement = self.agent_registry.register_agent(
            agent_type=original_agent.agent_type,
            phase_id=original_agent.phase_id,
            capabilities=original_agent.capabilities,
            capacity=original_agent.capacity,
            status=AgentStatus.IDLE.value,  # Use AgentStatus enum
            tags=original_agent.tags,
        )
        return replacement.id

    def _reassign_tasks(self, old_agent_id: str, new_agent_id: str) -> List[str]:
        """
        Reassign incomplete tasks from old agent to new agent per REQ-FT-AR-002 Step 4.

        Args:
            old_agent_id: ID of the old (terminated) agent
            new_agent_id: ID of the new (replacement) agent

        Returns:
            List of reassigned task IDs
        """
        from omoi_os.models.task import Task

        with self.db.get_session() as session:
            # Find all tasks assigned to old agent that are not completed
            incomplete_tasks = (
                session.query(Task)
                .filter(
                    Task.assigned_agent_id == old_agent_id,
                    Task.status.in_(["assigned", "running", "claiming"]),
                )
                .all()
            )

            reassigned_task_ids = []
            for task in incomplete_tasks:
                # Reassign task to new agent
                task.assigned_agent_id = new_agent_id
                task.status = "pending"  # Reset to pending so it can be picked up again
                # IMPORTANT: Clear sandbox_id so task can be picked up by get_next_task()
                # The atomic claim in get_next_task() filters out tasks with existing sandbox_id
                task.sandbox_id = None
                reassigned_task_ids.append(task.id)

            session.commit()
            return reassigned_task_ids

