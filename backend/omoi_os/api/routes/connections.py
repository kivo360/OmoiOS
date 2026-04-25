"""User-linked OAuth connections — spec §18 §2 canonical SDK resource.

V1 scope: GitHub personal OAuth only (token stored in
`user.attributes['github_access_token']` by the existing dashboard OAuth
flow in `routes/github_repos.py`). LLM provider API keys stay under the
existing `credentials` resource; workspace-scoped `credential_bindings`
stay under the broker.

Routes:
  GET    /api/v1/connections                    → list connected providers
  DELETE /api/v1/connections/{provider}         → revoke (wipe token)
  POST   /api/v1/connections/{provider}/start   → return OAuth URL

All routes are user-scoped (require a JWT / session). Platform API keys
can't enumerate a user's connections — that's a user-consent boundary.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from omoi_os.api.dependencies import get_current_user, get_db_service
from omoi_os.logging import get_logger
from omoi_os.models.user import User
from omoi_os.services.database import DatabaseService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/connections", tags=["connections"])


# V1 only surfaces GitHub personal OAuth. Additional providers should land
# here when we expose them (GitLab, Linear). Anthropic / OpenAI / Z.ai
# stay under `credentials` because they're bring-your-own-key secrets,
# not OAuth identities.
SUPPORTED_PROVIDERS = frozenset({"github"})


class Connection(BaseModel):
    """One provider the current user has connected via OAuth."""

    provider: str
    connected_at: Optional[datetime] = None
    scopes: List[str] = []


class OAuthStart(BaseModel):
    """Returned by POST /start — the URL the client should navigate to."""

    oauth_start_url: str


def _user_has_github_connection(user: User) -> bool:
    attrs = user.attributes or {}
    token = attrs.get("github_access_token")
    return bool(token)


def _build_connections(user: User) -> List[Connection]:
    """Reflect user.attributes into the Connection list shape."""
    out: List[Connection] = []
    attrs = user.attributes or {}
    if _user_has_github_connection(user):
        # We don't currently persist connection timestamp or granted scopes
        # alongside the token. Surface what we have; null/empty is fine —
        # the shape is stable for future enrichment.
        out.append(
            Connection(
                provider="github",
                connected_at=attrs.get("github_connected_at"),
                scopes=attrs.get("github_scopes") or [],
            )
        )
    return out


@router.get("", response_model=List[Connection])
async def list_connections(
    current_user: User = Depends(get_current_user),
) -> List[Connection]:
    """List OAuth providers the current user has connected."""
    return _build_connections(current_user)


@router.delete("/{provider}", status_code=204)
async def revoke_connection(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
) -> None:
    """Wipe the stored OAuth token for a provider.

    Does NOT call the upstream revoke endpoint — that's deliberately
    out of scope for v1. A follow-up can add GitHub `DELETE /applications/
    {client_id}/token`, but the user can always revoke in GitHub settings.
    """
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown provider '{provider}'",
        )

    token_key = f"{provider}_access_token"
    connected_at_key = f"{provider}_connected_at"
    scopes_key = f"{provider}_scopes"

    with db.get_session() as session:
        user = session.get(User, current_user.id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        attrs = dict(user.attributes or {})
        removed_any = False
        for key in (token_key, connected_at_key, scopes_key):
            if key in attrs:
                del attrs[key]
                removed_any = True
        if removed_any:
            user.attributes = attrs
            session.commit()


@router.post("/{provider}/start", response_model=OAuthStart)
async def start_oauth(
    provider: str,
    current_user: User = Depends(get_current_user),
) -> OAuthStart:
    """Return the URL the client should open to start the OAuth flow.

    We do NOT handle the callback here — that stays in the existing
    dashboard route (`routes/github_repos.py`). SDK callers open the URL
    in a browser, the user grants consent, and GitHub redirects back to
    the platform's existing callback which persists the token into
    `user.attributes['github_access_token']`. SDK then re-reads via
    `GET /api/v1/connections` to observe the connection landed.
    """
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown provider '{provider}'",
        )

    # Delegate to the existing OAuth service which:
    #   1. Builds the authorization URL with client_id/redirect_uri/scopes
    #   2. Stores a `connect:{provider}:{user_id}` state in Redis so the
    #      existing callback handler in routes/oauth.py associates the
    #      granted token with the current user (not by-email matching).
    try:
        from omoi_os.services.oauth_service import get_oauth_service
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth service unavailable on this deployment",
        )

    try:
        oauth_service = get_oauth_service()
        url, _state = oauth_service.get_connect_auth_url(provider, current_user.id)
    except ValueError as e:
        # Provider misconfigured or unknown to the OAuth service
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return OAuthStart(oauth_start_url=url)
