"""Tests for resource locking service."""

import pytest
from datetime import timedelta

from omoi_os.models.resource_lock import ResourceLock
from omoi_os.services.resource_lock import ResourceLockService
from omoi_os.utils.datetime import utc_now
from tests.test_helpers import create_test_agent, create_test_task, create_test_ticket


@pytest.fixture
def lock_service(db_service):
    """Create resource lock service instance."""
    return ResourceLockService(db_service)


class TestLockAcquisition:
    """Tests for lock acquisition."""

    def test_acquire_exclusive_lock(self, lock_service, db_service):
        """Test acquiring an exclusive lock on a resource."""
        agent = create_test_agent(db_service)
        ticket = create_test_ticket(db_service)
        task = create_test_task(db_service, ticket_id=ticket.id)

        lock = lock_service.acquire_lock(
            resource_type="file",
            resource_id="/path/to/file.py",
            task_id=task.id,
            agent_id=agent.id,
            lock_mode="exclusive",
        )

        assert lock is not None
        assert lock.resource_type == "file"
        assert lock.resource_id == "/path/to/file.py"
        assert lock.locked_by_task_id == task.id
        assert lock.locked_by_agent_id == agent.id
        assert lock.lock_mode == "exclusive"
        assert lock.released_at is None

    def test_acquire_lock_conflict(self, lock_service, db_service):
        """Test lock acquisition conflict."""
        agent1 = create_test_agent(db_service)
        agent2 = create_test_agent(db_service)
        ticket = create_test_ticket(db_service)
        task1 = create_test_task(db_service, ticket_id=ticket.id)
        task2 = create_test_task(db_service, ticket_id=ticket.id)

        # Agent 1 acquires lock
        lock1 = lock_service.acquire_lock(
            resource_type="database",
            resource_id="user_table",
            task_id=task1.id,
            agent_id=agent1.id,
        )
        assert lock1 is not None

        # Agent 2 tries to acquire same resource (should fail)
        lock2 = lock_service.acquire_lock(
            resource_type="database",
            resource_id="user_table",
            task_id=task2.id,
            agent_id=agent2.id,
        )
        assert lock2 is None

    def test_acquire_shared_locks(self, lock_service, db_service):
        """Test acquiring multiple shared locks on same resource."""
        agent1 = create_test_agent(db_service)
        agent2 = create_test_agent(db_service)
        ticket = create_test_ticket(db_service)
        task1 = create_test_task(db_service, ticket_id=ticket.id)
        task2 = create_test_task(db_service, ticket_id=ticket.id)

        # Both agents acquire shared locks
        lock1 = lock_service.acquire_lock(
            resource_type="file",
            resource_id="/path/to/config.yaml",
            task_id=task1.id,
            agent_id=agent1.id,
            lock_mode="shared",
        )
        lock2 = lock_service.acquire_lock(
            resource_type="file",
            resource_id="/path/to/config.yaml",
            task_id=task2.id,
            agent_id=agent2.id,
            lock_mode="shared",
        )

        assert lock1 is not None
        assert lock2 is not None

    def test_shared_conflicts_with_exclusive(self, lock_service, db_service):
        """Test that shared lock conflicts with existing exclusive lock."""
        agent1 = create_test_agent(db_service)
        agent2 = create_test_agent(db_service)
        ticket = create_test_ticket(db_service)
        task1 = create_test_task(db_service, ticket_id=ticket.id)
        task2 = create_test_task(db_service, ticket_id=ticket.id)

        # Agent 1 acquires exclusive lock
        lock1 = lock_service.acquire_lock(
            resource_type="service",
            resource_id="payment_api",
            task_id=task1.id,
            agent_id=agent1.id,
            lock_mode="exclusive",
        )
        assert lock1 is not None

        # Agent 2 tries to acquire shared lock (should fail)
        lock2 = lock_service.acquire_lock(
            resource_type="service",
            resource_id="payment_api",
            task_id=task2.id,
            agent_id=agent2.id,
            lock_mode="shared",
        )
        assert lock2 is None


class TestLockRelease:
    """Tests for lock release."""

    def test_release_lock(self, lock_service, db_service):
        """Test releasing a lock."""
        agent = create_test_agent(db_service)
        ticket = create_test_ticket(db_service)
        task = create_test_task(db_service, ticket_id=ticket.id)

        lock = lock_service.acquire_lock(
            resource_type="file",
            resource_id="/path/to/file.py",
            task_id=task.id,
            agent_id=agent.id,
        )

        success = lock_service.release_lock(lock.id)
        assert success is True

        # Should be able to acquire same resource now
        lock2 = lock_service.acquire_lock(
            resource_type="file",
            resource_id="/path/to/file.py",
            task_id=task.id,
            agent_id=agent.id,
        )
        assert lock2 is not None

    def test_release_task_locks(self, lock_service, db_service):
        """Test releasing all locks for a task."""
        agent = create_test_agent(db_service)
        ticket = create_test_ticket(db_service)
        task = create_test_task(db_service, ticket_id=ticket.id)

        # Acquire multiple locks
        lock_service.acquire_lock(
            resource_type="file",
            resource_id="/file1.py",
            task_id=task.id,
            agent_id=agent.id,
        )
        lock_service.acquire_lock(
            resource_type="file",
            resource_id="/file2.py",
            task_id=task.id,
            agent_id=agent.id,
        )

        count = lock_service.release_task_locks(task.id)
        assert count == 2

        # Verify locks are released
        active_locks = lock_service.get_active_locks(task_id=task.id)
        assert len(active_locks) == 0

    def test_cleanup_expired_locks(self, lock_service, db_service):
        """Test cleaning up expired locks."""
        agent = create_test_agent(db_service)
        ticket = create_test_ticket(db_service)
        task = create_test_task(db_service, ticket_id=ticket.id)

        # Create lock with past expiration
        with db_service.get_session() as session:
            lock = ResourceLock(
                resource_type="file",
                resource_id="/expired.py",
                locked_by_task_id=task.id,
                locked_by_agent_id=agent.id,
                expires_at=utc_now() - timedelta(seconds=10),  # Already expired
            )
            session.add(lock)
            session.commit()

        count = lock_service.cleanup_expired_locks()
        assert count == 1


class TestLockQueries:
    """Tests for lock query methods."""

    def test_is_resource_locked(self, lock_service, db_service):
        """Test checking if resource is locked."""
        agent = create_test_agent(db_service)
        ticket = create_test_ticket(db_service)
        task = create_test_task(db_service, ticket_id=ticket.id)

        # Resource not locked initially
        is_locked = lock_service.is_resource_locked("file", "/test.py")
        assert is_locked is False

        # Acquire lock
        lock_service.acquire_lock(
            resource_type="file",
            resource_id="/test.py",
            task_id=task.id,
            agent_id=agent.id,
        )

        # Now locked
        is_locked = lock_service.is_resource_locked("file", "/test.py")
        assert is_locked is True

    def test_get_active_locks(self, lock_service, db_service):
        """Test getting active locks."""
        agent = create_test_agent(db_service)
        ticket = create_test_ticket(db_service)
        task = create_test_task(db_service, ticket_id=ticket.id)

        lock1 = lock_service.acquire_lock(
            resource_type="file",
            resource_id="/file1.py",
            task_id=task.id,
            agent_id=agent.id,
        )
        lock_service.acquire_lock(
            resource_type="file",
            resource_id="/file2.py",
            task_id=task.id,
            agent_id=agent.id,
        )

        # Get all active locks for task
        locks = lock_service.get_active_locks(task_id=task.id)
        assert len(locks) == 2

        # Get all active locks for agent
        locks = lock_service.get_active_locks(agent_id=agent.id)
        assert len(locks) == 2

        # Release one lock
        lock_service.release_lock(lock1.id)

        # Should only see one active lock now
        locks = lock_service.get_active_locks(task_id=task.id)
        assert len(locks) == 1

