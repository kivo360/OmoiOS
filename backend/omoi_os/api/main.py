"""FastAPI application entry point."""

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError

from omoi_os.config import get_app_settings
from omoi_os.logging import configure_logging, get_logger, bind_context, clear_context
from omoi_os.observability.sentry import init_sentry
from omoi_os.analytics.posthog import init_posthog

# Configure structured logging at module load time
# This ensures logging is configured before any other imports that might log
_env = os.environ.get("OMOIOS_ENV", "development")
configure_logging(env=_env)  # type: ignore[arg-type]

# Initialize Sentry for error tracking and performance monitoring
# Must be done early, before any other operations that might raise exceptions
init_sentry()

# Initialize PostHog for server-side analytics
init_posthog()
from omoi_os.mcp.fastmcp_server import mcp_app
from omoi_os.api.routes import (
    agents,
    alerts,
    analytics_proxy,
    auth,
    billing,
    board,
    branch_workflow,
    collaboration,
    commits,
    costs,
    debug,
    diagnostic,
    events,
    explore,
    github,
    github_repos,
    graph,
    guardian,
    memory,
    mcp,
    oauth,
    onboarding,
    organizations,
    phases,
    projects,
    quality,
    reasoning,
    results,
    sandbox,
    specs,
    tasks,
    tickets,
    validation,
    watchdog,
)
from omoi_os.services.agent_health import AgentHealthService
from omoi_os.services.agent_registry import AgentRegistryService
from omoi_os.services.agent_status_manager import AgentStatusManager
from omoi_os.services.approval import ApprovalService
from omoi_os.services.budget_enforcer import BudgetEnforcerService
from omoi_os.services.collaboration import CollaborationService
from omoi_os.services.cost_tracking import CostTrackingService
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.heartbeat_protocol import HeartbeatProtocolService
from omoi_os.services.phase_gate import PhaseGateService
from omoi_os.services.resource_lock import ResourceLockService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.ticket_workflow import TicketWorkflowOrchestrator


# Global services (initialized in lifespan)
db: DatabaseService | None = None
queue: TaskQueueService | None = None
event_bus: EventBusService | None = None
health_service: AgentHealthService | None = None
heartbeat_protocol_service: HeartbeatProtocolService | None = None
registry_service: AgentRegistryService | None = None
agent_status_manager: AgentStatusManager | None = None
approval_service: ApprovalService | None = None
collaboration_service: CollaborationService | None = None
lock_service: ResourceLockService | None = None
monitor_service = None  # Defined below in lifespan
phase_gate_service: PhaseGateService | None = None
cost_tracking_service: CostTrackingService | None = None
budget_enforcer_service: BudgetEnforcerService | None = None
result_submission_service = None  # Defined below in lifespan
diagnostic_service = None
llm_service = None  # Unified LLM service  # Defined below in lifespan
validation_orchestrator = None  # Defined below in lifespan
ticket_workflow_orchestrator = None  # Defined below in lifespan
monitoring_loop = None  # Intelligent monitoring loop  # Defined below in lifespan


async def orchestrator_loop():
    """Background task that polls queue and assigns tasks to workers.

    Supports two execution modes:
    1. Legacy mode (SANDBOX_EXECUTION=false): Assigns to DB agents, workers poll
    2. Sandbox mode (SANDBOX_EXECUTION=true): Spawns Daytona sandboxes per task
    """
    global db, queue, event_bus, registry_service

    # Yield to event loop immediately so startup can complete
    await asyncio.sleep(0)

    if not db or not queue or not event_bus:
        return

    logger.info("Orchestrator loop started")

    # Check if sandbox execution is enabled
    from omoi_os.config import get_app_settings

    settings = get_app_settings()
    sandbox_execution = settings.daytona.sandbox_execution

    # Initialize Daytona spawner if sandbox mode enabled
    daytona_spawner = None
    if sandbox_execution:
        try:
            from omoi_os.services.daytona_spawner import get_daytona_spawner

            daytona_spawner = get_daytona_spawner(db=db, event_bus=event_bus)
            logger.info("Sandbox execution mode ENABLED - will spawn Daytona sandboxes")
        except Exception as e:
            logger.error("Failed to initialize Daytona spawner", error=str(e))
            logger.warning("Falling back to legacy mode")
            sandbox_execution = False
    else:
        logger.info("Legacy execution mode - workers poll for tasks")

    while True:
        try:
            # Get next pending task (no agent filter in sandbox mode)
            from omoi_os.models.agent import Agent
            from omoi_os.models.agent_status import AgentStatus

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

                if sandbox_execution and daytona_spawner:
                    # Sandbox mode: spawn a Daytona sandbox for this task
                    try:
                        # Determine agent type from phase
                        from omoi_os.agents.templates import get_template_for_phase

                        template = get_template_for_phase(phase_id)
                        agent_type = template.agent_type.value

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
                                status="RUNNING",  # Valid status
                                tags=["sandbox", "daytona"],
                                health_status="healthy",  # Assume healthy
                            )
                            session.add(agent)
                            session.commit()

                        # Determine execution mode from task type
                        # Default to implementation for legacy orchestrator loop
                        execution_mode = "implementation"
                        if hasattr(task, "task_type") and task.task_type:
                            # Use exploration mode for spec-creation tasks
                            if task.task_type in (
                                "explore_codebase", "create_spec", "create_requirements",
                                "create_design", "create_tickets", "create_tasks",
                                "analyze_dependencies", "define_feature"
                            ):
                                execution_mode = "exploration"
                            elif task.task_type in (
                                "validate", "validate_implementation", "review_code", "run_tests"
                            ):
                                execution_mode = "validation"

                        # Extract execution config from task (skill selection from frontend)
                        require_spec_skill = False
                        project_id = None
                        if hasattr(task, "execution_config") and task.execution_config:
                            exec_config = task.execution_config
                            require_spec_skill = exec_config.get("require_spec_skill", False)
                            # Get project_id from ticket's project
                            if hasattr(task, "ticket") and task.ticket:
                                project_id = task.ticket.project_id

                        # Spawn sandbox with appropriate skills for execution mode
                        sandbox_id = await daytona_spawner.spawn_for_task(
                            task_id=task_id,
                            agent_id=agent_id,
                            phase_id=phase_id,
                            agent_type=agent_type,
                            execution_mode=execution_mode,
                            require_spec_skill=require_spec_skill,
                            project_id=project_id,
                        )

                        # Update task with sandbox info
                        queue.assign_task(task.id, agent_id)

                        logger.info(
                            "Spawned sandbox for task",
                            sandbox_id=sandbox_id,
                            task_id=task_id,
                            agent_id=agent_id,
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
                        logger.error(
                            "Failed to spawn sandbox for task",
                            task_id=task_id,
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

                    logger.info("Assigned task to agent", task_id=task_id, agent_id=agent_id)

            # Poll every 10 seconds
            await asyncio.sleep(10)

        except Exception as e:
            logger.error("Error in orchestrator loop", error=str(e), exc_info=True)
            await asyncio.sleep(10)


async def heartbeat_monitoring_loop():
    """
    Check for missed heartbeats and trigger restarts per REQ-FT-AR-002.

    Monitors agents for missed heartbeats every 10 seconds and applies escalation ladder.
    When 3 consecutive heartbeats are missed, triggers restart protocol.
    """
    global db, heartbeat_protocol_service, registry_service, queue, event_bus

    if not db or not heartbeat_protocol_service:
        return

    logger.info("Heartbeat monitoring loop started")

    # Import restart orchestrator
    from omoi_os.services.restart_orchestrator import RestartOrchestrator
    from omoi_os.models.guardian_action import AuthorityLevel

    restart_orchestrator = RestartOrchestrator(
        db=db,
        agent_registry=registry_service,
        task_queue=queue,
        event_bus=event_bus,
        status_manager=agent_status_manager,
    )

    while True:
        try:
            # Check for missed heartbeats (applies escalation ladder)
            agents_with_missed = heartbeat_protocol_service.check_missed_heartbeats()

            for agent_data, missed_count in agents_with_missed:
                agent_id = agent_data["id"]
                if missed_count >= 3:
                    # 3 consecutive missed → UNRESPONSIVE → restart
                    logger.warning(
                        "Agent UNRESPONSIVE - initiating restart",
                        agent_id=agent_id,
                        missed_count=missed_count,
                    )

                    try:
                        restart_result = restart_orchestrator.initiate_restart(
                            agent_id=agent_id,
                            reason=f"missed_heartbeats ({missed_count} consecutive)",
                            authority=AuthorityLevel.MONITOR,
                        )

                        if restart_result:
                            logger.info(
                                "Agent restarted successfully",
                                agent_id=agent_id,
                                replacement_agent_id=restart_result['replacement_agent_id'],
                                reassigned_tasks=len(restart_result['reassigned_tasks']),
                            )
                        else:
                            logger.warning(
                                "Restart blocked (cooldown or max attempts)",
                                agent_id=agent_id,
                            )

                    except Exception as e:
                        logger.error("Error initiating restart", agent_id=agent_id, error=str(e), exc_info=True)

            # Check every 10 seconds (more frequent than diagnostic loop)
            await asyncio.sleep(10)

        except Exception as e:
            logger.error("Error in heartbeat monitoring loop", error=str(e), exc_info=True)
            await asyncio.sleep(10)


async def diagnostic_monitoring_loop():
    """Check for stuck workflows and spawn diagnostic agents."""
    global db, diagnostic_service, event_bus

    if not db or not diagnostic_service or not event_bus:
        return

    # Load diagnostic settings
    from omoi_os.config import get_app_settings

    app_settings = get_app_settings()
    diagnostic_settings = app_settings.diagnostic

    if not diagnostic_settings.enabled:
        logger.info("Diagnostic agent system disabled")
        return

    logger.info("Diagnostic monitoring loop started")

    while True:
        try:
            # Find stuck workflows using configured values
            stuck_workflows = diagnostic_service.find_stuck_workflows(
                cooldown_seconds=diagnostic_settings.cooldown_seconds,
                stuck_threshold_seconds=diagnostic_settings.min_stuck_time_seconds,
            )

            for workflow_info in stuck_workflows:
                workflow_id = workflow_info["workflow_id"]
                time_stuck = workflow_info["time_stuck_seconds"]

                logger.warning(
                    "Workflow stuck detected - creating diagnostic agent",
                    workflow_id=workflow_id,
                    time_stuck_seconds=time_stuck,
                )

                # Build diagnostic context using configured values
                context = diagnostic_service.build_diagnostic_context(
                    workflow_id=workflow_id,
                    max_agents=diagnostic_settings.max_agents_to_analyze,
                    max_analyses=diagnostic_settings.max_conductor_analyses,
                )

                # Update context with trigger info
                context.update(workflow_info)

                # Spawn diagnostic agent with configured max tasks
                diagnostic_run = await diagnostic_service.spawn_diagnostic_agent(
                    workflow_id=workflow_id,
                    context=context,
                    max_tasks=diagnostic_settings.max_tasks_per_run,
                )

                logger.info(
                    "Diagnostic run created",
                    diagnostic_run_id=str(diagnostic_run.id),
                    workflow_id=workflow_id,
                    tasks_created=diagnostic_run.tasks_created_count,
                )

            # Check every 60 seconds
            await asyncio.sleep(60)

        except Exception as e:
            logger.error("Error in diagnostic monitoring loop", error=str(e), exc_info=True)
            await asyncio.sleep(60)


async def approval_timeout_loop():
    """
    Check for ticket approval timeouts and process them per REQ-THA-004, REQ-THA-009.

    Monitors tickets in pending_review state for deadline expiration and processes timeouts.
    Timeout processing P95 < 2s from deadline per REQ-THA-009.
    """
    global db, approval_service

    if not db or not approval_service:
        return

    logger.info("Approval timeout monitoring loop started")

    while True:
        try:
            # Check for timed out tickets (REQ-THA-004, REQ-THA-009)
            timed_out_ids = approval_service.check_timeouts()

            if timed_out_ids:
                for ticket_id in timed_out_ids:
                    logger.warning(
                        "Ticket approval deadline exceeded",
                        ticket_id=ticket_id,
                    )

            # Check every 10 seconds (frequent enough to catch timeouts quickly per REQ-THA-009)
            await asyncio.sleep(10)

        except Exception as e:
            logger.error("Error in approval timeout loop", error=str(e), exc_info=True)
            await asyncio.sleep(10)


async def blocking_detection_loop():
    """
    Detect and mark blocked tickets per REQ-TKT-BL-001.

    Monitors tickets for blocking conditions (no task progress for BLOCKING_THRESHOLD)
    and automatically marks them as blocked.
    """
    global db, queue, phase_gate_service, event_bus, ticket_workflow_orchestrator

    if not db or not queue or not phase_gate_service:
        return

    logger.info("Blocking detection loop started")

    while True:
        try:
            # Detect blocking tickets
            results = ticket_workflow_orchestrator.detect_blocking()

            # Mark tickets as blocked
            for result in results:
                if result["should_block"]:
                    logger.warning(
                        "Blocking detected - marking ticket as blocked",
                        ticket_id=result["ticket_id"],
                        blocker_type=result["blocker_type"],
                        time_in_state_minutes=round(result["time_in_state_minutes"], 1),
                    )

                    ticket_workflow_orchestrator.mark_blocked(
                        result["ticket_id"],
                        result["blocker_type"],
                        initiated_by="blocking-detector",
                    )

            # Check every 5 minutes (frequent enough to catch blocking quickly)
            await asyncio.sleep(300)  # 5 minutes

        except Exception as e:
            logger.error("Error in blocking detection loop", error=str(e), exc_info=True)
            await asyncio.sleep(300)


async def anomaly_monitoring_loop():
    """
    Check for agent anomalies and auto-spawn diagnostic agents per REQ-FT-DIAG-001.

    Monitors agents for composite anomaly scores >= 0.8 for 3 consecutive readings
    and automatically spawns diagnostic agents to investigate.
    """
    global db, monitor_service, diagnostic_service, event_bus

    if not db or not monitor_service or not diagnostic_service:
        return

    logger.info("Anomaly monitoring loop started")

    # Track agents that have already triggered diagnostic runs (to avoid duplicate spawns)
    triggered_agents = set()

    while True:
        try:
            # Compute anomaly scores for all active agents
            anomaly_results = monitor_service.compute_agent_anomaly_scores(
                anomaly_threshold=0.8,  # REQ-FT-AN-001 default
                consecutive_threshold=3,  # REQ-FT-AN-003 default
            )

            for result in anomaly_results:
                agent_id = result["agent_id"]
                anomaly_score = result["anomaly_score"]
                consecutive_readings = result["consecutive_readings"]
                should_quarantine = result["should_quarantine"]

                # Auto-spawn diagnostic agent if anomaly_score >= threshold for 3 consecutive readings
                # per REQ-FT-DIAG-001
                if (
                    anomaly_score >= 0.8
                    and consecutive_readings >= 3
                    and agent_id not in triggered_agents
                ):
                    logger.warning(
                        "Agent anomaly detected - creating diagnostic agent",
                        agent_id=agent_id,
                        anomaly_score=round(anomaly_score, 3),
                        consecutive_readings=consecutive_readings,
                    )

                    # Get workflow ID from agent's current task or recent tasks
                    with db.get_session() as session:
                        from omoi_os.models.task import Task

                        # Find a workflow associated with this agent (via tasks)
                        task = (
                            session.query(Task)
                            .filter(
                                Task.assigned_agent_id == agent_id,
                                Task.status.in_(
                                    ["assigned", "running", "completed", "failed"]
                                ),
                            )
                            .order_by(Task.created_at.desc())
                            .first()
                        )

                        if task:
                            workflow_id = task.ticket_id

                            # Build diagnostic context for agent anomaly
                            context = diagnostic_service.build_diagnostic_context(
                                workflow_id=workflow_id,
                                max_agents=15,
                                max_analyses=5,
                            )

                            # Update context with anomaly info
                            context.update(
                                {
                                    "trigger": "agent_anomaly",
                                    "agent_id": agent_id,
                                    "anomaly_score": anomaly_score,
                                    "consecutive_readings": consecutive_readings,
                                    "should_quarantine": should_quarantine,
                                }
                            )

                            # Spawn diagnostic agent focusing on this agent
                            diagnostic_run = (
                                await diagnostic_service.spawn_diagnostic_agent(
                                    workflow_id=workflow_id,
                                    context=context,
                                    max_tasks=5,  # Use default max tasks
                                )
                            )

                            logger.info(
                                "Diagnostic run created for agent anomaly",
                                diagnostic_run_id=str(diagnostic_run.id),
                                agent_id=agent_id,
                                workflow_id=str(workflow_id),
                            )

                            # Mark agent as triggered to avoid duplicate spawns
                            triggered_agents.add(agent_id)

                            # Reset trigger after cooldown period (60 seconds)
                            # (in production, use a more sophisticated cooldown mechanism)
                            await asyncio.sleep(60)
                            triggered_agents.discard(agent_id)

                # Reset trigger for agents with anomaly_score < threshold
                elif anomaly_score < 0.8:
                    triggered_agents.discard(agent_id)

            # Check every 60 seconds (same frequency as diagnostic loop)
            await asyncio.sleep(60)

        except Exception as e:
            logger.error("Error in anomaly monitoring loop", error=str(e), exc_info=True)
            await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    global \
        db, \
        queue, \
        event_bus, \
        health_service, \
        heartbeat_protocol_service, \
        registry_service, \
        agent_status_manager, \
        approval_service, \
        collaboration_service, \
        lock_service, \
        monitor_service, \
        phase_gate_service, \
        cost_tracking_service, \
        budget_enforcer_service, \
        result_submission_service, \
        diagnostic_service, \
        validation_orchestrator, \
        ticket_workflow_orchestrator, \
        llm_service, \
        monitoring_loop, \
        mcp_app

    app_settings = get_app_settings()

    # Initialize services with configured pool and timeout settings
    db = DatabaseService(
        connection_string=app_settings.database.url,
        pool_size=app_settings.database.pool_size,
        max_overflow=app_settings.database.max_overflow,
        pool_timeout=app_settings.database.pool_timeout,
        pool_recycle=app_settings.database.pool_recycle,
        pool_pre_ping=app_settings.database.pool_pre_ping,
        pool_use_lifo=app_settings.database.pool_use_lifo,
        command_timeout=app_settings.database.command_timeout,
        connect_timeout=app_settings.database.connect_timeout,
    )
    event_bus = EventBusService(redis_url=app_settings.redis.url)
    queue = TaskQueueService(
        db, event_bus=event_bus
    )  # Pass event_bus for real-time updates
    agent_status_manager = AgentStatusManager(db, event_bus)
    approval_service = ApprovalService(db, event_bus)
    health_service = AgentHealthService(db, agent_status_manager)
    heartbeat_protocol_service = HeartbeatProtocolService(
        db, event_bus, agent_status_manager
    )
    registry_service = AgentRegistryService(db, event_bus, agent_status_manager)
    collaboration_service = CollaborationService(db, event_bus)
    lock_service = ResourceLockService(db)
    phase_gate_service = PhaseGateService(db)

    # Import MonitorService here to avoid issues if Phase 4 not complete
    try:
        from omoi_os.services.monitor import MonitorService

        monitor_service = MonitorService(db, event_bus)
    except ImportError:
        monitor_service = None

    # Phase 5 services
    cost_tracking_service = CostTrackingService(db, event_bus)
    budget_enforcer_service = BudgetEnforcerService(db, event_bus)

    # Diagnostic system services
    from omoi_os.services.phase_loader import PhaseLoader
    from omoi_os.services.result_submission import ResultSubmissionService
    from omoi_os.services.diagnostic import DiagnosticService
    from omoi_os.services.discovery import DiscoveryService
    from omoi_os.services.memory import MemoryService
    from omoi_os.services.embedding import EmbeddingService, preload_embedding_model
    from omoi_os.services.billing_service import BillingService

    # Start background preload of embedding model (if configured)
    # This allows the model to load while other services initialize
    preload_embedding_model()

    phase_loader = PhaseLoader()

    # Initialize billing service for workflow completion tracking
    billing_service = BillingService(db, event_bus)

    result_submission_service = ResultSubmissionService(
        db, event_bus, phase_loader, billing_service=billing_service
    )

    # Initialize diagnostic service with dependencies
    # Model will be ready immediately if preload finished, or lazy-loaded on first use
    embedding_service = EmbeddingService()
    memory_service = MemoryService(embedding_service, event_bus)
    discovery_service = DiscoveryService(event_bus)
    diagnostic_service = DiagnosticService(
        db=db,
        discovery=discovery_service,
        memory=memory_service,
        monitor=monitor_service,
        event_bus=event_bus,
    )

    # Initialize FastMCP server with services
    from omoi_os.mcp.fastmcp_server import initialize_mcp_services, mcp_app

    initialize_mcp_services(
        db=db,
        event_bus=event_bus,
        task_queue=queue,
        discovery_service=discovery_service,
        collaboration_service=collaboration_service,
    )

    # Validation system services
    from omoi_os.services.validation_orchestrator import ValidationOrchestrator

    validation_orchestrator = ValidationOrchestrator(
        db=db,
        agent_registry=registry_service,
        memory=memory_service,
        diagnostic=diagnostic_service,
        event_bus=event_bus,
    )

    # Ticket workflow orchestrator
    ticket_workflow_orchestrator = TicketWorkflowOrchestrator(
        db=db,
        task_queue=queue,
        phase_gate=phase_gate_service,
        event_bus=event_bus,
    )

    # Unified LLM service
    from omoi_os.services.llm_service import get_llm_service

    llm_service = get_llm_service()

    # Intelligent Monitoring Loop (Guardian + Conductor)
    try:
        from omoi_os.services.monitoring_loop import MonitoringLoop, MonitoringConfig

        monitoring_config = MonitoringConfig(
            guardian_interval_seconds=app_settings.monitoring.guardian_interval_seconds,
            conductor_interval_seconds=app_settings.monitoring.conductor_interval_seconds,
            health_check_interval_seconds=app_settings.monitoring.health_check_interval_seconds,
            auto_steering_enabled=app_settings.monitoring.auto_steering_enabled,
            max_concurrent_analyses=app_settings.monitoring.max_concurrent_analyses,
            workspace_root=app_settings.workspace.root,
        )

        monitoring_loop = MonitoringLoop(
            db=db,
            event_bus=event_bus,
            config=monitoring_config,
        )
        logger.info("Intelligent Monitoring Loop initialized")
    except ImportError as e:
        logger.warning("MonitoringLoop not available", error=str(e))
        monitoring_loop = None
    except Exception as e:
        logger.warning("Failed to initialize MonitoringLoop", error=str(e))
        monitoring_loop = None

    # NOTE: Database tables should be created via alembic migrations, not create_all()
    # Run: alembic upgrade head (handled in Dockerfile CMD)

    # Check if we're in testing mode or loops are disabled
    # These can be set directly as env vars for convenience
    is_testing = os.environ.get("TESTING", "").lower() == "true"
    monitoring_enabled = os.environ.get("MONITORING_ENABLED", "true").lower() != "false"
    orchestrator_enabled = (
        os.environ.get("ORCHESTRATOR_ENABLED", "true").lower() != "false"
    )

    # Start background loops
    orchestrator_task = None
    heartbeat_task = None
    diagnostic_task = None
    anomaly_task = None
    blocking_detection_task = None
    approval_timeout_task = None

    # Orchestrator can be disabled via ORCHESTRATOR_ENABLED=false
    if not is_testing and orchestrator_enabled:
        orchestrator_task = asyncio.create_task(orchestrator_loop())
        logger.info("Orchestrator loop started")
    elif not orchestrator_enabled:
        logger.warning("Orchestrator DISABLED via ORCHESTRATOR_ENABLED=false")
    else:
        logger.info("TESTING mode: Skipping orchestrator loop")

    # Monitoring loops can be disabled separately via MONITORING_ENABLED=false
    skip_monitoring = is_testing or not monitoring_enabled
    if not monitoring_enabled and not is_testing:
        logger.warning("Monitoring DISABLED via MONITORING_ENABLED=false")

    if not skip_monitoring:
        heartbeat_task = asyncio.create_task(heartbeat_monitoring_loop())
        diagnostic_task = asyncio.create_task(diagnostic_monitoring_loop())
        anomaly_task = asyncio.create_task(anomaly_monitoring_loop())
        blocking_detection_task = asyncio.create_task(blocking_detection_loop())
        approval_timeout_task = asyncio.create_task(approval_timeout_loop())

        # Start intelligent monitoring loop if available (as background task, don't block startup)
        if monitoring_loop:
            try:
                asyncio.create_task(monitoring_loop.start())
                logger.info("Intelligent Monitoring Loop started (background)")
            except Exception as e:
                logger.warning("Failed to start MonitoringLoop", error=str(e))

    yield

    # Cleanup (only if tasks were started)
    if orchestrator_task:
        orchestrator_task.cancel()
    if heartbeat_task:
        heartbeat_task.cancel()
    if diagnostic_task:
        diagnostic_task.cancel()
    if anomaly_task:
        anomaly_task.cancel()
    if blocking_detection_task:
        blocking_detection_task.cancel()
    if approval_timeout_task:
        approval_timeout_task.cancel()

    # Stop intelligent monitoring loop if running (and wasn't skipped)
    if monitoring_loop and not skip_monitoring:
        try:
            await monitoring_loop.stop()
            logger.info("Intelligent Monitoring Loop stopped")
        except Exception as e:
            logger.warning("Error stopping MonitoringLoop", error=str(e))

    # Await task cancellation (only if tasks were started)
    if orchestrator_task:
        try:
            await orchestrator_task
        except asyncio.CancelledError:
            pass
    if heartbeat_task:
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
    if diagnostic_task:
        try:
            await diagnostic_task
        except asyncio.CancelledError:
            pass
    if anomaly_task:
        try:
            await anomaly_task
        except asyncio.CancelledError:
            pass
    if blocking_detection_task:
        try:
            await blocking_detection_task
        except asyncio.CancelledError:
            pass
    if approval_timeout_task:
        try:
            await approval_timeout_task
        except asyncio.CancelledError:
            pass

    # Shutdown MCP server if it has a lifespan
    if "mcp_app" in globals() and mcp_app:
        try:
            async with mcp_app.lifespan(app):
                pass
        except Exception:
            pass

    event_bus.close()


# Combine lifespans for FastAPI and FastMCP
@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    """Combined lifespan for FastAPI and FastMCP."""
    is_testing = os.environ.get("TESTING", "").lower() == "true"
    mcp_enabled = os.environ.get("MCP_ENABLED", "true").lower() != "false"

    async with lifespan(app):
        if is_testing or not mcp_enabled:
            # Skip MCP server in test mode or when disabled
            if not mcp_enabled and not is_testing:
                logger.warning("MCP server DISABLED via MCP_ENABLED=false")
            yield
        else:
            # Import here to avoid circular dependencies
            from omoi_os.mcp.fastmcp_server import mcp_app

            async with mcp_app.lifespan(app):
                yield


# Create FastAPI app
app = FastAPI(
    title="OmoiOS API",
    description="Multi-Agent Orchestration System API",
    version="0.1.0",
    lifespan=combined_lifespan,
)

# Get structured logger
logger = get_logger(__name__)


# Exception handler for RequestValidationError (returns 422, but sometimes shows as 400)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log validation errors for debugging."""
    logger.error(
        f"Validation error on {request.method} {request.url.path}: {exc.errors()}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


# Exception handler for HTTPException with 400 status
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Log HTTP exceptions, especially 400 errors."""
    if exc.status_code == status.HTTP_400_BAD_REQUEST:
        logger.error(
            f"400 Bad Request on {request.method} {request.url.path}: "
            f"detail={exc.detail}, headers={dict(request.headers)}",
            exc_info=True,
        )
    # Return JSONResponse with CORS headers
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=dict(exc.headers) if exc.headers else {},
    )


# Exception handler for all unhandled exceptions (500 errors)
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Log all unhandled exceptions and return 500 with CORS headers."""
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {exc}",
        exc_info=True,
    )
    # Capture to Sentry with request context
    import sentry_sdk
    with sentry_sdk.push_scope() as scope:
        scope.set_context("request", {
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params),
        })
        sentry_sdk.capture_exception(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Logging context middleware - adds request_id to all logs within a request
@app.middleware("http")
async def logging_context_middleware(request: Request, call_next):
    """Add request context to all logs within a request lifecycle."""
    # Generate or use existing request ID
    request_id = request.headers.get("X-Request-ID", str(uuid4())[:8])

    # Bind context for all logs in this request
    bind_context(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )

    try:
        response = await call_next(request)
        # Add request ID to response headers for correlation
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        # Clear context at end of request
        clear_context()

# Include routers
app.include_router(tickets.router, prefix="/api/v1/tickets", tags=["tickets"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(phases.router, prefix="/api/v1", tags=["phases"])
app.include_router(agents.router, prefix="/api/v1", tags=["agents"])
app.include_router(collaboration.router, prefix="/api/v1", tags=["collaboration"])
app.include_router(costs.router, prefix="/api/v1/costs", tags=["costs"])
app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])
app.include_router(guardian.router, prefix="/api/v1/guardian", tags=["guardian"])
app.include_router(watchdog.router, prefix="/api/v1/watchdog", tags=["watchdog"])
app.include_router(alerts.router, prefix="/api/v1", tags=["alerts"])
app.include_router(memory.router, prefix="/api/v1", tags=["memory"])
app.include_router(board.router, prefix="/api/v1", tags=["board"])
app.include_router(quality.router, prefix="/api/v1", tags=["quality"])
app.include_router(results.router, prefix="/api/v1", tags=["results"])
app.include_router(diagnostic.router, prefix="/api/v1/diagnostic", tags=["diagnostic"])
app.include_router(debug.router, prefix="/api/v1/debug", tags=["debug"])
app.include_router(validation.router, prefix="/api/validation", tags=["validation"])
app.include_router(mcp.router, tags=["MCP"])
app.include_router(events.router, prefix="/api/v1", tags=["events"])
app.include_router(sandbox.router, prefix="/api/v1/sandboxes", tags=["sandboxes"])
app.include_router(
    branch_workflow.router, prefix="/api/v1/branch-workflow", tags=["branch-workflow"]
)

# Dependency graph routes
app.include_router(graph.router, prefix="/api/v1/graph", tags=["graph"])

# Commits, Projects, and GitHub Integration routes
app.include_router(commits.router, prefix="/api/v1/commits", tags=["commits"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(github.router, prefix="/api/v1/github", tags=["github"])

# Authentication routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

# OAuth routes
app.include_router(oauth.router, prefix="/api/v1/auth", tags=["OAuth"])

# Onboarding routes
app.include_router(onboarding.router, prefix="/api/v1/onboarding", tags=["onboarding"])

# GitHub Repository routes (authenticated)
app.include_router(github_repos.router, prefix="/api/v1/github", tags=["GitHub Repos"])

app.include_router(
    organizations.router, prefix="/api/v1/organizations", tags=["organizations"]
)

# Specs routes
app.include_router(specs.router, prefix="/api/v1", tags=["specs"])

# Reasoning chain routes
app.include_router(reasoning.router, prefix="/api/v1", tags=["reasoning"])

# Code exploration routes
app.include_router(explore.router, prefix="/api/v1", tags=["explore"])

# Analytics proxy routes (for bypassing ad blockers)
app.include_router(analytics_proxy.router, prefix="/ingest", tags=["analytics"])

# Mount FastMCP server at /mcp
app.mount("/mcp", mcp_app)

# Conditionally include monitor router if Phase 4 is available
try:
    from omoi_os.api.routes import monitor

    app.include_router(monitor.router, prefix="/api/v1", tags=["monitoring"])
except ImportError:
    pass

# Mount static files for web UI
static_dir = Path(__file__).parent.parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def serve_ui():
    """Serve the web UI."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "message": "OmoiOS API - Web UI not found. Visit /docs for API documentation."
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
