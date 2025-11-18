"""Validation system configuration (REQ-VAL-Config)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class ValidationConfig(BaseSettings):
    """Validation system configuration matching REQ-VAL-Config.

    Parameters:
        enabled_by_default: Enable validation for new tasks (default: false)
        max_iterations: Maximum validation loops per task (default: 10, range: 1-50)
        iteration_timeout_minutes: Timeout for a single iteration (default: 30, range: 1-240)
        validator_timeout_minutes: Timeout for validator agent work (default: 10, range: 1-120)
        keep_failed_iterations: Preserve failed review records (default: true)
        auto_create_followups: Auto-create fix tasks when failed (default: true)
        DIAG_ON_VALIDATION_FAILURES: Enable diagnosis on repeated fails (default: true)
        DIAG_VALIDATION_FAILURES_THRESHOLD: Consecutive failures before spawn (default: 2, range: 1-10)
        DIAG_ON_VALIDATION_TIMEOUT: Enable diagnosis on validation timeout (default: true)
    """

    model_config = SettingsConfigDict(
        env_prefix="VALIDATION_",
        env_file=(".env",),
        env_file_encoding="utf-8",
    )

    enabled_by_default: bool = False
    max_iterations: int = 10  # Range: 1-50
    iteration_timeout_minutes: int = 30  # Range: 1-240
    validator_timeout_minutes: int = 10  # Range: 1-120
    keep_failed_iterations: bool = True
    auto_create_followups: bool = True

    # Diagnosis integration
    DIAG_ON_VALIDATION_FAILURES: bool = True
    DIAG_VALIDATION_FAILURES_THRESHOLD: int = 2  # Range: 1-10
    DIAG_ON_VALIDATION_TIMEOUT: bool = True
