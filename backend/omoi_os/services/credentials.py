"""User credentials service for managing external API keys.

This service handles CRUD operations for user credentials and provides
methods for the spawner to fetch credentials when spawning sandboxes.

Fallback Logic:
1. User-specific credentials (from UserCredential table)
2. System defaults (from environment variables / config)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from omoi_os.config import get_app_settings, load_anthropic_settings
from omoi_os.models.user_credentials import UserCredential
from omoi_os.services.database import DatabaseService

logger = logging.getLogger(__name__)


@dataclass
class AnthropicCredentials:
    """Container for Anthropic API credentials.

    Token Configuration:
    - max_tokens: Maximum output tokens per response (default: 16384)
    - context_length: Model's context window size (GLM-4.6v: 128k)
    """

    api_key: str
    base_url: Optional[str] = None
    model: Optional[str] = None
    default_model: Optional[str] = None
    default_haiku_model: Optional[str] = None
    default_sonnet_model: Optional[str] = None
    default_opus_model: Optional[str] = None
    max_tokens: int = 16384  # Max output tokens per response
    context_length: int = 128000  # Model context window (GLM-4.6v = 128k)
    source: str = "config"  # "config" or "user"


@dataclass
class GitHubCredentials:
    """Container for GitHub credentials."""

    access_token: Optional[str] = None
    username: Optional[str] = None
    source: str = "config"  # "config", "user", or "oauth"

    @property
    def is_valid(self) -> bool:
        """Check if credentials are usable."""
        return bool(self.access_token)


@dataclass
class GenericCredentials:
    """Generic container for any provider's credentials."""

    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    config_data: Dict[str, Any] = field(default_factory=dict)
    source: str = "config"  # "config" or "user"

    @property
    def is_valid(self) -> bool:
        """Check if credentials are usable."""
        return bool(self.api_key)


class CredentialsService:
    """Service for managing user credentials with fallback defaults.

    Provides methods to:
    - Get user credentials for a specific provider
    - Get Anthropic credentials (user-specific or fallback to config)
    - Get GitHub credentials (user OAuth or fallback to system token)
    - Get generic credentials for any provider
    - Save/update user credentials

    Fallback Priority:
    1. User-specific credentials from database
    2. System defaults from environment/config
    """

    # Environment variable mappings for system defaults
    # Note: Default LLM is Z.AI with GLM-4.6v (configured in AnthropicSettings)
    DEFAULT_ENV_VARS = {
        "anthropic": {
            "api_key": "ANTHROPIC_API_KEY",  # or ANTHROPIC_AUTH_TOKEN
            "base_url": "ANTHROPIC_BASE_URL",  # Default: https://api.z.ai/api/anthropic
            "model": "ANTHROPIC_MODEL",  # Default: glm-4.6v
        },
        "openai": {
            "api_key": "OPENAI_API_KEY",
            "base_url": "OPENAI_BASE_URL",
            "model": "OPENAI_MODEL",
        },
        "github": {
            "api_key": "GITHUB_TOKEN",  # System default token
        },
        "z_ai": {
            # Z.AI uses Anthropic-compatible endpoint, so ANTHROPIC_* vars work
            "api_key": "ANTHROPIC_API_KEY",
            "base_url": "ANTHROPIC_BASE_URL",
            "model": "ANTHROPIC_MODEL",
        },
    }

    # Default model configuration (Z.AI / GLM)
    DEFAULT_BASE_URL = "https://api.z.ai/api/anthropic"
    DEFAULT_MODEL = "glm-4.6v"
    DEFAULT_MAX_TOKENS = 16384  # Max output tokens per response
    DEFAULT_CONTEXT_LENGTH = 128000  # GLM-4.6v context window (128k)
    DEFAULT_MODELS = {
        "default": "glm-4.6v",
        "haiku": "glm-4.6v-flash",  # Fast/cheap
        "sonnet": "glm-4.6v",  # Balanced
        "opus": "glm-4.6v",  # Most capable
    }

    def __init__(self, db: DatabaseService):
        self.db = db

    @classmethod
    def get_default_llm_config(cls) -> Dict[str, Any]:
        """Get the default LLM configuration (Z.AI / GLM).

        Returns:
            Dict with base_url, model, model variants, and token limits
        """
        return {
            "base_url": cls.DEFAULT_BASE_URL,
            "model": cls.DEFAULT_MODEL,
            "haiku_model": cls.DEFAULT_MODELS["haiku"],
            "sonnet_model": cls.DEFAULT_MODELS["sonnet"],
            "opus_model": cls.DEFAULT_MODELS["opus"],
            "max_tokens": cls.DEFAULT_MAX_TOKENS,
            "context_length": cls.DEFAULT_CONTEXT_LENGTH,
        }

    def check_default_credentials(self) -> Dict[str, bool]:
        """Check which default credentials are configured.

        Returns:
            Dict mapping provider -> bool (True if API key is available)
        """
        settings = load_anthropic_settings()

        return {
            "anthropic": bool(settings.get_api_key()),
            "github": bool(
                os.environ.get("GITHUB_TOKEN")
                or get_app_settings().integration.github_token
            ),
            "openai": bool(os.environ.get("OPENAI_API_KEY")),
        }

    def get_user_credential(
        self,
        user_id: UUID,
        provider: str,
        session: Optional[Session] = None,
    ) -> Optional[UserCredential]:
        """Get a user's credential for a specific provider.

        Args:
            user_id: The user's ID
            provider: Service provider (e.g., 'anthropic', 'openai')
            session: Optional existing session

        Returns:
            UserCredential if found, None otherwise
        """

        def _query(sess: Session) -> Optional[UserCredential]:
            stmt = (
                select(UserCredential)
                .where(
                    UserCredential.user_id == user_id,
                    UserCredential.provider == provider,
                    UserCredential.is_active == True,  # noqa: E712
                )
                .order_by(
                    UserCredential.is_default.desc(),  # Prefer default
                    UserCredential.created_at.desc(),  # Then newest
                )
                .limit(1)
            )
            return sess.execute(stmt).scalar_one_or_none()

        if session:
            return _query(session)

        with self.db.get_session() as sess:
            return _query(sess)

    def get_anthropic_credentials(
        self,
        user_id: Optional[UUID] = None,
        session: Optional[Session] = None,
    ) -> AnthropicCredentials:
        """Get Anthropic credentials, preferring user-specific if available.

        This method implements the fallback logic:
        1. If user_id is provided, check for user-specific credentials
        2. If no user credentials, fall back to global config

        Args:
            user_id: Optional user ID to check for custom credentials
            session: Optional existing database session

        Returns:
            AnthropicCredentials with the API key and configuration
        """
        # Try user-specific credentials first
        if user_id:
            user_cred = self.get_user_credential(user_id, "anthropic", session)
            if user_cred and user_cred.api_key:
                logger.debug(f"Using user credentials for user {user_id}")

                # Extract model configuration from config_data
                config = user_cred.config_data or {}

                return AnthropicCredentials(
                    api_key=user_cred.api_key,
                    base_url=user_cred.base_url,
                    model=user_cred.model or config.get("model"),
                    default_model=config.get("default_model"),
                    default_haiku_model=config.get("default_haiku_model"),
                    default_sonnet_model=config.get("default_sonnet_model"),
                    default_opus_model=config.get("default_opus_model"),
                    max_tokens=config.get("max_tokens", self.DEFAULT_MAX_TOKENS),
                    context_length=config.get(
                        "context_length", self.DEFAULT_CONTEXT_LENGTH
                    ),
                    source="user",
                )

        # Fall back to global config
        logger.debug("Using global config for Anthropic credentials")
        settings = load_anthropic_settings()

        return AnthropicCredentials(
            api_key=settings.get_api_key() or "",
            base_url=settings.base_url,
            model=settings.model,
            default_model=settings.default_model,
            default_haiku_model=settings.default_haiku_model,
            default_sonnet_model=settings.default_sonnet_model,
            default_opus_model=settings.default_opus_model,
            max_tokens=settings.max_tokens,
            context_length=settings.context_length,
            source="config",
        )

    def get_github_credentials(
        self,
        user_id: Optional[UUID] = None,
        session: Optional[Session] = None,
    ) -> GitHubCredentials:
        """Get GitHub credentials, preferring user OAuth token if available.

        Fallback order:
        1. User's OAuth access token (from User model via github_access_token)
        2. User's stored credential (provider="github")
        3. System default (GITHUB_TOKEN env var or integration settings)

        Args:
            user_id: Optional user ID to check for OAuth/stored credentials
            session: Optional existing database session

        Returns:
            GitHubCredentials with token and source info
        """
        # Try user's OAuth token first (stored on User model)
        if user_id:
            from omoi_os.models.user import User

            def _get_user_oauth(sess: Session) -> Optional[GitHubCredentials]:
                user = sess.get(User, user_id)
                if (
                    user
                    and hasattr(user, "github_access_token")
                    and user.github_access_token
                ):
                    logger.debug(f"Using GitHub OAuth token for user {user_id}")
                    return GitHubCredentials(
                        access_token=user.github_access_token,
                        username=getattr(user, "github_username", None),
                        source="oauth",
                    )
                return None

            if session:
                oauth_creds = _get_user_oauth(session)
                if oauth_creds:
                    return oauth_creds
            else:
                with self.db.get_session() as sess:
                    oauth_creds = _get_user_oauth(sess)
                    if oauth_creds:
                        return oauth_creds

            # Try user's stored credential
            user_cred = self.get_user_credential(user_id, "github", session)
            if user_cred and user_cred.api_key:
                logger.debug(f"Using stored GitHub credential for user {user_id}")
                config = user_cred.config_data or {}
                return GitHubCredentials(
                    access_token=user_cred.api_key,
                    username=config.get("username"),
                    source="user",
                )

        # Fall back to system default
        system_token = os.environ.get("GITHUB_TOKEN")
        if not system_token:
            # Try integration settings
            try:
                settings = get_app_settings()
                system_token = settings.integration.github_token
            except Exception:
                pass

        if system_token:
            logger.debug("Using system default GitHub token")
            return GitHubCredentials(
                access_token=system_token,
                source="config",
            )

        logger.warning("No GitHub credentials available")
        return GitHubCredentials(source="none")

    def get_credentials(
        self,
        provider: str,
        user_id: Optional[UUID] = None,
        session: Optional[Session] = None,
    ) -> GenericCredentials:
        """Get credentials for any provider with fallback to system defaults.

        This is a generic method that works for any provider. For providers
        with specific needs (like Anthropic or GitHub), use the dedicated methods.

        Fallback order:
        1. User-specific credential from database
        2. System default from environment variables

        Args:
            provider: Provider name (e.g., 'openai', 'z_ai', 'fireworks')
            user_id: Optional user ID to check for custom credentials
            session: Optional existing database session

        Returns:
            GenericCredentials with the credentials and source info
        """
        # Try user-specific credentials first
        if user_id:
            user_cred = self.get_user_credential(user_id, provider, session)
            if user_cred and user_cred.api_key:
                logger.debug(f"Using user credentials for {provider} (user {user_id})")
                return GenericCredentials(
                    provider=provider,
                    api_key=user_cred.api_key,
                    base_url=user_cred.base_url,
                    model=user_cred.model,
                    config_data=user_cred.config_data or {},
                    source="user",
                )

        # Fall back to environment variables
        env_mapping = self.DEFAULT_ENV_VARS.get(provider, {})
        api_key = os.environ.get(
            env_mapping.get("api_key", f"{provider.upper()}_API_KEY")
        )
        base_url = os.environ.get(
            env_mapping.get("base_url", f"{provider.upper()}_BASE_URL")
        )
        model = os.environ.get(env_mapping.get("model", f"{provider.upper()}_MODEL"))

        if api_key:
            logger.debug(f"Using system default credentials for {provider}")
            return GenericCredentials(
                provider=provider,
                api_key=api_key,
                base_url=base_url,
                model=model,
                source="config",
            )

        logger.warning(f"No credentials available for {provider}")
        return GenericCredentials(provider=provider, source="none")

    def get_sandbox_env_vars(
        self,
        user_id: Optional[UUID] = None,
        project_id: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> Dict[str, str]:
        """Get all environment variables needed for a sandbox.

        This is a convenience method that aggregates credentials for sandbox spawning.

        Args:
            user_id: User ID to fetch credentials for
            project_id: Project ID to fetch repo info from
            session: Optional database session

        Returns:
            Dict of environment variable name -> value
        """
        env_vars: Dict[str, str] = {}

        # Anthropic/LLM credentials
        anthropic_creds: AnthropicCredentials = self.get_anthropic_credentials(
            user_id, session
        )
        if anthropic_creds.api_key:
            env_vars["ANTHROPIC_API_KEY"] = anthropic_creds.api_key
        if anthropic_creds.base_url:
            env_vars["ANTHROPIC_BASE_URL"] = anthropic_creds.base_url
        if anthropic_creds.model:
            env_vars["MODEL"] = anthropic_creds.model
        # Token limits
        env_vars["MAX_TOKENS"] = str(anthropic_creds.max_tokens)
        env_vars["CONTEXT_LENGTH"] = str(anthropic_creds.context_length)

        # GitHub credentials
        github_creds = self.get_github_credentials(user_id, session)
        if github_creds.access_token:
            env_vars["GITHUB_TOKEN"] = github_creds.access_token

        # Project repo info
        if project_id:
            from omoi_os.models.project import Project

            def _get_project_repo(sess: Session) -> None:
                project = sess.get(Project, project_id)
                if project and project.github_owner and project.github_repo:
                    env_vars["GITHUB_REPO"] = (
                        f"{project.github_owner}/{project.github_repo}"
                    )

            if session:
                _get_project_repo(session)
            else:
                with self.db.get_session() as sess:
                    _get_project_repo(sess)

        return env_vars

    def save_user_credential(
        self,
        user_id: UUID,
        provider: str,
        api_key: str,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        name: Optional[str] = None,
        config_data: Optional[dict] = None,
        is_default: bool = True,
        session: Optional[Session] = None,
    ) -> UserCredential:
        """Save or update a user's credential for a provider.

        Args:
            user_id: The user's ID
            provider: Service provider (e.g., 'anthropic', 'openai')
            api_key: The API key to store
            base_url: Optional custom base URL
            model: Optional default model
            name: Optional friendly name
            config_data: Optional additional configuration
            is_default: Whether this should be the default for this provider
            session: Optional existing session

        Returns:
            The created or updated UserCredential
        """

        def _save(sess: Session) -> UserCredential:
            # Check for existing credential
            existing = self.get_user_credential(user_id, provider, sess)

            if existing:
                # Update existing
                existing.api_key = api_key
                existing.base_url = base_url
                existing.model = model
                if name:
                    existing.name = name
                if config_data:
                    existing.config_data = config_data
                existing.is_default = is_default
                sess.flush()
                return existing

            # Create new
            cred = UserCredential(
                user_id=user_id,
                provider=provider,
                api_key=api_key,
                base_url=base_url,
                model=model,
                name=name or f"{provider.title()} API Key",
                config_data=config_data or {},
                is_default=is_default,
            )
            sess.add(cred)
            sess.flush()
            return cred

        if session:
            return _save(session)

        with self.db.get_session() as sess:
            result = _save(sess)
            sess.commit()
            return result

    def delete_user_credential(
        self,
        user_id: UUID,
        provider: str,
        session: Optional[Session] = None,
    ) -> bool:
        """Delete a user's credential for a provider.

        Args:
            user_id: The user's ID
            provider: Service provider

        Returns:
            True if deleted, False if not found
        """

        def _delete(sess: Session) -> bool:
            cred = self.get_user_credential(user_id, provider, sess)
            if cred:
                sess.delete(cred)
                return True
            return False

        if session:
            return _delete(session)

        with self.db.get_session() as sess:
            result = _delete(sess)
            sess.commit()
            return result
