"""Auth + base URL resolution for `omoios` subcommands.

Precedence (highest first):
  1. `--api-base-url` / `--api-key` flags (per-command override)
  2. Process env: `OMOIOS_API_BASE_URL` + `OMOIOS_PLATFORM_API_KEY`
     (and `OMOIOS_API_KEY` as a back-compat alias)
  3. XDG config file at `$XDG_CONFIG_HOME/omoios/config.json` or
     `~/.config/omoios/config.json` — written by `omoios signup`.

The config file is JSON: `{"api_base_url": "...", "api_key": "...",
"workspace_id": "...", "user_id": "...", "github_token": "..."}`.
Optional keys are tolerated.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from omoios.cli._ui import CliError


from platformdirs import user_config_path

# Precedence for the config directory:
#   1. $OMOIOS_CONFIG_DIR — explicit per-user override
#   2. $XDG_CONFIG_HOME/omoios — honors the XDG spec on Linux and is
#      the convention many devs already rely on cross-platform
#   3. platformdirs default (macOS: ~/Library/Application Support/omoios;
#      Windows: %APPDATA%/omoios; Linux: ~/.config/omoios)
CONFIG_DIR_OVERRIDE_ENV = "OMOIOS_CONFIG_DIR"
XDG_ENV = "XDG_CONFIG_HOME"
APP_NAME = "omoios"
CONFIG_FILENAME = "config.json"


@dataclass
class CliConfig:
    api_base_url: str
    api_key: str
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None
    github_token: Optional[str] = None


def config_dir() -> Path:
    """Resolve the per-user config directory for omoios."""
    if override := os.environ.get(CONFIG_DIR_OVERRIDE_ENV):
        return Path(override)
    if xdg := os.environ.get(XDG_ENV):
        return Path(xdg) / APP_NAME
    return user_config_path(APP_NAME, appauthor=False, ensure_exists=False)


def config_path() -> Path:
    return config_dir() / CONFIG_FILENAME


def _load_file(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def resolve_config(
    *,
    api_base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> CliConfig:
    """Resolve the active CliConfig per the documented precedence chain.

    Raises :class:`CliError` (caught by the top-level command handler)
    when neither base URL nor key can be resolved.
    """
    file_data = _load_file(config_path())

    base_url = (
        api_base_url
        or os.environ.get("OMOIOS_API_BASE_URL")
        or file_data.get("api_base_url")
    )
    key = (
        api_key
        or os.environ.get("OMOIOS_PLATFORM_API_KEY")
        or os.environ.get("OMOIOS_API_KEY")
        or file_data.get("api_key")
    )

    if not base_url:
        raise CliError(
            "OMOIOS_API_BASE_URL not set. Pass --api-base-url, export "
            "OMOIOS_API_BASE_URL, or run `omoios signup` to write a "
            f"config file at {config_path()}."
        )
    if not key:
        raise CliError(
            "OMOIOS_PLATFORM_API_KEY not set. Pass --api-key, export "
            "OMOIOS_PLATFORM_API_KEY, or run `omoios signup` to mint one."
        )

    return CliConfig(
        api_base_url=base_url.rstrip("/"),
        api_key=key,
        workspace_id=file_data.get("workspace_id"),
        user_id=file_data.get("user_id"),
        github_token=file_data.get("github_token"),
    )


def update_config(**fields) -> Path:
    """Merge `fields` into the existing config file (creating it if absent).

    Used by `omoios auth github` to write only `github_token` without
    needing the rest of the config. Only non-None values are written.
    """
    path = config_path()
    existing = _load_file(path)
    existing.update({k: v for k, v in fields.items() if v is not None})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(existing, indent=2))
    try:
        os.chmod(path, 0o600)  # noqa: PTH101
    except OSError:
        pass
    return path


def write_config(cfg: CliConfig) -> Path:
    """Persist `cfg` to the canonical config file with 0600 perms."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict = {
        "api_base_url": cfg.api_base_url,
        "api_key": cfg.api_key,
    }
    if cfg.workspace_id:
        payload["workspace_id"] = cfg.workspace_id
    if cfg.user_id:
        payload["user_id"] = cfg.user_id
    if cfg.github_token:
        payload["github_token"] = cfg.github_token
    path.write_text(json.dumps(payload, indent=2))
    try:
        os.chmod(path, 0o600)  # noqa: PTH101
    except OSError:
        pass
    return path
