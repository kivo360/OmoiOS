"""
Redis-based message queue for sandbox message injection.

Phase 2 Fix: Replaces in-memory implementation with Redis for:
- Persistence across server restarts
- Shared state across multiple server instances
- Production-ready message queue

Follows EventBusService patterns from event_bus.py.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional, TypeAlias

import redis


class RedisMessageQueue:
    """
    Thread-safe Redis-based message queue.

    Uses Redis Lists for FIFO queue semantics:
    - LPUSH to add messages (left side)
    - LRANGE + DEL to atomically get and clear messages

    Key pattern: sandbox:messages:{sandbox_id}
    """

    def __init__(self, redis_url: str = "redis://localhost:16379"):
        """
        Initialize Redis message queue.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self._key_prefix = "sandbox:messages:"

    def _get_key(self, sandbox_id: str) -> str:
        """Get Redis key for sandbox message queue."""
        return f"{self._key_prefix}{sandbox_id}"

    def enqueue(
        self,
        sandbox_id: str,
        content: str,
        message_type: str,
    ) -> str:
        """
        Add message to queue. Returns message_id.

        Args:
            sandbox_id: Target sandbox identifier
            content: Message content
            message_type: Type of message

        Returns:
            Generated message ID
        """
        message_id = f"msg-{uuid.uuid4().hex[:12]}"

        message = {
            "id": message_id,
            "content": content,
            "message_type": message_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        key = self._get_key(sandbox_id)
        # RPUSH to maintain FIFO order (oldest at left, newest at right)
        self.redis_client.rpush(key, json.dumps(message))

        return message_id

    def get_all(self, sandbox_id: str) -> list[dict]:
        """
        Get and clear all messages for sandbox.

        Uses Redis transaction to atomically get and delete.

        Args:
            sandbox_id: Sandbox identifier

        Returns:
            List of message dictionaries (FIFO order)
        """
        key = self._get_key(sandbox_id)

        # Use pipeline for atomic get + delete
        pipe = self.redis_client.pipeline()
        pipe.lrange(key, 0, -1)  # Get all messages
        pipe.delete(key)  # Clear queue
        results = pipe.execute()

        # First result is the list of messages
        raw_messages = results[0] if results else []

        return [json.loads(m) for m in raw_messages]

    def peek(self, sandbox_id: str, count: int = 10) -> list[dict]:
        """
        Peek at messages without removing them.

        Args:
            sandbox_id: Sandbox identifier
            count: Maximum number of messages to return

        Returns:
            List of message dictionaries (FIFO order)
        """
        key = self._get_key(sandbox_id)
        raw_messages = self.redis_client.lrange(key, 0, count - 1)
        return [json.loads(m) for m in raw_messages]

    def count(self, sandbox_id: str) -> int:
        """
        Get count of pending messages.

        Args:
            sandbox_id: Sandbox identifier

        Returns:
            Number of pending messages
        """
        key = self._get_key(sandbox_id)
        return self.redis_client.llen(key)

    def close(self) -> None:
        """Close Redis connection."""
        self.redis_client.close()


class InMemoryMessageQueue:
    """
    Thread-safe in-memory message queue for testing.

    Same interface as RedisMessageQueue but stores in memory.
    Useful for unit tests that don't have Redis available.
    """

    def __init__(self):
        from collections import defaultdict
        from threading import Lock

        self._queues: dict[str, list[dict]] = defaultdict(list)
        self._lock = Lock()

    def enqueue(
        self,
        sandbox_id: str,
        content: str,
        message_type: str,
    ) -> str:
        """Add message to queue. Returns message_id."""
        message_id = f"msg-{uuid.uuid4().hex[:12]}"

        with self._lock:
            self._queues[sandbox_id].append(
                {
                    "id": message_id,
                    "content": content,
                    "message_type": message_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        return message_id

    def get_all(self, sandbox_id: str) -> list[dict]:
        """Get and clear all messages for sandbox."""
        with self._lock:
            messages = self._queues.pop(sandbox_id, [])
        return messages

    def peek(self, sandbox_id: str, count: int = 10) -> list[dict]:
        """Peek at messages without removing them."""
        with self._lock:
            return self._queues.get(sandbox_id, [])[:count]

    def count(self, sandbox_id: str) -> int:
        """Get count of pending messages."""
        with self._lock:
            return len(self._queues.get(sandbox_id, []))


# Type alias for either implementation
MessageQueue: TypeAlias = RedisMessageQueue | InMemoryMessageQueue


def get_message_queue(redis_url: Optional[str] = None) -> MessageQueue:
    """
    Factory function to get appropriate message queue.

    Args:
        redis_url: Redis URL. If None, uses settings. If "memory", uses in-memory.

    Returns:
        MessageQueue instance
    """
    if redis_url == "memory":
        return InMemoryMessageQueue()

    if redis_url is None:
        from omoi_os.config import get_app_settings

        settings = get_app_settings()
        redis_url = settings.redis.url

    return RedisMessageQueue(redis_url=redis_url)
