# Progressive Density Roadmap

**Created**: 2025-11-21
**Status**: Implementation Plan
**Purpose**: Roadmap for gradually incorporating Mission Control density features into the traditional Linear-style design

---

## Strategy: Traditional First, Mission Control Later

**Phase 1 (V1)**: Ship with clean Linear-style design (current `page_flow.md`)
**Phase 2-4**: Incrementally add density features based on user feedback

---

## Phase 1: Traditional Linear Design (V1 - Launch)

### What We Ship
- Clean, spacious layout with standard SaaS patterns
- Left sidebar navigation (Home, Board, Graph, Specs, Stats, Agents)
- Single-view main content area
- Collapsible right activity sidebar
- Standard card components (title, status, progress bar)

### Cards Look Like:
```
┌─────────────────────────────┐
│ Auth System Implementation  │
│                             │
│ Status: Building            │
│ Phase: PHASE_IMPLEMENTATION │
│ Agent: Worker-1             │
│                             │
│ Progress: ████████░░ 65%    │
│ 13 of 20 tasks complete     │
│                             │
│ [View Details]              │
└─────────────────────────────┘
```

**No Changes Needed**: Current `page_flow.md` and `page_architecture.md` are good as-is.

---

## Phase 2: Add Real-Time Metrics (V1.5)

### What We Add
Quick wins that add value without changing layout:

**1. Enhanced Workflow Cards**
Add metadata row to existing cards:
```
┌──────────────────────────────────────┐
│ Auth System Implementation           │
│ Status: Building | Phase: P2         │
│ Agent: Worker-1                      │
│                                      │
│ Progress: ████████░░ 65% (13/20)     │
│ ────────────────────────────────────  │
│ Last: PR #234 opened • 5m ago        │ ← NEW
│ Next: Integration tests (est. 15m)   │ ← NEW
│ Budget: $3.20 / $5.00 (64%)          │ ← NEW
│ ────────────────────────────────────  │
│ [View Details] [Logs] [Pause]        │
└──────────────────────────────────────┘
```

**2. Agent Status Widget**
Add collapsible widget to header or right sidebar:
```
┌────────────────────┐
│ AGENTS (4)         │
│ ● Worker-1 (85%)   │
│ ● Worker-2 (30%)   │
│ ○ Worker-3 (Idle)  │
│ ⚠ Worker-4 (Issue) │
│ [View All]         │
└────────────────────┘
```

**3. Cost Indicator in Header**
Show current burn rate in global header:
```
Header: OmoiOS | auth-system | $4.50/hr | Budget: 72% | 🔔 | Profile
```

**Development Effort**: Low (metadata display, no layout changes).

---

## Phase 3: Add Intervention Queue (V2)

### What We Add

**Intervention Notification Badge**
In global header, show count of pending decisions:
```
Header: ... | Notifications 🔔2 | ⚠ Decisions 3 | Profile
```

**Intervention Drawer** (Bottom Slide-Up)
Click "⚠ Decisions 3" → Drawer slides up from bottom:
```
┌─────────────────────────────────────────────────────────────┐
│ DECISIONS NEEDED (3)                        [Minimize] [x]  │
│ ─────────────────────────────────────────────────────────── │
│ ┌────┬────────────────────────────────────────────────┐    │
│ │ 🔴 │ HIGH: Auth timeout decision (2m ago)           │    │
│ │    │ 15m vs 60m - Recommends: 30m                   │    │
│ │    │ [Details] [Approve 30m] [Custom]               │    │
│ ├────┼────────────────────────────────────────────────┤    │
│ │ 🟡 │ MED: Stripe vs PayPal (8m ago)                 │    │
│ │    │ Recommends: Stripe - Blocks 2 tasks            │    │
│ │    │ [Analysis] [Approve] [Override]                │    │
│ └────┴────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**Benefits**:
- All decisions in one place (no hunting)
- Prioritized by urgency
- Inline actions (no navigation)

**Development Effort**: Medium (new component, WebSocket integration).

---

## Phase 4: Add Compact Mode Toggle (V2.5)

### What We Add

**Density Preference** (Settings → Appearance)
```
Density: 
○ Comfortable (default - current spacing)
● Compact (tighter spacing, more info)
```

**Compact Mode Changes**:
- Card padding: `24px` → `12px`
- List item height: `40px` → `32px`
- Font sizes: Body `14px` → `13px`, Small `12px` → `11px`
- Spacing between cards: `16px` → `8px`

**Visual Difference**:
```
COMFORTABLE MODE:
┌─────────────────────────────┐  ← 24px padding
│                             │
│ Auth System Implementation  │  ← 14px font
│                             │
│ Progress: ████████░░ 65%    │
│                             │  ← 16px gap
│ [View Details]              │
│                             │
└─────────────────────────────┘

COMPACT MODE:
┌───────────────────────────┐  ← 12px padding
│ Auth System Implementation│  ← 13px font
│ Progress: ████████░░ 65%  │  ← 8px gap
│ [View Details]            │
└───────────────────────────┘
```

**Benefits**: ~40% more info per screen without layout changes.

**Development Effort**: Low (CSS variables, saved preference).

---

## Phase 5: Add Persistent Agent Panel (V3)

### What We Add

**Agent Panel Toggle** (Settings or Cmd+A)
```
Agent Panel: 
[ ] Show persistent agent status panel
```

When enabled, layout shifts to 3-column:
```
┌─────────────────────────────────────────────────────────────┐
│ Header                                                       │
├──────┬──────────────────────────────────────┬───────────────┤
│ Nav  │ Main Content                         │ AGENTS (4)    │
│ ──── │                                      │ ───────────   │
│      │ [Workflows/Board/Graph/Stats]        │ ● Worker-1    │
│      │                                      │   [████░] 85% │
│      │                                      │   Auth/JWT    │
│      │                                      │   $1.20/h     │
│      │                                      │               │
│      │                                      │ ● Worker-2    │
│      │                                      │   [███░░] 30% │
│      │                                      │   ...         │
└──────┴──────────────────────────────────────┴───────────────┘
```

**Benefits**: Constant agent visibility without navigation.

**Development Effort**: Medium-High (new panel component, layout system).

---

## Phase 6: Add Sparklines & Trends (V3.5)

### What We Add

**Tiny Trend Graphs** on workflow cards:
```
┌──────────────────────────────────────┐
│ Auth System Implementation           │
│                                      │
│ Progress: ████████░░ 65% (13/20)     │
│ ▁▂▃▄▅▃▂▁ Velocity trending up        │ ← NEW
│                                      │
│ Burn: $3.20/$5 ▃▄▅▆▇▆▅▄ (spiking)   │ ← NEW
└──────────────────────────────────────┘
```

**Where to Add**:
- Workflow cards: Task velocity (24h)
- Agent cards: Cost burn trend
- Statistics page: Full sparklines for all metrics

**Development Effort**: Medium (charting library, data aggregation).

---

## Quick Wins for V1 (No Layout Changes)

These add "Mission Control" value without redesigning the layout:

### 1. Add ETAs to Cards
```
Progress: 13/20 tasks (65%)
ETA: 45m (if current velocity maintains)
```

### 2. Show "Last Action" in Cards
```
Last: PR #234 opened by Worker-1 • 5m ago
```

### 3. Add Risk Indicators
```
⚠ At risk: 2 tasks (flaky tests)
```

### 4. Show Budget Burn on Cards
```
Budget: $3.20 / $5.00 (64% used)
```

### 5. Add Status Dots with Animation
```
● Active (pulsing green dot)
○ Idle (static gray dot)
⚠ Issue (static orange/red icon)
```

### 6. Global Burn Rate in Header
```
Header: ... | $4.50/hr ↗︎ | Budget: 72% | ...
```

### 7. Intervention Count Badge
```
Header: ... | Notifications 🔔2 | ⚠ Decisions 3 | ...
```

---

## Implementation Priority

### Must Have (V1)
- [x] Traditional layout (current page_flow.md)
- [ ] Enhanced workflow cards (Last, Next, Budget, Risk)
- [ ] Status dots with pulse animation
- [ ] Global burn rate in header
- [ ] Intervention count badge

### Nice to Have (V1.5)
- [ ] Agent status widget (collapsible)
- [ ] ETAs on all cards
- [ ] Compact mode toggle

### Power Features (V2+)
- [ ] Intervention drawer (bottom slide-up)
- [ ] Persistent agent panel (right sidebar)
- [ ] Sparklines and trend graphs
- [ ] Mission Control full layout mode

---

## Data Requirements

To support these features, ensure APIs provide:

**For Enhanced Cards**:
- `last_action`: Latest event (type, timestamp, description)
- `next_action`: Predicted next step (description, ETA, confidence)
- `risk_indicators`: Count of at-risk items (blocked, flaky, stalled)
- `budget_used`: Amount spent vs. budget allocation
- `budget_percentage`: Percentage used (for progress bar)

**For Agent Status**:
- `current_task_progress`: Percentage complete (0-100)
- `task_eta_seconds`: Estimated time remaining
- `burn_rate_per_hour`: Cost burn rate
- `trend_direction`: "up", "stable", "down" (for arrow indicator)

**For Intervention Queue**:
- `intervention_type`: "decision", "approval", "alert"
- `urgency`: "critical", "high", "medium", "low"
- `context_summary`: Brief description (1-2 sentences)
- `impact`: What's blocked or affected
- `agent_recommendation`: What agent suggests
- `action_options`: Available actions

**For Sparklines**:
- `velocity_24h`: Array of task completion counts per hour (24 values)
- `cost_trend_24h`: Array of cost per hour (24 values)
- `health_trend_7d`: Array of success rates per day (7 values)

---

## Recommendation Summary

**Ship V1 with Traditional Design + Quick Wins**:
1. Keep current page flows and layouts (no changes)
2. Add enhanced workflow cards (Last, Next, Budget, Risk)
3. Add global burn rate indicator in header
4. Add intervention count badge in header
5. Add status pulse animations

**Plan for V2**:
1. Build intervention drawer (bottom slide-up)
2. Build agent status widget (header dropdown or right panel)
3. Add compact mode toggle

**Consider V3** (based on user demand):
1. Full Mission Control layout mode
2. Persistent multi-pane layout
3. Advanced sparklines and trends

This approach:
- ✅ Keeps your current design (no major rework)
- ✅ Adds high-value Mission Control features incrementally
- ✅ De-risks development (ship faster, iterate based on feedback)
- ✅ Serves both casual and power users
- ✅ Allows A/B testing to validate which features users actually use

