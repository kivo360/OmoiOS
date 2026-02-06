# Memory Management Strategy

Strategies for keeping a 24 GB Mac healthy under heavy dev workloads — multiple Claude Code sessions, Brave, Docker, voice input tools, and Next.js dev servers.

## Constraints

These apps are **always needed** and cannot be killed/suspended:
- **VoiceInk** — voice-to-text input, used constantly
- **Wispr Flow** — voice coding, used during development sessions
- **Raycast** — launcher/productivity, low memory (~30-50 MB)
- **Rectangle Pro** — window management, low memory (~15 MB)

These are **dev-session tools** that should only run when actively developing:
- Claude Code (+ MCP servers, node subagents)
- Docker Desktop (Virtualization VM)
- Next.js / Vite dev servers
- PostgreSQL

---

## Strategy 1: Process Policies (Manual, No Tooling)

Rules to follow without any automation.

### Kill Dev Servers When Switching Projects

Next.js dev servers leak memory over time via HMR caching. A server left running overnight can balloon from 200 MB to 2-11 GB.

```bash
# Find and kill all next-server processes
pkill -f "next-server"

# Find and kill all vite dev servers
pkill -f "vite"
```

**Rule:** Before switching projects or taking a break, kill dev servers in all terminals.

### Browser Tab Discipline

Each Brave tab = ~80-200 MB. Each extension = ~100-160 MB in its own process.

- Keep tabs under 10 during dev sessions
- Use bookmarks or Raycast notes instead of "I'll read this later" tabs
- Audit extensions quarterly — each one costs ~100 MB permanently

### Docker: Stop When Not Needed

Docker Desktop's VM reserves 1.9+ GB even when idle.

```bash
# Stop all containers and quit Docker
docker stop $(docker ps -q) 2>/dev/null
osascript -e 'quit app "Docker"'

# Restart when needed
open -a Docker
```

### PostgreSQL: On-Demand

If PostgreSQL runs via LaunchAgent, it's always on (~50-100 MB + shared buffers).

```bash
# Stop
launchctl unload ~/Library/LaunchAgents/homebrew.mxcl.postgresql@16.plist

# Start
launchctl load ~/Library/LaunchAgents/homebrew.mxcl.postgresql@16.plist
```

---

## Strategy 2: Shell Aliases & Functions (Lightweight Automation)

Add to `~/.zshrc` for quick memory management without a daemon.

### Memory Status Check

```bash
# Quick memory overview
memcheck() {
    echo "=== Memory ==="
    top -l 1 -n 0 | grep PhysMem
    echo ""
    echo "=== Swap ==="
    sysctl vm.swapusage
    echo ""
    echo "=== Top 5 by Memory ==="
    ps aux --sort=-%mem | head -6 | awk '{printf "%-8s %6dMB  %s\n", $2, $6/1024, $11}'
}
```

### Kill Idle Dev Servers

```bash
# Kill all dev servers (next, vite, webpack)
killdevs() {
    pkill -f "next-server" 2>/dev/null && echo "Killed Next.js servers"
    pkill -f "vite" 2>/dev/null && echo "Killed Vite servers"
    pkill -f "webpack-dev-server" 2>/dev/null && echo "Killed Webpack servers"
    echo "Done"
}
```

### Dev Session Start/Stop

```bash
# Start a full dev session
devstart() {
    launchctl load ~/Library/LaunchAgents/homebrew.mxcl.postgresql@16.plist 2>/dev/null
    open -a Docker
    echo "PostgreSQL and Docker starting..."
}

# End a dev session — clean up everything
devstop() {
    pkill -f "next-server" 2>/dev/null
    pkill -f "vite" 2>/dev/null
    docker stop $(docker ps -q) 2>/dev/null
    osascript -e 'quit app "Docker"' 2>/dev/null
    launchctl unload ~/Library/LaunchAgents/homebrew.mxcl.postgresql@16.plist 2>/dev/null
    echo "Dev services stopped. Freed resources."
}
```

---

## Strategy 3: Rust Resource Monitor Daemon

A lightweight background daemon that watches memory pressure and takes action without interrupting workflow.

### Design Principles

1. **Never kill voice tools** — VoiceInk and Wispr Flow are always protected
2. **Never interrupt focus** — No modal dialogs. Use macOS notifications only.
3. **Graduated response** — Warn first, suggest actions, only auto-act on safe targets
4. **Near-zero overhead** — Poll every 30-60s, <5 MB resident memory

### Architecture

```
┌──────────────────────────────────────────────┐
│           Resource Monitor Daemon             │
│                                               │
│  ┌─────────┐  ┌──────────┐  ┌─────────────┐ │
│  │ Sampler  │  │ Analyzer │  │  Responder  │ │
│  │ (30s)   │→│ (rules)  │→│ (actions)   │ │
│  └─────────┘  └──────────┘  └─────────────┘ │
│                                               │
│  Protected: VoiceInk, Wispr Flow, Raycast,   │
│             Rectangle Pro, WindowServer       │
└──────────────────────────────────────────────┘
         │
         ▼
    macOS Notifications
    (non-blocking)
```

### Sampler (every 30s)

Collects via `sysinfo` crate + `sysctl`:
- Total / free / compressed / wired memory
- Swap used / total
- Per-process RSS for top 20 processes
- Memory pressure level (normal / warn / critical)

### Analyzer (rule engine)

```
LEVEL 1 — Normal (free > 2 GB, swap < 10 GB)
  → Do nothing. Log metrics for trending.

LEVEL 2 — Elevated (free < 2 GB OR swap > 15 GB)
  → Notification: "Memory getting tight. Top consumers: [list]"
  → Scan for idle dev servers (next-server, vite with 0% CPU for 5+ min)

LEVEL 3 — High (free < 1 GB OR swap > 25 GB)
  → Notification: "Memory pressure high. Suggest closing [X]."
  → Auto-kill: idle dev servers (0% CPU for 10+ min)
  → Auto-kill: orphaned node processes with no parent terminal
  → Suggest: Docker stop, close browser tabs

LEVEL 4 — Critical (free < 500 MB AND swap > 30 GB)
  → Urgent notification with top 5 offenders
  → Auto-kill: all dev servers regardless of CPU
  → Auto-kill: orphaned node processes
  → Suggest: restart Brave (frees all tab/extension memory)
```

### Protected Process List (never touched)

```toml
# config.toml
[protected]
processes = [
    "VoiceInk",
    "Wispr Flow",
    "Raycast",
    "Rectangle Pro",
    "WindowServer",
    "Finder",
    "Dock",
    "Bartender",
    "loginwindow",
]
```

### Safe Auto-Kill Targets

These are always safe to kill without data loss:

| Target | Pattern | Condition |
|--------|---------|-----------|
| Next.js dev servers | `next-server` | 0% CPU for 10+ min |
| Vite dev servers | `vite` | 0% CPU for 10+ min |
| Orphaned node processes | `node` with no parent TTY | Always |
| Webpack dev servers | `webpack-dev-server` | 0% CPU for 10+ min |

### Notification Style

macOS native notifications via `mac-notification-sys` crate:

```
┌─────────────────────────────────────────┐
│ 🔶 Memory Pressure: Elevated           │
│                                         │
│ Free: 1.2 GB | Swap: 18 GB             │
│ Top: next-server (2.8 GB, idle 45 min) │
│       Brave (2.1 GB, 34 tabs)          │
│                                         │
│ Killed 1 idle dev server. Freed 2.8 GB │
└─────────────────────────────────────────┘
```

No sound. No modal. Just a banner that slides away.

### Rust Crate Dependencies

```toml
[dependencies]
sysinfo = "0.31"              # Process enumeration, CPU/memory stats
mac-notification-sys = "0.6"  # macOS native notifications
serde = { version = "1", features = ["derive"] }
toml = "0.8"                  # Config file parsing
log = "0.4"
env_logger = "0.11"
tokio = { version = "1", features = ["rt", "time", "macros"] }
```

### LaunchAgent Installation

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.kevinhill.resmgr</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/resmgr</string>
        <string>--config</string>
        <string>~/.config/resmgr/config.toml</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/resmgr.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/resmgr.err</string>
    <key>ProcessType</key>
    <string>Background</string>
    <key>LowPriorityBackgroundIO</key>
    <true/>
    <key>Nice</key>
    <integer>10</integer>
</dict>
</plist>
```

Key settings:
- `ProcessType: Background` — macOS gives it lowest scheduling priority
- `LowPriorityBackgroundIO: true` — won't compete for disk I/O
- `Nice: 10` — low CPU priority so it never impacts voice tools or active work

### Config File (~/.config/resmgr/config.toml)

```toml
[general]
poll_interval_seconds = 30
log_level = "info"

[thresholds]
elevated_free_gb = 2.0
elevated_swap_gb = 15.0
high_free_gb = 1.0
high_swap_gb = 25.0
critical_free_gb = 0.5
critical_swap_gb = 30.0

[auto_kill]
idle_dev_server_minutes = 10
orphan_node_always = true

[protected]
processes = [
    "VoiceInk",
    "Wispr Flow",
    "Raycast",
    "Rectangle Pro",
    "WindowServer",
    "Finder",
    "Dock",
    "Bartender",
    "loginwindow",
    "NordVPN",
]

[safe_kill_patterns]
dev_servers = ["next-server", "vite", "webpack-dev-server"]
orphans = ["node"]
```

---

## Recommended Implementation Order

1. **Now:** Add shell aliases (`memcheck`, `killdevs`, `devstop`) to `~/.zshrc` — immediate value, zero risk
2. **Next:** Build the Rust daemon with just the sampler + notifications (Level 1-2 only) — proves the concept
3. **Then:** Add auto-kill for idle dev servers (Level 3) — the biggest recurring offender
4. **Later:** Add trending/history so you can see patterns over time (e.g., "swap peaks every day at 3 PM")

---

## Expected Impact

| Scenario | Without Management | With Management |
|----------|-------------------|-----------------|
| Idle Next.js server overnight | 2-11 GB wasted | Auto-killed after 10 min idle |
| 30+ Brave tabs accumulated | 2+ GB + swap thrash | Notified at 15 tabs |
| Docker left running after `devstop` | 1.9 GB reserved | Stopped with session |
| Swap exceeds 25 GB | System grinds to halt | Notified + auto-cleanup |
| Free RAM below 1 GB | Everything swaps | Graduated response kicks in |
