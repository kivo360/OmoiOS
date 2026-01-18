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
from spec_sandbox.evaluators import get_evaluator, EvalResult
from spec_sandbox.executor.claude_executor import ClaudeExecutor, ExecutorConfig
from spec_sandbox.generators.markdown import MarkdownGenerator
from spec_sandbox.generators.claude_generator import ClaudeMarkdownGenerator, ClaudeGeneratorConfig
from spec_sandbox.reporters.base import Reporter
from spec_sandbox.reporters.array import ArrayReporter
from spec_sandbox.reporters.jsonl import JSONLReporter
from spec_sandbox.reporters.http import HTTPReporter
from spec_sandbox.schemas.events import Event, EventTypes
from spec_sandbox.schemas.spec import SpecPhase, PhaseResult
from spec_sandbox.services.ticket_creator import TicketCreator, TicketCreatorConfig, TicketCreationSummary


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
        executor: Optional[ClaudeExecutor] = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.reporter = reporter if reporter is not None else create_reporter(self.settings)

        # Create executor with settings
        if executor is not None:
            self.executor = executor
        else:
            executor_config = ExecutorConfig(
                model=self.settings.model,
                max_turns=self.settings.max_turns,
                max_budget_usd=self.settings.max_budget_usd,
                cwd=self.settings.cwd,
                use_mock=self.settings.use_mock,
            )
            self.executor = ClaudeExecutor(
                config=executor_config,
                reporter=self.reporter,
                spec_id=self.settings.spec_id,
            )

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

        # Markdown generator for rich documentation output
        # Choose generator type based on settings
        if self.settings.markdown_generator == "claude":
            # Claude Agent SDK-based generator (intelligent, language-aware)
            claude_config = ClaudeGeneratorConfig(
                model=self.settings.model,
                max_turns=10,
                output_dir=self.settings.output_directory,
                spec_id=self.settings.spec_id,
                spec_title=self.settings.spec_title,
                use_mock=self.settings.use_mock,
            )
            self._claude_generator = ClaudeMarkdownGenerator(
                config=claude_config,
                reporter=self.reporter,
            )
            self._markdown_generator = None  # Not used
        else:
            # Static template-based generator (fast, no API calls)
            self._markdown_generator = MarkdownGenerator(
                output_dir=self.settings.output_directory,
                spec_id=self.settings.spec_id,
                spec_title=self.settings.spec_title,
            )
            self._claude_generator = None  # Not used

        # Track generated markdown artifacts
        self.markdown_artifacts: Dict[str, Path] = {}

        # Ticket creation summary (populated if API integration is enabled)
        self.ticket_creation_summary: Optional[TicketCreationSummary] = None

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
                        # Emit agent.completed with failure status for backend
                        # Still include any phase_data that was collected before failure
                        phase_data = {
                            p.value: self.context.get(p.value, {})
                            for p in SpecPhase
                            if p.value in self.context
                        }
                        await self._emit(
                            "agent.completed",
                            data={
                                "spec_id": self.settings.spec_id,
                                "success": False,
                                "phase_data": phase_data,
                                "failed_phase": phase.value,
                                "error": result.error,
                            },
                        )
                        success = False
                        break

            if success:
                # Generate markdown documentation
                await self._generate_markdown_artifacts()

                # Create tickets in backend API if configured
                await self._create_tickets()

                # Report sync summary if using HTTP reporter
                await self._report_sync_summary()

                await self._emit(
                    EventTypes.SPEC_COMPLETED,
                    data={
                        "phases_completed": [
                            p.value
                            for p, r in self.phase_results.items()
                            if r.success
                        ],
                        "markdown_artifacts": {
                            k: str(v) for k, v in self.markdown_artifacts.items()
                        },
                        "ticket_creation": (
                            self.ticket_creation_summary.to_dict()
                            if self.ticket_creation_summary
                            else None
                        ),
                    },
                )

                # Emit agent.completed with phase_data for backend Spec model update
                # This triggers _update_spec_phase_data() in the backend
                phase_data = {
                    phase.value: self.context.get(phase.value, {})
                    for phase in SpecPhase
                    if phase.value in self.context
                }
                await self._emit(
                    "agent.completed",
                    data={
                        "spec_id": self.settings.spec_id,
                        "success": True,
                        "phase_data": phase_data,
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
        """Run a single phase with evaluation and retry logic.

        The phase is executed, then evaluated. If evaluation fails,
        the phase is retried with feedback from the evaluator.

        Returns PhaseResult with success status and outputs.
        """
        await self._emit(EventTypes.PHASE_STARTED, phase=phase.value)

        start_time = time.time()
        max_retries = 3
        retry_count = 0
        last_eval_feedback: Optional[str] = None

        while retry_count < max_retries:
            try:
                # Execute the phase (with eval feedback if retrying)
                output = await self._execute_phase(phase, eval_feedback=last_eval_feedback)

                # Evaluate the output
                evaluator = get_evaluator(phase.value)
                eval_result = await evaluator.evaluate(output, self.context)

                await self._emit(
                    EventTypes.PROGRESS,
                    phase=phase.value,
                    data={
                        "message": f"Evaluation score: {eval_result.score:.2f}",
                        "eval_passed": eval_result.passed,
                        "eval_details": eval_result.details,
                    },
                )

                if eval_result.passed:
                    # Success - evaluation passed
                    duration = time.time() - start_time

                    result = PhaseResult(
                        phase=phase,
                        success=True,
                        eval_score=eval_result.score,
                        duration_seconds=duration,
                        output=output,
                        retry_count=retry_count,
                    )

                    self.phase_results[phase] = result
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
                else:
                    # Evaluation failed - retry with feedback
                    retry_count += 1
                    last_eval_feedback = eval_result.feedback

                    if retry_count < max_retries:
                        await self._emit(
                            EventTypes.PHASE_RETRY,
                            phase=phase.value,
                            data={
                                "reason": "evaluation_failed",
                                "eval_score": eval_result.score,
                                "eval_feedback": eval_result.feedback,
                                "retry_count": retry_count,
                                "max_retries": max_retries,
                            },
                        )
                        await asyncio.sleep(2**retry_count)  # Exponential backoff
                    else:
                        # Max retries reached
                        duration = time.time() - start_time
                        result = PhaseResult(
                            phase=phase,
                            success=False,
                            eval_score=eval_result.score,
                            duration_seconds=duration,
                            output=output,
                            error=f"Evaluation failed after {max_retries} attempts: {eval_result.feedback}",
                            retry_count=retry_count,
                        )
                        self.phase_results[phase] = result

                        await self._emit(
                            EventTypes.PHASE_FAILED,
                            phase=phase.value,
                            data={
                                "reason": "evaluation_failed",
                                "eval_score": eval_result.score,
                                "eval_feedback": eval_result.feedback,
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
                            "reason": "execution_error",
                            "error": str(e),
                            "retry_count": retry_count,
                            "max_retries": max_retries,
                        },
                    )
                    await asyncio.sleep(2**retry_count)
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
                            "reason": "execution_error",
                            "error": str(e),
                            "retry_count": retry_count,
                        },
                    )

                    return result

        # Should not reach here, but satisfy type checker
        return PhaseResult(phase=phase, success=False, error="Unknown error")

    async def _execute_phase(
        self,
        phase: SpecPhase,
        eval_feedback: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a specific phase using Claude Agent SDK.

        The executor handles:
        - Building phase-specific prompts with context
        - Running the Claude Agent with appropriate tools
        - Extracting and validating structured output

        Args:
            phase: The phase to execute
            eval_feedback: Feedback from previous evaluation failure (for retries)
        """
        if eval_feedback:
            await self._emit(
                EventTypes.PROGRESS,
                phase=phase.value,
                data={
                    "message": f"Retrying {phase.value} phase with evaluation feedback...",
                    "eval_feedback": eval_feedback,
                },
            )
        else:
            await self._emit(
                EventTypes.PROGRESS,
                phase=phase.value,
                data={"message": f"Starting {phase.value} phase execution..."},
            )

        # Execute the phase using the Claude executor
        result = await self.executor.execute_phase(
            phase=phase,
            spec_title=self.settings.spec_title,
            spec_description=self.settings.spec_description,
            context=self.context,
            eval_feedback=eval_feedback,
        )

        if not result.success:
            raise RuntimeError(f"Phase {phase.value} failed: {result.error}")

        # Add execution metadata to output
        output = result.output.copy()
        output["_execution"] = {
            "cost_usd": result.cost_usd,
            "duration_ms": result.duration_ms,
            "tool_uses": result.tool_uses,
        }

        return output

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

    async def _generate_markdown_artifacts(self) -> None:
        """Generate markdown documentation from phase outputs.

        Creates rich markdown files with YAML frontmatter for:
        - Requirements document
        - Design document with Mermaid diagrams
        - Individual task files
        - Spec summary with coverage matrix

        Uses either Claude Agent SDK-based generation (intelligent, language-aware)
        or static template-based generation depending on settings.markdown_generator.
        """
        generator_type = "Claude-based" if self._claude_generator else "static"
        await self._emit(
            EventTypes.PROGRESS,
            data={"message": f"Generating markdown documentation ({generator_type})..."},
        )

        # Collect outputs from successful phases
        explore_output = self.context.get("explore")
        requirements_output = self.context.get("requirements")
        design_output = self.context.get("design")
        tasks_output = self.context.get("tasks")
        sync_output = self.context.get("sync")

        try:
            # Generate all markdown artifacts using the configured generator
            if self._claude_generator:
                # Use Claude Agent SDK-based generator (async)
                self.markdown_artifacts = await self._claude_generator.generate_all(
                    explore_output=explore_output,
                    requirements_output=requirements_output,
                    design_output=design_output,
                    tasks_output=tasks_output,
                    sync_output=sync_output,
                )
            else:
                # Use static template-based generator (sync)
                self.markdown_artifacts = self._markdown_generator.generate_all(
                    explore_output=explore_output,
                    requirements_output=requirements_output,
                    design_output=design_output,
                    tasks_output=tasks_output,
                    sync_output=sync_output,
                )

            await self._emit(
                EventTypes.PROGRESS,
                data={
                    "message": f"Generated {len(self.markdown_artifacts)} markdown artifacts",
                    "artifacts": list(self.markdown_artifacts.keys()),
                },
            )

        except Exception as e:
            # Log error but don't fail the spec - markdown is supplementary
            await self._emit(
                EventTypes.PROGRESS,
                data={
                    "message": f"Warning: Markdown generation failed: {e}",
                    "error": str(e),
                },
            )

    async def _report_sync_summary(self) -> None:
        """Report the sync summary with traceability stats to the backend.

        Only applies when using HTTPReporter. Sends a SyncSummary-style
        payload with traceability statistics for external monitoring.
        """
        sync_output = self.context.get("sync")
        if not sync_output:
            return

        # Check if reporter supports sync summary reporting
        if not hasattr(self.reporter, "report_sync_summary"):
            return

        try:
            # Collect all phase data for the summary
            phase_data = {
                "explore": self.context.get("explore", {}),
                "requirements": self.context.get("requirements", {}),
                "design": self.context.get("design", {}),
                "tasks": self.context.get("tasks", {}),
            }

            await self.reporter.report_sync_summary(
                spec_id=self.settings.spec_id,
                sync_output=sync_output,
                phase_data=phase_data,
            )

            await self._emit(
                EventTypes.PROGRESS,
                data={"message": "Sync summary reported to backend"},
            )

        except Exception as e:
            # Log error but don't fail - sync summary is supplementary
            await self._emit(
                EventTypes.PROGRESS,
                data={
                    "message": f"Warning: Sync summary reporting failed: {e}",
                    "error": str(e),
                },
            )

    async def _create_tickets(self) -> None:
        """Create tickets and tasks in the backend API from TASKS phase output.

        This is enabled when all three are configured:
        - omoios_api_url: The backend API URL
        - omoios_project_id: The project to create tickets in
        - omoios_api_key: API key for authentication

        The TASKS phase output must contain 'tickets' and 'tasks' arrays.
        Each ticket will be created with the user_id from the spec context
        so they appear on the correct user's board.
        """
        # Check if API integration is configured
        if not all([
            self.settings.omoios_api_url,
            self.settings.omoios_project_id,
            self.settings.omoios_api_key,
        ]):
            await self._emit(
                EventTypes.PROGRESS,
                data={
                    "message": "Ticket creation skipped - API not configured",
                    "missing": [
                        k for k, v in [
                            ("omoios_api_url", self.settings.omoios_api_url),
                            ("omoios_project_id", self.settings.omoios_project_id),
                            ("omoios_api_key", self.settings.omoios_api_key),
                        ] if not v
                    ],
                },
            )
            return

        # Get TASKS phase output
        tasks_output = self.context.get("tasks")
        if not tasks_output:
            await self._emit(
                EventTypes.PROGRESS,
                data={"message": "Ticket creation skipped - no tasks output"},
            )
            return

        # Check for tickets/tasks
        if not tasks_output.get("tickets") and not tasks_output.get("tasks"):
            await self._emit(
                EventTypes.PROGRESS,
                data={"message": "Ticket creation skipped - no tickets or tasks in output"},
            )
            return

        # Extract user_id from context (may come from explore phase or spec context)
        user_id = None
        explore_output = self.context.get("explore", {})
        if explore_output:
            user_id = explore_output.get("user_id")
        # Also check if it's in the spec context directly
        if not user_id:
            user_id = self.context.get("user_id")

        try:
            # Create ticket creator
            config = TicketCreatorConfig(
                api_url=self.settings.omoios_api_url,
                project_id=self.settings.omoios_project_id,
                api_key=self.settings.omoios_api_key,
                user_id=user_id,
            )
            creator = TicketCreator(
                config=config,
                reporter=self.reporter,
                spec_id=self.settings.spec_id,
            )

            await self._emit(
                EventTypes.PROGRESS,
                data={
                    "message": "Creating tickets in backend API...",
                    "api_url": self.settings.omoios_api_url,
                    "project_id": self.settings.omoios_project_id,
                    "user_id": user_id,
                },
            )

            # Create tickets and tasks
            self.ticket_creation_summary = await creator.create_from_phase_output(
                tasks_output=tasks_output,
            )

            # Close the HTTP client
            await creator.close()

            # Log results
            summary = self.ticket_creation_summary
            await self._emit(
                EventTypes.PROGRESS,
                data={
                    "message": f"Ticket creation completed: {summary.tickets_created} tickets, {summary.tasks_created} tasks",
                    "tickets_created": summary.tickets_created,
                    "tickets_failed": summary.tickets_failed,
                    "tasks_created": summary.tasks_created,
                    "tasks_failed": summary.tasks_failed,
                    "errors": summary.errors[:5] if summary.errors else [],  # Limit errors in log
                },
            )

            if summary.errors:
                await self._emit(
                    EventTypes.PROGRESS,
                    data={
                        "message": f"Warning: {len(summary.errors)} errors during ticket creation",
                        "error_count": len(summary.errors),
                    },
                )

        except Exception as e:
            # Log error but don't fail the spec - ticket creation is supplementary
            await self._emit(
                EventTypes.PROGRESS,
                data={
                    "message": f"Warning: Ticket creation failed: {e}",
                    "error": str(e),
                },
            )
