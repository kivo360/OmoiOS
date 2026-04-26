"""Render OpenCode + OmO config from an EnvironmentVersion's credentials.

Closes the smoke-test gap `opencode_config`: bootstrap.sh expects
`OMOIOS_OPENCODE_CONFIG` and `OMOIOS_OMO_CONFIG` env vars to contain the
JSON / JSONC bodies it should write into `~/.config/opencode/`. Without
them the agent boots with no provider surface and cannot route tasks.

Spec §14: OmO reads `opencode.json` for provider/model wiring and
`oh-my-openagent.jsonc` for layered agent/category routing. We render
both from the credential alias map so each environment version
auto-derives a usable agent runtime — no per-tenant config templates.

Design choices:

- Built-in providers (the OpenCode catalog: anthropic, openai, google,
  fireworks-ai, github-copilot, opencode, opencode-go, zai-coding-plan,
  …) need NO provider block in opencode.json — OpenCode resolves them
  from its built-in catalog and reads the key from auth.json. Custom
  providers (npm-loaded openai-compatible adapters etc.) need an
  explicit provider entry plus a `models` map.
- API keys live in auth.json (rendered by bootstrap.sh from broker
  data). The `{env:VAR}` apiKey template is harmless decoration but
  is NOT substituted for npm-loaded providers — auth.json is the
  source of truth.
- Aliases match OpenCode's actual provider ids (e.g. `fireworks-ai`,
  not `fireworks`) so the same name flows through credentials,
  auth.json, opencode.json `model`, and the OmO `agents`/`categories`
  routing tree.
"""

from __future__ import annotations

import json
from typing import Any, Optional


# Built-in OpenCode providers — listed in the catalog OpenCode ships
# with. For these, we never emit a `provider.<id>` block in
# opencode.json: OpenCode auto-resolves them and pulls the key from
# auth.json. The renderer only needs to know their default models.
_BUILTIN_PROVIDERS: set[str] = {
    "anthropic",
    "openai",
    "openrouter",
    "google",
    "groq",
    "xai",
    "fireworks-ai",
    "github-copilot",
    "opencode",
    "opencode-go",
    "zai-coding-plan",
    "minimax-coding-plan",
}

# Default model per credential alias — used when picking the top-level
# `model` field. Aliases must match OpenCode's actual provider ids.
_DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "anthropic/claude-sonnet-4-5",
    "openai": "openai/gpt-5",
    "openrouter": "openrouter/anthropic/claude-sonnet-4-5",
    "google": "google/gemini-2-pro",
    "groq": "groq/llama-3.3-70b-versatile",
    "xai": "xai/grok-4",
    "fireworks-ai": "fireworks-ai/accounts/fireworks/routers/kimi-k2p5-turbo",
}

# Preference order when an env_version binds multiple providers.
# `fireworks-ai` first: when present it's our default Kimi lane.
_PREFERENCE_ORDER = [
    "fireworks-ai",
    "anthropic",
    "openrouter",
    "openai",
    "google",
    "groq",
    "xai",
]


def render_opencode_config(
    credential_aliases: list[str],
    *,
    default_model: Optional[str] = None,
) -> str:
    """Build an opencode.json body for a sandbox.

    Args:
        credential_aliases: alias names from `env_version.credentials.keys()`.
            These are the broker aliases the agent can fetch at runtime.
        default_model: override the auto-selected default model. Useful
            for tenants pinning a specific model per environment.

    Returns:
        JSON string ready to be written to `~/.config/opencode/opencode.json`
        by `sandbox/bootstrap.sh` when `OMOIOS_OPENCODE_CONFIG` is set.
    """
    # Provider block: only emit entries for non-built-in aliases.
    # Built-ins (fireworks-ai, anthropic, openai, …) are resolved from
    # OpenCode's catalog + auth.json; an explicit override is unneeded.
    providers: dict[str, dict[str, Any]] = {}
    for alias in credential_aliases:
        if alias in _BUILTIN_PROVIDERS:
            continue
        providers[alias] = {
            "name": alias,
            "options": {
                "apiKey": f"{{env:{alias.upper()}_API_KEY}}",
            },
        }

    chosen_model = default_model
    if chosen_model is None:
        for pref in _PREFERENCE_ORDER:
            if pref in credential_aliases and pref in _DEFAULT_MODELS:
                chosen_model = _DEFAULT_MODELS[pref]
                break
        if chosen_model is None and credential_aliases:
            first = credential_aliases[0]
            chosen_model = _DEFAULT_MODELS.get(first) or f"{first}/default"

    config: dict[str, Any] = {
        "$schema": "https://opencode.ai/config.json",
    }
    if providers:
        config["provider"] = providers
    if chosen_model:
        config["model"] = chosen_model

    return json.dumps(config, indent=2)


def render_auth_json(resolved_aliases: dict[str, dict]) -> str:
    """Build OpenCode's auth.json from already-resolved credential payloads.

    Mirrors `sandbox/bootstrap.sh::render_auth_entry`, but runs in the
    spawner so Modal sandboxes (which start with `sleep infinity` and
    never execute bootstrap.sh) get the file written for them.

    Args:
        resolved_aliases: ``{alias: {kind, ...}}`` where each entry is
            already-decrypted broker output. Supported kinds:

            - ``bearer_secret``  → ``{"value": "fw_..."}``
            - ``user_oauth``     → ``{"access_token", "refresh_token?",
              "expires_at"}`` (expires_at as ISO string or epoch seconds)
            - ``github_app``     → ``{"token", "expires_at"}``

    Returns:
        JSON string ready to write to
        ``~/.local/share/opencode/auth.json``.
    """
    auth: dict[str, dict] = {}
    for alias, payload in resolved_aliases.items():
        kind = payload.get("kind")
        if kind == "bearer_secret":
            auth[alias] = {"type": "api", "key": payload["value"]}
        elif kind == "user_oauth":
            entry: dict = {
                "type": "oauth",
                "access": payload.get("access_token") or payload.get("access"),
            }
            refresh = payload.get("refresh_token") or payload.get("refresh")
            if refresh:
                entry["refresh"] = refresh
            expires = payload.get("expires_at") or payload.get("expires")
            if expires is not None:
                entry["expires"] = _coerce_expires(expires)
            auth[alias] = entry
        elif kind == "github_app":
            entry = {
                "type": "oauth",
                "access": payload.get("token") or payload.get("access"),
            }
            expires = payload.get("expires_at") or payload.get("expires")
            if expires is not None:
                entry["expires"] = _coerce_expires(expires)
            auth[alias] = entry
        else:
            # Skip unknown kinds rather than crashing — bootstrap does
            # the same and logs the miss; here we silently omit.
            continue
    return json.dumps(auth, indent=2)


def _coerce_expires(value: Any) -> int:
    """Best-effort ISO/epoch → unix-seconds-int (auth.json shape)."""
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        from datetime import datetime

        try:
            return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
        except ValueError:
            return 0
    return 0


def render_omo_config(
    credential_aliases: list[str],
    *,
    default_model: Optional[str] = None,
) -> str:
    """Build a minimal oh-my-openagent.jsonc body.

    Mirrors the real OmO shape (top-level `agents` and `categories`
    maps, each entry shaped `{model, fallback_models?}`). Tenants who
    want richer routing override at the env-version level.
    """
    chosen_model = default_model
    if chosen_model is None:
        for pref in _PREFERENCE_ORDER:
            if pref in credential_aliases and pref in _DEFAULT_MODELS:
                chosen_model = _DEFAULT_MODELS[pref]
                break

    if chosen_model is None:
        chosen_model = "anthropic/claude-sonnet-4-5"

    body = {
        "$schema": (
            "https://github.com/code-yeongyu/oh-my-openagent/raw/refs/"
            "heads/dev/assets/oh-my-opencode.schema.json"
        ),
        "agents": {
            "default": {"model": chosen_model},
        },
        "categories": {
            "default": {"model": chosen_model},
        },
    }
    return (
        "// oh-my-openagent.jsonc — auto-generated from environment "
        "credentials\n" + json.dumps(body, indent=2)
    )
