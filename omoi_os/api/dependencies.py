"""FastAPI dependencies for OmoiOS API."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omoi_os.services.agent_health import AgentHealthService
    from omoi_os.services.agent_registry import AgentRegistryService
    from omoi_os.services.budget_enforcer import BudgetEnforcerService
    from omoi_os.services.collaboration import CollaborationService
    from omoi_os.services.cost_tracking import CostTrackingService
    from omoi_os.services.database import DatabaseService
    from omoi_os.services.event_bus import EventBusService
    from omoi_os.services.heartbeat_protocol import HeartbeatProtocolService
    from omoi_os.services.monitor import MonitorService
    from omoi_os.services.resource_lock import ResourceLockService
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


def get_collaboration_service() -> "CollaborationService":
    """Get collaboration service instance."""
    from omoi_os.api.main import collaboration_service

    if collaboration_service is None:
        raise RuntimeError("Collaboration service not initialized")
    return collaboration_service


def get_resource_lock_service() -> "ResourceLockService":
    """Get resource lock service instance."""
    from omoi_os.api.main import lock_service

    if lock_service is None:
        raise RuntimeError("Resource lock service not initialized")
    return lock_service


def get_monitor_service() -> "MonitorService":
    """Get monitor service instance."""
    from omoi_os.api.main import monitor_service

    if monitor_service is None:
        raise RuntimeError("Monitor service not initialized")
    return monitor_service


def get_cost_tracking_service() -> "CostTrackingService":
    """Get cost tracking service instance."""
    from omoi_os.api.main import cost_tracking_service

    if cost_tracking_service is None:
        raise RuntimeError("Cost tracking service not initialized")
    return cost_tracking_service


def get_budget_enforcer_service() -> "BudgetEnforcerService":
    """Get budget enforcer service instance."""
    from omoi_os.api.main import budget_enforcer_service

    if budget_enforcer_service is None:
        raise RuntimeError("Budget enforcer service not initialized")
    return budget_enforcer_service


def get_heartbeat_protocol_service() -> "HeartbeatProtocolService":
    """Get heartbeat protocol service instance."""
    from omoi_os.api.main import heartbeat_protocol_service

    if heartbeat_protocol_service is None:
        raise RuntimeError("Heartbeat protocol service not initialized")
    return heartbeat_protocol_service

