"""MCP Server models for tool registry and server management."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from omoi_os.models.base import Base
from omoi_os.utils.datetime import utc_now


class MCPServer(Base):
    """MCP Server registry entry per REQ-MCP-REG-001."""

    __tablename__ = "mcp_servers"

    server_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    capabilities: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    connection_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="MCP server connection URL or path (HTTP URL or local file path)"
    )
    server_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="Additional server metadata"
    )

    # Relationships
    tools: Mapped[List["MCPTool"]] = relationship("MCPTool", back_populates="server", cascade="all, delete-orphan")


class MCPTool(Base):
    """MCP Tool registry entry per REQ-MCP-REG-002."""

    __tablename__ = "mcp_tools"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    server_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("mcp_servers.server_id", ondelete="CASCADE"), nullable=False, index=True
    )
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    schema: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, comment="JSON Schema for tool")
    version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    # Relationships
    server: Mapped["MCPServer"] = relationship("MCPServer", back_populates="tools")

    __table_args__ = (UniqueConstraint("server_id", "tool_name", name="uq_mcp_tools_server_tool"),)


class MCPPolicy(Base):
    """Authorization policy for agent-tool access per REQ-MCP-AUTH-001."""

    __tablename__ = "mcp_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    server_id: Mapped[str] = mapped_column(String(255), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    actions: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    granted_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (UniqueConstraint("agent_id", "server_id", "tool_name", name="uq_mcp_policies_agent_tool"),)


class MCPToken(Base):
    """Time-bounded authorization token per REQ-MCP-AUTH-003."""

    __tablename__ = "mcp_tokens"

    token_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    server_id: Mapped[str] = mapped_column(String(255), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)


class CircuitBreakerState(Base):
    """Circuit breaker state per server+tool per REQ-MCP-CALL-005."""

    __tablename__ = "circuit_breakers"

    circuit_key: Mapped[str] = mapped_column(String(255), primary_key=True, comment="server_id:tool_name")
    state: Mapped[str] = mapped_column(String(20), nullable=False, comment="CLOSED, OPEN, HALF_OPEN")
    failure_count: Mapped[int] = mapped_column(default=0)
    last_failure_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    success_count: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class MCPInvocation(Base):
    """Audit log for MCP tool invocations per REQ-MCP-OBS-002."""

    __tablename__ = "mcp_invocations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    correlation_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    server_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    params_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="SHA256 hash of params (redacted)"
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Redacted result")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(default=1)
    latency_ms: Mapped[Optional[float]] = mapped_column(nullable=True)
    policy_decision: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="ALLOW/DENY")
    cached_decision: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    invoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)

