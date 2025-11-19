"""MCP Integration Service - orchestrates tool invocations with full protection."""

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from omoi_os.models.mcp_server import MCPInvocation
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.mcp_authorization import (
    AuthorizationError,
    MCPAuthorizationService,
    PolicyDecision,
)
from omoi_os.services.mcp_circuit_breaker import (
    CircuitOpenError,
    MCPCircuitBreaker,
)
from omoi_os.services.mcp_registry import MCPRegistryService
from omoi_os.services.mcp_retry import (
    MCPRetryManager,
    RetryExhaustedError,
    TransientError,
)
from omoi_os.utils.datetime import utc_now


class ToolNotFoundError(Exception):
    """Tool not found in registry."""

    pass


class ToolDisabledError(Exception):
    """Tool exists but is disabled."""

    pass


class ToolInvocationError(Exception):
    """Tool invocation failed."""

    pass


class MCPInvocationRequest:
    """Request for MCP tool invocation."""

    def __init__(
        self,
        correlation_id: str,
        agent_id: str,
        server_id: str,
        tool_name: str,
        params: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        ticket_id: Optional[str] = None,
        task_id: Optional[str] = None,
        requested_at: Optional[datetime] = None,
    ):
        self.correlation_id = correlation_id
        self.agent_id = agent_id
        self.server_id = server_id
        self.tool_name = tool_name
        self.params = params
        self.idempotency_key = idempotency_key
        self.ticket_id = ticket_id
        self.task_id = task_id
        self.requested_at = requested_at or utc_now()


class MCPInvocationResult:
    """Result of MCP tool invocation."""

    def __init__(
        self,
        correlation_id: str,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
        attempts: int = 1,
        latency_ms: float = 0.0,
        completed_at: Optional[datetime] = None,
    ):
        self.correlation_id = correlation_id
        self.success = success
        self.result = result
        self.error = error
        self.attempts = attempts
        self.latency_ms = latency_ms
        self.completed_at = completed_at or utc_now()


class MCPIntegrationService:
    """
    Central service for MCP tool invocations.
    
    REQ-MCP-CALL-001: Structured Request
    REQ-MCP-CALL-004: Fallbacks
    """

    def __init__(
        self,
        db: DatabaseService,
        registry: MCPRegistryService,
        authorization: MCPAuthorizationService,
        retry_manager: MCPRetryManager,
        event_bus: Optional[EventBusService] = None,
        fallback_config: Optional[Dict[str, list[str]]] = None,
    ):
        """
        Initialize MCP integration service.

        Args:
            db: DatabaseService instance
            registry: MCPRegistryService instance
            authorization: MCPAuthorizationService instance
            retry_manager: MCPRetryManager instance
            event_bus: Optional EventBusService for event publishing
            fallback_config: Optional fallback configuration (tool_key -> [fallback_keys])
        """
        self.db = db
        self.registry = registry
        self.authorization = authorization
        self.retry_manager = retry_manager
        self.event_bus = event_bus
        self.fallback_config = fallback_config or {}
        self.circuit_breakers: Dict[str, MCPCircuitBreaker] = {}  # circuit_key -> breaker

    async def invoke_tool(self, request: MCPInvocationRequest) -> MCPInvocationResult:
        """
        Invoke MCP tool with full orchestration.
        
        Flow:
        1. Validate request structure
        2. Get tool from registry
        3. Authorize agent
        4. Execute with circuit breaker + retry
        5. Handle fallbacks if needed
        6. Record telemetry

        Args:
            request: MCPInvocationRequest

        Returns:
            MCPInvocationResult
        """
        start_time = utc_now()
        correlation_id = request.correlation_id
        attempts = 0
        policy_decision = None
        cached_decision = False

        try:
            # 1. Get tool
            tool = self.registry.get_tool(request.server_id, request.tool_name)
            if not tool:
                raise ToolNotFoundError(
                    f"Tool not found: {request.server_id}:{request.tool_name}"
                )

            if not tool.enabled:
                raise ToolDisabledError(
                    f"Tool disabled: {request.server_id}:{request.tool_name}"
                )

            # 2. Authorize
            require_token = self._requires_token(tool)
            auth_result = self.authorization.authorize(
                agent_id=request.agent_id,
                server_id=request.server_id,
                tool_name=request.tool_name,
                require_token=require_token,
            )

            policy_decision = auth_result.decision.value
            cached_decision = auth_result.cached

            if auth_result.decision != PolicyDecision.ALLOW:
                raise AuthorizationError(
                    f"Authorization denied: {auth_result.reason}",
                )

            # 3. Get circuit breaker
            circuit_key = f"{request.server_id}:{request.tool_name}"
            if circuit_key not in self.circuit_breakers:
                self.circuit_breakers[circuit_key] = MCPCircuitBreaker(
                    circuit_key=circuit_key, db=self.db
                )
            circuit_breaker = self.circuit_breakers[circuit_key]

            # 4. Execute with circuit breaker + retry
            last_error = None

            async def invoke():
                nonlocal attempts, last_error
                attempts += 1
                try:
                    return await circuit_breaker.call(
                        self._call_mcp_server,
                        request.server_id,
                        request.tool_name,
                        request.params,
                    )
                except Exception as e:
                    last_error = e
                    # Classify error as transient or permanent
                    if self._is_transient_error(e):
                        raise TransientError(str(e)) from e
                    raise

            try:
                result = await self.retry_manager.execute_with_retry(
                    invoke, idempotency_key=request.idempotency_key
                )

                latency_ms = (utc_now() - start_time).total_seconds() * 1000

                # Record successful invocation
                await self._record_invocation(
                    request=request,
                    success=True,
                    result=result,
                    attempts=attempts,
                    latency_ms=latency_ms,
                    policy_decision=policy_decision,
                    cached_decision=cached_decision,
                )

                # Publish event
                if self.event_bus:
                    self.event_bus.publish(
                        SystemEvent(
                            event_type="MCP_INVOCATION_COMPLETED",
                            entity_type="mcp_tool",
                            entity_id=f"{request.server_id}:{request.tool_name}",
                            payload={
                                "correlation_id": correlation_id,
                                "agent_id": request.agent_id,
                                "success": True,
                                "latency_ms": latency_ms,
                                "attempts": attempts,
                            },
                        )
                    )

                return MCPInvocationResult(
                    correlation_id=correlation_id,
                    success=True,
                    result=result,
                    attempts=attempts,
                    latency_ms=latency_ms,
                )

            except (RetryExhaustedError, CircuitOpenError) as e:
                last_error = e

                # 5. Try fallback
                fallback_result = await self._try_fallback(
                    request.server_id, request.tool_name, request.params
                )

                if fallback_result:
                    latency_ms = (utc_now() - start_time).total_seconds() * 1000

                    await self._record_invocation(
                        request=request,
                        success=True,
                        result=fallback_result,
                        attempts=attempts,
                        latency_ms=latency_ms,
                        policy_decision=policy_decision,
                        cached_decision=cached_decision,
                    )

                    return MCPInvocationResult(
                        correlation_id=correlation_id,
                        success=True,
                        result=fallback_result,
                        attempts=attempts,
                        latency_ms=latency_ms,
                    )
                else:
                    # Escalate
                    raise ToolInvocationError(
                        f"Tool invocation failed after retries and fallback: {str(last_error)}"
                    ) from last_error

        except Exception as e:
            latency_ms = (utc_now() - start_time).total_seconds() * 1000

            # 6. Record failed invocation
            await self._record_invocation(
                request=request,
                success=False,
                error=str(e),
                attempts=attempts,
                latency_ms=latency_ms,
                policy_decision=policy_decision,
                cached_decision=cached_decision,
            )

            # Publish event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="MCP_INVOCATION_FAILED",
                        entity_type="mcp_tool",
                        entity_id=f"{request.server_id}:{request.tool_name}",
                        payload={
                            "correlation_id": correlation_id,
                            "agent_id": request.agent_id,
                            "error": str(e),
                            "attempts": attempts,
                        },
                    )
                )

            return MCPInvocationResult(
                correlation_id=correlation_id,
                success=False,
                error=str(e),
                attempts=attempts,
                latency_ms=latency_ms,
            )

    async def _call_mcp_server(
        self, server_id: str, tool_name: str, params: Dict[str, Any]
    ) -> Any:
        """
        Direct call to MCP server using FastMCP Client (wrapped by circuit breaker).

        Args:
            server_id: Server identifier
            tool_name: Tool name
            params: Tool parameters

        Returns:
            Tool result

        Raises:
            Exception: If invocation fails
        """
        from fastmcp import Client

        # Get server connection info
        server = self.registry.get_server(server_id)
        if not server:
            raise ToolNotFoundError(f"Server not found: {server_id}")

        if not server.connection_url:
            raise ValueError(f"Server {server_id} has no connection URL configured")

        # Create FastMCP client
        # Client can handle:
        # - HTTP URLs: "https://example.com/mcp"
        # - Local file paths: "/path/to/server.py"
        # - In-memory servers: FastMCP instance
        client = Client(server.connection_url, timeout=30.0)

        try:
            # Use async context manager to ensure proper connection handling
            async with client:
                # Call the tool
                result = await client.call_tool(name=tool_name, arguments=params)
                return result
        except Exception as e:
            # Re-raise with more context
            raise Exception(
                f"Failed to invoke tool {tool_name} on server {server_id}: {str(e)}"
            ) from e

    def _requires_token(self, tool) -> bool:
        """
        Check if tool requires token-based authorization.

        Args:
            tool: MCPTool object

        Returns:
            True if token required, False otherwise
        """
        return self.authorization._is_high_risk_tool(tool.server_id, tool.tool_name)

    def _is_transient_error(self, error: Exception) -> bool:
        """
        Classify error as transient (retryable) or permanent.

        Args:
            error: Exception to classify

        Returns:
            True if transient, False if permanent
        """
        error_str = str(error).lower()
        transient_patterns = [
            "timeout",
            "connection",
            "network",
            "temporary",
            "unavailable",
            "rate limit",
        ]
        return any(pattern in error_str for pattern in transient_patterns)

    async def _try_fallback(
        self, server_id: str, tool_name: str, params: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Try fallback servers/tools in order.

        Args:
            server_id: Primary server ID
            tool_name: Primary tool name
            params: Tool parameters

        Returns:
            Fallback result or None if no fallback available
        """
        tool_key = f"{server_id}:{tool_name}"
        fallback_keys = self.fallback_config.get(tool_key, [])

        for fallback_key in fallback_keys:
            try:
                fallback_server_id, fallback_tool_name = fallback_key.split(":", 1)

                # Check if fallback tool exists and is enabled
                fallback_tool = self.registry.get_tool(fallback_server_id, fallback_tool_name)
                if not fallback_tool or not fallback_tool.enabled:
                    continue

                # Attempt fallback invocation (without retry/circuit breaker)
                result = await self._call_mcp_server(
                    fallback_server_id, fallback_tool_name, params
                )
                return result
            except Exception:
                # Continue to next fallback
                continue

        return None

    async def _record_invocation(
        self,
        request: MCPInvocationRequest,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
        attempts: int = 1,
        latency_ms: float = 0.0,
        policy_decision: Optional[str] = None,
        cached_decision: bool = False,
    ) -> None:
        """
        Record invocation in audit log.

        Args:
            request: Invocation request
            success: Whether invocation succeeded
            result: Invocation result (for successful calls)
            error: Error message (for failed calls)
            attempts: Number of attempts
            latency_ms: Latency in milliseconds
            policy_decision: Authorization decision
            cached_decision: Whether decision was cached
        """
        # Calculate params hash (redacted)
        params_hash = None
        if request.params:
            redacted_params = self._redact_params(request.params)
            params_hash = hashlib.sha256(
                json.dumps(redacted_params, sort_keys=True).encode()
            ).hexdigest()

        # Redact result for audit
        result_summary = None
        if result:
            result_summary = self._summarize_result(result)

        with self.db.get_session() as session:
            invocation = MCPInvocation(
                correlation_id=request.correlation_id,
                agent_id=request.agent_id,
                server_id=request.server_id,
                tool_name=request.tool_name,
                params_hash=params_hash,
                success=success,
                result_summary=result_summary,
                error_message=error,
                attempts=attempts,
                latency_ms=latency_ms,
                policy_decision=policy_decision,
                cached_decision=cached_decision,
            )
            session.add(invocation)
            session.commit()

    def _redact_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive parameters for audit.

        Args:
            params: Parameters dict

        Returns:
            Redacted parameters dict
        """
        sensitive_keys = ["password", "token", "secret", "key", "credential", "api_key"]
        redacted = params.copy()

        for key in redacted:
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                redacted[key] = "[REDACTED]"

        return redacted

    def _summarize_result(self, result: Any) -> str:
        """
        Create summary of result for audit (redacted).

        Args:
            result: Result object

        Returns:
            Summary string (max 500 chars)
        """
        if isinstance(result, dict):
            summary = json.dumps(result, default=str)[:500]
            return summary
        return str(result)[:500]

    def get_circuit_breaker_metrics(
        self, server_id: Optional[str] = None, tool_name: Optional[str] = None
    ) -> list[Dict[str, Any]]:
        """
        Get circuit breaker metrics.

        Args:
            server_id: Optional server filter
            tool_name: Optional tool filter

        Returns:
            List of circuit breaker metrics
        """
        metrics = []
        for circuit_key, breaker in self.circuit_breakers.items():
            if ":" not in circuit_key:
                continue

            cb_server_id, cb_tool_name = circuit_key.split(":", 1)

            if server_id and cb_server_id != server_id:
                continue
            if tool_name and cb_tool_name != tool_name:
                continue

            cb_metrics = breaker.get_metrics()
            metrics.append(
                {
                    "circuit_key": circuit_key,
                    "server_id": cb_server_id,
                    "tool_name": cb_tool_name,
                    "state": cb_metrics.state.value,
                    "failure_count": cb_metrics.failure_count,
                    "last_failure_time": (
                        cb_metrics.last_failure_time.isoformat()
                        if cb_metrics.last_failure_time
                        else None
                    ),
                    "opened_at": (
                        cb_metrics.opened_at.isoformat() if cb_metrics.opened_at else None
                    ),
                }
            )

        return metrics

