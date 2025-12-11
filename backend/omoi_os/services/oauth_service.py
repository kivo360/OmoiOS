"""OAuth service for managing authentication flows."""

import logging
from functools import lru_cache
from typing import Optional
from uuid import UUID

import redis
from sqlalchemy import select

from omoi_os.config import get_app_settings
from omoi_os.models.user import User
from omoi_os.services.database import DatabaseService
from omoi_os.services.oauth import get_provider, list_providers, OAuthUserInfo


logger = logging.getLogger(__name__)

# Redis key prefix for OAuth state storage
OAUTH_STATE_PREFIX = "oauth_state:"
# OAuth state TTL in seconds (10 minutes - enough time to complete OAuth flow)
OAUTH_STATE_TTL = 600


@lru_cache(maxsize=1)
def get_oauth_redis_client() -> redis.Redis:
    """Get cached Redis client for OAuth state storage."""
    redis_url = get_app_settings().redis_url
    return redis.from_url(redis_url, decode_responses=True)


class OAuthService:
    """Service for OAuth authentication flows."""

    def __init__(self, db: DatabaseService, redis_client: Optional[redis.Redis] = None):
        self.db = db
        self.settings = get_app_settings().auth

        # Use provided Redis client or get cached one
        self._redis = (
            redis_client if redis_client is not None else get_oauth_redis_client()
        )

    def get_available_providers(self) -> list[dict]:
        """Get list of configured OAuth providers."""
        providers = []
        for name in list_providers():
            config = self.settings.get_provider_config(name)
            providers.append(
                {
                    "name": name,
                    "enabled": config is not None,
                }
            )
        return providers

    def _build_redirect_uri(self, provider_name: str) -> str:
        """Build the OAuth callback redirect URI for a provider."""
        # Parse the base redirect URI to construct the callback URL
        base_uri = self.settings.oauth_redirect_uri

        # The redirect_uri sent to OAuth providers must point to the BACKEND callback endpoint
        # The base_uri is the frontend callback URL (e.g., http://localhost:3000/auth/callback)
        # We need to convert it to the backend callback URL (e.g., http://localhost:18000/api/v1/auth/oauth/{provider}/callback)

        from urllib.parse import urlparse

        parsed = urlparse(base_uri)

        # Extract the origin (scheme + netloc)
        if "localhost:3000" in parsed.netloc:
            # Development: frontend on 3000, backend on 18000
            backend_netloc = parsed.netloc.replace("localhost:3000", "localhost:18000")
        else:
            # Production: use same origin (backend and frontend on same domain)
            backend_netloc = parsed.netloc

        # Build the backend callback URL
        redirect_uri = f"{parsed.scheme}://{backend_netloc}/api/v1/auth/oauth/{provider_name}/callback"

        # Log the redirect URI for debugging OAuth configuration issues
        logger.info(
            f"OAuth redirect URI for {provider_name}: {redirect_uri} "
            f"(base_uri: {base_uri})"
        )

        return redirect_uri

    def get_auth_url(self, provider_name: str) -> tuple[str, str]:
        """
        Get OAuth authorization URL for a provider.

        Args:
            provider_name: Name of the OAuth provider

        Returns:
            Tuple of (auth_url, state)

        Raises:
            ValueError: If provider not configured
        """
        config = self.settings.get_provider_config(provider_name)
        if not config:
            raise ValueError(f"Provider '{provider_name}' not configured")

        redirect_uri = self._build_redirect_uri(provider_name)

        provider = get_provider(
            name=provider_name,
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            redirect_uri=redirect_uri,
            **{
                k: v
                for k, v in config.items()
                if k not in ("client_id", "client_secret")
            },
        )

        if not provider:
            raise ValueError(f"Provider '{provider_name}' not found")

        auth_url, state = provider.get_auth_url()

        # Log the authorization URL (without sensitive data) for debugging
        logger.debug(
            f"Generated OAuth auth URL for {provider_name} (state: {state[:8]}...)"
        )

        # Store state in Redis with TTL for verification
        state_key = f"{OAUTH_STATE_PREFIX}{state}"
        try:
            self._redis.setex(state_key, OAUTH_STATE_TTL, provider_name)
            logger.debug(f"Stored OAuth state for provider {provider_name}")
        except redis.RedisError as e:
            logger.error(f"Failed to store OAuth state in Redis: {e}")
            raise ValueError("Failed to initialize OAuth flow. Please try again.")

        return auth_url, state

    def verify_state(self, state: str, provider_name: str) -> bool:
        """Verify OAuth state parameter and remove it (one-time use)."""
        state_key = f"{OAUTH_STATE_PREFIX}{state}"
        try:
            # Get and delete atomically using pipeline
            pipe = self._redis.pipeline()
            pipe.get(state_key)
            pipe.delete(state_key)
            results = pipe.execute()
            stored_provider = results[0]

            if stored_provider is None:
                logger.warning(f"OAuth state not found or expired: {state[:8]}...")
                return False

            is_valid = stored_provider == provider_name
            if not is_valid:
                logger.warning(
                    f"OAuth state provider mismatch: expected {provider_name}, got {stored_provider}"
                )
            return is_valid
        except redis.RedisError as e:
            logger.error(f"Failed to verify OAuth state in Redis: {e}")
            return False

    async def handle_callback(
        self,
        provider_name: str,
        code: str,
    ) -> Optional[OAuthUserInfo]:
        """
        Handle OAuth callback and exchange code for user info.

        Args:
            provider_name: Name of the OAuth provider
            code: Authorization code from callback

        Returns:
            OAuthUserInfo if successful, None otherwise
        """
        config = self.settings.get_provider_config(provider_name)
        if not config:
            return None

        redirect_uri = self._build_redirect_uri(provider_name)

        provider = get_provider(
            name=provider_name,
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            redirect_uri=redirect_uri,
            **{
                k: v
                for k, v in config.items()
                if k not in ("client_id", "client_secret")
            },
        )

        if not provider:
            return None

        return await provider.exchange_code(code)

    def get_or_create_user(self, oauth_info: OAuthUserInfo) -> User:
        """
        Get existing user or create new one from OAuth info.

        Stores OAuth tokens in user.attributes.

        Args:
            oauth_info: User info from OAuth provider

        Returns:
            User instance
        """
        with self.db.get_session() as session:
            # Try to find by provider user ID
            provider_key = f"{oauth_info.provider}_user_id"

            # First check if user exists with this OAuth ID
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
                    attrs[f"{oauth_info.provider}_refresh_token"] = (
                        oauth_info.refresh_token
                    )
                if oauth_info.raw_data.get("login"):
                    attrs[f"{oauth_info.provider}_username"] = oauth_info.raw_data[
                        "login"
                    ]
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
                        f"{oauth_info.provider}_username": oauth_info.raw_data.get(
                            "login"
                        ),
                    },
                )
                session.add(user)

            session.commit()
            session.refresh(user)

            # Expunge user from session to prevent detached instance errors
            # when user object is used outside this session context
            session.expunge(user)

            return user

    def get_user_oauth_token(self, user_id: UUID, provider: str) -> Optional[str]:
        """
        Get OAuth access token for a user and provider.

        Args:
            user_id: User ID
            provider: OAuth provider name

        Returns:
            Access token if found, None otherwise
        """
        with self.db.get_session() as session:
            user = session.get(User, user_id)
            if not user:
                return None

            attrs = user.attributes or {}
            return attrs.get(f"{provider}_access_token")

    def update_user_oauth_token(
        self,
        user_id: UUID,
        provider: str,
        access_token: str,
        refresh_token: Optional[str] = None,
    ) -> bool:
        """
        Update OAuth tokens for a user.

        Args:
            user_id: User ID
            provider: OAuth provider name
            access_token: New access token
            refresh_token: Optional new refresh token

        Returns:
            True if updated, False if user not found
        """
        with self.db.get_session() as session:
            user = session.get(User, user_id)
            if not user:
                return False

            attrs = user.attributes or {}
            attrs[f"{provider}_access_token"] = access_token
            if refresh_token:
                attrs[f"{provider}_refresh_token"] = refresh_token
            user.attributes = attrs

            session.commit()
            return True

    def disconnect_provider(self, user_id: UUID, provider: str) -> bool:
        """
        Disconnect an OAuth provider from a user account.

        Args:
            user_id: User ID
            provider: OAuth provider name

        Returns:
            True if disconnected, False if user not found
        """
        with self.db.get_session() as session:
            user = session.get(User, user_id)
            if not user:
                return False

            attrs = user.attributes or {}

            # Remove all provider-related attributes
            keys_to_remove = [
                f"{provider}_user_id",
                f"{provider}_access_token",
                f"{provider}_refresh_token",
                f"{provider}_username",
            ]

            for key in keys_to_remove:
                attrs.pop(key, None)

            user.attributes = attrs
            session.commit()
            return True
