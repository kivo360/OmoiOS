"""
Taskiq broker configuration with Redis backend.

This module sets up the taskiq broker and scheduler for background
and scheduled task execution.

Usage:
    Worker: taskiq worker omoi_os.tasks.broker:broker
    Scheduler: taskiq scheduler omoi_os.tasks.broker:scheduler
"""

import logging

from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListQueueBroker

from omoi_os.config import load_redis_settings

logger = logging.getLogger(__name__)


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
    logger.info(f"Initializing taskiq broker with Redis: {safe_url}")

    return ListQueueBroker(
        url=redis_url,
        queue_name="omoios_tasks",
    )


# Create the broker instance
broker = _get_broker()

# Create the scheduler with LabelScheduleSource
# This allows tasks to be scheduled using the @broker.task(schedule=[...]) decorator
scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)
