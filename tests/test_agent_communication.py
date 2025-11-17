"""Tests for agent-to-agent collaboration service and messaging events."""

from __future__ import annotations

from typing import Tuple
from unittest.mock import Mock

import pytest

from omoi_os.services.collaboration import CollaborationService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.database import DatabaseService


@pytest.fixture
def collaboration_service(db_service: DatabaseService) -> Tuple[CollaborationService, Mock]:
    """Create a collaboration service with a mocked event bus."""
    mock_bus = Mock(spec=EventBusService)
    service = CollaborationService(db=db_service, event_bus=mock_bus)
    return service, mock_bus


def test_create_thread_records_participants(collaboration_service):
    """Creating a thread should persist subject, context, and participants."""
    service, mock_bus = collaboration_service

    thread = service.create_thread(
        subject="Parallel execution kickoff",
        context_type="ticket",
        context_id="ticket-123",
        created_by_agent_id="agent-alpha",
        participants=["agent-alpha", "agent-beta"],
        metadata={"phase": "PHASE_IMPLEMENTATION"},
    )

    assert thread.subject == "Parallel execution kickoff"
    assert sorted(thread.participants) == ["agent-alpha", "agent-beta"]
    assert thread.context_id == "ticket-123"
    mock_bus.publish_agent_collaboration_started.assert_called_once()
    event = mock_bus.publish_agent_collaboration_started.call_args[0][0]
    assert event.thread_id == thread.id


def test_send_message_updates_last_activity(collaboration_service):
    """Sending a message should append record, update thread metadata, and emit event."""
    service, mock_bus = collaboration_service
    thread = service.create_thread(
        subject="Dependency handoff",
        context_type="task",
        context_id="task-456",
        created_by_agent_id="agent-alpha",
        participants=["agent-alpha"],
    )

    message = service.send_message(
        thread_id=thread.id,
        sender_agent_id="agent-alpha",
        body="Please take over DAG evaluation.",
        message_type="text",
        target_agent_id="agent-beta",
    )

    assert message.thread_id == thread.id
    reloaded = service.get_thread(thread.id)
    assert reloaded.last_message_at is not None
    assert "agent-beta" in reloaded.participants
    mock_bus.publish_agent_message_sent.assert_called_once()
    event = mock_bus.publish_agent_message_sent.call_args[0][0]
    assert event.message_id == message.id


def test_send_message_missing_thread_raises(collaboration_service):
    """Sending to a non-existent thread should raise error."""
    service, _ = collaboration_service
    with pytest.raises(ValueError):
        service.send_message(
            thread_id="missing",
            sender_agent_id="agent-alpha",
            body="hello",
        )


def test_list_threads_filters_by_participant(collaboration_service):
    """Listing threads should allow filtering by participant agent id."""
    service, _ = collaboration_service
    thread_a = service.create_thread(
        subject="A",
        context_type="ticket",
        context_id="ticket-1",
        created_by_agent_id="agent-alpha",
        participants=["agent-alpha", "agent-beta"],
    )
    service.create_thread(
        subject="B",
        context_type="ticket",
        context_id="ticket-2",
        created_by_agent_id="agent-gamma",
        participants=["agent-gamma"],
    )

    threads = service.list_threads(participant_agent_id="agent-beta")
    assert len(threads) == 1
    assert threads[0].id == thread_a.id


def test_request_handoff_records_capabilities(collaboration_service):
    """Requesting a handoff should persist entry and emit event."""
    service, mock_bus = collaboration_service
    thread = service.create_thread(
        subject="Need reviewer",
        context_type="ticket",
        context_id="ticket-99",
        created_by_agent_id="agent-alpha",
        participants=["agent-alpha"],
    )

    handoff = service.request_handoff(
        thread_id=thread.id,
        requesting_agent_id="agent-alpha",
        target_agent_id="agent-reviewer",
        reason="Need reviewer with TypeScript skill",
        required_capabilities=["typescript", "review"],
        task_id="task-777",
    )

    assert handoff.status == "pending"
    assert handoff.required_capabilities == ["review", "typescript"]
    mock_bus.publish_agent_handoff_requested.assert_called_once()
    event = mock_bus.publish_agent_handoff_requested.call_args[0][0]
    assert event.handoff_id == handoff.id
