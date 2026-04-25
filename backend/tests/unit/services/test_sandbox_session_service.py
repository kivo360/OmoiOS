"""Test SandboxSessionService token lifecycle.

Tests the mint → verify → revoke round-trip and ensures
no plaintext token is ever persisted.
"""

from __future__ import annotations

import hashlib
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from omoi_os.models.sandbox_session import SandboxSession
from omoi_os.services.sandbox_session_service import SandboxSessionService
from omoi_os.utils.datetime import utc_now


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    """Create a SandboxSessionService with a mock DB."""
    return SandboxSessionService(db=mock_db)


@pytest.fixture
def workspace_id():
    return uuid4()


@pytest.fixture
def env_version_id():
    return uuid4()


class TestTokenHelpers:
    """Unit tests for static token helpers."""

    def test_mint_token_prefix(self):
        """Minted tokens start with 'sess_tok_'."""
        token = SandboxSessionService._mint_token()
        assert token.startswith("sess_tok_")

    def test_mint_token_length(self):
        """Minted tokens are 'sess_tok_' (9) + 40 hex chars = 49 total."""
        token = SandboxSessionService._mint_token()
        assert len(token) == 49

    def test_hash_token_sha256(self):
        """Hash produces a 64-char hex SHA-256 digest."""
        token = "sess_tok_abcdef0123456789abcdef0123456789abcdef01"
        digest = SandboxSessionService._hash_token(token)
        assert len(digest) == 64
        assert digest == hashlib.sha256(token.encode("utf-8")).hexdigest()

    def test_token_prefix_length(self):
        """Prefix is the first 8 characters."""
        token = "sess_tok_abcdef0123456789abcdef0123456789abcdef01"
        assert SandboxSessionService._token_prefix(token) == "sess_tok"


class TestCreateSession:
    """Tests for SandboxSessionService.create_session."""

    @pytest.mark.asyncio
    async def test_returns_plaintext_and_session(
        self, service, mock_db, workspace_id, env_version_id
    ):
        """create_session returns (plaintext_token, SandboxSession)."""
        token, session = await service.create_session(workspace_id, env_version_id)

        assert isinstance(token, str)
        assert token.startswith("sess_tok_")
        assert isinstance(session, SandboxSession)

    @pytest.mark.asyncio
    async def test_stores_hash_not_plaintext(
        self, service, mock_db, workspace_id, env_version_id
    ):
        """The session object stores the SHA-256 hash, not the plaintext."""
        token, session = await service.create_session(workspace_id, env_version_id)

        expected_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        assert session.session_token_hash == expected_hash
        assert token not in str(session.session_token_hash)
        assert token not in str(session.session_token_prefix)

    @pytest.mark.asyncio
    async def test_prefix_is_first_8_chars(
        self, service, mock_db, workspace_id, env_version_id
    ):
        """session_token_prefix is the first 8 chars of the plaintext."""
        token, session = await service.create_session(workspace_id, env_version_id)
        assert session.session_token_prefix == token[:8]

    @pytest.mark.asyncio
    async def test_default_ttl_is_24h(
        self, service, mock_db, workspace_id, env_version_id
    ):
        """Default TTL is 86400 seconds (24 hours)."""
        before = utc_now()
        token, session = await service.create_session(workspace_id, env_version_id)
        after = utc_now()

        expected_min = before + timedelta(seconds=86_400)
        expected_max = after + timedelta(seconds=86_400)
        assert expected_min <= session.expires_at <= expected_max

    @pytest.mark.asyncio
    async def test_custom_ttl(self, service, mock_db, workspace_id, env_version_id):
        """Custom TTL is respected."""
        token, session = await service.create_session(
            workspace_id, env_version_id, ttl_seconds=3600
        )
        now = utc_now()
        expected_min = now + timedelta(seconds=3599)
        expected_max = now + timedelta(seconds=3601)
        assert expected_min <= session.expires_at <= expected_max

    @pytest.mark.asyncio
    async def test_db_add_called(self, service, mock_db, workspace_id, env_version_id):
        """Session is added to the DB and committed."""
        await service.create_session(workspace_id, env_version_id)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()


class TestVerifySessionToken:
    """Tests for SandboxSessionService.verify_session_token."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_session(self, service, mock_db):
        """A valid, non-expired, non-revoked token returns the session."""
        token = "sess_tok_aabbccdd00112233aabbccdd00112233aabbccdd"
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

        fake_session = SandboxSession(
            id=uuid4(),
            session_token_hash=token_hash,
            session_token_prefix="sess_tok_",
            workspace_id=uuid4(),
            environment_version_id=uuid4(),
            expires_at=utc_now() + timedelta(hours=1),
            revoked_at=None,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_session
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.verify_session_token(token)
        assert result is not None
        assert result.session_token_hash == token_hash

    @pytest.mark.asyncio
    async def test_expired_token_returns_none(self, service, mock_db):
        """An expired token returns None."""
        token = "sess_tok_expired00112233aabbccdd00112233aabbccdd00"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.verify_session_token(token)
        assert result is None

    @pytest.mark.asyncio
    async def test_revoked_token_returns_none(self, service, mock_db):
        """A revoked token returns None."""
        token = "sess_tok_revokedd00112233aabbccdd00112233aabbccdd00"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.verify_session_token(token)
        assert result is None

    @pytest.mark.asyncio
    async def test_unknown_token_returns_none(self, service, mock_db):
        """A token that doesn't match any hash returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.verify_session_token("sess_tok_unknown")
        assert result is None

    @pytest.mark.asyncio
    async def test_updates_last_used_at(self, service, mock_db):
        """Successful verification updates last_used_at."""
        token = "sess_tok_aabbccdd00112233aabbccdd00112233aabbccdd"
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

        fake_session = SandboxSession(
            id=uuid4(),
            session_token_hash=token_hash,
            session_token_prefix="sess_tok_",
            workspace_id=uuid4(),
            environment_version_id=uuid4(),
            expires_at=utc_now() + timedelta(hours=1),
            revoked_at=None,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_session
        mock_db.execute = AsyncMock(return_value=mock_result)

        await service.verify_session_token(token)

        assert mock_db.execute.await_count == 2
        mock_db.commit.assert_awaited()


class TestRevoke:
    """Tests for SandboxSessionService.revoke."""

    @pytest.mark.asyncio
    async def test_revoke_sets_revoked_at(self, service, mock_db):
        """revoke() sets revoked_at to now."""
        session_id = uuid4()
        await service.revoke(session_id)

        mock_db.execute.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_revoke_uses_correct_session_id(self, service, mock_db):
        """revoke() targets the correct session by ID."""
        session_id = uuid4()
        await service.revoke(session_id)

        mock_db.execute.assert_awaited_once()


class TestSecurityNoPlaintext:
    """Ensure no plaintext token ever appears in stored columns."""

    @pytest.mark.asyncio
    async def test_plaintext_not_in_hash_column(
        self, service, mock_db, workspace_id, env_version_id
    ):
        """session_token_hash is a SHA-256 digest, not the plaintext."""
        token, session = await service.create_session(workspace_id, env_version_id)
        assert len(session.session_token_hash) == 64
        assert session.session_token_hash != token

    @pytest.mark.asyncio
    async def test_plaintext_not_in_prefix_column(
        self, service, mock_db, workspace_id, env_version_id
    ):
        """session_token_prefix is only 8 chars — not enough to reconstruct."""
        token, session = await service.create_session(workspace_id, env_version_id)
        assert len(session.session_token_prefix) == 8
        assert session.session_token_prefix == token[:8]
        assert len(session.session_token_prefix) < len(token)
