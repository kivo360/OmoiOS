"""
Contract tests for sandbox event API schemas.
These verify request/response schemas match expected API contract WITHOUT running server.

Phase 1.2 from implementation checklist.
"""

import pytest


@pytest.mark.contract
class TestEventEndpointContract:
    """Test API contract without HTTP layer."""

    def test_request_schema_matches_api_spec(self):
        """CONTRACT: Request body must match OpenAPI spec."""
        from omoi_os.api.routes.sandbox import SandboxEventCreate

        # These fields MUST exist per API contract
        schema = SandboxEventCreate.model_json_schema()
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        # event_type is the only required field
        assert "event_type" in required

        # event_data and source have defaults, so not required but must exist
        assert "event_data" in properties
        assert "source" in properties

    def test_response_schema_matches_api_spec(self):
        """CONTRACT: Response body must match OpenAPI spec."""
        from omoi_os.api.routes.sandbox import SandboxEventResponse

        schema = SandboxEventResponse.model_json_schema()
        properties = schema.get("properties", {})

        assert "status" in properties
        assert "sandbox_id" in properties
        assert "event_type" in properties
        assert "timestamp" in properties

    def test_event_type_accepts_dotted_format(self):
        """CONTRACT: event_type should accept 'category.action' format."""
        from omoi_os.api.routes.sandbox import SandboxEventCreate

        valid_types = [
            "agent.started",
            "agent.tool_use",
            "agent.thinking",
            "agent.error",
            "heartbeat",  # Also valid without dot
        ]

        for event_type in valid_types:
            event = SandboxEventCreate(
                event_type=event_type, event_data={}, source="agent"
            )
            assert event.event_type == event_type

    def test_source_enum_values(self):
        """CONTRACT: source must be one of allowed values."""
        from omoi_os.api.routes.sandbox import SandboxEventCreate

        valid_sources = ["agent", "worker", "system"]

        for source in valid_sources:
            event = SandboxEventCreate(event_type="test", event_data={}, source=source)
            assert event.source == source
