# OmoiOS API Test Report
**Date:** December 11, 2025  
**API Version:** 0.1.0  
**Total Endpoints:** 174 (+1 new)  

## Executive Summary

The API is largely functional with most core endpoints working correctly. Several bugs were identified and **FIXED** primarily in the memory, quality, diagnostic, and cost modules.

### ✅ BUGS FIXED IN THIS SESSION
1. `GET /api/v1/diagnostic/stuck-workflows` - Fixed MemoryService initialization
2. `GET /api/v1/memory/patterns` - Fixed database session handling  
3. `GET /api/v1/quality/trends` - Fixed database session handling
4. `POST /api/v1/tickets/{id}/transition` - Added proper error handling for InvalidTransitionError
5. `POST /api/v1/agents/register` - Fixed error handling to show actual rejection reason
6. `POST /api/v1/costs/budgets` - Fixed Budget model ID type mismatch (UUID → Integer)
7. `GET /api/v1/costs/budgets` - Fixed DetachedInstanceError by expunging objects

### ✅ NEW FEATURES ADDED
1. **Ticket Deduplication** - pgvector-based semantic duplicate detection
   - `POST /api/v1/tickets` now checks for duplicates before creation
   - New `POST /api/v1/tickets/check-duplicates` endpoint
2. **Ticket Filtering** - Added filter/search params to `GET /api/v1/tickets`
   - `status`, `priority`, `phase_id` filters
   - `search` param for text search in title/description
3. **Embedding Provider Fix** - Memory & Quality services now use configured provider
   - Fixed hardcoded `EmbeddingProvider.LOCAL` → uses Fireworks by default
   - Removed unnecessary FastEmbed model loading

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
| `POST /api/v1/agents/register` | ✅ 200 | Requires `agent_type` + `capabilities` array |

**Agent Register Required Fields:**
- `agent_type: string` - Type of agent (e.g., "worker", "coordinator")
- `capabilities: array` - List of capabilities (e.g., `["code_review", "testing"]`)

#### Tickets (16 endpoints)
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/tickets` | ✅ 200 | Returns paginated ticket list |
| `POST /api/v1/tickets` | ✅ 200 | Creates tickets with deduplication check |
| `POST /api/v1/tickets/check-duplicates` | ✅ 200 | **NEW** Check for similar tickets without creating |
| `GET /api/v1/tickets/{id}` | ✅ 200 | Returns ticket details |
| `GET /api/v1/tickets/{id}/context` | ✅ 200 | Returns ticket context |
| `GET /api/v1/tickets/{id}/gate-status` | ✅ 200 | Returns gate validation status |

**Ticket Deduplication Parameters:**
- `check_duplicates: bool = true` - Enable/disable duplicate detection
- `similarity_threshold: float = 0.85` - Cosine similarity threshold (0-1)
- `force_create: bool = false` - Force creation even if duplicates found

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

#### Costs (7 endpoints)
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/costs/budgets` | ✅ 200 | Returns budget list (fixed DetachedInstanceError) |
| `POST /api/v1/costs/budgets` | ✅ 200 | Creates new budget (fixed ID type mismatch) |
| `GET /api/v1/costs/summary` | ✅ 200 | Requires `scope_type` + `scope_id` for non-global |
| `GET /api/v1/costs/usage` | ✅ 200 | Returns usage breakdown |

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

### ⚠️ COMMON 422 ERRORS AND SOLUTIONS

| Endpoint | Error | Solution |
|----------|-------|----------|
| `GET /api/v1/tickets/search` | 422 | **Endpoint doesn't exist!** Use `GET /api/v1/tickets?search=term` instead |
| `GET /api/v1/costs/summary` | 422 | Missing `scope_type` param. Use `?scope_type=global` or `?scope_type=ticket&scope_id=xxx` |
| `POST /api/v1/memory/search` | 422 | Missing `task_description`. Use `{"task_description": "your query"}` not `{"query": "..."}` |
| `POST /api/v1/auth/login` | 422 | Use `email` and `password` fields, not `username` |
| `POST /api/v1/tickets/{id}/transition` | 422 | Missing `to_status` body field. Use `{"to_status": "analyzing"}` |

### ℹ️ DOCUMENTATION NOTES

| Endpoint | Notes |
|----------|-------|
| `GET /api/v1/costs/summary` | Valid `scope_type`: `global`, `ticket`, `agent`, `phase`, `task` |
| `GET /api/v1/tickets` | **NEW** Supports `status`, `priority`, `phase_id`, `search` filters |

**Ticket List Filtering Examples:**
```bash
# Filter by status
GET /api/v1/tickets?status=backlog

# Search in title/description
GET /api/v1/tickets?search=SSO

# Filter by priority
GET /api/v1/tickets?priority=high

# Combine filters
GET /api/v1/tickets?status=backlog&priority=high&limit=10
```

---

### 📋 Required Fields Reference

**Key endpoints with required fields (no defaults):**

| Endpoint | Required Fields |
|----------|-----------------|
| `POST /api/v1/agents/register` | `agent_type`, `capabilities` (array) |
| `POST /api/v1/tickets` | `title` |
| `POST /api/v1/tickets/check-duplicates` | `title` |
| `POST /api/v1/projects` | `name` |
| `POST /api/v1/costs/budgets` | `scope_type`, `limit_amount` |
| `POST /api/v1/memory/search` | `task_description` |
| `POST /api/v1/memory/store` | `task_id`, `execution_summary`, `success` |
| `POST /api/v1/tasks/{id}/dependencies` | `depends_on` (array) |

**Agent Registration Example:**
```bash
http POST /api/v1/agents/register \
  agent_type="worker" \
  capabilities:='["code_review", "testing"]'
```

**Note:** Agent registration requires heartbeat within 60s to complete.

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

### ✅ FIXED: Budget Model ID Type Mismatch
**Affected Endpoint:** `POST /api/v1/costs/budgets`  
**Previous Error:** `DatatypeMismatch: column "id" is of type integer but expression is of type character varying`  
**Root Cause:** `Budget` model used `String` (UUID) for `id`, but migration used `Integer`  
**Fix:** Changed `Budget.id` from `Mapped[str]` to `Mapped[int]` with autoincrement

---

### ✅ FIXED: Budget List DetachedInstanceError
**Affected Endpoint:** `GET /api/v1/costs/budgets`  
**Previous Error:** `DetachedInstanceError` when accessing budget attributes  
**Root Cause:** Budget objects were detached from session before attributes accessed  
**Fix:** Added `sess.expunge(budget)` in `list_budgets` to properly detach with loaded state

---

### ✅ NEW: Ticket Deduplication with pgvector
**Endpoints:** `POST /api/v1/tickets`, `POST /api/v1/tickets/check-duplicates`  
**Feature:** Semantic duplicate detection using Fireworks embeddings (1536 dimensions)  
**Behavior:**
- New tickets are checked against existing tickets using cosine similarity
- Duplicates (≥85% similarity by default) are blocked with candidate list
- Use `force_create=true` to bypass detection
- Embeddings stored in `tickets.embedding_vector` column (pgvector)

**Sample Response (duplicate found):**
```json
{
    "is_duplicate": true,
    "message": "Found 2 similar ticket(s). Set force_create=true to create anyway.",
    "candidates": [
        {
            "ticket_id": "7fc5e35a-40b0-46ff-846f-de2e9b81c8ae",
            "title": "Login issue with SSO",
            "similarity_score": 0.9234
        }
    ],
    "highest_similarity": 0.9234
}
```

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

1. ~~**Fix DatabaseService** - Add `execute` method or update code to use correct method~~ ✅ DONE
2. ~~**Improve error handling** - Ensure all exceptions include meaningful messages~~ ✅ DONE
3. **Document valid values** - Add validation error messages that list valid options (partially done)
4. **Add API authentication tests** - Test auth flow end-to-end with valid tokens
5. **Consider adding OpenAPI examples** - Add example values in schema for better docs

