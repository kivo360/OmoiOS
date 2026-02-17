# 14 Settings, Personalization & Activity

**Part of**: [User Journey Documentation](./README.md)

---

## Overview

Beyond the basic settings (profile, API keys, sessions), OmoiOS provides expanded settings for appearance customization, notification management, security hardening, integration connections, and a real-time activity timeline for monitoring all system events.

---

## 14.1 Appearance Customization

```
User navigates to /settings → Appearance:
   ↓
┌─────────────────────────────────────────────────────────────┐
│  Appearance Settings                                         │
│  Customize the look and feel of your workspace               │
│                                                              │
│  Theme:    [☀ Light] [🌙 Dark] [🖥 System]                  │
│  Accent:   ● Blue  ● Purple  ● Green  ● Orange  ● Pink     │
│  Font:     [──●──] 14px    Code: [JetBrains Mono ▼]        │
│  Sidebar:  [Left ▼]   Compact: [off]   Animations: [on]    │
│  A11y:     High Contrast: [off]                              │
│  Editor:   Line Numbers: [on]    Word Wrap: [on]            │
│                                                              │
│                     [Reset to Defaults] [Save Changes]       │
└─────────────────────────────────────────────────────────────┘

All settings persist to localStorage (client-side only).
No API calls — instant feedback.
```

### Available Customizations

| Category | Options |
|----------|---------|
| Theme | Light, Dark, System (auto-detect) |
| Accent Color | Blue, Purple, Green, Orange, Pink, Red |
| Font Size | 12px - 20px slider |
| Code Font | JetBrains Mono, Fira Code, Source Code Pro, Monaco, Consolas |
| Sidebar | Left or Right position |
| Compact Mode | Toggle for reduced spacing |
| Animations | Toggle transitions and animations |
| High Contrast | Accessibility mode |
| Line Numbers | Show/hide in code blocks |
| Word Wrap | Wrap long lines in code |

---

## 14.2 Notification Configuration

```
User navigates to /settings → Notifications:
   ↓
Configure per-event notification channels:
   ↓
                              In-App   Email   Slack
Agent Completions              [●]      [●]     [●]
Agent Errors                   [●]      [●]     [●]
Agent Spawned                  [●]      [○]     [○]
Phase Transitions              [●]      [○]     [●]
Gate Approval Required         [●]      [●]     [●]
Pull Request Created           [●]      [●]     [●]
Mentions & Comments            [●]      [●]     [○]

Bulk: [Enable All In-App] [Enable All Email] [Disable All Email]

Email Digest: [Daily ▼] — Sent at 9:00 AM your timezone
Quiet Hours: [off] Start: [22:00] End: [08:00]
Slack: [Not connected] [Connect Slack]

[Save Preferences]
```

### Key Behaviors

- **Per-event granularity**: Each notification type can be toggled independently across 3 channels
- **Bulk actions**: Quick enable/disable for entire channels
- **Email digest**: Configurable frequency (real-time, hourly, daily, weekly, never)
- **Quiet hours**: Pause notifications during specified time window
- **Slack integration**: Connect workspace for Slack channel delivery
- **Storage**: Persisted to localStorage (backend notification API planned)

---

## 14.3 Security Management

```
User navigates to /settings → Security:
   ↓
┌─────────────────────────────────────────────────────────────┐
│  Change Password                                             │
│  Current: [________]  New: [________]  Confirm: [________]  │
│                                        [Update Password]    │
│                                                              │
│  Two-Factor Authentication                                   │
│  🛡 2FA is disabled                             [toggle]    │
│                                                              │
│  Authentication                                              │
│  ℹ JWT-Based (access: 15min, refresh: 7 days)               │
│  🔑 API Keys                            [Manage Keys →]    │
│  📤 Sign out everywhere                 [Sign Out]          │
│                                                              │
│  ⚠ Danger Zone                                               │
│  Delete Account — permanent              [🗑 Delete Account] │
└─────────────────────────────────────────────────────────────┘
```

### Security Actions

| Action | Flow |
|--------|------|
| Change password | Enter current + new + confirm → POST /auth/change-password |
| Enable 2FA | Toggle switch (placeholder — backend integration pending) |
| Manage API keys | Navigate to /settings/api-keys |
| Sign out | Confirmation dialog → Clear all tokens → Redirect to /login |
| Delete account | Destructive confirmation dialog → Account deletion |

---

## 14.4 Integration Management

```
User navigates to /settings → Integrations:
   ↓
┌─────────────────────────────────────────────────────────────┐
│  Integrations                                                │
│  Connect third-party services to enhance your workflow       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  🐙 GitHub                  Connected as @kivo360   │   │
│  │                              [Disconnect]            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

Actions:
- View connected accounts (GitHub, etc.)
- Connect new service → OAuth flow → /callback
- Disconnect existing connection
```

---

## 14.5 Activity Timeline

```
User navigates to /activity (from sidebar or notification link):
   ↓
┌─────────────────────────────────────────────────────────────┐
│  Activity Timeline               🟢 Connected [42 events]   │
│  Real-time feed of all system activity     [● Live] [↻]    │
│                                                              │
│  Filters:                                                    │
│  🔍 [Search...]  Type: [All ▼]  [All|Agents|You|System]    │
│  Project: [All ▼]                                           │
│                                                              │
│  Today                                                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  🤖 agent_a5c2  Modified stripe.ts (+45 -3)  2m ago │   │
│  │  [FileChangeCard with diff preview]                  │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ⚡ System  AGENT_REGISTERED type: code_gen   5m ago │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Yesterday                                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ...older events                                     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Activity Timeline Features

| Feature | Description |
|---------|-------------|
| Real-time updates | WebSocket connection shows events as they happen |
| Live/Paused toggle | Start/stop receiving new events |
| Search | Filter events by title or description text |
| Type filter | Commits, Decisions, Comments, Completions, Errors, PRs, Discoveries, Blocking, Status Changes, File Edits |
| Actor filter | All, Agents, You, System |
| Project filter | All Projects, System Events, or specific project |
| Date grouping | Events grouped by Today, Yesterday, Earlier |
| Sandbox scope | `?sandbox_id=:id` filters to specific sandbox events |
| Event linking | Click event card to navigate to source (ticket, agent, task) |
| File diffs | File edit events render inline FileChangeCard with diff preview |
| Connection state | Visual indicator: Connecting (yellow), Connected (green), Disconnected (red) |
| Max events | Buffer capped at 100 events for performance |

### Use Cases

1. **During execution**: Monitor sandbox progress via `/activity?sandbox_id=:id`
2. **After execution**: Review what happened across all agents and tasks
3. **Debugging**: Filter by error events to find what went wrong
4. **Team awareness**: See all system activity in one real-time feed
5. **Status checks**: Quick glance at agent spawns, completions, and failures

---

## Settings Navigation Overview

```
/settings (Settings Hub)
    │
    ├── /settings/profile          — Name, email, avatar
    ├── /settings/appearance       — Theme, colors, fonts, layout
    ├── /settings/integrations     — GitHub OAuth connections
    ├── /settings/notifications    — Per-event channels, digest, quiet hours
    ├── /settings/security         — Password, 2FA, sessions, account deletion
    ├── /settings/api-keys         — Programmatic access key management
    └── /settings/sessions         — Active session management

/activity                          — Real-time system event feed
/activity?sandbox_id=:id           — Sandbox-scoped event feed
```

---

**Related**: See [page_flows/15_settings_expanded.md](../page_flows/15_settings_expanded.md) and [page_flows/17_activity_timeline.md](../page_flows/17_activity_timeline.md) for detailed page-level flow documentation.
