"""Tests for memory service - storage and retrieval."""

import pytest

from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.models.task_memory import TaskMemory
from omoi_os.services.memory import MemoryService
from omoi_os.services.embedding import EmbeddingService, EmbeddingProvider
from omoi_os.services.event_bus import EventBusService


@pytest.fixture
def embedding_service():
    """Fixture for embedding service (local model for tests)."""
    return EmbeddingService(provider=EmbeddingProvider.LOCAL)


@pytest.fixture
def memory_service(embedding_service):
    """Fixture for memory service."""
    event_bus = EventBusService()
    return MemoryService(embedding_service=embedding_service, event_bus=event_bus)


@pytest.fixture
def test_ticket(db_service):
    """Create a test ticket."""
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Ticket",
            description="Test ticket for memory tests",
            phase_id="PHASE_IMPLEMENTATION",
            priority="MEDIUM",
            status="open",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        session.expunge(ticket)
        return ticket


@pytest.fixture
def test_task(db_service, test_ticket: Ticket):
    """Create a test task."""
    with db_service.get_session() as session:
        task = Task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Implement user authentication system",
            priority="HIGH",
            status="completed",
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        session.expunge(task)
        return task


def test_store_execution_success(
    db_service,
    memory_service: MemoryService,
    test_task: Task,
):
    """Test storing a successful task execution."""
    summary = "Successfully implemented authentication with JWT tokens"
    
    with db_service.get_session() as session:
        memory = memory_service.store_execution(
            session=session,
            task_id=test_task.id,
            execution_summary=summary,
            success=True,
        )
        session.commit()
        
        assert memory is not None
        assert memory.task_id == test_task.id
        assert memory.execution_summary == summary
        assert memory.success is True
        assert memory.context_embedding is not None
        assert len(memory.context_embedding) == 1536  # Expected dimensions
        assert memory.reused_count == 0


def test_store_execution_failure(
    db_service,
    memory_service: MemoryService,
    test_task: Task,
):
    """Test storing a failed task execution with error patterns."""
    summary = "Failed to connect to database during authentication"
    error_patterns = {
        "error_type": "ConnectionError",
        "message": "Database connection refused",
        "stack_trace": "...",
    }
    
    with db_service.get_session() as session:
        memory = memory_service.store_execution(
            session=session,
            task_id=test_task.id,
            execution_summary=summary,
            success=False,
            error_patterns=error_patterns,
        )
        session.commit()
        
        assert memory is not None
        assert memory.success is False
        assert memory.error_patterns == error_patterns
        assert memory.context_embedding is not None


def test_store_execution_invalid_task(
    db_service,
    memory_service: MemoryService,
):
    """Test storing execution for non-existent task raises error."""
    with db_service.get_session() as session:
        with pytest.raises(ValueError, match="Task .* not found"):
            memory_service.store_execution(
                session=session,
                task_id="non-existent-task",
                execution_summary="Some summary",
                success=True,
            )


def test_search_similar_tasks(
    db_service,
    memory_service: MemoryService,
    test_ticket: Ticket,
):
    """Test searching for similar tasks."""
    with db_service.get_session() as session:
        # Create multiple tasks with memories
        tasks_data = [
            ("Implement JWT authentication", "Successfully implemented JWT auth", True),
            ("Add OAuth2 support", "Added OAuth2 with Google provider", True),
            ("Fix login bug", "Fixed password validation issue", True),
            ("Implement file upload", "Added file upload with S3", True),
        ]
        
        for desc, summary, success in tasks_data:
            task = Task(
                ticket_id=test_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="implement_feature",
                description=desc,
                priority="MEDIUM",
                status="completed",
            )
            session.add(task)
            session.flush()
            
            memory_service.store_execution(
                session=session,
                task_id=task.id,
                execution_summary=summary,
                success=success,
                auto_extract_patterns=False,  # Disable for this test
            )
        
        session.commit()
        
        # Search for authentication-related tasks
        results = memory_service.search_similar(
            session=session,
            task_description="Implement user authentication with JWT",
            top_k=3,
            similarity_threshold=0.3,  # Lower threshold for local embeddings
            success_only=True,
        )
        
        assert len(results) > 0
        assert all(r.success for r in results)
        assert all(0 <= r.similarity_score <= 1.0 for r in results)
        # Results should be ordered by similarity
        scores = [r.similarity_score for r in results]
        assert scores == sorted(scores, reverse=True)


def test_search_similar_with_threshold(
    db_service,
    memory_service: MemoryService,
    test_task: Task,
):
    """Test similarity search respects threshold."""
    with db_service.get_session() as session:
        # Store a memory
        memory_service.store_execution(
            session=session,
            task_id=test_task.id,
            execution_summary="Implemented JWT authentication successfully",
            success=True,
        )
        session.commit()
        
        # Search with very high threshold (should return nothing)
        results = memory_service.search_similar(
            session=session,
            task_description="Build a rocket ship",  # Completely different
            top_k=5,
            similarity_threshold=0.99,  # Very high threshold
        )
        
        assert len(results) == 0


def test_search_similar_success_only_filter(
    db_service,
    memory_service: MemoryService,
    test_ticket: Ticket,
):
    """Test success_only filter in similarity search."""
    with db_service.get_session() as session:
        # Create one successful and one failed task
        tasks_data = [
            ("Implement feature A", "Successfully completed", True),
            ("Implement feature B", "Failed due to error", False),
        ]
        
        for desc, summary, success in tasks_data:
            task = Task(
                ticket_id=test_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="implement_feature",
                description=desc,
                priority="MEDIUM",
                status="completed" if success else "failed",
            )
            session.add(task)
            session.flush()
            
            memory_service.store_execution(
                session=session,
                task_id=task.id,
                execution_summary=summary,
                success=success,
            )
        
        session.commit()
        
        # Search with success_only=True
        results = memory_service.search_similar(
            session=session,
            task_description="Implement feature",
            top_k=10,
            similarity_threshold=0.1,
            success_only=True,
        )
        
        assert all(r.success for r in results)


def test_memory_reuse_counter_increments(
    db_service,
    memory_service: MemoryService,
    test_task: Task,
):
    """Test that reuse counter increments when memory is referenced."""
    memory_id = None
    with db_service.get_session() as session:
        # Store a memory
        memory = memory_service.store_execution(
            session=session,
            task_id=test_task.id,
            execution_summary="Implemented authentication",
            success=True,
        )
        session.commit()
        memory_id = memory.id
        initial_count = memory.reused_count
        assert initial_count == 0
    
    with db_service.get_session() as session:
        # Search for it (should increment reuse counter)
        results = memory_service.search_similar(
            session=session,
            task_description="authentication",
            top_k=1,
            similarity_threshold=0.1,
        )
        session.commit()
        
        assert len(results) > 0
    
    # Check counter incremented
    with db_service.get_session() as session:
        memory = session.get(TaskMemory, memory_id)
        assert memory.reused_count == 1


def test_get_task_context(
    db_service,
    memory_service: MemoryService,
    test_ticket: Ticket,
):
    """Test getting context suggestions for a task."""
    with db_service.get_session() as session:
        # Create task with memory
        task = Task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Implement OAuth2 authentication",
            priority="HIGH",
            status="completed",
        )
        session.add(task)
        session.flush()
        
        memory_service.store_execution(
            session=session,
            task_id=task.id,
            execution_summary="Successfully implemented OAuth2 with Google",
            success=True,
        )
        session.commit()
        
        # Create new task needing context
        new_task = Task(
            ticket_id=test_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Implement GitHub OAuth authentication",
            priority="HIGH",
            status="pending",
        )
        session.add(new_task)
        session.commit()
        
        # Get context
        context = memory_service.get_task_context(
            session=session,
            task_description=new_task.description,
            top_k=3,
        )
        
        assert "similar_tasks" in context
        assert "matching_patterns" in context
        assert "recommendations" in context
        assert isinstance(context["similar_tasks"], list)
        assert isinstance(context["matching_patterns"], list)
        assert isinstance(context["recommendations"], list)


def test_store_execution_auto_extract_patterns(
    db_service,
    memory_service: MemoryService,
    test_ticket: Ticket,
):
    """Test that auto pattern extraction works on storage."""
    with db_service.get_session() as session:
        # Create multiple similar tasks
        for i in range(3):
            task = Task(
                ticket_id=test_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="implement_feature",
                description=f"Implement authentication feature {i}",
                priority="MEDIUM",
                status="completed",
            )
            session.add(task)
            session.flush()
            
            memory_service.store_execution(
                session=session,
                task_id=task.id,
                execution_summary=f"Successfully completed authentication {i}",
                success=True,
                auto_extract_patterns=True,
            )
        
        session.commit()
        
        # If we got here, auto extraction didn't crash
        assert True


def test_memory_embedding_dimensions(
    db_service,
    memory_service: MemoryService,
    test_task: Task,
):
    """Test that embeddings have correct dimensions (1536)."""
    with db_service.get_session() as session:
        memory = memory_service.store_execution(
            session=session,
            task_id=test_task.id,
            execution_summary="Test summary for embedding dimensions",
            success=True,
        )
        session.commit()
        
        assert memory.context_embedding is not None
        assert len(memory.context_embedding) == 1536
        assert all(isinstance(v, float) for v in memory.context_embedding)


def test_memory_to_dict(
    db_service,
    memory_service: MemoryService,
    test_task: Task,
):
    """Test TaskMemory.to_dict() serialization."""
    with db_service.get_session() as session:
        memory = memory_service.store_execution(
            session=session,
            task_id=test_task.id,
            execution_summary="Test summary",
            success=True,
        )
        session.commit()
        
        data = memory.to_dict()
        
        assert "id" in data
        assert "task_id" in data
        assert "execution_summary" in data
        assert "has_embedding" in data
        assert "embedding_dimensions" in data
        assert "success" in data
        assert "learned_at" in data
        assert "reused_count" in data
        
        assert data["has_embedding"] is True
        assert data["embedding_dimensions"] == 1536
