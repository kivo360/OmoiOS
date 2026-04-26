"""Shared settings for the poof probe suite.

Reads the canonical OmoiOS env names (so existing `.env.local` /
`.env.smoke-test` files keep working), with optional POOF_-prefixed knobs
for probe-specific tunables. The single env-flip (`POOF_ENV=local|staging`)
selects which dotenv file to source on top of the live process env.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO = Path(__file__).resolve().parent.parent.parent


def _load_env_file() -> Optional[Path]:
    """Load credentials from the dotenv file selected by POOF_ENV.

    Precedence (highest first):
      1. Live process env (never overwritten — `os.environ.setdefault`).
      2. The dotenv file picked by POOF_ENV.

    Defaults: `POOF_ENV=local` reads `backend/.env.local` (today's
    behavior in the monolith); `POOF_ENV=staging` reads
    `backend/.env.smoke-test`. Returns the path actually loaded, or
    None when no file matched.
    """
    poof_env = os.environ.get("POOF_ENV", "local").lower()
    candidates: list[Path]
    if poof_env == "staging":
        candidates = [
            REPO / "backend" / ".env.smoke-test",
            REPO / "backend" / ".env.smoke-test.local",
        ]
    else:
        candidates = [
            REPO / "backend" / ".env.local.poof",
            REPO / "backend" / ".env.local",
        ]

    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(
                key.strip(),
                value.strip().strip('"').strip("'"),
            )
        return path
    return None


class PoofSettings(BaseSettings):
    """Pydantic settings shared across every poof probe.

    Reads the canonical OmoiOS env names directly (no rename), so the
    existing `.env.local` / `.env.smoke-test` continue to work
    unchanged. POOF_-prefixed knobs cover the probe-specific tunables.
    """

    model_config = SettingsConfigDict(extra="ignore", populate_by_name=True)

    # ─── canonical OmoiOS env (used by the SDK + DB-direct steps) ──────────
    api_base_url: str = Field(..., alias="OMOIOS_API_BASE_URL")
    platform_api_key: str = Field(..., alias="OMOIOS_PLATFORM_API_KEY")
    test_org_id: str = Field(..., alias="OMOIOS_TEST_ORG_ID")
    test_workspace_a: Optional[str] = Field(None, alias="OMOIOS_TEST_WORKSPACE_A")
    fireworks_api_key: str = Field(..., alias="FIREWORKS_API_KEY")
    database_url: str = Field(..., alias="DATABASE_URL")

    # ─── poof-specific resource names (find-by-name first, then create) ────
    workspace_name: str = Field("poof-life", alias="POOF_WORKSPACE_NAME")
    credential_name: str = Field(
        "poof-fireworks-ai", alias="POOF_CREDENTIAL_NAME"
    )
    env_name: str = Field("poof-kimi", alias="POOF_ENV_NAME")
    alias: str = Field("fireworks-ai", alias="POOF_ALIAS")

    # ─── timeouts ──────────────────────────────────────────────────────────
    timeout_per_step_s: int = Field(30, alias="POOF_TIMEOUT_PER_STEP_S")
    overall_timeout_s: int = Field(300, alias="POOF_OVERALL_TIMEOUT_S")
    chat_responder_budget_s: int = Field(
        90, alias="POOF_CHAT_RESPONDER_BUDGET_S"
    )


@lru_cache(maxsize=1)
def get_settings() -> PoofSettings:
    """Cached settings accessor — call from any probe.

    The first call loads the dotenv file picked by POOF_ENV; subsequent
    calls reuse the cached PoofSettings instance.
    """
    _load_env_file()
    return PoofSettings()  # type: ignore[call-arg]


def reset_settings_cache() -> None:
    """Test-only — drop the cached settings so a re-import picks up new env."""
    get_settings.cache_clear()
