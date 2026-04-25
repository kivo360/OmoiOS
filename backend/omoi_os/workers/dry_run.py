"""Orchestrator dry-run mode — captures dispatch decisions without executing them."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class TaskSummary:
    """Lightweight summary of a task for dry-run reporting."""

    task_id: str
    task_type: str
    description: str
    priority: str
    phase_id: str
    ticket_id: Optional[str]


@dataclass
class BlockedTaskInfo:
    """Info about a task blocked by dependencies."""

    task_id: str
    task_type: str
    description: str
    blocked_by: list[str]  # IDs of incomplete dependencies


@dataclass
class DryRunDecision:
    """What the orchestrator WOULD do in a real dispatch cycle."""

    cycle_number: int
    timestamp: str

    # Task selection
    eligible_tasks: list[TaskSummary] = field(default_factory=list)
    selected_task: Optional[TaskSummary] = None
    selection_reason: str = ""

    # Dependency state
    dependency_graph: dict[str, list[str]] = field(default_factory=dict)
    blocked_tasks: list[BlockedTaskInfo] = field(default_factory=list)
    completed_predecessors: list[str] = field(default_factory=list)

    # Concurrency enforcement
    running_count_by_project: dict[str, int] = field(default_factory=dict)
    concurrency_limit_hit: bool = False
    limit_details: Optional[str] = None

    # What would happen
    would_spawn_sandbox: bool = False
    would_create_branch: bool = False
    branch_name_preview: Optional[str] = None
    env_vars_preview: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dict for event payload / JSON serialization."""
        return asdict(self)

    def to_log_dict(self) -> dict:
        """Compact dict for structured logging."""
        d = self.to_dict()
        # Truncate long fields for log readability
        if d.get("eligible_tasks") and len(d["eligible_tasks"]) > 5:
            d["eligible_tasks"] = d["eligible_tasks"][:5]
            d["eligible_tasks_truncated"] = True
        return d
