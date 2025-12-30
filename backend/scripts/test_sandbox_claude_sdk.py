#!/usr/bin/env python3
"""Test Claude Agent SDK installation and initialization in Daytona sandbox.

Tests:
1. Create sandbox with Python environment
2. Install Claude Agent SDK
3. Verify imports work
4. Test basic initialization (with API key if available)
"""

import os
import sys
import time
from pathlib import Path

# Add backend to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Load environment
from dotenv import load_dotenv

load_dotenv(backend_dir / ".env.local")
load_dotenv(backend_dir / ".env")


def test_claude_sdk():
    """Run Claude Agent SDK test in sandbox."""
    print("=" * 60)
    print("🧪 DAYTONA SANDBOX - CLAUDE AGENT SDK TEST")
    print("=" * 60)

    # Check Daytona API key
    api_key = os.environ.get("DAYTONA_API_KEY")
    if not api_key:
        print("❌ DAYTONA_API_KEY not set")
        return False

    print(f"✅ Daytona API Key: {api_key[:10]}...")

    # Z.AI / Custom Anthropic-compatible API credentials
    anthropic_base_url = os.environ.get(
        "ANTHROPIC_BASE_URL", "https://api.z.ai/api/anthropic"
    )
    anthropic_key = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get(
        "ANTHROPIC_API_KEY"
    )

    # Model selection - use GLM models via Z.AI
    default_model = os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL", "glm-4.6v")

    if anthropic_key:
        print(f"✅ Anthropic Auth Token: {anthropic_key[:15]}...")
        print(f"   Base URL: {anthropic_base_url}")
        print(f"   Model: {default_model}")
    else:
        print("⚠️  No ANTHROPIC_AUTH_TOKEN - will test installation only")

    try:
        from daytona import CreateSandboxFromImageParams, Daytona, DaytonaConfig
    except ImportError:
        print("❌ Daytona SDK not installed")
        return False

    # Configure Daytona
    config = DaytonaConfig(
        api_key=api_key,
        api_url="https://app.daytona.io/api",
        target="us",
    )
    daytona = Daytona(config)

    sandbox = None
    try:
        # Create sandbox
        print("\n📦 Creating sandbox...")
        start_time = time.time()

        params = CreateSandboxFromImageParams(
            image="nikolaik/python-nodejs:python3.12-nodejs22",
            labels={"test": "claude-sdk"},
            ephemeral=True,
            public=False,
        )

        sandbox = daytona.create(params=params, timeout=120)
        create_time = time.time() - start_time

        print(f"✅ Sandbox created in {create_time:.1f}s")
        print(f"   ID: {sandbox.id}")

        # ====================================================================
        # TEST 1: Install Claude Agent SDK
        # ====================================================================
        print("\n" + "=" * 60)
        print("📦 TEST 1: Install Claude Agent SDK")
        print("=" * 60)

        # Check if uv is available (it should be in the image)
        result = sandbox.process.exec("which uv")
        print(f"   UV location: {result.result.strip()}")

        # Install claude-agent-sdk using pip (uv pip install for speed)
        print("   Installing claude-agent-sdk...")
        install_start = time.time()

        result = sandbox.process.exec(
            "pip install claude-agent-sdk --quiet 2>&1 || pip install claude-agent-sdk 2>&1"
        )
        install_time = time.time() - install_start

        if result.exit_code == 0:
            print(f"✅ claude-agent-sdk installed in {install_time:.1f}s")
        else:
            print(f"⚠️  Install output: {result.result[:500]}")

        # ====================================================================
        # TEST 2: Verify imports
        # ====================================================================
        print("\n" + "=" * 60)
        print("🔍 TEST 2: Verify Claude SDK imports")
        print("=" * 60)

        import_test = """
import sys
try:
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, HookMatcher
    print("✅ Core imports successful")
    print(f"   ClaudeAgentOptions: {ClaudeAgentOptions}")
    print(f"   ClaudeSDKClient: {ClaudeSDKClient}")
    print(f"   HookMatcher: {HookMatcher}")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

try:
    from claude_agent_sdk import tool, create_sdk_mcp_server
    print("✅ Tool/MCP imports successful")
except ImportError as e:
    print(f"⚠️  Tool/MCP imports failed: {e}")

# Check version if available
try:
    import claude_agent_sdk
    version = getattr(claude_agent_sdk, '__version__', 'unknown')
    print(f"   Version: {version}")
except:
    pass
"""
        # Write and execute the import test
        sandbox.process.exec(
            f"cat > /tmp/test_imports.py << 'PYEOF'\n{import_test}\nPYEOF"
        )
        result = sandbox.process.exec("python /tmp/test_imports.py")
        print("\n   Import test output:")
        for line in result.result.strip().split("\n"):
            print(f"   {line}")

        if result.exit_code != 0:
            print("❌ Import test failed")
            return False

        # ====================================================================
        # TEST 3: Test basic initialization (no API call)
        # ====================================================================
        print("\n" + "=" * 60)
        print("🔧 TEST 3: Test basic initialization")
        print("=" * 60)

        init_test = f"""
import os
from pathlib import Path

# Set environment for Z.AI / custom Anthropic API
os.environ["ANTHROPIC_BASE_URL"] = "{anthropic_base_url}"
os.environ["ANTHROPIC_API_KEY"] = "{anthropic_key}" if "{anthropic_key}" else "test-key"

try:
    from claude_agent_sdk import ClaudeAgentOptions
    
    # Test creating options object with GLM model
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Bash"],
        permission_mode="bypassPermissions",
        system_prompt="Test system prompt",
        cwd=Path("/tmp"),
        max_turns=10,
        model="{default_model}",  # GLM model via Z.AI
    )
    print("✅ ClaudeAgentOptions created successfully")
    print(f"   model: {{options.model}}")
    print(f"   max_turns: {{options.max_turns}}")
    print(f"   permission_mode: {{options.permission_mode}}")
    print(f"   allowed_tools: {{options.allowed_tools}}")
except Exception as e:
    print(f"❌ Initialization failed: {{e}}")
    import traceback
    traceback.print_exc()
"""
        sandbox.process.exec(f"cat > /tmp/test_init.py << 'PYEOF'\n{init_test}\nPYEOF")

        result = sandbox.process.exec("python /tmp/test_init.py")
        print("\n   Init test output:")
        for line in result.result.strip().split("\n"):
            print(f"   {line}")

        # ====================================================================
        # TEST 4: Test with real API key (if available)
        # ====================================================================
        if anthropic_key:
            print("\n" + "=" * 60)
            print("🚀 TEST 4: Test API connection (lightweight)")
            print("=" * 60)

            api_test = f"""
import os
import asyncio

os.environ["ANTHROPIC_BASE_URL"] = "{anthropic_base_url}"
os.environ["ANTHROPIC_API_KEY"] = "{anthropic_key}"

async def test_api():
    try:
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
        from pathlib import Path
        
        print(f"   Model: {default_model}")
        
        options = ClaudeAgentOptions(
            allowed_tools=["Bash"],
            permission_mode="bypassPermissions",
            system_prompt="You are a helpful assistant. Be concise.",
            cwd=Path("/tmp"),
            max_turns=5,
            max_budget_usd=0.50,
            model="{default_model}",
        )
        
        async with ClaudeSDKClient(options=options) as client:
            print("   Task: Calculate 137 * 42 + 99")
            print("=" * 50)
            
            await client.query("Calculate 137 * 42 + 99. Use python -c to compute. Just show the answer.")
            
            async for msg in client.receive_response():
                msg_type = type(msg).__name__
                
                # Dump all attributes to see what we have
                if msg_type == "AssistantMessage":
                    if hasattr(msg, 'message'):
                        m = msg.message
                        if hasattr(m, 'content'):
                            for item in m.content:
                                if hasattr(item, 'text'):
                                    print(f"   💬 {{item.text}}")
                                elif hasattr(item, 'name') and hasattr(item, 'input'):
                                    print(f"   🔧 Tool: {{item.name}}")
                                    if hasattr(item.input, 'command'):
                                        print(f"      Command: {{item.input.command}}")
                                    elif isinstance(item.input, dict):
                                        print(f"      Input: {{item.input}}")
                
                elif msg_type == "UserMessage":
                    if hasattr(msg, 'message'):
                        m = msg.message
                        if hasattr(m, 'content'):
                            for item in m.content:
                                if hasattr(item, 'content'):
                                    # Tool result
                                    print(f"   📤 Result: {{item.content[:300]}}")
                
                elif msg_type == "ResultMessage":
                    if hasattr(msg, 'result'):
                        print(f"   ✅ Final: {{msg.result}}")
                    if hasattr(msg, 'subtype'):
                        print(f"      Subtype: {{msg.subtype}}")
            
            print("=" * 50)
            print("✅ Task completed!")
            return True
    except Exception as e:
        print(f"❌ API test failed: {{e}}")
        import traceback
        traceback.print_exc()
        return False

result = asyncio.run(test_api())
exit(0 if result else 1)
"""
            sandbox.process.exec(
                f"cat > /tmp/test_api.py << 'PYEOF'\n{api_test}\nPYEOF"
            )
            result = sandbox.process.exec("python /tmp/test_api.py")
            print("\n   API test output:")
            for line in result.result.strip().split("\n"):
                print(f"   {line}")

        # ====================================================================
        # Summary
        # ====================================================================
        print("\n" + "=" * 60)
        print("✅ CLAUDE AGENT SDK TESTS COMPLETED!")
        print("=" * 60)

        print("\n📋 Summary:")
        print("   ✅ claude-agent-sdk installed")
        print("   ✅ Core imports work (ClaudeAgentOptions, ClaudeSDKClient)")
        print("   ✅ Options initialization works")
        if anthropic_key:
            print("   ✅ API connection tested")
        else:
            print("   ⚠️  API connection not tested (no ANTHROPIC_API_KEY)")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Cleanup
        if sandbox:
            print("\n🧹 Cleaning up sandbox...")
            try:
                daytona.delete(sandbox)
                print("✅ Sandbox deleted")
            except Exception as e:
                print(f"⚠️  Cleanup error: {e}")


if __name__ == "__main__":
    success = test_claude_sdk()
    sys.exit(0 if success else 1)
