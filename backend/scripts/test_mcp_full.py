#!/usr/bin/env python3
"""Full MCP SSE test - verifies end-to-end message flow."""

import asyncio
import json
import sys
from pathlib import Path

import httpx

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_mcp_full_flow():
    """Test complete MCP SSE flow: connect, get session, send message, get response."""
    print("=" * 60)
    print("🧪 Full MCP SSE Flow Test")
    print("=" * 60)
    
    base_url = "http://localhost:18000/mcp"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Connect to SSE and extract session_id
        print("\n1. Connecting to SSE endpoint...")
        
        session_id = None
        
        async with client.stream(
            "GET", 
            f"{base_url}/sse",
            headers={"Accept": "text/event-stream"}
        ) as sse_response:
            print(f"   Status: {sse_response.status_code}")
            
            if sse_response.status_code != 200:
                print(f"   ❌ Failed to connect to SSE")
                return False
            
            # Read SSE events to get session_id
            buffer = ""
            async for chunk in sse_response.aiter_text():
                buffer += chunk
                
                # Parse SSE format: "event: xxx\ndata: yyy\n\n"
                while "\n\n" in buffer:
                    event_block, buffer = buffer.split("\n\n", 1)
                    
                    for line in event_block.split("\n"):
                        if line.startswith("data:"):
                            data = line[5:].strip()
                            if data:
                                print(f"   SSE data: {data[:80]}...")
                                
                                # Check if this contains session info
                                # FastMCP sends endpoint info with session_id in query
                                if "session_id=" in data:
                                    # Extract session_id from URL like /messages/?session_id=xxx
                                    import re
                                    match = re.search(r'session_id=([a-f0-9-]+)', data)
                                    if match:
                                        session_id = match.group(1)
                                        print(f"   ✅ Got session_id: {session_id}")
                                
                                # Also try JSON parsing
                                try:
                                    parsed = json.loads(data)
                                    if isinstance(parsed, dict):
                                        if "session_id" in parsed:
                                            session_id = parsed["session_id"]
                                            print(f"   ✅ Got session_id (JSON): {session_id}")
                                except json.JSONDecodeError:
                                    pass
                
                if session_id:
                    break
            
            if not session_id:
                print("   ❌ Could not extract session_id from SSE stream")
                print("   Trying to parse more of the stream...")
                # Show what we got
                print(f"   Buffer content: {buffer[:500]}")
                return False
            
            # Step 2: Send tools/list request
            print(f"\n2. Sending tools/list request (session_id={session_id[:8]}...)...")
            
            msg_response = await client.post(
                f"{base_url}/messages/",
                params={"session_id": session_id},
                json={
                    "jsonrpc": "2.0",
                    "id": "test-1",
                    "method": "tools/list",
                    "params": {}
                }
            )
            
            print(f"   POST status: {msg_response.status_code}")
            print(f"   POST response: {msg_response.text[:200]}")
            
            if msg_response.status_code != 200 and msg_response.status_code != 202:
                print(f"   ❌ Message request failed")
                return False
            
            print("   ✅ Message sent successfully")
            
            # Step 3: Read response from SSE stream
            print("\n3. Reading response from SSE stream...")
            
            tools_found = False
            event_count = 0
            max_events = 20
            
            async for chunk in sse_response.aiter_text():
                buffer += chunk
                
                while "\n\n" in buffer:
                    event_block, buffer = buffer.split("\n\n", 1)
                    
                    for line in event_block.split("\n"):
                        if line.startswith("data:"):
                            data = line[5:].strip()
                            if data:
                                try:
                                    parsed = json.loads(data)
                                    
                                    # Check for tools/list response
                                    if isinstance(parsed, dict):
                                        if "result" in parsed and "tools" in parsed.get("result", {}):
                                            tools = parsed["result"]["tools"]
                                            print(f"   ✅ Received tools/list response!")
                                            print(f"   Found {len(tools)} tools:")
                                            for tool in tools:
                                                print(f"      • {tool['name']}")
                                            tools_found = True
                                            break
                                        elif "id" in parsed:
                                            print(f"   Response: {json.dumps(parsed)[:150]}...")
                                except json.JSONDecodeError:
                                    pass
                    
                    event_count += 1
                    if tools_found or event_count >= max_events:
                        break
                
                if tools_found or event_count >= max_events:
                    break
            
            if not tools_found:
                print(f"   ⚠️  Did not receive tools/list response after {event_count} events")
                return False
    
    print("\n" + "=" * 60)
    print("✅ Full MCP Flow Test PASSED!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_mcp_full_flow())
    sys.exit(0 if success else 1)

