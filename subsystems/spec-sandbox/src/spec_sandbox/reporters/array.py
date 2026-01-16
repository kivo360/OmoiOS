"""In-memory array reporter for tests.

Collects events in a list for easy assertions in tests.
"""

from typing import List, Optional

from spec_sandbox.reporters.base import Reporter
from spec_sandbox.schemas.events import Event


class ArrayReporter(Reporter):
    """Collects events in memory for test assertions.

    Usage in tests:
        reporter = ArrayReporter()
        machine = SpecStateMachine(reporter=reporter, ...)
        await machine.run()

        # Assert on collected events
        assert len(reporter.events) > 0
        assert reporter.has_event("phase_completed")
        assert len(reporter.get_events_by_type("phase_started")) == 5
    """

    def __init__(self) -> None:
        self.events: List[Event] = []

    async def report(self, event: Event) -> None:
        """Add event to in-memory list."""
        self.events.append(event)

    async def flush(self) -> None:
        """Nothing to flush - all in memory."""
        pass

    # === Test Helpers ===

    def get_events_by_type(self, event_type: str) -> List[Event]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_events_by_phase(self, phase: str) -> List[Event]:
        """Get all events for a specific phase."""
        return [e for e in self.events if e.phase == phase]

    def has_event(self, event_type: str) -> bool:
        """Check if an event type was reported."""
        return any(e.event_type == event_type for e in self.events)

    def get_latest(self, event_type: Optional[str] = None) -> Optional[Event]:
        """Get the most recent event, optionally filtered by type."""
        filtered = (
            self.events if event_type is None else self.get_events_by_type(event_type)
        )
        return filtered[-1] if filtered else None

    def clear(self) -> None:
        """Clear all events (for test reset)."""
        self.events.clear()

    def to_list(self) -> List[dict]:
        """Export events as list of dicts (for debugging)."""
        return [e.model_dump(mode="json") for e in self.events]

    def __len__(self) -> int:
        """Return number of events."""
        return len(self.events)

    def __iter__(self):
        """Iterate over events."""
        return iter(self.events)
