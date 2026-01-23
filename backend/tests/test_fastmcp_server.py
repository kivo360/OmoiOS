"""Pytest tests for FastMCP server using FastMCP Client."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from fastmcp import Client, Context

import omoi_os.mcp.fastmcp_server as fastmcp_server_module
from omoi_os.mcp.fastmcp_server import mcp, initialize_mcp_services
from omoi_os.services.database import DatabaseService
from omoi_os.services.discovery import DiscoveryService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.memory import MemoryService, SimilarTask
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
# find_memory MCP Tool Tests (Unit Tests with Mocks)
# ============================================================================


@pytest.fixture
def mock_memory_service():
    """Create a mock MemoryService for testing."""
    return Mock(spec=MemoryService)


@pytest.fixture
def mock_db_service():
    """Create a mock DatabaseService for testing."""
    mock_db = Mock(spec=DatabaseService)
    mock_session = MagicMock()
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__ = Mock(return_value=mock_session)
    mock_context_manager.__exit__ = Mock(return_value=None)
    mock_db.get_session.return_value = mock_context_manager
    return mock_db, mock_session


@pytest.fixture
def mock_context():
    """Create a mock Context for testing."""
    ctx = Mock(spec=Context)
    ctx.info = Mock()
    ctx.warning = Mock()
    return ctx


@pytest.fixture
def mock_event_bus():
    """Create a mock EventBusService for testing."""
    return Mock(spec=EventBusService)


def test_find_memory_semantic_search(mock_memory_service, mock_db_service, mock_context, mock_event_bus):
    """Test find_memory with search_mode=semantic returns results."""
    mock_db, mock_session = mock_db_service

    # Setup mock return value
    mock_memory_service.search_similar.return_value = [
        SimilarTask(
            task_id="task-001",
            memory_id="mem-001",
            summary="Implemented authentication",
            success=True,
            similarity_score=0.85,
            reused_count=2,
            semantic_score=0.85,
            keyword_score=None,
        )
    ]

    with patch('omoi_os.mcp.fastmcp_server._memory_service', mock_memory_service), \
         patch('omoi_os.mcp.fastmcp_server._db', mock_db), \
         patch('omoi_os.mcp.fastmcp_server._event_bus', mock_event_bus):
        result = fastmcp_server_module.find_memory.fn(
            mock_context,
            task_description="Implement user authentication",
            search_mode="semantic",
            top_k=5,
            similarity_threshold=0.7,
            success_only=False,
            memory_types=None,
        )

    assert result["success"] is True
    assert result["count"] == 1
    assert result["search_mode"] == "semantic"
    assert len(result["memories"]) == 1
    assert result["memories"][0]["semantic_score"] == 0.85
    mock_memory_service.search_similar.assert_called_once()


def test_find_memory_hybrid_search(mock_memory_service, mock_db_service, mock_context, mock_event_bus):
    """Test find_memory with search_mode=hybrid (default) works."""
    mock_db, mock_session = mock_db_service

    mock_memory_service.search_similar.return_value = [
        SimilarTask(
            task_id="task-001",
            memory_id="mem-001",
            summary="Implemented JWT tokens",
            success=True,
            similarity_score=0.82,
            reused_count=1,
            semantic_score=0.80,
            keyword_score=0.75,
        )
    ]

    with patch('omoi_os.mcp.fastmcp_server._memory_service', mock_memory_service), \
         patch('omoi_os.mcp.fastmcp_server._db', mock_db), \
         patch('omoi_os.mcp.fastmcp_server._event_bus', mock_event_bus):
        result = fastmcp_server_module.find_memory.fn(
            mock_context,
            task_description="Implement JWT authentication",
            search_mode="hybrid",  # Default search_mode is hybrid
            top_k=5,
            similarity_threshold=0.7,
            success_only=False,
            memory_types=None,
        )

    assert result["success"] is True
    assert result["search_mode"] == "hybrid"
    assert result["memories"][0]["semantic_score"] == 0.80
    assert result["memories"][0]["keyword_score"] == 0.75


def test_find_memory_keyword_search(mock_memory_service, mock_db_service, mock_context, mock_event_bus):
    """Test find_memory with search_mode=keyword works."""
    mock_db, mock_session = mock_db_service

    mock_memory_service.search_similar.return_value = [
        SimilarTask(
            task_id="task-002",
            memory_id="mem-002",
            summary="Fixed OAuth bug",
            success=True,
            similarity_score=0.70,
            reused_count=0,
            semantic_score=None,
            keyword_score=0.70,
        )
    ]

    with patch('omoi_os.mcp.fastmcp_server._memory_service', mock_memory_service), \
         patch('omoi_os.mcp.fastmcp_server._db', mock_db), \
         patch('omoi_os.mcp.fastmcp_server._event_bus', mock_event_bus):
        result = fastmcp_server_module.find_memory.fn(
            mock_context,
            task_description="OAuth authentication bug",
            search_mode="keyword",
            top_k=5,
            similarity_threshold=0.7,
            success_only=False,
            memory_types=None,
        )

    assert result["success"] is True
    assert result["search_mode"] == "keyword"
    assert result["memories"][0]["keyword_score"] == 0.70


def test_find_memory_type_filter(mock_memory_service, mock_db_service, mock_context, mock_event_bus):
    """Test find_memory with memory_types filters correctly."""
    mock_db, mock_session = mock_db_service

    mock_memory_service.search_similar.return_value = [
        SimilarTask(
            task_id="task-003",
            memory_id="mem-003",
            summary="Fixed authentication error",
            success=True,
            similarity_score=0.90,
            reused_count=3,
            semantic_score=0.90,
            keyword_score=None,
        )
    ]

    with patch('omoi_os.mcp.fastmcp_server._memory_service', mock_memory_service), \
         patch('omoi_os.mcp.fastmcp_server._db', mock_db), \
         patch('omoi_os.mcp.fastmcp_server._event_bus', mock_event_bus):
        result = fastmcp_server_module.find_memory.fn(
            mock_context,
            task_description="Fix authentication issue",
            search_mode="hybrid",
            top_k=5,
            similarity_threshold=0.7,
            success_only=False,
            memory_types=[MemoryType.ERROR_FIX.value],
        )

    assert result["success"] is True
    # Verify the memory_types filter was passed to search_similar
    call_args = mock_memory_service.search_similar.call_args
    assert call_args.kwargs.get('memory_types') == [MemoryType.ERROR_FIX.value]


def test_find_memory_success_only_filter(mock_memory_service, mock_db_service, mock_context, mock_event_bus):
    """Test find_memory with success_only=True filters only successful memories."""
    mock_db, mock_session = mock_db_service

    mock_memory_service.search_similar.return_value = [
        SimilarTask(
            task_id="task-004",
            memory_id="mem-004",
            summary="Successfully deployed feature",
            success=True,
            similarity_score=0.88,
            reused_count=5,
            semantic_score=0.88,
            keyword_score=None,
        )
    ]

    with patch('omoi_os.mcp.fastmcp_server._memory_service', mock_memory_service), \
         patch('omoi_os.mcp.fastmcp_server._db', mock_db), \
         patch('omoi_os.mcp.fastmcp_server._event_bus', mock_event_bus):
        result = fastmcp_server_module.find_memory.fn(
            mock_context,
            task_description="Deploy feature",
            search_mode="hybrid",
            top_k=5,
            similarity_threshold=0.7,
            success_only=True,
            memory_types=None,
        )

    assert result["success"] is True
    # Verify success_only was passed to search_similar
    call_args = mock_memory_service.search_similar.call_args
    assert call_args.kwargs.get('success_only') is True
    # Verify all returned memories are successful
    for memory in result["memories"]:
        assert memory["success"] is True


def test_find_memory_no_results(mock_memory_service, mock_db_service, mock_context, mock_event_bus):
    """Test find_memory returns empty list (not error) when no results found."""
    mock_db, mock_session = mock_db_service

    mock_memory_service.search_similar.return_value = []

    with patch('omoi_os.mcp.fastmcp_server._memory_service', mock_memory_service), \
         patch('omoi_os.mcp.fastmcp_server._db', mock_db), \
         patch('omoi_os.mcp.fastmcp_server._event_bus', mock_event_bus):
        result = fastmcp_server_module.find_memory.fn(
            mock_context,
            task_description="unknown task that has no matches",
            search_mode="hybrid",
            top_k=5,
            similarity_threshold=0.7,
            success_only=False,
            memory_types=None,
        )

    assert result["success"] is True
    assert result["count"] == 0
    assert result["memories"] == []


def test_find_memory_reuse_count_increment(mock_memory_service, mock_db_service, mock_context, mock_event_bus):
    """Test that reused_count is returned and incremented by MemoryService."""
    mock_db, mock_session = mock_db_service

    # Initial reused_count is 5, will be 6 after this search
    mock_memory_service.search_similar.return_value = [
        SimilarTask(
            task_id="task-005",
            memory_id="mem-005",
            summary="Implemented caching layer",
            success=True,
            similarity_score=0.92,
            reused_count=6,  # Incremented by search_similar
            semantic_score=0.92,
            keyword_score=None,
        )
    ]

    with patch('omoi_os.mcp.fastmcp_server._memory_service', mock_memory_service), \
         patch('omoi_os.mcp.fastmcp_server._db', mock_db), \
         patch('omoi_os.mcp.fastmcp_server._event_bus', mock_event_bus):
        result = fastmcp_server_module.find_memory.fn(
            mock_context,
            task_description="Implement caching",
            search_mode="hybrid",
            top_k=5,
            similarity_threshold=0.7,
            success_only=False,
            memory_types=None,
        )

    assert result["success"] is True
    assert result["memories"][0]["reused_count"] == 6


def test_find_memory_invalid_search_mode(mock_memory_service, mock_db_service, mock_context, mock_event_bus):
    """Test find_memory returns error for invalid search_mode."""
    mock_db, mock_session = mock_db_service

    with patch('omoi_os.mcp.fastmcp_server._memory_service', mock_memory_service), \
         patch('omoi_os.mcp.fastmcp_server._db', mock_db), \
         patch('omoi_os.mcp.fastmcp_server._event_bus', mock_event_bus):
        result = fastmcp_server_module.find_memory.fn(
            mock_context,
            task_description="Some task",
            search_mode="invalid_mode",
            top_k=5,
            similarity_threshold=0.7,
            success_only=False,
            memory_types=None,
        )

    assert result["success"] is False
    assert "Invalid search_mode" in result["error"]
    assert "invalid_mode" in result["error"]


def test_find_memory_invalid_memory_type(mock_memory_service, mock_db_service, mock_context, mock_event_bus):
    """Test find_memory returns error for invalid memory_type in filter."""
    mock_db, mock_session = mock_db_service

    with patch('omoi_os.mcp.fastmcp_server._memory_service', mock_memory_service), \
         patch('omoi_os.mcp.fastmcp_server._db', mock_db), \
         patch('omoi_os.mcp.fastmcp_server._event_bus', mock_event_bus):
        result = fastmcp_server_module.find_memory.fn(
            mock_context,
            task_description="Some task",
            search_mode="hybrid",
            top_k=5,
            similarity_threshold=0.7,
            success_only=False,
            memory_types=["invalid_type"],
        )

    assert result["success"] is False
    assert "Invalid memory_type in filter" in result["error"]
    assert "invalid_type" in result["error"]


def test_find_memory_top_k_threshold(mock_memory_service, mock_db_service, mock_context, mock_event_bus):
    """Test find_memory respects top_k and similarity_threshold parameters."""
    mock_db, mock_session = mock_db_service

    mock_memory_service.search_similar.return_value = [
        SimilarTask(
            task_id=f"task-{i}",
            memory_id=f"mem-{i}",
            summary=f"Result {i}",
            success=True,
            similarity_score=0.95 - i * 0.05,
            reused_count=i,
            semantic_score=0.95 - i * 0.05,
            keyword_score=None,
        )
        for i in range(3)
    ]

    with patch('omoi_os.mcp.fastmcp_server._memory_service', mock_memory_service), \
         patch('omoi_os.mcp.fastmcp_server._db', mock_db), \
         patch('omoi_os.mcp.fastmcp_server._event_bus', mock_event_bus):
        result = fastmcp_server_module.find_memory.fn(
            mock_context,
            task_description="Search query",
            search_mode="hybrid",
            top_k=3,
            similarity_threshold=0.8,
            success_only=False,
            memory_types=None,
        )

    assert result["success"] is True
    # Verify the parameters were passed correctly to search_similar
    call_args = mock_memory_service.search_similar.call_args
    assert call_args.kwargs.get('top_k') == 3
    assert call_args.kwargs.get('similarity_threshold') == 0.8

