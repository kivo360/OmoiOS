"""Chat responder — turns session.message events into an agent reply.

Rationale: The full Claude-Agent-SDK worker path is the right home for
long-running code-execution sessions, but for *chat* the fastest
end-to-end loop is a backend-local LLM call that listens for user
messages and emits an agent response via the session event envelope.

Shape per reply:
    1. User posts via `POST /sessions/{id}/messages` (reply route).
    2. Reply persists `session.message` with actor=`user:<uuid>`.
    3. Reply schedules `respond_to_session(session_id)` as a background
       asyncio task (fire-and-forget, best-effort).
    4. Responder loads the session's event history, renders it into an
       OpenAI-style messages array, calls the LLM directly via an
       OpenAI-compatible chat completions endpoint (configured through
       LLM_* env vars), and emits the reply via `SessionEventEnvelope.emit(
       event_type="session.message", actor="agent")`.

The responder NEVER writes to the task status — chat is a conversational
loop, not a task run. The session stays in its current state.

Why the direct HTTP path (vs. `LLMService.complete`): the LLM service
routes through PydanticAI's Fireworks provider which hardcodes a model
that may not match our configured LLM_MODEL. For chat we want a plain
OpenAI-compatible chat completion with the exact model the operator set,
so we call the endpoint directly and skip the factory.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
from sqlalchemy import select

from omoi_os.logging import get_logger
from omoi_os.models.event import Event
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import get_event_bus
from omoi_os.services.session_event_envelope import (
    ACTOR_AGENT,
    SessionEventEnvelope,
)


logger = get_logger(__name__)


_DEFAULT_SYSTEM_PROMPT = (
    "You are an assistant helping the user work through a software engineering "
    "task. Be concise and direct. When the user asks a question, answer it "
    "plainly. When the user gives you a task, acknowledge it and say what "
    "you'll do next. Prefer short responses unless depth is explicitly needed."
)


def _history_to_messages(
    events: list[Event],
    *,
    include_created: bool = True,
) -> list[dict[str, str]]:
    """Convert persisted session.* events into {role, content} turns.

    - `session.created` provides the initial user prompt (if any) as the
      opening turn so the agent has context on why the session was made.
    - `session.message` turns are split on actor prefix:
        * `user:<uuid>`  → role="user"
        * `agent`        → role="assistant"
        * `system`       → ignored in the history (status events)
    """
    messages: list[dict[str, str]] = []
    for ev in events:
        etype = ev.event_type
        payload = ev.payload or {}
        if etype == "session.created" and include_created:
            prompt = payload.get("prompt") or payload.get("title")
            if isinstance(prompt, str) and prompt.strip():
                messages.append({"role": "user", "content": prompt.strip()})
            continue
        if etype != "session.message":
            continue
        text = (payload.get("text") or "").strip()
        if not text:
            continue
        actor = ev.actor or ""
        if actor.startswith("user:"):
            messages.append({"role": "user", "content": text})
        elif actor == ACTOR_AGENT:
            messages.append({"role": "assistant", "content": text})
    return messages


async def respond_to_session(
    session_id: str,
    *,
    db: DatabaseService,
) -> None:
    """Generate + emit one agent turn for the given session.

    Fire-and-forget — exceptions are logged and swallowed. The chat UX
    degrades to a silent (user-only) stream if the LLM call fails; the
    session itself is unaffected.
    """
    try:
        # 1. Load the conversation history from the events table. We
        # read inside an async session and copy the event state out so
        # the response path doesn't hold the DB session across the
        # LLM call.
        async with db.get_async_session() as sess:
            rows = (
                (
                    await sess.execute(
                        select(Event)
                        .where(
                            Event.entity_id == session_id,
                            Event.seq.is_not(None),
                            Event.event_type.in_(
                                ("session.created", "session.message")
                            ),
                        )
                        .order_by(Event.seq.asc())
                    )
                )
                .scalars()
                .all()
            )

        messages = _history_to_messages(rows)
        if not messages:
            logger.debug(
                "chat responder has no history to respond to",
                session_id=session_id,
            )
            return
        if messages[-1]["role"] != "user":
            # Last turn is already an agent reply — nothing to respond to.
            logger.debug(
                "chat responder skipped: last turn is agent",
                session_id=session_id,
            )
            return

        # 2. Build a plain user-facing prompt. We hand the LLM the full
        # alternating history as a single rendered context block and the
        # latest user turn as the `prompt`. PydanticAI's `complete` only
        # takes prompt+system, so we inline the history into the system
        # prompt. This keeps the dependency surface narrow.
        rendered = _render_history(messages)
        system_prompt = _DEFAULT_SYSTEM_PROMPT + "\n\n" + rendered["system_suffix"]
        last_user_turn = rendered["latest_user_turn"]

        # 3. Route to the active agent runtime. With the sandboxed-agent
        #    feature flag on, we dispatch the turn to an opencode server
        #    running inside a Daytona sandbox that's bound to this
        #    OmoiOS session; the direct chat completion is kept as the
        #    fallback for when the flag is off or the sandboxed path
        #    fails to come up.
        response_text: str = ""
        try:
            from omoi_os.services import sandboxed_agent as _sandboxed

            if _sandboxed.is_enabled():
                agent = await _sandboxed.get_or_spawn(session_id)
                response_text = await agent.prompt(last_user_turn)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "sandboxed agent path failed — falling back to direct LLM",
                session_id=session_id,
                error=str(exc),
            )

        if not response_text:
            response_text = await _call_chat_completion(
                system_prompt=system_prompt,
                user_prompt=last_user_turn,
            )
        response_text = (response_text or "").strip()
        if not response_text:
            logger.warning(
                "chat responder got empty LLM response",
                session_id=session_id,
            )
            return

        # 4. Emit the agent's reply as a session.message envelope. Same
        # emit path as a normal user reply, just with actor=agent.
        with db.get_session() as esess:
            SessionEventEnvelope(esess, get_event_bus()).emit(
                session_id=session_id,
                event_type="session.message",
                actor=ACTOR_AGENT,
                data={"text": response_text},
            )
            esess.commit()
        logger.info(
            "chat responder emitted agent reply",
            session_id=session_id,
            reply_chars=len(response_text),
        )

        # 5. Mark the task as `completed` so the session reaches a
        # terminal state. For chat-mode SDK-direct sessions, the agent
        # reply IS the work — there's no follow-on sandbox runtime to
        # wait for. The task_queue maps `completed` → `session.succeeded`
        # envelope automatically (see task_queue.update_task_status).
        # When a real sandboxed-agent path is wired (e.g. Modal), this
        # branch should be skipped for sessions that have an env_version
        # with sandbox-bound credentials — the sandbox driver will
        # complete the task itself.
        try:
            from omoi_os.services.task_queue import TaskQueueService

            queue = TaskQueueService(db=db)
            queue.update_task_status(session_id, "completed")
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "chat responder could not mark session completed",
                session_id=session_id,
                error=str(exc),
            )
    except Exception as exc:  # noqa: BLE001 — responder is best-effort
        import traceback

        logger.warning(
            "chat responder failed",
            session_id=session_id,
            error=repr(exc),
            error_type=type(exc).__name__,
            traceback=traceback.format_exc(),
        )


def _render_history(messages: list[dict[str, str]]) -> dict[str, str]:
    """Split the history into (prior-context, latest user turn).

    The LLM service takes a single `prompt` + `system_prompt`. We use the
    system prompt to carry the running conversation ("Here is the prior
    conversation:") and the prompt to carry the newest user turn so the
    LLM replies to *that* specifically.
    """
    if not messages:
        return {"system_suffix": "", "latest_user_turn": ""}

    latest = messages[-1]
    prior = messages[:-1]
    lines: list[str] = []
    if prior:
        lines.append("Prior conversation:")
        for turn in prior:
            who = "User" if turn["role"] == "user" else "Assistant"
            lines.append(f"{who}: {turn['content']}")
        lines.append("")
    else:
        lines.append("No prior conversation.")
    lines.append(
        "Reply to the user's latest message. Do not repeat the entire "
        "history; just answer."
    )
    return {
        "system_suffix": "\n".join(lines),
        "latest_user_turn": latest["content"],
    }


async def _call_chat_completion(
    *, system_prompt: str, user_prompt: str, timeout: float = 120.0
) -> str:
    """Call an OpenAI-compatible chat completions endpoint.

    Reads LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL from the process env
    (these are the same knobs the rest of the platform uses for its LLM
    config). Falls back to a polite placeholder when LLM_API_KEY is
    missing so a chat UX never hangs silently.
    """
    base_url = (os.environ.get("LLM_BASE_URL") or "").rstrip("/")
    api_key = os.environ.get("LLM_API_KEY") or ""
    model = os.environ.get("LLM_MODEL") or ""
    if not base_url or not api_key or not model:
        return (
            "(LLM not configured — set LLM_BASE_URL, LLM_API_KEY, and "
            "LLM_MODEL on the backend to enable chat responses.)"
        )

    # Strip the "openai/" prefix some configs use — upstream expects just
    # the raw model id.
    if model.startswith("openai/"):
        model = model[len("openai/") :]

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{base_url}/chat/completions"
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        body = r.json()
    choices = body.get("choices") or []
    if not choices:
        return ""
    msg = choices[0].get("message") or {}
    return msg.get("content") or ""


def schedule_response(session_id: str, db: DatabaseService) -> asyncio.Task[Any]:
    """Fire-and-forget helper for route handlers.

    Creates an asyncio task bound to the current event loop. Uses
    `fire_and_forget` so the task isn't garbage-collected before it runs
    — bare `asyncio.create_task` here lost initial-prompt agent replies
    in production until 2026-04-26. The task is returned so tests can
    await it; production callers ignore the handle.
    """
    from omoi_os.utils.asyncio_tasks import fire_and_forget

    return fire_and_forget(
        respond_to_session(session_id, db=db),
        name=f"chat_responder:{session_id[:8]}",
    )
