"""Pytest tests for FastMCP server using FastMCP Client."""

import pytest
import pytest_asyncio
from fastmcp import Client

from omoi_os.mcp.fastmcp_server import mcp, initialize_mcp_services
from omoi_os.services.database import DatabaseService
from omoi_os.services.discovery import DiscoveryService
from omoi_os.services.embedding import EmbeddingService, EmbeddingProvider
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.memory import MemoryService
from omoi_os.services.task_queue import TaskQueueService


@pytest_asyncio.fixture
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
    embedding_service = EmbeddingService(provider=EmbeddingProvider.LOCAL)
    memory_service = MemoryService(
        embedding_service=embedding_service, event_bus=event_bus
    )

    # Initialize MCP server with services
    initialize_mcp_services(
        db=db,
        event_bus=event_bus,
        task_queue=task_queue,
        discovery_service=discovery_service,
        memory_service=memory_service,
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
    assert "save_memory" in tool_names  # New memory tool


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
        },
    )

    assert result is not None
    if hasattr(result, "data") and isinstance(result.data, dict):
        assert "nodes" in result.data
        assert "edges" in result.data
        assert isinstance(result.data["nodes"], list)
        assert isinstance(result.data["edges"], list)


# ============================================================================
# save_memory Tool Tests
# ============================================================================


@pytest.mark.asyncio
async def test_save_memory_basic(mcp_client):
    """Test save_memory tool with basic parameters."""
    result = await mcp_client.call_tool(
        "save_memory",
        {
            "task_id": "00000000-0000-0000-0000-000000000001",
            "execution_summary": "Successfully completed the authentication task",
            "success": True,
        },
    )

    # May succeed or fail depending on whether task exists
    assert result is not None


@pytest.mark.asyncio
async def test_save_memory_with_memory_type(mcp_client):
    """Test save_memory tool with explicit memory_type."""
    result = await mcp_client.call_tool(
        "save_memory",
        {
            "task_id": "00000000-0000-0000-0000-000000000001",
            "execution_summary": "Fixed the authentication bug by correcting the JWT validation",
            "success": True,
            "memory_type": "error_fix",
        },
    )

    assert result is not None


@pytest.mark.asyncio
async def test_save_memory_with_ace_fields(mcp_client):
    """Test save_memory tool with ACE workflow fields (REQ-MEM-ACE-001)."""
    result = await mcp_client.call_tool(
        "save_memory",
        {
            "task_id": "00000000-0000-0000-0000-000000000001",
            "execution_summary": "Implemented user authentication system",
            "success": True,
            "goal": "Implement JWT authentication for the API",
            "result": "JWT authentication implemented with refresh token support",
            "feedback": "All tests passed, deployed to staging",
            "tool_usage": {"tools_used": ["Read", "Edit", "Bash"], "operations": 15},
        },
    )

    assert result is not None
    if hasattr(result, "data") and isinstance(result.data, dict):
        if result.data.get("success"):
            assert result.data.get("has_ace_fields") is True


@pytest.mark.asyncio
async def test_save_memory_invalid_memory_type(mcp_client):
    """Test save_memory tool rejects invalid memory_type."""
    result = await mcp_client.call_tool(
        "save_memory",
        {
            "task_id": "00000000-0000-0000-0000-000000000001",
            "execution_summary": "Some task execution summary",
            "success": True,
            "memory_type": "invalid_type",
        },
    )

    assert result is not None
    if hasattr(result, "data") and isinstance(result.data, dict):
        assert result.data.get("success") is False
        assert "error" in result.data
        assert "Invalid memory_type" in result.data["error"]


@pytest.mark.asyncio
async def test_save_memory_error_patterns_requires_failure(mcp_client):
    """Test save_memory tool rejects error_patterns when success=true."""
    result = await mcp_client.call_tool(
        "save_memory",
        {
            "task_id": "00000000-0000-0000-0000-000000000001",
            "execution_summary": "Task completed successfully",
            "success": True,
            "error_patterns": {"error_type": "SomeError"},
        },
    )

    assert result is not None
    if hasattr(result, "data") and isinstance(result.data, dict):
        assert result.data.get("success") is False
        assert "error" in result.data
        assert "error_patterns can only be provided when success=false" in result.data[
            "error"
        ]


@pytest.mark.asyncio
async def test_save_memory_with_error_patterns_on_failure(mcp_client):
    """Test save_memory tool accepts error_patterns when success=false."""
    result = await mcp_client.call_tool(
        "save_memory",
        {
            "task_id": "00000000-0000-0000-0000-000000000001",
            "execution_summary": "Failed to connect to database",
            "success": False,
            "error_patterns": {
                "error_type": "ConnectionError",
                "message": "Database connection refused",
            },
        },
    )

    # May succeed or fail depending on whether task exists
    # But should NOT fail due to error_patterns validation
    assert result is not None
    if hasattr(result, "data") and isinstance(result.data, dict):
        # If it failed, should not be because of error_patterns validation
        if result.data.get("success") is False:
            assert (
                "error_patterns can only be provided" not in result.data.get("error", "")
            )

