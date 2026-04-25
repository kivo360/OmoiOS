"""Integration tests for auth.json bootstrap inside a thin Docker container.

Tests cover:
- Green path: broker returns valid credentials, auth.json is written with correct
  permissions and content.
- Fail-closed path: broker returns 500, bootstrap exits non-zero, auth.json absent.
- Retry path: broker fails twice then succeeds, auth.json written successfully.

If Docker is unavailable the tests fall back to running the script directly in a
 temporary directory.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
BOOTSTRAP_SCRIPT = REPO_ROOT / "sandbox" / "bootstrap.sh"


def _docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _host_has_bootstrap_deps() -> bool:
    for tool in ("curl", "jq"):
        try:
            subprocess.run([tool, "--version"], capture_output=True, timeout=5)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    return True


class _QuietHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class GreenPathHandler(_QuietHandler):
    """Returns valid credential payloads for anthropic and github."""

    def do_GET(self):
        if "/creds/anthropic" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {"kind": "bearer_secret", "value": "sk-ant-fixture"}
            self.wfile.write(json.dumps(payload).encode())
        elif "/creds/github" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {
                "kind": "user_oauth",
                "access_token": "gho_test_fixture_token",
                "refresh_token": "ghr_test_refresh_token",
                "expires_at": 1893456000,
            }
            self.wfile.write(json.dumps(payload).encode())
        else:
            self.send_response(404)
            self.end_headers()


class FailClosedHandler(_QuietHandler):
    """Always returns HTTP 500."""

    def do_GET(self):
        self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "internal server error"}).encode())


class RetryHandler(_QuietHandler):
    """Fails the first two requests, then succeeds."""

    _counter: int = 0
    _lock = threading.Lock()

    def do_GET(self):
        with RetryHandler._lock:
            RetryHandler._counter += 1
            count = RetryHandler._counter

        if count <= 2:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "temporary failure"}).encode())
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if "anthropic" in self.path:
            payload = {"kind": "bearer_secret", "value": "sk-ant-fixture"}
        else:
            payload = {
                "kind": "user_oauth",
                "access_token": "gho_test_fixture_token",
                "refresh_token": "ghr_test_refresh_token",
                "expires_at": 1893456000,
            }
        self.wfile.write(json.dumps(payload).encode())


@pytest.fixture
def stub_server():
    """Yield a factory that starts an HTTP server with the given handler class."""

    def _start(handler_cls):
        server = HTTPServer(("127.0.0.1", 0), handler_cls)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.1)
        return port, server

    servers = []

    yield _start

    for srv in servers:
        srv.shutdown()


def _run_in_container(
    handler_cls,
    stub_server_factory,
    aliases: str = "anthropic,github",
) -> tuple[int, Path, str]:
    """Run bootstrap.sh inside a Docker container.

    Returns (returncode, home_dir_on_host, combined_output).
    """
    port, server = stub_server_factory(handler_cls)

    tmpdir = tempfile.mkdtemp()
    home_dir = Path(tmpdir) / "test-home"
    home_dir.mkdir(parents=True, exist_ok=True)

    env_vars = [
        "-e",
        "SESSION_TOKEN=sess_tok_test",
        "-e",
        f"BROKER_URL=http://host.docker.internal:{port}/broker",
        "-e",
        f"OMOIOS_CREDENTIAL_ALIASES={aliases}",
        "-e",
        "HOME=/tmp/test-home",
        "-e",
        "DISABLE_VNC=1",
    ]

    extra_args = []
    if sys.platform == "linux":
        extra_args = ["--add-host", "host.docker.internal:host-gateway"]

    cmd = [
        "docker",
        "run",
        "--rm",
        *extra_args,
        *env_vars,
        "-v",
        f"{home_dir}:/tmp/test-home",
        "-v",
        f"{BOOTSTRAP_SCRIPT}:/bootstrap.sh:ro",
        "python:3.11-slim",
        "bash",
        "-c",
        "apt-get update -qq && apt-get install -y -qq curl jq >/dev/null 2>&1 && bash /bootstrap.sh true",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    server.shutdown()
    return result.returncode, home_dir, result.stdout + result.stderr


def _run_in_tempdir(
    handler_cls,
    stub_server_factory,
    aliases: str = "anthropic,github",
) -> tuple[int, Path, str]:
    """Run bootstrap.sh directly on the host (fallback when Docker is missing)."""
    port, server = stub_server_factory(handler_cls)

    tmpdir = tempfile.mkdtemp()
    home_dir = Path(tmpdir) / "test-home"
    home_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["SESSION_TOKEN"] = "sess_tok_test"
    env["BROKER_URL"] = f"http://127.0.0.1:{port}/broker"
    env["OMOIOS_CREDENTIAL_ALIASES"] = aliases
    env["HOME"] = str(home_dir)
    env["DISABLE_VNC"] = "1"
    # Avoid mise shim interference (e.g. jq shim failing on config trust)
    env["PATH"] = "/usr/local/bin:/usr/bin:/bin:/sbin"

    result = subprocess.run(
        ["bash", str(BOOTSTRAP_SCRIPT), "true"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    server.shutdown()
    return result.returncode, home_dir, result.stdout + result.stderr


def _can_run_bootstrap() -> bool:
    return _docker_available() or _host_has_bootstrap_deps()


def _run_bootstrap(handler_cls, stub_server_factory, aliases: str = "anthropic,github"):
    """Run bootstrap using Docker if available, otherwise fall back to tempdir."""
    if _docker_available():
        return _run_in_container(handler_cls, stub_server_factory, aliases)
    return _run_in_tempdir(handler_cls, stub_server_factory, aliases)


def _assert_auth_json_ok(home_dir: Path) -> dict:
    """Verify auth.json exists with correct permissions and content."""
    auth_path = home_dir / ".local" / "share" / "opencode" / "auth.json"
    assert auth_path.exists(), f"auth.json not found at {auth_path}"

    assert oct(auth_path.stat().st_mode)[-3:] == "600", (
        f"auth.json mode is {oct(auth_path.stat().st_mode)}, expected 0o600"
    )
    parent = auth_path.parent
    assert oct(parent.stat().st_mode)[-3:] == "700", (
        f"parent dir mode is {oct(parent.stat().st_mode)}, expected 0o700"
    )

    with open(auth_path) as f:
        data = json.load(f)

    assert data["anthropic"]["type"] == "api"
    assert data["anthropic"]["key"] == "sk-ant-fixture"
    assert data["github"]["type"] == "oauth"
    assert data["github"]["access"], "github access token is empty"

    return data


_SKIP_REASON = "Docker unavailable and host lacks curl/jq"


@pytest.mark.skipif(
    not (_docker_available() or _host_has_bootstrap_deps()),
    reason=_SKIP_REASON,
)
@pytest.mark.integration
class TestBootstrapAuthJson:
    """Integration tests for auth.json bootstrap."""

    def test_green_path(self, stub_server):
        """Bootstrap succeeds and writes a correctly permissioned auth.json."""
        returncode, home_dir, output = _run_bootstrap(GreenPathHandler, stub_server)
        assert returncode == 0, f"bootstrap exited {returncode}: {output}"
        _assert_auth_json_ok(home_dir)

    def test_fail_closed_path(self, stub_server):
        """Broker returns 500; bootstrap exits non-zero and leaves no auth.json."""
        returncode, home_dir, output = _run_bootstrap(FailClosedHandler, stub_server)
        assert returncode != 0, f"expected non-zero exit, got {returncode}: {output}"

        auth_path = home_dir / ".local" / "share" / "opencode" / "auth.json"
        assert not auth_path.exists(), (
            f"auth.json should not exist after failure: {output}"
        )

    def test_retry_path(self, stub_server):
        """Broker fails twice then succeeds; auth.json is written after retries."""
        RetryHandler._counter = 0

        returncode, home_dir, output = _run_bootstrap(RetryHandler, stub_server)
        assert returncode == 0, f"bootstrap exited {returncode}: {output}"

        assert RetryHandler._counter >= 2, (
            f"expected at least 2 broker hits, got {RetryHandler._counter}"
        )

        _assert_auth_json_ok(home_dir)
        assert "retry" in output.lower(), f"expected retry messages in output: {output}"
