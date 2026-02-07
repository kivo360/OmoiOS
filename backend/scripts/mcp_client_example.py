#!/usr/bin/env python3
"""Example script to call the MCP service programmatically.

Usage:
    uv run python scripts/mcp_client_example.py
"""

import asyncio
from fastmcp import Client


async def main():
    """Connect to MCP server and call tools."""

    # Connect to your local MCP server (note the trailing slash!)
    mcp_url = "http://localhost:18000/mcp/"

    print(f"Connecting to MCP server at {mcp_url}...")

    async with Client(mcp_url) as client:
        # List all available tools
        print("\n📋 Available Tools:")
        print("-" * 50)
        tools = await client.list_tools()
        for tool in tools:
            print(
                f"  • {tool.name}: {tool.description[:60]}..."
                if tool.description and len(tool.description) > 60
                else f"  • {tool.name}: {tool.description}"
            )

        print(f"\nTotal: {len(tools)} tools available")

        # Example: Call get_task tool (if you have a task ID)
        # Uncomment and modify with a real task_id to test:
        #
        # result = await client.call_tool("get_task", {
        #     "task_id": "your-task-uuid-here"
        # })
        # print(f"\nTask result: {result}")

        # Example: Create a ticket (requires valid workflow_id and agent_id)
        # Uncomment to test:
        #
        # result = await client.call_tool("create_ticket", {
        #     "workflow_id": "test-workflow",
        #     "agent_id": "test-agent",
        #     "title": "Test ticket from Python client",
        #     "description": "This ticket was created programmatically via MCP",
        #     "ticket_type": "task",
        #     "priority": "medium"
        # })
        # print(f"\nCreated ticket: {result}")


if __name__ == "__main__":
    asyncio.run(main())
