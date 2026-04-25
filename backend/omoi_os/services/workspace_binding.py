"""Workspace ↔ GitHub repo binding.

Mirrors the auto-project pattern in `routes/tickets.py` (which maps a repo
string to a Project on the workflow side) but scoped to `Workspace` — the
spec §02 resource SDK callers interact with.

Idempotent: calling `ensure_workspace_for_github_repo(org_id, "foo/bar", …)`
twice returns the same workspace row both times. The unique partial index
`ux_workspaces_org_repo` (migration 071) is the race-proof backstop.
"""

from __future__ import annotations

import re
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from omoi_os.models.workspace import Workspace


_GITHUB_SLUG_RE = re.compile(r"^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$")


def _parse_slug(github_repo: str) -> tuple[str, str]:
    """Parse "owner/repo" or raise ValueError."""
    m = _GITHUB_SLUG_RE.match(github_repo.strip())
    if not m:
        raise ValueError(f"Invalid github_repo '{github_repo}' — expected 'owner/repo'")
    return m.group(1), m.group(2)


def _slugify(owner: str, repo: str) -> str:
    """Build a workspace slug from owner/repo. Not a security boundary — the
    unique constraint in `ux_workspaces_org_repo` is the source of truth."""
    return f"{owner}-{repo}".lower()


def ensure_workspace_for_github_repo_sync(
    session: Session,
    organization_id: UUID,
    github_repo: str,
    created_by: Optional[UUID] = None,
) -> Workspace:
    """Find-or-create a workspace bound to (org, github_owner, github_repo).

    Synchronous variant for callers inside `db.get_session()` blocks.
    """
    owner, repo = _parse_slug(github_repo)

    existing = (
        session.query(Workspace)
        .filter(
            Workspace.organization_id == organization_id,
            Workspace.github_owner == owner,
            Workspace.github_repo == repo,
        )
        .first()
    )
    if existing:
        return existing

    ws = Workspace(
        organization_id=organization_id,
        name=f"{owner}/{repo}",
        slug=_slugify(owner, repo),
        github_owner=owner,
        github_repo=repo,
        github_connected=True,
        settings={
            "source": "sdk-auto-bind",
            "created_by": str(created_by) if created_by else None,
        },
    )
    session.add(ws)
    session.flush()
    return ws


async def ensure_workspace_for_github_repo(
    session: AsyncSession,
    organization_id: UUID,
    github_repo: str,
    created_by: Optional[UUID] = None,
) -> Workspace:
    """Find-or-create a workspace bound to (org, github_owner, github_repo).

    Async variant for FastAPI routes using AsyncSession.
    """
    owner, repo = _parse_slug(github_repo)

    existing = await session.execute(
        select(Workspace).where(
            Workspace.organization_id == organization_id,
            Workspace.github_owner == owner,
            Workspace.github_repo == repo,
        )
    )
    ws = existing.scalar_one_or_none()
    if ws:
        return ws

    ws = Workspace(
        organization_id=organization_id,
        name=f"{owner}/{repo}",
        slug=_slugify(owner, repo),
        github_owner=owner,
        github_repo=repo,
        github_connected=True,
        settings={
            "source": "sdk-auto-bind",
            "created_by": str(created_by) if created_by else None,
        },
    )
    session.add(ws)
    await session.flush()
    return ws
