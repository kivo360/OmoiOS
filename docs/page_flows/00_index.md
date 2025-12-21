# Index

**Part of**: [Page Flow Documentation](./README.md)

---

## The Core Promise

> **Start a feature before bed. Wake up to a PR.**

Let AI run overnight and finish your software for you.

**See [../user_journey/00a_demo_flow.md](../user_journey/00a_demo_flow.md) for the video demo script.**

---

## The Overnight Story

```
9:00 PM - Type "Add Stripe payments", approve plan (5 min)
9:05 PM - Go to sleep 😴

   [Agents work through the night]
   [Guardian keeps them on track]
   [Bugs found → Fixed automatically]

7:00 AM - Wake up ☀️ PR waiting
7:05 AM - Review with coffee, approve ☕
7:10 AM - Feature merged before standup

Your time: 10 minutes | AI time: 10 hours | Shipped: Same morning
```

---

## Navigation Summary

### Main Routes

```
/ (Landing - unauthenticated)
├── /register (Email registration)
├── /login (Email login)
├── /login/oauth (OAuth login)
├── /verify-email (Email verification)
├── /forgot-password (Password reset)
├── /reset-password (Password reset confirmation)
├── /onboarding (First-time user)
│
└── / (Authenticated - Command Center) ← PRIMARY LANDING
    │
    ├── /analytics (Analytics Dashboard) ← SECONDARY (deliberate navigation)
    │
    ├── /health (System Health Dashboard) ← MONITORING (header indicator access)
    │   ├── /health/trajectories (Active Trajectory Analyses)
    │   ├── /health/interventions (Intervention History)
    │   └── /health/settings (Monitoring Configuration)
    │
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
    ├── /costs (Cost Dashboard)
    │   └── /costs?tab=records|budgets|forecast (Cost views)
    │
    ├── /memory (Agent Memory)
    │   ├── /memory?tab=search (Semantic search)
    │   └── /memory?tab=patterns (Learned patterns)
    │
    └── /settings (User settings)
        ├── /settings/profile (User profile)
        ├── /settings/api-keys (API key management)
        ├── /settings/sessions (Active sessions)
        └── /settings/preferences (User preferences)
```

### Key User Actions

1. **Registration**: Landing → Register/Login → Email Verification → Onboarding → Command Center
2. **Organization Setup**: Onboarding → Create Organization → Configure Limits → Command Center
3. **Command Center Flow**: Command Center → Select Repo → Type Task → Submit → Agent Detail View
4. **Quick Project Start**: Command Center → Select New Repo → Type Task → Auto-Create Project + Spawn Agent
5. **Analytics Access**: Command Center → Click "Analytics" in nav → Analytics Dashboard
6. **Agent History**: Command Center → Click agent in sidebar → Agent Detail View
7. **Project Selection**: Command Center → Projects → Projects List → Project Overview
8. **Spec Workflow**: Project → Specs List → Spec Viewer → (Requirements → Design → Tasks → Execution)
9. **Kanban Board**: Project → Board → View Tickets → Ticket Detail → (Details/Tasks/Commits/Graph/Comments/Audit)
10. **Dependency Graph**: Project → Graph → View Dependencies → Click Node → Ticket Graph View
11. **Statistics**: Project → Stats → View Analytics → (Overview/Tickets/Agents/Code/Cost)
12. **Activity Timeline**: Project → Activity → View Events → Filter by Type/Agent → View Details
13. **Agent Management**: Agents List → Spawn Agent → Agent Detail → Workspace Detail
14. **Workspace Management**: Agents → Workspace Detail → View Commits → View Merge Conflicts
15. **Monitoring**: Board → Ticket Detail → Commit Diff Viewer
16. **API Access**: Settings → API Keys → Generate Key → Use in CI/CD
17. **Organization Management**: Organizations → Organization Detail → Settings → Members
18. **Phase Management**: Project → Phases → View Phases → Edit Phase → Configure Done Definitions/Expected Outputs
19. **Task Phase Management**: Project → Tasks by Phase → View Tasks → Move Task to Phase → Approve Transition
20. **Phase Gate Approvals**: Project → Phase Gates → Review Pending → Approve/Reject Transitions
21. **Comments**: Ticket Detail → Comments Tab → Add Comment → Mention Agents → Attach Files → Real-time Updates
22. **Ticket Search**: Board → Search → Hybrid/Semantic/Keyword → Filter Results → View Ticket
23. **Ticket Creation**: Board → Create Ticket → Fill Form → Set Blockers → Create → Real-time Appears on Board
24. **Status Transition**: Ticket Detail → Move Ticket → Select Status → Add Reason → Transition → Real-time Updates
25. **Blocking Management**: Ticket Detail → Blocking Tab → Add/Remove Blockers → View Graph → Auto-unblock on Resolve
26. **Board Configuration**: Project Settings → Board Tab → Edit Columns → Configure Types → Set WIP Limits → Save
27. **GitHub OAuth**: Login → GitHub OAuth → Grant Permissions (repo, actions, workflow) → Authorize → Command Center
28. **GitHub Integration**: Project Settings → GitHub Tab → Authorize GitHub → Select Repository → Configure Webhook → Connect
29. **Diagnostic Reasoning View**: Ticket/Task Detail → View Reasoning Chain → See Discoveries → View Blocking Relationships → View Agent Memory → Understand WHY actions happened
30. **Phase Overview (Phasor)**: Project → Phases → View Phase Cards → See Task Counts → View Active Agents → Click "View Tasks" → See Phase-Specific Tasks
31. **Workflow Graph (Phasor)**: Project → Graph → View Phase Columns → See Discovery Branches → Click Edge → View Discovery Reasoning → Understand Adaptive Workflow
32. **Phase Configuration**: Project Settings → Phases Tab → View Default Phases → Edit Phase → Configure Done Definitions → Set Phase Prompt → Save
33. **Custom Phase Creation**: Project Settings → Phases Tab → Create Custom Phase → Define Phase Properties → Configure Transitions → Set Completion Criteria → Save
34. **Phase Gate Management**: Project → Phase Gates → View Pending Gates → Review Artifacts → Approve/Reject → Auto-Progress Ticket
35. **Task Phase Management**: Project → Tasks → Filter by Phase → View Phase-Specific Tasks → Move Task to Phase → Validate Transition
36. **Phase Metrics Dashboard**: Project → Statistics → Phases Tab → View Phase Performance → Compare Phase Efficiency → Identify Bottlenecks
37. **System Health Access**: Command Center → Click 🛡️ Guardian indicator → System Health Dashboard
38. **Monitoring Overview**: System Health → View Guardian/Conductor status → See active agents → Check alignment scores
39. **Trajectory Analysis**: System Health → Trajectories Tab → View agent alignment → See constraint tracking → Send intervention
40. **Intervention Review**: System Health → Interventions Tab → View history → Check success rates → Analyze recovery times
41. **Monitoring Configuration**: System Health → Settings → Configure thresholds → Set notification preferences → Adjust adaptive learning
42. **Cost Tracking**: Analytics/Project → Costs Tab → View spend by scope → Track budget utilization → Set alerts
43. **Budget Management**: Costs → Budgets → Create Budget → Set limits → Monitor utilization → Receive alerts
44. **Cost Forecasting**: Costs → Forecast → Estimate pending costs → Adjust parameters → Plan budget
45. **Memory Search**: Memory → Search → Enter task description → Find similar past tasks → Apply learnings
46. **Pattern Learning**: Memory → Patterns → View learned patterns → Provide feedback → Extract new patterns

---


---

**Next**: See [README.md](./README.md) for complete documentation index.
