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

Environment Variables (optional - session resumption):
    RESUME_SESSION_ID   - Session ID to resume a previous conversation
    FORK_SESSION        - Set to "true" to fork from session (creates new branch)
    SESSION_TRANSCRIPT_B64 - Base64-encoded session transcript for cross-sandbox resumption
    CONVERSATION_CONTEXT - Text context/summary for conversation hydration (alternative)

Example with GLM:
    SANDBOX_ID=my-sandbox \\
    CALLBACK_URL=http://localhost:8000 \\
    ANTHROPIC_API_KEY=your_z_ai_token \\
    ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic \\
    MODEL=glm-4.6v \\
    python claude_sandbox_worker.py
"""

import asyncio
import base64
import difflib
import logging
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import httpx

# Configure logging for standalone sandbox operation
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("claude_sandbox_worker")

# Try to import pydantic v2 for agent model serialization
# Define dataclass for agent definitions at module level (required for SDK's asdict())
from dataclasses import dataclass


@dataclass
class AgentDefinition:
    """Agent definition dataclass for SDK compatibility."""

    description: str
    prompt: str
    tools: list[str]
    model: Optional[str] = None


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
        HookInput,
        HookContext,
        HookJSONOutput,
    )

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False


# =============================================================================
# File Change Tracking
# =============================================================================


class FileChangeTracker:
    """Tracks file changes for diff generation."""

    def __init__(self):
        self.file_cache: dict[str, str] = {}  # path → content before edit

    def cache_file_before_edit(self, path: str, content: str):
        """Cache file content before Write/Edit tool executes."""
        self.file_cache[path] = content

    def generate_diff(self, path: str, new_content: str) -> dict:
        """Generate unified diff after edit completes."""
        old_content = self.file_cache.pop(path, "")

        # Handle new file vs modified file
        if not old_content:
            # New file
            new_lines = new_content.splitlines(keepends=True)
            lines_added = len(new_lines)
            lines_removed = 0
            diff = ["--- /dev/null\n", f"+++ b/{path}\n"]
            for line in new_lines:
                diff.append(f"+{line}")
            change_type = "created"
        else:
            # Modified file
            old_lines = old_content.splitlines(keepends=True)
            new_lines = new_content.splitlines(keepends=True)
            diff = list(
                difflib.unified_diff(
                    old_lines,
                    new_lines,
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                    lineterm="",
                )
            )
            lines_added = sum(
                1
                for line in diff
                if line.startswith("+") and not line.startswith("+++")
            )
            lines_removed = sum(
                1
                for line in diff
                if line.startswith("-") and not line.startswith("---")
            )
            change_type = "modified"

        diff_text = "".join(diff)
        diff_preview = "\n".join(diff[:100])
        if len(diff) > 100:
            diff_preview += f"\n... ({len(diff) - 100} more lines)"

        return {
            "file_path": path,
            "change_type": change_type,
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "diff_preview": diff_preview[:5000],
            "full_diff": diff_text if len(diff_text) <= 50000 else None,
            "full_diff_available": len(diff_text) > 5000,
            "full_diff_size": len(diff_text),
        }


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
        self.enable_subagents = (
            os.environ.get("ENABLE_SUBAGENTS", "true").lower() == "true"
        )

        # Add Task and Skill to allowed tools if enabled
        if self.enable_subagents and "Task" not in self.allowed_tools:
            self.allowed_tools.append("Task")
        if self.enable_skills and "Skill" not in self.allowed_tools:
            self.allowed_tools.append("Skill")

        # Setting sources for loading skills
        setting_sources_str = os.environ.get("SETTING_SOURCES", "user,project")
        self.setting_sources = [
            s.strip() for s in setting_sources_str.split(",") if s.strip()
        ]

        # GitHub config
        self.github_token = os.environ.get("GITHUB_TOKEN", "")
        self.github_repo = os.environ.get("GITHUB_REPO", "")
        self.branch_name = os.environ.get("BRANCH_NAME", "")

        # Session resumption - pass a session_id to continue a previous conversation
        self.resume_session_id = os.environ.get("RESUME_SESSION_ID")
        # Fork session - if True, creates a new branch from the resumed session
        # If False (default), continues the exact same session
        self.fork_session = os.environ.get("FORK_SESSION", "false").lower() == "true"

        # Session transcript for cross-sandbox resumption (Base64 encoded JSONL)
        # If provided, this transcript will be written to the local session store
        # before resuming, enabling session portability across sandboxes
        self.session_transcript_b64 = os.environ.get("SESSION_TRANSCRIPT_B64")

        # Conversation context for hydration (alternative to full transcript)
        # Use this to provide a summary of previous conversation
        self.conversation_context = os.environ.get("CONVERSATION_CONTEXT", "")

        # Append conversation context to system prompt if provided (for hydration)
        # NOTE: Must be after conversation_context is initialized above
        if self.conversation_context:
            self.system_prompt = f"""{self.system_prompt}

## Previous Conversation Context
You are resuming a previous conversation. Here's what happened before:
{self.conversation_context}

Continue from where we left off, acknowledging the previous context."""

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
            "resume_session_id": self.resume_session_id or "none",
            "fork_session": self.fork_session,
            "has_session_transcript": bool(self.session_transcript_b64),
            "has_conversation_context": bool(self.conversation_context),
        }

    def get_custom_agents(self) -> dict:
        """Return custom subagent definitions.

        Returns pydantic BaseModel instances if available, otherwise plain dicts.
        This allows the SDK to use model_dump() instead of asdict() for serialization.
        """
        agent_defs = {
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
                "model": "sonnet",
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
            },
        }

        # Convert to dataclass instances - SDK's asdict() requires dataclass instances
        # Must use module-level dataclass for proper serialization
        return {
            name: AgentDefinition(**agent_data)
            for name, agent_data in agent_defs.items()
        }

    def to_sdk_options(
        self, pre_tool_hook=None, post_tool_hook=None
    ) -> "ClaudeAgentOptions":
        """Create ClaudeAgentOptions from config."""
        # Build environment variables for the CLI subprocess
        env = {"ANTHROPIC_API_KEY": self.api_key}
        if self.api_base_url:
            env["ANTHROPIC_BASE_URL"] = self.api_base_url

        # Build options dict
        # Convert cwd to Path if it's a string (SDK expects Path)
        cwd_path = Path(self.cwd) if isinstance(self.cwd, str) else self.cwd

        options_kwargs = {
            "system_prompt": self.system_prompt,
            "allowed_tools": self.allowed_tools,
            "permission_mode": self.permission_mode,
            "max_turns": self.max_turns,
            "max_budget_usd": self.max_budget_usd,
            "cwd": cwd_path,
            "env": env,
        }

        # Add model if specified
        if self.model:
            options_kwargs["model"] = self.model

        # Add setting sources for skills
        if self.setting_sources:
            options_kwargs["setting_sources"] = self.setting_sources

        # Add custom subagents
        # Convert agent dicts to pydantic models so SDK can use model_dump() instead of asdict()
        if self.enable_subagents:
            options_kwargs["agents"] = self.get_custom_agents()

        # Add session resumption options
        if self.resume_session_id:
            options_kwargs["resume"] = self.resume_session_id
            options_kwargs["fork_session"] = self.fork_session

        # Add hooks
        hooks = {}
        if pre_tool_hook:
            hooks["PreToolUse"] = [
                HookMatcher(matcher="Write", hooks=[pre_tool_hook]),
                HookMatcher(matcher="Edit", hooks=[pre_tool_hook]),
            ]
        if post_tool_hook:
            hooks["PostToolUse"] = [
                HookMatcher(matcher=None, hooks=[post_tool_hook]),
            ]

        if hooks:
            options_kwargs["hooks"] = hooks

        return ClaudeAgentOptions(**options_kwargs)

    def get_session_transcript_path(self, session_id: str) -> Path:
        """Get the path where session transcripts are stored.

        Claude Code stores sessions in ~/.claude/projects/<project-key>/<session-id>.jsonl
        The project key is derived from cwd, replacing slashes with dashes.
        """
        # Convert cwd to project key format (e.g., /workspace -> -workspace)
        project_key = self.cwd.replace("/", "-")
        if not project_key.startswith("-"):
            project_key = "-" + project_key
        return (
            Path.home() / ".claude" / "projects" / project_key / f"{session_id}.jsonl"
        )

    def import_session_transcript(self) -> bool:
        """Import a session transcript from base64-encoded content.

        This enables session portability across sandboxes by:
        1. Decoding the base64 transcript content
        2. Writing it to the correct local path
        3. Enabling the resume option to find and use it

        Returns True if import succeeded, False otherwise.
        """
        if not self.session_transcript_b64 or not self.resume_session_id:
            return False

        try:
            # Decode the transcript
            transcript_content = base64.b64decode(self.session_transcript_b64).decode(
                "utf-8"
            )

            # Get the target path and ensure directory exists
            transcript_path = self.get_session_transcript_path(self.resume_session_id)
            transcript_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the transcript
            transcript_path.write_text(transcript_content)
            logger.info("Imported session transcript", extra={"session_id": self.resume_session_id, "path": str(transcript_path)})
            return True

        except Exception as e:
            logger.error("Failed to import session transcript", extra={"error": str(e)})
            return False

    def export_session_transcript(self, session_id: str) -> Optional[str]:
        """Export a session transcript as base64-encoded content.

        This can be used to save the session for later resumption on
        a different sandbox.

        Returns base64-encoded transcript content, or None if not found.
        """
        transcript_path = self.get_session_transcript_path(session_id)
        if not transcript_path.exists():
            return None

        try:
            transcript_content = transcript_path.read_text()
            return base64.b64encode(transcript_content.encode("utf-8")).decode("utf-8")
        except Exception as e:
            logger.error("Failed to export session transcript", extra={"error": str(e)})
            return None


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
                # Suppress 502 errors (Bad Gateway) - server temporarily unavailable
                # This is common during server restarts, load balancer issues, or DB timeouts
                if response.status_code == 502:
                    # Silently fail - heartbeats are non-critical and 502s are transient
                    return False
                # Log other non-200 status codes
                logger.warning("Event report failed", extra={"event_type": event_type, "status_code": response.status_code})
            return success
        except httpx.HTTPStatusError as e:
            # Handle HTTP errors (like 502 Bad Gateway)
            status_code = e.response.status_code if hasattr(e, "response") else None
            if status_code == 502:
                # Server temporarily unavailable - don't spam logs
                # Heartbeats are non-critical, so we silently fail
                return False
            else:
                logger.warning("HTTP error reporting event", extra={"event_type": event_type, "status_code": status_code})
            return False
        except httpx.RequestError as e:
            # Network-level errors (connection refused, timeout, etc.)
            # Check if it's a 502-related error
            error_str = str(e).lower()
            if "502" in error_str or "bad gateway" in error_str:
                # Silently fail for 502-related network errors
                return False
            # Log other network errors (but not for heartbeats to reduce spam)
            if event_type != "agent.heartbeat":
                logger.warning("Network error reporting event", extra={"event_type": event_type, "error": str(e)})
            return False
        except Exception as e:
            # Only log unexpected errors, not network timeouts or 502s
            error_str = str(e).lower()
            if "502" in error_str or "bad gateway" in error_str:
                # Silently fail for 502-related errors
                return False
            # Log other unexpected errors (but not for heartbeats)
            if event_type != "agent.heartbeat":
                logger.error("Failed to report event", extra={"event_type": event_type, "error": str(e)})
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
            logger.warning("Message poll failed", extra={"error": str(e)})

        return []


# =============================================================================
# GitHub Setup
# =============================================================================


def setup_github_workspace(config: WorkerConfig) -> bool:
    """Clone GitHub repo and setup workspace if configured."""
    if not config.github_token or not config.github_repo:
        logger.info("No GitHub credentials, skipping repo clone")
        return False

    # Check if already cloned
    if os.path.exists(os.path.join(config.cwd, ".git")):
        logger.info("Workspace already has git repo", extra={"cwd": config.cwd})
        return True

    # Configure git user
    subprocess.run(
        ["git", "config", "--global", "user.email", "agent@omoios.ai"], check=False
    )
    subprocess.run(
        ["git", "config", "--global", "user.name", "OmoiOS Agent"], check=False
    )

    # Clone with token
    clone_url = f"https://x-access-token:{config.github_token}@github.com/{config.github_repo}.git"
    logger.info("Cloning GitHub repository", extra={"repo": config.github_repo})

    result = subprocess.run(
        ["git", "clone", clone_url, config.cwd], capture_output=True, text=True
    )

    if result.returncode != 0:
        logger.error("GitHub clone failed", extra={"stderr": result.stderr})
        return False

    os.chdir(config.cwd)

    # Checkout branch if specified
    if config.branch_name:
        logger.info("Checking out branch", extra={"branch": config.branch_name})
        subprocess.run(["git", "checkout", config.branch_name], check=False)

    logger.info("Repository ready", extra={"cwd": config.cwd})
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
        self.file_tracker = FileChangeTracker()

    def _setup_signal_handlers(self):
        """Setup graceful shutdown on SIGTERM/SIGINT."""

        def handle_signal(signum, frame):
            logger.info("Received shutdown signal", extra={"signum": signum})
            self._shutdown_event.set()
            self._should_stop = True

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

    async def _create_post_tool_hook(self):
        """Create PostToolUse hook for comprehensive tool tracking."""
        # Capture references - reporter may be None initially, check before use
        reporter_ref = self.reporter
        file_tracker = self.file_tracker
        turn_count = self.turn_count

        async def track_tool_use(input_data, tool_use_id, context):
            """PostToolUse hook for comprehensive event reporting."""
            # Get current reporter (may have been set after hook creation)
            reporter = self.reporter or reporter_ref
            if not reporter:
                return {}  # Skip reporting if reporter not available

            tool_name = input_data.get("tool_name", "unknown")
            tool_input = input_data.get("tool_input", {})
            tool_response = input_data.get("tool_response", "")

            # NEW: File diff generation for Write/Edit
            if tool_name == "Write":
                file_path = tool_input.get("file_path")
                new_content = tool_input.get("content", "")
                if file_path and new_content:
                    try:
                        diff_info = file_tracker.generate_diff(file_path, new_content)
                        await reporter.report(
                            "agent.file_edited",
                            {
                                "turn": turn_count,
                                "tool_use_id": tool_use_id,
                                **diff_info,
                            },
                        )
                    except Exception as e:
                        logger.warning("Failed to generate diff", extra={"file_path": file_path, "error": str(e)})

            elif tool_name == "Edit":
                file_path = tool_input.get("file_path")
                if file_path:
                    try:
                        file_path = Path(file_path)
                        if file_path.exists():
                            new_content = file_path.read_text()
                            diff_info = file_tracker.generate_diff(
                                str(file_path), new_content
                            )
                            await reporter.report(
                                "agent.file_edited",
                                {
                                    "turn": turn_count,
                                    "tool_use_id": tool_use_id,
                                    **diff_info,
                                },
                            )
                    except Exception as e:
                        logger.warning("Failed to read file after edit", extra={"file_path": str(file_path), "error": str(e)})

            # Serialize tool_response properly
            # Claude SDK tool results (like CLIResult) are objects with stdout/stderr fields
            serialized_response = None
            if tool_response:
                if hasattr(tool_response, "stdout"):
                    # CLIResult-like object from Bash tool
                    serialized_response = tool_response.stdout or ""
                    if hasattr(tool_response, "stderr") and tool_response.stderr:
                        serialized_response += f"\n[stderr]: {tool_response.stderr}"
                elif hasattr(tool_response, "__dict__"):
                    # Generic object - try to serialize nicely
                    import json
                    try:
                        serialized_response = json.dumps(tool_response.__dict__, default=str)
                    except (TypeError, ValueError):
                        serialized_response = str(tool_response)
                else:
                    serialized_response = str(tool_response)

            # Full tool tracking
            event_data = {
                "turn": turn_count,
                "tool": tool_name,
                "tool_input": tool_input,
                "tool_response": serialized_response,
            }

            # Special tracking for subagents
            if tool_name == "Task":
                event_data["subagent_type"] = tool_input.get("subagent_type")
                event_data["description"] = tool_input.get("description")
                event_data["prompt"] = tool_input.get("prompt")
                await reporter.report("agent.subagent_completed", event_data)
            # Special tracking for skills
            elif tool_name == "Skill":
                event_data["skill_name"] = tool_input.get("name") or tool_input.get(
                    "skill_name"
                )
                await reporter.report("agent.skill_completed", event_data)
            else:
                await reporter.report("agent.tool_completed", event_data)

            return {}

        return track_tool_use

    async def _create_pre_tool_hook(self):
        """Create PreToolUse hook for file caching."""
        file_tracker = self.file_tracker

        async def pre_tool_use_file_cache(
            input_data: HookInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookJSONOutput:
            tool_name = input_data.get("tool_name", "")
            tool_input = input_data.get("tool_input", {})

            if tool_name in ["Write", "Edit"]:
                file_path = tool_input.get("file_path")
                if file_path:
                    file_path = Path(file_path)
                    if file_path.exists():
                        try:
                            old_content = file_path.read_text()
                            file_tracker.cache_file_before_edit(
                                str(file_path), old_content
                            )
                        except Exception as e:
                            logger.warning("Failed to cache file", extra={"file_path": str(file_path), "error": str(e)})

            return {}

        return pre_tool_use_file_cache

    async def _process_messages(
        self,
        client: "ClaudeSDKClient",
    ):
        """Process streaming messages with comprehensive event tracking."""
        final_output = []

        # Ensure reporter is available
        if not self.reporter:
            logger.warning("Reporter not available, skipping event reporting")
            # Still process messages but without reporting

        try:
            # Wrap receive_messages() with better error handling for SIGKILL (-9) errors
            try:
                message_stream = client.receive_messages()
            except Exception as stream_init_error:
                error_msg = str(stream_init_error)
                logger.error("Failed to initialize message stream", extra={"error": error_msg})
                if self.reporter:
                    await self.reporter.report(
                        "agent.stream_error",
                        {
                            "error": f"Stream initialization failed: {error_msg}",
                            "turn": self.turn_count,
                            "error_type": "stream_init",
                        },
                    )
                raise

            async for msg in message_stream:
                if isinstance(msg, AssistantMessage):
                    self.turn_count += 1

                    # Report assistant message metadata
                    if self.reporter:
                        await self.reporter.report(
                            "agent.assistant_message",
                            {
                                "turn": self.turn_count,
                                "model": getattr(msg, "model", self.config.model),
                                "stop_reason": getattr(msg, "stop_reason", None),
                                "block_count": len(msg.content),
                            },
                        )

                    for block in msg.content:
                        if isinstance(block, ThinkingBlock):
                            if self.reporter:
                                await self.reporter.report(
                                    "agent.thinking",
                                    {
                                        "turn": self.turn_count,
                                        "content": block.text,  # Full content
                                        "thinking_type": "extended_thinking",
                                    },
                                )
                            logger.debug("Agent thinking", extra={"content_preview": block.text[:100]})

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
                                tool_event["subagent_type"] = block.input.get(
                                    "subagent_type"
                                )
                                tool_event["subagent_description"] = block.input.get(
                                    "description"
                                )
                                tool_event["subagent_prompt"] = block.input.get(
                                    "prompt"
                                )
                                if self.reporter:
                                    await self.reporter.report(
                                        "agent.subagent_invoked", tool_event
                                    )
                                logger.info("Subagent invoked", extra={"subagent_type": block.input.get('subagent_type')})

                            # Special handling for skill invocation
                            elif block.name == "Skill":
                                tool_event["event_subtype"] = "skill_invoked"
                                tool_event["skill_name"] = block.input.get(
                                    "name"
                                ) or block.input.get("skill_name")
                                if self.reporter:
                                    await self.reporter.report(
                                        "agent.skill_invoked", tool_event
                                    )
                                logger.info("Skill invoked", extra={"skill_name": tool_event['skill_name']})

                            # Standard tool use
                            else:
                                tool_event["event_subtype"] = "tool_use"
                                if self.reporter:
                                    await self.reporter.report(
                                        "agent.tool_use", tool_event
                                    )
                                logger.info("Tool use", extra={"tool": block.name})

                        elif isinstance(block, ToolResultBlock):
                            result_content = str(block.content)
                            if self.reporter:
                                await self.reporter.report(
                                    "agent.tool_result",
                                    {
                                        "turn": self.turn_count,
                                        "tool_use_id": block.tool_use_id,
                                        "result": result_content[:5000]
                                        if len(result_content) > 5000
                                        else result_content,
                                        "result_truncated": len(result_content) > 5000,
                                        "result_full_length": len(result_content),
                                        "is_error": getattr(block, "is_error", False),
                                    },
                                )
                            is_error = getattr(block, "is_error", False)
                            logger.debug("Tool result", extra={"is_error": is_error, "result_preview": result_content[:80]})

                        elif isinstance(block, TextBlock):
                            if self.reporter:
                                await self.reporter.report(
                                    "agent.message",
                                    {
                                        "turn": self.turn_count,
                                        "content": block.text,  # Full content
                                        "content_length": len(block.text),
                                    },
                                )
                            final_output.append(block.text)
                            logger.debug("Agent message", extra={"content_preview": block.text[:100]})

                elif isinstance(msg, UserMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            if self.reporter:
                                await self.reporter.report(
                                    "agent.user_message",
                                    {
                                        "turn": self.turn_count,
                                        "content": block.text,
                                        "content_length": len(block.text),
                                    },
                                )
                        elif isinstance(block, ToolResultBlock):
                            result_content = str(block.content)
                            if self.reporter:
                                await self.reporter.report(
                                    "agent.user_tool_result",
                                    {
                                        "turn": self.turn_count,
                                        "tool_use_id": block.tool_use_id,
                                        "result": result_content[:5000]
                                        if len(result_content) > 5000
                                        else result_content,
                                        "result_truncated": len(result_content) > 5000,
                                    },
                                )

                elif isinstance(msg, SystemMessage):
                    if self.reporter:
                        await self.reporter.report(
                            "agent.system_message",
                            {
                                "turn": self.turn_count,
                                "metadata": getattr(msg, "metadata", {}),
                            },
                        )

                elif isinstance(msg, ResultMessage):
                    usage = getattr(msg, "usage", None)

                    # Export session transcript for cross-sandbox resumption
                    transcript_b64 = None
                    if hasattr(msg, "session_id") and msg.session_id:
                        try:
                            transcript_b64 = self.config.export_session_transcript(
                                msg.session_id
                            )
                            if transcript_b64:
                                logger.info("Exported session transcript", extra={"size_bytes": len(transcript_b64)})
                        except Exception as e:
                            logger.warning("Failed to export session transcript", extra={"error": str(e)})

                    # Safely extract message attributes (handle both object and dict)
                    num_turns = getattr(msg, "num_turns", None)
                    total_cost_usd = getattr(msg, "total_cost_usd", 0.0)
                    session_id = getattr(msg, "session_id", None)
                    stop_reason = getattr(msg, "stop_reason", None)

                    if self.reporter:
                        # Handle usage as dict or object
                        input_tokens = None
                        output_tokens = None
                        cache_read_tokens = None
                        cache_write_tokens = None

                        if usage:
                            if isinstance(usage, dict):
                                input_tokens = usage.get("input_tokens")
                                output_tokens = usage.get("output_tokens")
                                cache_read_tokens = usage.get("cache_read_input_tokens")
                                cache_write_tokens = usage.get(
                                    "cache_creation_input_tokens"
                                )
                            else:
                                input_tokens = getattr(usage, "input_tokens", None)
                                output_tokens = getattr(usage, "output_tokens", None)
                                cache_read_tokens = getattr(
                                    usage, "cache_read_input_tokens", None
                                )
                                cache_write_tokens = getattr(
                                    usage, "cache_creation_input_tokens", None
                                )

                        # Build completion event with final output
                        completion_event: dict[str, Any] = {
                            "success": True,
                            "turns": num_turns,
                            "cost_usd": total_cost_usd,
                            "session_id": session_id,
                            "transcript_b64": transcript_b64,  # Include transcript for server storage
                            "stop_reason": stop_reason,
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "cache_read_tokens": cache_read_tokens,
                            "cache_write_tokens": cache_write_tokens,
                            "final_output": "\n".join(final_output)
                            if final_output
                            else None,  # Include final output for task result
                        }

                        # Try to report completion with retries (critical for task finalization)
                        max_retries = 3
                        retry_delay: float = 1.0
                        reported = False

                        for attempt in range(max_retries):
                            reported: bool = await self.reporter.report(
                                "agent.completed",
                                completion_event,
                            )
                            if reported:
                                break
                            if attempt < max_retries - 1:
                                logger.warning("Retrying completion event", extra={"attempt": attempt + 1, "max_retries": max_retries})
                                await asyncio.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff

                        if not reported:
                            logger.warning("Failed to report completion after retries - task status may not update")
                    logger.info("Agent completed", extra={"turns": num_turns, "cost_usd": total_cost_usd})
                    return msg, final_output

        except Exception as e:
            error_str = str(e)
            error_type = "unknown"

            # Detect specific error types
            if "exit code -9" in error_str or "SIGKILL" in error_str:
                error_type = "sigkill"
                logger.error("Stream error: Process killed (SIGKILL/exit -9)", extra={
                    "possible_causes": ["OOM killer", "Resource limits exceeded", "Process timeout", "System resource constraints"]
                })
            elif "Command failed" in error_str:
                error_type = "command_failed"
                logger.error("Stream error: Command failed in message reader", extra={"error": error_str})
            else:
                logger.error("Stream error", extra={"error": str(e)})

            if self.reporter:
                await self.reporter.report(
                    "agent.stream_error",
                    {
                        "error": error_str,
                        "error_type": error_type,
                        "turn": self.turn_count,
                        "final_output_length": len("\n".join(final_output))
                        if final_output
                        else 0,
                    },
                )

            # If we have partial output, return it instead of None
            if final_output:
                logger.warning("Returning partial output", extra={"block_count": len(final_output)})

        return None, final_output

    async def run(self):
        """Main worker loop with comprehensive event tracking."""
        self._setup_signal_handlers()
        self.running = True

        logger.info("=" * 60)
        logger.info("CLAUDE SANDBOX WORKER (Production)")
        logger.info("=" * 60)
        logger.info("Configuration: %s", self.config.to_dict())

        # Validate config
        errors = self.config.validate()
        if errors:
            logger.error("Configuration errors", extra={"errors": errors})
            return 1

        if not SDK_AVAILABLE:
            logger.error("claude_agent_sdk package not installed - Run: pip install claude-agent-sdk")
            return 1

        # Setup workspace
        Path(self.config.cwd).mkdir(parents=True, exist_ok=True)
        setup_github_workspace(self.config)

        # Import session transcript if provided (for cross-sandbox resumption)
        if self.config.session_transcript_b64 and self.config.resume_session_id:
            logger.info("Importing session transcript for cross-sandbox resumption")
            if self.config.import_session_transcript():
                logger.info("Session transcript imported successfully")
            else:
                logger.warning("Session transcript import failed, starting fresh")
                self.config.resume_session_id = None  # Reset to avoid resume failure

        async with EventReporter(self.config) as reporter:
            self.reporter = reporter

            async with MessagePoller(self.config) as poller:
                # Create hooks and options
                pre_tool_hook = await self._create_pre_tool_hook()
                post_tool_hook = await self._create_post_tool_hook()
                sdk_options = self.config.to_sdk_options(
                    pre_tool_hook=pre_tool_hook,
                    post_tool_hook=post_tool_hook,
                )

                # Report startup
                await reporter.report(
                    "agent.started",
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "sdk": "claude_agent_sdk",
                        "model": self.config.model or "default",
                        "task": self.config.initial_prompt
                        or self.config.ticket_description,
                        "ticket_title": self.config.ticket_title,
                        "resumed_session_id": self.config.resume_session_id,
                        "is_resuming": bool(self.config.resume_session_id),
                        "fork_session": self.config.fork_session,
                    },
                    source="worker",
                )

                try:
                    # Debug: Log options structure before creating client
                    logger.debug("Creating SDK client with options")
                    logger.debug("SDK options type", extra={"options_type": str(type(sdk_options))})
                    if hasattr(sdk_options, "hooks") and sdk_options.hooks:
                        logger.debug(
                            "Hooks present in SDK options",
                            extra={"hooks": list(sdk_options.hooks.keys())}
                        )

                    async with ClaudeSDKClient(options=sdk_options) as client:
                        # Process initial prompt
                        initial_task = (
                            self.config.initial_prompt
                            or self.config.ticket_description
                            or f"Analyze ticket: {self.config.ticket_title}"
                        )

                        if initial_task and initial_task.strip():
                            logger.info("Processing initial task", extra={"task_preview": initial_task[:100]})
                            try:
                                await client.query(initial_task)
                                await self._process_messages(client)
                            except Exception as e:
                                logger.error("Failed to process initial task", extra={"error": str(e)}, exc_info=True)
                                if self.reporter:
                                    await self.reporter.report(
                                        "agent.error",
                                        {
                                            "error": f"Initial task failed: {str(e)}",
                                            "phase": "initial_task",
                                        },
                                    )
                        else:
                            logger.warning(
                                "No initial task provided - worker will wait for messages"
                            )

                        # Report ready
                        await reporter.report(
                            "agent.waiting",
                            {"message": "Ready for messages"},
                        )
                        logger.info("Waiting for messages")

                        # Main loop
                        last_heartbeat = asyncio.get_event_loop().time()
                        intervention_count = 0

                        while not self._shutdown_event.is_set():
                            try:
                                # Check for stop
                                if self._should_stop:
                                    await client.interrupt()
                                    await reporter.report(
                                        "agent.interrupted",
                                        {
                                            "reason": "shutdown_signal",
                                            "turn": self.turn_count,
                                        },
                                    )
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

                                    logger.info("Received message", extra={"msg_type": msg_type, "content_preview": content[:80]})

                                    # Handle interrupt
                                    if msg_type == "interrupt":
                                        self._should_stop = True
                                        await client.interrupt()
                                        await reporter.report(
                                            "agent.interrupted",
                                            {
                                                "reason": content,
                                                "sender_id": sender_id,
                                                "turn": self.turn_count,
                                            },
                                        )
                                        break

                                    # Report message injection
                                    await reporter.report(
                                        "agent.message_injected",
                                        {
                                            "message_type": msg_type,
                                            "content": content,  # Full content
                                            "content_length": len(content),
                                            "sender_id": sender_id,
                                            "message_id": message_id,
                                            "intervention_number": intervention_count,
                                            "turn": self.turn_count,
                                        },
                                    )

                                    # Process message
                                    try:
                                        await client.query(content)
                                        await self._process_messages(client)
                                    except Exception as e:
                                        logger.error("Failed to process message", extra={"error": str(e)}, exc_info=True)
                                        if self.reporter:
                                            await self.reporter.report(
                                                "agent.error",
                                                {
                                                    "error": f"Message processing failed: {str(e)}",
                                                    "message_type": msg_type,
                                                    "content_length": len(content),
                                                },
                                            )

                                    # Report ready
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

                                await asyncio.sleep(self.config.poll_interval)

                            except asyncio.CancelledError:
                                break
                            except Exception as e:
                                logger.error("Main loop error", extra={"error": str(e)}, exc_info=True)
                                await reporter.report("agent.error", {"error": str(e)})
                                await asyncio.sleep(1)

                except Exception as e:
                    import traceback

                    logger.error(
                        "SDK initialization error",
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "traceback": traceback.format_exc(),
                        },
                        exc_info=True,
                    )

                    # Try to identify what's causing the asdict() error
                    if "asdict()" in str(e):
                        debug_info = {"options_type": str(type(sdk_options))}
                        if hasattr(sdk_options, "__dict__"):
                            debug_info["options_keys"] = list(sdk_options.__dict__.keys())
                            if hasattr(sdk_options, "hooks"):
                                debug_info["hooks_type"] = str(type(sdk_options.hooks))
                                if sdk_options.hooks:
                                    hooks_debug = {}
                                    for hook_type, hook_list in sdk_options.hooks.items():
                                        hooks_debug[hook_type] = {
                                            "type": str(type(hook_list)),
                                            "length": len(hook_list) if isinstance(hook_list, list) else "N/A",
                                        }
                                        if isinstance(hook_list, list) and hook_list:
                                            hooks_debug[hook_type]["first_item_type"] = str(type(hook_list[0]))
                                    debug_info["hooks"] = hooks_debug
                        logger.debug("asdict() error - options structure debug", extra=debug_info)

                    await reporter.report(
                        "agent.error",
                        {
                            "error": str(e),
                            "phase": "initialization",
                            "traceback": traceback.format_exc(),
                        },
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
                logger.info("Worker shutdown complete", extra={"total_turns": self.turn_count})

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
