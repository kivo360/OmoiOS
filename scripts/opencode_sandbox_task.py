#!/usr/bin/env python3
"""Stage 3: OpenCode running inside a Daytona sandbox does real work.

Stages 1 and 2 proved we can chat with OpenCode. Stage 3 proves the
in-sandbox OpenCode can *act* — invoke its tools, write files to the
sandbox filesystem, and run shell commands — all observable from the
host via the opencode-ai SDK and independently verifiable by exec'ing
commands against the sandbox out-of-band.

Flow:
    1. Spawn a Daytona sandbox from the `omoios-omo-vnc` snapshot.
    2. Write `auth.json` with the zai-coding-plan credential.
    3. Start `opencode serve` inside the sandbox on :4096.
    4. Open the Daytona preview tunnel.
    5. Discover a primary (non-subagent) agent via `client.agent.list()`.
    6. Kick off `client.event.list()` in a background task — we'll tally
       every frame that flows across the wire.
    7. Give OpenCode a concrete task:
         a) create `/tmp/stage3-demo.md` with three lines
         b) report the exact line count via `wc -l`
    8. Wait for the prompt to complete.
    9. Independently verify (via `sandbox.process.exec`, not through
       OpenCode) that the file actually landed on the filesystem with
       the expected content.
   10. Print an event-stream summary (types seen + counts + first few
       tool-call part identifiers).
   11. Clean up.

Why the independent verify matters: when the agent runs the
`write` tool and then `bash`, we want to confirm the sandbox filesystem
actually changed rather than just trusting the model's prose. That
closes the loop — the agent isn't "reporting" a file; it wrote one.

Usage:
    uv run python scripts/opencode_sandbox_task.py [--keep-sandbox]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections import Counter
from typing import Any, Optional

import httpx


DEFAULT_SNAPSHOT = "omoios-omo-vnc"
DEFAULT_PROVIDER = "zai-coding-plan"
DEFAULT_MODEL = "glm-5.1"
DEFAULT_PORT = 4096
DEFAULT_ZAI_KEY = "d372fd4ff6aa4e939084c767f7a0333b.EBGBvMQhO3lwN1mR"

TARGET_PATH = "/tmp/stage3-demo.md"
TASK_PROMPT = (
    f"Please complete this task:\n\n"
    f"1. Create the file {TARGET_PATH} with EXACTLY these three lines (no extras):\n"
    f"   - thunder\n"
    f"   - pike\n"
    f"   - lightning\n"
    f"\n"
    f"2. After writing the file, run `wc -l {TARGET_PATH}` and report the "
    f"exact line count it prints.\n"
    f"\n"
    f"When you're done, reply with one sentence stating the line count. "
    f"Use your tools — don't fake it."
)


# ─── sandbox lifecycle ───────────────────────────────────────────────────────


def _make_daytona():
    from daytona import Daytona, DaytonaConfig

    api_key = os.environ.get("DAYTONA_API_KEY")
    if not api_key:
        raise RuntimeError("DAYTONA_API_KEY env var is required")
    return Daytona(
        DaytonaConfig(
            api_key=api_key,
            api_url=os.environ.get("DAYTONA_API_URL", "https://app.daytona.io/api"),
            target=os.environ.get("DAYTONA_TARGET", "us"),
        )
    )


def spawn_sandbox(snapshot: str):
    from daytona import CreateSandboxFromSnapshotParams

    d = _make_daytona()
    params = CreateSandboxFromSnapshotParams(
        snapshot=snapshot,
        labels={"purpose": "opencode-stage-3", "ts": str(int(time.time()))},
        env_vars={"OPENCODE_STAGE3": "1"},
    )
    print(f"creating sandbox from snapshot={snapshot} …")
    sb = d.create(params, timeout=120)
    print(f"sandbox id: {sb.id}")
    return sb


def run_cmd(sandbox, cmd: str, *, timeout: int = 30) -> str:
    result = sandbox.process.exec(cmd, timeout=timeout)
    return str(
        getattr(result, "result", None) or getattr(result, "stdout", None) or ""
    ).strip()


def write_auth_json(sandbox, *, zai_key: str) -> None:
    data_dir = "$HOME/.local/share/opencode"
    run_cmd(sandbox, f"mkdir -p {data_dir} && chmod 0700 {data_dir}")
    payload = json.dumps({"zai-coding-plan": {"type": "api", "key": zai_key}})
    run_cmd(
        sandbox, f"cat > {data_dir}/auth.json <<'JSON'\n{payload}\nJSON"
    )
    run_cmd(sandbox, f"chmod 0600 {data_dir}/auth.json")


def start_opencode(sandbox, *, port: int) -> None:
    from daytona.common.process import SessionExecuteRequest

    sandbox.process.create_session("opencode-serve")
    sandbox.process.execute_session_command(
        "opencode-serve",
        SessionExecuteRequest(
            command=(
                f"nohup opencode serve --port {port} --hostname 0.0.0.0 "
                "> /tmp/opencode-serve.log 2>&1 &"
            ),
            var_async=True,
        ),
        timeout=10,
    )


def open_preview(sandbox, *, port: int):
    pp = sandbox.get_preview_link(port)
    return pp.url, pp.token


def wait_for_health(url: str, *, token: str, timeout_s: float = 60.0) -> None:
    deadline = time.monotonic() + timeout_s
    headers = {"x-daytona-preview-token": token}
    last: Optional[str] = None
    while time.monotonic() < deadline:
        try:
            r = httpx.get(f"{url}/global/health", headers=headers, timeout=3.0)
            if r.status_code == 200:
                return
            last = f"{r.status_code}"
        except Exception as exc:  # noqa: BLE001
            last = type(exc).__name__
        time.sleep(1.5)
    raise RuntimeError(f"opencode not healthy through tunnel (last: {last})")


# ─── host-side SDK work ──────────────────────────────────────────────────────


def rule(title: str) -> None:
    print()
    print("═" * 80)
    print(f"  {title}")
    print("═" * 80)


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


def response_tool_calls(resp: Any) -> list[str]:
    """Flat list of tool names invoked in one prompt response."""
    names: list[str] = []
    parts = getattr(resp, "parts", None) or []
    for p in parts:
        ptype = getattr(p, "type", None) or (
            p.get("type") if isinstance(p, dict) else None
        )
        if ptype != "tool":
            continue
        # Part shape: {type: "tool", tool: "<name>", id, input?, output?, …}
        tool = getattr(p, "tool", None) or (
            p.get("tool") if isinstance(p, dict) else None
        )
        if isinstance(tool, str) and tool:
            names.append(tool)
    return names


def pick_primary_agent(agents: Any) -> str:
    """Return a non-subagent 'build'-style agent to run the task.

    We prefer:
      1. an agent explicitly named `build`
      2. any agent with mode=='primary'
      3. the first agent in the list as a last resort
    """
    rows: list[dict] = []
    if hasattr(agents, "model_dump"):
        data = agents.model_dump(mode="json")
        if isinstance(data, list):
            rows = [r for r in data if isinstance(r, dict)]
    for r in rows:
        if r.get("name") == "build":
            return "build"
    for r in rows:
        if (r.get("mode") or "").lower() == "primary":
            return str(r.get("name"))
    if rows:
        return str(rows[0].get("name") or "build")
    return "build"


async def run_stage3(
    *,
    preview_url: str,
    preview_token: str,
    provider: str,
    model: str,
    sandbox,
) -> None:
    from opencode_ai import AsyncOpencode

    headers = {"x-daytona-preview-token": preview_token}
    async with AsyncOpencode(
        base_url=preview_url, timeout=300.0, default_headers=headers
    ) as client:
        rule("agent.list() — pick a tool-using agent")
        agents = await client.agent.list()
        agent_name = pick_primary_agent(agents)
        print(f"chosen agent: {agent_name}")

        rule("event.list() — start tailing the sandbox-side SSE stream")
        event_counts: Counter[str] = Counter()
        tool_trace: list[str] = []
        first_frames: list[str] = []

        async def tail_events() -> None:
            try:
                stream = await client.event.list()
                async for evt in stream:
                    name = (
                        getattr(evt, "type", None)
                        or (evt.get("type") if isinstance(evt, dict) else None)
                        or type(evt).__name__
                    )
                    event_counts[str(name)] += 1
                    # Capture the first ~6 frames for visible proof the
                    # stream opened before the prompt completes.
                    if len(first_frames) < 6:
                        first_frames.append(str(name))
                    # When a tool part is updated, remember its name.
                    if str(name) == "message.part.updated":
                        props = getattr(evt, "properties", None)
                        part = getattr(props, "part", None) if props else None
                        ptype = getattr(part, "type", None)
                        if ptype == "tool":
                            tname = getattr(part, "tool", None)
                            if isinstance(tname, str) and tname:
                                tool_trace.append(tname)
            except Exception as exc:  # noqa: BLE001
                print(f"(event stream closed: {exc})")

        tail_task = asyncio.create_task(tail_events())

        try:
            rule("session.create() + session.prompt()")
            session = await client.session.create(title="stage-3 file-write task")
            sid = session.id
            print(f"session: {sid}")
            print()
            print("you>")
            print(TASK_PROMPT)

            started = time.monotonic()
            resp = await client.session.prompt(
                id=sid,
                agent=agent_name,
                parts=[{"type": "text", "text": TASK_PROMPT}],
                model={"provider_id": provider, "model_id": model},
            )
            elapsed = time.monotonic() - started

            rule(f"sandboxed opencode ({elapsed:.1f}s)")
            print(response_text(resp) or "(no text)")

            rule("tool calls observed in the response")
            per_response_tools = response_tool_calls(resp)
            if per_response_tools:
                for i, tname in enumerate(per_response_tools, start=1):
                    print(f"  {i:2d}. {tname}")
            else:
                print("(no tool parts in response — check event stream below)")
            print(
                f"via event stream: {len(tool_trace)} tool update frames "
                f"across {len(set(tool_trace))} distinct tools: "
                f"{sorted(set(tool_trace))}"
            )

            # ── INDEPENDENT VERIFICATION ────────────────────────────────────
            rule("out-of-band verify: sandbox.process.exec('cat …')")
            contents = run_cmd(sandbox, f"cat {TARGET_PATH}")
            print(f"--- {TARGET_PATH} ---")
            print(contents or "(empty)")
            print("----")
            line_count = run_cmd(sandbox, f"wc -l < {TARGET_PATH}")
            print(f"independent wc -l: {line_count}")
            expected_words = {"thunder", "pike", "lightning"}
            present = {w for w in expected_words if w in contents.lower()}
            missing = expected_words - present
            if not missing:
                print("✓ all expected lines present")
            else:
                print(f"✗ missing: {sorted(missing)}")

            # Brief tail to give the SSE stream a chance to flush last frames.
            await asyncio.sleep(1.0)

            rule("event stream summary")
            for name, n in event_counts.most_common():
                print(f"  {n:4d}  {name}")
            print()
            print(f"first frames seen: {first_frames}")

            rule("session.messages(sid) — full persisted turn history")
            messages = await client.session.messages(id=sid)
            raw = (
                messages.model_dump(mode="json")
                if hasattr(messages, "model_dump")
                else messages
            )
            msg_list = raw if isinstance(raw, list) else raw.get("items") or []
            # Count per-type parts across the full session.
            part_kinds: Counter[str] = Counter()
            for m in msg_list:
                if not isinstance(m, dict):
                    continue
                for p in m.get("parts", []) or []:
                    if isinstance(p, dict):
                        part_kinds[p.get("type") or "?"] += 1
            print(f"messages: {len(msg_list)}")
            for k, n in part_kinds.most_common():
                print(f"  parts: {n:3d}  {k}")

        finally:
            tail_task.cancel()
            try:
                await tail_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            try:
                await client.session.delete(id=session.id)  # type: ignore[name-defined]
            except Exception:  # noqa: BLE001
                pass


# ─── entrypoint ──────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", default=DEFAULT_SNAPSHOT)
    parser.add_argument("--provider", default=DEFAULT_PROVIDER)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--keep-sandbox", action="store_true")
    args = parser.parse_args()

    zai_key = os.environ.get("OPENCODE_ZAI_KEY", DEFAULT_ZAI_KEY)

    sb = None
    try:
        sb = spawn_sandbox(args.snapshot)

        rule("writing auth.json into the sandbox")
        write_auth_json(sb, zai_key=zai_key)
        print("auth.json: ok")

        rule(f"starting opencode serve on :{args.port} inside sandbox")
        start_opencode(sb, port=args.port)
        time.sleep(2)

        rule("opening Daytona preview tunnel")
        url, token = open_preview(sb, port=args.port)
        print(f"preview url:   {url}")
        print(f"preview token: {token[:8]}… (len {len(token)})")

        rule("polling /global/health through the tunnel")
        wait_for_health(url, token=token, timeout_s=60)
        print("in-sandbox opencode is up and reachable")

        asyncio.run(
            run_stage3(
                preview_url=url,
                preview_token=token,
                provider=args.provider,
                model=args.model,
                sandbox=sb,
            )
        )
        return 0
    finally:
        if sb is not None and not args.keep_sandbox:
            rule("terminating sandbox")
            try:
                sb.delete()
                print("sandbox deleted")
            except Exception as exc:  # noqa: BLE001
                print(f"delete failed: {exc}")


if __name__ == "__main__":
    sys.exit(main())
