#!/usr/bin/env python3
"""Test MCP server using raw HTTP (avoids fastmcp client import issues).

This tests the FastMCP server endpoint directly using httpx.

Usage:
    # With API server running:
    python scripts/test_mcp_http.py
"""

import asyncio
import sys
from pathlib import Path

import httpx

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_mcp_sse_endpoint():
    """Test the MCP SSE endpoint directly."""
    print("=" * 60)
    print("🧪 MCP Server HTTP Test")
    print("=" * 60)

    from omoi_os.config import get_app_settings

    base_url = get_app_settings().integrations.mcp_server_url
    print(f"\nTesting: {base_url}")
    print("Expected endpoints:")
    print(f"  - SSE: {base_url}/sse")
    print(f"  - Message: {base_url}/message\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Check health endpoint first
        print("1. Checking main API health...")
        try:
            health_url = base_url.replace("/mcp", "/health")
            response = await client.get(health_url)
            print(f"   Health endpoint status: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ API is healthy: {response.json()}")
            else:
                print("   ❌ API not healthy!")
                return False
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
            print("   Is the API server running? Try: just api")
            return False

        # Test 2: Check the root MCP path
        print("\n2. Checking root MCP path...")
        try:
            response = await client.get(base_url, follow_redirects=True)
            print(f"   Root path status: {response.status_code}")
            print(f"   Response: {response.text[:200] if response.text else '(empty)'}")
        except Exception as e:
            print(f"   ⚠️  Error: {e}")

        # Test 3: Check SSE endpoint (GET request with Accept header)
        print("\n3. Checking SSE endpoint...")
        try:
            response = await client.get(
                f"{base_url}/sse", headers={"Accept": "text/event-stream"}
            )
            print(f"   SSE endpoint status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
            if response.status_code == 200:
                print("   ✅ SSE endpoint accessible")
            else:
                print(f"   Response: {response.text[:200]}")
        except Exception as e:
            print(f"   ⚠️  SSE error: {e}")

        # Test 4: Try MCP initialize via message endpoint
        print("\n4. Testing MCP message endpoint (initialize)...")
        try:
            response = await client.post(
                f"{base_url}/message",
                headers={"Content-Type": "application/json"},
                json={
                    "jsonrpc": "2.0",
                    "id": "test-1",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test-client", "version": "1.0.0"},
                    },
                },
            )
            print(f"   Message endpoint status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print("   ✅ MCP initialized!")
                print(f"   Server: {data.get('result', {}).get('serverInfo', {})}")
            else:
                print(f"   Response: {response.text[:300]}")
        except Exception as e:
            print(f"   ⚠️  Message endpoint error: {e}")

        # Test 5: Try tools/list via message endpoint
        print("\n5. Testing tools/list...")
        try:
            response = await client.post(
                f"{base_url}/message",
                headers={"Content-Type": "application/json"},
                json={
                    "jsonrpc": "2.0",
                    "id": "test-2",
                    "method": "tools/list",
                    "params": {},
                },
            )
            print(f"   tools/list status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                tools = data.get("result", {}).get("tools", [])
                print(f"   ✅ Found {len(tools)} tools:")
                for tool in tools[:5]:  # Show first 5
                    print(f"      • {tool.get('name')}")
                if len(tools) > 5:
                    print(f"      ... and {len(tools) - 5} more")
            else:
                print(f"   Response: {response.text[:300]}")
        except Exception as e:
            print(f"   ⚠️  tools/list error: {e}")

    print("\n" + "=" * 60)
    print("✅ HTTP Test Complete!")
    print("=" * 60)
    return True


async def test_mcp_with_sse_client():
    """Test MCP using SSE client (more realistic)."""
    print("\n" + "=" * 60)
    print("🧪 MCP SSE Client Test")
    print("=" * 60)

    try:
        import httpx_sse
    except ImportError:
        print("\nℹ️  httpx-sse not installed. Install with: pip install httpx-sse")
        return True  # Not a failure, just skip

    from omoi_os.config import get_app_settings

    base_url = get_app_settings().integrations.mcp_server_url
    sse_url = f"{base_url}/sse"

    print(f"\nConnecting to SSE: {sse_url}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            async with httpx_sse.aconnect_sse(client, "GET", sse_url) as event_source:
                print("   ✅ SSE connection established")

                # Read first few events
                event_count = 0
                async for event in event_source.aiter_sse():
                    print(f"   Event: {event.event} - {event.data[:100]}...")
                    event_count += 1
                    if event_count >= 3:
                        break

        except Exception as e:
            print(f"   ⚠️  SSE connection error: {e}")

    return True


def main():
    print("\n🔍 Testing MCP Server Endpoints\n")
    print("Make sure the API server is running: just backend-dev\n")

    success = asyncio.run(test_mcp_sse_endpoint())

    if success:
        # Try SSE test too
        asyncio.run(test_mcp_with_sse_client())

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
