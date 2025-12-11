"""Base OAuth provider classes using Pydantic models."""

from abc import ABC, abstractmethod
from typing import Any, Optional
from urllib.parse import urlencode
import secrets

import httpx
from pydantic import BaseModel, Field


class OAuthUserInfo(BaseModel):
    """Standardized user information from OAuth providers."""

    provider: str
    provider_user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    access_token: str = ""
    refresh_token: Optional[str] = None
    raw_data: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class OAuthProvider(ABC):
    """Abstract base class for OAuth 2.0 providers."""

    name: str = "base"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    @property
    @abstractmethod
    def authorization_url(self) -> str:
        """OAuth authorization endpoint URL."""
        pass

    @property
    @abstractmethod
    def token_url(self) -> str:
        """OAuth token endpoint URL."""
        pass

    @property
    @abstractmethod
    def default_scopes(self) -> list[str]:
        """Default OAuth scopes to request."""
        pass

    def get_auth_url(
        self,
        state: Optional[str] = None,
        scopes: Optional[list[str]] = None,
    ) -> tuple[str, str]:
        """
        Generate OAuth authorization URL.

        Returns:
            Tuple of (authorization_url, state)
        """
        if state is None:
            state = secrets.token_urlsafe(32)

        if scopes is None:
            scopes = self.default_scopes

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "response_type": "code",
            **self._get_extra_auth_params(),
        }

        return f"{self.authorization_url}?{urlencode(params)}", state

    def _get_extra_auth_params(self) -> dict[str, str]:
        """Override to add provider-specific auth parameters."""
        return {}

    @abstractmethod
    async def exchange_code(self, code: str) -> Optional[OAuthUserInfo]:
        """
        Exchange authorization code for user info.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            OAuthUserInfo if successful, None otherwise
        """
        pass

    async def _fetch_token(self, code: str) -> Optional[dict[str, Any]]:
        """
        Exchange code for access token.

        Args:
            code: Authorization code

        Returns:
            Token response dict or None
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )

            if response.status_code == 200:
                return response.json()

            return None
