"""Tests for SpecStateMachine."""

import pytest

from spec_sandbox.config import SpecSandboxSettings
from spec_sandbox.reporters.array import ArrayReporter
from spec_sandbox.schemas.events import EventTypes
from spec_sandbox.schemas.spec import SpecPhase
from spec_sandbox.worker.state_machine import SpecStateMachine


@pytest.mark.asyncio
async def test_state_machine_emits_lifecycle_events():
    """State machine should emit spec_started and spec_completed events."""
    reporter = ArrayReporter()
    settings = SpecSandboxSettings(
        spec_id="test-sm",
        spec_title="Test Spec",
        spec_description="Build something",
        reporter_mode="array",
    )

    machine = SpecStateMachine(settings=settings, reporter=reporter)

    success = await machine.run()

    assert success is True
    assert reporter.has_event(EventTypes.SPEC_STARTED)
    assert reporter.has_event(EventTypes.SPEC_COMPLETED)


@pytest.mark.asyncio
async def test_state_machine_emits_phase_events():
    """State machine should emit phase_started and phase_completed for each phase."""
    reporter = ArrayReporter()
    settings = SpecSandboxSettings(
        spec_id="test-sm",
        reporter_mode="array",
    )

    machine = SpecStateMachine(settings=settings, reporter=reporter)

    await machine.run()

    # Should have 5 phase starts and 5 phase completions
    phase_starts = reporter.get_events_by_type(EventTypes.PHASE_STARTED)
    phase_completions = reporter.get_events_by_type(EventTypes.PHASE_COMPLETED)

    assert len(phase_starts) == 5
    assert len(phase_completions) == 5

    # Verify all phases were run
    phases_started = {e.phase for e in phase_starts}
    assert phases_started == {"explore", "requirements", "design", "tasks", "sync"}


@pytest.mark.asyncio
async def test_state_machine_single_phase():
    """State machine should run only specified phase when spec_phase is set."""
    reporter = ArrayReporter()
    settings = SpecSandboxSettings(
        spec_id="test-single",
        spec_phase="explore",
        reporter_mode="array",
    )

    machine = SpecStateMachine(settings=settings, reporter=reporter)

    await machine.run()

    # Should have only one phase
    phase_starts = reporter.get_events_by_type(EventTypes.PHASE_STARTED)
    assert len(phase_starts) == 1
    assert phase_starts[0].phase == "explore"


@pytest.mark.asyncio
async def test_state_machine_stores_phase_results():
    """State machine should store results for each phase."""
    reporter = ArrayReporter()
    settings = SpecSandboxSettings(
        spec_id="test-results",
        reporter_mode="array",
    )

    machine = SpecStateMachine(settings=settings, reporter=reporter)

    await machine.run()

    # All phases should have results
    assert len(machine.phase_results) == 5

    # Check explore phase result
    explore_result = machine.phase_results[SpecPhase.EXPLORE]
    assert explore_result.success is True
    assert explore_result.eval_score is not None


@pytest.mark.asyncio
async def test_state_machine_accumulates_context():
    """State machine should accumulate context from phase outputs."""
    reporter = ArrayReporter()
    settings = SpecSandboxSettings(
        spec_id="test-context",
        reporter_mode="array",
    )

    machine = SpecStateMachine(settings=settings, reporter=reporter)

    await machine.run()

    # Context should have outputs from all phases
    assert "explore" in machine.context
    assert "requirements" in machine.context
    assert "design" in machine.context
    assert "tasks" in machine.context
    assert "sync" in machine.context


@pytest.mark.asyncio
async def test_run_phase_returns_result():
    """run_phase should return a PhaseResult."""
    reporter = ArrayReporter()
    settings = SpecSandboxSettings(
        spec_id="test-phase",
        reporter_mode="array",
    )

    machine = SpecStateMachine(settings=settings, reporter=reporter)

    result = await machine.run_phase(SpecPhase.EXPLORE)

    assert result.phase == SpecPhase.EXPLORE
    assert result.success is True
    assert result.duration_seconds is not None
    assert result.duration_seconds > 0


@pytest.mark.asyncio
async def test_state_machine_spec_started_data():
    """spec_started event should include title and description."""
    reporter = ArrayReporter()
    settings = SpecSandboxSettings(
        spec_id="test-data",
        spec_title="My Spec",
        spec_description="Build a thing",
        reporter_mode="array",
    )

    machine = SpecStateMachine(settings=settings, reporter=reporter)

    await machine.run()

    started_event = reporter.get_latest(EventTypes.SPEC_STARTED)
    assert started_event is not None
    assert started_event.data["title"] == "My Spec"
    assert started_event.data["description"] == "Build a thing"


@pytest.mark.asyncio
async def test_state_machine_phase_completed_has_score():
    """phase_completed events should include eval_score."""
    reporter = ArrayReporter()
    settings = SpecSandboxSettings(
        spec_id="test-score",
        reporter_mode="array",
    )

    machine = SpecStateMachine(settings=settings, reporter=reporter)

    await machine.run()

    completed_events = reporter.get_events_by_type(EventTypes.PHASE_COMPLETED)

    for event in completed_events:
        assert "eval_score" in event.data
        assert "duration_seconds" in event.data
