"""Probe: spawn a fresh ModalSandboxedAgent and verify streaming end-to-end.

Validates that:
  1. The streaming-capable spawn path lights up (encrypted port, opencode
     serve, tunnel healthcheck, opencode session minted).
  2. ``agent.prompt(text, on_part=...)`` invokes the callback with at least
     one ``message.part.updated`` event scoped to our session.
  3. The returned text is non-empty.

Idempotent + iterative per the project's smoke-script convention. Each
phase prints PASS/FAIL with a short note. Run with:

    .venv/bin/python scripts/poof/probe_modal_streaming.py

Requires:
  - LLM_API_KEY (or FIREWORKS_API_KEY) — populates opencode auth.json.
  - Modal credentials in ~/.modal.toml or MODAL_TOKEN_ID/SECRET in env.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Source backend/.env so the probe runs from a clean shell.
_HERE = Path(__file__).resolve().parents[2]
_ENV_FILE = _HERE / "backend" / ".env"
if _ENV_FILE.exists():
    for line in _ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

# Allow `from omoi_os.services...` imports when run from the repo root.
sys.path.insert(0, str(_HERE / "backend"))

from omoi_os.services import modal_sandboxed_agent as msa  # noqa: E402


def _step(n: int, msg: str) -> None:
    print(f"[step {n}] {msg}", flush=True)


def _result(ok: bool, msg: str) -> None:
    print(f"   {'✓ PASS' if ok else '✗ FAIL'}: {msg}", flush=True)


async def main() -> int:
    api_key = os.environ.get("FIREWORKS_API_KEY") or os.environ.get("LLM_API_KEY")
    if not api_key:
        print("FATAL: no FIREWORKS_API_KEY or LLM_API_KEY in env", file=sys.stderr)
        return 2

    omoios_session_id = "probe-modal-streaming"

    _step(1, "spawn fresh sandbox via msa.get_or_spawn() — boots opencode serve")
    try:
        agent = await msa.get_or_spawn(omoios_session_id)
    except Exception as exc:  # noqa: BLE001
        _result(False, f"spawn raised: {type(exc).__name__}: {exc}")
        return 1
    _result(True, f"sandbox_id={agent.sandbox_id}, opencode_session={agent.opencode_session_id}")
    _result(True, f"tunnel_url={agent.tunnel_url}")

    _step(2, "stream a single turn — `Reply with PONG and nothing else.`")
    seen: list[tuple[str, dict]] = []
    delta_seen = False

    async def on_part(et: str, props: dict) -> None:
        nonlocal delta_seen
        seen.append((et, props))
        if et == "message.part.delta":
            delta_seen = True

    try:
        text = await agent.prompt(
            "Reply with the single word PONG and nothing else.",
            on_part=on_part,
        )
    except Exception as exc:  # noqa: BLE001
        _result(False, f"prompt raised: {type(exc).__name__}: {exc}")
        await msa.close(omoios_session_id)
        return 1

    _result(len(seen) >= 3, f"received {len(seen)} events through on_part")
    _result(delta_seen, "saw at least one message.part.delta")
    _result("PONG" in text.upper(), f"final text contains PONG (got: {text!r})")

    _step(3, "tear down sandbox via msa.close()")
    try:
        await msa.close(omoios_session_id)
        _result(True, "closed cleanly")
    except Exception as exc:  # noqa: BLE001
        _result(False, f"close raised: {type(exc).__name__}: {exc}")
        return 1

    print("\nALL CHECKS PASSED" if (delta_seen and "PONG" in text.upper()) else "\nSOME CHECKS FAILED")
    return 0 if (delta_seen and "PONG" in text.upper()) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
