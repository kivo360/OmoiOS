"""Idempotency-Key middleware for session-create retries.

Spec §03 requires `POST /sessions` to dedup retries via an `Idempotency-Key`
header. This middleware stores the response (status + body) keyed by
`{org_id}:{route}:{key}` in Redis for 24 hours. Semantics match Stripe:

- Same key + same body hash → return the stored response verbatim (same id).
- Same key + different body hash → 409 conflict with a stable error envelope.
- No key → no-op; request proceeds as normal.

This middleware activates only for `POST /api/v1/sessions` so far. The scope
is narrow on purpose — sessions are the spec's primary create-expensive
resource. Other POSTs can opt in later by extending `_PROTECTED_ROUTES`.

Keys are namespaced by the caller's org to prevent cross-tenant key collisions.
Legacy JWT callers (no org on token) share a fallback namespace keyed by
the resolved user_id.
"""

from __future__ import annotations

import hashlib
import json
from typing import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from omoi_os.logging import get_logger


logger = get_logger(__name__)

_PROTECTED_ROUTES: set[tuple[str, str]] = {
    ("POST", "/api/v1/sessions"),
    ("POST", "/api/v1/sessions/"),
}

_IDEMPOTENCY_TTL_SECONDS = 24 * 3600  # 24h window, matches Stripe defaults.


def _fingerprint_body(body: bytes) -> str:
    """Stable sha256 of the raw request body."""
    return hashlib.sha256(body or b"").hexdigest()


def _scope_key(request: Request, idem_key: str) -> str:
    """Build the Redis key under which this request's response is cached.

    Prefers organization_id from the auth context if available; falls back
    to the raw token hash so we never leak results across tokens.
    """
    # Org from AuthContext if the route-level auth already ran. Middleware
    # runs before routing, so we use header fallback.
    org = request.headers.get("X-Organization-Id", "")
    if not org:
        auth = request.headers.get("Authorization", "")
        # Use last 12 chars of the token (never the full secret) as an isolation
        # bucket. Still scoped per key value.
        org = f"auth-{hashlib.sha256(auth.encode()).hexdigest()[:12]}"
    route = request.url.path
    return f"idem:{org}:{route}:{idem_key}"


async def _get_redis():
    """Resolve the shared Redis client via EventBusService.

    Returns the client or None if Redis is unavailable (fail-open for the
    middleware — route continues normally).
    """
    try:
        from omoi_os.api.dependencies import get_event_bus_service

        bus = get_event_bus_service()
        if not getattr(bus, "_available", False):
            return None
        return bus.redis_client
    except Exception:  # noqa: BLE001
        return None


def _conflict_response(request_id: str, route: str) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "conflict",
                "type": "idempotency_conflict",
                "message": (
                    "Idempotency-Key reused with a different request body. "
                    "Use a new key for a new request."
                ),
                "request_id": request_id,
                "docs_url": "https://docs.omoios.dev/api/idempotency",
            }
        },
    )


async def idempotency_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """ASGI middleware that applies Stripe-style idempotency to POST /sessions."""
    method_path = (request.method, request.url.path)
    idem_key = request.headers.get("Idempotency-Key", "").strip()

    if method_path not in _PROTECTED_ROUTES or not idem_key:
        return await call_next(request)

    # Slurp the body — Starlette consumes it once, so we must replay it back
    # into the request object so downstream handlers still see it.
    body = await request.body()
    fp = _fingerprint_body(body)

    redis_client = await _get_redis()
    if redis_client is None:
        # Fail-open: no dedup, but don't fail the request. Log once so the
        # operator sees it in production.
        logger.warning("idempotency middleware: Redis unavailable, skipping dedup")
        return await call_next(request)

    cache_key = _scope_key(request, idem_key)
    try:
        raw = redis_client.get(cache_key)
    except Exception as e:  # noqa: BLE001
        logger.warning("idempotency lookup failed", key=cache_key, error=str(e))
        return await call_next(request)

    if raw:
        try:
            cached = json.loads(raw)
        except (ValueError, TypeError):
            cached = None

        if cached and cached.get("fp") == fp:
            # Replay the stored response verbatim.
            return JSONResponse(
                status_code=cached.get("status", 200),
                content=cached.get("body"),
                headers={
                    "Idempotent-Replay": "true",
                    **(cached.get("headers") or {}),
                },
            )
        if cached:
            return _conflict_response(
                request_id=request.headers.get("X-Request-ID", ""),
                route=request.url.path,
            )

    # Make the body available again — Starlette's `await request.body()` caches
    # the bytes on the request, so re-awaiting returns the same payload.
    async def replay_receive():
        return {"type": "http.request", "body": body, "more_body": False}

    request._receive = replay_receive  # type: ignore[attr-defined]

    response = await call_next(request)

    # Only cache successful creations (2xx). Errors should be re-tryable.
    if 200 <= response.status_code < 300:
        # Response body is a streaming iterator — drain it, cache, and rebuild.
        chunks = [chunk async for chunk in response.body_iterator]
        raw_body = b"".join(chunks)

        try:
            parsed_body = json.loads(raw_body) if raw_body else None
        except (ValueError, TypeError):
            parsed_body = None

        # Headers we want to echo on replay. Skip anything that changes per
        # request (dates, request IDs) to avoid drift surprising the caller.
        echo_headers = {
            k: v
            for k, v in response.headers.items()
            if k.lower() not in {"date", "x-request-id", "content-length"}
        }

        try:
            redis_client.setex(
                cache_key,
                _IDEMPOTENCY_TTL_SECONDS,
                json.dumps(
                    {
                        "fp": fp,
                        "status": response.status_code,
                        "body": parsed_body,
                        "headers": echo_headers,
                    }
                ),
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("idempotency write failed", key=cache_key, error=str(e))

        # Rebuild the response with the buffered body so the original client
        # still gets it.
        return Response(
            content=raw_body,
            status_code=response.status_code,
            headers=echo_headers,
            media_type=response.media_type,
        )

    return response
