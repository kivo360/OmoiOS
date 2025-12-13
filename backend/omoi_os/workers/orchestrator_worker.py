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
import signal
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omoi_os.services.database import DatabaseService
    from omoi_os.services.task_queue import TaskQueueService
    from omoi_os.services.event_bus import EventBusService
    from omoi_os.services.agent_registry import AgentRegistryService

# Services (initialized in init_services)
db: DatabaseService | None = None
queue: TaskQueueService | None = None
event_bus: EventBusService | None = None
registry_service: AgentRegistryService | None = None

# Shutdown flag
shutdown_event = asyncio.Event()


async def orchestrator_loop():
    """Background task that polls queue and assigns tasks to workers.

    Supports two execution modes:
    1. Legacy mode (SANDBOX_EXECUTION=false): Assigns to DB agents, workers poll
    2. Sandbox mode (SANDBOX_EXECUTION=true): Spawns Daytona sandboxes per task
    """
    global db, queue, event_bus, registry_service

    if not db or not queue or not event_bus:
        print("❌ Required services not initialized")
        return

    print("🚀 Orchestrator loop started")

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
            print("✅ Sandbox execution mode ENABLED - will spawn Daytona sandboxes")
        except Exception as e:
            print(f"❌ Failed to initialize Daytona spawner: {e}")
            print("   Falling back to legacy mode")
            sandbox_execution = False
    else:
        print("ℹ️  Legacy execution mode - workers poll for tasks")

    while not shutdown_event.is_set():
        try:
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
                                status="RUNNING",
                                tags=["sandbox", "daytona"],
                                health_status="healthy",
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

                    print(f"📋 Assigned task {task_id} to agent {agent_id}")

            # Poll every 10 seconds
            await asyncio.sleep(10)

        except asyncio.CancelledError:
            print("🛑 Orchestrator loop cancelled")
            break
        except Exception as e:
            print(f"❌ Error in orchestrator loop: {e}")
            await asyncio.sleep(10)


async def init_services():
    """Initialize required services."""
    global db, queue, event_bus, registry_service

    print("🔧 Initializing services...")

    from omoi_os.config import get_app_settings
    from omoi_os.services.database import DatabaseService
    from omoi_os.services.task_queue import TaskQueueService
    from omoi_os.services.event_bus import EventBusService
    from omoi_os.services.agent_registry import AgentRegistryService

    app_settings = get_app_settings()

    # Database - pass connection string, not settings object
    db = DatabaseService(connection_string=app_settings.database.url)
    print("   ✅ Database connected")

    # Task Queue (Redis-backed)
    queue = TaskQueueService(db)
    print("   ✅ Task queue initialized")

    # Event Bus (Redis-backed)
    event_bus = EventBusService(redis_url=app_settings.redis.url)
    print("   ✅ Event bus connected")

    # Agent Registry
    registry_service = AgentRegistryService(db)
    print("   ✅ Agent registry initialized")

    print("✅ All services initialized")


async def shutdown():
    """Graceful shutdown."""
    print("\n🛑 Shutting down orchestrator worker...")
    shutdown_event.set()

    # Close event bus
    if event_bus:
        event_bus.close()
        print("   ✅ Event bus closed")

    print("👋 Orchestrator worker stopped")


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    asyncio.create_task(shutdown())


async def main():
    """Main entry point."""
    print("=" * 60)
    print("🎭 OmoiOS Orchestrator Worker")
    print("=" * 60)

    # Setup signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown()))

    try:
        await init_services()
        await orchestrator_loop()
    except KeyboardInterrupt:
        await shutdown()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        await shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
