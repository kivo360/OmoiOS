"""Taskiq task wrappers for the chat responder.

Promotes ``chat_responder.respond_to_session`` from an in-process
``fire_and_forget`` task to a queued Taskiq job so chat works correctly
across N>1 replicas: any worker can pick up the job, regardless of
which replica took the original ``POST /api/v1/sessions/{id}/messages``.

Falls back to the in-process path when the broker isn't reachable —
keeps dev environments and tests working without requiring a separate
worker process.

Usage:
    # Start a worker so queued jobs run:
    taskiq worker omoi_os.tasks.broker:broker

    # Routes call schedule_response() unchanged; this module wires the
    # broker enqueue + fallback under the hood.
"""

from __future__ import annotations

from typing import Any, Optional

from omoi_os.logging import get_logger
from omoi_os.tasks.broker import broker


logger = get_logger(__name__)


@broker.task(task_name="omoi_os.chat.respond_to_session")
async def respond_to_session_task(session_id: str) -> None:
    """Run one chat-responder turn for a session — Taskiq entry point.

    Resolves the DB service inside the worker so the broker doesn't have
    to serialize the service handle across the queue. The actual response
    logic lives in ``chat_responder.respond_to_session``; this is a thin
    adapter so that function stays usable from both in-process and queued
    contexts.
    """
    from omoi_os.api.dependencies import get_db_service
    from omoi_os.services.chat_responder import respond_to_session

    db = get_db_service()
    await respond_to_session(session_id, db=db)


async def enqueue_response(session_id: str) -> Optional[Any]:
    """Enqueue a chat response on the broker. Returns the task handle or None.

    The handle is best-effort — callers don't need it for the chat path
    (the response surfaces through `session.message` envelopes, not via
    Taskiq's result backend). Returning it makes tests easier when they
    want to await completion.
    """
    try:
        return await respond_to_session_task.kiq(session_id)
    except Exception as exc:  # noqa: BLE001 — broker may be down in dev/test
        logger.warning(
            "chat responder: broker enqueue failed, will fall back in-process",
            session_id=session_id,
            error=str(exc),
        )
        return None
