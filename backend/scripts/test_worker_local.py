#!/usr/bin/env python3
"""Test the Claude sandbox worker locally before deploying to sandbox.

This script runs the worker with test environment variables to verify:
1. Worker initializes correctly
2. SDK client connects
3. Task description is read properly
4. Worker starts processing

Usage:
    cd backend
    set -a && source .env.local && set +a
    uv run python scripts/test_worker_local.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up test environment variables
os.environ["SANDBOX_ID"] = "test-sandbox-local"
os.environ["TASK_ID"] = "test-task-12345"
os.environ["AGENT_ID"] = "test-agent-12345"
os.environ["CALLBACK_URL"] = "http://localhost:18000"
os.environ["TICKET_ID"] = "test-ticket-12345"
os.environ["TICKET_TITLE"] = "Test Task: Calculate Binomial Coefficient"
os.environ[
    "TICKET_DESCRIPTION"
] = """Calculate the binomial coefficient C(50,25) which equals:
    factorial(50) / (factorial(25) * factorial(25))

Use Python to compute this exactly. The answer should be: 126410606437752

Step 1: Create a file called binomial.py with a function to calculate C(n, k)
Step 2: Then modify the file to add a main() function that calls the function with n=50, k=25 and prints the result"""
os.environ["PHASE_ID"] = "PHASE_IMPLEMENTATION"
os.environ["PERMISSION_MODE"] = "acceptEdits"
os.environ["ALLOWED_TOOLS"] = "Read,Write,Bash,Edit,Glob,Grep,Task,Skill"
os.environ["ENABLE_SKILLS"] = "true"
os.environ["ENABLE_SUBAGENTS"] = "true"
os.environ["SETTING_SOURCES"] = "user,project"
os.environ["CWD"] = "/tmp/test_workspace"
os.environ["MAX_TURNS"] = "10"  # Limit for testing
os.environ["MAX_BUDGET_USD"] = "1.0"  # Limit for testing

# Create test workspace
test_workspace = Path("/tmp/test_workspace")
test_workspace.mkdir(exist_ok=True)

# Ensure we have API key
if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("LLM_API_KEY"):
    print("⚠️  Warning: ANTHROPIC_API_KEY or LLM_API_KEY not set")
    print("   The worker will fail to initialize without an API key")
    print("   Set it in .env.local or export it before running")

print("=" * 70)
print("🧪 LOCAL WORKER TEST")
print("=" * 70)
print("\n📋 Test Configuration:")
print(f"   Sandbox ID: {os.environ['SANDBOX_ID']}")
print(f"   Task ID: {os.environ['TASK_ID']}")
print(f"   Callback URL: {os.environ['CALLBACK_URL']}")
print(f"   Workspace: {test_workspace}")
print(f"   Ticket Title: {os.environ['TICKET_TITLE']}")
print(f"   Ticket Description: {os.environ['TICKET_DESCRIPTION'][:80]}...")
print()

# Check if API key is set
api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("LLM_API_KEY")
if api_key:
    print(f"   ✅ API Key: {'*' * 20}...{api_key[-4:]}")
else:
    print("   ❌ API Key: NOT SET")
    print("\n   Please set ANTHROPIC_API_KEY or LLM_API_KEY in .env.local")
    sys.exit(1)

print("\n🚀 Starting worker...")
print("   (This will test SDK initialization and task processing)")
print("   (Press Ctrl+C to stop)\n")
print("=" * 70)
print()

# Import and run the worker
try:
    from omoi_os.workers.claude_sandbox_worker import main

    # Run with timeout to prevent hanging
    try:
        result = asyncio.run(asyncio.wait_for(main(), timeout=120.0))
        print("\n" + "=" * 70)
        print("✅ Worker test completed")
        print("=" * 70)
    except asyncio.TimeoutError:
        print("\n" + "=" * 70)
        print("⏰ Worker test timed out after 2 minutes")
        print("   This is normal - the worker runs indefinitely")
        print("   The test verified that the worker started correctly")
        print("=" * 70)
except KeyboardInterrupt:
    print("\n\n⚠️  Test interrupted by user")
    sys.exit(0)
except Exception as e:
    print(f"\n❌ Worker test failed: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
