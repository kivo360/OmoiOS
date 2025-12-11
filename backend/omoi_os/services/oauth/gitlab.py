"""GitLab OAuth provider."""

from typing import Optional

import httpx

from .base import OAuthProvider, OAuthUserInfo


class GitLabProvider(OAuthProvider):
    """GitLab OAuth 2.0 provider with custom instance support."""

    name = "gitlab"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        base_url: str = "https://gitlab.com",
    ):
        super().__init__(client_id, client_secret, redirect_uri)
        self.base_url = base_url.rstrip("/")

    @property
    def authorization_url(self) -> str:
        return f"{self.base_url}/oauth/authorize"

    @property
    def token_url(self) -> str:
        return f"{self.base_url}/oauth/token"

    @property
    def default_scopes(self) -> list[str]:
        return ["read_user", "email"]

    async def exchange_code(self, code: str) -> Optional[OAuthUserInfo]:
        """Exchange code for GitLab user info."""
        token_data = await self._fetch_token(code)
        if not token_data or "access_token" not in token_data:
            return None

        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")

        async with httpx.AsyncClient() as client:
            # Fetch user info
            response = await client.get(
                f"{self.base_url}/api/v4/user",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                return None

            user_data = response.json()

            return OAuthUserInfo(
                provider=self.name,
                provider_user_id=str(user_data["id"]),
                email=user_data.get("email"),
                name=user_data.get("name") or user_data.get("username"),
                avatar_url=user_data.get("avatar_url"),
                access_token=access_token,
                refresh_token=refresh_token,
                raw_data=user_data,
            )
