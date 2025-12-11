"""OAuth provider registry and exports."""

from typing import Optional, Type

from .base import OAuthProvider, OAuthUserInfo
from .github import GitHubProvider
from .google import GoogleProvider
from .gitlab import GitLabProvider


# Provider registry
PROVIDERS: dict[str, Type[OAuthProvider]] = {
    "github": GitHubProvider,
    "google": GoogleProvider,
    "gitlab": GitLabProvider,
}


def get_provider(
    name: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    **kwargs,
) -> Optional[OAuthProvider]:
    """
    Get an OAuth provider instance by name.

    Args:
        name: Provider name (github, google, gitlab)
        client_id: OAuth client ID
        client_secret: OAuth client secret
        redirect_uri: OAuth redirect URI
        **kwargs: Additional provider-specific arguments

    Returns:
        Provider instance or None if not found
    """
    provider_class = PROVIDERS.get(name.lower())
    if provider_class is None:
        return None

    return provider_class(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        **kwargs,
    )


def list_providers() -> list[str]:
    """Get list of registered provider names."""
    return list(PROVIDERS.keys())


def register_provider(name: str, provider_class: Type[OAuthProvider]) -> None:
    """Register a new OAuth provider."""
    PROVIDERS[name.lower()] = provider_class


__all__ = [
    "OAuthProvider",
    "OAuthUserInfo",
    "GitHubProvider",
    "GoogleProvider",
    "GitLabProvider",
    "PROVIDERS",
    "get_provider",
    "list_providers",
    "register_provider",
]
