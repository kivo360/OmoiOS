# Async Python Patterns for OmoiOS Performance

**Created**: 2025-12-22
**Status**: Approved
**Purpose**: Comprehensive guide for improving OmoiOS backend performance using modern async Python patterns

---

## Executive Summary

This guide provides actionable async Python patterns to improve the OmoiOS backend performance. Based on codebase analysis, the main opportunities are:

| Improvement | Expected Impact | Priority |
|------------|-----------------|----------|
| Async database operations | 50-70% latency reduction | CRITICAL |
| Parallel task processing | 3-5x throughput increase | CRITICAL |
| Eliminate threading patterns | Cleaner shutdown, better resource use | HIGH |
| Batch database operations | 10-50x fewer queries | HIGH |
| Connection pool tuning | Better concurrent handling | MEDIUM |

---

## Table of Contents

1. [Critical Patterns](#1-critical-patterns)
2. [Concurrency Primitives](#2-concurrency-primitives)
3. [Database Async Patterns](#3-database-async-patterns)
4. [Background Task Patterns](#4-background-task-patterns)
5. [Event-Driven Patterns](#5-event-driven-patterns)
6. [Anti-Patterns to Avoid](#6-anti-patterns-to-avoid)
7. [Migration Guide](#7-migration-guide)

---

## 1. Critical Patterns

### 1.1 Parallel Execution with `asyncio.gather()`

**Problem**: Sequential awaits that could run concurrently

```python
# ❌ ANTI-PATTERN: Sequential execution (3 seconds total)
async def process_ticket_slow(ticket_id: str):
    dedup_result = await check_duplicates(ticket_id)      # 1 second
    embedding = await generate_embedding(ticket_id)        # 1 second
    validation = await validate_ticket(ticket_id)          # 1 second
    return dedup_result, embedding, validation

# ✅ PATTERN: Parallel execution (1 second total)
async def process_ticket_fast(ticket_id: str):
    dedup_result, embedding, validation = await asyncio.gather(
        check_duplicates(ticket_id),
        generate_embedding(ticket_id),
        validate_ticket(ticket_id),
    )
    return dedup_result, embedding, validation
```

**When to use**: When operations are independent and don't depend on each other's results.

### 1.2 Parallel with Error Handling

```python
# ✅ PATTERN: Parallel execution with exception handling
async def process_with_fallbacks(items: list[str]) -> list[Result]:
    results = await asyncio.gather(
        *[process_item(item) for item in items],
        return_exceptions=True  # Don't fail fast, collect all results
    )

    successful = []
    failed = []
    for item, result in zip(items, results):
        if isinstance(result, Exception):
            logger.warning(f"Failed to process {item}: {result}")
            failed.append((item, result))
        else:
            successful.append(result)

    return successful, failed
```

### 1.3 Semaphore-Based Concurrency Control

**Problem**: Too many concurrent operations can overwhelm resources

```python
# ✅ PATTERN: Limit concurrent operations
async def analyze_agents_with_throttling(
    agent_ids: list[str],
    max_concurrent: int = 5
) -> list[AnalysisResult]:
    """Analyze multiple agents with controlled concurrency."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def analyze_with_limit(agent_id: str) -> AnalysisResult:
        async with semaphore:  # Only max_concurrent can run simultaneously
            return await analyze_agent(agent_id)

    tasks = [
        asyncio.create_task(analyze_with_limit(agent_id))
        for agent_id in agent_ids
    ]

    return await asyncio.gather(*tasks, return_exceptions=True)
```

### 1.4 TaskGroup for Structured Concurrency (Python 3.11+)

```python
# ✅ PATTERN: TaskGroup provides better error handling than gather
async def process_batch_structured(items: list[Item]) -> list[Result]:
    """Process items with automatic cancellation on first error."""
    results = []

    async with asyncio.TaskGroup() as tg:
        for item in items:
            tg.create_task(process_and_collect(item, results))

    # All tasks completed successfully if we reach here
    # If any task raises, all others are cancelled automatically
    return results

# With exception handling
async def process_batch_safe(items: list[Item]) -> tuple[list[Result], list[Exception]]:
    """Process items, collecting both results and errors."""
    results = []
    errors = []

    try:
        async with asyncio.TaskGroup() as tg:
            for item in items:
                tg.create_task(process_item_safe(item, results, errors))
    except* Exception as eg:
        # Handle exception group (Python 3.11+)
        for exc in eg.exceptions:
            errors.append(exc)

    return results, errors
```

---

## 2. Concurrency Primitives

### 2.1 When to Use Each Primitive

| Primitive | Use Case | Example |
|-----------|----------|---------|
| `asyncio.gather()` | Run multiple coroutines, wait for all | Parallel API calls |
| `asyncio.create_task()` | Fire-and-forget background work | Event publishing |
| `asyncio.TaskGroup` | Structured concurrency with auto-cancel | Batch processing |
| `asyncio.Semaphore` | Limit concurrent operations | Rate limiting |
| `asyncio.Lock` | Mutual exclusion | Shared resource access |
| `asyncio.Event` | Signal between coroutines | Coordination |
| `asyncio.Queue` | Producer-consumer pattern | Work queues |

### 2.2 Fire-and-Forget Pattern

```python
# ✅ PATTERN: Non-blocking event publishing
class EventPublisher:
    def __init__(self):
        self._background_tasks: set[asyncio.Task] = set()

    def publish_fire_and_forget(self, event: SystemEvent) -> None:
        """Publish event without waiting for completion."""
        task = asyncio.create_task(self._publish_async(event))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _publish_async(self, event: SystemEvent) -> None:
        try:
            await self.redis.publish(event.channel, event.to_json())
        except Exception as e:
            logger.warning(f"Failed to publish event: {e}")

    async def shutdown(self) -> None:
        """Wait for all background tasks to complete."""
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
```

### 2.3 Producer-Consumer with Queue

```python
# ✅ PATTERN: Async queue for work distribution
class AsyncTaskProcessor:
    def __init__(self, num_workers: int = 3):
        self.queue: asyncio.Queue[Task] = asyncio.Queue(maxsize=100)
        self.num_workers = num_workers
        self._workers: list[asyncio.Task] = []

    async def start(self) -> None:
        """Start worker tasks."""
        self._workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.num_workers)
        ]

    async def _worker(self, worker_id: int) -> None:
        """Worker that processes tasks from queue."""
        while True:
            task = await self.queue.get()
            try:
                await self.process_task(task)
            except Exception as e:
                logger.error(f"Worker {worker_id} failed: {e}")
            finally:
                self.queue.task_done()

    async def submit(self, task: Task) -> None:
        """Submit task to queue (blocks if queue is full)."""
        await self.queue.put(task)

    async def shutdown(self) -> None:
        """Graceful shutdown: wait for queue, cancel workers."""
        await self.queue.join()  # Wait for all tasks to complete
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
```

---

## 3. Database Async Patterns

### 3.1 Async SQLAlchemy Sessions

**Current Problem**: Sync database calls block the event loop

```python
# ❌ CURRENT: Blocking database access in async endpoint
@router.get("/tasks")
async def list_tasks(db: DatabaseService = Depends(get_db_service)):
    with db.get_session() as session:  # BLOCKS event loop!
        tasks = session.query(Task).filter(Task.status == "pending").all()
        return tasks
```

**Solution**: Use async sessions

```python
# ✅ PATTERN: Async database access
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Setup async engine
async_engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/db",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Dependency for FastAPI
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# Usage in endpoint
@router.get("/tasks")
async def list_tasks(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(
        select(Task).where(Task.status == "pending")
    )
    tasks = result.scalars().all()
    return tasks
```

### 3.2 Batch Database Operations

**Problem**: N+1 queries from loops

```python
# ❌ ANTI-PATTERN: N+1 queries (100 tasks = 100+ queries)
async def get_ready_tasks_slow(session: AsyncSession) -> list[Task]:
    result = await session.execute(select(Task).where(Task.status == "pending"))
    tasks = result.scalars().all()

    ready_tasks = []
    for task in tasks:
        # Each call is a separate query!
        deps_complete = await check_dependencies_complete(session, task)
        if deps_complete:
            ready_tasks.append(task)

    return ready_tasks
```

**Solution**: Batch queries with JOINs or subqueries

```python
# ✅ PATTERN: Single query with JOIN (1-2 queries total)
async def get_ready_tasks_fast(session: AsyncSession) -> list[Task]:
    """Get tasks where all dependencies are complete in ONE query."""

    # Subquery: tasks with incomplete dependencies
    incomplete_deps = (
        select(TaskDependency.task_id)
        .join(Task, TaskDependency.depends_on_id == Task.id)
        .where(Task.status != "completed")
        .distinct()
    )

    # Main query: pending tasks NOT in incomplete deps
    result = await session.execute(
        select(Task)
        .where(Task.status == "pending")
        .where(Task.id.notin_(incomplete_deps))
        .order_by(Task.priority.desc(), Task.created_at)
        .limit(10)
    )

    return result.scalars().all()
```

### 3.3 Bulk Updates

```python
# ❌ ANTI-PATTERN: Update one by one
async def update_scores_slow(session: AsyncSession, tasks: list[Task]):
    for task in tasks:
        task.score = compute_score(task)
        await session.flush()  # 100 flushes!

# ✅ PATTERN: Bulk update
async def update_scores_fast(session: AsyncSession, task_scores: dict[int, float]):
    """Update multiple task scores in one operation."""
    await session.execute(
        update(Task)
        .where(Task.id.in_(task_scores.keys()))
        .values(score=case(task_scores, value=Task.id))
    )
    await session.commit()

# Or with executemany pattern
async def update_scores_batch(session: AsyncSession, updates: list[dict]):
    """Batch update using executemany."""
    await session.execute(
        update(Task).where(Task.id == bindparam('task_id')),
        updates  # [{"task_id": 1, "score": 0.9}, ...]
    )
```

### 3.4 Raw Asyncpg for Performance-Critical Paths

For maximum performance, use asyncpg directly:

```python
# ✅ PATTERN: Direct asyncpg for hot paths
import asyncpg

class HighPerformanceTaskQueue:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self._prepared_get_ready = None

    async def initialize(self):
        """Prepare frequently-used statements."""
        async with self.pool.acquire() as conn:
            self._prepared_get_ready = await conn.prepare('''
                SELECT t.* FROM tasks t
                WHERE t.status = 'pending'
                AND NOT EXISTS (
                    SELECT 1 FROM task_dependencies td
                    JOIN tasks dep ON td.depends_on_id = dep.id
                    WHERE td.task_id = t.id AND dep.status != 'completed'
                )
                ORDER BY t.priority DESC, t.created_at
                LIMIT $1
            ''')

    async def get_ready_tasks(self, limit: int = 10) -> list[dict]:
        """Get ready tasks using prepared statement."""
        async with self.pool.acquire() as conn:
            rows = await self._prepared_get_ready.fetch(limit)
            return [dict(row) for row in rows]

    async def bulk_update_status(
        self,
        task_ids: list[int],
        status: str
    ) -> int:
        """Bulk update task status."""
        async with self.pool.acquire() as conn:
            result = await conn.execute('''
                UPDATE tasks
                SET status = $1, updated_at = NOW()
                WHERE id = ANY($2)
            ''', status, task_ids)
            return int(result.split()[-1])  # Returns "UPDATE N"
```

---

## 4. Background Task Patterns

### 4.1 Replace Threading with Async

**Current Problem**: HeartbeatManager uses threading

```python
# ❌ CURRENT: Threading pattern (worker.py)
class HeartbeatManager:
    def start(self) -> None:
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()

    def _heartbeat_loop(self):
        while self._running:
            self._emit_heartbeat()
            time.sleep(30)  # BLOCKS!
```

**Solution**: Pure async implementation

```python
# ✅ PATTERN: Async heartbeat manager
class AsyncHeartbeatManager:
    def __init__(
        self,
        agent_id: str,
        health_service: AgentHealthService,
        interval_seconds: float = 30.0,
    ):
        self.agent_id = agent_id
        self.health_service = health_service
        self.interval = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        """Start async heartbeat loop."""
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._heartbeat_loop())

    async def stop(self) -> None:
        """Gracefully stop heartbeat loop."""
        if self._task is None:
            return
        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _heartbeat_loop(self) -> None:
        """Async heartbeat loop."""
        while not self._stop_event.is_set():
            try:
                await self._emit_heartbeat()
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")

            # Non-blocking sleep with early exit support
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.interval
                )
                break  # Stop event was set
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue loop

    async def _emit_heartbeat(self) -> None:
        """Emit heartbeat to health service."""
        await self.health_service.record_heartbeat_async(self.agent_id)
```

### 4.2 Background Loop with Graceful Shutdown

```python
# ✅ PATTERN: Production-ready background loop
class BackgroundLoopManager:
    def __init__(self):
        self._loops: dict[str, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()

    def register_loop(
        self,
        name: str,
        coro_func: Callable[[], Coroutine],
        interval_seconds: float,
    ) -> None:
        """Register a background loop."""
        async def loop_wrapper():
            while not self._shutdown_event.is_set():
                try:
                    await coro_func()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.exception(f"Loop {name} error: {e}")

                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=interval_seconds
                    )
                    break
                except asyncio.TimeoutError:
                    pass

        self._loops[name] = asyncio.create_task(loop_wrapper())

    async def shutdown(self, timeout: float = 30.0) -> None:
        """Gracefully shutdown all loops."""
        self._shutdown_event.set()

        if self._loops:
            done, pending = await asyncio.wait(
                self._loops.values(),
                timeout=timeout
            )

            # Force cancel any still pending
            for task in pending:
                task.cancel()

            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
```

### 4.3 FastAPI BackgroundTasks Pattern

```python
# ✅ PATTERN: Background tasks with FastAPI
from fastapi import BackgroundTasks

@router.post("/tickets")
async def create_ticket(
    ticket_data: TicketCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
):
    """Create ticket with background processing."""
    # Critical path: create ticket synchronously
    ticket = Ticket(**ticket_data.model_dump())
    session.add(ticket)
    await session.flush()
    ticket_id = ticket.id

    # Non-critical: defer to background
    background_tasks.add_task(
        generate_embedding_background,
        ticket_id=ticket_id,  # Pass ID, not object!
    )
    background_tasks.add_task(
        notify_subscribers_background,
        ticket_id=ticket_id,
    )

    await session.commit()
    return {"ticket_id": ticket_id}


async def generate_embedding_background(ticket_id: int) -> None:
    """Background task creates its own resources."""
    # Create new session - don't share with request!
    async with AsyncSessionLocal() as session:
        ticket = await session.get(Ticket, ticket_id)
        if ticket:
            embedding = await embedding_service.generate(ticket.description)
            ticket.embedding = embedding
            await session.commit()
```

---

## 5. Event-Driven Patterns

### 5.1 Async Event Bus

```python
# ✅ PATTERN: Async-native event bus
from typing import Callable, Coroutine, Any
import aioredis

class AsyncEventBus:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None
        self._pubsub: Optional[aioredis.PubSub] = None
        self._handlers: dict[str, list[Callable]] = {}
        self._listener_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Initialize Redis connection."""
        self._redis = await aioredis.from_url(self.redis_url)
        self._pubsub = self._redis.pubsub()

    async def subscribe(
        self,
        event_type: str,
        handler: Callable[[SystemEvent], Coroutine[Any, Any, None]],
    ) -> None:
        """Subscribe async handler to event type."""
        channel = f"events.{event_type}"

        if channel not in self._handlers:
            self._handlers[channel] = []
            await self._pubsub.subscribe(channel)

        self._handlers[channel].append(handler)

    async def publish(self, event: SystemEvent) -> None:
        """Publish event to Redis."""
        channel = f"events.{event.event_type}"
        await self._redis.publish(channel, event.model_dump_json())

    async def start_listening(self) -> None:
        """Start async listener."""
        self._listener_task = asyncio.create_task(self._listen_loop())

    async def _listen_loop(self) -> None:
        """Async event listener loop."""
        async for message in self._pubsub.listen():
            if message["type"] != "message":
                continue

            channel = message["channel"].decode()
            handlers = self._handlers.get(channel, [])

            if handlers:
                event = SystemEvent.model_validate_json(message["data"])
                # Run all handlers concurrently
                await asyncio.gather(
                    *[handler(event) for handler in handlers],
                    return_exceptions=True,
                )

    async def close(self) -> None:
        """Clean shutdown."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self._pubsub:
            await self._pubsub.unsubscribe()

        if self._redis:
            await self._redis.close()
```

### 5.2 WebSocket Broadcasting

```python
# ✅ PATTERN: Efficient WebSocket broadcasting
class WebSocketManager:
    def __init__(self):
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        """Broadcast to all connections concurrently."""
        async with self._lock:
            connections = list(self._connections)

        if not connections:
            return

        # Broadcast to all concurrently
        results = await asyncio.gather(
            *[self._send_safe(ws, message) for ws in connections],
            return_exceptions=True,
        )

        # Remove failed connections
        failed = [
            ws for ws, result in zip(connections, results)
            if isinstance(result, Exception)
        ]
        if failed:
            async with self._lock:
                for ws in failed:
                    self._connections.discard(ws)

    async def _send_safe(self, websocket: WebSocket, message: dict) -> None:
        """Send with timeout to avoid blocking on slow clients."""
        try:
            await asyncio.wait_for(
                websocket.send_json(message),
                timeout=5.0,
            )
        except asyncio.TimeoutError:
            raise ConnectionError("Send timeout")
```

---

## 6. Anti-Patterns to Avoid

### 6.1 Blocking Calls in Async Context

```python
# ❌ NEVER: Blocking calls in async functions
async def bad_endpoint():
    time.sleep(1)  # BLOCKS event loop!
    requests.get("http://api.example.com")  # BLOCKS!
    with open("file.txt") as f:  # Potentially BLOCKS!
        data = f.read()

# ✅ ALWAYS: Use async equivalents
async def good_endpoint():
    await asyncio.sleep(1)
    async with httpx.AsyncClient() as client:
        await client.get("http://api.example.com")
    async with aiofiles.open("file.txt") as f:
        data = await f.read()
```

### 6.2 Running Sync Code in Async

When you must call sync code from async:

```python
# ✅ PATTERN: Run blocking code in executor
import asyncio
from concurrent.futures import ThreadPoolExecutor

# For CPU-bound work
executor = ThreadPoolExecutor(max_workers=4)

async def call_sync_safely(sync_func, *args):
    """Run sync function without blocking event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, sync_func, *args)

# Usage
async def endpoint():
    # This won't block the event loop
    result = await call_sync_safely(cpu_intensive_computation, data)
    return result
```

### 6.3 Creating Tasks Without Tracking

```python
# ❌ ANTI-PATTERN: Fire and forget without tracking
async def bad_publish(event):
    asyncio.create_task(send_to_redis(event))  # Task might be garbage collected!

# ✅ PATTERN: Track background tasks
class Publisher:
    def __init__(self):
        self._tasks: set[asyncio.Task] = set()

    async def publish(self, event):
        task = asyncio.create_task(self._send(event))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def shutdown(self):
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
```

### 6.4 Sequential Database Operations

```python
# ❌ ANTI-PATTERN: Sequential queries
async def get_dashboard_data_slow(user_id: int):
    user = await get_user(user_id)           # 50ms
    tasks = await get_user_tasks(user_id)     # 50ms
    stats = await get_user_stats(user_id)     # 50ms
    notifications = await get_notifications(user_id)  # 50ms
    # Total: 200ms

# ✅ PATTERN: Parallel queries
async def get_dashboard_data_fast(user_id: int):
    user, tasks, stats, notifications = await asyncio.gather(
        get_user(user_id),
        get_user_tasks(user_id),
        get_user_stats(user_id),
        get_notifications(user_id),
    )
    # Total: 50ms (parallel)
```

---

## 7. Migration Guide

### 7.1 Step 1: Convert HeartbeatManager (Priority: HIGH)

**File**: `omoi_os/worker.py`

1. Replace `threading.Thread` with `asyncio.Task`
2. Replace `time.sleep()` with `await asyncio.sleep()`
3. Add graceful shutdown with `asyncio.Event`

### 7.2 Step 2: Add Async Database Methods (Priority: CRITICAL)

**File**: `omoi_os/services/database.py`

1. Add async engine alongside sync engine
2. Create `get_async_session()` dependency
3. Gradually migrate hot-path endpoints

### 7.3 Step 3: Optimize Task Queue (Priority: CRITICAL)

**File**: `omoi_os/services/task_queue.py`

1. Replace N+1 queries with batch operations
2. Use JOINs/subqueries for dependency checking
3. Implement bulk updates for score changes

### 7.4 Step 4: Parallelize Ticket Creation (Priority: HIGH)

**File**: `omoi_os/api/routes/tickets.py`

1. Run dedup check and validation in parallel
2. Defer embedding generation to background task
3. Use `asyncio.gather()` for independent operations

### 7.5 Step 5: Refactor Event Bus (Priority: MEDIUM)

**File**: `omoi_os/services/event_bus.py`

1. Replace blocking `listen()` with async iteration
2. Support async callbacks
3. Add connection management

---

## Quick Reference

### Checklist for New Async Code

- [ ] Use `async def` for I/O operations
- [ ] Use `await asyncio.gather()` for parallel operations
- [ ] Use `asyncio.Semaphore` for rate limiting
- [ ] Track all `create_task()` calls for cleanup
- [ ] Use `return_exceptions=True` when partial failure is acceptable
- [ ] Never use `time.sleep()` in async code
- [ ] Use executor for unavoidable sync code
- [ ] Implement graceful shutdown with `asyncio.Event`

### Performance Testing Commands

```bash
# Profile async code
python -m cProfile -o profile.out your_script.py
python -m snakeviz profile.out

# Test concurrent requests
hey -n 1000 -c 100 http://localhost:8000/api/tasks

# Monitor event loop blocking
PYTHONASYNCIODEBUG=1 python your_script.py
```

---

## See Also

- [FastAPI Async Docs](https://fastapi.tiangolo.com/async/)
- [SQLAlchemy Async Guide](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)
- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
