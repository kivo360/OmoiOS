"""Context aggregation and summarization service."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from omoi_os.models.phase_context import PhaseContext
from omoi_os.models.phases import PHASE_SEQUENCE
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.context_summarizer import ContextSummarizer
from omoi_os.services.database import DatabaseService


class ContextService:
    """Manages cross-phase context aggregation and summarization."""

    def __init__(self, db: DatabaseService):
        self.db = db
        self.summarizer = ContextSummarizer()

    def aggregate_phase_context(self, ticket_id: str, phase_id: str) -> dict[str, Any]:
        """
        Aggregate context from completed tasks in a specific phase.

        Args:
            ticket_id: Ticket identifier
            phase_id: Phase identifier

        Returns:
            Dict containing aggregated context for the phase.
        """
        ticket_id = str(ticket_id)
        phase_id = str(phase_id)

        aggregated: dict[str, Any] = {
            "ticket_id": ticket_id,
            "phase_id": phase_id,
            "tasks": [],
            "decisions": [],
            "risks": [],
            "notes": [],
            "artifacts": [],
        }

        with self.db.get_session() as session:
            tasks = (
                session.query(Task)
                .filter(
                    Task.ticket_id == ticket_id,
                    Task.phase_id == phase_id,
                    Task.status == "completed",
                )
                .order_by(Task.completed_at.asc().nulls_last())
                .all()
            )

            for task in tasks:
                task_result = task.result or {}
                aggregated["tasks"].append(
                    {
                        "task_id": task.id,
                        "task_type": task.task_type,
                        "summary": task_result.get("summary") or task.description,
                        "outputs": task_result.get("outputs"),
                    }
                )
                context_block = task_result.get("context") or {}
                aggregated["decisions"].extend(_listify(context_block.get("decisions")))
                aggregated["risks"].extend(_listify(context_block.get("risks")))
                aggregated["notes"].extend(_listify(context_block.get("notes")))
                artifacts = task_result.get("artifacts") or []
                if isinstance(artifacts, list):
                    aggregated["artifacts"].extend(artifacts)

        aggregated["decisions"] = _dedupe_preserve_order(aggregated["decisions"])
        aggregated["risks"] = _dedupe_preserve_order(aggregated["risks"])
        aggregated["notes"] = _dedupe_preserve_order(aggregated["notes"])
        aggregated["summary"] = self._build_phase_summary(aggregated)
        return aggregated

    def summarize_context(self, context: dict[str, Any], max_tokens: int = 2000) -> str:
        """
        Summarize aggregated context to reduce token usage.

        Args:
            context: Structured context dict
            max_tokens: Character budget approximation for summary

        Returns:
            Summary string constrained to character budget.
        """
        summary = self.summarizer.summarize_structured(context)
        if len(summary) <= max_tokens:
            return summary
        truncated = summary[:max_tokens].rsplit(" ", 1)[0]
        return f"{truncated} ..."

    def get_context_for_phase(self, ticket_id: str, target_phase: str) -> dict[str, Any]:
        """
        Gather context from all phases preceding the target phase.

        Args:
            ticket_id: Ticket identifier
            target_phase: Phase requesting context

        Returns:
            Dict containing prior phase context and summary.
        """
        ticket_id = str(ticket_id)
        target_phase = str(target_phase)

        ordered_phases = [phase.value for phase in PHASE_SEQUENCE]
        try:
            target_index = ordered_phases.index(target_phase)
        except ValueError:
            target_index = len(ordered_phases)
        included = ordered_phases[:target_index]

        with self.db.get_session() as session:
            ticket = self._get_ticket_or_raise(session, ticket_id)
            existing_context = (ticket.context or {}).get("phases", {})
            context_subset: dict[str, Any] = {
                phase: existing_context[phase] for phase in included if phase in existing_context
            }

            missing_phases = [phase for phase in included if phase not in context_subset]
            if missing_phases:
                records = (
                    session.query(PhaseContext)
                    .filter(
                        PhaseContext.ticket_id == ticket_id,
                        PhaseContext.phase_id.in_(missing_phases),
                    )
                    .all()
                )
                for record in records:
                    context_subset[record.phase_id] = record.context_data

        summary_input = {"phases": context_subset} if context_subset else {}
        summary = self.summarize_context(summary_input) if summary_input else None
        return {
            "ticket_id": ticket_id,
            "target_phase": target_phase,
            "phases": context_subset,
            "summary": summary,
        }

    def update_ticket_context(self, ticket_id: str, phase_id: str) -> None:
        """
        Update ticket context with aggregated phase data.

        Args:
            ticket_id: Ticket identifier
            phase_id: Phase identifier to aggregate
        """
        ticket_id = str(ticket_id)
        phase_id = str(phase_id)

        phase_context = self.aggregate_phase_context(ticket_id, phase_id)
        phase_summary = self.summarize_context({"phases": {phase_id: phase_context}})

        with self.db.get_session() as session:
            ticket = self._get_ticket_or_raise(session, ticket_id)
            ticket_context = ticket.context or {}
            phases = ticket_context.get("phases") or {}
            phases[phase_id] = phase_context
            ticket_context["phases"] = phases
            history = ticket_context.get("history") or []
            history.append(
                {
                    "phase_id": phase_id,
                    "summary": phase_context.get("summary"),
                }
            )
            ticket_context["history"] = history
            ticket_context["last_updated_phase"] = phase_id
            ticket.context = ticket_context
            ticket.context_summary = self.summarize_context(ticket_context)

            existing = (
                session.query(PhaseContext)
                .filter(
                    PhaseContext.ticket_id == ticket_id,
                    PhaseContext.phase_id == phase_id,
                )
                .order_by(PhaseContext.created_at.desc())
                .first()
            )
            if existing:
                existing.context_data = phase_context
                existing.context_summary = phase_summary
            else:
                session.add(
                    PhaseContext(
                        ticket_id=ticket_id,
                        phase_id=phase_id,
                        context_data=phase_context,
                        context_summary=phase_summary,
                    )
                )

    def _build_phase_summary(self, aggregated: dict[str, Any]) -> str:
        """Compose a short textual summary for a single phase."""
        task_summaries = [
            task.get("summary") or task.get("task_type") for task in aggregated.get("tasks", [])
        ]
        decision_fragment = (
            f"Decisions: {', '.join(aggregated['decisions'])}"
            if aggregated["decisions"]
            else ""
        )
        sentences = [summary for summary in task_summaries if summary]
        if decision_fragment:
            sentences.append(decision_fragment)
        if aggregated.get("risks"):
            sentences.append(f"Risks: {', '.join(aggregated['risks'])}")
        if not sentences:
            return "No completed tasks recorded yet."
        return "; ".join(sentences)

    @staticmethod
    def _get_ticket_or_raise(session: Session, ticket_id: str) -> Ticket:
        ticket = session.get(Ticket, ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")
        return ticket


def _listify(value: Any) -> list[Any]:
    """Ensure a value is returned as a list."""
    if not value:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    return [value]


def _dedupe_preserve_order(items: list[Any]) -> list[Any]:
    """Remove duplicates while preserving order."""
    seen: set[Any] = set()
    result: list[Any] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


