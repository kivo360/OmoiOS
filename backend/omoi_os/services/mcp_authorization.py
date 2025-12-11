"""MCP Authorization Service for per-agent, per-tool authorization."""

import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from omoi_os.models.mcp_server import MCPPolicy, MCPToken
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now


class PolicyDecision(str, Enum):
    """Authorization decision."""

    ALLOW = "ALLOW"
    DENY = "DENY"


class AuthorizationError(Exception):
    """Authorization denied."""

    pass


class AuthorizationResult:
    """Result of authorization check."""

    def __init__(
        self,
        decision: PolicyDecision,
        cached: bool = False,
        reason: str = "",
        token_required: bool = False,
    ):
        self.decision = decision
        self.cached = cached
        self.reason = reason
        self.token_required = token_required


class PolicyGrant:
    """Policy grant for agent-tool access."""

    def __init__(
        self,
        agent_id: str,
        server_id: str,
        tool_name: str,
        actions: List[str],
        token_ttl: timedelta = timedelta(minutes=15),
        token_id: Optional[str] = None,
    ):
        self.agent_id = agent_id
        self.server_id = server_id
        self.tool_name = tool_name
        self.actions = actions
        self.token_ttl = token_ttl
        self.token_id = token_id


class MCPAuthorizationService:
    """
    Enforces agent-scoped permissions for tool invocations.
    
    REQ-MCP-AUTH-001: Agent-Scoped Permissions
    REQ-MCP-AUTH-002: Capability Binding
    REQ-MCP-AUTH-003: Least Privilege
    """

    def __init__(self, db: DatabaseService, cache_ttl: timedelta = timedelta(minutes=5)):
        """
        Initialize authorization service.

        Args:
            db: DatabaseService instance
            cache_ttl: Authorization decision cache TTL
        """
        self.db = db
        self.cache_ttl = cache_ttl
        self.decision_cache: Dict[str, tuple[PolicyDecision, datetime]] = {}  # cache_key -> (decision, timestamp)

    def authorize(
        self,
        agent_id: str,
        server_id: str,
        tool_name: str,
        require_token: bool = False,
    ) -> AuthorizationResult:
        """
        Authorize tool invocation for agent.
        
        Default-deny: Only explicit grants allow access.

        Args:
            agent_id: Agent identifier
            server_id: Server identifier
            tool_name: Tool name
            require_token: Whether token validation is required

        Returns:
            AuthorizationResult with decision and reason
        """
        tool_key = f"{server_id}:{tool_name}"
        cache_key = f"{agent_id}:{tool_key}"

        # Check cache first
        if cache_key in self.decision_cache:
            cached_decision, cached_time = self.decision_cache[cache_key]
            if (utc_now() - cached_time) < self.cache_ttl:
                return AuthorizationResult(
                    decision=cached_decision,
                    cached=True,
                    reason="Cached decision",
                    token_required=require_token,
                )
            else:
                # Cache expired
                del self.decision_cache[cache_key]

        # Default deny
        decision = PolicyDecision.DENY
        reason = "No explicit grant found"

        # Check agent policy
        with self.db.get_session() as session:
            policy = (
                session.query(MCPPolicy)
                .filter_by(agent_id=agent_id, server_id=server_id, tool_name=tool_name)
                .first()
            )

            if policy:
                # Check if policy expired
                if policy.expires_at and policy.expires_at < utc_now():
                    decision = PolicyDecision.DENY
                    reason = "Policy expired"
                else:
                    # Check if token required for high-risk tools
                    if require_token:
                        token_valid = self._validate_token(agent_id, server_id, tool_name)
                        if not token_valid:
                            decision = PolicyDecision.DENY
                            reason = "Token validation failed"
                        else:
                            decision = PolicyDecision.ALLOW
                            reason = "Authorized with valid token"
                    else:
                        decision = PolicyDecision.ALLOW
                        reason = "Authorized via policy grant"

        # Cache decision
        self.decision_cache[cache_key] = (decision, utc_now())

        return AuthorizationResult(
            decision=decision,
            cached=False,
            reason=reason,
            token_required=require_token,
        )

    def grant_permission(
        self,
        agent_id: str,
        server_id: str,
        tool_name: str,
        actions: List[str],
        granted_by: Optional[str] = None,
        token_ttl: timedelta = timedelta(minutes=15),
        expires_at: Optional[datetime] = None,
    ) -> PolicyGrant:
        """
        Grant tool permission to agent with optional time-bounded token.
        
        REQ-MCP-AUTH-003: Least Privilege - time-bounded tokens for high-risk tools

        Args:
            agent_id: Agent identifier
            server_id: Server identifier
            tool_name: Tool name
            actions: List of allowed actions
            granted_by: Optional identifier of who granted the permission
            token_ttl: Token TTL for high-risk tools
            expires_at: Optional policy expiration time

        Returns:
            PolicyGrant with token if required
        """
        with self.db.get_session() as session:
            # Create or update policy
            policy = (
                session.query(MCPPolicy)
                .filter_by(agent_id=agent_id, server_id=server_id, tool_name=tool_name)
                .first()
            )

            if policy:
                policy.actions = actions
                policy.granted_by = granted_by
                policy.expires_at = expires_at
            else:
                policy = MCPPolicy(
                    agent_id=agent_id,
                    server_id=server_id,
                    tool_name=tool_name,
                    actions=actions,
                    granted_by=granted_by,
                    expires_at=expires_at,
                )
                session.add(policy)

            session.commit()

        # Generate token if required (for high-risk tools)
        token_id = None
        if self._is_high_risk_tool(server_id, tool_name):
            token_id = self._generate_token(agent_id, server_id, tool_name, token_ttl)

        # Invalidate cache
        tool_key = f"{server_id}:{tool_name}"
        cache_key = f"{agent_id}:{tool_key}"
        self.decision_cache.pop(cache_key, None)

        return PolicyGrant(
            agent_id=agent_id,
            server_id=server_id,
            tool_name=tool_name,
            actions=actions,
            token_ttl=token_ttl,
            token_id=token_id,
        )

    def _generate_token(
        self, agent_id: str, server_id: str, tool_name: str, ttl: timedelta
    ) -> str:
        """
        Generate time-bounded authorization token.

        Args:
            agent_id: Agent identifier
            server_id: Server identifier
            tool_name: Tool name
            ttl: Token time-to-live

        Returns:
            Token ID string
        """
        token_id = secrets.token_urlsafe(32)
        expires_at = utc_now() + ttl

        with self.db.get_session() as session:
            token = MCPToken(
                token_id=token_id,
                agent_id=agent_id,
                server_id=server_id,
                tool_name=tool_name,
                expires_at=expires_at,
            )
            session.add(token)
            session.commit()

        return token_id

    def _validate_token(self, agent_id: str, server_id: str, tool_name: str) -> bool:
        """
        Validate token for agent and tool.

        Args:
            agent_id: Agent identifier
            server_id: Server identifier
            tool_name: Tool name

        Returns:
            True if valid token exists, False otherwise
        """
        with self.db.get_session() as session:
            token = (
                session.query(MCPToken)
                .filter_by(
                    agent_id=agent_id,
                    server_id=server_id,
                    tool_name=tool_name,
                    revoked=False,
                )
                .filter(MCPToken.expires_at > utc_now())
                .first()
            )
            return token is not None

    def _is_high_risk_tool(self, server_id: str, tool_name: str) -> bool:
        """
        Determine if tool requires token-based authorization.

        Args:
            server_id: Server identifier
            tool_name: Tool name

        Returns:
            True if high-risk, False otherwise
        """
        # High-risk patterns: write, delete, modify operations
        high_risk_patterns = ["write", "delete", "modify", "update", "create", "remove"]
        return any(pattern in tool_name.lower() for pattern in high_risk_patterns)

    def list_agent_permissions(self, agent_id: str) -> list[PolicyGrant]:
        """
        List all permissions for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            List of PolicyGrant objects
        """
        with self.db.get_session() as session:
            policies = session.query(MCPPolicy).filter_by(agent_id=agent_id).all()
            return [
                PolicyGrant(
                    agent_id=p.agent_id,
                    server_id=p.server_id,
                    tool_name=p.tool_name,
                    actions=p.actions,
                    token_id=None,  # Would need to look up token separately
                )
                for p in policies
                if not p.expires_at or p.expires_at > utc_now()
            ]

    def revoke_permission(
        self, agent_id: str, server_id: str, tool_name: str
    ) -> None:
        """
        Revoke tool permission for agent.

        Args:
            agent_id: Agent identifier
            server_id: Server identifier
            tool_name: Tool name
        """
        with self.db.get_session() as session:
            policy = (
                session.query(MCPPolicy)
                .filter_by(agent_id=agent_id, server_id=server_id, tool_name=tool_name)
                .first()
            )
            if policy:
                session.delete(policy)
                session.commit()

            # Revoke any active tokens
            tokens = (
                session.query(MCPToken)
                .filter_by(
                    agent_id=agent_id, server_id=server_id, tool_name=tool_name, revoked=False
                )
                .all()
            )
            for token in tokens:
                token.revoked = True
            session.commit()

        # Invalidate cache
        tool_key = f"{server_id}:{tool_name}"
        cache_key = f"{agent_id}:{tool_key}"
        self.decision_cache.pop(cache_key, None)

