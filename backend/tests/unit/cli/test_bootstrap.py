"""Test bootstrap CLI.

Tests cover:
- BootstrapChecker.check_all() returns valid report
- Individual check methods return correct status types
- Display formatting
- CLI argument parsing
"""

from __future__ import annotations

import argparse
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from omoi_os.cli.bootstrap import (
    BootstrapChecker,
    BootstrapReport,
    DependencyCheck,
    _status_icon,
    create_parser,
    display_report,
    main,
    main_async,
)


class TestDependencyCheck:
    """Test DependencyCheck dataclass."""

    def test_dependency_check_creation(self):
        """Test creating a DependencyCheck instance."""
        check = DependencyCheck(
            name="Python",
            status="ok",
            required=True,
            details="3.12.0",
            fix_command="",
            category="runtime",
        )
        assert check.name == "Python"
        assert check.status == "ok"
        assert check.required is True
        assert check.details == "3.12.0"
        assert check.category == "runtime"


class TestBootstrapReport:
    """Test BootstrapReport dataclass."""

    def test_empty_report(self):
        """Test empty report properties."""
        report = BootstrapReport()
        assert report.checks == []
        assert report.all_required_ok is True  # Empty = all ok
        assert report.has_warnings is False

    def test_all_required_ok_with_missing_required(self):
        """Test all_required_ok with missing required dependency."""
        report = BootstrapReport(
            checks=[
                DependencyCheck(
                    name="Python",
                    status="missing",
                    required=True,
                    details="Not found",
                    fix_command="install python",
                    category="runtime",
                ),
            ]
        )
        assert report.all_required_ok is False

    def test_all_required_ok_with_missing_optional(self):
        """Test all_required_ok with missing optional dependency."""
        report = BootstrapReport(
            checks=[
                DependencyCheck(
                    name="LLM Key",
                    status="not_configured",
                    required=False,
                    details="Not set",
                    fix_command="set env var",
                    category="config",
                ),
            ]
        )
        assert report.all_required_ok is True  # Optional missing is ok

    def test_has_warnings_with_optional_missing(self):
        """Test has_warnings with missing optional dependency."""
        report = BootstrapReport(
            checks=[
                DependencyCheck(
                    name="LLM Key",
                    status="not_configured",
                    required=False,
                    details="Not set",
                    fix_command="set env var",
                    category="config",
                ),
            ]
        )
        assert report.has_warnings is True

    def test_get_by_category(self):
        """Test filtering checks by category."""
        report = BootstrapReport(
            checks=[
                DependencyCheck(
                    name="Python",
                    status="ok",
                    required=True,
                    details="3.12.0",
                    fix_command="",
                    category="runtime",
                ),
                DependencyCheck(
                    name="Postgres",
                    status="ok",
                    required=True,
                    details="Running",
                    fix_command="",
                    category="database",
                ),
                DependencyCheck(
                    name="Redis",
                    status="ok",
                    required=True,
                    details="Running",
                    fix_command="",
                    category="database",
                ),
            ]
        )
        runtime_checks = report.get_by_category("runtime")
        assert len(runtime_checks) == 1
        assert runtime_checks[0].name == "Python"

        db_checks = report.get_by_category("database")
        assert len(db_checks) == 2

        config_checks = report.get_by_category("config")
        assert len(config_checks) == 0


class TestStatusIcon:
    """Test status icon selection."""

    def test_ok_status(self):
        """Test icon for ok status."""
        check = DependencyCheck(
            name="Test",
            status="ok",
            required=True,
            details="",
            fix_command="",
            category="runtime",
        )
        assert _status_icon(check) == "✅"

    def test_missing_required_status(self):
        """Test icon for missing required status."""
        check = DependencyCheck(
            name="Test",
            status="missing",
            required=True,
            details="",
            fix_command="",
            category="runtime",
        )
        assert _status_icon(check) == "❌"

    def test_missing_optional_status(self):
        """Test icon for missing optional status."""
        check = DependencyCheck(
            name="Test",
            status="missing",
            required=False,
            details="",
            fix_command="",
            category="runtime",
        )
        assert _status_icon(check) == "⚠️"

    def test_not_configured_status(self):
        """Test icon for not_configured status."""
        check = DependencyCheck(
            name="Test",
            status="not_configured",
            required=False,
            details="",
            fix_command="",
            category="config",
        )
        assert _status_icon(check) == "⚠️"

    def test_wrong_version_required_status(self):
        """Test icon for wrong_version required status."""
        check = DependencyCheck(
            name="Test",
            status="wrong_version",
            required=True,
            details="",
            fix_command="",
            category="runtime",
        )
        assert _status_icon(check) == "❌"


class TestBootstrapChecker:
    """Test BootstrapChecker class."""

    @pytest.mark.asyncio
    async def test_check_all_returns_report(self):
        """Test check_all returns a BootstrapReport."""
        checker = BootstrapChecker()
        report = await checker.check_all()
        assert isinstance(report, BootstrapReport)
        assert len(report.checks) > 0

    @pytest.mark.asyncio
    async def test_check_python_ok(self):
        """Test _check_python with valid Python version."""
        checker = BootstrapChecker()
        await checker._check_python()

        python_checks = [c for c in checker.report.checks if c.name == "Python"]
        assert len(python_checks) == 1
        assert python_checks[0].status in ("ok", "wrong_version")

    @pytest.mark.asyncio
    async def test_check_env_file_not_found(self, tmp_path, monkeypatch):
        """Test _check_env_file when no env file exists."""
        # Change to a temp directory with no .env files
        monkeypatch.chdir(tmp_path)

        checker = BootstrapChecker()
        await checker._check_env_file()

        env_checks = [c for c in checker.report.checks if c.name == ".env file"]
        assert len(env_checks) == 1
        assert env_checks[0].status == "not_configured"
        assert env_checks[0].required is False

    @pytest.mark.asyncio
    async def test_check_env_file_found(self, tmp_path, monkeypatch):
        """Test _check_env_file when .env exists."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text("TEST=value")

        checker = BootstrapChecker()
        await checker._check_env_file()

        env_checks = [c for c in checker.report.checks if c.name == ".env file"]
        assert len(env_checks) == 1
        assert env_checks[0].status == "ok"

    @pytest.mark.asyncio
    async def test_check_llm_key_with_mode_null(self, monkeypatch):
        """Test _check_llm_key when mode is null."""
        monkeypatch.setenv("LLM_MODE", "null")

        # Clear cached settings so the env override actually flows through —
        # without this, get_app_settings() returns whatever was loaded at
        # import time (mode="live") and the early-return at _check_llm_key:420
        # is never taken.
        from omoi_os.config import _load_yaml_config, get_app_settings

        get_app_settings.cache_clear()
        _load_yaml_config.cache_clear()

        try:
            checker = BootstrapChecker()
            await checker._check_llm_key()

            llm_checks = [c for c in checker.report.checks if c.name == "LLM API Key"]
            assert len(llm_checks) == 1
            # Should be ok because mode is null
            assert llm_checks[0].status == "ok"
        finally:
            get_app_settings.cache_clear()
            _load_yaml_config.cache_clear()

    @pytest.mark.asyncio
    async def test_check_llm_key_not_set(self, monkeypatch):
        """Test _check_llm_key when no key is set and mode is live."""
        monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        # Force live mode so the key check actually runs
        monkeypatch.setenv("OMOIOS_ENV", "test")

        # Clear cached settings so they reload with test env
        from omoi_os.config import get_app_settings, _load_yaml_config

        get_app_settings.cache_clear()
        _load_yaml_config.cache_clear()

        try:
            checker = BootstrapChecker()
            await checker._check_llm_key()

            llm_checks = [c for c in checker.report.checks if c.name == "LLM API Key"]
            assert len(llm_checks) == 1
            assert llm_checks[0].status == "not_configured"
        finally:
            # Restore cached settings
            get_app_settings.cache_clear()
            _load_yaml_config.cache_clear()

    @pytest.mark.asyncio
    async def test_check_llm_key_with_fireworks(self, monkeypatch):
        """Test _check_llm_key with FIREWORKS_API_KEY set."""
        monkeypatch.setenv("FIREWORKS_API_KEY", "test-key")

        checker = BootstrapChecker()
        await checker._check_llm_key()

        llm_checks = [c for c in checker.report.checks if c.name == "LLM API Key"]
        assert len(llm_checks) == 1
        assert llm_checks[0].status == "ok"

    @pytest.mark.asyncio
    async def test_check_github_token_not_set(self, monkeypatch):
        """Test _check_github_token when not set."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        checker = BootstrapChecker()
        await checker._check_github_token()

        github_checks = [c for c in checker.report.checks if c.name == "GitHub Token"]
        assert len(github_checks) == 1
        assert github_checks[0].status == "not_configured"
        assert github_checks[0].required is False

    @pytest.mark.asyncio
    async def test_check_github_token_set(self, monkeypatch):
        """Test _check_github_token when set."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")

        checker = BootstrapChecker()
        await checker._check_github_token()

        github_checks = [c for c in checker.report.checks if c.name == "GitHub Token"]
        assert len(github_checks) == 1
        assert github_checks[0].status == "ok"

    @pytest.mark.asyncio
    async def test_check_claude_key_not_set(self, monkeypatch):
        """Test _check_claude_key when not set."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)

        checker = BootstrapChecker()
        await checker._check_claude_key()

        claude_checks = [c for c in checker.report.checks if c.name == "Claude API Key"]
        assert len(claude_checks) == 1
        assert claude_checks[0].status == "not_configured"

    @pytest.mark.asyncio
    async def test_check_claude_key_with_oauth(self, monkeypatch):
        """Test _check_claude_key with CLAUDE_CODE_OAUTH_TOKEN."""
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "oauth_token")

        checker = BootstrapChecker()
        await checker._check_claude_key()

        claude_checks = [c for c in checker.report.checks if c.name == "Claude API Key"]
        assert len(claude_checks) == 1
        assert claude_checks[0].status == "ok"

    @pytest.mark.asyncio
    async def test_check_daytona_key_not_set(self, monkeypatch):
        """Test _check_daytona_key when not set."""
        monkeypatch.delenv("DAYTONA_API_KEY", raising=False)

        checker = BootstrapChecker()
        await checker._check_daytona_key()

        daytona_checks = [
            c for c in checker.report.checks if c.name == "Daytona API Key"
        ]
        assert len(daytona_checks) == 1
        assert daytona_checks[0].status == "not_configured"

    @pytest.mark.asyncio
    async def test_check_daytona_key_set(self, monkeypatch):
        """Test _check_daytona_key when set."""
        monkeypatch.setenv("DAYTONA_API_KEY", "daytona_test_key")

        checker = BootstrapChecker()
        await checker._check_daytona_key()

        daytona_checks = [
            c for c in checker.report.checks if c.name == "Daytona API Key"
        ]
        assert len(daytona_checks) == 1
        assert daytona_checks[0].status == "ok"

    @pytest.mark.asyncio
    async def test_run_command_success(self):
        """Test _run_command with successful execution."""
        checker = BootstrapChecker()
        returncode, stdout, stderr = await checker._run_command("echo", "hello")
        assert returncode == 0
        assert stdout == "hello"

    @pytest.mark.asyncio
    async def test_run_command_not_found(self):
        """Test _run_command with non-existent command."""
        checker = BootstrapChecker()
        returncode, stdout, stderr = await checker._run_command(
            "nonexistent_command_xyz"
        )
        assert returncode == 127
        assert "not found" in stderr.lower() or "not found" in stdout.lower()


class TestCreateParser:
    """Test CLI argument parser."""

    def test_parser_creation(self):
        """Test parser is created successfully."""
        parser = create_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_check_command(self):
        """Test check subcommand parsing."""
        parser = create_parser()
        args = parser.parse_args(["check"])
        assert args.command == "check"

    def test_check_command_with_json(self):
        """Test check subcommand with --json flag."""
        parser = create_parser()
        args = parser.parse_args(["check", "--json"])
        assert args.command == "check"
        assert args.json is True

    def test_health_command(self):
        """Test health subcommand parsing."""
        parser = create_parser()
        args = parser.parse_args(["health"])
        assert args.command == "health"

    def test_health_command_with_json(self):
        """Test health subcommand with --json flag."""
        parser = create_parser()
        args = parser.parse_args(["health", "--json"])
        assert args.command == "health"
        assert args.json is True

    def test_no_command_returns_none(self):
        """Test that no command returns None for command attribute."""
        parser = create_parser()
        # Parser itself doesn't raise SystemExit; main_async handles missing command
        args = parser.parse_args([])
        assert args.command is None


class TestDisplayReport:
    """Test report display function."""

    def test_display_successful_report(self, capsys):
        """Test displaying a successful report."""
        report = BootstrapReport(
            checks=[
                DependencyCheck(
                    name="Python",
                    status="ok",
                    required=True,
                    details="3.12.0",
                    fix_command="",
                    category="runtime",
                ),
            ]
        )
        display_report(report)
        captured = capsys.readouterr()
        assert "OmoiOS Dev Environment Check" in captured.out
        assert "✅ Python" in captured.out
        assert "Ready for local development" in captured.out

    def test_display_with_missing_required(self, capsys):
        """Test displaying a report with missing required dependency."""
        report = BootstrapReport(
            checks=[
                DependencyCheck(
                    name="Docker",
                    status="missing",
                    required=True,
                    details="Not installed",
                    fix_command="Install Docker",
                    category="runtime",
                ),
            ]
        )
        display_report(report)
        captured = capsys.readouterr()
        assert "❌ Docker" in captured.out
        assert "Missing required dependencies" in captured.out
        assert "Install Docker" in captured.out

    def test_display_with_warnings(self, capsys):
        """Test displaying a report with warnings."""
        report = BootstrapReport(
            checks=[
                DependencyCheck(
                    name="Python",
                    status="ok",
                    required=True,
                    details="3.12.0",
                    fix_command="",
                    category="runtime",
                ),
                DependencyCheck(
                    name="LLM Key",
                    status="not_configured",
                    required=False,
                    details="Not set",
                    fix_command="Set env var",
                    category="config",
                ),
            ]
        )
        display_report(report)
        captured = capsys.readouterr()
        # The icon and name are separated by single space in actual output
        assert "⚠️ LLM Key" in captured.out
        assert "Optional dependencies (warnings)" in captured.out


class TestMainAsync:
    """Test async main function."""

    @pytest.mark.asyncio
    async def test_main_no_args_returns_error(self, capsys):
        """Test main with no args shows help and returns error code."""
        result = await main_async([])
        assert result == 1
        captured = capsys.readouterr()
        assert "omoi-bootstrap" in captured.out or "Available commands" in captured.out

    @pytest.mark.asyncio
    async def test_main_check_command(self):
        """Test main with check command."""
        result = await main_async(["check"])
        assert result in (0, 1)  # Depends on environment

    @pytest.mark.asyncio
    async def test_main_health_command(self):
        """Test main with health command."""
        result = await main_async(["health"])
        assert result in (0, 1)  # Depends on environment

    @pytest.mark.asyncio
    async def test_main_check_json_output(self, capsys):
        """Test main with check --json outputs valid JSON."""
        import json

        await main_async(["check", "--json"])
        captured = capsys.readouterr()

        # Should be valid JSON
        data = json.loads(captured.out)
        assert "checks" in data
        assert "all_required_ok" in data
        assert "has_warnings" in data
        assert isinstance(data["checks"], list)


class TestMain:
    """Test main entry point."""

    def test_main_runs_async(self):
        """Test main runs the async version."""
        # Just verify it doesn't crash
        with patch.object(sys, "argv", ["bootstrap", "check"]):
            # Should complete without exception
            try:
                result = main(["check"])
                assert result in (0, 1)
            except Exception as e:
                # If it fails, it should be due to environment, not code
                pytest.fail(f"main() raised an exception: {e}")


class TestMockSubprocessScenarios:
    """Test BootstrapChecker with mocked subprocess calls."""

    @pytest.mark.asyncio
    async def test_check_node_success(self):
        """Test _check_node with successful node command."""
        checker = BootstrapChecker()

        with patch.object(checker, "_run_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (0, "v22.11.0", "")
            await checker._check_node()

        node_checks = [c for c in checker.report.checks if c.name == "Node.js"]
        assert len(node_checks) == 1
        assert node_checks[0].status == "ok"
        assert "22.11.0" in node_checks[0].details

    @pytest.mark.asyncio
    async def test_check_node_old_version(self):
        """Test _check_node with old node version."""
        checker = BootstrapChecker()

        with patch.object(checker, "_run_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (0, "v18.20.0", "")
            await checker._check_node()

        node_checks = [c for c in checker.report.checks if c.name == "Node.js"]
        assert len(node_checks) == 1
        assert node_checks[0].status == "wrong_version"

    @pytest.mark.asyncio
    async def test_check_node_not_installed(self):
        """Test _check_node when node is not installed."""
        checker = BootstrapChecker()

        with patch.object(checker, "_run_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (127, "", "command not found")
            await checker._check_node()

        node_checks = [c for c in checker.report.checks if c.name == "Node.js"]
        assert len(node_checks) == 1
        assert node_checks[0].status == "missing"

    @pytest.mark.asyncio
    async def test_check_docker_success(self):
        """Test _check_docker with successful docker command."""
        checker = BootstrapChecker()

        with patch.object(checker, "_run_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (0, "Docker version 24.0.7, build afdd53b", "")
            await checker._check_docker()

        docker_checks = [c for c in checker.report.checks if c.name == "Docker"]
        assert len(docker_checks) == 1
        assert docker_checks[0].status == "ok"

    @pytest.mark.asyncio
    async def test_check_uv_success(self):
        """Test _check_uv with successful uv command."""
        checker = BootstrapChecker()

        with patch.object(checker, "_run_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (0, "uv 0.5.0", "")
            await checker._check_uv()

        uv_checks = [c for c in checker.report.checks if c.name == "uv"]
        assert len(uv_checks) == 1
        assert uv_checks[0].status == "ok"
        assert "0.5.0" in uv_checks[0].details

    @pytest.mark.asyncio
    async def test_check_postgres_running(self):
        """Test _check_postgres when postgres is running."""
        checker = BootstrapChecker()

        with patch.object(checker, "_run_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (
                0,
                "/var/run/postgresql:15432 - accepting connections",
                "",
            )
            await checker._check_postgres()

        pg_checks = [c for c in checker.report.checks if c.name == "PostgreSQL"]
        assert len(pg_checks) == 1
        assert pg_checks[0].status == "ok"

    @pytest.mark.asyncio
    async def test_check_postgres_not_running(self):
        """Test _check_postgres when postgres is not running.

        `_check_postgres` has a TCP-socket fallback after pg_isready fails,
        so we must also stub socket.connect_ex to a non-zero return value —
        otherwise CI runners with their own postgres on :15432 (or any
        local dev environment with docker-compose running) take the
        socket-fallback "ok" branch and the test misreads the status.
        """
        checker = BootstrapChecker()

        fake_sock = MagicMock()
        fake_sock.connect_ex.return_value = 111  # ECONNREFUSED-ish

        with (
            patch.object(checker, "_run_command", new_callable=AsyncMock) as mock_run,
            patch("omoi_os.cli.bootstrap.socket.socket", return_value=fake_sock),
        ):
            mock_run.return_value = (2, "", "Connection refused")
            await checker._check_postgres()

        pg_checks = [c for c in checker.report.checks if c.name == "PostgreSQL"]
        assert len(pg_checks) == 1
        assert pg_checks[0].status == "missing"

    @pytest.mark.asyncio
    async def test_check_redis_running(self):
        """Test _check_redis when redis is running."""
        checker = BootstrapChecker()

        with patch.object(checker, "_run_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = (0, "PONG", "")
            await checker._check_redis()

        redis_checks = [c for c in checker.report.checks if c.name == "Redis"]
        assert len(redis_checks) == 1
        assert redis_checks[0].status == "ok"

    @pytest.mark.asyncio
    async def test_check_redis_not_running(self):
        """Test _check_redis when redis is not running.

        Same pattern as test_check_postgres_not_running — `_check_redis` has
        a TCP-socket fallback after redis-cli fails, so we must also stub
        socket.connect_ex to a non-zero value or CI runners with redis on
        :16379 (or local docker-compose) take the socket-fallback "ok" branch.
        """
        checker = BootstrapChecker()

        fake_sock = MagicMock()
        fake_sock.connect_ex.return_value = 111  # ECONNREFUSED-ish

        with (
            patch.object(checker, "_run_command", new_callable=AsyncMock) as mock_run,
            patch("omoi_os.cli.bootstrap.socket.socket", return_value=fake_sock),
        ):
            mock_run.return_value = (1, "", "Could not connect")
            await checker._check_redis()

        redis_checks = [c for c in checker.report.checks if c.name == "Redis"]
        assert len(redis_checks) == 1
        assert redis_checks[0].status == "missing"
