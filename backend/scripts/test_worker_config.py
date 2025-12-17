#!/usr/bin/env python3
"""Test worker configuration and SDK options creation without running the full worker.

This is a quick test to verify:
1. WorkerConfig loads environment variables correctly
2. SDK options are created without errors
3. Agent definitions are properly formatted

Usage:
    cd backend
    set -a && source .env.local && set +a
    uv run python scripts/test_worker_config.py
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up test environment variables
os.environ["SANDBOX_ID"] = "test-sandbox-config"
os.environ["TASK_ID"] = "test-task-config"
os.environ["AGENT_ID"] = "test-agent-config"
os.environ["CALLBACK_URL"] = "http://localhost:18000"
os.environ["TICKET_ID"] = "test-ticket-config"
os.environ["TICKET_TITLE"] = "Test Configuration"
os.environ["TICKET_DESCRIPTION"] = "Test task description for configuration testing"
os.environ["PHASE_ID"] = "PHASE_IMPLEMENTATION"
os.environ["PERMISSION_MODE"] = "acceptEdits"
os.environ["ALLOWED_TOOLS"] = "Read,Write,Bash,Edit,Glob,Grep,Task,Skill"
os.environ["ENABLE_SKILLS"] = "true"
os.environ["ENABLE_SUBAGENTS"] = "true"
os.environ["SETTING_SOURCES"] = "user,project"
os.environ["CWD"] = "/tmp/test_workspace_config"
os.environ["MAX_TURNS"] = "10"
os.environ["MAX_BUDGET_USD"] = "1.0"

# Set a dummy API key if not present (won't work for actual SDK calls, but allows config test)
if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("LLM_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"

print("=" * 70)
print("🧪 WORKER CONFIGURATION TEST")
print("=" * 70)
print()

try:
    from omoi_os.workers.claude_sandbox_worker import WorkerConfig

    print("[1/3] Testing WorkerConfig initialization...")
    config = WorkerConfig()
    print("   ✅ WorkerConfig created successfully")

    print("\n[2/3] Testing configuration values...")
    config_dict = config.to_dict()
    print(f"   ✅ Configuration loaded: {len(config_dict)} settings")
    print(f"   - Sandbox ID: {config.sandbox_id}")
    print(f"   - Task ID: {config.task_id}")
    print(f"   - Ticket Title: {config.ticket_title}")
    print(f"   - Ticket Description: {config.ticket_description[:60]}...")
    print(f"   - Callback URL: {config.callback_url}")
    print(f"   - Model: {config.model or 'default'}")
    print(f"   - Enable Subagents: {config.enable_subagents}")
    print(f"   - Enable Skills: {config.enable_skills}")

    print("\n[3/3] Testing SDK options creation...")
    try:
        sdk_options = config.to_sdk_options()
        print("   ✅ SDK options created successfully")
        print(f"   - Options type: {type(sdk_options).__name__}")
        print(f"   - Allowed tools: {len(sdk_options.allowed_tools)} tools")
        print(f"   - Max turns: {sdk_options.max_turns}")
        print(f"   - Permission mode: {sdk_options.permission_mode}")

        # Test agent definitions
        agents = config.get_custom_agents()
        if agents:
            print(f"   - Custom agents: {len(agents)} agents")
            for name, agent_def in agents.items():
                if hasattr(agent_def, "description"):
                    print(f"     • {name}: {agent_def.description[:50]}...")
                else:
                    print(f"     • {name}: {type(agent_def).__name__}")
        else:
            print("   - Custom agents: None (subagents disabled)")

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        print("\nThe worker configuration is correct!")
        print(
            "You can now test the full worker with: uv run python scripts/test_worker_local.py"
        )

    except Exception as e:
        print(f"   ❌ Failed to create SDK options: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
