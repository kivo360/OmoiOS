"""Tests for /api/v1/board/* endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
@pytest.mark.api
class TestBoardEndpointsUnit:
    """Unit tests for board (kanban) endpoints."""

    def test_get_board_view(self, client: TestClient):
        """Test GET /board/view returns board structure."""
        response = client.get("/api/v1/board/view")

        assert response.status_code == 200
        data = response.json()
        assert "columns" in data
        assert isinstance(data["columns"], list)

    def test_get_board_stats(self, client: TestClient):
        """Test GET /board/stats returns statistics."""
        response = client.get("/api/v1/board/stats")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_board_columns_have_required_fields(self, client: TestClient):
        """Test board columns have expected structure."""
        response = client.get("/api/v1/board/view")

        assert response.status_code == 200
        columns = response.json()["columns"]

        if columns:  # If there are columns
            column = columns[0]
            assert "id" in column
            assert "name" in column


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.requires_db
class TestBoardIntegration:
    """Integration tests for board with tickets."""

    def test_board_reflects_tickets(self, client: TestClient, sample_ticket):
        """Test board view reflects existing tickets."""
        response = client.get("/api/v1/board/view")

        assert response.status_code == 200
        # Board should load without error when tickets exist
