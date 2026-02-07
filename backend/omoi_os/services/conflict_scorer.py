"""Conflict Scorer Service for least-conflicts-first merge ordering.

Phase B: Conflict scoring for DAG Merge Executor integration.

This service scores branches/commits by their potential conflict count,
enabling the ConvergenceMergeService to merge in optimal order:
- Branches with fewer conflicts are merged first
- This minimizes the total number of conflicts to resolve
- Reduces the work for LLM conflict resolution

The scoring uses git merge-tree dry-run to count potential conflicts
without actually performing the merge.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

from omoi_os.logging import get_logger
from omoi_os.services.sandbox_git_operations import SandboxGitOperations

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


@dataclass
class BranchScore:
    """Score for a single branch's merge potential."""

    branch: str
    task_id: Optional[str] = None
    conflict_count: int = 0
    conflict_files: List[str] = field(default_factory=list)
    score_error: Optional[str] = None

    @property
    def has_conflicts(self) -> bool:
        return self.conflict_count > 0

    @property
    def is_clean(self) -> bool:
        return self.conflict_count == 0 and self.score_error is None


@dataclass
class ScoredMergeOrder:
    """Result of scoring and ordering branches for merge."""

    scores: Dict[str, BranchScore]  # branch/task_id -> score
    merge_order: List[str]  # Ordered list (least conflicts first)
    total_conflicts: int
    clean_count: int  # Number of branches with no conflicts
    failed_count: int  # Number that couldn't be scored

    @property
    def all_clean(self) -> bool:
        return self.total_conflicts == 0 and self.failed_count == 0


class ConflictScorer:
    """Scores branches by conflict count for optimal merge ordering.

    The least-conflicts-first strategy works because:
    1. Merging a clean branch doesn't create conflicts
    2. After merging, that code is now in the base
    3. The next branch's conflicts are now against the combined base
    4. Starting with clean merges builds up the base incrementally

    Usage:
        scorer = ConflictScorer(git_ops)

        # Score multiple branches/tasks
        result = await scorer.score_branches(
            base_branch="ticket/TKT-001",
            branches=["task-001", "task-002", "task-003"],
        )

        # Get optimal merge order
        for branch in result.merge_order:
            score = result.scores[branch]
            print(f"{branch}: {score.conflict_count} conflicts")
    """

    def __init__(
        self,
        git_ops: SandboxGitOperations,
    ):
        """Initialize the conflict scorer.

        Args:
            git_ops: SandboxGitOperations instance for running git commands
        """
        self.git_ops = git_ops
        logger.info("conflict_scorer_initialized")

    async def score_branch(
        self,
        branch: str,
        task_id: Optional[str] = None,
    ) -> BranchScore:
        """Score a single branch for merge conflicts.

        Args:
            branch: Branch name to score
            task_id: Optional task ID associated with this branch

        Returns:
            BranchScore with conflict information
        """
        try:
            dry_run = await self.git_ops.count_conflicts_dry_run(branch)

            score = BranchScore(
                branch=branch,
                task_id=task_id,
                conflict_count=dry_run.conflict_count,
                conflict_files=dry_run.conflict_files,
            )

            logger.debug(
                "branch_scored",
                extra={
                    "branch": branch,
                    "task_id": task_id,
                    "conflict_count": dry_run.conflict_count,
                    "conflict_files": dry_run.conflict_files[:5],  # Log first 5
                },
            )

            return score

        except Exception as e:
            logger.warning(
                "branch_score_failed",
                extra={
                    "branch": branch,
                    "task_id": task_id,
                    "error": str(e),
                },
            )
            return BranchScore(
                branch=branch,
                task_id=task_id,
                conflict_count=999,  # High score for errors (merge last)
                score_error=str(e),
            )

    async def score_branches(
        self,
        base_branch: str,
        branches: List[str],
        task_ids: Optional[Dict[str, str]] = None,
    ) -> ScoredMergeOrder:
        """Score multiple branches and return optimal merge order.

        Args:
            base_branch: The target branch to merge into (checkout first)
            branches: List of branches to score
            task_ids: Optional mapping of branch -> task_id

        Returns:
            ScoredMergeOrder with scores and optimal merge order
        """
        task_ids = task_ids or {}
        scores: Dict[str, BranchScore] = {}

        # Ensure we're on the base branch
        current = await self.git_ops.get_current_branch()
        if current != base_branch:
            # Fetch and checkout base branch
            await self.git_ops.fetch()
            checkout_result = self.git_ops._exec(f"git checkout {base_branch}")
            if checkout_result["exit_code"] != 0:
                logger.warning(
                    "base_branch_checkout_failed",
                    extra={
                        "base_branch": base_branch,
                        "error": checkout_result["stderr"],
                    },
                )

        # Score each branch
        for branch in branches:
            task_id = task_ids.get(branch)
            score = await self.score_branch(branch, task_id)
            scores[branch] = score

        # Sort by conflict count (ascending) for least-conflicts-first
        sorted_branches = sorted(
            branches,
            key=lambda b: (
                scores[b].score_error is not None,  # Errors go last
                scores[b].conflict_count,
            ),
        )

        # Calculate summary stats
        total_conflicts = sum(
            s.conflict_count for s in scores.values() if not s.score_error
        )
        clean_count = sum(1 for s in scores.values() if s.is_clean)
        failed_count = sum(1 for s in scores.values() if s.score_error)

        logger.info(
            "branches_scored",
            extra={
                "base_branch": base_branch,
                "branch_count": len(branches),
                "total_conflicts": total_conflicts,
                "clean_count": clean_count,
                "failed_count": failed_count,
                "merge_order": sorted_branches,
            },
        )

        return ScoredMergeOrder(
            scores=scores,
            merge_order=sorted_branches,
            total_conflicts=total_conflicts,
            clean_count=clean_count,
            failed_count=failed_count,
        )

    async def score_task_commits(
        self,
        base_branch: str,
        task_commits: Dict[str, str],
    ) -> ScoredMergeOrder:
        """Score tasks by their commit's merge potential.

        This is used when all tasks work on the same branch (ticket-level branching)
        but we want to order the merging of their commits.

        Args:
            base_branch: The target branch
            task_commits: Mapping of task_id -> commit SHA

        Returns:
            ScoredMergeOrder with task_ids as keys
        """
        scores: Dict[str, BranchScore] = {}

        # Ensure we're on the base branch
        current = await self.git_ops.get_current_branch()
        if current != base_branch:
            await self.git_ops.fetch()
            self.git_ops._exec(f"git checkout {base_branch}")

        # Score each task's commit
        for task_id, commit_sha in task_commits.items():
            try:
                dry_run = await self.git_ops.count_conflicts_dry_run(commit_sha)

                scores[task_id] = BranchScore(
                    branch=commit_sha,
                    task_id=task_id,
                    conflict_count=dry_run.conflict_count,
                    conflict_files=dry_run.conflict_files,
                )

            except Exception as e:
                logger.warning(
                    "task_commit_score_failed",
                    extra={
                        "task_id": task_id,
                        "commit": commit_sha[:8],
                        "error": str(e),
                    },
                )
                scores[task_id] = BranchScore(
                    branch=commit_sha,
                    task_id=task_id,
                    conflict_count=999,
                    score_error=str(e),
                )

        # Sort by conflict count
        sorted_task_ids = sorted(
            task_commits.keys(),
            key=lambda t: (
                scores[t].score_error is not None,
                scores[t].conflict_count,
            ),
        )

        total_conflicts = sum(
            s.conflict_count for s in scores.values() if not s.score_error
        )
        clean_count = sum(1 for s in scores.values() if s.is_clean)
        failed_count = sum(1 for s in scores.values() if s.score_error)

        logger.info(
            "task_commits_scored",
            extra={
                "base_branch": base_branch,
                "task_count": len(task_commits),
                "total_conflicts": total_conflicts,
                "clean_count": clean_count,
                "merge_order": sorted_task_ids,
            },
        )

        return ScoredMergeOrder(
            scores=scores,
            merge_order=sorted_task_ids,
            total_conflicts=total_conflicts,
            clean_count=clean_count,
            failed_count=failed_count,
        )

    async def estimate_merge_complexity(
        self,
        scored_order: ScoredMergeOrder,
    ) -> Dict[str, any]:
        """Estimate the complexity of merging all branches.

        Provides metrics useful for deciding whether to:
        - Proceed with automated merge
        - Request human review
        - Adjust the merge strategy

        Args:
            scored_order: Result from score_branches()

        Returns:
            Dict with complexity metrics
        """
        total_files = set()
        max_conflicts_single = 0
        conflict_file_overlap = 0

        for score in scored_order.scores.values():
            total_files.update(score.conflict_files)
            max_conflicts_single = max(max_conflicts_single, score.conflict_count)

        # Check for overlapping conflict files (same file conflicts in multiple branches)
        file_counts: Dict[str, int] = {}
        for score in scored_order.scores.values():
            for f in score.conflict_files:
                file_counts[f] = file_counts.get(f, 0) + 1

        conflict_file_overlap = sum(1 for count in file_counts.values() if count > 1)

        complexity = {
            "total_unique_conflict_files": len(total_files),
            "total_conflicts_across_branches": scored_order.total_conflicts,
            "max_conflicts_single_branch": max_conflicts_single,
            "conflict_file_overlap": conflict_file_overlap,
            "clean_branches": scored_order.clean_count,
            "problematic_branches": scored_order.failed_count,
            "estimated_llm_calls": scored_order.total_conflicts,  # One call per conflict
            "complexity_score": self._calculate_complexity_score(
                scored_order.total_conflicts,
                len(total_files),
                conflict_file_overlap,
            ),
        }

        logger.info(
            "merge_complexity_estimated",
            extra=complexity,
        )

        return complexity

    def _calculate_complexity_score(
        self,
        total_conflicts: int,
        unique_files: int,
        overlap: int,
    ) -> str:
        """Calculate a simple complexity rating.

        Args:
            total_conflicts: Total number of conflicts
            unique_files: Number of unique conflicting files
            overlap: Number of files with multiple conflicts

        Returns:
            Complexity rating: "low", "medium", "high", "very_high"
        """
        if total_conflicts == 0:
            return "none"
        elif total_conflicts <= 3 and unique_files <= 2 and overlap == 0:
            return "low"
        elif total_conflicts <= 10 and overlap <= 2:
            return "medium"
        elif total_conflicts <= 25:
            return "high"
        else:
            return "very_high"
