#!/usr/bin/env python3
"""
Standalone Sandbox Agent Worker - Deploy to Daytona sandboxes.

This is a STANDALONE script with NO local dependencies.
Just copy this file + install deps:

    pip install httpx claude-agent-sdk
    python standalone_sandbox_worker.py

Environment Variables (required):
    SANDBOX_ID          - Unique sandbox identifier
    CALLBACK_URL        - Main server base URL (e.g., https://api.example.com)
    ANTHROPIC_API_KEY   - API key for Claude (or Z.AI token)

Environment Variables (optional - model/API):
    MODEL               - Model to use (e.g., "glm-4.6v" for Z.AI, default: Claude's default)
    ANTHROPIC_BASE_URL  - Custom API endpoint (e.g., "https://api.z.ai/api/anthropic" for GLM)

Environment Variables (optional - skills):
    ENABLE_SKILLS       - Set to "true" to enable Claude skills (adds "Skill" to allowed_tools)
    SETTING_SOURCES     - Comma-separated: "user,project" to load ~/.claude/skills and .claude/skills

Environment Variables (optional - behavior):
    INITIAL_PROMPT      - Initial task prompt
    POLL_INTERVAL       - Message poll interval in seconds (default: 0.5)
    HEARTBEAT_INTERVAL  - Heartbeat interval in seconds (default: 30)
    MAX_TURNS           - Max turns per response (default: 50)
    PERMISSION_MODE     - SDK permission mode (default: acceptEdits)
    SYSTEM_PROMPT       - Custom system prompt
    ALLOWED_TOOLS       - Comma-separated tool list (default: Read,Write,Bash,Glob,Grep)
    CWD                 - Working directory (default: current directory)

Example with GLM:
    SANDBOX_ID=my-sandbox \\
    CALLBACK_URL=http://localhost:8000 \\
    ANTHROPIC_API_KEY=your_z_ai_token \\
    ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic \\
    MODEL=glm-4.6v \\
    python standalone_sandbox_worker.py

Example with Skills:
    ENABLE_SKILLS=true \\
    SETTING_SOURCES=user,project \\
    python standalone_sandbox_worker.py
"""

import asyncio
import os
import signal
import sys
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

import httpx

# Try to import Claude Agent SDK
try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ClaudeSDKClient,
        ResultMessage,
        TextBlock,
        ThinkingBlock,
        ToolResultBlock,
        ToolUseBlock,
    )

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False


# =============================================================================
# Configuration
# =============================================================================


class WorkerConfig:
    """Worker configuration from environment variables."""

    def __init__(self):
        # Core settings
        self.sandbox_id = os.environ.get("SANDBOX_ID", f"sandbox-{uuid4().hex[:8]}")
        self.callback_url = os.environ.get("CALLBACK_URL", "http://localhost:8000")
        self.api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get(
            "ANTHROPIC_AUTH_TOKEN", ""
        )
        self.initial_prompt = os.environ.get("INITIAL_PROMPT", "")
        self.poll_interval = float(os.environ.get("POLL_INTERVAL", "0.5"))
        self.heartbeat_interval = int(os.environ.get("HEARTBEAT_INTERVAL", "30"))

        # Model settings (for GLM or other models)
        self.model = os.environ.get("MODEL")  # e.g., "glm-4.6v" or None for default
        self.api_base_url = os.environ.get(
            "ANTHROPIC_BASE_URL"
        )  # e.g., "https://api.z.ai/api/anthropic"

        # SDK settings
        self.max_turns = int(os.environ.get("MAX_TURNS", "50"))
        self.permission_mode = os.environ.get("PERMISSION_MODE", "acceptEdits")
        self.system_prompt = os.environ.get(
            "SYSTEM_PROMPT",
            "You are a helpful coding assistant working in a sandboxed environment. "
            "You have access to the filesystem and can execute commands. "
            "Be thorough but concise in your responses.",
        )

        # Tools - parse comma-separated list
        default_tools = "Read,Write,Bash,Glob,Grep"
        self.allowed_tools = os.environ.get("ALLOWED_TOOLS", default_tools).split(",")

        # Skills support
        self.enable_skills = os.environ.get("ENABLE_SKILLS", "false").lower() == "true"
        if self.enable_skills and "Skill" not in self.allowed_tools:
            self.allowed_tools.append("Skill")

        # Setting sources for loading CLAUDE.md and skills
        # Options: "user", "project", or comma-separated list
        setting_sources_str = os.environ.get("SETTING_SOURCES", "")
        if setting_sources_str:
            self.setting_sources = [s.strip() for s in setting_sources_str.split(",")]
        elif self.enable_skills:
            self.setting_sources = [
                "user",
                "project",
            ]  # Load skills from both locations
        else:
            self.setting_sources = None

        self.cwd = os.environ.get("CWD", os.getcwd())

    def validate(self) -> list[str]:
        """Validate configuration, return list of errors."""
        errors = []
        if not self.api_key:
            errors.append("ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN required")
        if not self.callback_url:
            errors.append("CALLBACK_URL required")
        return errors

    def to_dict(self) -> dict:
        """Return config as dict (redacting sensitive values)."""
        return {
            "sandbox_id": self.sandbox_id,
            "callback_url": self.callback_url,
            "api_key": "***" if self.api_key else "NOT SET",
            "model": self.model or "default",
            "api_base_url": self.api_base_url or "default",
            "poll_interval": self.poll_interval,
            "heartbeat_interval": self.heartbeat_interval,
            "max_turns": self.max_turns,
            "permission_mode": self.permission_mode,
            "allowed_tools": self.allowed_tools,
            "enable_skills": self.enable_skills,
            "setting_sources": self.setting_sources,
            "cwd": self.cwd,
        }

    def to_sdk_options(self) -> "ClaudeAgentOptions":
        """Create ClaudeAgentOptions from config."""
        # Build environment variables for the CLI subprocess
        env = {"ANTHROPIC_API_KEY": self.api_key}
        if self.api_base_url:
            env["ANTHROPIC_BASE_URL"] = self.api_base_url

        # Build options dict
        options_kwargs = {
            "system_prompt": self.system_prompt,
            "allowed_tools": self.allowed_tools,
            "permission_mode": self.permission_mode,
            "max_turns": self.max_turns,
            "cwd": self.cwd,
            "env": env,
        }

        # Add model if specified
        if self.model:
            options_kwargs["model"] = self.model

        # Add setting sources for skills/CLAUDE.md
        if self.setting_sources:
            options_kwargs["setting_sources"] = self.setting_sources

        return ClaudeAgentOptions(**options_kwargs)


# =============================================================================
# Event Reporter (Webhook Client)
# =============================================================================


class EventReporter:
    """Reports events back to main server via HTTP POST."""

    def __init__(self, config: WorkerConfig):
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()

    async def report(
        self,
        event_type: str,
        event_data: dict[str, Any],
        source: str = "agent",
    ) -> bool:
        """Report event to main server."""
        if not self.client:
            return False

        url = f"{self.config.callback_url}/api/v1/sandboxes/{self.config.sandbox_id}/events"

        try:
            response = await self.client.post(
                url,
                json={
                    "event_type": event_type,
                    "event_data": event_data,
                    "source": source,
                },
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[EventReporter] Failed to report {event_type}: {e}")
            return False

    async def heartbeat(self) -> bool:
        """Send heartbeat event."""
        return await self.report(
            "agent.heartbeat",
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "alive",
            },
            source="worker",
        )


# =============================================================================
# Message Poller
# =============================================================================


class MessagePoller:
    """Polls main server for injected messages."""

    def __init__(self, config: WorkerConfig):
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        return self

    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()

    async def poll(self) -> list[dict]:
        """Poll for pending messages."""
        if not self.client:
            return []

        url = f"{self.config.callback_url}/api/v1/sandboxes/{self.config.sandbox_id}/messages"

        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"[MessagePoller] Poll failed: {e}")

        return []


# =============================================================================
# SDK Response Processor
# =============================================================================


async def process_sdk_response(
    client: "ClaudeSDKClient",
    reporter: EventReporter,
) -> Optional["ResultMessage"]:
    """Process streaming response from Claude Agent SDK."""
    result: Optional[ResultMessage] = None

    try:
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        await reporter.report(
                            "agent.message",
                            {
                                "content": block.text,
                                "role": "assistant",
                                "block_type": "text",
                            },
                        )
                        print(f"💬 {block.text[:100]}...")

                    elif isinstance(block, ThinkingBlock):
                        await reporter.report(
                            "agent.thinking",
                            {"content": block.thinking, "block_type": "thinking"},
                        )
                        print(f"🤔 Thinking: {block.thinking[:50]}...")

                    elif isinstance(block, ToolUseBlock):
                        await reporter.report(
                            "agent.tool_use",
                            {
                                "tool_name": block.name,
                                "tool_id": block.id,
                                "tool_input": block.input,
                                "block_type": "tool_use",
                            },
                        )
                        print(f"🔧 Tool: {block.name}")

                    elif isinstance(block, ToolResultBlock):
                        await reporter.report(
                            "agent.tool_result",
                            {
                                "tool_id": block.tool_use_id,
                                "content": str(block.content)[:1000],
                                "is_error": block.is_error,
                                "block_type": "tool_result",
                            },
                        )
                        status = "❌" if block.is_error else "✅"
                        print(f"   {status} Result: {str(block.content)[:50]}...")

            elif isinstance(msg, ResultMessage):
                result = msg
                await reporter.report(
                    "agent.turn_complete",
                    {
                        "num_turns": msg.num_turns,
                        "total_cost_usd": msg.total_cost_usd,
                        "session_id": msg.session_id,
                        "is_error": msg.is_error,
                        "duration_ms": msg.duration_ms,
                        "duration_api_ms": msg.duration_api_ms,
                    },
                )
                print(
                    f"📊 Turn {msg.num_turns} complete. Cost: ${msg.total_cost_usd:.4f}"
                )

    except Exception as e:
        await reporter.report(
            "agent.error",
            {"error": str(e), "error_type": type(e).__name__},
        )
        print(f"❌ Response error: {e}")

    return result


# =============================================================================
# Main Worker Loop
# =============================================================================


class SandboxWorker:
    """Main worker orchestrator using Claude Agent SDK."""

    def __init__(self, config: WorkerConfig):
        self.config = config
        self.running = False
        self._shutdown_event = asyncio.Event()

    def _setup_signal_handlers(self):
        """Setup graceful shutdown on SIGTERM/SIGINT."""

        def handle_signal(signum, frame):
            print(f"\n[Worker] Received signal {signum}, shutting down...")
            self._shutdown_event.set()

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

    async def run(self):
        """Main worker loop."""
        self._setup_signal_handlers()
        self.running = True

        print("=" * 60)
        print("🤖 STANDALONE SANDBOX WORKER (Claude Agent SDK)")
        print("=" * 60)
        print("\nConfiguration:")
        for key, value in self.config.to_dict().items():
            print(f"  {key}: {value}")
        print()

        # Validate config
        errors = self.config.validate()
        if errors:
            print("❌ Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            return 1

        if not SDK_AVAILABLE:
            print("❌ claude_agent_sdk package not installed")
            print("   Run: pip install claude-agent-sdk")
            return 1

        sdk_options = self.config.to_sdk_options()

        async with EventReporter(self.config) as reporter:
            async with MessagePoller(self.config) as poller:
                await reporter.report(
                    "agent.started",
                    {
                        "sandbox_id": self.config.sandbox_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "sdk": "claude_agent_sdk",
                    },
                    source="worker",
                )

                try:
                    async with ClaudeSDKClient(options=sdk_options) as client:
                        if self.config.initial_prompt:
                            print(
                                f"\n📤 Initial prompt: {self.config.initial_prompt[:50]}..."
                            )
                            await client.query(self.config.initial_prompt)
                            await process_sdk_response(client, reporter)

                        await reporter.report(
                            "agent.waiting", {"message": "Ready for messages"}
                        )
                        print("\n⏳ Waiting for messages...")

                        last_heartbeat = asyncio.get_event_loop().time()
                        total_turns = 0

                        while not self._shutdown_event.is_set():
                            try:
                                messages = await poller.poll()

                                for msg in messages:
                                    content = msg.get("content", "")
                                    msg_type = msg.get("message_type", "user_message")

                                    if not content:
                                        continue

                                    print(f"\n📥 [{msg_type}] {content[:50]}...")

                                    if msg_type == "interrupt":
                                        await reporter.report(
                                            "agent.interrupted", {"reason": content}
                                        )
                                        print("⚠️  Interrupt received")
                                        await client.interrupt()
                                        continue

                                    await reporter.report(
                                        "agent.processing",
                                        {
                                            "message_id": msg.get("id"),
                                            "message_type": msg_type,
                                        },
                                    )

                                    await client.query(content)
                                    result = await process_sdk_response(
                                        client, reporter
                                    )

                                    if result:
                                        total_turns = result.num_turns

                                    await reporter.report(
                                        "agent.waiting",
                                        {"message": "Ready for messages"},
                                    )

                                now = asyncio.get_event_loop().time()
                                if (
                                    now - last_heartbeat
                                    >= self.config.heartbeat_interval
                                ):
                                    await reporter.heartbeat()
                                    last_heartbeat = now

                                await asyncio.sleep(self.config.poll_interval)

                            except asyncio.CancelledError:
                                break
                            except Exception as e:
                                print(f"❌ Loop error: {e}")
                                await reporter.report("agent.error", {"error": str(e)})
                                await asyncio.sleep(1)

                except Exception as e:
                    print(f"❌ SDK initialization error: {e}")
                    await reporter.report(
                        "agent.error", {"error": str(e), "phase": "initialization"}
                    )
                    return 1

                await reporter.report(
                    "agent.completed",
                    {
                        "reason": "shutdown",
                        "total_turns": total_turns,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    source="worker",
                )
                print("\n✅ Worker shutdown complete")

        return 0


# =============================================================================
# Entry Point
# =============================================================================


async def main():
    config = WorkerConfig()
    worker = SandboxWorker(config)
    return await worker.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
