"""
Evaluator for the TASKS phase output.

Validates that tasks are implementable and have valid dependencies.
"""

from typing import Any

from .base import BaseEvaluator, EvalResult


class TaskEvaluator(BaseEvaluator):
    """
    Evaluates generated tasks for quality and implementability.

    Tasks should:
    - Have clear titles and descriptions
    - Have valid priorities (low, medium, high, critical)
    - Have valid phases (backend, frontend, integration, testing, etc.)
    - Have valid dependencies (reference existing tasks)
    - Not have circular dependencies
    - Be atomic (completable in 1-4 hours)
    """

    # Valid priority values
    VALID_PRIORITIES = frozenset(["low", "medium", "high", "critical"])

    # Valid phase values
    VALID_PHASES = frozenset(
        [
            "backend",
            "frontend",
            "integration",
            "testing",
            "devops",
            "documentation",
            "research",
            "design",
        ]
    )

    def evaluate(self, tasks: Any) -> EvalResult:
        """
        Evaluate generated tasks.

        Args:
            tasks: List of task dicts or TasksOutput dict with tickets/tasks

        Returns:
            EvalResult indicating if tasks pass quality gates
        """
        if not tasks:
            return EvalResult(
                passed=False,
                score=0.0,
                failures=["No tasks provided"],
                details={"no_tasks": False},
            )

        # Extract task list from various formats
        task_list = self._extract_tasks(tasks)

        if not task_list:
            return EvalResult(
                passed=False,
                score=0.0,
                failures=["No tasks in list"],
                details={"has_tasks": False},
            )

        checks = []

        # Check 1: Has tasks
        has_tasks = len(task_list) >= 1
        checks.append(("has_tasks", has_tasks))

        # Check 2: Tasks have titles
        has_titles = all(bool(t.get("title")) for t in task_list)
        checks.append(("has_titles", has_titles))

        # Check 3: Tasks have descriptions
        has_descriptions = all(
            bool(t.get("description") or t.get("objective")) for t in task_list
        )
        checks.append(("has_descriptions", has_descriptions))

        # Check 4: Tasks have valid priorities
        has_priorities = all(self._has_valid_priority(t) for t in task_list)
        checks.append(("valid_priorities", has_priorities))

        # Check 5: Tasks have valid phases
        has_phases = all(self._has_valid_phase(t) for t in task_list)
        checks.append(("valid_phases", has_phases))

        # Check 6: No duplicate titles
        titles = [t.get("title", "") for t in task_list]
        no_duplicates = len(set(titles)) == len(titles) and "" not in titles
        checks.append(("no_duplicates", no_duplicates))

        # Check 7: Dependencies reference valid tasks
        deps_valid = self._validate_dependencies(task_list)
        checks.append(("valid_dependencies", deps_valid))

        # Check 8: No circular dependencies
        no_circular = not self._has_circular_dependencies(task_list)
        checks.append(("no_circular_deps", no_circular))

        # Check 9: No self dependencies
        no_self_deps = all(self._has_no_self_dep(t) for t in task_list)
        checks.append(("no_self_dependencies", no_self_deps))

        # Check 10: Tasks have acceptance criteria or deliverables
        has_criteria = all(
            bool(t.get("acceptance_criteria") or t.get("deliverables"))
            for t in task_list
        )
        checks.append(("has_acceptance_criteria", has_criteria))

        result = self._make_result(checks)

        # Specific feedback
        if not deps_valid:
            result.feedback_for_retry = (
                "Task dependencies reference non-existent tasks. "
                "Dependencies should reference task titles or IDs that exist in the same list."
            )

        if not no_circular:
            if result.feedback_for_retry:
                result.feedback_for_retry += "\n\n"
            else:
                result.feedback_for_retry = ""
            result.feedback_for_retry += (
                "Circular dependencies detected. Task A cannot depend on Task B "
                "if Task B already depends on Task A (directly or transitively)."
            )

        if not has_phases:
            result.warnings.append(
                f"Some tasks have invalid phases. Valid phases: {', '.join(sorted(self.VALID_PHASES))}"
            )

        return result

    def _extract_tasks(self, data: Any) -> list[dict]:
        """Extract task list from various input formats."""
        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            # TasksOutput format with tickets
            if "tickets" in data:
                tasks = []
                for ticket in data.get("tickets", []):
                    if isinstance(ticket, dict):
                        tasks.extend(ticket.get("tasks", []))
                return tasks

            # Direct tasks list
            if "tasks" in data:
                return data.get("tasks", [])

        return []

    def _has_valid_priority(self, task: dict) -> bool:
        """Check if task has valid priority."""
        priority = task.get("priority", "")
        if not priority:
            return False
        return priority.lower() in self.VALID_PRIORITIES

    def _has_valid_phase(self, task: dict) -> bool:
        """Check if task has valid phase."""
        phase = task.get("phase", "")
        if not phase:
            return False
        return phase.lower() in self.VALID_PHASES

    def _has_no_self_dep(self, task: dict) -> bool:
        """Check that task doesn't depend on itself."""
        task_id = task.get("id") or task.get("title", "")
        deps = self._get_dependencies(task)
        return task_id not in deps

    def _get_dependencies(self, task: dict) -> list[str]:
        """Extract dependency list from task."""
        deps = task.get("dependencies", [])
        if isinstance(deps, dict):
            # TaskDependencies format
            return deps.get("depends_on", [])
        if isinstance(deps, list):
            return deps
        return []

    def _validate_dependencies(self, tasks: list[dict]) -> bool:
        """Validate that all dependencies reference existing tasks."""
        # Build set of valid task identifiers (both ID and title)
        valid_ids = set()
        for task in tasks:
            if task.get("id"):
                valid_ids.add(task["id"])
            if task.get("title"):
                valid_ids.add(task["title"])

        # Check all dependencies
        for task in tasks:
            for dep in self._get_dependencies(task):
                if dep and dep not in valid_ids:
                    return False
        return True

    def _has_circular_dependencies(self, tasks: list[dict]) -> bool:
        """
        Detect circular dependencies using DFS.

        Returns True if circular dependency found, False otherwise.
        """
        # Build adjacency graph (task -> dependencies)
        graph: dict[str, list[str]] = {}
        id_map: dict[str, str] = {}  # Map titles to IDs for consistency

        for task in tasks:
            task_id = task.get("id") or task.get("title", "")
            if task.get("title"):
                id_map[task["title"]] = task_id
            graph[task_id] = self._get_dependencies(task)

        # Normalize dependencies to use consistent IDs
        for task_id, deps in graph.items():
            graph[task_id] = [id_map.get(d, d) for d in deps]

        # DFS for cycle detection
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def has_cycle(node: str) -> bool:
            if node not in graph:
                return False
            if node in rec_stack:
                return True
            if node in visited:
                return False

            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if has_cycle(neighbor):
                    return True

            rec_stack.remove(node)
            return False

        for task_id in graph:
            if has_cycle(task_id):
                return True
        return False
