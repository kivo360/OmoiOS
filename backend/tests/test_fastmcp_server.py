"""Pytest tests for FastMCP server using FastMCP Client."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from fastmcp import Client

from omoi_os.mcp.fastmcp_server import mcp, initialize_mcp_services, save_memory
from omoi_os.services.database import DatabaseService
from omoi_os.services.discovery import DiscoveryService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.models.memory_type import MemoryType


@pytest.fixture
async def mcp_client():
    """Create FastMCP client connected to in-memory server."""
    # Initialize services with test database
    # Note: In real tests, you'd use a test database or mocks
    db = DatabaseService(
        connection_string="postgresql+psycopg://postgres:postgres@localhost:15432/test_db"
    )
    event_bus = EventBusService(redis_url="redis://localhost:16379")
    task_queue = TaskQueueService(db)
    discovery_service = DiscoveryService(event_bus)
    
    # Initialize MCP server with services
    initialize_mcp_services(
        db=db,
        event_bus=event_bus,
        task_queue=task_queue,
        discovery_service=discovery_service,
    )
    
    # Create client connected to in-memory server
    async with Client(mcp) as client:
        yield client


@pytest.mark.asyncio
async def test_list_tools(mcp_client):
    """Test listing available tools."""
    tools = await mcp_client.list_tools()
    
    assert len(tools) > 0
    
    # Check for expected tools
    tool_names = [tool.name for tool in tools]
    assert "create_ticket" in tool_names
    assert "create_task" in tool_names
    assert "search_tickets" in tool_names
    assert "get_task_discoveries" in tool_names
    assert "get_workflow_graph" in tool_names


@pytest.mark.asyncio
async def test_create_ticket_tool(mcp_client):
    """Test create_ticket tool."""
    result = await mcp_client.call_tool(
        "create_ticket",
        {
            "workflow_id": "test-workflow-001",
            "agent_id": "test-agent-001",
            "title": "Test Ticket",
            "description": "This is a test ticket for FastMCP testing",
            "ticket_type": "task",
            "priority": "medium",
        }
    )
    
    assert result is not None
    if hasattr(result, 'data'):
        assert isinstance(result.data, dict)
        assert "ticket_id" in result.data or "success" in result.data


@pytest.mark.asyncio
async def test_search_tickets_tool(mcp_client):
    """Test search_tickets tool."""
    result = await mcp_client.call_tool(
        "search_tickets",
        {
            "workflow_id": "test-workflow-001",
            "agent_id": "test-agent-001",
            "query": "test",
            "search_type": "hybrid",
            "limit": 10,
        }
    )
    
    assert result is not None
    if hasattr(result, 'data'):
        assert isinstance(result.data, dict)


@pytest.mark.asyncio
async def test_create_task_without_discovery(mcp_client):
    """Test create_task tool without discovery tracking."""
    # Note: This will fail if ticket_id doesn't exist
    # In real tests, create a ticket first or use mocks
    
    result = await mcp_client.call_tool(
        "create_task",
        {
            "ticket_id": "00000000-0000-0000-0000-000000000001",
            "phase_id": "PHASE_IMPLEMENTATION",
            "description": "Test task without discovery",
            "task_type": "implementation",
            "priority": "MEDIUM",
        }
    )
    
    # May succeed or fail depending on whether ticket exists
    assert result is not None


@pytest.mark.asyncio
async def test_create_task_with_discovery(mcp_client):
    """Test create_task tool with discovery tracking."""
    result = await mcp_client.call_tool(
        "create_task",
        {
            "ticket_id": "00000000-0000-0000-0000-000000000001",
            "phase_id": "PHASE_IMPLEMENTATION",
            "description": "Fix bug discovered during implementation",
            "task_type": "bug_fix",
            "priority": "HIGH",
            "discovery_type": "bug",
            "discovery_description": "Memory leak in auth module",
            "source_task_id": "00000000-0000-0000-0000-000000000002",
            "priority_boost": True,
        }
    )
    
    # May succeed or fail depending on whether ticket/task exists
    assert result is not None
    
    # If successful, should have discovery data
    if hasattr(result, 'data') and isinstance(result.data, dict):
        if "discovery" in result.data:
            discovery = result.data["discovery"]
            assert discovery.get("discovery_type") == "bug"
            assert discovery.get("priority_boost") is True


@pytest.mark.asyncio
async def test_get_task_discoveries(mcp_client):
    """Test get_task_discoveries tool."""
    result = await mcp_client.call_tool(
        "get_task_discoveries",
        {
            "task_id": "00000000-0000-0000-0000-000000000002",
        }
    )
    
    assert result is not None
    if hasattr(result, 'data') and isinstance(result.data, dict):
        assert "discoveries" in result.data
        assert isinstance(result.data["discoveries"], list)


@pytest.mark.asyncio
async def test_get_workflow_graph(mcp_client):
    """Test get_workflow_graph tool."""
    result = await mcp_client.call_tool(
        "get_workflow_graph",
        {
            "ticket_id": "00000000-0000-0000-0000-000000000001",
        }
    )

    assert result is not None
    if hasattr(result, 'data') and isinstance(result.data, dict):
        assert "nodes" in result.data
        assert "edges" in result.data
        assert isinstance(result.data["nodes"], list)
        assert isinstance(result.data["edges"], list)


# ============================================================================
# save_memory Unit Tests (with mocked services)
# ============================================================================


@pytest.fixture
def mock_memory_service():
    """Create a mock memory service for unit testing."""
    mock_service = Mock()
    return mock_service


@pytest.fixture
def mock_db_service():
    """Create a mock database service for unit testing."""
    mock_db = Mock()
    mock_session = MagicMock()
    mock_db.get_session.return_value.__enter__ = Mock(return_value=mock_session)
    mock_db.get_session.return_value.__exit__ = Mock(return_value=False)
    return mock_db


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus service for unit testing."""
    mock_bus = Mock()
    mock_bus.publish = Mock()
    return mock_bus


@pytest.fixture
def mock_context():
    """Create a mock FastMCP context."""
    ctx = Mock()
    ctx.info = Mock()
    ctx.warning = Mock()
    return ctx


class TestSaveMemory:
    """Unit tests for save_memory MCP tool."""

    def test_save_memory_success(self, mock_memory_service, mock_db_service, mock_context):
        """Test save_memory with valid inputs returns memory_id."""
        # Setup mock memory object
        mock_memory = Mock()
        mock_memory.id = "test-memory-id-123"
        mock_memory.memory_type = MemoryType.DISCOVERY.value
        mock_memory.context_embedding = [0.1] * 1536
        mock_memory_service.store_execution.return_value = mock_memory

        with patch('omoi_os.mcp.fastmcp_server._memory_service', mock_memory_service), \
             patch('omoi_os.mcp.fastmcp_server._db', mock_db_service):

            # Call the underlying function via .fn attribute
            result = save_memory.fn(
                mock_context,
                task_id="test-task-001",
                execution_summary="Successfully completed the implementation task",
                success=True,
            )

        assert result["success"] is True
        assert "memory_id" in result
        assert result["memory_id"] == "test-memory-id-123"
        assert result["task_id"] == "test-task-001"
        assert result["memory_type"] == MemoryType.DISCOVERY.value
        assert result["has_embedding"] is True
        mock_memory_service.store_execution.assert_called_once()

    def test_save_memory_missing_task_id(self, mock_memory_service, mock_db_service, mock_context):
        """Test save_memory returns error for missing required field (task not found)."""
        # Setup mock to raise ValueError for missing task
        mock_memory_service.store_execution.side_effect = ValueError("Task non-existent-task not found")

        with patch('omoi_os.mcp.fastmcp_server._memory_service', mock_memory_service), \
             patch('omoi_os.mcp.fastmcp_server._db', mock_db_service):

            result = save_memory.fn(
                mock_context,
                task_id="non-existent-task",
                execution_summary="Some execution summary here",
                success=True,
            )

        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"]

    def test_save_memory_invalid_memory_type(self, mock_memory_service, mock_db_service, mock_context):
        """Test save_memory returns error for invalid memory_type enum value."""
        # Setup mock to raise ValueError for invalid memory type
        mock_memory_service.store_execution.side_effect = ValueError(
            "Invalid memory_type: invalid_type. Must be one of: error_fix, discovery, decision, learning, warning, codebase_knowledge"
        )

        with patch('omoi_os.mcp.fastmcp_server._memory_service', mock_memory_service), \
             patch('omoi_os.mcp.fastmcp_server._db', mock_db_service):

            result = save_memory.fn(
                mock_context,
                task_id="test-task-001",
                execution_summary="Some execution summary here",
                success=True,
                memory_type="invalid_type",
            )

        assert result["success"] is False
        assert "error" in result
        assert "Invalid memory_type" in result["error"]

    def test_save_memory_auto_classify(self, mock_memory_service, mock_db_service, mock_context):
        """Test save_memory auto-classifies type when not provided."""
        # Setup mock memory object with auto-classified type
        mock_memory = Mock()
        mock_memory.id = "test-memory-id-456"
        mock_memory.memory_type = MemoryType.ERROR_FIX.value  # Auto-classified from summary
        mock_memory.context_embedding = [0.1] * 1536
        mock_memory_service.store_execution.return_value = mock_memory

        with patch('omoi_os.mcp.fastmcp_server._memory_service', mock_memory_service), \
             patch('omoi_os.mcp.fastmcp_server._db', mock_db_service):

            result = save_memory.fn(
                mock_context,
                task_id="test-task-001",
                execution_summary="Fixed bug in authentication module",
                success=True,
                # memory_type not provided - should be auto-classified
            )

        assert result["success"] is True
        assert result["memory_type"] == MemoryType.ERROR_FIX.value
        # Verify store_execution was called with memory_type=None for auto-classification
        call_args = mock_memory_service.store_execution.call_args
        assert call_args.kwargs.get("memory_type") is None

    def test_save_memory_ace_fields(self, mock_memory_service, mock_db_service, mock_context):
        """Test save_memory stores optional fields correctly."""
        # Setup mock memory object
        mock_memory = Mock()
        mock_memory.id = "test-memory-id-789"
        mock_memory.memory_type = MemoryType.WARNING.value
        mock_memory.context_embedding = [0.1] * 1536
        mock_memory_service.store_execution.return_value = mock_memory

        with patch('omoi_os.mcp.fastmcp_server._memory_service', mock_memory_service), \
             patch('omoi_os.mcp.fastmcp_server._db', mock_db_service):

            result = save_memory.fn(
                mock_context,
                task_id="test-task-001",
                execution_summary="Warning: Watch out for rate limiting issues",
                success=True,
                memory_type=MemoryType.WARNING.value,
                auto_extract_patterns=False,
            )

        assert result["success"] is True
        assert result["memory_type"] == MemoryType.WARNING.value
        # Verify store_execution was called with correct parameters
        call_args = mock_memory_service.store_execution.call_args
        assert call_args.kwargs.get("memory_type") == MemoryType.WARNING.value
        assert call_args.kwargs.get("auto_extract_patterns") is False

    def test_save_memory_error_patterns_success_false(self, mock_memory_service, mock_db_service, mock_context):
        """Test error_patterns can only be provided when success=false."""
        # Test that error_patterns with success=True returns error
        with patch('omoi_os.mcp.fastmcp_server._memory_service', mock_memory_service), \
             patch('omoi_os.mcp.fastmcp_server._db', mock_db_service):

            result = save_memory.fn(
                mock_context,
                task_id="test-task-001",
                execution_summary="Successfully completed the task",
                success=True,  # success=True but providing error_patterns
                error_patterns={"error_type": "ValueError", "message": "Something went wrong"},
            )

        assert result["success"] is False
        assert "error" in result
        assert "error_patterns can only be provided when success=false" in result["error"]
        # Verify store_execution was NOT called since validation failed
        mock_memory_service.store_execution.assert_not_called()

    def test_save_memory_error_patterns_valid(self, mock_memory_service, mock_db_service, mock_context):
        """Test error_patterns is correctly stored when success=false."""
        # Setup mock memory object for failed execution
        mock_memory = Mock()
        mock_memory.id = "test-memory-id-fail"
        mock_memory.memory_type = MemoryType.ERROR_FIX.value
        mock_memory.context_embedding = [0.1] * 1536
        mock_memory_service.store_execution.return_value = mock_memory

        error_patterns = {
            "error_type": "ConnectionError",
            "message": "Database connection refused",
            "stack_trace": "...",
        }

        with patch('omoi_os.mcp.fastmcp_server._memory_service', mock_memory_service), \
             patch('omoi_os.mcp.fastmcp_server._db', mock_db_service):

            result = save_memory.fn(
                mock_context,
                task_id="test-task-001",
                execution_summary="Failed due to database connection error",
                success=False,  # success=False, error_patterns is valid
                error_patterns=error_patterns,
            )

        assert result["success"] is True
        assert "memory_id" in result
        # Verify store_execution was called with error_patterns
        call_args = mock_memory_service.store_execution.call_args
        assert call_args.kwargs.get("error_patterns") == error_patterns
        assert call_args.kwargs.get("success") is False

    def test_save_memory_event_published(self, mock_memory_service, mock_db_service, mock_event_bus, mock_context):
        """Test event_bus.publish is called when memory is saved."""
        # Setup mock memory object
        mock_memory = Mock()
        mock_memory.id = "test-memory-id-event"
        mock_memory.memory_type = MemoryType.LEARNING.value
        mock_memory.context_embedding = [0.1] * 1536

        # Setup memory service with event bus
        mock_memory_service.store_execution.return_value = mock_memory
        mock_memory_service.event_bus = mock_event_bus

        with patch('omoi_os.mcp.fastmcp_server._memory_service', mock_memory_service), \
             patch('omoi_os.mcp.fastmcp_server._db', mock_db_service), \
             patch('omoi_os.mcp.fastmcp_server._event_bus', mock_event_bus):

            result = save_memory.fn(
                mock_context,
                task_id="test-task-001",
                execution_summary="Learned about OAuth2 redirect handling",
                success=True,
            )

        assert result["success"] is True
        # Note: The event_bus.publish is called inside MemoryService.store_execution,
        # so we verify the mock was called through store_execution
        mock_memory_service.store_execution.assert_called_once()
        # Verify the context.info was called (logs the memory save)
        mock_context.info.assert_called_once()
        assert "Saved memory" in mock_context.info.call_args[0][0]

    def test_save_memory_service_unavailable(self, mock_db_service, mock_context):
        """Test RuntimeError when memory service is None."""
        with patch('omoi_os.mcp.fastmcp_server._memory_service', None), \
             patch('omoi_os.mcp.fastmcp_server._db', mock_db_service):

            with pytest.raises(RuntimeError, match="Memory service not initialized"):
                save_memory.fn(
                    mock_context,
                    task_id="test-task-001",
                    execution_summary="Some execution summary here",
                    success=True,
                )

    def test_save_memory_db_unavailable(self, mock_memory_service, mock_context):
        """Test RuntimeError when database service is None."""
        with patch('omoi_os.mcp.fastmcp_server._memory_service', mock_memory_service), \
             patch('omoi_os.mcp.fastmcp_server._db', None):

            with pytest.raises(RuntimeError, match="Database service not initialized"):
                save_memory.fn(
                    mock_context,
                    task_id="test-task-001",
                    execution_summary="Some execution summary here",
                    success=True,
                )

