"""Test script for MCP endpoints."""

import asyncio

import httpx


async def test_mcp_endpoints():
    """Test MCP API endpoints."""
    base_url = "http://localhost:18000"

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        print("🧪 Testing MCP Endpoints\n")

        # Test 1: Register an MCP server
        print("1. Testing server registration...")
        register_request = {
            "server_id": "test_server",
            "version": "1.0.0",
            "capabilities": ["tools", "resources"],
            "connection_url": "https://example.com/mcp",  # Example URL
            "tools": [
                {
                    "name": "test_tool",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string"},
                            "count": {"type": "integer", "default": 1},
                        },
                        "required": ["message"],
                    },
                    "version": "1.0.0",
                }
            ],
            "metadata": {"description": "Test MCP server"},
        }

        try:
            response = await client.post("/api/mcp/register", json=register_request)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Registered {result['registered_count']} tools")
                print(f"   ❌ Rejected {result['rejected_count']} tools")
            else:
                print(f"   ❌ Error: {response.text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

        print()

        # Test 2: List tools
        print("2. Testing list tools...")
        try:
            response = await client.get("/api/mcp/tools")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                tools = response.json()
                print(f"   ✅ Found {len(tools)} tools")
                if tools:
                    print(
                        f"   First tool: {tools[0]['tool_name']} from {tools[0]['server_id']}"
                    )
            else:
                print(f"   ❌ Error: {response.text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

        print()

        # Test 3: Get specific tool
        print("3. Testing get tool...")
        try:
            response = await client.get("/api/mcp/tools/test_server/test_tool")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                tool = response.json()
                print(f"   ✅ Tool found: {tool['tool_name']}")
            else:
                print(f"   ❌ Error: {response.text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

        print()

        # Test 4: Grant permission
        print("4. Testing grant permission...")
        grant_request = {
            "agent_id": "test_agent_001",
            "server_id": "test_server",
            "tool_name": "test_tool",
            "actions": ["invoke"],
        }

        try:
            response = await client.post("/api/mcp/policies/grant", json=grant_request)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print("   ✅ Permission granted")
                if result.get("token_id"):
                    print(f"   Token ID: {result['token_id']}")
            else:
                print(f"   ❌ Error: {response.text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

        print()

        # Test 5: List agent permissions
        print("5. Testing list agent permissions...")
        try:
            response = await client.get("/api/mcp/policies/test_agent_001")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                permissions = response.json()
                print(f"   ✅ Found {len(permissions)} permissions")
            else:
                print(f"   ❌ Error: {response.text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

        print()

        # Test 6: List servers
        print("6. Testing list servers...")
        try:
            response = await client.get("/api/mcp/servers")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                servers = response.json()
                print(f"   ✅ Found {len(servers)} servers")
                if servers:
                    print(
                        f"   First server: {servers[0]['server_id']} ({servers[0]['status']})"
                    )
            else:
                print(f"   ❌ Error: {response.text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

        print()

        # Test 7: Get circuit breakers
        print("7. Testing circuit breakers...")
        try:
            response = await client.get("/api/mcp/circuit-breakers")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                breakers = response.json()
                print(f"   ✅ Found {len(breakers)} circuit breakers")
            else:
                print(f"   ❌ Error: {response.text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

        print()

        print("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(test_mcp_endpoints())
