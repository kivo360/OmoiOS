"""Tests for cross-phase context aggregation and summarization."""

from __future__ import annotations

from typing import Any

from omoi_os.models.phase_context import PhaseContext
from omoi_os.models.phases import Phase
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.context_service import ContextService
from omoi_os.services.context_summarizer import ContextSummarizer
from omoi_os.services.database import DatabaseService


def _create_ticket(session, phase: Phase = Phase.REQUIREMENTS) -> Ticket:
    ticket = Ticket(
        title="Context Ticket",
        description="Ticket for context aggregation tests",
        phase_id=phase.value,
        status="pending",
        priority="HIGH",
    )
    session.add(ticket)
    session.flush()
    session.refresh(ticket)
    session.expunge(ticket)
    return ticket


def _create_completed_task(
    session,
    ticket_id: str,
    phase: Phase,
    summary: str,
    decisions: list[str] | None = None,
    risks: list[str] | None = None,
    artifacts: list[dict[str, Any]] | None = None,
) -> Task:
    payload = {
        "summary": summary,
        "context": {
            "decisions": decisions or [],
            "risks": risks or [],
            "notes": [f"note-for-{phase.value.lower()}"],
        },
        "artifacts": artifacts or [],
    }
    task = Task(
        ticket_id=ticket_id,
        phase_id=phase.value,
        task_type=f"{phase.value.lower()}_task",
        description=f"{phase.name.title()} task",
        priority="MEDIUM",
        status="completed",
        result=payload,
    )
    session.add(task)
    session.flush()
    session.refresh(task)
    return task


def test_aggregate_phase_context(db_service: DatabaseService):
    """Context aggregation should include tasks, decisions, risks, and artifacts."""
    service = ContextService(db_service)
    with db_service.get_session() as session:
        ticket = _create_ticket(session)
        _create_completed_task(
            session,
            ticket.id,
            Phase.REQUIREMENTS,
            summary="Validated authentication scope",
            decisions=["Adopt OAuth2", "Document non-functional requirements"],
            risks=["Token leakage"],
            artifacts=[{"type": "doc", "path": "/tmp/auth.md"}],
        )
        _create_completed_task(
            session,
            ticket.id,
            Phase.REQUIREMENTS,
            summary="Outlined data contracts",
            decisions=["Introduce schema registry"],
            risks=[],
        )

    phase_context = service.aggregate_phase_context(ticket.id, Phase.REQUIREMENTS.value)
    assert phase_context["phase_id"] == Phase.REQUIREMENTS.value
    assert len(phase_context["tasks"]) == 2
    assert "Adopt OAuth2" in phase_context["decisions"]
    assert "Token leakage" in phase_context["risks"]
    assert phase_context["artifacts"][0]["type"] == "doc"
    assert "Outlined data contracts" in phase_context["summary"]


def test_summarize_context():
    """Structured context should be summarized with key points."""
    summarizer = ContextSummarizer()
    context = {
        "phases": {
            Phase.REQUIREMENTS.value: {
                "summary": "Requirements captured",
                "decisions": ["Use feature flags"],
                "risks": ["Scope creep"],
                "tasks": [
                    {
                        "task_id": "t1",
                        "task_type": "analysis",
                        "summary": "Captured requirements",
                    }
                ],
            }
        }
    }
    summary = summarizer.summarize_structured(context)
    assert "PHASE_REQUIREMENTS" in summary
    assert "Use feature flags" in summary
    assert "Scope creep" in summary
    key_points = summarizer.extract_key_points(context)
    assert any("decision" in point.lower() for point in key_points)


def test_get_context_for_phase(db_service: DatabaseService):
    """Context retrieval should include prior phases only."""
    service = ContextService(db_service)
    with db_service.get_session() as session:
        ticket = _create_ticket(session, Phase.DESIGN)
        _create_completed_task(
            session,
            ticket.id,
            Phase.REQUIREMENTS,
            summary="Requirement baseline locked",
            decisions=["Freeze MVP scope"],
        )
        _create_completed_task(
            session,
            ticket.id,
            Phase.DESIGN,
            summary="Drafted architecture options",
            decisions=["Adopt event-driven design"],
        )

    service.update_ticket_context(ticket.id, Phase.REQUIREMENTS.value)
    service.update_ticket_context(ticket.id, Phase.DESIGN.value)

    prior_context = service.get_context_for_phase(ticket.id, Phase.IMPLEMENTATION.value)
    assert Phase.REQUIREMENTS.value in prior_context["phases"]
    assert Phase.DESIGN.value in prior_context["phases"]
    assert Phase.IMPLEMENTATION.value not in prior_context["phases"]
    assert "event-driven" in repr(prior_context).lower()


def test_update_ticket_context(db_service: DatabaseService):
    """Updating ticket context should persist JSON fields and summaries."""
    service = ContextService(db_service)
    with db_service.get_session() as session:
        ticket = _create_ticket(session)
        _create_completed_task(
            session,
            ticket.id,
            Phase.REQUIREMENTS,
            summary="Finished discovery",
            decisions=["Prioritize latency"],
            artifacts=[{"type": "diagram", "path": "/tmp/diagram.png"}],
        )

    service.update_ticket_context(ticket.id, Phase.REQUIREMENTS.value)

    with db_service.get_session() as session:
        refreshed = session.get(Ticket, ticket.id)
        assert refreshed is not None
        assert refreshed.context is not None
        phases = refreshed.context.get("phases", {})
        assert Phase.REQUIREMENTS.value in phases
        assert refreshed.context_summary
        phase_records = (
            session.query(PhaseContext)
            .filter(
                PhaseContext.ticket_id == ticket.id,
                PhaseContext.phase_id == Phase.REQUIREMENTS.value,
            )
            .all()
        )
        assert phase_records, "Phase context rows should be persisted"
