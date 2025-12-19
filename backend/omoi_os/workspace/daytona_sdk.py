"""
SDK-Compatible Daytona Workspace Adapter

This module provides a Daytona workspace that properly inherits from the
OpenHands SDK LocalWorkspace, allowing it to be used directly with the
SDK's Conversation class.

The key difference from OpenHandsDaytonaWorkspace:
- Inherits from LocalWorkspace (required by SDK Conversation)
- Uses Pydantic model_post_init for setup
- Properly implements context manager protocol

Usage:
    from omoi_os.workspace.daytona_sdk import DaytonaLocalWorkspace

    workspace = DaytonaLocalWorkspace(
        working_dir="/workspaces/project",
        daytona_api_key="your-key",
    )

    with workspace:
        conversation = Conversation(agent=agent, workspace=workspace)
        conversation.send_message("Hello")
        conversation.run()
"""

from pathlib import Path
from typing import Any, Optional

from openhands.sdk.git.models import GitChange, GitChangeStatus, GitDiff
from openhands.sdk.workspace import LocalWorkspace
from openhands.sdk.workspace.models import CommandResult, FileOperationResult
from pydantic import Field, PrivateAttr

from omoi_os.logging import get_logger

logger = get_logger(__name__)


class DaytonaLocalWorkspace(LocalWorkspace):
    """SDK-compatible Daytona workspace that inherits from LocalWorkspace.

    This adapter allows Daytona cloud sandboxes to be used with the OpenHands
    SDK Conversation class by properly inheriting from LocalWorkspace.

    All command execution, file operations, and git operations are forwarded
    to the Daytona sandbox while maintaining SDK compatibility.

    Attributes:
        working_dir: Working directory (used for local staging)
        daytona_api_key: Daytona API key for authentication
        daytona_api_url: Daytona API URL (default: https://api.daytona.io)
        daytona_target: Daytona target environment
        project_id: Project identifier for sandbox labels
        sandbox_image: Docker image for the sandbox
    """

    # Daytona configuration fields
    daytona_api_key: str = Field(description="Daytona API key")
    daytona_api_url: str = Field(
        default="https://app.daytona.io/api", description="Daytona API URL"
    )
    daytona_target: str = Field(default="us", description="Daytona target environment")
    project_id: str = Field(default="default", description="Project identifier")
    sandbox_image: str = Field(
        default="nikolaik/python-nodejs:python3.12-nodejs22",
        description="Sandbox Docker image",
    )

    # Private attributes for runtime state
    _daytona_workspace: Any = PrivateAttr(default=None)
    _initialized: bool = PrivateAttr(default=False)

    def model_post_init(self, __context: Any) -> None:
        """Initialize after Pydantic model creation."""
        super().model_post_init(__context)
        # Ensure local staging directory exists
        Path(self.working_dir).mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> "DaytonaLocalWorkspace":
        """Enter context - create Daytona sandbox."""
        if self._initialized:
            return self

        # Late import to avoid circular dependencies
        from omoi_os.workspace.daytona import DaytonaWorkspace, DaytonaWorkspaceConfig

        # Determine working_dir based on image
        sandbox_working_dir = "/home/pn" if "nikolaik" in self.sandbox_image else "/workspace"

        config = DaytonaWorkspaceConfig(
            api_key=self.daytona_api_key,
            api_url=self.daytona_api_url,
            target=self.daytona_target,
            image=self.sandbox_image,
            labels={"project_id": self.project_id, "adapter": "sdk-compatible"},
            ephemeral=True,  # Auto-delete on stop
            working_dir=sandbox_working_dir,
        )

        self._daytona_workspace = DaytonaWorkspace(config)
        self._daytona_workspace.__enter__()
        self._initialized = True

        logger.info(
            f"DaytonaLocalWorkspace ready: sandbox={self._daytona_workspace.sandbox_id}"
        )
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context - cleanup sandbox."""
        if self._daytona_workspace is not None:
            self._daytona_workspace.__exit__(exc_type, exc_val, exc_tb)
            self._daytona_workspace = None
            self._initialized = False
            logger.info("DaytonaLocalWorkspace cleaned up")

    def _ensure_initialized(self) -> None:
        """Ensure workspace is initialized."""
        if not self._initialized or self._daytona_workspace is None:
            raise RuntimeError(
                "Workspace not initialized. Use 'with workspace:' context manager."
            )

    def execute_command(
        self,
        command: str,
        cwd: str | Path | None = None,
        timeout: float = 30.0,
    ) -> CommandResult:
        """Execute a bash command in the Daytona sandbox.

        Args:
            command: The bash command to execute
            cwd: Working directory (optional, defaults to /workspace)
            timeout: Timeout in seconds

        Returns:
            CommandResult with stdout, stderr, exit_code
        """
        self._ensure_initialized()

        result = self._daytona_workspace.execute_command(
            cmd=command,
            cwd=str(cwd) if cwd else self._daytona_workspace.working_dir,
            timeout=int(timeout),
        )

        return CommandResult(
            command=command,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            timeout_occurred=False,
        )

    def file_upload(
        self,
        source_path: str | Path,
        destination_path: str | Path,
    ) -> FileOperationResult:
        """Upload a file to the Daytona sandbox.

        Args:
            source_path: Path to the local source file
            destination_path: Path in the sandbox

        Returns:
            FileOperationResult with success status
        """
        self._ensure_initialized()

        source = Path(source_path)
        destination = str(destination_path)

        try:
            self._daytona_workspace.upload_file(str(source), destination)
            return FileOperationResult(
                success=True,
                source_path=str(source),
                destination_path=destination,
                file_size=source.stat().st_size,
            )
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            return FileOperationResult(
                success=False,
                source_path=str(source),
                destination_path=destination,
                error=str(e),
            )

    def file_download(
        self,
        source_path: str | Path,
        destination_path: str | Path,
    ) -> FileOperationResult:
        """Download a file from the Daytona sandbox.

        Args:
            source_path: Path in the sandbox
            destination_path: Local destination path

        Returns:
            FileOperationResult with success status
        """
        self._ensure_initialized()

        source = str(source_path)
        destination = Path(destination_path)

        try:
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            self._daytona_workspace.download_file(source, str(destination))
            return FileOperationResult(
                success=True,
                source_path=source,
                destination_path=str(destination),
                file_size=destination.stat().st_size,
            )
        except Exception as e:
            logger.error(f"File download failed: {e}")
            return FileOperationResult(
                success=False,
                source_path=source,
                destination_path=str(destination),
                error=str(e),
            )

    def git_changes(self, path: str | Path) -> list[GitChange]:
        """Get git changes for a repository in the sandbox.

        Args:
            path: Path to the git repository in the sandbox

        Returns:
            List of GitChange objects
        """
        self._ensure_initialized()

        result = self._daytona_workspace.execute_command(
            f"cd {path} && git status --porcelain",
            cwd=self._daytona_workspace.working_dir,
        )

        if result.exit_code != 0:
            logger.warning(f"git status failed: {result.stderr}")
            return []

        changes = []
        for line in result.stdout.rstrip().split("\n"):
            if not line or len(line) < 4:
                continue

            index_status = line[0]
            worktree_status = line[1]
            file_path = line[3:]

            # Handle renames
            if " -> " in file_path:
                _, file_path = file_path.split(" -> ", 1)

            # Determine status
            if index_status == "A" or worktree_status == "A":
                status = GitChangeStatus.ADDED
            elif index_status == "D" or worktree_status == "D":
                status = GitChangeStatus.DELETED
            elif index_status == "R" or worktree_status == "R":
                status = GitChangeStatus.MOVED
            elif index_status == "M" or worktree_status == "M":
                status = GitChangeStatus.UPDATED
            elif index_status == "?":
                status = GitChangeStatus.ADDED
            else:
                status = GitChangeStatus.UPDATED

            changes.append(GitChange(status=status, path=Path(file_path)))

        return changes

    def git_diff(self, path: str | Path) -> GitDiff:
        """Get git diff for a file in the sandbox.

        Args:
            path: Path to the file relative to repo root

        Returns:
            GitDiff with original and modified content
        """
        self._ensure_initialized()

        working_dir = self._daytona_workspace.working_dir

        # Get original content from HEAD
        original_result = self._daytona_workspace.execute_command(
            f"git show HEAD:{path} 2>/dev/null || echo ''",
            cwd=working_dir,
        )
        original = original_result.stdout if original_result.exit_code == 0 else None

        # Get modified content
        modified_result = self._daytona_workspace.execute_command(
            f"cat {path} 2>/dev/null || echo ''",
            cwd=working_dir,
        )
        modified = modified_result.stdout if modified_result.exit_code == 0 else None

        # Handle empty strings
        if original == "":
            original = None
        if modified == "":
            modified = None

        return GitDiff(original=original, modified=modified)

    @property
    def sandbox_id(self) -> Optional[str]:
        """Get the underlying Daytona sandbox ID."""
        if self._daytona_workspace:
            return self._daytona_workspace.sandbox_id
        return None

    @property
    def is_initialized(self) -> bool:
        """Check if workspace is initialized."""
        return self._initialized
