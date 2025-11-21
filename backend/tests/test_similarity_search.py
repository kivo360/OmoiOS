"""Tests for embedding-based similarity search."""

import pytest

from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
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
            description="Test ticket for similarity search tests",
            phase_id="PHASE_IMPLEMENTATION",
            priority="MEDIUM",
            status="open",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        session.expunge(ticket)
        return ticket


def test_vector_similarity_ranking(
    db_service,
    memory_service: MemoryService,
    test_ticket: Ticket,
):
    """Test that similar tasks are ranked correctly by embedding similarity."""
    with db_service.get_session() as session:
        # Create tasks with varying similarity to a query
        tasks_data = [
            (
                "Implement JWT authentication system",
                "Completed JWT auth with Redis sessions",
            ),
            ("Add OAuth2 Google login", "Integrated OAuth2 with Google provider"),
            ("Fix authentication bug", "Fixed token expiration handling"),
            ("Build payment system", "Implemented Stripe payment integration"),
            ("Create user profile page", "Built user profile with avatar upload"),
        ]

        for desc, summary in tasks_data:
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
                success=True,
            )

        session.commit()

        # Search for authentication-related tasks
        query = "Implement user authentication with JWT tokens"
        results = memory_service.search_similar(
            session=session,
            task_description=query,
            top_k=3,
            similarity_threshold=0.1,
        )

        # Should return authentication-related tasks first
        assert len(results) > 0
        # Results should be in descending similarity order
        for i in range(len(results) - 1):
            assert results[i].similarity_score >= results[i + 1].similarity_score


def test_cosine_similarity_calculation(
    embedding_service: EmbeddingService,
):
    """Test cosine similarity calculation between vectors."""
    # Test identical vectors
    vec1 = [1.0, 2.0, 3.0]
    vec2 = [1.0, 2.0, 3.0]
    similarity = embedding_service.cosine_similarity(vec1, vec2)
    assert 0.99 < similarity <= 1.0  # Should be ~1.0 for identical vectors

    # Test orthogonal vectors
    vec3 = [1.0, 0.0, 0.0]
    vec4 = [0.0, 1.0, 0.0]
    similarity = embedding_service.cosine_similarity(vec3, vec4)
    assert abs(similarity) < 0.01  # Should be ~0.0 for orthogonal

    # Test opposite vectors
    vec5 = [1.0, 2.0, 3.0]
    vec6 = [-1.0, -2.0, -3.0]
    similarity = embedding_service.cosine_similarity(vec5, vec6)
    assert -1.0 <= similarity < -0.99  # Should be ~-1.0 for opposite


def test_euclidean_distance_calculation(
    embedding_service: EmbeddingService,
):
    """Test Euclidean distance calculation between vectors."""
    # Test identical vectors
    vec1 = [1.0, 2.0, 3.0]
    vec2 = [1.0, 2.0, 3.0]
    distance = embedding_service.euclidean_distance(vec1, vec2)
    assert distance < 0.01  # Should be ~0.0 for identical vectors

    # Test different vectors
    vec3 = [0.0, 0.0, 0.0]
    vec4 = [3.0, 4.0, 0.0]
    distance = embedding_service.euclidean_distance(vec3, vec4)
    assert 4.99 < distance < 5.01  # Should be 5.0 (Pythagorean theorem)


def test_similarity_threshold_filtering(
    db_service,
    memory_service: MemoryService,
    test_ticket: Ticket,
):
    """Test that similarity threshold correctly filters results."""
    with db_service.get_session() as session:
        # Create diverse tasks
        tasks_data = [
            ("Implement REST API", "Built RESTful API"),
            ("Add database indexes", "Created database indexes"),
            ("Write unit tests", "Wrote comprehensive tests"),
        ]

        for desc, summary in tasks_data:
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
                success=True,
            )

        session.commit()

        # Search with low threshold (should return more results)
        low_threshold_results = memory_service.search_similar(
            session=session,
            task_description="Build API endpoint",
            top_k=10,
            similarity_threshold=0.1,
        )

        # Search with high threshold (should return fewer results)
        high_threshold_results = memory_service.search_similar(
            session=session,
            task_description="Build API endpoint",
            top_k=10,
            similarity_threshold=0.8,
        )

        # Low threshold should return more or equal results
        assert len(low_threshold_results) >= len(high_threshold_results)

        # All high threshold results should exceed threshold
        for result in high_threshold_results:
            assert result.similarity_score >= 0.8


def test_top_k_limit(
    db_service,
    memory_service: MemoryService,
    test_ticket: Ticket,
):
    """Test that top_k correctly limits number of results."""
    with db_service.get_session() as session:
        # Create many tasks
        for i in range(20):
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

        # Search with top_k=5
        results = memory_service.search_similar(
            session=session,
            task_description="Implement feature",
            top_k=5,
            similarity_threshold=0.1,
        )

        # Should return exactly 5 results (or fewer if not enough matches)
        assert len(results) <= 5


def test_embedding_consistency(
    embedding_service: EmbeddingService,
):
    """Test that same text produces consistent embeddings."""
    text = "Implement user authentication with JWT tokens"

    embedding1 = embedding_service.generate_embedding(text)
    embedding2 = embedding_service.generate_embedding(text)

    # Should be identical
    similarity = embedding_service.cosine_similarity(embedding1, embedding2)
    assert similarity > 0.999  # Nearly 1.0 (account for floating point precision)


def test_embedding_dimensions_consistency(
    embedding_service: EmbeddingService,
):
    """Test that all embeddings have consistent dimensions."""
    texts = [
        "Short text",
        "A longer piece of text with more words",
        "This is an even longer text with many more words to see if dimension stays consistent",
    ]

    embeddings = embedding_service.batch_generate_embeddings(texts)

    # All should have same dimensions
    dimensions = [len(emb) for emb in embeddings]
    assert all(d == 1536 for d in dimensions)


def test_batch_embedding_generation(
    embedding_service: EmbeddingService,
):
    """Test batch embedding generation matches individual generation."""
    texts = [
        "Implement authentication",
        "Add payment system",
        "Create admin dashboard",
    ]

    # Generate individually
    individual_embeddings = [
        embedding_service.generate_embedding(text) for text in texts
    ]

    # Generate in batch
    batch_embeddings = embedding_service.batch_generate_embeddings(texts)

    assert len(batch_embeddings) == len(individual_embeddings)

    # Compare similarities (should be very high, accounting for potential batch processing differences)
    for ind_emb, batch_emb in zip(individual_embeddings, batch_embeddings):
        similarity = embedding_service.cosine_similarity(ind_emb, batch_emb)
        assert (
            similarity > 0.99
        )  # Very similar (allow for minor differences in batch processing)
