"""MCP API routes for tool registration and invocation."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from omoi_os.models.mcp_server import MCPServer, MCPTool
from omoi_os.api.dependencies import (
    get_db_service,
    get_event_bus_service,
)
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.mcp_authorization import MCPAuthorizationService, PolicyGrant
from omoi_os.services.mcp_integration import (
    MCPIntegrationService,
    MCPInvocationRequest,
    MCPInvocationResult,
)
from omoi_os.services.mcp_registry import MCPRegistryService
from omoi_os.services.mcp_retry import MCPRetryManager
from omoi_os.utils.datetime import utc_now

router = APIRouter(prefix="/api/mcp", tags=["MCP"])


# Request/Response Models
class RegisterServerRequest(BaseModel):
    """Request model for registering MCP server."""

    server_id: str = Field(..., description="Unique server identifier")
    version: str = Field(..., description="Server version")
    capabilities: List[str] = Field(default_factory=list, description="Server capabilities")
    tools: List[Dict[str, Any]] = Field(..., description="List of tool definitions")
    connection_url: Optional[str] = Field(
        default=None, description="MCP server connection URL or path (HTTP URL or local file path)"
    )
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional server metadata")


class RegisterServerResponse(BaseModel):
    """Response model for server registration."""

    server_id: str
    registered_count: int
    rejected_count: int
    registered_tools: List[Dict[str, Any]]
    rejected_tools: List[Dict[str, Any]]


class InvokeToolRequest(BaseModel):
    """Request model for tool invocation."""

    correlation_id: Optional[str] = Field(
        default_factory=lambda: f"req-{uuid.uuid4()}", description="Correlation ID"
    )
    agent_id: str = Field(..., description="Agent identifier")
    server_id: str = Field(..., description="Server identifier")
    tool_name: str = Field(..., description="Tool name")
    params: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    idempotency_key: Optional[str] = Field(default=None, description="Idempotency key")
    ticket_id: Optional[str] = Field(default=None, description="Associated ticket ID")
    task_id: Optional[str] = Field(default=None, description="Associated task ID")


class InvokeToolResponse(BaseModel):
    """Response model for tool invocation."""

    correlation_id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    attempts: int = 1
    latency_ms: float = 0.0
    completed_at: str


class GrantPermissionRequest(BaseModel):
    """Request model for granting tool permission."""

    agent_id: str = Field(..., description="Agent identifier")
    server_id: str = Field(..., description="Server identifier")
    tool_name: str = Field(..., description="Tool name")
    actions: List[str] = Field(default_factory=list, description="Allowed actions")
    granted_by: Optional[str] = Field(default=None, description="Who granted the permission")
    expires_at: Optional[str] = Field(default=None, description="Policy expiration (ISO format)")


class GrantPermissionResponse(BaseModel):
    """Response model for permission grant."""

    agent_id: str
    server_id: str
    tool_name: str
    actions: List[str]
    token_id: Optional[str] = None


# Dependency injection helpers
def get_mcp_registry(db: DatabaseService = Depends(get_db_service)) -> MCPRegistryService:
    """Get MCP registry service."""
    return MCPRegistryService(db)


def get_mcp_authorization(db: DatabaseService = Depends(get_db_service)) -> MCPAuthorizationService:
    """Get MCP authorization service."""
    return MCPAuthorizationService(db)


def get_mcp_retry_manager() -> MCPRetryManager:
    """Get MCP retry manager."""
    return MCPRetryManager()


def get_mcp_integration(
    db: DatabaseService = Depends(get_db_service),
    registry: MCPRegistryService = Depends(get_mcp_registry),
    authorization: MCPAuthorizationService = Depends(get_mcp_authorization),
    retry_manager: MCPRetryManager = Depends(get_mcp_retry_manager),
    event_bus: EventBusService = Depends(get_event_bus_service),
) -> MCPIntegrationService:
    """Get MCP integration service."""
    return MCPIntegrationService(
        db=db,
        registry=registry,
        authorization=authorization,
        retry_manager=retry_manager,
        event_bus=event_bus,
    )


# API Endpoints
@router.post("/register", response_model=RegisterServerResponse)
async def register_server(
    request: RegisterServerRequest,
    registry: MCPRegistryService = Depends(get_mcp_registry),
) -> RegisterServerResponse:
    """
    Register MCP server and tools.
    
    REQ-MCP-REG-001: Server Discovery
    REQ-MCP-REG-002: Schema Validation
    """
    result = await registry.register_server(
        server_id=request.server_id,
        version=request.version,
        capabilities=request.capabilities,
        tools=request.tools,
        connection_url=request.connection_url,
        metadata=request.metadata,
    )

    return RegisterServerResponse(
        server_id=result.server_id,
        registered_count=result.registered_count,
        rejected_count=result.rejected_count,
        registered_tools=[
            {
                "id": str(tool.id),
                "server_id": tool.server_id,
                "tool_name": tool.tool_name,
                "version": tool.version,
                "enabled": tool.enabled,
            }
            for tool in result.registered_tools
        ],
        rejected_tools=result.rejected_tools,
    )


@router.get("/tools", response_model=List[Dict[str, Any]])
async def list_tools(
    server_id: Optional[str] = Query(None, description="Filter by server ID"),
    enabled_only: bool = Query(True, description="Only return enabled tools"),
    registry: MCPRegistryService = Depends(get_mcp_registry),
) -> List[Dict[str, Any]]:
    """
    List registered tools.
    
    Args:
        server_id: Optional server filter
        enabled_only: Only return enabled tools
        registry: MCP registry service

    Returns:
        List of tool definitions
    """
    tools = registry.list_tools(server_id=server_id, enabled_only=enabled_only)
    return [
        {
            "id": str(tool.id),
            "server_id": tool.server_id,
            "tool_name": tool.tool_name,
            "schema": tool.schema,
            "version": tool.version,
            "enabled": tool.enabled,
            "registered_at": tool.registered_at.isoformat(),
        }
        for tool in tools
    ]


@router.get("/tools/{server_id}/{tool_name}", response_model=Dict[str, Any])
async def get_tool(
    server_id: str,
    tool_name: str,
    registry: MCPRegistryService = Depends(get_mcp_registry),
) -> Dict[str, Any]:
    """
    Get specific tool by server and name.
    
    Args:
        server_id: Server identifier
        tool_name: Tool name
        registry: MCP registry service

    Returns:
        Tool definition

    Raises:
        HTTPException: If tool not found
    """
    tool = registry.get_tool(server_id, tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {server_id}:{tool_name}")

    return {
        "id": str(tool.id),
        "server_id": tool.server_id,
        "tool_name": tool.tool_name,
        "schema": tool.schema,
        "version": tool.version,
        "enabled": tool.enabled,
        "registered_at": tool.registered_at.isoformat(),
    }


@router.post("/invoke", response_model=InvokeToolResponse)
async def invoke_tool(
    request: InvokeToolRequest,
    integration: MCPIntegrationService = Depends(get_mcp_integration),
) -> InvokeToolResponse:
    """
    Invoke MCP tool with full orchestration.
    
    REQ-MCP-CALL-001: Structured Request
    REQ-MCP-CALL-002: Retry with Backoff
    REQ-MCP-CALL-003: Idempotency
    REQ-MCP-CALL-004: Fallbacks
    REQ-MCP-CALL-005: Circuit Breaker
    """
    invocation_request = MCPInvocationRequest(
        correlation_id=request.correlation_id or f"req-{uuid.uuid4()}",
        agent_id=request.agent_id,
        server_id=request.server_id,
        tool_name=request.tool_name,
        params=request.params,
        idempotency_key=request.idempotency_key,
        ticket_id=request.ticket_id,
        task_id=request.task_id,
    )

    result = await integration.invoke_tool(invocation_request)

    return InvokeToolResponse(
        correlation_id=result.correlation_id,
        success=result.success,
        result=result.result,
        error=result.error,
        attempts=result.attempts,
        latency_ms=result.latency_ms,
        completed_at=result.completed_at.isoformat(),
    )


@router.post("/policies/grant", response_model=GrantPermissionResponse)
async def grant_permission(
    request: GrantPermissionRequest,
    authorization: MCPAuthorizationService = Depends(get_mcp_authorization),
) -> GrantPermissionResponse:
    """
    Grant tool permission to agent.
    
    REQ-MCP-AUTH-001: Agent-Scoped Permissions
    REQ-MCP-AUTH-003: Least Privilege
    """
    expires_at = None
    if request.expires_at:
        expires_at = datetime.fromisoformat(request.expires_at.replace("Z", "+00:00"))

    grant = authorization.grant_permission(
        agent_id=request.agent_id,
        server_id=request.server_id,
        tool_name=request.tool_name,
        actions=request.actions,
        granted_by=request.granted_by,
        expires_at=expires_at,
    )

    return GrantPermissionResponse(
        agent_id=grant.agent_id,
        server_id=grant.server_id,
        tool_name=grant.tool_name,
        actions=grant.actions,
        token_id=grant.token_id,
    )


@router.get("/policies/{agent_id}", response_model=List[Dict[str, Any]])
async def list_agent_permissions(
    agent_id: str,
    authorization: MCPAuthorizationService = Depends(get_mcp_authorization),
) -> List[Dict[str, Any]]:
    """
    List all permissions for an agent.
    
    Args:
        agent_id: Agent identifier
        authorization: MCP authorization service

    Returns:
        List of permission grants
    """
    permissions = authorization.list_agent_permissions(agent_id)
    return [
        {
            "agent_id": p.agent_id,
            "server_id": p.server_id,
            "tool_name": p.tool_name,
            "actions": p.actions,
            "token_id": p.token_id,
        }
        for p in permissions
    ]


@router.delete("/policies/{agent_id}/{server_id}/{tool_name}")
async def revoke_permission(
    agent_id: str,
    server_id: str,
    tool_name: str,
    authorization: MCPAuthorizationService = Depends(get_mcp_authorization),
) -> Dict[str, str]:
    """
    Revoke tool permission for agent.
    
    Args:
        agent_id: Agent identifier
        server_id: Server identifier
        tool_name: Tool name
        authorization: MCP authorization service

    Returns:
        Success message
    """
    authorization.revoke_permission(agent_id, server_id, tool_name)
    return {"message": "Permission revoked successfully"}


@router.get("/circuit-breakers", response_model=List[Dict[str, Any]])
async def get_circuit_breakers(
    server_id: Optional[str] = Query(None, description="Filter by server ID"),
    tool_name: Optional[str] = Query(None, description="Filter by tool name"),
    integration: MCPIntegrationService = Depends(get_mcp_integration),
) -> List[Dict[str, Any]]:
    """
    Get circuit breaker states.
    
    REQ-MCP-CALL-005: Circuit Breaker
    
    Args:
        server_id: Optional server filter
        tool_name: Optional tool filter
        integration: MCP integration service

    Returns:
        List of circuit breaker metrics
    """
    return integration.get_circuit_breaker_metrics(server_id=server_id, tool_name=tool_name)


@router.get("/servers", response_model=List[Dict[str, Any]])
async def list_servers(
    status: Optional[str] = Query(None, description="Filter by status"),
    registry: MCPRegistryService = Depends(get_mcp_registry),
) -> List[Dict[str, Any]]:
    """
    List registered MCP servers.
    
    Args:
        status: Optional status filter
        registry: MCP registry service

    Returns:
        List of server definitions
    """
    servers = registry.list_servers(status=status)
    return [
        {
            "server_id": s.server_id,
            "version": s.version,
            "capabilities": s.capabilities,
            "connected_at": s.connected_at.isoformat(),
            "last_heartbeat": s.last_heartbeat.isoformat() if s.last_heartbeat else None,
            "status": s.status,
            "connection_url": s.connection_url,
            "metadata": s.server_metadata,
        }
        for s in servers
    ]

