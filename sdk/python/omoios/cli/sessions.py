"""`omoios sessions` — drive the §03 chat surface from the terminal.

This is the headline CLI experience per agent-platform-spec §18 use-case
#23: create a session, watch events live (Pattern C), reply mid-stream.
The SDK already exposes the full surface; this module is a thin Rich
veneer over it.

Subcommands:
  - create <prompt> [--workspace ID] [--watch]
  - list   [--status running|completed|failed]
  - get    <id>
  - watch  <id>   # live-stream events (Pattern C)
  - reply  <id> <text>
  - cancel <id>
"""

from __future__ import annotations

import asyncio
import json as _json
from typing import Annotated, Any, Awaitable, Optional

from cyclopts import App, Parameter
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from omoios.cli._config import resolve_config
from omoios.cli._ui import CliError, console, ok


sessions_app = App(
    name="sessions",
    help="Create, watch, reply to, and cancel chat sessions (spec §03).",
)


# ─── shared plumbing ─────────────────────────────────────────────────────────


def _run(coro: Awaitable[Any]) -> Any:
    """asyncio.run + SDK-error → CliError translation, identical shape to
    `providers._run_sdk` so the UX stays consistent across subapps."""
    from omoios.exceptions import AuthError, NotFoundError, OmoiOSError

    try:
        return asyncio.run(coro)
    except KeyboardInterrupt:
        # Keep this here so Ctrl+C inside `watch` doesn't print a stack;
        # main()'s handler covers the outer level.
        raise
    except AuthError as exc:
        raise CliError(
            f"AuthError: {exc}\n"
            "  hint: run `omoios whoami` to confirm your key, or `omoios "
            "signup` to mint a fresh one."
        ) from exc
    except NotFoundError as exc:
        raise CliError(
            f"NotFoundError: {exc}\n"
            "  hint: `omoios sessions list` shows every session you can see."
        ) from exc
    except OmoiOSError as exc:
        raise CliError(f"{type(exc).__name__}: {exc}") from exc


def _resolve_workspace(workspace: Optional[str]) -> Optional[str]:
    """Pick a workspace id from --workspace flag → $OMOIOS_WORKSPACE_ID
    → config file. Falling back to None means the user must pass
    --github-repo or get a 400 from the backend."""
    if workspace:
        return workspace
    import os

    if env := os.environ.get("OMOIOS_WORKSPACE_ID"):
        return env

    cfg = resolve_config()
    return cfg.workspace_id


def _render_message_event(evt) -> None:
    """Render a `session.message` event as a chat bubble.

    Colour and alignment follow `evt.actor`:
      - `agent`              → left-aligned, green border
      - `user:<id>`          → right-aligned, cyan border (it's *us*)
      - `system` / other     → left-aligned, dim border
    """
    text = (evt.data or {}).get("text", "")
    actor = getattr(evt, "actor", None) or "system"
    if actor == "agent":
        title, style, justify = "agent", "green", "left"
    elif actor.startswith("user:"):
        title, style, justify = "you", "cyan", "right"
    else:
        title, style, justify = actor, "dim", "left"

    panel = Panel(
        Text(text, justify="left"),
        title=title,
        border_style=style,
        title_align="left" if justify == "left" else "right",
        padding=(0, 1),
    )
    if justify == "right":
        # Approximate right-alignment via padding on a fresh print.
        console.print(panel, justify="right")
    else:
        console.print(panel)


def _render_event(evt) -> bool:
    """Print an event in chat-friendly form. Returns True if this event
    is terminal (chat loop should exit)."""
    etype = getattr(evt, "type", None) or evt.event_type
    if etype == "session.created":
        data = evt.data or {}
        title = data.get("title") or "(no title)"
        console.print(
            f"[bold]session.created[/bold] [dim]{evt.session_id}[/dim] · {title}"
        )
        return False
    if etype == "session.message":
        _render_message_event(evt)
        return False
    # Anything else — render muted so the user can see them but they
    # don't dominate the chat.
    console.print(f"[dim]· {etype}[/dim]")
    if etype in ("session.succeeded", "session.failed", "session.canceled"):
        return True
    return False


# ─── omoios sessions create ──────────────────────────────────────────────────


@sessions_app.command(name="create")
def create_cmd(
    prompt: Annotated[
        str, Parameter(help="The opening prompt for the session.")
    ],
    workspace: Annotated[
        Optional[str],
        Parameter(
            name=["--workspace", "-w"],
            env_var="OMOIOS_WORKSPACE_ID",
            help="Workspace ID. Defaults to config or $OMOIOS_WORKSPACE_ID.",
        ),
    ] = None,
    environment: Annotated[
        Optional[str],
        Parameter(name="--environment", help="Optional Environment ID to bind."),
    ] = None,
    github_repo: Annotated[
        Optional[str],
        Parameter(
            name="--github-repo",
            help="`owner/repo` instead of --workspace (auto-binds workspace).",
        ),
    ] = None,
    watch: Annotated[
        bool,
        Parameter(
            name="--watch",
            help="After creating, stream events until terminal state.",
        ),
    ] = False,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Create a new session and (optionally) live-stream it."""
    if not workspace and not github_repo:
        workspace = _resolve_workspace(None)
    if not workspace and not github_repo:
        raise CliError(
            "Provide --workspace <id> or --github-repo owner/repo, or set "
            "$OMOIOS_WORKSPACE_ID / a workspace_id in the config file."
        )

    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    session = _run(
        _create(
            cfg.api_base_url,
            cfg.api_key,
            prompt=prompt,
            workspace_id=workspace,
            environment_id=environment,
            github_repo=github_repo,
        )
    )
    ok(f"created session [bold]{session.id}[/bold]")
    if not watch:
        console.print(
            f"  watch with: [cyan]omoios sessions watch {session.id}[/cyan]"
        )
        return

    # Watch path — stream events until terminal state.
    _run(_watch_loop(cfg.api_base_url, cfg.api_key, str(session.id)))


# ─── omoios sessions watch ───────────────────────────────────────────────────


@sessions_app.command(name="watch")
def watch_cmd(
    session_id: Annotated[str, Parameter(help="Session ID to stream.")],
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Live-stream an existing session's events (Pattern C from spec §18)."""
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    _run(_watch_loop(cfg.api_base_url, cfg.api_key, session_id))


# ─── omoios sessions reply ───────────────────────────────────────────────────


@sessions_app.command(name="reply")
def reply_cmd(
    session_id: Annotated[str, Parameter(help="Session ID to reply to.")],
    text: Annotated[str, Parameter(help="Message body (1..32000 chars).")],
    watch: Annotated[
        bool,
        Parameter(
            name="--watch",
            help="After sending, stream events until terminal state.",
        ),
    ] = False,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Send a follow-up message to a running session."""
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    _run(_reply(cfg.api_base_url, cfg.api_key, session_id, text))
    ok(f"sent reply to [bold]{session_id}[/bold]")
    if watch:
        _run(_watch_loop(cfg.api_base_url, cfg.api_key, session_id))


# ─── omoios sessions cancel ──────────────────────────────────────────────────


@sessions_app.command(name="cancel")
def cancel_cmd(
    session_id: Annotated[str, Parameter(help="Session ID to cancel.")],
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Cancel a running session. Idempotent."""
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    _run(_cancel(cfg.api_base_url, cfg.api_key, session_id))
    ok(f"canceled [bold]{session_id}[/bold]")


# ─── omoios sessions list / get ──────────────────────────────────────────────


@sessions_app.command(name="list")
def list_cmd(
    status: Annotated[
        Optional[str],
        Parameter(
            name="--status",
            help="Filter by status (e.g. running, completed, failed).",
        ),
    ] = None,
    json_output: Annotated[
        bool, Parameter(name="--json", help="Emit JSON instead of a table.")
    ] = False,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """List sessions visible to the current key."""
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    items = _run(_list(cfg.api_base_url, cfg.api_key, status))

    if json_output:
        console.print_json(_json.dumps([_session_to_dict(s) for s in items]))
        return

    if not items:
        console.print("No sessions.")
        return

    table = Table(title=f"sessions ({len(items)})", show_lines=False)
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("STATUS", style="cyan")
    table.add_column("TITLE", style="white")
    table.add_column("CREATED", style="dim")
    for s in items:
        table.add_row(
            str(s.id),
            getattr(s, "status", "?") or "?",
            getattr(s, "title", "") or "",
            str(getattr(s, "created_at", "") or ""),
        )
    console.print(table)


@sessions_app.command(name="get")
def get_cmd(
    session_id: Annotated[str, Parameter(help="Session ID to fetch.")],
    json_output: Annotated[
        bool, Parameter(name="--json", help="Emit raw JSON.")
    ] = False,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Fetch one session by ID."""
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    s = _run(_get(cfg.api_base_url, cfg.api_key, session_id))
    if json_output:
        console.print_json(_json.dumps(_session_to_dict(s)))
        return
    console.print(f"[bold]{s.id}[/bold]")
    for k in ("status", "title", "workspace_id", "environment_version_id", "created_at"):
        v = getattr(s, k, None)
        if v is not None:
            console.print(f"  [dim]{k}:[/dim] {v}")


# ─── async impls ─────────────────────────────────────────────────────────────


async def _create(api_base_url, api_key, **kwargs):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        return await client.sessions.create(**{k: v for k, v in kwargs.items() if v is not None})


async def _get(api_base_url, api_key, session_id):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        return await client.sessions.get(session_id)


async def _list(api_base_url, api_key, status):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        return await client.sessions.list_all(status=status)


async def _reply(api_base_url, api_key, session_id, text):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        await client.sessions.reply(session_id, text)


async def _cancel(api_base_url, api_key, session_id):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        await client.sessions.cancel(session_id)


async def _watch_loop(api_base_url, api_key, session_id):
    """Stream events until a terminal session.* event arrives.

    Spec wire: events are full envelopes (no deltas / partials). Each
    event maps to a single console line or chat bubble.
    """
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=None
    ) as client:
        try:
            async for evt in client.sessions.events(session_id):
                if _render_event(evt):
                    return
        except KeyboardInterrupt:
            console.print("[yellow]watch interrupted[/yellow]")
            return


# ─── output helpers ──────────────────────────────────────────────────────────


def _session_to_dict(s) -> dict:
    keys = (
        "id",
        "status",
        "title",
        "workspace_id",
        "environment_version_id",
        "created_at",
        "updated_at",
    )
    return {k: _stringify(getattr(s, k, None)) for k in keys}


def _stringify(v):
    if v is None:
        return None
    return str(v) if not isinstance(v, (str, int, float, bool, list, dict)) else v
