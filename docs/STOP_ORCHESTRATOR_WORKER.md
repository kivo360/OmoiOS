# How to Stop the Orchestrator Worker on Railway

**Emergency Stop Guide** - Prevents duplicate task creation and credit consumption

## Quick Options (Choose One)

### Option 1: Railway Dashboard (Fastest - Recommended)

1. Go to [Railway Dashboard](https://railway.app)
2. Navigate to your project
3. Find the **orchestrator** service (or service running `orchestrator_worker`)
4. Click the **three dots menu** (⋯) on the service
5. Select **"Pause"** or **"Stop"**
   - **Pause**: Temporarily stops the service (can resume later)
   - **Stop**: Stops the service (will restart if configured to auto-restart)

### Option 2: Railway CLI

```bash
# Install Railway CLI if needed
npm i -g @railway/cli

# Login
railway login

# List services to find orchestrator service ID
railway status

# Stop the orchestrator service
railway service stop <service-id>

# Or pause it
railway service pause <service-id>
```

### Option 3: Environment Variable (If Code Supports It)

Add an environment variable to disable the orchestrator:

```bash
# In Railway dashboard, add to orchestrator service:
ORCHESTRATOR_ENABLED=false
```

**Note**: This requires code changes to check this variable. If not implemented, use Option 1 or 2.

### Option 4: Delete Service (Permanent)

⚠️ **Warning**: This permanently removes the service. You'll need to redeploy later.

1. Railway Dashboard → Your Project
2. Find orchestrator service
3. Settings → Delete Service

## Verify It's Stopped

1. Check Railway dashboard - service should show "Stopped" or "Paused"
2. Check logs - no new task assignments should appear
3. Check database - no new tasks should be created

## Re-enable Later

### Resume from Pause:
- Railway Dashboard → Service → Resume

### Restart Stopped Service:
- Railway Dashboard → Service → Deploy (or restart)

### Redeploy:
- If deleted, redeploy using `railway-orchestrator.json` configuration

## Prevent Future Issues

### Add Circuit Breaker Pattern

Consider adding a circuit breaker to the orchestrator to prevent infinite loops:

```python
# In orchestrator_worker.py, add:
MAX_TASKS_PER_HOUR = 100  # Configurable limit
task_count = 0
last_reset = time.time()

# In orchestrator_loop():
if time.time() - last_reset > 3600:
    task_count = 0
    last_reset = time.time()

if task_count >= MAX_TASKS_PER_HOUR:
    logger.warning("Task rate limit exceeded, pausing for 1 hour")
    await asyncio.sleep(3600)
    continue
```

### Add Task Deduplication

Check for duplicate tasks before creating new ones:

```python
# Before creating task, check if similar task exists:
existing_task = session.query(Task).filter(
    Task.description == task_description,
    Task.status.in_(["pending", "assigned", "running"]),
    Task.created_at > datetime.now() - timedelta(hours=1)
).first()

if existing_task:
    logger.info(f"Duplicate task detected, skipping: {existing_task.id}")
    continue
```

## Emergency Database Cleanup

If tasks were already created, you may want to clean them up:

```sql
-- Find duplicate tasks
SELECT description, COUNT(*) as count
FROM tasks
WHERE status IN ('pending', 'assigned')
    AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY description
HAVING COUNT(*) > 1;

-- Delete duplicate pending tasks (keep oldest)
DELETE FROM tasks
WHERE id IN (
    SELECT id FROM (
        SELECT id, ROW_NUMBER() OVER (
            PARTITION BY description 
            ORDER BY created_at ASC
        ) as rn
        FROM tasks
        WHERE status = 'pending'
            AND created_at > NOW() - INTERVAL '1 hour'
    ) t WHERE rn > 1
);
```

## Recommended: Add Monitoring Alert

Set up Railway alerts to notify you when:
- Service restarts repeatedly
- High task creation rate
- High resource usage

This will help catch issues before they consume all credits.
