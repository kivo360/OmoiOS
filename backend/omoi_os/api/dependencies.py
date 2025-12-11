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


# Lazy singleton instances for fallback when main module globals are None
_db_service_instance: "DatabaseService | None" = None
_event_bus_instance: "EventBusService | None" = None
_task_queue_instance: "TaskQueueService | None" = None
_agent_status_manager_instance: "AgentStatusManager | None" = None
_approval_service_instance: "ApprovalService | None" = None
_phase_gate_service_instance: "PhaseGateService | None" = None
_collaboration_service_instance: "CollaborationService | None" = None
_resource_lock_service_instance: "ResourceLockService | None" = None
_cost_tracking_service_instance: "CostTrackingService | None" = None
_budget_enforcer_service_instance: "BudgetEnforcerService | None" = None
_agent_health_service_instance: "AgentHealthService | None" = None
_registry_service_instance: "AgentRegistryService | None" = None
_heartbeat_protocol_service_instance: "HeartbeatProtocolService | None" = None
_monitor_service_instance: "MonitorService | None" = None


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


def get_agent_status_manager() -> "AgentStatusManager":
    """Get agent status manager instance with lazy initialization fallback."""
    global _agent_status_manager_instance
    import omoi_os.api.main as main_module

    if main_module.agent_status_manager is not None:
        return main_module.agent_status_manager

    if _agent_status_manager_instance is not None:
        return _agent_status_manager_instance

    from omoi_os.services.agent_status_manager import AgentStatusManager

    _agent_status_manager_instance = AgentStatusManager(
        get_db_service(), get_event_bus()
    )
    return _agent_status_manager_instance


def get_agent_health_service() -> "AgentHealthService":
    """Get agent health service instance with lazy initialization fallback."""
    global _agent_health_service_instance
    import omoi_os.api.main as main_module

    if main_module.health_service is not None:
        return main_module.health_service

    if _agent_health_service_instance is not None:
        return _agent_health_service_instance

    from omoi_os.services.agent_health import AgentHealthService

    _agent_health_service_instance = AgentHealthService(
        get_db_service(), get_agent_status_manager()
    )
    return _agent_health_service_instance


def get_agent_registry_service() -> "AgentRegistryService":
    """Get agent registry service instance with lazy initialization fallback."""
    global _registry_service_instance
    import omoi_os.api.main as main_module

    if main_module.registry_service is not None:
        return main_module.registry_service

    if _registry_service_instance is not None:
        return _registry_service_instance

    from omoi_os.services.agent_registry import AgentRegistryService

    _registry_service_instance = AgentRegistryService(
        get_db_service(), get_event_bus(), get_agent_status_manager()
    )
    return _registry_service_instance


def get_collaboration_service() -> "CollaborationService":
    """Get collaboration service instance with lazy initialization fallback."""
    global _collaboration_service_instance
    import omoi_os.api.main as main_module

    if main_module.collaboration_service is not None:
        return main_module.collaboration_service

    if _collaboration_service_instance is not None:
        return _collaboration_service_instance

    from omoi_os.services.collaboration import CollaborationService

    _collaboration_service_instance = CollaborationService(
        get_db_service(), get_event_bus()
    )
    return _collaboration_service_instance


def get_resource_lock_service() -> "ResourceLockService":
    """Get resource lock service instance with lazy initialization fallback."""
    global _resource_lock_service_instance
    import omoi_os.api.main as main_module

    if main_module.lock_service is not None:
        return main_module.lock_service

    if _resource_lock_service_instance is not None:
        return _resource_lock_service_instance

    from omoi_os.services.resource_lock import ResourceLockService

    _resource_lock_service_instance = ResourceLockService(get_db_service())
    return _resource_lock_service_instance


def get_monitor_service() -> "MonitorService":
    """Get monitor service instance with lazy initialization fallback."""
    global _monitor_service_instance
    import omoi_os.api.main as main_module

    if main_module.monitor_service is not None:
        return main_module.monitor_service

    if _monitor_service_instance is not None:
        return _monitor_service_instance

    from omoi_os.services.monitor import MonitorService

    _monitor_service_instance = MonitorService(get_db_service(), get_event_bus())
    return _monitor_service_instance


def get_cost_tracking_service() -> "CostTrackingService":
    """Get cost tracking service instance with lazy initialization fallback."""
    global _cost_tracking_service_instance
    import omoi_os.api.main as main_module

    if main_module.cost_tracking_service is not None:
        return main_module.cost_tracking_service

    if _cost_tracking_service_instance is not None:
        return _cost_tracking_service_instance

    from omoi_os.services.cost_tracking import CostTrackingService

    _cost_tracking_service_instance = CostTrackingService(
        get_db_service(), get_event_bus()
    )
    return _cost_tracking_service_instance


def get_budget_enforcer_service() -> "BudgetEnforcerService":
    """Get budget enforcer service instance with lazy initialization fallback."""
    global _budget_enforcer_service_instance
    import omoi_os.api.main as main_module

    if main_module.budget_enforcer_service is not None:
        return main_module.budget_enforcer_service

    if _budget_enforcer_service_instance is not None:
        return _budget_enforcer_service_instance

    from omoi_os.services.budget_enforcer import BudgetEnforcerService

    _budget_enforcer_service_instance = BudgetEnforcerService(
        get_db_service(), get_event_bus()
    )
    return _budget_enforcer_service_instance


def get_heartbeat_protocol_service() -> "HeartbeatProtocolService":
    """Get heartbeat protocol service instance with lazy initialization fallback."""
    global _heartbeat_protocol_service_instance
    import omoi_os.api.main as main_module

    if main_module.heartbeat_protocol_service is not None:
        return main_module.heartbeat_protocol_service

    if _heartbeat_protocol_service_instance is not None:
        return _heartbeat_protocol_service_instance

    from omoi_os.services.heartbeat_protocol import HeartbeatProtocolService

    _heartbeat_protocol_service_instance = HeartbeatProtocolService(
        get_db_service(), get_event_bus(), get_agent_status_manager()
    )
    return _heartbeat_protocol_service_instance


def get_phase_gate_service() -> "PhaseGateService":
    """Get phase gate service instance with lazy initialization fallback."""
    global _phase_gate_service_instance
    import omoi_os.api.main as main_module

    if main_module.phase_gate_service is not None:
        return main_module.phase_gate_service

    if _phase_gate_service_instance is not None:
        return _phase_gate_service_instance

    from omoi_os.services.phase_gate import PhaseGateService

    _phase_gate_service_instance = PhaseGateService(get_db_service())
    return _phase_gate_service_instance


def get_event_bus_service() -> "EventBusService":
    """Get event bus service instance (alias for get_event_bus for consistency)."""
    return get_event_bus()


def get_approval_service() -> "ApprovalService":
    """Get approval service instance with lazy initialization fallback."""
    global _approval_service_instance
    import omoi_os.api.main as main_module

    if main_module.approval_service is not None:
        return main_module.approval_service

    if _approval_service_instance is not None:
        return _approval_service_instance

    from omoi_os.services.approval import ApprovalService

    _approval_service_instance = ApprovalService(get_db_service(), get_event_bus())
    return _approval_service_instance


def get_llm_service() -> "LLMService":
    """Get LLM service instance for dependency injection."""
    from omoi_os.services.llm_service import get_llm_service

    return get_llm_service()


def get_restart_orchestrator():
    """Get RestartOrchestrator instance using fallback-enabled getters."""
    from omoi_os.services.restart_orchestrator import RestartOrchestrator

    return RestartOrchestrator(
        db=get_db_service(),
        agent_registry=get_agent_registry_service(),
        task_queue=get_task_queue(),
        event_bus=get_event_bus(),
        status_manager=get_agent_status_manager(),
    )


def get_guardian_service():
    """Get GuardianService instance using fallback-enabled getters."""
    from omoi_os.services.guardian import GuardianService

    return GuardianService(db=get_db_service(), event_bus=get_event_bus())


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

    Uses local JWT auth (not Supabase).

    Args:
        credentials: HTTP Bearer token credentials
        db: Database service

    Returns:
        Authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    from omoi_os.services.auth_service import AuthService
    from omoi_os.config import settings
    from omoi_os.models.user import User

    token = credentials.credentials

    # Create auth service with a sync session
    with db.get_session() as session:
        auth_service = AuthService(
            db=session,
            jwt_secret=settings.jwt_secret_key,
            jwt_algorithm=settings.jwt_algorithm,
            access_token_expire_minutes=settings.access_token_expire_minutes,
            refresh_token_expire_days=settings.refresh_token_expire_days,
        )

        # Verify JWT token
        token_data = auth_service.verify_token(token, token_type="access")
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Load user from database
        user = session.get(User, token_data.user_id)
        if not user or user.deleted_at:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Eagerly load all attributes before session closes
        # This prevents DetachedInstanceError when serializing
        session.refresh(user)
        session.expunge(user)

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


def get_sync_db_session():
    """Get sync database session from DatabaseService.

    Use this for sync routes that need a SQLAlchemy Session.
    The session is automatically committed on success or rolled back on error.
    """
    db = get_db_service()
    with db.get_session() as session:
        yield session


async def get_db_session():
    """Get async database session from DatabaseService using fallback-enabled getter."""
    db = get_db_service()

    # Use async context manager from DatabaseService
    async with db.get_async_session() as session:
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


# Singleton instances for embedding and deduplication services
_embedding_service_instance = None
_ticket_dedup_service_instance = None


def get_embedding_service():
    """Get embedding service instance with lazy initialization."""
    global _embedding_service_instance

    if _embedding_service_instance is not None:
        return _embedding_service_instance

    from omoi_os.services.embedding import EmbeddingService

    _embedding_service_instance = EmbeddingService()
    return _embedding_service_instance


def get_ticket_dedup_service():
    """Get ticket deduplication service with lazy initialization."""
    global _ticket_dedup_service_instance

    if _ticket_dedup_service_instance is not None:
        return _ticket_dedup_service_instance

    from omoi_os.services.ticket_dedup import TicketDeduplicationService

    db = get_db_service()
    embedding_service = get_embedding_service()
    _ticket_dedup_service_instance = TicketDeduplicationService(
        db=db,
        embedding_service=embedding_service,
    )
    return _ticket_dedup_service_instance
