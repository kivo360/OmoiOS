# Debug & Admin Endpoints Audit

> **Purpose**: Catalog all debug, test, and admin endpoints that should be reviewed/disabled before production launch.

**Last Updated**: 2025-01-03

---

## Summary

| Category             | Count | Action Required    |
| -------------------- | ----- | ------------------ |
| Debug/Test Endpoints | 10    | Disable or protect |
| Super Admin Only     | 3     | Already protected  |
| Sensitive Operations | 2     | Review access      |

---

## Debug/Test Endpoints (DISABLE BEFORE PRODUCTION)

These endpoints exist for development/testing and should be disabled or heavily restricted in production.

### 1. OAuth Debug

| Method | Endpoint                                  | Description                              | Risk                                 |
| ------ | ----------------------------------------- | ---------------------------------------- | ------------------------------------ |
| `POST` | `/api/v1/auth/oauth/{provider}/copy-from` | Copy OAuth credentials from another user | **HIGH** - Allows credential sharing |

**Recommendation**: Disable entirely in production, or restrict to super_admin only.

---

### 2. Billing Debug

| Method | Endpoint                             | Description               | Risk   |
| ------ | ------------------------------------ | ------------------------- | ------ |
| `POST` | `/api/v1/billing/debug/test-email`   | Send test billing email   | MEDIUM |
| `GET`  | `/api/v1/billing/debug/queue-status` | View billing queue status | LOW    |

**Recommendation**: Move behind super_admin check or disable.

---

### 3. GitHub Debug

| Method | Endpoint                    | Description             | Risk |
| ------ | --------------------------- | ----------------------- | ---- |
| `GET`  | `/api/v1/github/repos-test` | Test repository listing | LOW  |

**Recommendation**: Remove or disable.

---

### 4. Organization Debug

| Method | Endpoint                                          | Description                    | Risk   |
| ------ | ------------------------------------------------- | ------------------------------ | ------ |
| `GET`  | `/api/v1/organizations/{org_id}/debug/owner-info` | Get organization owner details | MEDIUM |

**Recommendation**: Remove or restrict to super_admin.

---

### 5. Agent Maintenance

| Method | Endpoint                       | Description          | Risk   |
| ------ | ------------------------------ | -------------------- | ------ |
| `GET`  | `/api/v1/agents/stale`         | List stale agents    | LOW    |
| `POST` | `/api/v1/agents/cleanup-stale` | Cleanup stale agents | MEDIUM |

**Recommendation**: These may be needed for ops. Restrict to super_admin.

---

### 6. Task Maintenance

| Method | Endpoint                          | Description                | Risk   |
| ------ | --------------------------------- | -------------------------- | ------ |
| `POST` | `/api/v1/tasks/cleanup-timed-out` | Cleanup timed out tasks    | MEDIUM |
| `POST` | `/api/v1/tasks/generate-titles`   | Batch generate task titles | LOW    |

**Recommendation**: Keep for ops but restrict to super_admin.

---

## Already Protected (Super Admin Only)

These endpoints are already protected with `is_super_admin` checks:

| Method | Endpoint                                  | Description                |
| ------ | ----------------------------------------- | -------------------------- |
| `GET`  | `/api/v1/auth/waitlist`                   | List waitlist users        |
| `POST` | `/api/v1/auth/waitlist/{user_id}/approve` | Approve waitlist user      |
| `POST` | `/api/v1/auth/waitlist/approve-all`       | Approve all waitlist users |

**Status**: ✅ Already protected

---

## Legitimate Sensitive Endpoints (Keep but Monitor)

These are legitimate endpoints but should be monitored for abuse:

| Method | Endpoint                       | Description            | Notes                  |
| ------ | ------------------------------ | ---------------------- | ---------------------- |
| `POST` | `/api/v1/auth/reset-password`  | Password reset         | Rate limit recommended |
| `POST` | `/api/v1/auth/forgot-password` | Request password reset | Rate limit recommended |
| `POST` | `/api/v1/auth/register`        | User registration      | Rate limit recommended |

---

## Implementation Options

### Option 1: Environment-based Disable

```python
from omoi_os.config import get_app_settings

def require_debug_mode():
    """Dependency that blocks in production."""
    settings = get_app_settings()
    if settings.env == "production":
        raise HTTPException(status_code=404, detail="Not Found")
```

### Option 2: Super Admin Only

```python
from omoi_os.api.dependencies import get_current_user

async def require_super_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Super admin required")
    return current_user
```

### Option 3: Remove Routes Entirely

For truly dangerous debug endpoints, remove them from the router registration in production builds.

---

## Pre-Launch Checklist

- [ ] Review each debug endpoint and decide: disable, protect, or keep
- [ ] Add `require_super_admin` to maintenance endpoints
- [ ] Add rate limiting to auth endpoints
- [ ] Remove or disable `/oauth/{provider}/copy-from` in production
- [ ] Remove `/billing/debug/*` endpoints
- [ ] Remove `/github/repos-test` endpoint
- [ ] Remove `/organizations/{org_id}/debug/*` endpoints
- [ ] Audit logs for all admin actions
- [ ] Test that disabled endpoints return 404 (not 403)

---

## File Locations

| File                                  | Debug Endpoints                          |
| ------------------------------------- | ---------------------------------------- |
| `omoi_os/api/routes/oauth.py`         | `copy-from`                              |
| `omoi_os/api/routes/billing.py`       | `debug/test-email`, `debug/queue-status` |
| `omoi_os/api/routes/github_repos.py`  | `repos-test`                             |
| `omoi_os/api/routes/organizations.py` | `debug/owner-info`                       |
| `omoi_os/api/routes/agents.py`        | `stale`, `cleanup-stale`                 |
| `omoi_os/api/routes/tasks.py`         | `cleanup-timed-out`, `generate-titles`   |
| `omoi_os/api/routes/auth.py`          | Waitlist management (already protected)  |
