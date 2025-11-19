"""Configuration settings for OmoiOS"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_files():
    """Get environment files in priority order for PydanticSettings.

    NOTE: PydanticSettings v2.12.0 seems to have reversed priority behavior
    compared to documentation. The first file in the list gets LOWEST priority,
    not HIGHEST priority as documented. So we reverse the order to work around this.

    Intended priority: .env.local (highest) > .env > environment variables
    Actual behavior: .env (highest) > .env.local > environment variables
    """
    # Workaround: Put .env first so it gets overridden by .env.local (backwards but works)
    env_files = []

    import os

    # Check for .env first (will be overridden by .env.local due to PydanticSettings bug)
    if os.path.exists(".env"):
        env_files.append(".env")

    # Then .env.local (will take priority due to reversed behavior)
    if os.path.exists(".env.local"):
        env_files.append(".env.local")

    return env_files if env_files else None


class LLMSettings(BaseSettings):
    """
    Loads LLM_* environment variables:
      - LLM_MODEL
      - LLM_API_KEY
      - LLM_BASE_URL (optional)

    Environment files priority: .env.local > .env > environment variables
    """

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=get_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields like FIREWORKS_API_KEY
    )

    model: str = "openhands/claude-sonnet-4-5-20250929"
    api_key: str
    base_url: Optional[str] = None


class DatabaseSettings(BaseSettings):
    """
    Database configuration settings.

    Environment files priority: .env.local > .env > environment variables
    """

    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        env_file=get_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: str = "postgresql+psycopg://postgres:postgres@localhost:15432/app_db"


class RedisSettings(BaseSettings):
    """
    Redis configuration settings.

    Environment files priority: .env.local > .env > environment variables
    """

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=get_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: str = "redis://localhost:16379"


def load_llm_settings() -> LLMSettings:
    return LLMSettings()


def load_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


def load_redis_settings() -> RedisSettings:
    return RedisSettings()


class TaskQueueSettings(BaseSettings):
    """
    Task queue configuration settings (REQ-TQM-PRI-002, REQ-TQM-PRI-003, REQ-TQM-PRI-004).

    Environment files priority: .env.local > .env > environment variables
    """

    model_config = SettingsConfigDict(
        env_prefix="TQ_",
        env_file=get_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra environment variables (e.g., LLM_* variables)
    )

    # Scoring parameters
    age_ceiling: int = 3600  # 1 hour in seconds (AGE_CEILING)
    sla_urgency_window: int = 900  # 15 minutes in seconds (SLA_URGENCY_WINDOW)
    starvation_limit: int = 7200  # 2 hours in seconds (STARVATION_LIMIT)
    blocker_ceiling: int = 10  # Maximum blocker count for normalization (BLOCKER_CEILING)

    # Scoring weights (defaults per REQ-TQM-PRI-002)
    w_p: float = 0.45  # Priority weight
    w_a: float = 0.20  # Age weight
    w_d: float = 0.15  # Deadline weight
    w_b: float = 0.15  # Blocker weight
    w_r: float = 0.05  # Retry weight

    # Score modifiers
    sla_boost_multiplier: float = 1.25  # SLA boost multiplier (REQ-TQM-PRI-003)
    starvation_floor_score: float = 0.6  # Floor score for starved tasks (REQ-TQM-PRI-004)


def load_task_queue_settings() -> TaskQueueSettings:
    return TaskQueueSettings()


class ApprovalSettings(BaseSettings):
    """
    Ticket approval configuration settings (REQ-THA-002, REQ-THA-004).

    Environment files priority: .env.local > .env > environment variables
    """

    model_config = SettingsConfigDict(
        env_prefix="APPROVAL_",
        env_file=get_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ticket_human_review: bool = False  # Enable approval gate (REQ-THA-002)
    approval_timeout_seconds: int = 1800  # 30 minutes default (60-86400 range per REQ-THA-004)
    on_reject: str = "delete"  # Behavior for rejected tickets: "delete" or "archive" (REQ-THA-004)


def load_approval_settings() -> ApprovalSettings:
    return ApprovalSettings()


class SupabaseSettings(BaseSettings):
    """
    Supabase configuration settings.

    Environment files priority: .env.local > .env > environment variables
    """

    model_config = SettingsConfigDict(
        env_prefix="SUPABASE_",
        env_file=get_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: str  # SUPABASE_URL
    anon_key: str  # SUPABASE_ANON_KEY (publishable key)
    service_role_key: str  # SUPABASE_SERVICE_ROLE_KEY (secret key)
    
    # Database connection (optional, for direct PostgreSQL access)
    db_url: Optional[str] = None  # SUPABASE_DB_URL


def load_supabase_settings() -> SupabaseSettings:
    return SupabaseSettings()
