"""FastAPI dependencies for OmoiOS API."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omoi_os.services.agent_health import AgentHealthService
    from omoi_os.services.agent_registry import AgentRegistryService
    from omoi_os.services.database import DatabaseService
    from omoi_os.services.event_bus import EventBusService
    from omoi_os.services.task_queue import TaskQueueService


def get_db_service() -> "DatabaseService":
    """Get database service instance."""
    # Lazy import to avoid circular dependency
    from omoi_os.api.main import db

    if db is None:
        raise RuntimeError("Database service not initialized")
    return db


def get_event_bus() -> "EventBusService":
    """Get event bus service instance."""
    # Lazy import to avoid circular dependency
    from omoi_os.api.main import event_bus

    if event_bus is None:
        raise RuntimeError("Event bus not initialized")
    return event_bus


def get_task_queue() -> "TaskQueueService":
    """Get task queue service instance."""
    # Lazy import to avoid circular dependency
    from omoi_os.api.main import queue

    if queue is None:
        raise RuntimeError("Task queue not initialized")
    return queue


def get_agent_health_service() -> "AgentHealthService":
    """Get agent health service instance."""
    # Lazy import to avoid circular dependency
    from omoi_os.api.main import health_service

    if health_service is None:
        raise RuntimeError("Agent health service not initialized")
    return health_service


def get_agent_registry_service() -> "AgentRegistryService":
    """Get agent registry service instance."""
    from omoi_os.api.main import registry_service

    if registry_service is None:
        raise RuntimeError("Agent registry service not initialized")
    return registry_service

