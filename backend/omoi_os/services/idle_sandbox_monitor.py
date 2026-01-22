"""Idle Sandbox Monitor - Detects and terminates idle sandboxes.

This service detects sandboxes that:
- Are alive (sending heartbeats)
- Show no work progress (no work events for extended period)
- Have no user input

These idle sandboxes waste Daytona resources and should be terminated.

See docs/design/sandbox-agents/02_gap_analysis.md for design details.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Optional, Set

from omoi_os.logging import get_logger
from omoi_os.models.sandbox_event import SandboxEvent
from omoi_os.models.task import Task
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.services.database import DatabaseService
    from omoi_os.services.daytona_spawner import DaytonaSpawnerService

logger = get_logger("idle_sandbox_monitor")


class IdleSandboxMonitor:
    """Detects and terminates idle sandboxes that show no work progress.

    Work Events (indicate actual progress):

    Agent Events (Claude Agent SDK):
    - agent.file_edited
    - agent.tool_completed
    - agent.subagent_completed
    - agent.skill_completed
    - agent.completed
    - agent.assistant_message
    - agent.tool_use
    - agent.tool_result

    Spec Events (spec-sandbox phases):
    - spec.execution_started, spec.execution_completed
    - spec.phase_started, spec.phase_completed, spec.phase_retry
    - spec.progress, spec.artifact_created
    - spec.requirements_generated, spec.design_generated, spec.tasks_generated
    - spec.sync_started, spec.sync_completed, spec.tasks_queued
    - spec.ticket_created, spec.task_created, etc.

    Non-Work Events (don't indicate progress):
    - agent.heartbeat, spec.heartbeat
    - agent.started
    - agent.thinking
    - agent.error, spec.phase_failed, spec.execution_failed
    """

    # Events that indicate actual work is being done
    # Includes both agent.* events (Claude Agent SDK) and spec.* events (spec-sandbox)
    WORK_EVENT_TYPES: Set[str] = {
        # Agent events (Claude Agent SDK)
        "agent.file_edited",
        "agent.tool_completed",
        "agent.subagent_completed",
        "agent.skill_completed",
        "agent.completed",
        "agent.assistant_message",
        "agent.tool_use",
        "agent.tool_result",
        # Spec events (spec-sandbox phases) - CRITICAL: These indicate spec generation progress
        # Without these, idle monitor may terminate sandboxes that are actively generating specs
        "spec.execution_started",
        "spec.execution_completed",
        "spec.phase_started",
        "spec.phase_completed",
        "spec.phase_retry",
        "spec.progress",
        "spec.artifact_created",
        "spec.requirements_generated",
        "spec.design_generated",
        "spec.tasks_generated",
        "spec.sync_started",
        "spec.sync_completed",
        "spec.tasks_queued",
        # Ticket/task CRUD events from spec-sandbox
        "spec.tickets_creation_started",
        "spec.tickets_creation_completed",
        "spec.ticket_created",
        "spec.ticket_updated",
        "spec.task_created",
        "spec.task_updated",
        # Requirements/design sync events
        "spec.requirements_sync_started",
        "spec.requirements_sync_completed",
        "spec.requirement_created",
        "spec.requirement_updated",
        "spec.design_sync_started",
        "spec.design_sync_completed",
        "spec.design_updated",
    }

    # Default idle threshold (10 minutes - if only heartbeats for this long, sandbox is idle)
    # Increased from 3 minutes to allow spec-sandbox more time for processing
    DEFAULT_IDLE_THRESHOLD = timedelta(minutes=10)

    # Heartbeat timeout (2 minutes - sandbox is dead if no heartbeat for this long)
    HEARTBEAT_TIMEOUT = timedelta(minutes=2)

    # Stuck running threshold (20 minutes - if agent reports "running" but no work events,
    # consider it stuck even though it claims to be working)
    # Doubled from 10 minutes to allow spec-sandbox more time for complex operations
    STUCK_RUNNING_THRESHOLD = timedelta(minutes=20)

    # Heartbeat event types (both agent and spec-sandbox heartbeats)
    HEARTBEAT_EVENT_TYPES: Set[str] = {
        "agent.heartbeat",
        "spec.heartbeat",
    }

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
            # Get last work event
            last_work = (
                session.query(SandboxEvent)
                .filter(
                    SandboxEvent.sandbox_id == sandbox_id,
                    SandboxEvent.event_type.in_(self.WORK_EVENT_TYPES),
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
                # If agent reports itself as 'running', check for stuck condition
                elif heartbeat_status == "running":
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

        # 2. Update associated task status (only if not already completed)
        task_id = None
        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.sandbox_id == sandbox_id).first()
            if task:
                task_id = str(task.id)
                # Only mark as failed if task is still in an active state
                # Don't overwrite completed/cancelled tasks
                if task.status in ("pending", "claiming", "assigned", "running"):
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
        """Check all active sandboxes and terminate any that are idle.

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
                    terminated.append(result)
                elif activity["is_alive"]:
                    # Log why we're NOT terminating this sandbox
                    if activity["has_completed"]:
                        log.debug(
                            "sandbox_skipped_already_completed",
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
