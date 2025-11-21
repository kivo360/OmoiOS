"""Example: Run agent in Docker with intervention support.

This example demonstrates how to run an agent in a Docker workspace and
send intervention messages while the agent is actively working.

Key features:
- Runs conversation in background thread to allow interventions
- Provides intervention function to send messages mid-execution
- Monitors conversation state and allows real-time steering
"""

import asyncio
import os
import platform
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Optional, List, Dict, Any, AsyncIterator

from openhands.sdk import (
    Agent,
    Conversation,
    LLM,
    Tool,
    get_logger,
)
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool
from omoi_os.config import load_llm_settings
import uuid

# DockerWorkspace import is lazy - only imported when use_docker=True
# This avoids requiring OpenHands SDK root when using local workspaces

logger = get_logger(__name__)


class InterventionType(Enum):
    """Types of structured interventions."""

    PRIORITIZE = "prioritize"
    STOP = "stop"
    REFOCUS = "refocus"
    ADD_CONSTRAINT = "add_constraint"
    INJECT_TOOL_CALL = "inject_tool_call"
    CUSTOM = "custom"


@dataclass
class InterventionRecord:
    """Record of an intervention sent to the conversation."""

    intervention_id: str
    timestamp: datetime
    type: InterventionType
    message: str
    structured_data: Optional[Dict[str, Any]] = None
    acknowledged: bool = False
    acknowledgment_message: Optional[str] = None
    effectiveness_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InterventionResult:
    """Result of sending an intervention."""

    success: bool
    intervention_id: str
    message: str
    timestamp: datetime
    error: Optional[str] = None


@dataclass
class ConversationEvent:
    """Event from the conversation stream."""

    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    intervention_id: Optional[str] = None  # Link to intervention if relevant


def detect_platform() -> str:
    """Detect Docker platform (arm64 or amd64)."""
    machine = platform.machine().lower()
    if "arm" in machine or "aarch64" in machine:
        return "linux/arm64"
    return "linux/amd64"


def find_available_port(start_port: int = 8020, max_attempts: int = 100) -> int:
    """Find an available port starting from start_port."""
    for i in range(max_attempts):
        port = start_port + i
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"Could not find available port starting from {start_port}")


def build_llm() -> LLM:
    """Build LLM instance using project configuration."""
    llm_settings = load_llm_settings()

    if not llm_settings.api_key:
        raise RuntimeError(
            "LLM_API_KEY must be set in environment or config. "
            "Set LLM_API_KEY in your environment or config/base.yaml"
        )

    return LLM(
        usage_id="ticket-agent",
        model=llm_settings.model,
        base_url=llm_settings.base_url,
        api_key=llm_settings.api_key,
    )


def build_agent(llm: LLM) -> Agent:
    """Build agent with file editor and terminal tools."""
    tools = [Tool(name=TerminalTool.name), Tool(name=FileEditorTool.name)]
    return Agent(llm=llm, tools=tools)


class InterventionHandler:
    """Enhanced handler for sending interventions with event streaming and history."""

    def __init__(self, conversation: Conversation):
        """Initialize intervention handler with a conversation."""
        self.conversation = conversation
        self.conversation_id = conversation.state.id
        self.persistence_dir = conversation.state.persistence_dir
        self.intervention_history: List[InterventionRecord] = []
        self.event_queue: List[ConversationEvent] = []
        self.event_listeners: List[Callable[[ConversationEvent], None]] = []
        self._event_monitoring = False
        self._event_thread: Optional[threading.Thread] = None
        logger.info(
            f"Intervention handler ready for conversation {self.conversation_id}"
        )

    def send_intervention(
        self,
        message: str,
        prefix: str = "[INTERVENTION]",
        intervention_type: InterventionType = InterventionType.CUSTOM,
        structured_data: Optional[Dict[str, Any]] = None,
    ) -> InterventionResult:
        """
        Send intervention message to running conversation.

        This works even while the conversation is actively running - OpenHands
        will queue the message and process it asynchronously.

        Args:
            message: Intervention message to send
            prefix: Optional prefix for the message (default: "[INTERVENTION]")
            intervention_type: Type of intervention (default: CUSTOM)
            structured_data: Optional structured data for the intervention

        Returns:
            InterventionResult with success status and intervention ID
        """
        intervention_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()

        try:
            # Format message based on intervention type
            if intervention_type == InterventionType.PRIORITIZE:
                formatted_message = f"{prefix} PRIORITY: {message}"
            elif intervention_type == InterventionType.STOP:
                formatted_message = f"{prefix} STOP: {message}"
            elif intervention_type == InterventionType.REFOCUS:
                formatted_message = f"{prefix} REFOCUS: {message}"
            else:
                formatted_message = f"{prefix} {message}"

            logger.info(
                f"Sending intervention [{intervention_type.value}]: {formatted_message}"
            )
            self.conversation.send_message(formatted_message)

            # Record intervention in history
            record = InterventionRecord(
                intervention_id=intervention_id,
                timestamp=timestamp,
                type=intervention_type,
                message=message,
                structured_data=structured_data,
            )
            self.intervention_history.append(record)

            # Check if we need to trigger processing
            # Note: RemoteState may not have agent_status, so we handle gracefully
            try:
                state = self.conversation.state
                if hasattr(state, "agent_status"):
                    status = state.agent_status
                    status_str = (
                        status.value if hasattr(status, "value") else str(status)
                    )

                    if status_str.lower() == "idle":
                        thread = threading.Thread(
                            target=self.conversation.run, daemon=True
                        )
                        thread.start()
                        logger.info(
                            "Started conversation processing after intervention"
                        )
                    else:
                        logger.info(
                            f"Intervention queued (agent status: {status_str}). "
                            "Message will be processed asynchronously."
                        )
                else:
                    # RemoteState doesn't expose agent_status directly
                    # Message will be queued and processed automatically
                    logger.info(
                        "Intervention sent. Message will be processed asynchronously."
                    )
            except Exception as e:
                logger.info(
                    f"Intervention sent (could not check status: {e}). "
                    "Message will be processed asynchronously."
                )

            return InterventionResult(
                success=True,
                intervention_id=intervention_id,
                message=message,
                timestamp=timestamp,
            )
        except Exception as e:
            logger.error(f"Failed to send intervention: {e}", exc_info=True)
            return InterventionResult(
                success=False,
                intervention_id=intervention_id,
                message=message,
                timestamp=timestamp,
                error=str(e),
            )

    def send_structured_intervention(
        self,
        intervention_type: InterventionType,
        message: str,
        **kwargs: Any,
    ) -> InterventionResult:
        """
        Send a structured intervention with type-specific formatting.

        Args:
            intervention_type: Type of intervention
            message: Intervention message
            **kwargs: Additional structured data (e.g., target, urgency, reason)

        Returns:
            InterventionResult with success status
        """
        structured_data = kwargs.copy()
        return self.send_intervention(
            message=message,
            intervention_type=intervention_type,
            structured_data=structured_data,
        )

    def get_status(self) -> dict:
        """Get current conversation status."""
        state = self.conversation.state
        status = {
            "conversation_id": str(self.conversation_id),
            "execution_status": state.execution_status.value
            if hasattr(state.execution_status, "value")
            else str(state.execution_status),
            "persistence_dir": state.persistence_dir,
            "intervention_count": len(self.intervention_history),
            "event_count": len(self.event_queue),
        }
        # RemoteState may not have agent_status
        if hasattr(state, "agent_status"):
            status["agent_status"] = (
                state.agent_status.value
                if hasattr(state.agent_status, "value")
                else str(state.agent_status)
            )
        else:
            status["agent_status"] = "unknown"
        return status

    def get_intervention_history(self) -> List[InterventionRecord]:
        """Get history of all interventions sent."""
        return self.intervention_history.copy()

    def start_event_monitoring(self):
        """Start monitoring conversation events in background."""
        if self._event_monitoring:
            logger.warning("Event monitoring already started")
            return

        self._event_monitoring = True

        def monitor_events():
            """Background thread to monitor conversation events."""
            last_event_count = 0
            while self._event_monitoring:
                try:
                    state = self.conversation.state
                    # Check for new events
                    if hasattr(state, "events") and state.events:
                        current_count = len(state.events)
                        if current_count > last_event_count:
                            # New events detected
                            new_events = state.events[last_event_count:]
                            for event in new_events:
                                event_data = ConversationEvent(
                                    event_type=type(event).__name__,
                                    timestamp=datetime.utcnow(),
                                    data={"event": str(event)},
                                )
                                self.event_queue.append(event_data)
                                # Notify listeners
                                for listener in self.event_listeners:
                                    try:
                                        listener(event_data)
                                    except Exception as e:
                                        logger.error(f"Event listener error: {e}")
                            last_event_count = current_count
                except Exception as e:
                    logger.error(f"Error monitoring events: {e}")

                time.sleep(0.5)  # Poll every 500ms

        self._event_thread = threading.Thread(target=monitor_events, daemon=True)
        self._event_thread.start()
        logger.info("Started event monitoring")

    def stop_event_monitoring(self):
        """Stop monitoring conversation events."""
        self._event_monitoring = False
        if self._event_thread:
            self._event_thread.join(timeout=2)
        logger.info("Stopped event monitoring")

    def add_event_listener(self, callback: Callable[[ConversationEvent], None]):
        """Add a callback to be called when events occur."""
        self.event_listeners.append(callback)

    async def stream_events(
        self, event_types: Optional[List[str]] = None
    ) -> AsyncIterator[ConversationEvent]:
        """
        Stream conversation events asynchronously.

        Args:
            event_types: Optional list of event types to filter (e.g., ["ToolCallEvent", "MessageEvent"])

        Yields:
            ConversationEvent objects as they occur
        """
        if not self._event_monitoring:
            self.start_event_monitoring()

        last_index = 0
        while True:
            # Check for new events
            if len(self.event_queue) > last_index:
                new_events = self.event_queue[last_index:]
                for event in new_events:
                    if event_types is None or event.event_type in event_types:
                        yield event
                last_index = len(self.event_queue)

            await asyncio.sleep(0.1)  # Poll every 100ms


async def run_ticket_with_interventions(
    ticket_id: str,
    title: str,
    description: str,
    repo_url: str,
    branch: str = "main",
    use_docker: bool = False,
    local_workspace_dir: Optional[str] = None,
    host_port: int = 8020,
    intervention_callback: Optional[Callable[[InterventionHandler], None]] = None,
    wait_for_completion: bool = True,
) -> InterventionHandler:
    """
    Run ticket agent with intervention support (Docker or local workspace).

    Args:
        ticket_id: Unique identifier for the ticket
        title: Ticket title
        description: Detailed ticket description
        repo_url: Git repository URL to clone
        branch: Git branch to checkout (default: "main")
        use_docker: If True, use DockerWorkspace. If False, use local directory.
        local_workspace_dir: Local directory path (only used if use_docker=False).
                           Defaults to examples/workspaces/{ticket_id}
        host_port: Host port to expose from container (only used if use_docker=True)
        intervention_callback: Optional callback that receives InterventionHandler
                               when conversation starts
        wait_for_completion: If True, wait for conversation to complete before returning

    Returns:
        InterventionHandler instance for sending interventions
    """
    if use_docker:
        return await run_ticket_in_docker_with_interventions(
            ticket_id=ticket_id,
            title=title,
            description=description,
            repo_url=repo_url,
            branch=branch,
            host_port=host_port,
            intervention_callback=intervention_callback,
            wait_for_completion=wait_for_completion,
        )
    else:
        return await run_ticket_local_with_interventions(
            ticket_id=ticket_id,
            title=title,
            description=description,
            repo_url=repo_url,
            branch=branch,
            workspace_dir=local_workspace_dir,
            intervention_callback=intervention_callback,
            wait_for_completion=wait_for_completion,
        )


async def run_ticket_local_with_interventions(
    ticket_id: str,
    title: str,
    description: str,
    repo_url: str,
    branch: str = "main",
    workspace_dir: Optional[str] = None,
    intervention_callback: Optional[Callable[[InterventionHandler], None]] = None,
    wait_for_completion: bool = True,
) -> InterventionHandler:
    """
    Run ticket agent in local workspace with intervention support.

    Uses a local directory instead of Docker - faster for prototyping but no isolation.

    Args:
        ticket_id: Unique identifier for the ticket
        title: Ticket title
        description: Detailed ticket description
        repo_url: Git repository URL to clone
        branch: Git branch to checkout (default: "main")
        workspace_dir: Local directory path. Defaults to examples/workspaces/{ticket_id}
        intervention_callback: Optional callback that receives InterventionHandler
                               when conversation starts
        wait_for_completion: If True, wait for conversation to complete before returning

    Returns:
        InterventionHandler instance for sending interventions
    """
    from pathlib import Path
    import subprocess

    llm = build_llm()
    agent = build_agent(llm)

    # Determine workspace directory
    if workspace_dir is None:
        # Default to examples/workspaces/{ticket_id}
        examples_dir = Path(__file__).parent
        workspace_dir = str(examples_dir / "workspaces" / ticket_id)

    workspace_path = Path(workspace_dir)
    workspace_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Using local workspace: {workspace_path.absolute()}")

    # Helper function to execute shell commands locally
    def sh(cmd: str, cwd: str = str(workspace_path)):
        """Execute shell command locally and log failures."""
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.warning(
                "[LOCAL] Command failed: %s\nstdout:\n%s\nstderr:\n%s",
                cmd,
                result.stdout,
                result.stderr,
            )
        return type(
            "Result",
            (),
            {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )()

    # 1) Prepare repo in local workspace
    # Create a subdirectory within the workspace for the cloned repository
    # Extract repo name from URL for the subdirectory name
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    if not repo_name:
        repo_name = f"repo_{ticket_id}"

    repo_dir = workspace_path / repo_name
    logger.info(f"Repository will be cloned into: {repo_dir}")

    # Remove existing repo directory if it exists
    if repo_dir.exists():
        logger.info(f"Removing existing repository directory: {repo_dir}")
        sh(f"rm -rf {repo_dir}")

    # Create the repo directory
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Convert SSH URL to HTTPS if needed
    clone_url = repo_url
    if repo_url.startswith("git@github.com:"):
        clone_url = repo_url.replace("git@github.com:", "https://github.com/")
        logger.info(f"Converted SSH URL to HTTPS: {clone_url}")

    # Clone repository into the subdirectory
    logger.info(f"Cloning repository {clone_url} into {repo_dir}...")
    clone_result = sh(f"git clone {clone_url} .", cwd=str(repo_dir))
    if clone_result.exit_code != 0:
        if clone_url != repo_url:
            logger.warning("HTTPS clone failed, trying original SSH URL...")
            clone_result = sh(f"git clone {repo_url} .", cwd=str(repo_dir))

        if clone_result.exit_code != 0:
            raise RuntimeError(
                f"Failed to clone repository. "
                f"Tried: {clone_url} and {repo_url if clone_url != repo_url else 'N/A'}. "
                f"Error: {clone_result.stderr}"
            )

    # Fetch and checkout the desired branch
    logger.info(f"Fetching and checking out branch {branch}...")
    sh("git fetch origin", cwd=str(repo_dir))
    checkout_result = sh(
        f"""
        git checkout {branch} 2>/dev/null || \
        git checkout -b {branch} origin/{branch} 2>/dev/null || \
        git checkout -b {branch}
        """,
        cwd=str(repo_dir),
    )
    if checkout_result.exit_code == 0:
        sh(
            f"git pull --ff-only origin {branch} 2>/dev/null || true",
            cwd=str(repo_dir),
        )

    logger.info("Repository setup complete")

    # Create conversation with the repo directory as workspace
    logger.info(f"Creating conversation with workspace: {repo_dir.absolute()}")
    conversation = Conversation(
        agent=agent,
        workspace=str(repo_dir.absolute()),
    )

    # Create intervention handler
    intervention_handler = InterventionHandler(conversation)

    # Call intervention callback if provided
    if intervention_callback:
        intervention_callback(intervention_handler)

    goal_prompt = f"""
You are working on ticket {ticket_id}: {title}

Ticket description:
{description}

Instructions:
- Work inside this repository (the cloned repo).
- Use file editor + terminal tools to implement the change.
- Run tests before finishing.
- When done, summarize the changes and what remains risky.
"""

    conversation.send_message(goal_prompt)

    logger.info(
        f"Conversation ready. Use InterventionHandler to send messages. "
        f"Conversation ID: {intervention_handler.conversation_id}"
    )
    logger.info("Starting conversation execution...")

    # Run conversation in background thread to allow interventions
    conversation_error = [None]
    conversation_started = threading.Event()

    def run_conversation():
        """Run conversation in background thread."""
        try:
            logger.info("Starting conversation.run() in background thread...")
            conversation_started.set()
            conversation.run()
            logger.info("Conversation execution completed successfully")
        except Exception as e:
            error_msg = str(e)
            conversation_error[0] = e
            conversation_started.set()
            logger.error(
                f"Conversation execution failed: {error_msg[:200]}", exc_info=True
            )

    # Start conversation in background thread
    conversation_thread = threading.Thread(target=run_conversation, daemon=False)
    conversation_thread.start()

    # Wait for conversation to start
    conversation_started.wait(timeout=10)

    # Check if there was an immediate error
    if conversation_error[0]:
        error_msg = str(conversation_error[0])
        logger.error(
            f"Conversation failed to start: {error_msg[:200]}. "
            "The InterventionHandler is still available, but interventions may not work."
        )
        if not wait_for_completion:
            return intervention_handler
    else:
        logger.info("Conversation started successfully in background thread")

    # If wait_for_completion is False, return immediately
    if not wait_for_completion:
        logger.warning(
            "Returning handler immediately with wait_for_completion=False. "
            "Conversation will continue running in background."
        )
        return intervention_handler

    # Wait for conversation to complete
    logger.info(
        "Waiting for conversation to complete. "
        "You can send interventions using the handler while waiting..."
    )

    max_wait_seconds = 600  # 10 minutes max
    poll_interval = 1.0
    start_time = time.time()

    while conversation_thread.is_alive():
        if time.time() - start_time > max_wait_seconds:
            logger.warning(f"Conversation timeout after {max_wait_seconds} seconds")
            break
        await asyncio.sleep(poll_interval)

    # Thread finished, wait a moment for cleanup
    conversation_thread.join(timeout=5)

    # Check final status
    if conversation_error[0]:
        logger.error(f"Conversation completed with error: {conversation_error[0]}")
    else:
        logger.info("Conversation completed successfully")

    return intervention_handler


async def run_ticket_in_docker_with_interventions(
    ticket_id: str,
    title: str,
    description: str,
    repo_url: str,
    branch: str = "main",
    host_port: int = 8020,
    intervention_callback: Optional[Callable[[InterventionHandler], None]] = None,
    wait_for_completion: bool = True,
) -> InterventionHandler:
    """
    Run ticket agent in Docker workspace with intervention support.

    Spins up a DockerWorkspace, clones the repo, and runs a conversation
    in a background thread. Returns an InterventionHandler that allows
    sending messages to the running conversation.

    Args:
        ticket_id: Unique identifier for the ticket
        title: Ticket title
        description: Detailed ticket description
        repo_url: Git repository URL to clone
        branch: Git branch to checkout (default: "main")
        host_port: Host port to expose from container (default: 8020)
        intervention_callback: Optional callback that receives InterventionHandler
                               when conversation starts (allows immediate setup)

    Returns:
        InterventionHandler instance for sending interventions
    """
    # Lazy import DockerWorkspace to avoid requiring OpenHands SDK root when not using Docker
    from openhands.workspace import DockerWorkspace

    llm = build_llm()
    agent = build_agent(llm)
    platform_str = detect_platform()

    # Docker image with Python + Node used in official examples
    base_image = "nikolaik/python-nodejs:python3.12-nodejs22"

    # Find an available port if the requested one is in use
    actual_port = find_available_port(host_port)
    if actual_port != host_port:
        logger.info("Port %d is in use, using port %d instead", host_port, actual_port)
        host_port = actual_port

    logger.info(
        "Starting DockerWorkspace (image=%s, port=%d)...", base_image, host_port
    )

    with DockerWorkspace(
        base_image=base_image,
        host_port=host_port,
        platform=platform_str,
        extra_ports=False,
    ) as workspace:
        cwd = workspace.working_dir

        # Helper function to execute shell commands in container
        def sh(cmd: str):
            """Execute shell command in workspace and log failures."""
            res = workspace.execute_command(cmd, cwd=cwd)
            if res.exit_code != 0:
                logger.warning(
                    "[DOCKER] Command failed: %s\nstdout:\n%s\nstderr:\n%s",
                    cmd,
                    res.stdout,
                    res.stderr,
                )
            return res

        # 1) Prepare repo inside the container
        # Create a subdirectory within the workspace for the cloned repository
        # Extract repo name from URL for the subdirectory name
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        if not repo_name:
            repo_name = f"repo_{ticket_id}"

        repo_dir = f"{cwd}/{repo_name}"
        logger.info(f"Repository will be cloned into: {repo_dir}")

        # Remove existing repo directory if it exists
        sh(f"rm -rf {repo_dir} 2>/dev/null || true")

        # Create the repo directory
        sh(f"mkdir -p {repo_dir}")

        # Convert SSH URL to HTTPS if needed (for public repos)
        clone_url = repo_url
        if repo_url.startswith("git@github.com:"):
            # Convert git@github.com:user/repo.git to https://github.com/user/repo.git
            clone_url = repo_url.replace("git@github.com:", "https://github.com/")
            logger.info(f"Converted SSH URL to HTTPS: {clone_url}")

        # Clone repository into the subdirectory
        logger.info(f"Cloning repository {clone_url} into {repo_dir}...")
        clone_result = sh(f"git clone {clone_url} {repo_dir}")
        if clone_result.exit_code != 0:
            # If HTTPS fails and we converted from SSH, try original SSH URL
            if clone_url != repo_url:
                logger.warning("HTTPS clone failed, trying original SSH URL...")
                logger.warning("Note: SSH keys may need to be set up in the container")
                clone_result = sh(f"git clone {repo_url} {repo_dir}")

            if clone_result.exit_code != 0:
                raise RuntimeError(
                    f"Failed to clone repository. "
                    f"Tried: {clone_url} and {repo_url if clone_url != repo_url else 'N/A'}. "
                    f"Error: {clone_result.stderr}"
                )

        logger.info("Repository successfully cloned to workspace subdirectory")

        # Fetch and checkout the desired branch
        logger.info(f"Fetching and checking out branch {branch}...")
        sh(f"cd {repo_dir} && git fetch origin")
        checkout_result = sh(
            f"""
            cd {repo_dir} && \
            git checkout {branch} 2>/dev/null || \
            git checkout -b {branch} origin/{branch} 2>/dev/null || \
            git checkout -b {branch}
            """
        )
        if checkout_result.exit_code == 0:
            sh(
                f"cd {repo_dir} && git pull --ff-only origin {branch} 2>/dev/null || true"
            )

        logger.info("Repository setup complete")

        # Wait for Docker workspace agent server to be fully ready
        # The agent server needs time to start up before we can create a conversation
        logger.info("Waiting for Docker workspace agent server to be ready...")

        # Try a simple command first to ensure workspace is responsive
        test_result = sh("echo 'workspace ready'")
        if test_result.exit_code != 0:
            logger.warning("Workspace command test failed, but continuing...")

        # Give the agent server a moment to fully initialize
        await asyncio.sleep(3)

        # Create conversation with retry logic
        # DockerWorkspace creates a RemoteConversation that connects to an agent server
        # The server might not be ready immediately, so we retry with exponential backoff
        max_retries = 5
        initial_delay = 2
        conversation = None

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Creating conversation (attempt {attempt + 1}/{max_retries})..."
                )
                conversation = Conversation(
                    agent=agent,
                    workspace=workspace,
                )
                logger.info("Conversation created successfully")
                break
            except Exception as e:
                error_msg = str(e)
                # Check if it's a connection error that might be retryable
                is_retryable = any(
                    keyword in error_msg.lower()
                    for keyword in [
                        "disconnected",
                        "connection",
                        "timeout",
                        "refused",
                        "protocol",
                    ]
                )

                if attempt < max_retries - 1 and is_retryable:
                    retry_delay = initial_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"Connection error (attempt {attempt + 1}): {error_msg[:100]}. "
                        f"Retrying in {retry_delay} seconds..."
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Failed to create conversation: {e}")
                    raise

        if conversation is None:
            raise RuntimeError("Failed to create conversation after all retries")

        # Create intervention handler
        intervention_handler = InterventionHandler(conversation)

        # Call intervention callback if provided (allows immediate setup)
        if intervention_callback:
            intervention_callback(intervention_handler)

        goal_prompt = f"""
You are working on ticket {ticket_id}: {title}

Ticket description:
{description}

Instructions:
- Work inside the repository directory: {repo_dir}
- The repository has been cloned into a subdirectory within the workspace.
- Use file editor + terminal tools to implement the change.
- IMPORTANT: Do NOT start or modify the OpenHands agent server running on port 8000.
  That is container infrastructure, not part of the repository you're working on.
- If you need to test a server, use port {host_port} (exposed to host) or any port other than 8000.
- Run tests before finishing.
- When done, summarize the changes and what remains risky.
"""

        conversation.send_message(goal_prompt)

        # For RemoteConversation, we need to run in the main thread but allow interventions
        # We'll use a different approach: run the conversation with a timeout/check mechanism
        # that allows us to check for completion while still being able to send interventions

        # Store the conversation in the handler for later access
        # The conversation will be run, but we'll monitor it and allow interventions

        logger.info(
            f"Conversation ready. Use InterventionHandler to send messages. "
            f"Conversation ID: {intervention_handler.conversation_id}"
        )
        logger.info("Starting conversation execution...")

        # For RemoteConversation with DockerWorkspace, we need to be careful about
        # when we run the conversation. The server connection needs to be stable.
        # We'll run it in a background thread but wait a bit longer for the server to be ready.

        # Additional wait to ensure the agent server is fully ready
        logger.info("Waiting additional time for agent server to stabilize...")
        await asyncio.sleep(5)  # Give more time for server to be ready

        conversation_error = [None]  # Use list to allow modification in nested function
        conversation_started = threading.Event()

        def run_conversation():
            """Run conversation in background thread."""
            try:
                logger.info("Starting conversation.run() in background thread...")
                conversation_started.set()
                conversation.run()
                logger.info("Conversation execution completed successfully")
            except Exception as e:
                error_msg = str(e)
                conversation_error[0] = e
                conversation_started.set()  # Set even on error so we know it tried
                logger.error(
                    f"Conversation execution failed: {error_msg[:200]}", exc_info=True
                )
                # Check if it's a connection error
                if any(
                    keyword in error_msg.lower()
                    for keyword in ["disconnected", "connection", "timeout", "protocol"]
                ):
                    logger.warning(
                        "Connection error during execution. "
                        "This might be a transient issue. "
                        "The server may need more time to stabilize."
                    )

        # Start conversation in background thread
        conversation_thread = threading.Thread(target=run_conversation, daemon=False)
        conversation_thread.start()

        # Wait for conversation to start (or fail quickly)
        conversation_started.wait(timeout=10)

        # Check if there was an immediate error
        if conversation_error[0]:
            error_msg = str(conversation_error[0])
            logger.error(
                f"Conversation failed to start: {error_msg[:200]}. "
                "The InterventionHandler is still available, but interventions may not work."
            )
            # Don't raise - return handler anyway so user can try interventions
        else:
            logger.info("Conversation started successfully in background thread")

        # If wait_for_completion is False, return immediately (caller manages workspace lifecycle)
        # If True, we'll wait for completion before returning (workspace stays alive)
        if not wait_for_completion:
            logger.warning(
                "Returning handler immediately with wait_for_completion=False. "
                "WARNING: DockerWorkspace will close when function returns, "
                "which may terminate the conversation. Interventions may not work."
            )
            return intervention_handler

        # Wait for conversation to complete (keeps workspace alive)
        # This allows interventions to be sent while waiting
        # We'll poll the thread instead of blocking join() so we can check status
        logger.info(
            "Waiting for conversation to complete (workspace will stay alive). "
            "You can send interventions using the handler while waiting..."
        )

        # Poll thread status instead of blocking join, so we can still send interventions
        max_wait_seconds = 600  # 10 minutes max
        poll_interval = 1.0  # Check every second
        start_time = time.time()

        while conversation_thread.is_alive():
            if time.time() - start_time > max_wait_seconds:
                logger.warning(f"Conversation timeout after {max_wait_seconds} seconds")
                break
            await asyncio.sleep(poll_interval)

        # Thread finished, wait a moment for cleanup
        conversation_thread.join(timeout=5)

        # Check final status
        if conversation_error[0]:
            logger.error(f"Conversation completed with error: {conversation_error[0]}")
        else:
            logger.info("Conversation completed successfully")

        # Return handler (workspace will close when we exit the with block)
        return intervention_handler


# Example: Interactive intervention session
async def interactive_intervention_example():
    """
    Interactive example where you can send interventions via command line.

    Usage:
        # Start the conversation
        handler = await run_ticket_in_docker_with_interventions(...)

        # In another thread or async task, send interventions:
        handler.send_intervention("Please focus on testing first")
        handler.send_intervention("Make sure the endpoint returns proper JSON")
        status = handler.get_status()  # Check current status
    """
    ticket_id = "T-456"
    title = "Add /health endpoint"
    description = (
        "Add /health endpoint returning JSON {{status, version}} to the repository's "
        "application (if it has a web server). If the repo doesn't have a server yet, "
        "create a simple Flask or FastAPI app with the /health endpoint. Use port 8020 "
        "(or any port other than 8000) to avoid conflicts with the OpenHands agent server."
    )

    repo_url = os.getenv(
        "REPO_URL", "git@github.com:hesreallyhim/awesome-claude-code.git"
    )

    print("Starting conversation with intervention support...")

    def setup_interventions(handler: InterventionHandler):
        """Setup function called when conversation starts."""
        print(f"\n[Setup] Intervention handler ready: {handler.conversation_id}")
        # You could send an initial intervention here if needed
        # handler.send_intervention("Please focus on clean, testable code")

    # Use local workspace for faster prototyping (set use_docker=True for Docker)
    handler = await run_ticket_with_interventions(
        ticket_id=ticket_id,
        title=title,
        description=description,
        repo_url=repo_url,
        branch="main",
        use_docker=False,  # Set to True for Docker, False for local workspace
        intervention_callback=setup_interventions,
        wait_for_completion=True,  # Keep workspace alive so interventions work
    )

    print("\n" + "=" * 70)
    print("CONVERSATION RUNNING - ENHANCED INTERVENTION HANDLER READY")
    print("=" * 70)
    print(f"\nConversation ID: {handler.conversation_id}")
    print("\nAvailable intervention methods:")
    print("  handler.send_intervention('message')  # Basic intervention")
    print(
        "  handler.send_structured_intervention(InterventionType.PRIORITIZE, 'message')"
    )
    print("  handler.get_status()  # Check status")
    print("  handler.get_intervention_history()  # View all interventions")
    print("  handler.start_event_monitoring()  # Start event streaming")
    print("  async for event in handler.stream_events(): ...  # Stream events")
    print("\nExample interventions:")
    print("  handler.send_structured_intervention(")
    print("      InterventionType.PRIORITIZE,")
    print("      'Focus on writing tests first',")
    print("      target='test_coverage', urgency='high'")
    print("  )")
    print("  handler.send_intervention('Make sure to use port 8020')")
    print("\n" + "=" * 70 + "\n")

    # Start event monitoring
    handler.start_event_monitoring()

    # Add event listener for real-time updates
    def on_event(event: ConversationEvent):
        """Handle conversation events."""
        print(f"[EVENT] {event.event_type}: {event.data.get('event', '')[:100]}")

    handler.add_event_listener(on_event)

    # Example: Send some interventions after a delay
    async def send_delayed_interventions():
        """Example of sending interventions after some time."""
        await asyncio.sleep(10)  # Wait 10 seconds
        print("\n[Example] Sending structured intervention: PRIORITIZE tests")
        result = handler.send_structured_intervention(
            InterventionType.PRIORITIZE,
            "Please make sure tests pass",
            target="test_coverage",
            urgency="high",
        )
        print(f"  Intervention ID: {result.intervention_id}")
        print(f"  Success: {result.success}")

        await asyncio.sleep(20)  # Wait another 20 seconds
        print("\n[Example] Sending intervention: 'Focus on clean code structure'")
        handler.send_intervention("Focus on clean code structure")

    # Start intervention task
    intervention_task = asyncio.create_task(send_delayed_interventions())

    # Monitor conversation
    max_wait_time = 300
    start_time = time.time()
    check_interval = 5

    while True:
        status = handler.get_status()
        execution_status = status["execution_status"]
        agent_status = status["agent_status"]

        elapsed = int(time.time() - start_time)
        print(
            f"[{elapsed:3d}s] Execution: {execution_status:12s} | Agent: {agent_status:12s}"
        )

        if execution_status in ["finished", "failed", "cancelled"]:
            break

        if time.time() - start_time > max_wait_time:
            logger.warning("Conversation timeout reached")
            break

        await asyncio.sleep(check_interval)

    # Cancel intervention task if still running
    if not intervention_task.done():
        intervention_task.cancel()

    # Get final state
    state = handler.conversation.state
    execution_status = state.execution_status

    last_text = ""
    try:
        if hasattr(state, "messages") and state.messages:
            last_msg = state.messages[-1]
            last_text = getattr(last_msg, "content", "")
        elif hasattr(state, "events") and state.events:
            from openhands.sdk.event import MessageEvent

            for event in reversed(state.events):
                if isinstance(event, MessageEvent):
                    msg = event.to_llm_message()
                    if msg.role == "assistant":
                        last_text = msg.content
                        break
        if not last_text:
            last_text = "Execution completed. Check conversation logs for details."
    except Exception as e:
        logger.warning(f"Could not retrieve final message: {e}")
        last_text = "Execution completed. Check conversation logs for details."

    print(f"\n=== Ticket {ticket_id} finished ===")
    print(f"Execution status: {execution_status}")
    print("\n--- Final assistant message ---\n")
    print(last_text)

    # Stop event monitoring
    handler.stop_event_monitoring()

    # Show intervention history
    print("\n" + "=" * 70)
    print("INTERVENTION HISTORY")
    print("=" * 70)
    history = handler.get_intervention_history()
    if history:
        for record in history:
            print(f"\n[{record.timestamp}] {record.type.value.upper()}")
            print(f"  Message: {record.message}")
            if record.structured_data:
                print(f"  Data: {record.structured_data}")
            print(f"  Acknowledged: {record.acknowledged}")
    else:
        print("No interventions were sent.")
    print("=" * 70)


if __name__ == "__main__":
    # Run interactive example
    asyncio.run(interactive_intervention_example())
