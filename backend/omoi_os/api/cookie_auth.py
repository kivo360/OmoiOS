"""HTTP-only cookie authentication helpers.

Provides secure cookie setting/clearing for JWT tokens.
Cookies are httpOnly (not accessible by JS), Secure (HTTPS only in production),
and SameSite=Lax (CSRF protection with cross-origin GET allowed for OAuth redirects).
"""

from __future__ import annotations

from fastapi import Request, Response

from omoi_os.config import get_app_settings

# Cookie names
ACCESS_TOKEN_COOKIE = "omoios_access_token"
REFRESH_TOKEN_COOKIE = "omoios_refresh_token"

# Cookie for frontend auth state detection (NOT httpOnly — readable by JS)
AUTH_STATE_COOKIE = "omoios_auth_state"


def _is_secure() -> bool:
    """Check if we should set Secure flag (HTTPS only)."""
    try:
        settings = get_app_settings()
        return getattr(settings, "env", "development") == "production"
    except Exception:
        return False


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    access_token_max_age: int | None = None,
    refresh_token_max_age: int | None = None,
) -> None:
    """Set httpOnly auth cookies on a response.

    Args:
        response: FastAPI Response object
        access_token: JWT access token
        refresh_token: JWT refresh token
        access_token_max_age: Max age in seconds (defaults to access_token_expire_minutes)
        refresh_token_max_age: Max age in seconds (defaults to refresh_token_expire_days)
    """
    settings = get_app_settings().auth
    secure = _is_secure()

    if access_token_max_age is None:
        access_token_max_age = settings.access_token_expire_minutes * 60

    if refresh_token_max_age is None:
        refresh_token_max_age = settings.refresh_token_expire_days * 86400

    # httpOnly access token cookie
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        max_age=access_token_max_age,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )

    # httpOnly refresh token cookie — scoped to refresh endpoint
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        max_age=refresh_token_max_age,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",  # Broad path so frontend can trigger refresh from any page
    )

    # Non-httpOnly state cookie for frontend to detect auth status (no sensitive data)
    response.set_cookie(
        key=AUTH_STATE_COOKIE,
        value="true",
        max_age=refresh_token_max_age,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear all auth cookies."""
    secure = _is_secure()

    for cookie_name in (ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE, AUTH_STATE_COOKIE):
        response.delete_cookie(
            key=cookie_name,
            path="/",
            secure=secure,
            samesite="lax",
        )


def get_token_from_request(request: Request) -> str | None:
    """Extract access token from request — checks Bearer header first, then cookies.

    Priority:
    1. Authorization: Bearer <token> header
    2. omoios_access_token cookie

    Returns:
        Token string or None
    """
    # 1. Check Authorization header
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header[7:]

    # 2. Check httpOnly cookie
    return request.cookies.get(ACCESS_TOKEN_COOKIE)


def get_refresh_token_from_request(request: Request) -> str | None:
    """Extract refresh token from request — checks body first, then cookies.

    Returns:
        Refresh token string or None
    """
    return request.cookies.get(REFRESH_TOKEN_COOKIE)
