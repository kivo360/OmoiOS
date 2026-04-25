"""Unit tests for runtime credential broker routes.

Tests Requirements:
- Runtime broker accepts only sandbox session bearer tokens.
- Runtime credential lookup maps unknown aliases to 404 and logs safe metadata.
- Runtime revoke accepts admin users only.
- Session creation returns a one-time session token only when aliases exist.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi import HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials

from omoi_os.api.routes import broker_runtime, sessions
from omoi_os.models.sandbox_session import SandboxSession
from omoi_os.models.user import User
from omoi_os.services.credential_broker import UnknownAliasError
from omoi_os.utils.datetime import utc_now


pytestmark = pytest.mark.unit


class FakeSessionService:
    """Small sandbox-session service double for route tests."""

    def __init__(self, sandbox_session: SandboxSession | None) -> None:
        self.sandbox_session = sandbox_session
        self.revoked_session_id = None
        self.db = SimpleNamespace(get=self.get_session)

    async def verify_session_token(self, token: str) -> SandboxSession | None:
        return self.sandbox_session if token == "sess_tok_valid" else None

    async def get_session(self, _model, session_id):
        if self.sandbox_session and self.sandbox_session.id == session_id:
            return self.sandbox_session
        return None

    async def revoke(self, session_id) -> None:
        self.revoked_session_id = session_id


class FakeCredentialBroker:
    """Credential broker double that returns a fixed payload or raises."""

    def __init__(self, credential_payload: dict | None = None, error=None) -> None:
        self.credential_payload = credential_payload or {
            "kind": "bearer_secret",
            "value": "secret-value",
        }
        self.error = error
        self.alias = None

    async def resolve_alias(self, sandbox_session: SandboxSession, alias: str) -> dict:
        self.alias = alias
        if self.error:
            raise self.error
        return self.credential_payload


class FakeRedis:
    """Redis double implementing the incr/expire API used by rate limiting."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.expired_keys: list[str] = []

    def incr(self, key: str) -> int:
        next_count = self.counts.get(key, 0) + 1
        self.counts[key] = next_count
        return next_count

    def expire(self, key: str, _seconds: int) -> None:
        self.expired_keys.append(key)


@pytest.fixture
def sandbox_session() -> SandboxSession:
    """Create a detached sandbox session for route-level tests."""
    return SandboxSession(
        id=uuid4(),
        session_token_hash="a" * 64,
        session_token_prefix="sess_tok",
        workspace_id=uuid4(),
        environment_version_id=uuid4(),
        expires_at=utc_now(),
    )


@pytest.fixture
def admin_user_object(mock_user: User) -> User:
    """Return a non-persisted admin user for authz branch tests."""
    mock_user.is_super_admin = True
    return mock_user


def bearer(token: str) -> HTTPAuthorizationCredentials:
    """Build a bearer credential object for dependency tests."""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_extract_session_token_rejects_missing_credentials() -> None:
    """Missing Authorization header returns 401."""
    with pytest.raises(HTTPException) as exc_info:
        broker_runtime._extract_session_token(None)
    assert exc_info.value.status_code == 401


def test_extract_session_token_rejects_non_session_bearer() -> None:
    """JWT/API-key shaped bearers cannot access runtime credentials."""
    with pytest.raises(HTTPException) as exc_info:
        broker_runtime._extract_session_token(bearer("eyJhbGciOiJIUzI1NiJ9"))
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_sandbox_session_accepts_valid_session_bearer(
    sandbox_session: SandboxSession,
) -> None:
    """Valid sess_tok bearer resolves to its sandbox session."""
    resolved_session = await broker_runtime.get_sandbox_session(
        credentials=bearer("sess_tok_valid"),
        session_service=cast(Any, FakeSessionService(sandbox_session)),
    )
    assert resolved_session is sandbox_session


@pytest.mark.asyncio
async def test_get_sandbox_session_rejects_invalid_session_bearer() -> None:
    """Unknown, expired, or revoked session tokens return 401."""
    with pytest.raises(HTTPException) as exc_info:
        await broker_runtime.get_sandbox_session(
            credentials=bearer("sess_tok_invalid"),
            session_service=cast(Any, FakeSessionService(None)),
        )
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_rate_limit_blocks_sixty_first_request(
    sandbox_session: SandboxSession,
) -> None:
    """Redis-backed rate limiting allows 60 requests per minute per session."""
    redis_client = FakeRedis()
    for _ in range(60):
        allowed_session = await broker_runtime.get_rate_limited_sandbox_session(
            sandbox_session=sandbox_session,
            redis_client=cast(Any, redis_client),
        )
        assert allowed_session is sandbox_session

    with pytest.raises(HTTPException) as exc_info:
        await broker_runtime.get_rate_limited_sandbox_session(
            sandbox_session=sandbox_session,
            redis_client=cast(Any, redis_client),
        )
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_get_credential_for_alias_returns_resolved_payload(
    sandbox_session: SandboxSession,
) -> None:
    """Credential route returns the per-kind broker payload."""
    credential_broker = FakeCredentialBroker()
    credential_payload = await broker_runtime.get_credential_for_alias(
        alias="github",
        sandbox_session=sandbox_session,
        credential_broker=cast(Any, credential_broker),
    )
    assert credential_payload == {"kind": "bearer_secret", "value": "secret-value"}
    assert credential_broker.alias == "github"


@pytest.mark.asyncio
async def test_get_credential_for_alias_maps_unknown_alias_to_404(
    sandbox_session: SandboxSession,
) -> None:
    """UnknownAliasError becomes a 404 response."""
    credential_broker = FakeCredentialBroker(error=UnknownAliasError("missing"))
    with pytest.raises(HTTPException) as exc_info:
        await broker_runtime.get_credential_for_alias(
            alias="missing",
            sandbox_session=sandbox_session,
            credential_broker=cast(Any, credential_broker),
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_revoke_sandbox_session_requires_admin(
    sandbox_session: SandboxSession,
    mock_user: User,
) -> None:
    """Non-admin JWT callers cannot revoke runtime sessions."""
    with pytest.raises(HTTPException) as exc_info:
        await broker_runtime.revoke_sandbox_session(
            session_id=sandbox_session.id,
            current_user=mock_user,
            session_service=cast(Any, FakeSessionService(sandbox_session)),
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_revoke_sandbox_session_returns_404_for_unknown_session(
    admin_user_object: User,
) -> None:
    """Admin revoke returns 404 when the sandbox session does not exist."""
    with pytest.raises(HTTPException) as exc_info:
        await broker_runtime.revoke_sandbox_session(
            session_id=uuid4(),
            current_user=admin_user_object,
            session_service=cast(Any, FakeSessionService(None)),
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_revoke_sandbox_session_succeeds_for_admin(
    sandbox_session: SandboxSession,
    admin_user_object: User,
) -> None:
    """Admin JWT callers can revoke known sandbox sessions."""
    session_service = FakeSessionService(sandbox_session)
    await broker_runtime.revoke_sandbox_session(
        session_id=sandbox_session.id,
        current_user=admin_user_object,
        session_service=cast(Any, session_service),
    )
    assert session_service.revoked_session_id == sandbox_session.id


def test_require_broker_enabled_returns_404_when_disabled(monkeypatch) -> None:
    """Feature flag guard hides the runtime broker surface."""
    monkeypatch.setattr(broker_runtime, "is_feature_enabled", lambda _flag: False)
    with pytest.raises(HTTPException) as exc_info:
        broker_runtime.require_broker_enabled()
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_session_returns_session_token_once(
    monkeypatch, mock_user: User
) -> None:
    """POST /api/v1/sessions includes session_token only when credentials exist."""

    async def fake_create_task(**_kwargs):
        return {
            "id": "task-1",
            "ticket_id": "ticket-1",
            "phase_id": "PHASE_IMPLEMENTATION",
            "task_type": "implementation",
            "title": "Build feature",
            "description": "Implement feature",
            "priority": "MEDIUM",
            "status": "pending",
            "dependencies": None,
            "execution_config": None,
            "created_at": "2026-04-24T00:00:00+00:00",
        }

    async def fake_mint_token(**_kwargs):
        return "sess_tok_once"

    monkeypatch.setattr(sessions, "is_feature_enabled", lambda _flag: True)
    monkeypatch.setattr(sessions.tasks_router, "create_task", fake_create_task)
    monkeypatch.setattr(
        sessions, "_mint_session_token_for_credentials", fake_mint_token
    )

    response_payload = await sessions.create_session(
        request=cast(Any, None),
        response=Response(),
        session_data=sessions.SessionCreate(
            ticket_id="ticket-1",
            title="Build feature",
            description="Implement feature",
        ),
        current_user=mock_user,
        db=cast(Any, SimpleNamespace()),
        queue=cast(Any, SimpleNamespace()),
    )

    assert response_payload["session_id"] == "task-1"
    assert response_payload["session_token"] == "sess_tok_once"


@pytest.mark.asyncio
async def test_create_session_omits_session_token_without_credentials(
    monkeypatch,
    mock_user: User,
) -> None:
    """POST /api/v1/sessions does not expose a token when no aliases exist."""

    async def fake_create_task(**_kwargs):
        return {"id": "task-2", "created_at": "2026-04-24T00:00:00+00:00"}

    async def fake_mint_token(**_kwargs):
        return None

    monkeypatch.setattr(sessions, "is_feature_enabled", lambda _flag: True)
    monkeypatch.setattr(sessions.tasks_router, "create_task", fake_create_task)
    monkeypatch.setattr(
        sessions, "_mint_session_token_for_credentials", fake_mint_token
    )

    response_payload = await sessions.create_session(
        request=cast(Any, None),
        response=Response(),
        session_data=sessions.SessionCreate(
            ticket_id="ticket-2",
            title="Build feature",
            description="Implement feature",
        ),
        current_user=mock_user,
        db=cast(Any, SimpleNamespace()),
        queue=cast(Any, SimpleNamespace()),
    )

    assert response_payload["session_id"] == "task-2"
    assert "session_token" not in response_payload
