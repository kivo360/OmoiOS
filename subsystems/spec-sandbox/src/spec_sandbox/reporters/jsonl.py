"""JSONL file reporter for local debugging.

Appends events to a .jsonl file (one JSON object per line).
Files can be inspected with: cat events.jsonl | jq .
"""

from pathlib import Path
from typing import List

from spec_sandbox.reporters.base import Reporter
from spec_sandbox.schemas.events import Event


class JSONLReporter(Reporter):
    """Appends events to a JSONL file (append-only log).

    Each event is written as a single JSON line.
    File is flushed after each write for durability.

    Usage:
        reporter = JSONLReporter(Path("./output/events.jsonl"))
        machine = SpecStateMachine(reporter=reporter, ...)
        await machine.run()

        # Then inspect:
        # cat output/events.jsonl | jq .
        # cat output/events.jsonl | jq 'select(.event_type == "spec.phase_completed")'
    """

    def __init__(self, output_path: Path, create_parents: bool = True) -> None:
        self.output_path = output_path

        if create_parents:
            output_path.parent.mkdir(parents=True, exist_ok=True)

    async def report(self, event: Event) -> None:
        """Append event as JSON line."""
        line = event.model_dump_json()

        with open(self.output_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    async def flush(self) -> None:
        """Already flushed on each write."""
        pass

    # === Utility Methods ===

    def read_all(self) -> List[Event]:
        """Read all events from file (for verification)."""
        if not self.output_path.exists():
            return []

        events = []
        with open(self.output_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(Event.model_validate_json(line))
        return events

    def clear(self) -> None:
        """Clear the file (for test reset)."""
        if self.output_path.exists():
            self.output_path.unlink()

    def line_count(self) -> int:
        """Count lines in the file."""
        if not self.output_path.exists():
            return 0

        with open(self.output_path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
