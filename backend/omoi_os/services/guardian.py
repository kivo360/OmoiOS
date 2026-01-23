"""Guardian service for emergency intervention and resource reallocation."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import attributes

from omoi_os.logging import get_logger
from omoi_os.models.agent import Agent
from omoi_os.models.guardian_action import AuthorityLevel, GuardianAction
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.services.spec_driven_settings import SpecDrivenSettingsService

logger = get_logger(__name__)


class GuardianService:
    """Emergency intervention system for critical failures and resource management.
    
    Provides authority-based intervention capabilities:
    - Emergency task cancellation
    - Agent capacity reallocation  
    - Priority queue override
    - Automatic rollback after crisis resolution
    
    Authority hierarchy: GUARDIAN (4) > MONITOR (3) > WATCHDOG (2) > WORKER (1)
    """

    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
        settings_service: Optional["SpecDrivenSettingsService"] = None,
    ):
        """Initialize guardian service.

        Args:
            db: DatabaseService instance for database operations
            event_bus: Optional EventBusService for publishing intervention events
            settings_service: Optional SpecDrivenSettingsService for project settings
        """
        self.db = db
        self.event_bus = event_bus
        self.settings_service = settings_service

    # -------------------------------------------------------------------------
    # Settings and Auto-Steering Helpers
    # -------------------------------------------------------------------------

    def _get_project_id_for_task(self, task_id: str) -> Optional[str]:
        """Get the project ID for a task through its ticket.

        Args:
            task_id: The task ID to look up

        Returns:
            Project ID if found, None otherwise
        """
        with self.db.get_session() as session:
            task = session.get(Task, task_id)
            if not task or not task.ticket_id:
                return None

            ticket = session.get(Ticket, task.ticket_id)
            if not ticket:
                return None

            return ticket.project_id

    def _check_auto_steering_enabled(
        self,
        project_id: Optional[str],
        action_type: str,
        target_entity: str,
    ) -> tuple[bool, bool]:
        """Check if auto-steering is enabled for a project.

        Args:
            project_id: The project ID to check settings for
            action_type: Type of intervention being attempted
            target_entity: Entity being intervened upon

        Returns:
            Tuple of (auto_steering_enabled, settings_checked)
            - auto_steering_enabled: True if intervention should proceed
            - settings_checked: True if settings were actually checked
        """
        # If no settings service configured, default to enabled
        if not self.settings_service:
            return True, False

        # If no project_id, we can't check settings - default to enabled
        if not project_id:
            logger.debug(
                "No project_id for intervention, defaulting to auto-steering enabled",
                action_type=action_type,
                target_entity=target_entity,
            )
            return True, False

        # Check project settings
        auto_steering = self.settings_service.get_guardian_auto_steering(project_id)

        logger.info(
            "Checked guardian_auto_steering setting",
            project_id=project_id,
            auto_steering_enabled=auto_steering,
            action_type=action_type,
            target_entity=target_entity,
        )

        return auto_steering, True

    def _log_intervention_skipped(
        self,
        action_type: str,
        target_entity: str,
        reason: str,
        initiated_by: str,
        authority: AuthorityLevel,
        project_id: Optional[str],
    ) -> GuardianAction:
        """Log an intervention that was skipped due to auto-steering being disabled.

        Creates an audit record with executed=False to track that the intervention
        was detected but not executed.

        Args:
            action_type: Type of intervention
            target_entity: Entity that would have been intervened upon
            reason: Original reason for intervention
            initiated_by: Who initiated the intervention
            authority: Authority level of initiator
            project_id: Project ID if known

        Returns:
            GuardianAction audit record
        """
        with self.db.get_session() as session:
            action = GuardianAction(
                action_type=action_type,
                target_entity=target_entity,
                authority_level=authority,
                reason=reason,
                initiated_by=initiated_by,
                approved_by=None,
                executed_at=None,  # Not executed
                audit_log={
                    "auto_steering_enabled": False,
                    "executed": False,
                    "skipped_reason": "guardian_auto_steering disabled for project",
                    "project_id": project_id,
                },
            )
            session.add(action)
            session.commit()
            session.refresh(action)
            session.expunge(action)

            logger.info(
                "Intervention logged but not executed (auto-steering disabled)",
                action_id=action.id,
                action_type=action_type,
                target_entity=target_entity,
                project_id=project_id,
            )

            return action

    # -------------------------------------------------------------------------
    # Core Intervention Methods
    # -------------------------------------------------------------------------

    def emergency_cancel_task(
        self,
        task_id: str,
        reason: str,
        initiated_by: str,
        authority: AuthorityLevel = AuthorityLevel.GUARDIAN,
        manual: bool = False,
    ) -> Optional[GuardianAction]:
        """Cancel a running task in emergency situations.

        Args:
            task_id: ID of task to cancel
            reason: Explanation for emergency cancellation
            initiated_by: Agent/user ID initiating the action
            authority: Authority level (must be GUARDIAN or higher)
            manual: If True, bypass auto-steering check (manual intervention)

        Returns:
            GuardianAction audit record if successful, None if task not found

        Raises:
            PermissionError: If authority level insufficient
        """
        if authority < AuthorityLevel.GUARDIAN:
            raise PermissionError(
                f"Emergency cancellation requires GUARDIAN authority (level {AuthorityLevel.GUARDIAN}), "
                f"but got {authority.name} (level {authority})"
            )

        # Get project_id for settings check
        project_id = self._get_project_id_for_task(task_id)

        # Check auto-steering setting (unless this is a manual intervention)
        if not manual:
            auto_steering, settings_checked = self._check_auto_steering_enabled(
                project_id, "cancel_task", task_id
            )
            if settings_checked and not auto_steering:
                return self._log_intervention_skipped(
                    action_type="cancel_task",
                    target_entity=task_id,
                    reason=reason,
                    initiated_by=initiated_by,
                    authority=authority,
                    project_id=project_id,
                )

        with self.db.get_session() as session:
            task = session.get(Task, task_id)
            if not task:
                return None

            # Record state before intervention
            before_state = {
                "status": task.status,
                "assigned_agent_id": task.assigned_agent_id,
                "priority": task.priority,
            }

            # Cancel the task
            old_status = task.status
            task.status = "failed"
            task.error_message = f"EMERGENCY CANCELLATION: {reason}"

            # Create audit record
            action = GuardianAction(
                action_type="cancel_task",
                target_entity=task_id,
                authority_level=authority,
                reason=reason,
                initiated_by=initiated_by,
                approved_by=None,  # Emergency actions auto-approved
                executed_at=utc_now(),
                audit_log={
                    "before": before_state,
                    "after": {"status": "failed", "error_message": task.error_message},
                    "old_status": old_status,
                    "intervention_type": "emergency",
                    "auto_steering_enabled": True,
                    "executed": True,
                    "manual": manual,
                    "project_id": project_id,
                },
            )
            session.add(action)
            session.commit()
            session.refresh(action)
            session.expunge(action)

            # Publish event
            self._publish_event(
                "guardian.intervention.started",
                entity_id=action.id,
                payload={
                    "action_type": "cancel_task",
                    "task_id": task_id,
                    "reason": reason,
                    "authority": authority.name,
                },
            )

            return action

    def reallocate_agent_capacity(
        self,
        from_agent_id: str,
        to_agent_id: str,
        capacity: int,
        reason: str,
        initiated_by: str,
        authority: AuthorityLevel = AuthorityLevel.GUARDIAN,
        manual: bool = False,
        project_id: Optional[str] = None,
    ) -> Optional[GuardianAction]:
        """Reallocate capacity from one agent to another.

        Typically used to steal resources from low-priority work
        to handle critical failures.

        Args:
            from_agent_id: Source agent to take capacity from
            to_agent_id: Target agent to give capacity to
            capacity: Amount of capacity to transfer
            reason: Explanation for reallocation
            initiated_by: Agent/user ID initiating the action
            authority: Authority level (must be GUARDIAN or higher)
            manual: If True, bypass auto-steering check (manual intervention)
            project_id: Optional project ID for settings lookup

        Returns:
            GuardianAction audit record if successful, None if agents not found

        Raises:
            PermissionError: If authority level insufficient
            ValueError: If capacity invalid or insufficient
        """
        if authority < AuthorityLevel.GUARDIAN:
            raise PermissionError(
                f"Capacity reallocation requires GUARDIAN authority (level {AuthorityLevel.GUARDIAN}), "
                f"but got {authority.name} (level {authority})"
            )

        if capacity <= 0:
            raise ValueError(f"Capacity must be positive, got {capacity}")

        target_entity = f"{from_agent_id}→{to_agent_id}"

        # Check auto-steering setting (unless this is a manual intervention)
        if not manual:
            auto_steering, settings_checked = self._check_auto_steering_enabled(
                project_id, "reallocate_capacity", target_entity
            )
            if settings_checked and not auto_steering:
                return self._log_intervention_skipped(
                    action_type="reallocate_capacity",
                    target_entity=target_entity,
                    reason=reason,
                    initiated_by=initiated_by,
                    authority=authority,
                    project_id=project_id,
                )

        with self.db.get_session() as session:
            from_agent = session.get(Agent, from_agent_id)
            to_agent = session.get(Agent, to_agent_id)

            if not from_agent or not to_agent:
                return None

            if from_agent.capacity < capacity:
                raise ValueError(
                    f"Agent {from_agent_id} has insufficient capacity "
                    f"(has {from_agent.capacity}, requested {capacity})"
                )

            # Record before state
            before_state = {
                "from_agent": {
                    "id": from_agent_id,
                    "capacity": from_agent.capacity,
                    "status": from_agent.status,
                },
                "to_agent": {
                    "id": to_agent_id,
                    "capacity": to_agent.capacity,
                    "status": to_agent.status,
                },
            }

            # Perform reallocation
            from_agent.capacity -= capacity
            to_agent.capacity += capacity

            # Create audit record
            action = GuardianAction(
                action_type="reallocate_capacity",
                target_entity=target_entity,
                authority_level=authority,
                reason=reason,
                initiated_by=initiated_by,
                executed_at=utc_now(),
                audit_log={
                    "before": before_state,
                    "after": {
                        "from_agent": {
                            "id": from_agent_id,
                            "capacity": from_agent.capacity,
                        },
                        "to_agent": {
                            "id": to_agent_id,
                            "capacity": to_agent.capacity,
                        },
                    },
                    "capacity_transferred": capacity,
                    "auto_steering_enabled": True,
                    "executed": True,
                    "manual": manual,
                    "project_id": project_id,
                },
            )
            session.add(action)
            session.commit()
            session.refresh(action)
            session.expunge(action)

            # Publish event
            self._publish_event(
                "guardian.resource.reallocated",
                entity_id=action.id,
                payload={
                    "from_agent_id": from_agent_id,
                    "to_agent_id": to_agent_id,
                    "capacity": capacity,
                    "reason": reason,
                },
            )

            return action

    def override_task_priority(
        self,
        task_id: str,
        new_priority: str,
        reason: str,
        initiated_by: str,
        authority: AuthorityLevel = AuthorityLevel.GUARDIAN,
        manual: bool = False,
    ) -> Optional[GuardianAction]:
        """Override task priority in the queue.

        Used to boost critical tasks ahead of normal queue order.

        Args:
            task_id: ID of task to boost
            new_priority: New priority level (CRITICAL, HIGH, MEDIUM, LOW)
            reason: Explanation for priority override
            initiated_by: Agent/user ID initiating the action
            authority: Authority level (must be GUARDIAN or higher)
            manual: If True, bypass auto-steering check (manual intervention)

        Returns:
            GuardianAction audit record if successful, None if task not found

        Raises:
            PermissionError: If authority level insufficient
            ValueError: If priority value invalid
        """
        if authority < AuthorityLevel.GUARDIAN:
            raise PermissionError(
                f"Priority override requires GUARDIAN authority (level {AuthorityLevel.GUARDIAN}), "
                f"but got {authority.name} (level {authority})"
            )

        valid_priorities = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        if new_priority not in valid_priorities:
            raise ValueError(
                f"Invalid priority '{new_priority}'. Must be one of {valid_priorities}"
            )

        # Get project_id for settings check
        project_id = self._get_project_id_for_task(task_id)

        # Check auto-steering setting (unless this is a manual intervention)
        if not manual:
            auto_steering, settings_checked = self._check_auto_steering_enabled(
                project_id, "override_priority", task_id
            )
            if settings_checked and not auto_steering:
                return self._log_intervention_skipped(
                    action_type="override_priority",
                    target_entity=task_id,
                    reason=reason,
                    initiated_by=initiated_by,
                    authority=authority,
                    project_id=project_id,
                )

        with self.db.get_session() as session:
            task = session.get(Task, task_id)
            if not task:
                return None

            # Record before state
            old_priority = task.priority
            before_state = {
                "priority": old_priority,
                "status": task.status,
            }

            # Override priority
            task.priority = new_priority

            # Create audit record
            action = GuardianAction(
                action_type="override_priority",
                target_entity=task_id,
                authority_level=authority,
                reason=reason,
                initiated_by=initiated_by,
                executed_at=utc_now(),
                audit_log={
                    "before": before_state,
                    "after": {"priority": new_priority},
                    "old_priority": old_priority,
                    "new_priority": new_priority,
                    "auto_steering_enabled": True,
                    "executed": True,
                    "manual": manual,
                    "project_id": project_id,
                },
            )
            session.add(action)
            session.commit()
            session.refresh(action)
            session.expunge(action)

            # Publish event
            self._publish_event(
                "guardian.intervention.completed",
                entity_id=action.id,
                payload={
                    "action_type": "override_priority",
                    "task_id": task_id,
                    "old_priority": old_priority,
                    "new_priority": new_priority,
                    "reason": reason,
                },
            )

            return action

    # -------------------------------------------------------------------------
    # Rollback and Audit
    # -------------------------------------------------------------------------

    def revert_intervention(
        self,
        action_id: str,
        reason: str,
        initiated_by: str,
    ) -> bool:
        """Revert a previous guardian intervention.
        
        Args:
            action_id: ID of the GuardianAction to revert
            reason: Explanation for reversion
            initiated_by: Agent/user ID initiating the reversion
            
        Returns:
            True if reverted successfully, False if action not found or already reverted
        """
        with self.db.get_session() as session:
            action = session.get(GuardianAction, action_id)
            if not action or action.reverted_at:
                return False

            # Mark as reverted
            action.reverted_at = utc_now()
            if action.audit_log:
                action.audit_log["revert_reason"] = reason
                action.audit_log["reverted_by"] = initiated_by
            else:
                action.audit_log = {
                    "revert_reason": reason,
                    "reverted_by": initiated_by,
                }
            
            # Flag the JSONB field as modified so SQLAlchemy detects the change
            attributes.flag_modified(action, "audit_log")

            session.commit()

            # Publish revert event
            self._publish_event(
                "guardian.intervention.reverted",
                entity_id=action_id,
                payload={
                    "action_type": action.action_type,
                    "target_entity": action.target_entity,
                    "reason": reason,
                    "reverted_by": initiated_by,
                },
            )

            return True

    def get_actions(
        self,
        limit: int = 100,
        action_type: Optional[str] = None,
        target_entity: Optional[str] = None,
    ) -> List[GuardianAction]:
        """Get guardian action audit trail.
        
        Args:
            limit: Maximum number of actions to return
            action_type: Optional filter by action type
            target_entity: Optional filter by target entity
            
        Returns:
            List of GuardianAction records, most recent first
        """
        with self.db.get_session() as session:
            query = session.query(GuardianAction)

            if action_type:
                query = query.filter(GuardianAction.action_type == action_type)
            if target_entity:
                query = query.filter(GuardianAction.target_entity == target_entity)

            actions = (
                query.order_by(desc(GuardianAction.created_at))
                .limit(limit)
                .all()
            )

            # Expunge for use outside session
            for action in actions:
                session.expunge(action)

            return actions

    def get_action(self, action_id: str) -> Optional[GuardianAction]:
        """Get a specific guardian action by ID.
        
        Args:
            action_id: ID of the guardian action
            
        Returns:
            GuardianAction if found, None otherwise
        """
        with self.db.get_session() as session:
            action = session.get(GuardianAction, action_id)
            if action:
                session.expunge(action)
            return action

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _publish_event(
        self,
        event_type: str,
        entity_id: str,
        payload: dict,
    ) -> None:
        """Publish guardian intervention event."""
        if not self.event_bus:
            return

        event = SystemEvent(
            event_type=event_type,
            entity_type="guardian_action",
            entity_id=entity_id,
            payload=payload,
        )
        self.event_bus.publish(event)

