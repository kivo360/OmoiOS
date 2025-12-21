# Demo Flow: Start a Feature Before Bed. Wake Up to a PR.

**Part of**: [User Journey Documentation](./README.md)

---

## The Core Message

> **Let AI run overnight and finish your software for you.**

You describe what you want, approve a plan, and go to sleep. While you're away, agents write code, run tests, fix bugs, and create PRs. You wake up to completed work.

---

## Video Demo Script (60 seconds)

This document outlines the ideal flow for a short social media demo video showing OmoiOS in action.

---

## Scene 1: The Setup (8 seconds)

**Narration**: "It's 9 PM. You need to add payment processing to your app."

**Visual**: Clock showing 9:00 PM, developer at laptop

---

## Scene 2: Describe What You Want (8 seconds)

**Narration**: "Just describe what you want built."

**Visual**: User types into Command Center:
```
"Add Stripe payment processing with subscription management"
```
*Click submit*

---

## Scene 3: Approve the Plan (10 seconds)

**Narration**: "OmoiOS generates a complete plan. Review it. Approve it."

**Visual**:
1. Spec Workspace appears with tabs:
   - **Requirements**: User stories with acceptance criteria
   - **Design**: Architecture diagram
   - **Tasks**: 12 discrete tasks

**User Action**: Clicks "Approve Plan"

**Narration**: "Now go to sleep."

**Visual**: 😴 Sleep emoji, clock fast-forwards

---

## Scene 4: Agents Work Overnight (15 seconds)

**Narration**: "While you sleep, agents work through the night."

**Visual**: Time-lapse dashboard showing:

```
┌─────────────────────────────────────────────────────────────┐
│  🌙 Overnight Execution                     Time: 2:34 AM   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Progress: ████████████████████░░░░ 82%                     │
│  Tests: 67/75 passing                                        │
│  Agents: 3 active                                           │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │ Agent 1        │  │ Agent 2        │  │ Agent 3        │ │
│  │ 🟢 Building    │  │ 🟢 Testing     │  │ 🟢 Fixing      │ │
│  │ Checkout API   │  │ Integration    │  │ Edge Case      │ │
│  └────────────────┘  └────────────────┘  └────────────────┘ │
│                                                              │
│  Activity Feed:                                             │
│  2:30 AM - Agent 1 committed subscription logic            │
│  2:32 AM - Agent 2 found edge case → spawned fix           │
│  2:33 AM - Agent 3 picked up fix task                      │
│  2:34 AM - Guardian sent refocus to Agent 1                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Narration**: "They find bugs. They fix them. They keep each other on track."

---

## Scene 5: Guardian Self-Heals (8 seconds)

**Narration**: "If an agent drifts, Guardian brings it back."

**Visual**:
```
┌─────────────────────────────────────────────────────────────┐
│  🛡️ Guardian Intervention                      3:15 AM      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Agent 1 drifting: Adding unrequested features             │
│                                                              │
│  [INTERVENTION SENT]                                        │
│  "Focus on checkout flow. Save optimization for later."    │
│                                                              │
│  Result: ✅ Back on track in 2 minutes                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Narration**: "No manual intervention needed. The system self-heals."

---

## Scene 6: Wake Up to a PR (12 seconds)

**Narration**: "You wake up. There's a PR waiting."

**Visual**:
1. Clock showing 7:00 AM ☀️
2. Notification: "PR #42 ready for review"
3. PR Review Modal:

```
┌─────────────────────────────────────────────────────────────┐
│  PR #42: Add Stripe Payment Processing                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ✅ All tests passing (75/75)                               │
│  ✅ Code review: No issues                                  │
│  ✅ Security scan: Clean                                    │
│                                                              │
│  Files changed: 28 (+3,200 -180)                           │
│  Work completed: 10 hours overnight                        │
│                                                              │
│              [Request Changes]  [Approve & Merge]           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Narration**: "Review it with your coffee. Approve. Merged before standup."

*User clicks "Approve & Merge"*

---

## Scene 7: The Result (5 seconds)

**Visual**: Celebration screen:
```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│             🎉 Feature Shipped                               │
│                                                              │
│         Payment processing with Stripe                      │
│                                                              │
│         Your time: 10 minutes                               │
│         AI work time: 10 hours                              │
│         Ready: Before your first meeting                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Narration**: "10 minutes of your time. 10 hours of AI work. Feature shipped."

---

## Key Talking Points

### The Core Message
> "Let AI run overnight and finish your software for you."

### The Hook
> "Start a feature before bed. Wake up to a PR."

### The Differentiators

1. **Overnight execution**: AI works while you sleep—not just assists while you code
2. **Self-healing**: Guardian keeps agents on track—no babysitting required
3. **Complete features**: Not just code snippets—full features with tests, ready for review
4. **Strategic approval**: You approve the plan and the PR—nothing in between

### Value Props by Audience

| For Engineering Managers | For Senior ICs | For CTOs |
|--------------------------|----------------|----------|
| 24/7 output without scaling team | Wake up to finished work | Ship faster without hiring |
| Monitor in the morning, not overnight | Focus on architecture, not boilerplate | Predictable overnight delivery |
| Features ready before standup | Review when rested, not while working | Compound productivity gains |

---

## The Overnight Promise

```
Traditional Development:
  Feature request → 3-5 days of work → PR → Review → Merge
  Your time: 40+ hours

With OmoiOS:
  9:00 PM - Describe feature, approve plan (5 min)
  9:05 PM - Go to sleep
  7:00 AM - Review PR with coffee (5 min)
  7:05 AM - Feature merged

  Your time: 10 minutes
  AI time: 10 hours
  Shipped: Same morning
```

---

## Page Flow for Demo

### The Overnight Path

1. **Command Center** (`/`) - 9:00 PM: Type feature request
2. **Spec Workspace** (`/projects/:id/specs/:specId`) - 9:02 PM: Review & approve plan
3. **Go to bed** - 9:05 PM
4. **[Agents work overnight - shown in time-lapse]**
5. **Morning notification** - 7:00 AM: PR ready
6. **PR Review Modal** - 7:01 AM: Review & approve
7. **Merged** - 7:05 AM: Before standup

### Key Screens to Highlight

| Screen | What to Show | Why It Matters |
|--------|--------------|----------------|
| Command Center + Clock | Single input, evening time | Start before bed |
| Spec Workspace | Requirements/Design/Tasks | Quick approval |
| Time-lapse Dashboard | Progress advancing, activity feed | AI working overnight |
| Guardian Intervention | Auto-correction at 3 AM | Self-healing while you sleep |
| Morning Notification | PR ready | Wake up to results |
| PR Review | All tests passing | Coffee + merge |

---

## Video Timing Breakdown

| Scene | Duration | Content |
|-------|----------|---------|
| 1. Setup | 8s | It's 9 PM, you need a feature |
| 2. Describe | 8s | Type what you want |
| 3. Approve | 10s | Review plan, approve, go to sleep |
| 4. Overnight | 15s | Agents work (time-lapse) |
| 5. Self-Heal | 8s | Guardian intervention at 3 AM |
| 6. Wake Up | 12s | Morning, PR waiting, approve |
| 7. Result | 5s | 10 min your time, 10 hours AI |

**Total: 66 seconds (~1 min)**

---

## Alternative Versions

### 30-Second Version (TikTok/Reels)
```
"Start a feature before bed. Wake up to a PR."

[0-5s]   9 PM: Type "Add Stripe payments"
[5-10s]  Approve plan → Go to sleep 😴
[10-20s] Time-lapse: Agents working overnight
[20-25s] 7 AM: PR notification → Approve with coffee
[25-30s] "10 min your time. 10 hours AI work. Shipped."
```

### 15-Second Version (Instagram Story)
```
[0-3s]   "Let AI code while you sleep"
[3-8s]   9 PM: Approve plan → 😴
[8-12s]  7 AM: ☕ + PR review
[12-15s] "Wake up to shipped features"
```

---

## Related Documentation

- [00_overview.md](./00_overview.md) - The Overnight Story, Core Promise
- [02_feature_planning.md](./02_feature_planning.md) - Detailed spec workflow
- [03_execution_monitoring.md](./03_execution_monitoring.md) - Agent execution details
- [06a_monitoring_system.md](./06a_monitoring_system.md) - Guardian system details
