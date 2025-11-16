"""Tests for PhaseHistory model and relationships."""

from datetime import datetime, timedelta

from omoi_os.models.phase_history import PhaseHistory
from omoi_os.models.phases import Phase
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService


def test_create_phase_history(db_service: DatabaseService, sample_ticket: Ticket):
    """Test creating a phase history record."""
    with db_service.get_session() as session:
        history = PhaseHistory(
            ticket_id=sample_ticket.id,
            from_phase=Phase.REQUIREMENTS.value,
            to_phase=Phase.DESIGN.value,
            transition_reason="Requirements approved",
            transitioned_by="agent-123",
            artifacts={"spec_summary": "approved"},
        )
        session.add(history)
        session.flush()
        session.refresh(history)
        session.expunge(history)

    assert history.id is not None
    assert history.from_phase == Phase.REQUIREMENTS.value
    assert history.to_phase == Phase.DESIGN.value
    assert history.transitioned_by == "agent-123"


def test_phase_history_relationships(db_service: DatabaseService, sample_ticket: Ticket):
    """Test phase history relationship to ticket."""
    with db_service.get_session() as session:
        history = PhaseHistory(
            ticket_id=sample_ticket.id,
            from_phase=Phase.REQUIREMENTS.value,
            to_phase=Phase.DESIGN.value,
            transition_reason="Design kickoff",
            transitioned_by="agent-321",
        )
        session.add(history)
        session.commit()

        refreshed_ticket = session.get(Ticket, sample_ticket.id)
        assert refreshed_ticket is not None
        assert len(refreshed_ticket.phase_history) == 1
        assert refreshed_ticket.phase_history[0].transition_reason == "Design kickoff"


def test_phase_history_timestamps(db_service: DatabaseService, sample_ticket: Ticket):
    """Test phase history timestamp tracking."""
    with db_service.get_session() as session:
        history = PhaseHistory(
            ticket_id=sample_ticket.id,
            from_phase=Phase.REQUIREMENTS.value,
            to_phase=Phase.DESIGN.value,
            transition_reason="Timestamp validation",
            transitioned_by="agent-abc",
        )
        session.add(history)
        session.commit()
        session.refresh(history)

        now = datetime.utcnow() + timedelta(seconds=5)
        assert history.created_at <= now
        assert history.created_at >= datetime.utcnow() - timedelta(minutes=5)



