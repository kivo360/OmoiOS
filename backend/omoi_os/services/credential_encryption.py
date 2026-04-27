"""Credential encryption service using Fernet AES-256-GCM.

This service provides transparent encryption/decryption for provider API keys.
Uses Fernet from the cryptography library which provides:
- AES-128-CBC encryption (symmetric)
- HMAC-SHA256 authentication
- Timestamp validation support

Security notes:
- Encryption key must be 32 bytes (64 hex characters)
- Key is read from CREDENTIAL_ENCRYPTION_KEY environment variable
- No plaintext credentials are ever logged
- Service is fail-closed: operations fail if not configured
"""

from __future__ import annotations

import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from omoi_os.config import get_app_settings
from omoi_os.logging import get_logger

logger = get_logger(__name__)


class EncryptionError(Exception):
    """Raised when encryption/decryption operations fail."""

    pass


class CredentialEncryptionService:
    """Service for encrypting and decrypting provider API keys.

    Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).
    Provides transparent encryption at the service layer.

    Example:
        >>> service = CredentialEncryptionService(encryption_key="...")
        >>> encrypted = service.encrypt("example-plaintext")
        >>> decrypted = service.decrypt(encrypted)
        >>> assert decrypted == "example-plaintext"

    Security:
        - Never logs plaintext or encrypted values
        - Fails closed if not properly configured
        - Validates key format on initialization
    """

    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize the encryption service.

        Args:
            encryption_key: 32-byte hex-encoded key (64 hex characters).
                          If None, service will be unconfigured.

        Raises:
            EncryptionError: If key is invalid (wrong length, non-hex, etc.)
        """
        self._fernet: Optional[Fernet] = None
        self._key: Optional[str] = None

        if encryption_key is None:
            logger.debug("CredentialEncryptionService initialized without key")
            return

        # Validate key format
        self._validate_key(encryption_key)

        try:
            # Convert hex key to Fernet-compatible format
            # Fernet.generate_key() returns URL-safe base64-encoded 32-byte key
            # We need to convert our hex key to the same format
            import base64

            # Decode hex to bytes
            key_bytes = bytes.fromhex(encryption_key)
            # Encode to URL-safe base64 (Fernet format)
            fernet_key = base64.urlsafe_b64encode(key_bytes).decode("ascii")

            self._fernet = Fernet(fernet_key)
            self._key = encryption_key  # Store hex version for reference
            logger.info("CredentialEncryptionService initialized successfully")
        except Exception as e:
            raise EncryptionError(f"Failed to initialize encryption: {e}") from e

    def _validate_key(self, key: str) -> None:
        """Validate encryption key format.

        Args:
            key: Hex-encoded encryption key

        Raises:
            EncryptionError: If key is invalid
        """
        if not key:
            raise EncryptionError("Encryption key is empty")

        # Check length (64 hex chars = 32 bytes)
        if len(key) != 64:
            raise EncryptionError(
                f"Encryption key must be 32 bytes (64 hex characters), "
                f"got {len(key)} characters"
            )

        # Check hex format
        try:
            bytes.fromhex(key)
        except ValueError:
            raise EncryptionError("Encryption key must be valid hex-encoded bytes")

    @property
    def is_configured(self) -> bool:
        """Check if service is properly configured with a valid key."""
        return self._fernet is not None

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext value.

        Args:
            plaintext: Value to encrypt (e.g., API key)

        Returns:
            Encrypted value as URL-safe base64 string

        Raises:
            EncryptionError: If service not configured or encryption fails
        """
        if not self.is_configured:
            raise EncryptionError(
                "CredentialEncryptionService is not configured. "
                "Set CREDENTIAL_ENCRYPTION_KEY environment variable."
            )

        try:
            # Fernet.encrypt returns bytes, decode to string
            encrypted_bytes = self._fernet.encrypt(plaintext.encode("utf-8"))
            return encrypted_bytes.decode("ascii")
        except Exception as e:
            # Log error without exposing plaintext
            logger.error(f"Encryption failed: {type(e).__name__}")
            raise EncryptionError(f"Failed to encrypt value: {type(e).__name__}") from e

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext value.

        Args:
            ciphertext: Encrypted value (URL-safe base64 string)

        Returns:
            Decrypted plaintext value

        Raises:
            EncryptionError: If service not configured, token invalid,
                           or decryption fails
        """
        if not self.is_configured:
            raise EncryptionError(
                "CredentialEncryptionService is not configured. "
                "Set CREDENTIAL_ENCRYPTION_KEY environment variable."
            )

        try:
            # Fernet.decrypt returns bytes, decode to string
            decrypted_bytes = self._fernet.decrypt(ciphertext.encode("ascii"))
            return decrypted_bytes.decode("utf-8")
        except InvalidToken:
            logger.warning("Decryption failed: Invalid or tampered token")
            raise EncryptionError(
                "Failed to decrypt value: Invalid token or wrong encryption key"
            )
        except Exception as e:
            # Log error without exposing ciphertext
            logger.error(f"Decryption failed: {type(e).__name__}")
            raise EncryptionError(f"Failed to decrypt value: {type(e).__name__}") from e


# Global singleton instance
_encryption_service: Optional[CredentialEncryptionService] = None


def get_credential_encryption_service() -> CredentialEncryptionService:
    """Get the global encryption service instance (singleton pattern).

    Reads encryption key from:
    1. CREDENTIAL_ENCRYPTION_KEY environment variable
    2. Settings (if configured)

    Returns:
        CredentialEncryptionService instance

    Example:
        >>> from omoi_os.services.credential_encryption import get_credential_encryption_service
        >>> service = get_credential_encryption_service()
        >>> if service.is_configured:
        ...     encrypted = service.encrypt("secret")
    """
    global _encryption_service

    if _encryption_service is None:
        # Try to get key from environment or settings
        key = os.environ.get("CREDENTIAL_ENCRYPTION_KEY")

        if key is None:
            try:
                settings = get_app_settings()
                key = getattr(settings, "credential_encryption_key", None)
            except Exception:
                # Settings might not be available during early startup
                pass

        _encryption_service = CredentialEncryptionService(encryption_key=key)

    return _encryption_service


def reset_credential_encryption_service() -> None:
    """Reset the global encryption service instance.

    Useful for testing to ensure clean state between tests.
    """
    global _encryption_service
    _encryption_service = None
