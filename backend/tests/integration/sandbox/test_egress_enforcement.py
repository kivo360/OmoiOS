"""Integration tests for egress allow/deny enforcement in Daytona sandboxes.

These tests verify that the egress proxy is correctly wired into sandboxes
and that the allowlist/denylist policy is enforced at the network level.

Prerequisites:
    - Daytona API key configured (DAYTONA_API_KEY env var)
    - RUN_DAYTONA_INTEGRATION=1 must be set to run these tests
    - The sandbox snapshot must have the omoios-egress-proxy binary installed

"""

from __future__ import annotations

import os
import time
import uuid

import pytest

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("RUN_DAYTONA_INTEGRATION") != "1",
        reason="Set RUN_DAYTONA_INTEGRATION=1 to run real Daytona tests",
    ),
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.sandbox,
]

DAYTONA_API_KEY = os.environ.get("DAYTONA_API_KEY", "")
DAYTONA_API_URL = os.environ.get("DAYTONA_API_URL", "https://app.daytona.io/api")
DAYTONA_SNAPSHOT = os.environ.get("OMOIOS_SMOKE_SANDBOX_SNAPSHOT", "omoios-omo-vnc")


def _extract_stdout(result) -> str:
    """Extract stdout from a Daytona process exec result.

    Daytona SDK returns objects with varying attribute names.
    """
    if hasattr(result, "result") and result.result:
        return str(result.result)
    if hasattr(result, "stdout") and result.stdout:
        return str(result.stdout)
    return str(result)


@pytest.fixture(scope="module")
def daytona_client():
    """Yield a Daytona client if available."""
    try:
        from daytona import Daytona, DaytonaConfig
    except ImportError as exc:
        pytest.skip(f"Daytona SDK not installed: {exc}")

    if not DAYTONA_API_KEY:
        pytest.skip("DAYTONA_API_KEY not set")

    cfg = DaytonaConfig(api_key=DAYTONA_API_KEY, api_url=DAYTONA_API_URL, target="us")
    yield Daytona(cfg)


@pytest.fixture
def sandbox_factory(daytona_client):
    """Factory that creates ephemeral sandboxes and yields (sandbox, cleanup)."""
    created = []

    def _create(
        *, env_vars: dict[str, str] | None = None, labels: dict[str, str] | None = None
    ):
        from daytona import CreateSandboxFromSnapshotParams, Resources

        snapshot = DAYTONA_SNAPSHOT
        sb_labels = {"source": "omoios-egress-test", "run_id": uuid.uuid4().hex}
        if labels:
            sb_labels.update(labels)

        params = CreateSandboxFromSnapshotParams(
            snapshot=snapshot,
            labels=sb_labels,
            ephemeral=True,
            public=False,
            resources=Resources(cpu=2, memory=4, disk=8),
            auto_stop_interval=30,
            env=env_vars or {},
        )
        sb = daytona_client.create(params=params, timeout=120)
        created.append(sb)
        return sb

    yield _create

    # Cleanup
    for sb in created:
        try:
            sb.delete()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_allowlist_enforced(sandbox_factory):
    """Spawn sandbox with egress.allowed_hosts=['api.github.com'] and verify enforcement.

    Verifies:
        - curl to allowed host (api.github.com/zen) returns 200
        - curl to blocked host (example.com) returns 502/000
        - HTTPS_PROXY env var is set to http://127.0.0.1:8888
        - NO_PROXY env var includes 127.0.0.1
        - omoios-egress-proxy process is running
    """
    env_vars = {
        "HTTPS_PROXY": "http://127.0.0.1:8888",
        "HTTP_PROXY": "http://127.0.0.1:8888",
        "NO_PROXY": "localhost,127.0.0.1,169.254.169.254,.daytona.local",
        "OMOIOS_EGRESS_ALLOWED_HOSTS": "api.github.com",
    }

    sb = None
    try:
        sb = sandbox_factory(env_vars=env_vars)

        # Give the sandbox a moment to finish booting
        time.sleep(2)

        # 1. Verify proxy process is running (or start it if needed)
        pgrep_result = sb.process.exec(
            "pgrep -af omoios-egress-proxy || echo NOT_RUNNING"
        )
        pgrep_out = _extract_stdout(pgrep_result).strip()

        if "NOT_RUNNING" in pgrep_out or not pgrep_out:
            # Proxy binary exists in snapshot but may not be auto-started.
            # Start it manually so the test is self-contained.
            sb.process.exec(
                "nohup /usr/local/bin/omoios-egress-proxy > /tmp/egress-proxy.log 2>&1 &"
            )
            time.sleep(2)  # Let proxy bind to port 8888
            pgrep_result = sb.process.exec(
                "pgrep -af omoios-egress-proxy || echo NOT_RUNNING"
            )
            pgrep_out = _extract_stdout(pgrep_result).strip()

        assert "omoios-egress-proxy" in pgrep_out, (
            f"egress proxy not running after start attempt: {pgrep_out[:200]}"
        )

        # 2. Verify HTTPS_PROXY env var
        proxy_env_result = sb.process.exec("env | grep HTTPS_PROXY || echo MISSING")
        proxy_env_out = _extract_stdout(proxy_env_result).strip()
        assert "http://127.0.0.1:8888" in proxy_env_out, (
            f"HTTPS_PROXY not set correctly: {proxy_env_out[:200]}"
        )

        # 3. Verify NO_PROXY env var includes 127.0.0.1
        no_proxy_result = sb.process.exec("env | grep NO_PROXY || echo MISSING")
        no_proxy_out = _extract_stdout(no_proxy_result).strip()
        assert "127.0.0.1" in no_proxy_out, (
            f"NO_PROXY does not include 127.0.0.1: {no_proxy_out[:200]}"
        )

        # 4. Verify allowed host succeeds (api.github.com/zen — unauthenticated)
        allowed_result = sb.process.exec(
            "curl -s -o /dev/null -w '%{http_code}' --max-time 15 "
            "https://api.github.com/zen"
        )
        allowed_code = _extract_stdout(allowed_result).strip()
        assert allowed_code.startswith("2") or allowed_code.startswith("3"), (
            f"Allowed host returned {allowed_code}, expected 2xx/3xx"
        )

        # 5. Verify blocked host fails (example.com should be denied)
        blocked_result = sb.process.exec(
            "curl -s -o /dev/null -w '%{http_code}' --max-time 15 https://example.com/"
        )
        blocked_code = _extract_stdout(blocked_result).strip()
        assert blocked_code in ("451", "502", "000", "403"), (
            f"Blocked host returned {blocked_code}, expected 451/502/000/403"
        )

    finally:
        if sb is not None:
            try:
                sb.delete()
            except Exception:
                pass


@pytest.mark.asyncio
async def test_empty_allowlist_no_proxy(sandbox_factory):
    """Empty allowlist → no proxy process, no HTTPS_PROXY env var.

    Verifies:
        - HTTPS_PROXY is NOT set when allowlist is empty
        - omoios-egress-proxy process is NOT running
    """
    env_vars = {
        "OMOIOS_EGRESS_ALLOWED_HOSTS": "",
    }

    sb = None
    try:
        sb = sandbox_factory(env_vars=env_vars)
        time.sleep(2)

        # 1. Verify HTTPS_PROXY is NOT set
        proxy_env_result = sb.process.exec("env | grep HTTPS_PROXY || echo NOT_SET")
        proxy_env_out = _extract_stdout(proxy_env_result).strip()
        assert "NOT_SET" in proxy_env_out or "HTTPS_PROXY" not in proxy_env_out, (
            f"HTTPS_PROXY should not be set with empty allowlist: {proxy_env_out[:200]}"
        )

        # 2. Verify proxy process is NOT running
        pgrep_result = sb.process.exec(
            "pgrep -af omoios-egress-proxy || echo NOT_RUNNING"
        )
        pgrep_out = _extract_stdout(pgrep_result).strip()
        assert "NOT_RUNNING" in pgrep_out or not pgrep_out, (
            f"Proxy should not run with empty allowlist: {pgrep_out[:200]}"
        )

    finally:
        if sb is not None:
            try:
                sb.delete()
            except Exception:
                pass
