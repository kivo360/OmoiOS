"""Tests for SessionAgentConfigRestorer service.

Tests Requirements:
- REQ-SES-001: Session agent configuration restoration after compaction
- REQ-SES-002: Agent state recovery from session transcripts
- REQ-SES-003: Sandbox reference updates post-restoration
"""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from omoi_os.services.session_agent_config_restorer import (
    SessionAgentConfigRestorer,
    RestorationResult,
    CompactionContext,
)
from omoi_os.models.agent import Agent
from omoi_os.models.agent_status import AgentStatus
from omoi_os.models.claude_session_transcript import ClaudeSessionTranscript


@pytest.fixture
def mock_db():
    """Create a mock database service."""
    db = MagicMock()
    session_context = MagicMock()
    db.get_session.return_value.__enter__ = MagicMock(return_value=session_context)
    db.get_session.return_value.__exit__ = MagicMock(return_value=False)
    return db, session_context


@pytest.fixture
def mock_agent_registry():
    """Create a mock agent registry service."""
    registry = MagicMock()
    registry.register_agent = MagicMock(return_value=MagicMock(id=str(uuid4())))
    registry.update_agent = MagicMock(return_value=MagicMock(id=str(uuid4())))
    return registry


@pytest.fixture
def mock_status_manager():
    """Create a mock agent status manager."""
    manager = MagicMock()
    manager.transition_status = MagicMock()
    return manager


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus service."""
    event_bus = MagicMock()
    event_bus.publish = MagicMock()
    return event_bus


@pytest.fixture
def restorer(mock_db, mock_agent_registry, mock_status_manager, mock_event_bus):
    """Create a SessionAgentConfigRestorer instance with mocked dependencies."""
    db, _ = mock_db
    return SessionAgentConfigRestorer(
        db=db,
        agent_registry=mock_agent_registry,
        status_manager=mock_status_manager,
        event_bus=mock_event_bus,
    )


class TestRestorationResult:
    """Test RestorationResult dataclass."""

    def test_success_result(self):
        """Test successful restoration result."""
        result = RestorationResult(
            success=True,
            agent_id="agent-123",
            restored_config={"agent_type": "worker"},
            restoration_metadata={"session_id": "sess-456"},
        )
        assert result.success is True
        assert result.agent_id == "agent-123"
        assert result.restored_config == {"agent_type": "worker"}
        assert result.error_message is None

    def test_failure_result(self):
        """Test failed restoration result."""
        result = RestorationResult(
            success=False,
            error_message="No transcript found",
            restoration_metadata={"session_id": "sess-456"},
        )
        assert result.success is False
        assert result.agent_id is None
        assert result.error_message == "No transcript found"


class TestCompactionContext:
    """Test CompactionContext dataclass."""

    def test_context_creation(self):
        """Test compaction context creation."""
        context = CompactionContext(
            session_id="sess-123",
            sandbox_id="sandbox-456",
            task_id="task-789",
            compaction_reason="memory_pressure",
            compaction_timestamp="2025-01-01T00:00:00Z",
            original_agent_id="agent-abc",
        )
        assert context.session_id == "sess-123"
        assert context.sandbox_id == "sandbox-456"
        assert context.compaction_reason == "memory_pressure"


class TestGetSessionTranscript:
    """Test _get_session_transcript method."""

    def test_get_existing_transcript(self, restorer, mock_db):
        """Test retrieving an existing session transcript."""
        db, session_context = mock_db

        # Create mock transcript
        mock_transcript = MagicMock()
        mock_transcript.id = "transcript-123"
        mock_transcript.session_id = "sess-456"
        mock_transcript.session_metadata = {"agent_config": {"agent_type": "worker"}}

        # Configure mock query
        session_context.query.return_value.filter.return_value.first.return_value = (
            mock_transcript
        )

        result = restorer._get_session_transcript("sess-456")

        assert result is not None
        assert result.id == "transcript-123"
        session_context.query.assert_called_once_with(ClaudeSessionTranscript)

    def test_get_nonexistent_transcript(self, restorer, mock_db):
        """Test retrieving a non-existent session transcript."""
        db, session_context = mock_db

        # Configure mock query to return None
        session_context.query.return_value.filter.return_value.first.return_value = None

        result = restorer._get_session_transcript("nonexistent-sess")

        assert result is None


class TestExtractAgentConfig:
    """Test _extract_agent_config method."""

    def test_extract_from_agent_config_key(self, restorer):
        """Test extracting agent config from 'agent_config' key."""
        metadata = {
            "agent_config": {
                "agent_id": "agent-123",
                "agent_type": "worker",
                "capabilities": ["code", "test"],
            }
        }

        result = restorer._extract_agent_config(metadata)

        assert result is not None
        assert result["agent_id"] == "agent-123"
        assert result["agent_type"] == "worker"

    def test_extract_from_agent_info_key(self, restorer):
        """Test extracting agent config from 'agent_info' key."""
        metadata = {
            "agent_info": {
                "agent_id": "agent-456",
                "agent_type": "monitor",
            }
        }

        result = restorer._extract_agent_config(metadata)

        assert result is not None
        assert result["agent_id"] == "agent-456"

    def test_extract_from_legacy_format(self, restorer):
        """Test extracting agent config from legacy format."""
        metadata = {
            "agent_id": "agent-789",
            "agent_type": "worker",
            "capabilities": ["explore"],
            "phase_id": "PHASE_IMPLEMENTATION",
            "config": {"key": "value"},
        }

        result = restorer._extract_agent_config(metadata)

        assert result is not None
        assert result["agent_id"] == "agent-789"
        assert result["phase_id"] == "PHASE_IMPLEMENTATION"

    def test_extract_no_config(self, restorer):
        """Test extracting when no agent config is present."""
        metadata = {"other_key": "other_value"}

        result = restorer._extract_agent_config(metadata)

        assert result is None


class TestGetAgentById:
    """Test _get_agent_by_id method."""

    def test_get_existing_agent(self, restorer, mock_db):
        """Test retrieving an existing agent."""
        db, session_context = mock_db

        mock_agent = MagicMock()
        mock_agent.id = "agent-123"
        session_context.get.return_value = mock_agent

        result = restorer._get_agent_by_id("agent-123")

        assert result is not None
        assert result.id == "agent-123"
        session_context.get.assert_called_once_with(Agent, "agent-123")

    def test_get_nonexistent_agent(self, restorer, mock_db):
        """Test retrieving a non-existent agent."""
        db, session_context = mock_db

        session_context.get.return_value = None

        result = restorer._get_agent_by_id("nonexistent-agent")

        assert result is None


class TestUpdateExistingAgent:
    """Test _update_existing_agent method."""

    @pytest.mark.asyncio
    async def test_update_agent_success(
        self, restorer, mock_agent_registry, mock_status_manager
    ):
        """Test successfully updating an existing agent."""
        mock_agent = MagicMock()
        mock_agent.id = "agent-123"
        mock_agent.agent_metadata = {"existing": "data"}
        mock_agent.status = AgentStatus.TERMINATED.value

        mock_agent_registry.update_agent.return_value = mock_agent

        agent_config = {
            "agent_type": "worker",
            "capabilities": ["code"],
            "sandbox_id": "old-sandbox",
            "tags": ["test"],
        }

        result = await restorer._update_existing_agent(
            agent=mock_agent,
            new_sandbox_id="new-sandbox-456",
            agent_config=agent_config,
            target_phase_id="PHASE_IMPLEMENTATION",
        )

        assert result is not None
        mock_agent_registry.update_agent.assert_called_once()
        call_args = mock_agent_registry.update_agent.call_args
        assert call_args.kwargs["agent_id"] == "agent-123"

        # Verify status transition was called for terminal state
        mock_status_manager.transition_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_agent_no_status_transition(
        self, restorer, mock_agent_registry, mock_status_manager
    ):
        """Test updating agent without status transition for non-terminal state."""
        mock_agent = MagicMock()
        mock_agent.id = "agent-123"
        mock_agent.agent_metadata = {}
        mock_agent.status = AgentStatus.IDLE.value  # Non-terminal

        mock_agent_registry.update_agent.return_value = mock_agent

        agent_config = {"agent_type": "worker"}

        await restorer._update_existing_agent(
            agent=mock_agent,
            new_sandbox_id="new-sandbox",
            agent_config=agent_config,
            target_phase_id=None,
        )

        # Status transition should not be called for non-terminal state
        mock_status_manager.transition_status.assert_not_called()


class TestCreateRestoredAgent:
    """Test _create_restored_agent method."""

    @pytest.mark.asyncio
    async def test_create_new_agent(self, restorer, mock_agent_registry):
        """Test creating a new restored agent."""
        mock_transcript = MagicMock()
        mock_transcript.id = "transcript-123"
        mock_transcript.session_id = "sess-456"

        new_agent = MagicMock()
        new_agent.id = "new-agent-789"
        mock_agent_registry.register_agent.return_value = new_agent

        agent_config = {
            "agent_type": "worker",
            "capabilities": ["code", "test"],
            "config": {"original": "settings"},
            "tags": ["restored"],
        }

        result = await restorer._create_restored_agent(
            original_agent_id="original-agent-abc",
            new_sandbox_id="sandbox-xyz",
            agent_config=agent_config,
            target_phase_id="PHASE_IMPLEMENTATION",
            transcript=mock_transcript,
        )

        assert result is not None
        assert result.id == "new-agent-789"
        mock_agent_registry.register_agent.assert_called_once()

        call_args = mock_agent_registry.register_agent.call_args
        assert call_args.kwargs["agent_type"] == "worker"
        assert call_args.kwargs["status"] == AgentStatus.IDLE.value
        assert "compaction_recovery" in call_args.kwargs["config"]


class TestUpdateTranscriptSandboxRef:
    """Test _update_transcript_sandbox_ref method."""

    def test_update_sandbox_reference(self, restorer, mock_db):
        """Test updating transcript sandbox reference."""
        db, session_context = mock_db

        mock_transcript = MagicMock()
        mock_transcript.id = "transcript-123"
        mock_transcript.sandbox_id = "old-sandbox"
        mock_transcript.session_metadata = {}

        # Configure merge to return the transcript
        session_context.merge.return_value = mock_transcript

        restorer._update_transcript_sandbox_ref(mock_transcript, "new-sandbox")

        assert mock_transcript.sandbox_id == "new-sandbox"
        assert "sandbox_history" in mock_transcript.session_metadata
        session_context.commit.assert_called_once()

    def test_update_with_existing_history(self, restorer, mock_db):
        """Test updating transcript with existing sandbox history."""
        db, session_context = mock_db

        mock_transcript = MagicMock()
        mock_transcript.id = "transcript-123"
        mock_transcript.sandbox_id = "sandbox-v2"
        mock_transcript.session_metadata = {
            "sandbox_history": [
                {"from": "sandbox-v1", "to": "sandbox-v2", "reason": "compaction"}
            ]
        }

        session_context.merge.return_value = mock_transcript

        restorer._update_transcript_sandbox_ref(mock_transcript, "sandbox-v3")

        history = mock_transcript.session_metadata["sandbox_history"]
        assert len(history) == 2
        assert history[1]["to"] == "sandbox-v3"


class TestPublishRestorationEvent:
    """Test _publish_restoration_event method."""

    def test_publish_event(self, restorer, mock_event_bus):
        """Test publishing restoration event."""
        restorer._publish_restoration_event(
            session_id="sess-123",
            agent_id="agent-456",
            original_agent_id="original-agent",
            new_sandbox_id="sandbox-789",
            compaction_metadata={"reason": "memory_pressure"},
        )

        mock_event_bus.publish.assert_called_once()
        call_args = mock_event_bus.publish.call_args
        event = call_args[0][0]
        assert event.event_type == "AGENT_CONFIG_RESTORED"
        assert event.entity_id == "agent-456"
        assert event.payload["session_id"] == "sess-123"
        assert event.payload["original_agent_id"] == "original-agent"

    def test_publish_no_event_bus(self, restorer):
        """Test that no event is published when event_bus is None."""
        restorer.event_bus = None

        # Should not raise any exception
        restorer._publish_restoration_event(
            session_id="sess-123",
            agent_id="agent-456",
            original_agent_id=None,
            new_sandbox_id="sandbox-789",
            compaction_metadata=None,
        )


class TestValidateRestorationPrerequisites:
    """Test validate_restoration_prerequisites method."""

    @pytest.mark.asyncio
    async def test_validation_success(self, restorer, mock_db):
        """Test successful validation."""
        db, session_context = mock_db

        mock_transcript = MagicMock()
        mock_transcript.id = "transcript-123"
        mock_transcript.session_metadata = {"agent_config": {"agent_type": "worker"}}

        session_context.query.return_value.filter.return_value.first.return_value = (
            mock_transcript
        )

        result = await restorer.validate_restoration_prerequisites(
            "sess-123", "sandbox-456"
        )

        assert result["valid"] is True
        assert result["checks"]["transcript_exists"] is True
        assert result["checks"]["agent_config_present"] is True

    @pytest.mark.asyncio
    async def test_validation_missing_transcript(self, restorer, mock_db):
        """Test validation fails when transcript is missing."""
        db, session_context = mock_db

        session_context.query.return_value.filter.return_value.first.return_value = None

        result = await restorer.validate_restoration_prerequisites(
            "nonexistent-sess", "sandbox-456"
        )

        assert result["valid"] is False
        assert result["checks"]["transcript_exists"] is False
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_validation_missing_agent_config(self, restorer, mock_db):
        """Test validation fails when agent config is missing."""
        db, session_context = mock_db

        mock_transcript = MagicMock()
        mock_transcript.id = "transcript-123"
        mock_transcript.session_metadata = {"other_key": "value"}

        session_context.query.return_value.filter.return_value.first.return_value = (
            mock_transcript
        )

        result = await restorer.validate_restoration_prerequisites(
            "sess-123", "sandbox-456"
        )

        assert result["valid"] is False
        assert result["checks"]["agent_config_present"] is False


class TestRestoreAfterCompaction:
    """Test restore_after_compaction method - main entry point."""

    @pytest.mark.asyncio
    async def test_restore_success_existing_agent(
        self,
        restorer,
        mock_db,
        mock_agent_registry,
        mock_status_manager,
        mock_event_bus,
    ):
        """Test successful restoration with existing agent."""
        db, session_context = mock_db

        # Setup mock transcript
        mock_transcript = MagicMock()
        mock_transcript.id = "transcript-123"
        mock_transcript.session_id = "sess-456"
        mock_transcript.session_metadata = {
            "agent_config": {
                "agent_id": "existing-agent",
                "agent_type": "worker",
                "capabilities": ["code"],
            }
        }

        # Setup mock agent
        mock_agent = MagicMock()
        mock_agent.id = "existing-agent"
        mock_agent.status = AgentStatus.IDLE.value

        # Configure mocks
        session_context.query.return_value.filter.return_value.first.return_value = (
            mock_transcript
        )
        session_context.get.return_value = mock_agent
        session_context.merge.return_value = mock_transcript

        mock_agent_registry.update_agent.return_value = mock_agent

        result = await restorer.restore_after_compaction(
            session_id="sess-456",
            new_sandbox_id="new-sandbox-789",
            target_phase_id="PHASE_IMPLEMENTATION",
            compaction_metadata={"reason": "test"},
        )

        assert result.success is True
        assert result.agent_id == "existing-agent"
        assert result.restored_config is not None
        mock_event_bus.publish.assert_called()

    @pytest.mark.asyncio
    async def test_restore_success_new_agent(
        self, restorer, mock_db, mock_agent_registry, mock_event_bus
    ):
        """Test successful restoration creating new agent."""
        db, session_context = mock_db

        # Setup mock transcript without existing agent
        mock_transcript = MagicMock()
        mock_transcript.id = "transcript-123"
        mock_transcript.session_id = "sess-456"
        mock_transcript.session_metadata = {
            "agent_config": {
                "agent_type": "worker",
                "capabilities": ["code"],
            }
        }

        new_agent = MagicMock()
        new_agent.id = "new-agent-789"

        # Configure mocks - no existing agent
        session_context.query.return_value.filter.return_value.first.return_value = (
            mock_transcript
        )
        session_context.get.return_value = None  # No existing agent
        session_context.merge.return_value = mock_transcript

        mock_agent_registry.register_agent.return_value = new_agent

        result = await restorer.restore_after_compaction(
            session_id="sess-456",
            new_sandbox_id="new-sandbox-789",
            target_phase_id="PHASE_IMPLEMENTATION",
        )

        assert result.success is True
        assert result.agent_id == "new-agent-789"
        mock_agent_registry.register_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_restore_missing_transcript(self, restorer, mock_db):
        """Test restoration fails when transcript is missing."""
        db, session_context = mock_db

        # No transcript found
        session_context.query.return_value.filter.return_value.first.return_value = None

        result = await restorer.restore_after_compaction(
            session_id="nonexistent-sess",
            new_sandbox_id="sandbox-789",
        )

        assert result.success is False
        assert "No session transcript found" in result.error_message

    @pytest.mark.asyncio
    async def test_restore_missing_agent_config(self, restorer, mock_db):
        """Test restoration fails when agent config is missing."""
        db, session_context = mock_db

        mock_transcript = MagicMock()
        mock_transcript.id = "transcript-123"
        mock_transcript.session_metadata = {"other_key": "value"}  # No agent config

        session_context.query.return_value.filter.return_value.first.return_value = (
            mock_transcript
        )

        result = await restorer.restore_after_compaction(
            session_id="sess-456",
            new_sandbox_id="sandbox-789",
        )

        assert result.success is False
        assert "No agent configuration found" in result.error_message

    @pytest.mark.asyncio
    async def test_restore_exception_handling(
        self, restorer, mock_db, mock_agent_registry
    ):
        """Test exception handling during restoration."""
        db, session_context = mock_db

        mock_transcript = MagicMock()
        mock_transcript.id = "transcript-123"
        mock_transcript.session_metadata = {"agent_config": {"agent_type": "worker"}}

        session_context.query.return_value.filter.return_value.first.return_value = (
            mock_transcript
        )

        # Simulate error during agent creation
        mock_agent_registry.register_agent.side_effect = Exception("Database error")

        result = await restorer.restore_after_compaction(
            session_id="sess-456",
            new_sandbox_id="sandbox-789",
        )

        assert result.success is False
        assert "Failed to restore agent configuration" in result.error_message
        assert result.restoration_metadata["error_type"] == "Exception"


class TestBatchRestore:
    """Test batch_restore_after_compaction method."""

    @pytest.mark.asyncio
    async def test_batch_restore(
        self, restorer, mock_db, mock_agent_registry, mock_event_bus
    ):
        """Test batch restoration of multiple sessions."""
        db, session_context = mock_db

        # Setup mock transcript
        mock_transcript = MagicMock()
        mock_transcript.id = "transcript-123"
        mock_transcript.session_id = "sess-456"
        mock_transcript.session_metadata = {"agent_config": {"agent_type": "worker"}}

        new_agent = MagicMock()
        new_agent.id = "agent-789"

        session_context.query.return_value.filter.return_value.first.return_value = (
            mock_transcript
        )
        session_context.get.return_value = None
        session_context.merge.return_value = mock_transcript
        mock_agent_registry.register_agent.return_value = new_agent

        results = await restorer.batch_restore_after_compaction(
            session_ids=["sess-1", "sess-2", "sess-3"],
            new_sandbox_id="sandbox-batch",
        )

        assert len(results) == 3
        assert all(r.success for r in results)

        # Verify batch event was published
        batch_calls = [
            c
            for c in mock_event_bus.publish.call_args_list
            if c[0][0].event_type == "BATCH_AGENT_CONFIG_RESTORED"
        ]
        assert len(batch_calls) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
