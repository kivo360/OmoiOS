"""GitHub OAuth provider."""

from typing import Optional

import httpx

from .base import OAuthProvider, OAuthUserInfo


class GitHubProvider(OAuthProvider):
    """GitHub OAuth 2.0 provider with repository access."""

    name = "github"

    @property
    def authorization_url(self) -> str:
        return "https://github.com/login/oauth/authorize"

    @property
    def token_url(self) -> str:
        return "https://github.com/login/oauth/access_token"

    @property
    def default_scopes(self) -> list[str]:
        return [
            "read:user",  # Read user profile
            "user:email",  # Access email addresses
            "repo",  # Full control of private and public repos
            "read:org",  # Read org membership
        ]

    async def exchange_code(self, code: str) -> Optional[OAuthUserInfo]:
        """Exchange code for GitHub user info."""
        token_data = await self._fetch_token(code)
        if not token_data or "access_token" not in token_data:
            return None

        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")

        async with httpx.AsyncClient() as client:
            # Fetch user profile
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }

            user_response = await client.get(
                "https://api.github.com/user",
                headers=headers,
            )

            if user_response.status_code != 200:
                return None

            user_data = user_response.json()

            # Get granted scopes from response headers
            granted_scopes = user_response.headers.get("X-OAuth-Scopes", "")

            # Fetch email if not in profile
            email = user_data.get("email")
            if not email:
                email_response = await client.get(
                    "https://api.github.com/user/emails",
                    headers=headers,
                )

                if email_response.status_code == 200:
                    emails = email_response.json()
                    # Find primary verified email
                    for e in emails:
                        if e.get("primary") and e.get("verified"):
                            email = e.get("email")
                            break
                    # Fallback to first verified email
                    if not email:
                        for e in emails:
                            if e.get("verified"):
                                email = e.get("email")
                                break

            return OAuthUserInfo(
                provider=self.name,
                provider_user_id=str(user_data["id"]),
                email=email,
                name=user_data.get("name") or user_data.get("login"),
                avatar_url=user_data.get("avatar_url"),
                access_token=access_token,
                refresh_token=refresh_token,
                raw_data={
                    **user_data,
                    "granted_scopes": granted_scopes,
                    "login": user_data.get("login"),
                },
            )
