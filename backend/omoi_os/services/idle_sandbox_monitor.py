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
    - agent.file_edited
    - agent.tool_completed
    - agent.subagent_completed
    - agent.skill_completed
    - agent.completed
    - agent.assistant_message
    - agent.tool_use
    - agent.tool_result

    Non-Work Events (don't indicate progress):
    - agent.heartbeat
    - agent.started
    - agent.thinking
    - agent.error
    """

    # Events that indicate actual work is being done
    WORK_EVENT_TYPES: Set[str] = {
        "agent.file_edited",
        "agent.tool_completed",
        "agent.subagent_completed",
        "agent.skill_completed",
        "agent.completed",
        "agent.assistant_message",
        "agent.tool_use",
        "agent.tool_result",
    }

    # Default idle threshold (3 minutes - if only heartbeats for this long, sandbox is idle)
    DEFAULT_IDLE_THRESHOLD = timedelta(minutes=3)

    # Heartbeat timeout (90 seconds - sandbox is dead if no heartbeat for this long)
    HEARTBEAT_TIMEOUT = timedelta(seconds=90)

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
            results = (
                session.query(SandboxEvent.sandbox_id)
                .filter(
                    SandboxEvent.event_type == "agent.heartbeat",
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

            # Get last heartbeat
            last_heartbeat = (
                session.query(SandboxEvent)
                .filter(
                    SandboxEvent.sandbox_id == sandbox_id,
                    SandboxEvent.event_type == "agent.heartbeat",
                )
                .order_by(SandboxEvent.created_at.desc())
                .first()
            )

            now = utc_now()

            # Determine if alive (has recent heartbeat)
            is_alive = False
            if last_heartbeat:
                heartbeat_age = now - last_heartbeat.created_at
                is_alive = heartbeat_age < self.HEARTBEAT_TIMEOUT

            # Determine if idle (alive but no recent work)
            is_idle = False
            idle_duration_seconds = 0

            if is_alive:
                if not last_work:
                    # Never did any work - considered idle from start
                    is_idle = True
                    if last_heartbeat:
                        # Idle since first heartbeat
                        idle_duration_seconds = (now - last_heartbeat.created_at).total_seconds()
                else:
                    work_age = now - last_work.created_at
                    is_idle = work_age > self.idle_threshold
                    idle_duration_seconds = work_age.total_seconds()

            return {
                "sandbox_id": sandbox_id,
                "last_work_at": last_work.created_at.isoformat() if last_work else None,
                "last_heartbeat_at": last_heartbeat.created_at.isoformat() if last_heartbeat else None,
                "is_alive": is_alive,
                "is_idle": is_idle,
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
        task_id = None
        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.sandbox_id == sandbox_id).first()
            if task:
                task_id = str(task.id)
                task.status = "failed"
                task.error_message = (
                    f"Sandbox terminated: {reason}. "
                    f"Idle for {int(idle_duration_seconds / 60)} minutes with no work progress."
                )
                session.commit()
                log.info("task_status_updated", task_id=task_id)
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
                    log.info(
                        "idle_sandbox_detected",
                        sandbox_id=sandbox_id,
                        idle_duration_seconds=activity["idle_duration_seconds"],
                        last_work_at=activity["last_work_at"],
                    )

                    result = await self.terminate_idle_sandbox(
                        sandbox_id=sandbox_id,
                        reason="idle_timeout",
                        idle_duration_seconds=activity["idle_duration_seconds"],
                    )
                    terminated.append(result)

            except Exception as e:
                log.error(
                    "sandbox_check_failed",
                    sandbox_id=sandbox_id,
                    error=str(e),
                )

        if terminated:
            log.info("idle_sandboxes_terminated", count=len(terminated))

        return terminated
