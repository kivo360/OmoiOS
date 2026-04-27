"""Textual three-zone TUI for `omoios sessions connect` (spec §18 Pattern D).

Layout (matches the design call):

  ┌─ sess-X · status · N participants ─────────────────────────┐
  ├──────────────────────────────────┬────────────────────────┤
  │  chat-bubble scroll              │ Participants            │
  │   ╭─ agent ─────╮                │  ● you                  │
  │   │ …           │                │  ● dev-b (typing…)      │
  │   ╰─────────────╯                │                         │
  │              ╭─ you ────╮         │ Events                  │
  │              │ try mocks│         │  · session.created      │
  │              ╰──────────╯         │  · session.message      │
  ├──────────────────────────────────┴────────────────────────┤
  │ > _                                                        │
  └────────────────────────────────────────────────────────────┘

Channels feed:
  - SSE event stream → renders chat bubbles + appends to the events log
  - WebSocket `SessionChannel` → presence (typing/joined) + outbound sends

Slash commands routed in-app:
  /share <user|email> [role]
  /fork <from-seq> <prompt>
  /upload <path>
  /quit  (also: Ctrl+C, Ctrl+Q)
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional

from rich.panel import Panel
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, Static


TYPING_DEBOUNCE_SECONDS = 1.5
EVENT_LOG_MAX_LINES = 50


class ChatBubble(Static):
    """One chat message rendered as a Rich Panel inside a Static widget."""

    def __init__(self, *, actor: str, text: str, you: bool) -> None:
        title, style, justify = self._style_for_actor(actor, you)
        panel = Panel(
            Text(text, justify="left"),
            title=title,
            border_style=style,
            title_align="left" if not you else "right",
            padding=(0, 1),
        )
        super().__init__(panel)
        self.classes = "bubble " + ("you" if you else "other")

    @staticmethod
    def _style_for_actor(actor: str, you: bool) -> tuple[str, str, str]:
        if actor == "agent":
            return "agent", "green", "left"
        if you:
            return "you", "cyan", "right"
        if actor.startswith("user:"):
            return actor.split(":", 1)[1][:8], "magenta", "left"
        return actor or "system", "dim", "left"


class ConnectApp(App):
    """Three-zone multiplayer TUI for one session."""

    CSS = """
    Screen {
        layout: vertical;
    }
    #middle {
        height: 1fr;
    }
    #chat {
        width: 3fr;
        padding: 0 1;
    }
    #sidebar {
        width: 1fr;
        border-left: solid cyan;
        padding: 0 1;
    }
    .bubble {
        margin: 0 0 1 0;
        max-width: 80%;
    }
    .bubble.you {
        margin: 0 0 1 8;
    }
    .bubble.other {
        margin: 0 8 1 0;
    }
    #participants {
        height: auto;
        margin-bottom: 1;
    }
    #events {
        height: 1fr;
        color: grey 50%;
    }
    #input {
        dock: bottom;
        height: 3;
        border: solid cyan;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(
        self,
        *,
        api_base_url: str,
        api_key: str,
        session_id: str,
        my_user_id: Optional[str],
        user_jwt: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.api_base_url = api_base_url
        self.api_key = api_key
        self.user_jwt = user_jwt
        self.session_id = session_id
        self.my_user_id = my_user_id or ""
        self._client = None
        self._channel = None
        self._sse_task: Optional[asyncio.Task] = None
        self._typing_task: Optional[asyncio.Task] = None
        self._participants: Dict[str, dict] = {}
        self._event_log: list[str] = []
        # Live-streaming state. Each opencode message-part is rendered as
        # one ChatBubble identified by `part_id`; `_part_text` holds the
        # cumulative text so deltas can append in O(1). `_live_message_ids`
        # tracks which opencode messages have already rendered as live
        # bubbles so the trailing `session.message` envelope (emitted by
        # chat_responder for old clients) doesn't double-render the reply.
        self._part_bubbles: Dict[str, ChatBubble] = {}
        self._part_text: Dict[str, str] = {}
        self._part_type: Dict[str, str] = {}
        self._live_message_ids: set[str] = set()

    # ── compose ────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="middle"):
            yield VerticalScroll(id="chat")
            with Vertical(id="sidebar"):
                yield Static("[bold]Participants[/bold]\n  · just you", id="participants")
                yield Static("[bold]Events[/bold]\n", id="events")
        yield Input(placeholder="message or /command…  (Ctrl+Q to quit)", id="input")
        yield Footer()

    # ── lifecycle ──────────────────────────────────────────────────────────

    async def on_mount(self) -> None:
        self.title = f"omoios · sess-{self.session_id[:8]}"
        self.sub_title = "connecting…"

        from omoios import AsyncOmoiOSClient

        self._client = AsyncOmoiOSClient(
            base_url=self.api_base_url,
            api_key=self.api_key,
            timeout=None,
        )
        await self._client.__aenter__()

        # SSE event-stream reader runs in the background; renders bubbles +
        # event-log lines as envelopes arrive.
        self._sse_task = asyncio.create_task(self._sse_reader())

        # WebSocket channel for presence + outbound sends. Best-effort: if
        # the backend hasn't wired the WS yet we keep the SSE-only mode.
        try:
            # session_channel.py requires a User JWT — platform key won't auth.
            ch = self._client.sessions.connect(self.session_id, user_token=self.user_jwt)
            ch.on("*", self._on_ws_event)
            self._channel = await ch.open()
            self._log_event("ws.connected")
        except Exception as exc:  # noqa: BLE001
            if not self.user_jwt:
                self._log_event(
                    "ws.failed · no user JWT (run `omoios signup` to mint one)"
                )
            else:
                self._log_event(f"ws.failed · {exc}")
            self._channel = None

        self.sub_title = "connected"
        self.query_one(Input).focus()

    async def on_unmount(self) -> None:
        if self._typing_task and not self._typing_task.done():
            self._typing_task.cancel()
        if self._sse_task and not self._sse_task.done():
            self._sse_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._sse_task
        if self._channel is not None:
            with contextlib.suppress(Exception):
                await self._channel.close()
        if self._client is not None:
            with contextlib.suppress(Exception):
                await self._client.__aexit__(None, None, None)

    # ── SSE reader ─────────────────────────────────────────────────────────

    async def _sse_reader(self) -> None:
        """Stream session.* envelopes and render each as a chat bubble."""
        assert self._client is not None
        try:
            async for evt in self._client.sessions.events(self.session_id):
                self._render_envelope(evt)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            self._log_event(f"sse.error · {exc}")

    def _render_envelope(self, evt) -> None:
        etype = getattr(evt, "type", None) or evt.event_type
        actor = getattr(evt, "actor", None) or "system"
        data = evt.data or {}

        if etype == "session.message.part.updated":
            self._render_part_updated(actor, data)
            return
        if etype == "session.message.part.delta":
            self._render_part_delta(actor, data)
            return
        if etype == "session.message":
            text = data.get("text", "")
            # If chat_responder already streamed this assistant message via
            # part.* events, skip the trailing assembled envelope so we
            # don't double-render the same reply.
            if actor == "agent" and self._live_message_ids:
                self._live_message_ids.clear()
                return
            you = actor.startswith("user:") and (
                self.my_user_id and self.my_user_id in actor
            )
            chat = self.query_one("#chat", VerticalScroll)
            chat.mount(ChatBubble(actor=actor, text=text, you=you))
            chat.scroll_end(animate=False)
            return
        if etype == "session.idle":
            # Turn boundary — ready for the next prompt. Live bubbles stay
            # but their per-turn keys clear so the next assistant message
            # gets fresh part ids without colliding.
            return
        self._log_event(f"{etype} · {actor}")

    # ── live streaming helpers ─────────────────────────────────────────────

    def _render_part_updated(self, actor: str, data: Dict[str, Any]) -> None:
        """Cumulative snapshot — opencode's authoritative part state."""
        part = data.get("part") or {}
        if not isinstance(part, dict):
            return
        part_id = part.get("id")
        ptype = part.get("type")
        if not isinstance(part_id, str) or ptype not in ("text", "reasoning", "tool"):
            return
        message_id = part.get("messageID")
        if isinstance(message_id, str):
            self._live_message_ids.add(message_id)

        if ptype == "tool":
            self._render_tool_part(part)
            return

        text = part.get("text", "") or ""
        self._part_text[part_id] = text
        self._part_type[part_id] = ptype
        self._upsert_bubble(part_id, ptype, actor, text)

    def _render_part_delta(self, actor: str, data: Dict[str, Any]) -> None:
        """Token-level delta — append to the running cumulative text."""
        if data.get("field") != "text":
            return
        part_id = data.get("partID")
        delta = data.get("delta", "")
        if not isinstance(part_id, str) or not isinstance(delta, str):
            return
        message_id = data.get("messageID")
        if isinstance(message_id, str):
            self._live_message_ids.add(message_id)
        # Default the part type to "text" until a part.updated tells us
        # otherwise — opencode emits delta first for fresh parts.
        ptype = self._part_type.get(part_id, "text")
        new_text = (self._part_text.get(part_id, "") or "") + delta
        self._part_text[part_id] = new_text
        self._upsert_bubble(part_id, ptype, actor, new_text)

    def _render_tool_part(self, part: Dict[str, Any]) -> None:
        """Tool calls render compact in the events log, not as bubbles."""
        tool = part.get("tool", "?")
        state = part.get("state") or {}
        status = state.get("status") if isinstance(state, dict) else None
        self._log_event(f"tool · {tool} · {status or 'pending'}")

    def _upsert_bubble(
        self, part_id: str, ptype: str, actor: str, text: str
    ) -> None:
        """Mount a bubble for this part on first sight; update in place after."""
        chat = self.query_one("#chat", VerticalScroll)
        bubble = self._part_bubbles.get(part_id)
        if bubble is None:
            bubble = ChatBubble(actor=actor, text=text, you=False)
            # Reasoning bubbles render dimmed so the user can ignore the
            # internal monologue and focus on the actual reply.
            if ptype == "reasoning":
                bubble.classes += " reasoning"
            self._part_bubbles[part_id] = bubble
            chat.mount(bubble)
        else:
            from rich.panel import Panel
            from rich.text import Text

            border = "yellow" if ptype == "reasoning" else "green"
            title = "reasoning" if ptype == "reasoning" else "agent"
            bubble.update(
                Panel(
                    Text(text, justify="left"),
                    title=title,
                    border_style=border,
                    title_align="left",
                    padding=(0, 1),
                )
            )
        chat.scroll_end(animate=False)

    # ── WebSocket inbound ─────────────────────────────────────────────────

    def _on_ws_event(self, msg: Dict[str, Any]) -> None:
        """Handler for every WS frame (registered with `ch.on('*', ...)`)."""
        mtype = msg.get("type", "?")
        if mtype.startswith("participant."):
            self._handle_participant(msg)
        elif mtype.startswith("presence."):
            self._handle_presence(msg)
        else:
            self._log_event(f"ws · {mtype}")

    def _handle_participant(self, msg: Dict[str, Any]) -> None:
        data = msg.get("data") or {}
        uid = data.get("user_id", "?")
        mtype = msg.get("type")
        if mtype == "participant.joined":
            self._participants[uid] = {"user_id": uid}
        elif mtype == "participant.left":
            self._participants.pop(uid, None)
        self._refresh_participants()
        self._log_event(f"{mtype} · {uid[:8]}")

    def _handle_presence(self, msg: Dict[str, Any]) -> None:
        data = msg.get("data") or {}
        uid = data.get("user_id", "?")
        mtype = msg.get("type")
        if uid in self._participants:
            if mtype == "presence.typing":
                self._participants[uid]["typing"] = True
            elif mtype == "presence.idle":
                self._participants[uid]["typing"] = False
        self._refresh_participants()

    def _refresh_participants(self) -> None:
        lines = ["[bold]Participants[/bold]"]
        if not self._participants:
            lines.append("  · just you")
        else:
            for uid, p in self._participants.items():
                marker = " (typing…)" if p.get("typing") else ""
                lines.append(f"  ● {uid[:12]}{marker}")
        self.query_one("#participants", Static).update("\n".join(lines))

    def _log_event(self, line: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self._event_log.append(f"  · {ts} {line}")
        self._event_log = self._event_log[-EVENT_LOG_MAX_LINES:]
        self.query_one("#events", Static).update(
            "[bold]Events[/bold]\n" + "\n".join(self._event_log)
        )

    # ── input → outbound ───────────────────────────────────────────────────

    async def on_input_submitted(self, message: Input.Submitted) -> None:
        text = message.value.strip()
        message.input.value = ""
        if not text:
            return
        if text.startswith("/"):
            await self._handle_slash(text)
            return
        await self._send_message(text)

    async def on_input_changed(self, message: Input.Changed) -> None:
        # Debounced typing indicator — fire `presence.typing` immediately,
        # schedule a single `presence.idle` for after the debounce window.
        if not self._channel:
            return
        await self._safe_send({"type": "presence.typing", "data": {}})
        if self._typing_task and not self._typing_task.done():
            self._typing_task.cancel()
        self._typing_task = asyncio.create_task(self._idle_after_debounce())

    async def _idle_after_debounce(self) -> None:
        try:
            await asyncio.sleep(TYPING_DEBOUNCE_SECONDS)
            await self._safe_send({"type": "presence.idle", "data": {}})
        except asyncio.CancelledError:
            pass

    async def _send_message(self, text: str) -> None:
        if not self._channel:
            self._log_event("send failed · no ws channel")
            return
        await self._safe_send({"type": "message.send", "data": {"text": text}})

    async def _safe_send(self, msg: Dict[str, Any]) -> None:
        try:
            await self._channel.send(msg)
        except Exception as exc:  # noqa: BLE001
            self._log_event(f"send.error · {exc}")

    # ── slash commands ─────────────────────────────────────────────────────

    async def _handle_slash(self, line: str) -> None:
        parts = line[1:].split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        rest = parts[1] if len(parts) > 1 else ""
        if cmd == "quit":
            await self.action_quit()
            return
        if cmd == "share":
            await self._slash_share(rest)
            return
        if cmd == "fork":
            self._log_event("/fork · run `omoios sessions fork` from another shell")
            return
        if cmd == "upload":
            self._log_event("/upload · run `omoios artifacts upload` from another shell")
            return
        self._log_event(f"unknown command: /{cmd}")

    async def _slash_share(self, rest: str) -> None:
        bits = rest.split()
        if not bits:
            self._log_event("/share <user-or-email> [role]")
            return
        target = bits[0]
        role = bits[1] if len(bits) > 1 else "editor"
        from omoios.cli.sessions import _share

        try:
            await _share(self.api_base_url, self.api_key, self.session_id, target, role)
            self._log_event(f"/share · granted {role} to {target}")
        except Exception as exc:  # noqa: BLE001
            self._log_event(f"/share failed · {exc}")


def run_connect_tui(
    *,
    api_base_url: str,
    api_key: str,
    session_id: str,
    my_user_id: Optional[str] = None,
    user_jwt: Optional[str] = None,
) -> None:
    """Launch the Textual app. Blocks until the user quits."""
    app = ConnectApp(
        api_base_url=api_base_url,
        api_key=api_key,
        session_id=session_id,
        my_user_id=my_user_id,
        user_jwt=user_jwt,
    )
    app.run()
