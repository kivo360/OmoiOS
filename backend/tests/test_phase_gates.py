"""Tests for phase gate validation service."""

from __future__ import annotations

from typing import Any

from omoi_os.models.phase_gate_artifact import PhaseGateArtifact
from omoi_os.models.ticket import Ticket
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.phase_gate import PhaseGateService

PHASE_REQUIREMENTS = "PHASE_REQUIREMENTS"


def _create_ticket(session, title: str = "Gate Test Ticket") -> Ticket:
    ticket = Ticket(
        title=title,
        description="Ticket used for gate testing",
        phase_id=PHASE_REQUIREMENTS,
        status="pending",
        priority="HIGH",
    )
    session.add(ticket)
    session.flush()
    session.refresh(ticket)
    session.expunge(ticket)
    return ticket


def _add_completed_task(
    session, ticket_id: str, result: dict[str, Any] | None = None
) -> Task:
    task = Task(
        ticket_id=ticket_id,
        phase_id=PHASE_REQUIREMENTS,
        task_type="analyze_requirements",
        description="Completed task for gate checks",
        priority="HIGH",
        status="completed",
        result=result,
    )
    session.add(task)
    session.flush()
    session.refresh(task)
    session.expunge(task)
    return task


def _create_artifact(
    session,
    ticket_id: str,
    artifact_type: str = "requirements_document",
    length: int = 600,
) -> PhaseGateArtifact:
    artifact = PhaseGateArtifact(
        ticket_id=ticket_id,
        phase_id=PHASE_REQUIREMENTS,
        artifact_type=artifact_type,
        artifact_content={
            "length": length,
            "sections": ["scope", "acceptance_criteria"],
        },
        collected_by="agent-alpha",
    )
    session.add(artifact)
    session.flush()
    session.refresh(artifact)
    session.expunge(artifact)
    return artifact


def test_check_gate_requirements_met(db_service: DatabaseService):
    """Gate requirements pass when artifacts and completed tasks exist."""
    service = PhaseGateService(db_service)
    with db_service.get_session() as session:
        ticket = _create_ticket(session)
        _add_completed_task(session, ticket.id)
        _create_artifact(session, ticket.id)

    result = service.check_gate_requirements(ticket.id, PHASE_REQUIREMENTS)
    assert result["requirements_met"] is True
    assert result["missing_artifacts"] == []
    assert result["validation_status"] == "ready"


def test_check_gate_requirements_missing(db_service: DatabaseService):
    """Missing artifacts or incomplete tasks block phase gates."""
    service = PhaseGateService(db_service)
    with db_service.get_session() as session:
        ticket = _create_ticket(session)
        session.commit()

    result = service.check_gate_requirements(ticket.id, PHASE_REQUIREMENTS)
    assert result["requirements_met"] is False
    assert result["validation_status"] == "blocked"
    assert "requirements_document" in result["missing_artifacts"]


def test_collect_artifacts(db_service: DatabaseService):
    """Artifacts are collected from completed task payloads."""
    service = PhaseGateService(db_service)
    with db_service.get_session() as session:
        ticket = _create_ticket(session)
        task_result = {
            "artifacts": [
                {
                    "type": "requirements_document",
                    "path": "/tmp/req.md",
                    "content": {
                        "length": 650,
                        "sections": ["scope", "acceptance_criteria"],
                    },
                    "collected_by": "agent-beta",
                }
            ]
        }
        _add_completed_task(session, ticket.id, task_result)

    artifacts = service.collect_artifacts(ticket.id, PHASE_REQUIREMENTS)
    assert len(artifacts) == 1
    assert artifacts[0].artifact_type == "requirements_document"
    assert artifacts[0].artifact_path == "/tmp/req.md"


def test_validate_gate_passed(db_service: DatabaseService):
    """Gate validation records passed status when all criteria met."""
    service = PhaseGateService(db_service)
    with db_service.get_session() as session:
        ticket = _create_ticket(session)
        _add_completed_task(session, ticket.id)
        _create_artifact(
            session,
            ticket.id,
            length=700,
        )

    result = service.validate_gate(ticket.id, PHASE_REQUIREMENTS)
    assert result.gate_status == "passed"
    assert result.blocking_reasons in (None, [])


def test_validate_gate_failed(db_service: DatabaseService):
    """Gate validation records failure with blocking reasons."""
    service = PhaseGateService(db_service)
    with db_service.get_session() as session:
        ticket = _create_ticket(session)
        _add_completed_task(session, ticket.id)
        _create_artifact(
            session,
            ticket.id,
            length=100,  # too short for requirement
        )

    result = service.validate_gate(ticket.id, PHASE_REQUIREMENTS)
    assert result.gate_status == "failed"
    assert result.blocking_reasons
    assert any("length" in reason for reason in result.blocking_reasons)


def test_can_transition_when_gate_passed(db_service: DatabaseService):
    """Tickets can transition when current phase gate passes."""
    service = PhaseGateService(db_service)
    with db_service.get_session() as session:
        ticket = _create_ticket(session)
        _add_completed_task(session, ticket.id)
        _create_artifact(session, ticket.id)

    can_transition, reasons = service.can_transition(ticket.id, "PHASE_DESIGN")
    assert can_transition is True
    assert reasons == []


def test_can_transition_when_gate_failed(db_service: DatabaseService):
    """Tickets cannot transition when gate fails."""
    service = PhaseGateService(db_service)
    with db_service.get_session() as session:
        ticket = _create_ticket(session)
        _add_completed_task(session, ticket.id)
        _create_artifact(
            session,
            ticket.id,
            length=120,
        )

    can_transition, reasons = service.can_transition(ticket.id, "PHASE_DESIGN")
    assert can_transition is False
    assert reasons
