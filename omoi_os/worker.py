"""Worker service for executing tasks."""

import os
import time
from uuid import UUID

from omoi_os.models.agent import Agent
from omoi_os.models.task import Task
from omoi_os.services.agent_executor import AgentExecutor
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.task_queue import TaskQueueService


def main():
    """Main worker loop."""
    # Initialize services
    database_url = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:15432/app_db")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:16379")
    workspace_dir = os.getenv("WORKSPACE_DIR", "/tmp/omoi_os_workspaces")

    db = DatabaseService(database_url)
    event_bus = EventBusService(redis_url)
    task_queue = TaskQueueService(db)

    # Register agent
    agent_id = register_agent(db, agent_type="worker", phase_id="PHASE_IMPLEMENTATION")

    print(f"Worker started with agent_id: {agent_id}")

    try:
        # Main worker loop
        while True:
            # Get assigned tasks for this agent
            tasks = task_queue.get_assigned_tasks(agent_id)

            if tasks:
                for task in tasks:
                    execute_task(task, agent_id, db, task_queue, event_bus, workspace_dir)
            else:
                # No tasks, sleep briefly
                time.sleep(2)

    except KeyboardInterrupt:
        print("Worker shutting down...")
    finally:
        # Deregister agent
        deregister_agent(db, agent_id)
        event_bus.close()


def register_agent(db: DatabaseService, agent_type: str, phase_id: str | None = None) -> UUID:
    """
    Register this agent in the database.

    Args:
        db: Database service
        agent_type: Type of agent (worker, monitor, etc.)
        phase_id: Phase ID for worker agents

    Returns:
        Agent ID
    """
    with db.get_session() as session:
        agent = Agent(
            agent_type=agent_type,
            phase_id=phase_id,
            status="idle",
            capabilities={"tools": ["bash", "file_editor"]},
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)
        return agent.id


def deregister_agent(db: DatabaseService, agent_id: UUID) -> None:
    """
    Deregister agent from database.

    Args:
        db: Database service
        agent_id: Agent ID to deregister
    """
    with db.get_session() as session:
        agent = session.get(Agent, agent_id)
        if agent:
            agent.status = "terminated"
            session.commit()


def execute_task(
    task: Task,
    agent_id: UUID,
    db: DatabaseService,
    task_queue: TaskQueueService,
    event_bus: EventBusService,
    workspace_dir: str,
) -> None:
    """
    Execute a task using OpenHands agent.

    Args:
        task: Task to execute
        agent_id: Agent ID executing the task
        db: Database service
        task_queue: Task queue service
        event_bus: Event bus service
        workspace_dir: Base directory for workspaces
    """
    import os

    print(f"Executing task {task.id}: {task.description}")

    # Update agent status
    with db.get_session() as session:
        agent = session.get(Agent, agent_id)
        if agent:
            agent.status = "running"

    # Update task status to running
    task_queue.update_task_status(task.id, "running")

    # Create workspace directory for this task
    task_workspace = os.path.join(workspace_dir, str(task.id))
    os.makedirs(task_workspace, exist_ok=True)

    try:
        # Create agent executor
        executor = AgentExecutor(phase_id=task.phase_id, workspace_dir=task_workspace)

        # Execute task
        result = executor.execute_task(task.description or "")

        # Update task status to completed
        task_queue.update_task_status(task.id, "completed", result=result)

        # Publish completion event
        event_bus.publish(
            SystemEvent(
                event_type="TASK_COMPLETED",
                entity_type="task",
                entity_id=str(task.id),
                payload=result,
            )
        )

        print(f"Task {task.id} completed successfully")

    except Exception as e:
        error_message = str(e)
        print(f"Task {task.id} failed: {error_message}")

        # Update task status to failed
        task_queue.update_task_status(task.id, "failed", error_message=error_message)

        # Publish failure event
        event_bus.publish(
            SystemEvent(
                event_type="TASK_FAILED",
                entity_type="task",
                entity_id=str(task.id),
                payload={"error": error_message},
            )
        )

    finally:
        # Update agent status back to idle
        from omoi_os.utils.datetime import utc_now

        with db.get_session() as session:
            agent = session.get(Agent, agent_id)
            if agent:
                agent.status = "idle"
                agent.last_heartbeat = utc_now()


if __name__ == "__main__":
    main()
