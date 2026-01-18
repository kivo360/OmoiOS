"""CLI for spec sandbox - test spec-driven development locally.

Commands:
- run: Run full spec workflow
- run-phase: Run a single phase
- inspect: Inspect events from a JSONL file
- create-tickets: Create tickets from TASKS phase output
- sync-markdown: Sync markdown files with frontmatter to backend API
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click

from spec_sandbox.config import SpecSandboxSettings, load_settings
from spec_sandbox.reporters.array import ArrayReporter
from spec_sandbox.reporters.console import ConsoleReporter
from spec_sandbox.reporters.jsonl import JSONLReporter
from spec_sandbox.schemas.spec import SpecPhase
from spec_sandbox.services.ticket_creator import TicketCreator, TicketCreatorConfig
from spec_sandbox.sync import MarkdownSyncService, SyncConfig
from spec_sandbox.worker.state_machine import SpecStateMachine


class MultiReporter:
    """Combines multiple reporters to report to all of them."""

    def __init__(self, reporters: list):
        self.reporters = reporters

    async def report(self, event):
        for reporter in self.reporters:
            await reporter.report(event)

    async def flush(self):
        for reporter in self.reporters:
            await reporter.flush()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.flush()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Spec Sandbox CLI - Test spec-driven development locally."""
    pass


@cli.command()
@click.option("--spec-id", default="local-test", help="Spec ID")
@click.option("--title", default="Test Spec", help="Spec title")
@click.option("--description", required=True, help="What to build")
@click.option(
    "--workspace",
    type=click.Path(exists=True),
    default=".",
    help="Working directory to explore",
)
@click.option(
    "--context-file",
    type=click.Path(exists=True),
    help="Path to context JSON (previous phase outputs)",
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default=".spec-output",
    help="Output directory for artifacts",
)
@click.option(
    "--live",
    is_flag=True,
    help="Use real Claude API (not mock mode)",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Show detailed progress output",
)
@click.option(
    "--show-data",
    is_flag=True,
    help="Show full event data JSON (very verbose)",
)
@click.option(
    "--quiet", "-q",
    is_flag=True,
    help="Minimal output (no console reporter)",
)
@click.option(
    "--generator",
    type=click.Choice(["static", "claude"]),
    default="claude",
    help="Markdown generator type (default: claude)",
)
def run(
    spec_id,
    title,
    description,
    workspace,
    context_file,
    output_dir,
    live,
    verbose,
    show_data,
    quiet,
    generator,
):
    """Run the full spec state machine locally.

    By default runs in mock mode (no API calls). Use --live for real execution.

    Examples:

        # Quick test with mock (no API calls)
        spec-sandbox run --description "Add user authentication"

        # Live test with real Claude API
        spec-sandbox run --live --description "Add user authentication"

        # Verbose output to see everything happening
        spec-sandbox run -v --description "Add user authentication"

        # Test against a specific project
        spec-sandbox run --workspace /path/to/project --description "Add feature X"
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Build settings
    settings = SpecSandboxSettings(
        spec_id=spec_id,
        spec_title=title,
        spec_description=description,
        cwd=workspace,
        context_file=Path(context_file) if context_file else None,
        output_directory=output_path,
        reporter_mode="array",  # We'll create our own reporter
        use_mock=not live,
        markdown_generator=generator,
    )

    # Create reporters
    reporters = []

    # Always add JSONL reporter for persistence
    jsonl_reporter = JSONLReporter(output_path / "events.jsonl")
    reporters.append(jsonl_reporter)

    # Add console reporter unless quiet
    console_reporter: Optional[ConsoleReporter] = None
    if not quiet:
        console_reporter = ConsoleReporter(
            verbose=verbose,
            show_data=show_data,
            show_timestamps=True,
        )
        reporters.append(console_reporter)

    # Create multi-reporter
    reporter = MultiReporter(reporters)

    # Create state machine with our reporter
    machine = SpecStateMachine(settings=settings, reporter=reporter)

    # Print header
    if not quiet:
        mode = "LIVE" if live else "MOCK"
        mode_color = "\033[32m" if live else "\033[33m"
        click.echo()
        click.echo(f"{'═' * 60}")
        click.echo(f"  SPEC SANDBOX - {mode_color}{mode} MODE\033[0m")
        click.echo(f"{'═' * 60}")
        click.echo(f"  Spec ID:     {spec_id}")
        click.echo(f"  Title:       {title}")
        click.echo(f"  Description: {description[:50]}{'...' if len(description) > 50 else ''}")
        click.echo(f"  Workspace:   {workspace}")
        click.echo(f"  Output:      {output_dir}")
        click.echo(f"  Generator:   {generator}")
        click.echo(f"{'═' * 60}")
        click.echo()
        sys.stdout.flush()  # Ensure header is displayed before async execution

    # Run the spec
    success = asyncio.run(machine.run())

    # Print summary
    if console_reporter:
        console_reporter.print_summary()

    if not quiet:
        click.echo()
        if success:
            click.echo("\033[32m" + "═" * 60 + "\033[0m")
            click.echo("\033[32m  ✅ SPEC COMPLETED SUCCESSFULLY\033[0m")
            click.echo("\033[32m" + "═" * 60 + "\033[0m")

            # Show generated artifacts
            if machine.markdown_artifacts:
                click.echo("\n  Generated Artifacts:")
                for name, path in machine.markdown_artifacts.items():
                    click.echo(f"    • {name}: {path}")

            click.echo(f"\n  Events log: {output_path / 'events.jsonl'}")
            click.echo("\n  Inspect with:")
            click.echo(f"    python -m spec_sandbox.cli inspect {output_path / 'events.jsonl'}")
        else:
            click.echo("\033[31m" + "═" * 60 + "\033[0m")
            click.echo("\033[31m  ❌ SPEC FAILED\033[0m")
            click.echo("\033[31m" + "═" * 60 + "\033[0m")
            click.echo(f"\n  Check events: {output_path / 'events.jsonl'}")
            raise SystemExit(1)


@cli.command("run-phase")
@click.option(
    "--phase",
    required=True,
    type=click.Choice(["explore", "requirements", "design", "tasks", "sync"]),
    help="Phase to run",
)
@click.option("--spec-id", default="phase-test", help="Spec ID")
@click.option("--title", default="Phase Test", help="Spec title")
@click.option("--description", default="Test phase execution", help="What to build")
@click.option(
    "--workspace",
    type=click.Path(exists=True),
    default=".",
    help="Working directory to explore",
)
@click.option(
    "--context-file",
    type=click.Path(exists=True),
    help="Path to context JSON (previous phase outputs)",
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default=".spec-output",
    help="Output directory",
)
@click.option(
    "--live",
    is_flag=True,
    help="Use real Claude API (not mock mode)",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Show detailed progress output",
)
def run_phase(phase, spec_id, title, description, workspace, context_file, output_dir, live, verbose):
    """Run a single phase (for debugging).

    Useful for testing individual phases or resuming from a context file.

    Examples:

        # Test explore phase on a project
        spec-sandbox run-phase --phase explore --workspace /path/to/project

        # Run requirements phase with previous context
        spec-sandbox run-phase --phase requirements --context-file ./context.json

        # Live execution of design phase
        spec-sandbox run-phase --phase design --live --context-file ./context.json
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    settings = SpecSandboxSettings(
        spec_id=spec_id,
        spec_title=title,
        spec_description=description,
        spec_phase=phase,
        cwd=workspace,
        context_file=Path(context_file) if context_file else None,
        output_directory=output_path,
        reporter_mode="array",
        use_mock=not live,
    )

    # Create reporters
    reporters = []
    jsonl_reporter = JSONLReporter(output_path / "events.jsonl")
    reporters.append(jsonl_reporter)

    console_reporter = ConsoleReporter(verbose=verbose, show_timestamps=True)
    reporters.append(console_reporter)

    reporter = MultiReporter(reporters)
    machine = SpecStateMachine(settings=settings, reporter=reporter)

    mode = "LIVE" if live else "MOCK"
    click.echo()
    click.echo(f"🔧 Running phase: {phase.upper()} ({mode} mode)")
    click.echo(f"   Workspace: {workspace}")
    if context_file:
        click.echo(f"   Context: {context_file}")
    click.echo()

    phase_enum = SpecPhase(phase)
    result = asyncio.run(machine.run_phase(phase_enum))

    console_reporter.print_summary()

    if result.success:
        click.echo()
        click.echo(f"\033[32m✅ Phase {phase.upper()} completed!\033[0m")
        if result.eval_score is not None:
            click.echo(f"   Eval score: {result.eval_score:.2f}")
        if result.duration_seconds is not None:
            click.echo(f"   Duration: {result.duration_seconds:.2f}s")

        # Save output for next phase
        if result.output:
            context_output = output_path / f"{phase}_output.json"
            context_output.write_text(json.dumps(result.output, indent=2))
            click.echo(f"   Output: {context_output}")
            click.echo()
            click.echo("   Use as context for next phase:")
            click.echo(f"   --context-file {context_output}")
    else:
        click.echo()
        click.echo(f"\033[31m❌ Phase {phase.upper()} failed.\033[0m")
        if result.error:
            click.echo(f"   Error: {result.error}")
        raise SystemExit(1)


@cli.command()
@click.argument("events_file", type=click.Path(exists=True))
@click.option("--filter-type", help="Filter by event type")
@click.option("--filter-phase", help="Filter by phase")
@click.option("--json-output", is_flag=True, help="Output as JSON")
@click.option("--summary", "-s", is_flag=True, help="Show summary only")
def inspect(events_file, filter_type, filter_phase, json_output, summary):
    """Inspect events from a JSONL file.

    Examples:

        # View all events
        spec-sandbox inspect .spec-output/events.jsonl

        # Filter by event type
        spec-sandbox inspect .spec-output/events.jsonl --filter-type phase_completed

        # Show only summary
        spec-sandbox inspect .spec-output/events.jsonl --summary

        # Output as JSON for piping
        spec-sandbox inspect .spec-output/events.jsonl --json-output | jq .
    """
    events_path = Path(events_file)
    reporter = JSONLReporter(events_path)
    events = reporter.read_all()

    # Apply filters
    if filter_type:
        events = [e for e in events if e.event_type == filter_type]
    if filter_phase:
        events = [e for e in events if e.phase == filter_phase]

    if json_output:
        # Output as JSON array
        output = [e.model_dump(mode="json") for e in events]
        click.echo(json.dumps(output, indent=2))
        return

    if summary:
        # Show summary only
        click.echo(f"\n📊 Event Summary for {events_file}")
        click.echo("─" * 50)

        # Count by type
        type_counts = {}
        phase_counts = {}
        for e in events:
            type_counts[e.event_type] = type_counts.get(e.event_type, 0) + 1
            if e.phase:
                phase_counts[e.phase] = phase_counts.get(e.phase, 0) + 1

        click.echo("\nBy Event Type:")
        for etype, count in sorted(type_counts.items()):
            click.echo(f"  {etype}: {count}")

        click.echo("\nBy Phase:")
        for phase, count in sorted(phase_counts.items()):
            click.echo(f"  {phase}: {count}")

        click.echo(f"\nTotal: {len(events)} events")
        return

    # Full output
    click.echo(f"\n📋 Found {len(events)} events\n")

    for event in events:
        timestamp = event.timestamp.strftime("%H:%M:%S")

        # Color based on event type
        if "failed" in event.event_type.lower():
            color = "\033[31m"  # Red
        elif "completed" in event.event_type.lower():
            color = "\033[32m"  # Green
        elif "started" in event.event_type.lower():
            color = "\033[34m"  # Blue
        else:
            color = "\033[0m"

        click.echo(f"{color}[{timestamp}] {event.event_type}\033[0m")
        if event.phase:
            click.echo(f"    Phase: {event.phase}")
        if event.data:
            # Show abbreviated data
            data_preview = json.dumps(event.data, default=str)
            if len(data_preview) > 100:
                data_preview = data_preview[:100] + "..."
            click.echo(f"    Data: {data_preview}")
        click.echo()


@cli.command()
@click.option(
    "--output-dir",
    type=click.Path(),
    default=".spec-output",
    help="Output directory to clean",
)
@click.option("--yes", is_flag=True, help="Skip confirmation")
def clean(output_dir, yes):
    """Clean output directory.

    Example:

        spec-sandbox clean --yes
    """
    output_path = Path(output_dir)

    if not output_path.exists():
        click.echo(f"Output directory {output_dir} does not exist.")
        return

    if not yes:
        if not click.confirm(f"Delete all files in {output_dir}?"):
            click.echo("Cancelled.")
            return

    import shutil

    shutil.rmtree(output_path)
    click.echo(f"✓ Cleaned {output_dir}")


@cli.command("create-tickets")
@click.argument("tasks_file", type=click.Path(exists=True))
@click.option(
    "--api-url",
    envvar="OMOIOS_API_URL",
    help="OmoiOS API URL (or OMOIOS_API_URL env var)",
)
@click.option(
    "--api-key",
    envvar="OMOIOS_API_KEY",
    help="OmoiOS API key (or OMOIOS_API_KEY env var)",
)
@click.option(
    "--project-id",
    envvar="OMOIOS_PROJECT_ID",
    required=True,
    help="Project ID to create tickets in (or OMOIOS_PROJECT_ID env var)",
)
@click.option(
    "--user-id",
    help="User ID to assign tickets to (for board visibility)",
)
@click.option(
    "--spec-id",
    default="cli-import",
    help="Spec ID for tracking",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be created without making API calls",
)
def create_tickets(tasks_file, api_url, api_key, project_id, user_id, spec_id, dry_run):
    """Create tickets and tasks from a TASKS phase output file.

    This command takes the output from the TASKS phase (JSON) and creates
    the corresponding tickets and tasks in the OmoiOS backend.

    Examples:

        # Create tickets from phase output
        spec-sandbox create-tickets .spec-output/tasks_output.json --project-id proj-123

        # With explicit API configuration
        spec-sandbox create-tickets tasks.json \\
            --api-url https://api.omoios.dev \\
            --api-key sk-... \\
            --project-id proj-123 \\
            --user-id user-456

        # Preview what would be created
        spec-sandbox create-tickets tasks.json --project-id proj-123 --dry-run
    """
    # Load settings from environment if not provided
    settings = load_settings()
    api_url = api_url or settings.omoios_api_url or "http://localhost:18000"
    api_key = api_key or settings.omoios_api_key

    # Load tasks file
    tasks_path = Path(tasks_file)
    try:
        tasks_output = json.loads(tasks_path.read_text())
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON in {tasks_file}: {e}")
        raise SystemExit(1)

    # Check for tickets/tasks
    tickets = tasks_output.get("tickets", [])
    tasks = tasks_output.get("tasks", [])

    if not tickets and not tasks:
        click.echo("Error: No tickets or tasks found in the file.")
        click.echo("Expected format: {\"tickets\": [...], \"tasks\": [...]}")
        raise SystemExit(1)

    click.echo()
    click.echo(f"{'═' * 60}")
    click.echo(f"  TICKET CREATION {'(DRY RUN)' if dry_run else ''}")
    click.echo(f"{'═' * 60}")
    click.echo(f"  API URL:    {api_url}")
    click.echo(f"  Project ID: {project_id}")
    click.echo(f"  User ID:    {user_id or '(not set - tickets may not appear on board)'}")
    click.echo(f"  Tickets:    {len(tickets)}")
    click.echo(f"  Tasks:      {len(tasks)}")
    click.echo(f"{'═' * 60}")
    click.echo()

    if dry_run:
        click.echo("DRY RUN - Preview of what would be created:\n")

        for ticket in tickets:
            click.echo(f"  [TICKET] {ticket.get('title', ticket.get('id', 'Unknown'))}")
            if ticket.get('description'):
                desc = ticket['description'][:60] + '...' if len(ticket.get('description', '')) > 60 else ticket['description']
                click.echo(f"           {desc}")

        for task in tasks:
            click.echo(f"  [TASK]   {task.get('title', task.get('id', 'Unknown'))}")
            click.echo(f"           → parent: {task.get('parent_ticket', 'Unknown')}")

        click.echo()
        click.echo("Run without --dry-run to create these items.")
        return

    if not api_key:
        click.echo("Error: API key required. Set OMOIOS_API_KEY or use --api-key")
        raise SystemExit(1)

    # Create ticket creator
    config = TicketCreatorConfig(
        api_url=api_url,
        project_id=project_id,
        api_key=api_key,
        user_id=user_id,
    )

    # Create a simple console reporter for progress
    console_reporter = ConsoleReporter(verbose=True, show_timestamps=True)

    creator = TicketCreator(
        config=config,
        reporter=console_reporter,
        spec_id=spec_id,
    )

    # Run the creation
    async def run_creation():
        try:
            summary = await creator.create_from_phase_output(tasks_output)
            return summary
        finally:
            await creator.close()

    summary = asyncio.run(run_creation())

    # Print results
    click.echo()
    click.echo(f"{'═' * 60}")
    if summary.tickets_failed == 0 and summary.tasks_failed == 0:
        click.echo(f"\033[32m  ✅ TICKET CREATION COMPLETED\033[0m")
    else:
        click.echo(f"\033[33m  ⚠️  TICKET CREATION COMPLETED WITH ERRORS\033[0m")
    click.echo(f"{'═' * 60}")
    click.echo(f"  Tickets created: {summary.tickets_created}")
    click.echo(f"  Tickets failed:  {summary.tickets_failed}")
    click.echo(f"  Tasks created:   {summary.tasks_created}")
    click.echo(f"  Tasks failed:    {summary.tasks_failed}")

    if summary.errors:
        click.echo()
        click.echo("  Errors:")
        for error in summary.errors[:10]:  # Limit displayed errors
            click.echo(f"    • {error}")
        if len(summary.errors) > 10:
            click.echo(f"    ... and {len(summary.errors) - 10} more")

    click.echo(f"{'═' * 60}")

    if summary.tickets_failed > 0 or summary.tasks_failed > 0:
        raise SystemExit(1)


@cli.command("sync-markdown")
@click.argument("input_dir", type=click.Path(exists=True))
@click.option(
    "--api-url",
    envvar="OMOIOS_API_URL",
    help="OmoiOS API URL (or OMOIOS_API_URL env var)",
)
@click.option(
    "--api-key",
    envvar="OMOIOS_API_KEY",
    help="OmoiOS API key (or OMOIOS_API_KEY env var)",
)
@click.option(
    "--project-id",
    envvar="OMOIOS_PROJECT_ID",
    required=True,
    help="Project ID to sync to (or OMOIOS_PROJECT_ID env var)",
)
@click.option(
    "--user-id",
    help="User ID to assign tickets to (for board visibility)",
)
@click.option(
    "--spec-id",
    default="markdown-sync",
    help="Spec ID for tracking",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be synced without making API calls",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Show detailed progress output",
)
def sync_markdown(input_dir, api_url, api_key, project_id, user_id, spec_id, dry_run, verbose):
    """Sync markdown files with frontmatter to the backend API.

    This command reads markdown files from the input directory structure:

    \b
        input_dir/
        ├── tickets/
        │   ├── TKT-001.md
        │   └── TKT-002.md
        └── tasks/
            ├── TSK-001.md
            └── TSK-002.md

    Each file should have YAML frontmatter (structured data) and markdown
    body (description). The frontmatter is validated and converted to API payloads.

    Examples:

    \b
        # Sync markdown files from output directory
        spec-sandbox sync-markdown .spec-output/markdown --project-id proj-123

    \b
        # With explicit API configuration
        spec-sandbox sync-markdown ./output \\
            --api-url https://api.omoios.dev \\
            --api-key sk-... \\
            --project-id proj-123 \\
            --user-id user-456

    \b
        # Preview what would be synced
        spec-sandbox sync-markdown ./output --project-id proj-123 --dry-run
    """
    # Load settings from environment if not provided
    settings = load_settings()
    api_url = api_url or settings.omoios_api_url or "http://localhost:18000"
    api_key = api_key or settings.omoios_api_key

    input_path = Path(input_dir)

    # Check directory structure
    tickets_dir = input_path / "tickets"
    tasks_dir = input_path / "tasks"

    ticket_files = list(tickets_dir.glob("TKT-*.md")) if tickets_dir.exists() else []
    task_files = list(tasks_dir.glob("TSK-*.md")) if tasks_dir.exists() else []

    if not ticket_files and not task_files:
        click.echo("Error: No markdown files found.")
        click.echo(f"Expected structure in {input_dir}:")
        click.echo("  tickets/TKT-001.md, TKT-002.md, ...")
        click.echo("  tasks/TSK-001.md, TSK-002.md, ...")
        raise SystemExit(1)

    click.echo()
    click.echo(f"{'═' * 60}")
    click.echo(f"  MARKDOWN SYNC {'(DRY RUN)' if dry_run else ''}")
    click.echo(f"{'═' * 60}")
    click.echo(f"  API URL:    {api_url}")
    click.echo(f"  Project ID: {project_id}")
    click.echo(f"  User ID:    {user_id or '(not set - tickets may not appear on board)'}")
    click.echo(f"  Input:      {input_dir}")
    click.echo(f"  Tickets:    {len(ticket_files)}")
    click.echo(f"  Tasks:      {len(task_files)}")
    click.echo(f"{'═' * 60}")
    click.echo()

    if dry_run:
        click.echo("DRY RUN - Preview of files to sync:\n")

        if ticket_files:
            click.echo("  Tickets:")
            for f in sorted(ticket_files):
                click.echo(f"    • {f.name}")

        if task_files:
            click.echo("\n  Tasks:")
            for f in sorted(task_files):
                click.echo(f"    • {f.name}")

        click.echo()

    if not dry_run and not api_key:
        click.echo("Error: API key required. Set OMOIOS_API_KEY or use --api-key")
        raise SystemExit(1)

    # Create sync config
    config = SyncConfig(
        api_url=api_url,
        project_id=project_id,
        spec_id=spec_id,
        api_key=api_key,
        user_id=user_id,
        dry_run=dry_run,
    )

    # Create reporter for progress
    console_reporter = ConsoleReporter(verbose=verbose, show_timestamps=True) if verbose else None

    # Create sync service
    service = MarkdownSyncService(config=config, reporter=console_reporter)

    # Run the sync
    async def run_sync():
        try:
            summary = await service.sync_directory(input_path)
            return summary
        finally:
            await service.close()

    summary = asyncio.run(run_sync())

    # Print results
    click.echo()
    click.echo(f"{'═' * 60}")
    if summary.tickets_failed == 0 and summary.tasks_failed == 0:
        click.echo(f"\033[32m  ✅ MARKDOWN SYNC COMPLETED\033[0m")
    else:
        click.echo(f"\033[33m  ⚠️  MARKDOWN SYNC COMPLETED WITH ERRORS\033[0m")
    click.echo(f"{'═' * 60}")
    click.echo(f"  Tickets synced: {summary.tickets_synced}")
    click.echo(f"  Tickets failed: {summary.tickets_failed}")
    click.echo(f"  Tasks synced:   {summary.tasks_synced}")
    click.echo(f"  Tasks failed:   {summary.tasks_failed}")

    if summary.ticket_id_map:
        click.echo()
        click.echo("  Ticket ID mapping (local → API):")
        for local_id, api_id in summary.ticket_id_map.items():
            click.echo(f"    {local_id} → {api_id}")

    if summary.task_id_map:
        click.echo()
        click.echo("  Task ID mapping (local → API):")
        for local_id, api_id in summary.task_id_map.items():
            click.echo(f"    {local_id} → {api_id}")

    if summary.errors:
        click.echo()
        click.echo("  Errors:")
        for error in summary.errors[:10]:  # Limit displayed errors
            click.echo(f"    • {error}")
        if len(summary.errors) > 10:
            click.echo(f"    ... and {len(summary.errors) - 10} more")

    click.echo(f"{'═' * 60}")

    if summary.tickets_failed > 0 or summary.tasks_failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
