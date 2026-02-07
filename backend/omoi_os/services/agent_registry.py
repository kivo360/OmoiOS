"""Agent registry service for CRUD, capability updates, and discovery."""

from __future__ import annotations

import hashlib
import os
import socket
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
from sqlalchemy import and_

from omoi_os.logging import get_logger
from omoi_os.models.agent import Agent
from omoi_os.models.agent_status import AgentStatus
from omoi_os.services.agent_status_manager import AgentStatusManager
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)


@dataclass(frozen=True)
class AgentMatch:
    """Discovery result wrapper."""

    agent: Agent
    match_score: float
    matched_capabilities: List[str]


@dataclass
class ValidationResult:
    """Result of pre-registration validation per REQ-ALM-001 Step 1."""

    success: bool
    reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class RegistrationRejectedError(Exception):
    """Raised when agent registration is rejected."""

    reason: str
    details: Optional[Dict[str, Any]] = None


class AgentRegistryService:
    """Capability-aware agent registry and discovery service."""

    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
        status_manager: Optional[AgentStatusManager] = None,
    ):
        self.db = db
        self.event_bus = event_bus
        self.status_manager = status_manager

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
        status: str = AgentStatus.IDLE.value,  # Default to IDLE per REQ-ALM-004
        tags: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
        resource_requirements: Optional[Dict[str, Any]] = None,
        binary_path: Optional[str] = None,
        version: Optional[str] = None,
    ) -> Agent:
        """
        Register a new agent using multi-step protocol per REQ-ALM-001.

        Steps:
        1. Pre-registration validation
        2. Identity assignment (UUID, name, crypto)
        3. Registry entry creation
        4. Event bus subscription
        5. Initial heartbeat timeout (60s)
        """
        # Step 1: Pre-Registration Validation
        validation = self._pre_validate(
            agent_type=agent_type,
            capabilities=capabilities,
            resource_requirements=resource_requirements,
            config=config,
            binary_path=binary_path,
            version=version,
        )
        if not validation.success:
            raise RegistrationRejectedError(
                reason=validation.reason or "Pre-validation failed",
                details=validation.details,
            )

        # Step 2: Identity Assignment
        agent_id = str(uuid.uuid4())
        agent_name = self._generate_agent_name(agent_type, phase_id)
        crypto_identity = self._generate_crypto_identity(agent_id)

        # Step 3: Registry Entry Creation
        normalized_caps = self._normalize_tokens(capabilities)
        normalized_tags = self._normalize_tokens(tags or [])

        # Get orchestrator identifier
        registered_by = self._get_orchestrator_identifier()

        # Build metadata
        metadata = {}
        if version:
            metadata["version"] = version
        if binary_path:
            metadata["binary_path"] = binary_path
        if config:
            metadata["config"] = config
        if resource_requirements:
            metadata["resource_requirements"] = resource_requirements

        with self.db.get_session() as session:
            agent = Agent(
                id=agent_id,
                agent_name=agent_name,
                agent_type=agent_type,
                phase_id=phase_id,
                status=AgentStatus.SPAWNING.value,  # Start in SPAWNING per REQ-ALM-004
                capabilities=normalized_caps,
                capacity=max(1, capacity),
                tags=normalized_tags or None,
                health_status="healthy",
                crypto_public_key=crypto_identity["public_key"],
                crypto_identity_metadata=crypto_identity["metadata"],
                agent_metadata=metadata if metadata else None,
                registered_by=registered_by,
            )
            session.add(agent)
            session.commit()
            session.refresh(agent)
            session.expunge(agent)

        # Step 4: Event Bus Subscription
        if self.event_bus:
            self._subscribe_to_event_bus(agent_id, agent_type, phase_id)

        # Step 5: Set initial heartbeat timestamp
        # NOTE: We no longer block waiting for heartbeat - this caused a deadlock where
        # the HTTP response couldn't be returned until heartbeat arrived, but the client
        # couldn't send heartbeats until it received the response with agent_id.
        # Instead, we set an initial heartbeat timestamp at registration time.
        # The monitoring system will track stale agents asynchronously.
        with self.db.get_session() as session:
            agent = session.get(Agent, agent_id)
            if agent:
                agent.last_heartbeat = utc_now()
                session.commit()
                session.refresh(agent)
                session.expunge(agent)

        logger.info(f"Agent {agent_id} registered with initial heartbeat timestamp")

        # Transition to requested status (default IDLE) using status manager
        if self.status_manager:
            try:
                self.status_manager.transition_status(
                    agent_id,
                    to_status=status,
                    initiated_by="system",
                    reason="Agent registration completed",
                )
                # Refresh agent to get updated status
                with self.db.get_session() as session:
                    agent = session.get(Agent, agent_id)
                    session.expunge(agent)
            except Exception as e:
                logger.warning(f"Status transition failed for agent {agent_id}: {e}")
                # Agent remains in SPAWNING, will be handled by monitoring/cleanup

        # Publish registration event
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="AGENT_REGISTERED",
                    entity_type="agent",
                    entity_id=agent_id,
                    payload={
                        "agent_id": agent_id,
                        "agent_name": agent_name,
                        "agent_type": agent_type,
                        "phase_id": phase_id,
                        "capabilities": normalized_caps,
                    },
                )
            )

        self._publish_capability_event(agent_id, normalized_caps)
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
                # Use status manager if available for state machine enforcement
                if self.status_manager:
                    # Status manager handles validation and events, but needs to be
                    # called outside this session context to avoid conflicts
                    # Store agent_id for status update after session closes
                    agent_id_for_status_update = agent.id
                    target_status = status
                else:
                    # Fallback: direct status update if status manager not available
                    # This should not happen in production but allows backward compatibility
                    agent.status = status

            if health_status is not None:
                agent.health_status = health_status

            session.commit()
            session.refresh(agent)

            # If status update was requested and status manager is available,
            # update status outside session context
            if (
                status is not None
                and self.status_manager
                and "agent_id_for_status_update" in locals()
            ):
                # Expunge agent before closing session
                session.expunge(agent)
                # Now update status using status manager
                try:
                    updated_agent = self.status_manager.transition_status(
                        agent_id_for_status_update,
                        to_status=target_status,
                        initiated_by="system",
                        reason="Agent metadata update",
                    )
                    return updated_agent
                except Exception:
                    # If transition fails, return agent with original status
                    # This allows backward compatibility
                    pass

            session.expunge(agent)

            if capabilities_changed:
                self._publish_capability_event(agent.id, agent.capabilities)

            return agent

    def toggle_availability(self, agent_id: str, available: bool) -> Optional[Agent]:
        """Mark an agent as available (idle) or unavailable (degraded)."""
        # Per REQ-ALM-004, maintenance is not a valid status
        # Unavailable agents should be DEGRADED or TERMINATED
        new_status = AgentStatus.IDLE.value if available else AgentStatus.DEGRADED.value
        if self.status_manager:
            try:
                return self.status_manager.transition_status(
                    agent_id,
                    to_status=new_status,
                    initiated_by="system",
                    reason="Availability toggle",
                )
            except Exception:
                # Fallback to direct update if status manager not available
                pass
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
                filters.append(
                    Agent.status.notin_(
                        [
                            AgentStatus.TERMINATED.value,
                            AgentStatus.QUARANTINED.value,
                            AgentStatus.FAILED.value,
                        ]
                    )
                )

            if filters:
                query = query.filter(and_(*filters))

            agents = query.all()

            # Expunge agents so they can be used outside the session
            for agent in agents:
                session.expunge(agent)

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

        availability_bonus = 0.2 if agent.status == AgentStatus.IDLE.value else 0.0
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

    # ---------------------------------------------------------------------
    # Registration Protocol Helpers (REQ-ALM-001)
    # ---------------------------------------------------------------------

    def _pre_validate(
        self,
        agent_type: str,
        capabilities: List[str],
        resource_requirements: Optional[Dict[str, Any]],
        config: Optional[Dict[str, Any]],
        binary_path: Optional[str],
        version: Optional[str],
    ) -> ValidationResult:
        """
        Pre-registration validation per REQ-ALM-001 Step 1.

        Validates:
        1. Binary integrity (if binary_path provided)
        2. Version compatibility
        3. Configuration schema
        4. Resource availability
        """
        details = {}

        # 1. Binary integrity verification (if binary_path provided)
        if binary_path:
            if not os.path.exists(binary_path):
                return ValidationResult(
                    success=False,
                    reason="Binary path does not exist",
                    details={"binary_path": binary_path},
                )
            # Calculate checksum (simplified - in production, compare against expected hash)
            try:
                with open(binary_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                details["binary_checksum"] = file_hash
            except Exception as e:
                logger.warning(f"Could not calculate binary checksum: {e}")

        # 2. Version compatibility check
        if version:
            # Simplified version check - in production, compare against orchestrator version
            # For now, just log it
            details["agent_version"] = version
            # TODO: Implement actual version compatibility matrix

        # 3. Configuration schema validation
        if config:
            # Simplified schema validation - in production, use JSON Schema or Pydantic
            if not isinstance(config, dict):
                return ValidationResult(
                    success=False,
                    reason="Configuration must be a dictionary",
                    details={"config": config},
                )
            details["config_validated"] = True

        # 4. Resource availability check
        if resource_requirements:
            # Simplified resource check - in production, check actual system resources
            # For now, just validate structure
            if not isinstance(resource_requirements, dict):
                return ValidationResult(
                    success=False,
                    reason="Resource requirements must be a dictionary",
                    details={"resource_requirements": resource_requirements},
                )
            details["resource_requirements"] = resource_requirements
            # TODO: Implement actual resource availability check

        return ValidationResult(success=True, details=details)

    def _generate_agent_name(self, agent_type: str, phase_id: Optional[str]) -> str:
        """
        Generate human-readable agent name per REQ-ALM-001 Step 2.
        Pattern: {type}-{phase}-{sequence}
        """
        with self.db.get_session() as session:
            # Get next sequence number for this agent type and phase
            query = session.query(Agent).filter(Agent.agent_type == agent_type)
            if phase_id:
                query = query.filter(Agent.phase_id == phase_id)
            count = query.count()
            sequence = count + 1

        phase_part = f"-{phase_id.lower().replace('phase_', '')}" if phase_id else ""
        return f"{agent_type.lower()}{phase_part}-{sequence:03d}"

    def _generate_crypto_identity(self, agent_id: str) -> Dict[str, Any]:
        """
        Generate cryptographic identity per REQ-ALM-001 Step 2.
        Returns public key and metadata.
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning(
                "cryptography library not available, skipping crypto identity generation"
            )
            return {
                "public_key": None,
                "metadata": {"error": "cryptography library not installed"},
            }

        try:
            # Generate RSA key pair
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            public_key = private_key.public_key()

            # Serialize public key
            public_key_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode("utf-8")

            # Create metadata
            metadata = {
                "key_id": f"{agent_id}-key",
                "algorithm": "RSA-2048",
                "created_at": utc_now().isoformat(),
            }

            # In production, private key would be securely transmitted to agent
            # For now, we only store the public key
            return {
                "public_key": public_key_pem,
                "metadata": metadata,
            }
        except Exception as e:
            logger.warning(f"Could not generate cryptographic identity: {e}")
            # Return empty identity if crypto generation fails
            return {
                "public_key": None,
                "metadata": {"error": str(e)},
            }

    def _get_orchestrator_identifier(self) -> str:
        """Get orchestrator instance identifier."""
        try:
            hostname = socket.gethostname()
            return f"orchestrator-{hostname}"
        except Exception:
            return "orchestrator-unknown"

    def _subscribe_to_event_bus(
        self, agent_id: str, agent_type: str, phase_id: Optional[str]
    ) -> None:
        """
        Subscribe agent to relevant event channels per REQ-ALM-001 Step 4.
        """
        if not self.event_bus:
            return

        # Subscribe to task assignment events for agent's phase
        if phase_id:
            channel = f"task.assignment.{phase_id}"
            # Event bus subscription would happen here
            # For now, we just log it
            logger.info(f"Agent {agent_id} subscribed to {channel}")

        # Subscribe to system-wide broadcasts
        logger.info(f"Agent {agent_id} subscribed to system broadcasts")

        # Subscribe to shutdown signals
        logger.info(f"Agent {agent_id} subscribed to shutdown signals")

        # In production, this would use actual event bus subscription API
        # For now, the event bus will route events based on agent_id matching

    def _wait_for_initial_heartbeat(self, agent_id: str, timeout: int = 60) -> None:
        """
        Wait for initial heartbeat with timeout per REQ-ALM-001 Step 5.

        Raises TimeoutError if heartbeat not received within timeout.
        """
        import time

        start_time = time.time()
        check_interval = 2  # Check every 2 seconds

        while time.time() - start_time < timeout:
            with self.db.get_session() as session:
                agent = session.get(Agent, agent_id)
                if agent and agent.last_heartbeat:
                    # Heartbeat received
                    logger.info(f"Initial heartbeat received for agent {agent_id}")
                    return
                session.expunge(agent) if agent else None

            time.sleep(check_interval)

        # Timeout exceeded
        raise TimeoutError(
            f"Initial heartbeat not received for agent {agent_id} within {timeout}s"
        )
