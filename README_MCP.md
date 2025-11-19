# FastMCP Server Testing Guide

## Quick Start

### 1. Start the API Server

```bash
# Start the FastAPI server (which includes the FastMCP server at /mcp)
uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 18000 --reload
```

### 2. Test with FastMCP Client

```bash
# Run the test script
uv run python scripts/test_fastmcp_server.py

# Or specify a custom URL
uv run python scripts/test_fastmcp_server.py --url http://localhost:18000/mcp
```

### 3. Run Pytest Tests

```bash
# Run FastMCP server tests
uv run pytest tests/test_fastmcp_server.py -v
```

## Testing Individual Tools

### Using Python Script

```python
import asyncio
from fastmcp import Client

async def test():
    async with Client("http://localhost:18000/mcp") as client:
        # List tools
        tools = await client.list_tools()
        print(f"Tools: {[t.name for t in tools]}")
        
        # Create ticket
        result = await client.call_tool("create_ticket", {
            "workflow_id": "test-001",
            "agent_id": "agent-001",
            "title": "Test",
            "description": "Test description",
        })
        print(result.data)

asyncio.run(test())
```

### Using curl (HTTP/SSE)

```bash
# List tools
curl -X POST http://localhost:18000/mcp \
  -H "Content-Type: application/json" \
  -H "Session-ID: test-123" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'

# Call a tool
curl -X POST http://localhost:18000/mcp \
  -H "Content-Type: application/json" \
  -H "Session-ID: test-123" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "create_ticket",
      "arguments": {
        "workflow_id": "test-001",
        "agent_id": "agent-001",
        "title": "Test Ticket",
        "description": "Test description"
      }
    },
    "id": 2
  }'
```

## Agent Configuration

Agents automatically connect to the FastMCP server when `ENABLE_MCP_TOOLS=true` (default).

To disable MCP tools:
```bash
export ENABLE_MCP_TOOLS=false
```

To use a different MCP server URL:
```bash
export MCP_SERVER_URL=http://localhost:18000/mcp
```

## Available Tools

See `docs/mcp/fastmcp_integration.md` for complete documentation.

