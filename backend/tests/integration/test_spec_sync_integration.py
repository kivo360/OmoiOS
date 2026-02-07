"""Integration tests for SpecSyncService with database.

Tests the full sync flow including:
- Requirements, tasks, and criteria creation with deduplication
- Embedding-based semantic similarity detection
- Hash-based exact match detection
- Retry scenarios where duplicates should be skipped
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from omoi_os.services.spec_dedup import (
    SpecDeduplicationService,
    compute_content_hash,
    EntityType,
)
from omoi_os.services.spec_sync import SpecSyncService, SyncStats

# =============================================================================
# Test: SyncStats
# =============================================================================


class TestSyncStats:
    """Test SyncStats dataclass."""

    def test_default_values(self):
        """Test default values are zero."""
        stats = SyncStats()
        assert stats.requirements_created == 0
        assert stats.requirements_skipped == 0
        assert stats.criteria_created == 0
        assert stats.criteria_skipped == 0
        assert stats.tasks_created == 0
        assert stats.tasks_skipped == 0
        assert stats.tickets_created == 0
        assert stats.tickets_skipped == 0
        assert stats.errors == []

    def test_to_dict(self):
        """Test conversion to dictionary."""
        stats = SyncStats(
            requirements_created=5,
            requirements_skipped=2,
            tasks_created=10,
            tickets_created=10,
            errors=["error1"],
        )
        result = stats.to_dict()

        assert result["requirements_created"] == 5
        assert result["requirements_skipped"] == 2
        assert result["tasks_created"] == 10
        assert result["tickets_created"] == 10
        assert result["errors"] == ["error1"]

    def test_accumulation(self):
        """Test stats can be accumulated."""
        stats = SyncStats()
        stats.requirements_created += 1
        stats.requirements_created += 1
        stats.tasks_skipped += 3

        assert stats.requirements_created == 2
        assert stats.tasks_skipped == 3


# =============================================================================
# Test: SpecSyncService Initialization
# =============================================================================


class TestSpecSyncServiceInitialization:
    """Test SpecSyncService initialization."""

    def test_init_with_db_only(self):
        """Test initialization with just database."""
        mock_db = MagicMock()
        service = SpecSyncService(db=mock_db)

        assert service.db == mock_db
        assert service.embedding_service is None
        assert service.dedup_service is not None

    def test_init_with_embedding_service(self):
        """Test initialization with embedding service."""
        mock_db = MagicMock()
        mock_embedding = MagicMock()
        service = SpecSyncService(db=mock_db, embedding_service=mock_embedding)

        assert service.embedding_service == mock_embedding


# =============================================================================
# Test: Deduplication Flow with Mock Database
# =============================================================================


class TestDeduplicationFlow:
    """Test deduplication flow scenarios."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database service."""
        db = MagicMock()
        db.get_async_session = MagicMock()
        return db

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock embedding service."""
        service = MagicMock()
        service.generate_embedding = MagicMock(return_value=[0.1] * 1536)
        return service

    @pytest.mark.asyncio
    async def test_criterion_dedup_exact_match(self, mock_db, mock_session):
        """Test criterion deduplication with exact match."""
        # Setup: Mock existing criterion with same text
        mock_existing = MagicMock()
        mock_existing.id = "crit-existing"
        mock_existing.text = "User sees success message"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing
        mock_session.execute.return_value = mock_result

        dedup_service = SpecDeduplicationService(db=mock_db)

        # Test: Check for duplicate
        result = await dedup_service.check_criterion_duplicate(
            requirement_id="req-123",
            text="User sees success message",  # Same text
            session=mock_session,
        )

        # Verify: Should be detected as duplicate
        assert result.is_duplicate is True
        assert result.action == "skip"
        assert len(result.candidates) == 1
        assert result.candidates[0].is_exact_match is True

    @pytest.mark.asyncio
    async def test_criterion_dedup_no_match(self, mock_db, mock_session):
        """Test criterion deduplication with no match."""
        # Setup: No existing criterion
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        dedup_service = SpecDeduplicationService(db=mock_db)

        # Test: Check for duplicate
        result = await dedup_service.check_criterion_duplicate(
            requirement_id="req-123",
            text="Brand new criterion",
            session=mock_session,
        )

        # Verify: Should not be a duplicate
        assert result.is_duplicate is False
        assert result.action == "create"
        assert result.content_hash is not None

    @pytest.mark.asyncio
    async def test_dedup_service_generates_embedding(
        self, mock_db, mock_session, mock_embedding_service
    ):
        """Test that dedup service uses embedding service when available."""
        # Setup: No existing matches
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        dedup_service = SpecDeduplicationService(
            db=mock_db, embedding_service=mock_embedding_service
        )

        # Test: Check for duplicate - should generate embedding
        result = await dedup_service.check_requirement_duplicate(
            spec_id="spec-123",
            title="Display Message Requirement",
            condition="WHEN user clicks button",
            action="THE SYSTEM SHALL display message",
            session=mock_session,
        )

        # Verify: Embedding should be generated and returned
        assert result.is_duplicate is False
        assert result.action == "create"
        assert result.embedding is not None
        assert len(result.embedding) == 1536
        # Verify embedding service was called
        mock_embedding_service.generate_embedding.assert_called_once()


# =============================================================================
# Test: Bulk Deduplication
# =============================================================================


class TestBulkDeduplication:
    """Test bulk deduplication scenarios."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database service."""
        db = MagicMock()
        return db

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_bulk_criteria_dedup_mixed(self, mock_db, mock_session):
        """Test bulk criteria deduplication with mix of new and duplicate."""
        # Setup: First criterion exists, second is new
        compute_content_hash("existing criterion")

        mock_existing = MagicMock()
        mock_existing.id = "crit-existing"
        mock_existing.text = "existing criterion"

        def mock_execute(query):
            result = MagicMock()
            # Check if query is for the existing criterion
            # Simple mock: return existing for first call, None for second
            if hasattr(mock_execute, "call_count"):
                mock_execute.call_count += 1
            else:
                mock_execute.call_count = 1

            if mock_execute.call_count == 1:
                result.scalar_one_or_none.return_value = mock_existing
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        dedup_service = SpecDeduplicationService(db=mock_db)

        criteria = [
            {"text": "existing criterion"},  # Should be skipped
            {"text": "brand new criterion"},  # Should be created
        ]

        result = await dedup_service.deduplicate_criteria_bulk(
            requirement_id="req-123",
            criteria=criteria,
            session=mock_session,
        )

        # Verify: One to create, one to skip
        assert len(result.to_create) == 1
        assert len(result.to_skip) == 1
        assert result.to_create[0]["text"] == "brand new criterion"


# =============================================================================
# Test: Content Hash Consistency
# =============================================================================


class TestContentHashConsistency:
    """Test content hash is consistent across operations."""

    def test_hash_consistent_for_same_content(self):
        """Same content should produce same hash."""
        content1 = "WHEN user clicks, THE SYSTEM SHALL respond"
        content2 = "WHEN user clicks, THE SYSTEM SHALL respond"

        hash1 = compute_content_hash(content1)
        hash2 = compute_content_hash(content2)

        assert hash1 == hash2

    def test_hash_normalizes_whitespace(self):
        """Hash should normalize whitespace."""
        content1 = "WHEN user clicks"
        content2 = "WHEN  user   clicks"

        hash1 = compute_content_hash(content1)
        hash2 = compute_content_hash(content2)

        assert hash1 == hash2

    def test_hash_case_insensitive(self):
        """Hash should be case insensitive."""
        content1 = "WHEN User Clicks"
        content2 = "when user clicks"

        hash1 = compute_content_hash(content1)
        hash2 = compute_content_hash(content2)

        assert hash1 == hash2

    def test_different_content_different_hash(self):
        """Different content should produce different hash."""
        content1 = "WHEN user clicks button A"
        content2 = "WHEN user clicks button B"

        hash1 = compute_content_hash(content1)
        hash2 = compute_content_hash(content2)

        assert hash1 != hash2


# =============================================================================
# Test: Entity Type Thresholds
# =============================================================================


class TestEntityTypeThresholds:
    """Test that entity types have appropriate thresholds."""

    def test_criterion_uses_hash_only(self):
        """Criteria should use hash-only deduplication (threshold = 1.0)."""
        from omoi_os.services.spec_dedup import SIMILARITY_THRESHOLDS

        assert SIMILARITY_THRESHOLDS[EntityType.CRITERION] == 1.0

    def test_spec_has_highest_threshold(self):
        """Specs should have highest threshold (most strict)."""
        from omoi_os.services.spec_dedup import SIMILARITY_THRESHOLDS

        spec_threshold = SIMILARITY_THRESHOLDS[EntityType.SPEC]
        req_threshold = SIMILARITY_THRESHOLDS[EntityType.REQUIREMENT]
        task_threshold = SIMILARITY_THRESHOLDS[EntityType.TASK]

        assert spec_threshold >= req_threshold
        assert spec_threshold >= task_threshold

    def test_requirement_threshold_reasonable(self):
        """Requirement threshold should be reasonable for semantic matching."""
        from omoi_os.services.spec_dedup import SIMILARITY_THRESHOLDS

        threshold = SIMILARITY_THRESHOLDS[EntityType.REQUIREMENT]

        # Should be between 0.8 and 0.95 for reasonable semantic matching
        assert 0.8 <= threshold <= 0.95


# =============================================================================
# Test: Retry Scenario Simulation
# =============================================================================


class TestRetryScenario:
    """Test deduplication during retry scenarios."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database service."""
        db = MagicMock()
        return db

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_retry_skips_already_created_requirements(
        self, mock_db, mock_session
    ):
        """On retry, already-created requirements should be skipped."""
        # First run: Create requirement
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None
        mock_result_none.scalars.return_value.all.return_value = []

        mock_session.execute.return_value = mock_result_none

        dedup_service = SpecDeduplicationService(db=mock_db)

        # First check - should be new
        result1 = await dedup_service.check_requirement_duplicate(
            spec_id="spec-123",
            title="Click Response Requirement",
            condition="WHEN user clicks",
            action="THE SYSTEM SHALL respond",
            session=mock_session,
        )

        assert result1.is_duplicate is False
        assert result1.action == "create"

        # Second run (retry): Requirement now exists
        mock_existing = MagicMock()
        mock_existing.id = "req-123"
        mock_existing.title = "Created Requirement"
        mock_existing.condition = "WHEN user clicks"
        mock_existing.action = "THE SYSTEM SHALL respond"

        mock_result_existing = MagicMock()
        mock_result_existing.scalar_one_or_none.return_value = mock_existing

        mock_session.execute.return_value = mock_result_existing

        # Second check - should be duplicate
        result2 = await dedup_service.check_requirement_duplicate(
            spec_id="spec-123",
            title="Click Response Requirement",
            condition="WHEN user clicks",
            action="THE SYSTEM SHALL respond",
            session=mock_session,
        )

        assert result2.is_duplicate is True
        assert result2.action == "skip"
