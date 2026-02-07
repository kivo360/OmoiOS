#!/usr/bin/env python3
"""Quick MCP server test using FastMCP patterns.

Usage:
    # In-memory test (no server needed):
    python scripts/test_mcp_quick.py --in-memory

    # Live server test (requires API to be running):
    python scripts/test_mcp_quick.py --live

    # HTTP transport test (spins up server in-process):
    python scripts/test_mcp_quick.py --http
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_in_memory():
    """Test MCP server in-memory (fastest, no network)."""
    print("=" * 60)
    print("🧪 In-Memory MCP Test")
    print("=" * 60)

    from fastmcp import Client

    # Import the mcp server instance directly
    from omoi_os.mcp.fastmcp_server import mcp

    # Initialize with mock/test services
    # Note: Some tools will fail without real services, but we can list tools
    print("\n⚠️  Note: Services not initialized - some tool calls may fail")
    print("   This test verifies tool registration, not full functionality.\n")

    async with Client(mcp) as client:
        # Test 1: List tools
        print("1. Listing registered tools...")
        try:
            tools = await client.list_tools()
            print(f"   ✅ Found {len(tools)} tools:")
            for tool in tools:
                desc = (tool.description or "No description")[:50]
                print(f"      • {tool.name}: {desc}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False

        # Test 2: Ping
        print("\n2. Pinging server...")
        try:
            result = await client.ping()
            print(f"   ✅ Ping result: {result}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n" + "=" * 60)
    print("✅ In-Memory Test Complete!")
    print("=" * 60)
    return True


async def test_live_server():
    """Test against live running server."""
    print("=" * 60)
    print("🧪 Live Server MCP Test")
    print("=" * 60)

    from fastmcp import Client
    from omoi_os.config import get_app_settings

    mcp_url = get_app_settings().integrations.mcp_server_url
    print(f"\nConnecting to: {mcp_url}\n")

    try:
        async with Client(mcp_url, timeout=10.0) as client:
            # Test 1: Ping
            print("1. Pinging server...")
            try:
                result = await client.ping()
                print(f"   ✅ Ping result: {result}")
            except Exception as e:
                print(f"   ❌ Ping failed: {e}")
                print("   Is the API server running? Try: just backend-dev")
                return False

            # Test 2: List tools
            print("\n2. Listing tools...")
            try:
                tools = await client.list_tools()
                print(f"   ✅ Found {len(tools)} tools:")
                for tool in tools:
                    desc = (tool.description or "No description")[:50]
                    print(f"      • {tool.name}: {desc}...")
            except Exception as e:
                print(f"   ❌ Error: {e}")
                return False

            # Test 3: Call a safe tool (search_tickets with empty query)
            print("\n3. Testing search_tickets tool...")
            try:
                result = await client.call_tool(
                    "search_tickets",
                    {
                        "workflow_id": "test-workflow",
                        "agent_id": "test-agent",
                        "query": "test",
                        "search_type": "keyword",
                        "limit": 1,
                    },
                )
                print(f"   ✅ search_tickets returned: {type(result.data)}")
            except Exception as e:
                print(f"   ⚠️  search_tickets error (expected if no data): {e}")

    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("   Make sure the API server is running!")
        return False

    print("\n" + "=" * 60)
    print("✅ Live Server Test Complete!")
    print("=" * 60)
    return True


async def test_http_transport():
    """Test with in-process HTTP server (run_server_async)."""
    print("=" * 60)
    print("🧪 HTTP Transport MCP Test (in-process)")
    print("=" * 60)

    try:
        from fastmcp import Client
        from fastmcp.utilities.tests import run_server_async
        from omoi_os.mcp.fastmcp_server import mcp

        print("\nStarting in-process HTTP server...")

        async with run_server_async(mcp, transport="sse") as url:
            print(f"   Server running at: {url}\n")

            async with Client(url, timeout=10.0) as client:
                # Test 1: Ping
                print("1. Pinging server...")
                try:
                    result = await client.ping()
                    print(f"   ✅ Ping result: {result}")
                except Exception as e:
                    print(f"   ❌ Ping failed: {e}")
                    return False

                # Test 2: List tools
                print("\n2. Listing tools...")
                try:
                    tools = await client.list_tools()
                    print(f"   ✅ Found {len(tools)} tools:")
                    for tool in tools:
                        desc = (tool.description or "No description")[:50]
                        print(f"      • {tool.name}: {desc}...")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    return False

        print("\n" + "=" * 60)
        print("✅ HTTP Transport Test Complete!")
        print("=" * 60)
        return True

    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("   Make sure fastmcp is installed with test utilities")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Quick MCP server test")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--in-memory", action="store_true", help="In-memory test (no network)"
    )
    group.add_argument("--live", action="store_true", help="Test against live server")
    group.add_argument(
        "--http", action="store_true", help="HTTP transport test (in-process server)"
    )

    args = parser.parse_args()

    if args.in_memory:
        success = asyncio.run(test_in_memory())
    elif args.live:
        success = asyncio.run(test_live_server())
    elif args.http:
        success = asyncio.run(test_http_transport())
    else:
        parser.print_help()
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
