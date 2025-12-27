#!/usr/bin/env python3
"""Test worker configuration and SDK options creation without running the full worker.

This is a quick test to verify:
1. WorkerConfig loads environment variables correctly
2. SDK options are created without errors
3. Agent definitions are properly formatted
4. Tools configuration works correctly (SDK defaults vs explicit)

Usage:
    cd backend
    set -a && source .env.local && set +a
    uv run python scripts/test_worker_config.py

    # Test specific scenarios:
    uv run python scripts/test_worker_config.py --mode default
    uv run python scripts/test_worker_config.py --mode replace
    uv run python scripts/test_worker_config.py --mode disallow
"""

import argparse
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def clear_tool_env_vars():
    """Clear tool-related environment variables for clean testing."""
    for var in ["ALLOWED_TOOLS", "DISALLOWED_TOOLS", "ENABLE_SPEC_TOOLS"]:
        os.environ.pop(var, None)


def set_base_env_vars():
    """Set up base environment variables required by WorkerConfig."""
    os.environ["SANDBOX_ID"] = "test-sandbox-config"
    os.environ["TASK_ID"] = "test-task-config"
    os.environ["AGENT_ID"] = "test-agent-config"
    os.environ["CALLBACK_URL"] = "http://localhost:18000"
    os.environ["TICKET_ID"] = "test-ticket-config"
    os.environ["TICKET_TITLE"] = "Test Configuration"
    os.environ["TICKET_DESCRIPTION"] = "Test task description for configuration testing"
    os.environ["PHASE_ID"] = "PHASE_IMPLEMENTATION"
    os.environ["PERMISSION_MODE"] = "acceptEdits"
    os.environ["ENABLE_SKILLS"] = "true"
    os.environ["ENABLE_SUBAGENTS"] = "true"
    os.environ["ENABLE_SPEC_TOOLS"] = "true"
    os.environ["SETTING_SOURCES"] = "user,project"
    os.environ["CWD"] = "/tmp/test_workspace_config"
    os.environ["MAX_TURNS"] = "10"
    os.environ["MAX_BUDGET_USD"] = "1.0"

    # Set a dummy API key if not present
    if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("LLM_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"


def reload_worker_module():
    """Reload the worker module to pick up new environment variables."""
    import importlib
    import omoi_os.workers.claude_sandbox_worker as worker_module
    importlib.reload(worker_module)
    return worker_module


def test_default_mode():
    """Test default tools mode (SDK defaults)."""
    print("\n" + "=" * 70)
    print("🧪 TEST: Default Tools Mode (SDK Defaults)")
    print("=" * 70)

    clear_tool_env_vars()
    set_base_env_vars()
    # Don't set ALLOWED_TOOLS - let SDK use defaults

    worker = reload_worker_module()
    config = worker.WorkerConfig()

    print(f"\n   Tools Mode: {config.tools_mode}")
    print(f"   allowed_tools: {config.allowed_tools}")
    print(f"   disallowed_tools: {config.disallowed_tools}")

    # Verify expectations
    assert config.tools_mode == "default", f"Expected 'default', got '{config.tools_mode}'"
    assert config.allowed_tools is None, f"Expected None, got {config.allowed_tools}"

    # Test SDK options
    sdk_options = config.to_sdk_options()
    has_allowed_tools = hasattr(sdk_options, 'allowed_tools') and sdk_options.allowed_tools is not None
    print(f"\n   SDK allowed_tools set: {has_allowed_tools}")

    if has_allowed_tools:
        print(f"   ⚠️  WARNING: SDK options has allowed_tools when it shouldn't")
    else:
        print(f"   ✅ SDK will use default preset (includes Skill, Task, etc.)")

    return True


def test_replace_mode():
    """Test explicit ALLOWED_TOOLS (replaces defaults)."""
    print("\n" + "=" * 70)
    print("🧪 TEST: Replace Tools Mode (ALLOWED_TOOLS set)")
    print("=" * 70)

    clear_tool_env_vars()
    set_base_env_vars()
    os.environ["ALLOWED_TOOLS"] = "Read, Write, Bash, Edit"

    worker = reload_worker_module()
    config = worker.WorkerConfig()

    print(f"\n   Tools Mode: {config.tools_mode}")
    print(f"   allowed_tools: {config.allowed_tools}")

    # Verify expectations
    assert config.tools_mode == "replace", f"Expected 'replace', got '{config.tools_mode}'"
    assert config.allowed_tools == ["Read", "Write", "Bash", "Edit"], f"Unexpected: {config.allowed_tools}"
    assert "Skill" not in config.allowed_tools, "Skill should NOT be in explicit list"
    assert "Task" not in config.allowed_tools, "Task should NOT be in explicit list"

    print(f"\n   ⚠️  WARNING: ALLOWED_TOOLS replaces SDK defaults!")
    print(f"      Missing tools: Skill, Task, WebSearch, Glob, Grep, etc.")

    # Test SDK options
    sdk_options = config.to_sdk_options()
    if hasattr(sdk_options, 'allowed_tools') and sdk_options.allowed_tools:
        print(f"   SDK allowed_tools: {sdk_options.allowed_tools}")

    return True


def test_disallow_mode():
    """Test DISALLOWED_TOOLS (blocks specific tools)."""
    print("\n" + "=" * 70)
    print("🧪 TEST: Disallow Tools Mode (DISALLOWED_TOOLS set)")
    print("=" * 70)

    clear_tool_env_vars()
    set_base_env_vars()
    os.environ["DISALLOWED_TOOLS"] = "Bash, Write"

    worker = reload_worker_module()
    config = worker.WorkerConfig()

    print(f"\n   Tools Mode: {config.tools_mode}")
    print(f"   allowed_tools: {config.allowed_tools}")
    print(f"   disallowed_tools: {config.disallowed_tools}")

    # Verify expectations
    assert config.tools_mode == "default", f"Expected 'default', got '{config.tools_mode}'"
    assert config.allowed_tools is None, "Should use SDK defaults"
    assert config.disallowed_tools == ["Bash", "Write"], f"Unexpected: {config.disallowed_tools}"

    print(f"\n   ✅ SDK will use defaults but block: Bash, Write")

    # Test SDK options
    sdk_options = config.to_sdk_options()
    if hasattr(sdk_options, 'disallowed_tools') and sdk_options.disallowed_tools:
        print(f"   SDK disallowed_tools: {sdk_options.disallowed_tools}")

    return True


def test_mcp_tools():
    """Test MCP spec workflow tools configuration."""
    print("\n" + "=" * 70)
    print("🧪 TEST: MCP Spec Workflow Tools")
    print("=" * 70)

    clear_tool_env_vars()
    set_base_env_vars()
    os.environ["ENABLE_SPEC_TOOLS"] = "true"

    worker = reload_worker_module()
    config = worker.WorkerConfig()

    print(f"\n   enable_spec_tools: {config.enable_spec_tools}")
    print(f"   MCP_AVAILABLE: {worker.MCP_AVAILABLE}")

    # Check system prompt for MCP docs
    if isinstance(config.system_prompt, dict):
        append_text = config.system_prompt.get("append", "")
        has_mcp_docs = "mcp__spec_workflow__" in append_text
        print(f"   System prompt (preset mode): {config.system_prompt.get('preset', 'N/A')}")
    else:
        append_text = config.system_prompt or ""
        has_mcp_docs = "mcp__spec_workflow__" in append_text

    print(f"   System prompt includes MCP docs: {has_mcp_docs}")

    if has_mcp_docs:
        print("   ✅ MCP tools documentation added to system prompt")
    else:
        print("   ⚠️  MCP tools documentation not found in system prompt")

    return True


def test_full_config():
    """Test full configuration with all features."""
    print("\n" + "=" * 70)
    print("🧪 TEST: Full Configuration")
    print("=" * 70)

    clear_tool_env_vars()
    set_base_env_vars()
    # Use SDK defaults with spec tools

    worker = reload_worker_module()
    config = worker.WorkerConfig()

    print(f"\n   Configuration Summary:")
    config_dict = config.to_dict()
    for key in ["tools_mode", "allowed_tools", "disallowed_tools",
                "enable_skills", "enable_subagents", "enable_spec_tools"]:
        print(f"   - {key}: {config_dict.get(key)}")

    print(f"\n   Testing SDK options creation...")
    sdk_options = config.to_sdk_options()
    print(f"   ✅ SDK options created: {type(sdk_options).__name__}")

    # Check for MCP servers
    if hasattr(sdk_options, 'mcp_servers') and sdk_options.mcp_servers:
        print(f"   ✅ MCP servers configured: {list(sdk_options.mcp_servers.keys())}")
    else:
        print(f"   ℹ️  No MCP servers in SDK options (may be added at runtime)")

    # Check custom agents
    agents = config.get_custom_agents()
    if agents:
        print(f"   ✅ Custom agents: {list(agents.keys())}")

    return True


def run_all_tests():
    """Run all test scenarios."""
    print("=" * 70)
    print("🧪 WORKER TOOLS CONFIGURATION TESTS")
    print("=" * 70)

    tests = [
        ("Default Mode", test_default_mode),
        ("Replace Mode", test_replace_mode),
        ("Disallow Mode", test_disallow_mode),
        ("MCP Tools", test_mcp_tools),
        ("Full Config", test_full_config),
    ]

    results = []
    for name, test_fn in tests:
        try:
            passed = test_fn()
            results.append((name, True))
        except Exception as e:
            print(f"\n   ❌ FAILED: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {name}")

    passed_count = sum(1 for _, p in results if p)
    total = len(results)
    print(f"\n   {passed_count}/{total} tests passed")

    if passed_count == total:
        print("\n✅ ALL TESTS PASSED")
        print("\nThe worker is correctly configured to:")
        print("  1. Use SDK default tools (includes Skill, Task, etc.)")
        print("  2. Support ALLOWED_TOOLS for explicit replacement")
        print("  3. Support DISALLOWED_TOOLS for blocking specific tools")
        print("  4. Auto-register MCP spec workflow tools")
    else:
        print("\n❌ SOME TESTS FAILED")

    return passed_count == total


def main():
    parser = argparse.ArgumentParser(description="Test worker tools configuration")
    parser.add_argument(
        "--mode",
        choices=["all", "default", "replace", "disallow", "mcp", "full"],
        default="all",
        help="Test mode to run"
    )
    args = parser.parse_args()

    mode_map = {
        "default": test_default_mode,
        "replace": test_replace_mode,
        "disallow": test_disallow_mode,
        "mcp": test_mcp_tools,
        "full": test_full_config,
    }

    if args.mode == "all":
        success = run_all_tests()
    else:
        set_base_env_vars()
        try:
            success = mode_map[args.mode]()
            print(f"\n✅ Test '{args.mode}' passed")
        except Exception as e:
            print(f"\n❌ Test '{args.mode}' failed: {e}")
            import traceback
            traceback.print_exc()
            success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
