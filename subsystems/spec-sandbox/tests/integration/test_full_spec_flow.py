"""Integration tests for full spec workflow."""

import pytest
from pathlib import Path

from spec_sandbox.config import SpecSandboxSettings
from spec_sandbox.reporters.jsonl import JSONLReporter
from spec_sandbox.schemas.events import EventTypes
from spec_sandbox.worker.state_machine import SpecStateMachine


@pytest.mark.asyncio
async def test_full_spec_flow_with_jsonl(tmp_path):
    """Test full spec flow with JSONL reporter."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    events_file = output_dir / "events.jsonl"

    settings = SpecSandboxSettings(
        spec_id="integration-test",
        spec_title="Integration Test Spec",
        spec_description="Test the full flow",
        output_directory=output_dir,
        reporter_mode="jsonl",
    )

    reporter = JSONLReporter(events_file)
    machine = SpecStateMachine(settings=settings, reporter=reporter)

    success = await machine.run()

    assert success is True

    # Verify events were written
    events = reporter.read_all()
    assert len(events) > 0

    # Verify lifecycle events
    event_types = [e.event_type for e in events]
    assert EventTypes.SPEC_STARTED in event_types
    assert EventTypes.SPEC_COMPLETED in event_types

    # Verify all phases completed
    phase_completed_count = sum(
        1 for e in events if e.event_type == EventTypes.PHASE_COMPLETED
    )
    assert phase_completed_count == 5


@pytest.mark.asyncio
async def test_spec_flow_creates_output_artifacts(tmp_path):
    """Test that spec flow creates expected output directory."""
    output_dir = tmp_path / "spec-output"

    settings = SpecSandboxSettings(
        spec_id="artifact-test",
        output_directory=output_dir,
        reporter_mode="jsonl",
    )

    reporter = JSONLReporter(output_dir / "events.jsonl")
    machine = SpecStateMachine(settings=settings, reporter=reporter)

    await machine.run()

    # Output directory should exist with events file
    assert output_dir.exists()
    assert (output_dir / "events.jsonl").exists()


@pytest.mark.asyncio
async def test_spec_context_passed_between_phases(tmp_path):
    """Test that context accumulates across phases."""
    settings = SpecSandboxSettings(
        spec_id="context-test",
        output_directory=tmp_path,
        reporter_mode="jsonl",
    )

    reporter = JSONLReporter(tmp_path / "events.jsonl")
    machine = SpecStateMachine(settings=settings, reporter=reporter)

    await machine.run()

    # Context should have outputs from all phases
    assert "explore" in machine.context
    assert "codebase_summary" in machine.context["explore"]

    assert "requirements" in machine.context
    assert "requirements" in machine.context["requirements"]

    assert "design" in machine.context
    assert "tasks" in machine.context
    assert "sync" in machine.context
