"""Tests for sync contract between spec-sandbox and backend.

These tests verify that the data formats and event types produced by
spec-sandbox reporters match what the backend expects.

Contract Requirements (from backend/omoi_os/api/routes/sandbox.py):
1. Events are sent to POST /api/v1/sandbox/events with SandboxEventCreate schema
2. Sync summaries sent to POST /api/v1/sandbox/sync-summary
3. Backend expects "agent.completed" event with spec_id and phase_data to update Spec model
4. Event schema: {event_type: str, event_data: dict, source: "agent"|"worker"|"system"}
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from spec_sandbox.reporters.array import ArrayReporter
from spec_sandbox.reporters.http import HTTPReporter
from spec_sandbox.schemas.events import Event, EventTypes


# ============================================================================
# SYNC SUMMARY FORMAT TESTS
# ============================================================================


class TestSyncSummaryFormat:
    """Test that sync_summary payload matches backend expectations."""

    @pytest.mark.asyncio
    async def test_sync_summary_contains_required_fields(self):
        """Sync summary must contain all fields expected by backend."""
        reporter = HTTPReporter(callback_url="http://localhost:8000", sandbox_id="test-sandbox-123")

        # Sample sync output from SpecStateMachine
        sync_output = {
            "ready_for_execution": True,
            "traceability_stats": {
                "requirements": {"total": 10, "covered": 10},
                "tasks": {"total": 15, "completed": 0},
                "orphans": {},
            },
            "spec_summary": {
                "total_requirements": 10,
                "total_tasks": 15,
                "total_estimated_hours": 40.5,
                "files_to_modify": 5,
                "files_to_create": 3,
                "requirement_coverage_percent": 100.0,
            },
            "validation_results": {
                "all_requirements_covered": True,
                "all_components_have_tasks": True,
                "dependency_order_valid": True,
                "no_circular_dependencies": True,
                "issues_found": [],
            },
            "coverage_matrix": [
                {"requirement": "REQ-001", "tasks": ["TASK-001", "TASK-002"]},
            ],
            "blockers": [],
        }

        phase_data = {
            "explore": {"codebase_summary": "Python project"},
            "requirements": {"requirements": []},
            "design": {"components": []},
            "tasks": {"tasks": []},
        }

        # Mock the HTTP client to avoid actual requests
        with patch.object(reporter, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            await reporter.report_sync_summary(
                spec_id="test-spec-123",
                sync_output=sync_output,
                phase_data=phase_data,
            )

            # Verify the payload structure
            call_args = mock_client.post.call_args
            url = call_args[0][0]
            payload = call_args[1]["json"]

            # URL should be the sandbox events endpoint
            assert "/api/v1/sandboxes/" in url
            assert url.endswith("/events")

            # Event format
            assert payload["event_type"] == "agent.completed"
            assert payload["source"] == "agent"

            # Event data contains sync_summary
            event_data = payload["event_data"]
            assert event_data["spec_id"] == "test-spec-123"

            # Sync summary within event_data
            sync_summary = event_data["sync_summary"]
            assert sync_summary["spec_id"] == "test-spec-123"
            assert sync_summary["status"] in ["completed", "blocked"]

            # Traceability section
            assert "traceability" in sync_summary
            assert "requirements" in sync_summary["traceability"]
            assert "tasks" in sync_summary["traceability"]
            assert "orphans" in sync_summary["traceability"]

            # Validation section
            assert "validation" in sync_summary
            assert "all_requirements_covered" in sync_summary["validation"]
            assert "all_components_have_tasks" in sync_summary["validation"]
            assert "dependency_order_valid" in sync_summary["validation"]
            assert "issues" in sync_summary["validation"]

            # Summary section
            assert "summary" in sync_summary
            assert "total_requirements" in sync_summary["summary"]
            assert "total_tasks" in sync_summary["summary"]
            assert "total_estimated_hours" in sync_summary["summary"]

            # Phase data for backend Spec model update
            assert "phase_data" in event_data
            assert event_data["phase_data"] == phase_data

    @pytest.mark.asyncio
    async def test_sync_summary_status_blocked_when_not_ready(self):
        """Sync summary status should be 'blocked' when ready_for_execution is False."""
        reporter = HTTPReporter(callback_url="http://localhost:8000", sandbox_id="test-sandbox-123")

        sync_output = {
            "ready_for_execution": False,  # Not ready
            "traceability_stats": {},
            "spec_summary": {},
            "validation_results": {},
            "coverage_matrix": [],
            "blockers": ["Missing coverage for REQ-003"],
        }

        with patch.object(reporter, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            await reporter.report_sync_summary(
                spec_id="test-spec",
                sync_output=sync_output,
            )

            payload = mock_client.post.call_args[1]["json"]
            sync_summary = payload["event_data"]["sync_summary"]
            assert sync_summary["status"] == "blocked"
            assert "Missing coverage" in sync_summary["blockers"][0]

    @pytest.mark.asyncio
    async def test_sync_summary_stored_for_inspection(self):
        """Sync summary should be stored on reporter for test inspection."""
        reporter = HTTPReporter(callback_url="http://localhost:8000", sandbox_id="test-sandbox-123")

        sync_output = {
            "ready_for_execution": True,
            "traceability_stats": {"requirements": {"total": 5, "covered": 5}},
            "spec_summary": {"total_requirements": 5},
            "validation_results": {},
            "coverage_matrix": [],
            "blockers": [],
        }

        with patch.object(reporter, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            await reporter.report_sync_summary(
                spec_id="test-spec",
                sync_output=sync_output,
            )

            # Verify sync_summary is accessible
            assert reporter.sync_summary is not None
            assert reporter.sync_summary["spec_id"] == "test-spec"


# ============================================================================
# EVENT SCHEMA CONTRACT TESTS
# ============================================================================


class TestEventSchemaContract:
    """Test that events match backend SandboxEventCreate schema."""

    def test_event_serializes_to_backend_format(self):
        """Event.model_dump should produce backend-compatible dict."""
        event = Event(
            event_type=EventTypes.SPEC_COMPLETED,
            spec_id="test-spec-123",
            phase="sync",
            data={
                "phases_completed": ["explore", "requirements", "design", "tasks"],
                "markdown_artifacts": {"requirements.md": "/path/to/file"},
            },
        )

        serialized = event.model_dump(mode="json")

        # Backend expects these fields
        assert "event_type" in serialized
        assert "spec_id" in serialized
        assert "data" in serialized
        assert "timestamp" in serialized

        # event_type should be a string
        assert isinstance(serialized["event_type"], str)

        # data should be a dict (not nested Event)
        assert isinstance(serialized["data"], dict)

    def test_event_data_is_json_serializable(self):
        """Event data must be JSON-serializable for HTTP transport."""
        import json

        event = Event(
            event_type="test",
            spec_id="spec-123",
            data={
                "nested": {"key": "value"},
                "list": [1, 2, 3],
                "float": 42.5,
                "bool": True,
                "none": None,
            },
        )

        # Should not raise
        serialized = event.model_dump(mode="json")
        json_str = json.dumps(serialized)
        roundtrip = json.loads(json_str)

        assert roundtrip["data"]["nested"]["key"] == "value"
        assert roundtrip["data"]["list"] == [1, 2, 3]

    def test_event_timestamp_is_iso_format(self):
        """Timestamp should serialize to ISO format for backend."""
        event = Event(
            event_type="test",
            spec_id="spec-123",
        )

        serialized = event.model_dump(mode="json")

        # Timestamp should be a string in ISO format
        assert isinstance(serialized["timestamp"], str)
        # Should be parseable
        datetime.fromisoformat(serialized["timestamp"].replace("Z", "+00:00"))


# ============================================================================
# SPEC_ID ROUTING TESTS
# ============================================================================


class TestSpecIdRouting:
    """Test that spec_id is properly included for backend routing."""

    @pytest.mark.asyncio
    async def test_all_events_include_spec_id(self):
        """All events should include spec_id for backend routing."""
        reporter = ArrayReporter()

        # Simulate a typical event sequence
        events_to_emit = [
            Event(
                event_type=EventTypes.SPEC_STARTED,
                spec_id="test-spec",
                data={"title": "Test Spec"},
            ),
            Event(
                event_type=EventTypes.PHASE_STARTED,
                spec_id="test-spec",
                phase="explore",
            ),
            Event(
                event_type=EventTypes.PHASE_COMPLETED,
                spec_id="test-spec",
                phase="explore",
                data={"duration_seconds": 10.5},
            ),
            Event(
                event_type=EventTypes.SPEC_COMPLETED,
                spec_id="test-spec",
                data={"phases_completed": ["explore"]},
            ),
        ]

        for event in events_to_emit:
            await reporter.report(event)

        # Verify all events have spec_id
        for event in reporter.events:
            assert event.spec_id == "test-spec", (
                f"Event {event.event_type} missing spec_id"
            )

    def test_spec_id_required_in_event(self):
        """Event should have spec_id field."""
        event = Event(
            event_type="test",
            spec_id="required-spec-id",
        )

        assert event.spec_id == "required-spec-id"
        serialized = event.model_dump(mode="json")
        assert serialized["spec_id"] == "required-spec-id"


# ============================================================================
# AGENT.COMPLETED EVENT TESTS
# ============================================================================


class TestAgentCompletedEvent:
    """Test that agent.completed event is emitted with phase_data.

    The backend expects an "agent.completed" event with:
    - spec_id: to identify which Spec to update
    - phase_data: dict of phase name -> phase content

    This triggers _update_spec_phase_data() in the backend.
    """

    @pytest.mark.asyncio
    async def test_agent_completed_event_format(self):
        """agent.completed event should have correct format for backend."""
        # This is the format the backend expects
        agent_completed_event = Event(
            event_type="agent.completed",
            spec_id="spec-uuid-123",
            data={
                "spec_id": "spec-uuid-123",  # Also in data for backend routing
                "success": True,
                "phase_data": {
                    "explore": {
                        "codebase_summary": "Python project with FastAPI",
                        "files_analyzed": 50,
                    },
                    "requirements": {
                        "requirements": [
                            {"id": "REQ-001", "title": "User Authentication"},
                        ],
                    },
                    "design": {
                        "components": [
                            {"name": "AuthService", "type": "service"},
                        ],
                    },
                    "tasks": {
                        "tasks": [
                            {"id": "TASK-001", "title": "Implement login"},
                        ],
                    },
                },
            },
        )

        serialized = agent_completed_event.model_dump(mode="json")

        # Backend checks for these
        assert serialized["event_type"] == "agent.completed"
        assert serialized["data"]["spec_id"] == "spec-uuid-123"
        assert serialized["data"]["success"] is True
        assert "phase_data" in serialized["data"]

        # phase_data should have expected structure
        phase_data = serialized["data"]["phase_data"]
        assert "explore" in phase_data
        assert "requirements" in phase_data
        assert "design" in phase_data
        assert "tasks" in phase_data

    @pytest.mark.asyncio
    async def test_phase_data_has_expected_keys(self):
        """phase_data for each phase should have expected content."""
        phase_data = {
            "explore": {
                "codebase_summary": "string",
                "file_tree": "string",
                "key_files": ["list"],
            },
            "requirements": {
                "requirements": [],  # List of requirement dicts
            },
            "design": {
                "components": [],  # List of component dicts
                "architecture": "string",
            },
            "tasks": {
                "tasks": [],  # List of task dicts
            },
        }

        event = Event(
            event_type="agent.completed",
            spec_id="test",
            data={"phase_data": phase_data, "success": True},
        )

        serialized = event.model_dump(mode="json")
        pd = serialized["data"]["phase_data"]

        # Each phase should be a dict
        assert isinstance(pd["explore"], dict)
        assert isinstance(pd["requirements"], dict)
        assert isinstance(pd["design"], dict)
        assert isinstance(pd["tasks"], dict)


# ============================================================================
# HTTP REPORTER EVENT BATCHING TESTS
# ============================================================================


class TestHTTPReporterBatching:
    """Test that HTTPReporter sends events to backend when batch size reached."""

    @pytest.mark.asyncio
    async def test_events_sent_on_batch_size(self):
        """Events should be sent individually when batch size is reached."""
        reporter = HTTPReporter(callback_url="http://localhost:8000", sandbox_id="test-sandbox-123", batch_size=2)

        events = [
            Event(event_type="a", spec_id="test"),
            Event(event_type="b", spec_id="test"),
        ]

        with patch.object(reporter, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            # Report two events (triggers flush due to batch_size=2)
            await reporter.report(events[0])
            await reporter.report(events[1])

            # Should have sent events (one call per event)
            assert mock_client.post.call_count == 2

            # Verify both events were sent
            call_args_list = mock_client.post.call_args_list
            assert call_args_list[0][1]["json"]["event_type"] == "a"
            assert call_args_list[1][1]["json"]["event_type"] == "b"

    @pytest.mark.asyncio
    async def test_flush_sends_remaining_events(self):
        """flush() should send any remaining buffered events."""
        reporter = HTTPReporter(callback_url="http://localhost:8000", sandbox_id="test-sandbox-123", batch_size=10)

        event = Event(event_type="single", spec_id="test")

        with patch.object(reporter, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            await reporter.report(event)
            # Not yet sent (batch_size=10)
            assert not mock_client.post.called

            await reporter.flush()
            # Now sent
            assert mock_client.post.called
            payload = mock_client.post.call_args[1]["json"]
            assert payload["event_type"] == "single"


# ============================================================================
# INTEGRATION: FULL SYNC FLOW SIMULATION
# ============================================================================


class TestSyncFlowSimulation:
    """Simulate the full sync flow using ArrayReporter."""

    @pytest.mark.asyncio
    async def test_full_spec_event_sequence(self):
        """Verify the complete event sequence for a spec run."""
        reporter = ArrayReporter()

        # Simulate the full spec workflow
        spec_id = "test-spec-uuid"

        # 1. Spec started
        await reporter.report(Event(
            event_type=EventTypes.SPEC_STARTED,
            spec_id=spec_id,
            data={"title": "Test Feature", "phases": ["explore", "requirements", "design", "tasks", "sync"]},
        ))

        # 2. Each phase
        phases = ["explore", "requirements", "design", "tasks", "sync"]
        phase_outputs = {}

        for phase in phases:
            await reporter.report(Event(
                event_type=EventTypes.PHASE_STARTED,
                spec_id=spec_id,
                phase=phase,
            ))

            # Simulate phase output
            phase_outputs[phase] = {f"{phase}_result": f"data for {phase}"}

            await reporter.report(Event(
                event_type=EventTypes.PHASE_COMPLETED,
                spec_id=spec_id,
                phase=phase,
                data={"output": phase_outputs[phase], "duration_seconds": 5.0},
            ))

        # 3. Spec completed
        await reporter.report(Event(
            event_type=EventTypes.SPEC_COMPLETED,
            spec_id=spec_id,
            data={
                "phases_completed": phases,
                "markdown_artifacts": {"requirements.md": "/path"},
            },
        ))

        # 4. Agent completed (for backend phase_data update)
        await reporter.report(Event(
            event_type="agent.completed",
            spec_id=spec_id,
            data={
                "spec_id": spec_id,
                "success": True,
                "phase_data": phase_outputs,
            },
        ))

        # Verify event sequence
        assert len(reporter.events) > 0

        # Check we have the key events
        assert reporter.has_event(EventTypes.SPEC_STARTED)
        assert reporter.has_event(EventTypes.SPEC_COMPLETED)
        assert reporter.has_event("agent.completed")

        # Check agent.completed has phase_data
        agent_completed = reporter.get_latest("agent.completed")
        assert agent_completed is not None
        assert "phase_data" in agent_completed.data
        assert "explore" in agent_completed.data["phase_data"]

    @pytest.mark.asyncio
    async def test_events_can_be_exported_for_jsonl(self):
        """Events should export correctly for JSONL format."""
        import json

        reporter = ArrayReporter()

        await reporter.report(Event(
            event_type=EventTypes.SPEC_STARTED,
            spec_id="test",
            data={"title": "Test"},
        ))

        # Export to list of dicts
        event_list = reporter.to_list()

        # Each event should be JSON-serializable
        for event_dict in event_list:
            json_str = json.dumps(event_dict)
            roundtrip = json.loads(json_str)
            assert roundtrip["event_type"] == event_dict["event_type"]
