#!/usr/bin/env python3
"""Exhaustive tour of the opencode-ai (next branch) SDK surface.

Runs one live script that touches every resource group the SDK exposes
— server + project + session + find + file + event streaming — so we
know exactly what works before the sandbox integration pins us to a
specific subset.

Exercises, in order:

    ┌───────────────── introspection ─────────────────┐
    app.providers()           — connected providers
    config.get()              — merged config tree
    agent.list()              — agent definitions
    command.list()            — slash-commands
    project.current()         — cwd project
    project.list()            — known projects
    path.get()                — root/cwd paths
    file.status()             — modified files
    find.files(query)         — fuzzy filename search
    find.text(pattern)        — ripgrep-style text search
    file.list(path)           — directory listing
    file.read(path)           — file content + ranges
    app.log(…)                — write a log entry
    session.list()            — existing sessions

    ┌───────────────── conversation ──────────────────┐
    session.create(title=…)   — open a new session
    session.get(id)           — re-fetch it
    session.update(id, title) — rename
    session.prompt(id, …)     — run 3 conversational turns
    session.messages(id)      — read the full history
    session.message(mid, id)  — read one message by id
    session.shell(id, …)      — exec a shell command
    session.summarize(id, …)  — async summary
    session.share(id)         — make public
    session.unshare(id)       — revoke
    session.children(id)      — list forks (empty)
    session.abort(id)         — idempotent abort
    session.delete(id)        — cleanup

    ┌───────────────── live stream ───────────────────┐
    event.list()              — SSE stream tailed in a background task
                                while the session is running; prints a
                                summary of what flowed across the wire

One script. One run. No OmoiOS. Stage 1 reconnaissance for the
sandbox-embedded agent runtime.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

import httpx


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4096
DEFAULT_PROVIDER = "zai-coding-plan"
DEFAULT_MODEL = "glm-5.1"

REPO_ROOT = Path(__file__).resolve().parent.parent


# ─── subprocess lifecycle ────────────────────────────────────────────────────


def boot_opencode(*, host: str, port: int) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        ["opencode", "serve", "--port", str(port), "--hostname", host],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


def wait_until_up(base_url: str, *, timeout_s: float = 30.0) -> None:
    url = f"{base_url}/global/health"
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            r = httpx.get(url, timeout=1.5)
            if r.status_code == 200:
                return
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.4)
    raise RuntimeError(f"opencode did not come up at {url}")


def stop_process(proc: subprocess.Popen[bytes]) -> None:
    for kill in (lambda: os.killpg(proc.pid, signal.SIGTERM), proc.terminate):
        try:
            kill()
            break
        except (ProcessLookupError, PermissionError):
            continue
        except Exception:  # noqa: BLE001
            continue
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass


# ─── pretty-print helpers ────────────────────────────────────────────────────


def rule(title: str) -> None:
    print()
    print("═" * 80)
    print(f"  {title}")
    print("═" * 80)


def show(value: Any, *, max_lines: int = 10, max_chars: int = 700) -> None:
    """Readable dump — works on Pydantic models, dicts, and plain lists."""
    if hasattr(value, "model_dump"):
        data = value.model_dump(mode="json")
    else:
        data = value
    try:
        rendered = json.dumps(data, indent=2, default=str, sort_keys=False)
    except TypeError:
        rendered = str(data)
    if len(rendered) > max_chars:
        rendered = rendered[:max_chars] + f"\n… (+{len(rendered) - max_chars} chars)"
    lines = rendered.splitlines()
    if len(lines) > max_lines:
        hidden = len(lines) - max_lines
        lines = lines[:max_lines] + [f"… (+{hidden} lines)"]
    print("\n".join(lines))


def response_text(resp: Any) -> str:
    parts = getattr(resp, "parts", None) or []
    chunks: list[str] = []
    for p in parts:
        ptype = getattr(p, "type", None) or (
            p.get("type") if isinstance(p, dict) else None
        )
        if ptype != "text":
            continue
        t = getattr(p, "text", None) or (
            p.get("text") if isinstance(p, dict) else None
        )
        if isinstance(t, str) and t:
            chunks.append(t)
    return "\n".join(chunks).strip()


def names_of(items: Any, *, key: str = "id", limit: int = 12) -> list[str]:
    """Extract a flat list of names/ids from a typed-list response."""
    seq = items
    if hasattr(items, "model_dump"):
        dumped = items.model_dump(mode="json")
        if isinstance(dumped, list):
            seq = dumped
        elif isinstance(dumped, dict):
            # common wrappers: items / data / providers / agents / sessions
            for wrapper in ("items", "data", "providers", "sessions", "agents"):
                if isinstance(dumped.get(wrapper), list):
                    seq = dumped[wrapper]
                    break
            else:
                seq = list(dumped.values())
    if not isinstance(seq, list):
        return []
    out: list[str] = []
    for row in seq[:limit]:
        if isinstance(row, dict):
            out.append(str(row.get(key) or row.get("name") or row.get("id") or "?"))
        else:
            out.append(str(getattr(row, key, "?") or getattr(row, "name", "?")))
    return out


# ─── the tour ────────────────────────────────────────────────────────────────


async def tour(
    *,
    base_url: str,
    provider: str,
    model: str,
    scan_directory: str,
) -> None:
    from opencode_ai import AsyncOpencode

    async with AsyncOpencode(base_url=base_url, timeout=180.0) as client:
        # ── INTROSPECTION ────────────────────────────────────────────────────
        rule("app.providers()")
        provs = await client.app.providers()
        show(provs, max_lines=6)

        rule("config.get()")
        try:
            config = await client.config.get()
            show(config, max_lines=10)
        except Exception as exc:  # noqa: BLE001
            print(f"config.get failed: {exc}")

        rule("agent.list()")
        agents = await client.agent.list()
        print("agents:", names_of(agents, key="name", limit=20))

        rule("command.list()")
        commands = await client.command.list()
        print("commands:", names_of(commands, key="name", limit=20))

        rule("project.current()")
        try:
            proj = await client.project.current()
            show(proj, max_lines=8)
        except Exception as exc:  # noqa: BLE001
            print(f"project.current failed: {exc}")

        rule("project.list()")
        projects = await client.project.list()
        print("projects:", names_of(projects, key="id", limit=20))

        rule("path.get()")
        path = await client.path.get()
        show(path, max_lines=6)

        rule("file.status()")
        try:
            status = await client.file.status()
            show(status, max_lines=6)
        except Exception as exc:  # noqa: BLE001
            print(f"file.status failed: {exc}")

        # ── REPO-ROOTED SEARCH ──────────────────────────────────────────────
        rule(f"find.files(query='README', directory={scan_directory!r})")
        try:
            files = await client.find.files(query="README", directory=scan_directory)
            show(files, max_lines=6)
        except Exception as exc:  # noqa: BLE001
            print(f"find.files failed: {exc}")

        rule(f"find.text(pattern='OpenCode', directory={scan_directory!r})")
        try:
            hits = await client.find.text(pattern="OpenCode", directory=scan_directory)
            show(hits, max_lines=6)
        except Exception as exc:  # noqa: BLE001
            print(f"find.text failed: {exc}")

        rule(f"file.list(path='.', directory={scan_directory!r})")
        try:
            listing = await client.file.list(path=".", directory=scan_directory)
            show(listing, max_lines=6)
        except Exception as exc:  # noqa: BLE001
            print(f"file.list failed: {exc}")

        # Pick a file we know exists — README.md at the repo root.
        rule(f"file.read(path='README.md', directory={scan_directory!r})")
        try:
            content = await client.file.read(
                path="README.md", directory=scan_directory
            )
            show(content, max_lines=6)
        except Exception as exc:  # noqa: BLE001
            print(f"file.read failed: {exc}")

        rule("app.log(level='info', service='sdk-tour', …)")
        try:
            ack = await client.app.log(
                level="info",
                service="sdk-tour",
                message="opencode SDK tour ran",
                extra={"stage": "1"},
            )
            print(f"log ack: {ack}")
        except Exception as exc:  # noqa: BLE001
            print(f"app.log failed: {exc}")

        rule("session.list()")
        sessions = await client.session.list()
        print(f"existing sessions: {len(names_of(sessions, limit=9999))}")

        # ── CONVERSATION + SESSION LIFECYCLE ────────────────────────────────
        rule("session.create(title='SDK tour')")
        session = await client.session.create(title="SDK tour")
        sid = session.id
        print(f"new session: {sid}")

        # Stream events in the background while we drive the session.
        event_log: list[str] = []

        async def tail_events() -> None:
            try:
                stream = await client.event.list()
                async for evt in stream:
                    name = (
                        getattr(evt, "type", None)
                        or (
                            evt.get("type") if isinstance(evt, dict) else None
                        )
                        or type(evt).__name__
                    )
                    event_log.append(str(name))
                    if len(event_log) <= 6:
                        # Don't flood stdout — print the first handful as
                        # live proof the stream is flowing.
                        print(f"  [event] {name}")
                    if len(event_log) >= 80:
                        return
            except Exception as exc:  # noqa: BLE001
                print(f"(event stream closed: {exc})")

        tail_task = asyncio.create_task(tail_events())

        try:
            rule("session.get(id)")
            fetched = await client.session.get(id=sid)
            show(fetched, max_lines=8)

            rule("session.update(id, title='SDK tour — live')")
            renamed = await client.session.update(id=sid, title="SDK tour — live")
            print(f"title is now: {renamed.title}")

            model_spec = {"provider_id": provider, "model_id": model}
            turns = [
                "In one sentence, what's the opencode server?",
                "Remember: the magic word is 'thunderpike'. Acknowledge briefly.",
                "What was the magic word I asked you to remember?",
            ]
            for i, prompt in enumerate(turns, start=1):
                rule(f"session.prompt() — turn {i}")
                print(f"you> {prompt}")
                started = time.monotonic()
                resp = await client.session.prompt(
                    id=sid,
                    parts=[{"type": "text", "text": prompt}],
                    model=model_spec,
                )
                print(
                    f"opencode ({time.monotonic() - started:.1f}s)> "
                    f"{response_text(resp) or '(no text)'}"
                )

            rule("session.messages(id)")
            messages = await client.session.messages(id=sid)
            if hasattr(messages, "model_dump"):
                raw = messages.model_dump(mode="json")
            else:
                raw = messages
            msg_list = raw if isinstance(raw, list) else raw.get("items") or []
            print(f"message count: {len(msg_list)}")
            for m in msg_list[-4:]:
                info = m.get("info") if isinstance(m, dict) else {}
                role = (info.get("role") if isinstance(info, dict) else None) or "?"
                mid = (info.get("id") if isinstance(info, dict) else None) or "?"
                print(f"  - {str(role):9s} {mid}")

            # Pick the last message id for session.message(single) probe.
            last_mid: Optional[str] = None
            if msg_list:
                last = msg_list[-1]
                if isinstance(last, dict):
                    info = last.get("info") or {}
                    if isinstance(info, dict):
                        last_mid = info.get("id")
            if last_mid:
                rule(f"session.message(message_id='{last_mid[:12]}…', id=sid)")
                single = await client.session.message(
                    message_id=last_mid, id=sid
                )
                show(single, max_lines=6)

            rule("session.shell(id, command='echo hi from shell', agent=…)")
            try:
                agent_name = _first_agent_name(agents) or "build"
                shell_resp = await client.session.shell(
                    id=sid,
                    command="echo hi from shell",
                    agent=agent_name,
                )
                show(shell_resp, max_lines=6)
            except Exception as exc:  # noqa: BLE001
                print(f"session.shell failed: {exc}")

            rule("session.summarize(id, model)")
            try:
                summary = await client.session.summarize(
                    id=sid, model_id=model, provider_id=provider
                )
                show(summary, max_lines=6)
            except Exception as exc:  # noqa: BLE001
                print(f"session.summarize failed: {exc}")

            rule("session.share(id) → url")
            try:
                shared = await client.session.share(id=sid)
                print(f"share: {getattr(shared, 'share', None) or shared}")
            except Exception as exc:  # noqa: BLE001
                print(f"session.share failed: {exc}")

            rule("session.unshare(id)")
            try:
                await client.session.unshare(id=sid)
                print("unshared")
            except Exception as exc:  # noqa: BLE001
                print(f"session.unshare failed: {exc}")

            rule("session.children(id)")
            try:
                kids = await client.session.children(id=sid)
                print(f"children count: {len(names_of(kids, limit=9999))}")
            except Exception as exc:  # noqa: BLE001
                print(f"session.children failed: {exc}")

            rule("session.abort(id)")
            try:
                aborted = await client.session.abort(id=sid)
                print(f"abort ack: {aborted}")
            except Exception as exc:  # noqa: BLE001
                print(f"session.abort failed: {exc}")

        finally:
            # Pull one last tally from the event stream, then shut it
            # down cleanly — don't let it outlive the session.
            await asyncio.sleep(0.5)
            tail_task.cancel()
            try:
                await tail_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass

            rule("event stream summary")
            from collections import Counter

            counts = Counter(event_log)
            for name, n in counts.most_common():
                print(f"  {n:4d}  {name}")

            rule("session.delete(id)")
            try:
                ack = await client.session.delete(id=sid)
                print(f"delete ack: {ack}")
            except Exception as exc:  # noqa: BLE001
                print(f"session.delete failed: {exc}")


def _first_agent_name(agents: Any) -> Optional[str]:
    if hasattr(agents, "model_dump"):
        data = agents.model_dump(mode="json")
    else:
        data = agents
    if isinstance(data, list):
        for row in data:
            if isinstance(row, dict) and row.get("name"):
                return row["name"]
    return None


# ─── entrypoint ─────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--provider", default=DEFAULT_PROVIDER)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--no-boot", action="store_true")
    parser.add_argument(
        "--scan-directory",
        default=str(REPO_ROOT),
        help="Directory the find/file calls run against (default: this repo)",
    )
    args = parser.parse_args()
    base_url = f"http://{args.host}:{args.port}"

    proc: Optional[subprocess.Popen[bytes]] = None
    try:
        if not args.no_boot:
            print("booting OpenCode server …")
            proc = boot_opencode(host=args.host, port=args.port)
            wait_until_up(base_url, timeout_s=30)
            print(f"OpenCode up at {base_url}")
        else:
            wait_until_up(base_url, timeout_s=5)

        asyncio.run(
            tour(
                base_url=base_url,
                provider=args.provider,
                model=args.model,
                scan_directory=args.scan_directory,
            )
        )
        return 0
    finally:
        if proc is not None:
            stop_process(proc)


if __name__ == "__main__":
    sys.exit(main())
