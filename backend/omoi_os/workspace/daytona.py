"""Daytona Cloud workspace implementation.

Provides command execution and file operations in Daytona Cloud sandboxes
for secure, isolated agent task execution.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from daytona import (
    AsyncDaytona,
    CreateSandboxBaseParams,
    CreateSandboxFromImageParams,
    Daytona,
    DaytonaConfig,
)
from daytona.common.daytona import CodeLanguage

from omoi_os.logging import get_logger
from omoi_os.workspace.managers import CommandExecutor, CommandResult, WorkspaceManager

if TYPE_CHECKING:
    from omoi_os.config import DaytonaSettings

logger = get_logger(__name__)


@dataclass
class DaytonaWorkspaceConfig:
    """Configuration for Daytona workspace."""

    api_key: str
    api_url: str = "https://app.daytona.io/api"
    target: str = "us"
    language: str = "python"  # python, node, go, rust, etc.
    image: Optional[str] = None  # Custom Docker image (overrides language)
    os_user: Optional[str] = None  # OS user for custom images
    working_dir: str = "/home/daytona"  # Working directory in sandbox
    timeout: int = 60  # Sandbox creation timeout
    labels: dict = field(default_factory=dict)
    ephemeral: bool = True  # Auto-delete on stop
    public: bool = False  # Make ports publicly accessible without auth

    @classmethod
    def from_settings(
        cls, settings: "DaytonaSettings" = None, **overrides
    ) -> "DaytonaWorkspaceConfig":
        """Create config from DaytonaSettings (loads from YAML/env).

        Args:
            settings: Optional DaytonaSettings instance. If None, loads from config.
            **overrides: Override specific fields (e.g., labels, image)

        Returns:
            DaytonaWorkspaceConfig instance

        Example:
            # Use defaults from config/base.yaml and DAYTONA_* env vars
            config = DaytonaWorkspaceConfig.from_settings()

            # Use custom Docker image
            config = DaytonaWorkspaceConfig.from_settings(
                image="nikolaik/python-nodejs:python3.12-nodejs22",
                labels={"task_id": "123"}
            )
        """
        if settings is None:
            from omoi_os.config import load_daytona_settings

            settings = load_daytona_settings()

        if not settings.api_key:
            raise ValueError(
                "DAYTONA_API_KEY not configured. Set it in .env.local or config/base.yaml"
            )

        # Get image from settings or overrides
        image = overrides.get("image", settings.image)

        # Map snapshot to language (e.g., "python:3.12" -> "python") if no image
        language = overrides.get("language")
        if not language and not image and settings.snapshot:
            language = settings.snapshot.split(":")[0]  # "python:3.12" -> "python"
        language = language or "python"

        # Set working_dir based on image or default
        working_dir = overrides.get(
            "working_dir", getattr(settings, "working_dir", None)
        )
        if not working_dir:
            # nikolaik images use /home/pn
            if image and "nikolaik" in image:
                working_dir = "/home/pn"
            elif image:
                working_dir = "/root"  # Default for custom images
            else:
                working_dir = "/home/daytona"  # Default for language sandboxes

        return cls(
            api_key=overrides.get("api_key", settings.api_key),
            api_url=overrides.get("api_url", settings.api_url),
            target=overrides.get("target", settings.target),
            language=language,
            image=image,
            os_user=overrides.get("os_user", getattr(settings, "os_user", None)),
            working_dir=working_dir,
            timeout=overrides.get("timeout", settings.timeout),
            labels=overrides.get("labels", {}),
            ephemeral=overrides.get("ephemeral", True),
            public=overrides.get("public", getattr(settings, "public", False)),
        )


class DaytonaCommandExecutor(CommandExecutor):
    """Execute commands in Daytona sandbox."""

    def __init__(self, sandbox, working_dir: str = "/home/daytona"):
        """Initialize with Daytona sandbox instance.

        Args:
            sandbox: Daytona sandbox instance
            working_dir: Default working directory in sandbox
        """
        self.sandbox = sandbox
        self.working_dir = working_dir

    def execute(self, cmd: str, cwd: Optional[str] = None) -> CommandResult:
        """Execute shell command in Daytona sandbox.

        Args:
            cmd: Shell command to execute
            cwd: Working directory (defaults to self.working_dir)

        Returns:
            CommandResult with exit_code, stdout, stderr
        """
        exec_cwd = cwd or self.working_dir

        try:
            result = self.sandbox.process.exec(
                cmd,
                cwd=exec_cwd,
                timeout=300,
            )
            return CommandResult(
                exit_code=result.exit_code if hasattr(result, "exit_code") else 0,
                stdout=result.result if hasattr(result, "result") else str(result),
                stderr=getattr(result, "stderr", "") or "",
            )
        except Exception as e:
            logger.error(f"Daytona command execution failed: {e}")
            return CommandResult(
                exit_code=1,
                stdout="",
                stderr=str(e),
            )


class AsyncDaytonaCommandExecutor:
    """Async command executor for Daytona sandbox."""

    def __init__(self, sandbox, working_dir: str = "/home/daytona"):
        """Initialize with Daytona sandbox instance."""
        self.sandbox = sandbox
        self.working_dir = working_dir

    async def execute(self, cmd: str, cwd: Optional[str] = None) -> CommandResult:
        """Execute shell command asynchronously in Daytona sandbox."""
        exec_cwd = cwd or self.working_dir

        try:
            result = await self.sandbox.process.exec(
                cmd,
                cwd=exec_cwd,
                timeout=300,
            )
            return CommandResult(
                exit_code=result.exit_code if hasattr(result, "exit_code") else 0,
                stdout=result.result if hasattr(result, "result") else str(result),
                stderr=getattr(result, "stderr", "") or "",
            )
        except Exception as e:
            logger.error(f"Daytona async command execution failed: {e}")
            return CommandResult(
                exit_code=1,
                stdout="",
                stderr=str(e),
            )

    async def sh(self, cmd: str, cwd: Optional[str] = None) -> CommandResult:
        """Execute shell command and log failures."""
        result = await self.execute(cmd, cwd)
        if result.exit_code != 0:
            logger.warning(
                f"[AsyncDaytonaCommandExecutor] Command failed: {cmd}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result


class DaytonaWorkspace:
    """Daytona Cloud sandbox workspace.

    Provides an isolated execution environment using Daytona Cloud.
    Supports both sync and async operations.

    Usage (sync):
        with DaytonaWorkspace(config) as workspace:
            result = workspace.execute_command("ls -la")
            workspace.upload_file("local.txt", "/home/daytona/remote.txt")

    Usage (async):
        async with DaytonaWorkspace(config).async_context() as workspace:
            result = await workspace.execute_command_async("ls -la")
    """

    def __init__(self, config: DaytonaWorkspaceConfig):
        """Initialize Daytona workspace.

        Args:
            config: DaytonaWorkspaceConfig with API key and settings
        """
        self.config = config
        self._daytona: Optional[Daytona] = None
        self._async_daytona: Optional[AsyncDaytona] = None
        self._sandbox = None
        self._executor: Optional[DaytonaCommandExecutor] = None
        self.working_dir = config.working_dir

    def __enter__(self) -> "DaytonaWorkspace":
        """Enter sync context - create sandbox."""
        daytona_config = DaytonaConfig(
            api_key=self.config.api_key,
            api_url=self.config.api_url,
            target=self.config.target,
        )
        self._daytona = Daytona(daytona_config)

        # Create sandbox params - use image if specified, otherwise use language
        if self.config.image:
            params = CreateSandboxFromImageParams(
                image=self.config.image,
                os_user=self.config.os_user,
                labels=self.config.labels or None,
                ephemeral=self.config.ephemeral,
                public=self.config.public,
            )
            logger.info(
                f"Creating Daytona sandbox with image: {self.config.image} (public={self.config.public})"
            )
        else:
            params = CreateSandboxBaseParams(
                language=CodeLanguage(self.config.language),
                labels=self.config.labels or None,
                ephemeral=self.config.ephemeral,
                public=self.config.public,
            )
            logger.info(
                f"Creating Daytona sandbox with language: {self.config.language} (public={self.config.public})"
            )

        self._sandbox = self._daytona.create(
            params=params,
            timeout=self.config.timeout,
        )
        self._executor = DaytonaCommandExecutor(self._sandbox, self.working_dir)

        logger.info(f"Daytona sandbox created: {self._sandbox.id}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit sync context - cleanup sandbox."""
        if self._sandbox:
            try:
                logger.info(f"Deleting Daytona sandbox: {self._sandbox.id}")
                self._sandbox.delete()
            except Exception as e:
                logger.warning(f"Failed to delete sandbox: {e}")
        return False

    async def __aenter__(self) -> "DaytonaWorkspace":
        """Enter async context - create sandbox."""
        daytona_config = DaytonaConfig(
            api_key=self.config.api_key,
            api_url=self.config.api_url,
            target=self.config.target,
        )
        self._async_daytona = AsyncDaytona(daytona_config)

        # Create sandbox params
        params = CreateSandboxBaseParams(
            language=CodeLanguage(self.config.language),
            labels=self.config.labels or None,
            ephemeral=self.config.ephemeral,
        )

        logger.info(
            f"Creating Daytona sandbox (async) with language: {self.config.language}"
        )
        self._sandbox = await self._async_daytona.create(
            params=params,
            timeout=self.config.timeout,
        )
        self._executor = AsyncDaytonaCommandExecutor(self._sandbox, self.working_dir)

        logger.info(f"Daytona sandbox created: {self._sandbox.id}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context - cleanup sandbox."""
        if self._sandbox:
            try:
                logger.info(f"Deleting Daytona sandbox: {self._sandbox.id}")
                await self._sandbox.delete()
            except Exception as e:
                logger.warning(f"Failed to delete sandbox: {e}")
        if self._async_daytona:
            await self._async_daytona.close()
        return False

    @property
    def sandbox(self):
        """Get the underlying Daytona sandbox instance."""
        if self._sandbox is None:
            raise RuntimeError(
                "Workspace not initialized. Use 'with' or 'async with' context."
            )
        return self._sandbox

    @property
    def sandbox_id(self) -> str:
        """Get sandbox ID."""
        return self.sandbox.id

    # -------------------------------------------------------------------------
    # Command Execution
    # -------------------------------------------------------------------------

    def execute_command(
        self,
        cmd: str,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> CommandResult:
        """Execute shell command in sandbox (sync).

        Args:
            cmd: Shell command to execute
            cwd: Working directory
            timeout: Command timeout in seconds

        Returns:
            CommandResult with exit_code, stdout, stderr
        """
        if self._executor is None:
            raise RuntimeError("Workspace not initialized")
        return self._executor.execute(cmd, cwd)

    async def execute_command_async(
        self,
        cmd: str,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> CommandResult:
        """Execute shell command in sandbox (async).

        Args:
            cmd: Shell command to execute
            cwd: Working directory
            timeout: Command timeout in seconds

        Returns:
            CommandResult with exit_code, stdout, stderr
        """
        if self._executor is None:
            raise RuntimeError("Workspace not initialized")
        return await self._executor.execute(cmd, cwd)

    # -------------------------------------------------------------------------
    # File Operations
    # -------------------------------------------------------------------------

    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload file to sandbox.

        Args:
            local_path: Path to local file
            remote_path: Destination path in sandbox
        """
        with open(local_path, "rb") as f:
            content = f.read()
        self.sandbox.fs.upload_file(remote_path, content)
        logger.debug(f"Uploaded {local_path} -> {remote_path}")

    def download_file(self, remote_path: str, local_path: str) -> None:
        """Download file from sandbox.

        Args:
            remote_path: Path in sandbox
            local_path: Destination path locally
        """
        content = self.sandbox.fs.download_file(remote_path)
        with open(local_path, "wb") as f:
            f.write(content)
        logger.debug(f"Downloaded {remote_path} -> {local_path}")

    def write_file(self, remote_path: str, content: str | bytes) -> None:
        """Write content to file in sandbox.

        Args:
            remote_path: Path in sandbox
            content: File content (str or bytes)
        """
        import tempfile

        if isinstance(content, str):
            content = content.encode("utf-8")

        # Daytona upload_file expects a local file path, so write to temp file first
        with tempfile.NamedTemporaryFile(delete=False, mode="wb") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            self.sandbox.fs.upload_file(tmp_path, remote_path)
            logger.debug(f"Wrote file: {remote_path}")
        finally:
            import os

            os.unlink(tmp_path)

    def read_file(self, remote_path: str) -> bytes:
        """Read file from sandbox.

        Args:
            remote_path: Path in sandbox

        Returns:
            File content as bytes
        """
        return self.sandbox.fs.download_file(remote_path)

    def create_folder(self, remote_path: str, mode: str = "755") -> None:
        """Create folder in sandbox.

        Args:
            remote_path: Path in sandbox
            mode: Permission mode
        """
        self.sandbox.fs.create_folder(remote_path, mode)
        logger.debug(f"Created folder: {remote_path}")

    # -------------------------------------------------------------------------
    # Git Operations
    # -------------------------------------------------------------------------

    def git_clone(self, url: str, path: str = "workspace") -> None:
        """Clone git repository into sandbox.

        Args:
            url: Repository URL
            path: Destination path in sandbox
        """
        self.sandbox.git.clone(url=url, path=path)
        logger.info(f"Cloned {url} -> {path}")

    def git_add(self, path: str, files: list[str]) -> None:
        """Stage files for commit.

        Args:
            path: Repository path
            files: List of files to stage
        """
        self.sandbox.git.add(path, files)

    def git_commit(
        self,
        path: str,
        message: str,
        author: str = "OmoiOS Agent",
        email: str = "agent@omoios.local",
    ) -> None:
        """Commit staged changes.

        Args:
            path: Repository path
            message: Commit message
            author: Author name
            email: Author email
        """
        self.sandbox.git.commit(
            path=path,
            message=message,
            author=author,
            email=email,
        )
        logger.info(f"Committed: {message[:50]}...")

    def git_status(self, path: str):
        """Get git status.

        Args:
            path: Repository path

        Returns:
            Git status object
        """
        return self.sandbox.git.status(path)

    def git_branches(self, path: str):
        """List branches.

        Args:
            path: Repository path

        Returns:
            List of branches
        """
        return self.sandbox.git.branches(path)

    # -------------------------------------------------------------------------
    # Port / Preview Operations
    # -------------------------------------------------------------------------

    def get_preview_url(self, port: int) -> str:
        """Get public preview URL for a port.

        Args:
            port: Port number running in sandbox

        Returns:
            Public URL to access the port

        Note:
            Sandbox must be created with public=True for unauthenticated access.
        """
        preview = self.sandbox.get_preview_link(port)
        return preview.url

    def get_preview_link(self, port: int):
        """Get full preview link info including token.

        Args:
            port: Port number running in sandbox

        Returns:
            Preview link object with url, token, etc.
        """
        return self.sandbox.get_preview_link(port)


class DaytonaWorkspaceManager(WorkspaceManager):
    """Workspace manager using Daytona Cloud sandboxes.

    Integrates with the existing WorkspaceManager pattern while
    using Daytona for actual execution.
    """

    def __init__(
        self,
        ticket_id: str,
        config: DaytonaWorkspaceConfig,
    ):
        """Initialize Daytona workspace manager.

        Args:
            ticket_id: Unique ticket/task identifier
            config: Daytona configuration
        """
        self.config = config
        self._daytona_workspace: Optional[DaytonaWorkspace] = None

        # Initialize parent with a placeholder path (actual path is in sandbox)
        workspace_path = Path(f"/home/daytona/workspaces/{ticket_id}")
        super().__init__(ticket_id, workspace_path)

    def _create_executor(self) -> CommandExecutor:
        """Create Daytona command executor."""
        if self._daytona_workspace is None:
            raise RuntimeError(
                "Daytona workspace not initialized. Call prepare_workspace() first."
            )
        return self._daytona_workspace._executor

    def get_repo_directory(self, repo_name: str) -> Path:
        """Get repository directory path in sandbox."""
        return Path(f"{self.workspace_path}/{repo_name}")

    def prepare_workspace(self) -> None:
        """Prepare Daytona workspace - create sandbox."""
        if self._daytona_workspace is not None:
            return  # Already prepared

        self._daytona_workspace = DaytonaWorkspace(self.config)
        self._daytona_workspace.__enter__()

        # Update executor
        self.executor = self._create_executor()

        # Create workspace directory in sandbox
        self._daytona_workspace.execute_command(f"mkdir -p {self.workspace_path}")

        logger.info(f"Daytona workspace prepared: {self._daytona_workspace.sandbox_id}")

    def cleanup(self) -> None:
        """Cleanup Daytona workspace - delete sandbox."""
        if self._daytona_workspace is not None:
            self._daytona_workspace.__exit__(None, None, None)
            self._daytona_workspace = None
            logger.info("Daytona workspace cleaned up")

    @property
    def daytona_workspace(self) -> DaytonaWorkspace:
        """Get the underlying DaytonaWorkspace instance."""
        if self._daytona_workspace is None:
            raise RuntimeError("Daytona workspace not initialized")
        return self._daytona_workspace


class OpenHandsDaytonaWorkspace:
    """OpenHands SDK compatible workspace backed by Daytona Cloud.

    This adapter wraps DaytonaWorkspace to implement the OpenHands BaseWorkspace
    interface, allowing Daytona to be used as a workspace backend for OpenHands agents.

    Usage:
        workspace = OpenHandsDaytonaWorkspace(
            working_dir="/workspaces/project-123",
            project_id="project-123",
            settings=load_daytona_settings(),
        )
        with workspace:
            result = workspace.execute_command("ls -la")
    """

    def __init__(
        self,
        working_dir: str,
        project_id: str,
        settings: "DaytonaSettings",
    ):
        """Initialize OpenHands-compatible Daytona workspace.

        Args:
            working_dir: Local working directory (used for staging)
            project_id: Project identifier for sandbox labels
            settings: DaytonaSettings from config
        """
        self.working_dir = working_dir
        self.project_id = project_id
        self._settings = settings
        self._daytona_workspace: Optional[DaytonaWorkspace] = None
        self._local_staging = Path(working_dir)
        self._local_staging.mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> "OpenHandsDaytonaWorkspace":
        """Enter workspace context - create Daytona sandbox."""
        config = DaytonaWorkspaceConfig.from_settings(
            settings=self._settings,
            labels={"project_id": self.project_id},
        )
        self._daytona_workspace = DaytonaWorkspace(config)
        self._daytona_workspace.__enter__()
        logger.info(
            f"OpenHandsDaytonaWorkspace ready: sandbox={self._daytona_workspace.sandbox_id}"
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit workspace context - cleanup sandbox."""
        if self._daytona_workspace:
            self._daytona_workspace.__exit__(exc_type, exc_val, exc_tb)
            self._daytona_workspace = None

    def execute_command(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """Execute a bash command in the Daytona sandbox.

        Args:
            command: The bash command to execute
            cwd: Working directory (optional)
            timeout: Timeout in seconds (default 30.0)

        Returns:
            CommandResult from openhands.sdk.workspace.models
        """
        from openhands.sdk.workspace.models import (
            CommandResult as OpenHandsCommandResult,
        )

        if self._daytona_workspace is None:
            raise RuntimeError("Workspace not initialized. Use 'with' context.")

        result = self._daytona_workspace.execute_command(
            cmd=command,
            cwd=cwd or self._daytona_workspace.working_dir,
            timeout=int(timeout),
        )

        return OpenHandsCommandResult(
            command=command,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            timeout_occurred=False,  # TODO: handle timeout properly
        )

    def file_upload(
        self,
        source_path: str,
        destination_path: str,
    ):
        """Upload a file to the Daytona sandbox.

        Args:
            source_path: Path to the source file (local)
            destination_path: Path where the file should be uploaded (in sandbox)

        Returns:
            FileOperationResult from openhands.sdk.workspace.models
        """
        from openhands.sdk.workspace.models import FileOperationResult

        if self._daytona_workspace is None:
            raise RuntimeError("Workspace not initialized. Use 'with' context.")

        try:
            self._daytona_workspace.upload_file(source_path, destination_path)
            file_size = Path(source_path).stat().st_size
            return FileOperationResult(
                success=True,
                source_path=source_path,
                destination_path=destination_path,
                file_size=file_size,
            )
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            return FileOperationResult(
                success=False,
                source_path=source_path,
                destination_path=destination_path,
                error=str(e),
            )

    def file_download(
        self,
        source_path: str,
        destination_path: str,
    ):
        """Download a file from the Daytona sandbox.

        Args:
            source_path: Path to the source file (in sandbox)
            destination_path: Path where the file should be downloaded (local)

        Returns:
            FileOperationResult from openhands.sdk.workspace.models
        """
        from openhands.sdk.workspace.models import FileOperationResult

        if self._daytona_workspace is None:
            raise RuntimeError("Workspace not initialized. Use 'with' context.")

        try:
            self._daytona_workspace.download_file(source_path, destination_path)
            file_size = Path(destination_path).stat().st_size
            return FileOperationResult(
                success=True,
                source_path=source_path,
                destination_path=destination_path,
                file_size=file_size,
            )
        except Exception as e:
            logger.error(f"File download failed: {e}")
            return FileOperationResult(
                success=False,
                source_path=source_path,
                destination_path=destination_path,
                error=str(e),
            )

    def git_changes(self, path: str) -> list:
        """Get git changes for the repository at the path.

        Args:
            path: Path to the git repository (in sandbox)

        Returns:
            list[GitChange] with status and path for each changed file
        """
        from openhands.sdk.git.models import GitChange, GitChangeStatus

        if self._daytona_workspace is None:
            raise RuntimeError("Workspace not initialized. Use 'with' context.")

        # Run git status --porcelain to get changed files
        # Format: XY PATH or XY ORIG -> PATH for renames
        result = self._daytona_workspace.execute_command(
            f"cd {path} && git status --porcelain",
            cwd=self._daytona_workspace.working_dir,
        )

        if result.exit_code != 0:
            logger.warning(f"git status failed: {result.stderr}")
            return []

        changes = []
        # Use rstrip() to preserve leading spaces in status codes
        for line in result.stdout.rstrip().split("\n"):
            if not line or len(line) < 4:
                continue

            # Parse status codes (first two chars, third is space)
            # Format: "XY filename" where X=index status, Y=worktree status
            index_status = line[0]
            worktree_status = line[1]
            # Skip the space at position 2
            file_path = line[3:]

            # Handle renames: "R  old -> new"
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
            elif index_status == "?":  # Untracked
                status = GitChangeStatus.ADDED
            else:
                status = GitChangeStatus.UPDATED

            changes.append(GitChange(status=status, path=Path(file_path)))

        return changes

    def git_diff(self, path: str):
        """Get git diff for the file at the path.

        Args:
            path: Path to the file (in sandbox, relative to repo root)

        Returns:
            GitDiff with original and modified content
        """
        from openhands.sdk.git.models import GitDiff

        if self._daytona_workspace is None:
            raise RuntimeError("Workspace not initialized. Use 'with' context.")

        working_dir = self._daytona_workspace.working_dir

        # Get the original content from HEAD
        original_result = self._daytona_workspace.execute_command(
            f"git show HEAD:{path} 2>/dev/null || echo ''",
            cwd=working_dir,
        )
        original = original_result.stdout if original_result.exit_code == 0 else None

        # Get the modified (current) content
        modified_result = self._daytona_workspace.execute_command(
            f"cat {path} 2>/dev/null || echo ''",
            cwd=working_dir,
        )
        modified = modified_result.stdout if modified_result.exit_code == 0 else None

        # Handle empty strings as None
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
