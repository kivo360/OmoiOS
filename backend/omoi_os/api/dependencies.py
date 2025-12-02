"""FastAPI dependencies for OmoiOS API."""

from typing import TYPE_CHECKING, Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Security scheme
security = HTTPBearer()

if TYPE_CHECKING:
    from omoi_os.models.user import User
    from omoi_os.services.agent_health import AgentHealthService
    from omoi_os.services.auth_service import AuthService
    from omoi_os.services.authorization_service import AuthorizationService
    from omoi_os.services.agent_registry import AgentRegistryService
    from omoi_os.services.agent_status_manager import AgentStatusManager
    from omoi_os.services.approval import ApprovalService
    from omoi_os.services.budget_enforcer import BudgetEnforcerService
    from omoi_os.services.collaboration import CollaborationService
    from omoi_os.services.cost_tracking import CostTrackingService
    from omoi_os.services.database import DatabaseService
    from omoi_os.services.event_bus import EventBusService
    from omoi_os.services.heartbeat_protocol import HeartbeatProtocolService
    from omoi_os.services.llm_service import LLMService
    from omoi_os.services.monitor import MonitorService
    from omoi_os.services.phase_gate import PhaseGateService
    from omoi_os.services.resource_lock import ResourceLockService
    from omoi_os.services.task_queue import TaskQueueService


_db_service_instance: "DatabaseService | None" = None
_event_bus_instance: "EventBusService | None" = None
_task_queue_instance: "TaskQueueService | None" = None


def get_db_service() -> "DatabaseService":
    """Get database service instance with lazy initialization fallback."""
    global _db_service_instance

    # First, try to get from main module (set by lifespan)
    import omoi_os.api.main as main_module

    if main_module.db is not None:
        return main_module.db

    # Fallback: Use cached singleton or create new one
    if _db_service_instance is not None:
        return _db_service_instance

    # Last resort: Create new DatabaseService from config
    from omoi_os.config import get_app_settings
    from omoi_os.services.database import DatabaseService

    app_settings = get_app_settings()
    _db_service_instance = DatabaseService(connection_string=app_settings.database.url)

    return _db_service_instance


def get_event_bus() -> "EventBusService":
    """Get event bus service instance with lazy initialization fallback."""
    global _event_bus_instance
    
    import omoi_os.api.main as main_module

    if main_module.event_bus is not None:
        return main_module.event_bus

    # Fallback: Use cached singleton or create new one
    if _event_bus_instance is not None:
        return _event_bus_instance

    # Last resort: Create new EventBusService from config
    from omoi_os.config import get_app_settings
    from omoi_os.services.event_bus import EventBusService

    app_settings = get_app_settings()
    _event_bus_instance = EventBusService(redis_url=app_settings.redis.url)

    return _event_bus_instance


def get_task_queue() -> "TaskQueueService":
    """Get task queue service instance with lazy initialization fallback."""
    global _task_queue_instance
    
    import omoi_os.api.main as main_module

    if main_module.queue is not None:
        return main_module.queue

    # Fallback: Use cached singleton or create new one
    if _task_queue_instance is not None:
        return _task_queue_instance

    # Last resort: Create new TaskQueueService (requires db and event_bus)
    from omoi_os.services.task_queue import TaskQueueService

    db = get_db_service()
    event_bus = get_event_bus()
    _task_queue_instance = TaskQueueService(db, event_bus=event_bus)

    return _task_queue_instance


def get_agent_health_service() -> "AgentHealthService":
    """Get agent health service instance."""
    import omoi_os.api.main as main_module

    if main_module.health_service is None:
        raise RuntimeError("Agent health service not initialized")
    return main_module.health_service


def get_agent_registry_service() -> "AgentRegistryService":
    """Get agent registry service instance."""
    import omoi_os.api.main as main_module

    if main_module.registry_service is None:
        raise RuntimeError("Agent registry service not initialized")
    return main_module.registry_service


def get_collaboration_service() -> "CollaborationService":
    """Get collaboration service instance."""
    import omoi_os.api.main as main_module

    if main_module.collaboration_service is None:
        raise RuntimeError("Collaboration service not initialized")
    return main_module.collaboration_service


def get_resource_lock_service() -> "ResourceLockService":
    """Get resource lock service instance."""
    import omoi_os.api.main as main_module

    if main_module.lock_service is None:
        raise RuntimeError("Resource lock service not initialized")
    return main_module.lock_service


def get_monitor_service() -> "MonitorService":
    """Get monitor service instance."""
    import omoi_os.api.main as main_module

    if main_module.monitor_service is None:
        raise RuntimeError("Monitor service not initialized")
    return main_module.monitor_service


def get_cost_tracking_service() -> "CostTrackingService":
    """Get cost tracking service instance."""
    import omoi_os.api.main as main_module

    if main_module.cost_tracking_service is None:
        raise RuntimeError("Cost tracking service not initialized")
    return main_module.cost_tracking_service


def get_budget_enforcer_service() -> "BudgetEnforcerService":
    """Get budget enforcer service instance."""
    import omoi_os.api.main as main_module

    if main_module.budget_enforcer_service is None:
        raise RuntimeError("Budget enforcer service not initialized")
    return main_module.budget_enforcer_service


def get_heartbeat_protocol_service() -> "HeartbeatProtocolService":
    """Get heartbeat protocol service instance."""
    import omoi_os.api.main as main_module

    if main_module.heartbeat_protocol_service is None:
        raise RuntimeError("Heartbeat protocol service not initialized")
    return main_module.heartbeat_protocol_service


def get_phase_gate_service() -> "PhaseGateService":
    """Get phase gate service instance."""
    import omoi_os.api.main as main_module

    if main_module.phase_gate_service is None:
        raise RuntimeError("Phase gate service not initialized")
    return main_module.phase_gate_service


def get_event_bus_service() -> "EventBusService":
    """Get event bus service instance (alias for get_event_bus for consistency)."""
    return get_event_bus()


def get_agent_status_manager() -> "AgentStatusManager":
    """Get agent status manager instance."""
    import omoi_os.api.main as main_module

    if main_module.agent_status_manager is None:
        raise RuntimeError("Agent status manager not initialized")
    return main_module.agent_status_manager


def get_approval_service() -> "ApprovalService":
    """Get approval service instance."""
    import omoi_os.api.main as main_module

    if main_module.approval_service is None:
        raise RuntimeError("Approval service not initialized")
    return main_module.approval_service


def get_llm_service() -> "LLMService":
    """Get LLM service instance for dependency injection."""
    from omoi_os.services.llm_service import get_llm_service

    return get_llm_service()


def get_restart_orchestrator():
    """Get RestartOrchestrator instance."""
    from omoi_os.services.restart_orchestrator import RestartOrchestrator
    import omoi_os.api.main as main_module

    if (
        main_module.db is None
        or main_module.registry_service is None
        or main_module.queue is None
    ):
        raise RuntimeError("Required services not initialized")

    return RestartOrchestrator(
        db=main_module.db,
        agent_registry=main_module.registry_service,
        task_queue=main_module.queue,
        event_bus=main_module.event_bus,
        status_manager=main_module.agent_status_manager,
    )


def get_guardian_service():
    """Get GuardianService instance."""
    from omoi_os.services.guardian import GuardianService
    import omoi_os.api.main as main_module

    if main_module.db is None:
        raise RuntimeError("Database service not initialized")

    return GuardianService(db=main_module.db, event_bus=main_module.event_bus)


def get_database_service() -> "DatabaseService":
    """Get database service instance (alias for get_db_service)."""
    return get_db_service()


def get_monitoring_loop():
    """Get MonitoringLoop instance."""
    import omoi_os.api.main as main_module

    if main_module.monitoring_loop is None:
        raise RuntimeError("Monitoring loop not initialized")
    return main_module.monitoring_loop


def get_supabase_auth_service():
    """Get Supabase auth service instance."""
    from omoi_os.services.supabase_auth import SupabaseAuthService
    from omoi_os.config import load_supabase_settings

    settings = load_supabase_settings()
    return SupabaseAuthService(settings)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: "DatabaseService" = Depends(get_db_service),
):
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials
        db: Database service

    Returns:
        Authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    supabase_auth = get_supabase_auth_service()

    from omoi_os.models.user import User

    token = credentials.credentials

    # Verify JWT token
    user_info = supabase_auth.verify_jwt_token(token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Load user from public.users
    with db.get_session() as session:
        user = session.get(User, user_info["id"])
        if not user or user.deleted_at:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user


_optional_security = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_optional_security),
    db: "DatabaseService" = Depends(get_db_service),
):
    """
    Get current user if authenticated, None otherwise.

    Useful for endpoints that work with or without authentication.
    """
    if credentials is None:
        return None

        supabase_auth = get_supabase_auth_service()

    try:
        return await get_current_user(credentials, db)
    except Exception:
        return None


def require_role(allowed_roles: list[str]):
    """
    Dependency factory for role-based authorization.

    Usage:
        @router.post("/admin-only")
        async def admin_endpoint(
            current_user: User = Depends(require_role(["admin"]))
        ):
            ...
    """
    from fastapi import Depends
    from omoi_os.models.user import User

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of these roles: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker


# New auth system dependencies


async def get_db_session():
    """Get async database session from DatabaseService."""
    import omoi_os.api.main as main_module

    if main_module.db is None:
        raise RuntimeError("Database service not initialized")

    # Use async context manager from DatabaseService
    async with main_module.db.get_async_session() as session:
        yield session


def get_auth_service(db_session=Depends(get_db_session)) -> "AuthService":
    """Get authentication service instance."""
    from omoi_os.services.auth_service import AuthService
    from omoi_os.config import settings

    return AuthService(
        db=db_session,
        jwt_secret=settings.jwt_secret_key,
        jwt_algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.access_token_expire_minutes,
        refresh_token_expire_days=settings.refresh_token_expire_days,
    )


def get_authorization_service(
    db_session=Depends(get_db_session),
) -> "AuthorizationService":
    """Get authorization service instance."""
    from omoi_os.services.authorization_service import AuthorizationService

    return AuthorizationService(db=db_session)


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db_session=Depends(get_db_session),
    auth_service: "AuthService" = Depends(get_auth_service),
) -> "User":
    """
    Get current authenticated user from JWT token.

    This is the new auth system version (replaces Supabase).
    """

    token = credentials.credentials

    # Try to verify as JWT first
    token_data = auth_service.verify_token(token, token_type="access")

    if token_data:
        # Load user
        user = await auth_service.get_user_by_id(token_data.user_id)
        if user:
            return user

    # Try to verify as API key
    api_key_result = await auth_service.verify_api_key(token)
    if api_key_result:
        user, api_key = api_key_result
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_permission(permission: str, organization_id: UUID):
    """
    Dependency factory for permission-based authorization.

    Usage:
        @router.get("/projects")
        async def list_projects(
            auth=Depends(require_permission("project:read", org_id))
        ):
            ...
    """
    from fastapi import Depends
    from omoi_os.services.authorization_service import ActorType

    async def permission_checker(
        current_user: User = Depends(get_current_user_from_token),
        auth_service: "AuthorizationService" = Depends(get_authorization_service),
    ):
        allowed, reason, details = await auth_service.is_authorized(
            actor_id=current_user.id,
            actor_type=ActorType.USER,
            action=permission,
            organization_id=organization_id,
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unauthorized: {reason}",
                headers={"X-Auth-Details": str(details)},
            )

        return details

    return permission_checker
