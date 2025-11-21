"""FastAPI dependencies for OmoiOS API."""

from typing import TYPE_CHECKING, Optional
from fastapi import Depends

if TYPE_CHECKING:
    from fastapi.security import HTTPAuthorizationCredentials

if TYPE_CHECKING:
    from omoi_os.services.agent_health import AgentHealthService
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


def get_phase_gate_service() -> "PhaseGateService":
    """Get phase gate service instance."""
    from omoi_os.api.main import phase_gate_service

    if phase_gate_service is None:
        raise RuntimeError("Phase gate service not initialized")
    return phase_gate_service


def get_event_bus_service() -> "EventBusService":
    """Get event bus service instance (alias for get_event_bus for consistency)."""
    return get_event_bus()


def get_agent_status_manager() -> "AgentStatusManager":
    """Get agent status manager instance."""
    from omoi_os.api.main import agent_status_manager

    if agent_status_manager is None:
        raise RuntimeError("Agent status manager not initialized")
    return agent_status_manager


def get_approval_service() -> "ApprovalService":
    """Get approval service instance."""
    from omoi_os.api.main import approval_service

    if approval_service is None:
        raise RuntimeError("Approval service not initialized")
    return approval_service


def get_llm_service() -> "LLMService":
    """Get LLM service instance for dependency injection."""
    from omoi_os.services.llm_service import get_llm_service
    
    return get_llm_service()


def get_restart_orchestrator():
    """Get RestartOrchestrator instance."""
    from omoi_os.services.restart_orchestrator import RestartOrchestrator
    from omoi_os.api.main import db, registry_service, queue, event_bus, agent_status_manager
    
    if db is None or registry_service is None or queue is None:
        raise RuntimeError("Required services not initialized")
    
    return RestartOrchestrator(
        db=db,
        agent_registry=registry_service,
        task_queue=queue,
        event_bus=event_bus,
        status_manager=agent_status_manager,
    )


def get_guardian_service():
    """Get GuardianService instance."""
    from omoi_os.services.guardian import GuardianService
    from omoi_os.api.main import db, event_bus
    
    if db is None:
        raise RuntimeError("Database service not initialized")
    
    return GuardianService(db=db, event_bus=event_bus)


def get_database_service() -> "DatabaseService":
    """Get database service instance (alias for get_db_service)."""
    return get_db_service()


def get_monitoring_loop():
    """Get MonitoringLoop instance."""
    from omoi_os.api.main import monitoring_loop
    
    if monitoring_loop is None:
        raise RuntimeError("Monitoring loop not initialized")
    return monitoring_loop


def get_supabase_auth_service():
    """Get Supabase auth service instance."""
    from omoi_os.services.supabase_auth import SupabaseAuthService
    from omoi_os.config import load_supabase_settings
    
    settings = load_supabase_settings()
    return SupabaseAuthService(settings)


async def get_current_user(
    credentials: "HTTPAuthorizationCredentials",
    supabase_auth = None,
    db: "DatabaseService" = None,
):
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials
        supabase_auth: Supabase auth service
        db: Database service

    Returns:
        Authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    from fastapi import Depends, HTTPException, status
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    
    if supabase_auth is None:
        supabase_auth = get_supabase_auth_service()
    if db is None:
        db = get_db_service()
    
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


async def get_current_user_optional(
    credentials: Optional["HTTPAuthorizationCredentials"] = None,
    supabase_auth = None,
    db: "DatabaseService" = None,
):
    """
    Get current user if authenticated, None otherwise.

    Useful for endpoints that work with or without authentication.
    """
    from fastapi.security import HTTPBearer
    
    if credentials is None:
        try:
            security = HTTPBearer(auto_error=False)
            # This will be handled by FastAPI's dependency injection
            return None
        except Exception:
            return None
    
    if not credentials:
        return None
    
    if supabase_auth is None:
        supabase_auth = get_supabase_auth_service()
    if db is None:
        db = get_db_service()
    
    try:
        return await get_current_user(credentials, supabase_auth, db)
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
    from fastapi import Depends, HTTPException, status
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
    from omoi_os.api.main import db
    
    if db is None:
        raise RuntimeError("Database service not initialized")
    
    # Use async context manager from DatabaseService
    async with db.get_async_session() as session:
        yield session


def get_auth_service(db_session = Depends(get_db_session)) -> "AuthService":
    """Get authentication service instance."""
    from omoi_os.services.auth_service import AuthService
    from omoi_os.config import settings
    
    return AuthService(
        db=db_session,
        jwt_secret=settings.jwt_secret_key,
        jwt_algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.access_token_expire_minutes,
        refresh_token_expire_days=settings.refresh_token_expire_days
    )


def get_authorization_service(db_session = Depends(get_db_session)) -> "AuthorizationService":
    """Get authorization service instance."""
    from omoi_os.services.authorization_service import AuthorizationService
    
    return AuthorizationService(db=db_session)


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db_session = Depends(get_db_session),
    auth_service: "AuthService" = Depends(get_auth_service)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    This is the new auth system version (replaces Supabase).
    """
    from fastapi import HTTPException, status
    from sqlalchemy import select
    from omoi_os.models.user import User
    
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
        headers={"WWW-Authenticate": "Bearer"}
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
    from fastapi import Depends, HTTPException, status
    from omoi_os.services.authorization_service import ActorType
    
    async def permission_checker(
        current_user: User = Depends(get_current_user_from_token),
        auth_service: "AuthorizationService" = Depends(get_authorization_service)
    ):
        allowed, reason, details = await auth_service.is_authorized(
            actor_id=current_user.id,
            actor_type=ActorType.USER,
            action=permission,
            organization_id=organization_id
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unauthorized: {reason}",
                headers={"X-Auth-Details": str(details)}
            )
        
        return details
    
    return permission_checker

