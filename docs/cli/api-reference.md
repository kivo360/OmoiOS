# OmoiOS CLI ↔ API Reference

Comprehensive mapping of every `omoios` subcommand to the HTTP / WebSocket
calls it makes against the OmoiOS backend, with request bodies, query
params, headers, response shapes, and the SDK method that does the work.

Source of truth:
- CLI: `sdk/python/omoios/cli/*.py`
- SDK: `sdk/python/omoios/resources/*.py`, `client.py`
- Backend routes: `backend/omoi_os/api/routes/*.py`

Spec alignment: doc-18 (`docs/agent-platform-analysis/.../18-sdk-and-client-patterns.md`).

---

## 0 · Cross-cutting concerns

### Auth headers

Resolved by `AsyncOmoiOSClient._headers()` (`sdk/python/omoios/client.py:236`).
Exactly one of these three is sent on every HTTP request:

| Token kind | Source | Header |
|---|---|---|
| Platform API key (`sk_live_…`) | `OMOIOS_PLATFORM_API_KEY` env, `--api-key` flag, or `api_key` in config file | `Authorization: Bearer <key>` |
| User JWT (`eyJ…`) | `OMOIOS_USER_JWT` env, or `user_jwt` in config file (written by `omoios signup`) | `Authorization: Bearer <jwt>` |
| Session token (`sess_tok_…`) | Injected by Broker into sandbox env (not used by CLI) | `Authorization: Bearer <session-token>` |

Plus on every request:
- `User-Agent: omoios-sdk/<version>`
- `Accept: application/json`

Mutual-exclusivity check: `client.py:200-204` raises if more than one is set.

### Base URL precedence (`_config.resolve_config`)

1. `--api-base-url` flag
2. `OMOIOS_API_BASE_URL` env
3. `api_base_url` in `~/Library/Application Support/omoios/config.json`
   (or `$XDG_CONFIG_HOME/omoios/config.json`, or `$OMOIOS_CONFIG_DIR/config.json`)

### Idempotency

`POST /api/v1/sessions` always sends an `Idempotency-Key: <uuid4>`
header (auto-generated unless caller supplies one). Same key + same body
returns the same Session.

### Pagination

List endpoints use `?limit=<n>&offset=<n>`. The SDK's `list()` methods
auto-paginate (default `page_size=100`), yielding rows; `list_all()` is
the eager `List[T]` variant. Server returns either a bare JSON array or
`{"items":[...]}` — SDK handles both.

### Error mapping

`client.py:_handle_errors` maps HTTP status → SDK exceptions:
`AuthError` (401), `PermissionError` (403), `NotFoundError` (404),
`ConflictError` (409), `RateLimitError` (429), `ValidationError` (422),
`APIError` (anything else). The CLI's `_run_sdk` helper translates these
to `CliError` with `--api-key` / signup hints.

### Telemetry

`AsyncOmoiOSClient(telemetry=callback)` receives:
- `{"kind":"request","method":...,"path":...,"status":...,"duration_ms":...}`
- `{"kind":"stream_open","path":...}` / `stream_close` (for SSE & WS)

---

## 1 · `omoios signup`

Six sequential HTTP calls. Implemented at `sdk/python/omoios/cli/signup.py`.

| # | Step | Method | Path | Body | Auth |
|---|---|---|---|---|---|
| 1 | Register | POST | `/api/v1/auth/register` | `{email, password, full_name?}` | none |
| 2 | Login (mint JWT) | POST | `/api/v1/auth/login` | `{email, password}` | none |
| 3 | List orgs | GET | `/api/v1/organizations` | — | JWT |
| 3a | Create org (if none) | POST | `/api/v1/organizations` | `{name, slug}` | JWT |
| 4 | Mint platform API key | POST | `/api/v1/auth/api-keys` | `{name, scopes:["*"], organization_id}` | JWT |
| 5 | Write XDG config | (local) | — | `{api_base_url, api_key, user_id, user_jwt}` | — |
| 6 | (`--connect-github`) | (local) | runs `omoios auth github` | — | — |

Idempotency: 409 / "already" on register is treated as soft-success
(`signup.py:_register`). Org create derives slug as
`{name-lower-kebab}-{unix_ts}`.

**Response handling**:
- Login: `body["access_token"]` → JWT (persisted as `user_jwt`)
- Mint key: `body["key"]` → platform key, `body["user_id"]` → owner UUID

---

## 2 · `omoios auth github`

GitHub OAuth Device Flow (RFC 8628). Implemented at
`sdk/python/omoios/cli/auth.py:run_github_device_flow`. **No OmoiOS API
calls** — this hits GitHub directly, then patches the local config.

| # | Step | Method | URL | Body |
|---|---|---|---|---|
| 1 | Request device code | POST | `https://github.com/login/device/code` | `client_id, scope=read:user repo` |
| 2 | Poll for token | POST | `https://github.com/login/oauth/access_token` | `client_id, device_code, grant_type=urn:ietf:params:oauth:grant-type:device_code` |
| 3 | Update XDG config | (local) | — | merge `{github_token: …}` |

Default `client_id`: `Ov23lix7wDPhUskntl4c` (production OAuth App with
Device Flow enabled).

---

## 3 · `omoios whoami`

| Method | Path | Auth | Returns |
|---|---|---|---|
| GET | `/api/v1/auth/me` | platform key **or** JWT | `{id, email, full_name, is_active, …}` |

If 401 → CLI prints "API key is invalid; rerun `omoios signup`".

---

## 4 · `omoios config {show, path, clear}`

Pure-local; no HTTP. `show` reads `config_path()`, masks `api_key`,
`user_jwt`, `github_token` (first 14 chars + `…(redacted)`); `--reveal`
prints raw values. `path` echoes the resolved file path. `clear` deletes
the file.

---

## 5 · `omoios completion {show, install}`

Pure-local. `cyclopts.App.generate_completion(shell)` writes shell
completion script to stdout (or to `--output <path>`); `install` adds a
source line to the user's shell rc unless `--no-startup`.

---

## 6 · `omoios workspaces …`

SDK: `omoios.resources.workspaces.WorkspacesResource`.

| CLI | Method | Path | Body / Params | Returns |
|---|---|---|---|---|
| `workspaces create --name <n> [--description …]` | POST | `/api/v1/workspaces` | `{name, description?}` | `Workspace` |
| `workspaces list` | GET | `/api/v1/workspaces` | — | `Workspace[]` |
| `workspaces get <id>` | GET | `/api/v1/workspaces/{id}` | — | `Workspace` |
| `workspaces delete <id>` | DELETE | `/api/v1/workspaces/{id}` | — | 204 |
| (SDK only) `get_settings` | GET | `/api/v1/workspaces/{id}/settings` | — | `WorkspaceSettings` |
| (SDK only) `update_settings` | PUT | `/api/v1/workspaces/{id}/settings` | JSON body | `WorkspaceSettings` |

---

## 7 · `omoios environments …`

SDK: `omoios.resources.environments.EnvironmentsResource`. Spec §05
"versions are immutable" — every `set` / `set-secret` does a
**read-merge-INSERT** of a new version, never UPDATE.

| CLI | Method | Path | Body / Params |
|---|---|---|---|
| `environments create --org <id> --name <n>` | POST | `/api/v1/environments` | `CreateEnvironmentRequest` JSON |
| `environments list --org <id>` | GET | `/api/v1/environments` | `?org_id=<id>` |
| `environments get <id>` | GET | `/api/v1/environments/{id}` | — |
| `environments versions <id>` | GET | `/api/v1/environments/{id}/versions` | — |
| `environments versions <id> --version <n>` | GET | `/api/v1/environments/{id}/versions/{n}` | — |
| `environments set <id> KEY=VAL …` | POST | `/api/v1/environments/{id}/versions` | merged `CreateEnvironmentVersionRequest` (variables) |
| `environments set-secret <id> KEY` (prompts) | POST | `/api/v1/environments/{id}/versions` | merged with `credentials.{name}.{value}` |
| `environments rollback <id> --to <n>` | POST | `/api/v1/environments/{id}/versions` | re-INSERTs the version-N variables as a new version |
| `environments bind <id> --workspace <ws>` | POST | `/api/v1/workspaces/{ws}/bindings` | `{environment_id}` |

`CreateEnvironmentVersionRequest` shape:
```json
{
  "variables":   {"KEY": "value"},
  "credentials": {"OPENAI_API_KEY": {"value": "sk-…", "type": "secret"}},
  "image":       "python:3.12-slim"
}
```

---

## 8 · `omoios providers …` (a.k.a. `credentials` in SDK)

SDK: `omoios.resources.credentials.CredentialsResource`.

| CLI | Method | Path | Body / Params |
|---|---|---|---|
| `providers list [--workspace <ws>] [--json]` | GET | `/api/v1/credentials` | `?workspace_id=<ws>` |
| `providers add --name <n> --provider <p> --workspace <ws>` (key from `OMOIOS_PROVIDER_KEY` env or stdin) | POST | `/api/v1/credentials` | `{name, provider, workspace_id, credentials:{api_key:…}}` |
| `providers delete <id>` | DELETE | `/api/v1/credentials/{id}` | — |
| (SDK) `get` | GET | `/api/v1/credentials/{id}` | — |

---

## 9 · `omoios connections …`

SDK: `omoios.resources.connections.ConnectionsResource`. OAuth
provider bindings (GitHub, GitLab, etc.).

| CLI | Method | Path |
|---|---|---|
| `connections list` | GET | `/api/v1/connections` |
| `connections oauth-url <provider>` | POST | `/api/v1/connections/{provider}/start` |
| `connections remove <provider>` | DELETE | `/api/v1/connections/{provider}` |

`oauth-url` returns `{oauth_start_url: "https://…"}`; CLI prints the URL.

---

## 10 · `omoios sessions …` — the centerpiece

SDK: `omoios.resources.sessions.SessionsResource`. All four spec §3
primitive patterns (A/B/C/D) live here.

### 10.1 `sessions create`

| Method | Path | Body | Headers |
|---|---|---|---|
| POST | `/api/v1/sessions` | see below | `Idempotency-Key: <uuid4>` |

Body:
```json
{
  "prompt": "say good morning",
  "workspace_id": "<uuid>",        // OR
  "github_repo":  "owner/repo",    // (auto-binds workspace)
  "environment_id": "<uuid>",      // optional
  "share_with":   ["uuid", "email@x"], // optional
  "metadata":     { "...": "..." }     // opaque, surfaces in agent context
}
```

CLI flags: `--workspace <id>`, `--github-repo owner/repo`,
`--environment <id>`, `--watch` (chains into `_watch_loop` after create
for Pattern C).

### 10.2 `sessions get`

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/sessions/{id}` | Backend rewrites `Task.status="completed"` → `"succeeded"` to match `session.*` event types (spec §03 mapping) |

### 10.3 `sessions list`

| Method | Path | Params |
|---|---|---|
| GET | `/api/v1/sessions` | `limit, offset, status?, phase_id?, ticket_id?` |

CLI: `omoios sessions list [--status running|succeeded|failed|cancelled]`.
Auto-paginates.

### 10.4 `sessions cancel`

| Method | Path |
|---|---|
| DELETE | `/api/v1/sessions/{id}` |

Idempotent. Returns the (now `cancelled`) Session row.

### 10.5 `sessions reply`

| Method | Path | Body |
|---|---|---|
| POST | `/api/v1/sessions/{id}/messages` | `{text}` |

Backend re-opens any terminal Task to `running` for multi-turn (fix for
spec §03 single-turn gap). CLI returns 204; with `--watch`, chains into
`_watch_loop(wait_for_our_text=text)` to skip event-replay history until
seeing the user's own message.

### 10.6 `sessions fork`

| Method | Path | Body |
|---|---|---|
| POST | `/api/v1/sessions/{id}/fork` | `{from_seq, prompt}` |

Returns a brand-new Session whose context replays events 0…`from_seq`
from the parent.

### 10.7 `sessions share` / `unshare`

| CLI | Method | Path | Body |
|---|---|---|---|
| `sessions share <sid> <user-or-email> [role]` | POST | `/api/v1/sessions/{sid}/share` | `{grants:[{user_id\|email, role}]}` |
| `sessions unshare <sid> <user-or-email>` | DELETE | `/api/v1/sessions/{sid}/share/{user_or_email}` | — |

`role` ∈ {`viewer`, `editor`}; default `editor`. Email→UUID resolution
happens server-side (privacy-scoped to share/unshare; no general
`/users` lookup). 422 returns `{missing_emails:[…]}`.

### 10.8 `sessions events` — Pattern C (SSE)

| Method | Path | Headers |
|---|---|---|
| GET | `/api/v1/sessions/{id}/events` | `Accept: text/event-stream`, optional `Last-Event-ID` |

SDK: `httpx-sse.aconnect_sse` → `async for sse in es.aiter_sse():` →
JSON-decode `sse.data` → yield `Event(...)`. Iterator closes when
server completes (replay exhausted + Redis pub/sub dry).

CLI variants:
- `omoios sessions events <id>` → drain to stdout
- `omoios sessions watch <id>` → render envelopes live until terminal

Envelope shape (`SessionEventEnvelope`):
```json
{
  "type": "session.message" | "session.created" | "session.succeeded" | …,
  "actor": "agent" | "user:<uuid>" | "system",
  "data": { "...": "..." },
  "seq": 42,
  "ts": "2026-04-26T20:28:38Z",
  "session_id": "<uuid>"
}
```

### 10.9 `sessions connect` — Pattern D (WebSocket / Textual TUI)

| Method | URL | Auth |
|---|---|---|
| WS | `wss://<host>/api/v1/sessions/{id}/ws?token=<JWT>` | **JWT only** (`session_channel.py:277`) |

SDK: `omoios.resources.sessions.SessionChannel`. `httpx-ws.aconnect_ws`
gives a duplex frame stream; SDK splits into:
- `ch.on(type, fn)` — register handlers (`*` matches all)
- `ch.send(msg)` — JSON-encode + `ws.send_text(...)`
- `_read_loop()` — drains inbound, dispatches by `msg["type"]`

Inbound types handled by the TUI (`connect_tui.py`):
- `session.message` → render `ChatBubble`
- `participant.{joined,left}` → update sidebar
- `presence.{typing,idle}` → typing indicator
- everything else → log to Events panel

Outbound types the TUI sends:
- `message.send` → `{type:"message.send", data:{text:"…"}}`
- `presence.typing` (debounced 1.5s)
- `presence.idle`

Slash commands inside the TUI route through CLI helpers:
- `/share <user|email> [role]` → calls `_share` (POST share)
- `/fork`, `/upload` → log "use other shell"
- `/quit` / Ctrl+Q / Ctrl+C → clean shutdown

---

## 11 · `omoios webhooks …`

SDK: `omoios.resources.webhooks.WebhooksResource`. **Path: `/webhooks/subscriptions`**, not `/webhooks`.

| CLI | Method | Path | Body / Params |
|---|---|---|---|
| `webhooks list --org <id>` | GET | `/api/v1/webhooks/subscriptions` | `?org_id=<id>&limit=100&offset=0` |
| `webhooks create --org <id> --url <u> --events <e1,e2>` | POST | `/api/v1/webhooks/subscriptions` | `?org_id=<id>` body=`CreateWebhookSubscriptionRequest` |
| `webhooks delete <id>` | DELETE | `/api/v1/webhooks/subscriptions/{id}` | — |
| `webhooks deliveries <id>` | GET | `/api/v1/webhooks/subscriptions/{id}/deliveries` | — |

Body shape:
```json
{ "url": "https://…", "events": ["session.succeeded"], "secret": "whsec_…", "active": true }
```

---

## 12 · `omoios artifacts …`

SDK: `omoios.resources.artifacts.ArtifactsResource`.

| CLI | Method | Path | Body / Params |
|---|---|---|---|
| `artifacts upload <path> --workspace <ws> [--stdin] [--name] [--content-type] [--session] [--metadata json]` | POST | `/api/v1/artifacts` | multipart: `files={file:(name, bytes, ct)}`, `data={workspace_id, session_id?, metadata?}` |
| `artifacts list --workspace <ws> [--limit 100] [--offset 0]` | GET | `/api/v1/artifacts` | `?workspace_id=<ws>&limit&offset` |
| `artifacts get <id>` | GET | `/api/v1/artifacts/{id}` | — |
| `artifacts download <id>` | GET | `/api/v1/artifacts/{id}/download` | — (returns raw bytes) |
| (SDK only) `delete` | DELETE | `/api/v1/artifacts/{id}` | — |

---

## 13 · `omoios usage …`

SDK: `omoios.resources.usage.UsageResource`.

| CLI | Method | Path | Params |
|---|---|---|---|
| `usage current [--org <id>] [--workspace <ws>]` | GET | `/api/v1/usage` | `?org_id?&workspace_id?` |
| `usage for-session <id>` | GET | `/api/v1/usage/sessions/{id}` | — |

Returns aggregated counters: tokens in/out, sandbox seconds, artifact
bytes, $ charges (where instrumented).

---

## 14 · Spec §3 Pattern map (which CLI command implements which primitive)

| Pattern | Spec name | CLI surface |
|---|---|---|
| A | Fire-and-forget | `omoios sessions create` (no `--watch`) |
| B | Synchronous wait | `omoios sessions create --watch` exits on terminal status |
| C | Live stream | `omoios sessions events`, `omoios sessions watch` |
| D | Multiplayer | `omoios sessions connect` (Textual TUI over WebSocket) |

---

## 15 · Endpoints we **do not** call from the CLI

Tracked for completeness:

- `POST /api/v1/auth/refresh` — JWT refresh; CLI re-runs signup instead.
- `POST /api/v1/auth/logout` — not exposed; `omoios config clear` is the
  local equivalent.
- Internal `/api/v1/broker/*` — sandbox-side only (session-token scope).
- `/api/v1/agents/heartbeat` — server-internal.
- Egress proxy / exposed-port routes — not deployed (deferred per
  CLAUDE.md MEMORY note).

---

## 16 · File-pointer index

Quick jump-list for navigating the implementation:

| Concern | File |
|---|---|
| Token resolution / config file | `sdk/python/omoios/cli/_config.py` |
| Auth headers / `_request` retry | `sdk/python/omoios/client.py` |
| Sessions HTTP/SSE/WS | `sdk/python/omoios/resources/sessions.py` |
| Textual three-zone TUI | `sdk/python/omoios/cli/connect_tui.py` |
| CLI signup (6-step) | `sdk/python/omoios/cli/signup.py` |
| GitHub Device Flow | `sdk/python/omoios/cli/auth.py` |
| Backend WS auth gate | `backend/omoi_os/api/routes/session_channel.py:277` |
| Backend session reply (re-opens task) | `backend/omoi_os/api/routes/sessions.py` |
| Backend status mapping | `_map_status` / `_enrich_session_response` in `sessions.py` |
| Spec source | `docs/agent-platform-analysis/agent-platform-spec/agent-platform-spec/18-sdk-and-client-patterns.md` |
