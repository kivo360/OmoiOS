"""Tests for monitoring replay service."""

import json
import pytest
import dataclasses
from pathlib import Path

from omoi_os.services.monitoring_replay import (
    AgentSessionSnapshot,
    MonitoringReplayService,
    AgentSessionRecorder,
)


@pytest.fixture
def tmp_recording_dir(tmp_path):
    """Create a temporary recording directory with sample data."""
    sessions_dir = tmp_path / "agent-sessions"
    sessions_dir.mkdir(parents=True)

    # Agent that completed successfully
    agent1 = {
        "agent_id": "agent-1",
        "task_id": "task-abc",
        "sandbox_id": "sb-1",
        "phase": "implementation",
        "started_at": "2026-03-01T12:00:00Z",
        "events": [{"type": "started"}, {"type": "tool_call"}, {"type": "completed"}],
        "tool_calls": [{"tool": "edit_file", "file": "src/auth.py"}],
        "current_output": "Implemented auth",
        "task_description": "Implement authentication middleware",
        "elapsed_seconds": 30,
        "status": "completed",
    }
    (sessions_dir / "agent-1.json").write_text(json.dumps(agent1))

    # Agent that is stuck
    agent2 = {
        "agent_id": "agent-2",
        "task_id": "task-def",
        "sandbox_id": "sb-2",
        "phase": "implementation",
        "started_at": "2026-03-01T12:00:00Z",
        "events": [],
        "tool_calls": [],
        "current_output": "",
        "task_description": "Write tests for authentication",
        "elapsed_seconds": 120,
        "status": "running",
    }
    (sessions_dir / "agent-2.json").write_text(json.dumps(agent2))

    # Agent with overlapping work
    agent3 = {
        "agent_id": "agent-3",
        "task_id": "task-ghi",
        "sandbox_id": "sb-3",
        "phase": "implementation",
        "started_at": "2026-03-01T12:01:00Z",
        "events": [{"type": "started"}, {"type": "tool_call"}],
        "tool_calls": [{"tool": "edit_file", "file": "src/auth.py"}],
        "current_output": "Working on auth",
        "task_description": "Implement authentication middleware for API",
        "elapsed_seconds": 60,
        "status": "running",
    }
    (sessions_dir / "agent-3.json").write_text(json.dumps(agent3))

    return tmp_path


class TestAgentSessionSnapshot:
    def test_creation(self):
        s = AgentSessionSnapshot(
            agent_id="a1",
            task_id="t1",
            sandbox_id="sb1",
            phase="impl",
            started_at="2026-01-01T00:00:00Z",
        )
        assert s.agent_id == "a1"
        assert s.events == []
        assert s.status == "running"

    def test_with_data(self):
        s = AgentSessionSnapshot(
            agent_id="a1",
            task_id="t1",
            sandbox_id="sb1",
            phase="impl",
            started_at="2026-01-01T00:00:00Z",
            events=[{"type": "started"}],
            tool_calls=[{"tool": "edit"}],
            current_output="Done",
            elapsed_seconds=30,
            status="completed",
        )
        assert len(s.events) == 1
        assert s.status == "completed"


class TestGuardianReplay:
    def test_completed_agent_high_score(self, tmp_recording_dir):
        svc = MonitoringReplayService(replay_dir=str(tmp_recording_dir))
        result = svc.replay_guardian("agent-sessions/agent-1.json")
        assert result.agent_id == "agent-1"
        assert result.trajectory_score > 0.5
        assert result.alignment_score > 0.8
        assert not result.would_intervene

    def test_stuck_agent_low_score(self, tmp_recording_dir):
        svc = MonitoringReplayService(replay_dir=str(tmp_recording_dir))
        result = svc.replay_guardian("agent-sessions/agent-2.json")
        assert result.agent_id == "agent-2"
        assert result.alignment_score < 0.6
        assert result.would_intervene
        assert result.intervention_type == "restart"

    def test_json_serializable(self, tmp_recording_dir):
        svc = MonitoringReplayService(replay_dir=str(tmp_recording_dir))
        result = svc.replay_guardian("agent-sessions/agent-1.json")
        json.dumps(dataclasses.asdict(result))


class TestConductorReplay:
    def test_single_session(self, tmp_recording_dir):
        svc = MonitoringReplayService(replay_dir=str(tmp_recording_dir))
        result = svc.replay_conductor(["agent-sessions/agent-1.json"])
        assert result.sessions_analyzed == 1
        assert result.coherence_score == 1.0

    def test_overlapping_agents(self, tmp_recording_dir):
        svc = MonitoringReplayService(replay_dir=str(tmp_recording_dir))
        result = svc.replay_conductor(
            [
                "agent-sessions/agent-1.json",
                "agent-sessions/agent-3.json",
            ]
        )
        assert result.sessions_analyzed == 2
        # agent-1 and agent-3 both edit src/auth.py
        assert len(result.coordination_issues) > 0

    def test_duplicate_detection(self, tmp_recording_dir):
        svc = MonitoringReplayService(replay_dir=str(tmp_recording_dir))
        result = svc.replay_conductor(
            [
                "agent-sessions/agent-1.json",
                "agent-sessions/agent-3.json",
            ]
        )
        # "Implement authentication middleware" vs "Implement authentication middleware for API"
        assert len(result.duplicates_detected) > 0

    def test_empty_sessions(self, tmp_recording_dir):
        svc = MonitoringReplayService(replay_dir=str(tmp_recording_dir))
        result = svc.replay_conductor([])
        assert result.sessions_analyzed == 0
        assert result.coherence_score == 1.0

    def test_json_serializable(self, tmp_recording_dir):
        svc = MonitoringReplayService(replay_dir=str(tmp_recording_dir))
        result = svc.replay_conductor(
            [
                "agent-sessions/agent-1.json",
                "agent-sessions/agent-2.json",
            ]
        )
        json.dumps(dataclasses.asdict(result))


class TestListRecordings:
    def test_list(self, tmp_recording_dir):
        svc = MonitoringReplayService(replay_dir=str(tmp_recording_dir))
        recordings = svc.list_recordings()
        assert len(recordings) == 3

    def test_list_empty_dir(self, tmp_path):
        svc = MonitoringReplayService(replay_dir=str(tmp_path / "nonexistent"))
        assert svc.list_recordings() == []


class TestAgentSessionRecorder:
    def test_start_and_end_session(self, tmp_path):
        recorder = AgentSessionRecorder(recording_dir=str(tmp_path))
        recorder.start_session(
            agent_id="a1",
            task_id="task-123",
            sandbox_id="sb-1",
            phase="impl",
            task_description="Test task",
        )
        assert "a1" in recorder.list_active()

        recorder.record_event("a1", {"type": "started"})
        recorder.record_tool_call("a1", {"tool": "edit", "file": "x.py"})
        recorder.update_output("a1", "Some output")

        filepath = recorder.end_session("a1", status="completed")
        assert filepath is not None
        assert Path(filepath).exists()

        # Verify saved data
        with open(filepath) as f:
            data = json.load(f)
        assert data["agent_id"] == "a1"
        assert data["status"] == "completed"
        assert len(data["events"]) == 1

    def test_end_nonexistent_session(self, tmp_path):
        recorder = AgentSessionRecorder(recording_dir=str(tmp_path))
        result = recorder.end_session("nonexistent")
        assert result is None

    def test_record_event_nonexistent_agent(self, tmp_path):
        recorder = AgentSessionRecorder(recording_dir=str(tmp_path))
        # Should not raise
        recorder.record_event("nonexistent", {"type": "test"})


class TestMonitoringSettings:
    def test_replay_mode_class_default(self):
        """Test the class default values for replay settings."""
        # Test the class default directly, bypassing YAML config
        from omoi_os.services.monitoring_replay import MonitoringReplayService

        svc = MonitoringReplayService()
        assert svc._replay_dir == Path(".monitoring-recordings")


class TestCLI:
    def test_format_guardian_output(self, tmp_recording_dir):
        """Test the guardian replay produces reasonable output."""
        svc = MonitoringReplayService(replay_dir=str(tmp_recording_dir))
        result = svc.replay_guardian("agent-sessions/agent-1.json")
        # Verify result has expected fields
        assert isinstance(result.trajectory_score, float)
        assert isinstance(result.alignment_score, float)
        assert isinstance(result.would_intervene, bool)
