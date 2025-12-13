"""User credentials service for managing external API keys.

This service handles CRUD operations for user credentials and provides
methods for the spawner to fetch credentials when spawning sandboxes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from omoi_os.config import load_anthropic_settings
from omoi_os.models.user_credentials import UserCredential
from omoi_os.services.database import DatabaseService

logger = logging.getLogger(__name__)


@dataclass
class AnthropicCredentials:
    """Container for Anthropic API credentials."""

    api_key: str
    base_url: Optional[str] = None
    model: Optional[str] = None
    default_model: Optional[str] = None
    default_haiku_model: Optional[str] = None
    default_sonnet_model: Optional[str] = None
    default_opus_model: Optional[str] = None
    source: str = "config"  # "config" or "user"


class CredentialsService:
    """Service for managing user credentials.

    Provides methods to:
    - Get user credentials for a specific provider
    - Get Anthropic credentials (user-specific or fallback to config)
    - Save/update user credentials
    """

    def __init__(self, db: DatabaseService):
        self.db = db

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
            source="config",
        )

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
