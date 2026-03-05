"""Redis-based token blacklist for JWT invalidation.

Used for:
- Logout (blacklist access + refresh tokens)
- Refresh token rotation (blacklist old refresh token)
- Single-use tokens (blacklist verification/reset tokens after use)
- Account lockout (track failed login attempts)
- Auth audit logging
"""

from __future__ import annotations

from typing import Optional

import redis.asyncio as aioredis

from omoi_os.logging import get_logger

logger = get_logger(__name__)


_BLACKLIST_PREFIX = "auth:blacklist:"
_LOCKOUT_PREFIX = "auth:lockout:"
_AUDIT_PREFIX = "auth:audit:"


class TokenBlacklistService:
    """Redis-backed token blacklist and auth security service.

    All operations are async and use automatic TTL expiry.
    """

    def __init__(self, redis_url: str) -> None:
        self._redis: aioredis.Redis = aioredis.from_url(
            redis_url, decode_responses=True
        )

    async def close(self) -> None:
        """Close the Redis connection."""
        await self._redis.aclose()

    async def blacklist_token(self, jti: str, ttl_seconds: int) -> None:
        """Add a token JTI to the blacklist with automatic expiry.

        Args:
            jti: JWT ID to blacklist
            ttl_seconds: Seconds until this entry auto-expires (should match token lifetime)
        """
        key = f"{_BLACKLIST_PREFIX}{jti}"
        await self._redis.setex(key, ttl_seconds, "1")
        logger.debug("Blacklisted token jti=%s ttl=%ds", jti, ttl_seconds)

    async def is_blacklisted(self, jti: str) -> bool:
        """Check if a token JTI is blacklisted."""
        key = f"{_BLACKLIST_PREFIX}{jti}"
        return await self._redis.exists(key) > 0

    async def blacklist_all_user_tokens(
        self, user_id: str, ttl_seconds: int = 86400
    ) -> None:
        """Mark a user-level blacklist flag (e.g., after password change).

        This is checked in addition to per-token blacklisting.
        Tokens issued before this timestamp are considered invalid.

        Args:
            user_id: User UUID as string
            ttl_seconds: How long to maintain the flag (default 24h — covers max token lifetime)
        """
        from omoi_os.utils.datetime import utc_now

        key = f"{_BLACKLIST_PREFIX}user:{user_id}"
        await self._redis.setex(key, ttl_seconds, str(utc_now().timestamp()))
        logger.info("Blacklisted all tokens for user=%s", user_id)

    async def is_user_blacklisted_since(self, user_id: str, token_iat: float) -> bool:
        """Check if user's tokens issued before a certain time are blacklisted.

        Args:
            user_id: User UUID as string
            token_iat: Token's 'iat' (issued-at) timestamp
        """
        key = f"{_BLACKLIST_PREFIX}user:{user_id}"
        blacklisted_since = await self._redis.get(key)
        if blacklisted_since is None:
            return False
        return token_iat < float(blacklisted_since)

    async def record_failed_login(self, email: str, window_seconds: int = 900) -> int:
        """Record a failed login attempt and return the current count.

        Args:
            email: Email address (lowercased)
            window_seconds: Lockout window in seconds (default 15 min)

        Returns:
            Number of failed attempts in the current window
        """
        key = f"{_LOCKOUT_PREFIX}{email.lower()}"
        pipe = self._redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        results = await pipe.execute()
        count = results[0]
        logger.debug("Failed login attempt for %s: count=%d", email, count)
        return count

    async def get_failed_login_count(self, email: str) -> int:
        """Get current failed login attempt count."""
        key = f"{_LOCKOUT_PREFIX}{email.lower()}"
        count = await self._redis.get(key)
        return int(count) if count else 0

    async def clear_failed_logins(self, email: str) -> None:
        """Clear failed login counter (called on successful login)."""
        key = f"{_LOCKOUT_PREFIX}{email.lower()}"
        await self._redis.delete(key)

    async def is_locked_out(self, email: str, max_attempts: int = 5) -> bool:
        """Check if an account is locked out due to too many failed attempts."""
        count = await self.get_failed_login_count(email)
        return count >= max_attempts

    async def log_auth_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[str] = None,
    ) -> None:
        """Log an authentication event for audit purposes.

        Events are stored in a Redis list with automatic trimming.
        For production, these should also be forwarded to a persistent store.

        Args:
            event_type: One of: login_success, login_failed, logout, password_change,
                       password_reset, account_locked, token_refresh, email_verified
            user_id: User UUID (if known)
            email: Email address (if known)
            ip_address: Client IP
            details: Additional context
        """
        import json
        from omoi_os.utils.datetime import utc_now

        entry = {
            "event": event_type,
            "timestamp": utc_now().isoformat(),
            "user_id": user_id,
            "email": email,
            "ip": ip_address,
            "details": details,
        }

        key = f"{_AUDIT_PREFIX}log"
        await self._redis.lpush(key, json.dumps(entry))
        await self._redis.ltrim(key, 0, 9999)  # cap at 10k entries

        logger.info(
            "AUTH_AUDIT: %s user=%s email=%s ip=%s details=%s",
            event_type,
            user_id,
            email,
            ip_address,
            details,
        )


_instance: Optional[TokenBlacklistService] = None


def init_token_blacklist(redis_url: str) -> TokenBlacklistService:
    """Initialize the global token blacklist service."""
    global _instance
    _instance = TokenBlacklistService(redis_url)
    return _instance


def get_token_blacklist() -> TokenBlacklistService:
    """Get the global token blacklist service.

    Raises:
        RuntimeError: If the service has not been initialized.
    """
    if _instance is None:
        raise RuntimeError(
            "TokenBlacklistService not initialized. "
            "Call init_token_blacklist() during app startup."
        )
    return _instance
