# 5 Organizations Api

**Part of**: [Page Flow Documentation](./README.md)

---
### Flow 6: Organization Management & Multi-Tenancy

```
┌─────────────────────────────────────────────────────────────┐
│          PAGE: /organizations (Organization List)          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Organizations                                       │   │
│  │                                                       │   │
│  │  [New Organization] [Switch Organization]           │   │
│  │                                                       │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Organization: Acme Corp                      │  │   │
│  │  │ Slug: acme-corp                               │  │   │
│  │  │ Status: Active                                 │  │   │
│  │  │ Owner: You ✓                                  │  │   │
│  │  │ Members: 5                                    │  │   │
│  │  │ Projects: 12                                  │  │   │
│  │  │ Resource Usage: 3/5 agents, 45.2/100 hours   │  │   │
│  │  │ [View] [Settings] [Switch]                    │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                       │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Organization: Beta Inc                       │  │   │
│  │  │ Slug: beta-inc                                │  │   │
│  │  │ Status: Active                                 │  │   │
│  │  │ Owner: john@example.com                      │  │   │
│  │  │ Members: 3                                    │  │   │
│  │  │ Projects: 8                                   │  │   │
│  │  │ Resource Usage: 2/5 agents, 12.5/100 hours   │  │   │
│  │  │ [View] [Switch]                               │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Click "Settings" or "New Organization"
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│    PAGE: /organizations/:id/settings (Org Settings)        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Organization: Acme Corp                            │   │
│  │  Slug: acme-corp                                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tabs: [General] [Resources] [Members] [Billing]     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  General Tab                                         │   │
│  │                                                      │   │
│  │  Name: [Acme Corp]                                   │   │
│  │  Slug: [acme-corp] [Edit]                          │   │
│  │  Description: [________________]                    │   │
│  │                                                      │   │
│  │  Status: ● Active                                    │   │
│  │                                                      │   │
│  │  [Save Changes]                                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Resources Tab                                       │   │
│  │                                                      │   │
│  │  Max Concurrent Agents: [5]                        │   │
│  │  Current Usage: 3/5                                 │   │
│  │                                                      │   │
│  │  Max Runtime Hours: [100.0]                        │   │
│  │  Current Usage: 45.2/100 hours                      │   │
│  │                                                      │   │
│  │  [Update Limits]                                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Members Tab (Future)                                │   │
│  │                                                      │   │
│  │  [Invite Member]                                    │   │
│  │                                                      │   │
│  │  • john@example.com (Owner)                         │   │
│  │  • jane@example.com (Member)                        │   │
│  │  • bob@example.com (Member)                         │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### Flow 7: Workspace Management & Isolation

```
┌─────────────────────────────────────────────────────────────┐
│          PAGE: /agents/:agentId/workspace (Workspace)       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Agent: worker-1                                     │   │
│  │  Workspace: Isolated                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Workspace Details                                   │   │
│  │                                                      │   │
│  │  Working Directory:                                  │   │
│  │  /tmp/omoi_os_workspaces/ws_worker-1                │   │
│  │                                                      │   │
│  │  Git Branch: workspace-worker-1                     │   │
│  │  Base Branch: main                                  │   │
│  │  Workspace Type: local                              │   │
│  │                                                      │   │
│  │  Parent Agent: None                                 │   │
│  │  Parent Commit: abc123def456                        │   │
│  │                                                      │   │
│  │  Status: ● Active                                    │   │
│  │  Created: Oct 30, 2025 10:23                        │   │
│  │  Updated: Oct 30, 2025 12:47                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tabs: [Commits] [Merge Conflicts] [Settings]       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Commits Tab                                         │   │
│  │                                                      │   │
│  │  Total Commits: 5                                    │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Commit: def456ghi789                          │  │   │
│  │  │ Type: validation                               │  │   │
│  │  │ Iteration: 1                                   │  │   │
│  │  │ Files Changed: 7                               │  │   │
│  │  │ Message: "[Agent worker-1] Iteration 1"       │  │   │
│  │  │ Date: Oct 30, 2025 11:15                       │  │   │
│  │  │ [View Diff]                                    │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Commit: abc123def456                          │  │   │
│  │  │ Type: checkpoint                              │  │   │
│  │  │ Files Changed: 3                               │  │   │
│  │  │ Message: "[Agent worker-1] Checkpoint"       │  │   │
│  │  │ Date: Oct 30, 2025 10:45                      │  │   │
│  │  │ [View Diff]                                    │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Merge Conflicts Tab                                 │   │
│  │                                                      │   │
│  │  Total Conflicts Resolved: 2                         │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Merge: xyz789abc123                          │  │   │
│  │  │ Target Branch: main                          │  │   │
│  │  │ Source Branch: workspace-worker-1           │  │   │
│  │  │ Conflicts Resolved: 2                        │  │   │
│  │  │ Strategy: newest_file_wins                   │  │   │
│  │  │ Files:                                       │  │   │
│  │  │   • src/auth/oauth2_handler.py              │  │   │
│  │  │   • tests/test_oauth2.py                    │  │   │
│  │  │ Date: Oct 30, 2025 12:30                    │  │   │
│  │  │ [View Details]                               │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### Flow 8: API Key Management

```
┌─────────────────────────────────────────────────────────────┐
│          PAGE: /settings/api-keys (API Keys)                │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  API Key Management                                  │   │
│  │                                                       │   │
│  │  [Generate New API Key]                              │   │
│  │                                                       │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Key: sk_live_abc123...xyz789                    │  │   │
│  │  │ Name: CI/CD Integration                        │  │   │
│  │  │ Scope: org:acme-corp:*                          │  │   │
│  │  │ Created: Oct 25, 2025                          │  │   │
│  │  │ Last Used: Oct 30, 2025 12:00                  │  │   │
│  │  │ Status: ● Active                                │  │   │
│  │  │ [Revoke] [Copy] [View Details]                 │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                       │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Key: sk_live_def456...uvw012                    │  │   │
│  │  │ Name: Development                               │  │   │
│  │  │ Scope: *:*                                      │  │   │
│  │  │ Created: Oct 20, 2025                          │  │   │
│  │  │ Last Used: Never                                │  │   │
│  │  │ Status: ● Active                                │  │   │
│  │  │ [Revoke] [Copy] [View Details]                 │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Click "Generate New API Key"
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│      PAGE: /settings/api-keys/new (Generate API Key)       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Generate New API Key                                │   │
│  │                                                       │   │
│  │  Name: [________________]                           │   │
│  │  Description: [________________]                    │   │
│  │                                                       │   │
│  │  Scope:                                              │   │
│  │  ○ Full Access (*:*)                                │   │
│  │  ● Organization Scope                               │   │
│  │    Organization: [acme-corp ▼]                     │   │
│  │    Permissions: [Select permissions...]             │   │
│  │                                                       │   │
│  │  Expiration (optional):                             │   │
│  │  [Never] [30 days] [90 days] [Custom]              │   │
│  │                                                       │   │
│  │  [Cancel] [Generate Key]                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Click "Generate Key"
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│      PAGE: /settings/api-keys/:id (API Key Created)        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  API Key Created ✓                                   │   │
│  │                                                       │   │
│  │  ⚠️ IMPORTANT: Copy this key now. You won't be able │   │
│  │  to see it again!                                    │   │
│  │                                                       │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ sk_live_abc123def456ghi789jkl012mno345pqr678 │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                       │   │
│  │  [Copy Key] [Download Key]                           │   │
│  │                                                       │   │
│  │  Usage Example:                                     │   │
│  │  curl -H "Authorization: Bearer sk_live_..." \     │   │
│  │       https://api.omoios.com/v1/projects            │   │
│  │                                                       │   │
│  │  [Done]                                             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---


---

**Next**: See [README.md](./README.md) for complete documentation index.
