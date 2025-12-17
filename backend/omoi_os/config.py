"""Configuration settings for OmoiOS"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar, Dict, Mapping, MutableMapping, Optional

from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


logger = logging.getLogger(__name__)
CONFIG_ROOT = Path("config")
ENVIRONMENT_VARIABLE = "OMOIOS_ENV"
DEFAULT_ENVIRONMENT = "local"


def get_env_files():
    """Get environment files in priority order: .env.local, .env."""
    # Pydantic Settings supports list for multiple env files (higher index = higher priority)
    # Priority order: .env.local (highest), .env
    env_files = []
    if os.path.exists(".env"):
        env_files.append(".env")
    if os.path.exists(".env.local"):
        env_files.append(".env.local")
    # Return list if files exist, None otherwise (pydantic-settings accepts list or str)
    return env_files if env_files else None


def _merge_mappings(
    base: MutableMapping[str, Any], override: Mapping[str, Any]
) -> MutableMapping[str, Any]:
    for key, value in override.items():
        base_value = base.get(key)
        if isinstance(base_value, MutableMapping) and isinstance(value, Mapping):
            base[key] = _merge_mappings(dict(base_value), value)
            continue
        base[key] = value
    return base


def _yaml_layers(env_name: str) -> list[Path]:
    layers: list[Path] = []
    base_path = CONFIG_ROOT / "base.yaml"
    if base_path.exists():
        layers.append(base_path)

    env_path = CONFIG_ROOT / f"{env_name}.yaml"
    if env_path.exists():
        layers.append(env_path)
    return layers


def _read_yaml(path: Path) -> Dict[str, Any]:
    if yaml is None or not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        logger.warning("Ignoring YAML config at %s; expected mapping", path)
        return {}
    return data


@lru_cache(maxsize=8)
def _load_yaml_config(env_name: Optional[str] = None) -> Dict[str, Any]:
    if yaml is None:
        logger.debug("PyYAML not available; skipping YAML config load")
        return {}
    resolved_env = env_name or os.getenv(ENVIRONMENT_VARIABLE, DEFAULT_ENVIRONMENT)
    config: Dict[str, Any] = {}
    for layer in _yaml_layers(resolved_env):
        layer_data = _read_yaml(layer)
        if layer_data:
            config = dict(_merge_mappings(config, layer_data))
    return config


def load_yaml_section(section: str, env_name: Optional[str] = None) -> Dict[str, Any]:
    config = _load_yaml_config(env_name)
    section_data = config.get(section, {})
    return section_data if isinstance(section_data, dict) else {}


class OmoiBaseSettings(BaseSettings):
    yaml_section: ClassVar[Optional[str]] = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        sources: list[PydanticBaseSettingsSource] = [
            init_settings,
            env_settings,
            dotenv_settings,  # Include .env file loading
            file_secret_settings,
        ]
        if cls.yaml_section:
            sources.append(
                YamlSectionSettingsSource(settings_cls, section=cls.yaml_section)
            )
        return tuple(sources)


class YamlSectionSettingsSource(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings], section: str):
        super().__init__(settings_cls=settings_cls)
        self.section = section
        self._cache: Optional[Dict[str, Any]] = None

    def get_field_value(
        self,
        field: FieldInfo,
        field_name: str,
    ) -> tuple[Any, str, bool]:
        data = self._data()
        key = field.alias or field_name
        return data.get(key), field_name, False

    def __call__(self) -> Dict[str, Any]:
        return dict(self._data())

    def _data(self) -> Dict[str, Any]:
        if self._cache is None:
            self._cache = load_yaml_section(self.section)
        return self._cache


class LLMSettings(OmoiBaseSettings):
    """
    Loads LLM_* environment variables:
      - LLM_MODEL
      - LLM_API_KEY
      - LLM_BASE_URL (optional)

    Precedence: YAML defaults (config/base.yaml + config/<env>.yaml) < environment variables < init kwargs.
    """

    yaml_section = "llm"
    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        extra="ignore",  # Ignore extra fields like FIREWORKS_API_KEY
    )

    model: str = "openhands/claude-sonnet-4-5-20250929"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    fireworks_api_key: Optional[str] = None


class AnthropicSettings(OmoiBaseSettings):
    """
    Anthropic / Z.AI API configuration for Claude Agent SDK.

    Loads ANTHROPIC_* environment variables:
      - ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN)
      - ANTHROPIC_BASE_URL (custom API endpoint, e.g., Z.AI)
      - ANTHROPIC_MODEL (default model to use)
      - ANTHROPIC_MAX_TOKENS (max output tokens per response)
      - ANTHROPIC_CONTEXT_LENGTH (model context window size)
      - ANTHROPIC_DEFAULT_HAIKU_MODEL
      - ANTHROPIC_DEFAULT_SONNET_MODEL
      - ANTHROPIC_DEFAULT_OPUS_MODEL

    Default Configuration (Z.AI / GLM-4.6v):
      - GLM-4.6v has 128k context length
      - GLM-4.6v-flash is the fast/cheap variant

    Precedence: YAML defaults < environment variables < init kwargs.
    """

    yaml_section = "anthropic"
    model_config = SettingsConfigDict(
        env_prefix="ANTHROPIC_",
        extra="ignore",
    )

    # API credentials
    api_key: Optional[str] = None
    auth_token: Optional[str] = None  # Alternative to api_key (Z.AI uses this)
    base_url: str = "https://api.z.ai/api/anthropic"  # Default to Z.AI

    # Model configuration
    model: str = "glm-4.6v"  # Default model
    default_model: str = "glm-4.6v"
    default_haiku_model: str = "glm-4.6v-flash"
    default_sonnet_model: str = "glm-4.6v"
    default_opus_model: str = "glm-4.6v"

    # Token limits
    max_tokens: int = 16384  # Max output tokens per response
    context_length: int = 128000  # GLM-4.6v context window (128k)

    def get_api_key(self) -> Optional[str]:
        """Get API key, preferring api_key over auth_token."""
        return self.api_key or self.auth_token


class DatabaseSettings(OmoiBaseSettings):
    """
    Database configuration settings.

    Precedence: YAML defaults (config/base.yaml + config/<env>.yaml) < environment variables < init kwargs.
    """

    yaml_section = "database"
    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        extra="ignore",
    )

    url: str = "postgresql+psycopg://postgres:postgres@localhost:15432/app_db"


class RedisSettings(OmoiBaseSettings):
    """
    Redis configuration settings.

    Precedence: YAML defaults (config/base.yaml + config/<env>.yaml) < environment variables < init kwargs.
    """

    yaml_section = "redis"
    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        extra="ignore",
    )

    url: str = "redis://localhost:16379"


def load_llm_settings() -> LLMSettings:
    return get_app_settings().llm


def load_anthropic_settings() -> AnthropicSettings:
    return get_app_settings().anthropic


def load_database_settings() -> DatabaseSettings:
    return get_app_settings().database


def load_redis_settings() -> RedisSettings:
    return get_app_settings().redis


class TaskQueueSettings(OmoiBaseSettings):
    """
    Task queue configuration settings (REQ-TQM-PRI-002, REQ-TQM-PRI-003, REQ-TQM-PRI-004).

    Precedence: YAML defaults (config/base.yaml + config/<env>.yaml) < environment variables < init kwargs.
    """

    yaml_section = "task_queue"
    model_config = SettingsConfigDict(
        env_prefix="TQ_",
        extra="ignore",  # Ignore extra environment variables (e.g., LLM_* variables)
    )

    # Scoring parameters
    age_ceiling: int = 3600  # 1 hour in seconds (AGE_CEILING)
    sla_urgency_window: int = 900  # 15 minutes in seconds (SLA_URGENCY_WINDOW)
    starvation_limit: int = 7200  # 2 hours in seconds (STARVATION_LIMIT)
    blocker_ceiling: int = (
        10  # Maximum blocker count for normalization (BLOCKER_CEILING)
    )

    # Scoring weights (defaults per REQ-TQM-PRI-002)
    w_p: float = 0.45  # Priority weight
    w_a: float = 0.20  # Age weight
    w_d: float = 0.15  # Deadline weight
    w_b: float = 0.15  # Blocker weight
    w_r: float = 0.05  # Retry weight

    # Score modifiers
    sla_boost_multiplier: float = 1.25  # SLA boost multiplier (REQ-TQM-PRI-003)
    starvation_floor_score: float = (
        0.6  # Floor score for starved tasks (REQ-TQM-PRI-004)
    )


def load_task_queue_settings() -> TaskQueueSettings:
    return get_app_settings().task_queue


class ApprovalSettings(OmoiBaseSettings):
    """
    Ticket approval configuration settings (REQ-THA-002, REQ-THA-004).

    Precedence: YAML defaults (config/base.yaml + config/<env>.yaml) < environment variables < init kwargs.
    """

    yaml_section = "approval"
    model_config = SettingsConfigDict(
        env_prefix="APPROVAL_",
        extra="ignore",
    )

    ticket_human_review: bool = False  # Enable approval gate (REQ-THA-002)
    approval_timeout_seconds: int = (
        1800  # 30 minutes default (60-86400 range per REQ-THA-004)
    )
    on_reject: str = (
        "delete"  # Behavior for rejected tickets: "delete" or "archive" (REQ-THA-004)
    )


def load_approval_settings() -> ApprovalSettings:
    return get_app_settings().approval


class SupabaseSettings(OmoiBaseSettings):
    """
    Supabase configuration settings.

    Precedence: YAML defaults (config/base.yaml + config/<env>.yaml) < environment variables < init kwargs.
    """

    yaml_section = "supabase"
    model_config = SettingsConfigDict(
        env_prefix="SUPABASE_",
        extra="ignore",
    )

    url: Optional[str] = None  # SUPABASE_URL
    anon_key: Optional[str] = None  # SUPABASE_ANON_KEY (publishable key)
    service_role_key: Optional[str] = None  # SUPABASE_SERVICE_ROLE_KEY (secret key)

    # Database connection (optional, for direct PostgreSQL access)
    db_url: Optional[str] = None  # SUPABASE_DB_URL


class AuthSettings(OmoiBaseSettings):
    """
    Authentication and authorization settings.

    Precedence: YAML defaults (config/base.yaml + config/<env>.yaml) < environment variables < init kwargs.
    """

    yaml_section = "auth"
    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        env_file=get_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # JWT settings
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Password requirements
    min_password_length: int = 8
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special_char: bool = False

    # Rate limiting
    max_login_attempts: int = 5
    login_attempt_window_minutes: int = 15

    # Session settings
    session_expire_days: int = 30

    # OAuth provider credentials
    github_client_id: Optional[str] = None
    github_client_secret: Optional[str] = None
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    gitlab_client_id: Optional[str] = None
    gitlab_client_secret: Optional[str] = None
    gitlab_base_url: str = "https://gitlab.com"

    # OAuth redirect URI
    oauth_redirect_uri: str = "http://localhost:3000/callback"

    def get_provider_config(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get OAuth config for a provider."""
        configs: Dict[str, Dict[str, Any]] = {
            "github": {
                "client_id": self.github_client_id,
                "client_secret": self.github_client_secret,
            },
            "google": {
                "client_id": self.google_client_id,
                "client_secret": self.google_client_secret,
            },
            "gitlab": {
                "client_id": self.gitlab_client_id,
                "client_secret": self.gitlab_client_secret,
                "base_url": self.gitlab_base_url,
            },
        }
        config = configs.get(provider.lower())
        if config and config.get("client_id") and config.get("client_secret"):
            return config
        return None


class WorkspaceSettings(OmoiBaseSettings):
    """
    Workspace directory configuration for API and worker processes.
    """

    yaml_section = "workspace"
    model_config = SettingsConfigDict(
        env_prefix="WORKSPACE_",
        extra="ignore",
    )

    root: str = str(Path.cwd() / "workspaces")
    worker_dir: str = "/tmp/omoi_os_workspaces"

    # Workspace mode: "local", "docker", "remote"
    mode: str = "local"

    # Docker workspace settings (only used when mode="docker")
    docker_base_image: Optional[str] = "nikolaik/python-nodejs:python3.12-nodejs22"
    docker_server_image: Optional[str] = "ghcr.io/openhands/agent-server:latest"

    # Remote workspace settings (only used when mode="remote")
    remote_host: Optional[str] = None
    remote_api_key: Optional[str] = None


class MonitoringSettings(OmoiBaseSettings):
    """
    Intelligent monitoring loop configuration.
    """

    yaml_section = "monitoring"
    model_config = SettingsConfigDict(
        env_prefix="MONITORING_",
        extra="ignore",
    )

    # Master toggle for all monitoring loops
    # Set MONITORING_ENABLED=false to disable all background monitoring
    enabled: bool = True

    # Toggle for orchestrator loop (task assignment/sandbox spawning)
    # Set ORCHESTRATOR_ENABLED=false to disable the orchestrator
    orchestrator_enabled: bool = True

    guardian_interval_seconds: int = 60
    conductor_interval_seconds: int = 300
    health_check_interval_seconds: int = 30
    auto_steering_enabled: bool = False
    max_concurrent_analyses: int = 5


class DiagnosticSettings(OmoiBaseSettings):
    """
    Diagnostic agent system configuration.

    Precedence: YAML defaults (config/base.yaml + config/<env>.yaml) < environment variables < init kwargs.
    """

    yaml_section = "diagnostic"
    model_config = SettingsConfigDict(
        env_prefix="DIAGNOSTIC_",
        extra="ignore",
    )

    enabled: bool = True
    cooldown_seconds: int = 60
    min_stuck_time_seconds: int = 60
    max_agents_to_analyze: int = 15
    max_conductor_analyses: int = 5
    max_tasks_per_run: int = 5


class WorkerSettings(OmoiBaseSettings):
    """
    Worker runtime configuration.
    """

    yaml_section = "worker"
    model_config = SettingsConfigDict(
        env_prefix="WORKER_",
        extra="ignore",
    )

    concurrency: int = 2


class DaytonaSettings(OmoiBaseSettings):
    """
    Daytona Cloud sandbox configuration.

    Precedence: YAML defaults (config/base.yaml + config/<env>.yaml) < environment variables < init kwargs.
    """

    yaml_section = "daytona"
    model_config = SettingsConfigDict(
        env_prefix="DAYTONA_",
        extra="ignore",
    )

    api_key: Optional[str] = None  # DAYTONA_API_KEY
    api_url: str = "https://app.daytona.io/api"  # DAYTONA_API_URL
    target: str = "us"  # DAYTONA_TARGET (us, eu)
    image: Optional[str] = None  # DAYTONA_IMAGE (custom Docker image)
    snapshot: str = "python:3.12"  # DAYTONA_SNAPSHOT (fallback language)
    timeout: int = 300  # DAYTONA_TIMEOUT (seconds)

    # Sandbox execution mode
    # When True: orchestrator spawns Daytona sandboxes per task
    # When False: legacy mode - workers poll for tasks
    sandbox_execution: bool = False  # DAYTONA_SANDBOX_EXECUTION


def load_daytona_settings() -> DaytonaSettings:
    return get_app_settings().daytona


class IntegrationSettings(OmoiBaseSettings):
    """
    External integration endpoints and tokens.
    """

    yaml_section = "integrations"
    model_config = SettingsConfigDict(
        env_prefix="INTEGRATIONS_",
        extra="ignore",
    )

    mcp_server_url: str = "http://localhost:18000/mcp"
    enable_mcp_tools: bool = True
    github_token: Optional[str] = None


class EmbeddingSettings(OmoiBaseSettings):
    """
    Embedding provider configuration.

    Supported providers:
    - "fireworks": Fireworks AI (default) - fast, affordable, OpenAI-compatible
    - "openai": OpenAI embeddings
    - "local": Local FastEmbed model (slow startup, no API costs)
    """

    yaml_section = "embedding"
    model_config = SettingsConfigDict(
        env_prefix="EMBEDDING_",
        extra="ignore",
    )

    # Provider configuration
    provider: str = "fireworks"  # "fireworks", "openai", or "local"

    # API keys (set via env vars: EMBEDDING_FIREWORKS_API_KEY, EMBEDDING_OPENAI_API_KEY)
    fireworks_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # Model name (provider-specific defaults applied if not set)
    # Fireworks: "fireworks/qwen3-embedding-8b"
    # OpenAI: "text-embedding-3-small"
    # Local: "intfloat/multilingual-e5-large"
    model_name: Optional[str] = None

    # Output dimensions (None = use model default)
    dimensions: Optional[int] = None

    # Local model optimization (only applies when provider="local")
    cache_dir: Optional[str] = None  # Defaults to ~/.cache/fastembed if None
    lazy_load: bool = True  # Defer model loading until first use
    preload_in_background: bool = False  # Preload model in background thread at startup


class ObservabilitySettings(OmoiBaseSettings):
    """
    Telemetry and tracing configuration.
    """

    yaml_section = "observability"
    model_config = SettingsConfigDict(
        env_prefix="OBSERVABILITY_",
        extra="ignore",
    )

    enable_tracing: bool = False
    logfire_token: Optional[str] = None


class DemoSettings(OmoiBaseSettings):
    """
    Developer demo / CLI example configuration.
    """

    yaml_section = "demo"
    model_config = SettingsConfigDict(
        env_prefix="DEMO_",
        extra="ignore",
    )

    sdk_example: str = "activate_skill"
    persistence_dir: str = ".conversations"
    add_security_analyzer: bool = False
    confirm_all: bool = True


def load_supabase_settings() -> SupabaseSettings:
    return get_app_settings().supabase


def load_auth_settings() -> AuthSettings:
    return get_app_settings().auth


def load_workspace_settings() -> WorkspaceSettings:
    return get_app_settings().workspace


class AppSettings:
    def __init__(self) -> None:
        self.llm = LLMSettings()
        self.anthropic = AnthropicSettings()
        self.database = DatabaseSettings()
        self.redis = RedisSettings()
        self.task_queue = TaskQueueSettings()
        self.approval = ApprovalSettings()
        self.supabase = SupabaseSettings()
        self.auth = AuthSettings()
        self.workspace = WorkspaceSettings()
        self.monitoring = MonitoringSettings()
        self.diagnostic = DiagnosticSettings()
        self.worker = WorkerSettings()
        self.daytona = DaytonaSettings()
        self.integrations = IntegrationSettings()
        self.embedding = EmbeddingSettings()
        self.observability = ObservabilitySettings()
        self.demo = DemoSettings()

    @property
    def database_url(self) -> str:
        return self.database.url

    @property
    def redis_url(self) -> str:
        return self.redis.url


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    return AppSettings()


def reload_app_settings() -> AppSettings:
    _load_yaml_config.cache_clear()
    get_app_settings.cache_clear()
    app_settings = get_app_settings()
    global settings  # type: ignore[global-variable-not-assigned]
    settings = app_settings.auth
    return app_settings


settings = get_app_settings().auth
