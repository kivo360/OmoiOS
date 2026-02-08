# Fix: Sandbox Failures Due to Inactive Daytona Snapshot

**Date**: 2026-02-08
**Status**: Fixed
**Severity**: Critical (all sandbox task execution blocked for ~1 week)

## Problem Description

All Daytona sandbox tasks were failing with the error:
```
Task stuck in assigned status for 3.1 minutes. Sandbox may have crashed before starting.
```

This affected every sandbox-based task since approximately February 1st, 2026. The sandbox `omoios-8c02ffe6-26b9bb` (task_id `8c02ffe6-89d3-423d-858a-130cdaab3f5a`) was one instance of this systemic failure. At least 10+ consecutive sandbox tasks all failed identically.

### Symptoms
- Sandbox created successfully (no spawn error)
- Task assigned to agent
- `started_at` remained `None` (worker never started)
- `conversation_id` remained `None` (no agent session)
- Zero `sandbox_events` recorded for any affected sandbox
- After 3 minutes, `stale_task_cleanup_loop` marked task as `failed`
- No error propagation to user-visible logs

## Root Cause Explanation

**Two issues combined to produce this failure:**

### Primary Cause: Inactive Daytona Snapshot

The Daytona snapshot `ai-agent-dev-light` (configured in `backend/config/base.yaml`) became **inactive** on the Daytona platform. When the spawner attempted to create a sandbox from this snapshot, Daytona returned:

```
DaytonaError: Failed to create sandbox: Snapshot ai-agent-dev-light is inactive
```

Snapshots can become inactive due to expiration, platform maintenance, or account-level resource limits.

### Secondary Cause: Silent Error Swallowing (Code Bug)

The `_create_daytona_sandbox` method had a flawed error handling pattern:

```python
# BEFORE (broken):
except Exception as e:
    logger.error(f"Failed to create Daytona sandbox: {e}")
    await self._create_mock_sandbox(sandbox_id, env_vars)  # Does nothing!
    return  # Returns normally -- caller thinks sandbox was created
```

When the snapshot creation failed:
1. The exception was caught in `_create_daytona_sandbox`
2. It fell back to `_create_mock_sandbox` which only logs (starts no worker)
3. The method returned normally without raising
4. `spawn_for_task` treated this as success, set status to "running"
5. No actual worker existed, so no `agent.started` event was ever sent
6. After 3 minutes, the stale task cleanup loop detected the orphaned task

This silent fallback pattern was intended for local development (mock sandboxes) but was active in production, masking the real error.

## Files Modified

### `backend/omoi_os/services/daytona_spawner.py`

**Fix 1: Snapshot fallback to image-based creation**

When snapshot creation fails (inactive, expired, unavailable), the code now automatically retries with image-based sandbox creation instead of falling back to a non-functional mock:

```python
# Create sandbox from snapshot if provided
if self.sandbox_snapshot:
    try:
        params = CreateSandboxFromSnapshotParams(snapshot=self.sandbox_snapshot, ...)
        sandbox = daytona.create(params=params, timeout=120)
    except Exception as snapshot_error:
        logger.warning(
            f"Snapshot '{self.sandbox_snapshot}' creation failed: {snapshot_error}. "
            f"Falling back to image-based sandbox creation."
        )
        # sandbox remains None, will be created from image below

if sandbox is None:
    # Fall back to image-based creation
    params = CreateSandboxFromImageParams(image=self.sandbox_image, ...)
    sandbox = daytona.create(params=params, timeout=120)
```

**Fix 2: Production error propagation**

In production (`OMOIOS_ENV=production`), sandbox creation failures now raise exceptions instead of silently falling back to mock mode. This ensures the orchestrator catches the error and marks the task as failed immediately with a clear error message, rather than leaving it orphaned for 3 minutes.

## Fix Implementation

The fix introduces two changes to `_create_daytona_sandbox`:

1. **Graceful snapshot fallback**: Wraps snapshot creation in its own try/except. If the snapshot fails (inactive, expired, etc.), it falls back to creating from the Docker image (`nikolaik/python-nodejs:python3.12-nodejs22`). This is a resilient approach since image-based creation is always available.

2. **Production safety**: In production mode, both `ImportError` (SDK missing) and general `Exception` (API errors after snapshot fallback also fails) now raise `RuntimeError` instead of silently creating a mock sandbox. The mock fallback is preserved only for local development.

## Tests Written/Modified

No new tests were required. The existing 10 unit tests in `tests/unit/services/test_daytona_spawner.py` all pass.

## Verification Results

### Reproduction of the original failure
```
$ python -c "daytona.create(CreateSandboxFromSnapshotParams(snapshot='ai-agent-dev-light', ...))"
DaytonaError: Failed to create sandbox: Snapshot ai-agent-dev-light is inactive
```

### Verification of the fix
```
Creating sandbox from snapshot: ai-agent-dev-light ...
WARNING: Snapshot 'ai-agent-dev-light' creation failed: Failed to create sandbox: Snapshot ai-agent-dev-light is inactive. Falling back to image-based sandbox creation.
Creating sandbox from image: nikolaik/python-nodejs:python3.12-nodejs22 ...
Daytona sandbox b5795541-a19a-4146-9311-9c4b3bb00dbf created for test-debug-fix
Worker started successfully in sandbox b5795541-a19a-4146-9311-9c4b3bb00dbf
SUCCESS: Sandbox created: b5795541-a19a-4146-9311-9c4b3bb00dbf
```

### Database evidence (all recent sandbox tasks failed identically)
```
2026-02-08 17:14:28 | 8c02ffe6... | failed | omoios-8c02ffe6-26b9bb | Task stuck in assigned status for 3.1 minutes
2026-02-07 20:30:17 | 4dd46fed... | failed | omoios-4dd46fed-053b87 | Task stuck in assigned status for 3.1 minutes
2026-02-07 20:29:59 | d355070c... | failed | omoios-d355070c-9b61ce | Task stuck in assigned status for 3.1 minutes
... (10+ consecutive failures with identical pattern)
```

Last successful sandbox events were from February 1st, confirming the snapshot became inactive around that date.

### Test suite results
```
10 passed in 0.05s (tests/unit/services/test_daytona_spawner.py)
```

## Deployment Notes

After deploying this fix:
1. Existing tasks that failed due to this issue will NOT automatically retry (they are in `failed` status with `retry_count=0`, `max_retries=3`)
2. New sandbox tasks will automatically fall back to image-based creation
3. Consider reactivating the `ai-agent-dev-light` snapshot in Daytona if it provides faster startup times
4. The `OMOIOS_ENV` environment variable should be set to `production` in Railway to enable production error propagation
