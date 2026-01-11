"""Unit tests for SpecDeduplicationService.

Tests deduplication logic for specs, requirements, tasks, and acceptance criteria
without requiring a real database or embedding service.
"""

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from omoi_os.services.spec_dedup import (
    EntityType,
    SIMILARITY_THRESHOLDS,
    DuplicateCandidate,
    DeduplicationResult,
    BulkDeduplicationResult,
    normalize_text,
    compute_content_hash,
    SpecDeduplicationService,
)


# =============================================================================
# Test: Text Normalization
# =============================================================================


class TestNormalizeText:
    """Test text normalization for consistent hashing."""

    def test_lowercases_text(self):
        """Normalization should lowercase text."""
        assert normalize_text("HELLO WORLD") == "hello world"

    def test_strips_whitespace(self):
        """Normalization should strip leading/trailing whitespace."""
        assert normalize_text("  hello  ") == "hello"

    def test_collapses_multiple_spaces(self):
        """Normalization should collapse multiple spaces."""
        assert normalize_text("hello    world") == "hello world"

    def test_handles_newlines_and_tabs(self):
        """Normalization should handle newlines and tabs."""
        assert normalize_text("hello\n\tworld") == "hello world"

    def test_empty_string(self):
        """Normalization should handle empty string."""
        assert normalize_text("") == ""

    def test_none_like_empty(self):
        """Normalization should handle None-like empty."""
        assert normalize_text("  ") == ""


# =============================================================================
# Test: Content Hash Computation
# =============================================================================


class TestComputeContentHash:
    """Test SHA256 content hash computation."""

    def test_produces_64_char_hash(self):
        """Hash should be 64 characters (SHA256 hex)."""
        result = compute_content_hash("test content")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_same_content_same_hash(self):
        """Same content should produce same hash."""
        hash1 = compute_content_hash("hello world")
        hash2 = compute_content_hash("hello world")
        assert hash1 == hash2

    def test_different_content_different_hash(self):
        """Different content should produce different hash."""
        hash1 = compute_content_hash("hello world")
        hash2 = compute_content_hash("goodbye world")
        assert hash1 != hash2

    def test_normalization_applied(self):
        """Hash should be computed on normalized text."""
        # These should be the same after normalization
        hash1 = compute_content_hash("Hello World")
        hash2 = compute_content_hash("hello   world")
        assert hash1 == hash2

    def test_case_insensitive(self):
        """Hash should be case insensitive."""
        hash1 = compute_content_hash("TEST")
        hash2 = compute_content_hash("test")
        assert hash1 == hash2


# =============================================================================
# Test: Similarity Thresholds
# =============================================================================


class TestSimilarityThresholds:
    """Test that similarity thresholds are properly configured."""

    def test_all_entity_types_have_thresholds(self):
        """All entity types should have thresholds defined."""
        for entity_type in EntityType:
            assert entity_type in SIMILARITY_THRESHOLDS

    def test_spec_threshold_highest(self):
        """Spec threshold should be highest (most strict)."""
        assert SIMILARITY_THRESHOLDS[EntityType.SPEC] >= 0.9

    def test_criterion_threshold_is_one(self):
        """Criterion threshold should be 1.0 (hash only)."""
        assert SIMILARITY_THRESHOLDS[EntityType.CRITERION] == 1.0

    def test_thresholds_are_valid(self):
        """All thresholds should be between 0 and 1."""
        for threshold in SIMILARITY_THRESHOLDS.values():
            assert 0.0 <= threshold <= 1.0


# =============================================================================
# Test: DeduplicationResult Dataclass
# =============================================================================


class TestDeduplicationResult:
    """Test DeduplicationResult dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        result = DeduplicationResult(
            is_duplicate=False,
            action="create",
        )
        assert result.candidates == []
        assert result.highest_similarity == 0.0
        assert result.content_hash is None
        assert result.embedding is None
        assert result.merge_target_id is None
        assert result.reason == ""

    def test_with_duplicate(self):
        """Test result with duplicate found."""
        candidate = DuplicateCandidate(
            entity_id="test-123",
            entity_type=EntityType.SPEC,
            content_preview="Test spec",
            similarity_score=0.95,
            is_exact_match=True,
        )
        result = DeduplicationResult(
            is_duplicate=True,
            action="skip",
            candidates=[candidate],
            highest_similarity=0.95,
            content_hash="abc123",
            reason="Exact match found",
        )
        assert result.is_duplicate
        assert result.action == "skip"
        assert len(result.candidates) == 1
        assert result.candidates[0].similarity_score == 0.95


# =============================================================================
# Test: SpecDeduplicationService (Unit Tests with Mocks)
# =============================================================================


class TestSpecDeduplicationServiceUnit:
    """Unit tests for SpecDeduplicationService using mocks."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database service."""
        db = MagicMock()
        db.get_async_session = MagicMock(return_value=AsyncMock())
        return db

    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock embedding service."""
        service = MagicMock()
        # Return a fake embedding
        service.generate_embedding = MagicMock(
            return_value=[0.1] * 1536
        )
        return service

    @pytest.fixture
    def dedup_service(self, mock_db, mock_embedding_service):
        """Create dedup service with mocks."""
        return SpecDeduplicationService(
            db=mock_db,
            embedding_service=mock_embedding_service,
        )

    def test_initialization(self, mock_db):
        """Test service initializes correctly."""
        service = SpecDeduplicationService(db=mock_db)
        assert service.db == mock_db
        assert service.embedding_service is None

    def test_initialization_with_embedding(self, mock_db, mock_embedding_service):
        """Test service initializes with embedding service."""
        service = SpecDeduplicationService(
            db=mock_db,
            embedding_service=mock_embedding_service,
        )
        assert service.embedding_service == mock_embedding_service

    def test_cosine_similarity_identical_vectors(self, dedup_service):
        """Test cosine similarity with identical vectors."""
        vec = [1.0, 0.0, 0.0]
        similarity = dedup_service._cosine_similarity(vec, vec)
        assert abs(similarity - 1.0) < 0.0001

    def test_cosine_similarity_orthogonal_vectors(self, dedup_service):
        """Test cosine similarity with orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = dedup_service._cosine_similarity(vec1, vec2)
        assert abs(similarity) < 0.0001

    def test_cosine_similarity_opposite_vectors(self, dedup_service):
        """Test cosine similarity with opposite vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = dedup_service._cosine_similarity(vec1, vec2)
        assert abs(similarity - (-1.0)) < 0.0001

    def test_cosine_similarity_empty_vectors(self, dedup_service):
        """Test cosine similarity with empty vectors."""
        similarity = dedup_service._cosine_similarity([], [])
        assert similarity == 0.0

    def test_cosine_similarity_mismatched_lengths(self, dedup_service):
        """Test cosine similarity with mismatched vector lengths."""
        vec1 = [1.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = dedup_service._cosine_similarity(vec1, vec2)
        assert similarity == 0.0

    def test_get_content_preview_spec(self, dedup_service):
        """Test content preview for spec entity."""
        mock_entity = MagicMock()
        mock_entity.title = "Test Spec"
        mock_entity.description = "This is a test description that is longer than 80 characters and should be truncated properly"

        preview = dedup_service._get_content_preview(mock_entity, EntityType.SPEC)
        assert "Test Spec:" in preview
        assert len(preview) <= 120  # title + ": " + 80 chars

    def test_get_content_preview_requirement(self, dedup_service):
        """Test content preview for requirement entity."""
        mock_entity = MagicMock()
        mock_entity.title = "Test Req"
        mock_entity.condition = "When user clicks button"

        preview = dedup_service._get_content_preview(mock_entity, EntityType.REQUIREMENT)
        assert "Test Req:" in preview
        assert "When user" in preview

    def test_get_content_preview_task(self, dedup_service):
        """Test content preview for task entity."""
        mock_entity = MagicMock()
        mock_entity.title = "Test Task"
        mock_entity.description = "Implement feature X"

        preview = dedup_service._get_content_preview(mock_entity, EntityType.TASK)
        assert "Test Task:" in preview
        assert "Implement" in preview

    def test_get_content_preview_criterion(self, dedup_service):
        """Test content preview for criterion entity."""
        mock_entity = MagicMock()
        mock_entity.text = "User should see success message"

        preview = dedup_service._get_content_preview(mock_entity, EntityType.CRITERION)
        assert "success message" in preview


# =============================================================================
# Test: Bulk Deduplication Results
# =============================================================================


class TestBulkDeduplicationResult:
    """Test BulkDeduplicationResult dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        result = BulkDeduplicationResult()
        assert result.to_create == []
        assert result.to_skip == []
        assert result.to_merge == []
        assert result.stats == {}

    def test_with_items(self):
        """Test result with categorized items."""
        result = BulkDeduplicationResult(
            to_create=[{"title": "New item"}],
            to_skip=[{"title": "Duplicate"}],
            stats={"created": 1, "skipped": 1},
        )
        assert len(result.to_create) == 1
        assert len(result.to_skip) == 1
        assert result.stats["created"] == 1


# =============================================================================
# Test: Integration-style tests with mock session
# =============================================================================


class TestCheckDuplicateLogic:
    """Test the core duplicate checking logic."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def mock_db(self, mock_session):
        """Create mock database service."""
        db = MagicMock()
        # Create async context manager for get_async_session
        async_cm = AsyncMock()
        async_cm.__aenter__.return_value = mock_session
        async_cm.__aexit__.return_value = None
        db.get_async_session.return_value = async_cm
        return db

    @pytest.mark.asyncio
    async def test_check_criterion_duplicate_no_match(self, mock_db, mock_session):
        """Test criterion check when no duplicate exists."""
        # Mock query result - no match
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = SpecDeduplicationService(db=mock_db)
        result = await service.check_criterion_duplicate(
            requirement_id="req-123",
            text="New acceptance criterion",
            session=mock_session,
        )

        assert not result.is_duplicate
        assert result.action == "create"
        assert result.content_hash is not None

    @pytest.mark.asyncio
    async def test_check_criterion_duplicate_with_match(self, mock_db, mock_session):
        """Test criterion check when duplicate exists."""
        # Mock existing criterion
        mock_existing = MagicMock()
        mock_existing.id = "crit-existing"
        mock_existing.text = "Existing criterion"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing
        mock_session.execute.return_value = mock_result

        service = SpecDeduplicationService(db=mock_db)
        result = await service.check_criterion_duplicate(
            requirement_id="req-123",
            text="Existing criterion",  # Same normalized text
            session=mock_session,
        )

        assert result.is_duplicate
        assert result.action == "skip"
        assert len(result.candidates) == 1
        assert result.candidates[0].entity_id == "crit-existing"
        assert result.candidates[0].is_exact_match


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_normalize_unicode_text(self):
        """Test normalization handles unicode properly."""
        result = normalize_text("Héllo Wörld")
        assert result == "héllo wörld"

    def test_hash_empty_content(self):
        """Test hash with empty content."""
        result = compute_content_hash("")
        assert len(result) == 64
        # Empty string should have consistent hash
        assert result == compute_content_hash("   ")

    def test_hash_very_long_content(self):
        """Test hash with very long content."""
        long_content = "x" * 100000
        result = compute_content_hash(long_content)
        assert len(result) == 64

    def test_duplicate_candidate_str_representation(self):
        """Test DuplicateCandidate has useful string representation."""
        candidate = DuplicateCandidate(
            entity_id="test-123",
            entity_type=EntityType.SPEC,
            content_preview="Test",
            similarity_score=0.95,
            is_exact_match=True,
        )
        # Should not raise
        str(candidate)
