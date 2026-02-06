# macOS Memory Audit — Feb 5, 2026

System was nearly unresponsive. This documents what was found and what was done.

## System State (Before Cleanup)

| Metric | Value | Severity |
|--------|-------|----------|
| Total RAM | 24 GB | — |
| RAM used | 23 GB | Critical |
| RAM free | 212 MB | Critical |
| Swap used | 32 GB / 34 GB | Critical |
| Compressor | 10 GB | High |
| Load average | 40.58 | Critical |
| Processes | 786 | High |
| Threads | 7,691 | High |
| Swap-ins (cumulative) | 143M | Extreme thrash |
| Swap-outs (cumulative) | 159M | Extreme thrash |

The system was spending most of its CPU time on memory management (swap I/O and compression) rather than actual work.

---

## Top Memory Offenders

### 1. Next.js Dev Server (PID 22485) — 2.8 GB RSS / 11 GB virtual

- Running `next-server v16.1.6` from `landing-pages/` directory
- **Was idle** — not being actively used
- Next.js dev servers balloon over time due to HMR (Hot Module Replacement) caching
- This single process was the largest contributor to swap pressure

**Fix:** `kill 22485` — freed ~2.8 GB immediately.

**Prevention:** Don't leave `pnpm dev` / `next dev` running in background terminals. Kill dev servers when switching projects.

### 2. Brave Browser — 37 processes, ~2.2 GB RSS total

Even with "one tab open," Brave spawns many processes:

| Process Type | Count | Total RAM | Notes |
|---|---|---|---|
| Main browser | 1 | 459 MB | Core Brave process |
| Extension renderers | 6 | ~640 MB | Each extension gets its own process |
| Tab renderers | 7 | ~860 MB | Page content (includes cached closed tabs) |
| GPU process | 1 | 118 MB | Graphics compositing |
| Network service | 1 | 110 MB | All HTTP/WebSocket I/O |
| Storage service | 1 | 23 MB | IndexedDB, localStorage |
| Audio service | 1 | 19 MB | Media playback |
| Video capture | 1 | 22 MB | Camera/screen sharing |
| Crash handler | 1 | 3 MB | Crash reporting |

**Key insight:** 6 extension processes (~640 MB) is the biggest hidden cost. Each installed extension runs in its own sandboxed renderer even when idle.

**Fix:** Closed 36 tabs. Freed ~1.5 GB.

**Prevention:**
- Audit extensions at `brave://extensions/` — disable ones not needed constantly
- Disable "Continue running background apps" at `brave://settings/system`
- Use `brave://discards` to check tab lifecycle
- Consider a tab suspender extension (ironic, but net-positive if it replaces 5+ tabs)

### 3. Apple Virtualization (PID 2071) — 1.9 GB RSS

A macOS virtualization process (likely Docker Desktop's underlying VM). Always resident when Docker is running.

**Prevention:** Quit Docker Desktop when not actively using containers. The `com.docker.vmnetd` helper stays resident but the VM itself can be stopped.

### 4. Warp Terminal (PID 6185) — 1.5 GB RSS

The `stable` binary is Warp's main process. 1.5 GB is high for a terminal emulator — Warp uses a GPU-accelerated Rust renderer plus AI features that keep models/state in memory.

**No immediate fix.** This is Warp's baseline. Consider iTerm2 or Alacritty if memory pressure is chronic (~50-100 MB for similar functionality).

### 5. Node.js Processes — 91 total, ~1 GB RSS combined

Mostly Claude Code subagent processes and MCP servers. Each one is ~120-140 MB. These come and go with Claude Code sessions.

**Prevention:** Exit Claude Code sessions when not using them. Each active session maintains multiple node processes for MCP servers.

### 6. Paste App (PID 985) — 618 MB

Clipboard history manager holding extensive history in memory.

**Prevention:** Reduce clipboard history retention in Paste settings, or switch to a lighter clipboard manager.

---

## Login Items & Launch Agents

### Login Items (start at every boot)

- NordVPN
- Notion
- Rectangle Pro
- Wispr Flow
- Raycast
- Bartender
- Paste
- Claude
- VoiceInk

**Candidates for on-demand launch (not needed at startup):**
- VoiceInk — launch when needed for voice input
- Wispr Flow — launch when needed
- Notion — opens fast enough on demand

### Launch Agents (background services)

| Agent | Purpose | Always needed? |
|-------|---------|----------------|
| `com.cognee.mcp-sse.plist` | Cognee MCP server | Only during dev sessions |
| `com.contextportal.server.plist` | Context Portal MCP | Only during dev sessions |
| `com.obsidian.autolink.plist` | Obsidian auto-linking | Only if using Obsidian |
| `com.openai.atlas.update-helper.plist` | OpenAI updater | Can disable |
| `com.setapp.DesktopClient.*` (4 agents) | Setapp management | Only 1 needed if using Setapp |
| `homebrew.mxcl.postgresql@16.plist` | PostgreSQL 16 | Only during dev |

**To disable a launch agent:**
```bash
launchctl unload ~/Library/LaunchAgents/com.cognee.mcp-sse.plist
```

**To re-enable:**
```bash
launchctl load ~/Library/LaunchAgents/com.cognee.mcp-sse.plist
```

---

## After Cleanup

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| RAM free | 212 MB | 2.85 GB | +13x |
| Compressor | 10 GB | 3.4 GB | -66% |
| Load average | 40.58 | 11.31 | -72% |
| Swap used | 32 GB | 22 GB | -10 GB |
| CPU idle | 37% | 60% | +62% |
| Stuck processes | 12 | 0 | Clean |

Swap will continue draining over time as the OS pulls pages back into real RAM.

---

## Future: Rust Resource Monitor Daemon

Idea for a lightweight LaunchAgent daemon written in Rust:

- **Memory pressure monitoring** — Watch `vm_stat` / Mach APIs for pressure events
- **Process profiling** — Track per-process RSS over time, flag runaways
- **Idle detection** — Alert on processes consuming memory with zero CPU for N minutes
- **Swap alerts** — Notify when swap crosses thresholds with top offender list
- **Tab counting** — Monitor browser process count and warn at thresholds

Would use `sysinfo` crate for process enumeration, `mac-notification-sys` for alerts, polling every 30-60s with near-zero overhead. Installed as a LaunchAgent for boot-time startup.
