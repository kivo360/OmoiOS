#!/usr/bin/env python
"""Example: Using OpenHands Agent with Daytona Workspace.

This example shows how to run OpenHands agents with Daytona Cloud sandboxes
as the execution backend.

## Setup

1. Set your Daytona API key:
   export DAYTONA_API_KEY="dtn_your_key_here"

2. Set workspace mode to daytona:
   export WORKSPACE_MODE=daytona

3. Run this script:
   uv run python examples/openhands_daytona_example.py
"""

import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_workspace_factory_daytona():
    """Test OpenHandsWorkspaceFactory with Daytona mode."""
    from omoi_os.config import load_daytona_settings, load_workspace_settings
    from omoi_os.services.workspace_manager import OpenHandsWorkspaceFactory

    print("=" * 60)
    print("Testing OpenHands Workspace Factory with Daytona")
    print("=" * 60)

    # Check configuration
    ws_settings = load_workspace_settings()
    daytona_settings = load_daytona_settings()

    print(f"\nWorkspace Mode: {ws_settings.mode}")
    print(f"Daytona API Key: {'***' + daytona_settings.api_key[-8:] if daytona_settings.api_key else 'NOT SET'}")
    print(f"Daytona Target: {daytona_settings.target}")

    if ws_settings.mode != "daytona":
        print("\n⚠️  Workspace mode is not 'daytona'. Set WORKSPACE_MODE=daytona")
        print("    For now, testing with explicit Daytona workspace creation...")

    # Create factory
    factory = OpenHandsWorkspaceFactory(settings=ws_settings)

    # For testing, we'll create a Daytona workspace directly
    if daytona_settings.api_key:
        print("\n📦 Creating Daytona workspace for project 'test-project'...")

        from omoi_os.workspace import OpenHandsDaytonaWorkspace

        workspace = OpenHandsDaytonaWorkspace(
            working_dir="/tmp/test-project",
            project_id="test-project",
            settings=daytona_settings,
        )

        with workspace:
            print(f"✓ Sandbox ID: {workspace.sandbox_id}")

            # Execute some commands
            result = workspace.execute_command("echo 'Hello from Daytona!'")
            print(f"✓ Command output: {result.stdout.strip()}")

            result = workspace.execute_command("python --version")
            print(f"✓ Python version: {result.stdout.strip()}")

            result = workspace.execute_command("uname -a")
            print(f"✓ System: {result.stdout.strip()[:60]}...")

            # Test file operations
            workspace._daytona_workspace.write_file("/tmp/test.txt", "Hello World")
            content = workspace._daytona_workspace.read_file("/tmp/test.txt")
            print(f"✓ File write/read: {content.decode().strip()}")

        print("✓ Sandbox cleaned up")
    else:
        print("\n❌ DAYTONA_API_KEY not set. Cannot test Daytona workspace.")
        print("   Set it with: export DAYTONA_API_KEY='dtn_...'")


def test_agent_executor_with_daytona():
    """Test AgentExecutor with Daytona workspace (requires full setup)."""
    from omoi_os.config import load_daytona_settings, load_workspace_settings

    print("\n" + "=" * 60)
    print("Testing AgentExecutor with Daytona (optional)")
    print("=" * 60)

    ws_settings = load_workspace_settings()
    daytona_settings = load_daytona_settings()

    if ws_settings.mode != "daytona":
        print("\n⚠️  To test AgentExecutor with Daytona:")
        print("   1. export WORKSPACE_MODE=daytona")
        print("   2. export DAYTONA_API_KEY='dtn_...'")
        print("   3. export LLM_API_KEY='your_llm_key'")
        print("   4. Re-run this script")
        return

    if not daytona_settings.api_key:
        print("\n❌ DAYTONA_API_KEY not set")
        return

    # Check for LLM key
    import os
    llm_key = os.environ.get("LLM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not llm_key:
        print("\n❌ LLM_API_KEY not set. Cannot test AgentExecutor.")
        return

    print("\n📦 Creating AgentExecutor with Daytona workspace...")
    from omoi_os.services.agent_executor import AgentExecutor

    try:
        executor = AgentExecutor.create_for_project(
            project_id="test-daytona-agent",
            phase_id="PHASE_IMPLEMENTATION",
            planning_mode=False,
        )
        print(f"✓ AgentExecutor created")
        print(f"  Workspace: {executor.workspace_dir}")
        print(f"  Mode: {ws_settings.mode}")

        # Note: Full agent execution would require additional setup
        print("\n✓ AgentExecutor initialized successfully with Daytona backend")

    except Exception as e:
        print(f"\n❌ AgentExecutor creation failed: {e}")


if __name__ == "__main__":
    test_workspace_factory_daytona()
    test_agent_executor_with_daytona()

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print("""
To use Daytona as your agent workspace backend:

1. Set environment variables:
   export DAYTONA_API_KEY="dtn_your_key"
   export WORKSPACE_MODE="daytona"

2. Or update config/base.yaml:
   workspace:
     mode: daytona

   daytona:
     api_key: ${DAYTONA_API_KEY}
     target: us
     snapshot: python:3.12

3. Then your agents will automatically use Daytona sandboxes
   for isolated, secure code execution.
""")
