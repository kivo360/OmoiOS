import textwrap
from pathlib import Path

import pytest

from omoi_os import config


def _write_yaml(path: Path, contents: str) -> None:
    path.write_text(textwrap.dedent(contents), encoding="utf-8")


def test_yaml_precedence_and_env_overrides(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CONFIG_ROOT", tmp_path)
    monkeypatch.setenv(config.ENVIRONMENT_VARIABLE, "testenv")
    for key in ("LLM_MODEL", "LLM_API_KEY", "LLM_BASE_URL"):
        monkeypatch.delenv(key, raising=False)
    _write_yaml(
        tmp_path / "base.yaml",
        """
        llm:
          model: base-model
          api_key: base-key
        database:
          url: base-db-url
        """,
    )
    _write_yaml(
        tmp_path / "testenv.yaml",
        """
        llm:
          model: env-model
        """,
    )
    monkeypatch.setenv("LLM_API_KEY", "env-api-key")
    config.reload_app_settings()
    settings = config.get_app_settings()
    assert settings.llm.model == "env-model"
    assert settings.llm.api_key == "env-api-key"
    assert settings.database.url == "base-db-url"


@pytest.mark.parametrize(
    "loader,attr",
    [
        (config.load_llm_settings, "llm"),
        (config.load_database_settings, "database"),
        (config.load_redis_settings, "redis"),
        (config.load_task_queue_settings, "task_queue"),
        (config.load_approval_settings, "approval"),
        (config.load_supabase_settings, "supabase"),
        (config.load_auth_settings, "auth"),
    ],
)
def test_helpers_return_singleton_slices(loader, attr):
    config.reload_app_settings()
    app_settings = config.get_app_settings()
    assert loader() is getattr(app_settings, attr)


def test_reload_updates_legacy_settings_reference(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CONFIG_ROOT", tmp_path)
    _write_yaml(
        tmp_path / "base.yaml",
        """
        auth:
          jwt_secret_key: new-secret
        """,
    )
    config.reload_app_settings()
    assert config.settings is config.get_app_settings().auth
    assert config.settings.jwt_secret_key == "new-secret"


def test_workspace_monitoring_and_related_sections(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CONFIG_ROOT", tmp_path)
    for key in (
        "WORKER_CONCURRENCY",
        "MONITORING_MAX_CONCURRENT_ANALYSES",
        "MONITORING_AUTO_STEERING_ENABLED",
    ):
        monkeypatch.delenv(key, raising=False)
    _write_yaml(
        tmp_path / "base.yaml",
        """
        workspace:
          root: /srv/workspaces
          worker_dir: /srv/workspaces/agents
        monitoring:
          guardian_interval_seconds: 45
          conductor_interval_seconds: 120
          health_check_interval_seconds: 15
          auto_steering_enabled: false
          max_concurrent_analyses: 3
        worker:
          concurrency: 4
        integrations:
          mcp_server_url: http://example.com/mcp
          enable_mcp_tools: false
        embedding:
          provider: openai
          openai_api_key: key-from-yaml
          model_name: text-embedding-custom
        observability:
          enable_tracing: true
          logfire_token: token-yaml
        demo:
          sdk_example: hello_world
          persistence_dir: ./tmp_conversations
          add_security_analyzer: true
          confirm_all: false
        """,
    )
    # Override a couple of values via env vars to ensure prefixes work
    monkeypatch.setenv("WORKER_CONCURRENCY", "7")
    monkeypatch.setenv("MONITORING_AUTO_STEERING_ENABLED", "true")
    monkeypatch.setenv("MONITORING_MAX_CONCURRENT_ANALYSES", "9")

    config.reload_app_settings()
    settings = config.get_app_settings()
    assert settings.workspace.root == "/srv/workspaces"
    assert settings.workspace.worker_dir == "/srv/workspaces/agents"
    assert settings.monitoring.guardian_interval_seconds == 45
    assert settings.monitoring.conductor_interval_seconds == 120
    assert settings.monitoring.auto_steering_enabled is True
    assert settings.monitoring.max_concurrent_analyses == 9
    assert settings.worker.concurrency == 7
    assert settings.integrations.enable_mcp_tools is False
    assert settings.embedding.provider == "openai"
    assert settings.embedding.model_name == "text-embedding-custom"
    assert settings.embedding.openai_api_key == "key-from-yaml"
    assert settings.observability.enable_tracing is True
    assert settings.observability.logfire_token == "token-yaml"
    assert settings.demo.sdk_example == "hello_world"
    assert settings.demo.add_security_analyzer is True
    assert settings.demo.confirm_all is False


def test_load_yaml_section_handles_missing_section(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CONFIG_ROOT", tmp_path)
    _write_yaml(tmp_path / "base.yaml", "llm: {model: foo}")
    config._load_yaml_config.cache_clear()
    data = config.load_yaml_section("nonexistent")
    assert data == {}

