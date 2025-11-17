"""Tests for collaboration service."""

import pytest

from omoi_os.services.collaboration import CollaborationService
from tests.test_helpers import create_test_agent, create_test_task, create_test_ticket


@pytest.fixture
def collaboration_service(db_service, event_bus_service):
    """Create collaboration service instance."""
    return CollaborationService(db_service, event_bus_service)


class TestThreadManagement:
    """Tests for collaboration thread management."""

    def test_create_thread(self, collaboration_service, db_service):
        """Test creating a collaboration thread."""
        agent1 = create_test_agent(db_service, agent_type="worker")
        agent2 = create_test_agent(db_service, agent_type="worker")

        thread = collaboration_service.create_thread(
            thread_type="consultation",
            participants=[agent1.id, agent2.id],
        )

        assert thread.id is not None
        assert thread.thread_type == "consultation"
        assert agent1.id in thread.participants
        assert agent2.id in thread.participants
        assert thread.status == "active"

    def test_create_thread_with_context(self, collaboration_service, db_service):
        """Test creating thread with ticket/task context."""
        agent1 = create_test_agent(db_service)
        ticket = create_test_ticket(db_service)
        task = create_test_task(db_service, ticket_id=ticket.id)

        thread = collaboration_service.create_thread(
            thread_type="review",
            participants=[agent1.id],
            ticket_id=ticket.id,
            task_id=task.id,
        )

        assert thread.ticket_id == ticket.id
        assert thread.task_id == task.id

    def test_close_thread(self, collaboration_service, db_service):
        """Test closing a thread."""
        agent1 = create_test_agent(db_service)
        thread = collaboration_service.create_thread(
            thread_type="handoff",
            participants=[agent1.id],
        )

        success = collaboration_service.close_thread(thread.id)
        assert success is True

        # Verify thread is closed
        updated_thread = collaboration_service.get_thread(thread.id)
        assert updated_thread.status == "resolved"
        assert updated_thread.closed_at is not None

    def test_list_threads(self, collaboration_service, db_service):
        """Test listing threads with filters."""
        agent1 = create_test_agent(db_service)
        agent2 = create_test_agent(db_service)
        ticket = create_test_ticket(db_service)

        # Create multiple threads
        thread1 = collaboration_service.create_thread(
            thread_type="handoff",
            participants=[agent1.id, agent2.id],
            ticket_id=ticket.id,
        )
        collaboration_service.create_thread(
            thread_type="review",
            participants=[agent1.id],
            ticket_id=ticket.id,
        )

        # List all threads for ticket
        threads = collaboration_service.list_threads(ticket_id=ticket.id)
        assert len(threads) == 2

        # Filter by participant
        threads = collaboration_service.list_threads(agent_id=agent2.id)
        assert len(threads) == 1
        assert threads[0].id == thread1.id


class TestMessaging:
    """Tests for agent messaging."""

    def test_send_message(self, collaboration_service, db_service):
        """Test sending a message in a thread."""
        agent1 = create_test_agent(db_service)
        agent2 = create_test_agent(db_service)
        thread = collaboration_service.create_thread(
            thread_type="consultation",
            participants=[agent1.id, agent2.id],
        )

        message = collaboration_service.send_message(
            thread_id=thread.id,
            from_agent_id=agent1.id,
            to_agent_id=agent2.id,
            message_type="question",
            content="How should we handle this edge case?",
        )

        assert message.id is not None
        assert message.thread_id == thread.id
        assert message.from_agent_id == agent1.id
        assert message.to_agent_id == agent2.id
        assert message.message_type == "question"
        assert message.read_at is None

    def test_get_thread_messages(self, collaboration_service, db_service):
        """Test retrieving thread messages."""
        agent1 = create_test_agent(db_service)
        thread = collaboration_service.create_thread(
            thread_type="discussion",
            participants=[agent1.id],
        )

        # Send multiple messages
        msg1 = collaboration_service.send_message(
            thread_id=thread.id,
            from_agent_id=agent1.id,
            message_type="info",
            content="Message 1",
        )
        msg2 = collaboration_service.send_message(
            thread_id=thread.id,
            from_agent_id=agent1.id,
            message_type="info",
            content="Message 2",
        )

        messages = collaboration_service.get_thread_messages(thread.id)
        assert len(messages) == 2
        # Should be in reverse chronological order (newest first)
        assert messages[0].id == msg2.id
        assert messages[1].id == msg1.id

    def test_mark_message_read(self, collaboration_service, db_service):
        """Test marking a message as read."""
        agent1 = create_test_agent(db_service)
        thread = collaboration_service.create_thread(
            thread_type="notification",
            participants=[agent1.id],
        )

        message = collaboration_service.send_message(
            thread_id=thread.id,
            from_agent_id=agent1.id,
            message_type="info",
            content="Test message",
        )

        success = collaboration_service.mark_message_read(message.id)
        assert success is True

        # Get updated message
        messages = collaboration_service.get_thread_messages(thread.id)
        assert messages[0].read_at is not None


class TestHandoffProtocol:
    """Tests for task handoff protocol."""

    def test_request_handoff(self, collaboration_service, db_service):
        """Test requesting a task handoff."""
        agent1 = create_test_agent(db_service)
        agent2 = create_test_agent(db_service)
        ticket = create_test_ticket(db_service)
        task = create_test_task(db_service, ticket_id=ticket.id)

        thread, message = collaboration_service.request_handoff(
            from_agent_id=agent1.id,
            to_agent_id=agent2.id,
            task_id=task.id,
            reason="Requires expertise in area X",
        )

        assert thread.thread_type == "handoff"
        assert agent1.id in thread.participants
        assert agent2.id in thread.participants
        assert thread.task_id == task.id
        assert message.message_type == "handoff_request"
        assert message.to_agent_id == agent2.id

    def test_accept_handoff(self, collaboration_service, db_service):
        """Test accepting a handoff request."""
        agent1 = create_test_agent(db_service)
        agent2 = create_test_agent(db_service)
        ticket = create_test_ticket(db_service)
        task = create_test_task(db_service, ticket_id=ticket.id)

        thread, request_msg = collaboration_service.request_handoff(
            from_agent_id=agent1.id,
            to_agent_id=agent2.id,
            task_id=task.id,
            reason="Need help",
        )

        response = collaboration_service.accept_handoff(
            thread_id=thread.id,
            accepting_agent_id=agent2.id,
        )

        assert response.message_type == "handoff_accepted"
        assert response.from_agent_id == agent2.id

    def test_decline_handoff(self, collaboration_service, db_service):
        """Test declining a handoff request."""
        agent1 = create_test_agent(db_service)
        agent2 = create_test_agent(db_service)
        ticket = create_test_ticket(db_service)
        task = create_test_task(db_service, ticket_id=ticket.id)

        thread, request_msg = collaboration_service.request_handoff(
            from_agent_id=agent1.id,
            to_agent_id=agent2.id,
            task_id=task.id,
            reason="Need help",
        )

        response = collaboration_service.decline_handoff(
            thread_id=thread.id,
            declining_agent_id=agent2.id,
            reason="Currently at capacity",
        )

        assert response.message_type == "handoff_declined"
        assert response.from_agent_id == agent2.id
        assert "capacity" in response.content

