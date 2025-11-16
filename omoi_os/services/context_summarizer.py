"""Utility for summarizing aggregated context."""

from __future__ import annotations

from typing import Any


class ContextSummarizer:
    """Summarizes structured context dictionaries into concise text."""

    def summarize_structured(self, context: dict[str, Any]) -> str:
        """
        Summarize structured context (decisions, risks, tasks, artifacts).

        Args:
            context: Structured context dict, typically {"phases": {...}}

        Returns:
            Human-readable summary string.
        """
        key_points = self.extract_key_points(context)
        if not key_points:
            return "No contextual insights available yet."

        lines = ["Context Summary:"]
        for point in key_points:
            lines.append(f"- {point}")
        return "\n".join(lines)

    def extract_key_points(self, context: dict[str, Any]) -> list[str]:
        """
        Extract key points (decisions, risks, highlights) from context.

        Args:
            context: Structured context dictionary

        Returns:
            Ordered list of key point strings.
        """
        key_points: list[str] = []
        phases = context.get("phases") if isinstance(context, dict) else None

        if isinstance(phases, dict):
            for phase_id, phase_context in phases.items():
                if not isinstance(phase_context, dict):
                    continue
                summary = phase_context.get("summary")
                if summary:
                    key_points.append(f"{phase_id}: {summary}")

                for decision in _safe_iterable(phase_context.get("decisions")):
                    key_points.append(f"{phase_id} decision: {decision}")

                for risk in _safe_iterable(phase_context.get("risks")):
                    key_points.append(f"{phase_id} risk: {risk}")

                tasks = phase_context.get("tasks")
                if isinstance(tasks, list) and tasks:
                    task_summary = tasks[0].get("summary") or tasks[0].get("task_type")
                    if task_summary:
                        key_points.append(f"{phase_id} lead task: {task_summary}")
        else:
            # Fall back to top-level decisions/risks if phases mapping not provided
            for decision in _safe_iterable(context.get("decisions")):
                key_points.append(f"Decision: {decision}")
            for risk in _safe_iterable(context.get("risks")):
                key_points.append(f"Risk: {risk}")

        # Limit to reasonable number of bullet points to avoid overlong summaries
        return key_points[:20]


def _safe_iterable(value: Any) -> list[Any]:
    """Return list if value iterable, else empty list."""
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


