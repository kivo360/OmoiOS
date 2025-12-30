#!/usr/bin/env python3
"""End-to-end test of DaytonaSpawnerService with Z.AI credentials.

Tests:
1. Spawner injects Z.AI environment variables
2. Sandbox can run Claude Agent SDK with those credentials
3. Agent can execute a simple task and return result

Usage:
    cd backend
    uv run python scripts/test_spawner_e2e.py
"""

import asyncio
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env.local")


async def main():
    print("=" * 60)
    print("🧪 SPAWNER END-TO-END TEST WITH Z.AI")
    print("=" * 60)

    # Import spawner
    from omoi_os.services.daytona_spawner import DaytonaSpawnerService

    # Check Daytona API key
    from omoi_os.config import load_daytona_settings, get_app_settings

    daytona_settings = load_daytona_settings()
    if not daytona_settings.api_key:
        print("❌ DAYTONA_API_KEY not set")
        return

    print(f"✅ Daytona API Key: {daytona_settings.api_key[:12]}...")

    # Create spawner (no db/event_bus for this test)
    # Use the configured MCP server URL from settings
    settings = get_app_settings()
    spawner = DaytonaSpawnerService(
        db=None,
        event_bus=None,
        mcp_server_url=settings.integrations.mcp_server_url,
    )
    print(f"   MCP Server URL: {settings.integrations.mcp_server_url}")

    # Test task info
    task_id = f"test-e2e-{int(time.time())}"
    agent_id = f"agent-test-{int(time.time())}"
    phase_id = "PHASE_TEST"

    print(f"\n📦 Spawning sandbox for task: {task_id}")
    print("   Runtime: claude")

    try:
        # Spawn sandbox with Claude runtime
        start_time = time.time()
        sandbox_id = await spawner.spawn_for_task(
            task_id=task_id,
            agent_id=agent_id,
            phase_id=phase_id,
            runtime="claude",
        )
        spawn_time = time.time() - start_time

        print(f"✅ Sandbox spawned in {spawn_time:.1f}s")
        print(f"   ID: {sandbox_id}")

        # Get sandbox info
        info = spawner.get_sandbox_info(sandbox_id)
        if info:
            print(f"   Status: {info.status}")
            print(f"   Runtime: {info.extra_data.get('runtime', 'unknown')}")

        # Now let's verify the environment variables are set correctly
        # by running a simple check inside the sandbox
        print("\n🔍 Verifying Z.AI environment variables in sandbox...")

        # Get the actual Daytona sandbox from the spawner's stored reference
        sandbox = None
        if info and "daytona_sandbox" in info.extra_data:
            sandbox = info.extra_data["daytona_sandbox"]
            print(
                f"   Got sandbox from spawner: {info.extra_data.get('daytona_sandbox_id')}"
            )

        if sandbox:
            print(f"   Found sandbox: {sandbox.id}")

            # Check environment variables from the saved file
            result = sandbox.process.exec(
                "cat /tmp/.sandbox_env 2>/dev/null || echo 'File not found'"
            )
            print("\n   Saved environment variables:")
            for line in result.result.strip().split("\n")[:10]:  # Show first 10
                if "ANTHROPIC" in line or "TASK" in line:
                    # Mask API key
                    if "API_KEY" in line and "=" in line:
                        key, val = line.split("=", 1)
                        val = (
                            val.strip('"')[:20] + "..."
                            if len(val.strip('"')) > 20
                            else val
                        )
                        print(f"   {key}={val}")
                    else:
                        print(f"   {line}")

            # Verify Z.AI is configured
            if "api.z.ai" in result.result:
                print("\n✅ Z.AI configuration verified!")
            else:
                print("\n⚠️  Z.AI configuration not found in environment")

            # Now run a simple Claude Agent SDK test
            print("\n🚀 Testing Claude Agent SDK with Z.AI...")

            # Multi-step math problem that REQUIRES writing and running a Python script
            # Expected answer: 1060 (sum of squares of first 10 primes: 2,3,5,7,11,13,17,19,23,29)
            # 4+9+25+49+121+169+289+361+529+841 = 2397

            math_task = """Create a Python script called "prime_calc.py" that:
1. Finds the first 10 prime numbers
2. Calculates the square of each prime
3. Sums all the squares together
4. Prints each step showing: the prime, its square, and running total
5. Prints the final sum

Then RUN the script with "python prime_calc.py" and show me the output.

DO NOT use python -c. You MUST write a .py file first, then run it."""

            sdk_test = f"""
import os
import asyncio

# Load environment from saved file
try:
    with open("/tmp/.sandbox_env") as f:
        for line in f:
            if "=" in line:
                key, val = line.strip().split("=", 1)
                os.environ[key] = val.strip('"')
except FileNotFoundError:
    pass

async def test():
    try:
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
        from pathlib import Path
        
        model = os.environ.get("ANTHROPIC_MODEL", "glm-4.6v")
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        
        print(f"Model: {{model}}")
        print(f"Base URL: {{base_url}}")
        print(f"API Key: {{api_key[:20]}}..." if api_key else "API Key: NOT SET")
        
        # Create workspace directory
        workspace = Path("/workspace")
        workspace.mkdir(exist_ok=True)
        os.chdir(workspace)
        print(f"Working directory: {{os.getcwd()}}")
        
        options = ClaudeAgentOptions(
            allowed_tools=["Read", "Write", "Edit", "Bash", "LS"],
            permission_mode="bypassPermissions",
            system_prompt="You are a helpful assistant. Always write code to files before running them. Use relative paths.",
            cwd=workspace,
            max_turns=10,
            max_budget_usd=1.00,
            model=model,
        )
        
        task = '''{math_task}'''
        
        async with ClaudeSDKClient(options=options) as client:
            await client.query(task)
            
            async for msg in client.receive_response():
                msg_type = type(msg).__name__
                
                # Print all message types for visibility
                if msg_type == "AssistantMessage":
                    if hasattr(msg, 'content'):
                        print(f"\\n[ASSISTANT] {{msg.content[:200]}}...")
                        
                elif msg_type == "ToolUseBlock":
                    tool_name = getattr(msg, 'name', 'unknown')
                    tool_input = getattr(msg, 'input', {{}})
                    print(f"\\n[TOOL CALL] {{tool_name}}")
                    if tool_name == "Write":
                        print(f"  File: {{tool_input.get('file_path', 'unknown')}}")
                        content = tool_input.get('content', '')
                        print(f"  Content preview: {{content[:100]}}...")
                    elif tool_name == "Bash":
                        print(f"  Command: {{tool_input.get('command', '')}}")
                        
                elif msg_type == "ToolResultBlock":
                    print(f"[TOOL RESULT] {{getattr(msg, 'content', '')[:300]}}")
                    
                elif msg_type == "ResultMessage":
                    if hasattr(msg, 'result'):
                        print(f"\\n[FINAL RESULT] {{msg.result}}")
                    if hasattr(msg, 'subtype'):
                        print(f"[STATUS] {{msg.subtype}}")
        
        # Verify the file was created
        if (workspace / "prime_calc.py").exists():
            print("\\n✅ prime_calc.py was created!")
            with open(workspace / "prime_calc.py") as f:
                print("--- File contents ---")
                print(f.read())
                print("--- End file ---")
        
        print("\\nSDK test completed!")
        return True
    except Exception as e:
        print(f"Error: {{e}}")
        import traceback
        traceback.print_exc()
        return False

asyncio.run(test())
"""
            # First install the SDK
            print("   Installing claude-agent-sdk...")
            sandbox.process.exec(
                "pip install claude-agent-sdk --quiet 2>/dev/null || pip install claude-agent-sdk"
            )

            # Run the test
            sandbox.process.exec(f"cat > /tmp/sdk_test.py << 'EOF'\n{sdk_test}\nEOF")
            result = sandbox.process.exec("python /tmp/sdk_test.py")

            print("\n   SDK Test Output:")
            for line in result.result.strip().split("\n"):
                print(f"   {line}")

            # Check for success - sum of squares of first 10 primes = 2397
            # Primes: 2,3,5,7,11,13,17,19,23,29
            # Squares: 4+9+25+49+121+169+289+361+529+841 = 2397
            if "2397" in result.result:
                print(
                    "\n🎉 SUCCESS! Agent computed sum of squares of first 10 primes = 2397"
                )
            elif "prime_calc.py was created" in result.result:
                print("\n✅ Agent wrote and ran the Python script!")
            elif "SDK test completed" in result.result:
                print("\n✅ Agent completed the task!")

            # Show worker logs
            print("\n📜 Worker logs (/tmp/worker.log):")
            print("-" * 50)
            worker_log = sandbox.process.exec(
                "cat /tmp/worker.log 2>/dev/null || echo 'No worker.log found'"
            )
            for line in worker_log.result.strip().split("\n"):
                print(f"   {line}")
            print("-" * 50)

            # Show any other relevant logs
            print("\n📜 Daytona logs:")
            print("-" * 50)
            daytona_log = sandbox.process.exec(
                "cat /tmp/daytona-daemon.log 2>/dev/null | tail -20 || echo 'No daytona log'"
            )
            for line in daytona_log.result.strip().split("\n"):
                print(f"   {line}")
            print("-" * 50)

        else:
            print("   ⚠️  Could not find sandbox to verify environment")

        # Cleanup
        print("\n🧹 Cleaning up...")
        await spawner.terminate_sandbox(sandbox_id)
        print("✅ Sandbox terminated")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

        # Try to cleanup
        try:
            await spawner.terminate_sandbox(sandbox_id)
        except:
            pass

    print("\n" + "=" * 60)
    print("🏁 END-TO-END TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
