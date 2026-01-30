"""Synthesis Service for parallel task result merging.

This service orchestrates result synthesis when sync points (joins) become ready.
It automatically triggers merge_task_results() when all parallel source tasks complete,
then injects the merged context into the continuation task.

The synthesis workflow:
1. CoordinationService creates a join via join_tasks()
2. SynthesisService registers the join by listening to coordination.join.created events
3. When each source task completes (TASK_COMPLETED event), SynthesisService checks if all sources are done
4. When ready, it merges results and injects into the continuation task's synthesis_context field
5. The continuation task can then access the merged parallel results when it executes

This addresses the gap where merge_task_results() existed but was never called in production.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from functools import lru_cache

from omoi_os.logging import get_logger
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent

logger = get_logger(__name__)


@dataclass
class PendingJoin:
    """Configuration for a pending join that needs synthesis when ready."""

    join_id: str
    source_task_ids: List[str]
    continuation_task_id: str
    merge_strategy: str = "combine"
    completed_source_ids: List[str] = field(default_factory=list)

    def is_ready(self) -> bool:
        """Check if all source tasks have completed."""
        return set(self.source_task_ids) == set(self.completed_source_ids)


class SynthesisService:
    """Orchestrates result synthesis when sync points (joins) become ready.

    This service bridges the gap between coordination primitives and actual
    result merging. It:
    - Tracks pending joins created by CoordinationService
    - Listens for task completion events
    - Triggers merge when all sources complete
    - Injects merged context into continuation tasks

    Usage:
        synthesis_service = SynthesisService(db, coordination, event_bus)
        synthesis_service.subscribe_to_events()

        # Now when parallel tasks complete, their results are automatically
        # merged and injected into continuation tasks
    """

    def __init__(
        self,
        db: DatabaseService,
        event_bus: EventBusService,
    ):
        """Initialize the synthesis service.

        Args:
            db: Database service for persistence
            event_bus: Event bus for subscribing to events
        """
        self.db = db
        self.event_bus = event_bus

        # Track pending joins: join_id -> PendingJoin
        self._pending_joins: Dict[str, PendingJoin] = {}

        # Reverse lookup: source_task_id -> [join_id, ...]
        # A task can be a source for multiple joins
        self._task_to_joins: Dict[str, List[str]] = {}

        logger.info("synthesis_service_initialized")

    def subscribe_to_events(self) -> None:
        """Subscribe to relevant events for synthesis orchestration."""
        # Listen for join creation events from CoordinationService
        self.event_bus.subscribe(
            "coordination.join.created", self._handle_join_created
        )

        # Listen for task completion to check if joins are ready
        self.event_bus.subscribe("TASK_COMPLETED", self._handle_task_completed)

        logger.info(
            "synthesis_service_subscribed",
            events=["coordination.join.created", "TASK_COMPLETED"],
        )

    def register_join(
        self,
        join_id: str,
        source_task_ids: List[str],
        continuation_task_id: str,
        merge_strategy: str = "combine",
    ) -> None:
        """Manually register a join for synthesis tracking.

        This can be used to register joins that weren't created through events,
        such as when loading existing joins from the database.

        Args:
            join_id: Unique identifier for the join
            source_task_ids: IDs of tasks that must complete before synthesis
            continuation_task_id: ID of task that receives merged results
            merge_strategy: Strategy for merging results
        """
        pending = PendingJoin(
            join_id=join_id,
            source_task_ids=source_task_ids,
            continuation_task_id=continuation_task_id,
            merge_strategy=merge_strategy,
        )
        self._pending_joins[join_id] = pending

        # Build reverse lookup
        for task_id in source_task_ids:
            if task_id not in self._task_to_joins:
                self._task_to_joins[task_id] = []
            self._task_to_joins[task_id].append(join_id)

        logger.info(
            "join_registered",
            join_id=join_id,
            source_task_count=len(source_task_ids),
            continuation_task_id=continuation_task_id,
            merge_strategy=merge_strategy,
        )

        # Check if any sources are already complete
        self._check_already_completed_sources(pending)

    def _handle_join_created(self, event_data: dict) -> None:
        """Handle coordination.join.created event to track pending joins.

        Args:
            event_data: Event payload from CoordinationService
        """
        payload = event_data.get("payload", {})
        join_id = payload.get("join_id")
        source_task_ids = payload.get("source_task_ids", [])
        continuation_task_id = payload.get("continuation_task_id")
        merge_strategy = payload.get("merge_strategy", "combine")

        if not join_id or not source_task_ids or not continuation_task_id:
            logger.warning(
                "invalid_join_event",
                join_id=join_id,
                has_sources=bool(source_task_ids),
                has_continuation=bool(continuation_task_id),
            )
            return

        self.register_join(
            join_id=join_id,
            source_task_ids=source_task_ids,
            continuation_task_id=continuation_task_id,
            merge_strategy=merge_strategy,
        )

    def _handle_task_completed(self, event_data: dict) -> None:
        """Handle TASK_COMPLETED event to check if any joins are ready.

        Args:
            event_data: Event payload with completed task info
        """
        completed_task_id = event_data.get("entity_id")
        if not completed_task_id:
            return

        # Check if this task is a source for any pending joins
        join_ids = self._task_to_joins.get(completed_task_id, [])
        if not join_ids:
            return

        logger.debug(
            "task_completed_checking_joins",
            task_id=completed_task_id,
            pending_join_count=len(join_ids),
        )

        for join_id in join_ids:
            pending = self._pending_joins.get(join_id)
            if not pending:
                continue

            # Mark this source as completed
            if completed_task_id not in pending.completed_source_ids:
                pending.completed_source_ids.append(completed_task_id)

            logger.debug(
                "join_progress_updated",
                join_id=join_id,
                completed=len(pending.completed_source_ids),
                total=len(pending.source_task_ids),
            )

            # Check if all sources are now complete
            if pending.is_ready():
                self._trigger_synthesis(join_id, pending)

    def _check_already_completed_sources(self, pending: PendingJoin) -> None:
        """Check if any source tasks are already completed when join is registered.

        This handles the case where tasks complete before the join is registered.

        Args:
            pending: The pending join to check
        """
        with self.db.get_session() as session:
            for task_id in pending.source_task_ids:
                task = session.query(Task).filter(Task.id == task_id).first()
                if task and task.status == "completed":
                    if task_id not in pending.completed_source_ids:
                        pending.completed_source_ids.append(task_id)
                        logger.debug(
                            "source_already_completed",
                            join_id=pending.join_id,
                            task_id=task_id,
                        )

        # Check if ready after accounting for already-completed tasks
        if pending.is_ready():
            self._trigger_synthesis(pending.join_id, pending)

    def _trigger_synthesis(self, join_id: str, pending: PendingJoin) -> None:
        """Trigger result synthesis for a ready join.

        This:
        1. Merges results from all source tasks
        2. Injects merged context into continuation task's synthesis_context
        3. Publishes synthesis completion event
        4. Cleans up the pending join

        Args:
            join_id: ID of the join
            pending: Pending join configuration
        """
        logger.info(
            "triggering_synthesis",
            join_id=join_id,
            source_count=len(pending.source_task_ids),
            merge_strategy=pending.merge_strategy,
        )

        try:
            # Merge results from all source tasks
            merged_result = self._merge_task_results(
                source_task_ids=pending.source_task_ids,
                merge_strategy=pending.merge_strategy,
            )

            # Inject into continuation task
            self._inject_synthesis_context(
                task_id=pending.continuation_task_id,
                synthesis_context=merged_result,
                source_task_ids=pending.source_task_ids,
                join_id=join_id,
            )

            # Publish synthesis complete event
            self.event_bus.publish(
                SystemEvent(
                    event_type="coordination.synthesis.completed",
                    entity_type="synthesis",
                    entity_id=join_id,
                    payload={
                        "join_id": join_id,
                        "continuation_task_id": pending.continuation_task_id,
                        "source_task_ids": pending.source_task_ids,
                        "merge_strategy": pending.merge_strategy,
                        "result_keys": list(merged_result.keys())
                        if isinstance(merged_result, dict)
                        else [],
                    },
                )
            )

            logger.info(
                "synthesis_completed",
                join_id=join_id,
                continuation_task_id=pending.continuation_task_id,
                merged_key_count=len(merged_result) if isinstance(merged_result, dict) else 0,
            )

        except Exception as e:
            logger.error(
                "synthesis_failed",
                join_id=join_id,
                error=str(e),
            )
            # Publish failure event
            self.event_bus.publish(
                SystemEvent(
                    event_type="coordination.synthesis.failed",
                    entity_type="synthesis",
                    entity_id=join_id,
                    payload={
                        "join_id": join_id,
                        "continuation_task_id": pending.continuation_task_id,
                        "error": str(e),
                    },
                )
            )

        finally:
            # Clean up the pending join
            self._cleanup_pending_join(join_id, pending)

    def _merge_task_results(
        self,
        source_task_ids: List[str],
        merge_strategy: str,
    ) -> Dict[str, Any]:
        """Merge results from multiple source tasks.

        This implements the actual merge logic that was previously unused
        in CoordinationService.merge_task_results().

        Args:
            source_task_ids: IDs of tasks to merge results from
            merge_strategy: Strategy for merging ("combine", "union", "intersection")

        Returns:
            Merged result dictionary
        """
        with self.db.get_session() as session:
            results = []
            for task_id in source_task_ids:
                task = session.query(Task).filter(Task.id == task_id).first()
                if not task:
                    logger.warning("source_task_not_found", task_id=task_id)
                    continue

                if task.status != "completed":
                    logger.warning(
                        "source_task_not_completed",
                        task_id=task_id,
                        status=task.status,
                    )
                    continue

                if task.result:
                    # Include task metadata with result
                    task_result = {
                        "_task_id": task_id,
                        "_task_type": task.task_type,
                        "_phase_id": task.phase_id,
                        **task.result,
                    }
                    results.append(task_result)

        return self._apply_merge_strategy(results, merge_strategy)

    def _apply_merge_strategy(
        self,
        results: List[Dict[str, Any]],
        strategy: str,
    ) -> Dict[str, Any]:
        """Apply merge strategy to combine results.

        Args:
            results: List of result dictionaries
            strategy: Merge strategy name

        Returns:
            Merged result dictionary
        """
        if not results:
            return {}

        if strategy == "combine":
            # Combine all results, preserving task metadata
            merged = {
                "_source_results": results,
                "_merge_strategy": strategy,
                "_source_count": len(results),
            }

            # Also flatten non-meta keys for convenience
            for result in results:
                for key, value in result.items():
                    if not key.startswith("_") and key not in merged:
                        merged[key] = value

            return merged

        elif strategy == "union":
            # Union of all keys, later values override earlier
            merged = {
                "_source_results": results,
                "_merge_strategy": strategy,
            }
            for result in results:
                for key, value in result.items():
                    if not key.startswith("_"):
                        merged[key] = value
            return merged

        elif strategy == "intersection":
            # Only keys present in all results
            if not results:
                return {}

            # Find common keys (excluding metadata)
            common_keys = set(k for k in results[0].keys() if not k.startswith("_"))
            for result in results[1:]:
                common_keys &= set(k for k in result.keys() if not k.startswith("_"))

            merged = {
                "_source_results": results,
                "_merge_strategy": strategy,
            }
            # Use values from last result for common keys
            for key in common_keys:
                merged[key] = results[-1][key]
            return merged

        else:
            # Default to combine
            logger.warning(
                "unknown_merge_strategy_falling_back",
                strategy=strategy,
                fallback="combine",
            )
            return self._apply_merge_strategy(results, "combine")

    def _inject_synthesis_context(
        self,
        task_id: str,
        synthesis_context: Dict[str, Any],
        source_task_ids: List[str],
        join_id: str,
    ) -> None:
        """Inject merged synthesis context into continuation task.

        Args:
            task_id: ID of the continuation task
            synthesis_context: Merged context to inject
            source_task_ids: IDs of source tasks (for metadata)
            join_id: ID of the join operation
        """
        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                raise ValueError(f"Continuation task not found: {task_id}")

            # Add metadata to synthesis context
            synthesis_context["_injected_at"] = str(task.updated_at)
            synthesis_context["_join_id"] = join_id
            synthesis_context["_source_task_ids"] = source_task_ids

            task.synthesis_context = synthesis_context
            session.commit()

            logger.info(
                "synthesis_context_injected",
                task_id=task_id,
                context_keys=list(synthesis_context.keys()),
            )

    def _cleanup_pending_join(self, join_id: str, pending: PendingJoin) -> None:
        """Clean up a completed pending join.

        Args:
            join_id: ID of the join to clean up
            pending: Pending join configuration
        """
        # Remove from pending joins
        if join_id in self._pending_joins:
            del self._pending_joins[join_id]

        # Clean up reverse lookup
        for task_id in pending.source_task_ids:
            if task_id in self._task_to_joins:
                self._task_to_joins[task_id] = [
                    jid for jid in self._task_to_joins[task_id] if jid != join_id
                ]
                if not self._task_to_joins[task_id]:
                    del self._task_to_joins[task_id]

    def get_pending_joins(self) -> Dict[str, PendingJoin]:
        """Get all pending joins (for debugging/monitoring).

        Returns:
            Dictionary of pending joins by join_id
        """
        return self._pending_joins.copy()

    def get_pending_join(self, join_id: str) -> Optional[PendingJoin]:
        """Get a specific pending join.

        Args:
            join_id: ID of the join to retrieve

        Returns:
            PendingJoin if found, None otherwise
        """
        return self._pending_joins.get(join_id)


# Singleton instance management
_synthesis_service: Optional[SynthesisService] = None


def get_synthesis_service(
    db: Optional[DatabaseService] = None,
    event_bus: Optional[EventBusService] = None,
) -> SynthesisService:
    """Get or create the SynthesisService singleton.

    Args:
        db: Database service (required on first call)
        event_bus: Event bus service (required on first call)

    Returns:
        SynthesisService instance
    """
    global _synthesis_service

    if _synthesis_service is None:
        if db is None or event_bus is None:
            raise ValueError(
                "db and event_bus are required on first call to get_synthesis_service"
            )
        _synthesis_service = SynthesisService(db=db, event_bus=event_bus)

    return _synthesis_service


def reset_synthesis_service() -> None:
    """Reset the singleton (for testing)."""
    global _synthesis_service
    _synthesis_service = None
