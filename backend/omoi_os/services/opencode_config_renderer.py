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

- Provider npm package names mirror OpenCode's conventions (`@ai-sdk/...`).
- API keys reference `{env:UPPERCASE_ALIAS_API_KEY}`. The bootstrap also
  writes `auth.json` from the broker; OpenCode prefers `auth.json`
  when both are set, so the env-var indirection is just a polite
  fallback for callers running OpenCode directly.
- Default model: prefer `anthropic` (best Claude 4 family for codegen),
  then fall back to whatever else the environment has.
- oh-my-openagent.jsonc gets a single `default` route; tenants who want
  multiple categories can override at the env-version level.
"""

from __future__ import annotations

import json
from typing import Any, Optional


# Mapping: credential alias → OpenCode provider definition fragment.
# When an alias is recognised here, we plug in the canonical npm
# package + key reference. Unknown aliases get a passthrough entry so
# the agent can still see the credential exists; OpenCode's provider
# resolver tolerates extra keys.
_KNOWN_PROVIDERS: dict[str, dict[str, Any]] = {
    "anthropic": {
        "npm": "@ai-sdk/anthropic",
        "name": "Anthropic",
        "options": {"apiKey": "{env:ANTHROPIC_API_KEY}"},
    },
    "openai": {
        "npm": "@ai-sdk/openai",
        "name": "OpenAI",
        "options": {"apiKey": "{env:OPENAI_API_KEY}"},
    },
    "openrouter": {
        "npm": "@openrouter/ai-sdk-provider",
        "name": "OpenRouter",
        "options": {"apiKey": "{env:OPENROUTER_API_KEY}"},
    },
    "google": {
        "npm": "@ai-sdk/google",
        "name": "Google",
        "options": {"apiKey": "{env:GOOGLE_API_KEY}"},
    },
    "groq": {
        "npm": "@ai-sdk/groq",
        "name": "Groq",
        "options": {"apiKey": "{env:GROQ_API_KEY}"},
    },
    "xai": {
        "npm": "@ai-sdk/xai",
        "name": "xAI",
        "options": {"apiKey": "{env:XAI_API_KEY}"},
    },
    "fireworks": {
        "npm": "@ai-sdk/openai-compatible",
        "name": "Fireworks AI",
        "options": {
            "baseURL": "https://api.fireworks.ai/inference/v1",
            "apiKey": "{env:FIREWORKS_API_KEY}",
        },
        # Custom providers (npm-loaded) need an explicit `models` map —
        # OpenCode can't auto-discover them and otherwise rejects the
        # model lookup with ProviderModelNotFoundError.
        "models": {
            "accounts/fireworks/routers/kimi-k2p5-turbo": {
                "name": "Kimi K2.5 Turbo",
            },
        },
    },
}

# Default model per provider — used when picking the top-level `model`
# field. Tenants can override by editing the environment version.
_DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "anthropic/claude-sonnet-4-5",
    "openai": "openai/gpt-5",
    "openrouter": "openrouter/anthropic/claude-sonnet-4-5",
    "google": "google/gemini-2-pro",
    "groq": "groq/llama-3.3-70b-versatile",
    "xai": "xai/grok-4",
    "fireworks": "fireworks/accounts/fireworks/routers/kimi-k2p5-turbo",
}

# Preference order when no alias is "anthropic" but multiple are set.
# `fireworks` first: when an env_version binds it, prefer Kimi K2.5 Turbo —
# this is how proof-of-life targets the right LLM without tenant override.
_PREFERENCE_ORDER = [
    "fireworks",
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
    # Build the provider block. Known aliases get the canonical
    # definition; unknown aliases get a stub so the agent at least sees
    # the alias exists — OpenCode treats extra providers as opt-in.
    providers: dict[str, dict[str, Any]] = {}
    for alias in credential_aliases:
        if alias in _KNOWN_PROVIDERS:
            providers[alias] = _KNOWN_PROVIDERS[alias]
        else:
            providers[alias] = {
                "name": alias,
                "options": {
                    "apiKey": f"{{env:{alias.upper()}_API_KEY}}",
                },
            }

    # Pick a default model. Caller override > anthropic > preference order.
    chosen_model = default_model
    if chosen_model is None:
        for pref in _PREFERENCE_ORDER:
            if pref in credential_aliases and pref in _DEFAULT_MODELS:
                chosen_model = _DEFAULT_MODELS[pref]
                break
        if chosen_model is None and credential_aliases:
            # Fallback: take the first alias and assume it follows
            # `provider/model` form. Better than no model at all.
            first = credential_aliases[0]
            chosen_model = f"{first}/default"

    config: dict[str, Any] = {
        "$schema": "https://opencode.ai/config.json",
    }
    if providers:
        config["provider"] = providers
    if chosen_model:
        config["model"] = chosen_model

    return json.dumps(config, indent=2)


def render_omo_config(
    credential_aliases: list[str],
    *,
    default_model: Optional[str] = None,
) -> str:
    """Build a minimal oh-my-openagent.jsonc body.

    Just defines a single `default` route. Tenants who want
    category-aware routing should override the environment version's
    config templates rather than relying on the auto-generated default.
    """
    chosen_model = default_model
    if chosen_model is None:
        for pref in _PREFERENCE_ORDER:
            if pref in credential_aliases and pref in _DEFAULT_MODELS:
                chosen_model = _DEFAULT_MODELS[pref]
                break

    if chosen_model is None:
        # Absent any creds we still emit a valid (if useless) doc — the
        # smoke phase tolerates this; OmO will pick the first available
        # provider at runtime.
        chosen_model = "anthropic/claude-sonnet-4-5"

    body = {
        "$schema": "https://oh-my-openagent.dev/config.json",
        "default": {"model": chosen_model},
    }
    # Wrap in JSONC-friendly preamble so editors highlight the file
    # correctly. JSON parsers tolerate the leading comment block.
    return (
        "// oh-my-openagent.jsonc — auto-generated from environment "
        "credentials\n" + json.dumps(body, indent=2)
    )
