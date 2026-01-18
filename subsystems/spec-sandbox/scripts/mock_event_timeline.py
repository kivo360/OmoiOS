#!/usr/bin/env python
"""Mock event timeline display using Rich.

Simulates the frontend EventTimeline component to preview
how spec events would appear in the UI.

Usage:
    python scripts/mock_event_timeline.py
    python scripts/mock_event_timeline.py --speed fast
    python scripts/mock_event_timeline.py --speed slow
    python scripts/mock_event_timeline.py --all  # Show all events at once
"""

import argparse
import asyncio
from datetime import datetime, timezone
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from spec_sandbox.schemas.events import Event, EventTypes


# Event display configuration (mirrors EventTimeline.tsx eventConfig)
EVENT_CONFIG = {
    # Spec lifecycle events
    EventTypes.SPEC_STARTED: {"icon": "▶", "color": "blue", "label": "Execution Started"},
    EventTypes.SPEC_COMPLETED: {"icon": "✓", "color": "green", "label": "Execution Complete"},
    EventTypes.SPEC_FAILED: {"icon": "✗", "color": "red", "label": "Execution Failed"},
    # Phase events
    EventTypes.PHASE_STARTED: {"icon": "●", "color": "blue", "label": "Phase Started"},
    EventTypes.PHASE_COMPLETED: {"icon": "✓", "color": "green", "label": "Phase Completed"},
    EventTypes.PHASE_FAILED: {"icon": "✗", "color": "red", "label": "Phase Failed"},
    EventTypes.PHASE_RETRY: {"icon": "↻", "color": "yellow", "label": "Phase Retry"},
    # Execution events
    EventTypes.HEARTBEAT: {"icon": "♥", "color": "dim", "label": "Heartbeat"},
    EventTypes.PROGRESS: {"icon": "⚡", "color": "cyan", "label": "Progress"},
    EventTypes.EVAL_RESULT: {"icon": "◆", "color": "magenta", "label": "Eval Result"},
    # Sync events
    EventTypes.SYNC_STARTED: {"icon": "↻", "color": "blue", "label": "Sync Started"},
    EventTypes.SYNC_COMPLETED: {"icon": "✓", "color": "green", "label": "Sync Completed"},
    EventTypes.TASKS_QUEUED: {"icon": "⚡", "color": "purple", "label": "Tasks Queued"},
    # Agent events
    "agent.completed": {"icon": "✓", "color": "green", "label": "Agent Completed"},
    "agent.started": {"icon": "▶", "color": "blue", "label": "Agent Started"},
    "agent.error": {"icon": "!", "color": "red", "label": "Agent Error"},
    # Default
    "default": {"icon": "○", "color": "white", "label": "Event"},
}


def get_event_config(event_type: str) -> dict:
    """Get display config for an event type."""
    return EVENT_CONFIG.get(event_type, EVENT_CONFIG["default"])


def format_timestamp(dt: datetime) -> str:
    """Format timestamp like the UI does."""
    return dt.strftime("%H:%M:%S")


def format_event_message(event: Event) -> str:
    """Extract a meaningful message from event data."""
    data = event.data or {}

    if "message" in data:
        return str(data["message"])
    if event.phase:
        phase_display = event.phase.upper()
        if "eval_score" in data:
            return f"Phase: {phase_display} (score: {data['eval_score']:.2f})"
        return f"Phase: {phase_display}"
    if "task_count" in data:
        return f"{data['task_count']} tasks"
    if "eval_score" in data:
        return f"Score: {data['eval_score']}"
    if "error" in data:
        return str(data["error"])[:60]
    if "duration_seconds" in data:
        return f"Duration: {data['duration_seconds']:.1f}s"
    if "phases_completed" in data:
        return f"Completed: {', '.join(data['phases_completed'])}"

    return ""


def create_event_row(event: Event, is_new: bool = False) -> tuple:
    """Create a table row for an event."""
    config = get_event_config(event.event_type)

    # Icon with color
    icon = Text(config["icon"], style=config["color"])

    # Label
    label = Text(config["label"], style=f"bold {config['color']}")

    # Source badge
    source = Text(f"[{event.data.get('source', 'spec')}]", style="dim")

    # Message
    message = Text(format_event_message(event), style="dim")

    # Timestamp
    timestamp = Text(format_timestamp(event.timestamp), style="dim")

    # Phase indicator if present
    phase = Text(event.phase or "", style="italic cyan") if event.phase else Text("")

    return (icon, label, phase, message, timestamp)


def create_timeline_table(events: list[Event], title: str = "Event Timeline") -> Table:
    """Create a Rich table displaying events like EventTimeline component."""
    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold",
        title=title,
        title_style="bold white",
        expand=True,
    )

    table.add_column("", width=2, justify="center")  # Icon
    table.add_column("Event", width=20)
    table.add_column("Phase", width=12)
    table.add_column("Details", ratio=1)
    table.add_column("Time", width=10, justify="right")

    for event in reversed(events):  # Newest first like the UI
        row = create_event_row(event)
        table.add_row(*row)

    return table


def create_phase_progress(
    current_phase: str,
    completed_phases: list[str],
    failed_phase: Optional[str] = None,
) -> Text:
    """Create a phase progress indicator like PhaseProgress component."""
    phases = ["explore", "requirements", "design", "tasks", "sync"]

    progress = Text()
    for i, phase in enumerate(phases):
        if phase == failed_phase:
            progress.append("✗", style="bold red")
        elif phase in completed_phases:
            progress.append("✓", style="bold green")
        elif phase == current_phase:
            progress.append("●", style="bold blue blink")
        else:
            progress.append("○", style="dim")

        if i < len(phases) - 1:
            if phase == failed_phase:
                connector_style = "red"
            elif phase in completed_phases:
                connector_style = "green"
            else:
                connector_style = "dim"
            progress.append("──", style=connector_style)

    progress.append("\n")
    for i, phase in enumerate(phases):
        if phase == failed_phase:
            style = "red"
        elif phase in completed_phases:
            style = "green"
        elif phase == current_phase:
            style = "blue"
        else:
            style = "dim"
        progress.append(f"{phase[:3].upper():^3}", style=style)
        if i < len(phases) - 1:
            progress.append("  ")

    return progress


def generate_mock_events(spec_id: str = "mock-spec-001") -> list[Event]:
    """Generate a realistic sequence of spec execution events."""
    events = []

    def add_event(event_type: str, phase: Optional[str] = None, data: Optional[dict] = None):
        events.append(Event(
            event_type=event_type,
            spec_id=spec_id,
            phase=phase,
            data=data or {},
        ))

    # Spec started
    add_event(EventTypes.SPEC_STARTED, data={
        "title": "User Authentication Feature",
        "description": "Implement OAuth2 login with Google",
        "phases": ["explore", "requirements", "design", "tasks", "sync"],
    })

    # EXPLORE phase
    add_event(EventTypes.PHASE_STARTED, phase="explore")
    add_event(EventTypes.PROGRESS, phase="explore", data={"message": "Scanning codebase structure..."})
    add_event(EventTypes.PROGRESS, phase="explore", data={"message": "Found 47 Python files, 12 TypeScript files"})
    add_event(EventTypes.PROGRESS, phase="explore", data={"message": "Identified existing auth patterns"})
    add_event(EventTypes.EVAL_RESULT, phase="explore", data={"score": 0.95, "passed": True})
    add_event(EventTypes.PHASE_COMPLETED, phase="explore", data={
        "eval_score": 0.95,
        "duration_seconds": 12.3,
        "retry_count": 0,
    })

    # REQUIREMENTS phase
    add_event(EventTypes.PHASE_STARTED, phase="requirements")
    add_event(EventTypes.PROGRESS, phase="requirements", data={"message": "Generating EARS-format requirements..."})
    add_event(EventTypes.PROGRESS, phase="requirements", data={"message": "Created 8 requirements with 24 criteria"})
    add_event(EventTypes.EVAL_RESULT, phase="requirements", data={"score": 0.88, "passed": True})
    add_event(EventTypes.PHASE_COMPLETED, phase="requirements", data={
        "eval_score": 0.88,
        "duration_seconds": 18.7,
        "retry_count": 0,
    })

    # DESIGN phase
    add_event(EventTypes.PHASE_STARTED, phase="design")
    add_event(EventTypes.PROGRESS, phase="design", data={"message": "Designing component architecture..."})
    add_event(EventTypes.PROGRESS, phase="design", data={"message": "Created AuthService, TokenManager, OAuthProvider"})
    add_event(EventTypes.EVAL_RESULT, phase="design", data={"score": 0.72, "passed": False, "feedback": "Missing error handling"})
    add_event(EventTypes.PHASE_RETRY, phase="design", data={
        "retry_count": 1,
        "max_retries": 3,
        "reason": "Eval score below threshold",
    })
    add_event(EventTypes.PROGRESS, phase="design", data={"message": "Adding error handling patterns..."})
    add_event(EventTypes.EVAL_RESULT, phase="design", data={"score": 0.91, "passed": True})
    add_event(EventTypes.PHASE_COMPLETED, phase="design", data={
        "eval_score": 0.91,
        "duration_seconds": 25.4,
        "retry_count": 1,
    })

    # TASKS phase
    add_event(EventTypes.PHASE_STARTED, phase="tasks")
    add_event(EventTypes.PROGRESS, phase="tasks", data={"message": "Breaking down into implementation tasks..."})
    add_event(EventTypes.PROGRESS, phase="tasks", data={"message": "Generated 12 tasks with dependencies"})
    add_event(EventTypes.EVAL_RESULT, phase="tasks", data={"score": 0.94, "passed": True})
    add_event(EventTypes.PHASE_COMPLETED, phase="tasks", data={
        "eval_score": 0.94,
        "duration_seconds": 15.2,
        "retry_count": 0,
    })

    # SYNC phase
    add_event(EventTypes.PHASE_STARTED, phase="sync")
    add_event(EventTypes.SYNC_STARTED, phase="sync", data={"items_to_sync": 12})
    add_event(EventTypes.PROGRESS, phase="sync", data={"message": "Validating requirement coverage..."})
    add_event(EventTypes.PROGRESS, phase="sync", data={"message": "All requirements covered by tasks"})
    add_event(EventTypes.TASKS_QUEUED, phase="sync", data={"task_count": 12})
    add_event(EventTypes.SYNC_COMPLETED, phase="sync", data={"items_synced": 12})
    add_event(EventTypes.PHASE_COMPLETED, phase="sync", data={
        "eval_score": 1.0,
        "duration_seconds": 8.1,
        "retry_count": 0,
    })

    # Spec completed
    add_event(EventTypes.SPEC_COMPLETED, data={
        "phases_completed": ["explore", "requirements", "design", "tasks", "sync"],
        "markdown_artifacts": {
            "requirements.md": "/output/requirements.md",
            "design.md": "/output/design.md",
            "tasks/index.md": "/output/tasks/index.md",
        },
    })

    # Agent completed (for backend sync)
    add_event("agent.completed", data={
        "spec_id": spec_id,
        "success": True,
        "phase_data": {
            "explore": {"codebase_summary": "..."},
            "requirements": {"requirements": []},
            "design": {"components": []},
            "tasks": {"tasks": []},
            "sync": {"validation": {}},
        },
        "phases_completed": ["explore", "requirements", "design", "tasks", "sync"],
    })

    return events


async def run_live_simulation(events: list[Event], speed: str = "normal"):
    """Run a live simulation showing events appearing over time."""
    console = Console()

    # Speed settings
    delays = {
        "fast": 0.3,
        "normal": 0.8,
        "slow": 1.5,
    }
    delay = delays.get(speed, 0.8)

    displayed_events = []
    current_phase = None
    completed_phases = []
    failed_phase = None

    console.print("\n[bold]Spec Execution Simulation[/bold]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    with Live(console=console, refresh_per_second=4) as live:
        for event in events:
            displayed_events.append(event)

            # Track phase progress
            if event.event_type == EventTypes.PHASE_STARTED:
                current_phase = event.phase
            elif event.event_type == EventTypes.PHASE_COMPLETED and event.phase:
                completed_phases.append(event.phase)
                current_phase = None
            elif event.event_type == EventTypes.PHASE_FAILED and event.phase:
                failed_phase = event.phase
                current_phase = None

            # Build the display
            layout = Table.grid(expand=True)
            layout.add_column()

            # Phase progress bar
            if current_phase or completed_phases or failed_phase:
                progress = create_phase_progress(current_phase or "", completed_phases, failed_phase)
                border_style = "red" if failed_phase else "blue"
                layout.add_row(Panel(progress, title="Phase Progress", border_style=border_style))
                layout.add_row("")

            # Event timeline
            timeline = create_timeline_table(
                displayed_events[-15:],  # Show last 15 events
                title=f"Event Timeline ({len(displayed_events)} events)"
            )
            layout.add_row(timeline)

            # Status line
            status = f"[dim]Spec ID: {event.spec_id} | Events: {len(displayed_events)}[/dim]"
            layout.add_row(Text(status))

            border_style = "red" if failed_phase else "blue"
            title = "[bold red]Spec Event Timeline - FAILED[/bold red]" if failed_phase else "[bold blue]Spec Event Timeline[/bold blue]"
            live.update(Panel(layout, title=title, border_style=border_style))

            await asyncio.sleep(delay)

    if failed_phase:
        console.print(f"\n[bold red]Simulation complete - FAILED at {failed_phase} phase[/bold red]")
    else:
        console.print("\n[bold green]Simulation complete![/bold green]")


def show_all_events(events: list[Event]):
    """Show all events at once (no animation)."""
    console = Console()

    # Determine final state from events
    completed_phases = []
    failed_phase = None

    for event in events:
        if event.event_type == EventTypes.PHASE_COMPLETED and event.phase:
            completed_phases.append(event.phase)
        elif event.event_type == EventTypes.PHASE_FAILED and event.phase:
            failed_phase = event.phase

    # Phase progress (final state)
    progress = create_phase_progress("", completed_phases, failed_phase)
    border_style = "red" if failed_phase else "green"
    console.print(Panel(progress, title="Phase Progress", border_style=border_style))
    console.print()

    # Full timeline
    timeline = create_timeline_table(events, title=f"Event Timeline ({len(events)} events)")
    console.print(timeline)

    # Summary
    console.print(f"\n[dim]Total events: {len(events)}[/dim]")
    console.print(f"[dim]Spec ID: {events[0].spec_id if events else 'N/A'}[/dim]")
    if failed_phase:
        console.print(f"[red]Status: FAILED at {failed_phase} phase[/red]")
    else:
        console.print("[green]Status: SUCCESS[/green]")


def generate_failure_events(spec_id: str = "mock-spec-fail") -> list[Event]:
    """Generate events showing a failed spec execution."""
    events = []

    def add_event(event_type: str, phase: Optional[str] = None, data: Optional[dict] = None):
        events.append(Event(
            event_type=event_type,
            spec_id=spec_id,
            phase=phase,
            data=data or {},
        ))

    # Spec started
    add_event(EventTypes.SPEC_STARTED, data={
        "title": "Complex Feature",
        "description": "A feature that will fail",
        "phases": ["explore", "requirements", "design", "tasks", "sync"],
    })

    # EXPLORE phase - success
    add_event(EventTypes.PHASE_STARTED, phase="explore")
    add_event(EventTypes.PROGRESS, phase="explore", data={"message": "Scanning codebase..."})
    add_event(EventTypes.EVAL_RESULT, phase="explore", data={"score": 0.92, "passed": True})
    add_event(EventTypes.PHASE_COMPLETED, phase="explore", data={
        "eval_score": 0.92,
        "duration_seconds": 10.5,
    })

    # REQUIREMENTS phase - success
    add_event(EventTypes.PHASE_STARTED, phase="requirements")
    add_event(EventTypes.PROGRESS, phase="requirements", data={"message": "Generating requirements..."})
    add_event(EventTypes.EVAL_RESULT, phase="requirements", data={"score": 0.85, "passed": True})
    add_event(EventTypes.PHASE_COMPLETED, phase="requirements", data={
        "eval_score": 0.85,
        "duration_seconds": 15.2,
    })

    # DESIGN phase - fails after max retries
    add_event(EventTypes.PHASE_STARTED, phase="design")
    add_event(EventTypes.PROGRESS, phase="design", data={"message": "Designing architecture..."})
    add_event(EventTypes.EVAL_RESULT, phase="design", data={
        "score": 0.45,
        "passed": False,
        "feedback": "Design lacks required security patterns",
    })
    add_event(EventTypes.PHASE_RETRY, phase="design", data={
        "retry_count": 1,
        "max_retries": 3,
        "reason": "Score 0.45 below threshold 0.80",
    })
    add_event(EventTypes.PROGRESS, phase="design", data={"message": "Retrying with security focus..."})
    add_event(EventTypes.EVAL_RESULT, phase="design", data={
        "score": 0.52,
        "passed": False,
        "feedback": "Still missing auth patterns",
    })
    add_event(EventTypes.PHASE_RETRY, phase="design", data={
        "retry_count": 2,
        "max_retries": 3,
        "reason": "Score 0.52 below threshold 0.80",
    })
    add_event(EventTypes.PROGRESS, phase="design", data={"message": "Final retry..."})
    add_event(EventTypes.EVAL_RESULT, phase="design", data={
        "score": 0.58,
        "passed": False,
        "feedback": "Design fundamentally flawed",
    })
    add_event(EventTypes.PHASE_FAILED, phase="design", data={
        "reason": "Max retries exceeded",
        "eval_feedback": "Design fundamentally flawed",
        "error": "Failed after 3 attempts. Best score: 0.58",
    })

    # Spec failed
    add_event(EventTypes.SPEC_FAILED, data={
        "failed_phase": "design",
        "error": "Design phase failed after max retries",
    })

    # Agent completed with failure
    add_event("agent.completed", data={
        "spec_id": spec_id,
        "success": False,
        "phase_data": {
            "explore": {"codebase_summary": "..."},
            "requirements": {"requirements": []},
        },
        "failed_phase": "design",
        "error": "Design phase failed after max retries",
    })

    return events


def main():
    parser = argparse.ArgumentParser(description="Mock event timeline display")
    parser.add_argument(
        "--speed",
        choices=["fast", "normal", "slow"],
        default="normal",
        help="Animation speed (default: normal)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show all events at once (no animation)",
    )
    parser.add_argument(
        "--scenario",
        choices=["success", "failure"],
        default="success",
        help="Which scenario to simulate (default: success)",
    )
    args = parser.parse_args()

    if args.scenario == "failure":
        events = generate_failure_events()
    else:
        events = generate_mock_events()

    if args.all:
        show_all_events(events)
    else:
        try:
            asyncio.run(run_live_simulation(events, args.speed))
        except KeyboardInterrupt:
            print("\n\nSimulation stopped.")


if __name__ == "__main__":
    main()
