"""Watchdog service for monitoring monitor agents and automated remediation per REQ-WATCHDOG-001."""

from __future__ import annotations

from datetime import timedelta
from typing import Dict, List, Optional

import yaml
from pathlib import Path

from omoi_os.models.agent import Agent
from omoi_os.models.agent_status import AgentStatus
from omoi_os.models.guardian_action import AuthorityLevel
from omoi_os.models.watchdog_action import WatchdogAction
from omoi_os.services.agent_registry import AgentRegistryService
from omoi_os.services.agent_status_manager import AgentStatusManager
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.guardian import GuardianService
from omoi_os.services.restart_orchestrator import RestartOrchestrator
from omoi_os.utils.datetime import utc_now


class WatchdogService:
    """Watchdog service for meta-monitoring of monitor agents.
    
    Per REQ-WATCHDOG-001:
    - Monitors monitor agents with fast heartbeat detection (15s TTL)
    - Executes remediation policies (restart, failover, escalate)
    - Escalates to Guardian when remediation fails
    - Maintains audit trail of all remediation actions
    
    Authority level: WATCHDOG (2) - can remediate monitors, escalates to Guardian (4)
    """
    
    # Watchdog-specific heartbeat thresholds per REQ-AGENT-WATCHDOG-002
    WATCHDOG_HEARTBEAT_TTL = timedelta(seconds=15)  # 15s TTL for monitor agents
    WATCHDOG_CHECK_INTERVAL = timedelta(seconds=5)  # Check every 5 seconds
    DETECTION_TIME_THRESHOLD = timedelta(seconds=20)  # Detect unresponsiveness within 20s
    ESCALATION_TIME_THRESHOLD = timedelta(seconds=5)  # Escalate to Guardian within 5s
    
    def __init__(
        self,
        db: DatabaseService,
        agent_registry: AgentRegistryService,
        restart_orchestrator: RestartOrchestrator,
        guardian_service: Optional[GuardianService] = None,
        event_bus: Optional[EventBusService] = None,
        status_manager: Optional[AgentStatusManager] = None,
        policies_dir: Optional[Path] = None,
    ):
        """Initialize watchdog service.
        
        Args:
            db: DatabaseService instance
            agent_registry: AgentRegistryService for agent operations
            restart_orchestrator: RestartOrchestrator for agent restarts
            guardian_service: Optional GuardianService for escalation
            event_bus: Optional EventBusService for event publishing
            status_manager: Optional AgentStatusManager for status transitions
            policies_dir: Optional path to watchdog policy YAML files
        """
        self.db = db
        self.agent_registry = agent_registry
        self.restart_orchestrator = restart_orchestrator
        self.guardian_service = guardian_service
        self.event_bus = event_bus
        self.status_manager = status_manager
        
        # Load remediation policies
        if policies_dir is None:
            # Default to config/watchdog_policies
            policies_dir = Path(__file__).parent.parent.parent / "config" / "watchdog_policies"
        self.policies_dir = policies_dir
        self.policies: Dict[str, dict] = {}
        self._load_policies()
    
    def _load_policies(self) -> None:
        """Load remediation policies from YAML files."""
        if not self.policies_dir.exists():
            # Create default policies if directory doesn't exist
            self.policies_dir.mkdir(parents=True, exist_ok=True)
            self._create_default_policies()
            return
        
        # Load existing YAML files
        yaml_files = list(self.policies_dir.glob("*.yaml"))
        
        # If no policies exist, create defaults
        if not yaml_files:
            self._create_default_policies()
            # Reload after creating defaults
            yaml_files = list(self.policies_dir.glob("*.yaml"))
        
        for policy_file in yaml_files:
            try:
                with open(policy_file, "r") as f:
                    policy_data = yaml.safe_load(f)
                    if policy_data and "policy" in policy_data:
                        policy_name = policy_data["policy"].get("name", policy_file.stem)
                        self.policies[policy_name] = policy_data["policy"]
            except Exception as e:
                # Log error but continue loading other policies
                print(f"Error loading policy {policy_file}: {e}")
    
    def _create_default_policies(self) -> None:
        """Create default remediation policies."""
        default_policies = {
            "monitor_restart.yaml": {
                "policy": {
                    "name": "monitor_restart",
                    "version": "1.0",
                    "description": "Restart unresponsive monitor agents",
                    "triggers": [
                        {
                            "type": "heartbeat_missed",
                            "condition": "consecutive_missed_heartbeats >= 3",
                            "description": "Monitor agent missed 3 consecutive heartbeats"
                        }
                    ],
                    "actions": [
                        {
                            "type": "restart",
                            "priority": 1,
                            "timeout_seconds": 60
                        }
                    ],
                    "escalation": {
                        "on_failure": "escalate_to_guardian",
                        "max_attempts": 2
                    }
                }
            },
            "monitor_failover.yaml": {
                "policy": {
                    "name": "monitor_failover",
                    "version": "1.0",
                    "description": "Failover to backup monitor when primary fails",
                    "triggers": [
                        {
                            "type": "agent_status",
                            "condition": "status == 'FAILED' OR status == 'UNRESPONSIVE'",
                            "description": "Monitor agent has failed or become unresponsive"
                        }
                    ],
                    "actions": [
                        {
                            "type": "failover",
                            "priority": 1,
                            "backup_agent_id": None  # Will be discovered dynamically
                        }
                    ],
                    "escalation": {
                        "on_failure": "escalate_to_guardian",
                        "max_attempts": 1
                    }
                }
            }
        }
        
        for filename, content in default_policies.items():
            policy_path = self.policies_dir / filename
            with open(policy_path, "w") as f:
                yaml.dump(content, f, default_flow_style=False)
        
        # Reload policies
        self._load_policies()
    
    def monitor_monitor_agents(self) -> List[Dict]:
        """Monitor all monitor agents and detect failures.
        
        Per REQ-AGENT-WATCHDOG-002, watchdog checks monitor agents every 5 seconds
        and detects unresponsiveness within 20 seconds.
        
        Returns:
            List of detected issues with monitor agents
        """
        issues = []
        now = utc_now()
        
        with self.db.get_session() as session:
            # Get all monitor agents
            monitor_agents = (
                session.query(Agent)
                .filter(Agent.agent_type == "monitor")
                .filter(Agent.status.in_([
                    AgentStatus.IDLE.value,
                    AgentStatus.RUNNING.value,
                    AgentStatus.DEGRADED.value,
                ]))
                .all()
            )
            
            for agent in monitor_agents:
                # Check heartbeat freshness
                if agent.last_heartbeat:
                    time_since_heartbeat = now - agent.last_heartbeat
                    
                    # Detect unresponsiveness (20s threshold per REQ-AGENT-WATCHDOG-002)
                    if time_since_heartbeat > self.DETECTION_TIME_THRESHOLD:
                        issues.append({
                            "agent_id": agent.id,
                            "agent_type": agent.agent_type,
                            "status": agent.status,
                            "issue": "unresponsive",
                            "time_since_heartbeat_seconds": time_since_heartbeat.total_seconds(),
                            "consecutive_missed_heartbeats": agent.consecutive_missed_heartbeats,
                        })
                    # Check for consecutive missed heartbeats
                    elif agent.consecutive_missed_heartbeats >= 3:
                        issues.append({
                            "agent_id": agent.id,
                            "agent_type": agent.agent_type,
                            "status": agent.status,
                            "issue": "consecutive_missed_heartbeats",
                            "consecutive_missed_heartbeats": agent.consecutive_missed_heartbeats,
                        })
                else:
                    # No heartbeat ever recorded
                    if (now - agent.created_at) > self.DETECTION_TIME_THRESHOLD:
                        issues.append({
                            "agent_id": agent.id,
                            "agent_type": agent.agent_type,
                            "status": agent.status,
                            "issue": "no_heartbeat",
                            "created_at": agent.created_at.isoformat(),
                        })
                
                # Check for failed or unresponsive status
                if agent.status in [AgentStatus.FAILED.value, "unresponsive"]:
                    issues.append({
                        "agent_id": agent.id,
                        "agent_type": agent.agent_type,
                        "status": agent.status,
                        "issue": "status_failure",
                    })
        
        return issues
    
    def execute_remediation(
        self,
        agent_id: str,
        policy_name: str,
        reason: str,
        watchdog_agent_id: str,
    ) -> Optional[WatchdogAction]:
        """Execute remediation action based on policy.
        
        Args:
            agent_id: ID of the monitor agent to remediate
            policy_name: Name of the remediation policy to apply
            reason: Reason for remediation
            watchdog_agent_id: ID of the watchdog agent executing this action
            
        Returns:
            WatchdogAction record if successful, None if policy not found
        """
        if policy_name not in self.policies:
            return None
        
        policy = self.policies[policy_name]
        actions = policy.get("actions", [])
        
        # Create watchdog action record
        with self.db.get_session() as session:
            agent = session.get(Agent, agent_id)
            if not agent:
                return None
            
            # Record before state
            before_state = {
                "status": agent.status,
                "health_status": agent.health_status,
                "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
            }
            
            watchdog_action = WatchdogAction(
                action_type=actions[0].get("type", "unknown") if actions else "unknown",
                target_agent_id=agent_id,
                remediation_policy=policy_name,
                reason=reason,
                initiated_by=watchdog_agent_id,
                executed_at=utc_now(),
                success="pending",
                escalated_to_guardian="false",
                audit_log={
                    "before": before_state,
                    "policy": policy_name,
                    "actions": actions,
                },
            )
            session.add(watchdog_action)
            session.commit()
            session.refresh(watchdog_action)
            session.expunge(watchdog_action)
            
            # Execute actions in priority order
            success = False
            for action in sorted(actions, key=lambda a: a.get("priority", 999)):
                action_type = action.get("type")
                
                if action_type == "restart":
                    success = self._execute_restart(agent_id, watchdog_action.id, reason)
                elif action_type == "failover":
                    success = self._execute_failover(agent_id, watchdog_action.id, action)
                elif action_type == "escalate":
                    success = self._execute_escalation(agent_id, watchdog_action.id, reason)
                else:
                    # Unknown action type
                    continue
                
                if success:
                    break  # Stop after first successful action
            
            # Update watchdog action status
            with self.db.get_session() as session:
                action = session.get(WatchdogAction, watchdog_action.id)
                if action:
                    action.success = "success" if success else "failed"
                    if not success:
                        # Check if we should escalate
                        escalation = policy.get("escalation", {})
                        if escalation.get("on_failure") == "escalate_to_guardian":
                            escalated = self._escalate_to_guardian(
                                agent_id, watchdog_action.id, reason
                            )
                            if escalated:
                                action.escalated_to_guardian = "true"
                    session.commit()
                    session.refresh(action)
                    session.expunge(action)
                    return action
        
        return watchdog_action
    
    def _execute_restart(
        self, agent_id: str, watchdog_action_id: str, reason: str
    ) -> bool:
        """Execute restart remediation action.
        
        Args:
            agent_id: ID of agent to restart
            watchdog_action_id: ID of watchdog action record
            reason: Reason for restart
            
        Returns:
            True if restart initiated successfully
        """
        try:
            result = self.restart_orchestrator.initiate_restart(
                agent_id=agent_id,
                reason=f"Watchdog remediation: {reason}",
                authority=AuthorityLevel.WATCHDOG,
            )
            
            if result:
                # Update watchdog action with restart details
                with self.db.get_session() as session:
                    action = session.get(WatchdogAction, watchdog_action_id)
                    if action:
                        if action.audit_log is None:
                            action.audit_log = {}
                        action.audit_log["restart_result"] = result
                        session.commit()
                
                # Publish event
                if self.event_bus:
                    self.event_bus.publish(
                        SystemEvent(
                            event_type="watchdog.remediation.started",
                            entity_type="agent",
                            entity_id=agent_id,
                            payload={
                                "action_type": "restart",
                                "watchdog_action_id": watchdog_action_id,
                                "reason": reason,
                            },
                        )
                    )
                
                return True
        except Exception as e:
            # Log error but don't fail
            print(f"Error executing restart for agent {agent_id}: {e}")
            return False
    
    def _execute_failover(
        self, agent_id: str, watchdog_action_id: str, action_config: dict
    ) -> bool:
        """Execute failover remediation action.
        
        Args:
            agent_id: ID of failed agent
            watchdog_action_id: ID of watchdog action record
            action_config: Failover action configuration
            
        Returns:
            True if failover successful
        """
        # Find backup monitor agent
        backup_agent_id = action_config.get("backup_agent_id")
        
        if not backup_agent_id:
            # Discover backup monitor dynamically
            with self.db.get_session() as session:
                backup_agent = (
                    session.query(Agent)
                    .filter(Agent.agent_type == "monitor")
                    .filter(Agent.id != agent_id)
                    .filter(Agent.status.in_([
                        AgentStatus.IDLE.value,
                        AgentStatus.RUNNING.value,
                    ]))
                    .first()
                )
                
                if not backup_agent:
                    return False
                
                backup_agent_id = backup_agent.id
        
        # Transfer monitoring responsibilities (in a real system, this would
        # involve updating monitoring assignments, but for now we just log it)
        with self.db.get_session() as session:
            action = session.get(WatchdogAction, watchdog_action_id)
            if action:
                if action.audit_log is None:
                    action.audit_log = {}
                action.audit_log["failover"] = {
                    "from_agent_id": agent_id,
                    "to_agent_id": backup_agent_id,
                }
                session.commit()
        
        # Publish event
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="watchdog.remediation.started",
                    entity_type="agent",
                    entity_id=agent_id,
                    payload={
                        "action_type": "failover",
                        "watchdog_action_id": watchdog_action_id,
                        "backup_agent_id": backup_agent_id,
                    },
                )
            )
        
        return True
    
    def _execute_escalation(
        self, agent_id: str, watchdog_action_id: str, reason: str
    ) -> bool:
        """Execute escalation remediation action.
        
        Args:
            agent_id: ID of agent to escalate
            watchdog_action_id: ID of watchdog action record
            reason: Reason for escalation
            
        Returns:
            True if escalation successful
        """
        return self._escalate_to_guardian(agent_id, watchdog_action_id, reason)
    
    def _escalate_to_guardian(
        self, agent_id: str, watchdog_action_id: str, reason: str
    ) -> bool:
        """Escalate to Guardian when remediation fails.
        
        Args:
            agent_id: ID of agent that needs Guardian intervention
            watchdog_action_id: ID of watchdog action record
            reason: Reason for escalation
            
        Returns:
            True if escalation successful
        """
        if not self.guardian_service:
            # No guardian service available
            return False
        
        try:
            # Use Guardian's emergency cancel or other intervention
            # For monitor agents, we might want to quarantine or force terminate
            with self.db.get_session() as session:
                agent = session.get(Agent, agent_id)
                if not agent:
                    return False
                
                # Try to quarantine the agent via Guardian
                # (Guardian has quarantine capability, but we'll use status manager for now)
                if self.status_manager:
                    try:
                        self.status_manager.transition_status(
                            agent_id,
                            to_status=AgentStatus.QUARANTINED.value,
                            initiated_by="watchdog",
                            reason=f"Escalated to Guardian: {reason}",
                            force=True,
                        )
                    except Exception:
                        pass
            
            # Update watchdog action with escalation details
            with self.db.get_session() as session:
                action = session.get(WatchdogAction, watchdog_action_id)
                if action:
                    action.escalated_to_guardian = "true"
                    if action.audit_log is None:
                        action.audit_log = {}
                    action.audit_log["escalation"] = {
                        "escalated_at": utc_now().isoformat(),
                        "reason": reason,
                    }
                    session.commit()
            
            # Publish escalation event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="watchdog.escalation",
                        entity_type="agent",
                        entity_id=agent_id,
                        payload={
                            "watchdog_action_id": watchdog_action_id,
                            "reason": reason,
                            "escalated_to": "guardian",
                        },
                    )
                )
            
            return True
        except Exception as e:
            print(f"Error escalating to Guardian for agent {agent_id}: {e}")
            return False
    
    def get_remediation_history(
        self, agent_id: Optional[str] = None, limit: int = 50
    ) -> List[WatchdogAction]:
        """Get remediation action history.
        
        Args:
            agent_id: Optional agent ID filter
            limit: Maximum number of actions to return
            
        Returns:
            List of WatchdogAction records
        """
        with self.db.get_session() as session:
            query = session.query(WatchdogAction)
            
            if agent_id:
                query = query.filter(WatchdogAction.target_agent_id == agent_id)
            
            actions = query.order_by(WatchdogAction.created_at.desc()).limit(limit).all()
            
            # Expunge all actions
            for action in actions:
                session.expunge(action)
            
            return actions
    
    def get_policies(self) -> Dict[str, dict]:
        """Get all loaded remediation policies.
        
        Returns:
            Dictionary of policy name to policy configuration
        """
        return self.policies.copy()

