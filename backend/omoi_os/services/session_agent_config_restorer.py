"""Session agent configuration restoration service.

Handles restoring agent configuration from checkpoints after compaction events.
This service ensures that agent state, capabilities, and configuration are
properly restored when a session is resumed from a checkpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from omoi_os.logging import get_logger
from omoi_os.models.agent import Agent
from omoi_os.models.agent_status import AgentStatus
from omoi_os.models.claude_session_transcript import ClaudeSessionTranscript
from omoi_os.services.agent_registry import AgentRegistryService
from omoi_os.services.agent_status_manager import AgentStatusManager
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)


@dataclass
class RestorationResult:
    """Result of agent configuration restoration."""

    success: bool
    agent_id: Optional[str] = None
    restored_config: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    restoration_metadata: Optional[Dict[str, Any]] = None


@dataclass
class CompactionContext:
    """Context information about the compaction event."""

    session_id: str
    sandbox_id: Optional[str] = None
    task_id: Optional[str] = None
    compaction_reason: Optional[str] = None
    compaction_timestamp: Optional[str] = None
    original_agent_id: Optional[str] = None


class SessionAgentConfigRestorer:
    """Service for restoring agent configuration after session compaction.

    This service handles the restoration of agent state, capabilities,
    and configuration when a session is resumed from a checkpoint after
    compaction. It ensures continuity of agent identity and state across
    sandbox boundaries.

    Attributes:
        db: Database service for persistence operations
        agent_registry: Agent registry service for agent CRUD operations
        status_manager: Agent status manager for state transitions
        event_bus: Optional event bus for publishing restoration events
    """

    def __init__(
        self,
        db: DatabaseService,
        agent_registry: AgentRegistryService,
        status_manager: AgentStatusManager,
        event_bus: Optional[EventBusService] = None,
    ):
        """Initialize the session agent configuration restorer.

        Args:
            db: Database service
            agent_registry: Agent registry service
            status_manager: Agent status manager
            event_bus: Optional event bus for publishing events
        """
        self.db = db
        self.agent_registry = agent_registry
        self.status_manager = status_manager
        self.event_bus = event_bus

    async def restore_after_compaction(
        self,
        session_id: str,
        new_sandbox_id: str,
        target_phase_id: Optional[str] = None,
        compaction_metadata: Optional[Dict[str, Any]] = None,
    ) -> RestorationResult:
        """Restore agent configuration after session compaction.

        This is the main entry point for restoring agent configuration
        when a session resumes after compaction. It retrieves the session
        transcript, extracts agent configuration, and creates or updates
        the agent with restored state.

        Args:
            session_id: The Claude Code session ID to restore
            new_sandbox_id: The new sandbox ID where session will resume
            target_phase_id: Optional phase ID for the restored agent
            compaction_metadata: Optional metadata about the compaction event

        Returns:
            RestorationResult with success status and restored configuration
        """
        logger.info(
            f"Starting agent config restoration for session {session_id} "
            f"in sandbox {new_sandbox_id}"
        )

        # Step 1: Retrieve session transcript
        transcript = self._get_session_transcript(session_id)
        if not transcript:
            error_msg = f"No session transcript found for session_id: {session_id}"
            logger.error(error_msg)
            return RestorationResult(
                success=False,
                error_message=error_msg,
                restoration_metadata={
                    "session_id": session_id,
                    "sandbox_id": new_sandbox_id,
                },
            )

        # Step 2: Parse session metadata to extract agent configuration
        session_metadata = transcript.session_metadata or {}
        agent_config = self._extract_agent_config(session_metadata)

        if not agent_config:
            error_msg = (
                f"No agent configuration found in session metadata for {session_id}"
            )
            logger.error(error_msg)
            return RestorationResult(
                success=False,
                error_message=error_msg,
                restoration_metadata={
                    "session_id": session_id,
                    "sandbox_id": new_sandbox_id,
                    "transcript_id": transcript.id,
                },
            )

        # Step 3: Determine if we need to create new agent or update existing
        original_agent_id = agent_config.get("agent_id")
        agent = None

        if original_agent_id:
            agent = self._get_agent_by_id(original_agent_id)

        # Step 4: Create or update agent with restored configuration
        try:
            if agent:
                restored_agent = await self._update_existing_agent(
                    agent=agent,
                    new_sandbox_id=new_sandbox_id,
                    agent_config=agent_config,
                    target_phase_id=target_phase_id,
                )
            else:
                restored_agent = await self._create_restored_agent(
                    original_agent_id=original_agent_id,
                    new_sandbox_id=new_sandbox_id,
                    agent_config=agent_config,
                    target_phase_id=target_phase_id,
                    transcript=transcript,
                )

            # Step 5: Update session transcript with new sandbox reference
            self._update_transcript_sandbox_ref(transcript, new_sandbox_id)

            # Step 6: Publish restoration event
            self._publish_restoration_event(
                session_id=session_id,
                agent_id=restored_agent.id,
                original_agent_id=original_agent_id,
                new_sandbox_id=new_sandbox_id,
                compaction_metadata=compaction_metadata,
            )

            logger.info(
                f"Successfully restored agent {restored_agent.id} for session {session_id}"
            )

            return RestorationResult(
                success=True,
                agent_id=restored_agent.id,
                restored_config=agent_config,
                restoration_metadata={
                    "session_id": session_id,
                    "sandbox_id": new_sandbox_id,
                    "original_agent_id": original_agent_id,
                    "restored_agent_id": restored_agent.id,
                    "transcript_id": transcript.id,
                    "restored_at": utc_now().isoformat(),
                },
            )

        except Exception as e:
            error_msg = f"Failed to restore agent configuration: {str(e)}"
            logger.exception(error_msg)
            return RestorationResult(
                success=False,
                error_message=error_msg,
                restoration_metadata={
                    "session_id": session_id,
                    "sandbox_id": new_sandbox_id,
                    "original_agent_id": original_agent_id,
                    "error_type": type(e).__name__,
                },
            )

    def _get_session_transcript(
        self, session_id: str
    ) -> Optional[ClaudeSessionTranscript]:
        """Retrieve session transcript by session ID.

        Args:
            session_id: The Claude Code session ID

        Returns:
            Session transcript if found, None otherwise
        """
        with self.db.get_session() as session:
            transcript = (
                session.query(ClaudeSessionTranscript)
                .filter(ClaudeSessionTranscript.session_id == session_id)
                .first()
            )
            if transcript:
                session.expunge(transcript)
            return transcript

    def _extract_agent_config(
        self, session_metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extract agent configuration from session metadata.

        Args:
            session_metadata: The session metadata dictionary

        Returns:
            Agent configuration dictionary if found, None otherwise
        """
        # Check for agent configuration in various locations within metadata
        agent_config = session_metadata.get("agent_config")
        if agent_config:
            return agent_config

        # Check for nested agent info
        agent_info = session_metadata.get("agent_info")
        if agent_info:
            return agent_info

        # Check for legacy format
        if "agent_id" in session_metadata:
            return {
                "agent_id": session_metadata.get("agent_id"),
                "agent_type": session_metadata.get("agent_type", "worker"),
                "capabilities": session_metadata.get("capabilities", []),
                "phase_id": session_metadata.get("phase_id"),
                "config": session_metadata.get("config", {}),
            }

        return None

    def _get_agent_by_id(self, agent_id: str) -> Optional[Agent]:
        """Retrieve agent by ID.

        Args:
            agent_id: The agent ID

        Returns:
            Agent if found, None otherwise
        """
        with self.db.get_session() as session:
            agent = session.get(Agent, agent_id)
            if agent:
                session.expunge(agent)
            return agent

    async def _update_existing_agent(
        self,
        agent: Agent,
        new_sandbox_id: str,
        agent_config: Dict[str, Any],
        target_phase_id: Optional[str],
    ) -> Agent:
        """Update existing agent with restored configuration.

        Args:
            agent: The existing agent to update
            new_sandbox_id: The new sandbox ID
            agent_config: The agent configuration to restore
            target_phase_id: Optional phase ID to update

        Returns:
            Updated agent
        """
        logger.info(f"Updating existing agent {agent.id} after compaction")

        # Update agent metadata with new sandbox reference
        current_metadata = agent.agent_metadata or {}
        current_metadata["restored_from_sandbox"] = agent_config.get("sandbox_id")
        current_metadata["restored_to_sandbox"] = new_sandbox_id
        current_metadata["restored_at"] = utc_now().isoformat()
        current_metadata["compaction_recovery"] = True

        # Update capabilities if provided in config
        capabilities = agent_config.get("capabilities")
        if capabilities:
            current_metadata["restored_capabilities"] = capabilities

        # Use agent registry to update the agent
        updated_agent = self.agent_registry.update_agent(
            agent_id=agent.id,
            config=current_metadata,
            tags=agent_config.get("tags"),
        )

        if not updated_agent:
            raise ValueError(f"Failed to update agent {agent.id}")

        # Transition agent status back to IDLE if it was in a terminal state
        if agent.status in [
            AgentStatus.TERMINATED.value,
            AgentStatus.FAILED.value,
            AgentStatus.QUARANTINED.value,
        ]:
            self.status_manager.transition_status(
                agent_id=agent.id,
                to_status=AgentStatus.IDLE.value,
                initiated_by="session_restorer",
                reason=f"Restored after compaction to sandbox {new_sandbox_id}",
                metadata={
                    "compaction_recovery": True,
                    "new_sandbox_id": new_sandbox_id,
                },
            )

        return updated_agent

    async def _create_restored_agent(
        self,
        original_agent_id: Optional[str],
        new_sandbox_id: str,
        agent_config: Dict[str, Any],
        target_phase_id: Optional[str],
        transcript: ClaudeSessionTranscript,
    ) -> Agent:
        """Create a new agent with restored configuration.

        Args:
            original_agent_id: The original agent ID (may be None)
            new_sandbox_id: The new sandbox ID
            agent_config: The agent configuration to restore
            target_phase_id: Optional phase ID
            transcript: The session transcript

        Returns:
            Newly created agent
        """
        logger.info(
            f"Creating new restored agent for original {original_agent_id} "
            f"in sandbox {new_sandbox_id}"
        )

        # Prepare restoration metadata
        restoration_metadata = {
            "original_agent_id": original_agent_id,
            "restored_from_session": transcript.session_id,
            "restored_from_transcript": transcript.id,
            "restored_to_sandbox": new_sandbox_id,
            "restored_at": utc_now().isoformat(),
            "compaction_recovery": True,
            "original_config": agent_config.get("config", {}),
        }

        # Register new agent with restored configuration
        agent_type = agent_config.get("agent_type", "worker")
        capabilities = agent_config.get("capabilities", [])
        phase_id = target_phase_id or agent_config.get("phase_id")

        # Merge original config with restoration metadata
        original_config = agent_config.get("config", {})
        merged_config = {**original_config, **restoration_metadata}

        new_agent = self.agent_registry.register_agent(
            agent_type=agent_type,
            phase_id=phase_id,
            capabilities=capabilities,
            status=AgentStatus.IDLE.value,
            tags=agent_config.get("tags", []),
            config=merged_config,
            resource_requirements=agent_config.get("resource_requirements"),
            version=agent_config.get("version"),
        )

        logger.info(
            f"Created restored agent {new_agent.id} (original: {original_agent_id})"
        )

        return new_agent

    def _update_transcript_sandbox_ref(
        self,
        transcript: ClaudeSessionTranscript,
        new_sandbox_id: str,
    ) -> None:
        """Update session transcript with new sandbox reference.

        Args:
            transcript: The session transcript to update
            new_sandbox_id: The new sandbox ID
        """
        with self.db.get_session() as session:
            # Re-attach transcript to session
            attached_transcript = session.merge(transcript)

            # Update sandbox ID
            old_sandbox_id = attached_transcript.sandbox_id
            attached_transcript.sandbox_id = new_sandbox_id

            # Update metadata with restoration info
            metadata = attached_transcript.session_metadata or {}
            if "sandbox_history" not in metadata:
                metadata["sandbox_history"] = []
            metadata["sandbox_history"].append(
                {
                    "from": old_sandbox_id,
                    "to": new_sandbox_id,
                    "timestamp": utc_now().isoformat(),
                    "reason": "compaction_recovery",
                }
            )
            attached_transcript.session_metadata = metadata

            session.commit()
            logger.info(
                f"Updated transcript {transcript.id} sandbox ref: {old_sandbox_id} -> {new_sandbox_id}"
            )

    def _publish_restoration_event(
        self,
        session_id: str,
        agent_id: str,
        original_agent_id: Optional[str],
        new_sandbox_id: str,
        compaction_metadata: Optional[Dict[str, Any]],
    ) -> None:
        """Publish agent restoration event to event bus.

        Args:
            session_id: The session ID
            agent_id: The restored agent ID
            original_agent_id: The original agent ID
            new_sandbox_id: The new sandbox ID
            compaction_metadata: Optional compaction metadata
        """
        if not self.event_bus:
            return

        event = SystemEvent(
            event_type="AGENT_CONFIG_RESTORED",
            entity_type="agent",
            entity_id=agent_id,
            payload={
                "session_id": session_id,
                "agent_id": agent_id,
                "original_agent_id": original_agent_id,
                "new_sandbox_id": new_sandbox_id,
                "restored_at": utc_now().isoformat(),
                "compaction_metadata": compaction_metadata or {},
            },
        )
        self.event_bus.publish(event)
        logger.debug(f"Published AGENT_CONFIG_RESTORED event for agent {agent_id}")

    async def validate_restoration_prerequisites(
        self,
        session_id: str,
        new_sandbox_id: str,
    ) -> Dict[str, Any]:
        """Validate that restoration prerequisites are met.

        Args:
            session_id: The session ID to validate
            new_sandbox_id: The new sandbox ID

        Returns:
            Validation result dictionary with status and details
        """
        validation_result = {
            "valid": True,
            "checks": {},
            "errors": [],
        }

        # Check 1: Session transcript exists
        transcript = self._get_session_transcript(session_id)
        if not transcript:
            validation_result["valid"] = False
            validation_result["checks"]["transcript_exists"] = False
            validation_result["errors"].append(
                f"No transcript found for session {session_id}"
            )
        else:
            validation_result["checks"]["transcript_exists"] = True
            validation_result["checks"]["transcript_id"] = transcript.id

        # Check 2: Session metadata contains agent config
        if transcript:
            agent_config = self._extract_agent_config(transcript.session_metadata or {})
            if not agent_config:
                validation_result["valid"] = False
                validation_result["checks"]["agent_config_present"] = False
                validation_result["errors"].append(
                    "No agent configuration in session metadata"
                )
            else:
                validation_result["checks"]["agent_config_present"] = True
                validation_result["checks"]["agent_config_keys"] = list(
                    agent_config.keys()
                )

        # Check 3: New sandbox is ready (placeholder - would check sandbox status)
        validation_result["checks"]["sandbox_ready"] = True
        validation_result["checks"]["sandbox_id"] = new_sandbox_id

        return validation_result

    async def batch_restore_after_compaction(
        self,
        session_ids: List[str],
        new_sandbox_id: str,
        target_phase_id: Optional[str] = None,
    ) -> List[RestorationResult]:
        """Restore multiple sessions after compaction.

        Args:
            session_ids: List of session IDs to restore
            new_sandbox_id: The new sandbox ID
            target_phase_id: Optional phase ID

        Returns:
            List of restoration results
        """
        results = []

        for session_id in session_ids:
            result = await self.restore_after_compaction(
                session_id=session_id,
                new_sandbox_id=new_sandbox_id,
                target_phase_id=target_phase_id,
            )
            results.append(result)

        # Publish batch restoration event
        if self.event_bus:
            successful = sum(1 for r in results if r.success)
            self.event_bus.publish(
                SystemEvent(
                    event_type="BATCH_AGENT_CONFIG_RESTORED",
                    entity_type="system",
                    entity_id="batch",
                    payload={
                        "total_sessions": len(session_ids),
                        "successful_restorations": successful,
                        "failed_restorations": len(session_ids) - successful,
                        "new_sandbox_id": new_sandbox_id,
                        "restored_at": utc_now().isoformat(),
                    },
                )
            )

        return results
