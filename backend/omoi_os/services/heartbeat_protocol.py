"""Enhanced heartbeat protocol service with sequence tracking, gap detection, and escalation."""

import hashlib
import json
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select

from omoi_os.models.agent import Agent
from omoi_os.models.agent_status import AgentStatus
from omoi_os.models.heartbeat_message import HeartbeatAck, HeartbeatMessage
from omoi_os.services.agent_status_manager import AgentStatusManager
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now


class HeartbeatProtocolService:
    """
    Enhanced heartbeat protocol service per REQ-ALM-002, REQ-FT-HB-001 to REQ-FT-HB-004.

    Features:
    - Bidirectional heartbeat protocol with acknowledgments
    - Sequence number tracking and gap detection
    - Checksum validation for message integrity
    - State-based TTL thresholds (30s IDLE, 15s RUNNING)
    - Escalation ladder (1→warn, 2→DEGRADED, 3→UNRESPONSIVE)
    """

    # TTL thresholds per REQ-FT-HB-002
    TTL_THRESHOLDS = {
        AgentStatus.IDLE.value.lower(): 30,  # IDLE agents: 30s
        AgentStatus.RUNNING.value.lower(): 15,  # RUNNING agents: 15s
        "monitor": 15,  # MONITOR agents: 15s
        "watchdog": 15,  # WATCHDOG agents: 15s
        "guardian": 60,  # GUARDIAN agents: 60s (less frequent)
        "idle": 30,  # Legacy lowercase support
        "running": 15,  # Legacy lowercase support
    }

    # Escalation thresholds per REQ-FT-AR-001
    ESCALATION_THRESHOLDS = {
        1: "warn",  # 1 missed → warn
        2: "degraded",  # 2 missed → DEGRADED
        3: "unresponsive",  # 3 missed → UNRESPONSIVE
    }

    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
        status_manager: Optional[AgentStatusManager] = None,
    ):
        """
        Initialize HeartbeatProtocolService.

        Args:
            db: Database service instance
            event_bus: Optional event bus for publishing heartbeat events
            status_manager: Optional status manager for state machine enforcement
        """
        self.db = db
        self.event_bus = event_bus
        self.status_manager = status_manager

    def _calculate_checksum(self, payload: dict) -> str:
        """
        Calculate SHA256 checksum of heartbeat payload per REQ-ALM-002.

        Args:
            payload: Heartbeat message payload (without checksum)

        Returns:
            SHA256 checksum hex string
        """
        # Create deterministic JSON string (sorted keys)
        payload_str = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(payload_str.encode()).hexdigest()

    def _validate_checksum(self, message: HeartbeatMessage) -> bool:
        """
        Validate heartbeat message checksum per REQ-ALM-002.

        Args:
            message: Heartbeat message to validate

        Returns:
            True if checksum is valid, False otherwise
        """
        # Reconstruct payload without checksum
        payload = {
            "agent_id": message.agent_id,
            "timestamp": message.timestamp.isoformat(),
            "sequence_number": message.sequence_number,
            "status": message.status,
            "current_task_id": message.current_task_id,
            "health_metrics": message.health_metrics,
        }
        expected_checksum = self._calculate_checksum(payload)
        return expected_checksum == message.checksum

    def _get_ttl_threshold(self, status: str, agent_type: str) -> int:
        """
        Get TTL threshold based on agent status and type per REQ-FT-HB-002.

        Args:
            status: Agent status (idle, running, etc.)
            agent_type: Agent type (worker, monitor, watchdog, guardian)

        Returns:
            TTL threshold in seconds
        """
        # Use status-based threshold if available
        if status.lower() in self.TTL_THRESHOLDS:
            return self.TTL_THRESHOLDS[status.lower()]

        # Fall back to agent type
        if agent_type.lower() in self.TTL_THRESHOLDS:
            return self.TTL_THRESHOLDS[agent_type.lower()]

        # Default to IDLE threshold
        return self.TTL_THRESHOLDS["idle"]

    def receive_heartbeat(self, message: HeartbeatMessage) -> HeartbeatAck:
        """
        Receive and process heartbeat message per REQ-FT-HB-001.

        Steps:
        1. Validate message integrity (checksum)
        2. Check sequence number for gaps
        3. Update agent's heartbeat state
        4. Process escalation ladder if needed
        5. Return acknowledgment

        Args:
            message: Heartbeat message from agent

        Returns:
            HeartbeatAck with acknowledgment details

        Raises:
            ValueError: If checksum validation fails or agent not found
        """
        # Validate checksum
        if not self._validate_checksum(message):
            return HeartbeatAck(
                agent_id=message.agent_id,
                sequence_number=message.sequence_number,
                received=False,
                message="Checksum validation failed",
            )

        with self.db.get_session() as session:
            agent = session.query(Agent).filter(Agent.id == message.agent_id).first()
            if not agent:
                return HeartbeatAck(
                    agent_id=message.agent_id,
                    sequence_number=message.sequence_number,
                    received=False,
                    message="Agent not found",
                )

            # Check sequence number for gaps (REQ-FT-HB-003)
            gaps = self._detect_sequence_gaps(agent, message.sequence_number)

            # Update agent heartbeat state
            agent.last_heartbeat = message.timestamp
            agent.sequence_number = message.sequence_number
            agent.last_expected_sequence = message.sequence_number + 1

            # Reset consecutive missed heartbeats if heartbeat received
            if agent.consecutive_missed_heartbeats > 0:
                agent.consecutive_missed_heartbeats = 0

            # Update status if was stale (legacy status should be IDLE)
            # Use status manager if available
            if agent.status in ["stale", "STALE"]:
                if self.status_manager:
                    try:
                        self.status_manager.transition_status(
                            agent.id,
                            to_status=AgentStatus.IDLE.value,
                            initiated_by="heartbeat_service",
                            reason="Heartbeat received, recovering from stale state",
                        )
                    except Exception:
                        # If transition fails, update directly as fallback
                        agent.status = AgentStatus.IDLE.value
                else:
                    agent.status = AgentStatus.IDLE.value
            agent.health_status = "healthy"

            # Publish heartbeat received event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="HEARTBEAT_RECEIVED",
                        entity_type="agent",
                        entity_id=message.agent_id,
                        payload={
                            "sequence_number": message.sequence_number,
                            "status": message.status,
                            "has_gaps": len(gaps) > 0,
                            "health_metrics": message.health_metrics,
                        },
                    )
                )

            session.commit()

            # Build acknowledgment message
            ack_message = None
            if gaps:
                ack_message = f"Sequence gaps detected: {[g['expected'] for g in gaps]}"

            return HeartbeatAck(
                agent_id=message.agent_id,
                sequence_number=message.sequence_number,
                received=True,
                message=ack_message,
            )

    def _detect_sequence_gaps(
        self, agent: Agent, received_sequence: int
    ) -> List[Dict[str, int]]:
        """
        Detect sequence number gaps per REQ-FT-HB-003.

        Args:
            agent: Agent object
            received_sequence: Received sequence number

        Returns:
            List of gap dictionaries with 'expected' and 'received' keys
        """
        gaps = []
        expected_sequence = agent.last_expected_sequence

        # If this is the first heartbeat, no gaps possible
        if expected_sequence == 0:
            return gaps

        # Check for gaps
        if received_sequence > expected_sequence:
            # Gap detected - missing sequences between expected and received
            for missing_seq in range(expected_sequence, received_sequence):
                gaps.append({"expected": missing_seq, "received": received_sequence})

        return gaps

    def check_missed_heartbeats(self) -> List[Tuple[dict, int]]:
        """
        Check for agents with missed heartbeats and apply escalation ladder per REQ-FT-AR-001.

        Returns:
            List of tuples (agent_data, missed_count) where agent_data is a dict with agent attributes
        """
        now = utc_now()
        agents_with_missed = []

        with self.db.get_session() as session:
            agents = (
                session.query(Agent)
                .filter(
                    Agent.status.in_(
                        [
                            AgentStatus.IDLE.value,
                            AgentStatus.RUNNING.value,
                            AgentStatus.DEGRADED.value,
                        ]
                    )
                )
                .all()
            )

            for agent in agents:
                if not agent.last_heartbeat:
                    # Never sent a heartbeat - treat as missed
                    agent.consecutive_missed_heartbeats += 1
                    agents_with_missed.append(
                        (agent, agent.consecutive_missed_heartbeats)
                    )
                else:
                    # Get TTL threshold based on status
                    ttl_threshold = self._get_ttl_threshold(
                        agent.status, agent.agent_type
                    )
                    time_since_heartbeat = (now - agent.last_heartbeat).total_seconds()

                    if time_since_heartbeat > ttl_threshold:
                        # Missed heartbeat detected
                        agent.consecutive_missed_heartbeats += 1
                        agents_with_missed.append(
                            (agent, agent.consecutive_missed_heartbeats)
                        )

                # Apply escalation ladder
                missed_count = agent.consecutive_missed_heartbeats
                if missed_count >= 1:
                    self._apply_escalation(agent, missed_count)

            session.commit()

            # Extract agent IDs and critical attributes before expunging (to avoid detached instance errors)
            result = []
            for agent, missed_count in agents_with_missed:
                # Extract ID and other needed attributes while still attached to session
                agent_data = {
                    "id": agent.id,
                    "agent_type": agent.agent_type,
                    "status": agent.status,
                    "phase_id": agent.phase_id,
                    "capabilities": agent.capabilities,
                    "capacity": agent.capacity,
                }
                session.expunge(agent)
                result.append((agent_data, missed_count))

        return result

    def _apply_escalation(self, agent: Agent, missed_count: int) -> None:
        """
        Apply escalation ladder per REQ-FT-AR-001.

        Escalation steps:
        - 1 missed → warn (log warning, increase monitoring)
        - 2 consecutive missed → DEGRADED status
        - 3 consecutive missed → UNRESPONSIVE status

        Args:
            agent: Agent object
            missed_count: Number of consecutive missed heartbeats
        """
        if missed_count == 1:
            # 1 missed → warn
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="HEARTBEAT_MISSED",
                        entity_type="agent",
                        entity_id=agent.id,
                        payload={
                            "missed_count": missed_count,
                            "escalation_level": "warn",
                            "action": "Increased monitoring frequency",
                        },
                    )
                )
        elif missed_count == 2:
            # 2 consecutive missed → DEGRADED per REQ-ALM-004
            if agent.status != AgentStatus.DEGRADED.value:
                old_status = agent.status
                if self.status_manager:
                    try:
                        self.status_manager.transition_status(
                            agent.id,
                            to_status=AgentStatus.DEGRADED.value,
                            initiated_by="heartbeat_service",
                            reason=f"{missed_count} consecutive missed heartbeats",
                        )
                    except Exception:
                        # If transition fails, update directly as fallback
                        agent.status = AgentStatus.DEGRADED.value
                        agent.health_status = "degraded"
                else:
                    agent.status = AgentStatus.DEGRADED.value
                    agent.health_status = "degraded"
                    if self.event_bus:
                        self.event_bus.publish(
                            SystemEvent(
                                event_type="AGENT_STATUS_CHANGED",
                                entity_type="agent",
                                entity_id=agent.id,
                                payload={
                                    "old_status": old_status,
                                    "new_status": AgentStatus.DEGRADED.value,
                                    "reason": "2 consecutive missed heartbeats",
                                },
                            )
                        )

                # Publish heartbeat missed event (status manager already published status changed)
                if self.event_bus and not self.status_manager:
                    self.event_bus.publish(
                        SystemEvent(
                            event_type="HEARTBEAT_MISSED",
                            entity_type="agent",
                            entity_id=agent.id,
                            payload={
                                "missed_count": missed_count,
                                "escalation_level": "degraded",
                                "action": "Agent marked as DEGRADED",
                            },
                        )
                    )
        elif missed_count >= 3:
            # 3 consecutive missed → FAILED per REQ-ALM-004 (UNRESPONSIVE is not a valid status)
            # FAILED triggers restart protocol
            if agent.status != AgentStatus.FAILED.value:
                old_status = agent.status
                if self.status_manager:
                    try:
                        self.status_manager.transition_status(
                            agent.id,
                            to_status=AgentStatus.FAILED.value,
                            initiated_by="heartbeat_service",
                            reason=f"{missed_count} consecutive missed heartbeats - unresponsive",
                        )
                    except Exception:
                        # If transition fails, update directly as fallback
                        agent.status = AgentStatus.FAILED.value
                        agent.health_status = "unresponsive"
                else:
                    agent.status = AgentStatus.FAILED.value
                    agent.health_status = "unresponsive"
                    if self.event_bus:
                        self.event_bus.publish(
                            SystemEvent(
                                event_type="AGENT_STATUS_CHANGED",
                                entity_type="agent",
                                entity_id=agent.id,
                                payload={
                                    "old_status": old_status,
                                    "new_status": AgentStatus.FAILED.value,
                                    "reason": "3 consecutive missed heartbeats",
                                },
                            )
                        )

                # Publish heartbeat missed event (status manager already published status changed)
                if self.event_bus and not self.status_manager:
                    self.event_bus.publish(
                        SystemEvent(
                            event_type="HEARTBEAT_MISSED",
                            entity_type="agent",
                            entity_id=agent.id,
                            payload={
                                "missed_count": missed_count,
                                "escalation_level": "unresponsive",
                                "action": "Initiate restart protocol",
                            },
                        )
                    )

    def check_agent_health_with_ttl(self, agent_id: str) -> Dict[str, any]:
        """
        Check agent health using state-based TTL thresholds per REQ-FT-HB-002.

        Args:
            agent_id: ID of the agent to check

        Returns:
            Dictionary containing health information
        """
        with self.db.get_session() as session:
            agent = session.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                return {
                    "agent_id": agent_id,
                    "status": "not_found",
                    "healthy": False,
                    "last_heartbeat": None,
                    "health_status": "unknown",
                }

            now = utc_now()
            last_heartbeat = agent.last_heartbeat

            if not last_heartbeat:
                return {
                    "agent_id": agent_id,
                    "status": agent.status,
                    "healthy": False,
                    "last_heartbeat": None,
                    "time_since_last_heartbeat": None,
                    "message": "No heartbeat recorded",
                    "health_status": agent.health_status or "unknown",
                    "ttl_threshold": self._get_ttl_threshold(
                        agent.status, agent.agent_type
                    ),
                }

            # Get state-based TTL threshold
            ttl_threshold = self._get_ttl_threshold(agent.status, agent.agent_type)
            time_since_heartbeat = (now - last_heartbeat).total_seconds()
            is_stale = time_since_heartbeat > ttl_threshold

            return {
                "agent_id": agent_id,
                "status": agent.status,
                "healthy": not is_stale,
                "last_heartbeat": last_heartbeat.isoformat(),
                "time_since_last_heartbeat": time_since_heartbeat,
                "ttl_threshold": ttl_threshold,
                "agent_type": agent.agent_type,
                "phase_id": agent.phase_id,
                "health_status": agent.health_status,
                "sequence_number": agent.sequence_number,
                "consecutive_missed_heartbeats": agent.consecutive_missed_heartbeats,
            }

    # =========================================================================
    # ASYNC METHODS
    # =========================================================================

    async def receive_heartbeat_async(self, message: HeartbeatMessage) -> HeartbeatAck:
        """
        Async version: Receive and process heartbeat message.

        Per async_python_patterns.md, this uses non-blocking database operations
        for better event loop utilization.

        Args:
            message: Heartbeat message from agent

        Returns:
            HeartbeatAck with acknowledgment details
        """
        # Validate checksum (sync operation, no I/O)
        if not self._validate_checksum(message):
            return HeartbeatAck(
                agent_id=message.agent_id,
                sequence_number=message.sequence_number,
                received=False,
                message="Checksum validation failed",
            )

        async with self.db.get_async_session() as session:
            result = await session.execute(
                select(Agent).filter(Agent.id == message.agent_id)
            )
            agent = result.scalar_one_or_none()

            if not agent:
                return HeartbeatAck(
                    agent_id=message.agent_id,
                    sequence_number=message.sequence_number,
                    received=False,
                    message="Agent not found",
                )

            # Check sequence number for gaps (REQ-FT-HB-003)
            gaps = self._detect_sequence_gaps(agent, message.sequence_number)

            # Update agent heartbeat state
            agent.last_heartbeat = message.timestamp
            agent.sequence_number = message.sequence_number
            agent.last_expected_sequence = message.sequence_number + 1

            # Reset consecutive missed heartbeats if heartbeat received
            if agent.consecutive_missed_heartbeats > 0:
                agent.consecutive_missed_heartbeats = 0

            # Update status if was stale
            if agent.status in ["stale", "STALE"]:
                if self.status_manager:
                    try:
                        self.status_manager.transition_status(
                            agent.id,
                            to_status=AgentStatus.IDLE.value,
                            initiated_by="heartbeat_service",
                            reason="Heartbeat received, recovering from stale state",
                        )
                    except Exception:
                        agent.status = AgentStatus.IDLE.value
                else:
                    agent.status = AgentStatus.IDLE.value
            agent.health_status = "healthy"

            # Publish heartbeat received event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="HEARTBEAT_RECEIVED",
                        entity_type="agent",
                        entity_id=message.agent_id,
                        payload={
                            "sequence_number": message.sequence_number,
                            "status": message.status,
                            "has_gaps": len(gaps) > 0,
                            "health_metrics": message.health_metrics,
                        },
                    )
                )

            await session.commit()

            # Build acknowledgment message
            ack_message = None
            if gaps:
                ack_message = f"Sequence gaps detected: {[g['expected'] for g in gaps]}"

            return HeartbeatAck(
                agent_id=message.agent_id,
                sequence_number=message.sequence_number,
                received=True,
                message=ack_message,
            )

    async def check_agent_health_with_ttl_async(self, agent_id: str) -> Dict[str, any]:
        """
        Async version: Check agent health using state-based TTL thresholds.

        Args:
            agent_id: ID of the agent to check

        Returns:
            Dictionary containing health information
        """
        async with self.db.get_async_session() as session:
            result = await session.execute(select(Agent).filter(Agent.id == agent_id))
            agent = result.scalar_one_or_none()

            if not agent:
                return {
                    "agent_id": agent_id,
                    "status": "not_found",
                    "healthy": False,
                    "last_heartbeat": None,
                    "health_status": "unknown",
                }

            now = utc_now()
            last_heartbeat = agent.last_heartbeat

            if not last_heartbeat:
                return {
                    "agent_id": agent_id,
                    "status": agent.status,
                    "healthy": False,
                    "last_heartbeat": None,
                    "time_since_last_heartbeat": None,
                    "message": "No heartbeat recorded",
                    "health_status": agent.health_status or "unknown",
                    "ttl_threshold": self._get_ttl_threshold(
                        agent.status, agent.agent_type
                    ),
                }

            ttl_threshold = self._get_ttl_threshold(agent.status, agent.agent_type)
            time_since_heartbeat = (now - last_heartbeat).total_seconds()
            is_stale = time_since_heartbeat > ttl_threshold

            return {
                "agent_id": agent_id,
                "status": agent.status,
                "healthy": not is_stale,
                "last_heartbeat": last_heartbeat.isoformat(),
                "time_since_last_heartbeat": time_since_heartbeat,
                "ttl_threshold": ttl_threshold,
                "agent_type": agent.agent_type,
                "phase_id": agent.phase_id,
                "health_status": agent.health_status,
                "sequence_number": agent.sequence_number,
                "consecutive_missed_heartbeats": agent.consecutive_missed_heartbeats,
            }
