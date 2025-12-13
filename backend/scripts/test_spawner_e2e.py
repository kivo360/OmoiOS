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
import os
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
    from omoi_os.config import load_daytona_settings

    daytona_settings = load_daytona_settings()
    if not daytona_settings.api_key:
        print("❌ DAYTONA_API_KEY not set")
        return

    print(f"✅ Daytona API Key: {daytona_settings.api_key[:12]}...")

    # Create spawner (no db/event_bus for this test)
    spawner = DaytonaSpawnerService(
        db=None,
        event_bus=None,
        mcp_server_url="http://localhost:18000/mcp/",
    )

    # Test task info
    task_id = f"test-e2e-{int(time.time())}"
    agent_id = f"agent-test-{int(time.time())}"
    phase_id = "PHASE_TEST"

    print(f"\n📦 Spawning sandbox for task: {task_id}")
    print(f"   Runtime: claude")

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
            print(f"   Got sandbox from spawner: {info.extra_data.get('daytona_sandbox_id')}")

        if sandbox:
            print(f"   Found sandbox: {sandbox.id}")

            # Check environment variables from the saved file
            result = sandbox.process.exec("cat /tmp/.sandbox_env 2>/dev/null || echo 'File not found'")
            print("\n   Saved environment variables:")
            for line in result.result.strip().split("\n")[:10]:  # Show first 10
                if "ANTHROPIC" in line or "TASK" in line:
                    # Mask API key
                    if "API_KEY" in line and "=" in line:
                        key, val = line.split("=", 1)
                        val = val.strip('"')[:20] + "..." if len(val.strip('"')) > 20 else val
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

            sdk_test = """
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
        
        print(f"Model: {model}")
        print(f"Base URL: {base_url}")
        print(f"API Key: {api_key[:20]}..." if api_key else "API Key: NOT SET")
        
        options = ClaudeAgentOptions(
            allowed_tools=["Bash"],
            permission_mode="acceptEdits",
            system_prompt="Be concise.",
            cwd=Path("/tmp"),
            max_turns=3,
            max_budget_usd=0.50,
            model=model,
        )
        
        async with ClaudeSDKClient(options=options) as client:
            await client.query("Calculate 42 * 37 using python -c. Just show the answer.")
            
            async for msg in client.receive_response():
                msg_type = type(msg).__name__
                if msg_type == "ResultMessage":
                    if hasattr(msg, 'result'):
                        print(f"Result: {msg.result}")
                    if hasattr(msg, 'subtype'):
                        print(f"Status: {msg.subtype}")
        
        print("SDK test completed!")
        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

asyncio.run(test())
"""
            # First install the SDK
            print("   Installing claude-agent-sdk...")
            sandbox.process.exec("pip install claude-agent-sdk --quiet 2>/dev/null || pip install claude-agent-sdk")

            # Run the test
            sandbox.process.exec(f"cat > /tmp/sdk_test.py << 'EOF'\n{sdk_test}\nEOF")
            result = sandbox.process.exec("python /tmp/sdk_test.py")

            print("\n   SDK Test Output:")
            for line in result.result.strip().split("\n"):
                print(f"   {line}")

            # Check for success
            if "1554" in result.result:  # 42 * 37 = 1554
                print("\n🎉 SUCCESS! Agent computed 42 × 37 = 1554")
            elif "Result:" in result.result:
                print("\n✅ Agent returned a result!")

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
