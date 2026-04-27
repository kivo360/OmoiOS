"""Unit tests for feature flags configuration."""

from omoi_os.config import (
    FeatureFlagsSettings,
    is_feature_enabled,
    load_feature_flags_settings,
)


class TestFeatureFlagsSettings:
    """Test FeatureFlagsSettings configuration class."""

    def test_all_flags_default_to_false(self):
        """All 6 feature flags should default to False."""
        settings = FeatureFlagsSettings()

        assert settings.sessions_api_v1 is False
        assert settings.environments_v1 is False
        assert settings.broker_enabled is False
        assert settings.egress_proxy_enabled is False
        assert settings.artifacts_unified_v1 is False
        assert settings.webhooks_enabled is False

    def test_individual_flag_access(self):
        """Should be able to access each flag individually."""
        settings = FeatureFlagsSettings()

        # Verify all flags are accessible and have correct type
        assert isinstance(settings.sessions_api_v1, bool)
        assert isinstance(settings.environments_v1, bool)
        assert isinstance(settings.broker_enabled, bool)
        assert isinstance(settings.egress_proxy_enabled, bool)
        assert isinstance(settings.artifacts_unified_v1, bool)
        assert isinstance(settings.webhooks_enabled, bool)

    def test_flag_can_be_enabled(self):
        """Flags can be explicitly enabled."""
        settings = FeatureFlagsSettings(
            sessions_api_v1=True,
            broker_enabled=True,
        )

        assert settings.sessions_api_v1 is True
        assert settings.broker_enabled is True
        # Other flags remain False
        assert settings.environments_v1 is False
        assert settings.egress_proxy_enabled is False
        assert settings.artifacts_unified_v1 is False
        assert settings.webhooks_enabled is False


class TestIsFeatureEnabled:
    """Test is_feature_enabled helper function."""

    def test_returns_false_for_all_flags_by_default(self):
        """is_feature_enabled should return False for all flags by default."""
        assert is_feature_enabled("sessions_api_v1") is False
        assert is_feature_enabled("environments_v1") is False
        assert is_feature_enabled("broker_enabled") is False
        assert is_feature_enabled("egress_proxy_enabled") is False
        assert is_feature_enabled("artifacts_unified_v1") is False
        assert is_feature_enabled("webhooks_enabled") is False

    def test_returns_false_for_unknown_flag(self):
        """is_feature_enabled should return False for unknown flags."""
        assert is_feature_enabled("unknown_flag") is False
        assert is_feature_enabled("nonexistent") is False


class TestLoadFeatureFlagsSettings:
    """Test load_feature_flags_settings helper function."""

    def test_returns_feature_flags_settings_instance(self):
        """Should return a FeatureFlagsSettings instance."""
        settings = load_feature_flags_settings()

        assert isinstance(settings, FeatureFlagsSettings)

    def test_returns_consistent_instance(self):
        """Should return consistent settings (cached)."""
        settings1 = load_feature_flags_settings()
        settings2 = load_feature_flags_settings()

        # Should be the same cached instance
        assert settings1 is settings2

    def test_loaded_settings_have_correct_defaults(self):
        """Loaded settings should have correct default values."""
        settings = load_feature_flags_settings()

        assert settings.sessions_api_v1 is False
        assert settings.environments_v1 is False
        assert settings.broker_enabled is False
        assert settings.egress_proxy_enabled is False
        assert settings.artifacts_unified_v1 is False
        assert settings.webhooks_enabled is False
