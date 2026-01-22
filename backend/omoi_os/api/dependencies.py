"""FastAPI dependencies for OmoiOS API."""

from typing import TYPE_CHECKING, Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from omoi_os.logging import get_logger

logger = get_logger(__name__)

# Security scheme
# Use auto_error=False to handle missing tokens gracefully
# We'll check for credentials manually and raise appropriate errors
security = HTTPBearer(auto_error=False)

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
    from omoi_os.services.phase_manager import PhaseManager
    from omoi_os.services.resource_lock import ResourceLockService
    from omoi_os.services.task_queue import TaskQueueService


# Lazy singleton instances for fallback when main module globals are None
_db_service_instance: "DatabaseService | None" = None
_event_bus_instance: "EventBusService | None" = None
_task_queue_instance: "TaskQueueService | None" = None
_agent_status_manager_instance: "AgentStatusManager | None" = None
_approval_service_instance: "ApprovalService | None" = None
_phase_gate_service_instance: "PhaseGateService | None" = None
_phase_manager_instance: "PhaseManager | None" = None
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
    _db_service_instance = DatabaseService(
        connection_string=app_settings.database.url,
        pool_size=app_settings.database.pool_size,
        max_overflow=app_settings.database.max_overflow,
        pool_timeout=app_settings.database.pool_timeout,
        pool_recycle=app_settings.database.pool_recycle,
        pool_pre_ping=app_settings.database.pool_pre_ping,
        pool_use_lifo=app_settings.database.pool_use_lifo,
        command_timeout=app_settings.database.command_timeout,
        connect_timeout=app_settings.database.connect_timeout,
    )

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


def get_phase_manager_service() -> "PhaseManager":
    """Get phase manager service instance with lazy initialization fallback.

    The PhaseManager provides a unified interface for:
    - Phase definitions and metadata
    - Transition rules and validation
    - Automatic progression callbacks
    - Phase gate orchestration
    - Status synchronization
    """
    global _phase_manager_instance
    import omoi_os.api.main as main_module

    if main_module.phase_manager is not None:
        return main_module.phase_manager

    if _phase_manager_instance is not None:
        return _phase_manager_instance

    # Last resort: Use the singleton getter from phase_manager module
    from omoi_os.services.phase_manager import get_phase_manager

    _phase_manager_instance = get_phase_manager(
        db=get_db_service(),
        task_queue=get_task_queue(),
        phase_gate=get_phase_gate_service(),
        event_bus=get_event_bus(),
    )
    return _phase_manager_instance


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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: "DatabaseService" = Depends(get_db_service),
):
    """
    Get current authenticated user from JWT token.

    Uses local JWT auth (not Supabase).

    Args:
        credentials: HTTP Bearer token credentials (optional if auto_error=False)
        db: Database service

    Returns:
        Authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    from omoi_os.services.auth_service import AuthService
    from omoi_os.config import settings
    from omoi_os.models.user import User

    # Check if credentials are provided
    if not credentials:
        # Debug level - this is expected for unauthenticated requests to protected endpoints
        logger.debug("Missing Authorization header in get_current_user")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token = credentials.credentials
    except AttributeError as e:
        logger.error(
            f"Missing credentials.credentials in get_current_user: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
            logger.warning("Token verification failed in get_current_user")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Load user from database
        user = session.get(User, token_data.user_id)
        if not user:
            logger.warning(f"User {token_data.user_id} not found in database")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if user.deleted_at:
            logger.warning(f"User {user.id} is deleted")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check waitlist status - allow login but we'll block app access elsewhere
        # This allows users to see their waitlist status via /auth/me

        # Eagerly load all attributes before session closes
        # This prevents DetachedInstanceError when serializing
        # Access attributes to ensure JSONB field is loaded
        _ = user.attributes  # Force load the JSONB field
        session.refresh(user)
        session.expunge(user)

        return user


_optional_security = HTTPBearer(auto_error=False)


async def get_approved_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: "DatabaseService" = Depends(get_db_service),
) -> "User":
    """
    Get current authenticated user, but only if they are approved (not on waitlist).

    Use this dependency for routes that should be blocked for waitlist users.
    Waitlist users will get a 403 Forbidden with a message about their status.

    Args:
        credentials: HTTP Bearer token credentials
        db: Database service

    Returns:
        Authenticated and approved user

    Raises:
        HTTPException: If user is on waitlist (403) or not authenticated (401)
    """
    # First, get the authenticated user
    user = await get_current_user(credentials, db)

    # Check waitlist status
    if hasattr(user, "waitlist_status") and user.waitlist_status != "approved":
        logger.info(f"User {user.id} blocked - waitlist_status: {user.waitlist_status}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "waitlist_pending",
                "message": "You're on the waitlist! We'll notify you when your account is approved.",
                "waitlist_status": user.waitlist_status,
            },
        )

    return user


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


# =============================================================================
# Multi-Tenant Access Control Helpers
# =============================================================================


async def get_user_organization_ids(
    current_user: "User" = Depends(get_current_user),
    db: "DatabaseService" = Depends(get_db_service),
) -> list[UUID]:
    """
    Get list of organization IDs the current user has access to.

    This is the foundation for multi-tenant filtering. Use this to filter
    queries to only return data from organizations the user is a member of.

    Returns:
        List of organization UUIDs the user can access
    """
    from sqlalchemy import select
    from omoi_os.models.organization import OrganizationMembership, Organization

    async with db.get_async_session() as session:
        # Get orgs where user is a member
        result = await session.execute(
            select(OrganizationMembership.organization_id).where(
                OrganizationMembership.user_id == current_user.id
            )
        )
        member_org_ids = [row[0] for row in result.fetchall()]

        # Also include orgs the user owns (they may not have a membership row)
        owner_result = await session.execute(
            select(Organization.id).where(Organization.owner_id == current_user.id)
        )
        owner_org_ids = [row[0] for row in owner_result.fetchall()]

        # Combine and deduplicate
        all_org_ids = list(set(member_org_ids + owner_org_ids))
        return all_org_ids


async def verify_organization_access(
    organization_id: UUID,
    current_user: "User" = Depends(get_current_user),
    db: "DatabaseService" = Depends(get_db_service),
) -> UUID:
    """
    Verify the current user has access to the specified organization.

    Use this as a dependency for routes that require access to a specific org.

    Args:
        organization_id: The organization ID to check access for

    Returns:
        The organization ID if access is granted

    Raises:
        HTTPException 403: If user doesn't have access to the organization
        HTTPException 404: If organization doesn't exist
    """
    from sqlalchemy import select
    from omoi_os.models.organization import Organization, OrganizationMembership

    async with db.get_async_session() as session:
        # Check if org exists
        org_result = await session.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        org = org_result.scalar_one_or_none()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )

        # Check if user is owner
        if org.owner_id == current_user.id:
            return organization_id

        # Check if user is a member
        membership_result = await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == current_user.id,
                OrganizationMembership.organization_id == organization_id,
            )
        )
        membership = membership_result.scalar_one_or_none()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this organization",
            )

        return organization_id


async def get_accessible_project_ids(
    current_user: "User" = Depends(get_current_user),
    db: "DatabaseService" = Depends(get_db_service),
) -> list[UUID]:
    """
    Get list of project IDs the current user has access to.

    Projects are accessible if they belong to an organization the user is a member of.

    Returns:
        List of project UUIDs the user can access
    """
    from sqlalchemy import select
    from omoi_os.models.project import Project

    # First get the user's organization IDs
    org_ids = await get_user_organization_ids(current_user, db)

    if not org_ids:
        return []

    async with db.get_async_session() as session:
        result = await session.execute(
            select(Project.id).where(Project.organization_id.in_(org_ids))
        )
        project_ids = [row[0] for row in result.fetchall()]
        return project_ids


async def verify_project_access(
    project_id: str,
    current_user: "User" = Depends(get_current_user),
    db: "DatabaseService" = Depends(get_db_service),
) -> str:
    """
    Verify the current user has access to the specified project.

    A project is accessible if it belongs to an organization the user is a member of.

    Args:
        project_id: The project ID to check access for

    Returns:
        The project ID if access is granted

    Raises:
        HTTPException 403: If user doesn't have access to the project
        HTTPException 404: If project doesn't exist
    """
    from sqlalchemy import select
    from omoi_os.models.project import Project

    async with db.get_async_session() as session:
        # Get the project
        result = await session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        # If project has no organization, check if user created it
        if project.organization_id is None:
            # Projects without org are legacy - allow access for now
            # TODO: Migrate all projects to have an organization
            logger.warning(
                f"Project {project_id} has no organization_id - allowing access",
                project_id=project_id,
                user_id=str(current_user.id),
            )
            return project_id

        # Check if user has access to the project's organization
        org_ids = await get_user_organization_ids(current_user, db)

        if project.organization_id not in org_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project",
            )

        return project_id


async def verify_ticket_access(
    ticket_id: str,
    current_user: "User" = Depends(get_current_user),
    db: "DatabaseService" = Depends(get_db_service),
) -> str:
    """
    Verify the current user has access to the specified ticket.

    A ticket is accessible if:
    1. The ticket's user_id matches the current user (direct ownership)
    2. OR the ticket belongs to a project in an organization the user is a member of

    Args:
        ticket_id: The ticket ID to check access for

    Returns:
        The ticket ID if access is granted

    Raises:
        HTTPException 403: If user doesn't have access to the ticket
        HTTPException 404: If ticket doesn't exist
    """
    from sqlalchemy import select
    from omoi_os.models.ticket import Ticket

    async with db.get_async_session() as session:
        # Get the ticket
        result = await session.execute(
            select(Ticket).where(Ticket.id == ticket_id)
        )
        ticket = result.scalar_one_or_none()

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found",
            )

        # Check direct user ownership first (new user_id field)
        if ticket.user_id and ticket.user_id == current_user.id:
            return ticket_id

        # If ticket has a project, verify project access
        if ticket.project_id:
            await verify_project_access(ticket.project_id, current_user, db)
            return ticket_id

        # Ticket has no user_id and no project_id - deny access
        # (Legacy tickets without user_id should be migrated)
        logger.warning(
            f"Ticket {ticket_id} has no user_id or project_id - denying access",
            ticket_id=ticket_id,
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this ticket",
        )


async def verify_task_access(
    task_id: str,
    current_user: "User" = Depends(get_current_user),
    db: "DatabaseService" = Depends(get_db_service),
) -> str:
    """
    Verify the current user has access to the specified task.

    A task is accessible if it belongs to a ticket in a project in an organization
    the user is a member of.

    Args:
        task_id: The task ID to check access for

    Returns:
        The task ID if access is granted

    Raises:
        HTTPException 403: If user doesn't have access to the task
        HTTPException 404: If task doesn't exist
    """
    from sqlalchemy import select
    from omoi_os.models.task import Task

    async with db.get_async_session() as session:
        # Get the task
        result = await session.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        # Verify access to the task's ticket
        await verify_ticket_access(task.ticket_id, current_user, db)

        return task_id


async def verify_spec_access(
    spec_id: str,
    current_user: "User" = Depends(get_current_user),
    db: "DatabaseService" = Depends(get_db_service),
) -> str:
    """
    Verify the current user has access to the specified spec.

    A spec is accessible if:
    1. The spec's user_id matches the current user (direct ownership)
    2. OR the spec belongs to a project in an organization the user is a member of

    Args:
        spec_id: The spec ID to check access for

    Returns:
        The spec ID if access is granted

    Raises:
        HTTPException 403: If user doesn't have access to the spec
        HTTPException 404: If spec doesn't exist
    """
    from sqlalchemy import select
    from omoi_os.models.spec import Spec

    async with db.get_async_session() as session:
        # Get the spec
        result = await session.execute(
            select(Spec).where(Spec.id == spec_id)
        )
        spec = result.scalar_one_or_none()

        if not spec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Spec not found",
            )

        # Check direct user ownership first (user_id field)
        if hasattr(spec, 'user_id') and spec.user_id and spec.user_id == current_user.id:
            return spec_id

        # If spec has a project, verify project access
        if spec.project_id:
            await verify_project_access(spec.project_id, current_user, db)
            return spec_id

        # Spec has no user_id and no valid project access - deny access
        logger.warning(
            f"Spec {spec_id} access denied - no user_id and no valid project access",
            spec_id=spec_id,
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this spec",
        )
