"""Tests for ArrayReporter."""

import pytest

from spec_sandbox.reporters.array import ArrayReporter
from spec_sandbox.schemas.events import Event, EventTypes


@pytest.mark.asyncio
async def test_array_reporter_collects_events():
    """ArrayReporter should collect events in memory."""
    reporter = ArrayReporter()

    await reporter.report(
        Event(
            event_type=EventTypes.SPEC_STARTED,
            spec_id="test-123",
        )
    )
    await reporter.report(
        Event(
            event_type=EventTypes.PHASE_STARTED,
            spec_id="test-123",
            phase="explore",
        )
    )

    assert len(reporter.events) == 2
    assert reporter.has_event(EventTypes.SPEC_STARTED)
    assert reporter.has_event(EventTypes.PHASE_STARTED)


@pytest.mark.asyncio
async def test_array_reporter_get_events_by_type():
    """get_events_by_type should filter correctly."""
    reporter = ArrayReporter()

    await reporter.report(Event(event_type="a", spec_id="test"))
    await reporter.report(Event(event_type="b", spec_id="test"))
    await reporter.report(Event(event_type="a", spec_id="test"))

    a_events = reporter.get_events_by_type("a")
    assert len(a_events) == 2

    b_events = reporter.get_events_by_type("b")
    assert len(b_events) == 1


@pytest.mark.asyncio
async def test_array_reporter_get_events_by_phase():
    """get_events_by_phase should filter correctly."""
    reporter = ArrayReporter()

    await reporter.report(Event(event_type="a", spec_id="test", phase="explore"))
    await reporter.report(Event(event_type="b", spec_id="test", phase="design"))
    await reporter.report(Event(event_type="c", spec_id="test", phase="explore"))

    explore_events = reporter.get_events_by_phase("explore")
    assert len(explore_events) == 2

    design_events = reporter.get_events_by_phase("design")
    assert len(design_events) == 1


@pytest.mark.asyncio
async def test_array_reporter_get_latest():
    """get_latest should return most recent event."""
    reporter = ArrayReporter()

    await reporter.report(Event(event_type="a", spec_id="test"))
    await reporter.report(Event(event_type="b", spec_id="test"))
    await reporter.report(Event(event_type="a", spec_id="test"))

    latest = reporter.get_latest()
    assert latest is not None
    assert latest.event_type == "a"

    latest_b = reporter.get_latest("b")
    assert latest_b is not None
    assert latest_b.event_type == "b"


@pytest.mark.asyncio
async def test_array_reporter_clear():
    """clear should remove all events."""
    reporter = ArrayReporter()

    await reporter.report(Event(event_type="a", spec_id="test"))
    await reporter.report(Event(event_type="b", spec_id="test"))

    assert len(reporter) == 2

    reporter.clear()

    assert len(reporter) == 0
    assert not reporter.has_event("a")


@pytest.mark.asyncio
async def test_array_reporter_to_list():
    """to_list should export events as dicts."""
    reporter = ArrayReporter()

    await reporter.report(
        Event(event_type="test", spec_id="spec-1", data={"key": "value"})
    )

    result = reporter.to_list()

    assert len(result) == 1
    assert result[0]["event_type"] == "test"
    assert result[0]["spec_id"] == "spec-1"
    assert result[0]["data"]["key"] == "value"


@pytest.mark.asyncio
async def test_array_reporter_iteration():
    """ArrayReporter should be iterable."""
    reporter = ArrayReporter()

    await reporter.report(Event(event_type="a", spec_id="test"))
    await reporter.report(Event(event_type="b", spec_id="test"))

    event_types = [e.event_type for e in reporter]
    assert event_types == ["a", "b"]
