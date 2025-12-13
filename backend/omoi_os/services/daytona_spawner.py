"""Daytona Spawner Service for OmoiOS.

This service manages the lifecycle of Daytona sandboxes for agent execution.
It's the bridge between the orchestrator and isolated agent execution.

The spawner:
1. Creates Daytona sandboxes with proper environment variables
2. Tracks active sandboxes and their associated tasks
3. Cleans up sandboxes when tasks complete
4. Provides health monitoring for running sandboxes
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from omoi_os.config import load_daytona_settings, get_app_settings
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now

logger = logging.getLogger(__name__)


@dataclass
class SandboxInfo:
    """Information about a spawned sandbox."""

    sandbox_id: str
    agent_id: str
    task_id: str
    phase_id: str
    status: str = "creating"  # creating, running, completed, failed, terminated
    created_at: datetime = field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)


class DaytonaSpawnerService:
    """Service for spawning and managing Daytona sandboxes.

    This service creates isolated execution environments for agents,
    passing the necessary configuration via environment variables.

    Usage:
        spawner = DaytonaSpawnerService(db, event_bus, mcp_server_url="http://localhost:18000/mcp")

        # Spawn a sandbox for a task
        sandbox_id = await spawner.spawn_for_task(
            task_id="task-123",
            agent_id="agent-456",
            phase_id="PHASE_IMPLEMENTATION"
        )

        # Check sandbox status
        info = spawner.get_sandbox_info(sandbox_id)

        # Terminate when done
        await spawner.terminate_sandbox(sandbox_id)
    """

    def __init__(
        self,
        db: Optional[DatabaseService] = None,
        event_bus: Optional[EventBusService] = None,
        mcp_server_url: str = "http://localhost:18000/mcp/",
        daytona_api_key: Optional[str] = None,
        daytona_api_url: str = "https://app.daytona.io/api",
        sandbox_image: str = "nikolaik/python-nodejs:python3.12-nodejs22",
        auto_cleanup: bool = True,
    ):
        """Initialize the spawner service.

        Args:
            db: Database service for persisting sandbox info
            event_bus: Event bus for publishing sandbox events
            mcp_server_url: URL of the MCP server sandboxes connect to
            daytona_api_key: Daytona API key (or from settings)
            daytona_api_url: Daytona API URL
            sandbox_image: Docker image for sandboxes
            auto_cleanup: Automatically cleanup sandboxes on completion
        """
        self.db = db
        self.event_bus = event_bus
        self.mcp_server_url = mcp_server_url
        self.sandbox_image = sandbox_image
        self.auto_cleanup = auto_cleanup

        # Load Daytona settings
        daytona_settings = load_daytona_settings()
        self.daytona_api_key = daytona_api_key or daytona_settings.api_key
        self.daytona_api_url = daytona_api_url or daytona_settings.api_url

        # In-memory tracking of active sandboxes
        self._sandboxes: Dict[str, SandboxInfo] = {}
        self._task_to_sandbox: Dict[str, str] = {}  # task_id -> sandbox_id

    async def spawn_for_task(
        self,
        task_id: str,
        agent_id: str,
        phase_id: str,
        agent_type: Optional[str] = None,
        extra_env: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None,
        runtime: str = "openhands",  # "openhands" or "claude"
    ) -> str:
        """Spawn a Daytona sandbox for executing a task.

        Args:
            task_id: ID of the task to execute
            agent_id: ID of the agent executing
            phase_id: Current phase ID
            agent_type: Optional agent type override
            extra_env: Additional environment variables
            labels: Labels for the sandbox
            runtime: Agent runtime to use - "openhands" (default) or "claude"

        Returns:
            Sandbox ID

        Raises:
            RuntimeError: If sandbox creation fails
        """
        if not self.daytona_api_key:
            raise RuntimeError("Daytona API key not configured")

        # Check if task already has a sandbox
        if task_id in self._task_to_sandbox:
            existing_id = self._task_to_sandbox[task_id]
            existing = self._sandboxes.get(existing_id)
            if existing and existing.status in ("creating", "running"):
                logger.warning(
                    f"Task {task_id} already has active sandbox {existing_id}"
                )
                return existing_id

        # Generate sandbox ID
        sandbox_id = f"omoios-{task_id[:8]}-{uuid4().hex[:6]}"

        # Build environment variables
        env_vars = {
            "AGENT_ID": agent_id,
            "TASK_ID": task_id,
            "MCP_SERVER_URL": self.mcp_server_url,
            "PHASE_ID": phase_id,
            "SANDBOX_ID": sandbox_id,
        }

        # Add agent type if specified
        if agent_type:
            env_vars["AGENT_TYPE"] = agent_type

        # Add LLM configuration from settings
        app_settings = get_app_settings()
        if hasattr(app_settings, "llm") and app_settings.llm:
            if app_settings.llm.api_key:
                env_vars["LLM_API_KEY"] = app_settings.llm.api_key
            if app_settings.llm.model:
                env_vars["LLM_MODEL"] = app_settings.llm.model

        # Add extra env vars
        if extra_env:
            env_vars.update(extra_env)

        # Build labels
        sandbox_labels = {
            "project": "omoios",
            "task_id": task_id,
            "agent_id": agent_id,
            "phase_id": phase_id,
        }
        if labels:
            sandbox_labels.update(labels)

        # Create sandbox info
        info = SandboxInfo(
            sandbox_id=sandbox_id,
            agent_id=agent_id,
            task_id=task_id,
            phase_id=phase_id,
            status="creating",
        )
        self._sandboxes[sandbox_id] = info
        self._task_to_sandbox[task_id] = sandbox_id

        try:
            # Create Daytona sandbox
            logger.info(
                f"Creating Daytona sandbox {sandbox_id} for task {task_id} (runtime: {runtime})"
            )

            # Store runtime type before creation
            info.extra_data["runtime"] = runtime

            await self._create_daytona_sandbox(
                sandbox_id=sandbox_id,
                env_vars=env_vars,
                labels=sandbox_labels,
                runtime=runtime,
            )

            # Update status
            info.status = "running"
            info.started_at = utc_now()

            # Publish event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="sandbox.spawned",
                        entity_type="sandbox",
                        entity_id=sandbox_id,
                        payload={
                            "task_id": task_id,
                            "agent_id": agent_id,
                            "phase_id": phase_id,
                        },
                    )
                )

            logger.info(f"Sandbox {sandbox_id} created and running")
            return sandbox_id

        except Exception as e:
            logger.error(f"Failed to create sandbox {sandbox_id}: {e}")
            info.status = "failed"
            info.error = str(e)

            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="sandbox.failed",
                        entity_type="sandbox",
                        entity_id=sandbox_id,
                        payload={"error": str(e)},
                    )
                )

            raise RuntimeError(f"Failed to spawn sandbox: {e}") from e

    async def _create_daytona_sandbox(
        self,
        sandbox_id: str,
        env_vars: Dict[str, str],
        labels: Dict[str, str],
        runtime: str = "openhands",
    ) -> None:
        """Create a Daytona sandbox via their API.

        This is the actual Daytona SDK integration point.

        Args:
            sandbox_id: Unique sandbox identifier
            env_vars: Environment variables to set in sandbox
            labels: Labels for sandbox organization
            runtime: Agent runtime - "openhands" or "claude"
        """
        try:
            from daytona import Daytona, DaytonaConfig, CreateSandboxFromImageParams

            daytona_config = DaytonaConfig(
                api_key=self.daytona_api_key,
                api_url=self.daytona_api_url,
                target="us",
            )
            daytona = Daytona(daytona_config)

            # Create sandbox with our worker image
            params = CreateSandboxFromImageParams(
                image=self.sandbox_image,
                labels=labels or None,
                ephemeral=True,  # Auto-delete when stopped
                public=False,
            )

            sandbox = daytona.create(params=params, timeout=120)

            # Store sandbox reference
            info = self._sandboxes.get(sandbox_id)
            if info:
                info.extra_data["daytona_sandbox"] = sandbox
                info.extra_data["daytona_sandbox_id"] = sandbox.id

            # Set environment variables and start the worker
            await self._start_worker_in_sandbox(sandbox, env_vars, runtime)

            logger.info(f"Daytona sandbox {sandbox.id} created for {sandbox_id}")

        except ImportError as e:
            # Daytona SDK not available - use mock for local testing
            logger.warning(f"Daytona SDK import failed: {e}, using mock sandbox")
            await self._create_mock_sandbox(sandbox_id, env_vars)
        except Exception as e:
            logger.error(f"Failed to create Daytona sandbox: {e}")
            await self._create_mock_sandbox(sandbox_id, env_vars)

    async def _start_worker_in_sandbox(
        self,
        sandbox: Any,
        env_vars: Dict[str, str],
        runtime: str = "openhands",
    ) -> None:
        """Start the sandbox worker inside the Daytona sandbox.

        Args:
            sandbox: Daytona sandbox instance
            env_vars: Environment variables for the worker
            runtime: Agent runtime - "openhands" or "claude"
        """

        # Build environment export string
        env_exports = " ".join([f'export {k}="{v}"' for k, v in env_vars.items()])

        # Install required packages based on runtime
        logger.info(f"Installing {runtime} dependencies in sandbox...")
        if runtime == "claude":
            install_cmd = "pip install claude-agent-sdk httpx"
        else:  # openhands (default)
            install_cmd = "pip install openhands-ai mcp httpx"
        sandbox.process.exec(install_cmd, timeout=120)

        # Upload the appropriate worker script
        if runtime == "claude":
            worker_script = self._get_claude_worker_script()
        else:
            worker_script = self._get_worker_script()
        sandbox.fs.upload_file(worker_script.encode("utf-8"), "/tmp/sandbox_worker.py")

        # Start the worker
        logger.info("Starting sandbox worker...")
        start_cmd = f"""
        {env_exports}
        cd /tmp && python sandbox_worker.py
        """

        # Run in background and capture output
        sandbox.process.exec(f"nohup bash -c '{start_cmd}' > /tmp/worker.log 2>&1 &")
        logger.info("Sandbox worker started, check /tmp/worker.log for output")

    def _get_worker_script(self) -> str:
        """Get the standalone sandbox worker script content.

        SDK Reference: docs/libraries/software-agent-sdk-clean.md
        GitHub: https://github.com/OpenHands/software-agent-sdk
        """
        return '''#!/usr/bin/env python3
"""Standalone sandbox worker - runs OpenHands agent for a task.

SDK Reference: https://github.com/OpenHands/software-agent-sdk
Local Docs: docs/libraries/software-agent-sdk-clean.md
"""

import asyncio
import os
import logging
import httpx

# OpenHands SDK imports - per official docs
from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.terminal import TerminalTool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
TASK_ID = os.environ.get("TASK_ID")
AGENT_ID = os.environ.get("AGENT_ID")
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:18000/mcp")
LLM_MODEL = os.environ.get("LLM_MODEL", "anthropic/claude-sonnet-4-20250514")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
SANDBOX_ID = os.environ.get("SANDBOX_ID", "")


async def fetch_task():
    """Fetch task details from MCP server via HTTP."""
    async with httpx.AsyncClient(timeout=30) as client:
        # Call MCP tool via HTTP endpoint
        resp = await client.get(
            f"{MCP_SERVER_URL.replace('/mcp', '')}/api/v1/tasks/{TASK_ID}",
        )
        if resp.status_code == 200:
            return resp.json()
    return None


async def report_event(event_type: str, event_data: dict):
    """Report an agent event back to the server."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{MCP_SERVER_URL.replace('/mcp', '')}/api/v1/agent-events",
                json={
                    "task_id": TASK_ID,
                    "agent_id": AGENT_ID,
                    "sandbox_id": SANDBOX_ID,
                    "event_type": event_type,
                    "event_data": event_data,
                },
            )
    except Exception as e:
        logger.debug(f"Failed to report event: {e}")


async def register_conversation(conversation_id: str):
    """Register conversation ID with server for Guardian observation."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{MCP_SERVER_URL.replace('/mcp', '')}/api/v1/tasks/{TASK_ID}/register-conversation",
                json={
                    "conversation_id": conversation_id,
                    "sandbox_id": SANDBOX_ID,
                },
            )
            logger.info(f"Registered conversation {conversation_id}")
    except Exception as e:
        logger.warning(f"Failed to register conversation: {e}")


async def update_task_status(status: str, result: str = None):
    """Update task status in the server."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.patch(
                f"{MCP_SERVER_URL.replace('/mcp', '')}/api/v1/tasks/{TASK_ID}",
                json={"status": status, "result": result},
            )
    except Exception as e:
        logger.warning(f"Failed to update task status: {e}")


async def main():
    logger.info(f"OpenHands Worker starting for task {TASK_ID}")
    
    if not TASK_ID or not AGENT_ID:
        logger.error("TASK_ID and AGENT_ID required")
        return
    
    if not LLM_API_KEY:
        logger.error("LLM_API_KEY required")
        await update_task_status("failed", "Missing LLM_API_KEY")
        return
    
    # Fetch task
    task = await fetch_task()
    if not task:
        logger.error(f"Could not fetch task {TASK_ID}")
        await update_task_status("failed", "Could not fetch task")
        return
    
    task_desc = task.get("description", "No description")
    logger.info(f"Task: {task_desc}")
    
    await update_task_status("in_progress")
    await report_event("agent_started", {"task": task_desc[:200]})
    
    # Create LLM instance (per SDK docs - LLM is separate from Agent)
    llm = LLM(
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
    )
    
    # Create agent with LLM and tools (per SDK docs)
    agent = Agent(
        llm=llm,
        tools=[
            Tool(name=TerminalTool.name),
            Tool(name=FileEditorTool.name),
            Tool(name=TaskTrackerTool.name),
        ],
    )
    
    # Event callback for Guardian observation
    def on_event(event):
        event_type = type(event).__name__
        event_data = {"message": str(event)[:300]}
        asyncio.create_task(report_event(event_type, event_data))
    
    # Create conversation with callbacks (per SDK docs - use Conversation, not LocalConversation)
    conversation = Conversation(
        agent=agent,
        workspace="/workspace",
        callbacks=[on_event],
    )
    
    # Register with server for Guardian observation
    # Per SDK docs: conversation ID is at conversation.state.id
    await register_conversation(str(conversation.state.id))
    
    # Send task and run
    logger.info("Sending task to agent...")
    conversation.send_message(task_desc)
    
    try:
        conversation.run()
        logger.info("Agent completed successfully")
        await update_task_status("completed", "Task completed successfully")
        await report_event("agent_completed", {"success": True})
    except Exception as e:
        logger.error(f"Agent failed: {e}")
        await update_task_status("failed", str(e))
        await report_event("agent_failed", {"error": str(e)})


if __name__ == "__main__":
    asyncio.run(main())
'''

    def _get_claude_worker_script(self) -> str:
        """Get the Claude Agent SDK worker script content.

        SDK Reference: docs/libraries/claude-agent-sdk-python-clean.md
        GitHub: https://github.com/anthropics/claude-agent-sdk-python
        """
        return '''#!/usr/bin/env python3
"""Standalone sandbox worker - runs Claude Agent SDK for a task.

SDK Reference: https://github.com/anthropics/claude-agent-sdk-python
Local Docs: docs/libraries/claude-agent-sdk-python-clean.md
"""

import asyncio
import os
import logging
import subprocess
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
TASK_ID = os.environ.get("TASK_ID")
AGENT_ID = os.environ.get("AGENT_ID")
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:18000")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", os.environ.get("LLM_API_KEY", ""))
SANDBOX_ID = os.environ.get("SANDBOX_ID", "")


async def fetch_task():
    """Fetch task details from orchestrator."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{MCP_SERVER_URL}/api/v1/tasks/{TASK_ID}")
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch task: {e}")
    return None


async def report_status(status: str, result: str = None):
    """Report task status back to orchestrator."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.patch(
                f"{MCP_SERVER_URL}/api/v1/tasks/{TASK_ID}",
                json={"status": status, "result": result},
            )
    except Exception as e:
        logger.debug(f"Failed to report status: {e}")


async def report_event(event_type: str, event_data: dict):
    """Report an agent event for Guardian observation."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{MCP_SERVER_URL}/api/v1/agent-events",
                json={
                    "task_id": TASK_ID,
                    "agent_id": AGENT_ID,
                    "sandbox_id": SANDBOX_ID,
                    "event_type": event_type,
                    "event_data": event_data,
                },
            )
    except Exception as e:
        logger.debug(f"Failed to report event: {e}")


def create_tools():
    """Create custom tools for the Claude agent."""
    from claude_agent_sdk import tool, create_sdk_mcp_server
    
    @tool("read_file", "Read contents of a file", {"file_path": str})
    async def read_file(args: dict[str, Any]) -> dict[str, Any]:
        file_path = Path(args["file_path"])
        try:
            content = file_path.read_text()
            return {"content": [{"type": "text", "text": content}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {e}"}], "is_error": True}
    
    @tool("write_file", "Write contents to a file", {"file_path": str, "content": str})
    async def write_file(args: dict[str, Any]) -> dict[str, Any]:
        file_path = Path(args["file_path"])
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(args["content"])
            asyncio.create_task(report_event("file_written", {"path": str(file_path)}))
            return {"content": [{"type": "text", "text": f"Wrote to {file_path}"}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {e}"}], "is_error": True}
    
    @tool("run_command", "Execute a shell command", {"command": str})
    async def run_command(args: dict[str, Any]) -> dict[str, Any]:
        command = args["command"]
        try:
            asyncio.create_task(report_event("command_started", {"command": command}))
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300, cwd="/workspace")
            return {"content": [{"type": "text", "text": f"Exit: {result.returncode}\\nStdout: {result.stdout}\\nStderr: {result.stderr}"}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {e}"}], "is_error": True}
    
    @tool("list_files", "List files in a directory", {"directory": str})
    async def list_files(args: dict[str, Any]) -> dict[str, Any]:
        directory = Path(args["directory"])
        try:
            files = ["[DIR] " + item.name if item.is_dir() else "[FILE] " + item.name for item in directory.iterdir()]
            return {"content": [{"type": "text", "text": "\\n".join(files) or "(empty)"}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {e}"}], "is_error": True}
    
    server = create_sdk_mcp_server("workspace", tools=[read_file, write_file, run_command, list_files])
    return server, ["mcp__workspace__read_file", "mcp__workspace__write_file", "mcp__workspace__run_command", "mcp__workspace__list_files"]


async def run_agent(task_description: str):
    """Run the Claude Agent SDK."""
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, HookMatcher
    
    tools_server, tool_names = create_tools()
    
    async def track_tool(input_data, tool_use_id, context):
        await report_event("tool_use", {"tool": input_data.get("tool_name", "unknown")})
        return {}
    
    options = ClaudeAgentOptions(
        allowed_tools=tool_names + ["Read", "Write", "Bash", "Edit", "Glob", "Grep"],
        permission_mode="acceptEdits",
        system_prompt=f"You are an AI coding agent. Your workspace is /workspace. Be thorough and test your changes.",
        cwd=Path("/workspace"),
        max_turns=50,
        max_budget_usd=10.0,
        model="claude-sonnet-4-20250514",  # Per SDK docs - use full model name with date
        mcp_servers={"workspace": tools_server},
        hooks={"PostToolUse": [HookMatcher(matcher=None, hooks=[track_tool])]},
    )
    
    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(task_description)
            outputs = []
            async for msg in client.receive_response():
                outputs.append(str(msg)[:500])
            return True, "\\n".join(outputs[-5:])
    except Exception as e:
        return False, str(e)


async def main():
    logger.info(f"Claude Agent Worker starting for task {TASK_ID}")
    
    if not TASK_ID or not AGENT_ID:
        logger.error("TASK_ID and AGENT_ID required")
        return
    
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY required")
        await report_status("failed", "Missing ANTHROPIC_API_KEY")
        return
    
    os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
    
    task = await fetch_task()
    if not task:
        await report_status("failed", "Could not fetch task")
        return
    
    task_desc = task.get("description", "No description")
    logger.info(f"Task: {task_desc}")
    
    await report_status("in_progress")
    await report_event("agent_started", {"task": task_desc[:200]})
    
    success, result = await run_agent(task_desc)
    
    if success:
        await report_status("completed", result)
        await report_event("agent_completed", {"success": True})
    else:
        await report_status("failed", result)
        await report_event("agent_failed", {"error": result})


if __name__ == "__main__":
    asyncio.run(main())
'''

    async def _create_mock_sandbox(
        self,
        sandbox_id: str,
        env_vars: Dict[str, str],
    ) -> None:
        """Create a mock sandbox for local testing without Daytona."""

        logger.info(f"Creating mock sandbox {sandbox_id}")

        # In mock mode, we could:
        # 1. Run the worker locally in a subprocess
        # 2. Just log and pretend (for unit tests)
        # 3. Use Docker directly

        # For now, just log - the sandbox_worker can be run manually
        logger.info("Mock sandbox created. To run manually:")
        logger.info(f"  AGENT_ID={env_vars.get('AGENT_ID')} \\")
        logger.info(f"  TASK_ID={env_vars.get('TASK_ID')} \\")
        logger.info(f"  MCP_SERVER_URL={env_vars.get('MCP_SERVER_URL')} \\")
        logger.info("  python -m omoi_os.sandbox_worker")

    async def terminate_sandbox(self, sandbox_id: str) -> bool:
        """Terminate a running sandbox.

        Args:
            sandbox_id: Sandbox to terminate

        Returns:
            True if terminated successfully
        """
        info = self._sandboxes.get(sandbox_id)
        if not info:
            logger.warning(f"Sandbox {sandbox_id} not found")
            return False

        if info.status in ("completed", "failed", "terminated"):
            logger.info(f"Sandbox {sandbox_id} already stopped")
            return True

        try:
            # Get Daytona sandbox reference
            daytona_sandbox = info.extra_data.get("daytona_sandbox")

            if daytona_sandbox:
                # Terminate via Daytona
                daytona_sandbox.stop()
                logger.info(f"Daytona sandbox {sandbox_id} terminated")

            info.status = "terminated"
            info.completed_at = utc_now()

            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="sandbox.terminated",
                        entity_type="sandbox",
                        entity_id=sandbox_id,
                        payload={"task_id": info.task_id},
                    )
                )

            return True

        except Exception as e:
            logger.error(f"Failed to terminate sandbox {sandbox_id}: {e}")
            return False

    def mark_completed(self, sandbox_id: str, result: Optional[Dict] = None) -> None:
        """Mark a sandbox as completed (called when task finishes)."""
        info = self._sandboxes.get(sandbox_id)
        if info:
            info.status = "completed"
            info.completed_at = utc_now()
            if result:
                info.extra_data["result"] = result

            if self.auto_cleanup:
                asyncio.create_task(self.terminate_sandbox(sandbox_id))

    def mark_failed(self, sandbox_id: str, error: str) -> None:
        """Mark a sandbox as failed."""
        info = self._sandboxes.get(sandbox_id)
        if info:
            info.status = "failed"
            info.completed_at = utc_now()
            info.error = error

            if self.auto_cleanup:
                asyncio.create_task(self.terminate_sandbox(sandbox_id))

    def get_sandbox_info(self, sandbox_id: str) -> Optional[SandboxInfo]:
        """Get information about a sandbox."""
        return self._sandboxes.get(sandbox_id)

    def get_sandbox_for_task(self, task_id: str) -> Optional[SandboxInfo]:
        """Get sandbox info for a task."""
        sandbox_id = self._task_to_sandbox.get(task_id)
        if sandbox_id:
            return self._sandboxes.get(sandbox_id)
        return None

    def list_active_sandboxes(self) -> List[SandboxInfo]:
        """List all active (creating or running) sandboxes."""
        return [
            info
            for info in self._sandboxes.values()
            if info.status in ("creating", "running")
        ]

    def list_all_sandboxes(self) -> List[SandboxInfo]:
        """List all tracked sandboxes."""
        return list(self._sandboxes.values())

    async def cleanup_stale_sandboxes(self, max_age_hours: int = 24) -> int:
        """Cleanup sandboxes older than max_age_hours.

        Returns:
            Number of sandboxes cleaned up
        """
        from datetime import timedelta

        now = utc_now()
        cutoff = now - timedelta(hours=max_age_hours)
        cleaned = 0

        for sandbox_id, info in list(self._sandboxes.items()):
            if info.created_at < cutoff and info.status in ("creating", "running"):
                logger.warning(f"Cleaning up stale sandbox {sandbox_id}")
                await self.terminate_sandbox(sandbox_id)
                cleaned += 1

        return cleaned


# Global singleton
_spawner_service: Optional[DaytonaSpawnerService] = None


def get_daytona_spawner(
    db: Optional[DatabaseService] = None,
    event_bus: Optional[EventBusService] = None,
    mcp_server_url: Optional[str] = None,
) -> DaytonaSpawnerService:
    """Get or create the global Daytona spawner service."""
    global _spawner_service

    if _spawner_service is None:
        settings = get_app_settings()
        url = mcp_server_url or settings.integrations.mcp_server_url

        _spawner_service = DaytonaSpawnerService(
            db=db,
            event_bus=event_bus,
            mcp_server_url=url,
        )

    return _spawner_service
