"""Tests to verify memory-related fixtures work correctly.

These tests validate that the fixtures defined in conftest.py are working
properly and can be used for isolated unit testing of MCP tools.
"""

import pytest
from unittest.mock import Mock

from omoi_os.models.task_memory import TaskMemory
from omoi_os.services.memory import SimilarTask


class TestMockEmbeddingServiceFixture:
    """Tests for mock_embedding_service fixture."""

    def test_fixture_has_spec(self, mock_embedding_service):
        """Test that mock has EmbeddingService spec."""
        # The mock should have generate_embedding method
        assert hasattr(mock_embedding_service, "generate_embedding")
        assert hasattr(mock_embedding_service, "batch_generate_embeddings")
        assert hasattr(mock_embedding_service, "cosine_similarity")

    def test_generate_embedding_returns_vector(self, mock_embedding_service):
        """Test that generate_embedding returns a 1536-dim vector."""
        result = mock_embedding_service.generate_embedding("test text")
        assert isinstance(result, list)
        assert len(result) == 1536

    def test_cosine_similarity_returns_float(self, mock_embedding_service):
        """Test that cosine_similarity returns a realistic score."""
        result = mock_embedding_service.cosine_similarity([0.1] * 1536, [0.2] * 1536)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_dimensions_attribute(self, mock_embedding_service):
        """Test that dimensions attribute is set."""
        assert mock_embedding_service.dimensions == 1536


class TestMockMemoryServiceFixture:
    """Tests for mock_memory_service fixture."""

    def test_fixture_has_spec(self, mock_memory_service):
        """Test that mock has MemoryService spec."""
        assert hasattr(mock_memory_service, "store_execution")
        assert hasattr(mock_memory_service, "search_similar")
        assert hasattr(mock_memory_service, "get_task_context")
        assert hasattr(mock_memory_service, "classify_memory_type_sync")

    def test_store_execution_returns_task_memory(self, mock_memory_service):
        """Test that store_execution returns a TaskMemory."""
        result = mock_memory_service.store_execution(
            session=Mock(),
            task_id="test-task",
            execution_summary="Test summary",
            success=True,
        )
        assert isinstance(result, TaskMemory)
        assert result.success is True

    def test_search_similar_returns_list(self, mock_memory_service):
        """Test that search_similar returns empty list by default."""
        result = mock_memory_service.search_similar(
            session=Mock(),
            task_description="test query",
        )
        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_task_context_returns_dict(self, mock_memory_service):
        """Test that get_task_context returns context dict."""
        result = mock_memory_service.get_task_context(
            session=Mock(),
            task_description="test task",
        )
        assert isinstance(result, dict)
        assert "similar_tasks" in result
        assert "matching_patterns" in result
        assert "recommendations" in result

    def test_classify_memory_type_returns_string(self, mock_memory_service):
        """Test that classify_memory_type_sync returns 'discovery' by default."""
        result = mock_memory_service.classify_memory_type_sync("test summary")
        assert result == "discovery"

    def test_has_embedding_service(self, mock_memory_service):
        """Test that mock has embedding_service attribute."""
        assert hasattr(mock_memory_service, "embedding_service")
        assert mock_memory_service.embedding_service is not None


class TestMockContextFixture:
    """Tests for mock_context fixture."""

    def test_fixture_has_logging_methods(self, mock_context):
        """Test that mock has logging methods."""
        assert hasattr(mock_context, "info")
        assert hasattr(mock_context, "warning")
        assert hasattr(mock_context, "error")
        assert hasattr(mock_context, "debug")

    def test_info_can_be_called(self, mock_context):
        """Test that info() can be called."""
        mock_context.info("Test message")
        mock_context.info.assert_called_once_with("Test message")

    def test_warning_can_be_called(self, mock_context):
        """Test that warning() can be called."""
        mock_context.warning("Test warning")
        mock_context.warning.assert_called_once_with("Test warning")

    def test_error_can_be_called(self, mock_context):
        """Test that error() can be called."""
        mock_context.error("Test error")
        mock_context.error.assert_called_once_with("Test error")

    def test_debug_can_be_called(self, mock_context):
        """Test that debug() can be called."""
        mock_context.debug("Test debug")
        mock_context.debug.assert_called_once_with("Test debug")

    @pytest.mark.asyncio
    async def test_report_progress_is_async(self, mock_context):
        """Test that report_progress is an async mock."""
        await mock_context.report_progress(50, 100)
        mock_context.report_progress.assert_awaited_once_with(50, 100)


class TestTaskMemoryFactory:
    """Tests for test_task_memory_factory fixture."""

    def test_factory_creates_task_memory(self, test_task_memory_factory):
        """Test that factory creates TaskMemory instances."""
        memory = test_task_memory_factory()
        assert isinstance(memory, TaskMemory)

    def test_factory_uses_defaults(self, test_task_memory_factory):
        """Test that factory uses sensible defaults."""
        memory = test_task_memory_factory()
        assert memory.success is True
        assert memory.memory_type == "discovery"
        assert memory.reused_count == 0
        assert memory.execution_summary == "Test task completed"

    def test_factory_accepts_custom_values(self, test_task_memory_factory):
        """Test that factory accepts custom parameter values."""
        memory = test_task_memory_factory(
            task_id="custom-task-id",
            execution_summary="Custom summary",
            memory_type="error_fix",
            success=False,
            reused_count=5,
        )
        assert memory.task_id == "custom-task-id"
        assert memory.execution_summary == "Custom summary"
        assert memory.memory_type == "error_fix"
        assert memory.success is False
        assert memory.reused_count == 5

    def test_factory_sets_ace_workflow_fields(self, test_task_memory_factory):
        """Test that factory can set ACE workflow fields."""
        memory = test_task_memory_factory(
            goal="Fix authentication bug",
            result="Bug fixed successfully",
            feedback="All tests passing",
            tool_usage={"bash": 3, "edit": 5},
        )
        assert memory.goal == "Fix authentication bug"
        assert memory.result == "Bug fixed successfully"
        assert memory.feedback == "All tests passing"
        assert memory.tool_usage == {"bash": 3, "edit": 5}

    def test_factory_creates_unique_ids(self, test_task_memory_factory):
        """Test that factory creates unique IDs."""
        memory1 = test_task_memory_factory()
        memory2 = test_task_memory_factory()
        assert memory1.id != memory2.id
        assert memory1.task_id != memory2.task_id

    def test_factory_sets_embedding(self, test_task_memory_factory):
        """Test that factory sets context_embedding by default."""
        memory = test_task_memory_factory()
        assert memory.context_embedding is not None
        assert len(memory.context_embedding) == 1536

    def test_factory_accepts_custom_embedding(self, test_task_memory_factory):
        """Test that factory accepts custom embedding."""
        custom_embedding = [0.5] * 1536
        memory = test_task_memory_factory(context_embedding=custom_embedding)
        assert memory.context_embedding == custom_embedding


class TestSampleSimilarTaskFixture:
    """Tests for sample_similar_task fixture."""

    def test_fixture_returns_similar_task(self, sample_similar_task):
        """Test that fixture returns a SimilarTask instance."""
        assert isinstance(sample_similar_task, SimilarTask)

    def test_fixture_has_realistic_values(self, sample_similar_task):
        """Test that fixture has realistic field values."""
        assert sample_similar_task.task_id is not None
        assert sample_similar_task.memory_id is not None
        assert sample_similar_task.summary is not None
        assert sample_similar_task.success is True
        assert 0.0 <= sample_similar_task.similarity_score <= 1.0
        assert sample_similar_task.reused_count >= 0

    def test_fixture_has_semantic_and_keyword_scores(self, sample_similar_task):
        """Test that fixture has both score types."""
        assert sample_similar_task.semantic_score is not None
        assert sample_similar_task.keyword_score is not None


class TestSampleSimilarTaskFactory:
    """Tests for sample_similar_task_factory fixture."""

    def test_factory_creates_similar_task(self, sample_similar_task_factory):
        """Test that factory creates SimilarTask instances."""
        similar = sample_similar_task_factory()
        assert isinstance(similar, SimilarTask)

    def test_factory_uses_defaults(self, sample_similar_task_factory):
        """Test that factory uses sensible defaults."""
        similar = sample_similar_task_factory()
        assert similar.success is True
        assert similar.similarity_score == 0.85
        assert similar.reused_count == 0
        assert similar.summary == "Test task execution summary"

    def test_factory_accepts_custom_values(self, sample_similar_task_factory):
        """Test that factory accepts custom parameter values."""
        similar = sample_similar_task_factory(
            task_id="custom-task",
            memory_id="custom-memory",
            summary="Custom summary",
            success=False,
            similarity_score=0.95,
            reused_count=10,
            semantic_score=0.92,
            keyword_score=0.88,
        )
        assert similar.task_id == "custom-task"
        assert similar.memory_id == "custom-memory"
        assert similar.summary == "Custom summary"
        assert similar.success is False
        assert similar.similarity_score == 0.95
        assert similar.reused_count == 10
        assert similar.semantic_score == 0.92
        assert similar.keyword_score == 0.88

    def test_factory_creates_unique_ids(self, sample_similar_task_factory):
        """Test that factory creates unique IDs."""
        similar1 = sample_similar_task_factory()
        similar2 = sample_similar_task_factory()
        assert similar1.task_id != similar2.task_id
        assert similar1.memory_id != similar2.memory_id


class TestFixtureIntegration:
    """Integration tests for using fixtures together."""

    def test_mock_memory_service_with_similar_task(
        self, mock_memory_service, sample_similar_task
    ):
        """Test using mock_memory_service with sample_similar_task."""
        # Configure mock to return the sample similar task
        mock_memory_service.search_similar.return_value = [sample_similar_task]

        # Simulate calling the service
        results = mock_memory_service.search_similar(
            session=Mock(),
            task_description="test query",
        )

        assert len(results) == 1
        assert results[0] == sample_similar_task

    def test_mock_memory_service_with_factory(
        self, mock_memory_service, test_task_memory_factory
    ):
        """Test using mock_memory_service with task memory factory."""
        # Create custom memory using factory
        custom_memory = test_task_memory_factory(
            execution_summary="Custom execution",
            success=True,
        )

        # Configure mock to return custom memory
        mock_memory_service.store_execution.return_value = custom_memory

        # Simulate calling the service
        result = mock_memory_service.store_execution(
            session=Mock(),
            task_id="test-task",
            execution_summary="Custom execution",
            success=True,
        )

        assert result.execution_summary == "Custom execution"

    def test_mock_context_with_assertions(self, mock_context):
        """Test that mock_context tracks calls for assertions."""
        # Simulate MCP tool behavior
        mock_context.info("Starting operation")
        mock_context.warning("Minor issue detected")
        mock_context.info("Operation completed")

        # Verify the calls
        assert mock_context.info.call_count == 2
        assert mock_context.warning.call_count == 1
        mock_context.error.assert_not_called()

    def test_multiple_similar_tasks_from_factory(self, sample_similar_task_factory):
        """Test creating multiple similar tasks with different scores."""
        results = [
            sample_similar_task_factory(similarity_score=0.95),
            sample_similar_task_factory(similarity_score=0.82),
            sample_similar_task_factory(similarity_score=0.71),
        ]

        # Verify ordering by score
        scores = [r.similarity_score for r in results]
        assert scores == sorted(scores, reverse=True)
