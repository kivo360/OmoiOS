# Phase Configuration

**Part of**: [Page Flow Documentation](./README.md)

---
### Flow 28: Phase Configuration & Management

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /projects/:projectId/settings/phases                 │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Phase Management                                   │   │
│  │  Configure workflow phases and transitions          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Default Phases                                      │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ PHASE_BACKLOG                                │  │   │
│  │  │ Initial ticket triage                        │  │   │
│  │  │ Sequence: 0 | Terminal: No                  │  │   │
│  │  │ [Edit] [View Details]                        │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ PHASE_REQUIREMENTS                            │  │   │
│  │  │ Requirements Analysis                         │  │   │
│  │  │ Sequence: 1 | Terminal: No                  │  │   │
│  │  │ Allowed Transitions: PHASE_DESIGN, PHASE_BLOCKED│ │   │
│  │  │ [Edit] [View Details]                        │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ PHASE_IMPLEMENTATION                          │  │   │
│  │  │ Implementation                                │  │   │
│  │  │ Sequence: 3 | Terminal: No                  │  │   │
│  │  │ Allowed Transitions: PHASE_TESTING, PHASE_REQUIREMENTS│ │   │
│  │  │ [Edit] [View Details]                        │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  [+ Create Custom Phase]                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Click "Edit" on PHASE_IMPLEMENTATION
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /projects/:projectId/phases/PHASE_IMPLEMENTATION   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Edit Phase: PHASE_IMPLEMENTATION                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tabs: [Basic Info] [Done Definitions] [Outputs]   │   │
│  │        [Phase Prompt] [Transitions] [Configuration]  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Basic Info Tab                                      │   │
│  │                                                      │   │
│  │  Phase ID: PHASE_IMPLEMENTATION (read-only)        │   │
│  │  Name: [Implementation                    ]         │   │
│  │  Description: [Build one component with...]        │   │
│  │  Sequence Order: [3]                                │   │
│  │  Terminal Phase: [ ] No  [✓] Yes                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Done Definitions Tab                                │   │
│  │                                                      │   │
│  │  Completion Criteria (one per line):                │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Component code files created in src/         │  │   │
│  │  │ Minimum 3 test cases written                 │  │   │
│  │  │ Tests passing locally                        │  │   │
│  │  │ Phase 3 validation task created             │  │   │
│  │  │ update_task_status called with status='done' │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  [+ Add Criterion]                                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Phase Prompt Tab                                    │   │
│  │                                                      │   │
│  │  System Instructions for Agents:                    │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ YOU ARE A SOFTWARE ENGINEER IN THE           │  │   │
│  │  │ IMPLEMENTATION PHASE                          │  │   │
│  │  │                                               │  │   │
│  │  │ STEP 1: Extract ticket ID from task...      │  │   │
│  │  │ STEP 2: Move ticket to 'building' status... │  │   │
│  │  │ ...                                           │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  [Preview] [Save]                                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Transitions Tab                                     │   │
│  │                                                      │   │
│  │  Allowed Transitions:                                │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ [✓] PHASE_TESTING                            │  │   │
│  │  │ [✓] PHASE_REQUIREMENTS (for clarification)  │  │   │
│  │  │ [✓] PHASE_BLOCKED                            │  │   │
│  │  │ [ ] PHASE_DESIGN                             │  │   │
│  │  │ [ ] PHASE_DEPLOYMENT                         │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  Note: Discovery-based spawning bypasses these      │   │
│  │  restrictions (agents can spawn any phase via      │   │
│  │  DiscoveryService)                                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Configuration Tab                                   │   │
│  │                                                      │   │
│  │  Phase-Specific Settings:                           │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Timeout (seconds): [3600]                    │  │   │
│  │  │ Max Retries: [3]                             │  │   │
│  │  │ Retry Strategy: [Exponential Backoff ▼]    │  │   │
│  │  │ WIP Limit: [10]                              │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  [Save Configuration]                               │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  [Save Phase] [Cancel] [Delete Phase]                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### Flow 29: Custom Phase Creation

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /projects/:projectId/settings/phases                 │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  [+ Create Custom Phase]                             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Click "Create Custom Phase"
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /projects/:projectId/phases/new                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Create Custom Phase                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Phase Identity                                       │   │
│  │                                                      │   │
│  │  Phase ID: [PHASE_CUSTOM_RESEARCH]                  │   │
│  │  (Must start with PHASE_)                            │   │
│  │                                                      │   │
│  │  Name: [Custom Research Phase        ]              │   │
│  │  Description: [Investigate topic and...]            │   │
│  │  Sequence Order: [8]                                │   │
│  │  Terminal Phase: [ ] No  [ ] Yes                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Done Definitions                                     │   │
│  │                                                      │   │
│  │  Completion Criteria:                                │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Research question defined                    │  │   │
│  │  │ Approaches identified                        │  │   │
│  │  │ Phase 2 evaluation tasks created             │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  [+ Add Criterion]                                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Phase Prompt                                        │   │
│  │                                                      │   │
│  │  System Instructions:                               │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ YOU ARE A RESEARCH ANALYST                   │  │   │
│  │  │                                               │  │   │
│  │  │ STEP 1: Understand the research question    │  │   │
│  │  │ STEP 2: Search for existing solutions       │  │   │
│  │  │ STEP 3: Identify 3-5 approaches to evaluate │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Allowed Transitions                                 │   │
│  │                                                      │   │
│  │  This phase can transition to:                       │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ [✓] PHASE_EVALUATION                        │  │   │
│  │  │ [✓] PHASE_BLOCKED                           │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  [+ Add Transition]                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  [Create Phase] [Cancel]                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### Flow 30: Phase Gate Approval

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /projects/:projectId/phase-gates                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Phase Gate Approvals                               │   │
│  │  Review and approve phase transitions                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Filter: [All Phases ▼] [Pending] [Approved] [Rejected]│ │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Pending Approvals                                   │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Ticket: Build Authentication System          │  │   │
│  │  │ Current Phase: PHASE_IMPLEMENTATION          │  │   │
│  │  │ Requested Transition: PHASE_TESTING          │  │   │
│  │  │ Requested by: Agent worker-2                 │  │   │
│  │  │ Requested at: 10:45 AM                       │  │   │
│  │  │                                                │  │   │
│  │  │ Gate Criteria Status:                         │  │   │
│  │  │ ✓ Required artifacts collected                │  │   │
│  │  │ ✓ All tasks completed                         │  │   │
│  │  │ ✓ Validation criteria met                     │  │   │
│  │  │                                                │  │   │
│  │  │ Artifacts:                                    │  │   │
│  │  │ • code_changes: src/auth/jwt.py (✓)           │  │   │
│  │  │ • test_coverage: 85% (✓)                     │  │   │
│  │  │                                                │  │   │
│  │  │ [Review Details] [Approve] [Reject]          │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Ticket: Implement API Endpoints              │  │   │
│  │  │ Current Phase: PHASE_REQUIREMENTS            │  │   │
│  │  │ Requested Transition: PHASE_DESIGN           │  │   │
│  │  │ Requested by: Agent worker-1                 │  │   │
│  │  │                                                │  │   │
│  │  │ Gate Criteria Status:                         │  │   │
│  │  │ ✓ Required artifacts collected                │  │   │
│  │  │ ✗ Missing: requirements_document              │  │   │
│  │  │                                                │  │   │
│  │  │ [Review Details] [Request More Info] [Reject]│  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Click "Review Details" on first gate
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /projects/:projectId/phase-gates/:gateId             │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Phase Gate Review                                  │   │
│  │  Ticket: Build Authentication System               │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Transition Request                                 │   │
│  │                                                      │   │
│  │  From: PHASE_IMPLEMENTATION                         │   │
│  │  To: PHASE_TESTING                                  │   │
│  │  Requested by: Agent worker-2                       │   │
│  │  Requested at: 10:45 AM                            │   │
│  │  Reason: "Implementation complete, tests passing"  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Gate Criteria Validation                           │   │
│  │                                                      │   │
│  │  ✓ Required Artifacts                               │   │
│  │    • code_changes: src/auth/jwt.py                  │   │
│  │    • test_coverage: 85% (min: 80%)                 │   │
│  │                                                      │   │
│  │  ✓ Tasks Completed                                 │   │
│  │    • All 3 tasks in PHASE_IMPLEMENTATION done      │   │
│  │                                                      │   │
│  │  ✓ Validation Criteria                              │   │
│  │    • Tests passing: ✓                              │   │
│  │    • Code quality: ✓                                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Artifacts Review                                   │   │
│  │                                                      │   │
│  │  Code Changes:                                       │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ File: src/auth/jwt.py                        │  │   │
│  │  │ Lines: +245, -12                              │  │   │
│  │  │ [View Diff] [View File]                      │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  Test Coverage:                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Coverage: 85%                               │  │   │
│  │  │ Passing Tests: 12/12                         │  │   │
│  │  │ [View Test Report]                           │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Approval Decision                                  │   │
│  │                                                      │   │
│  │  Comments:                                          │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ [Add comment...]                            │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  [Approve & Transition] [Request Changes] [Reject] │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### Flow 31: Task Phase Management

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /projects/:projectId/tasks/phases                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tasks by Phase                                     │   │
│  │  Manage tasks across workflow phases                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Filter: [All Phases ▼] [All Status ▼] [All Priorities ▼]│ │
│  │  Search: [Search tasks...]                          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  PHASE_REQUIREMENTS (1 task)                        │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ [▼] Expand                                  │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ PHASE_IMPLEMENTATION (28 tasks)            │  │   │
│  │  │ ┌────────────────────────────────────────┐  │  │   │
│  │  │ │ [▼] Expand                            │  │  │   │
│  │  │ └────────────────────────────────────────┘  │  │   │
│  │  │                                              │  │   │
│  │  │ ┌────────────────────────────────────────┐  │  │   │
│  │  │ │ P2 Plan And Implementation            │  │  │   │
│  │  │ │ Fix CRITICAL Analytics service        │  │  │   │
│  │  │ │ Status: Active | Priority: Critical  │  │  │   │
│  │  │ │ Agent: worker-2 | Created: 10:34 AM  │  │  │   │
│  │  │ │ [View Details] [Move to Phase ▼]     │  │  │   │
│  │  │ └────────────────────────────────────────┘  │  │   │
│  │  │                                              │  │   │
│  │  │ ┌────────────────────────────────────────┐  │  │   │
│  │  │ │ P2 Plan And Implementation            │  │  │   │
│  │  │ │ Plan & Implement Backend Infrastructure│  │  │   │
│  │  │ │ Status: Active | Priority: High        │  │  │   │
│  │  │ │ Agent: worker-1 | Created: 10:28 AM  │  │  │   │
│  │  │ │ [View Details] [Move to Phase ▼]     │  │  │   │
│  │  │ └────────────────────────────────────────┘  │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ PHASE_TESTING (23 tasks)                    │  │   │
│  │  │ ┌────────────────────────────────────────┐  │  │   │
│  │  │ │ [▼] Expand                            │  │  │   │
│  │  │ └────────────────────────────────────────┘  │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Bulk Actions                                        │   │
│  │  [Select All] [Move Selected to Phase ▼] [Bulk Edit]│   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Click "Move to Phase" on task
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /tasks/:taskId/move-phase                            │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Move Task to Phase                                 │   │
│  │  Task: Fix CRITICAL Analytics service               │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Current Phase: PHASE_IMPLEMENTATION                │   │
│  │                                                      │   │
│  │  Select Target Phase:                               │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Allowed Transitions:                          │  │   │
│  │  │ • PHASE_TESTING (normal flow)                  │  │   │
│  │  │ • PHASE_REQUIREMENTS (clarification needed)   │  │   │
│  │  │ • PHASE_BLOCKED (blocked)                     │  │   │
│  │  │                                                │  │   │
│  │  │ Discovery-Based (bypasses restrictions):      │  │   │
│  │  │ • Any phase (via DiscoveryService)            │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  Target Phase: [PHASE_TESTING ▼]                  │   │
│  │                                                      │   │
│  │  Reason for Transition:                            │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ [Implementation complete, ready for testing...]│  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  [Move Task] [Cancel]                               │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### Flow 32: Phase Metrics Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  PAGE: /projects/:projectId/stats                            │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Statistics Dashboard                               │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tabs: [Overview] [Tickets] [Agents] [Code] [Cost] │   │
│  │        [Phases]                                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Phases Tab                                         │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Phase Performance Overview                   │  │   │
│  │  │                                              │  │   │
│  │  │ Phase                Tasks  Done  Active   │  │   │
│  │  │ ─────────────────────────────────────────── │  │   │
│  │  │ PHASE_REQUIREMENTS     1      1      0      │  │   │
│  │  │ PHASE_IMPLEMENTATION  28     22      2      │  │   │
│  │  │ PHASE_TESTING         23     22      0      │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Phase Efficiency Metrics                     │  │   │
│  │  │                                              │  │   │
│  │  │ Phase                Avg Time  Success Rate │  │   │
│  │  │ ─────────────────────────────────────────── │  │   │
│  │  │ PHASE_REQUIREMENTS   45 min      100%      │  │   │
│  │  │ PHASE_IMPLEMENTATION 2.5 hrs     78%      │  │   │
│  │  │ PHASE_TESTING        1.2 hrs     95%      │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Phase Bottlenecks                            │  │   │
│  │  │                                              │  │   │
│  │  │ • PHASE_IMPLEMENTATION: 6 tasks queued      │  │   │
│  │  │   (WIP limit: 10, current: 2 active)       │  │   │
│  │  │                                              │  │   │
│  │  │ • PHASE_TESTING: 1 task blocked             │  │   │
│  │  │   (waiting for PHASE_IMPLEMENTATION)        │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Phase Cost Breakdown                         │  │   │
│  │  │                                              │  │   │
│  │  │ Phase                Cost    % of Total     │  │   │
│  │  │ ─────────────────────────────────────────── │  │   │
│  │  │ PHASE_REQUIREMENTS   $2.50      5%         │  │   │
│  │  │ PHASE_IMPLEMENTATION $35.00    70%         │  │   │
│  │  │ PHASE_TESTING        $12.50    25%         │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │ Discovery Activity by Phase                  │  │   │
│  │  │                                              │  │   │
│  │  │ Phase                Discoveries  Branches  │  │   │
│  │  │ ─────────────────────────────────────────── │  │   │
│  │  │ PHASE_IMPLEMENTATION    5          3        │  │   │
│  │  │ PHASE_TESTING           3          2        │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## API Integration

### Backend Endpoints

Phase configuration and gate endpoints.

---

### GET /api/v1/tickets/{ticket_id}/gate-status
**Description:** Get gate requirement status for phase configuration view

**Query Params:**
- `phase_id` (optional): Target phase

**Response (200):**
```json
{
  "ticket_id": "uuid",
  "phase_id": "PHASE_IMPLEMENTATION",
  "requirements": [
    { "name": "All code files created", "status": "passed" },
    { "name": "Minimum 3 test cases passing", "status": "failed", "current": 2, "required": 3 }
  ],
  "artifacts": [
    { "name": "Source files", "pattern": "src/auth/*.py", "found": 3, "expected": "1+", "status": "passed" }
  ],
  "overall_status": "failed"
}
```

---

### POST /api/v1/tickets/{ticket_id}/artifacts
**Description:** Register phase gate artifacts

**Request Body:**
```json
{
  "phase_id": "PHASE_IMPLEMENTATION",
  "artifact_type": "source_file",
  "artifact_path": "src/auth/oauth2_handler.py",
  "artifact_content": null,
  "collected_by": "worker-1"
}
```

---

### GET /api/v1/projects/{project_id}/stats
**Description:** Get project statistics for phase metrics dashboard

**Response (200):**
```json
{
  "project_id": "uuid",
  "total_tickets": 25,
  "tickets_by_status": {
    "backlog": 10,
    "building": 8,
    "testing": 5,
    "done": 2
  },
  "tickets_by_phase": {
    "PHASE_REQUIREMENTS": 3,
    "PHASE_IMPLEMENTATION": 12,
    "PHASE_TESTING": 5
  },
  "active_agents": 3,
  "total_commits": 47
}
```

---

### GET /api/v1/board/stats
**Description:** Get column statistics (for phase flow metrics)

**Response (200):**
```json
[
  {
    "column_id": "building",
    "name": "Building",
    "ticket_count": 4,
    "wip_limit": 5,
    "utilization": 0.8,
    "wip_exceeded": false
  }
]
```

---

## Quality Metrics API

Quality metrics track task execution quality and enable predictive quality scoring.

### POST /api/v1/quality/metrics/record
**Description:** Record a quality metric for a task

**Request Body:**
```json
{
  "task_id": "task-uuid",
  "metric_name": "test_coverage",
  "value": 85.5,
  "metadata": {
    "test_count": 24,
    "passing_tests": 24
  }
}
```

**Response (201):**
```json
{
  "metric_id": "uuid",
  "task_id": "task-uuid",
  "metric_name": "test_coverage",
  "value": 85.5,
  "recorded_at": "2025-01-15T10:30:00Z"
}
```

---

### GET /api/v1/quality/metrics/{task_id}
**Description:** Get all quality metrics for a task

**Path Params:** `task_id` (string)

**Response (200):**
```json
{
  "task_id": "task-uuid",
  "metrics": {
    "test_coverage": 85.5,
    "code_complexity": 12,
    "lint_score": 95,
    "documentation_coverage": 70
  },
  "overall_score": 82.5,
  "recorded_at": "2025-01-15T10:30:00Z"
}
```

---

### POST /api/v1/quality/predict
**Description:** Predict quality score for a planned task using Memory patterns

**Request Body:**
```json
{
  "task_description": "Implement OAuth2 authentication with JWT",
  "context": {
    "phase_id": "PHASE_IMPLEMENTATION",
    "agent_id": "worker-5"
  }
}
```

**Response (200):**
```json
{
  "predicted_score": 78.5,
  "confidence": 0.85,
  "similar_tasks_analyzed": 5,
  "recommendations": [
    "Consider adding integration tests for token refresh",
    "Similar tasks had issues with session expiry - add explicit handling"
  ],
  "risk_factors": [
    {
      "factor": "complexity",
      "level": "medium",
      "description": "OAuth2 implementations typically have moderate complexity"
    }
  ]
}
```

---

### GET /api/v1/quality/trends
**Description:** Get quality trends across tasks

**Query Params:**
- `phase_id` (optional): Filter by phase
- `limit` (default: 10): Number of recent tasks

**Response (200):**
```json
{
  "period": "last_30_days",
  "average_score": 81.2,
  "trend": "improving",
  "trend_change": "+5.3%",
  "by_phase": {
    "PHASE_IMPLEMENTATION": {
      "average_score": 79.5,
      "task_count": 45
    },
    "PHASE_TESTING": {
      "average_score": 88.2,
      "task_count": 32
    }
  },
  "recent_scores": [
    {"task_id": "uuid", "score": 85, "date": "2025-01-15"},
    {"task_id": "uuid", "score": 78, "date": "2025-01-14"}
  ]
}
```

---

### POST /api/v1/quality/gates/{gate_id}/evaluate
**Description:** Evaluate a quality gate for a task

**Path Params:** `gate_id` (string)

**Query Params:**
- `task_id` (required): Task to evaluate

**Response (200):**
```json
{
  "gate_id": "gate-uuid",
  "task_id": "task-uuid",
  "passed": true,
  "score": 85.5,
  "threshold": 80.0,
  "criteria": [
    {
      "name": "test_coverage",
      "required": 80,
      "actual": 85.5,
      "passed": true
    },
    {
      "name": "lint_score",
      "required": 90,
      "actual": 95,
      "passed": true
    }
  ],
  "evaluated_at": "2025-01-15T10:30:00Z"
}
```

---

**Next**: See [README.md](./README.md) for complete documentation index.
