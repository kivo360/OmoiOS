# Index

**Part of**: [Page Flow Documentation](./README.md)

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


---

**Next**: See [README.md](./README.md) for complete documentation index.
