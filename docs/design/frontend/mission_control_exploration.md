# Mission Control UI Exploration

**Created**: 2025-11-21
**Status**: Exploratory Design
**Purpose**: Explore "Mission Control" paradigm vs. current Linear-style design for OmoiOS

---

## Overview

This document explores what OmoiOS would look and feel like if we fully embraced a "Mission Control" interface paradigm—optimized for high information density, real-time operations monitoring, and rapid decision-making.

---

## Side-by-Side Comparison

### Current Approach: Linear-Style Dashboard

**Philosophy**: Modern SaaS, clean, minimal, one view at a time.

**Layout**:
```
┌─────────────────────────────────────────────────────────────────┐
│ Header: Logo | Projects ▼ | Search | 🔔 | Profile             │
├──────┬──────────────────────────────────────────────────────────┤
│      │                                                          │
│ Nav  │  Main Content Area (Full Width)                         │
│ ──── │  ┌────────────────────────────────────────────────┐    │
│ Home │  │ Project Overview                                │    │
│ Board│  │                                                 │    │
│ Graph│  │ Stats: [24 Tickets] [8 Active] [3 Agents]      │    │
│ Specs│  │                                                 │    │
│ Stats│  │ Quick Nav: [Board] [Graph] [Specs] [Stats]    │    │
│ Agent│  │                                                 │    │
│      │  │ Active Tickets Preview (Top 5)                  │    │
│      │  │ [Ticket 1]                                      │    │
│      │  │ [Ticket 2]                                      │    │
│      │  └────────────────────────────────────────────────┘    │
│      │                                                          │
└──────┴──────────────────────────────────────────────────────────┘
```

**Characteristics**:
- Clean, plenty of whitespace
- One primary focus at a time
- Click to navigate between views
- Activity feed in collapsible right sidebar

---

### Mission Control Approach: High-Density Operations

**Philosophy**: Real-time command center, all critical info visible simultaneously.

**Layout**:
```
┌────────────────────────────────────────────────────────────────────┐
│ [≡] OmoiOS | auth-system | $4.50/hr | 3 alerts | 🔔2 | Profile  │
├────┬───────────────────────────────────────┬──────────────────────┤
│[≡] │ MAIN OPERATIONS AREA                  │ AGENT STATUS PANEL   │
│Nav │                                       │ ──────────────────   │
│─── │ ┌─────────────────────────────────┐  │ AGENTS (4/2/1)       │
│[H] │ │ WORKFLOWS (3 active, 1 at risk) │  │ ● AgentX [████░] 15m │
│[B] │ │┌───────────────────────────────┐│  │   Auth System        │
│[G] │ ││[●] Auth System        BUILDING││  │   $1.20/hr ↗︎        │
│[S] │ ││ Progress: ████████░░ 13/20    ││  │                      │
│[A] │ ││ Last: PR #234 • 5m ago        ││  │ ● AgentY [██░░░] 32m │
│[P] │ ││ Next: Integration tests (15m) ││  │   Payment Integ      │
│    │ ││ Blocked: 0 | At risk: 2       ││  │   $0.80/hr →         │
│    │ ││ [Logs] [Pause] [Scope]        ││  │                      │
│    │ │└───────────────────────────────┘│  │ ○ AgentZ [Idle]      │
│    │ │┌───────────────────────────────┐│  │   Available          │
│    │ ││[⚠] Payment Integ      AT RISK││  │                      │
│    │ ││ Progress: ███░░░░░░░ 4/15     ││  │ ⚠ AgentA [Waiting]   │
│    │ ││ Last: Tests failing • 12m ago ││  │   Rate limited       │
│    │ ││ Issue: DB migration pending   ││  │   (resets 12m)       │
│    │ ││ [View Issues] [Intervene]     ││  │                      │
│    │ │└───────────────────────────────┘│  │ ─────────────────    │
│    │ └─────────────────────────────────┘  │ Total: $4.50/hr      │
│    │                                       │ Today: $32.15        │
│    │ TASK QUEUE (8 pending)                │ Budget: $150/mo      │
│    │ [CRITICAL] Fix auth timeout (Phase 2) │ ─────────────────    │
│    │ [HIGH] Add rate limiting (Phase 2)    │ [Spawn Agent]        │
│    │ [MEDIUM] Update docs (Phase 3)        │                      │
│    │ + 5 more [View All]                   │                      │
└────┴───────────────────────────────────────┴──────────────────────┘
                         │
                         │ ⚠ 3 DECISIONS NEEDED
                         │
                         ▼
┌────────────────────────────────────────────────────────────────────┐
│ INTERVENTION QUEUE (slides up from bottom)                        │
│ ┌───┬──────────────────────────────────────────────────────────┐ │
│ │🔴 │ HIGH: Auth System - Security Decision                    │ │
│ │   │ Agent needs approval for session timeout: 15m vs 60m     │ │
│ │   │ Tradeoff: Security vs UX. Similar systems use 30m.       │ │
│ │   │ [Context] [Approve 30m] [Custom]                2m ago   │ │
│ ├───┼──────────────────────────────────────────────────────────┤ │
│ │🟡 │ MED: Payment Integration - API Choice                    │ │
│ │   │ Stripe vs PayPal - agent recommends Stripe (better docs) │ │
│ │   │ Impact: 2 dependent tasks blocked                        │ │
│ │   │ [Analysis] [Approve] [Override]               8m ago    │ │
│ └───┴──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

**Characteristics**:
- All critical info visible at once (no navigation required)
- Real-time burn rates and ETAs
- Persistent agent status (always visible)
- Intervention queue surfaces decisions immediately
- Sparklines/progress bars show trends
- Compact, scannable rows

---

## Detailed Component Mockups

### 1. Mission Control Dashboard (Main View)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [≡] OmoiOS                                          ⚠3  🔔2  👤 Profile  │
├──┬───────────────────────────────────────────────────┬──────────────────┤
│≡ │ PROJECT: auth-system                              │ AGENTS (4/2/1)   │
│  │ Status: 🟢 HEALTHY | Burn: $4.50/hr | Budget: 72% │ ───────────────  │
│H │ ───────────────────────────────────────────────── │ ACTIVE (4)       │
│B │                                                    │ ● Worker-1       │
│G │ WORKFLOWS (Filter: [All▼] [Phase▼] [Status▼])   │   [████████░] 85% │
│S │ ┌────────────────────────────────────────────┐   │   Auth/JWT       │
│A │ │ [●] Auth System Implementation      ACTIVE │   │   $1.20/h ↗︎ 15m  │
│P │ │ ──────────────────────────────────────────  │   │                  │
│  │ │ Phase: IMPLEMENTATION | Agent: Worker-1    │   │ ● Worker-2       │
│  │ │ Progress: ████████████░░░ 13/20 (65%)      │   │   [███░░░░░░] 30% │
│  │ │ ▁▂▃▄▅▃▂▁ (24h velocity)                    │   │   Payment/Stripe │
│  │ │ ──────────────────────────────────────────  │   │   $0.80/h → 32m  │
│  │ │ Last: PR #234 opened • 5m ago              │   │                  │
│  │ │ Next: Integration tests (est. 15m)         │   │ ● Worker-3       │
│  │ │ Blocked: 0 | At risk: 2 | Budget: $3.20/$5 │   │   [██░░░░░░░] 25% │
│  │ │ ──────────────────────────────────────────  │   │   Email/Sendgrid │
│  │ │ [Logs] [Pause] [Scope] [Graph]             │   │   $0.65/h → 8m   │
│  │ └────────────────────────────────────────────┘   │                  │
│  │                                                    │ ● Validator-1    │
│  │ ┌────────────────────────────────────────────┐   │   [███████░░] 70% │
│  │ │ [⚠] Payment Integration              RISK  │   │   Testing/Auth   │
│  │ │ ──────────────────────────────────────────  │   │   $0.45/h → 5m   │
│  │ │ Phase: IMPLEMENTATION | Agent: Worker-2    │   │                  │
│  │ │ Progress: ████░░░░░░░░ 4/15 (27%)          │   │ IDLE (2)         │
│  │ │ ▁▁▁▁▁░░░ (stalled 12m)                     │   │ ○ Worker-4       │
│  │ │ ──────────────────────────────────────────  │   │ ○ Validator-2    │
│  │ │ Issue: 3 test failures, DB migration blocked│  │                  │
│  │ │ Last: Tests failed • 12m ago               │   │ ISSUES (1)       │
│  │ │ Next: Waiting on DB migration              │   │ ⚠ Worker-5       │
│  │ │ Budget: $1.80/$3.00 (60%)                  │   │   Rate limited   │
│  │ │ ──────────────────────────────────────────  │   │   (12m reset)    │
│  │ │ [Logs] [Diagnose] [Unblock] [Reassign]     │   │                  │
│  │ └────────────────────────────────────────────┘   │ ───────────────  │
│  │                                                    │ [+ Spawn Agent]  │
│  │ ┌────────────────────────────────────────────┐   │                  │
│  │ │ [✓] Email Service                      DONE│   │ SYSTEM METRICS   │
│  │ │ ──────────────────────────────────────────  │   │ Queue: 8 pending │
│  │ │ Phase: DEPLOYMENT | Completed: 8m ago      │   │ Avg wait: 4.2m   │
│  │ │ Cost: $0.85 | Tests: 12/12 ✓               │   │ Throughput: 3.5/h│
│  │ │ [View Details] [Archive]                   │   │                  │
│  │ └────────────────────────────────────────────┘   └──────────────────┘
│  │                                                    
│  │ TASK QUEUE (8 pending) [Expand ▼]
│  │ ┌────────────────────────────────────────────┐
│  │ │ [!] Fix auth token timeout      Phase 2    │
│  │ │     Blocked by: None | ETA: 20m            │
│  │ │ [!] Add rate limiting to API    Phase 2    │
│  │ │     Blocked by: Auth System | ETA: 1.5h    │
│  │ │ + 6 more [View Full Queue]                 │
│  │ └────────────────────────────────────────────┘
└──┴───────────────────────────────────────────────────────────────┘
                         ▲
                         │ Bottom drawer slides up
                         │
┌────────────────────────────────────────────────────────────────────┐
│ ⚠ INTERVENTION QUEUE (3 items need your input)                    │
│ ┌────┬──────────────────────────────────────────────────────────┐│
│ │ 🔴 │ HIGH: Auth System - Security Decision              2m ago││
│ │    │ Agent needs session timeout decision: 15m vs 60m          ││
│ │    │ Tradeoff: Security (15m) vs UX (60m). Similar: 30m        ││
│ │    │ Context: OWASP recommends 15m, but our users are power... ││
│ │    │ [View Full Analysis] [Approve 30m] [Custom]               ││
│ ├────┼──────────────────────────────────────────────────────────┤│
│ │ 🟡 │ MED: Payment Integration - API Choice              8m ago││
│ │    │ Stripe vs PayPal - Agent recommends Stripe (better docs) ││
│ │    │ Impact: 2 dependent tasks blocked waiting on decision     ││
│ │    │ Cost: Stripe 2.9%+30¢, PayPal 3.49%+49¢ per transaction  ││
│ │    │ [View Comparison] [Approve Stripe] [Override to PayPal]   ││
│ └────┴──────────────────────────────────────────────────────────┘│
│ [Minimize Queue]                                                   │
└────────────────────────────────────────────────────────────────────┘
```

**Key Differences**:
1. **Persistent Panels**: Agent status always visible (no navigation to `/agents`)
2. **Intervention Queue**: Surfaces decisions immediately (no hunting through notifications)
3. **Higher Density**: More info per pixel (sparklines, burn rates, ETAs)
4. **Real-Time Focus**: Live metrics (burn rate, ETAs) vs. static stats
5. **Dark Mode Priority**: Easier on eyes for long monitoring sessions

---

## Key Interface Patterns

### Pattern 1: The Agent Status Panel (Persistent Left/Right)

**Current Design**: Navigate to `/agents` page to see agent status.

**Mission Control Design**: Always-visible panel.

```
┌──────────────────────────┐
│ AGENTS (4 active)        │
│ ──────────────────────── │
│ ACTIVE (4)               │
│ ● Worker-1  [████████░]  │
│   Auth/JWT       85% 15m │
│   $1.20/h ↗︎             │
│                          │
│ ● Worker-2  [███░░░░░░]  │
│   Payment/API    30% 32m │
│   $0.80/h →             │
│                          │
│ ● Worker-3  [██░░░░░░░]  │
│   Email/Send     25% 8m  │
│   $0.65/h ↗︎             │
│                          │
│ ● Validator-1 [███████░] │
│   Test/Auth      70% 5m  │
│   $0.45/h ↗︎             │
│                          │
│ IDLE (2)                 │
│ ○ Worker-4               │
│ ○ Validator-2            │
│                          │
│ ISSUES (1)               │
│ ⚠ Worker-5               │
│   Rate limited (12m)     │
│                          │
│ ──────────────────────── │
│ Total: $4.50/hr          │
│ Today: $32.15            │
│ Budget: $150 (72% used)  │
│ ──────────────────────── │
│ [+ Spawn Agent]          │
│ [View All Logs]          │
└──────────────────────────┘
```

**Benefits**:
- Instant visibility into all agent states
- Real-time burn rate tracking
- Identify idle capacity at a glance
- Spot rate-limited/stuck agents immediately

**Information Revealed**:
- Which agents are working (green dot)
- What they're working on (task name)
- Progress estimate (progress bar + ETA)
- Cost burn rate ($/hr with trend arrow)
- Issues requiring attention (rate limits, failures)

---

### Pattern 2: High-Density Workflow Cards

**Current Design**: Simple card with title, status, progress bar.

```
┌─────────────────────────────┐
│ Auth System Implementation  │
│                             │
│ Status: Building            │
│ Progress: ████████░░ 65%    │
│ Agent: Worker-1             │
│                             │
│ [View Details]              │
└─────────────────────────────┘
```

**Mission Control Design**: Data-rich card with actionable metrics.

```
┌──────────────────────────────────────────────────┐
│ [●] Auth System Implementation          BUILDING │
│ ──────────────────────────────────────────────── │
│ [👤Worker-1] [P2 Implementation] [🔗 auth-repo]  │
│ ──────────────────────────────────────────────── │
│ Progress: ████████████░░░ 13/20 tasks (65%)      │
│ ▁▂▃▄▅▃▂▁ Velocity: 3.2 tasks/hr (trending up)    │
│ ──────────────────────────────────────────────── │
│ Last: PR #234 opened by Worker-1 • 5m ago        │
│ Next: Integration tests (est. 15m, 80% confident)│
│ ──────────────────────────────────────────────── │
│ Blocked: 0 | At risk: 2 (tests flaky)            │
│ Budget: $3.20 / $5.00 (64% used)                 │
│ ETA: 45m (if velocity maintains)                 │
│ ──────────────────────────────────────────────── │
│ Quick: [Logs] [Pause] [Adjust Scope] [Graph]     │
└──────────────────────────────────────────────────┘
```

**Additional Data Points**:
- **Sparkline**: Visual trend (velocity increasing/decreasing)
- **Last/Next Actions**: Clear progression understanding
- **Risk Indicators**: "At risk: 2" tells you what needs attention
- **Budget Burn**: Know if workflow is over-budget
- **ETA with Confidence**: "45m (if velocity maintains)" is actionable

---

### Pattern 3: The Intervention Queue (Bottom Drawer)

**Current Design**: Notifications in bell icon, approvals scattered across pages.

**Mission Control Design**: Dedicated queue for all human decisions.

```
┌────────────────────────────────────────────────────────────────────┐
│ ⚠ INTERVENTION QUEUE (3)                         [Minimize] [Clear]│
│ ──────────────────────────────────────────────────────────────────  │
│ ┌────┬──────────────────────────────────────────────────────────┐ │
│ │ 🔴 │ HIGH: Auth System - Security Decision              2m ago│ │
│ │    │ ──────────────────────────────────────────────────────── │ │
│ │    │ Question: Session timeout setting                        │ │
│ │    │ Options: 15 minutes (secure) vs 60 minutes (UX-friendly) │ │
│ │    │                                                          │ │
│ │    │ Agent Analysis:                                          │ │
│ │    │ • OWASP recommends 15m for sensitive apps                │ │
│ │    │ • Our users are power users (engineers), 60m acceptable  │ │
│ │    │ • Similar systems (GitHub, GitLab) use 30m compromise    │ │
│ │    │ • Recommendation: 30 minutes                             │ │
│ │    │                                                          │ │
│ │    │ Impact: Blocks 1 dependent task (login flow testing)    │ │
│ │    │ ──────────────────────────────────────────────────────── │ │
│ │    │ [View Full Context] [Approve 30m] [Custom Value]         │ │
│ ├────┼──────────────────────────────────────────────────────────┤ │
│ │ 🟡 │ MED: Payment Integration - Vendor Selection        8m ago│ │
│ │    │ ──────────────────────────────────────────────────────── │ │
│ │    │ Decision: Stripe vs PayPal for payment processing        │ │
│ │    │                                                          │ │
│ │    │ Stripe:                         PayPal:                  │ │
│ │    │ + Better docs (Agent found)     + Slightly cheaper       │ │
│ │    │ + Faster integration (2d est)   - Worse docs             │ │
│ │    │ - 2.9% + 30¢ per txn           - 3d integration est      │ │
│ │    │                                                          │ │
│ │    │ Agent Recommendation: Stripe (better DX for engineers)   │ │
│ │    │ Impact: 2 dependent tasks blocked (checkout, webhooks)   │ │
│ │    │ ──────────────────────────────────────────────────────── │ │
│ │    │ [View Analysis] [Approve Stripe] [Override to PayPal]    │ │
│ ├────┼──────────────────────────────────────────────────────────┤ │
│ │ 🟢 │ LOW: Email Templates - Design QA                  15m ago│ │
│ │    │ ──────────────────────────────────────────────────────── │ │
│ │    │ Generated 3 email templates (Welcome, Reset, Verify)     │ │
│ │    │ Impact: None (optional polish, no blockers)              │ │
│ │    │ ──────────────────────────────────────────────────────── │ │
│ │    │ [Preview Templates] [Approve All] [Edit]                 │ │
│ └────┴──────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

**Benefits**:
- **All decisions in one place**: No hunting through pages
- **Prioritized by urgency**: Color-coded, sorted by impact
- **Context-rich**: Agent provides analysis, not just a question
- **Inline actions**: Approve/reject without navigation
- **Impact visibility**: See what's blocked by each decision

---

### Pattern 4: Compact Task Queue

**Current Design**: Navigate to `/projects/:id/tasks/phases` to see task list.

**Mission Control Design**: Inline, collapsible queue on main view.

```
┌────────────────────────────────────────────────────┐
│ TASK QUEUE (8 pending, 4 running, 12 done)        │
│ [All▼] [Pending] [Running] [Blocked] [By Phase▼] │
│ ──────────────────────────────────────────────────│
│ PENDING (8)                                        │
│ [!] Fix auth token timeout           P2  CRITICAL │
│     Blocked: None | ETA: 20m | Agent: (next)      │
│ [!] Add rate limiting to API         P2  HIGH     │
│     Blocked: Auth System | ETA: 1.5h | Agent: TBD │
│ [ ] Update docs for JWT flow         P3  MEDIUM   │
│     Blocked: None | ETA: 30m | Agent: (next)      │
│ + 5 more [Expand Queue]                           │
│ ──────────────────────────────────────────────────│
│ RUNNING (4)                                        │
│ [●] Implement JWT token generation   P2  Worker-1 │
│     Started: 15m ago | ETA: 10m | Progress: 85%   │
│ [●] Build Stripe integration         P2  Worker-2 │
│     Started: 32m ago | ETA: 18m | Progress: 30%   │
│ + 2 more [View All Running]                       │
└────────────────────────────────────────────────────┘
```

**Information at a Glance**:
- How many tasks pending/running/done
- Which tasks are blocked (and by what)
- ETAs for completion
- Which agent is working on what
- Priority indicators ([!] for critical)

---

### Pattern 5: Mini Sparklines Everywhere

**Concept**: Show trends, not just snapshots.

**Examples**:

**Workflow Velocity (24h)**:
```
Progress: ████████░░ 65%  ▁▂▃▄▅▃▂▁ (accelerating)
```

**Cost Burn Trend**:
```
Burn: $4.50/hr  ▃▄▅▆▇▆▅▄ (spiking, investigate)
```

**Agent Utilization (7d)**:
```
Capacity: 4/6 agents  ░▂▃▅▇▇▆▅ (peaking, spawn more?)
```

**Test Pass Rate (24h)**:
```
Tests: 45/50 passing  ▇▇▇▅▃▂▁░ (degrading, alert!)
```

**Benefits**:
- Instant trend recognition
- Proactive problem detection
- No need to click into charts

---

## Interaction Flow Examples

### Example 1: Monitoring Active Work (No Clicks Required)

**User opens OmoiOS**:
```
1. Dashboard loads
   ↓
2. User scans Agent Status Panel (right side):
   - 4 agents active (green dots pulsing)
   - Worker-1: 85% done with Auth/JWT, $1.20/hr, 15m ETA
   - Worker-2: 30% done with Payment/API, $0.80/hr, 32m ETA
   - Worker-3: 25% done with Email/Send, $0.65/hr, 8m ETA
   - Validator-1: 70% done with Testing/Auth, $0.45/hr, 5m ETA
   ↓
3. User scans Workflows section:
   - Auth System: 65% complete, velocity trending up (sparkline)
   - Payment Integration: AT RISK (27% complete, stalled 12m)
   ↓
4. User notices Intervention Queue badge: "⚠ 3"
   ↓
5. User clicks badge → Bottom drawer slides up
   ↓
6. User sees:
   - HIGH: Security decision (2m old)
   - MEDIUM: API vendor choice (8m old, blocking 2 tasks)
   - LOW: Template review (15m old, no blockers)
   ↓
7. User clicks "Approve 30m" on security decision
   ↓
8. Intervention dismissed, agent unblocked, work continues
   ↓
Total time: ~30 seconds, zero navigation clicks
```

**vs. Current Approach**:
```
1. User opens dashboard
2. Clicks "Notifications" bell
3. Sees: "Agent needs decision" (no context)
4. Clicks notification → Navigates to ticket detail page
5. Clicks "Approvals" tab
6. Reads full context
7. Clicks "Approve" button
8. Navigates back to dashboard
↓
Total time: ~2-3 minutes, 5+ clicks
```

---

### Example 2: Spotting Problems Proactively

**Scenario**: Payment Integration workflow stalls.

**Mission Control View**:
```
┌────────────────────────────────────────────┐
│ [⚠] Payment Integration              RISK  │
│ ──────────────────────────────────────────  │
│ Progress: ████░░░░░░░░ 4/15 (27%)          │
│ ▁▁▁▁▁░░░ (velocity: 0 tasks/hr, stalled)   │
│ ──────────────────────────────────────────  │
│ Issue: 3 test failures, DB migration blocked│
│ Last: Tests failed • 12m ago               │
│ Agent: Worker-2 (stuck on error loop)      │
│ ──────────────────────────────────────────  │
│ [Auto-Diagnose] [View Logs] [Reassign]     │
└────────────────────────────────────────────┘
```

**User Actions**:
1. Sees "AT RISK" badge immediately (orange)
2. Sees sparkline flatlined (zero velocity)
3. Sees "Issue: 3 test failures" in card
4. Clicks "Auto-Diagnose" button
5. System runs diagnostic, suggests:
   - "DB migration is blocking. Run migration first?"
6. User clicks "Approve Migration" inline
7. Workflow unblocks, velocity resumes

**vs. Current Approach**:
- User might not notice stall until checking stats page
- No sparkline to show velocity drop
- Would need to navigate to task detail to see errors
- Manual diagnosis required

---

### Example 3: Budget Management in Real-Time

**Mission Control View**:
```
┌──────────────────────┐
│ SYSTEM METRICS       │
│ ──────────────────── │
│ Burn Rate: $4.50/hr  │
│ ▃▄▅▆▇▆▅▄ (spiking)   │
│                      │
│ Today: $32.15        │
│ Month: $108 / $150   │
│ Remaining: 9.3 days  │
│                      │
│ ⚠ High-cost agents:  │
│ • Worker-1: $1.20/hr │
│ • Worker-2: $0.80/hr │
│                      │
│ [Set Budget Alert]   │
│ [Pause Non-Critical] │
└──────────────────────┘
```

**Proactive Alerts**:
- If burn rate * remaining hours > budget:
  - Intervention appears: "Budget will exceed in 9 days at current rate"
  - Options: [Pause Low-Priority] [Increase Budget] [Optimize]

**Benefits**:
- Constant budget awareness
- Proactive intervention before overage
- Identify cost-heavy agents/workflows

---

## Visual Comparison: Same Data, Different Density

### Current Design: Agents Overview Page

```
┌─────────────────────────────────────────────────┐
│ Agents Overview                  [Spawn Agent]  │
├─────────────────────────────────────────────────┤
│                                                  │
│ Agent Metrics                                    │
│ ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐         │
│ │  5   │  │  3   │  │  2   │  │  0   │         │
│ │Total │  │Active│  │ Idle │  │Stuck │         │
│ └──────┘  └──────┘  └──────┘  └──────┘         │
│                                                  │
│ Average Alignment: 78%                           │
│ Tasks Completed Today: 12                        │
│                                                  │
│ ┌───────────────────────────────────────────┐   │
│ │ Agent: worker-1                           │   │
│ │ Status: 🟢 Active                         │   │
│ │ Phase: PHASE_IMPLEMENTATION               │   │
│ │ Current Task: "Implement JWT"            │   │
│ │ Alignment: 85%                            │   │
│ │ Tasks Completed: 8                        │   │
│ │ [View Details] [Intervene]                │   │
│ └───────────────────────────────────────────┘   │
│                                                  │
│ ┌───────────────────────────────────────────┐   │
│ │ Agent: worker-2                           │   │
│ │ Status: 🟡 Idle                           │   │
│ │ ... (similar card)                        │   │
│ └───────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

**Pixel Count**: ~800px tall for 2 agents.

---

### Mission Control Design: Agent Status Panel

```
┌─────────────────────────┐
│ AGENTS (5) $4.5/hr      │
│ ─────────────────────── │
│ ● Worker-1 [████████░]  │
│   JWT/Auth   85%   15m  │
│   $1.20/h ↗︎            │
│ ● Worker-2 [███░░░░░░]  │
│   Stripe/Pay 30%   32m  │
│   $0.80/h →            │
│ ○ Worker-3 [Idle]       │
│ ○ Worker-4 [Idle]       │
│ ⚠ Worker-5 [Rate limit] │
│   (resets 12m)          │
│ ─────────────────────── │
│ Align avg: 78%          │
│ Done today: 12          │
│ ─────────────────────── │
│ [+ Spawn] [All Logs]    │
└─────────────────────────┘
```

**Pixel Count**: ~320px tall for 5 agents.

**Density Gain**: 2.5x more information in less space.

---

## Layout Variants

### Variant A: Traditional (Current)
- **Navigation**: Left sidebar, click to switch views
- **Content**: One view at a time (Board OR Graph OR Stats)
- **Agents**: Separate page
- **Approvals**: Separate page or notifications

**Pros**: Familiar, clean, easy to implement.
**Cons**: Requires navigation, context switching, slower decision-making.

---

### Variant B: Mission Control (Recommended Exploration)
- **Navigation**: Icon-only rail (collapsed)
- **Content**: Main view + persistent Agent Panel + Intervention Drawer
- **Agents**: Always visible (right panel, 300px)
- **Approvals**: Immediate (bottom drawer, slides up)

**Pros**: All critical info visible, faster decisions, real-time awareness.
**Cons**: More complex layout, requires careful information hierarchy.

---

### Variant C: Hybrid (Best of Both)
- **Default**: Traditional layout (familiar onboarding)
- **Power Mode**: Toggle to Mission Control layout (Cmd+Shift+M)
- **Customizable**: Users choose which panels persist

**Pros**: Serves both casual users and power users.
**Cons**: More design/dev work, need to maintain two layouts.

---

## When to Use Mission Control vs. Traditional

### Use Mission Control When:
- User is **actively monitoring** multiple parallel workflows
- **Real-time decisions** are frequent (intervention queue active)
- **Cost/budget management** is critical
- User is managing **5+ concurrent agents**
- **Time-sensitivity** is high (production incidents, tight deadlines)

### Use Traditional When:
- User is **planning** (creating specs, designing workflows)
- **Single workflow focus** (working on one ticket)
- **Onboarding** new users (simpler mental model)
- **Configuring settings** (less need for real-time data)

---

## Proposed Approach: Progressive Density

**Level 1: Default (Linear-Style)**
- Clean, minimal, spacious
- One view at a time
- For: Onboarding, planning, configuration

**Level 2: Compact Mode (Toggle)**
- Tighter spacing, smaller fonts
- Same layout, more info visible
- For: Users who want efficiency

**Level 3: Mission Control (Toggle)**
- Persistent panels, intervention queue
- High density, sparklines, real-time metrics
- For: Active monitoring, multi-workflow management

**User Control**:
- Settings → Appearance → Density: [Comfortable] [Compact] [Mission Control]
- Save preference per user
- Quick toggle: Cmd+D cycles through modes

---

## Next Steps: Validation Questions

Before committing to Mission Control, answer:

1. **How often do users need to see ALL agents simultaneously?**
   - If rarely: Traditional is fine.
   - If constantly: Mission Control wins.

2. **How many workflows run in parallel typically?**
   - 1-2: Traditional.
   - 5+: Mission Control.

3. **How critical is real-time cost awareness?**
   - Nice-to-have: Traditional with stats page.
   - Critical: Mission Control with persistent burn metrics.

4. **What's the intervention frequency?**
   - Rare (1-2/day): Notifications work fine.
   - Frequent (5+/hour): Intervention queue essential.

5. **Target user skill level?**
   - Junior/Mixed: Traditional (gentler learning curve).
   - Senior/Power users only: Mission Control (optimize for experts).

---

## Recommendation

**Implement Variant C: Hybrid Approach**

1. **V1**: Ship with Traditional layout (faster to build, familiar UX)
2. **V1.5**: Add "Compact Mode" toggle (tighter spacing, smaller fonts)
3. **V2**: Add "Mission Control Mode" toggle (persistent panels, intervention drawer)
4. **V3**: Add customization (users choose which panels persist)

**Rationale**:
- Serves both new users (Traditional) and power users (Mission Control)
- De-risks launch (start simple, add complexity based on user feedback)
- Allows A/B testing (which layout do users actually prefer?)
- Incremental development (each mode builds on previous)

**Development Sequence**:
1. Build Traditional layout (80% of page_flow.md as-is)
2. Extract layout components (header, sidebar, main content)
3. Create Compact variant (CSS adjustments)
4. Build Mission Control layout (new components: Agent Panel, Intervention Drawer)
5. Add toggle mechanism (layout switcher in settings)

---

## Visual Mockups

### Mission Control Dashboard (Full Layout)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ [≡] OmoiOS | auth-system | 🟢 HEALTHY | $4.50/hr ↗︎ | Budget: 72% | ⚠3 🔔2 👤      │
├───┬─────────────────────────────────────────────────────────┬───────────────────────┤
│[≡]│ WORKFLOWS (3 active, 1 at risk, 1 done)                 │ AGENTS (4 active)     │
│   │ ────────────────────────────────────────────────────    │ ───────────────────   │
│[H]│ ┌─────────────────────────────────────────────────┐     │ ACTIVE (4)            │
│[B]│ │[●] Auth System Implementation          BUILDING │     │ ● Worker-1            │
│[G]│ │ ─────────────────────────────────────────────── │     │   [████████░] 85% 15m │
│[S]│ │ [👤W-1] [P2] [🔗auth] | 13/20 ████████░░ 65%    │     │   Auth/JWT            │
│[A]│ │ ▁▂▃▄▅▃▂▁ Velocity: 3.2/hr (up) | ETA: 45m       │     │   $1.20/h ↗︎          │
│[P]│ │ Last: PR #234 • 5m | Next: Integration tests    │     │                       │
│   │ │ Risk: 2 flaky tests | $3.20/$5 (64%)            │     │ ● Worker-2            │
│   │ │ [Logs] [Pause] [Graph]                          │     │   [███░░░░░░] 30% 32m │
│   │ └─────────────────────────────────────────────────┘     │   Payment/Stripe      │
│   │                                                           │   $0.80/h →          │
│   │ ┌─────────────────────────────────────────────────┐     │                       │
│   │ │[⚠] Payment Integration                    RISK  │     │ ● Worker-3            │
│   │ │ ─────────────────────────────────────────────── │     │   [██░░░░░░░] 25% 8m  │
│   │ │ [👤W-2] [P2] [🔗pay] | 4/15 ████░░░ 27%         │     │   Email/Sendgrid      │
│   │ │ ▁▁▁▁▁░░░ Velocity: 0/hr (STALLED 12m)          │     │   $0.65/h ↗︎          │
│   │ │ Issue: 3 test fails, DB migration blocked       │     │                       │
│   │ │ Last: Tests failed • 12m | Next: Waiting        │     │ ● Validator-1         │
│   │ │ $1.80/$3 (60%)                                  │     │   [███████░] 70% 5m   │
│   │ │ [Diagnose] [Logs] [Unblock] [Reassign]          │     │   Testing/Auth        │
│   │ └─────────────────────────────────────────────────┘     │   $0.45/h ↗︎          │
│   │                                                           │                       │
│   │ ┌─────────────────────────────────────────────────┐     │ IDLE (2)              │
│   │ │[✓] Email Service                          DONE  │     │ ○ Worker-4            │
│   │ │ Phase: DEPLOYMENT | Done: 8m ago | $0.85        │     │ ○ Validator-2         │
│   │ │ [Details] [Archive]                             │     │                       │
│   │ └─────────────────────────────────────────────────┘     │ ISSUES (1)            │
│   │                                                           │ ⚠ Worker-5            │
│   │ TASK QUEUE (8 pending) [Expand ▼]                        │   Rate limited (12m)  │
│   │ [!] Fix auth timeout        P2  CRITICAL  20m ETA         │                       │
│   │ [!] Add rate limiting       P2  HIGH      1.5h (blocked)  │ ───────────────────   │
│   │ + 6 more [View All]                                       │ Total: $4.50/hr       │
│   │                                                           │ Today: $32.15         │
│   │                                                           │ Budget: 72% used      │
│   │                                                           │ [Spawn] [All Logs]    │
└───┴───────────────────────────────────────────────────────────┴───────────────────────┘
                                    │
                                    │ ⚠ 3 INTERVENTIONS
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ INTERVENTION QUEUE                                             [Minimize] [Clear All]│
│ ─────────────────────────────────────────────────────────────────────────────────── │
│ ┌────┬──────────────────────────────────────────────────────────────────────────┐   │
│ │ 🔴 │ HIGH: Auth System - Security Decision                              2m ago│   │
│ │    │ Agent needs session timeout: 15m (secure) vs 60m (UX-friendly)            │   │
│ │    │ Recommendation: 30m (industry standard) | Impact: Blocks login testing    │   │
│ │    │ [View Context] [Approve 30m] [Custom]                                     │   │
│ ├────┼──────────────────────────────────────────────────────────────────────────┤   │
│ │ 🟡 │ MED: Payment Integration - Vendor Selection                        8m ago│   │
│ │    │ Stripe (better docs, faster) vs PayPal (cheaper) | Impact: 2 tasks blocked│   │
│ │    │ [View Analysis] [Approve Stripe] [Override]                               │   │
│ ├────┼──────────────────────────────────────────────────────────────────────────┤   │
│ │ 🟢 │ LOW: Email Templates - Design Review                              15m ago│   │
│ │    │ 3 templates generated (Welcome, Reset, Verify) | Impact: None (polish)    │   │
│ │    │ [Preview] [Approve All] [Edit]                                            │   │
│ └────┴──────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Information Architecture Changes

### Current IA (Page-Based)
```
Dashboard
├── Projects List
│   └── Project Overview
│       ├── Kanban Board (separate page)
│       ├── Dependency Graph (separate page)
│       ├── Statistics (separate page)
│       ├── Agents (separate page)
│       └── Activity Timeline (separate page)
```

**Navigation Pattern**: Click to switch views, one at a time.

---

### Mission Control IA (Panel-Based)
```
Mission Control Shell
├── Global Header (always visible)
│   ├── Project Selector
│   ├── System Health Indicator
│   ├── Global Metrics (burn rate, budget)
│   └── Notifications / Profile
├── Navigation Rail (icon-only, always visible)
│   ├── [H] Home/Overview
│   ├── [B] Board View
│   ├── [G] Graph View
│   ├── [S] Stats View
│   ├── [A] Agents (toggles panel)
│   └── [P] Settings
├── Agent Status Panel (persistent right, collapsible)
│   ├── Active Agents (with live progress)
│   ├── Idle Agents
│   ├── Issues (stuck, rate-limited)
│   ├── System Metrics (total burn, budget)
│   └── Quick Actions
├── Main Content Area (swappable views)
│   ├── Workflows List (default)
│   ├── Kanban Board (toggle)
│   ├── Dependency Graph (toggle)
│   └── Statistics (toggle)
└── Intervention Drawer (bottom, slides up when items present)
    ├── Decision Queue (prioritized)
    ├── Approval Requests
    └── Guardian Alerts
```

**Navigation Pattern**: Panels persist, main view toggles, minimal navigation.

---

## Specific Use Case: Managing 5 Parallel Workflows

### Current Design Experience:
```
1. User sees Dashboard with 5 workflow cards
2. Clicks Workflow 1 → Navigates to ticket detail
3. Reads status, clicks "Comments" tab
4. Sees agent update, clicks "Back"
5. Clicks "Agents" in sidebar → Navigates to agents page
6. Checks agent status, clicks "Back"
7. Clicks Workflow 2 → Repeat cycle...
```

**Time per workflow check**: ~1-2 minutes
**Total time for 5 workflows**: 5-10 minutes
**Mental overhead**: High (track state across navigation)

---

### Mission Control Experience:
```
1. User opens Mission Control
2. Scans Agent Status Panel (5 seconds):
   - 4 active, 1 idle, 1 rate-limited
   - Worker-1: 85% done, 15m ETA, trending up
   - Worker-2: 30% done, 32m ETA, stalled (⚠)
   - ...
3. Scans Workflows in main area (10 seconds):
   - Auth System: 65%, on track
   - Payment: AT RISK, stalled, issue visible
   - Email: 25%, normal velocity
4. Clicks "Auto-Diagnose" on Payment workflow
5. Sees: "DB migration blocking, run migration?"
6. Clicks "Approve" inline
7. Done. All 5 workflows assessed.
```

**Time for all 5 workflows**: ~30 seconds
**Mental overhead**: Low (everything in peripheral vision)

---

## Trade-Offs Summary

| Aspect | Traditional (Current) | Mission Control |
|--------|----------------------|-----------------|
| **Learning Curve** | Low (familiar) | Medium (dense) |
| **Speed to Insight** | Slow (navigate) | Fast (glance) |
| **Information Density** | Low (one view) | High (multi-pane) |
| **Decision Speed** | Slow (find, click) | Fast (inline queue) |
| **Mobile Friendly** | Yes | No (needs desktop) |
| **Complexity** | Low (simple layout) | High (state management) |
| **Best For** | Planning, reviewing | Monitoring, operating |
| **Development Time** | Faster | Slower |

---

## User Feedback Questions

To decide which direction to go, we need to know:

1. **How many workflows do you expect to monitor simultaneously?**
   - 1-2: Traditional is fine
   - 3-5: Hybrid might be good
   - 6+: Mission Control is valuable

2. **How often will you need to make intervention decisions?**
   - Rarely (few per day): Notifications work
   - Frequently (many per hour): Intervention queue essential

3. **How important is real-time cost visibility?**
   - Nice to have: Stats page is enough
   - Critical: Persistent metrics needed

4. **Are you primarily on desktop or mobile?**
   - Mobile-first: Traditional
   - Desktop-only: Mission Control viable

5. **What's your tolerance for visual complexity?**
   - Prefer simplicity: Traditional
   - Want maximum efficiency: Mission Control

---

## Recommendation

**Start with Traditional (V1), Add Mission Control as V2 Feature**

**Reasoning**:
- Faster to market with familiar UX
- Easier onboarding for new users
- Can validate the data model and backend first
- Add Mission Control later based on user demand
- Allows A/B testing to see which users prefer which mode

**But...**

Design the **data model and APIs** to support Mission Control from day one:
- Real-time metrics (burn rate, ETAs, velocity)
- Intervention queue endpoint (prioritized decisions)
- Agent status streaming (WebSocket updates)
- Sparkline data (24h task velocity, cost trends)

This way, switching to Mission Control later is mostly a frontend change, not a backend rewrite.

