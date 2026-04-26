"""Tests for the `omoios` Cyclopts CLI surface.

Covers help / version output, env-var auth resolution, JSON emission,
secret resolution from $OMOIOS_PROVIDER_KEY, the GitHub device-code
flow, and signup. Real network calls are mocked at the SDK + httpx
boundary so the suite runs offline.
"""

from __future__ import annotations

import json as _json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from omoios.cli.main import app
from omoios.cli._ui import CliError


# ─── tiny harness ────────────────────────────────────────────────────────────


def invoke(*tokens: str) -> int:
    """Run the cyclopts app with a token list and return the exit code.

    Goes through `app.meta` to exercise the launcher (matches the real
    `main()` entry point). `--no-tips` is appended so the random tip
    line never appears in stdout/stderr during tests.
    """
    try:
        app.meta(list(tokens) + ["--no-tips"])
        return 0
    except CliError:
        return 1
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0


# ─── help + version ──────────────────────────────────────────────────────────


class TestRootHelp:
    def test_root_help_lists_subcommands(self, capsys: pytest.CaptureFixture) -> None:
        try:
            app(["--help"])
        except SystemExit:
            pass
        out = capsys.readouterr().out
        for cmd in ("providers", "auth", "signup"):
            assert cmd in out

    def test_providers_help_lists_actions(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        try:
            app(["providers", "--help"])
        except SystemExit:
            pass
        out = capsys.readouterr().out
        for action in ("list", "add", "delete"):
            assert action in out


# ─── auth github (device-code flow, HTTP mocked) ─────────────────────────────


class TestAuthGitHub:
    def test_device_flow_writes_token_to_config(
        self,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        device_resp = SimpleNamespace(
            status_code=200,
            content=b"{}",
            text="",
            json=lambda: {
                "device_code": "DEV",
                "user_code": "ABCD-1234",
                "verification_uri": "https://github.com/login/device",
                "interval": 0,
                "expires_in": 60,
            },
        )
        token_resp_pending = SimpleNamespace(
            content=b"{}",
            json=lambda: {"error": "authorization_pending"},
        )
        token_resp_ok = SimpleNamespace(
            content=b"{}",
            json=lambda: {
                "access_token": "ghs_test_token",
                "scope": "repo,read:user",
            },
        )

        calls = {"n": 0}

        def fake_post(self, url, **kwargs):
            if "device/code" in url:
                return device_resp
            calls["n"] += 1
            return token_resp_pending if calls["n"] == 1 else token_resp_ok

        monkeypatch.setattr("httpx.Client.post", fake_post, raising=True)
        monkeypatch.setattr("webbrowser.open", lambda *_a, **_kw: None)

        rc = invoke("auth", "github", "--no-browser")
        assert rc == 0
        out = capsys.readouterr().out
        assert "ABCD-1234" in out
        assert "GitHub token saved" in out

        cfg = _json.loads((tmp_path / "omoios" / "config.json").read_text())
        assert cfg["github_token"] == "ghs_test_token"


# ─── signup (HTTP mocked) ────────────────────────────────────────────────────


class TestSignup:
    def test_signup_registers_logs_in_and_writes_config(
        self,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        def make_resp(status, body):
            return SimpleNamespace(
                status_code=status,
                text="",
                content=b"{}",
                json=lambda _b=body: _b,
            )

        def fake_post(self, url, **kwargs):
            if url.endswith("/auth/register"):
                return make_resp(201, {"id": "user-1"})
            if url.endswith("/auth/login"):
                return make_resp(200, {"access_token": "jwt-abc"})
            if url.endswith("/organizations"):
                return make_resp(201, {"id": "org-1"})
            if url.endswith("/auth/api-keys"):
                return make_resp(201, {"key": "omk_test", "user_id": "user-1"})
            raise AssertionError(f"unexpected POST to {url}")

        def fake_get(self, url, **kwargs):
            if url.endswith("/organizations"):
                return make_resp(200, [])
            raise AssertionError(f"unexpected GET to {url}")

        monkeypatch.setattr("httpx.Client.post", fake_post, raising=True)
        monkeypatch.setattr("httpx.Client.get", fake_get, raising=True)

        rc = invoke(
            "signup",
            "--api-base-url", "https://api.test",
            "--email", "new@example.com",
            "--password", "Pa55word!",  # pragma: allowlist secret
            "--full-name", "New User",
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "registered" in out and "new@example.com" in out
        assert "minted api key" in out

        cfg = _json.loads((tmp_path / "omoios" / "config.json").read_text())
        assert cfg["api_key"] == "omk_test"  # pragma: allowlist secret
        assert cfg["api_base_url"] == "https://api.test"
        assert cfg["user_id"] == "user-1"


# ─── providers list — env-var auth + JSON path ───────────────────────────────


class TestProvidersList:
    def test_missing_creds_is_clean_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OMOIOS_API_BASE_URL", raising=False)
        monkeypatch.delenv("OMOIOS_PLATFORM_API_KEY", raising=False)
        monkeypatch.delenv("OMOIOS_API_KEY", raising=False)
        monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/omoios-test-empty")

        rc = invoke("providers", "list", "--workspace", "ws-1")
        assert rc == 1

    def test_list_invokes_sdk_with_correct_args(
        self,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OMOIOS_API_BASE_URL", "https://api.test")
        monkeypatch.setenv("OMOIOS_PLATFORM_API_KEY", "test-key")

        with patch(
            "omoios.cli.providers._list", AsyncMock(return_value=[])
        ) as mocked:
            rc = invoke("providers", "list", "--workspace", "ws-1")
        assert rc == 0
        mocked.assert_awaited_once_with("https://api.test", "test-key", "ws-1")
        assert "No credentials" in capsys.readouterr().out

    def test_list_json_emits_dict_array(
        self,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
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
            rc = invoke("providers", "list", "--workspace", "ws-1", "--json")
        assert rc == 0

        out = capsys.readouterr().out
        # Strip rich's pretty-print decoration to find the JSON payload.
        # `print_json` always emits valid JSON on its own line(s).
        parsed = _json.loads(out.strip())
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
        self,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OMOIOS_API_BASE_URL", "https://api.test")
        monkeypatch.setenv("OMOIOS_PLATFORM_API_KEY", "test-key")
        monkeypatch.setenv("OMOIOS_PROVIDER_KEY", "fw-secret")

        kind = SimpleNamespace(value="bearer_secret")
        created = SimpleNamespace(id="cred-9", name="fw", kind=kind)
        with patch(
            "omoios.cli.providers._add", AsyncMock(return_value=created)
        ) as mocked:
            rc = invoke(
                "providers", "add",
                "--workspace", "ws-1",
                "--name", "fw",
            )
        assert rc == 0
        kwargs = mocked.await_args.kwargs
        assert kwargs["value"] == "fw-secret"
        assert kwargs["workspace_id"] == "ws-1"
        assert kwargs["name"] == "fw"
        assert kwargs["kind"] == "bearer_secret"
        assert "cred-9" in capsys.readouterr().out

    def test_add_without_secret_anywhere_fails_cleanly(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OMOIOS_API_BASE_URL", "https://api.test")
        monkeypatch.setenv("OMOIOS_PLATFORM_API_KEY", "test-key")
        monkeypatch.delenv("OMOIOS_PROVIDER_KEY", raising=False)

        rc = invoke(
            "providers", "add", "--workspace", "ws-1", "--name", "fw"
        )
        assert rc == 1

    def test_invalid_kind_is_rejected_by_cyclopts(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OMOIOS_API_BASE_URL", "https://api.test")
        monkeypatch.setenv("OMOIOS_PLATFORM_API_KEY", "test-key")
        monkeypatch.setenv("OMOIOS_PROVIDER_KEY", "fw-secret")
        # Cyclopts raises SystemExit on validation failure; invoke() returns
        # the non-zero code from that.
        rc = invoke(
            "providers", "add",
            "--workspace", "ws-1",
            "--name", "fw",
            "--kind", "nope",
        )
        assert rc != 0


# ─── config + whoami ─────────────────────────────────────────────────────────


class TestConfig:
    def test_path_prints_resolved_location(
        self,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        rc = invoke("config", "path")
        assert rc == 0
        out = capsys.readouterr().out.strip()
        assert out.endswith("omoios/config.json")
        assert str(tmp_path) in out

    def test_show_masks_secrets_by_default(
        self,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path,
    ) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        cfg_dir = tmp_path / "omoios"
        cfg_dir.mkdir()
        (cfg_dir / "config.json").write_text(
            _json.dumps(
                {"api_base_url": "https://api.test", "api_key": "sk_secret_123"}  # pragma: allowlist secret
            )
        )
        rc = invoke("config", "show")
        assert rc == 0
        out = capsys.readouterr().out
        assert "redacted" in out
        assert "sk_secret_123" not in out  # pragma: allowlist secret


class TestWhoami:
    def test_whoami_prints_user_info(
        self,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OMOIOS_API_BASE_URL", "https://api.test")
        monkeypatch.setenv("OMOIOS_PLATFORM_API_KEY", "test-key")

        def fake_get(self, url, **kwargs):
            return SimpleNamespace(
                status_code=200,
                text="",
                json=lambda: {
                    "id": "u1",
                    "email": "kevin@example.com",
                    "full_name": "Kevin",
                },
            )

        monkeypatch.setattr("httpx.Client.get", fake_get, raising=True)
        rc = invoke("whoami")
        assert rc == 0
        out = capsys.readouterr().out
        assert "kevin@example.com" in out
        assert "u1" in out

    def test_whoami_401_includes_signup_hint(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setenv("OMOIOS_API_BASE_URL", "https://api.test")
        monkeypatch.setenv("OMOIOS_PLATFORM_API_KEY", "stale-key")

        def fake_get(self, url, **kwargs):
            return SimpleNamespace(status_code=401, text="bad", json=lambda: {})

        monkeypatch.setattr("httpx.Client.get", fake_get, raising=True)
        rc = invoke("whoami")
        assert rc == 1
