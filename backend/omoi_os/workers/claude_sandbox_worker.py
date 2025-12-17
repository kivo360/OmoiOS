#!/usr/bin/env python3
"""
Claude Sandbox Agent Worker - Production-ready agent for Daytona sandboxes.

This is a STANDALONE script with NO local dependencies.
Just copy this file + install deps:

    pip install httpx claude-agent-sdk
    python claude_sandbox_worker.py

Environment Variables (required):
    SANDBOX_ID          - Unique sandbox identifier
    CALLBACK_URL        - Main server base URL (e.g., https://api.example.com)
    ANTHROPIC_API_KEY   - API key for Claude (or Z.AI token)

Environment Variables (optional - model/API):
    MODEL               - Model to use (e.g., "glm-4.6v" for Z.AI, default: Claude's default)
    ANTHROPIC_BASE_URL  - Custom API endpoint (e.g., "https://api.z.ai/api/anthropic" for GLM)

Environment Variables (optional - task context):
    TASK_ID             - Task identifier for tracking
    AGENT_ID            - Agent identifier for tracking
    TICKET_ID           - Ticket identifier
    TICKET_TITLE        - Ticket title for context
    TICKET_DESCRIPTION  - Full ticket description

Environment Variables (optional - skills & subagents):
    ENABLE_SKILLS       - Set to "true" to enable Claude skills
    ENABLE_SUBAGENTS    - Set to "true" to enable custom subagents
    SETTING_SOURCES     - Comma-separated: "user,project" to load skills

Environment Variables (optional - behavior):
    INITIAL_PROMPT      - Initial task prompt
    POLL_INTERVAL       - Message poll interval in seconds (default: 0.5)
    HEARTBEAT_INTERVAL  - Heartbeat interval in seconds (default: 30)
    MAX_TURNS           - Max turns per response (default: 50)
    MAX_BUDGET_USD      - Max budget in USD (default: 10.0)
    PERMISSION_MODE     - SDK permission mode (default: acceptEdits)
    SYSTEM_PROMPT       - Custom system prompt
    ALLOWED_TOOLS       - Comma-separated tool list
    CWD                 - Working directory (default: /workspace)

Environment Variables (optional - GitHub):
    GITHUB_TOKEN        - GitHub access token for repo operations
    GITHUB_REPO         - Repository in owner/repo format
    BRANCH_NAME         - Branch to checkout

Example with GLM:
    SANDBOX_ID=my-sandbox \\
    CALLBACK_URL=http://localhost:8000 \\
    ANTHROPIC_API_KEY=your_z_ai_token \\
    ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic \\
    MODEL=glm-4.6v \\
    python claude_sandbox_worker.py
"""

import asyncio
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import httpx

# Try to import Claude Agent SDK
try:
    from claude_agent_sdk import (
        # Message types
        AssistantMessage,
        UserMessage,
        SystemMessage,
        ResultMessage,
        # Content blocks
        TextBlock,
        ThinkingBlock,
        ToolUseBlock,
        ToolResultBlock,
        # Client and options
        ClaudeAgentOptions,
        ClaudeSDKClient,
        HookMatcher,
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
        # Core identifiers
        self.sandbox_id = os.environ.get("SANDBOX_ID", f"sandbox-{uuid4().hex[:8]}")
        self.task_id = os.environ.get("TASK_ID", "")
        self.agent_id = os.environ.get("AGENT_ID", "")
        self.ticket_id = os.environ.get("TICKET_ID", "")
        self.ticket_title = os.environ.get("TICKET_TITLE", "")
        self.ticket_description = os.environ.get("TICKET_DESCRIPTION", "")

        # Server connection
        self.callback_url = os.environ.get("CALLBACK_URL", "http://localhost:8000")
        self.api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get(
            "ANTHROPIC_AUTH_TOKEN", ""
        )

        # Model settings (for GLM or other models)
        self.model = os.environ.get("MODEL") or os.environ.get("ANTHROPIC_MODEL")
        self.api_base_url = os.environ.get("ANTHROPIC_BASE_URL")

        # Task and prompts
        self.initial_prompt = os.environ.get("INITIAL_PROMPT", "")
        self.poll_interval = float(os.environ.get("POLL_INTERVAL", "0.5"))
        self.heartbeat_interval = int(os.environ.get("HEARTBEAT_INTERVAL", "30"))

        # SDK settings
        self.max_turns = int(os.environ.get("MAX_TURNS", "50"))
        self.max_budget_usd = float(os.environ.get("MAX_BUDGET_USD", "10.0"))
        self.permission_mode = os.environ.get("PERMISSION_MODE", "acceptEdits")
        self.cwd = os.environ.get("CWD", "/workspace")

        # System prompt with subagent info
        default_system_prompt = """You are an AI coding agent. Your workspace is /workspace. Be thorough and test your changes.

You have access to specialized subagents:
- code-reviewer: For security and quality code reviews
- test-runner: For running and analyzing tests
- architect: For design decisions and structure analysis
- debugger: For investigating bugs

You also have access to Skills loaded from .claude/skills/ directories.
Use subagents and skills when they can help accomplish the task more effectively."""

        self.system_prompt = os.environ.get("SYSTEM_PROMPT", default_system_prompt)

        # Tools - parse comma-separated list
        default_tools = "Read,Write,Bash,Edit,Glob,Grep"
        self.allowed_tools = os.environ.get("ALLOWED_TOOLS", default_tools).split(",")

        # Skills and subagents
        self.enable_skills = os.environ.get("ENABLE_SKILLS", "true").lower() == "true"
        self.enable_subagents = os.environ.get("ENABLE_SUBAGENTS", "true").lower() == "true"

        # Add Task and Skill to allowed tools if enabled
        if self.enable_subagents and "Task" not in self.allowed_tools:
            self.allowed_tools.append("Task")
        if self.enable_skills and "Skill" not in self.allowed_tools:
            self.allowed_tools.append("Skill")

        # Setting sources for loading skills
        setting_sources_str = os.environ.get("SETTING_SOURCES", "user,project")
        self.setting_sources = [s.strip() for s in setting_sources_str.split(",") if s.strip()]

        # GitHub config
        self.github_token = os.environ.get("GITHUB_TOKEN", "")
        self.github_repo = os.environ.get("GITHUB_REPO", "")
        self.branch_name = os.environ.get("BRANCH_NAME", "")

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
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "callback_url": self.callback_url,
            "api_key": "***" if self.api_key else "NOT SET",
            "model": self.model or "default",
            "api_base_url": self.api_base_url or "default",
            "poll_interval": self.poll_interval,
            "heartbeat_interval": self.heartbeat_interval,
            "max_turns": self.max_turns,
            "max_budget_usd": self.max_budget_usd,
            "permission_mode": self.permission_mode,
            "allowed_tools": self.allowed_tools,
            "enable_skills": self.enable_skills,
            "enable_subagents": self.enable_subagents,
            "setting_sources": self.setting_sources,
            "cwd": self.cwd,
        }

    def get_custom_agents(self) -> dict:
        """Return custom subagent definitions."""
        return {
            "code-reviewer": {
                "description": "Expert code review specialist. Use for security, quality, and maintainability reviews.",
                "prompt": """You are a code review specialist with expertise in security, performance, and best practices.
When reviewing code:
- Identify security vulnerabilities and injection risks
- Check for performance issues and memory leaks
- Verify adherence to coding standards
- Suggest specific, actionable improvements
Be thorough but concise in your feedback.""",
                "tools": ["Read", "Grep", "Glob"],
                "model": "sonnet"
            },
            "test-runner": {
                "description": "Runs and analyzes test suites. Use for test execution and coverage analysis.",
                "prompt": """You are a test execution specialist. Run tests and provide clear analysis of results.
Focus on:
- Running test commands (pytest, npm test, etc.)
- Analyzing test output and identifying patterns
- Identifying failing tests and their root causes
- Suggesting fixes for test failures""",
                "tools": ["Bash", "Read", "Grep"],
            },
            "architect": {
                "description": "Software architecture specialist. Use for design decisions and codebase structure.",
                "prompt": """You are a software architecture specialist.
Analyze code structure, identify patterns, suggest architectural improvements.
Focus on:
- Module organization and dependencies
- Design patterns and anti-patterns
- Scalability and maintainability concerns
- API design and contracts""",
                "tools": ["Read", "Grep", "Glob"],
            },
            "debugger": {
                "description": "Debugging specialist. Use for investigating bugs and unexpected behavior.",
                "prompt": """You are a debugging specialist.
Systematically investigate issues:
- Reproduce the problem
- Add logging/tracing to narrow down the cause
- Identify root causes
- Propose and test fixes""",
                "tools": ["Read", "Bash", "Edit", "Grep"],
            }
        }

    def to_sdk_options(self, post_tool_hook=None) -> "ClaudeAgentOptions":
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
            "max_budget_usd": self.max_budget_usd,
            "cwd": self.cwd,
            "env": env,
        }

        # Add model if specified
        if self.model:
            options_kwargs["model"] = self.model

        # Add setting sources for skills
        if self.setting_sources:
            options_kwargs["setting_sources"] = self.setting_sources

        # Add custom subagents
        if self.enable_subagents:
            options_kwargs["agents"] = self.get_custom_agents()

        # Add hooks
        if post_tool_hook:
            options_kwargs["hooks"] = {
                "PostToolUse": [HookMatcher(matcher=None, hooks=[post_tool_hook])],
            }

        return ClaudeAgentOptions(**options_kwargs)


# =============================================================================
# Event Reporter (Webhook Client)
# =============================================================================


class EventReporter:
    """Reports events back to main server via HTTP POST with comprehensive tracking."""

    def __init__(self, config: WorkerConfig):
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None
        self.event_count = 0

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
        """Report event to main server with full context."""
        if not self.client:
            return False

        self.event_count += 1

        # Always add core identifiers
        event_data = {
            **event_data,
            "task_id": self.config.task_id,
            "agent_id": self.config.agent_id,
            "sandbox_id": self.config.sandbox_id,
        }

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
            success = response.status_code == 200
            if not success:
                print(f"[EventReporter] Event {event_type} failed: {response.status_code}")
            return success
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
                "event_count": self.event_count,
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
# GitHub Setup
# =============================================================================


def setup_github_workspace(config: WorkerConfig) -> bool:
    """Clone GitHub repo and setup workspace if configured."""
    if not config.github_token or not config.github_repo:
        print("[GitHub] No credentials, skipping repo clone")
        return False

    # Check if already cloned
    if os.path.exists(os.path.join(config.cwd, ".git")):
        print(f"[GitHub] Workspace {config.cwd} already has git repo")
        return True

    # Configure git user
    subprocess.run(["git", "config", "--global", "user.email", "agent@omoios.ai"], check=False)
    subprocess.run(["git", "config", "--global", "user.name", "OmoiOS Agent"], check=False)

    # Clone with token
    clone_url = f"https://x-access-token:{config.github_token}@github.com/{config.github_repo}.git"
    print(f"[GitHub] Cloning {config.github_repo}...")

    result = subprocess.run(
        ["git", "clone", clone_url, config.cwd],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"[GitHub] Clone failed: {result.stderr}")
        return False

    os.chdir(config.cwd)

    # Checkout branch if specified
    if config.branch_name:
        print(f"[GitHub] Checking out branch: {config.branch_name}")
        subprocess.run(["git", "checkout", config.branch_name], check=False)

    print(f"[GitHub] Repository ready at {config.cwd}")
    return True


# =============================================================================
# Main Worker
# =============================================================================


class SandboxWorker:
    """Main worker orchestrator with comprehensive event tracking."""

    def __init__(self, config: WorkerConfig):
        self.config = config
        self.running = False
        self._shutdown_event = asyncio.Event()
        self._should_stop = False
        self.turn_count = 0
        self.reporter: Optional[EventReporter] = None

    def _setup_signal_handlers(self):
        """Setup graceful shutdown on SIGTERM/SIGINT."""

        def handle_signal(signum, frame):
            print(f"\n[Worker] Received signal {signum}, shutting down...")
            self._shutdown_event.set()
            self._should_stop = True

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

    async def _create_post_tool_hook(self):
        """Create PostToolUse hook for comprehensive tool tracking."""
        reporter = self.reporter

        async def track_tool_use(input_data, tool_use_id, context):
            """PostToolUse hook for comprehensive event reporting."""
            tool_name = input_data.get("tool_name", "unknown")
            tool_input = input_data.get("tool_input", {})
            tool_response = input_data.get("tool_response", "")

            # Full tool tracking
            event_data = {
                "turn": self.turn_count,
                "tool": tool_name,
                "tool_input": tool_input,
                "tool_response": str(tool_response)[:2000] if tool_response else None,
            }

            # Special tracking for subagents
            if tool_name == "Task":
                event_data["subagent_type"] = tool_input.get("subagent_type")
                event_data["description"] = tool_input.get("description")
                event_data["prompt"] = tool_input.get("prompt")
                await reporter.report("agent.subagent_completed", event_data)
            # Special tracking for skills
            elif tool_name == "Skill":
                event_data["skill_name"] = tool_input.get("name") or tool_input.get("skill_name")
                await reporter.report("agent.skill_completed", event_data)
            else:
                await reporter.report("agent.tool_completed", event_data)

            return {}

        return track_tool_use

    async def _process_messages(
        self,
        client: "ClaudeSDKClient",
    ):
        """Process streaming messages with comprehensive event tracking."""
        final_output = []

        try:
            async for msg in client.receive_messages():
                if isinstance(msg, AssistantMessage):
                    self.turn_count += 1

                    # Report assistant message metadata
                    await self.reporter.report("agent.assistant_message", {
                        "turn": self.turn_count,
                        "model": getattr(msg, "model", self.config.model),
                        "stop_reason": getattr(msg, "stop_reason", None),
                        "block_count": len(msg.content),
                    })

                    for block in msg.content:
                        if isinstance(block, ThinkingBlock):
                            await self.reporter.report("agent.thinking", {
                                "turn": self.turn_count,
                                "content": block.text,  # Full content
                                "thinking_type": "extended_thinking",
                            })
                            print(f"🤔 Thinking: {block.text[:100]}...")

                        elif isinstance(block, ToolUseBlock):
                            tool_event = {
                                "turn": self.turn_count,
                                "tool": block.name,
                                "tool_use_id": block.id,
                                "input": block.input,  # Full input
                            }

                            # Special handling for subagent dispatch
                            if block.name == "Task":
                                tool_event["event_subtype"] = "subagent_invoked"
                                tool_event["subagent_type"] = block.input.get("subagent_type")
                                tool_event["subagent_description"] = block.input.get("description")
                                tool_event["subagent_prompt"] = block.input.get("prompt")
                                await self.reporter.report("agent.subagent_invoked", tool_event)
                                print(f"🤖 Subagent: {block.input.get('subagent_type')}")

                            # Special handling for skill invocation
                            elif block.name == "Skill":
                                tool_event["event_subtype"] = "skill_invoked"
                                tool_event["skill_name"] = block.input.get("name") or block.input.get("skill_name")
                                await self.reporter.report("agent.skill_invoked", tool_event)
                                print(f"⚡ Skill: {tool_event['skill_name']}")

                            # Standard tool use
                            else:
                                tool_event["event_subtype"] = "tool_use"
                                await self.reporter.report("agent.tool_use", tool_event)
                                print(f"🔧 Tool: {block.name}")

                        elif isinstance(block, ToolResultBlock):
                            result_content = str(block.content)
                            await self.reporter.report("agent.tool_result", {
                                "turn": self.turn_count,
                                "tool_use_id": block.tool_use_id,
                                "result": result_content[:5000] if len(result_content) > 5000 else result_content,
                                "result_truncated": len(result_content) > 5000,
                                "result_full_length": len(result_content),
                                "is_error": getattr(block, "is_error", False),
                            })
                            status = "❌" if getattr(block, "is_error", False) else "✅"
                            print(f"   {status} Result: {result_content[:80]}...")

                        elif isinstance(block, TextBlock):
                            await self.reporter.report("agent.message", {
                                "turn": self.turn_count,
                                "content": block.text,  # Full content
                                "content_length": len(block.text),
                            })
                            final_output.append(block.text)
                            print(f"💬 {block.text[:100]}...")

                elif isinstance(msg, UserMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            await self.reporter.report("agent.user_message", {
                                "turn": self.turn_count,
                                "content": block.text,
                                "content_length": len(block.text),
                            })
                        elif isinstance(block, ToolResultBlock):
                            result_content = str(block.content)
                            await self.reporter.report("agent.user_tool_result", {
                                "turn": self.turn_count,
                                "tool_use_id": block.tool_use_id,
                                "result": result_content[:5000] if len(result_content) > 5000 else result_content,
                                "result_truncated": len(result_content) > 5000,
                            })

                elif isinstance(msg, SystemMessage):
                    await self.reporter.report("agent.system_message", {
                        "turn": self.turn_count,
                        "metadata": getattr(msg, "metadata", {}),
                    })

                elif isinstance(msg, ResultMessage):
                    usage = getattr(msg, "usage", None)
                    await self.reporter.report("agent.completed", {
                        "success": True,
                        "turns": msg.num_turns,
                        "cost_usd": msg.total_cost_usd,
                        "session_id": msg.session_id,
                        "stop_reason": getattr(msg, "stop_reason", None),
                        "input_tokens": usage.input_tokens if usage else None,
                        "output_tokens": usage.output_tokens if usage else None,
                        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", None) if usage else None,
                        "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", None) if usage else None,
                    })
                    print(f"📊 Completed: {msg.num_turns} turns, ${msg.total_cost_usd:.4f}")
                    return msg, final_output

        except Exception as e:
            await self.reporter.report("agent.stream_error", {
                "error": str(e),
                "turn": self.turn_count,
            })
            print(f"❌ Stream error: {e}")

        return None, final_output

    async def run(self):
        """Main worker loop with comprehensive event tracking."""
        self._setup_signal_handlers()
        self.running = True

        print("=" * 60)
        print("🤖 CLAUDE SANDBOX WORKER (Production)")
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

        # Setup workspace
        Path(self.config.cwd).mkdir(parents=True, exist_ok=True)
        setup_github_workspace(self.config)

        async with EventReporter(self.config) as reporter:
            self.reporter = reporter

            async with MessagePoller(self.config) as poller:
                # Create hook and options
                post_tool_hook = await self._create_post_tool_hook()
                sdk_options = self.config.to_sdk_options(post_tool_hook=post_tool_hook)

                # Report startup
                await reporter.report(
                    "agent.started",
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "sdk": "claude_agent_sdk",
                        "model": self.config.model or "default",
                        "task": self.config.initial_prompt or self.config.ticket_description,
                        "ticket_title": self.config.ticket_title,
                    },
                    source="worker",
                )

                try:
                    async with ClaudeSDKClient(options=sdk_options) as client:
                        # Process initial prompt
                        initial_task = (
                            self.config.initial_prompt
                            or self.config.ticket_description
                            or f"Analyze ticket: {self.config.ticket_title}"
                        )

                        if initial_task:
                            print(f"\n📤 Initial task: {initial_task[:100]}...")
                            await client.query(initial_task)
                            await self._process_messages(client)

                        # Report ready
                        await reporter.report(
                            "agent.waiting",
                            {"message": "Ready for messages"},
                        )
                        print("\n⏳ Waiting for messages...")

                        # Main loop
                        last_heartbeat = asyncio.get_event_loop().time()
                        intervention_count = 0

                        while not self._shutdown_event.is_set():
                            try:
                                # Check for stop
                                if self._should_stop:
                                    await client.interrupt()
                                    await reporter.report("agent.interrupted", {
                                        "reason": "shutdown_signal",
                                        "turn": self.turn_count,
                                    })
                                    break

                                # Poll for messages
                                messages = await poller.poll()

                                for msg in messages:
                                    intervention_count += 1
                                    content = msg.get("content", "")
                                    msg_type = msg.get("message_type", "user_message")
                                    sender_id = msg.get("sender_id")
                                    message_id = msg.get("message_id")

                                    if not content:
                                        continue

                                    print(f"\n📥 [{msg_type}] {content[:80]}...")

                                    # Handle interrupt
                                    if msg_type == "interrupt":
                                        self._should_stop = True
                                        await client.interrupt()
                                        await reporter.report("agent.interrupted", {
                                            "reason": content,
                                            "sender_id": sender_id,
                                            "turn": self.turn_count,
                                        })
                                        break

                                    # Report message injection
                                    await reporter.report("agent.message_injected", {
                                        "message_type": msg_type,
                                        "content": content,  # Full content
                                        "content_length": len(content),
                                        "sender_id": sender_id,
                                        "message_id": message_id,
                                        "intervention_number": intervention_count,
                                        "turn": self.turn_count,
                                    })

                                    # Process message
                                    await client.query(content)
                                    await self._process_messages(client)

                                    # Report ready
                                    await reporter.report(
                                        "agent.waiting",
                                        {"message": "Ready for messages"},
                                    )

                                # Heartbeat
                                now = asyncio.get_event_loop().time()
                                if now - last_heartbeat >= self.config.heartbeat_interval:
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
                        "agent.error",
                        {"error": str(e), "phase": "initialization"},
                    )
                    return 1

                # Shutdown
                await reporter.report(
                    "agent.shutdown",
                    {
                        "reason": "complete",
                        "total_turns": self.turn_count,
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
