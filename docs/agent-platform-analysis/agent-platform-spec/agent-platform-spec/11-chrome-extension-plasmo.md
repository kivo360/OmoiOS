# 11 · Chrome Extension (Plasmo + React)

Ramp's extension lets non-engineers click an element on any internal page and describe a change; the agent picks it up with full DOM context. That pattern translates one-for-one to a multi-tenant public API.

**Trust boundary inside the extension:** the background service worker is the **only** surface that holds the platform API key. Popup and content script talk to it via `@plasmohq/messaging`; neither ever touches the platform directly.

> Verified against Plasmo docs via DeepWiki, April 2026. Confirmed: `PlasmoCSConfig`, `getOverlayAnchor`, default-exported React component, `@plasmohq/messaging` `sendToBackground` + `listen`, `@plasmohq/storage` `useStorage` hook.

## Layout

```
my-agent-extension/
├── package.json
├── tsconfig.json
├── popup.tsx                  # popup UI (React)
├── background.ts              # MV3 service worker, message router
├── contents/
│   └── picker.tsx             # content-script UI: click-to-select overlay
├── lib/
│   └── agent-client.ts        # SDK wrapper
└── assets/
    └── icon.png
```

| File | Role |
|---|---|
| `popup.tsx` | Entry point: recent sessions, quick prompt, settings. Uses `useStorage` + `sendToBackground`. |
| `contents/picker.tsx` | In-page overlay: click element, describe change. `PlasmoCSConfig` + `getOverlayAnchor`. |
| `background.ts` | API owner. Holds platform key, routes messages. `listen()` from `@plasmohq/messaging`. |

## package.json

```json
{
  "name": "agent-browser",
  "displayName": "Agent Browser",
  "version": "0.0.1",
  "scripts": {
    "dev":     "plasmo dev",
    "build":   "plasmo build",
    "package": "plasmo package"
  },
  "dependencies": {
    "@plasmohq/messaging": "^0.6.2",
    "@plasmohq/storage":   "^1.11.0",
    "plasmo":    "0.88.0",
    "react":     "18.2.0",
    "react-dom": "18.2.0"
  },
  "devDependencies": {
    "@types/chrome": "0.0.258",
    "@types/node":   "20.11.5",
    "@types/react":  "18.2.48",
    "typescript":    "5.3.3"
  },
  "manifest": {
    "permissions": ["storage", "activeTab", "scripting"],
    "host_permissions": ["<all_urls>"]
  }
}
```

## popup.tsx

Purely UI. Reads cached state via `useStorage`, sends messages to background for every API call. Never sees the platform key.

```tsx
import { useState } from "react"
import { useStorage } from "@plasmohq/storage/hook"
import { sendToBackground } from "@plasmohq/messaging"

type SessionSummary = { id: string; prompt: string; status: string }

function Popup() {
  const [recent] = useStorage<SessionSummary[]>("recent-sessions", [])
  const [apiKey] = useStorage<string>("platform-key", "")
  const [prompt, setPrompt] = useState("")
  const [busy, setBusy] = useState(false)

  const go = async () => {
    if (!prompt.trim() || !apiKey) return
    setBusy(true)
    const session = await sendToBackground({
      name: "create-session",
      body: { prompt, tab_url: await getActiveTabUrl() },
    })
    setBusy(false)
    setPrompt("")
    chrome.tabs.create({ url: session.urls.editor })
  }

  return (
    <div style={{ width: 360, padding: 16, fontFamily: "system-ui" }}>
      <h3 style={{ margin: "0 0 12px" }}>Agent</h3>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="what should the agent do on this page?"
        style={{ width: "100%", minHeight: 80, padding: 8 }}
      />
      <button onClick={go} disabled={busy} style={{ marginTop: 8, width: "100%" }}>
        {busy ? "starting…" : "run"}
      </button>
      <h4 style={{ margin: "16px 0 8px" }}>Recent</h4>
      <ul style={{ listStyle: "none", padding: 0, margin: 0, fontSize: 12 }}>
        {recent.map((s) => (
          <li key={s.id} style={{ padding: "6px 0", borderTop: "1px solid #eee" }}>
            <code>{s.id}</code> · {s.status}<br />
            <span style={{ color: "#666" }}>{s.prompt}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

async function getActiveTabUrl(): Promise<string> {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
  return tab?.url ?? ""
}

export default Popup
```

## background.ts

Only file that talks to the API. One `listen()` handler; each case maps to an SDK call.

```ts
import { listen } from "@plasmohq/messaging/message"
import { Storage } from "@plasmohq/storage"
import { AgentClient } from "~lib/agent-client"

const storage = new Storage()

async function getClient(): Promise<AgentClient> {
  const apiKey = await storage.get<string>("platform-key")
  const orgId  = await storage.get<string>("org-id")
  if (!apiKey || !orgId) throw new Error("not-configured")
  return new AgentClient({ apiKey, orgId })
}

listen(async (req, res) => {
  switch (req.name) {
    case "create-session": {
      const client = await getClient()
      const session = await client.sessions.create({
        workspace_id: await storage.get("default-workspace"),
        prompt: req.body.prompt,
        metadata: {
          origin: "chrome-extension",
          source_url: req.body.tab_url,
          selector:   req.body.selector,
          outer_html: req.body.outer_html,
        },
      })

      const recent = (await storage.get<any[]>("recent-sessions")) ?? []
      await storage.set("recent-sessions", [
        { id: session.id, prompt: req.body.prompt, status: session.status },
        ...recent.slice(0, 19),
      ])

      res.send(session)
      return
    }

    case "cancel-session": {
      const client = await getClient()
      res.send(await client.sessions.cancel(req.body.id))
      return
    }

    default:
      res.send({ error: `unknown message: ${req.name}` })
  }
})
```

## contents/picker.tsx — the Ramp pattern

`Alt+Shift+A` arms the picker. Click any element, describe the change, and the session starts with the element's CSS path + outer HTML attached as metadata — so the agent has real DOM context, not just a prompt.

```tsx
import type { PlasmoCSConfig } from "plasmo"
import { useEffect, useState } from "react"
import { sendToBackground } from "@plasmohq/messaging"

export const config: PlasmoCSConfig = {
  matches: ["<all_urls>"],
  run_at:  "document_idle",
}

export const getOverlayAnchor = async () => document.body

type Target = { selector: string; outerHTML: string }

function Picker() {
  const [armed,  setArmed]  = useState(false)
  const [target, setTarget] = useState<Target | null>(null)
  const [prompt, setPrompt] = useState("")

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.altKey && e.shiftKey && e.code === "KeyA") setArmed((v) => !v)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  useEffect(() => {
    if (!armed) return
    const onClick = (e: MouseEvent) => {
      e.preventDefault(); e.stopPropagation()
      const el = e.target as HTMLElement
      setTarget({
        selector:  cssPath(el),
        outerHTML: el.outerHTML.slice(0, 4000),
      })
      setArmed(false)
    }
    document.addEventListener("click", onClick, true)
    return () => document.removeEventListener("click", onClick, true)
  }, [armed])

  const run = async () => {
    if (!target || !prompt.trim()) return
    await sendToBackground({
      name: "create-session",
      body: {
        prompt,
        tab_url:    location.href,
        selector:   target.selector,
        outer_html: target.outerHTML,
      },
    })
    setTarget(null); setPrompt("")
  }

  return (
    <>
      {armed && <div style={overlayStyle}>click an element · esc to cancel</div>}
      {target && (
        <div style={panelStyle}>
          <code style={{ fontSize: 11, color: "#888" }}>{target.selector}</code>
          <textarea
            autoFocus
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="describe the change you want"
            style={{ width: "100%", minHeight: 72, margin: "8px 0" }}
          />
          <button onClick={run}>dispatch</button>
          <button onClick={() => setTarget(null)} style={{ marginLeft: 8 }}>cancel</button>
        </div>
      )}
    </>
  )
}

function cssPath(el: Element): string {
  const parts: string[] = []
  let cur: Element | null = el
  while (cur && cur.nodeType === 1 && parts.length < 6) {
    let p = cur.tagName.toLowerCase()
    if (cur.id) { p += `#${cur.id}`; parts.unshift(p); break }
    const siblings = Array.from(cur.parentElement?.children ?? [])
      .filter((n) => n.tagName === cur!.tagName)
    if (siblings.length > 1) p += `:nth-of-type(${siblings.indexOf(cur) + 1})`
    parts.unshift(p)
    cur = cur.parentElement
  }
  return parts.join(" > ")
}

const overlayStyle: React.CSSProperties = {
  position: "fixed", top: 16, left: "50%", transform: "translateX(-50%)",
  zIndex: 2147483647, padding: "8px 16px", background: "#111", color: "#fff",
  borderRadius: 4, fontFamily: "system-ui", fontSize: 13,
}

const panelStyle: React.CSSProperties = {
  position: "fixed", bottom: 24, right: 24, width: 340, padding: 16,
  background: "#fff", border: "1px solid #ddd", borderRadius: 8,
  boxShadow: "0 8px 32px rgba(0,0,0,0.15)", zIndex: 2147483647,
  fontFamily: "system-ui", fontSize: 13,
}

export default Picker
```

## lib/agent-client.ts

Minimal SDK wrapper — for a real extension you'd swap this for the `@yourorg/agent-sdk` package.

```ts
type Opts = { apiKey: string; orgId: string; baseUrl?: string }

export class AgentClient {
  private base: string
  constructor(private opts: Opts) {
    this.base = opts.baseUrl ?? "https://api.example.com/v1"
  }

  sessions = {
    create: (body: any) =>
      this.call("POST", `/organizations/${this.opts.orgId}/sessions`, body),
    cancel: (id: string) =>
      this.call("POST", `/organizations/${this.opts.orgId}/sessions/${id}/cancel`),
    get: (id: string) =>
      this.call("GET", `/organizations/${this.opts.orgId}/sessions/${id}`),
  }

  private async call(method: string, path: string, body?: any) {
    const r = await fetch(`${this.base}${path}`, {
      method,
      headers: {
        "Authorization":     `Bearer ${this.opts.apiKey}`,
        "X-Organization-Id": this.opts.orgId,
        "Content-Type":      "application/json",
      },
      body: body ? JSON.stringify(body) : undefined,
    })
    if (!r.ok) throw new Error(await r.text())
    return r.json()
  }
}
```

## Running it

1. `pnpm create plasmo agent-browser` — then replace generated files with these.
2. `pnpm dev` — Plasmo builds into `build/chrome-mv3-dev`.
3. Chrome → `chrome://extensions` → "Load unpacked" → point at that directory.
4. Open the popup, paste platform API key + org id into settings, then `Alt+Shift+A` on any page.
