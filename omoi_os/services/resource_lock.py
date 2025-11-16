"""Resource locking service for preventing conflicting task execution."""

import random
import time
from datetime import datetime, timedelta
from typing import Optional

from omoi_os.models.resource_lock import ResourceLock
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now


class LockAcquisitionError(Exception):
    """Raised when lock acquisition fails."""

    pass


class ResourceLockService:
    """Manages resource locks to prevent conflicting tasks from executing simultaneously."""

    def __init__(
        self,
        db: DatabaseService,
        default_lock_ttl_seconds: int = 3600,
        event_bus: Optional[EventBusService] = None,
    ):
        """
        Initialize resource lock service.

        Args:
            db: DatabaseService instance
            default_lock_ttl_seconds: Default TTL for locks in seconds (default: 1 hour)
            event_bus: Optional EventBusService for telemetry
        """
        self.db = db
        self.default_lock_ttl_seconds = default_lock_ttl_seconds
        self.event_bus = event_bus

    def acquire_lock(
        self,
        resource_key: str,
        task_id: str,
        agent_id: str,
        lock_type: str = "exclusive",
        ttl_seconds: Optional[int] = None,
        max_retries: int = 3,
        base_backoff: float = 0.1,
    ) -> ResourceLock:
        """
        Acquire a resource lock with optimistic retry/backoff.

        Args:
            resource_key: Unique identifier for the resource (e.g., "file:/path/to/file")
            task_id: ID of the task acquiring the lock
            agent_id: ID of the agent acquiring the lock
            lock_type: Type of lock ("exclusive" or "shared")
            ttl_seconds: Time-to-live for the lock in seconds (defaults to service default)
            max_retries: Maximum number of retry attempts (default: 3)
            base_backoff: Base backoff delay in seconds (default: 0.1)

        Returns:
            Acquired ResourceLock object

        Raises:
            LockAcquisitionError: If lock cannot be acquired after retries
        """
        ttl = ttl_seconds or self.default_lock_ttl_seconds
        expires_at = utc_now() + timedelta(seconds=ttl)

        wait_start_time = time.time()
        for attempt in range(max_retries + 1):
            with self.db.get_session() as session:
                # Check if lock already exists
                existing_lock = (
                    session.query(ResourceLock)
                    .filter(ResourceLock.resource_key == resource_key)
                    .first()
                )

                if existing_lock:
                    # Check if lock has expired
                    if existing_lock.expires_at and existing_lock.expires_at < utc_now():
                        # Lock expired, delete it
                        session.delete(existing_lock)
                        session.flush()
                    else:
                        # Lock is still valid, retry with backoff
                        if attempt < max_retries:
                            backoff_delay = base_backoff * (2 ** attempt) + random.uniform(0, base_backoff)
                            time.sleep(backoff_delay)
                            continue
                        else:
                            wait_time = time.time() - wait_start_time
                            # Emit telemetry
                            if self.event_bus:
                                self.event_bus.publish(
                                    SystemEvent(
                                        event_type="lock.wait_time",
                                        entity_type="lock",
                                        entity_id=resource_key,
                                        payload={
                                            "resource_key": resource_key,
                                            "task_id": task_id,
                                            "wait_time_seconds": wait_time,
                                            "attempts": attempt + 1,
                                            "failed": True,
                                        },
                                    )
                                )
                            raise LockAcquisitionError(
                                f"Failed to acquire lock on resource '{resource_key}' "
                                f"(held by task {existing_lock.task_id}, agent {existing_lock.agent_id})"
                            )

                # Try to acquire the lock
                try:
                    lock = ResourceLock(
                        resource_key=resource_key,
                        task_id=task_id,
                        agent_id=agent_id,
                        lock_type=lock_type,
                        expires_at=expires_at,
                        version=0,
                    )
                    session.add(lock)
                    session.commit()
                    session.refresh(lock)
                    session.expunge(lock)

                    # Emit telemetry for successful acquisition
                    wait_time = time.time() - wait_start_time
                    if self.event_bus:
                        self.event_bus.publish(
                            SystemEvent(
                                event_type="lock.wait_time",
                                entity_type="lock",
                                entity_id=resource_key,
                                payload={
                                    "resource_key": resource_key,
                                    "task_id": task_id,
                                    "wait_time_seconds": wait_time,
                                    "attempts": attempt + 1,
                                    "failed": False,
                                },
                            )
                        )

                    return lock
                except Exception as e:
                    session.rollback()
                    if attempt < max_retries:
                        backoff_delay = base_backoff * (2 ** attempt) + random.uniform(0, base_backoff)
                        time.sleep(backoff_delay)
                        continue
                    else:
                        raise LockAcquisitionError(f"Failed to acquire lock: {e}")

        raise LockAcquisitionError(f"Failed to acquire lock after {max_retries} retries")

    def release_lock(self, lock_id: str, agent_id: str) -> bool:
        """
        Release a resource lock.

        Args:
            lock_id: ID of the lock to release
            agent_id: ID of the agent releasing the lock (must match lock owner)

        Returns:
            True if lock was released, False if not found or not owned by agent
        """
        with self.db.get_session() as session:
            lock = session.query(ResourceLock).filter(ResourceLock.id == lock_id).first()
            if not lock:
                return False

            # Verify ownership
            if lock.agent_id != agent_id:
                return False

            session.delete(lock)
            session.commit()
            return True

    def release_lock_by_resource(self, resource_key: str, agent_id: str) -> bool:
        """
        Release a lock by resource key.

        Args:
            resource_key: Resource key of the lock to release
            agent_id: ID of the agent releasing the lock (must match lock owner)

        Returns:
            True if lock was released, False if not found or not owned by agent
        """
        with self.db.get_session() as session:
            lock = (
                session.query(ResourceLock)
                .filter(ResourceLock.resource_key == resource_key)
                .first()
            )
            if not lock:
                return False

            # Verify ownership
            if lock.agent_id != agent_id:
                return False

            session.delete(lock)
            session.commit()
            return True

    def release_locks_for_task(self, task_id: str, agent_id: str) -> int:
        """
        Release all locks held by a task.

        Args:
            task_id: ID of the task
            agent_id: ID of the agent (must match lock owner)

        Returns:
            Number of locks released
        """
        with self.db.get_session() as session:
            locks = (
                session.query(ResourceLock)
                .filter(ResourceLock.task_id == task_id, ResourceLock.agent_id == agent_id)
                .all()
            )
            count = len(locks)
            for lock in locks:
                session.delete(lock)
            session.commit()
            return count

    def is_locked(self, resource_key: str) -> bool:
        """
        Check if a resource is currently locked.

        Args:
            resource_key: Resource key to check

        Returns:
            True if resource is locked, False otherwise
        """
        with self.db.get_session() as session:
            lock = (
                session.query(ResourceLock)
                .filter(ResourceLock.resource_key == resource_key)
                .first()
            )
            if not lock:
                return False

            # Check if lock has expired
            if lock.expires_at and lock.expires_at < utc_now():
                # Lock expired, delete it
                session.delete(lock)
                session.commit()
                return False

            return True

    def get_lock_info(self, resource_key: str) -> Optional[dict]:
        """
        Get information about a lock on a resource.

        Args:
            resource_key: Resource key to check

        Returns:
            Dictionary with lock information, or None if not locked
        """
        with self.db.get_session() as session:
            lock = (
                session.query(ResourceLock)
                .filter(ResourceLock.resource_key == resource_key)
                .first()
            )
            if not lock:
                return None

            # Check if lock has expired
            if lock.expires_at and lock.expires_at < utc_now():
                session.delete(lock)
                session.commit()
                return None

            return {
                "lock_id": lock.id,
                "resource_key": lock.resource_key,
                "task_id": lock.task_id,
                "agent_id": lock.agent_id,
                "lock_type": lock.lock_type,
                "acquired_at": lock.acquired_at.isoformat() if lock.acquired_at else None,
                "expires_at": lock.expires_at.isoformat() if lock.expires_at else None,
                "version": lock.version,
            }

    def cleanup_expired_locks(self) -> int:
        """
        Clean up expired locks.

        Returns:
            Number of locks cleaned up
        """
        with self.db.get_session() as session:
            expired_locks = (
                session.query(ResourceLock)
                .filter(ResourceLock.expires_at < utc_now())
                .all()
            )
            count = len(expired_locks)
            for lock in expired_locks:
                session.delete(lock)
            session.commit()
            return count

    def extend_lock(self, lock_id: str, agent_id: str, additional_seconds: int) -> bool:
        """
        Extend the expiration time of a lock.

        Args:
            lock_id: ID of the lock to extend
            agent_id: ID of the agent (must match lock owner)
            additional_seconds: Additional seconds to add to expiration

        Returns:
            True if lock was extended, False if not found or not owned by agent
        """
        with self.db.get_session() as session:
            lock = session.query(ResourceLock).filter(ResourceLock.id == lock_id).first()
            if not lock:
                return False

            # Verify ownership
            if lock.agent_id != agent_id:
                return False

            # Extend expiration
            if lock.expires_at:
                lock.expires_at = lock.expires_at + timedelta(seconds=additional_seconds)
            else:
                lock.expires_at = utc_now() + timedelta(seconds=additional_seconds)

            lock.version += 1  # Increment version for optimistic locking
            session.commit()
            return True
