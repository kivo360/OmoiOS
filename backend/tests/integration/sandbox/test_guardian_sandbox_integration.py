"""
Integration tests for Guardian-Sandbox integration.

Phase 6: Guardian should be able to intervene with sandbox agents
by routing interventions through the message injection API instead
of direct OpenHands conversation access.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from fastapi.testclient import TestClient


@pytest.mark.unit
class TestTaskModelSandboxField:
    """Tests for sandbox_id field on Task model."""

    def test_task_model_has_sandbox_id(self):
        """
        SPEC: Task model should have sandbox_id field.

        This enables Guardian to detect sandbox mode and route
        interventions through the message injection API.
        """
        from omoi_os.models.task import Task

        task = Task(
            ticket_id="ticket-123",
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            priority="HIGH",
            status="pending",
            description="Test task",
        )

        # This should not raise an error
        task.sandbox_id = "sandbox-xyz-123"
        assert task.sandbox_id == "sandbox-xyz-123"

    def test_task_sandbox_id_defaults_to_none(self):
        """SPEC: sandbox_id should default to None (legacy tasks)."""
        from omoi_os.models.task import Task

        task = Task(
            ticket_id="ticket-123",
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            priority="HIGH",
            status="pending",
        )

        # Legacy tasks should have sandbox_id = None
        assert task.sandbox_id is None


@pytest.mark.unit
class TestGuardianSandboxDetection:
    """Tests for Guardian's ability to detect sandbox mode."""

    def test_guardian_detects_sandbox_task(self):
        """
        SPEC: Guardian should detect when a task is in sandbox mode.
        """
        from omoi_os.services.intelligent_guardian import IntelligentGuardian
        from omoi_os.models.task import Task

        # Create mock guardian (avoid DB dependency)
        mock_db = MagicMock()
        guardian = IntelligentGuardian(db=mock_db)

        # Sandbox task (has sandbox_id)
        sandbox_task = MagicMock(spec=Task)
        sandbox_task.sandbox_id = "sandbox-xyz"
        sandbox_task.conversation_id = "conv-456"
        sandbox_task.persistence_dir = None

        assert guardian._is_sandbox_task(sandbox_task) is True

    def test_guardian_detects_legacy_task(self):
        """
        SPEC: Guardian should detect when a task is legacy (not sandbox).
        """
        from omoi_os.services.intelligent_guardian import IntelligentGuardian
        from omoi_os.models.task import Task

        mock_db = MagicMock()
        guardian = IntelligentGuardian(db=mock_db)

        # Legacy task (no sandbox_id, has persistence_dir)
        legacy_task = MagicMock(spec=Task)
        legacy_task.sandbox_id = None
        legacy_task.conversation_id = "conv-123"
        legacy_task.persistence_dir = "/tmp/openhands/conv-123"

        assert guardian._is_sandbox_task(legacy_task) is False


@pytest.mark.asyncio
@pytest.mark.unit
class TestGuardianInterventionRouting:
    """Tests for Guardian's intervention routing logic."""

    async def test_guardian_intervention_uses_message_injection_for_sandbox(self):
        """
        SPEC: Guardian should POST to message injection endpoint for sandbox agents.
        """
        from omoi_os.services.intelligent_guardian import (
            IntelligentGuardian,
            SteeringIntervention,
        )

        mock_db = MagicMock()
        guardian = IntelligentGuardian(db=mock_db)

        # Create sandbox intervention
        intervention = SteeringIntervention(
            agent_id="agent-456",
            steering_type="guidance",
            message="Please focus on the authentication module.",
            actor_type="guardian",
            actor_id="intelligent_guardian",
            reason="Agent appears to be diverging from task scope.",
            confidence=0.85,
        )

        # Mock task with sandbox_id
        mock_task = MagicMock()
        mock_task.sandbox_id = "sandbox-xyz"
        mock_task.assigned_agent_id = "agent-456"

        with patch.object(
            guardian, "_sandbox_intervention", new_callable=AsyncMock
        ) as mock_sandbox:
            mock_sandbox.return_value = True

            # This should route to _sandbox_intervention
            success = await guardian._execute_intervention_for_task(
                intervention, mock_task
            )

            mock_sandbox.assert_called_once_with(intervention, mock_task)
            assert success is True

    async def test_guardian_intervention_uses_legacy_for_non_sandbox(self):
        """
        SPEC: Guardian should use ConversationInterventionService for legacy agents.
        """
        from omoi_os.services.intelligent_guardian import (
            IntelligentGuardian,
            SteeringIntervention,
        )

        mock_db = MagicMock()
        guardian = IntelligentGuardian(db=mock_db)

        intervention = SteeringIntervention(
            agent_id="agent-789",
            steering_type="guidance",
            message="Please focus on the authentication module.",
            actor_type="guardian",
            actor_id="intelligent_guardian",
            reason="Agent appears diverging.",
            confidence=0.85,
        )

        # Mock legacy task (no sandbox_id)
        mock_task = MagicMock()
        mock_task.sandbox_id = None
        mock_task.conversation_id = "conv-456"
        mock_task.persistence_dir = "/tmp/openhands/conv-456"
        mock_task.assigned_agent_id = "agent-789"

        with patch.object(
            guardian, "_legacy_intervention", new_callable=AsyncMock
        ) as mock_legacy:
            mock_legacy.return_value = True

            success = await guardian._execute_intervention_for_task(
                intervention, mock_task
            )

            mock_legacy.assert_called_once_with(intervention, mock_task)
            assert success is True


@pytest.mark.asyncio
@pytest.mark.unit
class TestSandboxInterventionImplementation:
    """Tests for the actual sandbox intervention HTTP call."""

    async def test_sandbox_intervention_posts_to_message_api(self):
        """
        SPEC: _sandbox_intervention should POST to /sandboxes/{id}/messages.
        """
        from omoi_os.services.intelligent_guardian import (
            IntelligentGuardian,
            SteeringIntervention,
        )

        mock_db = MagicMock()
        guardian = IntelligentGuardian(db=mock_db)

        intervention = SteeringIntervention(
            agent_id="agent-456",
            steering_type="focus_correction",
            message="Please focus on the authentication module.",
            actor_type="guardian",
            actor_id="intelligent_guardian",
            reason="Agent diverging.",
            confidence=0.85,
        )

        mock_task = MagicMock()
        mock_task.sandbox_id = "sandbox-xyz-123"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "queued"}
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            success = await guardian._sandbox_intervention(intervention, mock_task)

            assert success is True
            # Verify the POST was made to the correct endpoint
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "sandbox-xyz-123" in call_args[0][0]
            assert "messages" in call_args[0][0]
            # Verify message type is guardian_nudge
            json_body = call_args[1]["json"]
            assert json_body["message_type"] == "guardian_nudge"
            assert "focus on the authentication" in json_body["content"]


@pytest.mark.integration
class TestEndToEndGuardianSandboxFlow:
    """End-to-end integration tests for Guardian → Sandbox message flow."""

    def test_guardian_message_reaches_sandbox_queue(self, client: TestClient):
        """
        INTEGRATION: Guardian intervention message should be retrievable by worker.
        """
        sandbox_id = "guardian-e2e-test-sandbox"

        # 1. Queue a guardian intervention (simulating Guardian)
        response = client.post(
            f"/api/v1/sandboxes/{sandbox_id}/messages",
            json={
                "content": "[GUARDIAN] Please verify test results before proceeding.",
                "message_type": "guardian_nudge",
            },
        )
        assert response.status_code == 200

        # 2. Worker polls for messages
        response = client.get(f"/api/v1/sandboxes/{sandbox_id}/messages")
        assert response.status_code == 200
        messages = response.json()

        # 3. Should receive the guardian intervention
        assert len(messages) == 1
        assert messages[0]["message_type"] == "guardian_nudge"
        assert "[GUARDIAN]" in messages[0]["content"]

    def test_multiple_message_types_in_queue(self, client: TestClient):
        """
        INTEGRATION: Queue should handle mixed message types correctly.
        """
        sandbox_id = "guardian-mixed-test-sandbox"

        # Queue different message types
        messages_to_send = [
            {"content": "User feedback", "message_type": "user_message"},
            {"content": "Guardian nudge", "message_type": "guardian_nudge"},
            {"content": "System alert", "message_type": "system"},
        ]

        for msg in messages_to_send:
            response = client.post(
                f"/api/v1/sandboxes/{sandbox_id}/messages",
                json=msg,
            )
            assert response.status_code == 200

        # Retrieve all messages
        response = client.get(f"/api/v1/sandboxes/{sandbox_id}/messages")
        messages = response.json()

        # Should have all 3 in FIFO order
        assert len(messages) == 3
        assert messages[0]["message_type"] == "user_message"
        assert messages[1]["message_type"] == "guardian_nudge"
        assert messages[2]["message_type"] == "system"


@pytest.mark.unit
class TestWorkerScriptGuardianHandling:
    """Tests that worker scripts handle guardian messages correctly."""

    def test_openhands_worker_script_handles_guardian_intervention(self):
        """
        SPEC: OpenHands worker script should have guardian_nudge handling.
        """
        from omoi_os.services.daytona_spawner import OPENHANDS_WORKER_SCRIPT

        # Check that script handles guardian_nudge or guardian_intervention
        assert "guardian" in OPENHANDS_WORKER_SCRIPT.lower(), (
            "OpenHands worker script should reference guardian messages"
        )

    def test_claude_worker_script_handles_guardian_intervention(self):
        """
        SPEC: Claude worker script should have guardian_nudge handling.
        """
        from omoi_os.services.daytona_spawner import CLAUDE_WORKER_SCRIPT

        # Check that script handles guardian messages
        assert "guardian" in CLAUDE_WORKER_SCRIPT.lower(), (
            "Claude worker script should reference guardian messages"
        )
