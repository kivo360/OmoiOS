"""Tests for task timeout and cancellation functionality (Agent D)."""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.worker import TimeoutManager


@pytest.fixture
def mock_db():
    """Mock database service."""
    return Mock(spec=DatabaseService)


@pytest.fixture
def mock_event_bus():
    """Mock event bus service."""
    return Mock(spec=EventBusService)


@pytest.fixture
def task_queue(mock_db):
    """Task queue service with mock database."""
    return TaskQueueService(mock_db)


@pytest.fixture
def timeout_manager(task_queue, mock_event_bus):
    """Timeout manager with mocked dependencies."""
    return TimeoutManager(task_queue, mock_event_bus, interval_seconds=1)


@pytest.fixture
def sample_task():
    """Sample task for testing."""
    task = Mock(spec=Task)
    task.id = "test-task-123"
    task.ticket_id = "test-ticket-456"
    task.phase_id = "PHASE_IMPLEMENTATION"
    task.task_type = "implement_feature"
    task.description = "Test task description"
    task.priority = "HIGH"
    task.status = "running"
    task.assigned_agent_id = "agent-789"
    task.timeout_seconds = 30
    task.started_at = datetime.utcnow() - timedelta(seconds=35)  # 35 seconds ago
    task.created_at = datetime.utcnow() - timedelta(minutes=5)
    return task


class TestTaskTimeoutMethods:
    """Test timeout methods in TaskQueueService."""

    def test_check_task_timeout_true(self, task_queue, sample_task):
        """Test timeout detection for timed-out task."""
        with patch.object(task_queue, 'db') as mock_db:
            mock_session = Mock()
            mock_db.get_session.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = sample_task

            # Should return True since task started 35s ago with 30s timeout
            assert task_queue.check_task_timeout("test-task-123") == True

    def test_check_task_timeout_false(self, task_queue):
        """Test timeout detection for non-timed-out task."""
        # Create task that started recently
        recent_task = Mock(spec=Task)
        recent_task.status = "running"
        recent_task.timeout_seconds = 30
        recent_task.started_at = datetime.utcnow() - timedelta(seconds=10)  # 10 seconds ago

        with patch.object(task_queue, 'db') as mock_db:
            mock_session = Mock()
            mock_db.get_session.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = recent_task

            # Should return False since only 10s elapsed with 30s timeout
            assert task_queue.check_task_timeout("test-task-123") == False

    def test_check_task_timeout_not_running(self, task_queue, sample_task):
        """Test timeout detection for non-running task."""
        sample_task.status = "completed"

        with patch.object(task_queue, 'db') as mock_db:
            mock_session = Mock()
            mock_db.get_session.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = sample_task

            # Should return False since task is not running
            assert task_queue.check_task_timeout("test-task-123") == False

    def test_cancel_task_success(self, task_queue, sample_task):
        """Test successful task cancellation."""
        sample_task.status = "running"

        with patch.object(task_queue, 'db') as mock_db:
            mock_session = Mock()
            mock_db.get_session.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = sample_task

            result = task_queue.cancel_task("test-task-123", "user_requested")

            assert result == True
            assert sample_task.status == "failed"
            assert "Task cancelled: user_requested" in sample_task.error_message
            mock_session.commit.assert_called_once()

    def test_cancel_task_not_found(self, task_queue):
        """Test cancellation of non-existent task."""
        with patch.object(task_queue, 'db') as mock_db:
            mock_session = Mock()
            mock_db.get_session.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = None

            result = task_queue.cancel_task("non-existent")

            assert result == False

    def test_cancel_task_not_cancellable(self, task_queue, sample_task):
        """Test cancellation of completed task."""
        sample_task.status = "completed"

        with patch.object(task_queue, 'db') as mock_db:
            mock_session = Mock()
            mock_db.get_session.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = sample_task

            result = task_queue.cancel_task("test-task-123")

            assert result == False

    def test_get_timed_out_tasks(self, task_queue):
        """Test getting all timed-out tasks."""
        timed_out_task = Mock(spec=Task)
        timed_out_task.id = "timed-out-task"
        timed_out_task.started_at = datetime.utcnow() - timedelta(seconds=60)
        timed_out_task.timeout_seconds = 30

        running_task = Mock(spec=Task)
        running_task.id = "running-task"
        running_task.started_at = datetime.utcnow() - timedelta(seconds=10)
        running_task.timeout_seconds = 30

        with patch.object(task_queue, 'db') as mock_db:
            mock_session = Mock()
            mock_db.get_session.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.all.return_value = [timed_out_task, running_task]

            # Mock expunge
            mock_session.expunge = Mock()

            timed_out_tasks = task_queue.get_timed_out_tasks()

            # Should only return the timed-out task
            assert len(timed_out_tasks) == 1
            assert timed_out_tasks[0].id == "timed-out-task"

    def test_mark_task_timeout(self, task_queue, sample_task):
        """Test marking task as timed out."""
        sample_task.status = "running"

        with patch.object(task_queue, 'db') as mock_db:
            mock_session = Mock()
            mock_db.get_session.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = sample_task

            result = task_queue.mark_task_timeout("test-task-123", "timeout_exceeded")

            assert result == True
            assert sample_task.status == "failed"
            assert "Task timed out" in sample_task.error_message
            assert "timeout_exceeded" in sample_task.error_message
            mock_session.commit.assert_called_once()

    def test_get_cancellable_tasks(self, task_queue):
        """Test getting cancellable tasks."""
        running_task = Mock(spec=Task)
        running_task.id = "running-task"
        running_task.status = "running"

        assigned_task = Mock(spec=Task)
        assigned_task.id = "assigned-task"
        assigned_task.status = "assigned"

        completed_task = Mock(spec=Task)
        completed_task.id = "completed-task"
        completed_task.status = "completed"

        with patch.object(task_queue, 'db') as mock_db:
            mock_session = Mock()
            mock_db.get_session.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.all.return_value = [
                running_task, assigned_task, completed_task
            ]

            # Mock expunge
            mock_session.expunge = Mock()

            cancellable_tasks = task_queue.get_cancellable_tasks()

            # Should only return running and assigned tasks
            assert len(cancellable_tasks) == 2
            task_ids = [task.id for task in cancellable_tasks]
            assert "running-task" in task_ids
            assert "assigned-task" in task_ids
            assert "completed-task" not in task_ids

    def test_get_task_elapsed_time(self, task_queue, sample_task):
        """Test getting elapsed time for running task."""
        with patch.object(task_queue, 'db') as mock_db:
            mock_session = Mock()
            mock_db.get_session.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = sample_task

            elapsed = task_queue.get_task_elapsed_time("test-task-123")

            assert elapsed is not None
            assert elapsed > 30  # Should be > 30 seconds

    def test_get_task_timeout_status(self, task_queue, sample_task):
        """Test getting comprehensive timeout status."""
        sample_task.timeout_seconds = 60

        with patch.object(task_queue, 'db') as mock_db:
            mock_session = Mock()
            mock_db.get_session.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = sample_task

            status = task_queue.get_task_timeout_status("test-task-123")

            assert status["exists"] == True
            assert status["status"] == "running"
            assert status["timeout_seconds"] == 60
            assert status["elapsed_seconds"] > 30
            assert status["is_timed_out"] == True  # Since sample task started 35s ago with 60s timeout
            assert status["can_cancel"] == True

    def test_get_task_timeout_status_not_found(self, task_queue):
        """Test timeout status for non-existent task."""
        with patch.object(task_queue, 'db') as mock_db:
            mock_session = Mock()
            mock_db.get_session.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = None

            status = task_queue.get_task_timeout_status("non-existent")

            assert status["exists"] == False


class TestTimeoutManager:
    """Test TimeoutManager functionality."""

    def test_timeout_manager_initialization(self, timeout_manager):
        """Test TimeoutManager initialization."""
        assert timeout_manager.task_queue is not None
        assert timeout_manager.event_bus is not None
        assert timeout_manager.interval_seconds == 1
        assert timeout_manager._running == False
        assert timeout_manager._thread is None

    def test_timeout_manager_start_stop(self, timeout_manager):
        """Test starting and stopping TimeoutManager."""
        # Start the manager
        timeout_manager.start()
        assert timeout_manager._running == True
        assert timeout_manager._thread is not None

        # Stop the manager
        timeout_manager.stop()
        assert timeout_manager._running == False

    @patch('time.sleep')
    def test_timeout_monitoring_loop(self, mock_sleep, timeout_manager, sample_task):
        """Test timeout monitoring loop."""
        # Mock the timed out tasks response
        with patch.object(timeout_manager.task_queue, 'get_timed_out_tasks') as mock_get_timed_out, \
             patch.object(timeout_manager.task_queue, 'mark_task_timeout') as mock_mark_timeout, \
             patch.object(timeout_manager.task_queue, 'get_task_elapsed_time') as mock_get_elapsed, \
             patch.object(timeout_manager.event_bus, 'publish') as mock_publish:

            # Setup mocks
            mock_get_timed_out.return_value = [sample_task]
            mock_mark_timeout.return_value = True
            mock_get_elapsed.return_value = 35.0
            mock_sleep.side_effect = [None, KeyboardInterrupt]  # Sleep once then interrupt

            # Set running to True to start the loop
            timeout_manager._running = True

            # Run the loop (should stop after KeyboardInterrupt)
            with pytest.raises(KeyboardInterrupt):
                timeout_manager._timeout_monitoring_loop()

            # Verify interactions
            mock_get_timed_out.assert_called()
            mock_mark_timeout.assert_called_with(sample_task.id)
            mock_publish.assert_called_once()

            # Check the published event
            event_call = mock_publish.call_args[0][0]
            assert isinstance(event_call, SystemEvent)
            assert event_call.event_type == "TASK_TIMED_OUT"
            assert event_call.entity_id == str(sample_task.id)

    def test_check_task_cancellation_before_execution_success(self, timeout_manager, sample_task):
        """Test cancellation check before execution - task can proceed."""
        sample_task.status = "running"

        with patch.object(timeout_manager.task_queue.db, 'get_session') as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = sample_task

            result = timeout_manager.check_task_cancellation_before_execution(sample_task)

            assert result == True

    def test_check_task_cancellation_before_execution_cancelled(self, timeout_manager, sample_task):
        """Test cancellation check before execution - task was cancelled."""
        sample_task.status = "failed"

        with patch.object(timeout_manager.task_queue.db, 'get_session') as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = sample_task

            with patch('builtins.print') as mock_print:
                result = timeout_manager.check_task_cancellation_before_execution(sample_task)

                assert result == False
                mock_print.assert_called_with(f"Task {sample_task.id} status changed to {sample_task.status}, cancelling execution")

    def test_handle_task_timeout_during_execution_with_termination(self, timeout_manager, sample_task):
        """Test handling timeout during execution with termination support."""
        mock_executor = Mock()
        mock_executor.terminate_conversation = Mock()

        with patch('builtins.print') as mock_print:
            timeout_manager.handle_task_timeout_during_execution(sample_task, mock_executor)

            mock_executor.terminate_conversation.assert_called_once()
            mock_print.assert_any_call(f"Handling timeout for task {sample_task.id}")
            mock_print.assert_any_call(f"Terminated conversation for timed-out task {sample_task.id}")

    def test_handle_task_timeout_during_execution_without_termination(self, timeout_manager, sample_task):
        """Test handling timeout during execution without termination support."""
        mock_executor = Mock()
        # Don't add terminate_conversation method

        with patch('builtins.print') as mock_print:
            timeout_manager.handle_task_timeout_during_execution(sample_task, mock_executor)

            mock_print.assert_any_call(f"Handling timeout for task {sample_task.id}")
            mock_print.assert_any_call(f"Executor for task {sample_task.id} does not support conversation termination")


class TestTimeoutIntegration:
    """Integration tests for timeout functionality."""

    def test_task_timeout_flow(self, task_queue, mock_event_bus):
        """Test complete task timeout flow."""
        # Create a task that should time out
        timed_out_task = Mock(spec=Task)
        timed_out_task.id = "timeout-test-task"
        timed_out_task.status = "running"
        timed_out_task.timeout_seconds = 1
        timed_out_task.started_at = datetime.utcnow() - timedelta(seconds=2)
        timed_out_task.phase_id = "PHASE_IMPLEMENTATION"
        timed_out_task.task_type = "implement_feature"

        with patch.object(task_queue, 'db') as mock_db:
            mock_session = Mock()
            mock_db.get_session.return_value.__enter__.return_value = mock_session

            # Test timeout detection
            mock_session.query.return_value.filter.return_value.first.return_value = timed_out_task
            assert task_queue.check_task_timeout("timeout-test-task") == True

            # Test marking as timed out
            mock_session.query.return_value.filter.return_value.first.return_value = timed_out_task
            result = task_queue.mark_task_timeout("timeout-test-task")
            assert result == True

            # Verify task state
            assert timed_out_task.status == "failed"
            assert "Task timed out" in timed_out_task.error_message

    def test_task_cancellation_flow(self, task_queue):
        """Test complete task cancellation flow."""
        # Create a running task
        running_task = Mock(spec=Task)
        running_task.id = "cancel-test-task"
        running_task.status = "running"

        with patch.object(task_queue, 'db') as mock_db:
            mock_session = Mock()
            mock_db.get_session.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = running_task

            # Cancel the task
            result = task_queue.cancel_task("cancel-test-task", "user_request")
            assert result == True

            # Verify task state
            assert running_task.status == "failed"
            assert "Task cancelled: user_request" in running_task.error_message

    def test_timeout_manager_with_no_tasks(self, timeout_manager):
        """Test timeout manager when no tasks are timed out."""
        with patch.object(timeout_manager.task_queue, 'get_timed_out_tasks') as mock_get_timed_out, \
             patch('time.sleep') as mock_sleep:

            # No timed out tasks
            mock_get_timed_out.return_value = []
            mock_sleep.side_effect = KeyboardInterrupt

            timeout_manager._running = True

            with pytest.raises(KeyboardInterrupt):
                timeout_manager._timeout_monitoring_loop()

            # Should still have called get_timed_out_tasks
            mock_get_timed_out.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])