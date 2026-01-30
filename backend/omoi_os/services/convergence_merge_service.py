"""Convergence Merge Service for parallel task code synthesis.

Phase C: Orchestrates merge at convergence points in the task DAG.

This service handles the code synthesis problem: when parallel tasks complete
and a continuation task depends on all of them, their code changes must be
merged into the ticket branch before the continuation task can start.

The service:
1. Listens for synthesis completion events (all parallel sources complete)
2. Scores branches by conflict count (least-conflicts-first)
3. Merges in optimal order to minimize conflicts
4. Delegates conflict resolution to AgentConflictResolver (Claude Agent SDK)
5. Records all merge attempts in MergeAttempt for audit trail

Architecture:
- Integrates with SynthesisService (receives synthesis.completed events)
- Uses SandboxGitOperations for git commands
- Uses ConflictScorer for merge ordering
- Uses AgentConflictResolver for LLM-based conflict resolution
- Creates MergeAttempt records for audit trail
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

from omoi_os.logging import get_logger
from omoi_os.models.merge_attempt import MergeAttempt, MergeStatus
from omoi_os.services.conflict_scorer import ConflictScorer, ScoredMergeOrder
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.sandbox_git_operations import (
    SandboxGitOperations,
    MergeResult,
    MergeResultStatus,
    ConflictInfo,
)
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from daytona_sdk import Sandbox
    from omoi_os.services.agent_conflict_resolver import AgentConflictResolver

logger = get_logger(__name__)


@dataclass
class ConvergenceMergeConfig:
    """Configuration for convergence merge."""
    max_conflicts_auto_resolve: int = 10     # Max conflicts before requiring manual review
    max_llm_invocations: int = 20            # Max LLM calls per merge attempt
    conflict_timeout_seconds: int = 300       # Timeout for conflict resolution
    enable_auto_push: bool = False            # Push after successful merge
    require_clean_merge: bool = False         # Fail if any conflicts (no LLM resolution)


@dataclass
class ConvergenceMergeResult:
    """Result of a convergence merge operation."""
    success: bool
    merge_attempt_id: str
    merged_tasks: List[str]
    failed_tasks: List[str]
    total_conflicts_resolved: int
    llm_invocations: int
    error_message: Optional[str] = None

    @property
    def all_merged(self) -> bool:
        return self.success and len(self.failed_tasks) == 0


class ConvergenceMergeService:
    """Orchestrates code merging at convergence points.

    This is the main service for the DAG Merge Executor pattern.
    It coordinates the merging of parallel task code changes using
    the least-conflicts-first strategy.

    Usage:
        merge_service = ConvergenceMergeService(db, event_bus)

        # Subscribe to synthesis events
        merge_service.subscribe_to_events()

        # Or manually trigger merge for a convergence point
        result = await merge_service.merge_at_convergence(
            continuation_task_id="task-005",
            source_task_ids=["task-001", "task-002", "task-003"],
            ticket_id="ticket-001",
            sandbox=sandbox_instance,
        )
    """

    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
        config: Optional[ConvergenceMergeConfig] = None,
        conflict_resolver: Optional["AgentConflictResolver"] = None,
    ):
        """Initialize the convergence merge service.

        Args:
            db: Database service for persistence
            event_bus: Event bus for subscribing to synthesis events
            config: Configuration options
            conflict_resolver: Optional AgentConflictResolver for LLM resolution
        """
        self.db = db
        self.event_bus = event_bus
        self.config = config or ConvergenceMergeConfig()
        self.conflict_resolver = conflict_resolver

        logger.info(
            "convergence_merge_service_initialized",
            extra={
                "max_conflicts_auto": self.config.max_conflicts_auto_resolve,
                "has_conflict_resolver": conflict_resolver is not None,
            },
        )

    def subscribe_to_events(self) -> None:
        """Subscribe to synthesis completion events."""
        if not self.event_bus:
            logger.warning("convergence_merge_no_event_bus")
            return

        self.event_bus.subscribe(
            "coordination.synthesis.completed",
            self._handle_synthesis_completed,
        )
        logger.info("convergence_merge_subscribed_to_synthesis_events")

    def _handle_synthesis_completed(self, event_data: Dict[str, Any]) -> None:
        """Handle synthesis completion events.

        When synthesis completes (all parallel task results merged),
        this triggers the code merge if needed.

        Args:
            event_data: Event payload from SynthesisService
        """
        payload = event_data.get("payload", {})
        continuation_task_id = payload.get("continuation_task_id")
        source_task_ids = payload.get("source_task_ids", [])
        ticket_id = payload.get("ticket_id")

        if not continuation_task_id or not source_task_ids:
            logger.debug(
                "synthesis_completed_no_merge_needed",
                extra={"event_data": event_data},
            )
            return

        logger.info(
            "synthesis_completed_triggering_merge",
            extra={
                "continuation_task_id": continuation_task_id,
                "source_task_ids": source_task_ids,
                "ticket_id": ticket_id,
            },
        )

        # Note: The actual merge happens when the sandbox is spawned
        # This is because we need an active sandbox to run git commands
        # The merge_at_convergence method is called by DaytonaSpawner

    async def merge_at_convergence(
        self,
        continuation_task_id: str,
        source_task_ids: List[str],
        ticket_id: str,
        sandbox: "Sandbox",
        spec_id: Optional[str] = None,
        workspace_path: str = "/workspace",
        target_branch: Optional[str] = None,
    ) -> ConvergenceMergeResult:
        """Merge code changes from parallel tasks at a convergence point.

        This is the main entry point for convergence merging. It:
        1. Creates a MergeAttempt record
        2. Scores branches for conflict ordering
        3. Merges in least-conflicts-first order
        4. Resolves conflicts via LLM if needed
        5. Updates the MergeAttempt with results

        Args:
            continuation_task_id: Task that depends on all source tasks
            source_task_ids: List of parallel task IDs to merge
            ticket_id: Ticket ID for branch naming
            sandbox: Daytona sandbox with the git repository
            spec_id: Optional spec ID for audit trail
            workspace_path: Path to git repo in sandbox
            target_branch: Branch to merge into (defaults to ticket branch)

        Returns:
            ConvergenceMergeResult with merge outcome
        """
        # Create MergeAttempt record
        merge_attempt = self._create_merge_attempt(
            continuation_task_id=continuation_task_id,
            source_task_ids=source_task_ids,
            ticket_id=ticket_id,
            spec_id=spec_id,
            target_branch=target_branch or f"ticket/{ticket_id}",
        )

        # Initialize git operations
        git_ops = SandboxGitOperations(
            sandbox=sandbox,
            workspace_path=workspace_path,
        )

        try:
            # Update status to in_progress
            self._update_merge_attempt_status(merge_attempt.id, MergeStatus.IN_PROGRESS)

            # Score branches for optimal merge order
            scorer = ConflictScorer(git_ops)
            scored_order = await self._score_source_tasks(
                scorer=scorer,
                source_task_ids=source_task_ids,
                target_branch=merge_attempt.target_branch,
            )

            # Update merge attempt with scoring results
            self._update_merge_attempt_scoring(
                merge_attempt.id,
                scored_order,
            )

            # Check if conflicts exceed auto-resolve threshold
            if scored_order.total_conflicts > self.config.max_conflicts_auto_resolve:
                if self.config.require_clean_merge:
                    return self._fail_merge(
                        merge_attempt.id,
                        f"Too many conflicts ({scored_order.total_conflicts}) for auto-resolve",
                        source_task_ids,
                    )
                else:
                    # Flag for manual review
                    self._update_merge_attempt_status(merge_attempt.id, MergeStatus.MANUAL)
                    logger.warning(
                        "convergence_merge_needs_manual_review",
                        extra={
                            "merge_attempt_id": merge_attempt.id,
                            "total_conflicts": scored_order.total_conflicts,
                            "threshold": self.config.max_conflicts_auto_resolve,
                        },
                    )
                    return ConvergenceMergeResult(
                        success=False,
                        merge_attempt_id=merge_attempt.id,
                        merged_tasks=[],
                        failed_tasks=source_task_ids,
                        total_conflicts_resolved=0,
                        llm_invocations=0,
                        error_message="Manual review required due to high conflict count",
                    )

            # Merge in least-conflicts-first order
            result = await self._merge_in_order(
                merge_attempt_id=merge_attempt.id,
                git_ops=git_ops,
                scored_order=scored_order,
                target_branch=merge_attempt.target_branch,
            )

            # Push if configured
            if result.success and self.config.enable_auto_push:
                await git_ops.push()

            return result

        except Exception as e:
            logger.error(
                "convergence_merge_error",
                extra={
                    "merge_attempt_id": merge_attempt.id,
                    "error": str(e),
                },
                exc_info=True,
            )
            return self._fail_merge(
                merge_attempt.id,
                str(e),
                source_task_ids,
            )

    async def _score_source_tasks(
        self,
        scorer: ConflictScorer,
        source_task_ids: List[str],
        target_branch: str,
    ) -> ScoredMergeOrder:
        """Score source tasks for merge ordering.

        For ticket-level branching, we score each task's commits
        against the target branch.

        Args:
            scorer: ConflictScorer instance
            source_task_ids: Task IDs to score
            target_branch: Branch to merge into

        Returns:
            ScoredMergeOrder with optimal merge order
        """
        # Get commit SHAs for each task
        # For now, we use task IDs as branch refs (they may be commits or branches)
        # In ticket-level branching, these would be commits on the same branch
        task_commits = {task_id: task_id for task_id in source_task_ids}

        # In a full implementation, we'd fetch the actual commit SHAs from the database
        # or from the sandbox's git log

        return await scorer.score_task_commits(
            base_branch=target_branch,
            task_commits=task_commits,
        )

    async def _merge_in_order(
        self,
        merge_attempt_id: str,
        git_ops: SandboxGitOperations,
        scored_order: ScoredMergeOrder,
        target_branch: str,
    ) -> ConvergenceMergeResult:
        """Merge tasks in least-conflicts-first order.

        Args:
            merge_attempt_id: ID of the merge attempt record
            git_ops: SandboxGitOperations for git commands
            scored_order: Scored and ordered tasks
            target_branch: Target branch for merging

        Returns:
            ConvergenceMergeResult with outcome
        """
        merged_tasks: List[str] = []
        failed_tasks: List[str] = []
        total_conflicts_resolved = 0
        llm_invocations = 0

        for task_id in scored_order.merge_order:
            score = scored_order.scores[task_id]

            # Skip tasks that couldn't be scored
            if score.score_error:
                logger.warning(
                    "skipping_unscored_task",
                    extra={"task_id": task_id, "error": score.score_error},
                )
                failed_tasks.append(task_id)
                continue

            # For ticket-level branching with sequential commits,
            # we may not need to merge if commits are already in sequence
            if score.is_clean:
                merged_tasks.append(task_id)
                continue

            # Perform merge
            result = await git_ops.merge(
                branch=score.branch,
                no_commit=True,
            )

            if result.success:
                # Commit the merge
                await git_ops.commit_merge(
                    message=f"Merge task {task_id[:8]} (convergence point)"
                )
                merged_tasks.append(task_id)

            elif result.has_conflicts:
                # Try to resolve conflicts
                if self.conflict_resolver and llm_invocations < self.config.max_llm_invocations:
                    resolved, invocations = await self._resolve_conflicts(
                        git_ops=git_ops,
                        conflicts=result.conflicts,
                        task_id=task_id,
                        merge_attempt_id=merge_attempt_id,
                    )
                    llm_invocations += invocations

                    if resolved:
                        # Commit after resolution
                        await git_ops.commit_merge(
                            message=f"Merge task {task_id[:8]} with LLM conflict resolution"
                        )
                        merged_tasks.append(task_id)
                        total_conflicts_resolved += result.conflict_count
                    else:
                        await git_ops.merge_abort()
                        failed_tasks.append(task_id)
                else:
                    # No resolver or exceeded invocation limit
                    await git_ops.merge_abort()
                    failed_tasks.append(task_id)
                    logger.warning(
                        "merge_conflicts_unresolved",
                        extra={
                            "task_id": task_id,
                            "conflict_count": result.conflict_count,
                            "has_resolver": self.conflict_resolver is not None,
                            "llm_invocations": llm_invocations,
                        },
                    )
            else:
                # Merge failed for other reasons
                await git_ops.merge_abort()
                failed_tasks.append(task_id)
                logger.error(
                    "merge_failed",
                    extra={
                        "task_id": task_id,
                        "error": result.error_message,
                    },
                )

        # Update merge attempt with final results
        success = len(failed_tasks) == 0
        self._finalize_merge_attempt(
            merge_attempt_id=merge_attempt_id,
            success=success,
            llm_invocations=llm_invocations,
            total_conflicts=total_conflicts_resolved,
        )

        return ConvergenceMergeResult(
            success=success,
            merge_attempt_id=merge_attempt_id,
            merged_tasks=merged_tasks,
            failed_tasks=failed_tasks,
            total_conflicts_resolved=total_conflicts_resolved,
            llm_invocations=llm_invocations,
        )

    async def _resolve_conflicts(
        self,
        git_ops: SandboxGitOperations,
        conflicts: List[ConflictInfo],
        task_id: str,
        merge_attempt_id: str,
    ) -> tuple[bool, int]:
        """Resolve conflicts using LLM conflict resolver.

        Args:
            git_ops: Git operations instance
            conflicts: List of conflicts to resolve
            task_id: Task ID for context
            merge_attempt_id: Merge attempt ID for logging

        Returns:
            Tuple of (success, invocation_count)
        """
        if not self.conflict_resolver:
            return False, 0

        invocations = 0
        all_resolved = True

        for conflict in conflicts:
            try:
                # Call LLM resolver
                resolved_content = await self.conflict_resolver.resolve_conflict(
                    file_path=conflict.file_path,
                    ours_content=conflict.ours_content or "",
                    theirs_content=conflict.theirs_content or "",
                    base_content=conflict.base_content,
                    task_id=task_id,
                )
                invocations += 1

                if resolved_content:
                    # Write resolved content
                    await git_ops.write_file(conflict.file_path, resolved_content)
                    await git_ops.stage_file(conflict.file_path)

                    # Log resolution for audit
                    self._log_resolution(
                        merge_attempt_id=merge_attempt_id,
                        file_path=conflict.file_path,
                        resolved_content=resolved_content,
                    )
                else:
                    all_resolved = False
                    logger.warning(
                        "conflict_resolution_empty",
                        extra={
                            "file_path": conflict.file_path,
                            "task_id": task_id,
                        },
                    )

            except Exception as e:
                all_resolved = False
                logger.error(
                    "conflict_resolution_error",
                    extra={
                        "file_path": conflict.file_path,
                        "error": str(e),
                    },
                )

        return all_resolved, invocations

    def _create_merge_attempt(
        self,
        continuation_task_id: str,
        source_task_ids: List[str],
        ticket_id: str,
        spec_id: Optional[str],
        target_branch: str,
    ) -> MergeAttempt:
        """Create a MergeAttempt record in the database.

        Args:
            continuation_task_id: Task that triggered this merge
            source_task_ids: Tasks being merged
            ticket_id: Ticket ID
            spec_id: Optional spec ID
            target_branch: Target branch for merge

        Returns:
            Created MergeAttempt instance
        """
        with self.db.get_session() as session:
            merge_attempt = MergeAttempt(
                id=str(uuid4()),
                task_id=continuation_task_id,
                ticket_id=ticket_id,
                spec_id=spec_id,
                source_task_ids=source_task_ids,
                target_branch=target_branch,
                status=MergeStatus.PENDING.value,
            )
            session.add(merge_attempt)
            session.commit()

            logger.info(
                "merge_attempt_created",
                extra={
                    "merge_attempt_id": merge_attempt.id,
                    "continuation_task_id": continuation_task_id,
                    "source_count": len(source_task_ids),
                },
            )

            return merge_attempt

    def _update_merge_attempt_status(
        self,
        merge_attempt_id: str,
        status: MergeStatus,
    ) -> None:
        """Update merge attempt status."""
        with self.db.get_session() as session:
            attempt = session.query(MergeAttempt).filter(
                MergeAttempt.id == merge_attempt_id
            ).first()
            if attempt:
                attempt.status = status.value
                if status == MergeStatus.IN_PROGRESS:
                    attempt.started_at = utc_now()
                session.commit()

    def _update_merge_attempt_scoring(
        self,
        merge_attempt_id: str,
        scored_order: ScoredMergeOrder,
    ) -> None:
        """Update merge attempt with conflict scoring results."""
        with self.db.get_session() as session:
            attempt = session.query(MergeAttempt).filter(
                MergeAttempt.id == merge_attempt_id
            ).first()
            if attempt:
                attempt.merge_order = scored_order.merge_order
                attempt.conflict_scores = {
                    task_id: {
                        "count": score.conflict_count,
                        "files": score.conflict_files,
                        "error": score.score_error,
                    }
                    for task_id, score in scored_order.scores.items()
                }
                attempt.total_conflicts = scored_order.total_conflicts
                session.commit()

    def _finalize_merge_attempt(
        self,
        merge_attempt_id: str,
        success: bool,
        llm_invocations: int,
        total_conflicts: int,
    ) -> None:
        """Finalize merge attempt with results."""
        with self.db.get_session() as session:
            attempt = session.query(MergeAttempt).filter(
                MergeAttempt.id == merge_attempt_id
            ).first()
            if attempt:
                attempt.success = success
                attempt.status = (
                    MergeStatus.COMPLETED.value if success
                    else MergeStatus.FAILED.value
                )
                attempt.llm_invocations = llm_invocations
                attempt.total_conflicts = total_conflicts
                attempt.completed_at = utc_now()
                session.commit()

    def _log_resolution(
        self,
        merge_attempt_id: str,
        file_path: str,
        resolved_content: str,
    ) -> None:
        """Log LLM resolution for audit trail."""
        with self.db.get_session() as session:
            attempt = session.query(MergeAttempt).filter(
                MergeAttempt.id == merge_attempt_id
            ).first()
            if attempt:
                if not attempt.llm_resolution_log:
                    attempt.llm_resolution_log = {}
                attempt.llm_resolution_log[file_path] = {
                    "resolved_at": utc_now().isoformat(),
                    "content_length": len(resolved_content),
                }
                session.commit()

    def _fail_merge(
        self,
        merge_attempt_id: str,
        error_message: str,
        source_task_ids: List[str],
    ) -> ConvergenceMergeResult:
        """Record merge failure."""
        with self.db.get_session() as session:
            attempt = session.query(MergeAttempt).filter(
                MergeAttempt.id == merge_attempt_id
            ).first()
            if attempt:
                attempt.success = False
                attempt.status = MergeStatus.FAILED.value
                attempt.error_message = error_message
                attempt.completed_at = utc_now()
                session.commit()

        return ConvergenceMergeResult(
            success=False,
            merge_attempt_id=merge_attempt_id,
            merged_tasks=[],
            failed_tasks=source_task_ids,
            total_conflicts_resolved=0,
            llm_invocations=0,
            error_message=error_message,
        )


# Singleton management
_convergence_merge_service: Optional[ConvergenceMergeService] = None


def get_convergence_merge_service(
    db: Optional[DatabaseService] = None,
    event_bus: Optional[EventBusService] = None,
    config: Optional[ConvergenceMergeConfig] = None,
    conflict_resolver: Optional["AgentConflictResolver"] = None,
) -> ConvergenceMergeService:
    """Get or create the ConvergenceMergeService singleton.

    Args:
        db: Database service (required on first call)
        event_bus: Event bus for event subscription
        config: Configuration options
        conflict_resolver: LLM conflict resolver

    Returns:
        ConvergenceMergeService instance
    """
    global _convergence_merge_service

    if _convergence_merge_service is None:
        if db is None:
            raise ValueError("db is required on first call to get_convergence_merge_service")
        _convergence_merge_service = ConvergenceMergeService(
            db=db,
            event_bus=event_bus,
            config=config,
            conflict_resolver=conflict_resolver,
        )

    return _convergence_merge_service


def reset_convergence_merge_service() -> None:
    """Reset the singleton (for testing)."""
    global _convergence_merge_service
    _convergence_merge_service = None
