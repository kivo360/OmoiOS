# Settings (Expanded)

**Part of**: [Page Flow Documentation](./README.md)

---

## Overview

The Settings section provides user-level configuration across multiple domains: profile, appearance, integrations, notifications, security, API keys, and sessions. These pages extend the base settings documented in [05_organizations_api.md](./05_organizations_api.md).

---

## Flow 57: Appearance Settings

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /settings/appearance                                 │
│                                                             │
│  ← Back to Settings                                         │
│                                                             │
│  Appearance Settings                                        │
│  Customize the look and feel of your workspace              │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Theme                                                 │ │
│  │  Choose your preferred color scheme                    │ │
│  │                                                        │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │ │
│  │  │  ☀ Light │  │  🌙 Dark │  │  🖥 System│            │ │
│  │  └──────────┘  └──────────┘  └──────────┘            │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Accent Color                                          │ │
│  │  ● Blue  ● Purple  ● Green  ● Orange  ● Pink  ● Red  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Typography                                            │ │
│  │  Font Size: [──●────────] 14px                         │ │
│  │  Code Font: [JetBrains Mono ▼]                         │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Layout                                                │ │
│  │  Sidebar Position: [Left ▼]                            │ │
│  │  Compact Mode:     [  ○  ]                             │ │
│  │  Animations:       [  ●  ]                             │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Accessibility                                         │ │
│  │  High Contrast Mode: [  ○  ]                           │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Editor Preferences                                    │ │
│  │  Show Line Numbers: [  ●  ]                            │ │
│  │  Word Wrap:         [  ●  ]                            │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│                     [Reset to Defaults] [Save Changes]      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Route
`/settings/appearance`

### Purpose
Customize the visual appearance and editor behavior of the application.

### User Actions
- **Select theme**: Light, Dark, or System (auto-detect)
- **Choose accent color**: Blue, Purple, Green, Orange, Pink, Red
- **Adjust font size**: Slider from 12px to 20px
- **Select code font**: JetBrains Mono, Fira Code, Source Code Pro, Monaco, Consolas
- **Set sidebar position**: Left or Right
- **Toggle compact mode**: Reduce spacing for density
- **Toggle animations**: Enable/disable UI transitions
- **Toggle high contrast**: Increase contrast for accessibility
- **Toggle line numbers**: Show/hide in code blocks
- **Toggle word wrap**: Wrap long lines in code blocks
- **Save changes**: Persist to localStorage
- **Reset to defaults**: Reload page to reset

### Storage
All settings persisted to `localStorage` under key `appearance-settings`.

---

## Flow 58: Integrations Settings

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /settings/integrations                               │
│                                                             │
│  ← Back to Settings                                         │
│                                                             │
│  Integrations                                               │
│  Connect third-party services to enhance your workflow      │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Connected Accounts                                    │ │
│  │                                                        │ │
│  │  ┌──────────────────────────────────────────────────┐ │ │
│  │  │  🐙 GitHub              Connected as @kivo360   │ │ │
│  │  │                         [Disconnect]             │ │ │
│  │  └──────────────────────────────────────────────────┘ │ │
│  │                                                        │ │
│  │  ┌──────────────────────────────────────────────────┐ │ │
│  │  │  🔗 Other Integrations      [Connect]           │ │ │
│  │  └──────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Route
`/settings/integrations`

### Purpose
Manage connected third-party accounts (GitHub OAuth, etc.).

### User Actions
- **View connected accounts**: See which services are linked
- **Connect account**: Initiate OAuth flow for new connections
- **Disconnect account**: Remove linked account

### Components
- `IntegrationsSettingsPage` — Wrapper page
- `ConnectedAccounts` — Shared component showing OAuth connections

---

## Flow 59: Notification Settings

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /settings/notifications                              │
│                                                             │
│  ← Back to Settings                                         │
│                                                             │
│  Notification Settings                                      │
│  Configure how you receive notifications                    │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Notification Preferences          In-App Email Slack  │ │
│  │                                                        │ │
│  │  ✓ Agent Completions                [●]   [●]   [●]  │ │
│  │    When an agent completes a task                      │ │
│  │                                                        │ │
│  │  ✗ Agent Errors                     [●]   [●]   [●]  │ │
│  │    When an agent encounters an error                   │ │
│  │                                                        │ │
│  │  🤖 Agent Spawned                   [●]   [○]   [○]  │ │
│  │    When new agents are spawned                         │ │
│  │                                                        │ │
│  │  ⚡ Phase Transitions               [●]   [○]   [●]  │ │
│  │    When tickets move between phases                    │ │
│  │                                                        │ │
│  │  🛡 Gate Approval Required          [●]   [●]   [●]  │ │
│  │    When a phase gate requires approval                 │ │
│  │                                                        │ │
│  │  🔀 Pull Request Created            [●]   [●]   [●]  │ │
│  │    When agents create pull requests                    │ │
│  │                                                        │ │
│  │  💬 Mentions & Comments             [●]   [●]   [○]  │ │
│  │    When someone mentions you                           │ │
│  │                                                        │ │
│  │  Bulk: [Enable All In-App] [Enable All Email]          │ │
│  │        [Disable All Email]                             │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Email Digest                                          │ │
│  │  Frequency: [Daily ▼]                                  │ │
│  │  Daily digest sent at 9:00 AM in your timezone         │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Quiet Hours                                           │ │
│  │  Enable: [  ○  ]                                       │ │
│  │  Start: [22:00 ▼]  End: [08:00 ▼]                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Slack Integration                                     │ │
│  │  🟪 Slack Workspace     Not connected  [Connect Slack] │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│                                      [Save Preferences]    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Route
`/settings/notifications`

### Purpose
Configure notification delivery channels and timing preferences.

### User Actions
- **Toggle per-event channels**: Enable/disable In-App, Email, Slack per notification type
- **Bulk enable/disable**: One-click enable/disable all notifications for a channel
- **Set digest frequency**: Real-time, Hourly, Daily, Weekly, Never
- **Configure quiet hours**: Enable quiet period with start/end time
- **Connect Slack**: Link Slack workspace for notifications

### Notification Types
| Type | Description |
|------|-------------|
| Agent Completions | Agent successfully completes a task |
| Agent Errors | Agent encounters an error |
| Agent Spawned | New agents spawned |
| Phase Transitions | Tickets move between phases |
| Gate Approval Required | Phase gate needs approval |
| Pull Request Created | Agents create PRs |
| Mentions & Comments | Someone mentions you |

### Storage
Persisted to `localStorage` under key `notification-preferences`.

---

## Flow 60: Security Settings

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /settings/security                                   │
│                                                             │
│  ← Back to Settings                                         │
│                                                             │
│  Security Settings                                          │
│  Manage your account security and active sessions           │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Change Password                                       │ │
│  │                                                        │ │
│  │  Current Password: [________] 👁                       │ │
│  │  New Password:     [________] 👁                       │ │
│  │  Confirm Password: [________]                          │ │
│  │                                                        │ │
│  │                              [Update Password]         │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Two-Factor Authentication                             │ │
│  │  🛡 2FA is disabled          [  ○  ]                   │ │
│  │  Protect your account with a secondary method          │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Authentication                                        │ │
│  │  ℹ JWT-Based Authentication                            │ │
│  │    Access tokens: 15 min | Refresh tokens: 7 days      │ │
│  │                                                        │ │
│  │  🔑 API Keys                    [Manage Keys →]        │ │
│  │  📤 Sign out everywhere         [Sign Out]             │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ⚠ Danger Zone                                         │ │
│  │  Delete Account                                        │ │
│  │  Permanently delete your account and data              │ │
│  │                                [🗑 Delete Account]     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Route
`/settings/security`

### Purpose
Account security management: password changes, 2FA, session management, account deletion.

### User Actions
- **Change password**: Enter current + new password with confirmation, show/hide toggles
- **Toggle 2FA**: Enable/disable two-factor authentication
- **View auth info**: See JWT token expiration details
- **Manage API keys**: Navigate to `/settings/api-keys`
- **Sign out everywhere**: Clear all tokens with confirmation dialog
- **Delete account**: Permanently delete account with destructive confirmation dialog

### API Endpoints
- `POST /api/v1/auth/change-password` — Change password (via `useChangePassword`)
- Auth context `logout()` — Clear tokens and sign out

### Components
- `SecuritySettingsPage` — Main security page
- `AlertDialog` — Confirmation dialogs for sign-out and account deletion
- Password visibility toggle buttons

---

## Settings Navigation Summary

```
/settings (Settings Hub)
    │
    ├── /settings/profile          — User profile (name, email, avatar)
    ├── /settings/appearance       — Theme, colors, typography, layout
    ├── /settings/integrations     — Connected accounts (GitHub OAuth)
    ├── /settings/notifications    — Notification channels and timing
    ├── /settings/security         — Password, 2FA, account deletion
    ├── /settings/api-keys         — API key management
    └── /settings/sessions         — Active session management
```

---

**Next**: See [16_public_pages.md](./16_public_pages.md) for public-facing pages.
