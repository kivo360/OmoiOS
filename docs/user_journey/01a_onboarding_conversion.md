# Onboarding Flow - Conversion Optimized

**Part of**: [User Journey Documentation](./README.md)
**Created**: 2025-12-31
**Purpose**: Design an onboarding flow that maximizes conversion to paid tiers

---

## Executive Summary

The goal is to get users to:
1. **Experience the magic** (free tier value)
2. **Hit natural limits** (creates upgrade pressure)
3. **Choose paid tier** (with Founding Member as prominent option)

**Key Insight**: GitHub connection is BLOCKING - nothing works without it. This should be the first real action.

---

## Onboarding Flow Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ONBOARDING FLOW                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STEP 1: Welcome + Value Promise (5 sec)                               │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │  "Welcome, {name}! Ready to ship while you sleep?"            │     │
│  │                                                                │     │
│  │  Here's how it works:                                         │     │
│  │  1. You describe what to build                                │     │
│  │  2. Approve a plan                                            │     │
│  │  3. Wake up to a PR                                           │     │
│  │                                                                │     │
│  │  [Let's Get Started →]                                        │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                              ↓                                          │
│  STEP 2: Connect GitHub (BLOCKING - Required)                          │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │  🔗 Connect Your Code                                          │     │
│  │                                                                │     │
│  │  OmoiOS needs access to create branches and PRs for you.      │     │
│  │                                                                │     │
│  │  [⚫ Connect GitHub]                                           │     │
│  │                                                                │     │
│  │  🔒 We only access repos you explicitly select                │     │
│  │  🔒 You can disconnect anytime                                │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                              ↓                                          │
│  STEP 3: Select Repository                                             │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │  📁 Choose Your First Project                                  │     │
│  │                                                                │     │
│  │  ┌─────────────────────────────────────────────────────────┐  │     │
│  │  │ ○ kevinhill/senior-sandbox        ★ 12  TypeScript      │  │     │
│  │  │ ○ kevinhill/api-gateway           ★ 3   Python          │  │     │
│  │  │ ○ kevinhill/marketing-site        ★ 1   JavaScript      │  │     │
│  │  └─────────────────────────────────────────────────────────┘  │     │
│  │                                                                │     │
│  │  [Continue →]                                                  │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                              ↓                                          │
│  STEP 4: First Spec (Quick Win - Get to Value FAST)                    │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │  ✨ Describe Your First Feature                                │     │
│  │                                                                │     │
│  │  What should we build tonight? (You can start simple)         │     │
│  │                                                                │     │
│  │  ┌─────────────────────────────────────────────────────────┐  │     │
│  │  │ Add a logout button to the navbar that clears the       │  │     │
│  │  │ session and redirects to the login page                 │  │     │
│  │  └─────────────────────────────────────────────────────────┘  │     │
│  │                                                                │     │
│  │  💡 Suggestions:                                              │     │
│  │  • "Add form validation to the contact form"                  │     │
│  │  • "Create a dark mode toggle"                                │     │
│  │  • "Fix the broken link in the footer"                        │     │
│  │                                                                │     │
│  │  [Submit First Spec →]                                         │     │
│  │                                                                │     │
│  │  ⏱️ This will use 1 of your 5 free workflows                  │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                              ↓                                          │
│  STEP 5: Plan Selection (Soft Upsell - Not Blocking)                   │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │  🎉 Your first agent is working!                               │     │
│  │                                                                │     │
│  │  Want to ship even faster? Choose your plan:                  │     │
│  │                                                                │     │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │     │
│  │  │   FREE      │  │    PRO      │  │ ⭐ FOUNDING MEMBER  │   │     │
│  │  │   $0/mo     │  │  $50/mo     │  │    $299 once        │   │     │
│  │  │             │  │             │  │                     │   │     │
│  │  │ 1 agent     │  │ 5 agents    │  │ 5 agents            │   │     │
│  │  │ 5 workflows │  │ 100/month   │  │ 50/month + BYO keys │   │     │
│  │  │             │  │ BYO keys    │  │ Lifetime access     │   │     │
│  │  │             │  │             │  │ 87 spots left       │   │     │
│  │  │ [Current]   │  │ [Upgrade]   │  │ [Claim Lifetime →]  │   │     │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘   │     │
│  │                                                                │     │
│  │  [Skip for now - Continue to Dashboard →]                      │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                              ↓                                          │
│  STEP 6: Dashboard with Active Agent                                   │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │  Your agent is working on: "Add logout button..."             │     │
│  │                                                                │     │
│  │  ████████████░░░░░░░░░░░░░░░░░░  35%                          │     │
│  │                                                                │     │
│  │  📋 Planning → 🔨 Building → 🧪 Testing → ✅ PR Ready         │     │
│  │       ✓           Active                                      │     │
│  │                                                                │     │
│  │  💤 Come back in the morning for your PR!                     │     │
│  │                                                                │     │
│  │  [Set up notifications] [Explore dashboard]                   │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Step Details

### Step 1: Welcome + Value Promise

**Goal**: Set expectations, build excitement, minimal friction.

**UI Components**:
- Animated hero with overnight workflow visualization
- Clear 3-step process explanation
- Single CTA button

**Copy**:
```
Welcome, {firstName}! 👋

Ready to ship while you sleep?

Here's how OmoiOS works:
1. Describe what you want built
2. Approve a quick plan
3. Wake up to a pull request

Your time: 5 minutes | AI work: 8 hours | Result: Feature shipped

[Let's Get Started →]
```

**Technical Notes**:
- Pre-fill name from OAuth/registration
- Track `onboarding_started` analytics event
- Show skip button only after 3 seconds (prevents rushing)

---

### Step 2: Connect GitHub (BLOCKING)

**Goal**: Get GitHub OAuth connected. This is required - no skipping.

**UI Components**:
- Large GitHub button
- Security reassurances
- Permission scope explanation

**Copy**:
```
🔗 Connect Your Code

OmoiOS creates branches and PRs directly in your repos.
We need GitHub access to work our magic.

[Connect GitHub]

🔒 You choose which repos we can access
🔒 We never push to main without your approval
🔒 Disconnect anytime in settings
```

**Technical Notes**:
- OAuth flow with `repo` scope
- Store GitHub token in `user_credentials` table
- On callback, redirect to Step 3
- If user already has GitHub connected, skip to Step 3

---

### Step 3: Select Repository

**Goal**: Create first project linked to a real repo.

**UI Components**:
- Repository list with search/filter
- Language/stars metadata
- "Create new repo" option

**Copy**:
```
📁 Choose Your First Project

Select a repository for your first feature.
Don't worry - you can add more projects later.

[Search repos...]

┌────────────────────────────────────────────┐
│ ● kevinhill/senior-sandbox                 │
│   TypeScript • Updated 2 hours ago         │
├────────────────────────────────────────────┤
│ ○ kevinhill/api-gateway                    │
│   Python • Updated 3 days ago              │
├────────────────────────────────────────────┤
│ ○ kevinhill/marketing-site                 │
│   JavaScript • Updated 1 week ago          │
└────────────────────────────────────────────┘

[Continue →]
```

**Technical Notes**:
- Fetch repos from GitHub API using stored token
- Sort by recent activity
- Create `Project` record on selection
- Create default `Organization` if needed (personal workspace)

---

### Step 4: First Spec (Quick Win)

**Goal**: Get user to submit first feature request. This is the "magic moment."

**UI Components**:
- Large text input
- Suggestion chips for easy starts
- Usage indicator (builds awareness of limits)

**Copy**:
```
✨ Describe Your First Feature

What should we build tonight? Start simple - you can go bigger later.

[Text area with placeholder: "Add a logout button that clears the session..."]

💡 Quick starts:
[Add form validation] [Create dark mode] [Fix broken link]

────────────────────────────────────────────
⏱️ This will use 1 of your 5 free monthly workflows

[Submit First Spec →]
```

**Technical Notes**:
- Create `Spec` record on submission
- Start agent execution immediately (async)
- Track `first_spec_submitted` analytics event
- Show loading state while agent initializes

---

### Step 5: Plan Selection (Soft Upsell)

**Goal**: Introduce paid options while agent is working. Non-blocking.

**UI Components**:
- Three-column pricing comparison
- Founding Member highlighted with urgency
- Skip option clearly visible

**Copy**:
```
🎉 Your first agent is working!

While it runs, check out what's possible with more power:

┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  FREE             PRO                  ⭐ FOUNDING MEMBER           │
│  $0/month         $50/month            $299 one-time               │
│                                                                     │
│  • 1 agent        • 5 agents           • 5 agents                  │
│  • 5 workflows    • 100 workflows      • 50 workflows/mo           │
│  • 2GB storage    • 50GB storage       • 50GB storage              │
│                   • BYO API keys       • BYO API keys              │
│                   • Priority support   • Lifetime access           │
│                                        • Early features            │
│                                                                     │
│  [Current]        [Upgrade]            [Claim Lifetime →]          │
│                                                                     │
│                                        Only 87 of 100 spots left!  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

[Skip for now - Continue to Dashboard →]
```

**Technical Notes**:
- Show real-time "spots remaining" count
- Stripe checkout for Pro/Lifetime
- Track `pricing_viewed` and `upgrade_clicked` events
- Skip goes directly to dashboard

---

### Step 6: Dashboard with Active Agent

**Goal**: Show the agent working, build anticipation, explain next steps.

**UI Components**:
- Agent progress visualization
- Phase indicators (Planning → Building → Testing → PR)
- Notification setup prompt

**Copy**:
```
🚀 Your agent is working!

┌────────────────────────────────────────────────────────────────────┐
│  "Add logout button to navbar"                                     │
│                                                                     │
│  ████████████████░░░░░░░░░░░░░░░░░░░░░░░░  42%                    │
│                                                                     │
│  📋 Planning  →  🔨 Building  →  🧪 Testing  →  ✅ PR Ready        │
│       ✓             Active                                         │
│                                                                     │
│  Estimated completion: ~45 minutes                                 │
└────────────────────────────────────────────────────────────────────┘

💤 You don't need to watch this! Come back in the morning.

┌────────────────────────────────────────────────────────────────────┐
│  📬 Get notified when your PR is ready?                            │
│                                                                     │
│  [Enable Browser Notifications]  [Email me instead]  [No thanks]  │
└────────────────────────────────────────────────────────────────────┘
```

**Technical Notes**:
- WebSocket connection for real-time updates
- Request notification permission
- Store notification preferences
- Mark `onboarding_completed` in user record

---

## Conversion Triggers (Post-Onboarding)

After onboarding, conversion opportunities appear naturally:

### Trigger 1: Workflow Limit Reached

```
┌────────────────────────────────────────────────────────────────────┐
│  ⚠️ You've used 5 of 5 free workflows this month                   │
│                                                                     │
│  Your task is queued. It will run when:                            │
│  • Your limit resets on Jan 1 (4 days)                            │
│  • You upgrade to Pro ($50/mo for 100 workflows)                   │
│  • You claim Founding Member ($299 once for 50/mo forever)         │
│                                                                     │
│  [Upgrade to Pro]  [Claim Founding Member]  [Wait for reset]       │
└────────────────────────────────────────────────────────────────────┘
```

### Trigger 2: Agent Queue

```
┌────────────────────────────────────────────────────────────────────┐
│  🕐 2 tasks queued behind your running agent                       │
│                                                                     │
│  Free tier runs 1 agent at a time.                                 │
│  Pro runs 5 agents in parallel - ship 5x faster.                   │
│                                                                     │
│  [Upgrade to Pro →]  [Keep waiting]                                │
└────────────────────────────────────────────────────────────────────┘
```

### Trigger 3: Morning Email

```
Subject: ☀️ Your PR is ready! + a special offer

Hey {name},

Your feature "Add logout button" is ready for review!

→ View PR: https://github.com/...

You've shipped 3 features this week with OmoiOS.
At this pace, you'll hit your free limit in 2 days.

🔥 Lock in Founding Member access ($299 once) before it's gone:
→ Claim Your Spot (87 left)

Happy shipping,
The OmoiOS Team
```

---

## Analytics Events to Track

| Event | When | Data |
|-------|------|------|
| `onboarding_started` | Step 1 load | user_id, source |
| `github_connected` | OAuth complete | user_id, github_username |
| `repo_selected` | Step 3 complete | user_id, repo_name |
| `first_spec_submitted` | Step 4 complete | user_id, spec_length |
| `pricing_viewed` | Step 5 load | user_id, current_tier |
| `upgrade_clicked` | Any upgrade button | user_id, target_tier |
| `onboarding_completed` | Step 6 complete | user_id, total_time |
| `onboarding_abandoned` | Left mid-flow | user_id, last_step |

---

## Implementation Priority

1. **P0**: Steps 2-3 (GitHub + Repo selection) - Blocking, required
2. **P0**: Step 4 (First spec) - Core value moment
3. **P1**: Step 5 (Plan selection) - Revenue opportunity
4. **P1**: Post-onboarding triggers - Conversion nudges
5. **P2**: Step 1 animation polish
6. **P2**: Morning email sequence

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `frontend/app/(auth)/onboarding/page.tsx` | Modify | Replace with multi-step wizard |
| `frontend/components/onboarding/OnboardingWizard.tsx` | Create | Main wizard container |
| `frontend/components/onboarding/steps/WelcomeStep.tsx` | Create | Step 1 |
| `frontend/components/onboarding/steps/GitHubStep.tsx` | Create | Step 2 |
| `frontend/components/onboarding/steps/RepoSelectStep.tsx` | Create | Step 3 |
| `frontend/components/onboarding/steps/FirstSpecStep.tsx` | Create | Step 4 |
| `frontend/components/onboarding/steps/PlanSelectStep.tsx` | Create | Step 5 |
| `frontend/components/onboarding/UpgradeBanner.tsx` | Create | Reusable upgrade prompt |
| `frontend/hooks/useOnboarding.ts` | Create | Onboarding state management |

---

## Related Documentation

- [Pricing Strategy](../design/billing/pricing_strategy.md) - Tier definitions and pricing
- [Page Flows - Authentication](../page_flows/01_authentication.md) - OAuth flow details
- [Billing Page](../page_flows/11_cost_management.md) - Post-onboarding billing UI

---

**Next**: See [README.md](./README.md) for complete documentation index.
