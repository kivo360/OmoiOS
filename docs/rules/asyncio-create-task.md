# asyncio.create_task — never call directly without keeping a reference

## Symptom

Background coroutine appears to never run. No logs, no traceback, no
side effects. Sometimes it works in dev (single request, low load) and
silently breaks in prod (concurrency, GC pressure).

Concrete incident (2026-04-26): `chat_responder.schedule_response`
used `asyncio.create_task(...)` and discarded the return value. The
asyncio task got garbage-collected before the event loop scheduled it,
so initial-prompt agent replies were silently dropped on every fresh
session in production.

## Root cause

From the Python `asyncio.create_task` docs:

> Important: Save a reference to the result of this function, to avoid
> a task disappearing mid-execution. The event loop only keeps weak
> references to tasks. A task that isn't referenced elsewhere may be
> garbage collected at any time, even before it's done.

Python is allowed to collect a `Task` whose only reference was the
return value the caller threw away. Local dev rarely hits it because
GC runs are infrequent. Prod hits it under load.

## Pattern

Use the helper in `omoi_os.utils.asyncio_tasks`:

```python
from omoi_os.utils.asyncio_tasks import fire_and_forget

fire_and_forget(
    do_work_in_background(payload),
    name="my_module:do_work",
)
```

The helper holds the task in a module-level `set` and removes it via
`add_done_callback` once the coroutine finishes — so the GC can never
collect it mid-flight, and exceptions bubble to a warning log instead
of vanishing into the void.

## When direct `asyncio.create_task` is fine

Only when *something else* keeps the reference for the task's full life:

```python
# OK — instance attribute is a strong ref
self._loop_task = asyncio.create_task(self._main_loop())

# OK — appended to a list that outlives the call
self._workers.append(asyncio.create_task(worker()))

# OK — gathered before the local list goes out of scope
tasks = [asyncio.create_task(work(x)) for x in items]
results = await asyncio.gather(*tasks)
```

## When it is NOT fine

Anywhere the return value is discarded:

```python
# Bug — Task is the only reference, GC can collect it
asyncio.create_task(notify_listener(event))

# Bug — same shape, just hidden behind a helper
def schedule(coro):
    return asyncio.create_task(coro)   # caller's discarded return is the bug

schedule(do_work())                     # nothing strong-refs the task
```

## Enforcement

`scripts/check_asyncio_tasks.sh` greps the repo for bare
`asyncio.create_task` and `asyncio.ensure_future` outside the helper
itself. Wired into the pre-commit hook (`asyncio-create-task-guard`).

## See also

- Python docs: <https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task>
- `backend/omoi_os/utils/asyncio_tasks.py` — the helper.
- `backend/omoi_os/services/chat_responder.py:schedule_response` — original incident site.
