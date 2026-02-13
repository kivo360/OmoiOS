#!/usr/bin/env python3
"""Direct GLM-4.6V agent using Anthropic SDK with Z.AI.

This bypasses Claude Agent SDK to have full control over API parameters.
"""

import asyncio
import httpx
import os
from uuid import uuid4
from anthropic import AsyncAnthropic

BASE_URL = "http://localhost:8000"

# Z.AI Configuration
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get(
    "ANTHROPIC_AUTH_TOKEN", ""
)
ANTHROPIC_BASE_URL = os.environ.get(
    "ANTHROPIC_BASE_URL", "https://api.z.ai/api/anthropic"
)
# GLM-4.6V: 128K context, 128K max output
MODEL = os.environ.get("ANTHROPIC_MODEL", "glm-4.6v")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "8192"))  # Configurable output limit


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


async def run_glm_agent(sandbox_id: str, initial_prompt: str, duration: int = 300):
    """Run GLM-4.6V agent with direct Anthropic SDK control."""

    if not ANTHROPIC_API_KEY:
        print("❌ No API key. Set ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN")
        return

    print(f"\n🤖 Starting GLM Agent for sandbox: {sandbox_id}")
    print(f"   Model: {MODEL}")
    print(f"   Max tokens: {MAX_TOKENS}")
    print(f"   Base URL: {ANTHROPIC_BASE_URL}")

    # Initialize Anthropic client with Z.AI endpoint
    anthropic = AsyncAnthropic(
        api_key=ANTHROPIC_API_KEY,
        base_url=ANTHROPIC_BASE_URL,
    )

    # Conversation history for multi-turn
    messages = []

    async with httpx.AsyncClient(timeout=30.0) as http_client:
        await report_event(
            http_client,
            sandbox_id,
            "agent.started",
            {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
            },
        )

        async def send_message(content: str, role: str = "user") -> str:
            """Send a message and get response."""
            messages.append({"role": role, "content": content})

            print(f"\n📤 Sending to {MODEL}...")
            await report_event(
                http_client,
                sandbox_id,
                "agent.thinking",
                {
                    "content": "Processing...",
                },
            )

            try:
                response = await anthropic.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    messages=messages,
                    system="You are a helpful coding assistant. Be concise but thorough.",
                )

                # Extract response text
                assistant_content = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        assistant_content += block.text

                # Add to history
                messages.append({"role": "assistant", "content": assistant_content})

                # Report to UI
                await report_event(
                    http_client,
                    sandbox_id,
                    "agent.message",
                    {
                        "content": assistant_content,
                        "role": "assistant",
                        "usage": {
                            "input_tokens": response.usage.input_tokens,
                            "output_tokens": response.usage.output_tokens,
                        },
                        "stop_reason": response.stop_reason,
                    },
                )

                print(
                    f"   💬 Response ({response.usage.output_tokens} tokens): {assistant_content[:100]}..."
                )
                print(f"   📊 Stop reason: {response.stop_reason}")

                if response.stop_reason == "max_tokens":
                    print("   ⚠️  Output truncated! Increase MAX_TOKENS env var.")

                return assistant_content

            except Exception as e:
                await report_event(
                    http_client, sandbox_id, "agent.error", {"error": str(e)}
                )
                print(f"   ❌ Error: {e}")
                return ""

        # Initial query
        await send_message(initial_prompt)

        # Multi-turn loop
        print(f"\n⏳ Waiting for messages ({duration}s timeout)...")
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
            user_messages = await poll_messages(http_client, sandbox_id)

            for msg in user_messages:
                content = msg.get("content", "")
                if content:
                    print(f"\n📥 User: {content[:50]}...")
                    await send_message(content)

                    await report_event(
                        http_client,
                        sandbox_id,
                        "agent.waiting",
                        {
                            "message": "Ready for follow-up messages",
                        },
                    )
                    print("\n⏳ Waiting for more messages...")

            await asyncio.sleep(0.5)

        await report_event(
            http_client,
            sandbox_id,
            "agent.completed",
            {
                "reason": "session_timeout",
                "total_messages": len(messages),
            },
        )
        print("\n✅ Session ended")


async def main():
    print("=" * 60)
    print("🚀 GLM-4.6V DIRECT AGENT (Anthropic SDK)")
    print("=" * 60)

    sandbox_id = f"glm-agent-{uuid4().hex[:8]}"
    print(f"\n🆔 Sandbox ID: {sandbox_id}")
    print("   → Open sandbox-ui-sample.html")
    print(f"   → Enter: {sandbox_id}")

    # Config display
    print("\n" + "-" * 40)
    print("📋 Configuration:")
    print(f"   API Key: {'✅ Set' if ANTHROPIC_API_KEY else '❌ Missing'}")
    print(f"   Base URL: {ANTHROPIC_BASE_URL}")
    print(f"   Model: {MODEL}")
    print(f"   Max Tokens: {MAX_TOKENS}")
    print("\n   💡 To increase output limit:")
    print("      export MAX_TOKENS=16384")

    if not ANTHROPIC_API_KEY:
        print("\n❌ Set API key first:")
        print("   export ANTHROPIC_API_KEY=your_key")
        return

    # Check backend
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{BASE_URL}/health")
            if resp.status_code != 200:
                print(f"❌ Backend error: {resp.status_code}")
                return
            print("✅ Backend healthy")
    except Exception as e:
        print(f"❌ Backend unavailable: {e}")
        return

    print("\n" + "-" * 40)

    initial_prompt = "List the files in the current directory and briefly describe what this project is about."
    await run_glm_agent(sandbox_id, initial_prompt, duration=120)

    print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
