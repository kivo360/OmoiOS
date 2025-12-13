"""
Phase 3: Worker Script Integration Tests

These tests verify that worker scripts are correctly configured to use
the new sandbox endpoints and support message injection.
"""

import pytest


class TestWorkerScriptEndpoints:
    """Test that worker scripts use the correct sandbox endpoints."""

    def test_worker_script_reports_to_sandbox_endpoint(self):
        """
        SPEC: Worker script should POST events to /api/v1/sandboxes/{id}/events
        (not the old /tasks/{id}/events endpoint).
        """
        from omoi_os.services.daytona_spawner import DaytonaSpawnerService

        spawner = DaytonaSpawnerService()
        script = spawner._get_worker_script()

        # Verify script POSTs to sandbox endpoint
        assert "/api/v1/sandboxes/" in script or "sandboxes/{" in script.lower()
        assert "/events" in script

    def test_claude_worker_script_reports_to_sandbox_endpoint(self):
        """
        SPEC: Claude worker script should POST events to /api/v1/sandboxes/{id}/events.
        """
        from omoi_os.services.daytona_spawner import DaytonaSpawnerService

        spawner = DaytonaSpawnerService()
        script = spawner._get_claude_worker_script()

        # Verify script POSTs to sandbox endpoint
        assert "/api/v1/sandboxes/" in script
        assert "/events" in script


class TestWorkerScriptMessagePolling:
    """Test that worker scripts poll for messages."""

    def test_worker_script_polls_for_messages(self):
        """
        SPEC: Worker script should poll GET /api/v1/sandboxes/{id}/messages.
        """
        from omoi_os.services.daytona_spawner import DaytonaSpawnerService

        spawner = DaytonaSpawnerService()
        script = spawner._get_worker_script()

        # Verify script has message polling
        assert "/messages" in script
        assert "poll" in script.lower() or "get" in script.lower()

    def test_claude_worker_script_polls_for_messages(self):
        """
        SPEC: Claude worker script should poll GET /api/v1/sandboxes/{id}/messages.
        """
        from omoi_os.services.daytona_spawner import DaytonaSpawnerService

        spawner = DaytonaSpawnerService()
        script = spawner._get_claude_worker_script()

        # Verify script has message polling
        assert "/messages" in script
        assert "poll" in script.lower()


class TestWorkerScriptInterruptHandling:
    """Test that worker scripts handle interrupt messages."""

    def test_worker_script_handles_interrupt(self):
        """
        SPEC: Worker script should handle "interrupt" message type.
        """
        from omoi_os.services.daytona_spawner import DaytonaSpawnerService

        spawner = DaytonaSpawnerService()
        script = spawner._get_worker_script()

        assert "interrupt" in script.lower()

    def test_claude_worker_script_handles_interrupt(self):
        """
        SPEC: Claude worker script should handle "interrupt" message type.
        """
        from omoi_os.services.daytona_spawner import DaytonaSpawnerService

        spawner = DaytonaSpawnerService()
        script = spawner._get_claude_worker_script()

        assert "interrupt" in script.lower()


class TestClaudeWorkerHooks:
    """Test Claude worker script hook configuration."""

    def test_claude_worker_has_pretooluse_hook(self):
        """
        SPEC: Claude worker script should register PreToolUse hook for interventions.
        """
        from omoi_os.services.daytona_spawner import DaytonaSpawnerService

        spawner = DaytonaSpawnerService()
        script = spawner._get_claude_worker_script()

        # Verify hook registration
        assert "PreToolUse" in script
        assert (
            "check_pending_messages" in script or "pending_messages" in script.lower()
        )

    def test_claude_worker_has_posttooluse_hook(self):
        """
        SPEC: Claude worker script should have PostToolUse hook for tracking.
        """
        from omoi_os.services.daytona_spawner import DaytonaSpawnerService

        spawner = DaytonaSpawnerService()
        script = spawner._get_claude_worker_script()

        # Verify PostToolUse hook
        assert "PostToolUse" in script
        assert "track_tool" in script.lower() or "tool_use" in script.lower()


class TestOpenHandsWorkerCallbacks:
    """Test OpenHands worker script callback configuration."""

    def test_openhands_worker_has_event_callback(self):
        """
        SPEC: OpenHands worker should have event callback for message injection.
        """
        from omoi_os.services.daytona_spawner import DaytonaSpawnerService

        spawner = DaytonaSpawnerService()
        script = spawner._get_worker_script()

        # Verify callback configuration
        assert "callback" in script.lower()
        assert "poll_messages" in script or "poll" in script.lower()


@pytest.mark.integration
@pytest.mark.sandbox
@pytest.mark.asyncio
async def test_end_to_end_worker_event_flow(client, event_bus_service):
    """
    INTEGRATION: Simulate worker posting event, verify it's received.

    This simulates what happens when a real worker runs in Daytona.
    """

    sandbox_id = "e2e-worker-test"

    # Simulate worker posting event (like real worker would)
    response = client.post(
        f"/api/v1/sandboxes/{sandbox_id}/events",
        json={
            "event_type": "agent.tool_use",
            "event_data": {
                "tool": "write_file",
                "path": "/workspace/src/main.py",
                "success": True,
            },
            "source": "agent",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert data["sandbox_id"] == sandbox_id
    assert data["event_type"] == "agent.tool_use"


@pytest.mark.integration
@pytest.mark.sandbox
def test_worker_message_polling_flow(client):
    """
    INTEGRATION: Test the full message injection flow that workers use.

    1. Post message to queue
    2. Poll for messages (simulating worker)
    3. Verify messages are consumed
    """
    sandbox_id = "worker-message-test"

    # Step 1: Queue a message (UI/Guardian would do this)
    post_response = client.post(
        f"/api/v1/sandboxes/{sandbox_id}/messages",
        json={
            "content": "Focus on the authentication module",
            "message_type": "user_message",
        },
    )
    assert post_response.status_code == 200
    assert post_response.json()["status"] == "queued"

    # Step 2: Poll for messages (worker does this)
    get_response = client.get(f"/api/v1/sandboxes/{sandbox_id}/messages")
    assert get_response.status_code == 200
    messages = get_response.json()
    assert len(messages) == 1
    assert messages[0]["content"] == "Focus on the authentication module"
    assert messages[0]["message_type"] == "user_message"

    # Step 3: Verify consumed (second poll should be empty)
    second_get = client.get(f"/api/v1/sandboxes/{sandbox_id}/messages")
    assert second_get.status_code == 200
    assert len(second_get.json()) == 0


@pytest.mark.integration
@pytest.mark.sandbox
def test_worker_interrupt_handling_flow(client):
    """
    INTEGRATION: Test interrupt message handling that workers use.
    """
    sandbox_id = "worker-interrupt-test"

    # Queue an interrupt
    response = client.post(
        f"/api/v1/sandboxes/{sandbox_id}/messages",
        json={
            "content": "Stop and await new instructions",
            "message_type": "interrupt",
        },
    )
    assert response.status_code == 200

    # Worker polls and gets the interrupt
    messages_response = client.get(f"/api/v1/sandboxes/{sandbox_id}/messages")
    messages = messages_response.json()
    assert len(messages) == 1
    assert messages[0]["message_type"] == "interrupt"
    assert "Stop" in messages[0]["content"]
