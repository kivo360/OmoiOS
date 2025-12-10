"""FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from omoi_os.config import get_app_settings
from omoi_os.mcp.fastmcp_server import mcp_app
from omoi_os.api.routes import (
    agents,
    alerts,
    auth,
    board,
    collaboration,
    commits,
    costs,
    diagnostic,
    events,
    explore,
    github,
    graph,
    guardian,
    memory,
    mcp,
    organizations,
    phases,
    projects,
    quality,
    reasoning,
    results,
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

    if not db or not queue or not event_bus:
        return

    print("Orchestrator loop started")

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
            print("Sandbox execution mode ENABLED - will spawn Daytona sandboxes")
        except Exception as e:
            print(f"Failed to initialize Daytona spawner: {e}")
            print("Falling back to legacy mode")
            sandbox_execution = False
    else:
        print("Legacy execution mode - workers poll for tasks")

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

                        # Spawn sandbox
                        sandbox_id = await daytona_spawner.spawn_for_task(
                            task_id=task_id,
                            agent_id=agent_id,
                            phase_id=phase_id,
                            agent_type=agent_type,
                        )

                        # Update task with sandbox info
                        queue.assign_task(task.id, agent_id)

                        print(
                            f"🚀 Spawned sandbox {sandbox_id} for task {task_id} (agent: {agent_id})"
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
                        print(
                            f"❌ Failed to spawn sandbox for task {task_id}: {spawn_error}"
                        )
                        print(f"   Traceback: {error_details}")
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

                    print(f"Assigned task {task_id} to agent {agent_id}")

            # Poll every 10 seconds
            await asyncio.sleep(10)

        except Exception as e:
            print(f"Error in orchestrator loop: {e}")
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

    print("Heartbeat monitoring loop started")

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
                    print(
                        f"🚨 Agent {agent_id} UNRESPONSIVE ({missed_count} missed heartbeats)"
                    )
                    print(f"🔄 Initiating restart protocol for agent {agent_id}")

                    try:
                        restart_result = restart_orchestrator.initiate_restart(
                            agent_id=agent_id,
                            reason=f"missed_heartbeats ({missed_count} consecutive)",
                            authority=AuthorityLevel.MONITOR,
                        )

                        if restart_result:
                            print(
                                f"✅ Agent {agent_id} restarted. Replacement: {restart_result['replacement_agent_id']}"
                            )
                            print(
                                f"   Reassigned {len(restart_result['reassigned_tasks'])} tasks"
                            )
                        else:
                            print(
                                f"⚠️ Restart for agent {agent_id} blocked (cooldown or max attempts)"
                            )

                    except Exception as e:
                        print(f"❌ Error initiating restart for agent {agent_id}: {e}")

            # Check every 10 seconds (more frequent than diagnostic loop)
            await asyncio.sleep(10)

        except Exception as e:
            print(f"Error in heartbeat monitoring loop: {e}")
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
        print("Diagnostic agent system disabled")
        return

    print("Diagnostic monitoring loop started")

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

                print(f"🚨 WORKFLOW STUCK DETECTED - {time_stuck}s no progress")
                print(f"🔍 Creating diagnostic agent for workflow {workflow_id}")

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

                print(
                    f"✅ Diagnostic run {diagnostic_run.id} created for workflow {workflow_id} "
                    f"(spawned {diagnostic_run.tasks_created_count} recovery task(s))"
                )

            # Check every 60 seconds
            await asyncio.sleep(60)

        except Exception as e:
            print(f"Error in diagnostic monitoring loop: {e}")
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

    print("Approval timeout monitoring loop started")

    while True:
        try:
            # Check for timed out tickets (REQ-THA-004, REQ-THA-009)
            timed_out_ids = approval_service.check_timeouts()

            if timed_out_ids:
                for ticket_id in timed_out_ids:
                    print(
                        f"⏰ TICKET TIMEOUT - Ticket {ticket_id} approval deadline exceeded"
                    )

            # Check every 10 seconds (frequent enough to catch timeouts quickly per REQ-THA-009)
            await asyncio.sleep(10)

        except Exception as e:
            print(f"Error in approval timeout loop: {e}")
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

    print("Blocking detection loop started")

    while True:
        try:
            # Detect blocking tickets
            results = ticket_workflow_orchestrator.detect_blocking()

            # Mark tickets as blocked
            for result in results:
                if result["should_block"]:
                    print(
                        f"🚫 BLOCKING DETECTED - Ticket {result['ticket_id']} "
                        f"blocked ({result['blocker_type']}, "
                        f"{result['time_in_state_minutes']:.1f} min in state)"
                    )

                    ticket_workflow_orchestrator.mark_blocked(
                        result["ticket_id"],
                        result["blocker_type"],
                        initiated_by="blocking-detector",
                    )

            # Check every 5 minutes (frequent enough to catch blocking quickly)
            await asyncio.sleep(300)  # 5 minutes

        except Exception as e:
            print(f"Error in blocking detection loop: {e}")
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

    print("Anomaly monitoring loop started")

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
                    print(
                        f"🚨 AGENT ANOMALY DETECTED - Agent {agent_id} has anomaly_score={anomaly_score:.3f} "
                        f"({consecutive_readings} consecutive readings)"
                    )
                    print(
                        f"🔍 Creating diagnostic agent for anomalous agent {agent_id}"
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

                            print(
                                f"✅ Diagnostic run {diagnostic_run.id} created for agent {agent_id} anomaly "
                                f"(workflow {workflow_id})"
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
            print(f"Error in anomaly monitoring loop: {e}")
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

    # Initialize services
    db = DatabaseService(connection_string=app_settings.database.url)
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
    from omoi_os.services.embedding import EmbeddingService

    phase_loader = PhaseLoader()
    result_submission_service = ResultSubmissionService(db, event_bus, phase_loader)

    # Initialize diagnostic service with dependencies
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
        print("✅ Intelligent Monitoring Loop initialized")
    except ImportError as e:
        print(f"⚠️  MonitoringLoop not available: {e}")
        monitoring_loop = None
    except Exception as e:
        print(f"⚠️  Failed to initialize MonitoringLoop: {e}")
        monitoring_loop = None

    # NOTE: Database tables should be created via alembic migrations, not create_all()
    # Run: alembic upgrade head (handled in Dockerfile CMD)

    # Start background loops
    orchestrator_task = asyncio.create_task(orchestrator_loop())
    heartbeat_task = asyncio.create_task(heartbeat_monitoring_loop())
    diagnostic_task = asyncio.create_task(diagnostic_monitoring_loop())
    anomaly_task = asyncio.create_task(anomaly_monitoring_loop())
    blocking_detection_task = asyncio.create_task(blocking_detection_loop())
    approval_timeout_task = asyncio.create_task(approval_timeout_loop())

    # Start intelligent monitoring loop if available
    if monitoring_loop:
        try:
            await monitoring_loop.start()
            print("✅ Intelligent Monitoring Loop started")
        except Exception as e:
            print(f"⚠️  Failed to start MonitoringLoop: {e}")

    yield

    # Cleanup
    orchestrator_task.cancel()
    heartbeat_task.cancel()
    diagnostic_task.cancel()
    anomaly_task.cancel()
    blocking_detection_task.cancel()
    approval_timeout_task.cancel()

    # Stop intelligent monitoring loop if running
    if monitoring_loop:
        try:
            await monitoring_loop.stop()
            print("✅ Intelligent Monitoring Loop stopped")
        except Exception as e:
            print(f"⚠️  Error stopping MonitoringLoop: {e}")

    try:
        await orchestrator_task
    except asyncio.CancelledError:
        pass
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass
    try:
        await diagnostic_task
    except asyncio.CancelledError:
        pass
    try:
        await anomaly_task
    except asyncio.CancelledError:
        pass
    try:
        await blocking_detection_task
    except asyncio.CancelledError:
        pass
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
    # Import here to avoid circular dependencies
    from omoi_os.mcp.fastmcp_server import mcp_app

    async with lifespan(app):
        async with mcp_app.lifespan(app):
            yield


# Create FastAPI app
app = FastAPI(
    title="OmoiOS API",
    description="Multi-Agent Orchestration System API",
    version="0.1.0",
    lifespan=combined_lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tickets.router, prefix="/api/v1/tickets", tags=["tickets"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(phases.router, prefix="/api/v1", tags=["phases"])
app.include_router(agents.router, prefix="/api/v1", tags=["agents"])
app.include_router(collaboration.router, prefix="/api/v1", tags=["collaboration"])
app.include_router(costs.router, prefix="/api/v1/costs", tags=["costs"])
app.include_router(guardian.router, prefix="/api/v1/guardian", tags=["guardian"])
app.include_router(watchdog.router, prefix="/api/v1/watchdog", tags=["watchdog"])
app.include_router(alerts.router, prefix="/api/v1", tags=["alerts"])
app.include_router(memory.router, prefix="/api/v1", tags=["memory"])
app.include_router(board.router, prefix="/api/v1", tags=["board"])
app.include_router(quality.router, prefix="/api/v1", tags=["quality"])
app.include_router(results.router, prefix="/api/v1", tags=["results"])
app.include_router(diagnostic.router, prefix="/api/v1/diagnostic", tags=["diagnostic"])
app.include_router(validation.router, prefix="/api/validation", tags=["validation"])
app.include_router(mcp.router, tags=["MCP"])
app.include_router(events.router, prefix="/api/v1", tags=["events"])

# Dependency graph routes
app.include_router(graph.router, prefix="/api/v1/graph", tags=["graph"])

# Commits, Projects, and GitHub Integration routes
app.include_router(commits.router, prefix="/api/v1/commits", tags=["commits"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(github.router, prefix="/api/v1/github", tags=["github"])

# Authentication routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(
    organizations.router, prefix="/api/v1/organizations", tags=["organizations"]
)

# Specs routes
app.include_router(specs.router, prefix="/api/v1", tags=["specs"])

# Reasoning chain routes
app.include_router(reasoning.router, prefix="/api/v1", tags=["reasoning"])

# Code exploration routes
app.include_router(explore.router, prefix="/api/v1", tags=["explore"])

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
