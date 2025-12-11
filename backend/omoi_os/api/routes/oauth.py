"""OAuth API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select

from omoi_os.api.dependencies import get_db_service, get_current_user
from omoi_os.config import get_app_settings
from omoi_os.models.user import User
from omoi_os.services.auth_service import AuthService
from omoi_os.services.database import DatabaseService
from omoi_os.services.oauth_service import OAuthService


router = APIRouter()


# ============================================================================
# Pydantic Response Models
# ============================================================================


class ProviderInfo(BaseModel):
    """OAuth provider info."""

    name: str
    enabled: bool


class ProvidersResponse(BaseModel):
    """List of OAuth providers."""

    providers: list[ProviderInfo]


class AuthUrlResponse(BaseModel):
    """OAuth authorization URL response."""

    auth_url: str
    state: str


class ConnectedProvider(BaseModel):
    """Connected OAuth provider info."""

    provider: str
    username: Optional[str] = None
    connected: bool = True


class ConnectedProvidersResponse(BaseModel):
    """List of connected OAuth providers for a user."""

    providers: list[ConnectedProvider]


class DisconnectResponse(BaseModel):
    """Response for disconnecting a provider."""

    success: bool
    message: str


class RedirectUriDiagnostic(BaseModel):
    """OAuth redirect URI diagnostic information."""

    base_redirect_uri: str
    provider: str
    calculated_redirect_uri: str
    message: str


# ============================================================================
# Dependencies
# ============================================================================


def get_oauth_service(
    db: DatabaseService = Depends(get_db_service),
) -> OAuthService:
    """Get OAuth service instance."""
    return OAuthService(db)


def get_auth_service_sync(
    db: DatabaseService = Depends(get_db_service),
) -> AuthService:
    """Get auth service instance with sync session."""
    from omoi_os.config import settings

    with db.get_session() as session:
        return AuthService(
            db=session,
            jwt_secret=settings.jwt_secret_key,
            jwt_algorithm=settings.jwt_algorithm,
            access_token_expire_minutes=settings.access_token_expire_minutes,
            refresh_token_expire_days=settings.refresh_token_expire_days,
        )


# ============================================================================
# Public Routes (No Authentication Required)
# ============================================================================


@router.get("/oauth/providers", response_model=ProvidersResponse)
async def list_oauth_providers(
    oauth_service: OAuthService = Depends(get_oauth_service),
):
    """List available OAuth providers and their status."""
    providers = oauth_service.get_available_providers()
    return ProvidersResponse(providers=[ProviderInfo(**p) for p in providers])


@router.get("/oauth/{provider}/redirect-uri", response_model=RedirectUriDiagnostic)
async def get_redirect_uri_diagnostic(
    provider: str,
    oauth_service: OAuthService = Depends(get_oauth_service),
):
    """
    Get the redirect URI that will be used for a specific OAuth provider.

    This endpoint helps debug OAuth redirect URI configuration issues.
    Use this to verify what redirect URI your app is sending to the OAuth provider.
    """
    settings = get_app_settings().auth
    base_uri = settings.oauth_redirect_uri

    # Build the redirect URI using the same logic as the service
    redirect_uri = oauth_service._build_redirect_uri(provider)

    message = (
        f"This is the redirect URI that will be sent to {provider}. "
        f"Make sure this EXACTLY matches what's registered in your {provider} OAuth app settings. "
        f"See docs/troubleshooting/oauth_redirect_uri_fix.md for help."
    )

    return RedirectUriDiagnostic(
        base_redirect_uri=base_uri,
        provider=provider,
        calculated_redirect_uri=redirect_uri,
        message=message,
    )


@router.get("/oauth/{provider}/url", response_model=AuthUrlResponse)
async def get_oauth_url(
    provider: str,
    oauth_service: OAuthService = Depends(get_oauth_service),
):
    """
    Get OAuth authorization URL for a provider.

    Use this to get the URL to redirect the user to for OAuth login.
    The response includes a state parameter that will be verified on callback.
    """
    try:
        auth_url, state = oauth_service.get_auth_url(provider)
        return AuthUrlResponse(auth_url=auth_url, state=state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/oauth/{provider}")
async def start_oauth(
    provider: str,
    oauth_service: OAuthService = Depends(get_oauth_service),
):
    """
    Start OAuth flow for a provider.

    Redirects user to provider's authorization page.
    """
    try:
        auth_url, state = oauth_service.get_auth_url(provider)
        return RedirectResponse(url=auth_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    oauth_service: OAuthService = Depends(get_oauth_service),
    db: DatabaseService = Depends(get_db_service),
):
    """
    Handle OAuth callback.

    Exchanges code for user info, creates/updates user, and redirects to frontend.
    """
    settings = get_app_settings().auth
    frontend_url = settings.oauth_redirect_uri

    # Handle OAuth error
    if error:
        error_msg = error_description or error
        return RedirectResponse(url=f"{frontend_url}?error={error_msg}")

    # Verify state
    if not oauth_service.verify_state(state, provider):
        return RedirectResponse(url=f"{frontend_url}?error=invalid_state")

    # Exchange code for user info
    oauth_info = await oauth_service.handle_callback(provider, code)
    if not oauth_info:
        return RedirectResponse(url=f"{frontend_url}?error=oauth_failed")

    # Get or create user and generate tokens in the same session
    # This ensures the user object stays attached to the session
    from omoi_os.config import settings as auth_settings

    with db.get_session() as session:
        # Get or create user within this session
        provider_key = f"{oauth_info.provider}_user_id"

        # Try to find by provider user ID
        users = (
            session.execute(select(User).where(User.email == oauth_info.email))
            .scalars()
            .all()
        )

        user = None
        for u in users:
            attrs = u.attributes or {}
            if attrs.get(provider_key) == oauth_info.provider_user_id:
                user = u
                break

        # If no user with OAuth ID, try by email
        if not user and oauth_info.email:
            user = session.execute(
                select(User).where(User.email == oauth_info.email)
            ).scalar_one_or_none()

        if user:
            # Update existing user
            attrs = user.attributes or {}
            attrs[f"{oauth_info.provider}_user_id"] = oauth_info.provider_user_id
            attrs[f"{oauth_info.provider}_access_token"] = oauth_info.access_token
            if oauth_info.refresh_token:
                attrs[f"{oauth_info.provider}_refresh_token"] = oauth_info.refresh_token
            if oauth_info.raw_data.get("login"):
                attrs[f"{oauth_info.provider}_username"] = oauth_info.raw_data["login"]
            user.attributes = attrs

            # Update profile if empty
            if not user.full_name and oauth_info.name:
                user.full_name = oauth_info.name
            if not user.avatar_url and oauth_info.avatar_url:
                user.avatar_url = oauth_info.avatar_url
        else:
            # Create new user
            user = User(
                email=oauth_info.email,
                full_name=oauth_info.name,
                avatar_url=oauth_info.avatar_url,
                is_active=True,
                is_verified=True,  # OAuth emails are verified
                attributes={
                    f"{oauth_info.provider}_user_id": oauth_info.provider_user_id,
                    f"{oauth_info.provider}_access_token": oauth_info.access_token,
                    f"{oauth_info.provider}_refresh_token": oauth_info.refresh_token,
                    f"{oauth_info.provider}_username": oauth_info.raw_data.get("login"),
                },
            )
            session.add(user)

        session.commit()
        session.refresh(user)

        # Get user ID while still in session (before it becomes detached)
        user_id = user.id

        # Generate JWT tokens
        auth_service = AuthService(
            db=session,
            jwt_secret=auth_settings.jwt_secret_key,
            jwt_algorithm=auth_settings.jwt_algorithm,
            access_token_expire_minutes=auth_settings.access_token_expire_minutes,
            refresh_token_expire_days=auth_settings.refresh_token_expire_days,
        )

        access_token = auth_service.create_access_token(user_id)
        refresh_token = auth_service.create_refresh_token(user_id)

        # Expunge user from session to prevent detached instance errors
        session.expunge(user)

    # Redirect to frontend with tokens
    redirect_url = (
        f"{frontend_url}"
        f"?access_token={access_token}"
        f"&refresh_token={refresh_token}"
        f"&provider={provider}"
    )

    return RedirectResponse(url=redirect_url)


# ============================================================================
# Authenticated Routes
# ============================================================================


@router.get("/oauth/connected", response_model=ConnectedProvidersResponse)
async def list_connected_providers(
    current_user: User = Depends(get_current_user),
):
    """List OAuth providers connected to the current user's account."""
    providers = []
    attrs = current_user.attributes or {}

    for provider_name in ["github", "google", "gitlab"]:
        if attrs.get(f"{provider_name}_user_id"):
            providers.append(
                ConnectedProvider(
                    provider=provider_name,
                    username=attrs.get(f"{provider_name}_username"),
                    connected=True,
                )
            )

    return ConnectedProvidersResponse(providers=providers)


@router.post("/oauth/{provider}/connect")
async def connect_provider(
    provider: str,
    oauth_service: OAuthService = Depends(get_oauth_service),
    current_user: User = Depends(get_current_user),
):
    """
    Start OAuth flow to connect a provider to the current user's account.

    Returns the authorization URL - the frontend should redirect the user to this URL.
    """
    try:
        auth_url, state = oauth_service.get_auth_url(provider)
        return AuthUrlResponse(auth_url=auth_url, state=state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/oauth/{provider}/disconnect", response_model=DisconnectResponse)
async def disconnect_provider(
    provider: str,
    oauth_service: OAuthService = Depends(get_oauth_service),
    current_user: User = Depends(get_current_user),
):
    """Disconnect an OAuth provider from the current user's account."""
    # Check if user has a password set (can't disconnect if it's the only auth method)
    attrs = current_user.attributes or {}
    has_password = current_user.hashed_password is not None

    connected_providers = sum(
        1 for p in ["github", "google", "gitlab"] if attrs.get(f"{p}_user_id")
    )

    if not has_password and connected_providers <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot disconnect the only authentication method. Set a password first.",
        )

    success = oauth_service.disconnect_provider(current_user.id, provider)
    if success:
        return DisconnectResponse(
            success=True, message=f"{provider} disconnected successfully"
        )
    else:
        raise HTTPException(status_code=404, detail="User not found")
