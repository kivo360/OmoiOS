# 07 · Multiplayer

Within one tenant, multiple users can watch and steer the same session. Ramp gets this nearly for free because Durable Objects are already the session actor. Externally the pattern is the same; the only new work is the ACL.

## Sharing

```json
POST /v1/organizations/{org}/sessions/{id}/share

{
  "grants": [
    { "user_id": "usr_1Nbp", "role": "editor" },
    { "user_id": "usr_4Txm", "role": "viewer" }
  ]
}
```

| Role | Can |
|---|---|
| `owner` | full control, delete, re-share |
| `editor` | send messages, cancel, fork |
| `viewer` | read events, artifacts, editor URL |

## Presence over WebSocket

Every WebSocket message attributes `user_id`. Presence events: `participant.joined`, `participant.left`, `cursor.moved`. The session actor broadcasts each event to every connected participant.
