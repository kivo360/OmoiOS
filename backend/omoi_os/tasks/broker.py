"""
Taskiq broker configuration with Redis backend.

This module sets up the taskiq broker and scheduler for background
and scheduled task execution.

Usage:
    Worker: taskiq worker omoi_os.tasks.broker:broker
    Scheduler: taskiq scheduler omoi_os.tasks.broker:scheduler
"""

import logging as stdlib_logging
from typing import Any

from taskiq import TaskiqScheduler, TaskiqEvents, TaskiqState, TaskiqMessage
from taskiq import TaskiqMiddleware, TaskiqResult
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from omoi_os.config import load_redis_settings
from omoi_os.logging import configure_logging, get_logger

# Initialize structured logging for the worker
configure_logging()
logger = get_logger(__name__)

# Configure taskiq's internal loggers
# Set main taskiq logger to INFO to reduce noise (scheduler logs every second at DEBUG)
taskiq_logger = stdlib_logging.getLogger("taskiq")
taskiq_logger.setLevel(stdlib_logging.INFO)

# Specifically silence the noisy scheduler run module
scheduler_run_logger = stdlib_logging.getLogger("taskiq.cli.scheduler.run")
scheduler_run_logger.setLevel(stdlib_logging.WARNING)


def _get_redis_url() -> str:
    """Get Redis URL from config."""
    redis_settings = load_redis_settings()
    return redis_settings.url


def _get_broker() -> ListQueueBroker:
    """Create and configure the taskiq broker with result backend.

    Uses the project's pydantic-settings config system which supports:
    - YAML defaults (config/base.yaml + config/<env>.yaml)
    - Environment variables (REDIS_URL)
    - .env files
    """
    redis_url = _get_redis_url()

    # Log without exposing credentials
    safe_url = redis_url.split('@')[-1] if '@' in redis_url else redis_url
    logger.info(
        "Initializing taskiq broker",
        redis_host=safe_url,
        queue="omoios_tasks",
        result_backend="redis",
    )

    # Create result backend to store task results
    result_backend = RedisAsyncResultBackend(
        redis_url=redis_url,
        result_ex_time=3600,  # Results expire after 1 hour
    )

    return ListQueueBroker(
        url=redis_url,
        queue_name="omoios_tasks",
    ).with_result_backend(result_backend)


# Create the broker instance
broker = _get_broker()


# =============================================================================
# Logging Middleware
# =============================================================================

class LoggingMiddleware(TaskiqMiddleware):
    """Middleware to log all task execution with structured logging."""

    async def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        """Log before task execution."""
        logger.info(
            "Task received and starting execution",
            log_event="task_start",
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
        """Log after task execution with result details."""
        if result.is_err:
            logger.error(
                "Task execution failed",
                log_event="task_error",
                task_id=message.task_id,
                task_name=message.task_name,
                error=str(result.error),
                error_type=type(result.error).__name__ if result.error else None,
                execution_time=result.execution_time,
                log=result.log,  # Include any captured logs
            )
        else:
            logger.info(
                "Task execution completed successfully",
                log_event="task_complete",
                task_id=message.task_id,
                task_name=message.task_name,
                execution_time=result.execution_time,
                return_value_type=type(result.return_value).__name__ if result.return_value else None,
            )

    async def on_error(
        self,
        message: TaskiqMessage,
        result: TaskiqResult[Any],
        exception: BaseException,
    ) -> None:
        """Log unhandled exceptions during task execution."""
        logger.exception(
            "Unhandled exception in task",
            log_event="task_exception",
            task_id=message.task_id,
            task_name=message.task_name,
            exception_type=type(exception).__name__,
            exception_message=str(exception),
        )


# Add logging middleware to broker
broker.add_middlewares(LoggingMiddleware())


# =============================================================================
# Taskiq Event Hooks for Lifecycle Logging
# =============================================================================

@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def on_worker_startup(state: TaskiqState) -> None:
    """Log when worker starts up."""
    logger.info(
        "Taskiq worker started and ready to process tasks",
        log_event="worker_startup",
        queue="omoios_tasks",
    )


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def on_worker_shutdown(state: TaskiqState) -> None:
    """Log when worker shuts down."""
    logger.info(
        "Taskiq worker shutting down gracefully",
        log_event="worker_shutdown",
    )


@broker.on_event(TaskiqEvents.CLIENT_STARTUP)
async def on_client_startup(state: TaskiqState) -> None:
    """Log when client (task sender) starts up."""
    logger.info(
        "Taskiq client started - can now enqueue tasks",
        log_event="client_startup",
    )


@broker.on_event(TaskiqEvents.CLIENT_SHUTDOWN)
async def on_client_shutdown(state: TaskiqState) -> None:
    """Log when client shuts down."""
    logger.info(
        "Taskiq client shutting down",
        log_event="client_shutdown",
    )


# =============================================================================
# Scheduler Configuration
# =============================================================================

# Create the scheduler with LabelScheduleSource
# This allows tasks to be scheduled using the @broker.task(schedule=[...]) decorator
scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)

logger.info(
    "Taskiq broker and scheduler configured successfully",
    queue="omoios_tasks",
    result_backend="redis",
    scheduler_sources=["LabelScheduleSource"],
)
