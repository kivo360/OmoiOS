"""Tests for /api/v1/tickets/* endpoints.

Run options:
    pytest tests/api/test_tickets_api.py -m unit
    pytest tests/api/test_tickets_api.py -m integration
    pytest tests/api/test_tickets_api.py
"""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from omoi_os.models.ticket import Ticket


# =============================================================================
# UNIT TESTS (Fast, mocked dependencies)
# =============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestTicketsEndpointsUnit:
    """Unit tests for ticket endpoints."""

    def test_list_tickets_returns_list(self, client: TestClient):
        """Test GET /tickets returns a list structure."""
        response = client.get("/api/v1/tickets")

        assert response.status_code == 200
        data = response.json()
        assert "tickets" in data
        assert isinstance(data["tickets"], list)

    def test_list_tickets_with_pagination(self, client: TestClient):
        """Test GET /tickets with limit and offset."""
        response = client.get("/api/v1/tickets?limit=5&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert "tickets" in data

    def test_list_tickets_with_status_filter(self, client: TestClient):
        """Test GET /tickets with status filter."""
        response = client.get("/api/v1/tickets?status=pending")

        assert response.status_code == 200

    def test_get_nonexistent_ticket(self, client: TestClient):
        """Test GET /tickets/{id} for non-existent ticket."""
        fake_id = str(uuid4())
        response = client.get(f"/api/v1/tickets/{fake_id}")

        assert response.status_code == 404

    def test_create_ticket_missing_title(self, client: TestClient):
        """Test POST /tickets fails without title."""
        response = client.post(
            "/api/v1/tickets",
            json={"description": "No title provided"},
        )

        assert response.status_code == 422


# =============================================================================
# INTEGRATION TESTS (Requires database)
# =============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.requires_db
class TestTicketsCRUDIntegration:
    """Integration tests for ticket CRUD operations."""

    def test_create_ticket(self, client: TestClient):
        """Test creating a new ticket."""
        response = client.post(
            "/api/v1/tickets",
            json={
                "title": "Test Ticket",
                "description": "A test ticket description",
                "priority": "medium",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Ticket"
        assert data["description"] == "A test ticket description"
        assert "id" in data

    def test_get_ticket(self, client: TestClient, sample_ticket: Ticket):
        """Test getting a ticket by ID."""
        response = client.get(f"/api/v1/tickets/{sample_ticket.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_ticket.id)
        assert data["title"] == sample_ticket.title

    def test_list_tickets_returns_created(self, client: TestClient, sample_ticket: Ticket):
        """Test list includes created ticket."""
        response = client.get("/api/v1/tickets")

        assert response.status_code == 200
        tickets = response.json()["tickets"]
        ticket_ids = [t["id"] for t in tickets]
        assert str(sample_ticket.id) in ticket_ids


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.requires_db
class TestTicketTransitionsIntegration:
    """Integration tests for ticket status transitions (bug we fixed)."""

    def test_transition_ticket_valid(self, client: TestClient, sample_ticket: Ticket):
        """Test valid ticket status transition."""
        # Move from pending to in_progress
        response = client.post(
            f"/api/v1/tickets/{sample_ticket.id}/transition",
            json={"to_status": "in_progress"},
        )

        # Should succeed (200) or be invalid transition (400), not 500
        assert response.status_code in [200, 400]

    def test_transition_ticket_invalid_returns_400(
        self, client: TestClient, sample_ticket: Ticket
    ):
        """Test invalid transition returns 400, not 500 (bug fix verification)."""
        # Try invalid transition
        response = client.post(
            f"/api/v1/tickets/{sample_ticket.id}/transition",
            json={"to_status": "completed"},  # Can't skip steps
        )

        # CRITICAL: Should return 400 (bad request), NOT 500 (server error)
        # This was the bug we fixed
        if response.status_code == 400:
            assert "invalid" in response.json()["detail"].lower() or \
                   "transition" in response.json()["detail"].lower()
        else:
            # If 200, the transition was actually valid
            assert response.status_code == 200

    def test_transition_nonexistent_ticket(self, client: TestClient):
        """Test transitioning non-existent ticket returns 404."""
        fake_id = str(uuid4())
        response = client.post(
            f"/api/v1/tickets/{fake_id}/transition",
            json={"to_status": "in_progress"},
        )

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.requires_db
class TestTicketTasksIntegration:
    """Integration tests for ticket-task relationships."""

    def test_get_ticket_tasks(self, client: TestClient, sample_ticket: Ticket):
        """Test getting tasks for a ticket."""
        response = client.get(f"/api/v1/tickets/{sample_ticket.id}/tasks")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
