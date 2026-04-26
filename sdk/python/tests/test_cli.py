"""Tests for the `omoios` CLI surface.

Covers the wiring (Click invocation tree, env-var resolution, JSON
output, stub commands raise the expected error). Real network calls
are mocked at the SDK boundary so the suite runs offline.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from omoios.cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# ─── help + version ──────────────────────────────────────────────────────────


class TestRootHelp:
    def test_help_lists_subcommands(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        for cmd in ("providers", "auth", "signup"):
            assert cmd in result.output

    def test_providers_help_lists_actions(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["providers", "--help"])
        assert result.exit_code == 0
        for action in ("list", "add", "delete"):
            assert action in result.output


# ─── stubs raise a clean error, not a crash ──────────────────────────────────


class TestStubs:
    def test_auth_github_is_a_clean_error(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["auth", "github"])
        assert result.exit_code == 1
        assert "not implemented yet" in result.output

    def test_signup_is_a_clean_error(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["signup"])
        assert result.exit_code == 1
        assert "not implemented yet" in result.output


# ─── providers list — env-var auth + JSON path ───────────────────────────────


class TestProvidersList:
    def test_missing_creds_is_clean_error(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OMOIOS_API_BASE_URL", raising=False)
        monkeypatch.delenv("OMOIOS_PLATFORM_API_KEY", raising=False)
        monkeypatch.delenv("OMOIOS_API_KEY", raising=False)
        # Point the XDG dir at an empty tmp so no real ~/.config file leaks in.
        monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/omoios-test-empty")
        result = runner.invoke(
            cli, ["providers", "list", "--workspace", "ws-1"]
        )
        assert result.exit_code == 1
        assert "OMOIOS_API_BASE_URL" in result.output

    def test_list_invokes_sdk_with_correct_args(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OMOIOS_API_BASE_URL", "https://api.test")
        monkeypatch.setenv("OMOIOS_PLATFORM_API_KEY", "test-key")
        with patch(
            "omoios.cli.providers._list", AsyncMock(return_value=[])
        ) as mocked:
            result = runner.invoke(
                cli, ["providers", "list", "--workspace", "ws-1"]
            )
        assert result.exit_code == 0
        mocked.assert_awaited_once_with("https://api.test", "test-key", "ws-1")
        assert "No credentials" in result.output

    def test_list_json_emits_dict_array(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import json as _json
        from types import SimpleNamespace

        monkeypatch.setenv("OMOIOS_API_BASE_URL", "https://api.test")
        monkeypatch.setenv("OMOIOS_PLATFORM_API_KEY", "test-key")

        kind = SimpleNamespace(value="bearer_secret")
        fake = SimpleNamespace(
            id="cred-1",
            name="fireworks",
            kind=kind,
            workspace_id="ws-1",
        )
        with patch("omoios.cli.providers._list", AsyncMock(return_value=[fake])):
            result = runner.invoke(
                cli,
                ["providers", "list", "--workspace", "ws-1", "--json"],
            )
        assert result.exit_code == 0
        parsed = _json.loads(result.output)
        assert parsed == [
            {
                "id": "cred-1",
                "name": "fireworks",
                "kind": "bearer_secret",
                "workspace_id": "ws-1",
            }
        ]


# ─── providers add — secret resolution ───────────────────────────────────────


class TestProvidersAdd:
    def test_add_uses_env_for_secret_when_flag_omitted(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from types import SimpleNamespace

        monkeypatch.setenv("OMOIOS_API_BASE_URL", "https://api.test")
        monkeypatch.setenv("OMOIOS_PLATFORM_API_KEY", "test-key")
        monkeypatch.setenv("OMOIOS_PROVIDER_KEY", "fw-secret")
        kind = SimpleNamespace(value="bearer_secret")
        created = SimpleNamespace(id="cred-9", name="fw", kind=kind)
        with patch(
            "omoios.cli.providers._add", AsyncMock(return_value=created)
        ) as mocked:
            result = runner.invoke(
                cli,
                [
                    "providers",
                    "add",
                    "--workspace",
                    "ws-1",
                    "--name",
                    "fw",
                ],
            )
        assert result.exit_code == 0, result.output
        # Verify the secret came from the env, not a hardcoded literal.
        call_kwargs = mocked.await_args.kwargs
        assert call_kwargs["value"] == "fw-secret"
        assert call_kwargs["workspace_id"] == "ws-1"
        assert call_kwargs["name"] == "fw"
        assert call_kwargs["kind"] == "bearer_secret"
        assert "cred-9" in result.output

    def test_add_without_secret_anywhere_fails_cleanly(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OMOIOS_API_BASE_URL", "https://api.test")
        monkeypatch.setenv("OMOIOS_PLATFORM_API_KEY", "test-key")
        monkeypatch.delenv("OMOIOS_PROVIDER_KEY", raising=False)
        result = runner.invoke(
            cli,
            ["providers", "add", "--workspace", "ws-1", "--name", "fw"],
        )
        assert result.exit_code == 1
        assert "OMOIOS_PROVIDER_KEY" in result.output
