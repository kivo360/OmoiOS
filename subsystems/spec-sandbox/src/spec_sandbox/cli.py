"""CLI for spec sandbox - test spec-driven development locally.

Commands:
- run: Run full spec workflow
- run-phase: Run a single phase
- inspect: Inspect events from a JSONL file
"""

import asyncio
import json
from pathlib import Path

import click

from spec_sandbox.config import SpecSandboxSettings
from spec_sandbox.reporters.jsonl import JSONLReporter
from spec_sandbox.schemas.spec import SpecPhase
from spec_sandbox.worker.state_machine import SpecStateMachine


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
    help="Working directory",
)
@click.option(
    "--context-file",
    type=click.Path(exists=True),
    help="Path to context JSON",
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default=".spec-output",
    help="Output directory",
)
@click.option(
    "--reporter",
    type=click.Choice(["jsonl", "array"]),
    default="jsonl",
    help="Reporter mode",
)
def run(spec_id, title, description, workspace, context_file, output_dir, reporter):
    """Run the full spec state machine locally."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    settings = SpecSandboxSettings(
        spec_id=spec_id,
        spec_title=title,
        spec_description=description,
        working_directory=workspace,
        context_file=Path(context_file) if context_file else None,
        output_directory=output_path,
        reporter_mode=reporter,
    )

    machine = SpecStateMachine(settings=settings)

    click.echo(f"🚀 Starting spec: {title}")
    click.echo(f"   Description: {description}")
    click.echo(f"   Workspace: {workspace}")
    click.echo(f"   Output: {output_dir}")
    click.echo(f"   Reporter: {reporter}")
    click.echo()

    success = asyncio.run(machine.run())

    if success:
        click.echo()
        click.echo("✅ Spec completed successfully!")
        if reporter == "jsonl":
            events_file = output_path / "events.jsonl"
            click.echo(f"   Events: {events_file}")
            click.echo()
            click.echo("   Inspect with:")
            click.echo(f"   cat {events_file} | jq .")
    else:
        click.echo()
        click.echo("❌ Spec failed. Check events for details.")
        raise SystemExit(1)


@cli.command("run-phase")
@click.option(
    "--phase",
    required=True,
    type=click.Choice(["explore", "requirements", "design", "tasks", "sync"]),
    help="Phase to run",
)
@click.option("--spec-id", default="phase-test", help="Spec ID")
@click.option(
    "--context-file",
    type=click.Path(exists=True),
    help="Path to context JSON",
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default=".spec-output",
    help="Output directory",
)
def run_phase(phase, spec_id, context_file, output_dir):
    """Run a single phase (for debugging)."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    settings = SpecSandboxSettings(
        spec_id=spec_id,
        spec_phase=phase,
        context_file=Path(context_file) if context_file else None,
        output_directory=output_path,
        reporter_mode="jsonl",
    )

    machine = SpecStateMachine(settings=settings)

    click.echo(f"🔧 Running phase: {phase}")

    phase_enum = SpecPhase(phase)
    result = asyncio.run(machine.run_phase(phase_enum))

    if result.success:
        click.echo()
        click.echo(f"✅ Phase {phase} completed!")
        if result.eval_score is not None:
            click.echo(f"   Eval score: {result.eval_score:.2f}")
        if result.duration_seconds is not None:
            click.echo(f"   Duration: {result.duration_seconds:.2f}s")
    else:
        click.echo()
        click.echo(f"❌ Phase {phase} failed.")
        if result.error:
            click.echo(f"   Error: {result.error}")
        raise SystemExit(1)


@cli.command()
@click.argument("events_file", type=click.Path(exists=True))
@click.option("--filter-type", help="Filter by event type")
@click.option("--filter-phase", help="Filter by phase")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def inspect(events_file, filter_type, filter_phase, json_output):
    """Inspect events from a JSONL file."""
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
    else:
        click.echo(f"📋 Found {len(events)} events")
        click.echo()

        for event in events:
            timestamp = event.timestamp.strftime("%H:%M:%S")
            click.echo(f"[{timestamp}] {event.event_type}")
            if event.phase:
                click.echo(f"    Phase: {event.phase}")
            if event.data:
                data_str = json.dumps(event.data, indent=2)
                # Indent data for readability
                data_str = "\n".join(f"    {line}" for line in data_str.split("\n"))
                click.echo(f"    Data: {data_str}")
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
    """Clean output directory."""
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


if __name__ == "__main__":
    cli()
