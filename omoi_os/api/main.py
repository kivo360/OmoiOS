"""FastAPI application entry point."""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from omoi_os.api.routes import agents, phases, tasks, tickets
from omoi_os.services.agent_health import AgentHealthService
from omoi_os.services.agent_registry import AgentRegistryService
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.task_queue import TaskQueueService


# Global services (initialized in lifespan)
db: DatabaseService | None = None
queue: TaskQueueService | None = None
event_bus: EventBusService | None = None
health_service: AgentHealthService | None = None
registry_service: AgentRegistryService | None = None


async def orchestrator_loop():
    """Background task that polls queue and assigns tasks to workers."""
    global db, queue, event_bus, registry_service

    if not db or not queue or not event_bus:
        return

    print("Orchestrator loop started")

    while True:
        try:
            # Simple assignment: get next pending task and assign to first available worker
            # TODO: Implement proper agent registry lookup
            phase_id = "PHASE_IMPLEMENTATION"  # For MVP, hardcode phase
            task = queue.get_next_task(phase_id)

            if task:
                # For MVP, assign to first available agent
                # TODO: Implement proper agent selection logic
                from omoi_os.models.agent import Agent
                from uuid import UUID

                with db.get_session() as session:
                    available_agent = session.query(Agent).filter(Agent.status == "idle").first()
                    if available_agent:
                        queue.assign_task(task.id, available_agent.id)
                        agent_id = str(available_agent.id)
                    else:
                        # No available agents, skip this task
                        continue

                # Publish assignment event
                from omoi_os.services.event_bus import SystemEvent

                event_bus.publish(
                    SystemEvent(
                        event_type="TASK_ASSIGNED",
                        entity_type="task",
                        entity_id=str(task.id),
                        payload={"agent_id": agent_id},
                    )
                )

                print(f"Assigned task {task.id} to agent {agent_id}")

            # Poll every 10 seconds
            await asyncio.sleep(10)

        except Exception as e:
            print(f"Error in orchestrator loop: {e}")
            await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    global db, queue, event_bus, health_service, registry_service

    # Initialize services
    db = DatabaseService(
        connection_string=os.getenv(
            "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:15432/app_db"
        )
    )
    queue = TaskQueueService(db)
    event_bus = EventBusService(redis_url=os.getenv("REDIS_URL", "redis://localhost:16379"))
    health_service = AgentHealthService(db)
    registry_service = AgentRegistryService(db, event_bus)

    # Create database tables if they don't exist
    db.create_tables()

    # Start orchestrator loop
    orchestrator_task = asyncio.create_task(orchestrator_loop())

    yield

    # Cleanup
    orchestrator_task.cancel()
    try:
        await orchestrator_task
    except asyncio.CancelledError:
        pass
    event_bus.close()


# Create FastAPI app
app = FastAPI(
    title="OmoiOS API",
    description="Multi-Agent Orchestration System API",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(tickets.router, prefix="/api/v1", tags=["tickets"])
app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])
app.include_router(phases.router, prefix="/api/v1", tags=["phases"])
app.include_router(agents.router, prefix="/api/v1", tags=["agents"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
