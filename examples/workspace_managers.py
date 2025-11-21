"""Workspace management classes using OOP principles to reduce duplication."""

import asyncio
import os
import platform
import re
import socket
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from openhands.sdk import Agent, Conversation, LLM, Tool, get_logger
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool

from omoi_os.config import load_llm_settings

logger = get_logger(__name__)


@dataclass
class CommandResult:
    """Result of executing a shell command."""

    exit_code: int
    stdout: str
    stderr: str


class CommandExecutor(ABC):
    """Abstract base class for executing shell commands in different environments."""

    @abstractmethod
    def execute(self, cmd: str, cwd: Optional[str] = None) -> CommandResult:
        """Execute a shell command and return the result."""
        pass

    def sh(self, cmd: str, cwd: Optional[str] = None) -> CommandResult:
        """Execute shell command and log failures."""
        result = self.execute(cmd, cwd)
        if result.exit_code != 0:
            logger.warning(
                f"[{self.__class__.__name__}] Command failed: {cmd}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result


class LocalCommandExecutor(CommandExecutor):
    """Execute commands in local filesystem."""

    def execute(self, cmd: str, cwd: Optional[str] = None) -> CommandResult:
        """Execute shell command locally."""
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        return CommandResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )


class DockerCommandExecutor(CommandExecutor):
    """Execute commands in Docker workspace."""

    def __init__(self, workspace):
        """Initialize with Docker workspace."""
        self.workspace = workspace
        self.cwd = workspace.working_dir

    def execute(self, cmd: str, cwd: Optional[str] = None) -> CommandResult:
        """Execute shell command in Docker container."""
        exec_cwd = cwd or self.cwd
        res = self.workspace.execute_command(cmd, cwd=exec_cwd)
        return CommandResult(
            exit_code=res.exit_code,
            stdout=res.stdout,
            stderr=res.stderr,
        )


class RepositoryManager:
    """Manages Git repository operations."""

    def __init__(self, executor: CommandExecutor, workspace_path: Path):
        """Initialize with command executor and workspace path."""
        self.executor = executor
        self.workspace_path = workspace_path

    def extract_repo_name(self, repo_url: str, ticket_id: str) -> str:
        """Extract repository name from URL."""
        repo_name_match = re.search(r"/([^/]+?)(?:\.git)?$", repo_url)
        repo_name = repo_name_match.group(1) if repo_name_match else f"repo_{ticket_id}"
        return repo_name

    def normalize_url(self, repo_url: str) -> tuple[str, str]:
        """Convert SSH URL to HTTPS if needed, return (clone_url, original_url)."""
        clone_url = repo_url
        if repo_url.startswith("git@github.com:"):
            clone_url = repo_url.replace("git@github.com:", "https://github.com/")
            logger.info(f"Converted SSH URL to HTTPS: {clone_url}")
        return clone_url, repo_url

    def clone_repository(
        self, repo_url: str, repo_dir: Path, ticket_id: str
    ) -> None:
        """Clone repository into specified directory."""
        clone_url, original_url = self.normalize_url(repo_url)

        logger.info(f"Cloning repository {clone_url} into {repo_dir}...")
        clone_result = self.executor.sh(
            f"git clone {clone_url} .", cwd=str(repo_dir)
        )

        if clone_result.exit_code != 0:
            if clone_url != original_url:
                logger.warning("HTTPS clone failed, trying original SSH URL...")
                clone_result = self.executor.sh(
                    f"git clone {original_url} .", cwd=str(repo_dir)
                )

            if clone_result.exit_code != 0:
                raise RuntimeError(
                    f"Failed to clone repository. "
                    f"Tried: {clone_url} and {original_url if clone_url != original_url else 'N/A'}. "
                    f"Error: {clone_result.stderr}"
                )

    def checkout_branch(self, repo_dir: Path, branch: str) -> None:
        """Fetch and checkout the specified branch."""
        logger.info(f"Fetching and checking out branch {branch}...")
        self.executor.sh("git fetch origin", cwd=str(repo_dir))

        checkout_result = self.executor.sh(
            f"""
            git checkout {branch} 2>/dev/null || \
            git checkout -b {branch} origin/{branch} 2>/dev/null || \
            git checkout -b {branch}
            """,
            cwd=str(repo_dir),
        )

        if checkout_result.exit_code == 0:
            self.executor.sh(
                f"git pull --ff-only origin {branch} 2>/dev/null || true",
                cwd=str(repo_dir),
            )

    def setup_repository(
        self, repo_url: str, branch: str, ticket_id: str, repo_dir: Path
    ) -> None:
        """Complete repository setup: clone and checkout branch."""
        # Remove existing repo directory if it exists
        if isinstance(repo_dir, Path) and repo_dir.exists():
            logger.info(f"Removing existing repository directory: {repo_dir}")
            self.executor.sh(f"rm -rf {repo_dir}")

        # Create the repo directory
        if isinstance(repo_dir, Path):
            repo_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.executor.sh(f"mkdir -p {repo_dir}")

        # Clone repository
        self.clone_repository(repo_url, repo_dir, ticket_id)

        # Checkout branch
        self.checkout_branch(repo_dir, branch)

        logger.info("Repository setup complete")


class WorkspaceManager(ABC):
    """Abstract base class for workspace management."""

    def __init__(self, ticket_id: str, workspace_path: Path):
        """Initialize workspace manager."""
        self.ticket_id = ticket_id
        self.workspace_path = workspace_path
        self.executor = self._create_executor()
        self.repo_manager = RepositoryManager(self.executor, workspace_path)

    @abstractmethod
    def _create_executor(self) -> CommandExecutor:
        """Create the appropriate command executor."""
        pass

    @abstractmethod
    def get_repo_directory(self, repo_name: str) -> Path:
        """Get the path to the repository directory."""
        pass

    @abstractmethod
    def prepare_workspace(self) -> None:
        """Prepare the workspace (create directories, etc.)."""
        pass

    def setup_repository(self, repo_url: str, branch: str) -> Path:
        """Setup repository in workspace."""
        repo_name = self.repo_manager.extract_repo_name(repo_url, self.ticket_id)
        repo_dir = self.get_repo_directory(repo_name)

        self.repo_manager.setup_repository(
            repo_url, branch, self.ticket_id, repo_dir
        )

        return repo_dir


class LocalWorkspaceManager(WorkspaceManager):
    """Manages local filesystem workspace."""

    def __init__(
        self,
        ticket_id: str,
        workspace_dir: Optional[str] = None,
    ):
        """Initialize local workspace manager."""
        if workspace_dir is None:
            examples_dir = Path(__file__).parent
            workspace_dir = str(examples_dir / "workspaces" / ticket_id)

        workspace_path = Path(workspace_dir)
        workspace_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Using local workspace: {workspace_path.absolute()}")

        super().__init__(ticket_id, workspace_path)

    def _create_executor(self) -> CommandExecutor:
        """Create local command executor."""
        return LocalCommandExecutor()

    def get_repo_directory(self, repo_name: str) -> Path:
        """Get repository directory path."""
        return self.workspace_path / repo_name

    def prepare_workspace(self) -> None:
        """Prepare local workspace (already done in __init__)."""
        pass


class DockerWorkspaceManager(WorkspaceManager):
    """Manages Docker workspace."""

    def __init__(self, ticket_id: str, workspace, host_port: int = 8020):
        """Initialize Docker workspace manager."""
        self.workspace = workspace
        self.host_port = host_port
        workspace_path = Path(workspace.working_dir)

        super().__init__(ticket_id, workspace_path)

    def _create_executor(self) -> CommandExecutor:
        """Create Docker command executor."""
        return DockerCommandExecutor(self.workspace)

    def get_repo_directory(self, repo_name: str) -> Path:
        """Get repository directory path (as string for Docker)."""
        return Path(f"{self.workspace_path}/{repo_name}")

    def prepare_workspace(self) -> None:
        """Prepare Docker workspace (test responsiveness)."""
        logger.info("Waiting for Docker workspace agent server to be ready...")
        test_result = self.executor.sh("echo 'workspace ready'")
        if test_result.exit_code != 0:
            logger.warning("Workspace command test failed, but continuing...")


class ConversationRunner:
    """Manages conversation execution and intervention handling."""

    def __init__(
        self,
        agent: Agent,
        workspace_path: Path,
        ticket_id: str,
        title: str,
        description: str,
        intervention_callback: Optional[Callable] = None,
    ):
        """Initialize conversation runner."""
        self.agent = agent
        self.workspace_path = workspace_path
        self.ticket_id = ticket_id
        self.title = title
        self.description = description
        self.intervention_callback = intervention_callback

    def create_conversation(self, retry_count: int = 5, workspace_obj=None) -> Conversation:
        """Create conversation with retry logic.
        
        Args:
            retry_count: Number of retry attempts
            workspace_obj: Optional workspace object (for DockerWorkspace)
        """
        workspace = workspace_obj if workspace_obj else str(self.workspace_path.absolute())
        
        for attempt in range(retry_count):
            try:
                conversation = Conversation(
                    agent=self.agent,
                    workspace=workspace,
                )
                logger.info("Conversation created successfully")
                return conversation
            except Exception as e:
                if attempt < retry_count - 1:
                    delay = 2 * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"Failed to create conversation (attempt {attempt + 1}/{retry_count}): {e}. "
                        f"Retrying in {delay} seconds..."
                    )
                    time.sleep(delay)
                else:
                    raise

    def build_goal_prompt(self, repo_name: Optional[str] = None) -> str:
        """Build goal prompt for the conversation."""
        repo_context = (
            f"- Work inside the repository directory: {repo_name}\n"
            if repo_name
            else ""
        )
        return f"""
You are working on ticket {self.ticket_id}: {self.title}

Ticket description:
{self.description}

Instructions:
{repo_context}- Use file editor + terminal tools to implement the change.
- Run tests before finishing.
- When done, summarize the changes and what remains risky.
"""

    def run_conversation_in_background(
        self, conversation, wait_for_completion: bool = True
    ) -> tuple[threading.Thread, list]:
        """Run conversation in background thread."""
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

        conversation_thread = threading.Thread(target=run_conversation, daemon=False)
        conversation_thread.start()

        # Wait for conversation to start
        conversation_started.wait(timeout=10)

        if conversation_error[0]:
            error_msg = str(conversation_error[0])
            logger.error(
                f"Conversation failed to start: {error_msg[:200]}. "
                "The InterventionHandler is still available, but interventions may not work."
            )
        else:
            logger.info("Conversation started successfully in background thread")

        return conversation_thread, conversation_error


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

