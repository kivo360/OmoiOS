"""Tests for JSONLReporter."""

import pytest
from pathlib import Path

from spec_sandbox.reporters.jsonl import JSONLReporter
from spec_sandbox.schemas.events import Event, EventTypes


@pytest.mark.asyncio
async def test_jsonl_reporter_appends_events(tmp_path):
    """JSONLReporter should append events to file."""
    output_file = tmp_path / "events.jsonl"
    reporter = JSONLReporter(output_file)

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

    # Verify file contents
    lines = output_file.read_text().strip().split("\n")
    assert len(lines) == 2


@pytest.mark.asyncio
async def test_jsonl_reporter_read_all(tmp_path):
    """read_all should parse events from file."""
    output_file = tmp_path / "events.jsonl"
    reporter = JSONLReporter(output_file)

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

    events = reporter.read_all()
    assert len(events) == 2
    assert events[0].event_type == EventTypes.SPEC_STARTED
    assert events[1].event_type == EventTypes.PHASE_STARTED
    assert events[1].phase == "explore"


@pytest.mark.asyncio
async def test_jsonl_reporter_append_only(tmp_path):
    """Events from multiple reporters should be appended."""
    output_file = tmp_path / "events.jsonl"

    # First reporter
    reporter1 = JSONLReporter(output_file)
    await reporter1.report(Event(event_type="first", spec_id="test"))

    # Second reporter (simulates restart)
    reporter2 = JSONLReporter(output_file)
    await reporter2.report(Event(event_type="second", spec_id="test"))

    # Both events should be there
    events = reporter2.read_all()
    assert len(events) == 2
    assert events[0].event_type == "first"
    assert events[1].event_type == "second"


@pytest.mark.asyncio
async def test_jsonl_reporter_clear(tmp_path):
    """clear should remove the file."""
    output_file = tmp_path / "events.jsonl"
    reporter = JSONLReporter(output_file)

    await reporter.report(Event(event_type="test", spec_id="test"))
    assert output_file.exists()

    reporter.clear()
    assert not output_file.exists()


@pytest.mark.asyncio
async def test_jsonl_reporter_line_count(tmp_path):
    """line_count should return correct count."""
    output_file = tmp_path / "events.jsonl"
    reporter = JSONLReporter(output_file)

    assert reporter.line_count() == 0

    await reporter.report(Event(event_type="a", spec_id="test"))
    await reporter.report(Event(event_type="b", spec_id="test"))
    await reporter.report(Event(event_type="c", spec_id="test"))

    assert reporter.line_count() == 3


@pytest.mark.asyncio
async def test_jsonl_reporter_creates_parent_dirs(tmp_path):
    """Reporter should create parent directories."""
    output_file = tmp_path / "nested" / "dirs" / "events.jsonl"
    reporter = JSONLReporter(output_file)

    await reporter.report(Event(event_type="test", spec_id="test"))

    assert output_file.exists()
    assert output_file.parent.exists()


@pytest.mark.asyncio
async def test_jsonl_reporter_preserves_data(tmp_path):
    """Event data should be preserved through serialization."""
    output_file = tmp_path / "events.jsonl"
    reporter = JSONLReporter(output_file)

    await reporter.report(
        Event(
            event_type="test",
            spec_id="test-123",
            phase="explore",
            data={
                "nested": {"key": "value"},
                "list": [1, 2, 3],
                "number": 42.5,
            },
        )
    )

    events = reporter.read_all()
    assert len(events) == 1
    assert events[0].data["nested"]["key"] == "value"
    assert events[0].data["list"] == [1, 2, 3]
    assert events[0].data["number"] == 42.5
