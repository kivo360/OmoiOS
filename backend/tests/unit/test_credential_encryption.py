"""Unit tests for credential encryption service.

Tests Fernet AES-256-GCM encryption for provider API keys.
Security-critical: ensures no plaintext credentials in logs or errors.
"""

import os
import pytest
from unittest.mock import MagicMock, patch


from omoi_os.services.credential_encryption import (
    CredentialEncryptionService,
    get_credential_encryption_service,
    EncryptionError,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def valid_encryption_key() -> str:
    """Generate a valid 32-byte hex-encoded encryption key."""
    # Fernet.generate_key() returns URL-safe base64-encoded 32-byte key
    # For hex format (64 chars = 32 bytes), we generate random bytes
    return os.urandom(32).hex()


@pytest.fixture
def encryption_service(valid_encryption_key: str) -> CredentialEncryptionService:
    """Create an encryption service with a valid key."""
    return CredentialEncryptionService(encryption_key=valid_encryption_key)


# ============================================================================
# Tests: Key Validation
# ============================================================================


class TestKeyValidation:
    """Tests for encryption key validation."""

    def test_valid_32_byte_hex_key(self, valid_encryption_key: str):
        """Service accepts valid 32-byte hex-encoded key (64 hex chars)."""
        service = CredentialEncryptionService(encryption_key=valid_encryption_key)
        assert service.is_configured is True
        assert service._fernet is not None

    def test_valid_32_byte_raw_bytes(self):
        """Service accepts raw 32-byte bytes converted to hex."""
        raw_key = os.urandom(32)
        hex_key = raw_key.hex()
        service = CredentialEncryptionService(encryption_key=hex_key)
        assert service.is_configured is True

    def test_invalid_key_too_short(self):
        """Service raises error for key shorter than 32 bytes (64 hex chars)."""
        short_key = "aabbccdd" * 7  # 56 chars = 28 bytes
        with pytest.raises(EncryptionError) as exc_info:
            CredentialEncryptionService(encryption_key=short_key)
        assert "32 bytes" in str(exc_info.value)
        assert "56" in str(exc_info.value)  # Should report actual length

    def test_invalid_key_too_long(self):
        """Service raises error for key longer than 32 bytes."""
        long_key = "aabbccdd" * 9  # 72 chars = 36 bytes
        with pytest.raises(EncryptionError) as exc_info:
            CredentialEncryptionService(encryption_key=long_key)
        assert "32 bytes" in str(exc_info.value)
        assert "72" in str(exc_info.value)

    def test_invalid_key_non_hex(self):
        """Service raises error for non-hex key."""
        invalid_key = "not-a-valid-hex-key-!@#$%^&*()"
        with pytest.raises(EncryptionError) as exc_info:
            CredentialEncryptionService(encryption_key=invalid_key)
        assert "hex" in str(exc_info.value).lower()

    def test_empty_key(self):
        """Service raises error for empty key."""
        with pytest.raises(EncryptionError) as exc_info:
            CredentialEncryptionService(encryption_key="")
        assert "empty" in str(exc_info.value).lower() or "32 bytes" in str(
            exc_info.value
        )

    def test_none_key(self):
        """Service is not configured when key is None."""
        service = CredentialEncryptionService(encryption_key=None)
        assert service.is_configured is False
        assert service._fernet is None


# ============================================================================
# Tests: Encryption and Decryption
# ============================================================================


class TestEncryptionDecryption:
    """Tests for encrypt/decrypt operations."""

    def test_encrypt_decrypt_roundtrip(
        self, encryption_service: CredentialEncryptionService
    ):
        """Encrypt and decrypt returns original plaintext."""
        plaintext = "sk-test-api-key-12345"

        encrypted = encryption_service.encrypt(plaintext)
        assert encrypted != plaintext
        assert encrypted is not None
        assert len(encrypted) > 0

        decrypted = encryption_service.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_produces_different_output_each_time(
        self, encryption_service: CredentialEncryptionService
    ):
        """Same plaintext encrypts to different ciphertext each time (Fernet uses random IV)."""
        plaintext = "same-secret-key"

        encrypted1 = encryption_service.encrypt(plaintext)
        encrypted2 = encryption_service.encrypt(plaintext)

        assert encrypted1 != encrypted2
        # Both should decrypt to same value
        assert encryption_service.decrypt(encrypted1) == plaintext
        assert encryption_service.decrypt(encrypted2) == plaintext

    def test_encrypt_empty_string(
        self, encryption_service: CredentialEncryptionService
    ):
        """Empty string can be encrypted and decrypted."""
        plaintext = ""
        encrypted = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_unicode(self, encryption_service: CredentialEncryptionService):
        """Unicode characters can be encrypted and decrypted."""
        plaintext = "🔐 API Key: 密钥-123-测试"
        encrypted = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_long_value(self, encryption_service: CredentialEncryptionService):
        """Long values (4096+ chars) can be encrypted and decrypted."""
        plaintext = "x" * 4096
        encrypted = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(encrypted)
        assert decrypted == plaintext

    def test_decrypt_invalid_token(
        self, encryption_service: CredentialEncryptionService
    ):
        """Decrypting invalid token raises EncryptionError."""
        with pytest.raises(EncryptionError) as exc_info:
            encryption_service.decrypt("invalid-token-not-fernet")
        assert (
            "decrypt" in str(exc_info.value).lower()
            or "invalid" in str(exc_info.value).lower()
        )

    def test_decrypt_tampered_token(
        self, encryption_service: CredentialEncryptionService
    ):
        """Decrypting tampered token raises EncryptionError."""
        plaintext = "secret"
        encrypted = encryption_service.encrypt(plaintext)
        # Tamper with the encrypted value
        tampered = encrypted[:-10] + "XXXXXXXXXX"

        with pytest.raises(EncryptionError) as exc_info:
            encryption_service.decrypt(tampered)
        assert (
            "decrypt" in str(exc_info.value).lower()
            or "invalid" in str(exc_info.value).lower()
        )

    def test_decrypt_wrong_key(self, valid_encryption_key: str):
        """Decrypting with wrong key raises EncryptionError."""
        service1 = CredentialEncryptionService(encryption_key=valid_encryption_key)

        different_key = os.urandom(32).hex()
        service2 = CredentialEncryptionService(encryption_key=different_key)

        plaintext = "secret"
        encrypted = service1.encrypt(plaintext)

        with pytest.raises(EncryptionError):
            service2.decrypt(encrypted)


# ============================================================================
# Tests: Unconfigured Service Behavior
# ============================================================================


class TestUnconfiguredService:
    """Tests for service behavior when encryption is not configured."""

    def test_encrypt_when_not_configured(self):
        """Encrypt raises error when service is not configured."""
        service = CredentialEncryptionService(encryption_key=None)

        with pytest.raises(EncryptionError) as exc_info:
            service.encrypt("secret")
        assert "not configured" in str(exc_info.value).lower()

    def test_decrypt_when_not_configured(self):
        """Decrypt raises error when service is not configured."""
        service = CredentialEncryptionService(encryption_key=None)

        with pytest.raises(EncryptionError) as exc_info:
            service.decrypt("some-token")
        assert "not configured" in str(exc_info.value).lower()


# ============================================================================
# Tests: Singleton Pattern
# ============================================================================


class TestSingletonPattern:
    """Tests for get_credential_encryption_service singleton."""

    def setup_method(self):
        """Reset singleton before each test."""
        from omoi_os.services import credential_encryption

        credential_encryption._encryption_service = None

    def teardown_method(self):
        """Reset singleton after each test."""
        from omoi_os.services import credential_encryption

        credential_encryption._encryption_service = None

    @patch("omoi_os.services.credential_encryption.CredentialEncryptionService")
    def test_get_service_creates_singleton(self, mock_service_class):
        """get_credential_encryption_service creates service on first call."""
        mock_instance = MagicMock()
        mock_instance.is_configured = True
        mock_service_class.return_value = mock_instance

        # First call should create service
        service1 = get_credential_encryption_service()
        mock_service_class.assert_called_once()

        # Reset mock to verify second call doesn't recreate
        mock_service_class.reset_mock()

        # Second call should return same instance
        service2 = get_credential_encryption_service()
        mock_service_class.assert_not_called()
        assert service1 is service2

    @patch.dict(os.environ, {"CREDENTIAL_ENCRYPTION_KEY": "a" * 64})
    @patch("omoi_os.services.credential_encryption.CredentialEncryptionService")
    def test_get_service_uses_env_var(self, mock_service_class):
        """get_credential_encryption_service reads key from CREDENTIAL_ENCRYPTION_KEY env var."""
        mock_instance = MagicMock()
        mock_instance.is_configured = True
        mock_service_class.return_value = mock_instance

        get_credential_encryption_service()

        mock_service_class.assert_called_once_with(encryption_key="a" * 64)


# ============================================================================
# Tests: Security Requirements
# ============================================================================


class TestSecurityRequirements:
    """Security-critical tests ensuring no plaintext exposure."""

    def test_encrypted_output_not_equal_plaintext(
        self, encryption_service: CredentialEncryptionService
    ):
        """Encrypted output must never equal plaintext."""
        plaintext = "sk-live-12345"
        encrypted = encryption_service.encrypt(plaintext)

        assert encrypted != plaintext
        # Encrypted should be base64-like (Fernet format)
        assert isinstance(encrypted, str)
        assert len(encrypted) > len(plaintext)

    def test_no_plaintext_in_error_messages(
        self, encryption_service: CredentialEncryptionService
    ):
        """Error messages must not contain plaintext."""
        plaintext = "super-secret-api-key-12345"
        encrypted = encryption_service.encrypt(plaintext)

        # Tamper to cause decryption failure
        tampered = encrypted[:-5] + "XXXXX"

        try:
            encryption_service.decrypt(tampered)
        except EncryptionError as e:
            error_msg = str(e)
            # Plaintext should NOT appear in error
            assert plaintext not in error_msg
            # Encrypted value should NOT appear in error
            assert encrypted not in error_msg
            assert tampered not in error_msg

    def test_encrypt_returns_string(
        self, encryption_service: CredentialEncryptionService
    ):
        """Encrypt always returns string (not bytes)."""
        plaintext = "test-key"
        encrypted = encryption_service.encrypt(plaintext)
        assert isinstance(encrypted, str)

    def test_decrypt_returns_string(
        self, encryption_service: CredentialEncryptionService
    ):
        """Decrypt always returns string (not bytes)."""
        plaintext = "test-key"
        encrypted = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(encrypted)
        assert isinstance(decrypted, str)


# ============================================================================
# Tests: Integration with Settings
# ============================================================================


class TestSettingsIntegration:
    """Tests for integration with OmoiBaseSettings pattern."""

    @patch("omoi_os.services.credential_encryption.get_app_settings")
    def test_service_reads_from_settings(self, mock_get_settings):
        """Service reads encryption key from settings."""
        test_key = os.urandom(32).hex()

        mock_settings = MagicMock()
        mock_settings.credential_encryption_key = test_key
        mock_get_settings.return_value = mock_settings

        # Reset singleton
        from omoi_os.services import credential_encryption

        credential_encryption._encryption_service = None

        service = get_credential_encryption_service()

        # Verify it was configured with the key
        assert service.is_configured is True

    def test_service_handles_missing_settings(self):
        """Service handles missing settings gracefully."""
        # Reset singleton
        from omoi_os.services import credential_encryption

        credential_encryption._encryption_service = None

        # Patch get_app_settings to return None for the key
        with patch(
            "omoi_os.services.credential_encryption.get_app_settings"
        ) as mock_get:
            mock_settings = MagicMock()
            mock_settings.credential_encryption_key = None
            mock_get.return_value = mock_settings

            service = get_credential_encryption_service()
            assert service.is_configured is False
