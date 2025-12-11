"""Google OAuth provider."""

from typing import Optional

import httpx

from .base import OAuthProvider, OAuthUserInfo


class GoogleProvider(OAuthProvider):
    """Google OAuth 2.0 provider."""

    name = "google"

    @property
    def authorization_url(self) -> str:
        return "https://accounts.google.com/o/oauth2/v2/auth"

    @property
    def token_url(self) -> str:
        return "https://oauth2.googleapis.com/token"

    @property
    def default_scopes(self) -> list[str]:
        return [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ]

    def _get_extra_auth_params(self) -> dict[str, str]:
        """Request offline access for refresh token."""
        return {
            "access_type": "offline",
            "prompt": "consent",
        }

    async def exchange_code(self, code: str) -> Optional[OAuthUserInfo]:
        """Exchange code for Google user info."""
        token_data = await self._fetch_token(code)
        if not token_data or "access_token" not in token_data:
            return None

        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")

        async with httpx.AsyncClient() as client:
            # Fetch user info
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                return None

            user_data = response.json()

            return OAuthUserInfo(
                provider=self.name,
                provider_user_id=user_data["id"],
                email=user_data.get("email"),
                name=user_data.get("name"),
                avatar_url=user_data.get("picture"),
                access_token=access_token,
                refresh_token=refresh_token,
                raw_data=user_data,
            )
