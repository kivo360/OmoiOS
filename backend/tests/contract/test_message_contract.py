"""
Contract tests for message queue API schemas.
These verify request/response schemas match expected API contract WITHOUT running server.

Phase 2.2 from implementation checklist.
"""

import pytest


@pytest.mark.contract
class TestMessageEndpointContract:
    """Test API contract without HTTP layer."""

    def test_post_message_request_schema(self):
        """CONTRACT: POST request must have content field."""
        from omoi_os.api.routes.sandbox import SandboxMessage

        schema = SandboxMessage.model_json_schema()
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        # content is required
        assert "content" in required
        # message_type has default, so not required but must exist
        assert "message_type" in properties

    def test_post_message_response_schema(self):
        """CONTRACT: POST response must have status and message_id."""
        from omoi_os.api.routes.sandbox import MessageQueueResponse

        schema = MessageQueueResponse.model_json_schema()
        properties = schema.get("properties", {})

        assert "status" in properties
        assert "message_id" in properties
        assert "sandbox_id" in properties

    def test_get_messages_returns_list_items(self):
        """CONTRACT: GET should return list of message objects with required fields."""
        from omoi_os.api.routes.sandbox import MessageItem

        schema = MessageItem.model_json_schema()
        properties = schema.get("properties", {})

        assert "id" in properties
        assert "content" in properties
        assert "message_type" in properties
        assert "timestamp" in properties

    def test_message_type_enum_values(self):
        """CONTRACT: message_type should accept expected values."""
        from omoi_os.api.routes.sandbox import SandboxMessage

        # All valid types should work
        valid_types = ["user_message", "interrupt", "guardian_nudge", "system"]

        for msg_type in valid_types:
            msg = SandboxMessage(content="test", message_type=msg_type)
            assert msg.message_type == msg_type
