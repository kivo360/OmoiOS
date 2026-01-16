# Spec Sandbox Subsystem Strategy

**Created**: 2025-01-15
**Status**: Approved
**Purpose**: Strategy for extracting Claude Sandbox Worker + Spec State Machine into an independent, testable subsystem

---

## Executive Summary

**Goals:**
1. Test the Claude Sandbox Worker and Spec-Driven Development code locally
2. Move it to a subsystem for independent development and testing
3. Handle Daytona spawning with both mocks and real sandboxes

**Core Design Principle:** Use a **Reporter abstraction** where the only thing that changes between environments is the event destination:

| Mode | Reporter | Destination | Speed |
|------|----------|-------------|-------|
| Mock | `ArrayReporter` | In-memory list (for assertions) | Instant |
| Local | `JSONLReporter` | Append-only `.jsonl` file | Fast |
| Production | `HTTPReporter` | POST to callback URL | Real-time |

**Key Benefits:**
- Same event format everywhere - just different sinks
- JSONL files are inspectable (`cat events.jsonl | jq .`)
- Easy to replay/debug from logs
- Tests verify event shape by asserting on arrays

---

## Architecture Overview

### What We're Extracting

| Component | Source File | Dependencies | Notes |
|-----------|-------------|--------------|-------|
| Claude Sandbox Worker | `workers/claude_sandbox_worker.py` | `httpx`, `claude-agent-sdk` | Already standalone |
| Spec State Machine | `workers/spec_state_machine.py` | Evaluators, has `_MockSpec` | DB-free mode exists |
| Evaluators | `evals/*.py` | Pydantic, LLM service | Pure logic |
| Schemas | `schemas/spec_generation.py` | Pydantic only | Data models |

### What Stays in Backend

| Component | Reason |
|-----------|--------|
| Daytona Spawner | Coupled to DB, EventBus - backend creates adapter |
| Spec Sync | SQLAlchemy models - backend concern |
| Spec Dedup | pgvector, embeddings - backend concern |
| Phase Gates | DB queries - backend concern |

---

## Subsystem Structure

```
subsystems/spec-sandbox/
├── pyproject.toml
├── README.md
│
├── src/spec_sandbox/
│   ├── __init__.py
│   │
│   ├── config.py                     # Pydantic Settings (extra="ignore")
│   │
│   ├── worker/                       # Core execution
│   │   ├── __init__.py
│   │   ├── claude_worker.py          # Standalone Claude agent worker
│   │   └── state_machine.py          # Spec phase orchestration
│   │
│   ├── evaluators/                   # Phase evaluators
│   │   ├── __init__.py
│   │   ├── base.py                   # EvalResult, BaseEvaluator
│   │   ├── exploration.py
│   │   ├── requirements.py
│   │   ├── design.py
│   │   └── tasks.py
│   │
│   ├── schemas/                      # Pydantic models
│   │   ├── __init__.py
│   │   ├── spec.py                   # SpecPhase, PhaseResult
│   │   └── events.py                 # Event schema
│   │
│   ├── reporters/                    # Event reporting abstraction
│   │   ├── __init__.py
│   │   ├── base.py                   # Abstract Reporter
│   │   ├── array.py                  # In-memory (for tests)
│   │   ├── jsonl.py                  # Append-only file (for local)
│   │   └── http.py                   # HTTP callback (for production)
│   │
│   └── cli.py                        # CLI for local testing
│
└── tests/
    ├── conftest.py
    ├── test_reporters/
    │   ├── test_array_reporter.py
    │   ├── test_jsonl_reporter.py
    │   └── test_http_reporter.py
    ├── test_state_machine.py
    ├── test_evaluators.py
    └── integration/
        └── test_full_spec_flow.py
```

---

## Configuration with Pydantic Settings

Use `pydantic-settings` with `extra="ignore"` so unknown environment variables are silently ignored. This makes the same code work in all environments without errors.

```python
# config.py
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SpecSandboxSettings(BaseSettings):
    """Configuration for spec sandbox execution.

    All settings can come from environment variables.
    Unknown variables are ignored (extra="ignore").
    """

    model_config = SettingsConfigDict(
        env_prefix="",           # No prefix - use exact var names
        extra="ignore",          # Ignore unknown env vars
        env_file=".env",         # Optional .env file
        env_file_encoding="utf-8",
    )

    # === Required (for production) ===
    spec_id: str = Field(default="local-spec", description="Unique spec identifier")

    # === Paths ===
    working_directory: str = Field(default=".", description="Workspace directory")
    context_file: Optional[Path] = Field(default=None, description="Path to context JSON")
    output_directory: Path = Field(default=Path(".spec-output"), description="Output directory")

    # === Reporter Mode ===
    reporter_mode: str = Field(
        default="jsonl",
        description="Reporter type: 'array' (test), 'jsonl' (local), 'http' (production)"
    )
    callback_url: Optional[str] = Field(default=None, description="HTTP callback URL (production)")

    # === Claude Agent SDK ===
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    anthropic_base_url: Optional[str] = Field(default=None, description="Custom API endpoint")
    model: Optional[str] = Field(default=None, description="Model to use")

    # === Execution Limits ===
    max_turns: int = Field(default=50, description="Max turns per phase")
    max_budget_usd: float = Field(default=10.0, description="Max budget in USD")
    heartbeat_interval: int = Field(default=30, description="Heartbeat interval in seconds")

    # === Phase Control ===
    current_phase: Optional[str] = Field(default=None, description="Run single phase only")
    resume_transcript_b64: Optional[str] = Field(default=None, description="Resume from transcript")

    # === Spec Content (from orchestrator) ===
    spec_title: str = Field(default="Untitled Spec", description="Spec title")
    spec_description: str = Field(default="", description="Spec description")
    task_data_base64: Optional[str] = Field(default=None, description="Full task context (base64)")

    # === GitHub (optional) ===
    github_token: Optional[str] = Field(default=None)
    github_repo: Optional[str] = Field(default=None)
    branch_name: Optional[str] = Field(default=None)


def load_settings() -> SpecSandboxSettings:
    """Load settings from environment."""
    return SpecSandboxSettings()
```

**Usage:**

```python
# Works in ANY environment - unknown vars are ignored
settings = load_settings()

# In production (Daytona sandbox):
# SPEC_ID=spec-123 CALLBACK_URL=https://api.omoios.dev ANTHROPIC_API_KEY=sk-...
# → settings.spec_id = "spec-123"
# → settings.callback_url = "https://api.omoios.dev"
# → settings.reporter_mode defaults to "jsonl" but we'd set REPORTER_MODE=http

# In local testing:
# SPEC_ID=test WORKING_DIRECTORY=./my-project
# → settings.spec_id = "test"
# → settings.reporter_mode = "jsonl" (default)
# → settings.callback_url = None (not needed)

# In unit tests:
# Just create settings directly:
settings = SpecSandboxSettings(spec_id="test", reporter_mode="array")
```

---

## Reporter Abstraction

The reporter is where events go. Same event format, different destinations.

### Event Schema

```python
# schemas/events.py
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from spec_sandbox.utils import utc_now


class Event(BaseModel):
    """Unified event format for all reporters."""

    event_type: str = Field(..., description="Event type identifier")
    timestamp: datetime = Field(default_factory=utc_now)
    spec_id: str
    phase: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Common event types
class EventTypes:
    # Lifecycle
    SPEC_STARTED = "spec_started"
    SPEC_COMPLETED = "spec_completed"
    SPEC_FAILED = "spec_failed"

    # Phase events
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    PHASE_FAILED = "phase_failed"
    PHASE_RETRY = "phase_retry"

    # Execution
    HEARTBEAT = "heartbeat"
    PROGRESS = "progress"
    EVAL_RESULT = "eval_result"

    # Artifacts
    ARTIFACT_CREATED = "artifact_created"
    REQUIREMENTS_GENERATED = "requirements_generated"
    DESIGN_GENERATED = "design_generated"
    TASKS_GENERATED = "tasks_generated"
```

### Base Reporter

```python
# reporters/base.py
from abc import ABC, abstractmethod
from typing import List

from spec_sandbox.schemas.events import Event


class Reporter(ABC):
    """Abstract reporter - where events go."""

    @abstractmethod
    async def report(self, event: Event) -> None:
        """Report a single event."""
        pass

    @abstractmethod
    async def flush(self) -> None:
        """Ensure all events are persisted."""
        pass

    async def report_many(self, events: List[Event]) -> None:
        """Report multiple events (default: sequential)."""
        for event in events:
            await self.report(event)
        await self.flush()
```

### ArrayReporter (Mock - for Tests)

```python
# reporters/array.py
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
        assert reporter.get_events_by_type("phase_completed") == 5
        assert reporter.has_event("spec_completed")
    """

    def __init__(self):
        self.events: List[Event] = []

    async def report(self, event: Event) -> None:
        self.events.append(event)

    async def flush(self) -> None:
        pass  # Nothing to flush - all in memory

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
        filtered = self.events if event_type is None else self.get_events_by_type(event_type)
        return filtered[-1] if filtered else None

    def clear(self) -> None:
        """Clear all events (for test reset)."""
        self.events.clear()

    def to_list(self) -> List[dict]:
        """Export events as list of dicts (for debugging)."""
        return [e.model_dump(mode="json") for e in self.events]
```

### JSONLReporter (Local - for Debugging)

```python
# reporters/jsonl.py
import json
from pathlib import Path
from typing import Optional

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
        # cat output/events.jsonl | jq 'select(.event_type == "phase_completed")'
    """

    def __init__(self, output_path: Path, create_parents: bool = True):
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

    def read_all(self) -> list[Event]:
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
```

### HTTPReporter (Production - Daytona)

```python
# reporters/http.py
import asyncio
from typing import List, Optional

import httpx

from spec_sandbox.reporters.base import Reporter
from spec_sandbox.schemas.events import Event


class HTTPReporter(Reporter):
    """POSTs events to callback URL (production mode).

    Features:
    - Batching: Collects events and sends in batches
    - Retry: Retries failed requests with backoff
    - Timeout: Configurable request timeout

    Usage:
        reporter = HTTPReporter(
            callback_url="https://api.omoios.dev",
            batch_size=10,
        )
        machine = SpecStateMachine(reporter=reporter, ...)
        await machine.run()
    """

    def __init__(
        self,
        callback_url: str,
        batch_size: int = 10,
        flush_interval: float = 5.0,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self.callback_url = callback_url.rstrip("/")
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.timeout = timeout
        self.max_retries = max_retries

        self._buffer: List[Event] = []
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def report(self, event: Event) -> None:
        """Add event to buffer, flush if batch size reached."""
        self._buffer.append(event)

        if len(self._buffer) >= self.batch_size:
            await self.flush()

    async def flush(self) -> None:
        """Send buffered events to callback URL."""
        if not self._buffer:
            return

        events_to_send = self._buffer.copy()
        self._buffer.clear()

        client = await self._get_client()

        for attempt in range(self.max_retries):
            try:
                response = await client.post(
                    f"{self.callback_url}/api/v1/sandbox/events",
                    json=[e.model_dump(mode="json") for e in events_to_send],
                )
                response.raise_for_status()
                return
            except httpx.HTTPError as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    # On final failure, log but don't crash
                    # Events are lost but execution continues
                    print(f"Failed to send events after {self.max_retries} attempts: {e}")

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
```

---

## State Machine Integration

The state machine uses the reporter for all event emission:

```python
# worker/state_machine.py
from pathlib import Path
from typing import Optional

from spec_sandbox.config import SpecSandboxSettings, load_settings
from spec_sandbox.reporters.base import Reporter
from spec_sandbox.reporters.array import ArrayReporter
from spec_sandbox.reporters.jsonl import JSONLReporter
from spec_sandbox.reporters.http import HTTPReporter
from spec_sandbox.schemas.events import Event, EventTypes
from spec_sandbox.schemas.spec import SpecPhase


def create_reporter(settings: SpecSandboxSettings) -> Reporter:
    """Create reporter based on settings."""
    if settings.reporter_mode == "array":
        return ArrayReporter()
    elif settings.reporter_mode == "jsonl":
        output_file = settings.output_directory / "events.jsonl"
        return JSONLReporter(output_file)
    elif settings.reporter_mode == "http":
        if not settings.callback_url:
            raise ValueError("callback_url required for http reporter")
        return HTTPReporter(settings.callback_url)
    else:
        raise ValueError(f"Unknown reporter mode: {settings.reporter_mode}")


class SpecStateMachine:
    """Spec-driven development state machine.

    Orchestrates phases: EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC → COMPLETE

    All events are emitted through the reporter, which can be:
    - ArrayReporter: In-memory (tests)
    - JSONLReporter: Append-only file (local debugging)
    - HTTPReporter: HTTP callback (production)
    """

    def __init__(
        self,
        settings: Optional[SpecSandboxSettings] = None,
        reporter: Optional[Reporter] = None,
    ):
        self.settings = settings or load_settings()
        self.reporter = reporter or create_reporter(self.settings)

        # Load context if provided
        self.context = {}
        if self.settings.context_file and self.settings.context_file.exists():
            import json
            self.context = json.loads(self.settings.context_file.read_text())

    async def run(self) -> bool:
        """Run full spec workflow."""
        await self._emit(EventTypes.SPEC_STARTED, data={
            "title": self.settings.spec_title,
            "description": self.settings.spec_description,
        })

        try:
            for phase in [
                SpecPhase.EXPLORE,
                SpecPhase.REQUIREMENTS,
                SpecPhase.DESIGN,
                SpecPhase.TASKS,
                SpecPhase.SYNC,
            ]:
                success = await self.run_phase(phase)
                if not success:
                    await self._emit(EventTypes.SPEC_FAILED, data={"failed_phase": phase.value})
                    return False

            await self._emit(EventTypes.SPEC_COMPLETED)
            return True

        finally:
            await self.reporter.flush()

    async def run_phase(self, phase: SpecPhase) -> bool:
        """Run a single phase."""
        await self._emit(EventTypes.PHASE_STARTED, phase=phase.value)

        try:
            # ... phase execution logic ...
            result = await self._execute_phase(phase)

            await self._emit(EventTypes.PHASE_COMPLETED, phase=phase.value, data={
                "eval_score": result.eval_score,
                "duration_seconds": result.duration_seconds,
            })

            return True

        except Exception as e:
            await self._emit(EventTypes.PHASE_FAILED, phase=phase.value, data={
                "error": str(e),
            })
            return False

    async def _emit(
        self,
        event_type: str,
        phase: Optional[str] = None,
        data: Optional[dict] = None,
    ) -> None:
        """Emit an event through the reporter."""
        event = Event(
            event_type=event_type,
            spec_id=self.settings.spec_id,
            phase=phase,
            data=data,
        )
        await self.reporter.report(event)

    async def _execute_phase(self, phase: SpecPhase):
        """Execute a specific phase (placeholder)."""
        # This is where the actual Claude Agent SDK execution happens
        # ... implementation details ...
        pass
```

---

## CLI for Local Testing

```python
# cli.py
import asyncio
import json
from pathlib import Path

import click

from spec_sandbox.config import SpecSandboxSettings
from spec_sandbox.reporters.jsonl import JSONLReporter
from spec_sandbox.worker.state_machine import SpecStateMachine


@click.group()
def cli():
    """Spec Sandbox CLI - Test spec-driven development locally."""
    pass


@cli.command()
@click.option("--spec-id", default="local-test", help="Spec ID")
@click.option("--title", default="Test Spec", help="Spec title")
@click.option("--description", required=True, help="What to build")
@click.option("--workspace", type=click.Path(exists=True), default=".", help="Working directory")
@click.option("--context-file", type=click.Path(exists=True), help="Path to context JSON")
@click.option("--output-dir", type=click.Path(), default=".spec-output", help="Output directory")
@click.option("--reporter", type=click.Choice(["jsonl", "array"]), default="jsonl")
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
    click.echo(f"   Workspace: {workspace}")
    click.echo(f"   Output: {output_dir}")
    click.echo(f"   Reporter: {reporter}")
    click.echo()

    success = asyncio.run(machine.run())

    if success:
        click.echo(f"✅ Spec completed successfully!")
        click.echo(f"   Events: {output_path / 'events.jsonl'}")
    else:
        click.echo(f"❌ Spec failed. Check events for details.")
        raise SystemExit(1)


@cli.command()
@click.option("--phase", required=True, type=click.Choice(["explore", "requirements", "design", "tasks", "sync"]))
@click.option("--spec-id", default="phase-test", help="Spec ID")
@click.option("--context-file", type=click.Path(exists=True), help="Path to context JSON")
@click.option("--output-dir", type=click.Path(), default=".spec-output")
def run_phase(phase, spec_id, context_file, output_dir):
    """Run a single phase (for debugging)."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    settings = SpecSandboxSettings(
        spec_id=spec_id,
        current_phase=phase,
        context_file=Path(context_file) if context_file else None,
        output_directory=output_path,
        reporter_mode="jsonl",
    )

    from spec_sandbox.schemas.spec import SpecPhase

    machine = SpecStateMachine(settings=settings)

    click.echo(f"🔧 Running phase: {phase}")

    phase_enum = SpecPhase(phase)
    success = asyncio.run(machine.run_phase(phase_enum))

    if success:
        click.echo(f"✅ Phase {phase} completed!")
    else:
        click.echo(f"❌ Phase {phase} failed.")
        raise SystemExit(1)


@cli.command()
@click.argument("events_file", type=click.Path(exists=True))
@click.option("--filter-type", help="Filter by event type")
@click.option("--filter-phase", help="Filter by phase")
def inspect(events_file, filter_type, filter_phase):
    """Inspect events from a JSONL file."""

    events_path = Path(events_file)
    reporter = JSONLReporter(events_path)
    events = reporter.read_all()

    # Apply filters
    if filter_type:
        events = [e for e in events if e.event_type == filter_type]
    if filter_phase:
        events = [e for e in events if e.phase == filter_phase]

    click.echo(f"📋 Found {len(events)} events\n")

    for event in events:
        click.echo(f"[{event.timestamp.strftime('%H:%M:%S')}] {event.event_type}")
        if event.phase:
            click.echo(f"    Phase: {event.phase}")
        if event.data:
            click.echo(f"    Data: {json.dumps(event.data, indent=2)}")
        click.echo()


if __name__ == "__main__":
    cli()
```

---

## pyproject.toml

```toml
[project]
name = "spec-sandbox"
version = "0.1.0"
description = "Spec-driven development sandbox for Claude Agent SDK"
readme = "README.md"
authors = [
    { name = "Kevin Hill", email = "kivo360@gmail.com" }
]
requires-python = ">=3.12"
dependencies = [
    "httpx>=0.27.0",
    "claude-agent-sdk>=0.1.17",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    "click>=8.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
]

[project.scripts]
spec-sandbox = "spec_sandbox.cli:cli"

[build-system]
requires = ["uv_build>=0.9.22,<0.10.0"]
build-backend = "uv_build"

[tool.uv.build-backend]
module-name = "spec_sandbox"
module-root = "src"
```

---

## Testing Strategy

### Test Order (Simple → Complex)

1. **ArrayReporter** (instant) - Verify event collection
2. **JSONLReporter** (fast) - Verify file output
3. **State Machine with ArrayReporter** (fast) - Verify event flow
4. **State Machine with JSONLReporter** (fast) - Verify full local run
5. **HTTPReporter** (requires server) - Mock httpx or use real callback
6. **Daytona** (slow, last) - Only in CI with real API key

### Example Tests

```python
# tests/test_reporters/test_array_reporter.py
import pytest
from spec_sandbox.reporters.array import ArrayReporter
from spec_sandbox.schemas.events import Event, EventTypes


@pytest.mark.asyncio
async def test_array_reporter_collects_events():
    reporter = ArrayReporter()

    await reporter.report(Event(
        event_type=EventTypes.SPEC_STARTED,
        spec_id="test-123",
    ))
    await reporter.report(Event(
        event_type=EventTypes.PHASE_STARTED,
        spec_id="test-123",
        phase="explore",
    ))

    assert len(reporter.events) == 2
    assert reporter.has_event(EventTypes.SPEC_STARTED)
    assert reporter.get_events_by_phase("explore") == [reporter.events[1]]


@pytest.mark.asyncio
async def test_array_reporter_get_latest():
    reporter = ArrayReporter()

    await reporter.report(Event(event_type="a", spec_id="test"))
    await reporter.report(Event(event_type="b", spec_id="test"))
    await reporter.report(Event(event_type="a", spec_id="test"))

    assert reporter.get_latest().event_type == "a"
    assert reporter.get_latest("b").event_type == "b"
```

```python
# tests/test_reporters/test_jsonl_reporter.py
import pytest
from pathlib import Path
from spec_sandbox.reporters.jsonl import JSONLReporter
from spec_sandbox.schemas.events import Event, EventTypes


@pytest.mark.asyncio
async def test_jsonl_reporter_appends_events(tmp_path):
    output_file = tmp_path / "events.jsonl"
    reporter = JSONLReporter(output_file)

    await reporter.report(Event(
        event_type=EventTypes.SPEC_STARTED,
        spec_id="test-123",
    ))
    await reporter.report(Event(
        event_type=EventTypes.PHASE_STARTED,
        spec_id="test-123",
        phase="explore",
    ))

    # Verify file contents
    lines = output_file.read_text().strip().split("\n")
    assert len(lines) == 2

    # Verify can read back
    events = reporter.read_all()
    assert len(events) == 2
    assert events[0].event_type == EventTypes.SPEC_STARTED


@pytest.mark.asyncio
async def test_jsonl_reporter_append_only(tmp_path):
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
```

```python
# tests/test_state_machine.py
import pytest
from spec_sandbox.config import SpecSandboxSettings
from spec_sandbox.reporters.array import ArrayReporter
from spec_sandbox.worker.state_machine import SpecStateMachine
from spec_sandbox.schemas.events import EventTypes


@pytest.mark.asyncio
async def test_state_machine_emits_lifecycle_events():
    reporter = ArrayReporter()
    settings = SpecSandboxSettings(
        spec_id="test-sm",
        spec_title="Test Spec",
        spec_description="Build something",
        reporter_mode="array",
    )

    machine = SpecStateMachine(settings=settings, reporter=reporter)

    # Run (will use mock execution for now)
    await machine.run()

    # Verify lifecycle events
    assert reporter.has_event(EventTypes.SPEC_STARTED)
    assert reporter.has_event(EventTypes.SPEC_COMPLETED) or reporter.has_event(EventTypes.SPEC_FAILED)

    # Verify phase events
    phase_starts = reporter.get_events_by_type(EventTypes.PHASE_STARTED)
    assert len(phase_starts) >= 1  # At least explore phase started
```

---

## Quick Start Commands

```bash
# Install subsystem
cd subsystems/spec-sandbox
uv sync

# Run tests (start with reporters)
uv run pytest tests/test_reporters/ -v

# Run state machine tests
uv run pytest tests/test_state_machine.py -v

# Run full spec locally
uv run spec-sandbox run --description "Build a REST API for todo items"

# Run single phase
uv run spec-sandbox run-phase --phase explore --context-file context.json

# Inspect events
uv run spec-sandbox inspect .spec-output/events.jsonl
uv run spec-sandbox inspect .spec-output/events.jsonl --filter-type phase_completed

# Or just use jq
cat .spec-output/events.jsonl | jq .
cat .spec-output/events.jsonl | jq 'select(.event_type == "phase_completed")'
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SPEC_ID` | No | `local-spec` | Unique spec identifier |
| `SPEC_TITLE` | No | `Untitled Spec` | Spec title |
| `SPEC_DESCRIPTION` | No | `""` | What to build |
| `WORKING_DIRECTORY` | No | `.` | Workspace path |
| `CONTEXT_FILE` | No | None | Path to context JSON |
| `OUTPUT_DIRECTORY` | No | `.spec-output` | Output directory |
| `REPORTER_MODE` | No | `jsonl` | `array`, `jsonl`, or `http` |
| `CALLBACK_URL` | For HTTP | None | HTTP callback URL |
| `ANTHROPIC_API_KEY` | For Claude | None | API key |
| `ANTHROPIC_BASE_URL` | No | None | Custom API endpoint |
| `MODEL` | No | None | Model override |
| `MAX_TURNS` | No | `50` | Max turns per phase |
| `MAX_BUDGET_USD` | No | `10.0` | Budget limit |
| `HEARTBEAT_INTERVAL` | No | `30` | Heartbeat seconds |
| `CURRENT_PHASE` | No | None | Run single phase only |
| `RESUME_TRANSCRIPT_B64` | No | None | Resume from transcript |
| `GITHUB_TOKEN` | No | None | GitHub token |
| `GITHUB_REPO` | No | None | owner/repo |
| `BRANCH_NAME` | No | None | Branch name |

---

## Implementation Checklist

### Phase 1: Core Structure
- [ ] Create `subsystems/spec-sandbox/` directory
- [ ] Create `pyproject.toml` with dependencies
- [ ] Create `src/spec_sandbox/config.py` with Pydantic Settings
- [ ] Create `src/spec_sandbox/schemas/events.py` with Event model

### Phase 2: Reporters (Test First)
- [ ] Implement `reporters/base.py` - Abstract Reporter
- [ ] Implement `reporters/array.py` - ArrayReporter
- [ ] Write tests for ArrayReporter
- [ ] Implement `reporters/jsonl.py` - JSONLReporter
- [ ] Write tests for JSONLReporter
- [ ] Implement `reporters/http.py` - HTTPReporter
- [ ] Write tests for HTTPReporter (mock httpx)

### Phase 3: State Machine
- [ ] Copy `spec_state_machine.py` → `worker/state_machine.py`
- [ ] Adapt to use Reporter instead of direct callbacks
- [ ] Copy evaluators
- [ ] Write state machine tests with ArrayReporter

### Phase 4: CLI
- [ ] Implement `cli.py` with run, run-phase, inspect commands
- [ ] Test CLI locally

### Phase 5: Integration
- [ ] Add `spec-sandbox` to backend's `pyproject.toml`
- [ ] Create adapter in backend for Daytona integration
- [ ] Test HTTPReporter with real callback URL
- [ ] Test with Daytona (last!)

---

## Environment Variable Analysis

### Comparison: Spawner → Worker → SpecSandboxSettings

The following table shows which env vars are:
- **Injected by Spawner** (`daytona_spawner.py`)
- **Read by Worker** (`claude_sandbox_worker.py`)
- **Defined in SpecSandboxSettings** (new subsystem)

| Variable | Spawner Injects | Worker Reads | Settings Has | Notes |
|----------|-----------------|--------------|--------------|-------|
| **Core Identity** |
| `SPEC_ID` | ✅ (spawn_for_phase) | ❌ | ✅ | Subsystem needs this |
| `SANDBOX_ID` | ✅ | ✅ | ❌ **ADD** | Worker reads it |
| `TASK_ID` | ✅ | ✅ | ❌ | Task-based only |
| `AGENT_ID` | ✅ | ✅ | ❌ | Task-based only |
| `PHASE_ID` | ✅ | ❌ | ❌ | Spawner internal |
| `SPEC_PHASE` | ✅ (spawn_for_phase) | ❌ | ❌ **ADD** | Spec execution |
| **Execution Control** |
| `EXECUTION_MODE` | ✅ | ❌ | ❌ | Skill loading mode |
| `REPORTER_MODE` | ❌ | ❌ | ✅ | Subsystem only |
| `CALLBACK_URL` | ✅ | ✅ | ✅ | All use this |
| `CONTINUOUS_MODE` | ✅ | ✅ | ❌ | Task-based only |
| **Anthropic/Claude** |
| `ANTHROPIC_API_KEY` | ✅ | ✅ | ✅ | Primary auth |
| `CLAUDE_CODE_OAUTH_TOKEN` | ✅ | ✅ | ❌ **ADD** | OAuth preferred |
| `ANTHROPIC_BASE_URL` | ✅ | ✅ | ✅ | Custom endpoint |
| `MODEL` | ✅ | ✅ | ✅ | Model selection |
| `ANTHROPIC_MODEL` | ✅ | ✅ (fallback) | ❌ | Compatibility |
| **Execution Limits** |
| `MAX_TURNS` | ❌ | ✅ | ✅ | Per-phase limit |
| `MAX_BUDGET_USD` | ❌ | ✅ | ✅ | Budget cap |
| `HEARTBEAT_INTERVAL` | ❌ | ✅ | ✅ | Health reporting |
| `MAX_ITERATIONS` | ✅ | ✅ | ❌ | Continuous mode |
| `MAX_TOTAL_COST_USD` | ✅ | ✅ | ❌ | Continuous mode |
| `MAX_DURATION_SECONDS` | ✅ | ✅ | ❌ | Time limit |
| **Spec Content** |
| `SPEC_TITLE` | ❌ | ❌ | ✅ | Local testing |
| `SPEC_DESCRIPTION` | ❌ | ❌ | ✅ | Local testing |
| `TASK_DATA_BASE64` | ✅ | ✅ | ✅ | Full context |
| `PHASE_CONTEXT_B64` | ✅ (spawn_for_phase) | ❌ | ❌ **ADD** | Phase history |
| **GitHub** |
| `GITHUB_TOKEN` | ✅ | ✅ | ✅ | Repo access |
| `GITHUB_REPO` | ✅ | ✅ | ✅ | owner/repo |
| `BRANCH_NAME` | ✅ | ✅ | ✅ | Feature branch |
| `GITHUB_USERNAME` | ✅ | ❌ | ❌ | API metadata |
| **Session Resumption** |
| `RESUME_SESSION_ID` | ✅ | ✅ | ❌ | Task-based |
| `SESSION_TRANSCRIPT_B64` | ✅ | ✅ | ✅ | Cross-sandbox resume |
| `RESUME_TRANSCRIPT_B64` | ❌ | ❌ | ✅ **RENAME** | Align naming |
| **Paths** |
| `WORKING_DIRECTORY` | ❌ | ✅ (CWD) | ✅ | Workspace path |
| `OUTPUT_DIRECTORY` | ❌ | ❌ | ✅ | Local output |
| `CONTEXT_FILE` | ❌ | ❌ | ✅ | Local testing |
| **OmoiOS Integration** |
| `OMOIOS_API_URL` | ✅ | ❌ | ❌ **ADD** | API base URL |
| `OMOIOS_PROJECT_ID` | ✅ | ❌ | ❌ **ADD** | Project for sync |
| `OMOIOS_API_KEY` | ✅ | ❌ | ❌ **ADD** | Auth for sync |
| `PROJECT_ID` | ✅ (spawn_for_phase) | ❌ | ❌ | Same as above |
| **Spec Skill** |
| `REQUIRE_SPEC_SKILL` | ✅ | ✅ | ❌ | Enforcement flag |
| `IS_SANDBOX` | ✅ | ✅ | ❌ | Sandbox detection |
| `MCP_SERVER_URL` | ✅ | ❌ | ❌ | MCP tools |

### Updated SpecSandboxSettings

Based on the analysis above, here's the **updated** config that captures all needed vars:

```python
# config.py
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SpecSandboxSettings(BaseSettings):
    """Configuration for spec sandbox execution.

    Uses Pydantic Settings v2 with extra="ignore" so unknown
    environment variables are silently ignored.
    """

    model_config = SettingsConfigDict(
        env_prefix="",           # No prefix - use exact var names
        extra="ignore",          # ✅ Unknown env vars silently ignored
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # === Core Identity ===
    spec_id: str = Field(default="local-spec", description="Unique spec identifier")
    sandbox_id: Optional[str] = Field(default=None, description="Daytona sandbox ID")
    spec_phase: Optional[str] = Field(default=None, description="Current phase (explore/requirements/design/tasks/sync)")

    # === Paths ===
    working_directory: str = Field(default=".", description="Workspace directory")
    context_file: Optional[Path] = Field(default=None, description="Path to context JSON")
    output_directory: Path = Field(default=Path(".spec-output"), description="Output directory")

    # === Reporter Mode ===
    reporter_mode: str = Field(
        default="jsonl",
        description="Reporter type: 'array' (test), 'jsonl' (local), 'http' (production)"
    )
    callback_url: Optional[str] = Field(default=None, description="HTTP callback URL")

    # === Claude Agent SDK ===
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    claude_code_oauth_token: Optional[str] = Field(default=None, description="OAuth token (preferred)")
    anthropic_base_url: Optional[str] = Field(default=None, description="Custom API endpoint")
    model: Optional[str] = Field(default=None, description="Model to use")

    # === Execution Limits ===
    max_turns: int = Field(default=50, description="Max turns per phase")
    max_budget_usd: float = Field(default=10.0, description="Max budget in USD")
    heartbeat_interval: int = Field(default=30, description="Heartbeat interval in seconds")

    # === Phase Context (from previous phases) ===
    phase_context_b64: Optional[str] = Field(default=None, description="Base64 JSON of accumulated context")
    session_transcript_b64: Optional[str] = Field(default=None, description="Resume from transcript")

    # === Spec Content (for local testing or from orchestrator) ===
    spec_title: str = Field(default="Untitled Spec", description="Spec title")
    spec_description: str = Field(default="", description="Spec description")
    task_data_base64: Optional[str] = Field(default=None, description="Full task context (base64)")

    # === GitHub ===
    github_token: Optional[str] = Field(default=None)
    github_repo: Optional[str] = Field(default=None)
    branch_name: Optional[str] = Field(default=None)

    # === OmoiOS Integration (Production) ===
    omoios_api_url: Optional[str] = Field(default=None, description="OmoiOS API URL for syncing")
    omoios_project_id: Optional[str] = Field(default=None, description="Project ID for spec sync")
    omoios_api_key: Optional[str] = Field(default=None, description="API key for auth")


def load_settings() -> SpecSandboxSettings:
    """Load settings from environment."""
    return SpecSandboxSettings()
```

### Pydantic Settings v2 Confirmation

✅ **Yes, we're using v2 properly.** The backend already has `pydantic-settings>=2.3.0` in `pyproject.toml`:

```toml
# backend/pyproject.toml (already exists)
dependencies = [
    "pydantic>=2.7.0,<3",
    "pydantic-settings>=2.3.0,<3",  # ← v2 already here!
    ...
]
```

Key v2 features we're using:
- `SettingsConfigDict` (not the old `Config` inner class)
- `extra="ignore"` to silently ignore unknown env vars
- `env_file_encoding` parameter

---

## Package Injection Strategy for Daytona Sandboxes

### Current Approach: File Upload

The current production code uploads individual Python files to the sandbox:

```python
# daytona_spawner.py lines 1249-1279
spec_modules = get_spec_state_machine_files(install_path="/tmp/omoi_os")
for sandbox_path, content in spec_modules.items():
    parent_dir = "/".join(sandbox_path.rsplit("/", 1)[:-1])
    sandbox.process.exec(f"mkdir -p {parent_dir}")
    sandbox.fs.upload_file(content.encode("utf-8"), sandbox_path)

# Add to PYTHONPATH
env_vars["PYTHONPATH"] = "/tmp/omoi_os"
```

**Files uploaded:** (`sandbox_modules/__init__.py`)
- `workers/spec_state_machine.py`
- `schemas/spec_generation.py`
- `evals/*.py` (evaluators)
- Stub services (embedding, spec_sync)

### Recommended: Two-Phase Strategy

#### Phase 1: Continue File Upload (Current)

For **rapid iteration** while developing the subsystem:
1. Keep the current `get_spec_state_machine_files()` approach
2. Update it to pull from `subsystems/spec-sandbox/src/` instead of `backend/omoi_os/`
3. No wheel building, no pip install in sandbox

**Pros:**
- No build step
- Instant changes (just modify source)
- Simple to debug

**Cons:**
- Files spread across sandbox
- No dependency resolution

#### Phase 2: Wheel Install (Production)

Once the subsystem is stable, build and install as a wheel:

```python
# In spawner
# Option A: Build wheel and upload
sandbox.fs.upload_file(wheel_bytes, "/tmp/spec_sandbox-0.1.0-py3-none-any.whl")
sandbox.process.exec("pip install /tmp/spec_sandbox-0.1.0-py3-none-any.whl")

# Option B: Install from PyPI (if published)
sandbox.process.exec("pip install spec-sandbox>=0.1.0")
```

**Pros:**
- Proper Python package with dependencies
- Version pinning
- Cleaner sandbox environment

**Cons:**
- Requires build step
- Slower iteration

### Recommended Implementation

**For now:** Update `get_spec_state_machine_files()` to reference the new subsystem:

```python
# sandbox_modules/__init__.py
def get_spec_state_machine_files(install_path: str = "/tmp/spec_sandbox") -> dict[str, str]:
    """Get files from subsystems/spec-sandbox/src for upload."""
    result = {}

    # Find subsystem root (navigate from backend/)
    subsystem_root = Path(__file__).parent.parent.parent / "subsystems" / "spec-sandbox" / "src"

    files_to_upload = [
        "spec_sandbox/__init__.py",
        "spec_sandbox/config.py",
        "spec_sandbox/worker/__init__.py",
        "spec_sandbox/worker/state_machine.py",
        "spec_sandbox/reporters/__init__.py",
        "spec_sandbox/reporters/base.py",
        "spec_sandbox/reporters/array.py",
        "spec_sandbox/reporters/jsonl.py",
        "spec_sandbox/reporters/http.py",
        "spec_sandbox/schemas/__init__.py",
        "spec_sandbox/schemas/events.py",
        "spec_sandbox/evaluators/__init__.py",
        "spec_sandbox/evaluators/base.py",
        # ... etc
    ]

    for rel_path in files_to_upload:
        file_path = subsystem_root / rel_path
        if file_path.exists():
            sandbox_path = f"{install_path}/{rel_path}"
            result[sandbox_path] = file_path.read_text()

    return result
```

---

## Should You Move the Session?

**Yes, move to the subsystem directory** once basic structure is in place. Here's why:

1. **Context locality**: All spec-sandbox work in one place
2. **Independent testing**: Can run `uv sync` and tests from subsystem root
3. **Cleaner iteration**: Focus on the isolated subsystem without backend complexity

**When to move:**
- After creating `subsystems/spec-sandbox/pyproject.toml`
- After creating basic directory structure
- Before implementing reporters

**Workflow after move:**
```bash
cd subsystems/spec-sandbox
uv sync                           # Install deps
uv run pytest tests/ -v           # Run tests
uv run spec-sandbox run --help    # Use CLI
```

---

## Summary

**Key Design Decisions:**

1. **Reporter Abstraction** - Same event format, different destinations (array/jsonl/http)
2. **Pydantic Settings v2 with `extra="ignore"`** - Unknown env vars silently ignored
3. **JSONL for Local Testing** - Append-only, inspectable with `cat | jq`
4. **Test Order** - Simple reporters first, Daytona last
5. **CLI Tools** - `run`, `run-phase`, `inspect` commands
6. **File Upload for Injection** - Continue current approach, upgrade to wheel later

**Environment Variable Coverage:**
- Added 8 missing variables to `SpecSandboxSettings`
- Aligned naming with `daytona_spawner.py`
- OAuth token support added (`CLAUDE_CODE_OAUTH_TOKEN`)
- OmoiOS integration vars added (`OMOIOS_API_URL`, `OMOIOS_PROJECT_ID`, `OMOIOS_API_KEY`)

**This approach gives you:**
- Fast local iteration (JSONL reporter, no network)
- Easy debugging (inspect events with jq)
- Test assertions (ArrayReporter captures events)
- Production compatibility (HTTPReporter posts to callback)
- Flexible configuration (all settings optional with sane defaults)
- Same package injection pattern as production (file upload)
