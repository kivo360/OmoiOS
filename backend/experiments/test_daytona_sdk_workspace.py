#!/usr/bin/env python3
"""
Experiment: Test OpenHandsDaytonaWorkspace with SDK Conversation

This script tests whether our Daytona workspace adapter can work with
the OpenHands SDK Conversation class.

Expected outcome based on SDK analysis:
- Current implementation WILL FAIL because OpenHandsDaytonaWorkspace
  doesn't inherit from LocalWorkspace (SDK assertion at line 93)

Run with: uv run python experiments/test_daytona_sdk_workspace.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_current_implementation():
    """Test 1: OLD OpenHandsDaytonaWorkspace with SDK (expected to FAIL)."""
    print("\n" + "=" * 60)
    print("TEST 1: OLD OpenHandsDaytonaWorkspace (expected to FAIL)")
    print("=" * 60)

    from omoi_os.config import load_daytona_settings
    from omoi_os.workspace.daytona import OpenHandsDaytonaWorkspace
    from openhands.sdk.workspace import LocalWorkspace

    settings = load_daytona_settings()

    if not settings.api_key:
        print("⚠️  DAYTONA_API_KEY not set - skipping")
        return False

    workspace = OpenHandsDaytonaWorkspace(
        working_dir="/tmp/test-workspace",
        project_id="test-project",
        settings=settings,
    )

    is_local = isinstance(workspace, LocalWorkspace)
    print(f"isinstance(workspace, LocalWorkspace): {is_local}")
    print("Expected: False (old adapter doesn't inherit)")
    return not is_local  # Pass if it's NOT a LocalWorkspace (proving the issue)


def test_new_sdk_adapter():
    """Test 2: NEW DaytonaLocalWorkspace with SDK (should PASS)."""
    print("\n" + "=" * 60)
    print("TEST 2: NEW DaytonaLocalWorkspace with SDK Conversation")
    print("=" * 60)

    from omoi_os.config import load_daytona_settings
    from omoi_os.workspace.daytona_sdk import DaytonaLocalWorkspace
    from openhands.sdk import LLM, Agent, Conversation
    from openhands.sdk.workspace import LocalWorkspace
    from pydantic import SecretStr

    settings = load_daytona_settings()

    if not settings.api_key:
        print("⚠️  DAYTONA_API_KEY not set - skipping")
        return False

    workspace = DaytonaLocalWorkspace(
        working_dir="/tmp/test-daytona-sdk",
        daytona_api_key=settings.api_key,
        daytona_api_url=settings.api_url,
        daytona_target=settings.target,
        sandbox_image=settings.image,
        project_id="sdk-test",
    )

    is_local = isinstance(workspace, LocalWorkspace)
    print(f"isinstance(workspace, LocalWorkspace): {is_local}")

    if not is_local:
        print("❌ FAIL: Should inherit from LocalWorkspace")
        return False

    # Create agent (no tools)
    llm = LLM(
        model="anthropic/claude-sonnet-4-5-20250929",
        api_key=SecretStr("test-key"),
    )
    agent = Agent(llm=llm, tools=[])

    try:
        conversation = Conversation(
            agent=agent,
            workspace=workspace,
        )
        print(f"✓ Conversation created: {conversation.id}")
        print(f"  Workspace type: {type(conversation.workspace).__name__}")
        conversation.close()
        return True

    except AssertionError as e:
        print(f"❌ AssertionError: {e}")
        return False
    except Exception as e:
        print(f"❌ {type(e).__name__}: {e}")
        return False


def test_daytona_sandbox_operations():
    """Test 3: DaytonaLocalWorkspace sandbox operations."""
    print("\n" + "=" * 60)
    print("TEST 3: DaytonaLocalWorkspace Sandbox Operations")
    print("=" * 60)

    from omoi_os.config import load_daytona_settings
    from omoi_os.workspace.daytona_sdk import DaytonaLocalWorkspace

    settings = load_daytona_settings()

    if not settings.api_key:
        print("⚠️  DAYTONA_API_KEY not set - skipping")
        return False

    workspace = DaytonaLocalWorkspace(
        working_dir="/tmp/test-daytona-ops",
        daytona_api_key=settings.api_key,
        daytona_api_url=settings.api_url,
        daytona_target=settings.target,
        sandbox_image=settings.image,
        project_id="ops-test",
    )

    print("Creating Daytona sandbox...")
    try:
        with workspace:
            print(f"✓ Sandbox created: {workspace.sandbox_id}")

            # Test command execution
            print("\nTesting execute_command...")
            result = workspace.execute_command("echo hello")
            print(f"  exit_code: {result.exit_code}")
            print(f"  stdout: {result.stdout.strip()}")

            # Test Python
            result = workspace.execute_command("python3 --version")
            print(f"  Python: {result.stdout.strip()}")

        print("\n✓ Sandbox operations successful!")
        return True

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_local_workspace_baseline():
    """Test 4: Baseline - LocalWorkspace with Conversation."""
    print("\n" + "=" * 60)
    print("TEST 4: Baseline - LocalWorkspace (no API call)")
    print("=" * 60)

    import tempfile

    from openhands.sdk import LLM, Agent, Conversation
    from openhands.sdk.workspace import LocalWorkspace
    from pydantic import SecretStr

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = LocalWorkspace(working_dir=tmpdir)
        print(f"✓ Created LocalWorkspace at {tmpdir}")

        llm = LLM(
            model="anthropic/claude-sonnet-4-5-20250929",
            api_key=SecretStr("test-key"),
        )
        agent = Agent(llm=llm, tools=[])

        try:
            conversation = Conversation(
                agent=agent,
                workspace=workspace,
            )
            print(f"✓ Conversation created: {conversation.id}")
            conversation.close()
            return True

        except Exception as e:
            print(f"\n❌ Error: {type(e).__name__}: {e}")
            return False


def main():
    print("=" * 60)
    print("DAYTONA SDK WORKSPACE INTEGRATION EXPERIMENTS")
    print("=" * 60)

    results = {}

    # Test 1: OLD adapter (expected to show issue)
    results["old_adapter_fails"] = test_current_implementation()

    # Test 2: NEW SDK-compatible adapter
    results["new_adapter_works"] = test_new_sdk_adapter()

    # Test 3: Sandbox operations
    results["sandbox_ops"] = test_daytona_sandbox_operations()

    # Test 4: Baseline LocalWorkspace
    results["baseline"] = test_local_workspace_baseline()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, passed in results.items():
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")

    print("\nConclusions:")
    if results["old_adapter_fails"] and results["new_adapter_works"]:
        print("  ✓ OLD OpenHandsDaytonaWorkspace doesn't inherit LocalWorkspace")
        print("  ✓ NEW DaytonaLocalWorkspace works with SDK Conversation")
        print("  ✓ Use DaytonaLocalWorkspace for SDK integration")


if __name__ == "__main__":
    main()
