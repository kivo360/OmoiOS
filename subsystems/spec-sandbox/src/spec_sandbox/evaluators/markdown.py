"""Evaluator for markdown generation output.

Validates markdown files with frontmatter to ensure they meet
quality standards before syncing to the backend API.

Key validations:
- Frontmatter schema compliance (Pydantic models)
- Required fields present
- ID format validation (TKT-NNN, TSK-NNN)
- Cross-reference validation (task parent_ticket references valid ticket)
- Body content quality (non-empty, minimum length)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from spec_sandbox.evaluators.base import BaseEvaluator, EvalResult
from spec_sandbox.parsers.markdown import (
    MarkdownParseError,
    parse_ticket_markdown,
    parse_task_markdown,
)
from spec_sandbox.schemas.frontmatter import TaskFrontmatter, TicketFrontmatter


class MarkdownOutputEvaluator(BaseEvaluator):
    """Evaluator for markdown generation output.

    Validates:
    - All ticket/task files parse successfully
    - Frontmatter validates against Pydantic schemas
    - IDs use correct format (TKT-NNN, TSK-NNN)
    - Task parent_ticket references exist in tickets
    - Body content has minimum length
    - No duplicate IDs
    """

    threshold: float = 0.8  # Higher threshold for markdown validation

    async def evaluate(
        self,
        output: Dict[str, Any],
        context: Dict[str, Any],
    ) -> EvalResult:
        """Evaluate markdown output.

        Args:
            output: Dict containing either:
                - "output_dir": Path to directory with tickets/ and tasks/ subdirs
                - OR "tickets" and "tasks" lists of file paths
                - OR "ticket_files" and "task_files" lists directly
            context: Accumulated context (may contain expected IDs)

        Returns:
            EvalResult with score and pass/fail status
        """
        scores = {}
        issues = []
        warnings = []

        # Determine input format
        output_dir = output.get("output_dir")
        ticket_files = output.get("ticket_files", [])
        task_files = output.get("task_files", [])

        if output_dir:
            output_path = Path(output_dir)
            tickets_dir = output_path / "tickets"
            tasks_dir = output_path / "tasks"

            if tickets_dir.exists():
                ticket_files = list(tickets_dir.glob("TKT-*.md"))
            if tasks_dir.exists():
                task_files = list(tasks_dir.glob("TSK-*.md"))

        # Validate we have files to check
        if not ticket_files and not task_files:
            return self._create_result(
                score=0.0,
                feedback="No markdown files found to validate",
                details={"files_found": 0},
            )

        # Track parsed results
        parsed_tickets: List[Tuple[TicketFrontmatter, str, Path]] = []
        parsed_tasks: List[Tuple[TaskFrontmatter, str, Path]] = []
        ticket_ids = set()
        task_ids = set()

        # Validate tickets
        ticket_parse_success = 0
        ticket_parse_errors = []

        for file_path in ticket_files:
            path = Path(file_path) if isinstance(file_path, str) else file_path
            try:
                ticket, body = parse_ticket_markdown(path)
                parsed_tickets.append((ticket, body, path))
                ticket_parse_success += 1

                # Track ID for duplicate detection
                if ticket.id in ticket_ids:
                    issues.append(f"Duplicate ticket ID: {ticket.id}")
                ticket_ids.add(ticket.id)

            except MarkdownParseError as e:
                ticket_parse_errors.append(f"{path.name}: {e}")

        # Validate tasks
        task_parse_success = 0
        task_parse_errors = []

        for file_path in task_files:
            path = Path(file_path) if isinstance(file_path, str) else file_path
            try:
                task, body = parse_task_markdown(path)
                parsed_tasks.append((task, body, path))
                task_parse_success += 1

                # Track ID for duplicate detection
                if task.id in task_ids:
                    issues.append(f"Duplicate task ID: {task.id}")
                task_ids.add(task.id)

            except MarkdownParseError as e:
                task_parse_errors.append(f"{path.name}: {e}")

        # Calculate parsing scores
        total_tickets = len(ticket_files)
        total_tasks = len(task_files)

        scores["ticket_parsing"] = ticket_parse_success / total_tickets if total_tickets > 0 else 1.0
        scores["task_parsing"] = task_parse_success / total_tasks if total_tasks > 0 else 1.0

        for error in ticket_parse_errors:
            issues.append(f"Ticket parse error: {error}")
        for error in task_parse_errors:
            issues.append(f"Task parse error: {error}")

        # Validate cross-references (task parent_ticket -> ticket)
        valid_parent_refs = 0
        invalid_parent_refs = []

        for task, body, path in parsed_tasks:
            if task.parent_ticket in ticket_ids:
                valid_parent_refs += 1
            else:
                invalid_parent_refs.append(
                    f"Task {task.id} references unknown ticket: {task.parent_ticket}"
                )

        if parsed_tasks:
            scores["parent_references"] = valid_parent_refs / len(parsed_tasks)
        else:
            scores["parent_references"] = 1.0

        for ref_error in invalid_parent_refs:
            issues.append(ref_error)

        # Validate body content quality
        body_quality_scores = []

        for ticket, body, path in parsed_tickets:
            quality = self._evaluate_body_quality(body, "ticket")
            body_quality_scores.append(quality)
            if quality < 0.5:
                warnings.append(f"Ticket {ticket.id} has sparse body content")

        for task, body, path in parsed_tasks:
            quality = self._evaluate_body_quality(body, "task")
            body_quality_scores.append(quality)
            if quality < 0.5:
                warnings.append(f"Task {task.id} has sparse body content")

        scores["body_quality"] = (
            sum(body_quality_scores) / len(body_quality_scores)
            if body_quality_scores
            else 1.0
        )

        # Validate ID sequence
        scores["id_sequence"] = self._validate_id_sequence(ticket_ids, task_ids, warnings)

        # Check for expected IDs from context (if provided)
        expected_tickets = context.get("expected_ticket_ids", set())
        expected_tasks = context.get("expected_task_ids", set())

        if expected_tickets:
            missing_tickets = expected_tickets - ticket_ids
            extra_tickets = ticket_ids - expected_tickets
            if missing_tickets:
                warnings.append(f"Missing expected tickets: {missing_tickets}")
            if extra_tickets:
                warnings.append(f"Extra unexpected tickets: {extra_tickets}")
            scores["expected_tickets"] = (
                len(ticket_ids & expected_tickets) / len(expected_tickets)
            )
        else:
            scores["expected_tickets"] = 1.0

        if expected_tasks:
            missing_tasks = expected_tasks - task_ids
            extra_tasks = task_ids - expected_tasks
            if missing_tasks:
                warnings.append(f"Missing expected tasks: {missing_tasks}")
            if extra_tasks:
                warnings.append(f"Extra unexpected tasks: {extra_tasks}")
            scores["expected_tasks"] = len(task_ids & expected_tasks) / len(expected_tasks)
        else:
            scores["expected_tasks"] = 1.0

        # Calculate overall score
        weights = {
            "ticket_parsing": 0.25,
            "task_parsing": 0.25,
            "parent_references": 0.20,
            "body_quality": 0.15,
            "id_sequence": 0.05,
            "expected_tickets": 0.05,
            "expected_tasks": 0.05,
        }

        total_score = sum(scores[k] * weights[k] for k in scores)

        # Build feedback
        feedback_parts = []
        if issues:
            feedback_parts.append("Issues found:\n- " + "\n- ".join(issues))
        if warnings:
            feedback_parts.append("Warnings:\n- " + "\n- ".join(warnings))

        feedback = "\n\n".join(feedback_parts) if feedback_parts else None

        # Add summary to details
        details = {
            **scores,
            "total_tickets": total_tickets,
            "total_tasks": total_tasks,
            "parsed_tickets": ticket_parse_success,
            "parsed_tasks": task_parse_success,
            "ticket_ids": list(ticket_ids),
            "task_ids": list(task_ids),
        }

        return self._create_result(
            score=total_score,
            feedback=feedback,
            details=details,
        )

    def _evaluate_body_quality(self, body: str, artifact_type: str) -> float:
        """Evaluate the quality of markdown body content.

        Args:
            body: The markdown body content
            artifact_type: "ticket" or "task"

        Returns:
            Quality score 0-1
        """
        if not body or not body.strip():
            return 0.0

        body = body.strip()
        score = 0.0

        # Minimum length check
        min_length = 100 if artifact_type == "ticket" else 50
        if len(body) >= min_length:
            score += 0.4
        elif len(body) >= min_length // 2:
            score += 0.2

        # Has markdown structure (headers, lists, etc.)
        has_headers = body.count("#") >= 1
        has_lists = body.count("-") >= 2 or body.count("*") >= 2 or body.count("1.") >= 1
        has_code = "```" in body or "`" in body

        if has_headers:
            score += 0.2
        if has_lists:
            score += 0.2
        if has_code:
            score += 0.1

        # Content substance
        word_count = len(body.split())
        if word_count >= 50:
            score += 0.1
        elif word_count >= 20:
            score += 0.05

        return min(1.0, score)

    def _validate_id_sequence(
        self,
        ticket_ids: set,
        task_ids: set,
        warnings: List[str],
    ) -> float:
        """Validate that IDs follow sequential pattern.

        Args:
            ticket_ids: Set of ticket IDs
            task_ids: Set of task IDs
            warnings: List to append warnings to

        Returns:
            Sequence score 0-1
        """
        score = 1.0

        # Extract numbers from IDs
        ticket_nums = []
        for tid in ticket_ids:
            if tid.startswith("TKT-"):
                try:
                    ticket_nums.append(int(tid[4:]))
                except ValueError:
                    warnings.append(f"Invalid ticket ID format: {tid}")
                    score -= 0.1

        task_nums = []
        for tid in task_ids:
            if tid.startswith("TSK-"):
                try:
                    task_nums.append(int(tid[4:]))
                except ValueError:
                    warnings.append(f"Invalid task ID format: {tid}")
                    score -= 0.1

        # Check for gaps (warning only)
        if ticket_nums:
            ticket_nums.sort()
            expected = set(range(ticket_nums[0], ticket_nums[-1] + 1))
            actual = set(ticket_nums)
            gaps = expected - actual
            if gaps:
                warnings.append(f"Gap in ticket ID sequence: missing {gaps}")

        if task_nums:
            task_nums.sort()
            expected = set(range(task_nums[0], task_nums[-1] + 1))
            actual = set(task_nums)
            gaps = expected - actual
            if gaps:
                warnings.append(f"Gap in task ID sequence: missing {gaps}")

        return max(0.0, score)


async def validate_markdown_directory(
    output_dir: Path,
    expected_ticket_ids: Optional[set] = None,
    expected_task_ids: Optional[set] = None,
) -> EvalResult:
    """Convenience function to validate a markdown output directory.

    Args:
        output_dir: Path to directory containing tickets/ and tasks/ subdirs
        expected_ticket_ids: Optional set of expected ticket IDs
        expected_task_ids: Optional set of expected task IDs

    Returns:
        EvalResult with validation results
    """
    evaluator = MarkdownOutputEvaluator()

    output = {"output_dir": str(output_dir)}
    context = {}

    if expected_ticket_ids:
        context["expected_ticket_ids"] = expected_ticket_ids
    if expected_task_ids:
        context["expected_task_ids"] = expected_task_ids

    return await evaluator.evaluate(output, context)
