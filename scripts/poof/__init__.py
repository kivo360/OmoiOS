"""Decomposed proof-of-life probes — one file per "prior" the chat path
needs to satisfy.

The orchestration entry point is `scripts/agent_proof_of_life.py`; each
probe in this package is also runnable solo for surgical debugging:

    POOF_ENV=local .venv/bin/python -m scripts.poof.chat_responder_fires \\
        --session-id 39d55536-…

Per-probe contract (`run(client, state) -> StepResult`):
- Loads `PoofSettings` (`get_settings()`).
- Caches its own result under `.sisyphus/poof-state/<probe>.json`.
- Reuses cached resources via find-by-name first, then create.
- Emits a single PASS/FAIL line within `timeout_per_step_s`.

See `memory/project_poof_settings_and_decomposition.md` for the design
rationale ("don't reinvent — extract from the current monolith").
"""

from __future__ import annotations

from scripts.poof._common import StepResult, print_step

__all__ = ["StepResult", "print_step"]
