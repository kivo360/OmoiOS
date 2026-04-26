"""`omoios environments` — manage Environment containers + their versions.

Critical model rule (see project memory `EnvironmentVersion is the unit
of change, not 'env vars'`): `environment_versions` rows are immutable.
"Setting a variable" is *never* an UPDATE; it's read-latest → merge →
INSERT a new version with `version_number = max + 1`.

Subcommands:
  - list                          — Environments in your org
  - get <env_id>                  — env + latest version
  - versions <env_id>             — full version history
  - create <name> --org <id>      — new Environment container
  - set <env_id> KEY=VALUE [...]  — new version with merged variables
  - set-secret <env_id> KEY       — same, type=secret, value from
                                    $OMOIOS_PROVIDER_KEY
  - bind <env_id> ALIAS=BINDING_ID — new version with merged credentials map
  - rollback <env_id> <version>   — create a *new* version that copies
                                    an old one (immutability preserved)

`bind` and `rollback` use the same SDK route as `set` because the only
mutating operation the public API exposes is `POST /environments/{id}/
versions`. Per the memory, raw `credentials` writes need direct DB
today — the CLI surfaces an error explaining that until the route
lands.
"""

from __future__ import annotations

import json as _json
import os
from typing import Annotated, Optional

from cyclopts import App, Parameter
from rich.table import Table

from omoios.cli._config import resolve_config
from omoios.cli._sdk import run_sdk
from omoios.cli._ui import CliError, console, ok


environments_app = App(
    name="environments",
    help="Manage Environment containers + immutable EnvironmentVersion snapshots.",
)


# ─── list / get / versions / create ─────────────────────────────────────────


@environments_app.command(name="list")
def list_cmd(
    org: Annotated[
        Optional[str],
        Parameter(
            name=["--org", "--org-id"],
            env_var="OMOIOS_TEST_ORG_ID",
            help="Organization ID (env: OMOIOS_TEST_ORG_ID).",
        ),
    ] = None,
    json_output: Annotated[bool, Parameter(name="--json")] = False,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """List environments in an org."""
    if not org:
        raise CliError("Pass --org <id> or set $OMOIOS_TEST_ORG_ID.")
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    items = run_sdk(_list(cfg.api_base_url, cfg.api_key, org))

    if json_output:
        console.print_json(_json.dumps([_env_to_dict(e) for e in items]))
        return
    if not items:
        console.print(f"No environments in org {org}.")
        return

    table = Table(title=f"environments · org {org}")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("NAME", style="cyan")
    table.add_column("DESCRIPTION", style="dim")
    for e in items:
        table.add_row(
            str(e.id), e.name, getattr(e, "description", "") or ""
        )
    console.print(table)


@environments_app.command(name="get")
def get_cmd(
    env_id: Annotated[str, Parameter(help="Environment ID.")],
    json_output: Annotated[bool, Parameter(name="--json")] = False,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Show an environment + its latest version."""
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    result = run_sdk(_get(cfg.api_base_url, cfg.api_key, env_id))
    env = result["environment"]
    latest = result.get("latest_version")

    if json_output:
        console.print_json(
            _json.dumps(
                {
                    "environment": _env_to_dict(env),
                    "latest_version": _version_to_dict(latest),
                }
            )
        )
        return

    console.print(f"[bold]{env.id}[/bold] {env.name}")
    if latest:
        console.print(
            f"  [dim]latest version:[/dim] v{latest.version_number}"
            f" · {len(latest.variables or {})} vars"
            f" · {len(getattr(latest, 'credentials', None) or {})} bindings"
        )
    else:
        console.print("  [dim](no versions yet — `omoios environments set` to create one)[/dim]")


@environments_app.command(name="versions")
def versions_cmd(
    env_id: Annotated[str, Parameter(help="Environment ID.")],
    json_output: Annotated[bool, Parameter(name="--json")] = False,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Print version history for an environment.

    Note: the public API only returns the `latest_version` on `get`. A
    full history endpoint isn't exposed yet (see project memory
    `project_environment_versions_not_variables`); until it lands this
    command renders the latest version only and surfaces the gap.
    """
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    result = run_sdk(_get(cfg.api_base_url, cfg.api_key, env_id))
    latest = result.get("latest_version")
    if latest is None:
        console.print("(no versions)")
        return

    if json_output:
        console.print_json(_json.dumps([_version_to_dict(latest)]))
        return

    table = Table(title=f"latest version · env {env_id}")
    table.add_column("VERSION", style="cyan")
    table.add_column("VARIABLES", style="white")
    table.add_column("BINDINGS", style="white")
    table.add_column("EGRESS", style="dim")
    creds = getattr(latest, "credentials", None) or {}
    egress = getattr(latest, "egress", None) or {}
    table.add_row(
        f"v{latest.version_number}",
        str(len(latest.variables or {})),
        str(len(creds)),
        "yes" if egress.get("allowed_hosts") else "—",
    )
    console.print(table)
    console.print(
        "[dim]· full history endpoint not in public API yet; this shows "
        "latest only.[/dim]"
    )


@environments_app.command(name="create")
def create_cmd(
    name: Annotated[str, Parameter(help="Environment name (unique within org).")],
    org: Annotated[
        Optional[str],
        Parameter(
            name=["--org", "--org-id"],
            env_var="OMOIOS_TEST_ORG_ID",
            help="Organization ID.",
        ),
    ] = None,
    description: Annotated[str, Parameter(name="--description")] = "",
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Create a new Environment container (no versions yet)."""
    if not org:
        raise CliError("Pass --org <id> or set $OMOIOS_TEST_ORG_ID.")
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    env = run_sdk(_create(cfg.api_base_url, cfg.api_key, name, org, description))
    ok(f"created env [bold]{env.id}[/bold] · {env.name}")
    console.print("  [dim]next: `omoios environments set <id> KEY=value` to make a v1[/dim]")


# ─── set / set-secret / bind / rollback (the immutable-version operations) ──


@environments_app.command(name="set")
def set_cmd(
    env_id: Annotated[str, Parameter(help="Environment ID.")],
    pairs: Annotated[
        list[str],
        Parameter(help="One or more KEY=VALUE pairs (string-typed)."),
    ],
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Create a new version with merged variables (NOT in-place edit).

    Reads the latest version's `variables`, merges the KEY=VALUE pairs
    in, and POSTs a new version. Existing sessions stay pinned to the
    old version; only future spawns see the change.
    """
    parsed = _parse_kv_pairs(pairs)
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    new_version = run_sdk(
        _merge_and_create_version(
            cfg.api_base_url,
            cfg.api_key,
            env_id,
            variable_overrides={
                k: {"type": "string", "value": v} for k, v in parsed.items()
            },
        )
    )
    ok(f"created v{new_version.version_number} (merged {len(parsed)} var(s))")
    console.print(
        "  [dim]running sessions stay pinned to the old version; new "
        "spawns see the change.[/dim]"
    )


@environments_app.command(name="set-secret")
def set_secret_cmd(
    env_id: Annotated[str, Parameter(help="Environment ID.")],
    key: Annotated[str, Parameter(help="Variable name to set.")],
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Create a new version with a `type=secret` variable.

    The secret value is read from `$OMOIOS_PROVIDER_KEY` (same convention
    as `omoios providers add`) so it stays out of shell history.
    """
    value = os.environ.get("OMOIOS_PROVIDER_KEY")
    if not value:
        raise CliError(
            "Set $OMOIOS_PROVIDER_KEY in the environment before calling "
            "set-secret. The value is encrypted server-side before storage."
        )
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    new_version = run_sdk(
        _merge_and_create_version(
            cfg.api_base_url,
            cfg.api_key,
            env_id,
            variable_overrides={key: {"type": "secret", "value": value}},
        )
    )
    ok(f"created v{new_version.version_number} (set secret [cyan]{key}[/cyan])")


@environments_app.command(name="bind")
def bind_cmd(
    env_id: Annotated[str, Parameter(help="Environment ID.")],
    pairs: Annotated[
        list[str],
        Parameter(help="One or more ALIAS=BINDING_ID pairs."),
    ],
    kind: Annotated[
        str,
        Parameter(
            name="--kind",
            help="BindingKind for the alias (default: bearer_secret).",
        ),
    ] = "bearer_secret",
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Bind credential aliases on a new version's `credentials` map.

    The public `POST /environments/{id}/versions` route accepts
    `credentials` in the body for some backends but not others (see
    the project memory). If your deployment doesn't accept it, this
    command will return a clean error and you'll need the
    `setup_*_smoke_account.py`-style direct-DB write — that's a known
    backend gap.
    """
    parsed = _parse_kv_pairs(pairs)
    overrides = {
        alias: {"kind": kind, "binding_id": binding_id}
        for alias, binding_id in parsed.items()
    }
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    new_version = run_sdk(
        _merge_and_create_version(
            cfg.api_base_url,
            cfg.api_key,
            env_id,
            credentials_overrides=overrides,
        )
    )
    ok(
        f"created v{new_version.version_number} "
        f"(bound {len(parsed)} alias(es))"
    )


@environments_app.command(name="rollback")
def rollback_cmd(
    env_id: Annotated[str, Parameter(help="Environment ID.")],
    target: Annotated[
        int, Parameter(name="--to", help="Version number to copy variables from.")
    ],
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """'Rollback' = create a NEW version that copies an older one's contents.

    Immutability is preserved: we never edit the target version or the
    current version. We just append a fresh version with the older
    payload. Sessions pinned to whatever version they spawned with stay
    put — only future spawns see the rollback.
    """
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    new_version = run_sdk(_rollback(cfg.api_base_url, cfg.api_key, env_id, target))
    ok(
        f"created v{new_version.version_number} as a copy of v{target} "
        f"({len(new_version.variables or {})} var(s))"
    )
    console.print(
        "  [dim]running sessions stay pinned to the version they spawned "
        "with; only new spawns see this rollback.[/dim]"
    )


# ─── async impls ─────────────────────────────────────────────────────────────


async def _list(api_base_url, api_key, org_id):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        return await client.environments.list(org_id=org_id)


async def _get(api_base_url, api_key, env_id):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        return await client.environments.get(env_id)


async def _create(api_base_url, api_key, name, org_id, description):
    from omoios import AsyncOmoiOSClient
    from omoios.types import CreateEnvironmentRequest

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        return await client.environments.create(
            CreateEnvironmentRequest(
                name=name, org_id=org_id, description=description or None
            )
        )


async def _rollback(api_base_url, api_key, env_id, target_version):
    """Read v(target), then INSERT a new version copying its payload.

    Immutability is preserved: the target row stays untouched.
    """
    from omoios import AsyncOmoiOSClient
    from omoios.types import (
        CreateEnvironmentVersionRequest,
        EnvironmentVariable,
    )

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        target = await client.environments.get_version(env_id, target_version)
        as_models = {}
        for k, v in (target.variables or {}).items():
            as_models[k] = (
                v if hasattr(v, "model_dump") else EnvironmentVariable.model_validate(v)
            )
        request = CreateEnvironmentVersionRequest(
            variables=as_models,
            credentials=getattr(target, "credentials", None),
        )
        return await client.environments.create_version(env_id, request)


async def _merge_and_create_version(
    api_base_url,
    api_key,
    env_id,
    *,
    variable_overrides: Optional[dict] = None,
    credentials_overrides: Optional[dict] = None,
):
    """The read-merge-INSERT workhorse.

    All `set / set-secret / bind` flow through here so the immutable
    pattern is in exactly one place.
    """
    from omoios import AsyncOmoiOSClient
    from omoios.types import (
        CreateEnvironmentVersionRequest,
        EnvironmentVariable,
    )

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        # 1. Read latest version (may not exist yet).
        result = await client.environments.get(env_id)
        latest = result.get("latest_version")
        base_vars: dict = {}
        base_creds: dict = {}
        if latest is not None:
            # `latest.variables` may be EnvironmentVariable models or raw dicts
            for k, v in (latest.variables or {}).items():
                if hasattr(v, "model_dump"):
                    base_vars[k] = v.model_dump(mode="json")
                else:
                    base_vars[k] = dict(v)
            base_creds = dict(getattr(latest, "credentials", None) or {})

        # 2. Merge in the overrides.
        if variable_overrides:
            base_vars.update(variable_overrides)
        if credentials_overrides:
            base_creds.update(credentials_overrides)

        # 3. INSERT a new version.
        as_models = {
            k: EnvironmentVariable.model_validate(v) for k, v in base_vars.items()
        }
        request = CreateEnvironmentVersionRequest(
            variables=as_models,
            credentials=base_creds or None,
        )
        return await client.environments.create_version(env_id, request)


# ─── small dict/output helpers ───────────────────────────────────────────────


def _parse_kv_pairs(pairs: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in pairs:
        if "=" not in item:
            raise CliError(f"expected KEY=VALUE, got {item!r}")
        k, v = item.split("=", 1)
        if not k:
            raise CliError(f"empty key in {item!r}")
        out[k] = v
    return out


def _env_to_dict(e) -> dict:
    return {
        "id": str(e.id),
        "name": e.name,
        "description": getattr(e, "description", None),
        "org_id": str(getattr(e, "org_id", "") or ""),
    }


def _version_to_dict(v) -> Optional[dict]:
    if v is None:
        return None
    return {
        "id": str(v.id),
        "version_number": v.version_number,
        "variable_count": len(v.variables or {}),
        "credential_count": len(getattr(v, "credentials", None) or {}),
        "egress_hosts": (getattr(v, "egress", None) or {}).get("allowed_hosts"),
        "exposed_ports": getattr(v, "exposed_ports", None),
    }
