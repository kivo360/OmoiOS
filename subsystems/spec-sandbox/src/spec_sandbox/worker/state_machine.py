"""Spec State Machine - orchestrates spec-driven development phases.

Phases: EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC → COMPLETE

All events are emitted through the reporter, which can be:
- ArrayReporter: In-memory (tests)
- JSONLReporter: Append-only file (local debugging)
- HTTPReporter: HTTP callback (production)
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from spec_sandbox.config import SpecSandboxSettings, load_settings
from spec_sandbox.reporters.base import Reporter
from spec_sandbox.reporters.array import ArrayReporter
from spec_sandbox.reporters.jsonl import JSONLReporter
from spec_sandbox.reporters.http import HTTPReporter
from spec_sandbox.schemas.events import Event, EventTypes
from spec_sandbox.schemas.spec import SpecPhase, PhaseResult


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

    Orchestrates phases: EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC

    All events are emitted through the reporter abstraction.
    """

    # Default phase order
    PHASES = [
        SpecPhase.EXPLORE,
        SpecPhase.REQUIREMENTS,
        SpecPhase.DESIGN,
        SpecPhase.TASKS,
        SpecPhase.SYNC,
    ]

    def __init__(
        self,
        settings: Optional[SpecSandboxSettings] = None,
        reporter: Optional[Reporter] = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.reporter = reporter if reporter is not None else create_reporter(self.settings)

        # Phase results storage
        self.phase_results: Dict[SpecPhase, PhaseResult] = {}

        # Accumulated context from previous phases
        self.context: Dict[str, Any] = {}

        # Load context if provided
        if self.settings.context_file and self.settings.context_file.exists():
            self.context = json.loads(self.settings.context_file.read_text())

        # Load phase context if resuming
        if self.settings.phase_context_b64:
            import base64

            phase_context_json = base64.b64decode(
                self.settings.phase_context_b64
            ).decode("utf-8")
            self.context.update(json.loads(phase_context_json))

        # Heartbeat task
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

    async def run(self) -> bool:
        """Run full spec workflow.

        Returns True if all phases completed successfully.
        """
        await self._emit(
            EventTypes.SPEC_STARTED,
            data={
                "title": self.settings.spec_title,
                "description": self.settings.spec_description,
                "phases": [p.value for p in self.PHASES],
            },
        )

        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        try:
            # If single phase specified, run only that
            if self.settings.spec_phase:
                phase = SpecPhase(self.settings.spec_phase)
                result = await self.run_phase(phase)
                success = result.success
            else:
                # Run all phases in order
                success = True
                for phase in self.PHASES:
                    result = await self.run_phase(phase)
                    if not result.success:
                        await self._emit(
                            EventTypes.SPEC_FAILED,
                            data={
                                "failed_phase": phase.value,
                                "error": result.error,
                            },
                        )
                        success = False
                        break

            if success:
                await self._emit(
                    EventTypes.SPEC_COMPLETED,
                    data={
                        "phases_completed": [
                            p.value
                            for p, r in self.phase_results.items()
                            if r.success
                        ],
                    },
                )

            return success

        finally:
            self._running = False
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass
            await self.reporter.flush()

    async def run_phase(self, phase: SpecPhase) -> PhaseResult:
        """Run a single phase.

        Returns PhaseResult with success status and outputs.
        """
        await self._emit(EventTypes.PHASE_STARTED, phase=phase.value)

        start_time = time.time()
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Execute the phase
                output = await self._execute_phase(phase)

                duration = time.time() - start_time

                # Create result
                result = PhaseResult(
                    phase=phase,
                    success=True,
                    eval_score=output.get("eval_score"),
                    duration_seconds=duration,
                    output=output,
                    retry_count=retry_count,
                )

                self.phase_results[phase] = result

                # Update context with phase outputs
                self.context[phase.value] = output

                await self._emit(
                    EventTypes.PHASE_COMPLETED,
                    phase=phase.value,
                    data={
                        "eval_score": result.eval_score,
                        "duration_seconds": result.duration_seconds,
                        "retry_count": retry_count,
                    },
                )

                return result

            except Exception as e:
                retry_count += 1

                if retry_count < max_retries:
                    await self._emit(
                        EventTypes.PHASE_RETRY,
                        phase=phase.value,
                        data={
                            "error": str(e),
                            "retry_count": retry_count,
                            "max_retries": max_retries,
                        },
                    )
                    await asyncio.sleep(2**retry_count)  # Exponential backoff
                else:
                    duration = time.time() - start_time
                    result = PhaseResult(
                        phase=phase,
                        success=False,
                        duration_seconds=duration,
                        error=str(e),
                        retry_count=retry_count,
                    )
                    self.phase_results[phase] = result

                    await self._emit(
                        EventTypes.PHASE_FAILED,
                        phase=phase.value,
                        data={
                            "error": str(e),
                            "retry_count": retry_count,
                        },
                    )

                    return result

        # Should not reach here, but satisfy type checker
        return PhaseResult(phase=phase, success=False, error="Unknown error")

    async def _execute_phase(self, phase: SpecPhase) -> Dict[str, Any]:
        """Execute a specific phase.

        This is where Claude Agent SDK execution happens.
        For now, returns mock data - will be implemented with real agent.
        """
        # TODO: Implement real Claude Agent SDK execution
        # For now, return mock output for testing

        await self._emit(
            EventTypes.PROGRESS,
            phase=phase.value,
            data={"message": f"Executing {phase.value} phase..."},
        )

        # Simulate some work
        await asyncio.sleep(0.1)

        # Mock outputs based on phase
        mock_outputs = {
            SpecPhase.EXPLORE: {
                "codebase_summary": "Mock codebase analysis",
                "key_files": ["src/main.py", "src/utils.py"],
                "eval_score": 0.85,
            },
            SpecPhase.REQUIREMENTS: {
                "requirements": [
                    {"id": "REQ-001", "text": "The system shall..."},
                ],
                "eval_score": 0.80,
            },
            SpecPhase.DESIGN: {
                "architecture": "Mock architecture design",
                "components": ["API", "Database", "Frontend"],
                "eval_score": 0.75,
            },
            SpecPhase.TASKS: {
                "tasks": [
                    {"id": "TASK-001", "title": "Implement API endpoint"},
                    {"id": "TASK-002", "title": "Add database schema"},
                ],
                "eval_score": 0.90,
            },
            SpecPhase.SYNC: {
                "synced": True,
                "artifacts_created": 5,
                "eval_score": 1.0,
            },
        }

        return mock_outputs.get(phase, {"eval_score": 0.5})

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

    async def _heartbeat_loop(self) -> None:
        """Background heartbeat loop."""
        while self._running:
            try:
                await asyncio.sleep(self.settings.heartbeat_interval)
                if self._running:
                    await self._emit(
                        EventTypes.HEARTBEAT,
                        data={
                            "phases_completed": len(self.phase_results),
                            "current_phase": (
                                list(self.phase_results.keys())[-1].value
                                if self.phase_results
                                else None
                            ),
                        },
                    )
            except asyncio.CancelledError:
                break
