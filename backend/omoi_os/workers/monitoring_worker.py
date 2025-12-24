"""
Monitoring Worker - Standalone process for all monitoring loops.

Runs the following monitoring loops:
- Heartbeat monitoring (agent health)
- Diagnostic monitoring (stuck workflows)
- Anomaly monitoring (agent anomalies)
- Blocking detection (stuck tickets)
- Approval timeout (ticket approvals)
- Intelligent Monitoring Loop (Guardian + Conductor)

Run with: python -m omoi_os.workers.monitoring_worker
"""

from __future__ import annotations

import asyncio
import signal
import sys
from typing import TYPE_CHECKING

from omoi_os.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from omoi_os.services.database import DatabaseService
    from omoi_os.services.task_queue import TaskQueueService
    from omoi_os.services.event_bus import EventBusService
    from omoi_os.services.agent_health import AgentHealthService
    from omoi_os.services.heartbeat_protocol import HeartbeatProtocolService
    from omoi_os.services.agent_registry import AgentRegistryService
    from omoi_os.services.agent_status_manager import AgentStatusManager
    from omoi_os.services.approval import ApprovalService
    from omoi_os.services.phase_gate import PhaseGateService

# Services (initialized in init_services)
db: DatabaseService | None = None
queue: TaskQueueService | None = None
event_bus: EventBusService | None = None
health_service: AgentHealthService | None = None
heartbeat_protocol_service: HeartbeatProtocolService | None = None
registry_service: AgentRegistryService | None = None
agent_status_manager: AgentStatusManager | None = None
approval_service: ApprovalService | None = None
phase_gate_service: PhaseGateService | None = None
monitor_service = None
diagnostic_service = None
ticket_workflow_orchestrator = None
monitoring_loop = None

# Shutdown flag
shutdown_event = asyncio.Event()


async def heartbeat_monitoring_loop():
    """Check for missed heartbeats and trigger restarts."""
    global \
        db, \
        heartbeat_protocol_service, \
        registry_service, \
        queue, \
        event_bus, \
        agent_status_manager

    if not db or not heartbeat_protocol_service:
        logger.warning("Heartbeat monitoring: Required services not available")
        return

    logger.info("Heartbeat monitoring loop started")

    from omoi_os.services.restart_orchestrator import RestartOrchestrator
    from omoi_os.models.guardian_action import AuthorityLevel

    restart_orchestrator = RestartOrchestrator(
        db=db,
        agent_registry=registry_service,
        task_queue=queue,
        event_bus=event_bus,
        status_manager=agent_status_manager,
    )

    while not shutdown_event.is_set():
        try:
            agents_with_missed = heartbeat_protocol_service.check_missed_heartbeats()

            for agent_data, missed_count in agents_with_missed:
                agent_id = agent_data["id"]
                if missed_count >= 3:
                    logger.warning(
                        "Agent unresponsive - missed heartbeats",
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
                                replacement_agent_id=restart_result["replacement_agent_id"],
                            )
                        else:
                            logger.warning(
                                "Restart blocked for agent (cooldown or max attempts)",
                                agent_id=agent_id,
                            )

                    except Exception as e:
                        logger.error("Error initiating restart for agent", agent_id=agent_id, error=str(e), exc_info=True)

            await asyncio.sleep(10)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in heartbeat monitoring loop", error=str(e), exc_info=True)
            await asyncio.sleep(10)


async def diagnostic_monitoring_loop():
    """Check for stuck workflows and spawn diagnostic agents."""
    global db, diagnostic_service, event_bus

    if not db or not diagnostic_service or not event_bus:
        logger.warning("Diagnostic monitoring: Required services not available")
        return

    from omoi_os.config import get_app_settings

    app_settings = get_app_settings()
    diagnostic_settings = app_settings.diagnostic

    if not diagnostic_settings.enabled:
        logger.info("Diagnostic agent system disabled")
        return

    logger.info("Diagnostic monitoring loop started")

    while not shutdown_event.is_set():
        try:
            # First, check outcomes of previously spawned diagnostic tasks
            # This updates failure tracking to prevent runaway spawning
            try:
                diagnostic_service.check_diagnostic_task_outcomes()
            except Exception as e:
                logger.warning("Error checking diagnostic task outcomes", error=str(e))

            # Now find truly stuck workflows (with safeguards applied)
            stuck_workflows = diagnostic_service.find_stuck_workflows(
                cooldown_seconds=diagnostic_settings.cooldown_seconds,
                stuck_threshold_seconds=diagnostic_settings.min_stuck_time_seconds,
            )

            for workflow_info in stuck_workflows:
                workflow_id = workflow_info["workflow_id"]
                time_stuck = workflow_info["time_stuck_seconds"]

                logger.warning("Workflow stuck detected", workflow_id=workflow_id, time_stuck_seconds=time_stuck)

                context = diagnostic_service.build_diagnostic_context(
                    workflow_id=workflow_id,
                    max_agents=diagnostic_settings.max_agents_to_analyze,
                    max_analyses=diagnostic_settings.max_conductor_analyses,
                )
                context.update(workflow_info)

                diagnostic_run = await diagnostic_service.spawn_diagnostic_agent(
                    workflow_id=workflow_id,
                    context=context,
                    max_tasks=diagnostic_settings.max_tasks_per_run,
                )

                logger.info(
                    "Diagnostic run created",
                    diagnostic_run_id=str(diagnostic_run.id),
                    workflow_id=workflow_id,
                )

            await asyncio.sleep(60)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in diagnostic monitoring loop", error=str(e), exc_info=True)
            await asyncio.sleep(60)


async def approval_timeout_loop():
    """Check for ticket approval timeouts."""
    global db, approval_service

    if not db or not approval_service:
        logger.warning("Approval timeout: Required services not available")
        return

    logger.info("Approval timeout loop started")

    while not shutdown_event.is_set():
        try:
            timed_out_ids = approval_service.check_timeouts()

            for ticket_id in timed_out_ids:
                logger.warning(
                    "Ticket approval deadline exceeded",
                    ticket_id=ticket_id,
                )

            await asyncio.sleep(10)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in approval timeout loop", error=str(e), exc_info=True)
            await asyncio.sleep(10)


async def blocking_detection_loop():
    """Detect and mark blocked tickets."""
    global db, queue, phase_gate_service, event_bus, ticket_workflow_orchestrator

    if (
        not db
        or not queue
        or not phase_gate_service
        or not ticket_workflow_orchestrator
    ):
        logger.warning("Blocking detection: Required services not available")
        return

    logger.info("Blocking detection loop started")

    while not shutdown_event.is_set():
        try:
            results = ticket_workflow_orchestrator.detect_blocking()

            for result in results:
                if result["should_block"]:
                    logger.warning(
                        "Blocking detected - marking ticket as blocked",
                        ticket_id=result["ticket_id"],
                        blocker_type=result["blocker_type"],
                        time_in_state_minutes=result["time_in_state_minutes"],
                    )

                    ticket_workflow_orchestrator.mark_blocked(
                        result["ticket_id"],
                        result["blocker_type"],
                        initiated_by="blocking-detector",
                    )

            await asyncio.sleep(300)  # 5 minutes

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in blocking detection loop", error=str(e), exc_info=True)
            await asyncio.sleep(300)


async def anomaly_monitoring_loop():
    """Check for agent anomalies and auto-spawn diagnostic agents."""
    global db, monitor_service, diagnostic_service, event_bus

    if not db or not monitor_service or not diagnostic_service:
        logger.warning("Anomaly monitoring: Required services not available")
        return

    logger.info("Anomaly monitoring loop started")

    triggered_agents = set()

    while not shutdown_event.is_set():
        try:
            anomaly_results = monitor_service.compute_agent_anomaly_scores(
                anomaly_threshold=0.8,
                consecutive_threshold=3,
            )

            for result in anomaly_results:
                agent_id = result["agent_id"]
                anomaly_score = result["anomaly_score"]
                consecutive_readings = result["consecutive_readings"]

                if (
                    anomaly_score >= 0.8
                    and consecutive_readings >= 3
                    and agent_id not in triggered_agents
                ):
                    logger.warning("Agent anomaly detected", agent_id=agent_id, anomaly_score=anomaly_score)

                    with db.get_session() as session:
                        from omoi_os.models.task import Task

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
                            context = diagnostic_service.build_diagnostic_context(
                                workflow_id=workflow_id,
                                max_agents=15,
                                max_analyses=5,
                            )
                            context.update(
                                {
                                    "trigger": "agent_anomaly",
                                    "agent_id": agent_id,
                                    "anomaly_score": anomaly_score,
                                }
                            )

                            diagnostic_run = (
                                await diagnostic_service.spawn_diagnostic_agent(
                                    workflow_id=workflow_id,
                                    context=context,
                                    max_tasks=5,
                                )
                            )

                            logger.info(
                                "Diagnostic run created for agent anomaly",
                                diagnostic_run_id=str(diagnostic_run.id),
                                agent_id=agent_id,
                            )
                            triggered_agents.add(agent_id)

                elif anomaly_score < 0.8:
                    triggered_agents.discard(agent_id)

            await asyncio.sleep(60)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in anomaly monitoring loop", error=str(e), exc_info=True)
            await asyncio.sleep(60)


async def init_services():
    """Initialize required services."""
    global db, queue, event_bus, health_service, heartbeat_protocol_service
    global registry_service, agent_status_manager, approval_service
    global phase_gate_service, monitor_service, diagnostic_service
    global ticket_workflow_orchestrator, monitoring_loop

    logger.info("Initializing services...")

    from omoi_os.config import get_app_settings
    from omoi_os.services.database import DatabaseService
    from omoi_os.services.task_queue import TaskQueueService
    from omoi_os.services.event_bus import EventBusService
    from omoi_os.services.agent_health import AgentHealthService
    from omoi_os.services.heartbeat_protocol import HeartbeatProtocolService
    from omoi_os.services.agent_registry import AgentRegistryService
    from omoi_os.services.agent_status_manager import AgentStatusManager
    from omoi_os.services.approval import ApprovalService
    from omoi_os.services.phase_gate import PhaseGateService
    from omoi_os.services.ticket_workflow import TicketWorkflowOrchestrator

    app_settings = get_app_settings()

    # Core services
    db = DatabaseService(connection_string=app_settings.database.url)
    event_bus = EventBusService(redis_url=app_settings.redis.url)
    queue = TaskQueueService(db, event_bus=event_bus)
    logger.info("Core services initialized (DB, Redis, Queue)")

    # Agent services
    agent_status_manager = AgentStatusManager(db, event_bus)
    health_service = AgentHealthService(db, agent_status_manager)
    heartbeat_protocol_service = HeartbeatProtocolService(
        db, event_bus, agent_status_manager
    )
    registry_service = AgentRegistryService(db, event_bus, agent_status_manager)
    logger.info("Agent services initialized")

    # Approval and phase services
    approval_service = ApprovalService(db, event_bus)
    phase_gate_service = PhaseGateService(db)
    logger.info("Approval and phase services initialized")

    # Monitor service
    try:
        from omoi_os.services.monitor import MonitorService

        monitor_service = MonitorService(db, event_bus)
        logger.info("Monitor service initialized")
    except ImportError:
        logger.warning("Monitor service not available")
        monitor_service = None

    # Diagnostic service
    try:
        from omoi_os.services.diagnostic import DiagnosticService
        from omoi_os.services.discovery import DiscoveryService
        from omoi_os.services.memory import MemoryService
        from omoi_os.services.embedding import EmbeddingService
        from omoi_os.services.title_generation_service import (
            TitleGenerationService,
            get_title_generation_service,
        )

        embedding_service = EmbeddingService()
        memory_service = MemoryService(embedding_service, event_bus)

        # Initialize title generation service for LLM-based task titles
        title_service: TitleGenerationService | None = None
        try:
            title_service = get_title_generation_service()
            logger.info("Title generation service initialized")
        except Exception as e:
            logger.warning("Title generation service not available, using fallback", error=str(e))

        discovery_service = DiscoveryService(
            event_bus=event_bus,
            title_service=title_service,
        )
        diagnostic_service = DiagnosticService(
            db=db,
            discovery=discovery_service,
            memory=memory_service,
            monitor=monitor_service,
            event_bus=event_bus,
            embedding_service=embedding_service,  # Enable vector-based task deduplication
        )
        logger.info("Diagnostic service initialized (with vector deduplication)")
    except ImportError as e:
        logger.warning("Diagnostic service not available", error=str(e))
        diagnostic_service = None

    # Ticket workflow orchestrator
    ticket_workflow_orchestrator = TicketWorkflowOrchestrator(
        db=db,
        task_queue=queue,
        phase_gate=phase_gate_service,
        event_bus=event_bus,
    )
    logger.info("Ticket workflow orchestrator initialized")

    # Intelligent Monitoring Loop
    try:
        from omoi_os.services.monitoring_loop import MonitoringLoop, MonitoringConfig

        monitoring_config = MonitoringConfig(
            guardian_interval_seconds=app_settings.monitoring.guardian_interval_seconds,
            conductor_interval_seconds=app_settings.monitoring.conductor_interval_seconds,
            health_check_interval_seconds=app_settings.monitoring.health_check_interval_seconds,
            auto_steering_enabled=app_settings.monitoring.auto_steering_enabled,
            max_concurrent_analyses=app_settings.monitoring.max_concurrent_analyses,
            workspace_root=app_settings.workspace.root,
            llm_analysis_enabled=app_settings.monitoring.llm_analysis_enabled,
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

    logger.info("All services initialized")


async def shutdown():
    """Graceful shutdown."""
    logger.info("Shutting down monitoring worker")
    shutdown_event.set()

    # Stop intelligent monitoring loop
    if monitoring_loop:
        try:
            await monitoring_loop.stop()
            logger.info("Intelligent Monitoring Loop stopped")
        except Exception as e:
            logger.warning("Error stopping MonitoringLoop", error=str(e))

    # Close event bus
    if event_bus:
        event_bus.close()
        logger.info("Event bus closed")

    logger.info("Monitoring worker stopped")


async def main():
    """Main entry point."""
    logger.info("OmoiOS Monitoring Worker starting")

    # Setup signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown()))

    try:
        await init_services()

        logger.info("Starting monitoring loops")

        # Create all monitoring tasks
        tasks = [
            asyncio.create_task(heartbeat_monitoring_loop()),
            asyncio.create_task(diagnostic_monitoring_loop()),
            asyncio.create_task(anomaly_monitoring_loop()),
            asyncio.create_task(blocking_detection_loop()),
            asyncio.create_task(approval_timeout_loop()),
        ]

        # Start intelligent monitoring loop if available
        if monitoring_loop:
            try:
                tasks.append(asyncio.create_task(monitoring_loop.start()))
                logger.info("Intelligent Monitoring Loop started")
            except Exception as e:
                logger.warning("Failed to start MonitoringLoop", error=str(e))

        logger.info("All monitoring loops running")

        # Wait for shutdown
        await shutdown_event.wait()

        # Cancel all tasks
        for task in tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)

    except KeyboardInterrupt:
        await shutdown()
    except Exception as e:
        logger.error("Fatal error in monitoring worker", error=str(e), exc_info=True)
        await shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
