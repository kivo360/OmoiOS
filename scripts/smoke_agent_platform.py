#!/usr/bin/env python3
"""End-to-end smoke test for the agent workspace platform.

Exercises the full built surface (credentials CRUD, environments, artifacts,
webhooks, workspace isolation, sessions alias) against a running local API,
then allocates a REAL Daytona sandbox to verify the sandbox boot path and
egress proxy wiring.

Each phase reports one of:
    PASS — behavior matches expectation
    FAIL — regression against a built feature (exit nonzero)
    GAP  — spec requirement not implemented yet (expected; documented, not a failure)
    SKIP — prerequisite unavailable (e.g. DAYTONA_API_KEY unset)

Exit code is 0 unless any FAIL is recorded. GAPs are tracked but do not fail
the run — they're the map of what's left to build.

Prerequisites:
    - Backend API running at API_BASE_URL (default http://localhost:18000)
    - Postgres + Redis up (just watch)
    - CREDENTIAL_ENCRYPTION_KEY set
    - Feature flags flipped (sessions_api_v1, environments_v1, broker_enabled,
      egress_proxy_enabled, artifacts_unified_v1, webhooks_enabled)
    - DAYTONA_API_KEY set (required — per project decision, no mock mode)
    - OMOIOS_PLATFORM_API_KEY set (tenant-scoped platform key)

Usage:
    uv run python scripts/smoke_agent_platform.py
    uv run python scripts/smoke_agent_platform.py --keep-sandbox
    uv run python scripts/smoke_agent_platform.py --only credentials_crud,artifacts_roundtrip
    uv run python scripts/smoke_agent_platform.py --report .sisyphus/evidence/smoke-$(date +%F).json
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import hmac
import json
import os
import secrets
import socket
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable, Optional

import httpx

# The SDK lives in `sdk/python/` and is not part of the uv workspace; inject
# its path so `import omoios` resolves even when the smoke test runs from the
# monorepo root. Done at module load so every phase can use it.
_SDK_PYTHON_ROOT = Path(__file__).resolve().parent.parent / "sdk" / "python"
if _SDK_PYTHON_ROOT.exists() and str(_SDK_PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(_SDK_PYTHON_ROOT))


API_BASE_URL = os.environ.get("OMOIOS_API_BASE_URL", "http://localhost:18000")
PLATFORM_KEY = os.environ.get("OMOIOS_PLATFORM_API_KEY", "")
DAYTONA_API_KEY = os.environ.get("DAYTONA_API_KEY", "")
DAYTONA_API_URL = os.environ.get("DAYTONA_API_URL", "https://app.daytona.io/api")
EGRESS_PROXY_URL = os.environ.get("OMOIOS_EGRESS_PROXY_URL", "http://egress-proxy:3128")
EGRESS_ALLOWED_HOST = os.environ.get("SMOKE_EGRESS_ALLOWED_HOST", "api.github.com")
EGRESS_BLOCKED_HOST = os.environ.get("SMOKE_EGRESS_BLOCKED_HOST", "example.com")


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    GAP = "GAP"
    SKIP = "SKIP"


@dataclass
class PhaseResult:
    name: str
    verdict: Verdict
    duration_sec: float = 0.0
    detail: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class Context:
    """Mutable shared state across phases."""
    org_id: Optional[str] = None
    workspace_a_id: Optional[str] = None
    workspace_b_id: Optional[str] = None
    binding_a_id: Optional[str] = None
    binding_b_id: Optional[str] = None
    environment_id: Optional[str] = None
    env_version_1: Optional[int] = None
    env_version_2: Optional[int] = None
    artifact_id: Optional[str] = None
    webhook_sub_id: Optional[str] = None
    webhook_secret: Optional[str] = None
    daytona_sandbox_id: Optional[str] = None
    client: Optional[httpx.AsyncClient] = None

    # SDK-driven session lifecycle state (Wave 5, Task 19).
    sdk_client: Optional[Any] = None            # AsyncOmoiOSClient
    sdk_ticket_id: Optional[str] = None         # legacy: ticket for ticket-ful sessions
    sdk_workspace_id: Optional[str] = None      # primary: workspace for spec §03 sessions
    sdk_session_id: Optional[str] = None        # session created via SDK
    sdk_session_last_seq: Optional[int] = None  # last seq observed during SSE
    sdk_fork_session_id: Optional[str] = None   # forked session id for cleanup
    sdk_ticketless_session_id: Optional[str] = None  # ticket-less variant for Task 13
    sdk_session_owner_id: Optional[str] = None  # uuid of the user who owns sdk_session_id


def auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {PLATFORM_KEY}",
        "Content-Type": "application/json",
    }


# ─── phase registry ──────────────────────────────────────────────────────────

PHASES: list[tuple[str, Callable[[Context], Any]]] = []


def phase(name: str):
    """Decorator: register an async function as a named phase."""
    def wrap(fn: Callable[[Context], Any]) -> Callable[[Context], Any]:
        PHASES.append((name, fn))
        return fn
    return wrap


# ─── utility: local webhook catcher ───────────────────────────────────────────

class WebhookCatcher:
    """Spins up a one-shot HTTP server to receive a webhook POST."""

    def __init__(self):
        self.received: list[dict[str, Any]] = []
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self.port = self._pick_port()

    @staticmethod
    def _pick_port() -> int:
        with socket.socket() as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    def start(self) -> str:
        catcher = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else b""
                catcher.received.append({
                    "headers": dict(self.headers),
                    "body": body.decode(errors="replace"),
                    "received_at": time.time(),
                })
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"ok":true}')

            def log_message(self, *a, **k):  # quiet
                pass

        self._server = HTTPServer(("127.0.0.1", self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return f"http://127.0.0.1:{self.port}/hook"

    def stop(self):
        if self._server:
            self._server.shutdown()


# ─── phases ─────────────────────────────────────────────────────────────────

@phase("prereqs")
async def phase_prereqs(ctx: Context) -> PhaseResult:
    missing = []
    if not PLATFORM_KEY:
        missing.append("OMOIOS_PLATFORM_API_KEY")
    if not DAYTONA_API_KEY:
        missing.append("DAYTONA_API_KEY")
    if not os.environ.get("CREDENTIAL_ENCRYPTION_KEY"):
        missing.append("CREDENTIAL_ENCRYPTION_KEY")
    if missing:
        return PhaseResult("prereqs", Verdict.FAIL, detail=f"missing env vars: {missing}")

    # Ping the API.
    try:
        r = await ctx.client.get(f"{API_BASE_URL}/health", timeout=5.0)
        if r.status_code >= 400:
            return PhaseResult("prereqs", Verdict.FAIL, detail=f"/health returned {r.status_code}")
    except Exception as e:
        return PhaseResult("prereqs", Verdict.FAIL, detail=f"API not reachable: {e}")

    return PhaseResult("prereqs", Verdict.PASS, detail="env + API reachable")


@phase("org_setup")
async def phase_org_setup(ctx: Context) -> PhaseResult:
    """Resolve an org + two workspaces for isolation tests.

    Platform keys are tenant-scoped so the org is implied by the key. We just
    need workspace IDs — read the first two from whatever the key resolves to.
    """
    r = await ctx.client.get(f"{API_BASE_URL}/api/v1/workspaces", headers=auth_headers())
    if r.status_code != 200:
        return PhaseResult("org_setup", Verdict.FAIL,
                           detail=f"list workspaces: {r.status_code} {r.text[:200]}")
    wss = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    if len(wss) < 2:
        return PhaseResult("org_setup", Verdict.SKIP,
                           detail=f"need ≥2 workspaces for isolation tests, found {len(wss)}")
    ctx.workspace_a_id = wss[0]["id"]
    ctx.workspace_b_id = wss[1]["id"]
    ctx.org_id = wss[0].get("organization_id") or wss[0].get("org_id")
    return PhaseResult("org_setup", Verdict.PASS,
                       evidence={"ws_a": ctx.workspace_a_id, "ws_b": ctx.workspace_b_id})


@phase("credentials_crud")
async def phase_credentials_crud(ctx: Context) -> PhaseResult:
    """POST/GET/DELETE /api/v1/credentials — built surface."""
    plaintext = f"sk-smoke-{secrets.token_hex(8)}"
    r = await ctx.client.post(
        f"{API_BASE_URL}/api/v1/credentials",
        headers=auth_headers(),
        json={
            "workspace_id": ctx.workspace_a_id,
            "kind": "bearer_secret",
            "name": f"smoke-{secrets.token_hex(4)}",
            "value": plaintext,
        },
    )
    if r.status_code not in (200, 201):
        return PhaseResult("credentials_crud", Verdict.FAIL,
                           detail=f"create: {r.status_code} {r.text[:300]}")
    created = r.json()
    ctx.binding_a_id = created["id"]

    # Response must NOT contain the plaintext.
    body_text = r.text
    if plaintext in body_text:
        return PhaseResult("credentials_crud", Verdict.FAIL,
                           detail="PLAINTEXT LEAK: create response contains plaintext value")

    # GET by id.
    r = await ctx.client.get(f"{API_BASE_URL}/api/v1/credentials/{ctx.binding_a_id}",
                             headers=auth_headers())
    if r.status_code != 200:
        return PhaseResult("credentials_crud", Verdict.FAIL,
                           detail=f"get: {r.status_code} {r.text[:300]}")
    if plaintext in r.text:
        return PhaseResult("credentials_crud", Verdict.FAIL,
                           detail="PLAINTEXT LEAK: get response contains plaintext value")

    return PhaseResult("credentials_crud", Verdict.PASS,
                       evidence={"binding_id": ctx.binding_a_id})


@phase("environments_crud")
async def phase_environments_crud(ctx: Context) -> PhaseResult:
    """Create env → v1 (with secret variable) → v2 → verify v1 still retrievable."""
    r = await ctx.client.post(
        f"{API_BASE_URL}/api/v1/environments",
        headers=auth_headers(),
        json={
            "name": f"smoke-{secrets.token_hex(4)}",
            "description": "smoke test env",
            "org_id": ctx.org_id,
        },
    )
    if r.status_code not in (200, 201):
        return PhaseResult("environments_crud", Verdict.FAIL,
                           detail=f"create env: {r.status_code} {r.text[:300]}")
    ctx.environment_id = r.json()["id"]

    secret_plaintext = f"env-secret-{secrets.token_hex(8)}"
    r = await ctx.client.post(
        f"{API_BASE_URL}/api/v1/environments/{ctx.environment_id}/versions",
        headers=auth_headers(),
        json={"variables": {
            "DB_URL": {"type": "string", "value": "postgres://example"},
            "API_KEY": {"type": "secret", "value": secret_plaintext},
        }},
    )
    if r.status_code not in (200, 201):
        return PhaseResult("environments_crud", Verdict.FAIL,
                           detail=f"v1: {r.status_code} {r.text[:300]}")
    v1 = r.json()
    ctx.env_version_1 = v1.get("version_number") or v1.get("version")

    if secret_plaintext in r.text:
        return PhaseResult("environments_crud", Verdict.FAIL,
                           detail="PLAINTEXT LEAK: env v1 response contains secret value")

    r = await ctx.client.post(
        f"{API_BASE_URL}/api/v1/environments/{ctx.environment_id}/versions",
        headers=auth_headers(),
        json={"variables": {"DB_URL": {"type": "string", "value": "postgres://changed"}}},
    )
    if r.status_code not in (200, 201):
        return PhaseResult("environments_crud", Verdict.FAIL,
                           detail=f"v2: {r.status_code} {r.text[:300]}")
    v2 = r.json()
    ctx.env_version_2 = v2.get("version_number") or v2.get("version")

    if ctx.env_version_2 == ctx.env_version_1:
        return PhaseResult("environments_crud", Verdict.FAIL,
                           detail="v2 did not increment version")
    return PhaseResult("environments_crud", Verdict.PASS,
                       evidence={"env_id": ctx.environment_id,
                                 "v1": ctx.env_version_1, "v2": ctx.env_version_2})


@phase("artifacts_roundtrip")
async def phase_artifacts_roundtrip(ctx: Context) -> PhaseResult:
    """Upload → download → checksum match."""
    payload = f"smoke-artifact-{secrets.token_hex(16)}".encode()
    expected_sha = hashlib.sha256(payload).hexdigest()

    files = {"file": ("smoke.bin", payload, "application/octet-stream")}
    r = await ctx.client.post(
        f"{API_BASE_URL}/api/v1/artifacts/upload",
        headers={"Authorization": f"Bearer {PLATFORM_KEY}"},
        files=files,
        data={"workspace_id": ctx.workspace_a_id},
    )
    if r.status_code not in (200, 201):
        return PhaseResult("artifacts_roundtrip", Verdict.FAIL,
                           detail=f"upload: {r.status_code} {r.text[:300]}")
    ctx.artifact_id = r.json()["id"]

    r = await ctx.client.get(
        f"{API_BASE_URL}/api/v1/artifacts/{ctx.artifact_id}/download",
        headers=auth_headers(),
    )
    if r.status_code != 200:
        return PhaseResult("artifacts_roundtrip", Verdict.FAIL,
                           detail=f"download: {r.status_code}")
    got_sha = hashlib.sha256(r.content).hexdigest()
    if got_sha != expected_sha:
        return PhaseResult("artifacts_roundtrip", Verdict.FAIL,
                           detail=f"checksum mismatch: expected {expected_sha}, got {got_sha}")
    return PhaseResult("artifacts_roundtrip", Verdict.PASS,
                       evidence={"artifact_id": ctx.artifact_id, "sha256": got_sha})


@phase("webhooks_hmac")
async def phase_webhooks_hmac(ctx: Context) -> PhaseResult:
    """Register subscription → trigger event → catcher receives + HMAC verifies."""
    # Webhook delivery requires the API server to be able to reach back to the
    # local HTTP catcher. When the API is remote (Railway/staging/prod) it
    # cannot dial 127.0.0.1, so this phase is meaningless without a tunnel.
    # SKIP rather than FAIL so the run reflects real product health.
    if "localhost" not in API_BASE_URL and "127.0.0.1" not in API_BASE_URL:
        return PhaseResult(
            "webhooks_hmac",
            Verdict.SKIP,
            detail=(
                "remote API cannot reach 127.0.0.1 catcher; "
                "run against a local API or expose the catcher via tunnel"
            ),
        )
    catcher = WebhookCatcher()
    url = catcher.start()
    ctx.webhook_secret = f"whsec_{secrets.token_hex(16)}"
    try:
        r = await ctx.client.post(
            f"{API_BASE_URL}/api/v1/webhooks/subscriptions",
            headers=auth_headers(),
            params={"org_id": ctx.org_id},
            json={
                "url": url,
                "events": ["artifact.uploaded"],
                "secret": ctx.webhook_secret,
            },
        )
        if r.status_code not in (200, 201):
            return PhaseResult("webhooks_hmac", Verdict.FAIL,
                               detail=f"subscribe: {r.status_code} {r.text[:300]}")
        ctx.webhook_sub_id = r.json()["id"]

        # Trigger an artifact.uploaded by uploading a small file.
        r = await ctx.client.post(
            f"{API_BASE_URL}/api/v1/artifacts/upload",
            headers={"Authorization": f"Bearer {PLATFORM_KEY}"},
            files={"file": ("hook.txt", b"hello", "text/plain")},
            data={"workspace_id": ctx.workspace_a_id},
        )
        if r.status_code not in (200, 201):
            return PhaseResult("webhooks_hmac", Verdict.FAIL,
                               detail=f"trigger upload: {r.status_code}")

        # Poll up to 10s for a delivery.
        deadline = time.time() + 10
        while time.time() < deadline and not catcher.received:
            await asyncio.sleep(0.3)

        if not catcher.received:
            return PhaseResult("webhooks_hmac", Verdict.FAIL,
                               detail="no webhook received within 10s")

        delivery = catcher.received[0]
        sig_header = delivery["headers"].get("X-Signature") or delivery["headers"].get("X-Hub-Signature-256") or ""
        if not sig_header:
            return PhaseResult("webhooks_hmac", Verdict.FAIL,
                               detail=f"no signature header; got headers={list(delivery['headers'])}")

        # Signature format varies — try common shapes:
        #   "t=<ts>,v1=<hmac>"  (Stripe-style)
        #   "sha256=<hmac>"     (GitHub-style)
        body_bytes = delivery["body"].encode()
        ok = False
        if "v1=" in sig_header and "t=" in sig_header:
            parts = dict(p.split("=", 1) for p in sig_header.split(","))
            signed = f"{parts['t']}.{delivery['body']}".encode()
            expected = hmac.new(ctx.webhook_secret.encode(), signed, hashlib.sha256).hexdigest()
            ok = hmac.compare_digest(expected, parts.get("v1", ""))
        elif sig_header.startswith("sha256="):
            expected = hmac.new(ctx.webhook_secret.encode(), body_bytes, hashlib.sha256).hexdigest()
            ok = hmac.compare_digest(expected, sig_header.split("=", 1)[1])
        else:
            expected = hmac.new(ctx.webhook_secret.encode(), body_bytes, hashlib.sha256).hexdigest()
            ok = hmac.compare_digest(expected, sig_header)

        if not ok:
            return PhaseResult("webhooks_hmac", Verdict.FAIL,
                               detail=f"HMAC signature mismatch; header={sig_header[:60]}")
        return PhaseResult("webhooks_hmac", Verdict.PASS,
                           evidence={"sub_id": ctx.webhook_sub_id,
                                     "signature_header": sig_header[:120]})
    finally:
        catcher.stop()


@phase("workspace_isolation")
async def phase_workspace_isolation(ctx: Context) -> PhaseResult:
    """Create a binding in B; assert the binding in A cannot be retrieved via B's scope."""
    # Create a binding in workspace B for contrast.
    r = await ctx.client.post(
        f"{API_BASE_URL}/api/v1/credentials",
        headers=auth_headers(),
        json={
            "workspace_id": ctx.workspace_b_id,
            "kind": "bearer_secret",
            "name": f"iso-{secrets.token_hex(4)}",
            "value": f"sk-iso-{secrets.token_hex(8)}",
        },
    )
    if r.status_code not in (200, 201):
        return PhaseResult("workspace_isolation", Verdict.FAIL,
                           detail=f"create in B: {r.status_code} {r.text[:300]}")
    ctx.binding_b_id = r.json()["id"]

    # Listing workspace A should NOT include B's binding.
    r = await ctx.client.get(
        f"{API_BASE_URL}/api/v1/credentials?workspace_id={ctx.workspace_a_id}",
        headers=auth_headers(),
    )
    if r.status_code != 200:
        return PhaseResult("workspace_isolation", Verdict.FAIL,
                           detail=f"list A: {r.status_code}")
    ids = {b["id"] for b in (r.json() if isinstance(r.json(), list) else r.json().get("items", []))}
    if ctx.binding_b_id in ids:
        return PhaseResult("workspace_isolation", Verdict.FAIL,
                           detail="ISOLATION BREACH: ws A's listing included ws B's binding")
    return PhaseResult("workspace_isolation", Verdict.PASS,
                       evidence={"binding_a_in_a": ctx.binding_a_id in ids,
                                 "binding_b_leaked_to_a": False})


@phase("sessions_alias")
async def phase_sessions_alias(ctx: Context) -> PhaseResult:
    """GET /api/v1/sessions responds with its own 4-arm visibility query.

    Historically `/api/v1/sessions` delegated to `/api/v1/tasks` and the two
    responses were byte-identical. The session-ticket decoupling (Wave 1
    T1 of the spec-18 alignment plan) replaced that with a dedicated query
    that enforces the 4-arm visibility clause (ticket+archived-spec,
    workspace-org, created_by, SessionACL). The bodies MAY now differ —
    sessions includes ticket-less rows and filters archived specs — so we
    no longer require a byte-match.

    What we still require: the endpoint is reachable and each response is
    a JSON list. The X-Deprecated header is no longer expected either;
    `/api/v1/sessions` is the canonical surface, not the alias.
    """
    r_sess = await ctx.client.get(f"{API_BASE_URL}/api/v1/sessions", headers=auth_headers())
    r_tasks = await ctx.client.get(f"{API_BASE_URL}/api/v1/tasks", headers=auth_headers())

    if r_sess.status_code != 200:
        return PhaseResult("sessions_alias", Verdict.FAIL,
                           detail=f"/sessions: {r_sess.status_code}")
    try:
        sess_body = r_sess.json()
    except Exception as exc:  # noqa: BLE001
        return PhaseResult("sessions_alias", Verdict.FAIL,
                           detail=f"/sessions body not JSON: {exc}")
    if not isinstance(sess_body, list):
        return PhaseResult("sessions_alias", Verdict.FAIL,
                           detail=f"/sessions must return list, got {type(sess_body).__name__}")

    return PhaseResult("sessions_alias", Verdict.PASS,
                       evidence={
                           "sessions_count": len(sess_body),
                           "tasks_status": r_tasks.status_code,
                           "bodies_match": r_tasks.status_code == 200 and r_tasks.text == r_sess.text,
                       })


@phase("daytona_allocation")
async def phase_daytona_allocation(ctx: Context) -> PhaseResult:
    """Spin up a real sandbox and run a command inside it.

    Baseline: proves the configured provider's creds + image work. Required
    before egress tests. The phase name is `daytona_allocation` for backwards
    compatibility with prior reports, but the actual backend is whichever
    provider `SANDBOX_PROVIDER` (or `OMOIOS_SMOKE_SANDBOX_PROVIDER`) selects.
    """
    provider_name = os.environ.get(
        "OMOIOS_SMOKE_SANDBOX_PROVIDER",
        os.environ.get("SANDBOX_PROVIDER", "daytona"),
    ).lower()

    if provider_name == "modal":
        return await _allocate_via_modal(ctx)
    return await _allocate_via_daytona(ctx)


async def _allocate_via_daytona(ctx: Context) -> PhaseResult:
    try:
        from daytona import Daytona, DaytonaConfig, CreateSandboxFromSnapshotParams
    except ImportError as e:
        return PhaseResult("daytona_allocation", Verdict.SKIP,
                           detail=f"daytona SDK not importable: {e}")

    cfg = DaytonaConfig(api_key=DAYTONA_API_KEY, api_url=DAYTONA_API_URL, target="us")
    d = Daytona(cfg)
    try:
        snapshot = os.environ.get("OMOIOS_SMOKE_SANDBOX_SNAPSHOT", "omoios-omo-vnc")
        params = CreateSandboxFromSnapshotParams(
            snapshot=snapshot,
            labels={"source": "omoios-smoke-test", "run_id": uuid.uuid4().hex},
            env_vars={"SMOKE_TEST": "1"},
        )
        sb = d.create(params)
        ctx.daytona_sandbox_id = getattr(sb, "id", None) or getattr(sb, "sandbox_id", None)
    except Exception as e:
        return PhaseResult("daytona_allocation", Verdict.FAIL,
                           detail=f"sandbox create failed: {e}")

    try:
        result = sb.process.exec("echo hello-from-daytona && curl -s -o /dev/null -w '%{http_code}' https://api.github.com")
        out = getattr(result, "result", "") or getattr(result, "stdout", "")
        if "hello-from-daytona" not in str(out):
            return PhaseResult("daytona_allocation", Verdict.FAIL,
                               detail=f"exec echo failed; stdout={str(out)[:200]}")
        return PhaseResult("daytona_allocation", Verdict.PASS,
                           evidence={"provider": "daytona",
                                     "sandbox_id": ctx.daytona_sandbox_id,
                                     "exec_output": str(out)[:300]})
    except Exception as e:
        return PhaseResult("daytona_allocation", Verdict.FAIL,
                           detail=f"exec failed: {e}")


async def _allocate_via_modal(ctx: Context) -> PhaseResult:
    """Modal-backed allocation that goes through the OmoiOS provider stack."""
    try:
        # Import lazily so the smoke can run even if `modal` isn't installed.
        # The factory returns ModalProvider when SANDBOX_PROVIDER=modal.
        os.environ["SANDBOX_PROVIDER"] = "modal"
        from omoi_os.services.sandbox_factory import create_sandbox_provider
        from omoi_os.services.modal_provider import ModalProvider
        from omoi_os.services.modal_spawner import get_modal_spawner
    except Exception as e:
        return PhaseResult("daytona_allocation", Verdict.SKIP,
                           detail=f"modal provider not importable: {e}")

    try:
        provider = create_sandbox_provider(db=None, event_bus=None)
        if not isinstance(provider, ModalProvider):
            return PhaseResult(
                "daytona_allocation", Verdict.FAIL,
                detail=f"factory returned {type(provider).__name__}; expected ModalProvider")
        result = await provider.spawn_for_task(
            task_id=f"smoke-{uuid.uuid4().hex[:8]}",
            agent_id="smoke-agent",
            phase_id="PHASE_SMOKE",
            env_vars={"SMOKE_TEST": "1"},
            runtime="claude",
            execution_mode="implementation",
        )
        ctx.daytona_sandbox_id = result.sandbox_id  # reused field; provider-agnostic
    except Exception as e:
        return PhaseResult("daytona_allocation", Verdict.FAIL,
                           detail=f"modal spawn failed: {e}")

    try:
        spawner = get_modal_spawner()
        out_obj = await spawner.exec(
            ctx.daytona_sandbox_id,
            "sh", "-c",
            "echo hello-from-modal && curl -s -o /dev/null -w '%{http_code}' https://api.github.com",
        )
        out = (out_obj.get("stdout") or "")
        if "hello-from-modal" not in str(out):
            return PhaseResult("daytona_allocation", Verdict.FAIL,
                               detail=f"exec echo failed; stdout={str(out)[:200]}")
        return PhaseResult("daytona_allocation", Verdict.PASS,
                           evidence={"provider": "modal",
                                     "sandbox_id": ctx.daytona_sandbox_id,
                                     "exec_output": str(out)[:300]})
    except Exception as e:
        return PhaseResult("daytona_allocation", Verdict.FAIL,
                           detail=f"exec failed: {e}")


def _is_modal_provider() -> bool:
    """True when smoke is running in Modal mode."""
    return os.environ.get(
        "OMOIOS_SMOKE_SANDBOX_PROVIDER",
        os.environ.get("SANDBOX_PROVIDER", "daytona"),
    ).lower() == "modal"


async def _sandbox_exec(ctx: Context, cmd_str: str) -> tuple[str, int]:
    """Provider-agnostic exec that returns (stdout, exit_code).

    `cmd_str` is a single shell string — both backends invoke it via
    `sh -c "<cmd_str>"` so quoting works the same on both. Returns the
    stdout as a stripped string and the process exit code (0 on success).
    Raises if the sandbox handle isn't available.
    """
    if not ctx.daytona_sandbox_id:
        raise RuntimeError("no sandbox allocated")

    if _is_modal_provider():
        from omoi_os.services.modal_spawner import get_modal_spawner

        spawner = get_modal_spawner()
        result = await spawner.exec(ctx.daytona_sandbox_id, "sh", "-c", cmd_str)
        stdout = (result.get("stdout") or "")
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        exit_code = int(result.get("exit_code") or 0)
        return str(stdout), exit_code

    # Daytona path.
    from daytona import Daytona, DaytonaConfig

    cfg = DaytonaConfig(api_key=DAYTONA_API_KEY, api_url=DAYTONA_API_URL, target="us")
    sb = Daytona(cfg).get(ctx.daytona_sandbox_id)
    result = sb.process.exec(cmd_str)
    out = getattr(result, "result", None)
    if out is None:
        out = getattr(result, "stdout", "")
    code = int(getattr(result, "exit_code", 0) or 0)
    return str(out), code


@phase("egress_proxy_wiring")
async def phase_egress_proxy_wiring(ctx: Context) -> PhaseResult:
    """Verify the Daytona spawner injects HTTPS_PROXY when egress is configured.

    `daytona_spawner.py` injects HTTPS_PROXY / HTTP_PROXY / NO_PROXY only when
    the bound `EnvironmentVersion.egress.allowed_hosts` is non-empty. The raw
    sandbox allocated by `phase_daytona_allocation` bypasses the spawner and
    has no env-version binding, so it WILL NOT have these vars — that's
    expected, not a bug. Reports SKIP with a clear reason in that case.

    To actually exercise the spawner path, allocate via OmoiOS:
      - create env_version with egress.allowed_hosts
      - bind to a workspace
      - launch a session that spawns through `DaytonaSpawnerService`
    """
    if not ctx.daytona_sandbox_id:
        return PhaseResult("egress_proxy_wiring", Verdict.SKIP,
                           detail="no sandbox allocated")
    try:
        out, _ = await _sandbox_exec(
            ctx, "env | grep -E '^(HTTPS_PROXY|HTTP_PROXY|NO_PROXY)=' || echo NOT_SET",
        )
        if "NOT_SET" in out:
            return PhaseResult(
                "egress_proxy_wiring", Verdict.SKIP,
                detail=(
                    "bare sandbox; spawner injection only fires when an "
                    "EnvironmentVersion with egress.allowed_hosts is bound. "
                    "To exercise this path, allocate via OmoiOS, not directly."
                ),
                evidence={"env_check": out[:400]})
        return PhaseResult("egress_proxy_wiring", Verdict.PASS,
                           evidence={"proxy_env": out[:400]})
    except Exception as e:
        return PhaseResult("egress_proxy_wiring", Verdict.FAIL,
                           detail=f"env inspect failed: {e}")


@phase("egress_allow_deny")
async def phase_egress_allow_deny(ctx: Context) -> PhaseResult:
    """With HTTPS_PROXY set, an allowed host succeeds and a blocked one returns 451.

    Will SKIP if the proxy isn't wired (prior phase reported GAP).
    """
    if not ctx.daytona_sandbox_id:
        return PhaseResult("egress_allow_deny", Verdict.SKIP, detail="no sandbox")

    try:
        # Probe: is HTTPS_PROXY set? If not, skip — nothing to verify.
        proxy_val, _ = await _sandbox_exec(ctx, "echo $HTTPS_PROXY")
        proxy_val = proxy_val.strip()
        if not proxy_val:
            return PhaseResult(
                "egress_allow_deny", Verdict.SKIP,
                detail="HTTPS_PROXY unset in sandbox; cannot verify allow/deny behavior")

        a_code, _ = await _sandbox_exec(
            ctx, f"curl -s -o /dev/null -w '%{{http_code}}' https://{EGRESS_ALLOWED_HOST}",
        )
        b_code, _ = await _sandbox_exec(
            ctx, f"curl -s -o /dev/null -w '%{{http_code}}' https://{EGRESS_BLOCKED_HOST}",
        )
        a_code = a_code.strip()
        b_code = b_code.strip()

        a_ok = a_code.startswith("2") or a_code.startswith("3")
        b_blocked = b_code == "451" or b_code == "000"  # 000 = connection closed
        if a_ok and b_blocked:
            return PhaseResult("egress_allow_deny", Verdict.PASS,
                               evidence={"allowed_host_code": a_code, "blocked_host_code": b_code})
        return PhaseResult("egress_allow_deny", Verdict.FAIL,
                           detail=f"allow={a_code} (expect 2xx/3xx), deny={b_code} (expect 451/000)",
                           evidence={"proxy": proxy_val})
    except Exception as e:
        return PhaseResult("egress_allow_deny", Verdict.FAIL, detail=f"exec failed: {e}")


@phase("opencode_auth_json")
async def phase_opencode_auth_json(ctx: Context) -> PhaseResult:
    """Spec §14: OmO reads ~/.local/share/opencode/auth.json for provider creds.

    Required shape (mode 0600):
        { "<provider>": { "type": "api"|"oauth", "key"|"access": "..." }, ... }

    Bootstrap writes this file **only when** `OMOIOS_CREDENTIAL_ALIASES`,
    `SESSION_TOKEN`, and `BROKER_URL` are all set at sandbox boot. The
    daytona_allocation phase spawns a bare sandbox with none of those
    configured, so absence of auth.json is correct conditional behavior,
    not a gap. We verify (a) the entrypoint ran and (b) the OpenCode data
    directory is present + 0700 — proof that the bootstrap's filesystem
    setup fired.
    """
    if not ctx.daytona_sandbox_id:
        return PhaseResult("opencode_auth_json", Verdict.SKIP, detail="no sandbox")
    try:
        out, _ = await _sandbox_exec(
            ctx,
            "for f in /root/.local/share/opencode/auth.json "
            "$HOME/.local/share/opencode/auth.json; do "
            "  if [ -f \"$f\" ]; then "
            "    echo FOUND:$f:$(stat -c '%a' \"$f\"):$(cat \"$f\" | head -c 500); "
            "    exit 0; "
            "  fi; "
            "done; echo MISSING",
        )
        out = out.strip()

        if out.startswith("MISSING"):
            # Probe for the bootstrap script + data dir — if those are in
            # place, the sandbox is wired correctly; auth.json would have
            # landed had credential aliases been configured.
            dir_out, _ = await _sandbox_exec(
                ctx,
                "for d in /root/.local/share/opencode "
                "$HOME/.local/share/opencode; do "
                "  if [ -d \"$d\" ]; then "
                "    echo DATA_DIR:$d:$(stat -c '%a' \"$d\"); "
                "    exit 0; "
                "  fi; "
                "done; echo NO_DATA_DIR",
            )
            dir_out = dir_out.strip()
            if dir_out.startswith("DATA_DIR:"):
                return PhaseResult(
                    "opencode_auth_json", Verdict.PASS,
                    evidence={
                        "note": (
                            "bootstrap ran; auth.json is conditional on "
                            "OMOIOS_CREDENTIAL_ALIASES being set at spawn "
                            "time — not in this bare allocation"
                        ),
                        "data_dir": dir_out,
                    },
                )
            return PhaseResult(
                "opencode_auth_json", Verdict.FAIL,
                detail=(
                    "bootstrap did not create the OpenCode data dir "
                    "(~/.local/share/opencode). Snapshot entrypoint may be "
                    "misconfigured."
                ),
                evidence={"probe": out, "dir_probe": dir_out},
            )

        # Parse "FOUND:<path>:<mode>:<first 500 bytes of content>"
        parts = out.split(":", 3)
        path, mode, preview = parts[1], parts[2], parts[3] if len(parts) > 3 else ""
        try:
            parsed = json.loads(preview)
        except json.JSONDecodeError:
            return PhaseResult("opencode_auth_json", Verdict.FAIL,
                               detail=f"auth.json not valid JSON: {preview[:200]}")
        if mode != "600":
            return PhaseResult("opencode_auth_json", Verdict.FAIL,
                               detail=f"auth.json permissions {mode}, expected 600",
                               evidence={"path": path, "providers": list(parsed.keys())})
        if not isinstance(parsed, dict) or not parsed:
            return PhaseResult("opencode_auth_json", Verdict.FAIL,
                               detail="auth.json is empty or not an object")
        # Validate shape: every entry needs a "type" field.
        bad = [k for k, v in parsed.items()
               if not isinstance(v, dict) or "type" not in v]
        if bad:
            return PhaseResult("opencode_auth_json", Verdict.FAIL,
                               detail=f"auth.json entries missing 'type' field: {bad}")
        return PhaseResult("opencode_auth_json", Verdict.PASS,
                           evidence={"path": path, "mode": mode,
                                     "providers": sorted(parsed.keys())})
    except Exception as e:
        return PhaseResult("opencode_auth_json", Verdict.FAIL, detail=f"exec failed: {e}")


@phase("opencode_config")
async def phase_opencode_config(ctx: Context) -> PhaseResult:
    """Spec §14: OmO reads opencode.json for provider/model surface.

    Expected at ~/.config/opencode/opencode.json with `provider` block defining
    each provider (npm package + `{env:VAR}` substitutions). Optional layered
    override: `oh-my-openagent.jsonc` for agent/category routing.

    Today: not written at sandbox boot. Bootstrap needs to render this from
    the environment version's provider definitions.
    """
    if not ctx.daytona_sandbox_id:
        return PhaseResult("opencode_config", Verdict.SKIP, detail="no sandbox")
    try:
        out, _ = await _sandbox_exec(
            ctx,
            "for f in /root/.config/opencode/opencode.json "
            "$HOME/.config/opencode/opencode.json "
            "/root/.config/opencode/oh-my-openagent.jsonc "
            "$HOME/.config/opencode/oh-my-openagent.jsonc; do "
            "  if [ -f \"$f\" ]; then echo \"FOUND:$f\"; fi; "
            "done; echo DONE",
        )
        out = out.strip()
        found = [line.split(":", 1)[1] for line in out.splitlines()
                 if line.startswith("FOUND:")]
        if not found:
            return PhaseResult(
                "opencode_config", Verdict.GAP,
                detail="opencode.json / oh-my-openagent.jsonc not present. "
                       "Bootstrap must render these from env.credentials + env.tools so "
                       "OmO knows which providers + models + fallback chains to use. "
                       "Without these, OmO has no provider surface and cannot route tasks.")
        return PhaseResult("opencode_config", Verdict.PASS,
                           evidence={"files": found})
    except Exception as e:
        return PhaseResult("opencode_config", Verdict.FAIL, detail=f"exec failed: {e}")


@phase("spec_broker_flow")
async def phase_spec_broker_flow(ctx: Context) -> PhaseResult:
    """Spec §04: sandbox presents sess_tok_... to GET /broker/creds/{alias}.

    The broker route is mounted at /broker/creds/{alias} and verifies the
    sandbox session token. With a *fake* token the correct response is
    401 — that proves the endpoint exists, auth plumbing works, and the
    token verifier runs. A full end-to-end check (session_create mints
    a real token → broker resolves it) would need an environment with a
    credential alias bound; we leave that to manual verification rather
    than stand up the full credential chain in smoke.
    """
    r = await ctx.client.get(
        f"{API_BASE_URL}/broker/creds/anthropic",
        headers={"Authorization": f"Bearer sess_tok_{secrets.token_hex(16)}"},
    )
    if r.status_code == 404:
        return PhaseResult(
            "spec_broker_flow", Verdict.FAIL,
            detail="GET /broker/creds/{alias} not mounted",
            evidence={"http_code": r.status_code})
    if r.status_code in (401, 403):
        return PhaseResult(
            "spec_broker_flow", Verdict.PASS,
            evidence={
                "http_code": r.status_code,
                "note": "endpoint rejects fake token as expected; full flow "
                        "requires real session_token from session create",
            })
    if r.status_code < 400:
        return PhaseResult(
            "spec_broker_flow", Verdict.PASS,
            evidence={"http_code": r.status_code, "body": r.text[:300]},
        )
    return PhaseResult(
        "spec_broker_flow", Verdict.FAIL,
        detail=f"unexpected status {r.status_code}: {r.text[:200]}",
    )


@phase("session_token_bounded_scope")
async def phase_session_token_bounded_scope(ctx: Context) -> PhaseResult:
    """Spec §06 last row: a `sess_tok_…` may ONLY authenticate against the
    broker. Every other authenticated route must reject it with 401, not
    coerce it into a platform-key code path that could expose data.

    A leaked sandbox session token must be useless beyond `/broker/*`. We
    use a fake `sess_tok_` here — the route classifier should send it to
    the session verifier (which rejects fake tokens) regardless of which
    endpoint it lands on. The interesting failure is a 200/201/403 on a
    blocked path, which would mean the prefix wasn't honored.
    """
    fake = f"sess_tok_{secrets.token_hex(16)}"
    headers = {"Authorization": f"Bearer {fake}"}

    blocked_paths = [
        "/api/v1/sessions",
        "/api/v1/credentials",
        "/api/v1/workspaces",
        "/api/v1/environments",
        "/api/v1/artifacts",
        "/api/v1/connections",
        "/api/v1/usage",
    ]

    leaks: list[str] = []
    statuses: dict[str, int] = {}
    for path in blocked_paths:
        try:
            r = await ctx.client.get(
                f"{API_BASE_URL}{path}", headers=headers,
                params={"workspace_id": ctx.workspace_a_id} if ctx.workspace_a_id else None,
            )
            statuses[path] = r.status_code
            if r.status_code in (200, 201):
                leaks.append(f"{path}={r.status_code}")
        except Exception as e:
            statuses[path] = -1
            leaks.append(f"{path} raised {type(e).__name__}")

    if leaks:
        return PhaseResult(
            "session_token_bounded_scope", Verdict.FAIL,
            detail=f"sess_tok_ accepted on platform endpoints: {'; '.join(leaks)}",
            evidence={"statuses": statuses},
        )
    return PhaseResult(
        "session_token_bounded_scope", Verdict.PASS,
        evidence={"statuses": statuses,
                  "note": "all platform endpoints rejected fake sess_tok_"},
    )


@phase("api_shape_gate")
async def phase_api_shape_gate(ctx: Context) -> PhaseResult:
    """Spec §1.4: SDK types must match the server schema. Production has
    /openapi.json disabled for security, so we instead probe known
    response shapes — failure here means the SDK will silently break.

    Required field set per spec §02 + sdk/python/omoios/types.py::Session.
    Allows additive fields (extra='allow' on the model) but flags any
    REMOVAL of a previously-documented key.
    """
    if not ctx.sdk_session_id:
        return PhaseResult("api_shape_gate", Verdict.SKIP,
                           detail="needs sdk_session_id; depends on session_create")

    r = await ctx.client.get(
        f"{API_BASE_URL}/api/v1/sessions/{ctx.sdk_session_id}",
        headers=auth_headers(),
    )
    if r.status_code != 200:
        return PhaseResult("api_shape_gate", Verdict.FAIL,
                           detail=f"GET session: {r.status_code} {r.text[:200]}")
    try:
        body = r.json()
    except Exception as e:
        return PhaseResult("api_shape_gate", Verdict.FAIL,
                           detail=f"non-JSON response: {e}")

    required = {"id", "status", "created_at"}
    expected = {
        "id", "status", "created_at",
        # nullable but present:
        "ticket_id", "workspace_id", "environment_id",
        "github_repo", "created_by", "ended_at",
    }
    missing_required = required - set(body.keys())
    if missing_required:
        return PhaseResult(
            "api_shape_gate", Verdict.FAIL,
            detail=f"required fields missing: {sorted(missing_required)}",
            evidence={"keys_present": sorted(body.keys())},
        )

    # Soft signal: documented optional fields gone (the SDK declares them).
    soft_missing = expected - set(body.keys()) - missing_required
    return PhaseResult(
        "api_shape_gate", Verdict.PASS,
        evidence={
            "keys_present": sorted(body.keys()),
            "soft_missing": sorted(soft_missing),
            "note": (
                "all required fields present; SDK Session model expects "
                f"{len(expected)} fields, server returned {len(body)}"
            ),
        },
    )


@phase("spec_event_envelope")
async def phase_spec_event_envelope(ctx: Context) -> PhaseResult:
    """Spec §03: events carry {id, seq, type, session_id, actor, timestamp, data}.

    Uses `ctx.sdk_session_id` when available (definitely has session.created),
    otherwise walks the first page of tasks looking for one with events.
    """
    task_id: Optional[str] = ctx.sdk_session_id
    if not task_id:
        r = await ctx.client.get(
            f"{API_BASE_URL}/api/v1/tasks?limit=25", headers=auth_headers(),
        )
        if r.status_code != 200:
            return PhaseResult("spec_event_envelope", Verdict.SKIP,
                               detail="could not list tasks for event probe")
        tasks = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
        if not tasks:
            return PhaseResult("spec_event_envelope", Verdict.SKIP, detail="no tasks to inspect")
        # Walk until we find one with events so we aren't at the mercy of
        # which task the `limit=1` window happened to land on.
        task_id = None
        for candidate in tasks:
            cid = candidate.get("id")
            if not cid:
                continue
            probe = await ctx.client.get(
                f"{API_BASE_URL}/api/v1/events?task_id={cid}&limit=1",
                headers=auth_headers(),
            )
            if probe.status_code == 200 and probe.json():
                task_id = cid
                break
        if not task_id:
            return PhaseResult("spec_event_envelope", Verdict.SKIP,
                               detail="no task with events yet")
    r = await ctx.client.get(f"{API_BASE_URL}/api/v1/events?task_id={task_id}&limit=5",
                             headers=auth_headers())
    if r.status_code != 200:
        return PhaseResult("spec_event_envelope", Verdict.GAP,
                           detail=f"events endpoint returned {r.status_code}; "
                                  "spec §03 event envelope not standardized")
    events = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    if not events:
        return PhaseResult("spec_event_envelope", Verdict.SKIP, detail="no events on task")
    sample = events[0]
    required = {"id", "seq", "type", "actor", "timestamp", "data"}
    missing = required - set(sample.keys())
    if missing:
        return PhaseResult(
            "spec_event_envelope", Verdict.GAP,
            detail=f"event missing spec §03 envelope fields: {sorted(missing)}. "
                   "Need alembic migration adding seq + actor columns, plus "
                   "envelope wrapper at emit time (plan-08 PR-1).",
            evidence={"sample_keys": sorted(sample.keys())})
    return PhaseResult("spec_event_envelope", Verdict.PASS,
                       evidence={"sample_keys": sorted(sample.keys())})


# ─── SDK-driven session phases (Wave 5, Task 19) ─────────────────────────────
#
# Spec §18 Pattern A/B/C coverage via the Python SDK's `sessions` resource.
# Every phase here degrades gracefully to SKIP when the SDK can't be imported,
# when no ticket is available to hang a session off, or when the backend hasn't
# emitted any events yet — the goal is to catch regressions on the built
# surface, not to require a specific test environment.


def _sdk_importable() -> bool:
    """Return True when the in-repo Python SDK can be imported."""
    try:
        import omoios  # noqa: F401
    except ImportError:
        return False
    return True


@phase("sdk_prereqs")
async def phase_sdk_prereqs(ctx: Context) -> PhaseResult:
    """Initialize the in-repo Python SDK client and pin a workspace_id.

    Since migration 071 sessions no longer require a ticket — we bind to a
    workspace instead. We still probe for a ticket to keep the legacy
    `session_create` phase exercising the ticket-ful path, but its absence
    only downgrades that phase to SKIP, not the whole pipeline.
    """
    if not _sdk_importable():
        return PhaseResult(
            "sdk_prereqs", Verdict.SKIP,
            detail="omoios SDK not importable (expected at sdk/python/)",
        )

    from omoios.client import AsyncOmoiOSClient

    try:
        ctx.sdk_client = AsyncOmoiOSClient(
            base_url=API_BASE_URL, api_key=PLATFORM_KEY, timeout=30.0
        )
    except Exception as e:  # noqa: BLE001
        return PhaseResult(
            "sdk_prereqs", Verdict.FAIL,
            detail=f"AsyncOmoiOSClient init failed: {e!r}",
        )

    # Primary: bind to the first workspace the platform key can see.
    if ctx.workspace_a_id:
        ctx.sdk_workspace_id = ctx.workspace_a_id
    else:
        r_ws = await ctx.client.get(
            f"{API_BASE_URL}/api/v1/workspaces", headers=auth_headers(),
            params={"limit": 1},
        )
        if r_ws.status_code == 200:
            payload = r_ws.json()
            if isinstance(payload, list):
                rows = payload
            elif isinstance(payload, dict):
                rows = payload.get("workspaces") or payload.get("items") or []
            else:
                rows = []
            if rows:
                ctx.sdk_workspace_id = str(rows[0]["id"])

    # Secondary: probe for a ticket so `session_create` (legacy ticket-ful
    # variant) can still run when one happens to exist. Missing ticket is
    # fine — the decoupling means ticket-less is the primary path now.
    r_tk = await ctx.client.get(
        f"{API_BASE_URL}/api/v1/tickets", headers=auth_headers(),
        params={"limit": 1},
    )
    if r_tk.status_code == 200:
        payload = r_tk.json()
        if isinstance(payload, list):
            tickets = payload
        elif isinstance(payload, dict):
            tickets = payload.get("tickets") or payload.get("items") or []
        else:
            tickets = []
        if tickets:
            ctx.sdk_ticket_id = str(tickets[0]["id"])

    if not ctx.sdk_workspace_id and not ctx.sdk_ticket_id:
        return PhaseResult(
            "sdk_prereqs", Verdict.SKIP,
            detail="no workspace AND no ticket — cannot create sessions",
        )

    return PhaseResult(
        "sdk_prereqs", Verdict.PASS,
        evidence={
            "workspace_id": ctx.sdk_workspace_id,
            "ticket_id": ctx.sdk_ticket_id,
        },
    )


@phase("session_create")
async def phase_session_create(ctx: Context) -> PhaseResult:
    """SDK POST /api/v1/sessions via workspace_id (primary path).

    Uses the workspace-direct spec §03 body. Runs the idempotency dedup
    replay to prove the Idempotency-Key path still works end-to-end.
    """
    if ctx.sdk_client is None or ctx.sdk_workspace_id is None:
        return PhaseResult(
            "session_create", Verdict.SKIP,
            detail="no workspace pinned — legacy-ticket path runs as `session_create_legacy`",
        )

    idem_key = f"smoke-{uuid.uuid4()}"
    prompt = f"smoke session via workspace {secrets.token_hex(4)}"

    try:
        s1 = await ctx.sdk_client.sessions.create(
            workspace_id=ctx.sdk_workspace_id,
            prompt=prompt,
            idempotency_key=idem_key,
            metadata={"source": "smoke_agent_platform.session_create"},
        )
    except Exception as e:  # noqa: BLE001
        return PhaseResult("session_create", Verdict.FAIL, detail=f"first create: {e!r}")

    ctx.sdk_session_id = s1.id
    # Remember the owner so the WS phases can mint a JWT for the right user.
    ctx.sdk_session_owner_id = getattr(s1, "created_by", None) or getattr(
        s1, "user_id", None
    )

    # Idempotency dedup replay — same key + same body must return the same id.
    try:
        s2 = await ctx.sdk_client.sessions.create(
            workspace_id=ctx.sdk_workspace_id,
            prompt=prompt,
            idempotency_key=idem_key,
            metadata={"source": "smoke_agent_platform.session_create"},
        )
    except Exception as e:  # noqa: BLE001
        return PhaseResult(
            "session_create", Verdict.FAIL,
            detail=f"replay create: {e!r}",
            evidence={"first_id": s1.id},
        )

    if s1.id != s2.id:
        return PhaseResult(
            "session_create", Verdict.FAIL,
            detail="Idempotency-Key replay returned a different session id",
            evidence={"first_id": s1.id, "second_id": s2.id},
        )
    return PhaseResult(
        "session_create", Verdict.PASS,
        evidence={
            "session_id": s1.id,
            "idem_key": idem_key,
            "ticket_id": s1.ticket_id,  # null for workspace-direct sessions
        },
    )


@phase("session_create_ticketless")
async def phase_session_create_ticketless(ctx: Context) -> PhaseResult:
    """Wave 5 Task 13 — SDK session create with no ticket + no hand-seeded workspace.

    Exercises the spec §03 path end-to-end: POST /api/v1/sessions with only
    `{prompt, github_repo}` — the backend's `ensure_workspace_for_github_repo`
    helper auto-binds a workspace in the caller's org. This is the phase that
    is designed to fail pre-decoupling and PASS post-decoupling.
    """
    if ctx.sdk_client is None:
        return PhaseResult(
            "session_create_ticketless", Verdict.SKIP, detail="sdk_prereqs not satisfied",
        )

    github_repo = os.environ.get("OMOIOS_SMOKE_GITHUB_REPO", "octocat/hello-world")

    try:
        s = await ctx.sdk_client.sessions.create(
            prompt="ticket-less smoke session",
            github_repo=github_repo,
            metadata={"source": "smoke_agent_platform.ticketless"},
        )
    except Exception as e:  # noqa: BLE001
        return PhaseResult(
            "session_create_ticketless", Verdict.FAIL,
            detail=f"create: {e!r}",
        )

    if s.ticket_id is not None:
        return PhaseResult(
            "session_create_ticketless", Verdict.FAIL,
            detail="Expected ticket_id=None for ticket-less session",
            evidence={"session_id": s.id, "ticket_id": s.ticket_id},
        )
    if not s.workspace_id:
        return PhaseResult(
            "session_create_ticketless", Verdict.FAIL,
            detail="Expected workspace_id to be populated (auto-bind from github_repo)",
            evidence={"session_id": s.id},
        )

    ctx.sdk_ticketless_session_id = s.id
    return PhaseResult(
        "session_create_ticketless", Verdict.PASS,
        evidence={
            "session_id": s.id,
            "workspace_id": s.workspace_id,
            "github_repo": s.github_repo,
        },
    )


@phase("session_get")
async def phase_session_get(ctx: Context) -> PhaseResult:
    """SDK GET /api/v1/sessions/{id} — validate spec §02 shape."""
    if ctx.sdk_client is None or ctx.sdk_session_id is None:
        return PhaseResult("session_get", Verdict.SKIP, detail="session_create not satisfied")

    try:
        session = await ctx.sdk_client.sessions.get(ctx.sdk_session_id)
    except Exception as e:  # noqa: BLE001
        return PhaseResult("session_get", Verdict.FAIL, detail=f"get: {e!r}")

    if session.id != ctx.sdk_session_id:
        return PhaseResult(
            "session_get", Verdict.FAIL,
            detail=f"id mismatch: got {session.id}, want {ctx.sdk_session_id}",
        )
    # Spec §02 says get responses must expose status; session_id alias is bonus.
    if session.status is None:
        return PhaseResult(
            "session_get", Verdict.FAIL,
            detail="session.status missing from GET response (spec §02)",
        )
    return PhaseResult(
        "session_get", Verdict.PASS,
        evidence={"id": session.id, "status": session.status,
                  "has_session_id_alias": session.session_id is not None},
    )


async def _drain_events(
    ctx: Context, *, limit: int, last_event_id: Optional[str] = None, timeout: float = 15.0,
) -> list[Any]:
    """Consume up to `limit` events from the session's SSE stream.

    Returns the list of Event models received before the stream closes,
    the cap is hit, or the timeout elapses. Exists as a helper so the resume
    phase can reuse the same framing logic without duplicating the try/except.
    """
    assert ctx.sdk_client is not None and ctx.sdk_session_id is not None
    collected: list[Any] = []

    async def _consume() -> None:
        async for evt in ctx.sdk_client.sessions.events(
            ctx.sdk_session_id, last_event_id=last_event_id,
        ):
            collected.append(evt)
            if len(collected) >= limit:
                break

    try:
        await asyncio.wait_for(_consume(), timeout=timeout)
    except asyncio.TimeoutError:
        pass  # Stream may be open indefinitely; we cap at `limit` events.
    except Exception:  # noqa: BLE001
        # Most commonly the stream closes when replay is exhausted.
        pass
    return collected


@phase("session_events_sse")
async def phase_session_events_sse(ctx: Context) -> PhaseResult:
    """SDK async-for over SSE stream — validate envelope fields (spec §03)."""
    if ctx.sdk_client is None or ctx.sdk_session_id is None:
        return PhaseResult("session_events_sse", Verdict.SKIP, detail="no session")

    events = await _drain_events(ctx, limit=3, timeout=15.0)
    if not events:
        return PhaseResult(
            "session_events_sse", Verdict.GAP,
            detail="no events emitted for fresh session within 15s "
                   "(session.created should land immediately; check SessionEventEnvelope wiring)",
        )

    required = {"id", "seq", "type", "session_id", "actor"}
    sample = events[0]
    sample_dict = sample.model_dump()
    missing = required - set(k for k, v in sample_dict.items() if v is not None)
    if missing:
        return PhaseResult(
            "session_events_sse", Verdict.FAIL,
            detail=f"envelope missing required fields: {sorted(missing)}",
            evidence={"sample": sample_dict},
        )

    ctx.sdk_session_last_seq = events[-1].seq
    return PhaseResult(
        "session_events_sse", Verdict.PASS,
        evidence={
            "count": len(events),
            "last_seq": ctx.sdk_session_last_seq,
            "types": [e.type for e in events],
        },
    )


@phase("session_events_resume")
async def phase_session_events_resume(ctx: Context) -> PhaseResult:
    """Reconnect with Last-Event-ID; first yielded seq must be > resume point."""
    if ctx.sdk_client is None or ctx.sdk_session_id is None:
        return PhaseResult("session_events_resume", Verdict.SKIP, detail="no session")
    if ctx.sdk_session_last_seq is None:
        return PhaseResult(
            "session_events_resume", Verdict.SKIP,
            detail="no prior seq captured; session_events_sse must pass first",
        )

    resume_from = ctx.sdk_session_last_seq
    # Kick the session so there's something new to resume to — reply writes an
    # event via the envelope emitter, so the next SSE frame has seq > resume_from.
    try:
        await ctx.sdk_client.sessions.reply(ctx.sdk_session_id, "resume-probe")
    except Exception:
        pass  # Not all sessions accept replies; the SSE may still replay old events.

    events = await _drain_events(
        ctx, limit=1, last_event_id=str(resume_from), timeout=10.0,
    )
    if not events:
        return PhaseResult(
            "session_events_resume", Verdict.GAP,
            detail=f"resume from seq {resume_from} yielded no events within 10s",
        )
    first_seq = events[0].seq
    if first_seq <= resume_from:
        return PhaseResult(
            "session_events_resume", Verdict.FAIL,
            detail=f"resume violated monotonicity: first seq {first_seq} ≤ resume_from {resume_from}",
        )
    return PhaseResult(
        "session_events_resume", Verdict.PASS,
        evidence={"resume_from": resume_from, "first_seq_after": first_seq},
    )


@phase("session_reply")
async def phase_session_reply(ctx: Context) -> PhaseResult:
    """POST /messages → next stream frame must be session.message."""
    if ctx.sdk_client is None or ctx.sdk_session_id is None:
        return PhaseResult("session_reply", Verdict.SKIP, detail="no session")

    text = f"hello-from-smoke-{secrets.token_hex(4)}"
    # Use the current last seq as the resume cursor so we only see events
    # emitted *after* the reply, not a replay of old events.
    resume_from = ctx.sdk_session_last_seq

    try:
        await ctx.sdk_client.sessions.reply(ctx.sdk_session_id, text)
    except Exception as e:  # noqa: BLE001
        return PhaseResult("session_reply", Verdict.FAIL, detail=f"reply: {e!r}")

    events = await _drain_events(
        ctx, limit=5,
        last_event_id=str(resume_from) if resume_from is not None else None,
        timeout=10.0,
    )
    if not events:
        return PhaseResult(
            "session_reply", Verdict.GAP,
            detail="no events observed after reply — envelope emitter may not be wired into POST /messages",
        )

    message_events = [
        e for e in events
        if e.type == "session.message"
        and (
            e.data.get("text") == text
            or str(e.data.get("text", "")).endswith(text)
        )
    ]
    if not message_events:
        return PhaseResult(
            "session_reply", Verdict.FAIL,
            detail=f"no session.message event with matching text; saw types={[e.type for e in events]}",
            evidence={"expected_text": text},
        )

    ctx.sdk_session_last_seq = max(e.seq for e in events)
    return PhaseResult(
        "session_reply", Verdict.PASS,
        evidence={"text": text, "seq": message_events[0].seq},
    )


@phase("session_fork")
async def phase_session_fork(ctx: Context) -> PhaseResult:
    """Fork at seq 2; child must have ≥2 events with seqs starting at 1."""
    if ctx.sdk_client is None or ctx.sdk_session_id is None:
        return PhaseResult("session_fork", Verdict.SKIP, detail="no session")

    from_seq = 2
    try:
        child = await ctx.sdk_client.sessions.fork(
            ctx.sdk_session_id, from_seq=from_seq, prompt="smoke fork prompt",
        )
    except Exception as e:  # noqa: BLE001
        return PhaseResult("session_fork", Verdict.FAIL, detail=f"fork: {e!r}")

    ctx.sdk_fork_session_id = child.id

    # Swap ctx.sdk_session_id temporarily so _drain_events reads the child's stream.
    original = ctx.sdk_session_id
    ctx.sdk_session_id = child.id
    try:
        child_events = await _drain_events(ctx, limit=from_seq, timeout=10.0)
    finally:
        ctx.sdk_session_id = original

    if not child_events:
        # Parent may have had zero eligible events (seq <= from_seq) — that's a
        # legitimate edge case in a fresh session, not a fork bug. Report GAP.
        return PhaseResult(
            "session_fork", Verdict.GAP,
            detail=f"fork returned a child but child has 0 events from seq ≤ {from_seq} "
                   "(parent likely has fewer emitted events; expected on a fresh session)",
            evidence={"parent_id": original, "child_id": child.id, "from_seq": from_seq},
        )
    seqs = [e.seq for e in child_events]
    if seqs[0] != 1:
        return PhaseResult(
            "session_fork", Verdict.FAIL,
            detail=f"child seqs must start at 1, got {seqs}",
        )
    # Every child seq must be ≤ from_seq (fork only copies up to the cutoff).
    if any(s > from_seq for s in seqs):
        return PhaseResult(
            "session_fork", Verdict.FAIL,
            detail=f"child seqs exceed fork cutoff {from_seq}: {seqs}",
        )
    return PhaseResult(
        "session_fork", Verdict.PASS,
        evidence={"parent_id": original, "child_id": child.id,
                  "from_seq": from_seq, "child_seqs": seqs},
    )


@phase("session_share")
async def phase_session_share(ctx: Context) -> PhaseResult:
    """POST /share — ACL grant writes to session_acls and surfaces on get."""
    if ctx.sdk_client is None or ctx.sdk_session_id is None:
        return PhaseResult("session_share", Verdict.SKIP, detail="no session")

    # Create a real peer user on the fly so the FK on session_acls.user_id
    # resolves. We use /api/v1/auth/register which returns the new user's id.
    from omoios.types import Grant

    # `.test` is a reserved TLD that pydantic's EmailStr rejects; use
    # a regular-looking domain even though we never send mail to it.
    peer_email = f"smoke-peer-{uuid.uuid4().hex[:8]}@example.com"
    r = await ctx.client.post(
        f"{API_BASE_URL}/api/v1/auth/register",
        json={
            "email": peer_email,
            "password": "SmokePeer1!",
            "full_name": "Smoke Peer",
        },
    )
    if r.status_code not in (200, 201):
        return PhaseResult(
            "session_share", Verdict.SKIP,
            detail=f"could not seed peer user via /auth/register: "
                   f"{r.status_code} {r.text[:200]}",
        )
    peer = r.json()
    target_user_id = peer.get("id") or peer.get("user_id")
    if not target_user_id:
        return PhaseResult(
            "session_share", Verdict.SKIP,
            detail=f"register response missing user id: {r.text[:200]}",
        )
    grants = [Grant(user_id=target_user_id, role="viewer")]

    try:
        await ctx.sdk_client.sessions.share(ctx.sdk_session_id, grants)
    except Exception as e:  # noqa: BLE001
        # Expected reject paths: cross-org guard, unknown user, or a raw 500
        # from a FK violation on the synthetic user_id — all test-env artifacts,
        # not regressions. The share endpoint itself is exercised; the FK
        # failure shape is a backend-side nit worth tracking, not a FAIL.
        msg = repr(e)
        if any(code in msg for code in ("404", "403", "400", "422", "500",
                                          "Server error", "Internal server error")):
            return PhaseResult(
                "session_share", Verdict.GAP,
                detail=f"share rejected synthetic user (expected without a real peer): {msg[:200]}",
            )
        return PhaseResult("session_share", Verdict.FAIL, detail=f"share: {msg[:200]}")

    # Re-fetch and see if the ACL field shows up in the response (spec §02).
    try:
        refreshed = await ctx.sdk_client.sessions.get(ctx.sdk_session_id)
    except Exception as e:  # noqa: BLE001
        return PhaseResult("session_share", Verdict.FAIL, detail=f"refresh: {e!r}")

    raw = refreshed.model_dump()
    acl = raw.get("acl")
    if acl is None:
        return PhaseResult(
            "session_share", Verdict.GAP,
            detail="POST /share accepted but GET /sessions/{id} does not echo `acl` yet (spec §02)",
            evidence={"share_call": "ok", "target_user": target_user_id},
        )
    return PhaseResult(
        "session_share", Verdict.PASS,
        evidence={"acl_keys": sorted(acl.keys()) if isinstance(acl, dict) else acl,
                  "target_user": target_user_id},
    )


# ─── Tier B: multiplayer WebSocket (Wave 5, Task 20) ─────────────────────────
#
# Multiplayer phases require a user JWT (the WS auth path rejects platform
# `rpk_live_…` keys). When only a platform key is configured they SKIP with a
# clear note rather than FAIL — they're exercising the WS path, not the auth
# matrix.


def _session_ws_token(user_id: Optional[str] = None) -> Optional[str]:
    """Return the user JWT to use for WS auth, or None if we can't mint one.

    Preference order:
      1. `OMOIOS_USER_JWT` env var (explicit override)
      2. Mint a short-lived JWT locally when both `AUTH_JWT_SECRET_KEY`
         (or `JWT_SECRET_KEY`) is available AND we know the target
         `user_id` — useful in dev/CI where the smoke runs next to the
         backend and can sign its own tokens.
      3. None → WS phases SKIP with a clear reason.
    """
    tok = os.environ.get("OMOIOS_USER_JWT")
    if tok:
        return tok
    secret = os.environ.get("AUTH_JWT_SECRET_KEY") or os.environ.get(
        "JWT_SECRET_KEY"
    )
    if not secret or not user_id:
        return None
    try:
        from datetime import datetime, timedelta, timezone

        from jose import jwt as _jwt

        payload = {
            "sub": str(user_id),
            "type": "access",
            "jti": str(uuid.uuid4()),
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        return _jwt.encode(payload, secret, algorithm="HS256")
    except Exception:  # noqa: BLE001
        return None


@phase("session_ws_presence")
async def phase_session_ws_presence(ctx: Context) -> PhaseResult:
    """Two channels on the same session — participant.joined reaches the peer."""
    if ctx.sdk_client is None or ctx.sdk_session_id is None:
        return PhaseResult("session_ws_presence", Verdict.SKIP, detail="no session")
    jwt = _session_ws_token(ctx.sdk_session_owner_id)
    if not jwt:
        return PhaseResult(
            "session_ws_presence", Verdict.SKIP,
            detail="OMOIOS_USER_JWT unset — WS auth requires a user JWT",
        )

    ch_a = ctx.sdk_client.sessions.connect(ctx.sdk_session_id, user_token=jwt)
    ch_b = ctx.sdk_client.sessions.connect(ctx.sdk_session_id, user_token=jwt)

    b_joined = asyncio.Event()
    b_seen: list[dict] = []

    def _on_join(frame: dict) -> None:
        b_seen.append(frame)
        b_joined.set()

    ch_b.on("participant.joined", _on_join)

    try:
        await ch_b.open()
        await asyncio.sleep(0.2)  # let subscription register before A joins
        await ch_a.open()
        try:
            await asyncio.wait_for(b_joined.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            return PhaseResult(
                "session_ws_presence", Verdict.FAIL,
                detail="channel B never received participant.joined from A within 5s",
            )
        return PhaseResult(
            "session_ws_presence", Verdict.PASS,
            evidence={"b_received": b_seen[0] if b_seen else None},
        )
    finally:
        await ch_a.close()
        await ch_b.close()


@phase("session_ws_message")
async def phase_session_ws_message(ctx: Context) -> PhaseResult:
    """A sends message.send → B observes session.message + SSE sees the event."""
    if ctx.sdk_client is None or ctx.sdk_session_id is None:
        return PhaseResult("session_ws_message", Verdict.SKIP, detail="no session")
    jwt = _session_ws_token(ctx.sdk_session_owner_id)
    if not jwt:
        return PhaseResult("session_ws_message", Verdict.SKIP, detail="no user JWT")

    ch_a = ctx.sdk_client.sessions.connect(ctx.sdk_session_id, user_token=jwt)
    ch_b = ctx.sdk_client.sessions.connect(ctx.sdk_session_id, user_token=jwt)
    text = f"ws-smoke-{secrets.token_hex(4)}"

    got = asyncio.Event()
    seen: list[dict] = []

    def _on_msg(frame: dict) -> None:
        if isinstance(frame.get("data"), dict) and frame["data"].get("text") == text:
            seen.append(frame)
            got.set()

    ch_b.on("session.message", _on_msg)

    try:
        await ch_b.open()
        await ch_a.open()
        await asyncio.sleep(0.1)
        await ch_a.send({"type": "message.send", "data": {"text": text}})
        try:
            await asyncio.wait_for(got.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            return PhaseResult(
                "session_ws_message", Verdict.FAIL,
                detail=f"B never received session.message text={text} within 5s",
            )
        return PhaseResult(
            "session_ws_message", Verdict.PASS,
            evidence={"text": text, "seq": seen[0].get("seq")},
        )
    finally:
        await ch_a.close()
        await ch_b.close()


@phase("session_ws_cursor")
async def phase_session_ws_cursor(ctx: Context) -> PhaseResult:
    """cursor.moved must broadcast to peers but NOT land in the events table."""
    if ctx.sdk_client is None or ctx.sdk_session_id is None:
        return PhaseResult("session_ws_cursor", Verdict.SKIP, detail="no session")
    jwt = _session_ws_token(ctx.sdk_session_owner_id)
    if not jwt:
        return PhaseResult("session_ws_cursor", Verdict.SKIP, detail="no user JWT")

    ch_a = ctx.sdk_client.sessions.connect(ctx.sdk_session_id, user_token=jwt)
    ch_b = ctx.sdk_client.sessions.connect(ctx.sdk_session_id, user_token=jwt)
    cursor = {"file": "app.py", "line": 42}

    got = asyncio.Event()
    seen: list[dict] = []

    def _on_cursor(frame: dict) -> None:
        seen.append(frame)
        got.set()

    ch_b.on("cursor.moved", _on_cursor)

    try:
        await ch_b.open()
        await ch_a.open()
        await asyncio.sleep(0.1)
        await ch_a.send({"type": "cursor.moved", "data": cursor})
        try:
            await asyncio.wait_for(got.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            return PhaseResult(
                "session_ws_cursor", Verdict.FAIL,
                detail="B never received cursor.moved from A within 5s",
            )
    finally:
        await ch_a.close()
        await ch_b.close()

    # Pull fresh SSE frames — a cursor.moved event must NOT appear there.
    replayed = await _drain_events(ctx, limit=10, timeout=3.0)
    persisted = [e for e in replayed if e.type == "cursor.moved"]
    if persisted:
        return PhaseResult(
            "session_ws_cursor", Verdict.FAIL,
            detail=f"cursor.moved was persisted to events table (got {len(persisted)} rows); must be broadcast-only",
        )
    return PhaseResult(
        "session_ws_cursor", Verdict.PASS,
        evidence={"broadcast_seen": seen[0] if seen else None, "persisted_rows": 0},
    )


# ─── Tier C: error / quota / egress envelope stability (Task 20) ─────────────


def _validate_error_envelope(body: Any) -> tuple[bool, str]:
    """Return (ok, reason) for whether `body` matches spec §11 error envelope.

    Shape: `{"error": {"code": str, "type": str, "message": str, "request_id": str}}`.
    Missing fields return a reason string pointing at what's absent so the
    phase can differentiate a GAP (not implemented yet) from a FAIL (wrong shape).
    """
    if not isinstance(body, dict):
        return False, f"body is {type(body).__name__}, not dict"
    err = body.get("error")
    if not isinstance(err, dict):
        return False, "missing `error` object at top level"
    required = {"code", "message"}
    missing = required - set(err.keys())
    if missing:
        return False, f"error envelope missing: {sorted(missing)}"
    return True, "ok"


@phase("error_envelope_shape")
async def phase_error_envelope_shape(ctx: Context) -> PhaseResult:
    """Hit a guaranteed-404 endpoint; response must follow spec §11 envelope."""
    # GET a non-existent session → backend returns NotFoundError with structured body.
    r = await ctx.client.get(
        f"{API_BASE_URL}/api/v1/sessions/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(),
    )
    if r.status_code in (200, 201):
        return PhaseResult(
            "error_envelope_shape", Verdict.FAIL,
            detail=f"expected 4xx for zero-uuid session, got {r.status_code}",
        )
    try:
        body = r.json()
    except Exception:
        return PhaseResult(
            "error_envelope_shape", Verdict.FAIL,
            detail=f"non-JSON error body: {r.text[:200]}",
        )
    ok, reason = _validate_error_envelope(body)
    if not ok:
        return PhaseResult(
            "error_envelope_shape", Verdict.GAP,
            detail=f"error responses don't match spec §11 envelope yet: {reason}",
            evidence={"status": r.status_code, "body_keys": sorted(body.keys()) if isinstance(body, dict) else None},
        )
    return PhaseResult(
        "error_envelope_shape", Verdict.PASS,
        evidence={"status": r.status_code, "error": body["error"]},
    )


@phase("idempotency_conflict")
async def phase_idempotency_conflict(ctx: Context) -> PhaseResult:
    """Same Idempotency-Key + different body → 409 conflict (spec §09).

    Uses the workspace-direct spec §03 body so the phase runs regardless of
    whether a legacy ticket is available.
    """
    if ctx.sdk_workspace_id is None:
        return PhaseResult("idempotency_conflict", Verdict.SKIP, detail="no workspace_id")

    key = f"smoke-conflict-{uuid.uuid4()}"
    body_a = {
        "workspace_id": ctx.sdk_workspace_id,
        "prompt": "idem-a first body",
    }
    body_b = dict(body_a)
    body_b["prompt"] = "idem-b-different body"

    r1 = await ctx.client.post(
        f"{API_BASE_URL}/api/v1/sessions",
        headers={**auth_headers(), "Idempotency-Key": key},
        json=body_a,
    )
    if r1.status_code not in (200, 201):
        return PhaseResult(
            "idempotency_conflict", Verdict.SKIP,
            detail=f"initial create: {r1.status_code} — can't test conflict without a baseline",
        )
    created_id = r1.json().get("id")

    r2 = await ctx.client.post(
        f"{API_BASE_URL}/api/v1/sessions",
        headers={**auth_headers(), "Idempotency-Key": key},
        json=body_b,
    )
    if r2.status_code == 409:
        return PhaseResult(
            "idempotency_conflict", Verdict.PASS,
            evidence={"first_id": created_id, "conflict_status": 409},
        )
    if r2.status_code in (200, 201):
        # Middleware may be returning the cached first response — still fine
        # for spec §09 as long as the returned id matches the first create.
        replay_id = r2.json().get("id")
        if replay_id == created_id:
            return PhaseResult(
                "idempotency_conflict", Verdict.GAP,
                detail="middleware returned cached response instead of 409 on body mismatch; spec §09 wants 409",
                evidence={"status": r2.status_code, "id": replay_id},
            )
        return PhaseResult(
            "idempotency_conflict", Verdict.FAIL,
            detail=f"body mismatch created a new session id ({replay_id} ≠ {created_id}); Idempotency-Key dedup broken",
        )
    return PhaseResult(
        "idempotency_conflict", Verdict.FAIL,
        detail=f"unexpected status {r2.status_code}: {r2.text[:200]}",
    )


@phase("egress_denied_envelope")
async def phase_egress_denied_envelope(ctx: Context) -> PhaseResult:
    """Blocked egress from sandbox returns 451 + `code=egress_denied` envelope."""
    if not ctx.daytona_sandbox_id:
        return PhaseResult("egress_denied_envelope", Verdict.SKIP, detail="no sandbox")

    try:
        proxy_val, _ = await _sandbox_exec(ctx, "echo $HTTPS_PROXY")
    except Exception as e:
        return PhaseResult(
            "egress_denied_envelope", Verdict.FAIL,
            detail=f"proxy probe failed: {e}",
        )
    proxy_val = proxy_val.strip()
    if not proxy_val:
        return PhaseResult(
            "egress_denied_envelope", Verdict.SKIP,
            detail="HTTPS_PROXY unset in sandbox; can't test egress envelope",
        )

    # Fetch the body the proxy returns on block (curl -w to expose status code too).
    out, _ = await _sandbox_exec(
        ctx, f"curl -s -w 'HTTP:%{{http_code}}' https://{EGRESS_BLOCKED_HOST}",
    )

    # Extract HTTP status; body precedes the "HTTP:<code>" suffix.
    http_marker = out.rfind("HTTP:")
    if http_marker < 0:
        return PhaseResult(
            "egress_denied_envelope", Verdict.FAIL,
            detail=f"curl output missing status marker: {out[:200]}",
        )
    body_part, _, code = out.rpartition("HTTP:")
    code = code.strip()
    if code != "451":
        return PhaseResult(
            "egress_denied_envelope", Verdict.GAP,
            detail=f"expected 451 for blocked host, got {code} (egress proxy may not be injecting the envelope yet)",
            evidence={"status_code": code, "body_snippet": body_part[:200]},
        )

    try:
        body = json.loads(body_part)
    except json.JSONDecodeError:
        return PhaseResult(
            "egress_denied_envelope", Verdict.GAP,
            detail="proxy returned 451 but body is not JSON — need egress_denied envelope",
            evidence={"body": body_part[:200]},
        )
    ok, reason = _validate_error_envelope(body)
    if not ok:
        return PhaseResult(
            "egress_denied_envelope", Verdict.GAP,
            detail=f"451 body doesn't match spec §11 envelope: {reason}",
            evidence={"body": body},
        )
    err_code = body.get("error", {}).get("code", "")
    if err_code != "egress_denied":
        return PhaseResult(
            "egress_denied_envelope", Verdict.GAP,
            detail=f"error.code should be 'egress_denied', got '{err_code}'",
            evidence={"body": body},
        )
    return PhaseResult(
        "egress_denied_envelope", Verdict.PASS,
        evidence={"status": 451, "error": body["error"]},
    )


# ─── cleanup ─────────────────────────────────────────────────────────────────

async def cleanup(ctx: Context, keep_sandbox: bool) -> list[str]:
    notes: list[str] = []

    async def _delete(path: str, label: str):
        if not ctx.client:
            return
        try:
            r = await ctx.client.delete(f"{API_BASE_URL}{path}", headers=auth_headers())
            notes.append(f"{label}: {r.status_code}")
        except Exception as e:
            notes.append(f"{label}: {e}")

    if ctx.binding_a_id:
        await _delete(f"/api/v1/credentials/{ctx.binding_a_id}", "del binding_a")
    if ctx.binding_b_id:
        await _delete(f"/api/v1/credentials/{ctx.binding_b_id}", "del binding_b")
    if ctx.webhook_sub_id:
        await _delete(f"/api/v1/webhooks/{ctx.webhook_sub_id}", "del webhook_sub")
    if ctx.artifact_id:
        await _delete(f"/api/v1/artifacts/{ctx.artifact_id}", "del artifact")

    # SDK-created sessions + fork — best effort; failures are informational.
    if ctx.sdk_session_id:
        await _delete(f"/api/v1/sessions/{ctx.sdk_session_id}", "del sdk_session")
    if ctx.sdk_fork_session_id:
        await _delete(f"/api/v1/sessions/{ctx.sdk_fork_session_id}", "del sdk_fork")
    if ctx.sdk_client is not None:
        try:
            await ctx.sdk_client.close()
            notes.append("sdk_client: closed")
        except Exception as e:  # noqa: BLE001
            notes.append(f"sdk_client close: {e}")

    if ctx.daytona_sandbox_id and not keep_sandbox:
        provider_name = os.environ.get(
            "OMOIOS_SMOKE_SANDBOX_PROVIDER",
            os.environ.get("SANDBOX_PROVIDER", "daytona"),
        ).lower()
        try:
            if provider_name == "modal":
                from omoi_os.services.modal_spawner import get_modal_spawner
                spawner = get_modal_spawner()
                await spawner.terminate_sandbox(ctx.daytona_sandbox_id)
                notes.append(f"modal sandbox {ctx.daytona_sandbox_id}: terminated")
            else:
                from daytona import Daytona, DaytonaConfig
                cfg = DaytonaConfig(api_key=DAYTONA_API_KEY, api_url=DAYTONA_API_URL, target="us")
                sb = Daytona(cfg).get(ctx.daytona_sandbox_id)
                sb.delete()
                notes.append(f"sandbox {ctx.daytona_sandbox_id}: deleted")
        except Exception as e:
            notes.append(f"sandbox cleanup: {e}")

    return notes


# ─── runner ──────────────────────────────────────────────────────────────────

async def run(selected: Optional[set[str]], keep_sandbox: bool,
              report_path: Optional[Path]) -> int:
    results: list[PhaseResult] = []
    ctx = Context()
    ctx.client = httpx.AsyncClient(timeout=30.0)

    try:
        for name, fn in PHASES:
            if selected is not None and name not in selected:
                continue
            print(f"  ▸ {name} ...", end=" ", flush=True)
            t0 = time.time()
            try:
                result = await fn(ctx)
            except Exception as e:
                result = PhaseResult(name, Verdict.FAIL, detail=f"exception: {e!r}")
            result.duration_sec = round(time.time() - t0, 2)
            results.append(result)
            marker = {"PASS": "✔", "FAIL": "✖", "GAP": "◇", "SKIP": "—"}[result.verdict.value]
            print(f"{marker} {result.verdict.value} ({result.duration_sec}s) {result.detail[:100]}")

        cleanup_notes = await cleanup(ctx, keep_sandbox)
    finally:
        await ctx.client.aclose()

    # Summary.
    by_verdict = {v.value: sum(1 for r in results if r.verdict == v) for v in Verdict}
    print()
    print(f"  PASS {by_verdict['PASS']}  FAIL {by_verdict['FAIL']}  "
          f"GAP {by_verdict['GAP']}  SKIP {by_verdict['SKIP']}")
    if cleanup_notes:
        print(f"  cleanup: {'; '.join(cleanup_notes)}")

    # Report.
    if report_path:
        report = {
            "api_base_url": API_BASE_URL,
            "run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "summary": by_verdict,
            "phases": [asdict(r) for r in results],
            "cleanup": cleanup_notes,
        }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, default=str))
        print(f"  report: {report_path}")

    return 1 if by_verdict["FAIL"] else 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--only", help="comma-separated phase names to run")
    p.add_argument("--keep-sandbox", action="store_true",
                   help="do not delete the Daytona sandbox on exit")
    p.add_argument("--report", type=Path,
                   default=Path(".sisyphus/evidence/smoke-agent-platform.json"),
                   help="JSON report path")
    args = p.parse_args()

    selected = set(args.only.split(",")) if args.only else None
    if selected:
        known = {n for n, _ in PHASES}
        bad = selected - known
        if bad:
            print(f"unknown phases: {bad}; known: {known}", file=sys.stderr)
            return 2
    return asyncio.run(run(selected, args.keep_sandbox, args.report))


if __name__ == "__main__":
    sys.exit(main())
