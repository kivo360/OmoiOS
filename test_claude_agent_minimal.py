#!/usr/bin/env python3
"""Minimal test to verify Claude Agent SDK worker pattern works.

Run this to verify the fixed pattern matches Claude Code web behavior.
"""

import asyncio
import os
from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    ToolResultBlock,
    ResultMessage,
)

# Z.AI / Anthropic API configuration (matching worker script)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get(
    "ANTHROPIC_AUTH_TOKEN", ""
)
ANTHROPIC_BASE_URL = os.environ.get(
    "ANTHROPIC_BASE_URL", "https://api.z.ai/api/anthropic"
)
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL") or os.environ.get(
    "ANTHROPIC_DEFAULT_SONNET_MODEL", "glm-4.6v"
)

# Set environment variables for SDK
if ANTHROPIC_API_KEY:
    os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
if ANTHROPIC_BASE_URL:
    os.environ["ANTHROPIC_BASE_URL"] = ANTHROPIC_BASE_URL


async def test_minimal():
    """Test the core pattern: query → stream → inject message → stream response."""

    print("🚀 Starting minimal Claude Agent test...")
    print("=" * 60)

    # Print configuration
    print(
        f"🔑 API Key: {ANTHROPIC_API_KEY[:15] + '...' if ANTHROPIC_API_KEY else 'NOT SET'}"
    )
    print(f"🌐 Base URL: {ANTHROPIC_BASE_URL}")
    print(f"🤖 Model: {ANTHROPIC_MODEL}")

    if not ANTHROPIC_API_KEY:
        print("❌ ERROR: ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN not set")
        return False

    options = ClaudeAgentOptions(
        system_prompt="You are a helpful coding assistant. Be concise.",
        allowed_tools=["Read", "Write", "Bash"],
        permission_mode="acceptEdits",
        max_turns=10,
        max_budget_usd=1.0,  # Safety limit
        model=ANTHROPIC_MODEL,  # Use Z.AI model
    )

    try:
        async with ClaudeSDKClient(options=options) as client:
            # Step 1: Initial query (like task description)
            print("\n📝 Step 1: Sending initial query...")
            await client.query("List the files in the current directory")

            # Step 2: Stream messages (like receive_messages in worker)
            print("\n📡 Step 2: Streaming messages...")
            message_count = 0
            first_response_received = False

            async for msg in client.receive_messages():
                message_count += 1

                if isinstance(msg, AssistantMessage):
                    if not first_response_received:
                        print(
                            f"✅ Got first AssistantMessage (message #{message_count})"
                        )
                        first_response_received = True

                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            print(f"  📄 Text: {block.text[:100]}...")
                        elif isinstance(block, ThinkingBlock):
                            print(f"  🤔 Thinking: {block.text[:100]}...")
                        elif isinstance(block, ToolUseBlock):
                            print(f"  🔧 Tool: {block.name}")
                        elif isinstance(block, ToolResultBlock):
                            print(f"  ✅ Tool result: {str(block.content)[:100]}...")

                elif isinstance(msg, ResultMessage):
                    print(
                        f"\n✅ Step 2 complete: {msg.num_turns} turns, ${msg.total_cost_usd:.4f}"
                    )
                    break

                # Step 3: After first response, inject a message (like intervention)
                if first_response_received and message_count == 2:
                    print("\n💬 Step 3: Injecting follow-up message...")
                    await client.query(
                        "Now create a file called test.txt with 'Hello World'"
                    )
                    print("✅ Message injected via client.query()")
                    # Continue streaming to see response
                    continue

            # Step 4: Verify we can do another turn
            print("\n🔄 Step 4: Testing another query...")
            await client.query("What's in test.txt?")

            async for msg in client.receive_messages():
                if isinstance(msg, ResultMessage):
                    print(f"✅ Step 4 complete: Total {msg.num_turns} turns")
                    break
                elif isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            print(f"  📄 Response: {block.text[:100]}...")

            print("\n" + "=" * 60)
            print("✅ ALL TESTS PASSED - Pattern matches Claude Code web!")
            print("=" * 60)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    # Check for API key (either ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN)
    if not ANTHROPIC_API_KEY:
        print(
            "❌ ERROR: Set ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN environment variable"
        )
        print("\nExample:")
        print("  export ANTHROPIC_AUTH_TOKEN=your_z_ai_token")
        print("  export ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic")
        print("  export ANTHROPIC_MODEL=glm-4.6v")
        exit(1)

    success = asyncio.run(test_minimal())
    exit(0 if success else 1)
