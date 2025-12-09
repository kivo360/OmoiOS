# Github Integration

**Part of**: [Page Flow Documentation](./README.md)

---
### Flow 22: GitHub OAuth Authorization & Integration

```
┌─────────────────────────────────────────────────────────────┐
│          PAGE: /login (OAuth Option)                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Login to OmoiOS                                    │   │
│  │                                                      │   │
│  │  Email: [________________]                          │   │
│  │  Password: [________________]                       │   │
│  │                                                      │   │
│  │  [Login]                                             │   │
│  │                                                      │   │
│  │  ──────────── OR ────────────                        │   │
│  │                                                      │   │
│  │  [🔵 Login with GitHub]                             │   │
│  │  [🟠 Login with GitLab]                             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Click "Login with GitHub"
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│      PAGE: /login/oauth/github (GitHub OAuth Redirect)     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Redirecting to GitHub...                           │   │
│  │                                                      │   │
│  │  Please wait while we redirect you to GitHub       │   │
│  │  for authorization.                                │   │
│  │                                                      │   │
│  │  [Loading spinner...]                                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Auto-redirect to GitHub
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│      EXTERNAL: GitHub Authorization Page                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Authorize OmoiOS                                   │   │
│  │                                                      │   │
│  │  OmoiOS wants to access your GitHub account.        │   │
│  │                                                      │   │
│  │  This application will be able to:                  │   │
│  │                                                      │   │
│  │  ✓ Read and write repository contents               │   │
│  │  ✓ Read and write repository metadata               │   │
│  │  ✓ Read and write GitHub Actions                    │   │
│  │  ✓ Read and write workflow files                    │   │
│  │  ✓ Read user profile information                   │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Permission Details:                          │  │   │
│  │  │                                              │  │   │
│  │  │ • repo: Full control of private repositories │  │   │
│  │  │ • actions: Read and write GitHub Actions     │  │   │
│  │  │ • workflow: Read and write workflow files    │  │   │
│  │  │ • user:email: Read user email addresses      │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  [Cancel] [Authorize OmoiOS]                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Click "Authorize OmoiOS"
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│    PAGE: /login/oauth/callback (OAuth Callback Handler)   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Processing GitHub Authorization...                 │   │
│  │                                                      │   │
│  │  [Loading spinner...]                                │   │
│  │                                                      │   │
│  │  • Exchanging authorization code for tokens        │   │
│  │  • Fetching your GitHub profile                     │   │
│  │  • Creating your OmoiOS account                     │   │
│  │  • Storing access tokens securely                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Success
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│          PAGE: /dashboard (Authenticated)                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Welcome! GitHub account connected ✓                 │   │
│  │                                                      │   │
│  │  You can now:                                        │   │
│  │  • Link repositories to projects                    │   │
│  │  • Create repositories via API                       │   │
│  │  • View and edit repository contents               │   │
│  │  • Manage GitHub Actions                            │   │
│  │  • Access workflow files                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### Flow 23: GitHub Repository Connection

```
┌─────────────────────────────────────────────────────────────┐
│    PAGE: /projects/:projectId/settings (GitHub Tab)        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Project: Authentication System                      │   │
│  │  [General] [GitHub] [Phases] [Board] [Notifications] │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  GitHub Integration                                 │   │
│  │                                                      │   │
│  │  Connection Status:                                  │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Not Connected                                │  │   │
│  │  │                                              │  │   │
│  │  │ [Connect GitHub Repository]                 │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  OR                                                  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Connected: owner/repo-name ✓                  │  │   │
│  │  │ Webhook Status: ✓ Active                      │  │   │
│  │  │                                              │  │   │
│  │  │ [Disconnect] [Reconnect] [Test Webhook]     │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Click "Connect GitHub Repository"
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│      PAGE: /projects/:projectId/settings/github/connect    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Connect GitHub Repository                           │   │
│  │                                                      │   │
│  │  Step 1: Authorize GitHub Access                   │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ GitHub Authorization Status:                  │  │   │
│  │  │                                              │  │   │
│  │  │ ⚠️ Not Authorized                            │  │   │
│  │  │                                              │  │   │
│  │  │ OmoiOS needs permission to:                  │  │   │
│  │  │ • Read and write repositories                │  │   │
│  │  │ • Read and write GitHub Actions              │  │   │
│  │  │ • Read and write workflow files              │  │   │
│  │  │                                              │  │   │
│  │  │ [Authorize GitHub]                           │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  OR                                                  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ GitHub Authorization Status:                  │  │   │
│  │  │                                              │  │   │
│  │  │ ✓ Authorized                                 │  │   │
│  │  │ Permissions: repo, actions, workflow         │  │   │
│  │  │                                              │  │   │
│  │  │ [Reauthorize] [View Permissions]            │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  Step 2: Select Repository                         │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Search Repositories:                          │  │   │
│  │  │ [Search by name...] [🔍]                     │  │   │
│  │  │                                              │  │   │
│  │  │ Filter: [All ▼] [Owned] [Organization]      │  │   │
│  │  │                                              │  │   │
│  │  │ ┌────────────────────────────────────────┐ │  │   │
│  │  │ │ owner/repo-name                        │ │  │   │
│  │  │ │ Description: Authentication system...    │ │  │   │
│  │  │ │ ⭐ 42 stars | 🍴 12 forks              │ │  │   │
│  │  │ │ [Select]                                │ │  │   │
│  │  │ └────────────────────────────────────────┘ │  │   │
│  │  │                                              │  │   │
│  │  │ ┌────────────────────────────────────────┐ │  │   │
│  │  │ │ owner/another-repo                    │ │  │   │
│  │  │ │ Description: Another project...        │ │  │   │
│  │  │ │ ⭐ 15 stars | 🍴 3 forks              │ │  │   │
│  │  │ │ [Select]                               │ │  │   │
│  │  │ └────────────────────────────────────────┘ │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  Step 3: Configure Webhook                        │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Webhook Events:                             │  │   │
│  │  │                                              │  │   │
│  │  │ ☑ Issues (created, updated, closed)        │  │   │
│  │  │ ☑ Pushes (code commits)                    │  │   │
│  │  │ ☑ Pull Requests (opened, merged, closed)   │  │   │
│  │  │ ☑ Workflow Runs (started, completed)       │  │   │
│  │  │                                              │  │   │
│  │  │ Auto-sync Options:                          │  │   │
│  │  │                                              │  │   │
│  │  │ ☑ Auto-create tickets from issues          │  │   │
│  │  │ ☑ Auto-link commits to tickets             │  │   │
│  │  │ ☑ Auto-complete tasks on PR merge          │  │   │
│  │  │ ☑ Auto-update workflow status              │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  [Cancel] [Connect Repository]                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Click "Authorize GitHub" (if needed)
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│      EXTERNAL: GitHub Authorization Page                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Authorize OmoiOS                                   │   │
│  │                                                      │   │
│  │  OmoiOS wants to access your GitHub account.        │   │
│  │                                                      │   │
│  │  This application will be able to:                  │   │
│  │                                                      │   │
│  │  ✓ Read and write repository contents               │   │
│  │  ✓ Read and write repository metadata               │   │
│  │  ✓ Read and write GitHub Actions                    │   │
│  │  ✓ Read and write workflow files                    │   │
│  │                                                      │   │
│  │  [Cancel] [Authorize OmoiOS]                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ User authorizes
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│    PAGE: /projects/:projectId/settings/github/connect      │
│    (After Authorization)                                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Connect GitHub Repository                           │   │
│  │                                                      │   │
│  │  Step 1: Authorize GitHub Access                   │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ GitHub Authorization Status:                  │  │   │
│  │  │                                              │  │   │
│  │  │ ✓ Authorized                                 │  │   │
│  │  │ Permissions: repo, actions, workflow         │  │   │
│  │  │                                              │  │   │
│  │  │ [Reauthorize] [View Permissions]            │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  Step 2: Select Repository                         │   │
│  │  (Now enabled - can search and select)            │   │
│  │                                                      │   │
│  │  Step 3: Configure Webhook                        │   │
│  │  (Configuration options shown)                     │   │
│  │                                                      │   │
│  │  [Cancel] [Connect Repository]                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Navigation Summary

### Main Routes

```
/ (Landing)
├── /register (Email registration)
├── /login (Email login)
├── /login/oauth (OAuth login)
├── /verify-email (Email verification)
├── /forgot-password (Password reset)
├── /reset-password (Password reset confirmation)
├── /onboarding (First-time user)
└── /dashboard
    ├── /organizations (Organization list)
    │   ├── /organizations/new (Create organization)
    │   └── /organizations/:id (Organization detail)
    │       ├── /organizations/:id/settings (Org settings)
    │       └── /organizations/:id/members (Org members)
    │
    ├── /projects (Project list)
    │   ├── /projects/new (Create project)
    │   ├── /projects/:id (Project overview)
    │   ├── /projects/:id/explore (AI exploration)
    │   ├── /projects/:id/specs (Specs list)
    │   └── /projects/:id/specs/:specId (Spec viewer)
    │
    ├── /board/:projectId (Kanban board)
    │   └── /board/:projectId/:ticketId (Ticket detail)
    │
    ├── /graph/:projectId (Dependency graph)
    │   └── /graph/:projectId/:ticketId (Ticket graph)
    │
    ├── /agents (Agent list)
    │   ├── /agents/spawn (Spawn agent)
    │   ├── /agents/:agentId (Agent detail)
    │   └── /agents/:agentId/workspace (Workspace detail)
    │
    ├── /workspaces (Workspace list)
    │   └── /workspaces/:agentId (Workspace detail)
    │
    ├── /commits/:commitSha (Commit diff viewer)
    │
    └── /settings (User settings)
        ├── /settings/profile (User profile)
        ├── /settings/api-keys (API key management)
        ├── /settings/sessions (Active sessions)
        └── /settings/preferences (User preferences)
```

### Key User Actions

1. **Registration**: Landing → Register/Login → Email Verification → Onboarding → Dashboard
2. **Organization Setup**: Onboarding → Create Organization → Configure Limits → Dashboard
3. **Project Selection**: Dashboard → Projects List → Project Overview
4. **Spec Workflow**: Project → Specs List → Spec Viewer → (Requirements → Design → Tasks → Execution)
5. **Kanban Board**: Project → Board → View Tickets → Ticket Detail → (Details/Tasks/Commits/Graph/Comments/Audit)
6. **Dependency Graph**: Project → Graph → View Dependencies → Click Node → Ticket Graph View
7. **Statistics**: Project → Stats → View Analytics → (Overview/Tickets/Agents/Code/Cost)
8. **Activity Timeline**: Project → Activity → View Events → Filter by Type/Agent → View Details
9. **Agent Management**: Agents List → Spawn Agent → Agent Detail → Workspace Detail
10. **Workspace Management**: Agents → Workspace Detail → View Commits → View Merge Conflicts
11. **Monitoring**: Board → Ticket Detail → Commit Diff Viewer
12. **API Access**: Settings → API Keys → Generate Key → Use in CI/CD
13. **Organization Management**: Organizations → Organization Detail → Settings → Members
14. **Phase Management**: Project → Phases → View Phases → Edit Phase → Configure Done Definitions/Expected Outputs
15. **Task Phase Management**: Project → Tasks by Phase → View Tasks → Move Task to Phase → Approve Transition
16. **Phase Gate Approvals**: Project → Phase Gates → Review Pending → Approve/Reject Transitions
17. **Comments**: Ticket Detail → Comments Tab → Add Comment → Mention Agents → Attach Files → Real-time Updates
18. **Ticket Search**: Board → Search → Hybrid/Semantic/Keyword → Filter Results → View Ticket
19. **Ticket Creation**: Board → Create Ticket → Fill Form → Set Blockers → Create → Real-time Appears on Board
20. **Status Transition**: Ticket Detail → Move Ticket → Select Status → Add Reason → Transition → Real-time Updates
21. **Blocking Management**: Ticket Detail → Blocking Tab → Add/Remove Blockers → View Graph → Auto-unblock on Resolve
22. **Board Configuration**: Project Settings → Board Tab → Edit Columns → Configure Types → Set WIP Limits → Save
23. **GitHub OAuth**: Login → GitHub OAuth → Grant Permissions (repo, actions, workflow) → Authorize → Dashboard
24. **GitHub Integration**: Project Settings → GitHub Tab → Authorize GitHub → Select Repository → Configure Webhook → Connect
25. **Diagnostic Reasoning View**: Ticket/Task Detail → View Reasoning Chain → See Discoveries → View Blocking Relationships → View Agent Memory → Understand WHY actions happened
26. **Phase Overview (Phasor)**: Project → Phases → View Phase Cards → See Task Counts → View Active Agents → Click "View Tasks" → See Phase-Specific Tasks
27. **Workflow Graph (Phasor)**: Project → Graph → View Phase Columns → See Discovery Branches → Click Edge → View Discovery Reasoning → Understand Adaptive Workflow
28. **Phase Configuration**: Project Settings → Phases Tab → View Default Phases → Edit Phase → Configure Done Definitions → Set Phase Prompt → Save
29. **Custom Phase Creation**: Project Settings → Phases Tab → Create Custom Phase → Define Phase Properties → Configure Transitions → Set Completion Criteria → Save
30. **Phase Gate Management**: Project → Phase Gates → View Pending Gates → Review Artifacts → Approve/Reject → Auto-Progress Ticket
31. **Task Phase Management**: Project → Tasks → Filter by Phase → View Phase-Specific Tasks → Move Task to Phase → Validate Transition
32. **Phase Metrics Dashboard**: Project → Statistics → Phases Tab → View Phase Performance → Compare Phase Efficiency → Identify Bottlenecks

---

## API Integration

### Backend Endpoints

GitHub integration endpoints are prefixed with `/api/v1/github/`.

---

### POST /api/v1/github/connect
**Description:** Connect a GitHub repository to a project

**Query Params:**
- `project_id`: Project ID to connect

**Request Body:**
```json
{
  "owner": "kivo360",
  "repo": "auth-system",
  "webhook_secret": "optional-secret"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Repository connected successfully",
  "project_id": "uuid",
  "webhook_url": "/api/v1/webhooks/github"
}
```

---

### GET /api/v1/github/repos
**Description:** List all connected GitHub repositories

**Response (200):**
```json
[
  {
    "owner": "kivo360",
    "repo": "auth-system",
    "connected": true,
    "webhook_configured": true
  }
]
```

---

### POST /api/v1/github/webhooks/github
**Description:** Handle GitHub webhook events

**Headers:**
- `X-GitHub-Event`: Event type (e.g., `push`, `pull_request`)
- `X-Hub-Signature-256`: Webhook signature for verification

**Body:** GitHub webhook payload (varies by event type)

---

### POST /api/v1/github/sync
**Description:** Manually trigger sync with GitHub repository

**Query Params:**
- `project_id`: Project ID to sync

**Response (200):**
```json
{
  "success": true,
  "message": "Sync initiated for kivo360/auth-system"
}
```

---

### GitHub OAuth Scopes Required:
- `repo`: Full control of private repositories
- `read:org`: Read org and team membership
- `workflow`: Update GitHub Action workflows
- `admin:repo_hook`: Full control of repository hooks

---

**Next**: See [README.md](./README.md) for complete documentation index.
