"""Workspace management classes using OOP principles.

Provides command executors, repository managers, and workspace managers
for both local and Docker environments.
"""

import logging
import platform
import re
import socket
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


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
            workspace_dir = str(Path.cwd() / "workspaces" / ticket_id)

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
