"""Sandbox Git Operations Service for parallel task code merging.

Phase B: Git operations for DAG Merge Executor integration.

This service wraps git operations that run inside Daytona sandboxes,
enabling:
- Merge operations at convergence points
- Conflict detection via dry-run (git merge-tree)
- Rebase operations for sequential commit ordering
- Conflict content extraction for LLM resolution

All operations run inside the sandbox's isolated environment, keeping
the merge process secure and contained.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from omoi_os.logging import get_logger

if TYPE_CHECKING:
    from daytona_sdk import Sandbox

logger = get_logger(__name__)


class MergeResultStatus(str, Enum):
    """Status of a merge operation."""

    SUCCESS = "success"  # Merge completed cleanly
    CONFLICT = "conflict"  # Merge has conflicts requiring resolution
    FAILED = "failed"  # Merge failed (not due to conflicts)
    ABORTED = "aborted"  # Merge was aborted


@dataclass
class ConflictInfo:
    """Information about a single conflict in a file."""

    file_path: str
    conflict_type: str  # "content", "rename", "delete", "mode"
    ours_content: Optional[str] = None  # Content from target branch
    theirs_content: Optional[str] = None  # Content from incoming branch
    base_content: Optional[str] = None  # Content from common ancestor
    markers_start: Optional[int] = None  # Line number of <<<<<<< marker
    markers_end: Optional[int] = None  # Line number of >>>>>>> marker


@dataclass
class MergeResult:
    """Result of a merge operation."""

    status: MergeResultStatus
    success: bool
    conflicts: List[ConflictInfo] = field(default_factory=list)
    conflict_files: List[str] = field(default_factory=list)
    merged_commit: Optional[str] = None
    error_message: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None

    @property
    def has_conflicts(self) -> bool:
        return self.status == MergeResultStatus.CONFLICT

    @property
    def conflict_count(self) -> int:
        return len(self.conflict_files)


@dataclass
class DryRunResult:
    """Result of a dry-run merge check."""

    would_conflict: bool
    conflict_count: int
    conflict_files: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class SandboxGitOperations:
    """Git operations for merge and conflict resolution in sandboxes.

    This service executes git commands inside a Daytona sandbox to:
    - Check for merge conflicts (dry-run)
    - Perform actual merges
    - Extract conflict information for LLM resolution
    - Apply resolved content

    Usage:
        # During convergence merge
        git_ops = SandboxGitOperations(sandbox, workspace_path="/workspace/repo")

        # Check conflicts before merging
        dry_run = await git_ops.count_conflicts_dry_run("feature-branch")
        print(f"Would have {dry_run.conflict_count} conflicts")

        # Perform merge
        result = await git_ops.merge("feature-branch", no_commit=True)
        if result.has_conflicts:
            for conflict in result.conflicts:
                # LLM resolves each conflict
                resolved = await llm_resolver.resolve(conflict)
                await git_ops.write_file(conflict.file_path, resolved)
            await git_ops.commit_merge()
    """

    def __init__(
        self,
        sandbox: "Sandbox",
        workspace_path: str = "/workspace",
        timeout_seconds: int = 120,
    ):
        """Initialize git operations for a sandbox.

        Args:
            sandbox: Daytona sandbox instance
            workspace_path: Path to the git repository in the sandbox
            timeout_seconds: Default timeout for git commands
        """
        self.sandbox = sandbox
        self.workspace_path = workspace_path.rstrip("/")
        self.timeout = timeout_seconds
        logger.info(
            "sandbox_git_operations_initialized",
            extra={
                "sandbox_id": getattr(sandbox, "id", "unknown"),
                "workspace_path": self.workspace_path,
            },
        )

    def _exec(self, command: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Execute a command in the sandbox.

        Args:
            command: Command to execute
            timeout: Optional timeout override

        Returns:
            Dict with stdout, stderr, exit_code
        """
        full_command = f"cd {self.workspace_path} && {command}"
        actual_timeout = timeout or self.timeout

        try:
            result = self.sandbox.process.exec(full_command, timeout=actual_timeout)

            # Handle different result formats from Daytona SDK
            if hasattr(result, "output"):
                stdout = result.output
                stderr = getattr(result, "stderr", "")
                exit_code = getattr(result, "exit_code", 0)
            elif isinstance(result, str):
                stdout = result
                stderr = ""
                exit_code = 0
            else:
                stdout = str(result)
                stderr = ""
                exit_code = 0

            return {
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
            }
        except Exception as e:
            logger.warning(
                "sandbox_git_exec_error",
                extra={
                    "command": command[:100],
                    "error": str(e),
                },
            )
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": 1,
            }

    async def get_current_branch(self) -> str:
        """Get the current branch name.

        Returns:
            Name of the current branch
        """
        result = self._exec("git rev-parse --abbrev-ref HEAD")
        return result["stdout"].strip()

    async def get_current_commit(self) -> str:
        """Get the current commit SHA.

        Returns:
            Full commit SHA
        """
        result = self._exec("git rev-parse HEAD")
        return result["stdout"].strip()

    async def fetch(self, remote: str = "origin") -> bool:
        """Fetch from remote.

        Args:
            remote: Remote name to fetch from

        Returns:
            True if successful
        """
        result = self._exec(f"git fetch {remote}")
        return result["exit_code"] == 0

    async def count_conflicts_dry_run(self, branch: str) -> DryRunResult:
        """Count potential merge conflicts without actually merging.

        Uses `git merge-tree` (Git 2.38+) to do a dry-run merge and
        count conflicts. This is used for least-conflicts-first ordering.

        Args:
            branch: Branch to check for conflicts against current HEAD

        Returns:
            DryRunResult with conflict count and file list
        """
        # First, try git merge-tree (Git 2.38+, provides best results)
        # Syntax: git merge-tree --write-tree HEAD branch_name
        result = self._exec(f"git merge-tree --write-tree HEAD {branch} 2>&1 || true")

        # If merge-tree isn't available, fall back to checking merge
        if (
            "unknown option" in result["stderr"]
            or "not a git command" in result["stderr"]
        ):
            return await self._count_conflicts_fallback(branch)

        # Parse merge-tree output
        # If there are conflicts, output includes "CONFLICT" lines
        stdout = result["stdout"]
        conflict_files = []

        for line in stdout.split("\n"):
            if line.startswith("CONFLICT"):
                # Extract file path from conflict line
                # Format: "CONFLICT (content): Merge conflict in path/to/file"
                match = re.search(r"Merge conflict in (.+)$", line)
                if match:
                    conflict_files.append(match.group(1))
                else:
                    # Alternative format: "CONFLICT (modify/delete): file deleted in HEAD"
                    match = re.search(r"CONFLICT \([^)]+\): (.+)", line)
                    if match:
                        conflict_files.append(match.group(1).split()[0])

        return DryRunResult(
            would_conflict=len(conflict_files) > 0,
            conflict_count=len(conflict_files),
            conflict_files=conflict_files,
        )

    async def _count_conflicts_fallback(self, branch: str) -> DryRunResult:
        """Fallback conflict counting using merge --no-commit.

        Used when git merge-tree isn't available.

        Args:
            branch: Branch to check conflicts against

        Returns:
            DryRunResult with conflict information
        """
        # Stash any uncommitted changes first
        self._exec("git stash -q")

        try:
            # Attempt merge without committing
            result = self._exec(f"git merge --no-commit --no-ff {branch}")

            if result["exit_code"] == 0:
                # No conflicts - abort the merge
                self._exec("git merge --abort")
                return DryRunResult(
                    would_conflict=False,
                    conflict_count=0,
                    conflict_files=[],
                )

            # Check for conflicts
            status = self._exec("git diff --name-only --diff-filter=U")
            conflict_files = [
                f.strip() for f in status["stdout"].split("\n") if f.strip()
            ]

            # Abort the merge
            self._exec("git merge --abort")

            return DryRunResult(
                would_conflict=len(conflict_files) > 0,
                conflict_count=len(conflict_files),
                conflict_files=conflict_files,
            )
        finally:
            # Restore stashed changes
            self._exec("git stash pop -q 2>/dev/null || true")

    async def merge(
        self,
        branch: str,
        no_commit: bool = True,
        message: Optional[str] = None,
    ) -> MergeResult:
        """Perform a git merge.

        Args:
            branch: Branch to merge into current HEAD
            no_commit: If True, don't automatically commit (allows conflict resolution)
            message: Optional commit message (used when committing)

        Returns:
            MergeResult with success status and conflict details
        """
        # Build merge command
        cmd_parts = ["git", "merge"]
        if no_commit:
            cmd_parts.append("--no-commit")
        if message:
            cmd_parts.extend(["-m", f'"{message}"'])
        cmd_parts.append(branch)

        result = self._exec(" ".join(cmd_parts))

        # Check if merge was clean
        if result["exit_code"] == 0:
            # Get the merge commit if we committed
            merged_commit = None
            if not no_commit:
                commit_result = self._exec("git rev-parse HEAD")
                merged_commit = commit_result["stdout"].strip()

            return MergeResult(
                status=MergeResultStatus.SUCCESS,
                success=True,
                merged_commit=merged_commit,
                stdout=result["stdout"],
                stderr=result["stderr"],
            )

        # Merge has conflicts - gather conflict information
        conflict_files = await self._get_conflict_files()
        conflicts = await self._extract_conflicts(conflict_files)

        return MergeResult(
            status=MergeResultStatus.CONFLICT,
            success=False,
            conflicts=conflicts,
            conflict_files=conflict_files,
            stdout=result["stdout"],
            stderr=result["stderr"],
        )

    async def _get_conflict_files(self) -> List[str]:
        """Get list of files with merge conflicts.

        Returns:
            List of file paths with conflicts
        """
        result = self._exec("git diff --name-only --diff-filter=U")
        return [f.strip() for f in result["stdout"].split("\n") if f.strip()]

    async def _extract_conflicts(self, conflict_files: List[str]) -> List[ConflictInfo]:
        """Extract detailed conflict information from conflicted files.

        Args:
            conflict_files: List of files with conflicts

        Returns:
            List of ConflictInfo with content for LLM resolution
        """
        conflicts = []

        for file_path in conflict_files:
            # Read the conflicted file content
            result = self._exec(f"cat '{file_path}'")
            content = result["stdout"]

            # Parse conflict markers
            conflict_info = self._parse_conflict_markers(file_path, content)
            conflicts.append(conflict_info)

        return conflicts

    def _parse_conflict_markers(self, file_path: str, content: str) -> ConflictInfo:
        """Parse git conflict markers to extract ours/theirs content.

        Args:
            file_path: Path of the conflicted file
            content: Full file content with conflict markers

        Returns:
            ConflictInfo with extracted content
        """
        lines = content.split("\n")
        ours_lines = []
        theirs_lines = []
        base_lines = []

        in_conflict = False
        in_ours = False
        in_base = False
        in_theirs = False
        markers_start = None
        markers_end = None

        for i, line in enumerate(lines):
            if line.startswith("<<<<<<<"):
                in_conflict = True
                in_ours = True
                markers_start = i
            elif line.startswith("|||||||"):
                in_ours = False
                in_base = True
            elif line.startswith("======="):
                in_ours = False
                in_base = False
                in_theirs = True
            elif line.startswith(">>>>>>>"):
                in_conflict = False
                in_theirs = False
                markers_end = i
            elif in_conflict:
                if in_ours:
                    ours_lines.append(line)
                elif in_base:
                    base_lines.append(line)
                elif in_theirs:
                    theirs_lines.append(line)

        return ConflictInfo(
            file_path=file_path,
            conflict_type="content",
            ours_content="\n".join(ours_lines) if ours_lines else None,
            theirs_content="\n".join(theirs_lines) if theirs_lines else None,
            base_content="\n".join(base_lines) if base_lines else None,
            markers_start=markers_start,
            markers_end=markers_end,
        )

    async def get_conflict_content(self, file_path: str) -> ConflictInfo:
        """Get detailed conflict information for a specific file.

        Args:
            file_path: Path to the conflicted file

        Returns:
            ConflictInfo with ours/theirs/base content
        """
        result = self._exec(f"cat '{file_path}'")
        return self._parse_conflict_markers(file_path, result["stdout"])

    async def write_file(self, file_path: str, content: str) -> bool:
        """Write resolved content to a file.

        Args:
            file_path: Path to the file
            content: Resolved content to write

        Returns:
            True if successful
        """
        # Escape content for shell
        escaped_content = content.replace("'", "'\\''")
        result = self._exec(
            f"cat > '{file_path}' << 'RESOLVED_EOF'\n{escaped_content}\nRESOLVED_EOF"
        )
        return result["exit_code"] == 0

    async def stage_file(self, file_path: str) -> bool:
        """Stage a file for commit.

        Args:
            file_path: Path to the file to stage

        Returns:
            True if successful
        """
        result = self._exec(f"git add '{file_path}'")
        return result["exit_code"] == 0

    async def commit_merge(self, message: Optional[str] = None) -> Optional[str]:
        """Complete a merge by committing.

        Args:
            message: Optional commit message

        Returns:
            Commit SHA if successful, None otherwise
        """
        cmd = "git commit"
        if message:
            cmd += f' -m "{message}"'
        else:
            cmd += " --no-edit"

        result = self._exec(cmd)
        if result["exit_code"] != 0:
            return None

        # Get the commit SHA
        commit_result = self._exec("git rev-parse HEAD")
        return commit_result["stdout"].strip()

    async def merge_abort(self) -> bool:
        """Abort an in-progress merge.

        Returns:
            True if successful
        """
        result = self._exec("git merge --abort")
        return result["exit_code"] == 0

    async def rebase(
        self,
        onto: str,
        interactive: bool = False,
    ) -> MergeResult:
        """Rebase current branch onto another.

        Args:
            onto: Branch or commit to rebase onto
            interactive: Whether to use interactive rebase (not recommended for automation)

        Returns:
            MergeResult with success status
        """
        cmd = f"git rebase {onto}"

        result = self._exec(cmd)

        if result["exit_code"] == 0:
            return MergeResult(
                status=MergeResultStatus.SUCCESS,
                success=True,
                stdout=result["stdout"],
                stderr=result["stderr"],
            )

        # Check for conflicts
        conflict_files = await self._get_conflict_files()

        return MergeResult(
            status=MergeResultStatus.CONFLICT,
            success=False,
            conflict_files=conflict_files,
            stdout=result["stdout"],
            stderr=result["stderr"],
        )

    async def rebase_abort(self) -> bool:
        """Abort an in-progress rebase.

        Returns:
            True if successful
        """
        result = self._exec("git rebase --abort")
        return result["exit_code"] == 0

    async def rebase_continue(self) -> bool:
        """Continue a rebase after resolving conflicts.

        Returns:
            True if successful
        """
        result = self._exec("git rebase --continue")
        return result["exit_code"] == 0

    async def push(
        self,
        remote: str = "origin",
        branch: Optional[str] = None,
        force: bool = False,
    ) -> bool:
        """Push to remote.

        Args:
            remote: Remote name
            branch: Branch name (defaults to current)
            force: Whether to force push

        Returns:
            True if successful
        """
        cmd_parts = ["git", "push", remote]
        if branch:
            cmd_parts.append(branch)
        if force:
            cmd_parts.append("--force-with-lease")

        result = self._exec(" ".join(cmd_parts))
        return result["exit_code"] == 0

    async def get_diff_stat(
        self,
        base: str = "HEAD~1",
        target: str = "HEAD",
    ) -> Dict[str, Any]:
        """Get diff statistics between two commits.

        Args:
            base: Base commit/branch
            target: Target commit/branch

        Returns:
            Dict with files_changed, insertions, deletions
        """
        result = self._exec(f"git diff --stat {base}..{target}")

        # Parse the last line for summary
        lines = result["stdout"].strip().split("\n")
        if not lines:
            return {"files_changed": 0, "insertions": 0, "deletions": 0}

        summary = lines[-1]
        files_match = re.search(r"(\d+) files? changed", summary)
        insert_match = re.search(r"(\d+) insertions?", summary)
        delete_match = re.search(r"(\d+) deletions?", summary)

        return {
            "files_changed": int(files_match.group(1)) if files_match else 0,
            "insertions": int(insert_match.group(1)) if insert_match else 0,
            "deletions": int(delete_match.group(1)) if delete_match else 0,
        }
