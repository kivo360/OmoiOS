# Part 9: MCP Integration

> Summary doc — see linked design docs for full details.

## Overview

OmoiOS integrates with **Model Context Protocol (MCP)** servers to extend agent capabilities with external tools. The integration includes circuit breakers, retry logic, authorization enforcement, and tool discovery via vector search.

## Architecture

```
┌─────────────────────┐     ┌────────────────────────┐     ┌──────────────────┐
│  Agent (in sandbox) │────→│  MCPIntegrationService │────→│  MCP Server      │
│                     │     │                        │     │  (external)      │
│  Tool invocation    │     │  ┌──────────────────┐  │     └──────────────────┘
│                     │     │  │ Authorization    │  │
│                     │     │  │ Engine           │  │
│                     │     │  ├──────────────────┤  │
│                     │     │  │ Retry Manager    │  │
│                     │     │  ├──────────────────┤  │
│                     │     │  │ Circuit Breaker  │  │
│                     │     │  │ (per server+tool)│  │
│                     │     │  ├──────────────────┤  │
│                     │     │  │ Tool Registry    │  │
│                     │     │  └──────────────────┘  │
│                     │     └────────────────────────┘
└─────────────────────┘
```

## Key Components

### Tool Registry
- Catalogs all available MCP tools across servers
- PGVector-backed semantic search for tool discovery
- Duplicate detection via vector similarity (provider-agnostic)

### Authorization Engine
- Agent-scoped permissions with least-privilege
- Time-bounded tokens for high-risk tools
- Default-deny policy — tools must be explicitly allowed

### Retry Manager
- Exponential backoff: 3 attempts, 500ms base delay, 2x factor
- Idempotency tracking to prevent duplicate side effects
- Per-tool retry configuration

### Circuit Breaker
- Per server+tool granularity
- **Closed** → **Open** after 5 consecutive failures
- **Open** → **Half-Open** after 60-second cooldown
- **Half-Open** → **Closed** on success, back to **Open** on failure

## Observability

- Prometheus metrics: latency histograms, error counters, circuit breaker state
- Audit log for all tool invocations with parameter redaction
- Health dashboard per MCP server

## Key Files

| File | Purpose |
|------|---------|
| `backend/omoi_os/services/mcp_integration.py` | Core integration service with circuit breaker and retry |
| `backend/omoi_os/api/routes/mcp.py` | MCP API endpoints |
| `backend/omoi_os/models/mcp_server.py` | MCP server registration model |

## Detailed Documentation

| Document | Content |
|----------|---------|
| [MCP Server Integration](../design/integration/mcp_server_integration.md) | Full integration design (~1,577 lines) — authorization model, tool registry, retry patterns |
| [FastMCP Integration](../design/integration/fastmcp_integration.md) | FastMCP-specific implementation guide |
