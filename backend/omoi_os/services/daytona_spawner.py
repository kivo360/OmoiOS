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

        # Anthropic / Z.AI API Configuration
        # Supports per-user credentials with fallback to global config
        from omoi_os.services.credentials import CredentialsService

        # Get user_id from extra_env if provided
        user_id = None
        if extra_env and extra_env.get("USER_ID"):
            try:
                from uuid import UUID

                user_id = UUID(extra_env["USER_ID"])
            except (ValueError, TypeError):
                pass

        # Get credentials (user-specific or global fallback)
        cred_service = CredentialsService(self.db) if self.db else None
        if cred_service:
            creds = cred_service.get_anthropic_credentials(user_id=user_id)
        else:
            # No DB available, use config directly
            from omoi_os.config import load_anthropic_settings

            settings = load_anthropic_settings()
            from omoi_os.services.credentials import AnthropicCredentials

            creds = AnthropicCredentials(
                api_key=settings.get_api_key() or "",
                base_url=settings.base_url,
                model=settings.model,
                default_model=settings.default_model,
                default_haiku_model=settings.default_haiku_model,
                default_sonnet_model=settings.default_sonnet_model,
                default_opus_model=settings.default_opus_model,
                source="config",
            )

        if creds.api_key:
            env_vars["ANTHROPIC_API_KEY"] = creds.api_key
        if creds.base_url:
            env_vars["ANTHROPIC_BASE_URL"] = creds.base_url
        if creds.model:
            env_vars["ANTHROPIC_MODEL"] = creds.model
        # Model aliases for Claude SDK compatibility
        if creds.default_model:
            env_vars["ANTHROPIC_DEFAULT_MODEL"] = creds.default_model
        if creds.default_haiku_model:
            env_vars["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = creds.default_haiku_model
        if creds.default_sonnet_model:
            env_vars["ANTHROPIC_DEFAULT_SONNET_MODEL"] = creds.default_sonnet_model
        if creds.default_opus_model:
            env_vars["ANTHROPIC_DEFAULT_OPUS_MODEL"] = creds.default_opus_model

        logger.debug(f"Using {creds.source} credentials for sandbox")

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

        # Also write env vars to a file for persistence and debugging
        env_file_content = "\n".join([f'{k}="{v}"' for k, v in env_vars.items()])
        sandbox.process.exec(
            f"cat > /tmp/.sandbox_env << 'ENVEOF'\n{env_file_content}\nENVOF"
        )
        # Export to current shell profile for all future commands
        sandbox.process.exec(f"cat >> /root/.bashrc << 'ENVEOF'\n{env_exports}\nENVOF")

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

        Phase 3 Updates:
        - Uses /api/v1/sandboxes/{id}/events for event callbacks
        - Polls /api/v1/sandboxes/{id}/messages for message injection
        - Enhanced callback checks for pending messages
        - Handles interrupt messages to stop execution

        Phase 3.5 Updates:
        - Clones GitHub repository on startup if credentials provided
        - Checks out feature branch if BRANCH_NAME specified
        - Configures git user for commits
        """
        return '''#!/usr/bin/env python3
"""Standalone sandbox worker - runs OpenHands agent for a task.

SDK Reference: https://github.com/OpenHands/software-agent-sdk
Local Docs: docs/libraries/software-agent-sdk-clean.md

Phase 3: HTTP Callbacks and Message Injection
- Reports events via POST /api/v1/sandboxes/{sandbox_id}/events
- Polls GET /api/v1/sandboxes/{sandbox_id}/messages for injected messages
- Event callback checks for pending messages

Phase 3.5: GitHub Clone Integration
- Clones repository on startup if GITHUB_TOKEN provided
- Checks out feature branch if BRANCH_NAME specified
"""

import asyncio
import os
import logging
import subprocess
import httpx
from typing import List, Optional

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
SANDBOX_ID = os.environ.get("SANDBOX_ID", "")
# Base URL without /mcp suffix for API calls
BASE_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:18000").replace("/mcp", "").rstrip("/")
LLM_MODEL = os.environ.get("LLM_MODEL", "anthropic/claude-sonnet-4-20250514")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")

# GitHub configuration (Phase 3.5)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")  # format: owner/repo
BRANCH_NAME = os.environ.get("BRANCH_NAME")

# Phase 5: Additional environment variables for branch workflow
TICKET_ID = os.environ.get("TICKET_ID")  # For GitFlow branch naming
TICKET_TITLE = os.environ.get("TICKET_TITLE", "")
TICKET_TYPE = os.environ.get("TICKET_TYPE", "feature")
USER_ID = os.environ.get("USER_ID", "")

# Global state for message injection
_should_stop: bool = False
_conversation: Optional[Conversation] = None


# ============================================================================
# GITHUB CLONE SETUP (Phase 3.5 + Phase 5 Integration)
# ============================================================================

async def create_branch_via_api():
    """Call BranchWorkflowService API to create properly named branch.
    
    Phase 5: Uses BranchWorkflowService for GitFlow-compliant branch naming.
    Returns the branch name if successful, None otherwise.
    """
    if not GITHUB_REPO or not TICKET_ID or not USER_ID:
        logger.info("Missing GITHUB_REPO, TICKET_ID, or USER_ID - skipping API branch creation")
        return None
    
    # Parse owner/repo
    parts = GITHUB_REPO.split("/")
    if len(parts) != 2:
        logger.error(f"Invalid GITHUB_REPO format: {GITHUB_REPO}")
        return None
    owner, repo = parts
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{BASE_URL}/api/v1/branch-workflow/start",
                json={
                    "ticket_id": TICKET_ID,
                    "ticket_title": TICKET_TITLE or f"Task {TICKET_ID}",
                    "repo_owner": owner,
                    "repo_name": repo,
                    "user_id": USER_ID,
                    "ticket_type": TICKET_TYPE,
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    branch_name = data.get("branch_name")
                    logger.info(f"Branch created via API: {branch_name}")
                    return branch_name
                else:
                    logger.warning(f"Branch creation failed: {data.get('error')}")
            else:
                logger.warning(f"Branch API returned {resp.status_code}")
    except Exception as e:
        logger.warning(f"Failed to create branch via API: {e}")
    
    return None


def clone_repo(branch_name: str | None = None):
    """Clone GitHub repo and checkout branch. Called on startup.
    
    Phase 3.5: Clones repository if GITHUB_TOKEN and GITHUB_REPO are set.
    Phase 5: Uses branch_name from BranchWorkflowService if provided,
             otherwise falls back to BRANCH_NAME env var.
    """
    if not GITHUB_TOKEN or not GITHUB_REPO:
        logger.info("No GitHub credentials, skipping repo clone")
        return False
    
    # Use provided branch_name or fall back to env var
    target_branch = branch_name or BRANCH_NAME
    
    # Configure git user for commits
    subprocess.run(["git", "config", "--global", "user.email", "agent@omoios.ai"], check=False)
    subprocess.run(["git", "config", "--global", "user.name", "OmoiOS Agent"], check=False)
    
    # Build authenticated clone URL
    clone_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
    
    logger.info(f"Cloning {GITHUB_REPO}...")
    result = subprocess.run(
        ["git", "clone", clone_url, "/workspace"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        logger.error(f"Clone failed: {result.stderr}")
        return False
    
    os.chdir("/workspace")
    
    # Checkout branch if specified
    if target_branch:
        logger.info(f"Checking out branch: {target_branch}")
        # Try to checkout existing branch (created via API)
        result = subprocess.run(
            ["git", "checkout", target_branch],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            # Branch doesn't exist remotely, create it locally
            logger.info(f"Creating new branch locally: {target_branch}")
            subprocess.run(["git", "checkout", "-b", target_branch], check=False)
    
    logger.info("Repository ready at /workspace")
    return True


async def setup_github_workspace():
    """Setup GitHub workspace with proper branch naming.
    
    Phase 5 Integration: 
    1. Calls BranchWorkflowService API to create properly named branch
    2. Clones repo and checks out the branch
    """
    # Try to create branch via API (Phase 5)
    branch_name = await create_branch_via_api()
    
    # Clone repo (will use API branch name or fall back to BRANCH_NAME env var)
    return clone_repo(branch_name)


# ============================================================================
# HTTP CALLBACK FUNCTIONS (Phase 3)
# ============================================================================

async def fetch_task():
    """Fetch task details from orchestrator."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{BASE_URL}/api/v1/tasks/{TASK_ID}")
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch task: {e}")
    return None


async def report_event(event_type: str, event_data: dict, source: str = "agent"):
    """Report an agent event via sandbox callback endpoint.
    
    Phase 3: Uses POST /api/v1/sandboxes/{sandbox_id}/events
    """
    if not SANDBOX_ID:
        logger.debug("No SANDBOX_ID, skipping event report")
        return
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{BASE_URL}/api/v1/sandboxes/{SANDBOX_ID}/events",
                json={
                    "event_type": event_type,
                    "event_data": {
                        **event_data,
                        "task_id": TASK_ID,
                        "agent_id": AGENT_ID,
                    },
                    "source": source,
                },
            )
    except Exception as e:
        logger.debug(f"Failed to report event: {e}")


async def poll_messages() -> List[dict]:
    """Poll for pending messages from the message queue.
    
    Phase 3: Uses GET /api/v1/sandboxes/{sandbox_id}/messages
    Messages are consumed (cleared) after retrieval.
    """
    if not SANDBOX_ID:
        return []
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{BASE_URL}/api/v1/sandboxes/{SANDBOX_ID}/messages")
            if resp.status_code == 200:
                messages = resp.json()
                if messages:
                    logger.info(f"Received {len(messages)} injected message(s)")
                return messages
    except Exception as e:
        logger.debug(f"Failed to poll messages: {e}")
    return []


def process_messages(messages: List[dict]) -> Optional[str]:
    """Process injected messages and return context to inject.
    
    Handles message types:
    - user_message: Guidance from user
    - guardian_nudge: Suggestion from Guardian
    - interrupt: Stop current work immediately
    - system: System notification
    """
    global _should_stop
    
    context_parts = []
    
    for msg in messages:
        msg_type = msg.get("message_type", "user_message")
        content = msg.get("content", "")
        
        if msg_type == "interrupt":
            logger.warning(f"INTERRUPT received: {content}")
            _should_stop = True
            return f"INTERRUPT: {content}. Stop current work immediately."
        
        elif msg_type == "guardian_nudge":
            context_parts.append(f"Guardian suggests: {content}")
        
        elif msg_type == "user_message":
            context_parts.append(f"User message: {content}")
        
        elif msg_type == "system":
            context_parts.append(f"System: {content}")
    
    if context_parts:
        return "\\n".join(context_parts)
    return None


async def register_conversation(conversation_id: str):
    """Register conversation ID with server for Guardian observation."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{BASE_URL}/api/v1/tasks/{TASK_ID}/register-conversation",
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
                f"{BASE_URL}/api/v1/tasks/{TASK_ID}",
                json={"status": status, "result": result},
            )
    except Exception as e:
        logger.warning(f"Failed to update task status: {e}")


# ============================================================================
# AGENT EXECUTION WITH MESSAGE INJECTION
# ============================================================================

def create_event_callback():
    """Create event callback with message injection support."""
    global _should_stop, _conversation
    
    async def check_and_report(event):
        """Event callback that checks for messages and reports events."""
        global _should_stop
        
        # Report the event
        event_type = type(event).__name__
        event_data = {"message": str(event)[:300]}
        await report_event(f"agent.{event_type}", event_data)
        
        # Check for pending messages (message injection)
        messages = await poll_messages()
        if messages:
            injected_context = process_messages(messages)
            
            if _should_stop:
                # Interrupt received - this will be handled in main loop
                await report_event("agent.interrupted", {"reason": "interrupt_message"})
                logger.warning("Interrupt flag set - agent should stop")
            
            elif injected_context and _conversation:
                # Inject the message into the conversation
                await report_event("agent.message_injected", {"message_count": len(messages)})
                # Send injected context as a new message
                _conversation.send_message(f"[INJECTED GUIDANCE]\\n{injected_context}")
    
    def sync_callback(event):
        """Synchronous wrapper for async callback."""
        asyncio.create_task(check_and_report(event))
    
    return sync_callback


async def main():
    global _conversation, _should_stop

    logger.info(f"OpenHands Worker starting for task {TASK_ID}")
    logger.info(f"Sandbox ID: {SANDBOX_ID}")
    logger.info(f"Backend URL: {BASE_URL}")
    
    if not TASK_ID or not AGENT_ID:
        logger.error("TASK_ID and AGENT_ID required")
        return
    
    if not LLM_API_KEY:
        logger.error("LLM_API_KEY required")
        await update_task_status("failed", "Missing LLM_API_KEY")
        return
    
    # Phase 3.5 + Phase 5: Setup GitHub workspace with proper branch naming
    await setup_github_workspace()

    # Fetch task
    task = await fetch_task()
    if not task:
        logger.error(f"Could not fetch task {TASK_ID}")
        await update_task_status("failed", "Could not fetch task")
        return
    
    task_desc = task.get("description", "No description")
    logger.info(f"Task: {task_desc}")
    
    await update_task_status("in_progress")
    await report_event("agent.started", {"task": task_desc[:200]})
    
    # Create LLM instance
    llm = LLM(
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
    )
    
    # Create agent with LLM and tools
    agent = Agent(
        llm=llm,
        tools=[
            Tool(name=TerminalTool.name),
            Tool(name=FileEditorTool.name),
            Tool(name=TaskTrackerTool.name),
        ],
    )
    
    # Create conversation with message injection callback
    _conversation = Conversation(
        agent=agent,
        workspace="/workspace",
        callbacks=[create_event_callback()],
    )
    
    # Register with server for Guardian observation
    await register_conversation(str(_conversation.state.id))
    
    # Send task and run
    logger.info("Sending task to agent...")
    _conversation.send_message(task_desc)
    
    try:
        _conversation.run()
        
        if _should_stop:
            logger.warning("Agent stopped due to interrupt")
            await update_task_status("completed", "Stopped by interrupt")
            await report_event("agent.completed", {"success": True, "interrupted": True})
        else:
            logger.info("Agent completed successfully")
            await update_task_status("completed", "Task completed successfully")
            await report_event("agent.completed", {"success": True})
            
    except Exception as e:
        logger.error(f"Agent failed: {e}")
        await update_task_status("failed", str(e))
        await report_event("agent.failed", {"error": str(e)})


if __name__ == "__main__":
    asyncio.run(main())
'''

    def _get_claude_worker_script(self) -> str:
        """Get the Claude Agent SDK worker script content.

        SDK Reference: docs/libraries/claude-agent-sdk-python-clean.md
        GitHub: https://github.com/anthropics/claude-agent-sdk-python

        Phase 3 Updates:
        - Uses /api/v1/sandboxes/{id}/events for event callbacks
        - Polls /api/v1/sandboxes/{id}/messages for message injection
        - PreToolUse hook for sub-second intervention delivery
        - Handles interrupt messages to stop execution

        Phase 3.5 Updates:
        - Clones GitHub repository on startup if credentials provided
        - Checks out feature branch if BRANCH_NAME specified
        - Configures git user for commits
        """
        return '''#!/usr/bin/env python3
"""Standalone sandbox worker - runs Claude Agent SDK for a task.

SDK Reference: https://github.com/anthropics/claude-agent-sdk-python
Local Docs: docs/libraries/claude-agent-sdk-python-clean.md

Phase 3: HTTP Callbacks and Message Injection
- Reports events via POST /api/v1/sandboxes/{sandbox_id}/events
- Polls GET /api/v1/sandboxes/{sandbox_id}/messages for injected messages
- PreToolUse hook checks for pending messages (sub-second intervention)

Phase 3.5: GitHub Clone Integration
- Clones repository on startup if GITHUB_TOKEN provided
- Checks out feature branch if BRANCH_NAME specified
"""

import asyncio
import os
import logging
import subprocess
from pathlib import Path
from typing import Any, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
TASK_ID = os.environ.get("TASK_ID")
AGENT_ID = os.environ.get("AGENT_ID")
SANDBOX_ID = os.environ.get("SANDBOX_ID", "")
# Base URL without /mcp suffix for API calls
BASE_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:18000").replace("/mcp", "").rstrip("/")

# Anthropic / Z.AI API configuration
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", os.environ.get("LLM_API_KEY", ""))
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "")  # Custom API endpoint (e.g., Z.AI)
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL", "claude-sonnet-4-20250514"))

# GitHub configuration (Phase 3.5)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")  # format: owner/repo
BRANCH_NAME = os.environ.get("BRANCH_NAME")

# Phase 5: Additional environment variables for branch workflow
TICKET_ID = os.environ.get("TICKET_ID")  # For GitFlow branch naming
TICKET_TITLE = os.environ.get("TICKET_TITLE", "")
TICKET_TYPE = os.environ.get("TICKET_TYPE", "feature")
USER_ID = os.environ.get("USER_ID", "")

# Global state for message injection
_pending_messages: List[dict] = []
_should_stop: bool = False


# ============================================================================
# GITHUB CLONE SETUP (Phase 3.5 + Phase 5 Integration)
# ============================================================================

async def create_branch_via_api():
    """Call BranchWorkflowService API to create properly named branch.
    
    Phase 5: Uses BranchWorkflowService for GitFlow-compliant branch naming.
    Returns the branch name if successful, None otherwise.
    """
    import httpx
    
    if not GITHUB_REPO or not TICKET_ID or not USER_ID:
        logger.info("Missing GITHUB_REPO, TICKET_ID, or USER_ID - skipping API branch creation")
        return None
    
    # Parse owner/repo
    parts = GITHUB_REPO.split("/")
    if len(parts) != 2:
        logger.error(f"Invalid GITHUB_REPO format: {GITHUB_REPO}")
        return None
    owner, repo = parts
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{BASE_URL}/api/v1/branch-workflow/start",
                json={
                    "ticket_id": TICKET_ID,
                    "ticket_title": TICKET_TITLE or f"Task {TICKET_ID}",
                    "repo_owner": owner,
                    "repo_name": repo,
                    "user_id": USER_ID,
                    "ticket_type": TICKET_TYPE,
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    branch_name = data.get("branch_name")
                    logger.info(f"Branch created via API: {branch_name}")
                    return branch_name
                else:
                    logger.warning(f"Branch creation failed: {data.get('error')}")
            else:
                logger.warning(f"Branch API returned {resp.status_code}")
    except Exception as e:
        logger.warning(f"Failed to create branch via API: {e}")
    
    return None


def clone_repo(branch_name: str | None = None):
    """Clone GitHub repo and checkout branch. Called on startup.
    
    Phase 3.5: Clones repository if GITHUB_TOKEN and GITHUB_REPO are set.
    Phase 5: Uses branch_name from BranchWorkflowService if provided,
             otherwise falls back to BRANCH_NAME env var.
    """
    if not GITHUB_TOKEN or not GITHUB_REPO:
        logger.info("No GitHub credentials, skipping repo clone")
        return False
    
    # Use provided branch_name or fall back to env var
    target_branch = branch_name or BRANCH_NAME
    
    # Configure git user for commits
    subprocess.run(["git", "config", "--global", "user.email", "agent@omoios.ai"], check=False)
    subprocess.run(["git", "config", "--global", "user.name", "OmoiOS Agent"], check=False)
    
    # Build authenticated clone URL
    clone_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
    
    logger.info(f"Cloning {GITHUB_REPO}...")
    result = subprocess.run(
        ["git", "clone", clone_url, "/workspace"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        logger.error(f"Clone failed: {result.stderr}")
        return False
    
    os.chdir("/workspace")
    
    # Checkout branch if specified
    if target_branch:
        logger.info(f"Checking out branch: {target_branch}")
        # Try to checkout existing branch (created via API)
        result = subprocess.run(
            ["git", "checkout", target_branch],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            # Branch doesn't exist remotely, create it locally
            logger.info(f"Creating new branch locally: {target_branch}")
            subprocess.run(["git", "checkout", "-b", target_branch], check=False)
    
    logger.info("Repository ready at /workspace")
    return True


async def setup_github_workspace():
    """Setup GitHub workspace with proper branch naming.
    
    Phase 5 Integration: 
    1. Calls BranchWorkflowService API to create properly named branch
    2. Clones repo and checks out the branch
    """
    # Try to create branch via API (Phase 5)
    branch_name = await create_branch_via_api()
    
    # Clone repo (will use API branch name or fall back to BRANCH_NAME env var)
    return clone_repo(branch_name)


# ============================================================================
# HTTP CALLBACK FUNCTIONS (Phase 3)
# ============================================================================

async def fetch_task():
    """Fetch task details from orchestrator."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{BASE_URL}/api/v1/tasks/{TASK_ID}")
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
                f"{BASE_URL}/api/v1/tasks/{TASK_ID}",
                json={"status": status, "result": result},
            )
    except Exception as e:
        logger.debug(f"Failed to report status: {e}")


async def report_event(event_type: str, event_data: dict, source: str = "agent"):
    """Report an agent event via sandbox callback endpoint.
    
    Phase 3: Uses POST /api/v1/sandboxes/{sandbox_id}/events
    """
    import httpx
    if not SANDBOX_ID:
        logger.debug("No SANDBOX_ID, skipping event report")
        return
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{BASE_URL}/api/v1/sandboxes/{SANDBOX_ID}/events",
                json={
                    "event_type": event_type,
                    "event_data": {
                        **event_data,
                        "task_id": TASK_ID,
                        "agent_id": AGENT_ID,
                    },
                    "source": source,
                },
            )
    except Exception as e:
        logger.debug(f"Failed to report event: {e}")


async def poll_messages() -> List[dict]:
    """Poll for pending messages from the message queue.
    
    Phase 3: Uses GET /api/v1/sandboxes/{sandbox_id}/messages
    Messages are consumed (cleared) after retrieval.
    
    Returns:
        List of message dicts with content, message_type, timestamp
    """
    import httpx
    if not SANDBOX_ID:
        return []
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{BASE_URL}/api/v1/sandboxes/{SANDBOX_ID}/messages")
            if resp.status_code == 200:
                messages = resp.json()
                if messages:
                    logger.info(f"Received {len(messages)} injected message(s)")
                return messages
    except Exception as e:
        logger.debug(f"Failed to poll messages: {e}")
    return []


def process_messages(messages: List[dict]) -> Optional[str]:
    """Process injected messages and return context to inject.
    
    Handles message types:
    - user_message: Guidance from user
    - guardian_nudge: Suggestion from Guardian
    - interrupt: Stop current work immediately
    - system: System notification
    
    Returns:
        Context string to inject, or None
    """
    global _should_stop
    
    context_parts = []
    
    for msg in messages:
        msg_type = msg.get("message_type", "user_message")
        content = msg.get("content", "")
        
        if msg_type == "interrupt":
            logger.warning(f"INTERRUPT received: {content}")
            _should_stop = True
            return f"⚠️ INTERRUPT: {content}. Stop current work immediately."
        
        elif msg_type == "guardian_nudge":
            context_parts.append(f"💡 Guardian suggests: {content}")
        
        elif msg_type == "user_message":
            context_parts.append(f"📝 User message: {content}")
        
        elif msg_type == "system":
            context_parts.append(f"🔔 System: {content}")
    
    if context_parts:
        return "\\n".join(context_parts)
    return None


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

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
            asyncio.create_task(report_event("agent.file_written", {"path": str(file_path)}))
            return {"content": [{"type": "text", "text": f"Wrote to {file_path}"}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {e}"}], "is_error": True}
    
    @tool("run_command", "Execute a shell command", {"command": str})
    async def run_command(args: dict[str, Any]) -> dict[str, Any]:
        command = args["command"]
        try:
            asyncio.create_task(report_event("agent.command_started", {"command": command}))
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300, cwd="/workspace")
            asyncio.create_task(report_event("agent.command_completed", {"command": command, "exit_code": result.returncode}))
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


# ============================================================================
# AGENT EXECUTION WITH HOOKS (Phase 3)
# ============================================================================

async def run_agent(task_description: str):
    """Run the Claude Agent SDK with message injection hooks."""
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, HookMatcher
    
    tools_server, tool_names = create_tools()
    
    # PreToolUse hook: Check for pending messages before each tool call
    # This provides sub-second intervention latency
    async def check_pending_messages(input_data, tool_use_id, context):
        """PreToolUse hook for immediate message injection."""
        global _should_stop
        
        # Poll for any pending messages
        messages = await poll_messages()
        
        if messages:
            injected_context = process_messages(messages)
            
            if _should_stop:
                # Interrupt received - stop execution
                await report_event("agent.interrupted", {"reason": "interrupt_message"})
                return {
                    "continue_": False,
                    "stopReason": "Interrupt received from user/guardian",
                    "systemMessage": injected_context,
                }
            
            if injected_context:
                # Inject context as system message
                await report_event("agent.message_injected", {"message_count": len(messages)})
                return {
                    "continue_": True,
                    "systemMessage": injected_context,
                    "reason": "Injected guidance from message queue",
                }
        
        return {"continue_": True}
    
    # PostToolUse hook: Report tool usage for Guardian observation
    async def track_tool_use(input_data, tool_use_id, context):
        """PostToolUse hook for event reporting."""
        tool_name = input_data.get("tool_name", "unknown")
        await report_event("agent.tool_use", {"tool": tool_name})
        return {}
    
    options = ClaudeAgentOptions(
        allowed_tools=tool_names + ["Read", "Write", "Bash", "Edit", "Glob", "Grep"],
        permission_mode="acceptEdits",
        system_prompt=f"You are an AI coding agent. Your workspace is /workspace. Be thorough and test your changes. If you receive guidance messages, incorporate them into your work.",
        cwd=Path("/workspace"),
        max_turns=50,
        max_budget_usd=10.0,
        model=ANTHROPIC_MODEL,  # Use configured model (e.g., glm-4.6v via Z.AI)
        mcp_servers={"workspace": tools_server},
        hooks={
            "PreToolUse": [HookMatcher(matcher=None, hooks=[check_pending_messages])],
            "PostToolUse": [HookMatcher(matcher=None, hooks=[track_tool_use])],
        },
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
    logger.info(f"Sandbox ID: {SANDBOX_ID}")
    logger.info(f"Backend URL: {BASE_URL}")
    logger.info(f"Anthropic Base URL: {ANTHROPIC_BASE_URL or 'default'}")
    logger.info(f"Model: {ANTHROPIC_MODEL}")
    
    if not TASK_ID or not AGENT_ID:
        logger.error("TASK_ID and AGENT_ID required")
        return
    
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY required")
        await report_status("failed", "Missing ANTHROPIC_API_KEY")
        return
    
    # Phase 3.5 + Phase 5: Setup GitHub workspace with proper branch naming
    await setup_github_workspace()

    # Set Anthropic/Z.AI environment variables
    os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
    if ANTHROPIC_BASE_URL:
        os.environ["ANTHROPIC_BASE_URL"] = ANTHROPIC_BASE_URL
        logger.info(f"Using custom Anthropic API: {ANTHROPIC_BASE_URL}")
    logger.info(f"Using model: {ANTHROPIC_MODEL}")
    
    task = await fetch_task()
    if not task:
        await report_status("failed", "Could not fetch task")
        return
    
    task_desc = task.get("description", "No description")
    logger.info(f"Task: {task_desc}")
    
    await report_status("in_progress")
    await report_event("agent.started", {"task": task_desc[:200]})
    
    success, result = await run_agent(task_desc)
    
    if success:
        await report_status("completed", result)
        await report_event("agent.completed", {"success": True})
    else:
        await report_status("failed", result)
        await report_event("agent.failed", {"error": result})


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


# ============================================================================
# WORKER SCRIPT EXPORTS (for testing and inspection)
# ============================================================================

# These module-level constants allow tests to verify worker script contents.
# They are created once by instantiating a minimal service instance.


def _create_worker_script_exports():
    """Create worker script exports without full service initialization."""
    # Create minimal instance just to access script methods
    service = DaytonaSpawnerService.__new__(DaytonaSpawnerService)
    return (
        service._get_worker_script(),
        service._get_claude_worker_script(),
    )


# Export worker scripts as module-level constants
# These contain the full worker script content including guardian_nudge handling
OPENHANDS_WORKER_SCRIPT, CLAUDE_WORKER_SCRIPT = _create_worker_script_exports()
