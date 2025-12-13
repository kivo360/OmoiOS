"""
Orchestrator Worker - Standalone process for task orchestration.

Runs the orchestrator loop that:
- Polls for pending tasks
- Spawns Daytona sandboxes (when DAYTONA_SANDBOX_EXECUTION=true)
- Assigns tasks to agents (legacy mode)

Run with: python -m omoi_os.workers.orchestrator_worker
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import time
from typing import TYPE_CHECKING, Literal

import structlog

if TYPE_CHECKING:
    from omoi_os.services.database import DatabaseService
    from omoi_os.services.task_queue import TaskQueueService
    from omoi_os.services.event_bus import EventBusService
    from omoi_os.services.agent_registry import AgentRegistryService

# Configure structlog for JSON output
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)
logger = structlog.get_logger("orchestrator")

# Services (initialized in init_services)
db: DatabaseService | None = None
queue: TaskQueueService | None = None
event_bus: EventBusService | None = None
registry_service: AgentRegistryService | None = None

# Shutdown flag
shutdown_event = asyncio.Event()

# Stats tracking (global for heartbeat access)
stats = {
    "poll_count": 0,
    "tasks_processed": 0,
    "tasks_failed": 0,
    "start_time": 0.0,
}


async def heartbeat_task():
    """Log heartbeat every 30 seconds to confirm worker is alive."""
    heartbeat_num = 0
    while not shutdown_event.is_set():
        heartbeat_num += 1
        uptime = int(time.time() - stats["start_time"])
        logger.info(
            "heartbeat",
            heartbeat_num=heartbeat_num,
            uptime_seconds=uptime,
            poll_count=stats["poll_count"],
            tasks_processed=stats["tasks_processed"],
            tasks_failed=stats["tasks_failed"],
        )
        await asyncio.sleep(30)


async def orchestrator_loop():
    """Background task that polls queue and assigns tasks to workers.

    Supports two execution modes:
    1. Legacy mode (SANDBOX_EXECUTION=false): Assigns to DB agents, workers poll
    2. Sandbox mode (SANDBOX_EXECUTION=true): Spawns Daytona sandboxes per task
    """
    global db, queue, event_bus, registry_service

    if not db or not queue or not event_bus:
        logger.error("services_not_initialized")
        return

    logger.info("orchestrator_loop_started")

    # Check if sandbox execution is enabled
    from omoi_os.config import get_app_settings

    settings = get_app_settings()
    sandbox_execution = settings.daytona.sandbox_execution
    mode = "sandbox" if sandbox_execution else "legacy"

    # Initialize Daytona spawner if sandbox mode enabled
    daytona_spawner = None
    if sandbox_execution:
        try:
            from omoi_os.services.daytona_spawner import get_daytona_spawner

            daytona_spawner = get_daytona_spawner(db=db, event_bus=event_bus)
            logger.info("daytona_spawner_initialized", mode=mode)
        except Exception as e:
            logger.error("daytona_spawner_failed", error=str(e))
            logger.warning("falling_back_to_legacy_mode")
            sandbox_execution = False
            mode = "legacy"
    else:
        logger.info("legacy_mode_enabled", mode=mode)

    while not shutdown_event.is_set():
        try:
            stats["poll_count"] += 1
            cycle = stats["poll_count"]

            # Create cycle-bound logger
            log = logger.bind(cycle=cycle, mode=mode)
            log.debug("poll_started")

            # Get next pending task (no agent filter in sandbox mode)
            from omoi_os.models.agent import Agent
            from omoi_os.models.agent_status import AgentStatus

            available_agent_id = None

            with db.get_session() as session:
                if sandbox_execution:
                    # Sandbox mode: just get next pending task
                    task = queue.get_next_task(phase_id=None)
                else:
                    # Legacy mode: check for available agent first
                    available_agent = (
                        session.query(Agent)
                        .filter(Agent.status == AgentStatus.IDLE.value)
                        .first()
                    )
                    if not available_agent:
                        log.debug("no_idle_agents")
                        await asyncio.sleep(5)
                        continue

                    available_agent_id = str(available_agent.id)
                    agent_capabilities = available_agent.capabilities or []
                    phase_id = "PHASE_IMPLEMENTATION"

                    task = queue.get_next_task(
                        phase_id, agent_capabilities=agent_capabilities
                    )

            if task:
                task_id = str(task.id)
                phase_id = task.phase_id or "PHASE_IMPLEMENTATION"

                # Bind task context to logger
                log = log.bind(
                    task_id=task_id, phase=phase_id, ticket_id=str(task.ticket_id)
                )
                log.info("task_found")

                if sandbox_execution and daytona_spawner:
                    # Sandbox mode: spawn a Daytona sandbox for this task
                    try:
                        # Extract user_id, repo info, ticket info, and GitHub token from DB
                        # This enables per-user credentials and GitHub branch workflow
                        extra_env: dict[str, str] = {}
                        user_id_for_token = None
                        with db.get_session() as session:
                            from omoi_os.models.ticket import Ticket
                            from omoi_os.models.user import User

                            ticket = session.get(Ticket, task.ticket_id)
                            if ticket:
                                # Ticket info for branch naming
                                extra_env["TICKET_ID"] = str(ticket.id)
                                extra_env["TICKET_TITLE"] = ticket.title or ""
                                # Determine ticket type from phase or status
                                ticket_type = "feature"
                                if ticket.priority == "CRITICAL":
                                    ticket_type = "hotfix"
                                elif "bug" in (ticket.title or "").lower():
                                    ticket_type = "bug"
                                extra_env["TICKET_TYPE"] = ticket_type

                                if ticket.project:
                                    if ticket.project.created_by:
                                        user_id_for_token = ticket.project.created_by
                                        extra_env["USER_ID"] = str(user_id_for_token)
                                    # Combine owner/repo into GITHUB_REPO format
                                    owner = ticket.project.github_owner
                                    repo = ticket.project.github_repo
                                    if owner and repo:
                                        extra_env["GITHUB_REPO"] = f"{owner}/{repo}"
                                        # Also keep separate vars for backwards compat
                                        extra_env["GITHUB_REPO_OWNER"] = owner
                                        extra_env["GITHUB_REPO_NAME"] = repo

                            # Fetch GitHub token from user attributes
                            # Token is stored in user.attributes.github_access_token (via OAuth)
                            if user_id_for_token:
                                user = session.get(User, user_id_for_token)
                                if user:
                                    attrs = user.attributes or {}
                                    github_token = attrs.get("github_access_token")
                                    if github_token:
                                        extra_env["GITHUB_TOKEN"] = github_token
                                        log.debug(
                                            "github_token_found",
                                            user_id=str(user_id_for_token),
                                        )
                                    else:
                                        log.debug(
                                            "no_github_token",
                                            user_id=str(user_id_for_token),
                                        )

                        log.debug(
                            "env_extracted",
                            user_id=extra_env.get("USER_ID"),
                            github_repo=extra_env.get("GITHUB_REPO"),
                            ticket_type=extra_env.get("TICKET_TYPE"),
                            has_github_token="GITHUB_TOKEN" in extra_env,
                        )

                        # Determine agent type from phase
                        from omoi_os.agents.templates import get_template_for_phase

                        template = get_template_for_phase(phase_id)
                        agent_type: Literal[
                            "planner",
                            "implementer",
                            "validator",
                            "diagnostician",
                            "coordinator",
                        ] = template.agent_type.value

                        # Register sandbox agent in database (skip heartbeat wait)
                        from omoi_os.models.agent import Agent
                        from uuid import uuid4

                        agent_id = str(uuid4())
                        capabilities = (
                            template.tools.get_sdk_tools()
                            if template.tools
                            else ["sandbox"]
                        )

                        with db.get_session() as session:
                            agent = Agent(
                                id=agent_id,
                                agent_type=agent_type,
                                phase_id=phase_id,
                                capabilities=capabilities,
                                status="RUNNING",
                                tags=["sandbox", "daytona"],
                                health_status="healthy",
                            )
                            session.add(agent)
                            session.commit()

                        log.info(
                            "spawning_sandbox", agent_id=agent_id, agent_type=agent_type
                        )

                        # Spawn sandbox with user/repo context
                        sandbox_id = await daytona_spawner.spawn_for_task(
                            task_id=task_id,
                            agent_id=agent_id,
                            phase_id=phase_id,
                            agent_type=agent_type,
                            extra_env=extra_env if extra_env else None,
                        )

                        # Update task with sandbox info
                        queue.assign_task(task.id, agent_id)

                        stats["tasks_processed"] += 1
                        log.info(
                            "sandbox_spawned", sandbox_id=sandbox_id, agent_id=agent_id
                        )

                        # Publish event
                        from omoi_os.services.event_bus import SystemEvent

                        event_bus.publish(
                            SystemEvent(
                                event_type="SANDBOX_SPAWNED",
                                entity_type="sandbox",
                                entity_id=sandbox_id,
                                payload={
                                    "task_id": task_id,
                                    "agent_id": agent_id,
                                    "phase_id": phase_id,
                                },
                            )
                        )

                    except Exception as spawn_error:
                        import traceback

                        error_details = traceback.format_exc()
                        stats["tasks_failed"] += 1
                        log.error(
                            "sandbox_spawn_failed",
                            error=str(spawn_error),
                            traceback=error_details,
                        )
                        # Mark task as failed
                        queue.update_task_status(
                            task.id,
                            "failed",
                            error_message=f"Sandbox spawn failed: {spawn_error}",
                        )
                else:
                    # Legacy mode: assign to available agent
                    queue.assign_task(task.id, available_agent_id)
                    agent_id = available_agent_id

                    from omoi_os.services.event_bus import SystemEvent

                    event_bus.publish(
                        SystemEvent(
                            event_type="TASK_ASSIGNED",
                            entity_type="task",
                            entity_id=task_id,
                            payload={"agent_id": agent_id},
                        )
                    )

                    stats["tasks_processed"] += 1
                    log.info("task_assigned", agent_id=agent_id)

            else:
                log.debug("no_pending_tasks")

            # Poll every 10 seconds
            await asyncio.sleep(10)

        except asyncio.CancelledError:
            logger.info("orchestrator_loop_cancelled")
            break
        except Exception as e:
            stats["tasks_failed"] += 1
            logger.error("orchestrator_loop_error", error=str(e))
            await asyncio.sleep(10)


async def init_services():
    """Initialize required services."""
    global db, queue, event_bus, registry_service

    logger.info("initializing_services")

    from omoi_os.config import get_app_settings
    from omoi_os.services.database import DatabaseService
    from omoi_os.services.task_queue import TaskQueueService
    from omoi_os.services.event_bus import EventBusService
    from omoi_os.services.agent_registry import AgentRegistryService

    app_settings = get_app_settings()

    # Database - pass connection string, not settings object
    db = DatabaseService(connection_string=app_settings.database.url)
    logger.info("service_initialized", service="database")

    # Task Queue (Redis-backed)
    queue = TaskQueueService(db)
    logger.info("service_initialized", service="task_queue")

    # Event Bus (Redis-backed)
    event_bus = EventBusService(redis_url=app_settings.redis.url)
    logger.info("service_initialized", service="event_bus")

    # Agent Registry
    registry_service = AgentRegistryService(db)
    logger.info("service_initialized", service="agent_registry")

    logger.info("all_services_initialized")


async def shutdown():
    """Graceful shutdown."""
    uptime = int(time.time() - stats["start_time"]) if stats["start_time"] else 0
    logger.info(
        "shutting_down",
        uptime_seconds=uptime,
        total_polls=stats["poll_count"],
        tasks_processed=stats["tasks_processed"],
        tasks_failed=stats["tasks_failed"],
    )
    shutdown_event.set()

    # Close database connections
    if db:
        db.close()
        logger.info("service_closed", service="database")

    # Close event bus
    if event_bus:
        event_bus.close()
        logger.info("service_closed", service="event_bus")

    logger.info("orchestrator_stopped")


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    asyncio.create_task(shutdown())


async def main():
    """Main entry point."""
    stats["start_time"] = time.time()

    logger.info(
        "orchestrator_starting",
        version="1.0.0",
        pid=os.getpid(),
    )

    # Setup signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown()))

    try:
        await init_services()
        # Run heartbeat and orchestrator loop concurrently
        await asyncio.gather(
            heartbeat_task(),
            orchestrator_loop(),
        )
    except KeyboardInterrupt:
        await shutdown()
    except Exception as e:
        logger.error("fatal_error", error=str(e))
        await shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
