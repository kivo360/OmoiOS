#!/usr/bin/env python3
"""Real Claude Agent with event streaming to UI.

Uses ClaudeSDKClient for proper multi-turn conversations.
User can send follow-up messages via the UI between responses.
"""

import asyncio
import httpx
import os
from uuid import uuid4

# Claude Agent SDK imports
try:
    from claude_agent_sdk import ClaudeSDKClient, ClaudeCodeOptions
    from claude_agent_sdk.types import (
        AssistantMessage,
        ResultMessage,
    )

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    print("⚠️  Claude Agent SDK not installed. Run: pip install claude-code-sdk")

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/api/v1/ws/events"

# Z.AI / Anthropic API configuration
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get(
    "ANTHROPIC_AUTH_TOKEN", ""
)
ANTHROPIC_BASE_URL = os.environ.get(
    "ANTHROPIC_BASE_URL", "https://api.z.ai/api/anthropic"
)
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL") or os.environ.get(
    "ANTHROPIC_DEFAULT_SONNET_MODEL", "claude-sonnet-4-20250514"
)


async def report_event(
    client: httpx.AsyncClient, sandbox_id: str, event_type: str, event_data: dict
):
    """Report an event to the backend for UI streaming."""
    try:
        await client.post(
            f"{BASE_URL}/api/v1/sandboxes/{sandbox_id}/events",
            json={
                "event_type": event_type,
                "event_data": event_data,
                "source": "agent",
            },
        )
    except Exception as e:
        print(f"   ⚠️  Failed to report event: {e}")


async def poll_messages(client: httpx.AsyncClient, sandbox_id: str) -> list:
    """Poll for user-injected messages."""
    try:
        resp = await client.get(f"{BASE_URL}/api/v1/sandboxes/{sandbox_id}/messages")
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []


async def process_response(
    http_client: httpx.AsyncClient, sandbox_id: str, client: "ClaudeSDKClient"
):
    """Process all messages from a query response."""
    try:
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                content = ""
                for block in message.content:
                    if hasattr(block, "text"):
                        content += block.text
                    elif hasattr(block, "name"):  # Tool use
                        await report_event(
                            http_client,
                            sandbox_id,
                            "agent.tool_use",
                            {
                                "tool": block.name,
                                "input": (
                                    str(block.input)[:200]
                                    if hasattr(block, "input")
                                    else ""
                                ),
                            },
                        )
                        print(f"   🔧 Tool: {block.name}")

                if content:
                    await report_event(
                        http_client,
                        sandbox_id,
                        "agent.message",
                        {
                            "content": content,
                            "role": "assistant",
                        },
                    )
                    print(f"   💬 Assistant: {content[:80]}...")

            elif isinstance(message, ResultMessage):
                await report_event(
                    http_client,
                    sandbox_id,
                    "agent.turn_completed",
                    {
                        "cost_usd": (
                            message.cost_usd if hasattr(message, "cost_usd") else 0
                        ),
                        "duration_ms": (
                            message.duration_ms
                            if hasattr(message, "duration_ms")
                            else 0
                        ),
                        "turns": (
                            message.num_turns if hasattr(message, "num_turns") else 0
                        ),
                    },
                )
                print("   ✅ Turn completed")
                return message
    except Exception as e:
        await report_event(
            http_client,
            sandbox_id,
            "agent.error",
            {
                "error": str(e),
            },
        )
        print(f"   ❌ Error: {e}")
        raise


async def run_claude_agent(sandbox_id: str, initial_prompt: str, duration: int = 300):
    """Run a real Claude agent with multi-turn conversation support."""

    if not SDK_AVAILABLE:
        print("❌ Claude Agent SDK not available")
        return

    if not ANTHROPIC_API_KEY:
        print("❌ No API key set. Export ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN")
        return

    print(f"\n🤖 Starting Claude Agent for sandbox: {sandbox_id}")
    print(f"   Model: {ANTHROPIC_MODEL}")
    print(f"   Initial prompt: {initial_prompt[:50]}...")
    print(f"   Session duration: {duration}s")

    # Set environment for SDK
    os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
    if ANTHROPIC_BASE_URL:
        os.environ["ANTHROPIC_BASE_URL"] = ANTHROPIC_BASE_URL

    options = ClaudeCodeOptions(
        max_turns=20,
    )

    async with httpx.AsyncClient(timeout=30.0) as http_client:
        await report_event(
            http_client,
            sandbox_id,
            "agent.started",
            {
                "model": ANTHROPIC_MODEL,
                "prompt": initial_prompt[:100],
            },
        )

        async with ClaudeSDKClient(options=options) as client:
            # Initial query
            print("\n📤 Sending initial prompt...")
            await report_event(
                http_client,
                sandbox_id,
                "agent.query",
                {
                    "content": initial_prompt,
                    "source": "system",
                },
            )

            await client.query(initial_prompt)
            await process_response(http_client, sandbox_id, client)

            # Multi-turn loop - poll for user messages
            print(
                f"\n⏳ Waiting for user messages (type in UI, {duration}s timeout)..."
            )
            await report_event(
                http_client,
                sandbox_id,
                "agent.waiting",
                {
                    "message": "Ready for follow-up messages",
                },
            )

            start_time = asyncio.get_event_loop().time()

            while asyncio.get_event_loop().time() - start_time < duration:
                # Poll for user messages
                messages = await poll_messages(http_client, sandbox_id)

                for msg in messages:
                    content = msg.get("content", "")
                    if content:
                        print(f"\n📥 User message: {content[:50]}...")
                        await report_event(
                            http_client,
                            sandbox_id,
                            "agent.query",
                            {
                                "content": content,
                                "source": "user",
                            },
                        )

                        # Send to Claude
                        await client.query(content)
                        await process_response(http_client, sandbox_id, client)

                        # Report ready for more
                        await report_event(
                            http_client,
                            sandbox_id,
                            "agent.waiting",
                            {
                                "message": "Ready for follow-up messages",
                            },
                        )
                        print("\n⏳ Waiting for more messages...")

                await asyncio.sleep(0.5)  # Poll every 500ms

            await report_event(
                http_client,
                sandbox_id,
                "agent.completed",
                {
                    "reason": "session_timeout",
                },
            )
            print("\n✅ Session ended (timeout)")


async def main():
    """Main entry point."""
    print("=" * 60)
    print("🚀 REAL CLAUDE AGENT - MULTI-TURN")
    print("=" * 60)

    # Generate sandbox ID
    sandbox_id = f"claude-agent-{uuid4().hex[:8]}"
    print(f"\n🆔 Sandbox ID: {sandbox_id}")
    print("   → Open sandbox-ui-sample.html")
    print(f"   → Enter this ID: {sandbox_id}")
    print("   → Click Connect to see events")
    print("   → Type messages to continue the conversation!")

    # Check backend
    print("\n" + "-" * 40)
    print("📋 Checking backend...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{BASE_URL}/health")
            if resp.status_code == 200:
                print(f"✅ Backend healthy: {resp.json()}")
            else:
                print(f"❌ Backend returned: {resp.status_code}")
                return
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        return

    # Show config
    print("\n" + "-" * 40)
    print("📋 Configuration:")
    print(f"   API Key: {'✅ Set' if ANTHROPIC_API_KEY else '❌ Missing'}")
    print(f"   Base URL: {ANTHROPIC_BASE_URL}")
    print(f"   Model: {ANTHROPIC_MODEL}")

    if not ANTHROPIC_API_KEY:
        print("\n❌ Set ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN first:")
        print("   export ANTHROPIC_API_KEY=your_key")
        return

    # Run agent
    print("\n" + "-" * 40)
    print("🤖 Starting agent...")
    print("   (Send messages via the UI)")
    print("-" * 40)

    initial_prompt = "List the files in the current directory and briefly describe what this project is about."

    await run_claude_agent(sandbox_id, initial_prompt, duration=120)

    print("\n" + "=" * 60)
    print("✅ Session complete")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
