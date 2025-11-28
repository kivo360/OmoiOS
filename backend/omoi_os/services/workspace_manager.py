"""Unified Workspace Manager Service.

Integrates the OOP workspace managers with the application's workspace isolation system.
Provides Git-backed workspaces with branching, commits, and merges per the documented design.

Also provides OpenHands workspace integration for agent execution.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union, TYPE_CHECKING
from uuid import uuid4

from omoi_os.config import WorkspaceSettings, load_workspace_settings
from omoi_os.models.workspace import (
    AgentWorkspace,
    WorkspaceCommit,
    MergeConflictResolution,
)
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now

# Import OOP workspace managers from omoi_os.workspace
from omoi_os.workspace import (
    LocalCommandExecutor,
    LocalWorkspaceManager,
)

# OpenHands workspace imports (lazy loaded to avoid import errors if not installed)
if TYPE_CHECKING:
    from openhands.sdk.workspace import LocalWorkspace
    from openhands.workspace.docker import DockerWorkspace

logger = None  # Will be initialized on first use


def get_logger():
    """Lazy import logger to avoid circular dependencies."""
    global logger
    if logger is None:
        from openhands.sdk import get_logger as get_openhands_logger

        logger = get_openhands_logger(__name__)
    return logger


@dataclass
class WorkspaceInfo:
    """Information about a created workspace."""

    working_directory: str
    branch_name: str
    parent_commit: Optional[str] = None
    workspace_id: Optional[str] = None


@dataclass
class WorkspaceChanges:
    """Changes made in a workspace."""

    files_created: List[str]
    files_modified: List[str]
    files_deleted: List[str]
    total_changes: int
    stats: Dict[str, int]
    detailed_diff: Optional[str] = None


@dataclass
class CommitInfo:
    """Information about a Git commit."""

    commit_sha: str
    files_changed: int
    message: str
    timestamp: Optional[str] = None


@dataclass
class MergeResult:
    """Result of merging workspace changes."""

    status: str  # "success" | "conflict_resolved"
    merged_to: str
    commit_sha: str
    conflicts_resolved: List[str]
    resolution_strategy: str
    total_conflicts: int


class WorkspaceManagerService:
    """
    Unified Workspace Manager Service.

    Integrates OOP workspace managers with database-backed workspace tracking.
    Provides Git-backed workspaces with branching, commits, and merges.
    """

    def __init__(
        self,
        db: DatabaseService,
        workspace_settings: Optional[WorkspaceSettings] = None,
    ):
        """Initialize workspace manager service."""
        self.db = db
        self.settings = workspace_settings or load_workspace_settings()
        self.base_path = Path(self.settings.worker_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def create_workspace(
        self,
        agent_id: str,
        repo_url: Optional[str] = None,
        branch: str = "main",
        parent_id: Optional[str] = None,
        use_docker: bool = False,
        host_port: Optional[int] = None,
    ) -> WorkspaceInfo:
        """
        Create a new isolated workspace for an agent with Git branching.

        Args:
            agent_id: Unique agent identifier
            repo_url: Optional repository URL to clone (if None, uses existing repo)
            branch: Git branch to checkout (default: "main")
            parent_id: Parent agent ID for inheritance
            use_docker: If True, use Docker workspace (default: False)
            host_port: Host port for Docker workspace (only used if use_docker=True)

        Returns:
            WorkspaceInfo with working_directory, branch_name, parent_commit
        """
        log = get_logger()
        log.info(f"Creating workspace for agent {agent_id}")

        # Generate workspace branch name
        branch_name = f"workspace-agent-{agent_id}"

        # Get parent commit if parent_id is provided
        parent_commit = None
        if parent_id:
            parent_commit = self._get_parent_commit(parent_id)

        # Create workspace directory
        workspace_dir = self.base_path / f"ws_{agent_id}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # Use appropriate workspace manager based on type
        if use_docker:
            # For Docker, we need to create DockerWorkspace first
            # This is handled by the caller who passes the workspace object
            # For now, fall back to local
            log.warning(
                "Docker workspace creation requires DockerWorkspace object. "
                "Falling back to local workspace."
            )
            workspace_manager = LocalWorkspaceManager(
                ticket_id=agent_id, workspace_dir=str(workspace_dir)
            )
        else:
            workspace_manager = LocalWorkspaceManager(
                ticket_id=agent_id, workspace_dir=str(workspace_dir)
            )

        workspace_manager.prepare_workspace()

        # If repo_url is provided, clone it
        if repo_url:
            repo_dir = workspace_manager.setup_repository(repo_url, branch)
            working_directory = str(repo_dir.absolute())
        else:
            # Use workspace directory directly
            working_directory = str(workspace_dir.absolute())

        # Store workspace info in database
        self._store_workspace_info(
            agent_id=agent_id,
            working_directory=working_directory,
            branch_name=branch_name,
            parent_commit=parent_commit,
            parent_agent_id=parent_id,
            repo_url=repo_url,
            base_branch=branch,
            workspace_type="docker" if use_docker else "local",
            workspace_config={"host_port": host_port}
            if use_docker and host_port
            else None,
        )

        log.info(
            f"Created workspace for agent {agent_id}: {working_directory} "
            f"(branch: {branch_name})"
        )

        return WorkspaceInfo(
            working_directory=working_directory,
            branch_name=branch_name,
            parent_commit=parent_commit,
            workspace_id=agent_id,
        )

    def commit_for_validation(
        self, agent_id: str, iteration: int, message: Optional[str] = None
    ) -> CommitInfo:
        """
        Create a Git commit representing the workspace's state for validator inspection.

        Args:
            agent_id: Agent identifier
            iteration: Iteration number
            message: Optional commit message

        Returns:
            CommitInfo with commit_sha, files_changed, message
        """
        log = get_logger()
        workspace_info = self._get_workspace_info(agent_id)
        if not workspace_info:
            raise ValueError(f"Workspace not found for agent {agent_id}")

        working_dir = Path(workspace_info["working_directory"])

        # Create commit message
        commit_message = (
            message
            or f"[Agent {agent_id}] Iteration {iteration} - Ready for validation"
        )

        # Execute git commands
        executor = LocalCommandExecutor()

        # Stage all changes
        executor.execute("git add -A", cwd=str(working_dir))

        # Create commit
        result = executor.execute(
            f'git commit -m "{commit_message}"', cwd=str(working_dir)
        )

        if result.exit_code != 0:
            log.warning(f"Commit failed: {result.stderr}")
            # Try to get current commit SHA anyway
            result = executor.execute("git rev-parse HEAD", cwd=str(working_dir))
            commit_sha = result.stdout.strip() if result.exit_code == 0 else "unknown"
        else:
            # Get commit SHA
            result = executor.execute("git rev-parse HEAD", cwd=str(working_dir))
            commit_sha = result.stdout.strip()

        # Count files changed
        result = executor.execute(
            "git diff --name-only HEAD~1 HEAD", cwd=str(working_dir)
        )
        files_changed = len([f for f in result.stdout.strip().split("\n") if f.strip()])

        # Store commit info in database
        self._store_commit_info(
            agent_id=agent_id,
            commit_sha=commit_sha,
            files_changed=files_changed,
            message=commit_message,
            iteration=iteration,
            commit_type="validation",
            metadata={
                "files_changed": files_changed
            },  # This will be stored as commit_metadata
        )

        return CommitInfo(
            commit_sha=commit_sha,
            files_changed=files_changed,
            message=commit_message,
            timestamp=utc_now().isoformat(),
        )

    def get_workspace_changes(
        self, agent_id: str, since_commit: Optional[str] = None
    ) -> WorkspaceChanges:
        """
        Returns detailed file diff metadata.

        Args:
            agent_id: Agent identifier
            since_commit: Optional commit SHA to compare against (default: parent commit)

        Returns:
            WorkspaceChanges with file lists and stats
        """
        workspace_info = self._get_workspace_info(agent_id)
        if not workspace_info:
            raise ValueError(f"Workspace not found for agent {agent_id}")

        working_dir = Path(workspace_info["working_directory"])
        executor = LocalCommandExecutor()

        # Determine comparison point
        compare_point = since_commit or workspace_info.get("parent_commit") or "HEAD~1"

        # Get file changes
        result = executor.execute(
            f"git diff --name-status {compare_point} HEAD", cwd=str(working_dir)
        )

        files_created = []
        files_modified = []
        files_deleted = []

        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            status, filepath = line.split("\t", 1)
            if status.startswith("A"):
                files_created.append(filepath)
            elif status.startswith("M"):
                files_modified.append(filepath)
            elif status.startswith("D"):
                files_deleted.append(filepath)

        # Get diff stats
        result = executor.execute(
            f"git diff --stat {compare_point} HEAD", cwd=str(working_dir)
        )
        stats = (
            (
                self._parse_diff_stats(result.stdout)
                if result.exit_code == 0
                else {"insertions": 0, "deletions": 0}
            )
            if result.exit_code == 0
            else {"insertions": 0, "deletions": 0}
        )

        # Get detailed diff
        result = executor.execute(
            f"git diff {compare_point} HEAD", cwd=str(working_dir)
        )
        detailed_diff = result.stdout

        return WorkspaceChanges(
            files_created=files_created,
            files_modified=files_modified,
            files_deleted=files_deleted,
            total_changes=len(files_created) + len(files_modified) + len(files_deleted),
            stats=stats,
            detailed_diff=detailed_diff,
        )

    def merge_to_parent(
        self, agent_id: str, target_branch: str = "main"
    ) -> MergeResult:
        """
        Merge a workspace's changes back into its parent or main branch.

        Uses "newest file wins" strategy for conflict resolution.

        Args:
            agent_id: Agent identifier
            target_branch: Target branch to merge into (default: "main")

        Returns:
            MergeResult with merge status and conflict information
        """
        log = get_logger()
        workspace_info = self._get_workspace_info(agent_id)
        if not workspace_info:
            raise ValueError(f"Workspace not found for agent {agent_id}")

        working_dir = Path(workspace_info["working_directory"])
        branch_name = workspace_info["branch_name"]
        executor = LocalCommandExecutor()

        # Switch to target branch
        executor.execute(f"git checkout {target_branch}", cwd=str(working_dir))

        # Merge workspace branch
        result = executor.execute(
            f"git merge {branch_name} --no-ff", cwd=str(working_dir)
        )

        conflicts_resolved = []
        total_conflicts = 0

        if result.exit_code != 0:
            # Handle conflicts using "newest file wins" strategy
            log.info(
                "Merge conflicts detected, resolving with newest file wins strategy"
            )
            conflicts = self._detect_conflicts(working_dir)
            total_conflicts = len(conflicts)

            for conflict_file in conflicts:
                # Use workspace version (newer)
                executor.execute(
                    f"git checkout --theirs {conflict_file}", cwd=str(working_dir)
                )
                executor.execute("git add {conflict_file}", cwd=str(working_dir))
                conflicts_resolved.append(conflict_file)

            # Complete merge
            executor.execute(
                'git commit -m "Merge workspace branch with conflict resolution"',
                cwd=str(working_dir),
            )

        # Get merge commit SHA
        result = executor.execute("git rev-parse HEAD", cwd=str(working_dir))
        commit_sha = result.stdout.strip()

        # Store merge conflict resolution in database
        self._store_merge_resolution(
            agent_id=agent_id,
            merge_commit_sha=commit_sha,
            target_branch=target_branch,
            source_branch=branch_name,
            conflicts_resolved=conflicts_resolved,
            resolution_strategy="newest_file_wins",
            total_conflicts=total_conflicts,
        )

        return MergeResult(
            status="conflict_resolved" if total_conflicts > 0 else "success",
            merged_to=target_branch,
            commit_sha=commit_sha,
            conflicts_resolved=conflicts_resolved,
            resolution_strategy="newest_file_wins",
            total_conflicts=total_conflicts,
        )

    def cleanup_workspace(
        self, agent_id: str, preserve_branch: bool = True
    ) -> Dict[str, any]:
        """
        Delete a workspace and (optionally) preserve its Git branch for debugging.

        Args:
            agent_id: Agent identifier
            preserve_branch: If True, preserve Git branch (default: True)

        Returns:
            Dictionary with cleanup status and disk space freed
        """
        log = get_logger()
        workspace_info = self._get_workspace_info(agent_id)
        if not workspace_info:
            log.warning(f"Workspace not found for agent {agent_id}")
            return {"status": "not_found"}

        working_dir = Path(workspace_info["working_directory"])

        # Calculate disk space before cleanup
        disk_space_mb = self._calculate_directory_size(working_dir) / (1024 * 1024)

        # Delete workspace directory
        import shutil

        shutil.rmtree(working_dir, ignore_errors=True)

        # Mark workspace as inactive in database (don't delete for audit trail)
        self._deactivate_workspace(agent_id)

        log.info(f"Cleaned up workspace for agent {agent_id}")

        return {
            "status": "cleaned",
            "branch_preserved": preserve_branch,
            "disk_space_freed_mb": int(disk_space_mb),
        }

    # Private helper methods

    def _get_parent_commit(self, parent_id: str) -> Optional[str]:
        """Get parent commit SHA from database."""
        with self.db.get_session() as session:
            parent_workspace = (
                session.query(AgentWorkspace)
                .filter(AgentWorkspace.agent_id == parent_id)
                .first()
            )
            if parent_workspace:
                # Get the latest commit for the parent workspace
                latest_commit = (
                    session.query(WorkspaceCommit)
                    .filter(WorkspaceCommit.agent_id == parent_id)
                    .order_by(WorkspaceCommit.created_at.desc())
                    .first()
                )
                if latest_commit:
                    return latest_commit.commit_sha
            return None

    def _store_workspace_info(
        self,
        agent_id: str,
        working_directory: str,
        branch_name: str,
        parent_commit: Optional[str],
        parent_agent_id: Optional[str] = None,
        repo_url: Optional[str] = None,
        base_branch: str = "main",
        workspace_type: str = "local",
        workspace_config: Optional[dict] = None,
    ):
        """Store workspace information in database."""
        with self.db.get_session() as session:
            workspace = AgentWorkspace(
                agent_id=agent_id,
                working_directory=working_directory,
                branch_name=branch_name,
                parent_commit=parent_commit,
                parent_agent_id=parent_agent_id,
                repo_url=repo_url,
                base_branch=base_branch,
                workspace_type=workspace_type,
                workspace_config=workspace_config,
                is_active=True,
            )
            session.add(workspace)
            session.commit()
            get_logger().info(
                f"Stored workspace info: agent_id={agent_id}, "
                f"dir={working_directory}, branch={branch_name}"
            )

    def _get_workspace_info(self, agent_id: str) -> Optional[Dict[str, any]]:
        """Get workspace information from database."""
        with self.db.get_session() as session:
            workspace = (
                session.query(AgentWorkspace)
                .filter(AgentWorkspace.agent_id == agent_id)
                .first()
            )
            if workspace:
                return {
                    "working_directory": workspace.working_directory,
                    "branch_name": workspace.branch_name,
                    "parent_commit": workspace.parent_commit,
                    "parent_agent_id": workspace.parent_agent_id,
                    "repo_url": workspace.repo_url,
                    "base_branch": workspace.base_branch,
                    "workspace_type": workspace.workspace_type,
                    "workspace_config": workspace.workspace_config,
                    "is_active": workspace.is_active,
                }
            return None

    def _store_commit_info(
        self,
        agent_id: str,
        commit_sha: str,
        files_changed: int,
        message: str,
        iteration: Optional[int] = None,
        commit_type: str = "validation",
        metadata: Optional[dict] = None,
    ):
        """Store commit information in database."""
        with self.db.get_session() as session:
            commit = WorkspaceCommit(
                id=str(uuid4()),
                agent_id=agent_id,
                commit_sha=commit_sha,
                files_changed=files_changed,
                message=message,
                iteration=iteration,
                commit_type=commit_type,
                commit_metadata=metadata,  # Use commit_metadata instead of metadata
            )
            session.add(commit)
            session.commit()
            get_logger().info(
                f"Stored commit info: agent_id={agent_id}, "
                f"commit={commit_sha}, files={files_changed}"
            )

    def _parse_diff_stats(self, diff_output: str) -> Dict[str, int]:
        """Parse git diff --stat output."""
        stats = {"insertions": 0, "deletions": 0}
        # Simple parsing - can be enhanced
        for line in diff_output.split("\n"):
            if "insertion" in line or "deletion" in line:
                # Extract numbers
                import re

                matches = re.findall(r"(\d+)\s+(insertion|deletion)", line)
                for count, type_ in matches:
                    if type_ == "insertion":
                        stats["insertions"] += int(count)
                    else:
                        stats["deletions"] += int(count)
        return stats

    def _detect_conflicts(self, working_dir: Path) -> List[str]:
        """Detect merge conflict files."""
        executor = LocalCommandExecutor()
        result = executor.execute(
            "git diff --name-only --diff-filter=U", cwd=str(working_dir)
        )
        return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]

    def _calculate_directory_size(self, directory: Path) -> int:
        """Calculate total size of directory in bytes."""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = Path(dirpath) / filename
                try:
                    total_size += filepath.stat().st_size
                except (OSError, FileNotFoundError):
                    pass
        return total_size

    def _store_merge_resolution(
        self,
        agent_id: str,
        merge_commit_sha: str,
        target_branch: str,
        source_branch: str,
        conflicts_resolved: List[str],
        resolution_strategy: str,
        total_conflicts: int,
        merge_metadata: Optional[dict] = None,
    ):
        """Store merge conflict resolution in database."""
        with self.db.get_session() as session:
            resolution = MergeConflictResolution(
                id=str(uuid4()),
                agent_id=agent_id,
                merge_commit_sha=merge_commit_sha,
                target_branch=target_branch,
                source_branch=source_branch,
                conflicts_resolved=conflicts_resolved,
                resolution_strategy=resolution_strategy,
                total_conflicts=total_conflicts,
                merge_extra_data=merge_metadata,  # Use merge_extra_data instead of merge_metadata
            )
            session.add(resolution)
            session.commit()
            get_logger().info(
                f"Stored merge resolution: agent_id={agent_id}, "
                f"commit={merge_commit_sha}, conflicts={total_conflicts}"
            )

    def _deactivate_workspace(self, agent_id: str):
        """Deactivate workspace in database (mark as inactive, don't delete)."""
        with self.db.get_session() as session:
            workspace = (
                session.query(AgentWorkspace)
                .filter(AgentWorkspace.agent_id == agent_id)
                .first()
            )
            if workspace:
                workspace.is_active = False
                workspace.updated_at = utc_now()
                session.commit()
                get_logger().info(f"Deactivated workspace for agent {agent_id}")


class OpenHandsWorkspaceFactory:
    """
    Factory for creating OpenHands SDK workspaces.

    Supports three modes:
    - local: Direct filesystem access (LocalWorkspace)
    - docker: Isolated Docker container (DockerWorkspace)
    - remote: Connect to existing OpenHands agent server (RemoteWorkspace)

    Example:
        factory = OpenHandsWorkspaceFactory()
        workspace = factory.create_for_project("proj-123")
        with workspace:
            # Agent operations run in isolated workspace
            result = workspace.execute_command("ls -la")
    """

    def __init__(self, settings: Optional[WorkspaceSettings] = None):
        """Initialize workspace factory."""
        self.settings = settings or load_workspace_settings()
        self.base_path = Path(self.settings.root)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def create_for_project(
        self,
        project_id: str,
        task_id: Optional[str] = None,
    ) -> "Union[LocalWorkspace, DockerWorkspace]":
        """
        Create an OpenHands workspace for a project.

        Args:
            project_id: Project identifier
            task_id: Optional task ID for task-specific subdirectory

        Returns:
            OpenHands workspace instance (LocalWorkspace or DockerWorkspace)
        """
        log = get_logger()
        mode = self.settings.mode

        # Build workspace path: /workspaces/{project_id}/[{task_id}/]
        workspace_path = self.base_path / project_id
        if task_id:
            workspace_path = workspace_path / task_id
        workspace_path.mkdir(parents=True, exist_ok=True)

        log.info(
            f"Creating {mode} workspace for project {project_id} at {workspace_path}"
        )

        if mode == "local":
            return self._create_local_workspace(workspace_path)
        elif mode == "docker":
            return self._create_docker_workspace(workspace_path, project_id)
        elif mode == "remote":
            return self._create_remote_workspace(workspace_path)
        else:
            log.warning(f"Unknown workspace mode '{mode}', falling back to local")
            return self._create_local_workspace(workspace_path)

    def _create_local_workspace(self, workspace_path: Path) -> "LocalWorkspace":
        """Create a LocalWorkspace for direct filesystem access."""
        from openhands.sdk.workspace import LocalWorkspace

        return LocalWorkspace(working_dir=str(workspace_path))

    def _create_docker_workspace(
        self, workspace_path: Path, project_id: str
    ) -> "DockerWorkspace":
        """Create a DockerWorkspace for isolated container execution."""
        try:
            from openhands.workspace.docker import DockerWorkspace
        except ImportError:
            get_logger().warning(
                "openhands-workspace not installed, falling back to LocalWorkspace. "
                "Install with: uv sync --group dev"
            )
            return self._create_local_workspace(workspace_path)

        # Use server_image if provided, else build from base_image
        if self.settings.docker_server_image:
            return DockerWorkspace(
                server_image=self.settings.docker_server_image,
                mount_dir=str(workspace_path),
                working_dir="/workspace",
            )
        elif self.settings.docker_base_image:
            return DockerWorkspace(
                base_image=self.settings.docker_base_image,
                mount_dir=str(workspace_path),
                working_dir="/workspace",
            )
        else:
            get_logger().warning(
                "No docker image configured, falling back to LocalWorkspace. "
                "Set WORKSPACE_DOCKER_SERVER_IMAGE or WORKSPACE_DOCKER_BASE_IMAGE"
            )
            return self._create_local_workspace(workspace_path)

    def _create_remote_workspace(self, workspace_path: Path) -> "LocalWorkspace":
        """Create a RemoteWorkspace for connecting to an existing agent server."""
        if not self.settings.remote_host:
            get_logger().warning(
                "No remote host configured, falling back to LocalWorkspace. "
                "Set WORKSPACE_REMOTE_HOST"
            )
            return self._create_local_workspace(workspace_path)

        try:
            from openhands.sdk.workspace import RemoteWorkspace

            return RemoteWorkspace(
                host=self.settings.remote_host,
                api_key=self.settings.remote_api_key,
                working_dir=str(workspace_path),
            )
        except ImportError:
            get_logger().warning(
                "RemoteWorkspace not available, falling back to LocalWorkspace"
            )
            return self._create_local_workspace(workspace_path)

    def get_project_workspace_path(self, project_id: str) -> Path:
        """Get the filesystem path for a project's workspace."""
        return self.base_path / project_id


# Singleton factory instance
_workspace_factory: Optional[OpenHandsWorkspaceFactory] = None


def get_workspace_factory() -> OpenHandsWorkspaceFactory:
    """Get or create the global workspace factory."""
    global _workspace_factory
    if _workspace_factory is None:
        _workspace_factory = OpenHandsWorkspaceFactory()
    return _workspace_factory
