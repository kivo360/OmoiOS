# Comments Collaboration

**Part of**: [Page Flow Documentation](./README.md)

---
### Flow 16: Comments & Collaboration

```
┌─────────────────────────────────────────────────────────────┐
│    PAGE: /board/:projectId/:ticketId (Comments Tab)        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Ticket: Add OAuth2 Authentication                    │   │
│  │  [Details] [Tasks] [Commits] [Graph] [Comments] [Audit]│   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Comments Tab (Active)                               │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ worker-1 (2 hours ago)                      │  │   │
│  │  │ Starting implementation. Setting up JWT      │  │   │
│  │  │ library and token generation logic.         │  │   │
│  │  │ [Reply] [Edit]                              │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ worker-1 (1 hour ago)                       │  │   │
│  │  │ Token generation working. Moving on to       │  │   │
│  │  │ validation middleware.                      │  │   │
│  │  │ [Reply]                                      │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ worker-1 (30 min ago)                        │  │   │
│  │  │ Blocked: Need database schema for user      │  │   │
│  │  │ table before implementing login.            │  │   │
│  │  │ Creating task for database team.             │  │   │
│  │  │ [Reply]                                      │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ worker-2 (15 min ago)                        │  │   │
│  │  │ Database schema complete. User table        │  │   │
│  │  │ available. Unblocking auth work.             │  │   │
│  │  │ [Reply]                                      │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ worker-1 (5 min ago)                         │  │   │
│  │  │ Login endpoint implemented and tested.      │  │   │
│  │  │ All functionality complete.                  │  │   │
│  │  │ [Reply]                                      │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Add Comment                                  │  │   │
│  │  │                                              │  │   │
│  │  │ [Rich Text Editor]                           │  │   │
│  │  │ Type @ to mention agents/users...            │  │   │
│  │  │                                              │  │   │
│  │  │ 📎 [Attach File]                             │  │   │
│  │  │                                              │  │   │
│  │  │ Comment Type: [General ▼]                   │  │   │
│  │  │                                              │  │   │
│  │  │ [Cancel] [Post Comment]                     │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  💬 Real-time: New comments appear instantly via   │   │
│  │     WebSocket (COMMENT_ADDED event)                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## API Integration

### Backend Endpoints

Collaboration endpoints are prefixed with `/api/v1/`.

---

### POST /api/v1/collaboration/threads
**Description:** Create a new collaboration thread

**Request Body:**
```json
{
  "thread_type": "handoff",
  "participants": ["worker-1", "worker-2"],
  "ticket_id": "ticket-uuid",
  "task_id": "task-uuid",
  "thread_metadata": { "priority": "high" }
}
```

**Response (201):**
```json
{
  "thread_id": "thread-uuid",
  "thread_type": "handoff",
  "ticket_id": "ticket-uuid",
  "task_id": "task-uuid",
  "participants": ["worker-1", "worker-2"],
  "status": "open",
  "thread_metadata": { "priority": "high" },
  "created_at": "2025-01-15T10:00:00Z",
  "closed_at": null
}
```

---

### GET /api/v1/collaboration/threads
**Description:** List collaboration threads with filters

**Query Params:**
- `agent_id` (optional): Filter by agent
- `ticket_id` (optional): Filter by ticket
- `status` (optional): Filter by status (`open`, `closed`)

---

### POST /api/v1/collaboration/threads/{thread_id}/close
**Description:** Close a collaboration thread

---

### POST /api/v1/collaboration/messages
**Description:** Send a message in a collaboration thread

**Request Body:**
```json
{
  "thread_id": "thread-uuid",
  "from_agent_id": "worker-1",
  "message_type": "info",
  "content": "Login endpoint implemented and tested.",
  "to_agent_id": null,
  "message_metadata": null
}
```

**Response (201):**
```json
{
  "message_id": "msg-uuid",
  "thread_id": "thread-uuid",
  "from_agent_id": "worker-1",
  "to_agent_id": null,
  "message_type": "info",
  "content": "Login endpoint implemented and tested.",
  "message_metadata": null,
  "read_at": null,
  "created_at": "2025-01-15T10:00:00Z"
}
```

---

### GET /api/v1/collaboration/threads/{thread_id}/messages
**Description:** Get messages in a thread

**Query Params:**
- `limit` (default: 50)
- `unread_only` (default: false)

---

### POST /api/v1/collaboration/messages/{message_id}/read
**Description:** Mark a message as read

---

### POST /api/v1/collaboration/handoff/request
**Description:** Request a task handoff to another agent

**Request Body:**
```json
{
  "from_agent_id": "worker-1",
  "to_agent_id": "worker-2",
  "task_id": "task-uuid",
  "reason": "Need frontend expertise",
  "context": { "current_progress": "50%" }
}
```

**Response (200):**
```json
{
  "thread_id": "thread-uuid",
  "message_id": "msg-uuid"
}
```

---

### POST /api/v1/collaboration/handoff/{thread_id}/accept
**Description:** Accept a handoff request

**Query Params:**
- `accepting_agent_id`: Agent accepting the handoff
- `message` (default: "Handoff accepted")

---

### POST /api/v1/collaboration/handoff/{thread_id}/decline
**Description:** Decline a handoff request

**Query Params:**
- `declining_agent_id`: Agent declining
- `reason`: Reason for declining

---

**Next**: See [README.md](./README.md) for complete documentation index.
