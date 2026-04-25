"""Runtime credential broker routes for sandbox sessions.

This surface is intentionally separate from the admin credential CRUD API. It
only accepts sandbox session bearer tokens for credential resolution, and only
accepts admin user JWTs for session revocation.
"""

from __future__ import annotations

import time
from typing import Optional, cast
from uuid import UUID

import redis
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from omoi_os.api.dependencies import get_current_user, get_db_session, get_event_bus
from omoi_os.config import is_feature_enabled
from omoi_os.logging import get_logger
from omoi_os.models.sandbox_session import SandboxSession
from omoi_os.models.user import User
from omoi_os.services.credential_broker import (
    CredentialBrokerError,
    CredentialBrokerService,
    UnknownAliasError,
    get_credential_broker_service,
)
from omoi_os.services.sandbox_session_service import SandboxSessionService

logger = get_logger(__name__)
router = APIRouter()
session_bearer = HTTPBearer(auto_error=False)

REQUESTS_PER_SESSION_PER_MINUTE = 60


def require_broker_enabled() -> None:
    """Hide runtime broker routes when the broker feature is disabled."""
    if not is_feature_enabled("broker_enabled"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not Found",
        )


def get_session_service(
    db_session: AsyncSession = Depends(get_db_session),
) -> SandboxSessionService:
    """Return the sandbox session service for request-scoped DB access."""
    return SandboxSessionService(db_session)


def get_runtime_credential_broker() -> CredentialBrokerService:
    """Return the credential broker service used by runtime routes."""
    return get_credential_broker_service()


def get_rate_limit_redis(event_bus=Depends(get_event_bus)) -> Optional[redis.Redis]:
    """Return the Redis client used for broker rate limiting, if available."""
    return getattr(event_bus, "redis_client", None)


def _unauthorized() -> HTTPException:
    """Build a consistent session bearer authentication failure."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired session token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _extract_session_token(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> str:
    """Extract and validate the runtime sandbox bearer token shape."""
    if not credentials or not credentials.credentials:
        raise _unauthorized()
    if credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    token = credentials.credentials
    if not token.startswith("sess_tok_"):
        raise _unauthorized()
    return token


async def get_sandbox_session(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(session_bearer),
    session_service: SandboxSessionService = Depends(get_session_service),
) -> SandboxSession:
    """Verify a runtime session bearer and return its sandbox session."""
    token = _extract_session_token(credentials)
    sandbox_session = await session_service.verify_session_token(token)
    if sandbox_session is None:
        raise _unauthorized()
    return sandbox_session


def _rate_limit_key(sandbox_session: SandboxSession) -> str:
    """Return the Redis key for the current session/minute window."""
    minute_window = int(time.time() // 60)
    return f"broker:rl:{sandbox_session.id}:{minute_window}"


async def get_rate_limited_sandbox_session(
    sandbox_session: SandboxSession = Depends(get_sandbox_session),
    redis_client: Optional[redis.Redis] = Depends(get_rate_limit_redis),
) -> SandboxSession:
    """Enforce 60 credential reads per minute per sandbox session."""
    if redis_client is None:
        logger.warning(
            "Broker rate limit skipped because Redis is unavailable",
            sandbox_session_id=str(sandbox_session.id),
        )
        return sandbox_session

    key = _rate_limit_key(sandbox_session)
    request_count = int(cast(int, redis_client.incr(key)))
    if request_count == 1:
        redis_client.expire(key, 70)
    if request_count > REQUESTS_PER_SESSION_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )
    return sandbox_session


@router.get(
    "/creds/{alias}",
    dependencies=[Depends(require_broker_enabled)],
)
async def get_credential_for_alias(
    alias: str,
    sandbox_session: SandboxSession = Depends(get_rate_limited_sandbox_session),
    credential_broker: CredentialBrokerService = Depends(get_runtime_credential_broker),
) -> dict:
    """Return a per-kind credential payload for a sandbox session alias."""
    try:
        credential_payload = await credential_broker.resolve_alias(
            sandbox_session, alias
        )
    except UnknownAliasError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except CredentialBrokerError as exc:
        logger.error(
            "Runtime credential resolution failed",
            session_token_prefix=sandbox_session.session_token_prefix,
            alias=alias,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Credential resolution failed",
        ) from exc

    logger.info(
        "Runtime credential resolved",
        session_token_prefix=sandbox_session.session_token_prefix,
        alias=alias,
    )
    return credential_payload


@router.post(
    "/sessions/{session_id}/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_broker_enabled)],
)
async def revoke_sandbox_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session_service: SandboxSessionService = Depends(get_session_service),
) -> None:
    """Revoke a sandbox session. Only admin user JWTs may call this route."""
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    sandbox_session = await session_service.db.get(SandboxSession, session_id)
    if sandbox_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    await session_service.revoke(session_id)
    return None
