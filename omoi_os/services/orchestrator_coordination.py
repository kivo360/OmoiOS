"""Orchestrator coordination integration for pattern-based task generation.

This module extends the orchestrator to interpret coordination patterns
when generating tasks from tickets.
"""

from typing import Any, Dict, List, Optional

from omoi_os.services.coordination import CoordinationService
from omoi_os.services.pattern_loader import PatternLoader
from omoi_os.services.task_queue import TaskQueueService


class OrchestratorCoordination:
    """Orchestrator integration for coordination patterns."""

    def __init__(
        self,
        coordination_service: CoordinationService,
        pattern_loader: Optional[PatternLoader] = None,
    ):
        """
        Initialize orchestrator coordination.

        Args:
            coordination_service: Coordination service instance
            pattern_loader: Optional pattern loader (creates default if None)
        """
        self.coordination = coordination_service
        self.pattern_loader = pattern_loader or PatternLoader()

    def apply_pattern_to_ticket(
        self,
        ticket_id: str,
        pattern_name: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Apply a coordination pattern to a ticket.

        Args:
            ticket_id: Ticket ID to apply pattern to
            pattern_name: Name of the pattern to apply
            context: Optional context dictionary for pattern resolution

        Returns:
            Dictionary with created entities (tasks, sync points, etc.)
        """
        # Load pattern configuration
        pattern_config = self.pattern_loader.load_pattern(pattern_name)

        # Resolve template variables if context provided
        if context:
            pattern_config = self.pattern_loader.resolve_pattern(
                pattern_config, context
            )

        # Get the main pattern definition
        pattern_def = pattern_config.get("pattern", {})

        # If source_task_id is in context, use it
        if context and "source_task_id" in context:
            pattern_def["source_task_id"] = context["source_task_id"]

        # Execute pattern
        result = self.coordination.execute_pattern(pattern_def)

        # Handle sync points if defined
        sync_points_config = pattern_config.get("sync_points", [])
        sync_results = []
        for sync_config in sync_points_config:
            # Resolve sync config with created task IDs
            if context:
                sync_config = self.pattern_loader.resolve_pattern(
                    sync_config, {**context, **result}
                )

            sync_point = self.coordination.create_sync_point(
                sync_id=sync_config.get("id", ""),
                waiting_task_ids=sync_config.get("waiting_task_ids", []),
                required_count=sync_config.get("required_count"),
                timeout_seconds=sync_config.get("timeout_seconds"),
            )
            sync_results.append(sync_point)

        # Handle join if defined
        join_config = pattern_config.get("join")
        join_result = None
        if join_config:
            if context:
                join_config = self.pattern_loader.resolve_pattern(
                    join_config, {**context, **result}
                )

            continuation = self.coordination.join_tasks(
                join_id=join_config.get("id", ""),
                source_task_ids=join_config.get("source_task_ids", []),
                continuation_task=join_config.get("continuation_task", {}),
                merge_strategy=join_config.get("merge_strategy", "all"),
            )
            join_result = continuation

        # Handle merge if defined
        merge_config = pattern_config.get("merge")
        merge_result = None
        if merge_config:
            if context:
                merge_config = self.pattern_loader.resolve_pattern(
                    merge_config, {**context, **result}
                )

            merged = self.coordination.merge_task_results(
                merge_id=merge_config.get("id", ""),
                source_task_ids=merge_config.get("source_task_ids", []),
                merge_strategy=merge_config.get("merge_strategy", "combine"),
                custom_merge_fn=merge_config.get("custom_merge_fn"),
            )
            merge_result = merged

        return {
            "pattern": result,
            "sync_points": sync_results,
            "join": join_result,
            "merge": merge_result,
        }

    def generate_tasks_with_pattern(
        self,
        ticket_id: str,
        initial_task_type: str,
        pattern_name: Optional[str] = None,
        pattern_context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Generate tasks for a ticket, optionally using a coordination pattern.

        Args:
            ticket_id: Ticket ID
            initial_task_type: Type of initial task to create
            pattern_name: Optional pattern name to apply after initial task
            pattern_context: Optional context for pattern resolution

        Returns:
            List of created task IDs
        """
        queue = self.coordination.queue

        # Create initial task
        initial_task = queue.enqueue_task(
            ticket_id=ticket_id,
            phase_id="PHASE_INITIAL",
            task_type=initial_task_type,
            description=f"Initial task: {initial_task_type}",
            priority="MEDIUM",
        )

        task_ids = [initial_task.id]

        # Apply pattern if specified
        if pattern_name:
            context = pattern_context or {}
            context["source_task_id"] = initial_task.id

            pattern_result = self.apply_pattern_to_ticket(
                ticket_id=ticket_id,
                pattern_name=pattern_name,
                context=context,
            )

            # Collect all created task IDs
            if "tasks" in pattern_result.get("pattern", {}):
                task_ids.extend(
                    [t.id for t in pattern_result["pattern"]["tasks"]]
                )
            elif "task_id" in pattern_result.get("pattern", {}):
                task_ids.append(pattern_result["pattern"]["task_id"])

            if pattern_result.get("join"):
                task_ids.append(pattern_result["join"].id)

        return task_ids

