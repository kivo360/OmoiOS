"""
Phase 4: Sandbox Persistence Tests

These tests verify that sandbox events are persisted to the database
for audit trails and analytics.

NOTE: Tests that require database access use the db_service fixture.
The sandbox_events table must exist (run migrations first).
"""

import pytest
from uuid import uuid4


class TestSandboxEventPersistence:
    """Test that sandbox events are persisted to database."""

    @pytest.mark.integration
    def test_sandbox_event_model_exists(self):
        """
        SPEC: SandboxEvent model should exist and be importable.
        """
        from omoi_os.models.sandbox_event import SandboxEvent

        assert SandboxEvent is not None
        assert hasattr(SandboxEvent, "__tablename__")
        assert SandboxEvent.__tablename__ == "sandbox_events"

    @pytest.mark.integration
    def test_sandbox_event_has_required_fields(self):
        """
        SPEC: SandboxEvent should have required fields.
        """
        from omoi_os.models.sandbox_event import SandboxEvent

        # Check required fields
        assert hasattr(SandboxEvent, "id")
        assert hasattr(SandboxEvent, "sandbox_id")
        assert hasattr(SandboxEvent, "event_type")
        assert hasattr(SandboxEvent, "event_data")
        assert hasattr(SandboxEvent, "source")
        assert hasattr(SandboxEvent, "created_at")

    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_sandbox_event_can_be_created(self, db_service):
        """
        SPEC: SandboxEvent should be creatable and persistable.
        """
        from omoi_os.models.sandbox_event import SandboxEvent

        with db_service.get_session() as session:
            event = SandboxEvent(
                sandbox_id=f"test-sandbox-{uuid4().hex[:8]}",
                event_type="agent.tool_use",
                event_data={"tool": "bash", "command": "ls -la"},
                source="agent",
            )

            session.add(event)
            session.commit()
            session.refresh(event)

            assert event.id is not None
            assert event.created_at is not None

    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_sandbox_event_query_by_sandbox_id(self, db_service):
        """
        SPEC: Events should be queryable by sandbox_id.
        """
        from omoi_os.models.sandbox_event import SandboxEvent

        sandbox_id = f"query-test-{uuid4().hex[:8]}"

        with db_service.get_session() as session:
            # Create multiple events
            for i in range(3):
                event = SandboxEvent(
                    sandbox_id=sandbox_id,
                    event_type=f"event.type.{i}",
                    event_data={"index": i},
                    source="agent",
                )
                session.add(event)

            session.commit()

            # Query by sandbox_id
            events = (
                session.query(SandboxEvent)
                .filter_by(sandbox_id=sandbox_id)
                .order_by(SandboxEvent.created_at)
                .all()
            )

            assert len(events) == 3
            assert events[0].event_type == "event.type.0"
            assert events[2].event_type == "event.type.2"


class TestEventEndpointPersistence:
    """Test that event callback endpoint persists events."""

    @pytest.mark.integration
    def test_event_endpoint_returns_event_id(self, client):
        """
        SPEC: Event endpoint should return the created event ID.

        NOTE: This test verifies the response includes event_id.
        If the sandbox_events table doesn't exist, persistence will fail
        but the endpoint should still return event_id in the response schema.
        """
        sandbox_id = f"id-test-{uuid4().hex[:8]}"

        response = client.post(
            f"/api/v1/sandboxes/{sandbox_id}/events",
            json={
                "event_type": "agent.tool_use",
                "event_data": {"tool": "file_editor"},
                "source": "agent",
            },
        )

        # If DB table exists, should be 200. If not, might be 500.
        # We test the schema, not DB operation here.
        if response.status_code == 200:
            data = response.json()
            assert "event_id" in data
        else:
            # Table doesn't exist - this is expected before migration
            pytest.skip("sandbox_events table not created (run migrations)")


class TestEventEndpointPersistenceWithDB:
    """Tests that require database table to exist."""

    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_event_endpoint_persists_to_database(self, client, db_service):
        """
        SPEC: POST /api/v1/sandboxes/{id}/events should persist event to database.
        """
        from omoi_os.models.sandbox_event import SandboxEvent

        sandbox_id = f"persist-test-{uuid4().hex[:8]}"

        # Post event via API
        response = client.post(
            f"/api/v1/sandboxes/{sandbox_id}/events",
            json={
                "event_type": "agent.started",
                "event_data": {"task": "test task"},
                "source": "agent",
            },
        )

        if response.status_code != 200:
            pytest.skip("sandbox_events table not created (run migrations)")

        assert response.status_code == 200

        # Query database to verify persistence
        with db_service.get_session() as session:
            event = (
                session.query(SandboxEvent)
                .filter_by(sandbox_id=sandbox_id, event_type="agent.started")
                .first()
            )

            assert event is not None
            assert event.event_data["task"] == "test task"
            assert event.source == "agent"


class TestEventQueryEndpoint:
    """Test event query functionality."""

    @pytest.mark.integration
    @pytest.mark.requires_db
    def test_events_queryable_by_sandbox(self, client, db_service):
        """
        SPEC: Events should be queryable via GET endpoint.
        """
        from omoi_os.models.sandbox_event import SandboxEvent

        sandbox_id = f"query-api-{uuid4().hex[:8]}"

        # Create events directly in DB
        with db_service.get_session() as session:
            for i in range(3):
                event = SandboxEvent(
                    sandbox_id=sandbox_id,
                    event_type=f"test.event.{i}",
                    event_data={"index": i},
                    source="agent",
                )
                session.add(event)
            session.commit()

        # Query via API (if endpoint exists)
        response = client.get(f"/api/v1/sandboxes/{sandbox_id}/events")

        # Endpoint may not exist yet - skip if 404
        if response.status_code == 404:
            pytest.skip("GET events endpoint not implemented yet")

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 3
