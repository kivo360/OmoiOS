"""Warm pool of pre-baked sandboxes with opencode-ai already running.

Why: the cold spawn path is ~7-10s of real time (Daytona boot + auth.json
+ start opencode + tunnel + health). That's the floor on a user's first
message. If we keep N sandboxes warm in a pool — already spawned,
serving opencode, port exposed, healthy — then "first message" drops to
SDK overhead + model latency. Fresh ones refill the pool in the
background so the invariant stays `len(available) >= N` amortized.

The pool is:
  • **opt-in**, default size zero — set FEATURE_SANDBOX_WARM_POOL_SIZE
    to turn it on. Zero means no background activity; `try_acquire`
    always returns None and `get_or_spawn` falls through to a fresh
    spawn. Good for dev and anyone who doesn't want the bill for idle
    Daytona time.
  • **stateless across restarts** — no persistence. On uvicorn boot we
    refill to size; on shutdown we tear down every pool entry. Any
    sandboxes that were already "owned" by a session (claimed out of
    the pool) are tracked on task.result (see sandboxed_agent.py) so
    they survive the restart via rehydration — that's a separate path.
  • **thread-unsafe across processes** — on multi-replica Railway we'd
    keep the pool per replica; aggregate capacity is N × replicas.
    Redis-coordinated pools are a stage-6 problem.

Shape:
    await start()     # on FastAPI lifespan startup
    prebaked = await try_acquire()   # non-blocking; returns None if empty
    await shutdown()  # on FastAPI lifespan shutdown
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Optional

from omoi_os.logging import get_logger


logger = get_logger(__name__)


def _pool_size() -> int:
    """Read the pool size from env every time (so tests can tweak it)."""
    try:
        return max(0, int(os.environ.get("FEATURE_SANDBOX_WARM_POOL_SIZE", "0")))
    except (TypeError, ValueError):
        return 0


# ─── state ──────────────────────────────────────────────────────────────────


_available: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
_refill_task: Optional[asyncio.Task[None]] = None
_refill_lock = asyncio.Lock()
_shutdown_event: asyncio.Event = asyncio.Event()
_started = False


# ─── public API ─────────────────────────────────────────────────────────────


async def try_acquire(timeout_s: float = 0.5) -> Optional[dict[str, Any]]:
    """Claim one warm entry. Non-blocking-ish — gives the queue a brief
    chance to hand over, then returns None if none are ready.

    Returns the provisioned dict straight out of `_provision_live_sandbox`:
    {sandbox, sandbox_id, preview_url, preview_token, spawned_at}.

    The caller owns the handle from this point; the pool will refill in
    the background. A None return is NOT an error — it just means cold
    path.
    """
    if _pool_size() <= 0:
        return None
    try:
        prebaked = await asyncio.wait_for(_available.get(), timeout=timeout_s)
    except asyncio.TimeoutError:
        return None
    # Kick the refill loop — there's now a free slot to fill.
    _schedule_refill()
    return prebaked


async def start() -> None:
    """Bring the pool up. Idempotent — safe to call from lifespan."""
    global _started
    if _started:
        return
    _started = True
    _shutdown_event.clear()
    if _pool_size() <= 0:
        logger.info("sandbox pool disabled (size=0)")
        return
    logger.info(f"sandbox pool starting (target size {_pool_size()})")
    _schedule_refill()


async def shutdown() -> None:
    """Tear everything the pool owns. Idempotent."""
    global _refill_task, _started
    _shutdown_event.set()
    if _refill_task is not None:
        _refill_task.cancel()
        try:
            await _refill_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
        _refill_task = None
    # Drain and destroy any pre-baked sandboxes that never got claimed.
    while not _available.empty():
        try:
            entry = _available.get_nowait()
        except asyncio.QueueEmpty:
            break
        try:
            sb = entry.get("sandbox")
            if sb is not None:
                sb.delete()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "pool shutdown: entry delete failed",
                sandbox_id=entry.get("sandbox_id"),
                error=str(exc),
            )
    _started = False


async def size() -> int:
    return _available.qsize()


# ─── refill loop ────────────────────────────────────────────────────────────


def _schedule_refill() -> None:
    """Ensure a single refill coroutine is running."""
    global _refill_task
    if _refill_task is not None and not _refill_task.done():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return  # no loop yet (e.g. during import)
    _refill_task = loop.create_task(_refill_loop(), name="sandbox-pool-refill")


async def _refill_loop() -> None:
    """Top up the pool until it reaches the target size, then idle."""
    async with _refill_lock:
        try:
            target = _pool_size()
            while not _shutdown_event.is_set() and _available.qsize() < target:
                try:
                    entry = await _spawn_pool_entry()
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "sandbox pool: refill entry failed — retrying in 30s",
                        error=str(exc),
                    )
                    await asyncio.sleep(30)
                    continue
                await _available.put(entry)
                logger.info(
                    f"sandbox pool: entry added — size now "
                    f"{_available.qsize()}/{target}"
                )
        except asyncio.CancelledError:
            raise


async def _spawn_pool_entry() -> dict[str, Any]:
    """Provision one warm sandbox for the pool."""
    from omoi_os.services.sandboxed_agent import _provision_live_sandbox

    labels = {
        "purpose": "omoios-sandbox-pool",
        "ts": str(int(time.time())),
    }
    provisioned = await _provision_live_sandbox(labels)
    provisioned["spawned_at"] = time.time()
    return provisioned
