"""Test script for FastMCP server using FastMCP Client.

This script demonstrates how to:
1. Connect to the FastMCP server
2. List available tools
3. Call tools with various parameters
4. Test discovery-based task creation
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastmcp import Client
from omoi_os.config import get_app_settings


async def test_fastmcp_server():
    """Test the FastMCP server tools."""
    
    # Connect to the FastMCP server
    # Option 1: HTTP endpoint (when API server is running)
    mcp_url = get_app_settings().integrations.mcp_server_url
    
    print("=" * 80)
    print("FastMCP Server Test")
    print("=" * 80)
    print(f"Connecting to: {mcp_url}\n")
    
    async with Client(mcp_url, timeout=30.0) as client:
        # Test 1: List available tools
        print("1. Listing available tools...")
        try:
            tools = await client.list_tools()
            print(f"   ✅ Found {len(tools)} tools:")
            for tool in tools:
                print(f"      - {tool.name}: {tool.description or 'No description'}")
        except Exception as e:
            print(f"   ❌ Error listing tools: {e}")
            return
        
        print()
        
        # Test 2: Create a ticket
        print("2. Testing create_ticket tool...")
        try:
            result = await client.call_tool(
                "create_ticket",
                {
                    "workflow_id": "test-workflow-001",
                    "agent_id": "test-agent-001",
                    "title": "Test Ticket from FastMCP",
                    "description": "This is a test ticket created via FastMCP client",
                    "ticket_type": "task",
                    "priority": "medium",
                    "tags": ["test", "fastmcp"],
                }
            )
            print(f"   ✅ Ticket created successfully")
            if hasattr(result, 'data') and isinstance(result.data, dict):
                ticket_id = result.data.get("ticket_id")
                print(f"   Ticket ID: {ticket_id}")
                print(f"   Full result: {result.data}")
            else:
                print(f"   Result: {result}")
        except Exception as e:
            print(f"   ❌ Error creating ticket: {e}")
            import traceback
            traceback.print_exc()
        
        print()
        
        # Test 3: Search tickets
        print("3. Testing search_tickets tool...")
        try:
            result = await client.call_tool(
                "search_tickets",
                {
                    "workflow_id": "test-workflow-001",
                    "agent_id": "test-agent-001",
                    "query": "test",
                    "search_type": "hybrid",
                    "limit": 5,
                }
            )
            print(f"   ✅ Search completed")
            if hasattr(result, 'data') and isinstance(result.data, dict):
                tickets = result.data.get("tickets", [])
                print(f"   Found {len(tickets)} tickets")
            else:
                print(f"   Result: {result}")
        except Exception as e:
            print(f"   ❌ Error searching tickets: {e}")
        
        print()
        
        # Test 4: Create a task (without discovery)
        print("4. Testing create_task tool (without discovery)...")
        try:
            # First, we need a ticket_id - use the one from test 2 if available
            # For this test, we'll use a placeholder
            result = await client.call_tool(
                "create_task",
                {
                    "ticket_id": "00000000-0000-0000-0000-000000000001",  # Placeholder
                    "phase_id": "PHASE_IMPLEMENTATION",
                    "description": "Test task created via FastMCP - no discovery",
                    "task_type": "implementation",
                    "priority": "MEDIUM",
                }
            )
            print(f"   ✅ Task created successfully")
            if hasattr(result, 'data') and isinstance(result.data, dict):
                task_id = result.data.get("task_id")
                print(f"   Task ID: {task_id}")
                print(f"   Full result: {result.data}")
            else:
                print(f"   Result: {result}")
        except Exception as e:
            print(f"   ❌ Error creating task: {e}")
            print(f"   Note: This may fail if ticket_id doesn't exist")
        
        print()
        
        # Test 5: Create a task with discovery tracking
        print("5. Testing create_task tool (with discovery tracking)...")
        try:
            result = await client.call_tool(
                "create_task",
                {
                    "ticket_id": "00000000-0000-0000-0000-000000000001",  # Placeholder
                    "phase_id": "PHASE_IMPLEMENTATION",
                    "description": "Fix critical bug discovered during implementation",
                    "task_type": "bug_fix",
                    "priority": "HIGH",
                    "discovery_type": "bug",
                    "discovery_description": "Found a memory leak in the authentication module",
                    "source_task_id": "00000000-0000-0000-0000-000000000002",  # Placeholder
                    "priority_boost": True,
                }
            )
            print(f"   ✅ Task created with discovery tracking")
            if hasattr(result, 'data') and isinstance(result.data, dict):
                task_id = result.data.get("task_id")
                discovery = result.data.get("discovery")
                print(f"   Task ID: {task_id}")
                if discovery:
                    print(f"   Discovery ID: {discovery.get('discovery_id')}")
                    print(f"   Discovery Type: {discovery.get('discovery_type')}")
                    print(f"   Priority Boost: {discovery.get('priority_boost')}")
            else:
                print(f"   Result: {result}")
        except Exception as e:
            print(f"   ❌ Error creating task with discovery: {e}")
            print(f"   Note: This may fail if ticket_id or source_task_id don't exist")
        
        print()
        
        # Test 6: Get task discoveries
        print("6. Testing get_task_discoveries tool...")
        try:
            result = await client.call_tool(
                "get_task_discoveries",
                {
                    "task_id": "00000000-0000-0000-0000-000000000002",  # Placeholder
                }
            )
            print(f"   ✅ Retrieved discoveries")
            if hasattr(result, 'data') and isinstance(result.data, dict):
                discoveries = result.data.get("discoveries", [])
                print(f"   Found {len(discoveries)} discoveries")
                for disc in discoveries:
                    print(f"      - {disc.get('discovery_type')}: {disc.get('description')[:50]}")
            else:
                print(f"   Result: {result}")
        except Exception as e:
            print(f"   ❌ Error getting discoveries: {e}")
        
        print()
        
        # Test 7: Get workflow graph
        print("7. Testing get_workflow_graph tool...")
        try:
            result = await client.call_tool(
                "get_workflow_graph",
                {
                    "ticket_id": "00000000-0000-0000-0000-000000000001",  # Placeholder
                }
            )
            print(f"   ✅ Retrieved workflow graph")
            if hasattr(result, 'data') and isinstance(result.data, dict):
                nodes = result.data.get("nodes", [])
                edges = result.data.get("edges", [])
                print(f"   Graph has {len(nodes)} nodes and {len(edges)} edges")
            else:
                print(f"   Result: {result}")
        except Exception as e:
            print(f"   ❌ Error getting workflow graph: {e}")
        
        print()
        print("=" * 80)
        print("Test Complete!")
        print("=" * 80)


async def test_in_memory_server():
    """Test FastMCP server in-memory (for unit testing).
    
    This is useful for pytest tests where you don't want to start the full API server.
    """
    print("=" * 80)
    print("In-Memory FastMCP Server Test")
    print("=" * 80)
    
    # Import the server instance directly
    from omoi_os.mcp.fastmcp_server import mcp
    
    # Initialize services with test/mock services
    # Note: In real tests, you'd use mocks or test database
    print("Note: In-memory testing requires initialized services")
    print("For full testing, use the HTTP endpoint test instead")
    
    # Example of how to use in-memory client:
    # async with Client(mcp) as client:
    #     tools = await client.list_tools()
    #     print(f"Found {len(tools)} tools")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test FastMCP server")
    parser.add_argument(
        "--in-memory",
        action="store_true",
        help="Test using in-memory server (requires service initialization)",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="MCP server URL (default: http://localhost:18000/mcp)",
    )
    
    args = parser.parse_args()
    
    if args.url:
        os.environ["MCP_SERVER_URL"] = args.url
    
    if args.in_memory:
        asyncio.run(test_in_memory_server())
    else:
        asyncio.run(test_fastmcp_server())

