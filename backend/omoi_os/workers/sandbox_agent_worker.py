#!/usr/bin/env python3
"""
Sandbox Agent Worker - Long-running agent process for Daytona sandboxes.

This script uses the Claude Agent SDK (claude_code_sdk) and is designed to
be deployed inside a Daytona sandbox. It:
1. Maintains a persistent conversation session with Claude
2. Polls the main server for user messages
3. Posts events back to the main server (webhook pattern)
4. Handles graceful shutdown on signals

Usage:
    # Inside sandbox (environment variables set by orchestrator):
    python -m omoi_os.workers.sandbox_agent_worker

    # Or directly with config:
    SANDBOX_ID=sandbox-abc123 \
    CALLBACK_URL=https://api.example.com \
    ANTHROPIC_API_KEY=your_key \
    python sandbox_agent_worker.py

Environment Variables:
    SANDBOX_ID          - Unique sandbox identifier (required)
    CALLBACK_URL        - Main server base URL for callbacks (required)
    ANTHROPIC_API_KEY   - API key for Claude (required)
    INITIAL_PROMPT      - Optional initial task prompt
    POLL_INTERVAL       - Message poll interval in seconds (default: 0.5)
    HEARTBEAT_INTERVAL  - Heartbeat interval in seconds (default: 30)
    MAX_TURNS           - Max turns per response (default: 50)
    PERMISSION_MODE     - SDK permission mode (default: acceptEdits)
    SYSTEM_PROMPT       - Optional custom system prompt
"""

import asyncio
import os
import signal
import sys
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

import httpx

# Configure logging for standalone sandbox script
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("sandbox_agent_worker")


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
        self.sandbox_id = os.environ.get("SANDBOX_ID", f"sandbox-{uuid4().hex[:8]}")
        self.callback_url = os.environ.get("CALLBACK_URL", "http://localhost:8000")
        self.api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get(
            "ANTHROPIC_AUTH_TOKEN", ""
        )
        self.initial_prompt = os.environ.get("INITIAL_PROMPT", "")
        self.poll_interval = float(os.environ.get("POLL_INTERVAL", "0.5"))
        self.heartbeat_interval = int(os.environ.get("HEARTBEAT_INTERVAL", "30"))
        self.max_turns = int(os.environ.get("MAX_TURNS", "50"))
        self.permission_mode = os.environ.get("PERMISSION_MODE", "bypassPermissions")
        self.system_prompt = os.environ.get(
            "SYSTEM_PROMPT",
            "You are a helpful coding assistant working in a sandboxed environment. "
            "You have access to the filesystem and can execute commands. "
            "Be thorough but concise in your responses.",
        )
        self.allowed_tools = os.environ.get(
            "ALLOWED_TOOLS", "Read,Write,Bash,Glob,Grep"
        ).split(",")
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
            "poll_interval": self.poll_interval,
            "heartbeat_interval": self.heartbeat_interval,
            "max_turns": self.max_turns,
            "permission_mode": self.permission_mode,
            "allowed_tools": self.allowed_tools,
            "cwd": self.cwd,
        }

    def to_sdk_options(self) -> "ClaudeAgentOptions":
        """Create ClaudeCodeOptions from config."""
        return ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            allowed_tools=self.allowed_tools,
            permission_mode=self.permission_mode,
            max_turns=self.max_turns,
            cwd=self.cwd,
            env={"ANTHROPIC_API_KEY": self.api_key},
        )


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
        """
        Report event to main server.

        Args:
            event_type: Event type (e.g., 'agent.message', 'agent.tool_use')
            event_data: Event payload
            source: Event source identifier

        Returns:
            True if successful, False otherwise
        """
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
            logger.error("Failed to report event", extra={"event_type": event_type, "error": str(e)})
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
        """
        Poll for pending messages.

        Returns:
            List of message dicts with 'content', 'message_type', 'id', 'timestamp'
        """
        if not self.client:
            return []

        url = f"{self.config.callback_url}/api/v1/sandboxes/{self.config.sandbox_id}/messages"

        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error("Message poll failed", extra={"error": str(e)})

        return []


# =============================================================================
# SDK Response Processor
# =============================================================================


async def process_sdk_response(
    client: "ClaudeSDKClient",
    reporter: EventReporter,
) -> Optional["ResultMessage"]:
    """
    Process streaming response from Claude Agent SDK.

    Args:
        client: ClaudeSDKClient instance
        reporter: EventReporter for streaming events back

    Returns:
        ResultMessage when response completes, None on error
    """
    result: Optional[ResultMessage] = None

    try:
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                # Process each content block
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        # Report text output
                        await reporter.report(
                            "agent.message",
                            {
                                "content": block.text,
                                "role": "assistant",
                                "block_type": "text",
                            },
                        )
                        logger.info("Assistant message", extra={"text_preview": block.text[:100]})

                    elif isinstance(block, ThinkingBlock):
                        # Report thinking (if present)
                        await reporter.report(
                            "agent.thinking",
                            {
                                "content": block.thinking,
                                "block_type": "thinking",
                            },
                        )
                        logger.debug("Agent thinking", extra={"thinking_preview": block.thinking[:50]})

                    elif isinstance(block, ToolUseBlock):
                        # Report tool use
                        await reporter.report(
                            "agent.tool_use",
                            {
                                "tool_name": block.name,
                                "tool_id": block.id,
                                "tool_input": block.input,
                                "block_type": "tool_use",
                            },
                        )
                        logger.info("Tool use", extra={"tool_name": block.name, "tool_id": block.id})

                    elif isinstance(block, ToolResultBlock):
                        # Report tool result
                        await reporter.report(
                            "agent.tool_result",
                            {
                                "tool_id": block.tool_use_id,
                                "content": str(block.content)[:1000],  # Truncate
                                "is_error": block.is_error,
                                "block_type": "tool_result",
                            },
                        )
                        log_level = logging.ERROR if block.is_error else logging.INFO
                        logger.log(log_level, "Tool result", extra={
                            "tool_id": block.tool_use_id,
                            "is_error": block.is_error,
                            "result_preview": str(block.content)[:50],
                        })

            elif isinstance(msg, ResultMessage):
                # Conversation turn completed
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
                logger.info("Turn complete", extra={
                    "num_turns": msg.num_turns,
                    "total_cost_usd": msg.total_cost_usd,
                    "is_error": msg.is_error,
                })

    except Exception as e:
        await reporter.report(
            "agent.error",
            {"error": str(e), "error_type": type(e).__name__},
        )
        logger.error("Response processing error", extra={"error": str(e), "error_type": type(e).__name__}, exc_info=True)

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
            logger.info("Received shutdown signal", extra={"signal": signum})
            self._shutdown_event.set()

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

    async def run(self):
        """Main worker loop."""
        self._setup_signal_handlers()
        self.running = True

        logger.info("=" * 60)
        logger.info("SANDBOX AGENT WORKER (Claude Agent SDK)")
        logger.info("=" * 60)
        logger.info("Configuration", extra=self.config.to_dict())

        # Validate config
        errors = self.config.validate()
        if errors:
            logger.error("Configuration errors", extra={"errors": errors})
            return 1

        if not SDK_AVAILABLE:
            logger.error("claude_agent_sdk package not installed - Run: pip install claude-agent-sdk")
            return 1

        # Create SDK options
        sdk_options = self.config.to_sdk_options()

        async with EventReporter(self.config) as reporter:
            async with MessagePoller(self.config) as poller:
                # Report startup
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
                        # Process initial prompt if provided
                        if self.config.initial_prompt:
                            logger.info(
                                "Processing initial prompt",
                                extra={"prompt_preview": self.config.initial_prompt[:50]}
                            )
                            await client.query(self.config.initial_prompt)
                            await process_sdk_response(client, reporter)

                        # Report ready for messages
                        await reporter.report(
                            "agent.waiting",
                            {"message": "Ready for messages"},
                        )
                        logger.info("Waiting for messages")

                        # Main loop
                        last_heartbeat = asyncio.get_event_loop().time()
                        total_turns = 0

                        while not self._shutdown_event.is_set():
                            try:
                                # Poll for messages
                                messages = await poller.poll()

                                for msg in messages:
                                    content = msg.get("content", "")
                                    msg_type = msg.get("message_type", "user_message")

                                    if not content:
                                        continue

                                    logger.info("Received message", extra={"msg_type": msg_type, "content_preview": content[:50]})

                                    # Handle interrupt specially
                                    if msg_type == "interrupt":
                                        await reporter.report(
                                            "agent.interrupted",
                                            {"reason": content},
                                        )
                                        logger.warning("Interrupt received", extra={"reason": content})
                                        await client.interrupt()
                                        continue

                                    # Report processing
                                    await reporter.report(
                                        "agent.processing",
                                        {
                                            "message_id": msg.get("id"),
                                            "message_type": msg_type,
                                        },
                                    )

                                    # Send to Claude via SDK
                                    await client.query(content)
                                    result = await process_sdk_response(
                                        client, reporter
                                    )

                                    if result:
                                        total_turns = result.num_turns

                                    # Report ready for more
                                    await reporter.report(
                                        "agent.waiting",
                                        {"message": "Ready for messages"},
                                    )

                                # Heartbeat
                                now = asyncio.get_event_loop().time()
                                if (
                                    now - last_heartbeat
                                    >= self.config.heartbeat_interval
                                ):
                                    await reporter.heartbeat()
                                    last_heartbeat = now

                                # Wait before next poll
                                await asyncio.sleep(self.config.poll_interval)

                            except asyncio.CancelledError:
                                break
                            except Exception as e:
                                logger.error("Main loop error", extra={"error": str(e)}, exc_info=True)
                                await reporter.report(
                                    "agent.error",
                                    {"error": str(e)},
                                )
                                await asyncio.sleep(1)  # Back off on error

                except Exception as e:
                    logger.error("SDK initialization error", extra={"error": str(e)}, exc_info=True)
                    await reporter.report(
                        "agent.error",
                        {"error": str(e), "phase": "initialization"},
                    )
                    return 1

                # Shutdown
                await reporter.report(
                    "agent.completed",
                    {
                        "reason": "shutdown",
                        "total_turns": total_turns,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    source="worker",
                )

                logger.info("Worker shutdown complete", extra={"total_turns": total_turns})

        return 0


# =============================================================================
# Entry Point
# =============================================================================


async def main():
    """Entry point for sandbox agent worker."""
    config = WorkerConfig()
    worker = SandboxWorker(config)
    return await worker.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
