"""MCP Server Integration (REQ-MCP-REG-001, REQ-MCP-AUTH-001, REQ-MCP-CALL-005)

Revision ID: 019_mcp_server_integration
Revises: 018_ace_workflow
Create Date: 2025-01-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "019_mcp_server_integration"
down_revision: Union[str, None] = "018_ace_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # MCP Servers table (REQ-MCP-REG-001)
    op.create_table(
        "mcp_servers",
        sa.Column("server_id", sa.String(255), primary_key=True),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column(
            "capabilities", postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column(
            "connection_url",
            sa.String(500),
            nullable=True,
            comment="MCP server connection URL or path (HTTP URL or local file path)",
        ),
        sa.Column(
            "server_metadata",
            postgresql.JSONB,
            nullable=True,
            comment="Additional server metadata",
        ),
        sa.Index("ix_mcp_servers_status", "status"),
    )

    # MCP Tools table (REQ-MCP-REG-002)
    op.create_table(
        "mcp_tools",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("server_id", sa.String(255), nullable=False),
        sa.Column("tool_name", sa.String(255), nullable=False),
        sa.Column(
            "schema", postgresql.JSONB, nullable=False, comment="JSON Schema for tool"
        ),
        sa.Column("version", sa.String(50), nullable=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["server_id"], ["mcp_servers.server_id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("server_id", "tool_name", name="uq_mcp_tools_server_tool"),
        sa.Index("ix_mcp_tools_server_id", "server_id"),
        sa.Index("ix_mcp_tools_enabled", "enabled"),
    )

    # MCP Policies table (REQ-MCP-AUTH-001)
    op.create_table(
        "mcp_policies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("agent_id", sa.String(255), nullable=False),
        sa.Column("server_id", sa.String(255), nullable=False),
        sa.Column("tool_name", sa.String(255), nullable=False),
        sa.Column("actions", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("granted_by", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "agent_id", "server_id", "tool_name", name="uq_mcp_policies_agent_tool"
        ),
        sa.Index("ix_mcp_policies_agent_id", "agent_id"),
        sa.Index("ix_mcp_policies_expires_at", "expires_at"),
    )

    # MCP Tokens table (REQ-MCP-AUTH-003)
    op.create_table(
        "mcp_tokens",
        sa.Column("token_id", sa.String(255), primary_key=True),
        sa.Column("agent_id", sa.String(255), nullable=False),
        sa.Column("server_id", sa.String(255), nullable=False),
        sa.Column("tool_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default="false"),
        sa.Index("ix_mcp_tokens_agent_id", "agent_id"),
        sa.Index("ix_mcp_tokens_expires_at", "expires_at"),
        sa.Index("ix_mcp_tokens_revoked", "revoked"),
    )

    # Circuit Breakers table (REQ-MCP-CALL-005)
    op.create_table(
        "circuit_breakers",
        sa.Column(
            "circuit_key",
            sa.String(255),
            primary_key=True,
            comment="server_id:tool_name",
        ),
        sa.Column(
            "state", sa.String(20), nullable=False, comment="CLOSED, OPEN, HALF_OPEN"
        ),
        sa.Column("failure_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_failure_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("success_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # MCP Invocations audit log (REQ-MCP-OBS-002)
    op.create_table(
        "mcp_invocations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("correlation_id", sa.String(255), nullable=False),
        sa.Column("agent_id", sa.String(255), nullable=False),
        sa.Column("server_id", sa.String(255), nullable=False),
        sa.Column("tool_name", sa.String(255), nullable=False),
        sa.Column(
            "params_hash",
            sa.String(64),
            nullable=True,
            comment="SHA256 hash of params (redacted)",
        ),
        sa.Column("success", sa.Boolean, nullable=False),
        sa.Column("result_summary", sa.Text, nullable=True, comment="Redacted result"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="1"),
        sa.Column("latency_ms", sa.Float, nullable=True),
        sa.Column(
            "policy_decision", sa.String(10), nullable=True, comment="ALLOW/DENY"
        ),
        sa.Column(
            "cached_decision", sa.Boolean, nullable=False, server_default="false"
        ),
        sa.Column("invoked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Index("ix_mcp_invocations_correlation_id", "correlation_id"),
        sa.Index("ix_mcp_invocations_agent_id", "agent_id"),
        sa.Index("ix_mcp_invocations_server_id", "server_id"),
        sa.Index("ix_mcp_invocations_tool_name", "tool_name"),
        sa.Index("ix_mcp_invocations_invoked_at", "invoked_at"),
    )


def downgrade() -> None:
    op.drop_table("mcp_invocations")
    op.drop_table("circuit_breakers")
    op.drop_table("mcp_tokens")
    op.drop_table("mcp_policies")
    op.drop_table("mcp_tools")
    op.drop_table("mcp_servers")
