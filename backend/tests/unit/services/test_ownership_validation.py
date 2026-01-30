"""Unit tests for OwnershipValidationService.

Tests file ownership validation for parallel task conflict prevention.
Uses real database fixtures to properly test SQLAlchemy queries.
"""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService
from omoi_os.services.ownership_validation import (
    OwnershipValidationService,
    ValidationResult,
    OwnershipConflictError,
    get_ownership_validation_service,
    reset_ownership_service,
)


# =============================================================================
# DATACLASS TESTS (No database needed)
# =============================================================================


class TestValidationResult:
    """Tests for the ValidationResult dataclass."""

    def test_has_warnings_true(self):
        """Test has_warnings returns True when warnings exist."""
        result = ValidationResult(
            valid=True,
            conflicts=[],
            warnings=["Some warning"],
            conflicting_task_ids=[],
        )
        assert result.has_warnings

    def test_has_warnings_false(self):
        """Test has_warnings returns False when no warnings."""
        result = ValidationResult(
            valid=True,
            conflicts=[],
            warnings=[],
            conflicting_task_ids=[],
        )
        assert not result.has_warnings

    def test_has_conflicts_true(self):
        """Test has_conflicts returns True when conflicts exist."""
        result = ValidationResult(
            valid=False,
            conflicts=["Conflict!"],
            warnings=[],
            conflicting_task_ids=["task-1"],
        )
        assert result.has_conflicts

    def test_has_conflicts_false(self):
        """Test has_conflicts returns False when no conflicts."""
        result = ValidationResult(
            valid=True,
            conflicts=[],
            warnings=[],
            conflicting_task_ids=[],
        )
        assert not result.has_conflicts


class TestOwnershipConflictError:
    """Tests for the OwnershipConflictError exception."""

    def test_error_message_short(self):
        """Test error message with few conflicts."""
        error = OwnershipConflictError(
            conflicts=["Conflict 1", "Conflict 2"],
            conflicting_task_ids=["task-1"],
        )
        assert "Conflict 1" in str(error)
        assert "Conflict 2" in str(error)

    def test_error_message_truncated(self):
        """Test error message truncates many conflicts."""
        error = OwnershipConflictError(
            conflicts=["C1", "C2", "C3", "C4", "C5"],
            conflicting_task_ids=["task-1"],
        )
        assert "and 2 more" in str(error)

    def test_error_attributes(self):
        """Test error attributes are accessible."""
        error = OwnershipConflictError(
            conflicts=["c1", "c2"],
            conflicting_task_ids=["task-1", "task-2"],
        )
        assert error.conflicts == ["c1", "c2"]
        assert error.conflicting_task_ids == ["task-1", "task-2"]


# =============================================================================
# PATTERN MATCHING TESTS (No database needed)
# =============================================================================


class TestPatternMatching:
    """Tests for glob pattern matching logic."""

    @pytest.fixture
    def ownership_service(self):
        """Create an OwnershipValidationService with mock db for pattern tests."""
        reset_ownership_service()
        mock_db = MagicMock()
        return OwnershipValidationService(db=mock_db, strict_mode=False)

    def test_file_matches_exact_pattern(self, ownership_service):
        """Test exact file path matching."""
        assert ownership_service._file_matches_patterns("src/main.py", ["src/main.py"])

    def test_file_matches_wildcard_extension(self, ownership_service):
        """Test wildcard extension matching."""
        assert ownership_service._file_matches_patterns("test.py", ["*.py"])
        assert not ownership_service._file_matches_patterns("test.js", ["*.py"])

    def test_file_matches_recursive_wildcard(self, ownership_service):
        """Test recursive ** wildcard matching."""
        patterns = ["src/**"]
        assert ownership_service._file_matches_patterns("src/file.py", patterns)
        assert ownership_service._file_matches_patterns("src/deep/nested/file.py", patterns)
        assert not ownership_service._file_matches_patterns("other/file.py", patterns)

    def test_file_matches_recursive_with_extension(self, ownership_service):
        """Test recursive wildcard with extension filter."""
        patterns = ["src/**/*.py"]
        assert ownership_service._file_matches_patterns("src/file.py", patterns)
        assert ownership_service._file_matches_patterns("src/deep/file.py", patterns)
        assert not ownership_service._file_matches_patterns("src/file.js", patterns)

    def test_file_matches_no_patterns(self, ownership_service):
        """Test that empty patterns match nothing."""
        assert not ownership_service._file_matches_patterns("any/file.py", [])

    def test_normalized_path(self, ownership_service):
        """Test that paths are normalized (leading ./ removed)."""
        assert ownership_service._file_matches_patterns("./src/file.py", ["src/**"])

    def test_file_matches_multiple_patterns(self, ownership_service):
        """Test that any matching pattern succeeds."""
        patterns = ["tests/**", "src/services/**"]
        assert ownership_service._file_matches_patterns("tests/test_foo.py", patterns)
        assert ownership_service._file_matches_patterns("src/services/user.py", patterns)
        assert not ownership_service._file_matches_patterns("src/api/routes.py", patterns)


# =============================================================================
# PATTERN OVERLAP DETECTION TESTS (No database needed)
# =============================================================================


class TestPatternOverlapDetection:
    """Tests for detecting overlapping patterns."""

    @pytest.fixture
    def ownership_service(self):
        """Create an OwnershipValidationService with mock db."""
        reset_ownership_service()
        mock_db = MagicMock()
        return OwnershipValidationService(db=mock_db, strict_mode=False)

    def test_patterns_may_overlap_exact_match(self, ownership_service):
        """Test that identical patterns overlap."""
        assert ownership_service._patterns_may_overlap("src/**", "src/**")

    def test_patterns_may_overlap_prefix(self, ownership_service):
        """Test that prefix patterns overlap."""
        assert ownership_service._patterns_may_overlap("src/**", "src/services/**")
        assert ownership_service._patterns_may_overlap("src/services/**", "src/**")

    def test_patterns_may_overlap_recursive_wildcard(self, ownership_service):
        """Test that recursive wildcards might overlap anything under same base."""
        assert ownership_service._patterns_may_overlap("src/**", "src/api/**")

    def test_patterns_no_overlap_different_roots(self, ownership_service):
        """Test that different root directories don't overlap."""
        assert not ownership_service._patterns_may_overlap("src/**", "tests/**")
        assert not ownership_service._patterns_may_overlap("frontend/**", "backend/**")

    def test_find_pattern_overlaps_returns_details(self, ownership_service):
        """Test that find_pattern_overlaps returns overlap details."""
        task_patterns = ["src/**"]
        sibling_patterns = ["src/services/**", "tests/**"]

        overlaps = ownership_service._find_pattern_overlaps(task_patterns, sibling_patterns)

        assert len(overlaps) == 1  # Only src/** overlaps with src/services/**
        assert overlaps[0]["task_pattern"] == "src/**"
        assert overlaps[0]["sibling_pattern"] == "src/services/**"


# =============================================================================
# DATABASE INTEGRATION TESTS
# =============================================================================


class TestOwnershipValidationWithDatabase:
    """Tests that use real database fixtures to test SQLAlchemy queries."""

    @pytest.fixture
    def ticket(self, db_service: DatabaseService) -> Ticket:
        """Create a test ticket."""
        with db_service.get_session() as session:
            ticket = Ticket(
                title="Test Ownership Ticket",
                description="Testing ownership validation",
                phase_id="PHASE_IMPLEMENTATION",
                status="in_progress",
                priority="MEDIUM",
            )
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            session.expunge(ticket)
            return ticket

    @pytest.fixture
    def ownership_service(self, db_service: DatabaseService) -> OwnershipValidationService:
        """Create an OwnershipValidationService with real database."""
        reset_ownership_service()
        return OwnershipValidationService(db=db_service, strict_mode=False)

    @pytest.fixture
    def strict_ownership_service(self, db_service: DatabaseService) -> OwnershipValidationService:
        """Create a strict OwnershipValidationService."""
        return OwnershipValidationService(db=db_service, strict_mode=True)

    def test_task_without_ownership_always_valid(self, ownership_service, db_service, ticket):
        """Test that tasks without owned_files are always valid."""
        with db_service.get_session() as session:
            task = Task(
                ticket_id=ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test_task",
                description="Task without ownership",
                priority="MEDIUM",
                status="pending",
                owned_files=None,  # No ownership
            )
            session.add(task)
            session.commit()
            session.refresh(task)

            result = ownership_service.validate_task_ownership(task)

        assert result.valid
        assert not result.has_conflicts
        assert not result.has_warnings

    def test_no_conflicts_when_no_siblings(self, ownership_service, db_service, ticket):
        """Test no conflicts when there are no parallel siblings."""
        with db_service.get_session() as session:
            task = Task(
                ticket_id=ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test_task",
                description="Only task",
                priority="MEDIUM",
                status="pending",
                owned_files=["src/services/**"],
            )
            session.add(task)
            session.commit()
            session.refresh(task)

            result = ownership_service.validate_task_ownership(task)

        assert result.valid
        assert not result.has_conflicts

    def test_conflict_detected_overlapping_patterns(self, strict_ownership_service, db_service, ticket):
        """Test that overlapping patterns are detected as conflicts in strict mode."""
        with db_service.get_session() as session:
            # Create sibling task first (running, with ownership)
            sibling = Task(
                ticket_id=ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="sibling_task",
                description="Sibling with overlapping ownership",
                priority="MEDIUM",
                status="running",  # Running = parallel
                owned_files=["src/services/user/**"],
            )
            session.add(sibling)
            session.commit()
            sibling_id = str(sibling.id)  # Capture ID before session closes

            # Create task to validate
            task = Task(
                ticket_id=ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test_task",
                description="Task to validate",
                priority="MEDIUM",
                status="pending",
                owned_files=["src/services/**"],  # Overlaps with sibling
            )
            session.add(task)
            session.commit()
            session.refresh(task)

            result = strict_ownership_service.validate_task_ownership(task)

        assert not result.valid
        assert result.has_conflicts
        assert sibling_id in result.conflicting_task_ids

    def test_lenient_mode_reports_warnings(self, ownership_service, db_service, ticket):
        """Test that lenient mode converts conflicts to warnings."""
        with db_service.get_session() as session:
            sibling = Task(
                ticket_id=ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="sibling_task",
                description="Sibling",
                priority="MEDIUM",
                status="running",
                owned_files=["src/api/**"],
            )
            session.add(sibling)
            session.commit()

            task = Task(
                ticket_id=ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test_task",
                description="Task",
                priority="MEDIUM",
                status="pending",
                owned_files=["src/**"],  # Overlaps
            )
            session.add(task)
            session.commit()
            session.refresh(task)

            result = ownership_service.validate_task_ownership(task)

        # In lenient mode, still valid but has warnings
        assert result.valid
        assert not result.has_conflicts
        assert result.has_warnings

    def test_no_conflict_with_completed_tasks(self, ownership_service, db_service, ticket):
        """Test that completed tasks don't cause conflicts."""
        with db_service.get_session() as session:
            completed_task = Task(
                ticket_id=ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="completed_task",
                description="Already done",
                priority="MEDIUM",
                status="completed",  # Completed = not parallel
                owned_files=["src/**"],
            )
            session.add(completed_task)
            session.commit()

            task = Task(
                ticket_id=ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test_task",
                description="New task",
                priority="MEDIUM",
                status="pending",
                owned_files=["src/**"],  # Same pattern but completed task is ignored
            )
            session.add(task)
            session.commit()
            session.refresh(task)

            result = ownership_service.validate_task_ownership(task)

        # No conflict because the sibling is completed
        assert result.valid
        assert not result.has_warnings

    def test_no_conflict_with_different_ownership(self, ownership_service, db_service, ticket):
        """Test no conflict when ownership patterns don't overlap."""
        with db_service.get_session() as session:
            sibling = Task(
                ticket_id=ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="sibling_task",
                description="Sibling",
                priority="MEDIUM",
                status="running",
                owned_files=["frontend/**"],  # Different root
            )
            session.add(sibling)
            session.commit()

            task = Task(
                ticket_id=ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test_task",
                description="Task",
                priority="MEDIUM",
                status="pending",
                owned_files=["backend/**"],  # Non-overlapping
            )
            session.add(task)
            session.commit()
            session.refresh(task)

            result = ownership_service.validate_task_ownership(task)

        assert result.valid
        assert not result.has_conflicts
        assert not result.has_warnings


# =============================================================================
# FILE MODIFICATION VALIDATION TESTS
# =============================================================================


class TestFileModificationValidation:
    """Tests for validating individual file modifications."""

    @pytest.fixture
    def ownership_service(self, db_service: DatabaseService) -> OwnershipValidationService:
        """Create an OwnershipValidationService with real database."""
        reset_ownership_service()
        return OwnershipValidationService(db=db_service, strict_mode=False)

    @pytest.fixture
    def ticket(self, db_service: DatabaseService) -> Ticket:
        """Create a test ticket."""
        with db_service.get_session() as session:
            ticket = Ticket(
                title="File Modification Ticket",
                description="Testing file modification validation",
                phase_id="PHASE_IMPLEMENTATION",
                status="in_progress",
                priority="MEDIUM",
            )
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            session.expunge(ticket)
            return ticket

    def test_modification_allowed_within_ownership(self, ownership_service, db_service, ticket):
        """Test that modifications within ownership patterns are allowed."""
        with db_service.get_session() as session:
            task = Task(
                ticket_id=ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test_task",
                description="Task with ownership",
                priority="MEDIUM",
                status="running",
                owned_files=["src/services/**"],
            )
            session.add(task)
            session.commit()
            task_id = task.id

        assert ownership_service.validate_file_modification(task_id, "src/services/user.py")
        assert ownership_service.validate_file_modification(task_id, "src/services/deep/nested.py")

    def test_modification_blocked_outside_ownership(self, ownership_service, db_service, ticket):
        """Test that modifications outside ownership patterns are blocked."""
        with db_service.get_session() as session:
            task = Task(
                ticket_id=ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test_task",
                description="Task with ownership",
                priority="MEDIUM",
                status="running",
                owned_files=["src/services/**"],
            )
            session.add(task)
            session.commit()
            task_id = task.id

        assert not ownership_service.validate_file_modification(task_id, "src/api/routes.py")
        assert not ownership_service.validate_file_modification(task_id, "tests/test_services.py")

    def test_modification_allowed_no_restrictions(self, ownership_service, db_service, ticket):
        """Test that tasks without ownership can modify any file."""
        with db_service.get_session() as session:
            task = Task(
                ticket_id=ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test_task",
                description="Task without ownership",
                priority="MEDIUM",
                status="running",
                owned_files=None,  # No restrictions
            )
            session.add(task)
            session.commit()
            task_id = task.id

        assert ownership_service.validate_file_modification(task_id, "any/path/file.py")
        assert ownership_service.validate_file_modification(task_id, "anywhere/at/all.txt")

    def test_modification_allowed_task_not_found(self, ownership_service):
        """Test that unknown tasks are allowed (lenient behavior)."""
        # Task doesn't exist - lenient mode allows it
        assert ownership_service.validate_file_modification("non-existent-id", "any/file.py")


# =============================================================================
# FILE OWNERSHIP CHECK TESTS
# =============================================================================


class TestFileOwnershipCheck:
    """Tests for checking who owns a file."""

    @pytest.fixture
    def ownership_service(self, db_service: DatabaseService) -> OwnershipValidationService:
        """Create an OwnershipValidationService with real database."""
        reset_ownership_service()
        return OwnershipValidationService(db=db_service, strict_mode=False)

    @pytest.fixture
    def ticket(self, db_service: DatabaseService) -> Ticket:
        """Create a test ticket."""
        with db_service.get_session() as session:
            ticket = Ticket(
                title="Ownership Check Ticket",
                description="Testing ownership checking",
                phase_id="PHASE_IMPLEMENTATION",
                status="in_progress",
                priority="MEDIUM",
            )
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            session.expunge(ticket)
            return ticket

    def test_check_file_ownership_finds_owner(self, ownership_service, db_service, ticket):
        """Test that check_file_ownership finds the correct owner."""
        with db_service.get_session() as session:
            owner_task = Task(
                ticket_id=ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="owner_task",
                description="Owner task",
                priority="MEDIUM",
                status="running",
                owned_files=["src/services/**"],
            )
            session.add(owner_task)

            other_task = Task(
                ticket_id=ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="other_task",
                description="Other task",
                priority="MEDIUM",
                status="running",
                owned_files=["src/api/**"],
            )
            session.add(other_task)
            session.commit()
            owner_id = owner_task.id
            other_id = other_task.id

        # Check ownership
        result = ownership_service.check_file_ownership(other_id, "src/services/user.py")
        assert result == owner_id

    def test_check_file_ownership_returns_none_no_owner(self, ownership_service, db_service, ticket):
        """Test that check_file_ownership returns None when no owner."""
        with db_service.get_session() as session:
            task = Task(
                ticket_id=ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test_task",
                description="Task",
                priority="MEDIUM",
                status="running",
                owned_files=["src/services/**"],
            )
            session.add(task)
            session.commit()
            task_id = task.id

        # Check ownership of unowned file
        result = ownership_service.check_file_ownership(task_id, "unowned/path/file.py")
        assert result is None


# =============================================================================
# SINGLETON TESTS
# =============================================================================


class TestOwnershipServiceSingleton:
    """Tests for singleton management."""

    def test_get_ownership_service_requires_db_first_call(self):
        """Test that first call requires db."""
        reset_ownership_service()
        with pytest.raises(ValueError, match="db is required"):
            get_ownership_validation_service()

    def test_get_ownership_service_returns_same_instance(self):
        """Test that subsequent calls return the same instance."""
        reset_ownership_service()

        mock_db = MagicMock()

        service1 = get_ownership_validation_service(db=mock_db)
        service2 = get_ownership_validation_service()  # No args needed

        assert service1 is service2

    def test_reset_ownership_service(self):
        """Test that reset clears the singleton."""
        reset_ownership_service()

        mock_db = MagicMock()

        get_ownership_validation_service(db=mock_db)
        reset_ownership_service()

        # Need to provide args again
        with pytest.raises(ValueError):
            get_ownership_validation_service()
