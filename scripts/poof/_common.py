"""Shared helpers for poof probes — output formatting + per-probe state cache.

Each probe writes its own JSON file under `.sisyphus/poof-state/<probe>.json`
so re-runs and surgical solo-debugging don't have to re-prove every prior.
The shared `state` dict is reconstructed by merging every per-probe cache
file at orchestrator startup.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


REPO = Path(__file__).resolve().parent.parent.parent
STATE_DIR = REPO / ".sisyphus" / "poof-state"
EVIDENCE_DIR = REPO / ".sisyphus" / "evidence"
LEGACY_STATE_PATH = REPO / ".sisyphus" / "poof.state.json"


@dataclass
class StepResult:
    status: str  # "PASS" | "FAIL" | "SKIP"
    elapsed_ms: float
    detail: Optional[str] = None


def print_step(num: int, name: str, result: StepResult) -> None:
    """Single-line PASS/FAIL/SKIP renderer matching the monolith's format."""
    glyph = {"PASS": "✓", "FAIL": "✗", "SKIP": "·"}[result.status]
    color = {"PASS": "\033[32m", "FAIL": "\033[31m", "SKIP": "\033[90m"}[
        result.status
    ]
    reset = "\033[0m"
    detail = f"  {result.detail}" if result.detail else ""
    print(
        f"  {color}{glyph} step {num} {name:<14}{reset}"
        f"  {result.status:>4}  {result.elapsed_ms:>5.0f}ms{detail}",
        flush=True,
    )


def print_boot_banner() -> None:
    """Single boot line printed before heavy imports settle."""
    print("  ▸ poof booting…", flush=True)
    sys.stdout.flush()


# ─── per-probe state cache ────────────────────────────────────────────────────


def _probe_path(probe: str) -> Path:
    return STATE_DIR / f"{probe}.json"


def save_probe_state(probe: str, payload: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    _probe_path(probe).write_text(json.dumps(payload, indent=2))


def load_probe_state(probe: str) -> dict[str, Any]:
    path = _probe_path(probe)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def load_merged_state(probes: list[str]) -> dict[str, Any]:
    """Merge all per-probe caches into a single shared state dict.

    Probes are merged in order — later probes can overwrite keys from
    earlier ones (rare; happens only when a key carries the same name
    across probes for legitimate reasons).
    """
    state: dict[str, Any] = {}
    for probe in probes:
        state.update(load_probe_state(probe))
    # Backwards-compat: if the legacy single-file cache is still around,
    # fold it in as a base layer so a fresh `scripts/poof/` install can
    # pick up where the monolith left off.
    if LEGACY_STATE_PATH.exists():
        try:
            legacy = json.loads(LEGACY_STATE_PATH.read_text())
            if isinstance(legacy, dict):
                merged: dict[str, Any] = dict(legacy)
                merged.update(state)
                state = merged
        except json.JSONDecodeError:
            pass
    return state


def clear_all_probe_state() -> None:
    if STATE_DIR.exists():
        for child in STATE_DIR.iterdir():
            if child.is_file():
                child.unlink()
    if LEGACY_STATE_PATH.exists():
        LEGACY_STATE_PATH.unlink()
