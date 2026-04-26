# 18 · SDK & Client Patterns — 30 Use Cases

The SDK's job is to make every kind of client *look the same from the outside* — whether it's a Slack bot, a Chrome extension using ReactGrab, a CI runner, a mobile app, or a Postgres trigger. This document walks through the SDK surface once, then demonstrates it across 30 distinct client patterns to prove the surface is actually flexible enough.

## 1 · Design principles

The SDK is **thin by design**. It does five things and nothing else:

1. **Build HTTP requests** with the right auth headers for whichever token type you passed it.
2. **Parse SSE and WebSocket streams** into native async iterables.
3. **Auto-paginate** list endpoints.
4. **Shape-match types** to the server's OpenAPI. No runtime validation; TypeScript/Pydantic types.
5. **Propagate cancellation** via `AbortSignal` (TS) / `CancelScope` (Python).

Everything else — retries, caching, persistence, UI state, reconnection logic — is **the client's responsibility**, because every runtime has different primitives. A React app has `useState`; a Cloudflare Worker has Durable Object storage; a CLI has a filesystem. Baking one retry policy into the SDK makes it wrong for everyone.

## 2 · Core surface (one page)

```ts
// @platform/agent-sdk
export class AgentClient {
  constructor(opts: {
    apiKey?:    string              // rpk_live_… (server)
    userToken?: string              // eyJ…       (browser/extension)
    orgId:      string
    baseUrl?:   string
    fetch?:     typeof fetch        // for runtimes with weird fetch (Workers, RN)
    telemetry?: (e: TelemetryEvent) => void
  })

  sessions:     Sessions
  environments: Environments
  secrets:      Secrets
  connections:  Connections
  webhooks:     Webhooks
  usage:        Usage
  artifacts:    Artifacts
}

class Sessions {
  create(p: CreateSession):                    Promise<Session>
  get(id: string):                             Promise<Session>
  list(p?: ListSessions):                      AsyncIterable<Session>    // auto-paginate
  cancel(id: string):                          Promise<Session>
  reply(id: string, text: string):             Promise<void>
  fork(id: string, fromSeq: number, prompt: string): Promise<Session>

  events(id: string, o?: EventOpts):           AsyncIterable<Event>      // SSE, resumable
  connect(id: string, userToken: string):      SessionChannel            // WebSocket

  share(id: string, grants: Grant[]):          Promise<void>
}

interface SessionChannel {
  on<T extends Event["type"]>(type: T, fn: (e: EventByType<T>) => void): void
  send(msg: ChannelMessage):                   void
  close():                                     void
}
```

Python mirrors this exactly with `async for` instead of `for-await-of` and `contextlib.AbstractAsyncContextManager` for the client.

## 3 · Four primitive interaction patterns

Every one of the 30 use cases below is a combination of these four. Learn these and the SDK reveals itself.

**A. Fire-and-forget.** Create, don't wait, handle the result via webhook or later poll.
```ts
const s = await client.sessions.create({ prompt: "..." });
// done. server webhook notifies us on completion.
```

**B. Synchronous wait.** Create, block until terminal state.
```ts
const s = await client.sessions.create({ prompt: "..." });
for await (const e of client.sessions.events(s.id))
  if (e.type === "session_ended") return e.data.status;
```

**C. Live stream.** Create, stream incremental events to a UI.
```ts
const s = await client.sessions.create({ prompt: "..." });
for await (const e of client.sessions.events(s.id)) render(e);
```

**D. Interactive multiplayer.** Create, open WebSocket, users send messages + see presence.
```ts
const ch = client.sessions.connect(s.id, userToken);
ch.on("session.message", m => append(m));
ch.send({ type: "message.send", data: { text: "..." } });
```

## 4 · Thirty use cases

Organized by client runtime, with escalating complexity.

### Server-side (long-running backends)

**1. Slack slash command → thread reply.** Pattern B. User types `/agent fix the flaky test`; bot creates session, posts thread, webhook updates thread on completion. Full code in [`10 §1`](./10-client-patterns.md).

**2. Discord bot with presence.** Pattern D. Multiple users in a voice channel watch the same session via a shared embed. Bot relays `participant.joined` events to Discord presence.

**3. GitHub Action that fixes failing tests.** Pattern B. On `workflow_run.failure`, create session with commit SHA + failing test name. Exit code = session status. CI gates on it.

**4. Linear webhook → auto-triage.** Pattern A. New bug report → create session with issue body as prompt → agent opens PR with reproduction + fix, posts link back to Linear.

**5. Cron nightly codebase health check.** Pattern B. Scheduled job per tenant; session runs lint/security/dep-audit; webhook delivers report.

**6. Stripe webhook → usage-based billing.** Pattern A. Listen for `usage.threshold_crossed` webhooks; post Stripe usage records. Bidirectional: no session creation, just consuming events.

**7. Email-to-agent inbound.** Pattern A. Inbound email via Resend/SendGrid webhook → parse subject+body → create session with reply-to as metadata → webhook response emails the thread back.

**8. Postgres trigger → refactor on schema change.** Pattern A. DB migration deployed → trigger → session tasked with updating ORM models. Non-interactive.

**9. Tenant backend bridging to their own users.** Pattern A + user JWT minting. Tenant runs token exchange on their server, hands short-lived user JWTs to their own frontend. The spec's [`01 §Token exchange`](./01-auth-and-tenancy.md) pattern.

### Browser / dashboard

**10. Custom dashboard with live session feed.** Pattern C. React app subscribes to `sessions.events(id)` for every active session; renders a kanban of "planning / working / reviewing / done" with real-time transitions.

**11. Hosted-editor iframe.** Pattern D. Next.js page embeds the platform's editor tunnel URL; sidebar app uses `SessionChannel` for messages + presence. Full code in [`10 §3`](./10-client-patterns.md).

**12. Agent playground / public demo.** Pattern C. Marketing site uses an anonymous API key with a quota of 3 sessions/IP/day. Visitors type a prompt, watch the agent work, get a read-only link to share.

**13. Shareable session replay.** Pattern A + artifact fetch. After a session ends, generate a public read-only URL that streams stored events + final artifacts. Useful for bug reports ("here's what the agent did").

**14. Multi-cursor review view.** Pattern D. Team reviews an agent's PR; everyone sees each other's cursor position in the diff via `cursor.moved` WebSocket messages. Presence comes free.

**15. Mobile companion app (React Native).** Pattern C with pared-down UI. Receive push notifications for `input_required` events; reply from phone. SDK runs in RN with the `fetch` polyfill.

### Extensions

**16. Plasmo Chrome extension with element picker.** Pattern A. Alt+Shift+A to arm, click element, describe change. Full code in [`11`](./11-chrome-extension-plasmo.md).

**17. ReactGrab-style visual picker.** Pattern A. Hover any React component on the page; ReactGrab highlights the component tree, you click one, its props + source file location get attached to the session prompt. The agent has rich component context, not just DOM. (See §5 below for the full pattern.)

**18. Firefox extension mirror.** Same Plasmo code targets both MV3-capable browsers; SDK doesn't care which browser context it's in.

**19. Safari Web Extension with iCloud Keychain auth.** Pattern A. Platform API key stored in Keychain; user authorizes access via Safari prompt. SDK works unchanged; only the credential source differs.

**20. VS Code extension sidebar.** Pattern C. "Ask agent" right-click on a file → opens sidebar with live event stream. User can send follow-ups inline. Uses `vscode.window.withProgress` to show "agent is thinking."

**21. Raycast extension (macOS launcher).** Pattern B. Raycast action → synchronous agent run with live spinner showing latest event → copy PR link to clipboard on finish.

**22. JetBrains plugin.** Same shape as the VS Code extension; different plugin API; identical SDK usage.

### CLI and local dev

**23. Local CLI `agent do "..."`**. Pattern C. Detect terminal TTY; render live events with `ink` (TS) or `rich` (Python). Follow-ups via stdin. Ctrl+C aborts via `AbortSignal`.

**24. tmux/iTerm session-per-tab.** Pattern C × N. Spawn one session per terminal tab; each tab runs its own event stream; status line shows aggregate. Makes parallel agent work ergonomic.

**25. Git pre-push hook.** Pattern B. On push, run agent against changed files for a security check. Blocks push if session fails. Local hook, remote agent.

**26. Make target integration.** Pattern B. `make agent-fix` invokes the CLI with prompt loaded from a `.agent-prompts/` file. Exit code propagates.

**27. Shell auto-complete-on-failure.** Pattern A. Zsh/Fish hook: when a command exits non-zero, offer to `agent fix this`; on accept, creates session with the last command + its output as context.

### Edge and embedded

**28. Cloudflare Worker as webhook relay.** Pattern A, no streaming. Worker receives a form POST, creates a session, returns immediately. Uses the `fetch` constructor option because Workers have a subtly different `fetch`.

**29. Vercel Edge Function for public demo.** Pattern C with SSE proxying. Edge function accepts a public request, creates a session, streams events back to the browser. Platform API key hidden from client.

**30. Zapier / Make / n8n custom integration.** Pattern A. Node box that creates a session from a trigger, waits for webhook delivery, passes the artifact URL to the next step. The SDK runs in the no-code platform's sandboxed Node environment.

## 5 · The ReactGrab extension pattern (worked example)

[ReactGrab](https://github.com/code-yeongyu/reactgrab) lets a user visually select a React component on any page and extract its source code, props, and file location — all at runtime, using the React DevTools hooks. Combining it with the platform's Chrome extension pattern gives you something genuinely new: **an agent that gets *component-level* context, not DOM-level context.**

The user's mental model: "point at this component, tell the agent what to change."

### The flow

```
User arms picker (Alt+Shift+G)
    ↓
Hovers a React component → ReactGrab highlights its boundary
    ↓
Clicks → ReactGrab extracts: { componentName, filePath, props, sourceCode }
    ↓
Extension shows prompt panel with extracted context pre-filled
    ↓
User describes change → sendToBackground("create-session", { reactgrab_context, prompt })
    ↓
Background worker → SDK → session created with rich metadata
    ↓
Agent has: file path (knows where to edit), props (knows the interface),
           source (knows the current implementation), prompt (knows the intent)
```

### The Plasmo content script (diff against [`11`](./11-chrome-extension-plasmo.md))

```tsx
// contents/reactgrab-picker.tsx
import type { PlasmoCSConfig } from "plasmo"
import { useEffect, useState } from "react"
import { sendToBackground } from "@plasmohq/messaging"
import { ReactGrab } from "@reactgrab/core"

export const config: PlasmoCSConfig = {
  matches: ["<all_urls>"],
  run_at:  "document_idle",
}

export const getOverlayAnchor = async () => document.body

type GrabbedComponent = {
  name:       string
  filePath:   string         // e.g. "src/components/CheckoutButton.tsx:42"
  props:      Record<string, any>
  sourceCode: string
  treeePath:  string[]       // ["App", "CheckoutPage", "CheckoutButton"]
}

function ReactGrabPicker() {
  const [armed,   setArmed]   = useState(false)
  const [grabbed, setGrabbed] = useState<GrabbedComponent | null>(null)
  const [prompt,  setPrompt]  = useState("")

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.altKey && e.shiftKey && e.code === "KeyG") setArmed(v => !v)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  useEffect(() => {
    if (!armed) return

    // ReactGrab's arm() API: hooks into React DevTools fiber tree,
    // returns a teardown function.
    const teardown = ReactGrab.arm({
      onHover: (fiber) => ReactGrab.highlight(fiber),
      onSelect: async (fiber) => {
        const extracted = await ReactGrab.extract(fiber, {
          includeSource: true,
          includeProps:  true,
          maxDepth:      3,
        })
        setGrabbed({
          name:       extracted.displayName,
          filePath:   extracted.source.fileName + ":" + extracted.source.lineNumber,
          props:      extracted.memoizedProps,
          sourceCode: extracted.source.code,
          treeePath:  extracted.ancestors.map(a => a.displayName),
        })
        setArmed(false)
      },
    })
    return teardown
  }, [armed])

  const dispatch = async () => {
    if (!grabbed || !prompt.trim()) return

    await sendToBackground({
      name: "create-session",
      body: {
        prompt,
        tab_url: location.href,
        metadata: {
          origin: "chrome-extension-reactgrab",
          reactgrab: {
            component:   grabbed.name,
            file_path:   grabbed.filePath,
            tree_path:   grabbed.treeePath.join(" > "),
            props:       grabbed.props,
            source_code: grabbed.sourceCode,
          },
        },
      },
    })
    setGrabbed(null)
    setPrompt("")
  }

  return (
    <>
      {armed && (
        <div style={bannerStyle}>
          🎯 hover a React component · click to grab · esc to cancel
        </div>
      )}
      {grabbed && (
        <div style={panelStyle}>
          <div style={{ fontSize: 11, color: "#888", marginBottom: 4 }}>
            &lt;{grabbed.name} /&gt;
          </div>
          <div style={{ fontSize: 10, color: "#aaa", fontFamily: "monospace" }}>
            {grabbed.filePath}
          </div>
          <div style={{ fontSize: 10, color: "#aaa", marginBottom: 8 }}>
            {grabbed.treeePath.join(" › ")}
          </div>
          <details style={{ fontSize: 11, marginBottom: 8 }}>
            <summary>props ({Object.keys(grabbed.props).length})</summary>
            <pre style={{ maxHeight: 120, overflow: "auto", fontSize: 10 }}>
              {JSON.stringify(grabbed.props, null, 2)}
            </pre>
          </details>
          <textarea
            autoFocus
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            placeholder={`describe the change to <${grabbed.name}>`}
            style={{ width: "100%", minHeight: 72, marginBottom: 8 }}
          />
          <button onClick={dispatch}>dispatch</button>
          <button onClick={() => setGrabbed(null)} style={{ marginLeft: 8 }}>
            cancel
          </button>
        </div>
      )}
    </>
  )
}

const bannerStyle: React.CSSProperties = {
  position: "fixed", top: 16, left: "50%", transform: "translateX(-50%)",
  zIndex: 2147483647, padding: "8px 16px",
  background: "#5b4dd4", color: "#fff",
  borderRadius: 4, fontFamily: "system-ui", fontSize: 13,
}

const panelStyle: React.CSSProperties = {
  position: "fixed", bottom: 24, right: 24, width: 380, padding: 16,
  background: "#fff", border: "1px solid #ddd", borderRadius: 8,
  boxShadow: "0 8px 32px rgba(0,0,0,0.15)", zIndex: 2147483647,
  fontFamily: "system-ui", fontSize: 13,
}

export default ReactGrabPicker
```

### Why this is more powerful than the DOM picker from [`11`](./11-chrome-extension-plasmo.md)

The original picker captures:
- CSS selector path
- outer HTML

ReactGrab picker captures:
- **Component name** — agent knows what the thing *is*, not just what it looks like
- **File path and line number** — agent knows exactly where to edit, no grepping
- **Props** — agent knows the interface the component exposes
- **Source code** — agent knows the current implementation
- **Tree path** — agent knows the parent context

That's enough information for the agent to make a change *without cloning the repo and searching*. The prompt can go from "change the checkout button color" (DOM picker) to "in `CheckoutButton.tsx:42`, which currently renders a purple primary button, change the variant prop to accept a `theme: 'dark' | 'light'` option and update the Tailwind classes accordingly" — generated by the extension, not typed by the user.

### The SDK's job in this pattern

Exactly zero SDK changes. Everything ReactGrab-specific is metadata on the session. The agent runtime on the server reads `metadata.reactgrab.*` and adjusts its prompt accordingly. If you ever want to surface ReactGrab context differently (e.g. render a code-diff preview in the event stream), you do it by emitting different event types from the agent — no SDK change.

**This is the SDK's load-bearing design choice:** metadata is opaque to the SDK. Any client can invent its own metadata schema, and the agent runtime decides how to consume it. The SDK doesn't need a release for every new client pattern.

## 6 · Auth patterns by client type

The token you pass to `AgentClient` determines what the client can do. This is the other dimension of the surface.

| Client runtime | Token type | How it gets there |
|---|---|---|
| Tenant server (Slack bot, CI) | **Platform key** `rpk_live_…` | Env var, long-lived |
| Tenant dashboard (browser) | **User JWT** `eyJ…` | Exchanged from session cookie |
| Chrome/Firefox extension | **User JWT** `eyJ…` | Stored in extension storage after OAuth |
| Mobile app | **User JWT** | Stored in secure enclave/Keychain |
| Public demo (Vercel Edge) | **Platform key, proxied** | Key lives in Edge env; client never sees it |
| Sandbox itself | **Session token** `sess_tok_…` | Injected at boot, used only for Broker |
| CLI | **User JWT** or **platform key** | `~/.config/agent/credentials` |

The SDK doesn't care which you pass; it just sets the right `Authorization` header. But the **scope** of what the SDK can do differs:
- Platform key → can act on any org resource
- User JWT → RBAC-gated subset
- Session token → can only hit the Broker, nothing else

## 7 · Non-goals (what the SDK deliberately doesn't do)

Each of these is tempting and each would make the SDK worse:

- **No retry policies.** Retries depend on runtime (CLI can retry forever, Edge Function has 10s budget). Client code decides.
- **No caching.** What to cache depends on the UX. A dashboard caches sessions; a CLI doesn't.
- **No local state sync.** No "subscribe to all my sessions and keep them live in an object." The SDK gives you iterators; you build sync on top if you need it.
- **No auth flows.** The SDK consumes tokens; it doesn't obtain them. OAuth happens outside the SDK (via Better Auth or whatever).
- **No "offline mode."** The SDK is a network client; offline is a client-layer concern.

Keeping the SDK this small is what makes all 30 use cases possible with the same package.

## 8 · What to build first

Not all 30 at once. Suggested priority:

1. **Slack slash command + webhook** (#1). Highest bang/buck, demos well, validates the server pattern.
2. **GitHub Action** (#3). CI integration is the second most common way people try an agent platform.
3. **Hosted-editor iframe + React dashboard** (#10, #11). The visually-impressive piece that sells the product.
4. **CLI** (#23). Internal tool first; dogfood it for your team. Surfaces SDK papercuts fast.
5. **Plasmo extension with ReactGrab** (#17). Distinctive and showable; the "we do what nobody else does" demo.
6. **The other 25.** Build as customer demand dictates. None requires SDK changes.

## 9 · Three next steps

1. **Write the SDK's smoke test before writing the SDK.** A test file that exercises all four primitive patterns (A, B, C, D) against a mock server. If the test is ugly to write, the SDK surface is wrong. This takes 2 hours and saves 2 weeks of incremental API drift.
2. **Ship #1 and #23 (Slack bot + CLI) against a stubbed backend.** Same backend stub both use. Validates that the same SDK works in opposite runtimes (long-lived server vs. one-shot CLI) without branching.
3. **Try ReactGrab against a real React app before committing to the pattern.** ReactGrab depends on React DevTools hooks being injected. If the target page disables them (many production apps do via `__REACT_DEVTOOLS_GLOBAL_HOOK__` suppression), the picker degrades to the DOM picker. Know this before demoing.

## Reflective question

The SDK surface above is ~100 lines of public API for 30 use cases. That ratio — 1 line of SDK per 0.3 use cases — is the argument for keeping it small.

**When you imagine yourself using the SDK six months from now, on a use case you haven't thought of yet — what's the shape of the method call you wish was there?** If it's "like one of the four primitive patterns, with new metadata," the SDK is right. If it's something structurally new (streaming *to* the session, long-polling against artifacts, federated queries across orgs) — that's a hint the core surface needs to grow, not that the client should hack around it.

The discipline is resisting the hack-around until the pattern has appeared twice.
