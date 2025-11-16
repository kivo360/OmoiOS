"""Worker service for executing tasks."""

import math
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import UUID

from omoi_os.models.agent import Agent
from omoi_os.models.task import Task
from omoi_os.services.agent_executor import AgentExecutor
from omoi_os.services.agent_health import AgentHealthService
from omoi_os.services.agent_registry import AgentRegistryService
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.resource_lock import LockAcquisitionError, ResourceLockService
from omoi_os.services.scheduler import SchedulerService
from omoi_os.services.task_queue import TaskQueueService


class HeartbeatManager:
    """Manages background heartbeat emission for a worker agent."""

    def __init__(self, agent_id: str, health_service: AgentHealthService, interval_seconds: int = 30):
        """
        Initialize HeartbeatManager.

        Args:
            agent_id: ID of the agent to emit heartbeats for
            health_service: AgentHealthService instance
            interval_seconds: Heartbeat interval in seconds (default: 30)
        """
        self.agent_id = agent_id
        self.health_service = health_service
        self.interval_seconds = interval_seconds
        self._running = False
        self._thread = None

    def start(self) -> None:
        """Start the background heartbeat thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()
        print(f"Heartbeat manager started for agent {self.agent_id}")

    def stop(self) -> None:
        """Stop the background heartbeat thread."""
        if not self._running:
            return

        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.interval_seconds + 5)
        print(f"Heartbeat manager stopped for agent {self.agent_id}")

    def _heartbeat_loop(self) -> None:
        """Background loop that emits heartbeats at regular intervals."""
        while self._running:
            try:
                # Emit heartbeat
                success = self.health_service.emit_heartbeat(self.agent_id)
                if not success:
                    print(f"Warning: Failed to emit heartbeat for agent {self.agent_id} (agent not found)")

                # Sleep for the interval
                time.sleep(self.interval_seconds)

            except Exception as e:
                print(f"Error in heartbeat loop for agent {self.agent_id}: {e}")
                # Continue running even if there's an error
                time.sleep(self.interval_seconds)


class TimeoutManager:
    """Manages background timeout monitoring for tasks."""

    def __init__(self, task_queue: TaskQueueService, event_bus: EventBusService, interval_seconds: int = 10):
        """
        Initialize TimeoutManager.

        Args:
            task_queue: TaskQueueService instance
            event_bus: EventBusService instance for publishing timeout events
            interval_seconds: Check interval in seconds (default: 10)
        """
        self.task_queue = task_queue
        self.event_bus = event_bus
        self.interval_seconds = interval_seconds
        self._running = False
        self._thread = None

    def start(self) -> None:
        """Start the background timeout monitoring thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._timeout_monitoring_loop, daemon=True)
        self._thread.start()
        print("Timeout manager started")

    def stop(self) -> None:
        """Stop the background timeout monitoring thread."""
        if not self._running:
            return

        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.interval_seconds + 5)
        print("Timeout manager stopped")

    def _timeout_monitoring_loop(self) -> None:
        """Background loop that checks for timed-out tasks at regular intervals."""
        while self._running:
            try:
                # Get all timed-out tasks
                timed_out_tasks = self.task_queue.get_timed_out_tasks()

                for task in timed_out_tasks:
                    try:
                        # Mark task as timed out
                        success = self.task_queue.mark_task_timeout(task.id)

                        if success:
                            print(f"Task {task.id} timed out after {task.timeout_seconds}s")

                            # Publish timeout event
                            self.event_bus.publish(
                                SystemEvent(
                                    event_type="TASK_TIMED_OUT",
                                    entity_type="task",
                                    entity_id=str(task.id),
                                    payload={
                                        "timeout_seconds": task.timeout_seconds,
                                        "elapsed_time": self.task_queue.get_task_elapsed_time(task.id),
                                        "phase_id": task.phase_id,
                                        "task_type": task.task_type,
                                    },
                                )
                            )
                        else:
                            print(f"Failed to mark task {task.id} as timed out")

                    except Exception as e:
                        print(f"Error handling timeout for task {task.id}: {e}")

                # Sleep for the interval
                time.sleep(self.interval_seconds)

            except Exception as e:
                print(f"Error in timeout monitoring loop: {e}")
                # Continue running even if there's an error
                time.sleep(self.interval_seconds)

    def check_task_cancellation_before_execution(self, task: Task) -> bool:
        """
        Check if a task has been cancelled before starting execution.

        Args:
            task: Task to check

        Returns:
            True if task can proceed, False if task was cancelled
        """
        # Refresh task status from database
        with self.task_queue.db.get_session() as session:
            current_task = session.query(Task).filter(Task.id == task.id).first()
            if not current_task:
                return False

            # Check if task status is no longer executable
            if current_task.status not in ["assigned", "running"]:
                print(f"Task {task.id} status changed to {current_task.status}, cancelling execution")
                return False

        return True

    def handle_task_timeout_during_execution(self, task: Task, executor: AgentExecutor) -> None:
        """
        Handle timeout during task execution by terminating the conversation.

        Args:
            task: Task that timed out
            executor: AgentExecutor instance to terminate
        """
        try:
            print(f"Handling timeout for task {task.id}")

            # Attempt to terminate the OpenHands conversation
            if hasattr(executor, 'terminate_conversation'):
                executor.terminate_conversation()
                print(f"Terminated conversation for timed-out task {task.id}")
            else:
                print(f"Executor for task {task.id} does not support conversation termination")

        except Exception as e:
            print(f"Error handling timeout for task {task.id}: {e}")


def main():
    """Main worker loop with concurrent task execution."""
    # Initialize services
    database_url = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:15432/app_db")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:16379")
    workspace_dir = os.getenv("WORKSPACE_DIR", "/tmp/omoi_os_workspaces")
    max_concurrent_tasks = int(os.getenv("MAX_CONCURRENT_TASKS", "3"))

    db = DatabaseService(database_url)
    event_bus = EventBusService(redis_url)
    task_queue = TaskQueueService(db)
    health_service = AgentHealthService(db)
    registry = AgentRegistryService(db, event_bus)
    lock_service = ResourceLockService(db, event_bus=event_bus)
    scheduler = SchedulerService(db, task_queue, registry, lock_service, event_bus)

    # Register agent
    agent_id = register_agent(db, agent_type="worker", phase_id="PHASE_IMPLEMENTATION")

    # Initialize heartbeat manager
    heartbeat_manager = HeartbeatManager(str(agent_id), health_service, interval_seconds=30)
    heartbeat_manager.start()

    # Initialize timeout manager
    timeout_manager = TimeoutManager(task_queue, event_bus, interval_seconds=10)
    timeout_manager.start()

    print(f"Worker started with agent_id: {agent_id}, max_concurrent_tasks: {max_concurrent_tasks}")

    # Thread pool for concurrent task execution
    executor = ThreadPoolExecutor(max_workers=max_concurrent_tasks)
    running_tasks = {}  # task_id -> future

    try:
        # Main worker loop
        while True:
            # Get assigned tasks for this agent
            tasks = task_queue.get_assigned_tasks(str(agent_id))

            # Also check scheduler for ready tasks that could be assigned to us
            # This allows workers to pull work proactively
            ready_assignments = scheduler.schedule_and_assign(
                phase_id=None,  # Could filter by agent's phase_id
                limit=max_concurrent_tasks - len(running_tasks),
            )

            # Assign ready tasks to this agent if we have capacity
            for assignment in ready_assignments:
                if assignment["assigned"] and assignment["agent_id"] == str(agent_id):
                    if assignment["task_id"] not in running_tasks:
                        # Actually assign the task
                        task_queue.assign_task(assignment["task_id"], str(agent_id))
                        task = assignment["task"]
                        tasks.append(task)
                elif not assignment["assigned"]:
                    # Task is ready but not assigned - try to assign to this agent
                    # Check if we have capacity
                    if len(running_tasks) < max_concurrent_tasks:
                        # Assign to this agent
                        task_queue.assign_task(assignment["task_id"], str(agent_id))
                        task = assignment["task"]
                        tasks.append(task)

            # Start new tasks if we have capacity
            for task in tasks:
                if len(running_tasks) >= max_concurrent_tasks:
                    break

                if task.id in running_tasks:
                    continue  # Already running

                # Submit task for concurrent execution
                future = executor.submit(
                    execute_task_with_retry_and_locks,
                    task,
                    str(agent_id),
                    db,
                    task_queue,
                    event_bus,
                    workspace_dir,
                    timeout_manager,
                    lock_service,
                )
                running_tasks[task.id] = future

            # Check for completed tasks
            completed_tasks = []
            for task_id, future in list(running_tasks.items()):
                if future.done():
                    try:
                        future.result()  # Raise any exceptions
                    except Exception as e:
                        print(f"Task {task_id} execution error: {e}")
                    completed_tasks.append(task_id)

            # Remove completed tasks
            for task_id in completed_tasks:
                del running_tasks[task_id]

            # Sleep if no work
            if not tasks and not running_tasks:
                time.sleep(2)
            else:
                time.sleep(0.5)  # Shorter sleep when there's work

    except KeyboardInterrupt:
        print("Worker shutting down...")
    finally:
        # Wait for running tasks to complete (with timeout)
        print(f"Waiting for {len(running_tasks)} running tasks to complete...")
        for task_id, future in running_tasks.items():
            try:
                future.result(timeout=30)
            except Exception as e:
                print(f"Task {task_id} did not complete gracefully: {e}")

        executor.shutdown(wait=True)

        # Stop managers
        heartbeat_manager.stop()
        timeout_manager.stop()

        # Release all locks held by this agent
        with db.get_session() as session:
            from omoi_os.models.resource_lock import ResourceLock
            locks = session.query(ResourceLock).filter(ResourceLock.agent_id == str(agent_id)).all()
            for lock in locks:
                session.delete(lock)
            session.commit()

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
            capabilities=["bash", "file_editor"],
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


def calculate_backoff_delay(retry_count: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    """
    Calculate exponential backoff delay with jitter.

    Args:
        retry_count: Current retry attempt number (0-based)
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)

    Returns:
        Delay in seconds with exponential backoff and jitter
    """
    # Calculate exponential backoff: base_delay * (2^retry_count)
    exponential_delay = base_delay * (2 ** retry_count)

    # Apply jitter: ±25% random variation
    jitter_factor = 0.75 + (random.random() * 0.5)  # Random between 0.75 and 1.25
    delay_with_jitter = exponential_delay * jitter_factor

    # Cap at maximum delay
    return min(delay_with_jitter, max_delay)


def execute_task_with_retry_and_locks(
    task: Task,
    agent_id: str,
    db: DatabaseService,
    task_queue: TaskQueueService,
    event_bus: EventBusService,
    workspace_dir: str,
    timeout_manager: TimeoutManager | None = None,
    lock_service: ResourceLockService | None = None,
) -> None:
    """
    Execute a task with retry logic, resource locking, and exponential backoff.

    Args:
        task: Task to execute
        agent_id: Agent ID executing the task
        db: Database service
        task_queue: Task queue service
        event_bus: Event bus service
        workspace_dir: Base directory for workspaces
        timeout_manager: Optional TimeoutManager for cancellation checks
        lock_service: Optional ResourceLockService for resource locking
    """
    import os

    # Acquire resource locks if lock service is available
    acquired_locks = []
    if lock_service:
        # Extract resource keys from task metadata if available
        # For now, use task workspace as resource key
        resource_key = f"workspace:{task.id}"
        try:
            lock = lock_service.acquire_lock(
                resource_key=resource_key,
                task_id=task.id,
                agent_id=agent_id,
                lock_type="exclusive",
            )
            acquired_locks.append(lock)
        except LockAcquisitionError as e:
            print(f"Failed to acquire lock for task {task.id}: {e}")
            task_queue.update_task_status(task.id, "failed", error_message=str(e))
            event_bus.publish(
                SystemEvent(
                    event_type="TASK_FAILED",
                    entity_type="task",
                    entity_id=str(task.id),
                    payload={"error": str(e), "reason": "lock_acquisition_failed"},
                )
            )
            return

    try:
        execute_task_with_retry(
            task,
            UUID(agent_id),
            db,
            task_queue,
            event_bus,
            workspace_dir,
            timeout_manager,
        )
    finally:
        # Release all acquired locks
        if lock_service:
            for lock in acquired_locks:
                try:
                    lock_service.release_lock(lock.id, agent_id)
                except Exception as e:
                    print(f"Error releasing lock {lock.id}: {e}")


def execute_task_with_retry(
    task: Task,
    agent_id: UUID,
    db: DatabaseService,
    task_queue: TaskQueueService,
    event_bus: EventBusService,
    workspace_dir: str,
    timeout_manager: TimeoutManager | None = None,
) -> None:
    """
    Execute a task with retry logic and exponential backoff.

    Args:
        task: Task to execute
        agent_id: Agent ID executing the task
        db: Database service
        task_queue: Task queue service
        event_bus: Event bus service
        workspace_dir: Base directory for workspaces
        timeout_manager: Optional TimeoutManager for cancellation checks
    """
    import os

    # Check if this is a retry attempt
    is_retry = task.retry_count > 0
    attempt_count = task.retry_count + 1  # Current attempt (1-based)

    print(f"Executing task {task.id} (attempt {attempt_count}/{task.max_retries + 1}): {task.description}")

    # Update agent status
    with db.get_session() as session:
        agent = session.get(Agent, agent_id)
        if agent:
            agent.status = "running"

    # Update task status to running
    task_queue.update_task_status(task.id, "running")

    # Pre-execution cancellation check
    if timeout_manager:
        if not timeout_manager.check_task_cancellation_before_execution(task):
            print(f"Task {task.id} was cancelled before execution")
            return

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
                payload={
                    "result": result,
                    "retry_count": task.retry_count,
                    "max_retries": task.max_retries,
                },
            )
        )

        if is_retry:
            print(f"Task {task.id} completed successfully after {task.retry_count} retries")
        else:
            print(f"Task {task.id} completed successfully")

    except Exception as e:
        error_message = str(e)
        print(f"Task {task.id} failed (attempt {attempt_count}): {error_message}")

        # Handle timeout during execution if timeout_manager is available
        if timeout_manager and "timeout" in error_message.lower():
            timeout_manager.handle_task_timeout_during_execution(task, executor)

        # Update task status to failed
        task_queue.update_task_status(task.id, "failed", error_message=error_message)

        # Publish failure event
        event_bus.publish(
            SystemEvent(
                event_type="TASK_FAILED",
                entity_type="task",
                entity_id=str(task.id),
                payload={
                    "error": error_message,
                    "retry_count": task.retry_count,
                    "max_retries": task.max_retries,
                    "attempt": attempt_count,
                },
            )
        )

        # Check if task should be retried
        if task_queue.should_retry(task.id):
            # Check if error is retryable
            if task_queue.is_retryable_error(error_message):
                # Increment retry count and schedule retry
                if task_queue.increment_retry(task.id):
                    # Calculate backoff delay
                    delay = calculate_backoff_delay(task.retry_count - 1)  # Use incremented retry_count

                    print(f"Scheduling retry for task {task.id} in {delay:.2f} seconds")

                    # Publish retry event
                    event_bus.publish(
                        SystemEvent(
                            event_type="TASK_RETRY_SCHEDULED",
                            entity_type="task",
                            entity_id=str(task.id),
                            payload={
                                "retry_count": task.retry_count,
                                "max_retries": task.max_retries,
                                "delay_seconds": delay,
                                "error_message": error_message,
                            },
                        )
                    )

                    # Schedule retry in background (non-blocking)
                    def schedule_retry():
                        time.sleep(delay)
                        # The task will be picked up by get_next_task() since it's now "pending"
                        print(f"Retry delay completed for task {task.id}, task is now pending")

                    # Start retry timer in background thread
                    retry_thread = threading.Thread(target=schedule_retry, daemon=True)
                    retry_thread.start()
                else:
                    print(f"Failed to schedule retry for task {task.id} (max retries exceeded)")
            else:
                print(f"Task {task.id} failed with permanent error, not retrying: {error_message}")
                # Publish permanent failure event
                event_bus.publish(
                    SystemEvent(
                        event_type="TASK_PERMANENTLY_FAILED",
                        entity_type="task",
                        entity_id=str(task.id),
                        payload={
                            "error": error_message,
                            "reason": "permanent_error",
                        },
                    )
                )
        else:
            print(f"Task {task.id} will not be retried (max retries: {task.max_retries}, current: {task.retry_count})")
            # Publish max retries exceeded event
            event_bus.publish(
                SystemEvent(
                    event_type="TASK_PERMANENTLY_FAILED",
                    entity_type="task",
                    entity_id=str(task.id),
                    payload={
                        "error": error_message,
                        "reason": "max_retries_exceeded",
                        "retry_count": task.retry_count,
                        "max_retries": task.max_retries,
                    },
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
