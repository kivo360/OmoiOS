"""Auth + base URL resolution for `omoios` subcommands.

Precedence (highest first):
  1. `--api-base-url` / `--api-key` Click options (per-command override)
  2. Process env: `OMOIOS_API_BASE_URL` + `OMOIOS_PLATFORM_API_KEY`
     (and `OMOIOS_API_KEY` as a back-compat alias)
  3. XDG config file at `$XDG_CONFIG_HOME/omoios/config.json` or
     `~/.config/omoios/config.json` — written by `omoios signup`
     (when that lands).

The config file is JSON: `{"api_base_url": "...", "api_key": "...",
"workspace_id": "...", "user_id": "..."}`. Optional keys are tolerated.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


CONFIG_DIR_ENV = "XDG_CONFIG_HOME"
DEFAULT_CONFIG_DIR = Path.home() / ".config"
CONFIG_FILENAME = "config.json"


@dataclass
class CliConfig:
    api_base_url: str
    api_key: str
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None


def config_path() -> Path:
    base = Path(os.environ.get(CONFIG_DIR_ENV) or DEFAULT_CONFIG_DIR)
    return base / "omoios" / CONFIG_FILENAME


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

    Raises `click.ClickException` (caught by Click as a clean error exit)
    when neither base URL nor key can be resolved.
    """
    import click  # local — keeps the SDK importable without click in lib code

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
        raise click.ClickException(
            "OMOIOS_API_BASE_URL not set. Pass --api-base-url, export "
            "OMOIOS_API_BASE_URL, or run `omoios signup` to write a "
            f"config file at {config_path()}."
        )
    if not key:
        raise click.ClickException(
            "OMOIOS_PLATFORM_API_KEY not set. Pass --api-key, export "
            "OMOIOS_PLATFORM_API_KEY, or run `omoios signup` to mint one."
        )

    return CliConfig(
        api_base_url=base_url.rstrip("/"),
        api_key=key,
        workspace_id=file_data.get("workspace_id"),
        user_id=file_data.get("user_id"),
    )


def write_config(cfg: CliConfig) -> Path:
    """Persist `cfg` to the canonical config file with 0600 perms.

    Creates the parent directory if needed. Returns the path written so
    callers can show it to the user.
    """
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
    path.write_text(json.dumps(payload, indent=2))
    try:
        os.chmod(path, 0o600)  # noqa: PTH101 — direct os call is intentional
    except OSError:
        pass
    return path
