"""Safe fire-and-forget for asyncio tasks.

Why this module exists: `asyncio.create_task(coro)` returns a `Task`
that must be referenced by *something* until it completes. From the
Python docs:

    Important: Save a reference to the result of this function, to
    avoid a task disappearing mid-execution. The event loop only
    keeps weak references to tasks. A task that isn't referenced
    elsewhere may be garbage collected at any time, even before it's
    done.

This bit us in production: `chat_responder.schedule_response` used
`asyncio.create_task(...)` and threw the result away. The task was
collected before it ever ran, so initial-prompt agent replies
silently disappeared. The bug only fires under load (when the GC
runs between the `create_task` call and the next event-loop tick),
which is why local dev didn't catch it.

Use `fire_and_forget(coro)` instead of `asyncio.create_task(coro)`
whenever you don't keep the returned `Task` somewhere. The helper
holds a strong reference in a module-level set and removes it via
`add_done_callback` so the GC can't collect the task mid-flight.

Direct `asyncio.create_task` is fine when *you* keep the reference:

    self._task = asyncio.create_task(self._loop())     # OK — held on instance
    tasks.append(asyncio.create_task(worker()))         # OK — held in list

Direct `asyncio.create_task` is NOT fine in any of these patterns:

    asyncio.create_task(notify_listener(...))           # Bug — discarded
    schedule_response(...)                              # Bug if helper does the same
    asyncio.create_task(coro)                           # Bug — discarded
"""

from __future__ import annotations

import asyncio
from typing import Any, Coroutine, Optional, Set

from omoi_os.logging import get_logger

logger = get_logger(__name__)


# Module-level strong-reference set so the GC can't collect a
# fire-and-forget task before it runs. Tasks are removed via
# `add_done_callback` once they finish or raise.
_BACKGROUND_TASKS: Set[asyncio.Task[Any]] = set()


def fire_and_forget(
    coro: Coroutine[Any, Any, Any],
    *,
    name: Optional[str] = None,
    log_exceptions: bool = True,
) -> asyncio.Task[Any]:
    """Schedule a coroutine without losing it to the GC.

    Args:
        coro: The coroutine to run.
        name: Optional task name (shows up in `asyncio.all_tasks()`
            and traceback frames — please set it for diagnosability).
        log_exceptions: Log unhandled exceptions raised by the
            coroutine at WARNING level (default True). Disable only
            when the coroutine handles its own errors.

    Returns:
        The created `asyncio.Task` — still safe to ignore. Held in
        a module-level set until done.
    """
    task = asyncio.create_task(coro, name=name)
    _BACKGROUND_TASKS.add(task)

    def _on_done(t: asyncio.Task[Any]) -> None:
        _BACKGROUND_TASKS.discard(t)
        if t.cancelled():
            return
        exc = t.exception()
        if exc is None or not log_exceptions:
            return
        logger.warning(
            "fire-and-forget task raised",
            task_name=t.get_name(),
            error=str(exc),
            error_type=type(exc).__name__,
        )

    task.add_done_callback(_on_done)
    return task


def background_task_count() -> int:
    """How many fire-and-forget tasks are currently in flight.

    Useful for shutdown drains and metrics.
    """
    return len(_BACKGROUND_TASKS)
