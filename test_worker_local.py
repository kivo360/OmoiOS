#!/usr/bin/env python3
"""
Test the sandbox worker locally (without Daytona).

This simulates running the worker as if it were inside a sandbox,
but runs locally for testing the webhook/message flow.

Uses the Claude Agent SDK (claude_code_sdk) for real Claude interactions.

Usage:
    # Make sure backend is running first
    python test_worker_local.py

    # With custom initial prompt
    INITIAL_PROMPT="Analyze this codebase" python test_worker_local.py
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))


def main():
    """Run worker locally for testing."""
    from uuid import uuid4

    # Set environment for local testing
    sandbox_id = f"local-worker-{uuid4().hex[:8]}"

    # Use existing env vars or defaults
    os.environ.setdefault("SANDBOX_ID", sandbox_id)
    os.environ.setdefault("CALLBACK_URL", "http://localhost:8000")
    os.environ.setdefault("POLL_INTERVAL", "0.5")
    os.environ.setdefault("HEARTBEAT_INTERVAL", "30")
    os.environ.setdefault("MAX_TURNS", "50")
    os.environ.setdefault("PERMISSION_MODE", "acceptEdits")
    os.environ.setdefault("ALLOWED_TOOLS", "Read,Write,Bash,Glob,Grep")

    # Default initial prompt for testing
    os.environ.setdefault(
        "INITIAL_PROMPT",
        "List the files in the current directory and briefly describe what you see.",
    )

    print("=" * 60)
    print("🧪 LOCAL WORKER TEST")
    print("=" * 60)
    print(f"\n🆔 Sandbox ID: {sandbox_id}")
    print("   → Open sandbox-ui-sample.html in browser")
    print(f"   → Enter sandbox ID: {sandbox_id}")
    print("   → Click Connect to see events")
    print("   → Send messages to interact with the worker")
    print("\n" + "-" * 60)

    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get(
        "ANTHROPIC_AUTH_TOKEN"
    )
    if not api_key:
        print("\n❌ No API key set!")
        print("   export ANTHROPIC_API_KEY=your_key")
        print("   # or")
        print("   export ANTHROPIC_AUTH_TOKEN=your_token")
        return 1

    # Import and run worker
    try:
        import asyncio

        from omoi_os.workers.sandbox_agent_worker import main as worker_main

        return asyncio.run(worker_main())
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("   Make sure you're in the project directory")
        print("   and dependencies are installed: uv sync")
        return 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 0


if __name__ == "__main__":
    sys.exit(main())
