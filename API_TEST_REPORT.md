# OmoiOS API Test Report
**Date:** December 10, 2025  
**API Version:** 0.1.0  
**Total Endpoints:** 173  

## Executive Summary

The API is largely functional with most core endpoints working correctly. Several bugs were identified and **FIXED** primarily in the memory, quality, and diagnostic modules.

### ✅ BUGS FIXED IN THIS SESSION
1. `GET /api/v1/diagnostic/stuck-workflows` - Fixed MemoryService initialization
2. `GET /api/v1/memory/patterns` - Fixed database session handling  
3. `GET /api/v1/quality/trends` - Fixed database session handling
4. `POST /api/v1/tickets/{id}/transition` - Added proper error handling for InvalidTransitionError
5. `POST /api/v1/agents/register` - Fixed error handling to show actual rejection reason

---

## Test Results by Category

### ✅ WORKING ENDPOINTS

#### Health & Root
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /` | ✅ 200 | Returns HTML Task Runner UI |
| `GET /health` | ✅ 200 | `{"status":"healthy","version":"0.1.0"}` |

#### Agents (14 endpoints)
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/agents` | ✅ 200 | Returns list of registered agents |
| `GET /api/v1/agents/health` | ✅ 200 | Agent health status |
| `GET /api/v1/agents/statistics` | ✅ 200 | Agent statistics |
| `GET /api/v1/agents/stale` | ✅ 200 | Stale agents list |
| `POST /api/v1/agents/register` | ⚠️ 500 | Bug: "Failed to register agent: " (empty error) |

#### Tickets (15 endpoints)
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/tickets` | ✅ 200 | Returns paginated ticket list |
| `POST /api/v1/tickets` | ✅ 200 | Successfully creates tickets |
| `GET /api/v1/tickets/{id}` | ✅ 200 | Returns ticket details |
| `GET /api/v1/tickets/{id}/context` | ✅ 200 | Returns ticket context |
| `GET /api/v1/tickets/{id}/gate-status` | ✅ 200 | Returns gate validation status |

#### Tasks (14 endpoints)
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/tasks` | ✅ 200 | Returns task list with details |

#### Projects (6 endpoints)
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/projects` | ✅ 200 | Returns project list |

#### Board (6 endpoints)
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/board/view` | ✅ 200 | Returns Kanban board with columns |
| `GET /api/v1/board/stats` | ✅ 200 | Returns column statistics |

#### Specs (15 endpoints)
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/specs/project/{id}` | ✅ 200 | Returns specs with requirements, design, tasks |

#### Explore (7 endpoints)
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/explore/project/{id}/conversations` | ✅ 200 | Returns conversation list |

#### Graph (4 endpoints)
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/graph/dependency-graph/project/{id}` | ✅ 200 | Returns nodes and edges |

#### Reasoning (5 endpoints)
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/reasoning/types` | ✅ 200 | Returns event, evidence, decision types |
| `GET /api/v1/reasoning/{type}/{id}` | ✅ 200 | Returns reasoning events for entity |

#### Monitoring (8 endpoints)
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/monitor/dashboard` | ✅ 200 | Returns dashboard summary |

#### Guardian (6 endpoints)
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/guardian/actions` | ✅ 200 | Returns empty array (no actions) |

#### Collaboration (9 endpoints)
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/collaboration/threads` | ✅ 200 | Returns empty array (no threads) |

#### Alerts (5 endpoints)
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/alerts` | ✅ 200 | Returns empty array (no alerts) |

#### Auth (13 endpoints)
| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /api/v1/auth/register` | ✅ 200 | User registration works |
| `POST /api/v1/auth/login` | ⚠️ 401 | Needs valid credentials |
| `GET /api/v1/organizations` | ⚠️ 401 | Requires authentication |

---

### ✅ FIXED ENDPOINTS

| Endpoint | Previous | Now | Fix Applied |
|----------|----------|-----|-------------|
| `GET /api/v1/diagnostic/stuck-workflows` | ❌ 500 | ✅ 200 | Fixed MemoryService init params |
| `GET /api/v1/memory/patterns` | ❌ 500 | ✅ 200 | Added `get_sync_db_session` dependency |
| `GET /api/v1/quality/trends` | ❌ 500 | ✅ 200 | Added `get_sync_db_session` dependency |

### ✅ ALSO FIXED: Agent Registration Error Handling
| Endpoint | Previous | Now | Notes |
|----------|----------|-----|-------|
| `POST /api/v1/agents/register` | ❌ 500 empty | ✅ 400 | Returns proper rejection reason |

**Note:** Agents require heartbeat within 60s to complete registration. This is expected behavior.

### ℹ️ DOCUMENTATION NEEDED

| Endpoint | Issue |
|----------|-------|
| `GET /api/v1/costs/summary` | Valid `scope_type` values: `task`, `ticket`, `project` (not `organization`) |

---

## Bugs Summary

### ✅ FIXED: DatabaseService Session Handling
**Affected Endpoints:** `memory/patterns`, `quality/trends`  
**Root Cause:** Routes used `db: Session = Depends(get_db_service)` which returns `DatabaseService`, not `Session`  
**Fix:** Created `get_sync_db_session` dependency that properly yields a session

---

### ✅ FIXED: MemoryService Initialization  
**Affected Endpoint:** `diagnostic/stuck-workflows`  
**Root Cause:** `MemoryService(db=db, embedding=embedding, ...)` - wrong parameter names  
**Fix:** Changed to `MemoryService(embedding_service=embedding, event_bus=event_bus)`

---

### ✅ FIXED: Ticket Transition Error Handling
**Affected Endpoint:** `POST /api/v1/tickets/{id}/transition`  
**Root Cause:** `InvalidTransitionError` thrown as 500 instead of 400  
**Fix:** Added try/except to convert to HTTPException(400)

---

### ✅ FIXED: Agent Registration Error Handling
**Affected Endpoint:** `POST /api/v1/agents/register`  
**Previous Error:** `{"detail":"Failed to register agent: "}` (empty)  
**Fix:** Added proper exception handling for `RegistrationRejectedError`  
**New Response:** `{"detail":"Registration rejected: Initial heartbeat not received within 60 seconds"}`

**Note:** This is expected behavior - agents must send a heartbeat within 60s to prove they're alive.

---

### ℹ️ Documentation: Cost Summary Scope Types
**Endpoint:** `GET /api/v1/costs/summary`  
**Valid scope_type values:** `task`, `ticket`, `project`  
**Example:** `GET /api/v1/costs/summary?scope_type=task&scope_id=task-123`

---

## Sample API Responses

### Ticket Created
```json
{
    "id": "e63cbfa9-6ffc-4942-8317-9d50d06400a0",
    "title": "API Test Ticket",
    "description": "Created by API testing",
    "phase_id": "PHASE_REQUIREMENTS",
    "status": "backlog",
    "priority": "LOW",
    "approval_status": "approved"
}
```

### Dashboard Summary
```json
{
    "total_tasks_pending": 5,
    "total_tasks_completed": 0,
    "active_agents": 0,
    "stale_agents": 0,
    "active_locks": 0,
    "recent_anomalies": 0,
    "critical_alerts": 0
}
```

### Gate Status
```json
{
    "requirements_met": false,
    "missing_artifacts": ["requirements_document"],
    "validation_status": "blocked"
}
```

---

## Recommendations

1. **Fix DatabaseService** - Add `execute` method or update code to use correct method
2. **Improve error handling** - Ensure all exceptions include meaningful messages
3. **Document valid values** - Add validation error messages that list valid options
4. **Add API authentication tests** - Test auth flow end-to-end with valid tokens

