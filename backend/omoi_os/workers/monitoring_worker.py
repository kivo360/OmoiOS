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
        print("⚠️  Heartbeat monitoring: Required services not available")
        return

    print("   ✅ Heartbeat monitoring loop started")

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
                    print(
                        f"🚨 Agent {agent_id} UNRESPONSIVE ({missed_count} missed heartbeats)"
                    )

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
                        else:
                            print(
                                f"⚠️  Restart for agent {agent_id} blocked (cooldown or max attempts)"
                            )

                    except Exception as e:
                        print(f"❌ Error initiating restart for agent {agent_id}: {e}")

            await asyncio.sleep(10)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"❌ Error in heartbeat monitoring loop: {e}")
            await asyncio.sleep(10)


async def diagnostic_monitoring_loop():
    """Check for stuck workflows and spawn diagnostic agents."""
    global db, diagnostic_service, event_bus

    if not db or not diagnostic_service or not event_bus:
        print("⚠️  Diagnostic monitoring: Required services not available")
        return

    from omoi_os.config import get_app_settings

    app_settings = get_app_settings()
    diagnostic_settings = app_settings.diagnostic

    if not diagnostic_settings.enabled:
        print("   ℹ️  Diagnostic agent system disabled")
        return

    print("   ✅ Diagnostic monitoring loop started")

    while not shutdown_event.is_set():
        try:
            stuck_workflows = diagnostic_service.find_stuck_workflows(
                cooldown_seconds=diagnostic_settings.cooldown_seconds,
                stuck_threshold_seconds=diagnostic_settings.min_stuck_time_seconds,
            )

            for workflow_info in stuck_workflows:
                workflow_id = workflow_info["workflow_id"]
                time_stuck = workflow_info["time_stuck_seconds"]

                print(f"🚨 WORKFLOW STUCK DETECTED - {time_stuck}s no progress")

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

                print(
                    f"✅ Diagnostic run {diagnostic_run.id} created for workflow {workflow_id}"
                )

            await asyncio.sleep(60)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"❌ Error in diagnostic monitoring loop: {e}")
            await asyncio.sleep(60)


async def approval_timeout_loop():
    """Check for ticket approval timeouts."""
    global db, approval_service

    if not db or not approval_service:
        print("⚠️  Approval timeout: Required services not available")
        return

    print("   ✅ Approval timeout loop started")

    while not shutdown_event.is_set():
        try:
            timed_out_ids = approval_service.check_timeouts()

            for ticket_id in timed_out_ids:
                print(
                    f"⏰ TICKET TIMEOUT - Ticket {ticket_id} approval deadline exceeded"
                )

            await asyncio.sleep(10)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"❌ Error in approval timeout loop: {e}")
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
        print("⚠️  Blocking detection: Required services not available")
        return

    print("   ✅ Blocking detection loop started")

    while not shutdown_event.is_set():
        try:
            results = ticket_workflow_orchestrator.detect_blocking()

            for result in results:
                if result["should_block"]:
                    print(
                        f"🚫 BLOCKING DETECTED - Ticket {result['ticket_id']} "
                        f"blocked ({result['blocker_type']}, {result['time_in_state_minutes']:.1f} min)"
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
            print(f"❌ Error in blocking detection loop: {e}")
            await asyncio.sleep(300)


async def anomaly_monitoring_loop():
    """Check for agent anomalies and auto-spawn diagnostic agents."""
    global db, monitor_service, diagnostic_service, event_bus

    if not db or not monitor_service or not diagnostic_service:
        print("⚠️  Anomaly monitoring: Required services not available")
        return

    print("   ✅ Anomaly monitoring loop started")

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
                    print(f"🚨 AGENT ANOMALY - {agent_id} score={anomaly_score:.3f}")

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

                            print(
                                f"✅ Diagnostic run {diagnostic_run.id} for agent {agent_id} anomaly"
                            )
                            triggered_agents.add(agent_id)

                elif anomaly_score < 0.8:
                    triggered_agents.discard(agent_id)

            await asyncio.sleep(60)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"❌ Error in anomaly monitoring loop: {e}")
            await asyncio.sleep(60)


async def init_services():
    """Initialize required services."""
    global db, queue, event_bus, health_service, heartbeat_protocol_service
    global registry_service, agent_status_manager, approval_service
    global phase_gate_service, monitor_service, diagnostic_service
    global ticket_workflow_orchestrator, monitoring_loop

    print("🔧 Initializing services...")

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
    print("   ✅ Core services (DB, Redis, Queue)")

    # Agent services
    agent_status_manager = AgentStatusManager(db, event_bus)
    health_service = AgentHealthService(db, agent_status_manager)
    heartbeat_protocol_service = HeartbeatProtocolService(
        db, event_bus, agent_status_manager
    )
    registry_service = AgentRegistryService(db, event_bus, agent_status_manager)
    print("   ✅ Agent services")

    # Approval and phase services
    approval_service = ApprovalService(db, event_bus)
    phase_gate_service = PhaseGateService(db)
    print("   ✅ Approval and phase services")

    # Monitor service
    try:
        from omoi_os.services.monitor import MonitorService

        monitor_service = MonitorService(db, event_bus)
        print("   ✅ Monitor service")
    except ImportError:
        print("   ⚠️  Monitor service not available")
        monitor_service = None

    # Diagnostic service
    try:
        from omoi_os.services.diagnostic import DiagnosticService
        from omoi_os.services.discovery import DiscoveryService
        from omoi_os.services.memory import MemoryService
        from omoi_os.services.embedding import EmbeddingService

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
        print("   ✅ Diagnostic service")
    except ImportError as e:
        print(f"   ⚠️  Diagnostic service not available: {e}")
        diagnostic_service = None

    # Ticket workflow orchestrator
    ticket_workflow_orchestrator = TicketWorkflowOrchestrator(
        db=db,
        task_queue=queue,
        phase_gate=phase_gate_service,
        event_bus=event_bus,
    )
    print("   ✅ Ticket workflow orchestrator")

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
        )

        monitoring_loop = MonitoringLoop(
            db=db,
            event_bus=event_bus,
            config=monitoring_config,
        )
        print("   ✅ Intelligent Monitoring Loop")
    except ImportError as e:
        print(f"   ⚠️  MonitoringLoop not available: {e}")
        monitoring_loop = None
    except Exception as e:
        print(f"   ⚠️  Failed to initialize MonitoringLoop: {e}")
        monitoring_loop = None

    print("✅ All services initialized")


async def shutdown():
    """Graceful shutdown."""
    print("\n🛑 Shutting down monitoring worker...")
    shutdown_event.set()

    # Stop intelligent monitoring loop
    if monitoring_loop:
        try:
            await monitoring_loop.stop()
            print("   ✅ Intelligent Monitoring Loop stopped")
        except Exception as e:
            print(f"   ⚠️  Error stopping MonitoringLoop: {e}")

    # Close event bus
    if event_bus:
        event_bus.close()
        print("   ✅ Event bus closed")

    print("👋 Monitoring worker stopped")


async def main():
    """Main entry point."""
    print("=" * 60)
    print("📊 OmoiOS Monitoring Worker")
    print("=" * 60)

    # Setup signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown()))

    try:
        await init_services()

        print("\n🚀 Starting monitoring loops...")

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
                print("   ✅ Intelligent Monitoring Loop started")
            except Exception as e:
                print(f"   ⚠️  Failed to start MonitoringLoop: {e}")

        print("\n✅ All monitoring loops running")
        print("   Press Ctrl+C to stop\n")

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
        print(f"❌ Fatal error: {e}")
        await shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
