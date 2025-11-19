# FastMCP Server Integration Guide

This guide explains how to use and test the FastMCP server integrated with OmoiOS.

## Overview

The FastMCP server provides MCP tools for agents to interact with the OmoiOS system, including:
- **Ticket Management**: Create, update, search tickets
- **Task Management**: Create tasks with automatic discovery tracking
- **Discovery Tools**: Query discovery history and workflow graphs

## Server Location

The FastMCP server is mounted at `/mcp` on the FastAPI application:
- **URL**: `http://localhost:18000/mcp` (or your configured API port)
- **Protocol**: HTTP/SSE (Server-Sent Events)

## Available Tools

### Ticket Management Tools

1. **`create_ticket`** - Create a new ticket
2. **`update_ticket`** - Update ticket fields
3. **`change_ticket_status`** - Change ticket status with commit linkage
4. **`search_tickets`** - Search tickets (semantic, keyword, or hybrid)

### Task Management Tools

1. **`create_task`** - Create a new task (with optional discovery tracking)
2. **`update_task_status`** - Update task status and result
3. **`get_task`** - Get task details

### Discovery Tools

1. **`get_task_discoveries`** - Get all discoveries made by a task
2. **`get_workflow_graph`** - Build workflow graph showing discoveries and branches

## Testing with FastMCP Client

### Quick Test Script

Run the test script to verify the server is working:

```bash
# Start the API server first
uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 18000 --reload

# In another terminal, run the test script
uv run python scripts/test_fastmcp_server.py
```

### Using FastMCP Client in Python

```python
import asyncio
from fastmcp import Client

async def test_mcp_server():
    async with Client("http://localhost:18000/mcp") as client:
        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {[t.name for t in tools]}")
        
        # Create a ticket
        result = await client.call_tool(
            "create_ticket",
            {
                "workflow_id": "workflow-001",
                "agent_id": "agent-001",
                "title": "Test Ticket",
                "description": "Testing FastMCP integration",
                "priority": "medium",
            }
        )
        print(f"Ticket created: {result.data}")

asyncio.run(test_mcp_server())
```

### Testing with Pytest

```bash
# Run FastMCP server tests
uv run pytest tests/test_fastmcp_server.py -v
```

## Connecting OpenHands Agents

OpenHands agents can connect to the FastMCP server via MCP protocol. There are two approaches:

### Approach 1: HTTP MCP Server (Recommended)

Configure agents to connect to the HTTP endpoint:

```python
from openhands.sdk import Agent, LLM, Conversation

llm = LLM(model="openhands/claude-sonnet-4-5-20250929", api_key=os.getenv("LLM_API_KEY"))

# Configure MCP connection
mcp_config = {
    "mcpServers": {
        "omoi-os": {
            "command": "npx",
            "args": [
                "-y",
                "mcp-remote",
                "http://localhost:18000/mcp"
            ]
        }
    }
}

agent = Agent(
    llm=llm,
    mcp_config=mcp_config,
    cli_mode=True,
)

conversation = Conversation(
    agent=agent,
    workspace="./workspace",
)

# Agent can now use tools like create_ticket, create_task, etc.
conversation.send_message("Create a ticket for implementing user authentication")
conversation.run()
```

### Approach 2: Direct Tool Registration (Legacy)

For backward compatibility, the old OpenHands tool registration still works:

```python
from omoi_os.ticketing.mcp_tools import register_hephaestus_mcp_tools

# Register tools (happens automatically in worker)
register_hephaestus_mcp_tools()
```

## Discovery-Based Task Creation

The `create_task` tool automatically tracks discoveries when provided with discovery metadata:

```python
# Create a task that branches from another task
result = await client.call_tool(
    "create_task",
    {
        "ticket_id": "ticket-123",
        "phase_id": "PHASE_IMPLEMENTATION",
        "description": "Fix memory leak in authentication",
        "task_type": "bug_fix",
        "priority": "HIGH",
        # Discovery tracking parameters
        "discovery_type": "bug",
        "discovery_description": "Found memory leak during code review",
        "source_task_id": "task-456",  # Task that discovered this
        "priority_boost": True,  # Boost priority based on discovery
    }
)

# Result includes both task and discovery information
print(f"Task ID: {result.data['task_id']}")
print(f"Discovery ID: {result.data['discovery']['discovery_id']}")
```

This automatically:
1. Creates the task via `TaskQueueService`
2. Records the discovery via `DiscoveryService.record_discovery_and_branch()`
3. Links the spawned task to the discovery
4. Publishes events for real-time dashboard updates

## Workflow Graph Visualization

Query the workflow graph to see how tasks branch based on discoveries:

```python
result = await client.call_tool(
    "get_workflow_graph",
    {
        "ticket_id": "ticket-123",
    }
)

graph = result.data
print(f"Workflow has {len(graph['nodes'])} tasks")
print(f"With {len(graph['edges'])} discovery-based branches")

for edge in graph['edges']:
    print(f"Task {edge['from']} discovered {edge['discovery_type']} → spawned {edge['to']}")
```

## Error Handling

The FastMCP server handles errors gracefully:

- **Missing services**: Raises `RuntimeError` if services aren't initialized
- **Invalid parameters**: FastMCP validates parameters using Pydantic
- **Database errors**: Caught and returned as error responses
- **Tool execution errors**: Logged via `Context` and returned to client

## Testing Checklist

- [ ] Server starts and mounts at `/mcp`
- [ ] Tools are listed correctly
- [ ] `create_ticket` creates tickets in database
- [ ] `create_task` creates tasks in database
- [ ] `create_task` with discovery tracks discoveries
- [ ] `get_task_discoveries` returns discovery history
- [ ] `get_workflow_graph` builds correct graph structure
- [ ] Events are published to EventBus
- [ ] OpenHands agents can connect via MCP protocol

## Troubleshooting

### Server Not Responding

1. Check API server is running: `curl http://localhost:18000/health`
2. Check MCP endpoint: `curl http://localhost:18000/mcp`
3. Verify services are initialized in `lifespan()`

### Tools Not Available

1. Verify `initialize_mcp_services()` is called in `lifespan()`
2. Check database connection is working
3. Verify services are properly injected

### Discovery Tracking Not Working

1. Ensure `source_task_id` exists in database
2. Check `DiscoveryService` is initialized with `EventBusService`
3. Verify task is created before discovery is recorded

## Next Steps

- [ ] Add authentication/authorization for MCP tools
- [ ] Add rate limiting for tool calls
- [ ] Add tool usage metrics
- [ ] Create OpenHands agent configuration examples
- [ ] Add integration tests with real database

