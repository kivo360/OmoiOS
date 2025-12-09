# Agent Memory & Learning

**Part of**: [Page Flow Documentation](./README.md)

---

## Overview

Agent Memory provides semantic storage and retrieval of task execution patterns, enabling agents to learn from past experiences. The ACE (Aggregation, Consolidation, Extraction) workflow transforms completed tasks into reusable knowledge patterns.

---

## Flow 47: Memory Search

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /memory (or embedded in Agent/Task views)             │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tabs: [Search] [Patterns] [Playbook] [Insights]     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Semantic Memory Search                               │   │
│  │                                                       │   │
│  │  Search by similarity:                               │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ Implement OAuth2 authentication with JWT       │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │  [Search]                                            │   │
│  │                                                       │   │
│  │  Results (3 similar tasks):                          │   │
│  │                                                       │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ 🎯 95% match                                   │  │   │
│  │  │ "Add JWT token validation to API endpoints"   │  │   │
│  │  │ Completed by worker-3 • 2 days ago            │  │   │
│  │  │                                                │  │   │
│  │  │ Key learnings:                                │  │   │
│  │  │ • Used jose library for JWT validation        │  │   │
│  │  │ • Added middleware pattern for auth           │  │   │
│  │  │ • 2 retries needed due to token expiry edge  │  │   │
│  │  │                                                │  │   │
│  │  │ [View Details] [Apply to Current Task]        │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                                                       │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ 🎯 87% match                                   │  │   │
│  │  │ "Implement OAuth2 flow for GitHub login"      │  │   │
│  │  │ Completed by worker-1 • 5 days ago            │  │   │
│  │  │                                                │  │   │
│  │  │ [View Details] [Apply to Current Task]        │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Search Features:**
- Semantic similarity search using embeddings
- Filter by task type, outcome, agent
- View execution context and learnings
- Apply patterns to new tasks

---

## Flow 48: Learned Patterns

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /memory?tab=patterns                                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Learned Patterns                                     │   │
│  │                                                       │   │
│  │  Filters:                                            │   │
│  │  [Task Type ▼] [Pattern Type ▼] [Confidence ▼]      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ Pattern: Authentication Implementation         │  │   │
│  │  │ Type: implementation • Confidence: 92%        │  │   │
│  │  │ Used: 14 times • Last used: 1 day ago         │  │   │
│  │  │                                                │  │   │
│  │  │ Template:                                     │  │   │
│  │  │ 1. Create auth middleware                     │  │   │
│  │  │ 2. Implement token validation                 │  │   │
│  │  │ 3. Add protected route wrapper               │  │   │
│  │  │ 4. Write integration tests                   │  │   │
│  │  │                                                │  │   │
│  │  │ Success indicators:                          │  │   │
│  │  │ • Tests pass within 2 iterations             │  │   │
│  │  │ • No security vulnerabilities                │  │   │
│  │  │                                                │  │   │
│  │  │ [👍 Helpful] [👎 Not Helpful] [Edit]          │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                                                       │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ Pattern: API Error Handling                    │  │   │
│  │  │ Type: error_handling • Confidence: 88%        │  │   │
│  │  │ Used: 23 times • Last used: 3 hours ago       │  │   │
│  │  │                                                │  │   │
│  │  │ [👍 Helpful] [👎 Not Helpful] [Edit]          │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Pattern Details:**
- Pattern name and type
- Confidence score (based on success rate)
- Usage count and recency
- Template steps
- Success indicators
- Feedback buttons for refinement

---

## Flow 49: Task Context View

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /tasks/:taskId (Memory Context Panel)                 │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Suggested Context from Memory                        │   │
│  │                                                       │   │
│  │  Based on task: "Implement user profile API"         │   │
│  │                                                       │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ 📚 Similar Past Tasks (3 found)                │  │   │
│  │  │                                                │  │   │
│  │  │ 1. "Create user settings endpoint" (91%)      │  │   │
│  │  │    → Used FastAPI with Pydantic models        │  │   │
│  │  │    → Avg completion: 45 minutes               │  │   │
│  │  │                                                │  │   │
│  │  │ 2. "Add profile photo upload" (84%)           │  │   │
│  │  │    → Used presigned S3 URLs                   │  │   │
│  │  │    → Watch out for: file size limits          │  │   │
│  │  │                                                │  │   │
│  │  │ 3. "Implement account deletion" (78%)         │  │   │
│  │  │    → Soft delete pattern worked well          │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                                                       │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ 🎯 Recommended Patterns                        │  │   │
│  │  │                                                │  │   │
│  │  │ • API Endpoint Pattern (92% confidence)       │  │   │
│  │  │ • Input Validation Pattern (88% confidence)   │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                                                       │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ ⚠️ Known Pitfalls                              │  │   │
│  │  │                                                │  │   │
│  │  │ • Profile APIs often need rate limiting       │  │   │
│  │  │ • Consider caching for frequently accessed   │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                                                       │   │
│  │  [Apply Context to Agent] [Dismiss]                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow 50: Pattern Extraction

```
┌─────────────────────────────────────────────────────────────┐
│  MODAL: Extract Pattern                                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Create Pattern from Completed Tasks                  │   │
│  │                                                       │   │
│  │  Task Type Pattern (regex):                          │   │
│  │  [.*authentication.*]                                │   │
│  │                                                       │   │
│  │  Minimum Samples Required:                           │   │
│  │  [3]                                                 │   │
│  │                                                       │   │
│  │  ℹ️ Found 5 matching completed tasks                  │   │
│  │                                                       │   │
│  │  Pattern Preview:                                    │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ Extracted from 5 successful tasks:             │  │   │
│  │  │                                                │  │   │
│  │  │ Common Steps:                                  │  │   │
│  │  │ 1. Set up auth middleware (5/5 tasks)         │  │   │
│  │  │ 2. Implement token validation (5/5 tasks)     │  │   │
│  │  │ 3. Add route protection (4/5 tasks)           │  │   │
│  │  │ 4. Write tests (5/5 tasks)                    │  │   │
│  │  │                                                │  │   │
│  │  │ Common Tools:                                  │  │   │
│  │  │ • jose library (4/5 tasks)                    │  │   │
│  │  │ • bcrypt for hashing (3/5 tasks)              │  │   │
│  │  │                                                │  │   │
│  │  │ Estimated Confidence: 85%                     │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                                                       │   │
│  │  [Cancel] [Extract Pattern]                          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow 51: ACE Workflow Completion

```
┌─────────────────────────────────────────────────────────────┐
│  NOTIFICATION: Task Completion Processed                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ACE Workflow Complete                                │   │
│  │                                                       │   │
│  │  Task: "Implement OAuth2 authentication"             │   │
│  │  Agent: worker-5                                     │   │
│  │                                                       │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ ✓ Executor Phase                               │  │   │
│  │  │   • Memory record created                      │  │   │
│  │  │   • Embedding generated                        │  │   │
│  │  │   • Classification: implementation             │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                                                       │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ ✓ Reflector Phase                              │  │   │
│  │  │   • 2 related playbook entries found           │  │   │
│  │  │   • Tags: [auth, jwt, security]                │  │   │
│  │  │   • Insight: "JWT refresh pattern effective"   │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                                                       │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ ✓ Curator Phase                                │  │   │
│  │  │   • Playbook update proposed                   │  │   │
│  │  │   • Delta: +2 bullets, ~1 modified             │  │   │
│  │  │   • Applied to "Authentication Patterns"       │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                                                       │   │
│  │  [View Memory Entry] [View Playbook Changes]         │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## API Integration

### Backend Endpoints

All memory endpoints are prefixed with `/api/v1/memory/`.

---

### POST /api/v1/memory/store
**Description:** Store task execution in memory with embedding

**Request Body:**
```json
{
  "task_id": "task-uuid",
  "task_description": "Implement OAuth2 authentication with JWT tokens",
  "agent_id": "agent-uuid",
  "outcome": "success",
  "execution_details": {
    "tools_used": ["file_write", "terminal"],
    "files_modified": ["src/auth/jwt.py", "src/middleware/auth.py"],
    "duration_seconds": 1847,
    "retry_count": 1
  },
  "learnings": "JWT refresh token pattern works well for long sessions"
}
```

**Response (201):**
```json
{
  "memory_id": "uuid",
  "status": "stored"
}
```

---

### POST /api/v1/memory/search
**Description:** Search for similar past tasks using embedding similarity

**Request Body:**
```json
{
  "query": "Implement user authentication with OAuth2",
  "top_k": 5,
  "min_similarity": 0.7,
  "filters": {
    "outcome": "success",
    "task_type": "implementation"
  }
}
```

**Response (200):**
```json
[
  {
    "task_id": "task-uuid",
    "description": "Add JWT token validation to API endpoints",
    "similarity_score": 0.95,
    "outcome": "success",
    "agent_id": "worker-3",
    "completed_at": "2025-01-13T15:30:00Z",
    "learnings": "Used jose library for JWT validation",
    "execution_details": {
      "tools_used": ["file_write", "terminal"],
      "duration_seconds": 2400
    }
  }
]
```

---

### GET /api/v1/memory/tasks/{task_id}/context
**Description:** Get suggested context for a task based on similar past executions

**Path Params:** `task_id` (string)

**Query Params:**
- `top_k` (default: 3, max: 10): Number of similar tasks to return

**Response (200):**
```json
{
  "task_id": "task-uuid",
  "task_description": "Implement user profile API",
  "similar_tasks": [
    {
      "task_id": "similar-task-uuid",
      "description": "Create user settings endpoint",
      "similarity_score": 0.91,
      "key_learnings": "Used FastAPI with Pydantic models",
      "avg_duration_seconds": 2700
    }
  ],
  "recommended_patterns": [
    {
      "pattern_id": "pattern-uuid",
      "name": "API Endpoint Pattern",
      "confidence": 0.92
    }
  ],
  "known_pitfalls": [
    "Profile APIs often need rate limiting",
    "Consider caching for frequently accessed data"
  ]
}
```

---

### GET /api/v1/memory/patterns
**Description:** List learned patterns ordered by confidence and usage

**Query Params:**
- `task_type` (optional): Filter by task type pattern
- `pattern_type` (optional): Filter by pattern type
- `limit` (default: 10, max: 50): Maximum results

**Response (200):**
```json
[
  {
    "pattern_id": "uuid",
    "name": "Authentication Implementation",
    "pattern_type": "implementation",
    "task_type_regex": ".*authentication.*",
    "confidence_score": 0.92,
    "usage_count": 14,
    "last_used_at": "2025-01-14T10:00:00Z",
    "template_steps": [
      "Create auth middleware",
      "Implement token validation",
      "Add protected route wrapper",
      "Write integration tests"
    ],
    "success_indicators": [
      "Tests pass within 2 iterations",
      "No security vulnerabilities"
    ],
    "created_at": "2025-01-01T00:00:00Z"
  }
]
```

---

### POST /api/v1/memory/patterns/extract
**Description:** Extract a pattern from completed tasks matching a regex

**Request Body:**
```json
{
  "task_type_regex": ".*authentication.*",
  "min_samples": 3,
  "pattern_name": "Authentication Implementation"
}
```

**Response (201):**
```json
{
  "pattern_id": "uuid",
  "name": "Authentication Implementation",
  "samples_used": 5,
  "confidence_score": 0.85,
  "status": "extracted"
}
```

---

### POST /api/v1/memory/patterns/{pattern_id}/feedback
**Description:** Provide feedback on pattern usefulness

**Path Params:** `pattern_id` (string)

**Request Body:**
```json
{
  "helpful": true,
  "task_id": "task-uuid",
  "comments": "Pattern steps were accurate but needed minor adjustments"
}
```

**Response (200):**
```json
{
  "pattern_id": "uuid",
  "feedback_recorded": true,
  "new_confidence_score": 0.93
}
```

---

### POST /api/v1/memory/complete-task
**Description:** Execute ACE workflow on task completion (transforms task into knowledge)

**Request Body:**
```json
{
  "task_id": "task-uuid",
  "result": {
    "success": true,
    "output": "Implementation complete with tests passing"
  },
  "feedback": "Good implementation, consider adding rate limiting"
}
```

**Response (200):**
```json
{
  "memory_id": "uuid",
  "tags": ["auth", "jwt", "security"],
  "insights": ["JWT refresh pattern effective for long sessions"],
  "errors": [],
  "related_playbook_entries": [
    {
      "entry_id": "playbook-uuid",
      "title": "Authentication Patterns"
    }
  ],
  "playbook_delta": {
    "additions": 2,
    "modifications": 1,
    "deletions": 0
  },
  "updated_bullets": [
    "Use JWT with refresh tokens for session management",
    "Implement token rotation on sensitive operations"
  ]
}
```

---

## Related Documentation

- [Diagnostic Reasoning](./09a_diagnostic_reasoning.md) - Agent reasoning and memory
- [Monitoring System](./10a_monitoring_system.md) - Pattern learning in monitoring
- [Agent Workspaces](./03_agents_workspaces.md) - Agent execution context

---

**Next**: See [README.md](./README.md) for complete documentation index.

