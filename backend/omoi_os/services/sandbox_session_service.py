"""Sandbox session service for minting, verifying, and revoking session tokens.

Tokens are minted as ``sess_tok_`` + 40 random hex characters.
Only the SHA-256 hash and an 8-char prefix are stored in the database.
The plaintext token is returned to the caller exactly once at creation.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from omoi_os.models.sandbox_session import SandboxSession
from omoi_os.utils.datetime import utc_now


class SandboxSessionService:
    """Manages lifecycle of sandbox session tokens."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _mint_token() -> str:
        """Generate a new session token: ``sess_tok_`` + 40 random hex chars."""
        return f"sess_tok_{secrets.token_hex(20)}"

    @staticmethod
    def _hash_token(token: str) -> str:
        """Return the SHA-256 hex digest of *token*."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _token_prefix(token: str) -> str:
        """Return the first 8 characters of *token* for log display."""
        return token[:8]

    async def create_session(
        self,
        workspace_id: UUID,
        environment_version_id: UUID,
        ttl_seconds: int = 86_400,
    ) -> tuple[str, SandboxSession]:
        """Mint a new session token and persist its hash.

        Returns:
            A tuple of ``(plaintext_token, SandboxSession)``.
            The plaintext token is returned **once** — it cannot be
            recovered after this call.
        """
        token = self._mint_token()
        token_hash = self._hash_token(token)
        prefix = self._token_prefix(token)

        now = utc_now()
        session = SandboxSession(
            session_token_hash=token_hash,
            session_token_prefix=prefix,
            workspace_id=workspace_id,
            environment_version_id=environment_version_id,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        return token, session

    async def verify_session_token(
        self,
        token: str,
    ) -> Optional[SandboxSession]:
        """Verify a plaintext token and return the associated session.

        Checks:
        1. Token hash matches a stored session.
        2. Session has not expired (``expires_at > now``).
        3. Session has not been revoked (``revoked_at IS NULL``).

        On success, updates ``last_used_at``.

        Returns:
            The :class:`SandboxSession` if valid, otherwise ``None``.
        """
        token_hash = self._hash_token(token)
        now = utc_now()

        result = await self.db.execute(
            select(SandboxSession).where(
                SandboxSession.session_token_hash == token_hash,
                SandboxSession.expires_at > now,
                SandboxSession.revoked_at.is_(None),
            )
        )
        session = result.scalar_one_or_none()

        if session is None:
            return None

        await self.db.execute(
            update(SandboxSession)
            .where(SandboxSession.id == session.id)
            .values(last_used_at=now)
        )
        await self.db.commit()
        await self.db.refresh(session)

        return session

    async def revoke(
        self,
        session_id: UUID,
    ) -> None:
        """Revoke a session by setting ``revoked_at`` to now."""
        await self.db.execute(
            update(SandboxSession)
            .where(SandboxSession.id == session_id)
            .values(revoked_at=utc_now())
        )
        await self.db.commit()
