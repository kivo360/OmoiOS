"""Idle Sandbox Monitor - Detects and terminates idle sandboxes.

This service detects sandboxes that:
- Are alive (sending heartbeats)
- Show no work progress (no work events for extended period)
- Have no user input

These idle sandboxes waste Daytona resources and should be terminated.

See docs/design/sandbox-agents/02_gap_analysis.md for design details.

DESIGN PRINCIPLE (2025-01 refactor):
Instead of maintaining an allowlist of "work events" (which is fragile and requires
constant updates as new event types are added), we use an INVERTED approach:

1. Define a small BLOCKLIST of events that are explicitly NOT work:
   - Heartbeats (just keepalive signals)
   - Started events (initialization, not actual work)
   - Error events (failures, not progress)
   - Waiting events (ready state, not doing work)

2. ANY event NOT in the blocklist is considered work.

This means new event types are automatically treated as work, preventing premature
sandbox termination when new features are added.

The canonical event type definitions are in omoi_os.schemas.events.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Optional, Set

from omoi_os.logging import get_logger
from omoi_os.models.sandbox_event import SandboxEvent
from omoi_os.models.task import Task
from omoi_os.schemas.events import (
    NON_WORK_EVENTS,
    AgentEventTypes,
    SpecEventTypes,
)
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.services.database import DatabaseService
    from omoi_os.services.daytona_spawner import DaytonaSpawnerService

logger = get_logger("idle_sandbox_monitor")


class IdleSandboxMonitor:
    """Detects and terminates idle sandboxes that show no work progress.

    INVERTED LOGIC: Instead of allowlisting work events, we blocklist non-work events.
    Any event NOT in the blocklist is considered work, which is safer for new event types.

    Non-Work Events (explicitly excluded from work detection):
    - Heartbeats: agent.heartbeat, spec.heartbeat (keepalive signals, not work)
    - Started events: agent.started (initialization, not actual work)
    - Error events: agent.error, agent.stream_error, spec.phase_failed, spec.execution_failed
    - Waiting events: agent.waiting (ready state, not doing work)
    - Shutdown events: agent.shutdown (cleanup, not work)

    Everything else is considered work, including but not limited to:
    - Tool events: agent.tool_use, agent.tool_result, agent.tool_completed
    - File events: agent.file_edited
    - Message events: agent.message, agent.assistant_message, agent.thinking
    - Subagent/skill events: agent.subagent_*, agent.skill_*
    - Iteration events: iteration.*, continuous.*
    - Spec events: spec.phase_*, spec.execution_*, spec.*_generated, etc.
    """

    # ==========================================================================
    # NON-WORK EVENTS (Blocklist)
    # ==========================================================================
    # Uses the canonical NON_WORK_EVENTS from omoi_os.schemas.events.
    # Any event NOT in this set is considered work.
    # This inverted approach is safer - new event types are automatically treated as work.
    #
    # Convert frozenset to set for SQLAlchemy compatibility
    NON_WORK_EVENT_TYPES: Set[str] = set(NON_WORK_EVENTS)

    # Default idle threshold (10 minutes - if only heartbeats for this long, sandbox is idle)
    # This is for sandboxes that are alive but not doing any work
    DEFAULT_IDLE_THRESHOLD = timedelta(minutes=10)

    # Heartbeat timeout (2 minutes - sandbox is dead if no heartbeat for this long)
    HEARTBEAT_TIMEOUT = timedelta(minutes=2)

    # Stuck running threshold (15 minutes - if agent reports "running" but no work events,
    # consider it stuck even though it claims to be working)
    # This catches sandboxes that are hung/stuck in a loop
    STUCK_RUNNING_THRESHOLD = timedelta(minutes=15)

    # Heartbeat event types (both agent and spec-sandbox heartbeats)
    # Uses canonical event types from omoi_os.schemas.events
    HEARTBEAT_EVENT_TYPES: Set[str] = {
        AgentEventTypes.HEARTBEAT,
        SpecEventTypes.HEARTBEAT,
    }

    # Expected phase order for spec sandboxes
    EXPECTED_PHASES: list[str] = ["explore", "prd", "requirements", "design", "tasks", "sync"]

    # Stuck between phases threshold (5 minutes)
    # If a phase completes but the next phase doesn't start within this time,
    # the sandbox might be stuck
    STUCK_BETWEEN_PHASES_THRESHOLD = timedelta(minutes=5)

    def __init__(
        self,
        db: DatabaseService,
        daytona_spawner: DaytonaSpawnerService,
        event_bus: Optional[EventBusService] = None,
        idle_threshold: Optional[timedelta] = None,
    ):
        """Initialize IdleSandboxMonitor.

        Args:
            db: Database service instance
            daytona_spawner: Daytona spawner for sandbox termination
            event_bus: Optional event bus for publishing termination events
            idle_threshold: Time without work events before considering idle
        """
        self.db = db
        self.daytona_spawner = daytona_spawner
        self.event_bus = event_bus
        self.idle_threshold = idle_threshold or self.DEFAULT_IDLE_THRESHOLD

    def get_active_sandbox_ids(self) -> list[str]:
        """Get sandbox IDs that have recent heartbeats (are alive).

        Returns:
            List of sandbox IDs with heartbeats in the last HEARTBEAT_TIMEOUT
        """
        cutoff = utc_now() - self.HEARTBEAT_TIMEOUT

        with self.db.get_session() as session:
            # Query distinct sandbox IDs with recent heartbeats
            # Supports both agent.heartbeat and spec.heartbeat events
            results = (
                session.query(SandboxEvent.sandbox_id)
                .filter(
                    SandboxEvent.event_type.in_(self.HEARTBEAT_EVENT_TYPES),
                    SandboxEvent.created_at >= cutoff,
                )
                .distinct()
                .all()
            )
            return [r[0] for r in results]

    def get_phase_completion_status(self, sandbox_id: str) -> dict:
        """Get phase completion status for a spec sandbox.

        Detects which phases have completed and if the sandbox is stuck
        between phases (phase completed but next phase hasn't started).

        Args:
            sandbox_id: ID of the sandbox to check

        Returns:
            Dictionary with phase completion details:
            - sandbox_id: The sandbox ID
            - is_spec_sandbox: Whether this is a spec sandbox (starts with 'spec-')
            - phases_completed: List of completed phase names
            - phases_started: List of started phase names
            - last_phase_completed: Name of last completed phase (or None)
            - last_phase_completed_at: Timestamp of last phase completion
            - next_expected_phase: Name of next expected phase (or None if done)
            - is_stuck_between_phases: Whether sandbox appears stuck between phases
            - stuck_duration_seconds: How long it's been stuck (if stuck)
            - has_execution_completed: Whether spec.execution_completed was emitted
            - has_execution_failed: Whether spec.execution_failed was emitted
        """
        is_spec_sandbox = sandbox_id.startswith("spec-")

        if not is_spec_sandbox:
            return {
                "sandbox_id": sandbox_id,
                "is_spec_sandbox": False,
                "phases_completed": [],
                "phases_started": [],
                "last_phase_completed": None,
                "last_phase_completed_at": None,
                "next_expected_phase": None,
                "is_stuck_between_phases": False,
                "stuck_duration_seconds": 0,
                "has_execution_completed": False,
                "has_execution_failed": False,
            }

        with self.db.get_session() as session:
            # Get all phase_started events
            phase_started_events = (
                session.query(SandboxEvent)
                .filter(
                    SandboxEvent.sandbox_id == sandbox_id,
                    SandboxEvent.event_type == SpecEventTypes.PHASE_STARTED,
                )
                .order_by(SandboxEvent.created_at.asc())
                .all()
            )

            # Get all phase_completed events
            phase_completed_events = (
                session.query(SandboxEvent)
                .filter(
                    SandboxEvent.sandbox_id == sandbox_id,
                    SandboxEvent.event_type == SpecEventTypes.PHASE_COMPLETED,
                )
                .order_by(SandboxEvent.created_at.asc())
                .all()
            )

            # Extract phase names
            phases_started = []
            for e in phase_started_events:
                phase = e.event_data.get("phase") if e.event_data else None
                if phase:
                    phases_started.append(phase)

            phases_completed = []
            last_phase_completed = None
            last_phase_completed_at = None
            for e in phase_completed_events:
                phase = e.event_data.get("phase") if e.event_data else None
                if phase:
                    phases_completed.append(phase)
                    last_phase_completed = phase
                    last_phase_completed_at = e.created_at

            # Check for execution completion/failure
            execution_completed = (
                session.query(SandboxEvent)
                .filter(
                    SandboxEvent.sandbox_id == sandbox_id,
                    SandboxEvent.event_type == SpecEventTypes.EXECUTION_COMPLETED,
                )
                .first()
            )

            execution_failed = (
                session.query(SandboxEvent)
                .filter(
                    SandboxEvent.sandbox_id == sandbox_id,
                    SandboxEvent.event_type == SpecEventTypes.EXECUTION_FAILED,
                )
                .first()
            )

            # Determine next expected phase
            next_expected_phase = None
            if last_phase_completed and last_phase_completed in self.EXPECTED_PHASES:
                idx = self.EXPECTED_PHASES.index(last_phase_completed)
                if idx + 1 < len(self.EXPECTED_PHASES):
                    next_expected_phase = self.EXPECTED_PHASES[idx + 1]

            # Check if stuck between phases
            is_stuck_between_phases = False
            stuck_duration_seconds = 0
            now = utc_now()

            if (
                last_phase_completed_at
                and next_expected_phase
                and next_expected_phase not in phases_started
                and not execution_completed
                and not execution_failed
            ):
                # A phase completed, next phase hasn't started, and execution isn't done
                time_since_completion = now - last_phase_completed_at
                if time_since_completion > self.STUCK_BETWEEN_PHASES_THRESHOLD:
                    is_stuck_between_phases = True
                    stuck_duration_seconds = time_since_completion.total_seconds()
                    logger.warning(
                        "sandbox_stuck_between_phases",
                        sandbox_id=sandbox_id,
                        last_phase=last_phase_completed,
                        next_expected=next_expected_phase,
                        stuck_seconds=stuck_duration_seconds,
                    )

            return {
                "sandbox_id": sandbox_id,
                "is_spec_sandbox": True,
                "phases_completed": phases_completed,
                "phases_started": phases_started,
                "last_phase_completed": last_phase_completed,
                "last_phase_completed_at": (
                    last_phase_completed_at.isoformat() if last_phase_completed_at else None
                ),
                "next_expected_phase": next_expected_phase,
                "is_stuck_between_phases": is_stuck_between_phases,
                "stuck_duration_seconds": stuck_duration_seconds,
                "has_execution_completed": execution_completed is not None,
                "has_execution_failed": execution_failed is not None,
            }

    def check_sandbox_activity(self, sandbox_id: str) -> dict:
        """Check if a sandbox has recent work activity.

        Args:
            sandbox_id: ID of the sandbox to check

        Returns:
            Dictionary with activity details:
            - sandbox_id: The sandbox ID
            - last_work_at: Timestamp of last work event (or None)
            - last_heartbeat_at: Timestamp of last heartbeat (or None)
            - heartbeat_status: Status from last heartbeat ('idle', 'running', etc.)
            - has_completed: Whether agent.completed event was seen
            - is_alive: Whether sandbox has recent heartbeats
            - is_idle: Whether sandbox is alive but has no recent work
            - idle_duration_seconds: How long the sandbox has been idle
        """
        with self.db.get_session() as session:
            # Get last work event using INVERTED logic:
            # Any event NOT in the blocklist is considered work.
            # This is safer than allowlisting - new event types are automatically treated as work.
            last_work = (
                session.query(SandboxEvent)
                .filter(
                    SandboxEvent.sandbox_id == sandbox_id,
                    SandboxEvent.event_type.notin_(self.NON_WORK_EVENT_TYPES),
                )
                .order_by(SandboxEvent.created_at.desc())
                .first()
            )

            # Get last heartbeat (supports both agent and spec-sandbox heartbeats)
            last_heartbeat = (
                session.query(SandboxEvent)
                .filter(
                    SandboxEvent.sandbox_id == sandbox_id,
                    SandboxEvent.event_type.in_(self.HEARTBEAT_EVENT_TYPES),
                )
                .order_by(SandboxEvent.created_at.desc())
                .first()
            )

            # Check if agent.completed event exists (agent finished its work)
            # Get the LATEST completion event timestamp so we can check if work
            # happened after completion (agent was resumed)
            completed_event = (
                session.query(SandboxEvent)
                .filter(
                    SandboxEvent.sandbox_id == sandbox_id,
                    SandboxEvent.event_type == "agent.completed",
                )
                .order_by(SandboxEvent.created_at.desc())
                .first()
            )
            completed_at = completed_event.created_at if completed_event else None

            # Check if work happened AFTER the last completion (agent resumed work)
            # If so, the completion is "stale" and agent is effectively running again
            has_completed = False
            if completed_at:
                if last_work and last_work.created_at > completed_at:
                    # Work happened after completion - agent resumed
                    has_completed = False
                    logger.debug(
                        "sandbox_completion_reset_by_resumed_work",
                        sandbox_id=sandbox_id,
                        completed_at=completed_at.isoformat(),
                        last_work_at=last_work.created_at.isoformat(),
                    )
                else:
                    # No work after completion - agent is truly done
                    has_completed = True

            now = utc_now()

            # Determine if alive (has recent heartbeat)
            is_alive = False
            heartbeat_status = None
            if last_heartbeat:
                heartbeat_age = now - last_heartbeat.created_at
                is_alive = heartbeat_age < self.HEARTBEAT_TIMEOUT
                # Extract status from heartbeat payload
                if last_heartbeat.event_data:
                    heartbeat_status = last_heartbeat.event_data.get("status")

            # Determine if idle (alive but no recent work)
            # IMPORTANT: Several conditions mean the sandbox is NOT idle:
            # 1. Agent has completed (agent.completed event seen) - work is done
            # 2. Heartbeat reports 'running' status - agent is actively working
            is_idle = False
            idle_duration_seconds = 0

            # Track if agent is stuck (reports running but no actual work)
            is_stuck_running = False

            if is_alive:
                # If agent has completed, it's not idle - it finished its work
                if has_completed:
                    is_idle = False
                    idle_duration_seconds = 0
                    logger.debug(
                        "sandbox_not_idle_agent_completed",
                        sandbox_id=sandbox_id,
                    )
                # If agent reports itself as 'running' or 'alive', check for stuck condition
                # 'running' = spec state machine actively running
                # 'alive' = regular agent worker actively processing
                elif heartbeat_status in ("running", "alive"):
                    # Check if agent is "stuck running" - reports running but no work
                    if last_work:
                        work_age = now - last_work.created_at
                        if work_age > self.STUCK_RUNNING_THRESHOLD:
                            # Agent claims running but hasn't done work in 10+ minutes
                            # This is a stuck agent - force terminate
                            is_idle = True
                            is_stuck_running = True
                            idle_duration_seconds = work_age.total_seconds()
                            logger.warning(
                                "sandbox_stuck_running_detected",
                                sandbox_id=sandbox_id,
                                heartbeat_status=heartbeat_status,
                                work_age_seconds=work_age.total_seconds(),
                            )
                        else:
                            # Agent is running and has done work recently enough
                            is_idle = False
                            idle_duration_seconds = 0
                            logger.debug(
                                "sandbox_not_idle_agent_running",
                                sandbox_id=sandbox_id,
                                heartbeat_status=heartbeat_status,
                            )
                    else:
                        # Never did any work but claims running - give it time
                        # (might still be initializing)
                        is_idle = False
                        idle_duration_seconds = 0
                        logger.debug(
                            "sandbox_not_idle_agent_running_no_work_yet",
                            sandbox_id=sandbox_id,
                        )
                elif not last_work:
                    # Never did any work AND agent doesn't report running AND not completed
                    is_idle = True
                    if last_heartbeat:
                        idle_duration_seconds = (now - last_heartbeat.created_at).total_seconds()
                else:
                    work_age = now - last_work.created_at
                    is_idle = work_age > self.idle_threshold
                    idle_duration_seconds = work_age.total_seconds()

            return {
                "sandbox_id": sandbox_id,
                "last_work_at": last_work.created_at.isoformat() if last_work else None,
                "last_heartbeat_at": last_heartbeat.created_at.isoformat() if last_heartbeat else None,
                "heartbeat_status": heartbeat_status,
                "has_completed": has_completed,
                "is_alive": is_alive,
                "is_idle": is_idle,
                "is_stuck_running": is_stuck_running,
                "idle_duration_seconds": idle_duration_seconds,
            }

    async def _save_transcript(self, sandbox_id: str, transcript_b64: str) -> bool:
        """Save a session transcript to the database.

        Uses the existing save_session_transcript function from sandbox routes.

        Args:
            sandbox_id: ID of the sandbox the transcript came from
            transcript_b64: Base64-encoded transcript content

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Generate a session ID from the sandbox_id if we don't have one
            # The transcript file name might contain the actual session ID, but
            # for idle termination we'll use sandbox_id as the session reference
            session_id = f"idle-{sandbox_id}"

            # Get task_id from the sandbox
            task_id = None
            with self.db.get_session() as session:
                task = session.query(Task).filter(Task.sandbox_id == sandbox_id).first()
                if task:
                    task_id = str(task.id)

            # Save transcript using the existing function from sandbox routes
            from omoi_os.api.routes.sandbox import save_session_transcript

            save_session_transcript(
                db=self.db,
                session_id=session_id,
                sandbox_id=sandbox_id,
                task_id=task_id,
                transcript_b64=transcript_b64,
            )

            logger.info(
                "transcript_saved",
                sandbox_id=sandbox_id,
                session_id=session_id,
                task_id=task_id,
            )
            return True

        except Exception as e:
            logger.error(
                "transcript_save_failed",
                sandbox_id=sandbox_id,
                error=str(e),
            )
            return False

    async def terminate_idle_sandbox(
        self,
        sandbox_id: str,
        reason: str = "idle_timeout",
        idle_duration_seconds: float = 0,
    ) -> dict:
        """Terminate an idle sandbox.

        Before termination, attempts to extract and save the session transcript
        for potential later resumption or debugging.

        Args:
            sandbox_id: ID of the sandbox to terminate
            reason: Reason for termination
            idle_duration_seconds: How long the sandbox was idle

        Returns:
            Dictionary with termination details
        """
        log = logger.bind(sandbox_id=sandbox_id, reason=reason)
        log.info(
            "terminating_idle_sandbox",
            idle_duration_seconds=idle_duration_seconds,
        )

        # 0. Extract and save session transcript before termination
        transcript_saved = False
        try:
            transcript_b64 = await self.daytona_spawner.extract_session_transcript(
                sandbox_id
            )
            if transcript_b64:
                # Save the transcript to database
                await self._save_transcript(sandbox_id, transcript_b64)
                transcript_saved = True
                log.info("transcript_saved_before_termination")
            else:
                log.debug("no_transcript_to_save")
        except Exception as e:
            log.warning("transcript_extraction_failed", error=str(e))
            # Continue with termination even if transcript extraction fails

        # 1. Stop sandbox via Daytona
        try:
            await self.daytona_spawner.terminate_sandbox(sandbox_id)
            log.info("sandbox_stopped")
        except Exception as e:
            log.error("sandbox_stop_failed", error=str(e))
            # Continue to update task status even if stop fails

        # 2. Update associated task status
        # For completion-based termination: don't change task status (it should already be completed)
        # For failure-based termination: mark as failed if still in active state
        task_id = None
        is_graceful_completion = reason in (
            "execution_completed",
            "execution_failed",
        )

        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.sandbox_id == sandbox_id).first()
            if task:
                task_id = str(task.id)

                if is_graceful_completion:
                    # Graceful completion - sandbox is being cleaned up after work is done
                    # Don't change task status; it should already be set appropriately
                    log.info(
                        "task_status_preserved_graceful_completion",
                        task_id=task_id,
                        existing_status=task.status,
                        reason=reason,
                    )
                elif task.status in ("pending", "claiming", "assigned", "running"):
                    # Failure-based termination (idle, stuck) - mark task as failed
                    task.status = "failed"
                    task.error_message = (
                        f"Sandbox terminated: {reason}. "
                        f"Idle for {int(idle_duration_seconds / 60)} minutes with no work progress."
                    )
                    session.commit()
                    log.info("task_status_updated", task_id=task_id, new_status="failed")
                else:
                    log.info(
                        "task_status_preserved",
                        task_id=task_id,
                        existing_status=task.status,
                        reason="Task already in terminal state",
                    )
            else:
                log.warning("no_task_found_for_sandbox")

        # 3. Emit event
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="SANDBOX_TERMINATED_IDLE",
                    entity_type="sandbox",
                    entity_id=sandbox_id,
                    payload={
                        "reason": reason,
                        "idle_duration_seconds": idle_duration_seconds,
                        "task_id": task_id,
                        "transcript_saved": transcript_saved,
                    },
                )
            )
            log.debug("termination_event_published")

        return {
            "sandbox_id": sandbox_id,
            "terminated": True,
            "transcript_saved": transcript_saved,
            "reason": reason,
            "task_id": task_id,
            "idle_duration_seconds": idle_duration_seconds,
        }

    async def check_and_terminate_idle_sandboxes(self) -> list[dict]:
        """Check all active sandboxes and terminate any that are idle, stuck, or completed.

        This method checks for:
        1. Completed sandboxes (spec.execution_completed or agent.completed) - graceful cleanup
        2. Idle sandboxes (no work events for extended period)
        3. Stuck running sandboxes (reports running but no actual work)
        4. Stuck between phases (phase completed but next phase hasn't started)

        Returns:
            List of termination results for any sandboxes that were terminated
        """
        log = logger.bind()

        # Get all active sandboxes
        active_sandbox_ids = self.get_active_sandbox_ids()
        log.debug("checking_sandboxes", count=len(active_sandbox_ids))

        terminated = []

        for sandbox_id in active_sandbox_ids:
            try:
                activity = self.check_sandbox_activity(sandbox_id)

                # For spec sandboxes, also check phase completion status
                phase_status = None
                if sandbox_id.startswith("spec-"):
                    phase_status = self.get_phase_completion_status(sandbox_id)

                    # Log phase status for visibility
                    log.debug(
                        "spec_sandbox_phase_status",
                        sandbox_id=sandbox_id,
                        phases_completed=phase_status.get("phases_completed", []),
                        phases_started=phase_status.get("phases_started", []),
                        last_phase_completed=phase_status.get("last_phase_completed"),
                        next_expected_phase=phase_status.get("next_expected_phase"),
                        is_stuck_between_phases=phase_status.get("is_stuck_between_phases"),
                        has_execution_completed=phase_status.get("has_execution_completed"),
                        has_execution_failed=phase_status.get("has_execution_failed"),
                    )

                    # Check for completed spec sandboxes - terminate gracefully
                    if phase_status.get("has_execution_completed") or phase_status.get(
                        "has_execution_failed"
                    ):
                        reason = (
                            "execution_completed"
                            if phase_status.get("has_execution_completed")
                            else "execution_failed"
                        )
                        log.info(
                            "completed_spec_sandbox_detected",
                            sandbox_id=sandbox_id,
                            reason=reason,
                            phases_completed=phase_status.get("phases_completed", []),
                        )

                        result = await self.terminate_idle_sandbox(
                            sandbox_id=sandbox_id,
                            reason=reason,
                            idle_duration_seconds=0,  # Not idle, just completed
                        )
                        result["phase_status"] = phase_status
                        terminated.append(result)
                        continue  # Don't check other conditions

                # Check for stuck-between-phases condition (spec sandboxes only)
                if phase_status and phase_status.get("is_stuck_between_phases"):
                    reason = "stuck_between_phases"
                    log.warning(
                        "stuck_between_phases_sandbox_detected",
                        sandbox_id=sandbox_id,
                        last_phase=phase_status.get("last_phase_completed"),
                        next_expected=phase_status.get("next_expected_phase"),
                        stuck_duration_seconds=phase_status.get("stuck_duration_seconds"),
                        phases_completed=phase_status.get("phases_completed"),
                    )

                    result = await self.terminate_idle_sandbox(
                        sandbox_id=sandbox_id,
                        reason=reason,
                        idle_duration_seconds=phase_status.get("stuck_duration_seconds", 0),
                    )
                    # Add phase status to result for API visibility
                    result["phase_status"] = phase_status
                    terminated.append(result)
                    continue  # Don't check other conditions

                if activity["is_idle"]:
                    # Determine appropriate reason based on why it's idle
                    if activity.get("is_stuck_running"):
                        reason = "stuck_running"
                        log.warning(
                            "stuck_running_sandbox_detected",
                            sandbox_id=sandbox_id,
                            idle_duration_seconds=activity["idle_duration_seconds"],
                            last_work_at=activity["last_work_at"],
                            heartbeat_status=activity["heartbeat_status"],
                        )
                    else:
                        reason = "idle_timeout"
                        log.info(
                            "idle_sandbox_detected",
                            sandbox_id=sandbox_id,
                            idle_duration_seconds=activity["idle_duration_seconds"],
                            last_work_at=activity["last_work_at"],
                            heartbeat_status=activity["heartbeat_status"],
                        )

                    result = await self.terminate_idle_sandbox(
                        sandbox_id=sandbox_id,
                        reason=reason,
                        idle_duration_seconds=activity["idle_duration_seconds"],
                    )
                    # Add phase status if available
                    if phase_status:
                        result["phase_status"] = phase_status
                    terminated.append(result)
                elif activity["is_alive"]:
                    # Note: We don't terminate on agent.completed for regular sandboxes
                    # because continuous agents emit agent.completed multiple times
                    # during execution. Let idle detection handle cleanup instead.
                    if activity["has_completed"]:
                        log.debug(
                            "sandbox_has_completed_event",
                            sandbox_id=sandbox_id,
                        )
                    elif activity["heartbeat_status"] == "running":
                        log.debug(
                            "sandbox_skipped_agent_running",
                            sandbox_id=sandbox_id,
                            heartbeat_status=activity["heartbeat_status"],
                        )

            except Exception as e:
                log.error(
                    "sandbox_check_failed",
                    sandbox_id=sandbox_id,
                    error=str(e),
                )

        if terminated:
            log.info("idle_sandboxes_terminated", count=len(terminated))

        return terminated

    def get_all_sandbox_status(self) -> list[dict]:
        """Get status for all active sandboxes including phase completion.

        Returns a list of status dictionaries for all sandboxes that have
        recent heartbeats, including their activity status and phase completion
        status (for spec sandboxes).

        Returns:
            List of status dictionaries with keys:
            - sandbox_id: The sandbox ID
            - activity: Activity check results (is_idle, is_alive, etc.)
            - phase_status: Phase completion status (for spec sandboxes only)
        """
        active_sandbox_ids = self.get_active_sandbox_ids()
        results = []

        for sandbox_id in active_sandbox_ids:
            try:
                activity = self.check_sandbox_activity(sandbox_id)

                status = {
                    "sandbox_id": sandbox_id,
                    "activity": activity,
                    "phase_status": None,
                }

                # Add phase status for spec sandboxes
                if sandbox_id.startswith("spec-"):
                    status["phase_status"] = self.get_phase_completion_status(sandbox_id)

                results.append(status)

            except Exception as e:
                logger.error(
                    "sandbox_status_check_failed",
                    sandbox_id=sandbox_id,
                    error=str(e),
                )
                results.append({
                    "sandbox_id": sandbox_id,
                    "activity": None,
                    "phase_status": None,
                    "error": str(e),
                })

        return results
