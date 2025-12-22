"""Worker service for executing tasks."""

import asyncio
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from omoi_os.config import get_app_settings
from omoi_os.logging import get_logger

logger = get_logger(__name__)
from omoi_os.models.agent import Agent
from omoi_os.models.agent_status import AgentStatus
from omoi_os.models.task import Task
from omoi_os.services.agent_executor import AgentExecutor
from omoi_os.services.agent_health import AgentHealthService
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.models.heartbeat_message import HeartbeatMessage


class HeartbeatManager:
    """
    Enhanced heartbeat manager per REQ-ALM-002.

    Features:
    - Adaptive frequency based on agent status (30s IDLE, 15s RUNNING)
    - Sequence number tracking
    - Health metrics collection
    - Checksum validation
    - Bidirectional acknowledgment handling
    """

    # Interval thresholds per REQ-FT-HB-002
    IDLE_INTERVAL = 30  # IDLE agents: 30s
    RUNNING_INTERVAL = 15  # RUNNING agents: 15s
    HIGH_LOAD_INTERVAL = 10  # Under high load: 10s

    def __init__(
        self,
        agent_id: str,
        heartbeat_protocol_service,
        current_task_id: Optional[str] = None,
        get_agent_status: Optional[callable] = None,
        collect_health_metrics: Optional[callable] = None,
    ):
        """
        Initialize HeartbeatManager.

        Args:
            agent_id: ID of the agent to emit heartbeats for
            heartbeat_protocol_service: HeartbeatProtocolService instance
            current_task_id: Optional callable to get current task ID
            get_agent_status: Optional callable to get current agent status
            collect_health_metrics: Optional callable to collect health metrics
        """
        self.agent_id = agent_id
        self.heartbeat_protocol_service = heartbeat_protocol_service
        self.current_task_id = current_task_id
        self.get_agent_status = get_agent_status or (lambda: "idle")
        self.collect_health_metrics = collect_health_metrics or (lambda: {})
        self._sequence_number = 0
        self._running = False
        self._thread = None

    def start(self) -> None:
        """Start the background heartbeat thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()
        logger.info("Heartbeat manager started", agent_id=self.agent_id)

    def stop(self) -> None:
        """Stop the background heartbeat thread."""
        if not self._running:
            return

        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.IDLE_INTERVAL + 5)
        logger.info("Heartbeat manager stopped", agent_id=self.agent_id)

    def _get_interval(self) -> int:
        """
        Get adaptive heartbeat interval per REQ-FT-HB-002.

        Returns:
            Interval in seconds
        """
        status = self.get_agent_status()
        if status == "running":
            return self.RUNNING_INTERVAL
        elif status == "idle":
            return self.IDLE_INTERVAL
        else:
            return self.IDLE_INTERVAL

    def _collect_health_metrics(self) -> dict:
        """
        Collect health metrics for heartbeat per REQ-ALM-002.

        Returns:
            Dictionary of health metrics
        """
        base_metrics = self.collect_health_metrics()
        # Add common metrics if not present
        metrics = {
            "cpu_usage_percent": base_metrics.get("cpu_usage_percent", 0.0),
            "memory_usage_mb": base_metrics.get("memory_usage_mb", 0),
            "active_connections": base_metrics.get("active_connections", 0),
            "pending_operations": base_metrics.get("pending_operations", 0),
            "last_error_timestamp": base_metrics.get("last_error_timestamp"),
            "custom_metrics": base_metrics.get("custom_metrics", {}),
        }
        return metrics

    def _create_heartbeat_message(self) -> "HeartbeatMessage":
        """
        Create heartbeat message with sequence number and checksum per REQ-ALM-002.

        Returns:
            HeartbeatMessage with all required fields
        """
        from omoi_os.models.heartbeat_message import HeartbeatMessage

        # Increment sequence number
        self._sequence_number += 1

        # Get current status and task
        status = self.get_agent_status()
        task_id = None
        if callable(self.current_task_id):
            task_id = self.current_task_id()
        elif self.current_task_id:
            task_id = self.current_task_id

        # Collect health metrics
        health_metrics = self._collect_health_metrics()

        # Get current timestamp once to ensure consistency
        now = utc_now()

        # Create message payload (without checksum)
        payload = {
            "agent_id": self.agent_id,
            "timestamp": now.isoformat(),
            "sequence_number": self._sequence_number,
            "status": status,
            "current_task_id": task_id,
            "health_metrics": health_metrics,
        }

        # Calculate checksum
        checksum = self.heartbeat_protocol_service._calculate_checksum(payload)

        # Create heartbeat message with the same timestamp used for checksum
        return HeartbeatMessage(
            agent_id=self.agent_id,
            timestamp=now,
            sequence_number=self._sequence_number,
            status=status,
            current_task_id=task_id,
            health_metrics=health_metrics,
            checksum=checksum,
        )

    def _heartbeat_loop(self) -> None:
        """Background loop that emits heartbeats at adaptive intervals per REQ-ALM-002."""
        while self._running:
            try:
                # Create heartbeat message with sequence number and checksum
                heartbeat_message = self._create_heartbeat_message()

                # Send heartbeat and get acknowledgment
                ack = self.heartbeat_protocol_service.receive_heartbeat(
                    heartbeat_message
                )

                if not ack.received:
                    logger.warning(
                        "Heartbeat not acknowledged",
                        agent_id=self.agent_id,
                        message=ack.message,
                    )
                elif ack.message:
                    # Log warnings from acknowledgment (e.g., sequence gaps)
                    logger.debug("Heartbeat acknowledged", agent_id=self.agent_id, message=ack.message)

                # Get adaptive interval based on status
                interval = self._get_interval()
                time.sleep(interval)

            except Exception as e:
                logger.error("Error in heartbeat loop", agent_id=self.agent_id, error=str(e), exc_info=True)
                # Continue running even if there's an error
                interval = self._get_interval()
                time.sleep(interval)


class AsyncHeartbeatManager:
    """
    Async heartbeat manager - pure async replacement for HeartbeatManager.

    Per the async_python_patterns.md guide, this replaces threading with asyncio
    for cleaner shutdown and better resource utilization.

    Features:
    - Adaptive frequency based on agent status (30s IDLE, 15s RUNNING)
    - Sequence number tracking
    - Health metrics collection
    - Checksum validation
    - Graceful shutdown with asyncio.Event
    """

    # Interval thresholds per REQ-FT-HB-002
    IDLE_INTERVAL = 30  # IDLE agents: 30s
    RUNNING_INTERVAL = 15  # RUNNING agents: 15s
    HIGH_LOAD_INTERVAL = 10  # Under high load: 10s

    def __init__(
        self,
        agent_id: str,
        heartbeat_protocol_service,
        current_task_id: Optional[str] = None,
        get_agent_status: Optional[callable] = None,
        collect_health_metrics: Optional[callable] = None,
    ):
        """
        Initialize AsyncHeartbeatManager.

        Args:
            agent_id: ID of the agent to emit heartbeats for
            heartbeat_protocol_service: HeartbeatProtocolService instance (async-aware)
            current_task_id: Optional callable to get current task ID
            get_agent_status: Optional async callable to get current agent status
            collect_health_metrics: Optional async callable to collect health metrics
        """
        self.agent_id = agent_id
        self.heartbeat_protocol_service = heartbeat_protocol_service
        self.current_task_id = current_task_id
        self.get_agent_status = get_agent_status or (lambda: "idle")
        self.collect_health_metrics = collect_health_metrics or (lambda: {})
        self._sequence_number = 0
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        """Start the async heartbeat loop."""
        if self._task is not None:
            return

        self._stop_event.clear()
        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.info("Async heartbeat manager started", agent_id=self.agent_id)

    async def stop(self) -> None:
        """Gracefully stop the async heartbeat loop."""
        if self._task is None:
            return

        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("Async heartbeat manager stopped", agent_id=self.agent_id)

    async def _get_interval_async(self) -> int:
        """
        Get adaptive heartbeat interval per REQ-FT-HB-002.

        Returns:
            Interval in seconds
        """
        status = self.get_agent_status()
        if asyncio.iscoroutine(status):
            status = await status
        if status == "running":
            return self.RUNNING_INTERVAL
        elif status == "idle":
            return self.IDLE_INTERVAL
        else:
            return self.IDLE_INTERVAL

    async def _collect_health_metrics_async(self) -> dict:
        """
        Collect health metrics for heartbeat per REQ-ALM-002.

        Returns:
            Dictionary of health metrics
        """
        base_metrics = self.collect_health_metrics()
        if asyncio.iscoroutine(base_metrics):
            base_metrics = await base_metrics

        if not base_metrics:
            base_metrics = {}

        metrics = {
            "cpu_usage_percent": base_metrics.get("cpu_usage_percent", 0.0),
            "memory_usage_mb": base_metrics.get("memory_usage_mb", 0),
            "active_connections": base_metrics.get("active_connections", 0),
            "pending_operations": base_metrics.get("pending_operations", 0),
            "last_error_timestamp": base_metrics.get("last_error_timestamp"),
            "custom_metrics": base_metrics.get("custom_metrics", {}),
        }
        return metrics

    async def _create_heartbeat_message_async(self) -> "HeartbeatMessage":
        """
        Create heartbeat message with sequence number and checksum per REQ-ALM-002.

        Returns:
            HeartbeatMessage with all required fields
        """
        from omoi_os.models.heartbeat_message import HeartbeatMessage

        self._sequence_number += 1

        status = self.get_agent_status()
        if asyncio.iscoroutine(status):
            status = await status
        if not status:
            status = "idle"

        task_id = None
        if callable(self.current_task_id):
            task_id = self.current_task_id()
        elif self.current_task_id:
            task_id = self.current_task_id

        health_metrics = await self._collect_health_metrics_async()
        now = utc_now()

        payload = {
            "agent_id": self.agent_id,
            "timestamp": now.isoformat(),
            "sequence_number": self._sequence_number,
            "status": status,
            "current_task_id": task_id,
            "health_metrics": health_metrics,
        }

        checksum = self.heartbeat_protocol_service._calculate_checksum(payload)

        return HeartbeatMessage(
            agent_id=self.agent_id,
            timestamp=now,
            sequence_number=self._sequence_number,
            status=status,
            current_task_id=task_id,
            health_metrics=health_metrics,
            checksum=checksum,
        )

    async def _heartbeat_loop(self) -> None:
        """Async heartbeat loop with graceful shutdown support."""
        while not self._stop_event.is_set():
            try:
                heartbeat_message = await self._create_heartbeat_message_async()

                # Use async method if available, otherwise fall back to sync
                if hasattr(self.heartbeat_protocol_service, 'receive_heartbeat_async'):
                    ack = await self.heartbeat_protocol_service.receive_heartbeat_async(
                        heartbeat_message
                    )
                else:
                    ack = self.heartbeat_protocol_service.receive_heartbeat(
                        heartbeat_message
                    )

                if not ack.received:
                    logger.warning(
                        "Heartbeat not acknowledged",
                        agent_id=self.agent_id,
                        message=ack.message,
                    )
                elif ack.message:
                    logger.debug(
                        "Heartbeat acknowledged",
                        agent_id=self.agent_id,
                        message=ack.message,
                    )

            except Exception as e:
                logger.error(
                    "Error in async heartbeat loop",
                    agent_id=self.agent_id,
                    error=str(e),
                    exc_info=True,
                )

            # Non-blocking sleep with early exit support
            interval = await self._get_interval_async()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=interval
                )
                break  # Stop event was set
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue loop


class AsyncTimeoutManager:
    """
    Async timeout manager - pure async replacement for TimeoutManager.

    Per the async_python_patterns.md guide, this eliminates threading
    for cleaner shutdown and better integration with async services.
    """

    def __init__(
        self,
        task_queue: TaskQueueService,
        event_bus: EventBusService,
        interval_seconds: int = 10,
    ):
        """
        Initialize AsyncTimeoutManager.

        Args:
            task_queue: TaskQueueService instance
            event_bus: EventBusService instance for publishing timeout events
            interval_seconds: Check interval in seconds (default: 10)
        """
        self.task_queue = task_queue
        self.event_bus = event_bus
        self.interval_seconds = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        """Start the async timeout monitoring loop."""
        if self._task is not None:
            return

        self._stop_event.clear()
        self._task = asyncio.create_task(self._timeout_monitoring_loop())
        logger.info("Async timeout manager started")

    async def stop(self) -> None:
        """Gracefully stop the async timeout monitoring loop."""
        if self._task is None:
            return

        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("Async timeout manager stopped")

    async def _timeout_monitoring_loop(self) -> None:
        """Async loop that checks for timed-out tasks at regular intervals."""
        while not self._stop_event.is_set():
            try:
                # Use async method if available
                if hasattr(self.task_queue, 'get_timed_out_tasks_async'):
                    timed_out_tasks = await self.task_queue.get_timed_out_tasks_async()
                else:
                    timed_out_tasks = self.task_queue.get_timed_out_tasks()

                for task in timed_out_tasks:
                    try:
                        # Use async method if available
                        if hasattr(self.task_queue, 'mark_task_timeout_async'):
                            success = await self.task_queue.mark_task_timeout_async(task.id)
                        else:
                            success = self.task_queue.mark_task_timeout(task.id)

                        if success:
                            logger.warning(
                                "Task timed out",
                                task_id=str(task.id),
                                timeout_seconds=task.timeout_seconds,
                            )

                            # Publish timeout event
                            self.event_bus.publish(
                                SystemEvent(
                                    event_type="TASK_TIMED_OUT",
                                    entity_type="task",
                                    entity_id=str(task.id),
                                    payload={
                                        "timeout_seconds": task.timeout_seconds,
                                        "elapsed_time": self.task_queue.get_task_elapsed_time(
                                            task.id
                                        ),
                                        "phase_id": task.phase_id,
                                        "task_type": task.task_type,
                                    },
                                )
                            )
                        else:
                            logger.error(
                                "Failed to mark task as timed out",
                                task_id=str(task.id),
                            )

                    except Exception as e:
                        logger.error(
                            "Error handling timeout for task",
                            task_id=str(task.id),
                            error=str(e),
                            exc_info=True,
                        )

            except Exception as e:
                logger.error(
                    "Error in async timeout monitoring loop",
                    error=str(e),
                    exc_info=True,
                )

            # Non-blocking sleep with early exit support
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.interval_seconds
                )
                break  # Stop event was set
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue loop

    async def check_task_cancellation_before_execution_async(self, task: Task) -> bool:
        """
        Async check if a task has been cancelled before starting execution.

        Args:
            task: Task to check

        Returns:
            True if task can proceed, False if task was cancelled
        """
        async with self.task_queue.db.get_async_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Task).filter(Task.id == task.id)
            )
            current_task = result.scalar_one_or_none()

            if not current_task:
                return False

            if current_task.status not in ["assigned", "running"]:
                logger.info(
                    "Task status changed, cancelling execution",
                    task_id=str(task.id),
                    new_status=current_task.status,
                )
                return False

        return True


class TimeoutManager:
    """Manages background timeout monitoring for tasks."""

    def __init__(
        self,
        task_queue: TaskQueueService,
        event_bus: EventBusService,
        interval_seconds: int = 10,
    ):
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
        self._thread = threading.Thread(
            target=self._timeout_monitoring_loop, daemon=True
        )
        self._thread.start()
        logger.info("Timeout manager started")

    def stop(self) -> None:
        """Stop the background timeout monitoring thread."""
        if not self._running:
            return

        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.interval_seconds + 5)
        logger.info("Timeout manager stopped")

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
                            logger.warning(
                                "Task timed out",
                                task_id=str(task.id),
                                timeout_seconds=task.timeout_seconds,
                            )

                            # Publish timeout event
                            self.event_bus.publish(
                                SystemEvent(
                                    event_type="TASK_TIMED_OUT",
                                    entity_type="task",
                                    entity_id=str(task.id),
                                    payload={
                                        "timeout_seconds": task.timeout_seconds,
                                        "elapsed_time": self.task_queue.get_task_elapsed_time(
                                            task.id
                                        ),
                                        "phase_id": task.phase_id,
                                        "task_type": task.task_type,
                                    },
                                )
                            )
                        else:
                            logger.error("Failed to mark task as timed out", task_id=str(task.id))

                    except Exception as e:
                        logger.error("Error handling timeout for task", task_id=str(task.id), error=str(e), exc_info=True)

                # Sleep for the interval
                time.sleep(self.interval_seconds)

            except Exception as e:
                logger.error("Error in timeout monitoring loop", error=str(e), exc_info=True)
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
                logger.info(
                    "Task status changed, cancelling execution",
                    task_id=str(task.id),
                    new_status=current_task.status,
                )
                return False

        return True

    def handle_task_timeout_during_execution(
        self, task: Task, executor: AgentExecutor
    ) -> None:
        """
        Handle timeout during task execution by terminating the conversation.

        Args:
            task: Task that timed out
            executor: AgentExecutor instance to terminate
        """
        try:
            logger.info("Handling timeout for task", task_id=str(task.id))

            # Attempt to terminate the OpenHands conversation
            if hasattr(executor, "terminate_conversation"):
                executor.terminate_conversation()
                logger.info("Terminated conversation for timed-out task", task_id=str(task.id))
            else:
                logger.warning(
                    "Executor does not support conversation termination",
                    task_id=str(task.id),
                )

        except Exception as e:
            logger.error("Error handling timeout for task", task_id=str(task.id), error=str(e), exc_info=True)


def main():
    """Main worker loop with concurrent task execution."""
    # Initialize services
    app_settings = get_app_settings()
    database_url = app_settings.database.url
    redis_url = app_settings.redis.url
    workspace_dir = app_settings.workspace.worker_dir
    max_workers = app_settings.worker.concurrency

    db = DatabaseService(database_url)
    event_bus = EventBusService(redis_url)
    task_queue = TaskQueueService(db)
    health_service = AgentHealthService(db)

    # Import heartbeat protocol service for enhanced heartbeat
    from omoi_os.services.heartbeat_protocol import HeartbeatProtocolService

    heartbeat_protocol_service = HeartbeatProtocolService(db, event_bus)

    # Register agent with capacity
    agent_id = register_agent(
        db, agent_type="worker", phase_id="PHASE_IMPLEMENTATION", capacity=max_workers
    )

    # Track current task for heartbeat
    current_task_ref = {"id": None}

    def get_agent_status():
        """Get current agent status based on tasks."""
        with db.get_session() as session:
            agent = session.query(Agent).filter(Agent.id == agent_id).first()
            if agent:
                return agent.status
            return "idle"

    def get_current_task_id():
        """Get current task ID."""
        return current_task_ref["id"]

    def collect_health_metrics():
        """Collect health metrics for heartbeat."""
        # In a real implementation, this would collect actual metrics
        # For now, return basic metrics
        return {
            "cpu_usage_percent": 0.0,
            "memory_usage_mb": 0,
            "active_connections": 0,
            "pending_operations": len(task_queue.get_assigned_tasks(agent_id))
            if task_queue
            else 0,
            "last_error_timestamp": None,
            "custom_metrics": {},
        }

    # Initialize enhanced heartbeat manager
    heartbeat_manager = HeartbeatManager(
        agent_id=str(agent_id),
        heartbeat_protocol_service=heartbeat_protocol_service,
        current_task_id=get_current_task_id,
        get_agent_status=get_agent_status,
        collect_health_metrics=collect_health_metrics,
    )
    heartbeat_manager.start()

    # Initialize timeout manager
    timeout_manager = TimeoutManager(task_queue, event_bus, interval_seconds=10)
    timeout_manager.start()

    logger.info("Worker started", agent_id=str(agent_id), concurrency=max_workers)

    try:
        # Main worker loop with thread pool
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            while True:
                # Get assigned tasks for this agent
                tasks = task_queue.get_assigned_tasks(agent_id)

                if tasks:
                    # Submit tasks to thread pool for concurrent execution
                    futures = {}
                    for task in tasks:
                        # Update current task for heartbeat
                        current_task_ref["id"] = str(task.id)

                        future = executor.submit(
                            execute_task_with_retry,
                            task,
                            agent_id,
                            db,
                            task_queue,
                            event_bus,
                            workspace_dir,
                            timeout_manager,
                        )
                        futures[future] = task

                    # Wait for task completion
                    # Note: No timeout here - task-level timeouts are handled by TimeoutManager
                    for future in as_completed(futures):
                        task = futures[future]
                        try:
                            future.result()  # Get result to propagate exceptions
                            # Clear current task after completion
                            if current_task_ref["id"] == str(task.id):
                                current_task_ref["id"] = None
                        except Exception as e:
                            logger.error(
                                "Error in concurrent task execution",
                                task_id=str(task.id),
                                error=str(e),
                                exc_info=True,
                            )
                            # Clear current task on error too
                            if current_task_ref["id"] == str(task.id):
                                current_task_ref["id"] = None
                else:
                    # No tasks, sleep briefly
                    time.sleep(2)

    except KeyboardInterrupt:
        logger.info("Worker shutting down...")
    finally:
        # Stop managers
        heartbeat_manager.stop()
        timeout_manager.stop()
        # Deregister agent
        deregister_agent(db, agent_id)
        event_bus.close()


def register_agent(
    db: DatabaseService,
    agent_type: str,
    phase_id: str | None = None,
    capacity: int = 1,
) -> UUID:
    """
    Register this agent in the database.

    Args:
        db: Database service
        agent_type: Type of agent (worker, monitor, etc.)
        phase_id: Phase ID for worker agents
        capacity: Number of concurrent tasks this agent can handle

    Returns:
        Agent ID
    """
    with db.get_session() as session:
        # Start in SPAWNING state per REQ-ALM-004, then transition to IDLE
        agent = Agent(
            agent_type=agent_type,
            phase_id=phase_id,
            status=AgentStatus.SPAWNING.value,  # Start in SPAWNING
            capabilities=["bash", "file_editor"],
            capacity=capacity,
            health_status="healthy",
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)
        agent_id = agent.id

        # Transition to IDLE after registration (simplified - should use AgentRegistryService in production)
        agent.status = AgentStatus.IDLE.value
        session.commit()

        return agent_id


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
            agent.status = AgentStatus.TERMINATED.value
            session.commit()


def calculate_backoff_delay(
    retry_count: int, base_delay: float = 1.0, max_delay: float = 60.0
) -> float:
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
    exponential_delay = base_delay * (2**retry_count)

    # Apply jitter: ±25% random variation
    jitter_factor = 0.75 + (random.random() * 0.5)  # Random between 0.75 and 1.25
    delay_with_jitter = exponential_delay * jitter_factor

    # Cap at maximum delay
    return min(delay_with_jitter, max_delay)


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

    # Check if this is a retry attempt
    is_retry = task.retry_count > 0
    attempt_count = task.retry_count + 1  # Current attempt (1-based)

    logger.info(
        "Executing task with retry",
        task_id=str(task.id),
        attempt=attempt_count,
        max_attempts=task.max_retries + 1,
        description=task.description[:100] if task.description else None,
    )

    # Update agent status
    with db.get_session() as session:
        agent = session.get(Agent, agent_id)
        if agent:
            agent.status = AgentStatus.RUNNING.value

    # Update task status to running
    task_queue.update_task_status(task.id, "running")

    # Pre-execution cancellation check
    if timeout_manager:
        if not timeout_manager.check_task_cancellation_before_execution(task):
            logger.info("Task was cancelled before execution", task_id=str(task.id))
            return

    # Create workspace directory for this task
    task_workspace = os.path.join(workspace_dir, str(task.id))
    os.makedirs(task_workspace, exist_ok=True)

    try:
        # Create agent executor with database service for phase context loading
        executor = AgentExecutor(
            phase_id=task.phase_id,
            workspace_dir=task_workspace,
            db=db,
        )

        # Prepare conversation and store metadata BEFORE execution starts
        # This enables Guardian to send interventions during execution
        conversation_metadata = executor.prepare_conversation(task_id=str(task.id))
        conversation_id = conversation_metadata["conversation_id"]
        persistence_dir = conversation_metadata["persistence_dir"]

        # Store conversation info in database immediately (before running)
        # This allows Guardian to send interventions while agent is executing
        task_queue.update_task_status(
            task.id,
            "running",
            conversation_id=conversation_id,
            persistence_dir=persistence_dir,
        )

        # Execute task with pre-prepared conversation
        result = executor.execute_task(
            task.description or "",
            task_id=str(task.id),
            conversation_metadata=conversation_metadata,
        )

        # Sanitize result to ensure JSON serializability (UUIDs, enums, etc.)
        from omoi_os.utils.datetime import sanitize_for_json

        sanitized_result = sanitize_for_json(result)

        # Update task status to completed with final result
        task_queue.update_task_status(
            task.id,
            "completed",
            result=sanitized_result,
            conversation_id=conversation_id,
            persistence_dir=persistence_dir,
        )

        # Publish completion event
        event_bus.publish(
            SystemEvent(
                event_type="TASK_COMPLETED",
                entity_type="task",
                entity_id=str(task.id),
                payload={
                    "result": sanitized_result,
                    "retry_count": task.retry_count,
                    "max_retries": task.max_retries,
                },
            )
        )

        if is_retry:
            logger.info(
                "Task completed successfully after retries",
                task_id=str(task.id),
                retry_count=task.retry_count,
            )
        else:
            logger.info("Task completed successfully", task_id=str(task.id))

    except Exception as e:
        error_message = str(e)
        logger.error(
            "Task execution failed",
            task_id=str(task.id),
            attempt=attempt_count,
            error=error_message,
            exc_info=True,
        )

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
                    delay = calculate_backoff_delay(
                        task.retry_count - 1
                    )  # Use incremented retry_count

                    logger.info(
                        "Scheduling retry for task",
                        task_id=str(task.id),
                        delay_seconds=round(delay, 2),
                    )

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
                        logger.info("Retry delay completed, task is now pending", task_id=str(task.id))

                    # Start retry timer in background thread
                    retry_thread = threading.Thread(target=schedule_retry, daemon=True)
                    retry_thread.start()
                else:
                    logger.warning(
                        "Failed to schedule retry - max retries exceeded",
                        task_id=str(task.id),
                    )
            else:
                logger.warning(
                    "Task failed with permanent error, not retrying",
                    task_id=str(task.id),
                    error=error_message,
                )
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
            logger.warning(
                "Task will not be retried",
                task_id=str(task.id),
                max_retries=task.max_retries,
                retry_count=task.retry_count,
            )
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
                agent.status = AgentStatus.IDLE.value
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

    logger.info(
        "Executing task",
        task_id=str(task.id),
        description=task.description[:100] if task.description else None,
    )

    # Update agent status
    with db.get_session() as session:
        agent = session.get(Agent, agent_id)
        if agent:
            agent.status = AgentStatus.RUNNING.value

    # Create workspace directory for this task
    task_workspace = os.path.join(workspace_dir, str(task.id))
    os.makedirs(task_workspace, exist_ok=True)

    try:
        # Create agent executor with database service for phase context loading
        executor = AgentExecutor(
            phase_id=task.phase_id,
            workspace_dir=task_workspace,
            db=db,
        )

        # Prepare conversation and store metadata BEFORE execution starts
        # This enables Guardian to send interventions during execution
        conversation_metadata = executor.prepare_conversation(task_id=str(task.id))
        conversation_id = conversation_metadata["conversation_id"]
        persistence_dir = conversation_metadata["persistence_dir"]

        # Store conversation info in database immediately (before running)
        # This allows Guardian to send interventions while agent is executing
        task_queue.update_task_status(
            task.id,
            "running",
            conversation_id=conversation_id,
            persistence_dir=persistence_dir,
        )

        # Execute task with pre-prepared conversation
        result = executor.execute_task(
            task.description or "",
            task_id=str(task.id),
            conversation_metadata=conversation_metadata,
        )

        # Sanitize result to ensure JSON serializability (UUIDs, enums, etc.)
        from omoi_os.utils.datetime import sanitize_for_json

        sanitized_result = sanitize_for_json(result)

        # Update task status to completed with final result
        task_queue.update_task_status(
            task.id,
            "completed",
            result=sanitized_result,
            conversation_id=conversation_id,
            persistence_dir=persistence_dir,
        )

        # Publish completion event
        event_bus.publish(
            SystemEvent(
                event_type="TASK_COMPLETED",
                entity_type="task",
                entity_id=str(task.id),
                payload=sanitized_result,
            )
        )

        logger.info("Task completed successfully", task_id=str(task.id))

    except Exception as e:
        error_message = str(e)
        logger.error("Task failed", task_id=str(task.id), error=error_message, exc_info=True)

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
                agent.status = AgentStatus.IDLE.value
                agent.last_heartbeat = utc_now()


if __name__ == "__main__":
    main()
