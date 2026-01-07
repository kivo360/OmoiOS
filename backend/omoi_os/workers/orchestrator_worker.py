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
import os
import signal
import sys
import time
from typing import TYPE_CHECKING, Literal, Optional

# Configure logging before any other imports that might log
from omoi_os.logging import configure_logging, get_logger

_env = os.environ.get("OMOIOS_ENV", "development")
configure_logging(env=_env)  # type: ignore[arg-type]

if TYPE_CHECKING:
    from omoi_os.services.database import DatabaseService
    from omoi_os.services.task_queue import TaskQueueService
    from omoi_os.services.event_bus import EventBusService
    from omoi_os.services.agent_registry import AgentRegistryService
    from omoi_os.services.task_requirements_analyzer import TaskRequirements

logger = get_logger("orchestrator")

# Task requirements analyzer (initialized in init_services)
task_analyzer: Optional["TaskRequirementsAnalyzer"] = None

# Services (initialized in init_services)
db: DatabaseService | None = None
queue: TaskQueueService | None = None
event_bus: EventBusService | None = None
registry_service: AgentRegistryService | None = None

# Shutdown flag
shutdown_event = asyncio.Event()

# Task ready event - set when a new task is created (for instant wakeup)
task_ready_event = asyncio.Event()

# Stats tracking (global for heartbeat access)
stats = {
    "poll_count": 0,
    "tasks_processed": 0,
    "tasks_failed": 0,
    "events_received": 0,
    "start_time": 0.0,
}


# Task type categories for execution mode determination
# These task types are research/analysis focused and do NOT produce code changes.
# They get execution_mode="exploration" which disables git validation requirements.
EXPLORATION_TASK_TYPES = frozenset([
    # Codebase exploration and analysis
    "explore_codebase",
    "analyze_codebase",
    "analyze_requirements",  # Research task - doesn't write code
    "analyze_dependencies",
    # Spec and requirements creation (produces docs, not code)
    "create_spec",
    "create_requirements",
    "create_design",
    "create_tickets",
    "create_tasks",
    "define_feature",
    "generate_prd",  # Dynamic PRD generation (produces docs, not code)
    # Research and discovery
    "research",
    "discover",
    "investigate",
])

VALIDATION_TASK_TYPES = frozenset([
    "validate",
    "validate_implementation",
    "review_code",
    "run_tests",
])


def get_execution_mode(task_type: str) -> Literal["exploration", "implementation", "validation"]:
    """Determine execution mode based on task type (fallback method).

    This is the fallback for when LLM-based analysis is unavailable.
    Prefer using analyze_task_requirements() for intelligent analysis.

    This controls which skills are loaded into the sandbox:
    - exploration: spec-driven-dev skill for creating specs/tickets/tasks
    - implementation: git-workflow, code-review, etc. for executing tasks
    - validation: code-review, test-writer for validating implementation

    Args:
        task_type: The task type string (e.g., "implement_feature", "create_spec")

    Returns:
        Execution mode string: "exploration", "implementation", or "validation"
    """
    if task_type in EXPLORATION_TASK_TYPES:
        return "exploration"
    elif task_type in VALIDATION_TASK_TYPES:
        return "validation"
    else:
        # Default to implementation for all other task types
        # This includes: implement_feature, fix_bug, write_tests, refactor, etc.
        return "implementation"


async def analyze_task_requirements(
    task_description: str,
    task_type: Optional[str] = None,
    ticket_title: Optional[str] = None,
    ticket_description: Optional[str] = None,
) -> "TaskRequirements":
    """Analyze a task using LLM to determine its requirements.

    Uses the TaskRequirementsAnalyzer to intelligently determine:
    - Execution mode (exploration, implementation, validation)
    - Output type (analysis, documentation, code, tests, etc.)
    - Git workflow requirements (commit, push, PR)
    - Whether tests are required

    Falls back to hardcoded task type mappings if LLM analysis fails.

    Args:
        task_description: The full task description/prompt
        task_type: Optional task type hint (e.g., "analyze_requirements")
        ticket_title: Optional parent ticket title for context
        ticket_description: Optional parent ticket description

    Returns:
        TaskRequirements with all validation and execution settings
    """
    global task_analyzer

    if task_analyzer is None:
        # Lazy initialization if not already done in init_services
        from omoi_os.services.task_requirements_analyzer import get_task_requirements_analyzer
        task_analyzer = get_task_requirements_analyzer()

    return await task_analyzer.analyze(
        task_description=task_description,
        task_type=task_type,
        ticket_title=ticket_title,
        ticket_description=ticket_description,
    )


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
            events_received=stats["events_received"],
        )
        await asyncio.sleep(30)


def handle_task_event(event_data: dict) -> None:
    """Handle task-related events to wake up orchestrator immediately.

    This is called by the Redis event bus subscriber when:
    - A new task is created (TASK_CREATED)
    - A new ticket is created (TICKET_CREATED)
    - A task completes (SANDBOX_agent.completed) - frees up a slot

    Sets the task_ready_event to interrupt the polling sleep.
    """
    stats["events_received"] += 1
    event_type = event_data.get("event_type", "unknown")
    entity_id = event_data.get("entity_id", "unknown")
    logger.info(
        "task_event_received",
        event_type=event_type,
        entity_id=entity_id,
        events_total=stats["events_received"],
    )
    # Wake up the orchestrator loop immediately
    task_ready_event.set()


def handle_validation_failed(event_data: dict) -> None:
    """Handle TASK_VALIDATION_FAILED event to reset task for re-implementation.

    When a validator agent fails the validation:
    1. Task is already marked as 'needs_revision' (by task_validator service)
    2. This handler resets the task to 'pending' so it can be picked up again
    3. The implementer will receive the validation feedback in the task result

    The implementer gets the revision feedback from task.result which contains:
    - revision_feedback: Human-readable description of what failed
    - revision_recommendations: List of specific fixes needed
    """
    global db

    if not db:
        logger.error("database_not_initialized_for_validation_handling")
        return

    event_type = event_data.get("event_type", "TASK_VALIDATION_FAILED")
    task_id = event_data.get("entity_id")
    payload = event_data.get("payload", {})
    iteration = payload.get("iteration", 0)
    feedback = payload.get("feedback", "No feedback provided")

    logger.info(
        "validation_failed_handling",
        task_id=task_id,
        iteration=iteration,
        feedback_preview=feedback[:100] if feedback else None,
    )

    if not task_id:
        logger.warning("validation_failed_no_task_id", event_data=event_data)
        return

    try:
        from omoi_os.models.task import Task
        from sqlalchemy import select

        with db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()

            if not task:
                logger.warning("validation_failed_task_not_found", task_id=task_id)
                return

            # Only reset if task is in needs_revision status
            if task.status != "needs_revision":
                logger.info(
                    "validation_failed_task_not_needs_revision",
                    task_id=task_id,
                    current_status=task.status,
                )
                return

            # Reset task for re-implementation
            # Keep the revision feedback in task.result so implementer can see it
            task.status = "pending"
            task.sandbox_id = None  # Clear sandbox so it gets a fresh one
            task.assigned_agent_id = None  # Clear agent assignment

            session.commit()

            logger.info(
                "task_reset_for_revision",
                task_id=task_id,
                iteration=iteration,
                new_status="pending",
            )

        # Wake up the orchestrator to pick up the reset task
        task_ready_event.set()

    except Exception as e:
        logger.error(
            "validation_failed_handling_error",
            task_id=task_id,
            error=str(e),
        )


async def orchestrator_loop():
    """Background task that polls queue and assigns tasks to workers.

    Supports two execution modes:
    1. Legacy mode (SANDBOX_EXECUTION=false): Assigns to DB agents, workers poll
    2. Sandbox mode (SANDBOX_EXECUTION=true): Spawns Daytona sandboxes per task

    Uses hybrid event-driven + polling approach:
    - Subscribes to TASK_CREATED events for instant wakeup
    - Falls back to polling every 5 seconds if events are missed
    """
    global db, queue, event_bus, registry_service

    # Check if orchestrator is disabled via environment variable
    if os.getenv("ORCHESTRATOR_ENABLED", "true").lower() in ("false", "0", "no"):
        logger.info("orchestrator_disabled_via_env", env_var="ORCHESTRATOR_ENABLED")
        # Sleep indefinitely to keep process alive but not process tasks
        while not shutdown_event.is_set():
            await asyncio.sleep(60)
        return

    if not db or not queue or not event_bus:
        logger.error("services_not_initialized")
        return

    logger.info("orchestrator_loop_started")

    # Subscribe to task events for instant wakeup (hybrid approach)
    # This allows the orchestrator to respond immediately when:
    # 1. New tasks are created (so we can spawn sandboxes)
    # 2. Tasks complete (so we can spawn more now that a slot is free)
    # 3. Validation fails (so we can reset task for re-implementation)
    try:
        event_bus.subscribe("TASK_CREATED", handle_task_event)
        event_bus.subscribe("TICKET_CREATED", handle_task_event)  # Tickets also trigger tasks
        # Subscribe to completion events to spawn more tasks when slots open
        event_bus.subscribe("SANDBOX_agent.completed", handle_task_event)
        event_bus.subscribe("SANDBOX_agent.failed", handle_task_event)
        event_bus.subscribe("SANDBOX_agent.error", handle_task_event)
        # Subscribe to validation events for the revision workflow
        event_bus.subscribe("TASK_VALIDATION_FAILED", handle_validation_failed)
        event_bus.subscribe("TASK_VALIDATION_PASSED", handle_task_event)  # Just for wakeup/metrics
        logger.info(
            "event_subscriptions_registered",
            events=[
                "TASK_CREATED",
                "TICKET_CREATED",
                "SANDBOX_agent.completed",
                "SANDBOX_agent.failed",
                "SANDBOX_agent.error",
                "TASK_VALIDATION_FAILED",
                "TASK_VALIDATION_PASSED",
            ],
        )
    except Exception as e:
        logger.warning("event_subscription_failed", error=str(e), fallback="polling_only")

    # Check if sandbox execution is enabled
    from omoi_os.config import get_app_settings

    settings = get_app_settings()
    sandbox_execution = settings.daytona.sandbox_execution
    mode = "sandbox" if sandbox_execution else "legacy"

    # Get concurrency limit from environment (default: 5 concurrent tasks per project)
    max_concurrent_per_project = int(os.getenv("MAX_CONCURRENT_TASKS_PER_PROJECT", "5"))
    logger.info(
        "concurrency_config",
        max_concurrent_per_project=max_concurrent_per_project,
    )

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
            from omoi_os.models.task import Task

            available_agent_id = None

            with db.get_session() as session:
                if sandbox_execution:
                    # Sandbox mode: get next pending task with concurrency limits
                    # This ensures we don't spawn more than max_concurrent_per_project
                    # sandboxes for any single project at a time
                    task = queue.get_next_task_with_concurrency_limit(
                        max_concurrent_per_project=max_concurrent_per_project,
                        phase_id=None,
                    )
                else:
                    # Legacy mode: check for available agent first
                    available_agent = (
                        session.query(Agent)
                        .filter(Agent.status == AgentStatus.IDLE.value)
                        .first()
                    )
                    if not available_agent:
                        log.debug("no_idle_agents")
                        await asyncio.sleep(1)
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
                log.info(
                    "task_found",
                    task_status=task.status,
                    task_type=task.task_type,
                    sandbox_id=task.sandbox_id,
                    assigned_agent_id=task.assigned_agent_id,
                    created_at=str(task.created_at) if task.created_at else None,
                )

                # Check if task already has a sandbox (shouldn't spawn another)
                if task.sandbox_id:
                    log.warning(
                        "task_already_has_sandbox",
                        existing_sandbox_id=task.sandbox_id,
                        task_status=task.status,
                        reason="Task found in pending queue but already has sandbox_id - skipping spawn",
                    )
                    # Skip this task - it already has a sandbox
                    await asyncio.sleep(1)
                    continue

                if sandbox_execution and daytona_spawner:
                    # Sandbox mode: spawn a Daytona sandbox for this task
                    log.info(
                        "sandbox_spawn_decision",
                        reason="Task has no sandbox_id and status is pending - will spawn new sandbox",
                        sandbox_execution=sandbox_execution,
                        daytona_spawner_available=daytona_spawner is not None,
                    )
                    try:
                        # Extract user_id, repo info, ticket info, GitHub token, and FULL TASK DATA from DB
                        # This enables per-user credentials, GitHub branch workflow, and task injection
                        import json

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
                                extra_env["TICKET_DESCRIPTION"] = (
                                    ticket.description or ""
                                )
                                # Determine ticket type from phase or status
                                ticket_type = "feature"
                                if ticket.priority == "CRITICAL":
                                    ticket_type = "hotfix"
                                elif "bug" in (ticket.title or "").lower():
                                    ticket_type = "bug"
                                extra_env["TICKET_TYPE"] = ticket_type
                                extra_env["TICKET_PRIORITY"] = (
                                    ticket.priority or "MEDIUM"
                                )

                                # Inject full task context as base64-encoded JSON
                                # This eliminates the need for worker to fetch from API
                                # Base64 encoding avoids shell escaping issues with JSON
                                import base64

                                task_data = {
                                    "task_id": str(task.id),
                                    "task_type": task.task_type,
                                    "task_description": task.description or "",
                                    "task_priority": task.priority,
                                    "phase_id": task.phase_id,
                                    "ticket_id": str(ticket.id),
                                    "ticket_title": ticket.title or "",
                                    "ticket_description": ticket.description or "",
                                    "ticket_priority": ticket.priority,
                                    "ticket_context": ticket.context or {},
                                }

                                # Include revision feedback if task previously failed validation
                                # This allows the implementer to see what went wrong and fix it
                                if task.result:
                                    if task.result.get("revision_feedback"):
                                        task_data["revision_feedback"] = task.result["revision_feedback"]
                                    if task.result.get("revision_recommendations"):
                                        task_data["revision_recommendations"] = task.result["revision_recommendations"]
                                    if task.result.get("validation_iteration"):
                                        task_data["validation_iteration"] = task.result["validation_iteration"]
                                # Base64 encode to avoid shell escaping issues
                                task_json = json.dumps(task_data)
                                extra_env["TASK_DATA_BASE64"] = base64.b64encode(
                                    task_json.encode()
                                ).decode()

                                if ticket.project:
                                    # Inject project ID for spec CLI syncing
                                    extra_env["OMOIOS_PROJECT_ID"] = str(ticket.project.id)
                                    log.info(
                                        "project_found_for_ticket",
                                        ticket_id=str(ticket.id),
                                        project_id=str(ticket.project.id),
                                        project_name=ticket.project.name,
                                        github_owner=ticket.project.github_owner,
                                        github_repo=ticket.project.github_repo,
                                        created_by=str(ticket.project.created_by) if ticket.project.created_by else None,
                                    )
                                    if ticket.project.created_by:
                                        user_id_for_token = ticket.project.created_by
                                        extra_env["USER_ID"] = str(user_id_for_token)
                                    else:
                                        # Fallback: use ticket's user_id if project has no created_by
                                        # This handles older projects created before we tracked created_by
                                        if ticket.user_id:
                                            user_id_for_token = ticket.user_id
                                            extra_env["USER_ID"] = str(user_id_for_token)
                                            log.info(
                                                "using_ticket_user_id_fallback",
                                                project_id=str(ticket.project.id),
                                                ticket_user_id=str(ticket.user_id),
                                                msg="Project has no created_by, falling back to ticket.user_id",
                                            )
                                        else:
                                            log.warning(
                                                "project_missing_created_by",
                                                project_id=str(ticket.project.id),
                                                msg="Project has no created_by and ticket has no user_id - cannot fetch GitHub token",
                                            )
                                    # Combine owner/repo into GITHUB_REPO format
                                    owner = ticket.project.github_owner
                                    repo = ticket.project.github_repo
                                    if owner and repo:
                                        extra_env["GITHUB_REPO"] = f"{owner}/{repo}"
                                        # Also keep separate vars for backwards compat
                                        extra_env["GITHUB_REPO_OWNER"] = owner
                                        extra_env["GITHUB_REPO_NAME"] = repo
                                    else:
                                        log.warning(
                                            "project_missing_github_info",
                                            project_id=str(ticket.project.id),
                                            github_owner=owner,
                                            github_repo=repo,
                                            msg="Project missing github_owner or github_repo",
                                        )
                                else:
                                    # No project - try to get user_id from ticket directly
                                    if ticket.user_id:
                                        user_id_for_token = ticket.user_id
                                        extra_env["USER_ID"] = str(user_id_for_token)
                                        log.info(
                                            "using_ticket_user_id_no_project",
                                            ticket_id=str(ticket.id),
                                            ticket_user_id=str(ticket.user_id),
                                            msg="Ticket has no project, using ticket.user_id for GitHub token",
                                        )
                                    else:
                                        log.warning(
                                            "ticket_has_no_project",
                                            ticket_id=str(ticket.id),
                                            msg="Ticket has no project and no user_id - cannot get GitHub info",
                                        )

                            # Fetch GitHub token from user attributes
                            # Token is stored in user.attributes.github_access_token (via OAuth)
                            if user_id_for_token:
                                user = session.get(User, user_id_for_token)
                                if user:
                                    attrs = user.attributes or {}
                                    log.info(
                                        "checking_user_github_token",
                                        user_id=str(user_id_for_token),
                                        user_email=user.email,
                                        has_attributes=bool(attrs),
                                        attribute_keys=list(attrs.keys()) if attrs else [],
                                    )
                                    github_token = attrs.get("github_access_token")
                                    if github_token:
                                        extra_env["GITHUB_TOKEN"] = github_token
                                        log.info(
                                            "github_token_found",
                                            user_id=str(user_id_for_token),
                                            token_prefix=github_token[:10] + "..." if len(github_token) > 10 else "***",
                                        )
                                    else:
                                        log.warning(
                                            "no_github_token_in_user_attributes",
                                            user_id=str(user_id_for_token),
                                            user_email=user.email,
                                            available_attrs=list(attrs.keys()) if attrs else [],
                                            msg="User has no github_access_token in attributes - repo clone will fail",
                                        )
                                else:
                                    log.error(
                                        "user_not_found_for_token",
                                        user_id=str(user_id_for_token),
                                        msg="Could not find user to get GitHub token",
                                    )
                            else:
                                log.warning(
                                    "no_user_id_for_github_token",
                                    ticket_id=str(ticket.id),
                                    msg="No user_id_for_token set - cannot fetch GitHub token",
                                )

                        log.debug(
                            "env_extracted",
                            user_id=extra_env.get("USER_ID"),
                            github_repo=extra_env.get("GITHUB_REPO"),
                            ticket_type=extra_env.get("TICKET_TYPE"),
                            has_github_token="GITHUB_TOKEN" in extra_env,
                            has_task_data="TASK_DATA_JSON" in extra_env,
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

                        # Determine sandbox runtime: "claude" (Claude Agent SDK) or "openhands"
                        # Default to "claude" for the new Claude Agent SDK worker
                        sandbox_runtime = os.environ.get("SANDBOX_RUNTIME", "claude")

                        log.info(
                            "spawning_sandbox_starting",
                            agent_id=agent_id,
                            agent_type=agent_type,
                            runtime=sandbox_runtime,
                            github_repo=extra_env.get("GITHUB_REPO"),
                            has_github_token="GITHUB_TOKEN" in extra_env,
                            ticket_id=extra_env.get("TICKET_ID"),
                            ticket_type=extra_env.get("TICKET_TYPE"),
                        )

                        # Analyze task requirements using LLM for intelligent determination
                        # This replaces hardcoded task type mappings with dynamic analysis
                        # Falls back to get_execution_mode() if analysis fails
                        task_requirements = await analyze_task_requirements(
                            task_description=task.description or "",
                            task_type=task.task_type,
                            ticket_title=extra_env.get("TICKET_TITLE"),
                            ticket_description=extra_env.get("TICKET_DESCRIPTION"),
                        )
                        execution_mode = task_requirements.execution_mode.value
                        log.info(
                            "task_requirements_analyzed",
                            task_type=task.task_type,
                            execution_mode=execution_mode,
                            output_type=task_requirements.output_type.value,
                            requires_code=task_requirements.requires_code_changes,
                            requires_pr=task_requirements.requires_pull_request,
                            reasoning=task_requirements.reasoning[:100],
                        )

                        # Spawn sandbox with user/repo context and analyzed requirements
                        sandbox_id = await daytona_spawner.spawn_for_task(
                            task_id=task_id,
                            agent_id=agent_id,
                            phase_id=phase_id,
                            agent_type=agent_type,
                            extra_env=extra_env if extra_env else None,
                            runtime=sandbox_runtime,
                            execution_mode=execution_mode,
                            task_requirements=task_requirements,
                        )

                        log.info(
                            "sandbox_spawn_returned",
                            sandbox_id=sandbox_id,
                            agent_id=agent_id,
                        )

                        # Update task with sandbox info
                        queue.assign_task(task.id, agent_id)

                        # Also update task.sandbox_id directly (assign_task doesn't set it)
                        with db.get_session() as session:
                            task_obj = (
                                session.query(Task).filter(Task.id == task.id).first()
                            )
                            if task_obj:
                                # Double-check task doesn't already have a different sandbox
                                if task_obj.sandbox_id and task_obj.sandbox_id != sandbox_id:
                                    log.error(
                                        "task_sandbox_id_conflict",
                                        existing_sandbox_id=task_obj.sandbox_id,
                                        new_sandbox_id=sandbox_id,
                                        task_status=task_obj.status,
                                        reason="Task already has a different sandbox_id - this is a bug!",
                                    )
                                task_obj.sandbox_id = sandbox_id
                                session.commit()
                                log.info(
                                    "task_sandbox_id_updated",
                                    sandbox_id=sandbox_id,
                                    task_status=task_obj.status,
                                )

                        stats["tasks_processed"] += 1
                        log.info(
                            "sandbox_spawned_successfully",
                            sandbox_id=sandbox_id,
                            agent_id=agent_id,
                            task_id=task_id,
                        )

                        # Publish event (include sandbox_id in payload for frontend compatibility)
                        from omoi_os.services.event_bus import SystemEvent

                        event_bus.publish(
                            SystemEvent(
                                event_type="SANDBOX_SPAWNED",
                                entity_type="sandbox",
                                entity_id=sandbox_id,
                                payload={
                                    "sandbox_id": sandbox_id,  # Also in payload for easier access
                                    "task_id": task_id,
                                    "ticket_id": str(task.ticket_id),
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
                # No pending tasks - check for validation tasks
                log.debug("no_pending_tasks")

            # Also check for tasks needing validation (in addition to pending tasks)
            # This spawns validation sandboxes for tasks in pending_validation status
            if sandbox_execution and daytona_spawner:
                validation_task = queue.get_next_validation_task(
                    max_concurrent_per_project=max_concurrent_per_project,
                )
                if validation_task:
                    val_task_id = str(validation_task.id)
                    val_phase_id = validation_task.phase_id or "PHASE_IMPLEMENTATION"

                    val_log = log.bind(
                        task_id=val_task_id,
                        phase=val_phase_id,
                        ticket_id=str(validation_task.ticket_id),
                        task_type="validation",
                    )
                    val_log.info(
                        "validation_task_found",
                        task_status=validation_task.status,
                        original_task_type=validation_task.task_type,
                    )

                    try:
                        # Extract task data for validation sandbox
                        import json
                        import base64

                        extra_env: dict[str, str] = {}
                        user_id_for_token = None

                        with db.get_session() as session:
                            from omoi_os.models.ticket import Ticket
                            from omoi_os.models.user import User

                            ticket = session.get(Ticket, validation_task.ticket_id)
                            if ticket:
                                extra_env["TICKET_ID"] = str(ticket.id)
                                extra_env["TICKET_TITLE"] = ticket.title or ""
                                extra_env["TICKET_DESCRIPTION"] = ticket.description or ""

                                # Include task data with validation context
                                task_data = {
                                    "task_id": str(validation_task.id),
                                    "task_type": validation_task.task_type,
                                    "task_description": validation_task.description or "",
                                    "task_priority": validation_task.priority,
                                    "phase_id": validation_task.phase_id,
                                    "ticket_id": str(ticket.id),
                                    "ticket_title": ticket.title or "",
                                    "ticket_description": ticket.description or "",
                                    "validation_mode": True,  # Signals this is a validation run
                                    "implementation_result": validation_task.result or {},  # Previous implementation result
                                }

                                task_json = json.dumps(task_data)
                                extra_env["TASK_DATA_BASE64"] = base64.b64encode(
                                    task_json.encode()
                                ).decode()

                                if ticket.project:
                                    if ticket.project.created_by:
                                        user_id_for_token = ticket.project.created_by
                                        extra_env["USER_ID"] = str(user_id_for_token)
                                    owner = ticket.project.github_owner
                                    repo = ticket.project.github_repo
                                    if owner and repo:
                                        extra_env["GITHUB_REPO"] = f"{owner}/{repo}"

                            if user_id_for_token:
                                user = session.get(User, user_id_for_token)
                                if user:
                                    attrs = user.attributes or {}
                                    github_token = attrs.get("github_access_token")
                                    if github_token:
                                        extra_env["GITHUB_TOKEN"] = github_token

                        # Register validation agent
                        from omoi_os.models.agent import Agent
                        from uuid import uuid4

                        agent_id = str(uuid4())
                        with db.get_session() as session:
                            agent = Agent(
                                id=agent_id,
                                agent_type="validator",
                                phase_id=val_phase_id,
                                capabilities=["validation", "code-review", "test-runner"],
                                status="RUNNING",
                                tags=["sandbox", "daytona", "validation"],
                                health_status="healthy",
                            )
                            session.add(agent)
                            session.commit()

                        sandbox_runtime = os.environ.get("SANDBOX_RUNTIME", "claude")

                        val_log.info(
                            "spawning_validation_sandbox",
                            agent_id=agent_id,
                            runtime=sandbox_runtime,
                        )

                        # Spawn with validation execution mode
                        sandbox_id = await daytona_spawner.spawn_for_task(
                            task_id=val_task_id,
                            agent_id=agent_id,
                            phase_id=val_phase_id,
                            agent_type="validator",
                            extra_env=extra_env if extra_env else None,
                            runtime=sandbox_runtime,
                            execution_mode="validation",  # Force validation mode
                        )

                        # Update task with sandbox info
                        queue.assign_task(validation_task.id, agent_id)

                        with db.get_session() as session:
                            task_obj = (
                                session.query(Task).filter(Task.id == validation_task.id).first()
                            )
                            if task_obj:
                                task_obj.sandbox_id = sandbox_id
                                task_obj.status = "running"  # Move from validating to running
                                session.commit()

                        stats["tasks_processed"] += 1
                        val_log.info(
                            "validation_sandbox_spawned",
                            sandbox_id=sandbox_id,
                            agent_id=agent_id,
                        )

                        # Publish event
                        from omoi_os.services.event_bus import SystemEvent

                        event_bus.publish(
                            SystemEvent(
                                event_type="VALIDATION_SANDBOX_SPAWNED",
                                entity_type="sandbox",
                                entity_id=sandbox_id,
                                payload={
                                    "sandbox_id": sandbox_id,
                                    "task_id": val_task_id,
                                    "ticket_id": str(validation_task.ticket_id),
                                    "agent_id": agent_id,
                                    "execution_mode": "validation",
                                },
                            )
                        )

                    except Exception as spawn_error:
                        import traceback

                        error_details = traceback.format_exc()
                        stats["tasks_failed"] += 1
                        val_log.error(
                            "validation_sandbox_spawn_failed",
                            error=str(spawn_error),
                            traceback=error_details,
                        )
                        # Reset task status to pending_validation for retry
                        queue.update_task_status(
                            validation_task.id,
                            "pending_validation",
                            error_message=f"Validation sandbox spawn failed: {spawn_error}",
                        )

            # Hybrid wait: event-driven with polling fallback
            # - If TASK_CREATED event fires, wake up immediately
            # - Otherwise, poll every 1 second as fallback
            try:
                await asyncio.wait_for(task_ready_event.wait(), timeout=1.0)
                task_ready_event.clear()  # Reset for next event
                log.debug("woke_up_from_event")
            except asyncio.TimeoutError:
                # Normal polling cycle - no event received
                pass

        except asyncio.CancelledError:
            logger.info("orchestrator_loop_cancelled")
            break
        except Exception as e:
            stats["tasks_failed"] += 1
            logger.error("orchestrator_loop_error", error=str(e))
            await asyncio.sleep(10)


async def stale_task_cleanup_loop():
    """Background task that cleans up tasks stuck in 'assigned' or 'claiming' status.

    Tasks that have been assigned but never transitioned to 'running' are
    likely orphaned (sandbox crashed before sending agent.started event).

    Tasks stuck in 'claiming' status are reset to 'pending' so they can be
    picked up again (orchestrator crashed after claiming but before assigning).

    This loop periodically marks these stale tasks as failed so they can
    be retried or investigated.
    """
    global db, queue

    # Check if stale cleanup is enabled
    stale_cleanup_enabled = os.getenv("STALE_TASK_CLEANUP_ENABLED", "true").lower() in ("true", "1", "yes")
    if not stale_cleanup_enabled:
        logger.info("stale_task_cleanup_disabled_via_env")
        return

    # Wait for services to initialize
    await asyncio.sleep(10)

    if not db or not queue:
        logger.error("services_not_initialized_for_stale_cleanup")
        return

    logger.info("stale_task_cleanup_loop_started")

    # Get thresholds from environment
    # Default: 3 minutes threshold - sandbox should be running by then
    # Default: 15 second check interval - quick detection of stale tasks
    # Default: 60 second threshold for claiming tasks (should be quick)
    stale_threshold_minutes = int(os.getenv("STALE_TASK_THRESHOLD_MINUTES", "3"))
    stale_claiming_threshold_seconds = int(os.getenv("STALE_CLAIMING_THRESHOLD_SECONDS", "60"))
    check_interval = int(os.getenv("STALE_TASK_CHECK_INTERVAL_SECONDS", "15"))

    logger.info(
        "stale_task_cleanup_config",
        stale_threshold_minutes=stale_threshold_minutes,
        stale_claiming_threshold_seconds=stale_claiming_threshold_seconds,
        check_interval_seconds=check_interval,
    )

    while not shutdown_event.is_set():
        try:
            # Clean up stale claiming tasks (reset to pending for retry)
            claiming_cleaned = queue.cleanup_stale_claiming_tasks(
                stale_threshold_seconds=stale_claiming_threshold_seconds,
            )

            if claiming_cleaned:
                logger.info(
                    "stale_claiming_tasks_reset",
                    count=len(claiming_cleaned),
                    task_ids=[t["task_id"][:8] for t in claiming_cleaned],
                )

            # Clean up stale assigned tasks (mark as failed)
            cleaned_tasks = queue.cleanup_stale_assigned_tasks(
                stale_threshold_minutes=stale_threshold_minutes,
                dry_run=False,
            )

            if cleaned_tasks:
                logger.info(
                    "stale_tasks_cleaned",
                    count=len(cleaned_tasks),
                    task_ids=[t["task_id"][:8] for t in cleaned_tasks],
                )

            await asyncio.sleep(check_interval)

        except asyncio.CancelledError:
            logger.info("stale_task_cleanup_loop_cancelled")
            break
        except Exception as e:
            logger.error("stale_task_cleanup_error", error=str(e))
            await asyncio.sleep(check_interval)


async def idle_sandbox_check_loop():
    """Background task that checks for idle sandboxes and terminates them.

    An idle sandbox is one that:
    - Has recent heartbeats (is alive)
    - Has no work events for an extended period (is idle)

    These sandboxes waste Daytona resources and should be terminated.
    """
    global db, event_bus

    # Check if idle detection is enabled
    idle_detection_enabled = os.getenv("IDLE_DETECTION_ENABLED", "true").lower() in ("true", "1", "yes")
    if not idle_detection_enabled:
        logger.info("idle_detection_disabled_via_env")
        return

    # Wait for services to initialize
    await asyncio.sleep(5)

    if not db:
        logger.error("database_not_initialized_for_idle_check")
        return

    # Check if sandbox execution is enabled (only check if we're using sandboxes)
    from omoi_os.config import get_app_settings

    settings = get_app_settings()
    if not settings.daytona.sandbox_execution:
        logger.info("idle_sandbox_check_skipped_legacy_mode")
        return

    logger.info("idle_sandbox_check_loop_started")

    # Get idle threshold from environment (default 30 minutes)
    from datetime import timedelta

    idle_threshold_minutes = int(os.getenv("IDLE_THRESHOLD_MINUTES", "10"))
    idle_threshold = timedelta(minutes=idle_threshold_minutes)
    check_interval = int(os.getenv("IDLE_CHECK_INTERVAL_SECONDS", "30"))

    # Initialize idle sandbox monitor
    from omoi_os.services.daytona_spawner import get_daytona_spawner
    from omoi_os.services.idle_sandbox_monitor import IdleSandboxMonitor

    try:
        daytona_spawner = get_daytona_spawner(db=db, event_bus=event_bus)
        idle_monitor = IdleSandboxMonitor(
            db=db,
            daytona_spawner=daytona_spawner,
            event_bus=event_bus,
            idle_threshold=idle_threshold,
        )
        logger.info(
            "idle_monitor_initialized",
            idle_threshold_minutes=idle_threshold_minutes,
            check_interval_seconds=check_interval,
        )
    except Exception as e:
        logger.error("idle_monitor_init_failed", error=str(e))
        return

    while not shutdown_event.is_set():
        try:
            # Check and terminate idle sandboxes
            terminated = await idle_monitor.check_and_terminate_idle_sandboxes()

            if terminated:
                logger.info(
                    "idle_sandboxes_terminated",
                    count=len(terminated),
                    sandbox_ids=[t["sandbox_id"] for t in terminated],
                )

            await asyncio.sleep(check_interval)

        except asyncio.CancelledError:
            logger.info("idle_sandbox_check_loop_cancelled")
            break
        except Exception as e:
            logger.error("idle_sandbox_check_error", error=str(e))
            await asyncio.sleep(check_interval)


async def init_services():
    """Initialize required services."""
    global db, queue, event_bus, registry_service, task_analyzer

    logger.info("initializing_services")

    from omoi_os.config import get_app_settings
    from omoi_os.services.database import DatabaseService
    from omoi_os.services.task_queue import TaskQueueService
    from omoi_os.services.event_bus import EventBusService
    from omoi_os.services.agent_registry import AgentRegistryService
    from omoi_os.services.task_requirements_analyzer import get_task_requirements_analyzer
    from omoi_os.services.phase_gate import PhaseGateService
    from omoi_os.services.phase_progression_service import get_phase_progression_service
    from omoi_os.services.ticket_workflow import TicketWorkflowOrchestrator

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

    # Task Requirements Analyzer (LLM-based task analysis)
    task_analyzer = get_task_requirements_analyzer()
    logger.info("service_initialized", service="task_requirements_analyzer")

    # Phase Gate Service
    phase_gate = PhaseGateService(db)
    logger.info("service_initialized", service="phase_gate")

    # Ticket Workflow Orchestrator
    workflow_orchestrator = TicketWorkflowOrchestrator(
        db=db,
        task_queue=queue,
        phase_gate=phase_gate,
        event_bus=event_bus,
    )
    logger.info("service_initialized", service="ticket_workflow_orchestrator")

    # Phase Progression Service (Hook 1 + Hook 2)
    # This service:
    # - Hook 1: Auto-advances tickets when all phase tasks complete
    # - Hook 2: Auto-spawns tasks when tickets enter new phases
    phase_progression = get_phase_progression_service(
        db=db,
        task_queue=queue,
        phase_gate=phase_gate,
        event_bus=event_bus,
    )
    phase_progression.set_workflow_orchestrator(workflow_orchestrator)
    phase_progression.subscribe_to_events()
    logger.info(
        "service_initialized",
        service="phase_progression",
        hooks=["Hook1:TaskCompletion->PhaseAdvance", "Hook2:PhaseTransition->TaskSpawn"],
    )

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
        # Run heartbeat, orchestrator loop, idle sandbox check, and stale task cleanup concurrently
        await asyncio.gather(
            heartbeat_task(),
            orchestrator_loop(),
            idle_sandbox_check_loop(),
            stale_task_cleanup_loop(),
        )
    except KeyboardInterrupt:
        await shutdown()
    except Exception as e:
        logger.error("fatal_error", error=str(e))
        await shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
