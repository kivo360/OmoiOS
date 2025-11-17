"""Resource locking service for preventing conflicting task execution."""

from __future__ import annotations

from datetime import timedelta
from typing import List, Optional


from omoi_os.models.resource_lock import ResourceLock
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now


class ResourceLockService:
    """Service for managing resource locks to prevent conflicts."""

    def __init__(self, db: DatabaseService):
        """
        Initialize resource lock service.

        Args:
            db: Database service
        """
        self.db = db

    def acquire_lock(
        self,
        resource_type: str,
        resource_id: str,
        task_id: str,
        agent_id: str,
        lock_mode: str = "exclusive",
        timeout_seconds: Optional[int] = None,
    ) -> Optional[ResourceLock]:
        """
        Attempt to acquire a resource lock.

        Args:
            resource_type: Type of resource (file, database, service)
            resource_id: Resource identifier
            task_id: Task requesting the lock
            agent_id: Agent requesting the lock
            lock_mode: Lock mode (exclusive, shared)
            timeout_seconds: Optional lock expiration timeout

        Returns:
            ResourceLock if acquired, None if resource already locked
        """
        with self.db.get_session() as session:
            # Check for existing locks on this resource
            existing_locks = (
                session.query(ResourceLock)
                .filter(
                    ResourceLock.resource_type == resource_type,
                    ResourceLock.resource_id == resource_id,
                    ResourceLock.released_at.is_(None),  # Not yet released
                )
                .all()
            )

            # Check for conflicts
            if lock_mode == "exclusive":
                # Exclusive lock conflicts with any existing lock
                if existing_locks:
                    return None
            elif lock_mode == "shared":
                # Shared lock conflicts with exclusive locks
                for lock in existing_locks:
                    if lock.lock_mode == "exclusive":
                        return None

            # Create lock
            expires_at = None
            if timeout_seconds:
                expires_at = utc_now() + timedelta(seconds=timeout_seconds)

            lock = ResourceLock(
                resource_type=resource_type,
                resource_id=resource_id,
                locked_by_task_id=task_id,
                locked_by_agent_id=agent_id,
                lock_mode=lock_mode,
                expires_at=expires_at,
            )
            session.add(lock)
            session.commit()
            session.refresh(lock)
            session.expunge(lock)

            return lock

    def release_lock(self, lock_id: str) -> bool:
        """
        Release a resource lock.

        Args:
            lock_id: Lock ID to release

        Returns:
            True if released successfully
        """
        with self.db.get_session() as session:
            lock = session.query(ResourceLock).filter(
                ResourceLock.id == lock_id
            ).first()
            if not lock:
                return False

            lock.released_at = utc_now()
            session.commit()
            return True

    def release_task_locks(self, task_id: str) -> int:
        """
        Release all locks held by a task.

        Args:
            task_id: Task ID

        Returns:
            Number of locks released
        """
        with self.db.get_session() as session:
            locks = (
                session.query(ResourceLock)
                .filter(
                    ResourceLock.locked_by_task_id == task_id,
                    ResourceLock.released_at.is_(None),
                )
                .all()
            )

            count = 0
            for lock in locks:
                lock.released_at = utc_now()
                count += 1

            session.commit()
            return count

    def release_agent_locks(self, agent_id: str) -> int:
        """
        Release all locks held by an agent.

        Args:
            agent_id: Agent ID

        Returns:
            Number of locks released
        """
        with self.db.get_session() as session:
            locks = (
                session.query(ResourceLock)
                .filter(
                    ResourceLock.locked_by_agent_id == agent_id,
                    ResourceLock.released_at.is_(None),
                )
                .all()
            )

            count = 0
            for lock in locks:
                lock.released_at = utc_now()
                count += 1

            session.commit()
            return count

    def cleanup_expired_locks(self) -> int:
        """
        Release locks that have exceeded their expiration time.

        Returns:
            Number of locks cleaned up
        """
        now = utc_now()

        with self.db.get_session() as session:
            expired_locks = (
                session.query(ResourceLock)
                .filter(
                    ResourceLock.expires_at.isnot(None),
                    ResourceLock.expires_at < now,
                    ResourceLock.released_at.is_(None),
                )
                .all()
            )

            count = 0
            for lock in expired_locks:
                lock.released_at = now
                count += 1

            session.commit()
            return count

    def is_resource_locked(
        self,
        resource_type: str,
        resource_id: str,
        lock_mode: str = "exclusive",
    ) -> bool:
        """
        Check if a resource is currently locked.

        Args:
            resource_type: Resource type
            resource_id: Resource identifier
            lock_mode: Requested lock mode

        Returns:
            True if resource is locked in a conflicting way
        """
        with self.db.get_session() as session:
            existing_locks = (
                session.query(ResourceLock)
                .filter(
                    ResourceLock.resource_type == resource_type,
                    ResourceLock.resource_id == resource_id,
                    ResourceLock.released_at.is_(None),
                )
                .all()
            )

            if not existing_locks:
                return False

            # Exclusive mode conflicts with any lock
            if lock_mode == "exclusive":
                return True

            # Shared mode only conflicts with exclusive locks
            return any(lock.lock_mode == "exclusive" for lock in existing_locks)

    def get_active_locks(
        self,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> List[ResourceLock]:
        """
        Get active locks with optional filters.

        Args:
            task_id: Filter by task
            agent_id: Filter by agent

        Returns:
            List of active ResourceLock objects
        """
        with self.db.get_session() as session:
            query = session.query(ResourceLock).filter(
                ResourceLock.released_at.is_(None)
            )

            if task_id:
                query = query.filter(ResourceLock.locked_by_task_id == task_id)
            if agent_id:
                query = query.filter(ResourceLock.locked_by_agent_id == agent_id)

            locks = query.all()

            for lock in locks:
                session.expunge(lock)

            return locks

