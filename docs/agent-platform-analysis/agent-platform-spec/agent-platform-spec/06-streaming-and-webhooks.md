# 06 · Streaming & Webhooks

Three ways to find out what's happening. Pick based on what's on the other side.

| Channel | When | How |
|---|---|---|
| **SSE** | Browser or simple client wants a live feed. | `GET /events`, `text/event-stream`, resume via `Last-Event-Id`. |
| **WebSocket** | Multiplayer, bidirectional, IDE integrations. | `wss://…` with per-connection user JWT. Presence + replies. |
| **Webhooks** | Server-to-server async notification. | HMAC-SHA256 signed. Retries with exponential backoff up to 24h. |

## Webhook payload

```http
POST https://acme.com/hooks/agent
Content-Type: application/json
X-Signature: t=1713700142,v1=7a9f3b1c…
X-Event-Id:  evt_01HW…
X-Event-Type: session.succeeded

{
  "id": "evt_01HW…",
  "type": "session.succeeded",
  "organization_id": "org_2fJxKk9",
  "created_at": "2026-04-21T14:11:02Z",
  "data": {
    "session_id": "sess_9Qw2",
    "usage": { "compute_seconds": 321, "tokens_input": 94210, "tokens_output": 12043 },
    "artifacts": [{ "id": "art_7Yp3", "kind": "pull_request", "external_url": "…" }]
  }
}
```

Signature verification: HMAC-SHA256 of `t.body` using the tenant-chosen secret. `X-Event-Id` is the idempotency key.

## Event types

| Type | When |
|---|---|
| `session.created` | after `POST /sessions` succeeds |
| `session.started` | sandbox allocated and running |
| `session.message` | user or agent sends a message |
| `session.tool_call` | agent invokes a tool |
| `session.tool_result` | tool returns |
| `session.input_required` | agent paused, waiting on human |
| `session.artifact_created` | PR opened, file written, screenshot taken |
| `session.succeeded` | terminal success |
| `session.failed` | terminal failure; `data.reason` explains |
| `session.cancelled` | user or timeout cancelled |
| `usage.threshold_crossed` | org crossed 80 % of a monthly limit |
