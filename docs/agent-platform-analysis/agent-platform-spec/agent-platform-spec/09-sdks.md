# 09 · SDKs

Two first-party SDKs, identical surface, idiomatic in each language. TypeScript uses `AsyncIterable` + `for-await-of`; Python uses `async for`. Everything else is the same.

## Design principles

- **Resource-oriented.** `client.sessions.create`, `client.environments.list`. One class per resource.
- **Streams are async iterables.** SSE exposed as a native async iterator. No callback emitters.
- **Two auth modes, one client.** Construct with `apiKey` (server) or `userToken` (browser/extension).
- **Resumable by default.** Every stream accepts `lastEventId`; dropped connection = resume from last `seq`.

---

## TypeScript

### Surface

```ts
export class AgentClient {
  constructor(opts: {
    apiKey?:    string                // rpk_live_… (server)
    userToken?: string                // eyJ…       (browser)
    orgId:      string
    baseUrl?:   string
    fetch?:     typeof globalThis.fetch
  })

  sessions:     Sessions
  environments: Environments
  connections:  Connections
  secrets:      Secrets
  webhooks:     Webhooks
  usage:        Usage
}

export class Sessions {
  create(params: CreateSession):                     Promise<Session>
  get(id: string):                                   Promise<Session>
  list(params?: ListSessions):                       AsyncIterable<Session>
  cancel(id: string):                                Promise<Session>
  reply(id: string, text: string):                   Promise<void>
  fork(id: string, fromSeq: number, prompt: string): Promise<Session>
  artifacts(id: string):                             Promise<Artifact[]>

  events(id: string, opts?: {
    lastEventId?: string
    signal?: AbortSignal
  }):                                                AsyncIterable<Event>

  connect(id: string, userToken: string):            SessionChannel
}
```

### Usage

```ts
const client = new AgentClient({ apiKey: KEY, orgId: "org_2fJxKk9" });

// 1. Create — non-blocking, returns in <200ms
const session = await client.sessions.create({
  workspace_id: "ws_aK3p",
  prompt: "fix the flaky test in payments/refund_spec.ts",
});

// 2. Stream events
for await (const evt of client.sessions.events(session.id)) {
  switch (evt.type) {
    case "status_change":    console.log("→", evt.data.to); break;
    case "tool_call":        console.log("↳", evt.data.tool); break;
    case "input_required":   await client.sessions.reply(session.id, ask()); break;
    case "artifact_created": console.log("✓", evt.data.external_url); break;
    case "session_ended":    return evt.data.status;
  }
}

// 3. Resume after a disconnect
for await (const evt of client.sessions.events(id, { lastEventId: "142" })) {
  // picks up at seq 143
}

// 4. Auto-pagination for list()
for await (const s of client.sessions.list({ status: "running" })) {
  console.log(s.id, s.initial_prompt);
}

// 5. Cancel / fork are RPCs
await client.sessions.cancel(id);
const forked = await client.sessions.fork(id, 87, "try a different approach");
```

### WebSocket (multiplayer)

```ts
const channel = client.sessions.connect(session.id, userJwt);

channel.on("participant.joined", (p) => showAvatar(p.user_id));
channel.on("session.message",    (m) => appendMessage(m));
channel.on("tool_call",          (t) => appendToolCall(t));
channel.on("artifact_created",   (a) => showArtifact(a));

channel.send({ type: "message.send", data: { text: "add a regression test" } });
channel.send({ type: "cursor.moved", data: { file: "refund_spec.ts", line: 42 } });

channel.close();
```

### Internals — SSE parser

One method shown in full; rest follows the same pattern.

```ts
async *events(id: string, opts: { lastEventId?: string, signal?: AbortSignal } = {}) {
  const url = `${this.client.baseUrl}/organizations/${this.client.orgId}/sessions/${id}/events`;
  const headers: Record<string, string> = { Accept: "text/event-stream" };
  if (opts.lastEventId) headers["Last-Event-ID"] = opts.lastEventId;
  headers.Authorization = this.client._authHeader();

  const res = await this.client.fetch(url, { headers, signal: opts.signal });
  if (!res.body) throw new Error("no body");

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += value;
    let idx;
    while ((idx = buf.indexOf("\n\n")) !== -1) {
      const frame = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const data = frame.split("\n").find(l => l.startsWith("data: "))?.slice(6);
      if (data) yield JSON.parse(data) as Event;
    }
  }
}
```

---

## Python

### Surface

```python
from typing import AsyncIterator, Optional

class AgentClient:
    def __init__(
        self,
        org_id: str,
        api_key: Optional[str] = None,
        user_token: Optional[str] = None,
        base_url: str = "https://api.example.com",
    ): ...

    sessions:     "Sessions"
    environments: "Environments"
    connections:  "Connections"
    secrets:      "Secrets"
    webhooks:     "Webhooks"
    usage:        "Usage"

    async def __aenter__(self) -> "AgentClient": ...
    async def __aexit__(self, *exc) -> None: ...


class Sessions:
    async def create(self, **params) -> "Session": ...
    async def get(self, id: str) -> "Session": ...
    async def list(self, **params) -> AsyncIterator["Session"]: ...
    async def cancel(self, id: str) -> "Session": ...
    async def reply(self, id: str, text: str) -> None: ...
    async def fork(self, id: str, from_seq: int, prompt: str) -> "Session": ...
    async def artifacts(self, id: str) -> list["Artifact"]: ...

    async def events(
        self, id: str, *, last_event_id: Optional[str] = None,
    ) -> AsyncIterator["Event"]: ...
```

### Usage

```python
import asyncio
from agent_sdk import AgentClient

async def main():
    async with AgentClient(org_id="org_2fJxKk9", api_key=KEY) as client:
        session = await client.sessions.create(
            workspace_id="ws_aK3p",
            prompt="fix the flaky test in payments/refund_spec.ts",
        )

        async for evt in client.sessions.events(session.id):
            match evt.type:
                case "status_change":    print("→", evt.data["to"])
                case "tool_call":        print("↳", evt.data["tool"])
                case "input_required":   await client.sessions.reply(session.id, ask())
                case "artifact_created": print("✓", evt.data["external_url"])
                case "session_ended":    return evt.data["status"]

        async for s in client.sessions.list(status="running"):
            print(s.id, s.initial_prompt)

asyncio.run(main())
```

### Internals — httpx + SSE

```python
import httpx, json
from typing import AsyncIterator

class Sessions:
    def __init__(self, client: "AgentClient"):
        self._c = client

    async def create(self, **params) -> "Session":
        r = await self._c._http.post(
            f"/organizations/{self._c.org_id}/sessions",
            json=params,
            headers={"Idempotency-Key": params.pop("idempotency_key", _uuid())},
        )
        r.raise_for_status()
        return Session(**r.json())

    async def events(
        self, id: str, *, last_event_id: str | None = None,
    ) -> AsyncIterator["Event"]:
        headers = {"Accept": "text/event-stream"}
        if last_event_id:
            headers["Last-Event-ID"] = last_event_id

        async with self._c._http.stream(
            "GET",
            f"/organizations/{self._c.org_id}/sessions/{id}/events",
            headers=headers,
            timeout=None,
        ) as r:
            r.raise_for_status()
            buf = ""
            async for chunk in r.aiter_text():
                buf += chunk
                while "\n\n" in buf:
                    frame, buf = buf.split("\n\n", 1)
                    for line in frame.splitlines():
                        if line.startswith("data: "):
                            yield Event(**json.loads(line[6:]))
```
