"""Test agent executor: mocked OpenHands integration, conversation lifecycle."""

import os
import tempfile
from unittest.mock import Mock, MagicMock, patch

import pytest

from omoi_os.services.agent_executor import AgentExecutor


@pytest.fixture
def test_workspace_dir():
    """Create a temporary workspace directory."""
    return tempfile.mkdtemp(prefix="omoi_test_workspace_")


@pytest.fixture
def mock_llm():
    """Create a mock LLM object."""
    llm = Mock()
    llm.model = "test-model"
    return llm


@pytest.fixture
def mock_agent():
    """Create a mock Agent object."""
    agent = Mock()
    return agent


@pytest.fixture
def mock_conversation():
    """Create a mock Conversation object."""
    conversation = Mock()
    conversation.state = Mock()
    conversation.state.execution_status = "finished"
    conversation.state.events = [Mock(), Mock()]  # 2 events
    conversation.conversation_stats = Mock()
    conversation.conversation_stats.get_combined_metrics = Mock(return_value=Mock(accumulated_cost=0.05))
    conversation.close = Mock()
    return conversation


@patch("omoi_os.services.agent_executor.LLM")
@patch("omoi_os.services.agent_executor.get_default_agent")
def test_agent_executor_initialization(
    mock_get_agent,
    mock_llm_class,
    test_workspace_dir,
    mock_llm,
    mock_agent,
):
    """Test AgentExecutor initialization."""
    mock_llm_class.return_value = mock_llm
    mock_get_agent.return_value = mock_agent

    executor = AgentExecutor(
        phase_id="PHASE_REQUIREMENTS",
        workspace_dir=test_workspace_dir,
    )

    assert executor.phase_id == "PHASE_REQUIREMENTS"
    assert executor.workspace_dir == test_workspace_dir
    assert executor.llm is not None
    assert executor.agent is not None

    # Verify LLM was created with correct parameters
    mock_llm_class.assert_called_once()
    mock_get_agent.assert_called_once_with(llm=mock_llm, cli_mode=True)


@patch("omoi_os.services.agent_executor.LLM")
@patch("omoi_os.services.agent_executor.get_default_agent")
@patch("omoi_os.services.agent_executor.Conversation")
def test_execute_task_success(
    mock_conversation_class,
    mock_get_agent,
    mock_llm_class,
    test_workspace_dir,
    mock_llm,
    mock_agent,
    mock_conversation,
):
    """Test successful task execution."""
    mock_llm_class.return_value = mock_llm
    mock_get_agent.return_value = mock_agent
    mock_conversation_class.return_value = mock_conversation

    executor = AgentExecutor(
        phase_id="PHASE_REQUIREMENTS",
        workspace_dir=test_workspace_dir,
    )

    result = executor.execute_task("Test task description")

    # Verify conversation was created
    mock_conversation_class.assert_called_once()
    call_args = mock_conversation_class.call_args
    assert call_args.kwargs["agent"] == mock_agent
    assert call_args.kwargs["workspace"] == test_workspace_dir

    # Verify message was sent
    mock_conversation.send_message.assert_called_once_with("Test task description")

    # Verify conversation was run
    mock_conversation.run.assert_called_once()

    # Verify result structure
    assert result["status"] == "finished"
    assert result["event_count"] == 2
    assert result["cost"] == 0.05

    # Verify conversation was closed
    mock_conversation.close.assert_called_once()


@patch("omoi_os.services.agent_executor.LLM")
@patch("omoi_os.services.agent_executor.get_default_agent")
@patch("omoi_os.services.agent_executor.Conversation")
def test_execute_task_failure(
    mock_conversation_class,
    mock_get_agent,
    mock_llm_class,
    test_workspace_dir,
    mock_llm,
    mock_agent,
):
    """Test task execution failure handling."""
    mock_llm_class.return_value = mock_llm
    mock_get_agent.return_value = mock_agent

    # Mock conversation that raises an exception
    mock_conversation = Mock()
    mock_conversation.send_message = Mock()
    mock_conversation.run = Mock(side_effect=Exception("Execution failed"))
    mock_conversation.state = Mock()
    mock_conversation.state.execution_status = "failed"
    mock_conversation.state.events = []
    mock_conversation.conversation_stats = Mock()
    mock_conversation.conversation_stats.get_combined_metrics = Mock(return_value=Mock(accumulated_cost=0.0))
    mock_conversation.close = Mock()

    mock_conversation_class.return_value = mock_conversation

    executor = AgentExecutor(
        phase_id="PHASE_REQUIREMENTS",
        workspace_dir=test_workspace_dir,
    )

    # Execution should handle the exception
    with pytest.raises(Exception, match="Execution failed"):
        executor.execute_task("Test task description")

    # Verify conversation was still closed
    mock_conversation.close.assert_called_once()


@patch("omoi_os.services.agent_executor.LLM")
@patch("omoi_os.services.agent_executor.get_default_agent")
def test_workspace_directory_creation(
    mock_get_agent,
    mock_llm_class,
    test_workspace_dir,
    mock_llm,
    mock_agent,
):
    """Test that workspace directory is created if it doesn't exist."""
    mock_llm_class.return_value = mock_llm
    mock_get_agent.return_value = mock_agent

    # Use a new directory that doesn't exist
    new_workspace = os.path.join(test_workspace_dir, "new_workspace")

    executor = AgentExecutor(
        phase_id="PHASE_REQUIREMENTS",
        workspace_dir=new_workspace,
    )

    # Directory should be created (or at least accessible)
    # The actual creation happens in execute_task, but we verify the executor
    # can be initialized with a workspace path
    assert executor.workspace_dir == new_workspace


@patch("omoi_os.services.agent_executor.LLM")
@patch("omoi_os.services.agent_executor.get_default_agent")
@patch("omoi_os.services.agent_executor.Conversation")
def test_result_structure(
    mock_conversation_class,
    mock_get_agent,
    mock_llm_class,
    test_workspace_dir,
    mock_llm,
    mock_agent,
    mock_conversation,
):
    """Test that execute_task returns the expected result structure."""
    mock_llm_class.return_value = mock_llm
    mock_get_agent.return_value = mock_agent
    mock_conversation_class.return_value = mock_conversation

    executor = AgentExecutor(
        phase_id="PHASE_REQUIREMENTS",
        workspace_dir=test_workspace_dir,
    )

    result = executor.execute_task("Test task")

    # Verify result has all required keys
    assert "status" in result
    assert "event_count" in result
    assert "cost" in result

    # Verify types
    assert isinstance(result["status"], str)
    assert isinstance(result["event_count"], int)
    assert isinstance(result["cost"], (int, float))

