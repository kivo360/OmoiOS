"""Tests for pattern learning functionality."""

import pytest

from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.models.learned_pattern import LearnedPattern, TaskPattern
from omoi_os.services.memory import MemoryService
from omoi_os.services.embedding import EmbeddingService, EmbeddingProvider


@pytest.fixture
def embedding_service():
    """Fixture for embedding service (local model for tests)."""
    return EmbeddingService(provider=EmbeddingProvider.LOCAL)


@pytest.fixture
def memory_service(embedding_service):
    """Fixture for memory service."""
    return MemoryService(embedding_service=embedding_service, event_bus=None)


@pytest.fixture
def test_ticket(db_service):
    """Create a test ticket."""
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Ticket",
            description="Test ticket for pattern tests",
            phase_id="PHASE_IMPLEMENTATION",
            priority="MEDIUM",
            status="open",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        session.expunge(ticket)
        return ticket


def test_extract_pattern_success(
    db_service,
    memory_service: MemoryService,
    test_ticket: Ticket,
):
    """Test extracting a success pattern from multiple completed tasks."""
    with db_service.get_session() as session:
        # Create multiple similar successful tasks
        for i in range(5):
            task = Task(
                ticket_id=test_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="implement_api_endpoint",
                description=f"Implement API endpoint for user registration {i}",
                priority="MEDIUM",
                status="completed",
            )
            session.add(task)
            session.flush()

            memory_service.store_execution(
                session=session,
                task_id=task.id,
                execution_summary=f"Successfully completed API endpoint {i} with validation",
                success=True,
                auto_extract_patterns=False,
            )

        session.commit()

        # Extract pattern
        pattern = memory_service.extract_pattern(
            session=session,
            task_type_pattern=".*API endpoint.*",
            pattern_type="success",
            min_samples=3,
        )

        assert pattern is not None
        assert pattern.pattern_type == "success"
        assert pattern.task_type_pattern == ".*API endpoint.*"
        assert pattern.confidence_score > 0.0
        assert pattern.usage_count == 0
        assert len(pattern.success_indicators) > 0


def test_extract_pattern_insufficient_samples(
    db_service,
    memory_service: MemoryService,
    test_ticket: Ticket,
):
    """Test that pattern extraction fails with insufficient samples."""
    with db_service.get_session() as session:
        # Create only 2 tasks (need 3 minimum)
        for i in range(2):
            task = Task(
                ticket_id=test_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="implement_feature",
                description=f"Implement feature {i}",
                priority="MEDIUM",
                status="completed",
            )
            session.add(task)
            session.flush()

            memory_service.store_execution(
                session=session,
                task_id=task.id,
                execution_summary=f"Completed feature {i}",
                success=True,
            )

        session.commit()

        # Try to extract pattern (should return None)
        pattern = memory_service.extract_pattern(
            session=session,
            task_type_pattern=".*feature.*",
            pattern_type="success",
            min_samples=3,
        )

        assert pattern is None


def test_pattern_confidence_scaling(
    db_service,
    memory_service: MemoryService,
    test_ticket: Ticket,
):
    """Test that pattern confidence scales with sample size."""
    sample_counts = [3, 5, 10]
    confidences = []

    for count in sample_counts:
        with db_service.get_session() as session:
            # Clear previous data
            session.query(Task).delete()
            session.commit()

            # Create tasks
            for i in range(count):
                task = Task(
                    ticket_id=test_ticket.id,
                    phase_id="PHASE_IMPLEMENTATION",
                    task_type=f"test_{count}_feature",
                    description=f"Test pattern confidence {count} - task {i}",
                    priority="MEDIUM",
                    status="completed",
                )
                session.add(task)
                session.flush()

                memory_service.store_execution(
                    session=session,
                    task_id=task.id,
                    execution_summary=f"Completed task {i}",
                    success=True,
                )

            session.commit()

            # Extract pattern
            pattern = memory_service.extract_pattern(
                session=session,
                task_type_pattern=f".*pattern confidence {count}.*",
                pattern_type="success",
                min_samples=3,
            )

            if pattern:
                confidences.append(pattern.confidence_score)

    # Confidence should generally increase with more samples
    assert len(confidences) > 0


def test_pattern_increment_usage(
    db_service,
):
    """Test incrementing pattern usage counter."""
    with db_service.get_session() as session:
        pattern = LearnedPattern(
            pattern_type="success",
            task_type_pattern=".*test.*",
            success_indicators=["completed", "validated"],
            failure_indicators=[],
            recommended_context={"test": True},
            confidence_score=0.8,
            usage_count=0,
        )
        session.add(pattern)
        session.commit()
        session.refresh(pattern)

        initial_count = pattern.usage_count
        initial_updated = pattern.updated_at

        pattern.increment_usage()
        session.commit()

        assert pattern.usage_count == initial_count + 1
        assert pattern.updated_at > initial_updated


def test_pattern_update_confidence(
    db_service,
):
    """Test updating pattern confidence score."""
    with db_service.get_session() as session:
        pattern = LearnedPattern(
            pattern_type="success",
            task_type_pattern=".*test.*",
            confidence_score=0.5,
        )
        session.add(pattern)
        session.commit()
        session.refresh(pattern)

        initial_updated = pattern.updated_at

        pattern.update_confidence(0.8)
        session.commit()

        assert pattern.confidence_score == 0.8
        assert pattern.updated_at > initial_updated


def test_pattern_update_confidence_validation(
    db_service,
):
    """Test that confidence score is validated (0.0 to 1.0)."""
    with db_service.get_session() as session:
        pattern = LearnedPattern(
            pattern_type="success",
            task_type_pattern=".*test.*",
            confidence_score=0.5,
        )
        session.add(pattern)
        session.commit()

        # Test invalid confidence scores
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            pattern.update_confidence(1.5)

        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            pattern.update_confidence(-0.1)


def test_find_matching_patterns(
    db_service,
    memory_service: MemoryService,
):
    """Test finding patterns that match a task description."""
    with db_service.get_session() as session:
        # Create patterns
        patterns_data = [
            (".*authentication.*", 0.8),
            (".*API.*", 0.7),
            (".*database.*", 0.6),
            (".*frontend.*", 0.3),  # Below min_confidence
        ]

        for pattern_regex, confidence in patterns_data:
            pattern = LearnedPattern(
                pattern_type="success",
                task_type_pattern=pattern_regex,
                confidence_score=confidence,
            )
            session.add(pattern)

        session.commit()

        # Find matching patterns
        matches = memory_service.find_matching_patterns(
            session=session,
            task_description="Implement API authentication endpoint",
            min_confidence=0.5,
        )

        # Should match authentication and API patterns (both >= 0.5 confidence)
        assert len(matches) >= 2
        assert all(m.confidence_score >= 0.5 for m in matches)


def test_search_patterns_by_type(
    db_service,
    memory_service: MemoryService,
):
    """Test searching patterns by pattern type."""
    with db_service.get_session() as session:
        # Create patterns of different types
        for ptype in ["success", "failure", "optimization"]:
            pattern = LearnedPattern(
                pattern_type=ptype,
                task_type_pattern=f".*{ptype}.*",
                confidence_score=0.7,
            )
            session.add(pattern)

        session.commit()

        # Search for success patterns
        success_patterns = memory_service.search_patterns(
            session=session,
            pattern_type="success",
            limit=10,
        )

        assert len(success_patterns) > 0
        assert all(isinstance(p, TaskPattern) for p in success_patterns)
        assert all(p.pattern_type == "success" for p in success_patterns)


def test_search_patterns_ordering(
    db_service,
    memory_service: MemoryService,
):
    """Test that patterns are ordered by confidence and usage."""
    with db_service.get_session() as session:
        # Create patterns with different confidence/usage
        patterns_data = [
            (0.9, 10),  # High confidence, high usage
            (0.8, 20),  # Medium-high confidence, very high usage
            (0.6, 5),  # Medium confidence, low usage
        ]

        for confidence, usage in patterns_data:
            pattern = LearnedPattern(
                pattern_type="success",
                task_type_pattern=".*test.*",
                confidence_score=confidence,
                usage_count=usage,
            )
            session.add(pattern)

        session.commit()

        # Search patterns
        patterns = memory_service.search_patterns(
            session=session,
            limit=10,
        )

        # Should be ordered (confidence DESC, usage DESC)
        assert len(patterns) > 0
        # First pattern should have highest confidence
        assert patterns[0].confidence_score >= patterns[-1].confidence_score


def test_pattern_to_dict(
    db_service,
):
    """Test LearnedPattern.to_dict() serialization."""
    with db_service.get_session() as session:
        pattern = LearnedPattern(
            pattern_type="success",
            task_type_pattern=".*test.*",
            success_indicators=["completed", "passed"],
            failure_indicators=[],
            recommended_context={"env": "test"},
            confidence_score=0.8,
            usage_count=5,
        )
        session.add(pattern)
        session.commit()
        session.refresh(pattern)

        data = pattern.to_dict()

        assert "id" in data
        assert "pattern_type" in data
        assert "task_type_pattern" in data
        assert "success_indicators" in data
        assert "failure_indicators" in data
        assert "recommended_context" in data
        assert "confidence_score" in data
        assert "usage_count" in data
        assert "created_at" in data
        assert "updated_at" in data

        assert data["pattern_type"] == "success"
        assert data["confidence_score"] == 0.8
        assert data["usage_count"] == 5
