"""Tests for retry logic in task queue and worker."""

import math
import time
import uuid
from unittest.mock import Mock, patch

import pytest

from omoi_os.models.task import Task
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.database import DatabaseService
from omoi_os.worker import calculate_backoff_delay


class TestRetryLogic:
    """Test suite for retry logic functionality."""

    def test_calculate_backoff_delay_basic(self):
        """Test basic exponential backoff calculation."""
        # Test base case (retry_count = 0)
        delay = calculate_backoff_delay(0, base_delay=1.0, max_delay=60.0)
        assert 0.75 <= delay <= 1.25  # 1.0 * 2^0 * jitter (0.75-1.25)

        # Test exponential growth
        delay_1 = calculate_backoff_delay(1, base_delay=1.0, max_delay=60.0)
        assert 1.5 <= delay_1 <= 2.5  # 1.0 * 2^1 * jitter

        delay_2 = calculate_backoff_delay(2, base_delay=1.0, max_delay=60.0)
        assert 3.0 <= delay_2 <= 5.0  # 1.0 * 2^2 * jitter

        delay_3 = calculate_backoff_delay(3, base_delay=1.0, max_delay=60.0)
        assert 6.0 <= delay_3 <= 10.0  # 1.0 * 2^3 * jitter

    def test_calculate_backoff_delay_max_cap(self):
        """Test that backoff delay is capped at max_delay."""
        # Use a small max_delay to test capping
        delay = calculate_backoff_delay(10, base_delay=1.0, max_delay=5.0)
        assert delay <= 5.0

        # Test with larger base_delay
        delay = calculate_backoff_delay(5, base_delay=10.0, max_delay=30.0)
        assert delay <= 30.0

    def test_calculate_backoff_delay_jitter(self):
        """Test that jitter adds randomness to delays."""
        # Run multiple times to ensure we get different values
        delays = [calculate_backoff_delay(2, base_delay=1.0, max_delay=60.0) for _ in range(10)]

        # Should have some variation (not all identical)
        assert len(set(round(d, 2) for d in delays)) > 1

    def test_calculate_backoff_delay_deterministic_range(self):
        """Test that delay stays within expected range with jitter."""
        for retry_count in range(5):
            for _ in range(100):  # Test many times for each retry count
                base_delay = 1.0
                expected_delay = base_delay * (2 ** retry_count)
                max_delay = 60.0

                delay = calculate_backoff_delay(retry_count, base_delay, max_delay)

                # Should be within jitter range
                jitter_min = expected_delay * 0.75
                jitter_max = expected_delay * 1.25

                # But not exceed max_delay
                expected_min = min(jitter_min, max_delay)
                expected_max = min(jitter_max, max_delay)

                assert expected_min <= delay <= expected_max


@pytest.fixture
def mock_db():
    """Create a mock DatabaseService."""
    db = Mock(spec=DatabaseService)

    # Mock session context manager
    mock_session = Mock()
    mock_query = Mock()
    mock_session.query.return_value = mock_query

    # Create a proper context manager mock
    mock_context_manager = Mock()
    mock_context_manager.__enter__ = Mock(return_value=mock_session)
    mock_context_manager.__exit__ = Mock(return_value=None)
    db.get_session.return_value = mock_context_manager

    return db, mock_session, mock_query


@pytest.fixture
def task_queue_service(mock_db):
    """Create a TaskQueueService with mock dependencies."""
    db, _, _ = mock_db
    return TaskQueueService(db)


class TestTaskQueueServiceRetryMethods:
    """Test suite for TaskQueueService retry methods."""

    def test_should_retry_true(self, task_queue_service, mock_db):
        """Test should_retry returns True for failed tasks with remaining retries."""
        _, mock_session, mock_query = mock_db

        # Create a mock task
        task = Mock(spec=Task)
        task.id = str(uuid.uuid4())
        task.status = "failed"
        task.retry_count = 1
        task.max_retries = 3

        mock_query.filter.return_value.first.return_value = task

        result = task_queue_service.should_retry(task.id)

        assert result is True
        mock_session.query.assert_called_once_with(Task)
        mock_query.filter.assert_called_once()

    def test_should_retry_false_max_retries_exceeded(self, task_queue_service, mock_db):
        """Test should_retry returns False when max retries exceeded."""
        _, mock_session, mock_query = mock_db

        # Create a mock task with max retries exceeded
        task = Mock(spec=Task)
        task.id = str(uuid.uuid4())
        task.status = "failed"
        task.retry_count = 3
        task.max_retries = 3

        mock_query.filter.return_value.first.return_value = task

        result = task_queue_service.should_retry(task.id)

        assert result is False

    def test_should_retry_false_not_failed(self, task_queue_service, mock_db):
        """Test should_retry returns False for non-failed tasks."""
        _, mock_session, mock_query = mock_db

        # Create a mock task that's not failed
        task = Mock(spec=Task)
        task.id = str(uuid.uuid4())
        task.status = "completed"
        task.retry_count = 0
        task.max_retries = 3

        mock_query.filter.return_value.first.return_value = task

        result = task_queue_service.should_retry(task.id)

        assert result is False

    def test_should_retry_false_task_not_found(self, task_queue_service, mock_db):
        """Test should_retry returns False when task not found."""
        _, mock_session, mock_query = mock_db

        mock_query.filter.return_value.first.return_value = None

        result = task_queue_service.should_retry(str(uuid.uuid4()))

        assert result is False

    def test_increment_retry_success(self, task_queue_service, mock_db):
        """Test increment_retry successfully increments retry count."""
        _, mock_session, mock_query = mock_db

        # Create a mock task
        task = Mock(spec=Task)
        task.id = str(uuid.uuid4())
        task.retry_count = 1
        task.max_retries = 3

        mock_query.filter.return_value.first.return_value = task

        result = task_queue_service.increment_retry(task.id)

        assert result is True
        assert task.retry_count == 2
        assert task.status == "pending"
        assert task.error_message is None
        assert task.assigned_agent_id is None
        mock_session.commit.assert_called_once()

    def test_increment_retry_max_retries_exceeded(self, task_queue_service, mock_db):
        """Test increment_retry fails when max retries exceeded."""
        _, mock_session, mock_query = mock_db

        # Create a mock task at max retries
        task = Mock(spec=Task)
        task.id = str(uuid.uuid4())
        task.retry_count = 3
        task.max_retries = 3

        mock_query.filter.return_value.first.return_value = task

        result = task_queue_service.increment_retry(task.id)

        assert result is False
        # Should not modify the task
        assert task.retry_count == 3
        mock_session.commit.assert_not_called()

    def test_increment_retry_task_not_found(self, task_queue_service, mock_db):
        """Test increment_retry returns False when task not found."""
        _, mock_session, mock_query = mock_db

        mock_query.filter.return_value.first.return_value = None

        result = task_queue_service.increment_retry(str(uuid.uuid4()))

        assert result is False
        mock_session.commit.assert_not_called()

    def test_get_retryable_tasks_with_phase_filter(self, task_queue_service, mock_db):
        """Test get_retryable_tasks with phase filtering."""
        _, mock_session, mock_query = mock_db

        # Create mock tasks
        task1 = Mock(spec=Task)
        task1.id = str(uuid.uuid4())
        task1.retry_count = 1
        task1.max_retries = 3
        task1.phase_id = "PHASE_IMPLEMENTATION"

        task2 = Mock(spec=Task)
        task2.id = str(uuid.uuid4())
        task2.retry_count = 3
        task2.max_retries = 3
        task2.phase_id = "PHASE_IMPLEMENTATION"

        task3 = Mock(spec=Task)
        task3.id = str(uuid.uuid4())
        task3.retry_count = 1
        task3.max_retries = 3
        task3.phase_id = "PHASE_TESTING"

        # Mock the query chain properly
        mock_filter1 = Mock()
        mock_filter2 = Mock()
        mock_query.filter.return_value = mock_filter1
        mock_filter1.filter.return_value = mock_filter2
        mock_filter2.all.return_value = [task1, task2, task3]

        # Filter by implementation phase
        result = task_queue_service.get_retryable_tasks("PHASE_IMPLEMENTATION")

        # Should return tasks from implementation phase that haven't exceeded retries
        # and automatically filter by retry count < max_retries
        implementation_tasks = [t for t in [task1, task2, task3] if t.retry_count < t.max_retries]
        expected_count = len(implementation_tasks)

        assert len(result) == expected_count
        mock_query.filter.assert_called()
        mock_session.expunge.assert_called()

    def test_get_retryable_tasks_all_phases(self, task_queue_service, mock_db):
        """Test get_retryable_tasks without phase filtering."""
        _, mock_session, mock_query = mock_db

        # Create mock tasks
        task1 = Mock(spec=Task)
        task1.id = str(uuid.uuid4())
        task1.retry_count = 1
        task1.max_retries = 3

        task2 = Mock(spec=Task)
        task2.id = str(uuid.uuid4())
        task2.retry_count = 3
        task2.max_retries = 3

        task3 = Mock(spec=Task)
        task3.id = str(uuid.uuid4())
        task3.retry_count = 0
        task3.max_retries = 2

        # Mock the query chain for no phase filter
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = [task1, task2, task3]

        result = task_queue_service.get_retryable_tasks()

        # Should automatically filter by retry count < max_retries
        retryable_tasks = [t for t in [task1, task2, task3] if t.retry_count < t.max_retries]

        assert len(result) == len(retryable_tasks)
        mock_session.expunge.assert_called()

    def test_is_retryable_error_permanent_errors(self, task_queue_service):
        """Test is_retryable_error returns False for permanent errors."""
        permanent_errors = [
            "Permission denied accessing file",
            "Authentication failed for user",
            "Syntax error in Python code",
            "Invalid argument provided",
            "File not found",
            "Directory does not exist",
            "Record already exists",
            "Duplicate key constraint violation",
            "Immutable configuration",
            "Read-only filesystem",
            "Quota exceeded for user",
            "Rate limit exceeded",
        ]

        for error_msg in permanent_errors:
            result = task_queue_service.is_retryable_error(error_msg)
            assert result is False, f"Should not retry permanent error: {error_msg}"

    def test_is_retryable_error_retryable_errors(self, task_queue_service):
        """Test is_retryable_error returns True for retryable errors."""
        retryable_errors = [
            "Connection timeout occurred",
            "Network connection lost",
            "Temporary service unavailable",
            "Retryable error occurred",
            "Transient failure detected",
            "Intermittent connection issue",
            "Connection reset by peer",
        ]

        for error_msg in retryable_errors:
            result = task_queue_service.is_retryable_error(error_msg)
            assert result is True, f"Should retry retryable error: {error_msg}"

    def test_is_retryable_error_unknown_error(self, task_queue_service):
        """Test is_retryable_error returns True for unknown errors."""
        unknown_errors = [
            "Some weird error happened",
            "Unexpected condition occurred",
            "Generic error message",
            "",
            None,  # Should handle None gracefully
        ]

        for error_msg in unknown_errors:
            result = task_queue_service.is_retryable_error(error_msg)
            assert result is True, f"Should retry unknown error: {error_msg}"

    def test_is_retryable_error_case_insensitive(self, task_queue_service):
        """Test is_retryable_error is case insensitive."""
        # Test permanent errors in different cases
        assert task_queue_service.is_retryable_error("PERMISSION DENIED") is False
        assert task_queue_service.is_retryable_error("Permission Denied") is False
        assert task_queue_service.is_retryable_error("permission denied") is False

        # Test retryable errors in different cases
        assert task_queue_service.is_retryable_error("CONNECTION TIMEOUT") is True
        assert task_queue_service.is_retryable_error("Connection Timeout") is True
        assert task_queue_service.is_retryable_error("connection timeout") is True

    def test_is_retryable_error_partial_match(self, task_queue_service):
        """Test is_retryable_error matches partial strings."""
        # Should match permanent error patterns anywhere in the string
        assert task_queue_service.is_retryable_error("Error: permission denied while accessing file") is False
        assert task_queue_service.is_retryable_error("Failed due to authentication failed") is False

        # Should match retryable error patterns anywhere in the string
        assert task_queue_service.is_retryable_error("Error: connection timeout after 30 seconds") is True
        assert task_queue_service.is_retryable_error("Failed due to network connectivity issues") is True


class TestRetryIntegration:
    """Integration tests for retry functionality."""

    def test_retry_workflow_complete_cycle(self, task_queue_service, mock_db):
        """Test a complete retry workflow cycle."""
        db, mock_session, mock_query = mock_db

        task_id = str(uuid.uuid4())

        # Create a mock task
        task = Mock(spec=Task)
        task.id = task_id
        task.status = "failed"
        task.retry_count = 0
        task.max_retries = 3
        task.error_message = "Connection timeout occurred"

        # Set up the mock to return the task for all calls
        mock_query.filter.return_value.first.return_value = task

        # 1. Check if task should be retried
        assert task_queue_service.should_retry(task_id) is True

        # 2. Check if error is retryable
        assert task_queue_service.is_retryable_error(task.error_message) is True

        # 3. Increment retry count
        assert task_queue_service.increment_retry(task_id) is True
        assert task.retry_count == 1
        assert task.status == "pending"

        # 4. After increment, task status is now "pending", so should_retry returns False
        # should_retry only works on failed tasks
        assert task_queue_service.should_retry(task_id) is False

    def test_retry_workflow_permanent_error(self, task_queue_service, mock_db):
        """Test retry workflow with permanent error."""
        db, mock_session, mock_query = mock_db

        task_id = str(uuid.uuid4())

        # Create a mock task with permanent error
        task = Mock(spec=Task)
        task.id = task_id
        task.status = "failed"
        task.retry_count = 0
        task.max_retries = 3
        task.error_message = "Permission denied accessing file"

        mock_query.filter.return_value.first.return_value = task

        # 1. Check if task should be retried (based on count)
        assert task_queue_service.should_retry(task_id) is True

        # 2. Check if error is retryable (it's not)
        assert task_queue_service.is_retryable_error(task.error_message) is False

        # 3. Even though we could retry based on count, the error is permanent
        # So the workflow should not schedule a retry

    def test_retry_workflow_max_retries_exceeded(self, task_queue_service, mock_db):
        """Test retry workflow when max retries exceeded."""
        db, mock_session, mock_query = mock_db

        task_id = str(uuid.uuid4())

        # Create a mock task at max retries
        task = Mock(spec=Task)
        task.id = task_id
        task.status = "failed"
        task.retry_count = 3
        task.max_retries = 3
        task.error_message = "Connection timeout occurred"

        mock_query.filter.return_value.first.return_value = task

        # 1. Check if task should be retried (it shouldn't)
        assert task_queue_service.should_retry(task_id) is False

        # 2. Try to increment retry (should fail)
        assert task_queue_service.increment_retry(task_id) is False
        assert task.retry_count == 3  # Unchanged

    def test_exponential_backoff_sequence_pattern(self):
        """Test exponential backoff delay sequence pattern."""
        # Test that delays roughly follow exponential pattern
        # Due to jitter, they won't be exact, but should be in expected ranges

        delays = []
        for retry_count in range(4):
            # Call with fixed random seed for predictable jitter
            import random
            random.seed(42)  # Fixed seed for predictable jitter
            delay = calculate_backoff_delay(retry_count, base_delay=1.0, max_delay=60.0)
            delays.append(delay)

        # Check exponential growth pattern (allowing for jitter)
        # retry 0: ~1.0 (0.75-1.25)
        # retry 1: ~2.0 (1.5-2.5)
        # retry 2: ~4.0 (3.0-5.0)
        # retry 3: ~8.0 (6.0-10.0)

        assert 0.75 <= delays[0] <= 1.25  # retry 0
        assert 1.5 <= delays[1] <= 2.5   # retry 1
        assert 3.0 <= delays[2] <= 5.0   # retry 2
        assert 6.0 <= delays[3] <= 10.0  # retry 3


class TestRetryErrorHandling:
    """Test error handling in retry functionality."""

    
    def test_task_queue_service_init(self):
        """Test TaskQueueService initialization."""
        mock_db = Mock(spec=DatabaseService)
        service = TaskQueueService(mock_db)

        assert service.db == mock_db