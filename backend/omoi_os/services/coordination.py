"""Coordination patterns service for multi-agent workflow orchestration.

This module provides reusable coordination primitives (sync, split, join, merge)
that enable complex multi-agent workflows with synchronization points,
parallel execution, and result aggregation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.task_queue import TaskQueueService


class CoordinationPattern(str, Enum):
    """Coordination pattern types."""

    SYNC = "sync"  # Synchronization point - wait for multiple tasks
    SPLIT = "split"  # Split work into parallel tasks
    JOIN = "join"  # Join multiple tasks before proceeding
    MERGE = "merge"  # Merge results from multiple tasks


@dataclass
class SyncPoint:
    """Synchronization point configuration.

    A sync point waits for multiple tasks to complete before allowing
    dependent tasks to proceed.
    """

    sync_id: str
    waiting_task_ids: List[str]
    required_count: Optional[int] = None  # None = wait for all
    timeout_seconds: Optional[int] = None


@dataclass
class SplitConfig:
    """Split configuration for parallel task creation.

    Splits a single task into multiple parallel tasks that can execute
    independently.
    """

    split_id: str
    source_task_id: str
    target_tasks: List[Dict[str, Any]]  # List of task configs
    required_capabilities: Optional[List[str]] = None


@dataclass
class JoinConfig:
    """Join configuration for aggregating parallel tasks.

    Joins multiple parallel tasks and creates a continuation task
    that depends on all joined tasks completing.
    """

    join_id: str
    source_task_ids: List[str]
    continuation_task: Dict[str, Any]  # Task config for continuation
    merge_strategy: str = "all"  # "all", "first", "majority"


@dataclass
class MergeConfig:
    """Merge configuration for combining task results.

    Merges results from multiple tasks using a specified strategy.
    """

    merge_id: str
    source_task_ids: List[str]
    merge_strategy: str = "combine"  # "combine", "union", "intersection", "custom"
    custom_merge_fn: Optional[str] = None  # Reference to custom merge function


class CoordinationService:
    """Service for managing coordination patterns in multi-agent workflows."""

    def __init__(
        self,
        db: DatabaseService,
        queue: TaskQueueService,
        event_bus: Optional[EventBusService] = None,
    ):
        """
        Initialize coordination service.

        Args:
            db: Database service
            queue: Task queue service
            event_bus: Optional event bus for publishing coordination events
        """
        self.db = db
        self.queue = queue
        self.event_bus = event_bus

    # ---------------------------------------------------------------------
    # Sync Point Operations
    # ---------------------------------------------------------------------

    def create_sync_point(
        self,
        sync_id: str,
        waiting_task_ids: List[str],
        required_count: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
    ) -> SyncPoint:
        """
        Create a synchronization point.

        Args:
            sync_id: Unique identifier for the sync point
            waiting_task_ids: List of task IDs that must complete
            required_count: Number of tasks that must complete (None = all)
            timeout_seconds: Optional timeout for sync point

        Returns:
            Created SyncPoint configuration
        """
        sync_point = SyncPoint(
            sync_id=sync_id,
            waiting_task_ids=waiting_task_ids,
            required_count=required_count or len(waiting_task_ids),
            timeout_seconds=timeout_seconds,
        )

        # Publish sync point created event
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="coordination.sync.created",
                    entity_type="sync_point",
                    entity_id=sync_id,
                    payload={
                        "sync_id": sync_id,
                        "waiting_task_ids": waiting_task_ids,
                        "required_count": sync_point.required_count,
                    },
                )
            )

        return sync_point

    def check_sync_point_ready(self, sync_id: str, sync_point: SyncPoint) -> bool:
        """
        Check if a sync point is ready (required tasks completed).

        Args:
            sync_id: Sync point identifier
            sync_point: SyncPoint configuration

        Returns:
            True if sync point is ready, False otherwise
        """
        with self.db.get_session() as session:
            completed_count = 0
            for task_id in sync_point.waiting_task_ids:
                task = session.query(Task).filter(Task.id == task_id).first()
                if task and task.status == "completed":
                    completed_count += 1

            is_ready = completed_count >= sync_point.required_count

            if is_ready and self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="coordination.sync.ready",
                        entity_type="sync_point",
                        entity_id=sync_id,
                        payload={
                            "sync_id": sync_id,
                            "completed_count": completed_count,
                            "required_count": sync_point.required_count,
                        },
                    )
                )

            return is_ready

    # ---------------------------------------------------------------------
    # Split Operations
    # ---------------------------------------------------------------------

    def split_task(
        self,
        split_id: str,
        source_task_id: str,
        target_tasks: List[Dict[str, Any]],
        required_capabilities: Optional[List[str]] = None,
    ) -> List[Task]:
        """
        Split a task into multiple parallel tasks.

        Args:
            split_id: Unique identifier for the split operation
            source_task_id: ID of the source task being split
            target_tasks: List of task configurations for parallel tasks
            required_capabilities: Optional capabilities required for target tasks

        Returns:
            List of created Task objects
        """
        with self.db.get_session() as session:
            source_task = session.query(Task).filter(Task.id == source_task_id).first()
            if not source_task:
                raise ValueError(f"Source task {source_task_id} not found")

            created_tasks = []
            for task_config in target_tasks:
                # Create task with dependency on source task
                task = self.queue.enqueue_task(
                    ticket_id=source_task.ticket_id,
                    phase_id=task_config.get("phase_id", source_task.phase_id),
                    task_type=task_config.get("task_type", "split_task"),
                    description=task_config.get("description", ""),
                    priority=task_config.get("priority", source_task.priority),
                    dependencies={"depends_on": [source_task_id]},
                )
                created_tasks.append(task)

            # Publish split event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="coordination.split.created",
                        entity_type="split",
                        entity_id=split_id,
                        payload={
                            "split_id": split_id,
                            "source_task_id": source_task_id,
                            "target_task_ids": [t.id for t in created_tasks],
                            "required_capabilities": required_capabilities,
                        },
                    )
                )

            return created_tasks

    # ---------------------------------------------------------------------
    # Join Operations
    # ---------------------------------------------------------------------

    def join_tasks(
        self,
        join_id: str,
        source_task_ids: List[str],
        continuation_task: Dict[str, Any],
        merge_strategy: str = "all",
    ) -> Task:
        """
        Join multiple tasks and create a continuation task.

        Args:
            join_id: Unique identifier for the join operation
            source_task_ids: List of task IDs to join
            continuation_task: Configuration for the continuation task
            merge_strategy: Strategy for merging results ("all", "first", "majority")

        Returns:
            Created continuation Task object
        """
        with self.db.get_session() as session:
            # Verify all source tasks exist
            source_tasks = (
                session.query(Task).filter(Task.id.in_(source_task_ids)).all()
            )
            if len(source_tasks) != len(source_task_ids):
                raise ValueError("Some source tasks not found")

            # Get ticket_id from first source task
            ticket_id = source_tasks[0].ticket_id

            # Create continuation task with dependencies on all source tasks
            continuation = self.queue.enqueue_task(
                ticket_id=ticket_id,
                phase_id=continuation_task.get("phase_id", source_tasks[0].phase_id),
                task_type=continuation_task.get("task_type", "join_task"),
                description=continuation_task.get("description", ""),
                priority=continuation_task.get("priority", source_tasks[0].priority),
                dependencies={"depends_on": source_task_ids},
            )

            # Publish join event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="coordination.join.created",
                        entity_type="join",
                        entity_id=join_id,
                        payload={
                            "join_id": join_id,
                            "source_task_ids": source_task_ids,
                            "continuation_task_id": continuation.id,
                            "merge_strategy": merge_strategy,
                        },
                    )
                )

            return continuation

    def register_join(
        self,
        join_id: str,
        source_task_ids: List[str],
        continuation_task_id: str,
        merge_strategy: str = "all",
    ) -> None:
        """
        Register a join operation for an existing continuation task.

        Unlike join_tasks(), this method does NOT create a new task.
        It only publishes the coordination.join.created event so that
        SynthesisService can track the join and merge results when ready.

        Use this when the continuation task was already created elsewhere
        (e.g., by SpecTaskExecutionService during spec task conversion).

        Args:
            join_id: Unique identifier for the join operation
            source_task_ids: List of task IDs that must complete before continuation
            continuation_task_id: ID of the existing task that will receive merged results
            merge_strategy: Strategy for merging results ("all", "first", "majority")
        """
        with self.db.get_session() as session:
            # Verify all source tasks exist
            source_tasks = (
                session.query(Task).filter(Task.id.in_(source_task_ids)).all()
            )
            if len(source_tasks) != len(source_task_ids):
                raise ValueError("Some source tasks not found")

            # Verify continuation task exists
            continuation = session.query(Task).filter(Task.id == continuation_task_id).first()
            if not continuation:
                raise ValueError(f"Continuation task not found: {continuation_task_id}")

            # Update continuation task dependencies to include all source tasks
            # This ensures it won't be picked up until all sources complete
            existing_deps = continuation.dependencies or {}
            depends_on = existing_deps.get("depends_on", [])
            for source_id in source_task_ids:
                if source_id not in depends_on:
                    depends_on.append(source_id)
            continuation.dependencies = {"depends_on": depends_on}
            session.commit()

        # Publish join event for SynthesisService
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="coordination.join.created",
                    entity_type="join",
                    entity_id=join_id,
                    payload={
                        "join_id": join_id,
                        "source_task_ids": source_task_ids,
                        "continuation_task_id": continuation_task_id,
                        "merge_strategy": merge_strategy,
                    },
                )
            )

    # ---------------------------------------------------------------------
    # Merge Operations
    # ---------------------------------------------------------------------

    def merge_task_results(
        self,
        merge_id: str,
        source_task_ids: List[str],
        merge_strategy: str = "combine",
        custom_merge_fn: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Merge results from multiple tasks.

        Args:
            merge_id: Unique identifier for the merge operation
            source_task_ids: List of task IDs to merge results from
            merge_strategy: Strategy for merging ("combine", "union", "intersection", "custom")
            custom_merge_fn: Optional reference to custom merge function

        Returns:
            Merged result dictionary
        """
        with self.db.get_session() as session:
            # Get all source tasks
            source_tasks = (
                session.query(Task).filter(Task.id.in_(source_task_ids)).all()
            )
            if len(source_tasks) != len(source_task_ids):
                raise ValueError("Some source tasks not found")

            # Collect results
            results = []
            for task in source_tasks:
                if task.status != "completed":
                    raise ValueError(f"Task {task.id} is not completed")
                if task.result:
                    results.append(task.result)

            # Apply merge strategy
            merged_result = self._apply_merge_strategy(
                results, merge_strategy, custom_merge_fn
            )

            # Publish merge event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="coordination.merge.completed",
                        entity_type="merge",
                        entity_id=merge_id,
                        payload={
                            "merge_id": merge_id,
                            "source_task_ids": source_task_ids,
                            "merge_strategy": merge_strategy,
                            "result_keys": list(merged_result.keys())
                            if isinstance(merged_result, dict)
                            else [],
                        },
                    )
                )

            return merged_result

    def _apply_merge_strategy(
        self,
        results: List[Dict[str, Any]],
        strategy: str,
        custom_fn: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Apply merge strategy to combine results.

        Args:
            results: List of result dictionaries
            strategy: Merge strategy name
            custom_fn: Optional custom function reference

        Returns:
            Merged result dictionary
        """
        if not results:
            return {}

        if strategy == "combine":
            # Combine all results into a single dict
            merged = {}
            for result in results:
                if isinstance(result, dict):
                    merged.update(result)
            return merged

        elif strategy == "union":
            # Union of all keys, values from last result
            merged = {}
            for result in results:
                if isinstance(result, dict):
                    merged.update(result)
            return merged

        elif strategy == "intersection":
            # Only keys present in all results
            if not results:
                return {}
            common_keys = set(results[0].keys())
            for result in results[1:]:
                if isinstance(result, dict):
                    common_keys &= set(result.keys())
            return {k: results[-1][k] for k in common_keys if k in results[-1]}

        elif strategy == "custom" and custom_fn:
            # Custom merge function (would need to be loaded/executed)
            # For now, fall back to combine
            return self._apply_merge_strategy(results, "combine", None)

        else:
            # Default: combine
            return self._apply_merge_strategy(results, "combine", None)

    # ---------------------------------------------------------------------
    # Pattern Execution Helpers
    # ---------------------------------------------------------------------

    def execute_pattern(self, pattern_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a coordination pattern from configuration.

        Args:
            pattern_config: Pattern configuration dictionary

        Returns:
            Execution result with created entities
        """
        pattern_type = pattern_config.get("type")
        pattern_id = pattern_config.get("id", "")

        if pattern_type == CoordinationPattern.SYNC:
            sync_point = self.create_sync_point(
                sync_id=pattern_id,
                waiting_task_ids=pattern_config.get("waiting_task_ids", []),
                required_count=pattern_config.get("required_count"),
                timeout_seconds=pattern_config.get("timeout_seconds"),
            )
            return {"sync_point": sync_point, "sync_id": sync_point.sync_id}

        elif pattern_type == CoordinationPattern.SPLIT:
            tasks = self.split_task(
                split_id=pattern_id,
                source_task_id=pattern_config.get("source_task_id", ""),
                target_tasks=pattern_config.get("target_tasks", []),
                required_capabilities=pattern_config.get("required_capabilities"),
            )
            return {"tasks": tasks, "task_ids": [t.id for t in tasks]}

        elif pattern_type == CoordinationPattern.JOIN:
            continuation = self.join_tasks(
                join_id=pattern_id,
                source_task_ids=pattern_config.get("source_task_ids", []),
                continuation_task=pattern_config.get("continuation_task", {}),
                merge_strategy=pattern_config.get("merge_strategy", "all"),
            )
            return {"continuation_task": continuation, "task_id": continuation.id}

        elif pattern_type == CoordinationPattern.MERGE:
            merged = self.merge_task_results(
                merge_id=pattern_id,
                source_task_ids=pattern_config.get("source_task_ids", []),
                merge_strategy=pattern_config.get("merge_strategy", "combine"),
                custom_merge_fn=pattern_config.get("custom_merge_fn"),
            )
            return {"merged_result": merged}

        else:
            raise ValueError(f"Unknown pattern type: {pattern_type}")
