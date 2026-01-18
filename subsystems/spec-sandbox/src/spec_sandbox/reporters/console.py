"""Console reporter for pretty-printed live output.

Prints events to the console with colors and formatting for
easy local debugging and development.
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from spec_sandbox.reporters.base import Reporter
from spec_sandbox.schemas.events import Event, EventTypes


# ANSI color codes
class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"

    @classmethod
    def disable(cls) -> None:
        """Disable colors (for non-TTY output)."""
        cls.RESET = ""
        cls.BOLD = ""
        cls.DIM = ""
        cls.RED = ""
        cls.GREEN = ""
        cls.YELLOW = ""
        cls.BLUE = ""
        cls.MAGENTA = ""
        cls.CYAN = ""
        cls.WHITE = ""
        cls.BG_RED = ""
        cls.BG_GREEN = ""
        cls.BG_YELLOW = ""
        cls.BG_BLUE = ""


# Event type styling
EVENT_STYLES = {
    EventTypes.SPEC_STARTED: (Colors.BG_BLUE, "🚀"),
    EventTypes.SPEC_COMPLETED: (Colors.BG_GREEN, "✅"),
    EventTypes.SPEC_FAILED: (Colors.BG_RED, "❌"),
    EventTypes.PHASE_STARTED: (Colors.CYAN, "▶"),
    EventTypes.PHASE_COMPLETED: (Colors.GREEN, "✓"),
    EventTypes.PHASE_FAILED: (Colors.RED, "✗"),
    EventTypes.PHASE_RETRY: (Colors.YELLOW, "↻"),
    EventTypes.PROGRESS: (Colors.DIM, "·"),
    EventTypes.HEARTBEAT: (Colors.DIM, "♥"),
}

# Phase colors
PHASE_COLORS = {
    "explore": Colors.BLUE,
    "requirements": Colors.MAGENTA,
    "design": Colors.CYAN,
    "tasks": Colors.YELLOW,
    "sync": Colors.GREEN,
}


class ConsoleReporter(Reporter):
    """Pretty-prints events to the console.

    Features:
    - Colored output for different event types
    - Phase-specific colors
    - Progress bars and spinners
    - Collapsible data sections
    - Timestamps

    Usage:
        reporter = ConsoleReporter(verbose=True)
        machine = SpecStateMachine(reporter=reporter, ...)
        await machine.run()
    """

    def __init__(
        self,
        verbose: bool = False,
        show_data: bool = False,
        show_timestamps: bool = True,
        file=None,
    ) -> None:
        """Initialize console reporter.

        Args:
            verbose: Show all events including heartbeats
            show_data: Show full event data JSON
            show_timestamps: Show timestamps on each line
            file: Output file (default: sys.stdout)
        """
        self.verbose = verbose
        self.show_data = show_data
        self.show_timestamps = show_timestamps
        self.file = file or sys.stdout

        # Disable colors if not a TTY
        if not hasattr(self.file, "isatty") or not self.file.isatty():
            Colors.disable()

        self._current_phase: Optional[str] = None
        self._phase_start_time: Optional[datetime] = None
        self._event_count = 0

    async def report(self, event: Event) -> None:
        """Print event to console with formatting."""
        self._event_count += 1

        # Skip heartbeats unless verbose
        if event.event_type == EventTypes.HEARTBEAT and not self.verbose:
            return

        # Get styling for event type
        color, icon = EVENT_STYLES.get(event.event_type, (Colors.WHITE, "•"))

        # Build the output line
        line_parts = []

        # Timestamp
        if self.show_timestamps:
            timestamp = event.timestamp.strftime("%H:%M:%S")
            line_parts.append(f"{Colors.DIM}[{timestamp}]{Colors.RESET}")

        # Phase indicator (colored)
        if event.phase:
            phase_color = PHASE_COLORS.get(event.phase, Colors.WHITE)
            line_parts.append(f"{phase_color}{event.phase.upper():12}{Colors.RESET}")

        # Event icon and type
        line_parts.append(f"{color}{icon} {event.event_type}{Colors.RESET}")

        # Print the line
        self._print(" ".join(line_parts))

        # Print event-specific details
        self._print_event_details(event)

        # Print data if enabled
        if self.show_data and event.data:
            self._print_data(event.data)

    def _print_event_details(self, event: Event) -> None:
        """Print event-specific formatted details."""
        data = event.data or {}

        if event.event_type == EventTypes.SPEC_STARTED:
            self._print_box("SPEC STARTED", [
                f"Title: {data.get('title', 'Unknown')}",
                f"Description: {data.get('description', 'No description')}",
                f"Phases: {' → '.join(data.get('phases', []))}",
            ])
            self._current_phase = None

        elif event.event_type == EventTypes.SPEC_COMPLETED:
            phases = data.get("phases_completed", [])
            artifacts = data.get("markdown_artifacts", {})
            self._print_box("SPEC COMPLETED", [
                f"Phases: {', '.join(phases)}",
                f"Artifacts: {len(artifacts)} files generated",
            ], color=Colors.GREEN)

        elif event.event_type == EventTypes.SPEC_FAILED:
            self._print_box("SPEC FAILED", [
                f"Failed Phase: {data.get('failed_phase', 'Unknown')}",
                f"Error: {data.get('error', 'No error message')}",
            ], color=Colors.RED)

        elif event.event_type == EventTypes.PHASE_STARTED:
            self._current_phase = event.phase
            self._phase_start_time = event.timestamp
            self._print(f"   {Colors.DIM}{'─' * 50}{Colors.RESET}")

        elif event.event_type == EventTypes.PHASE_COMPLETED:
            score = data.get("eval_score")
            duration = data.get("duration_seconds")
            retries = data.get("retry_count", 0)

            details = []
            if score is not None:
                score_color = Colors.GREEN if score >= 0.8 else Colors.YELLOW if score >= 0.6 else Colors.RED
                details.append(f"Score: {score_color}{score:.2f}{Colors.RESET}")
            if duration is not None:
                details.append(f"Duration: {duration:.1f}s")
            if retries > 0:
                details.append(f"Retries: {retries}")

            if details:
                self._print(f"   {' | '.join(details)}")

        elif event.event_type == EventTypes.PHASE_FAILED:
            self._print(f"   {Colors.RED}Reason: {data.get('reason', 'Unknown')}{Colors.RESET}")
            if data.get("eval_feedback"):
                self._print(f"   {Colors.YELLOW}Feedback: {data.get('eval_feedback')}{Colors.RESET}")
            if data.get("error"):
                self._print(f"   {Colors.RED}Error: {data.get('error')}{Colors.RESET}")

        elif event.event_type == EventTypes.PHASE_RETRY:
            reason = data.get("reason", "unknown")
            retry_count = data.get("retry_count", 0)
            max_retries = data.get("max_retries", 3)
            self._print(f"   {Colors.YELLOW}Retrying ({retry_count}/{max_retries}): {reason}{Colors.RESET}")

        elif event.event_type == EventTypes.PROGRESS:
            message = data.get("message", "")
            if message:
                self._print(f"   {Colors.DIM}{message}{Colors.RESET}")

            # Show eval details if present
            if data.get("eval_passed") is not None:
                passed = data.get("eval_passed")
                status = f"{Colors.GREEN}PASSED{Colors.RESET}" if passed else f"{Colors.RED}FAILED{Colors.RESET}"
                self._print(f"   Evaluation: {status}")

                if data.get("eval_details"):
                    for key, value in data["eval_details"].items():
                        self._print(f"      {key}: {value}")

    def _print_box(
        self,
        title: str,
        lines: list[str],
        color: str = Colors.BLUE,
    ) -> None:
        """Print a formatted box with title and content."""
        width = 60
        self._print(f"\n{color}{'═' * width}{Colors.RESET}")
        self._print(f"{color}{Colors.BOLD}  {title}{Colors.RESET}")
        self._print(f"{color}{'─' * width}{Colors.RESET}")
        for line in lines:
            self._print(f"  {line}")
        self._print(f"{color}{'═' * width}{Colors.RESET}\n")

    def _print_data(self, data: Dict[str, Any]) -> None:
        """Print event data as indented JSON."""
        try:
            json_str = json.dumps(data, indent=2, default=str)
            for line in json_str.split("\n"):
                self._print(f"   {Colors.DIM}{line}{Colors.RESET}")
        except Exception:
            self._print(f"   {Colors.DIM}{data}{Colors.RESET}")

    def _print(self, message: str) -> None:
        """Print a line to the output file."""
        print(message, file=self.file, flush=True)

    async def flush(self) -> None:
        """Flush output."""
        if hasattr(self.file, "flush"):
            self.file.flush()

    def print_summary(self) -> None:
        """Print a final summary of the run."""
        self._print(f"\n{Colors.DIM}Total events: {self._event_count}{Colors.RESET}")
