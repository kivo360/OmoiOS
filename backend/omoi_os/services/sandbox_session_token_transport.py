"""Ephemeral transport for broker session tokens headed to sandboxes.

Session tokens are still minted and persisted by :class:`SandboxSessionService`.
This module only provides a short-lived Redis handoff so the sandbox spawner can
receive the same plaintext token without storing it in PostgreSQL or logging it.
"""

from __future__ import annotations

from typing import Optional, cast

import redis

from omoi_os.config import get_app_settings
from omoi_os.logging import get_logger

logger = get_logger(__name__)

TOKEN_TRANSPORT_TTL_SECONDS = 600


def _transport_key(task_id: str) -> str:
    """Return the Redis key used for a task-scoped token handoff."""
    return f"broker:session-token:{task_id}"


def _get_redis_client() -> Optional[redis.Redis]:
    """Create a Redis client for token transport, returning None if unavailable."""
    try:
        redis_url = get_app_settings().redis.url
        client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
        client.ping()
        return client
    except Exception as exc:
        logger.warning(
            "Broker session token transport unavailable",
            error_type=type(exc).__name__,
        )
        return None


def store_session_token_for_task(
    task_id: str,
    session_token: str,
    ttl_seconds: int = TOKEN_TRANSPORT_TTL_SECONDS,
) -> bool:
    """Store a plaintext session token briefly for the sandbox spawner.

    The token value is never logged. Returns False when Redis is unavailable.
    """
    client = _get_redis_client()
    if client is None:
        return False
    client.setex(_transport_key(task_id), ttl_seconds, session_token)
    return True


def pop_session_token_for_task(task_id: str) -> Optional[str]:
    """Atomically retrieve and delete the token for a task if present."""
    client = _get_redis_client()
    if client is None:
        return None

    key = _transport_key(task_id)
    try:
        value = cast(Optional[str], client.getdel(key))
    except AttributeError:
        pipe = client.pipeline()
        pipe.get(key)
        pipe.delete(key)
        value, _deleted = pipe.execute()
    return cast(Optional[str], value)
