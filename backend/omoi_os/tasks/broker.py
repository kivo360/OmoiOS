"""
Taskiq broker configuration with Redis backend.

This module sets up the taskiq broker and scheduler for background
and scheduled task execution.

Usage:
    Worker: taskiq worker omoi_os.tasks.broker:broker
    Scheduler: taskiq scheduler omoi_os.tasks.broker:scheduler
"""

from taskiq import TaskiqScheduler, TaskiqEvents, TaskiqState, TaskiqMessage
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListQueueBroker

from omoi_os.config import load_redis_settings
from omoi_os.logging import configure_logging, get_logger

# Initialize structured logging for the worker
configure_logging()
logger = get_logger(__name__)


def _get_broker() -> ListQueueBroker:
    """Create and configure the taskiq broker.

    Uses the project's pydantic-settings config system which supports:
    - YAML defaults (config/base.yaml + config/<env>.yaml)
    - Environment variables (REDIS_URL)
    - .env files
    """
    redis_settings = load_redis_settings()
    redis_url = redis_settings.url

    # Log without exposing credentials
    safe_url = redis_url.split('@')[-1] if '@' in redis_url else redis_url
    logger.info("Initializing taskiq broker", redis_host=safe_url, queue="omoios_tasks")

    return ListQueueBroker(
        url=redis_url,
        queue_name="omoios_tasks",
    )


# Create the broker instance
broker = _get_broker()


# =============================================================================
# Taskiq Event Hooks for Logging
# =============================================================================

@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def on_worker_startup(state: TaskiqState) -> None:
    """Log when worker starts up."""
    logger.info("Taskiq worker started", event="worker_startup")


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def on_worker_shutdown(state: TaskiqState) -> None:
    """Log when worker shuts down."""
    logger.info("Taskiq worker shutting down", event="worker_shutdown")


@broker.on_event(TaskiqEvents.CLIENT_STARTUP)
async def on_client_startup(state: TaskiqState) -> None:
    """Log when client starts up."""
    logger.info("Taskiq client started", event="client_startup")


@broker.on_event(TaskiqEvents.CLIENT_SHUTDOWN)
async def on_client_shutdown(state: TaskiqState) -> None:
    """Log when client shuts down."""
    logger.info("Taskiq client shutting down", event="client_shutdown")


# Task execution middleware for logging
from taskiq import TaskiqMiddleware, TaskiqResult
from typing import Any


class LoggingMiddleware(TaskiqMiddleware):
    """Middleware to log all task execution."""

    async def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        """Log before task execution."""
        logger.info(
            "Task starting",
            event="task_start",
            task_id=message.task_id,
            task_name=message.task_name,
            labels=message.labels,
        )
        return message

    async def post_execute(
        self,
        message: TaskiqMessage,
        result: TaskiqResult[Any],
    ) -> None:
        """Log after task execution."""
        if result.is_err:
            logger.error(
                "Task failed",
                event="task_error",
                task_id=message.task_id,
                task_name=message.task_name,
                error=str(result.error),
                execution_time=result.execution_time,
            )
        else:
            logger.info(
                "Task completed",
                event="task_complete",
                task_id=message.task_id,
                task_name=message.task_name,
                execution_time=result.execution_time,
            )


# Add logging middleware to broker
broker.add_middlewares(LoggingMiddleware())


# Create the scheduler with LabelScheduleSource
# This allows tasks to be scheduled using the @broker.task(schedule=[...]) decorator
scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)

logger.info("Taskiq broker and scheduler configured", queue="omoios_tasks")
