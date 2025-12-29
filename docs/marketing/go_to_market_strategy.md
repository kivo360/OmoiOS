# OmoiOS — Go-to-Market Strategy

**Created**: 2025-12-15
**Updated**: 2025-12-29
**Status**: Draft
**Purpose**: Define target users, positioning, launch strategy, acquisition channels, metrics, expansion, and an open source strategy for OmoiOS.

> **Related Documents**:
> - [Marketing Overview](./marketing_overview.md) - Core positioning and messaging
> - [Sub-Niche Targeting](./sub_niche_targeting.md) - Specific software sub-niches (2 layers deep)
> - [Cross-Market Niche Ideas](./cross_market_niche_ideas.md) - Non-software market opportunities
> - [Reality Outreach Playbook](./reality_contact_outreach_playbook.md) - Outreach tactics

---

## Table of contents

1. [The core challenge](#1-the-core-challenge)
2. [Target users + buying committee](#2-target-users--buying-committee)
3. [Competitive landscape](#3-competitive-landscape)
4. [Positioning + differentiation](#4-positioning--differentiation)
5. [Market strategy (wedge + pricing direction)](#5-market-strategy-wedge--pricing-direction)
6. [Pre-launch validation](#6-pre-launch-validation)
7. [Customer acquisition (supply/demand equivalent)](#7-customer-acquisition-supplydemand-equivalent)
8. [Launch sequence](#8-launch-sequence)
9. [Incentives + offers](#9-incentives--offers)
10. [Channel playbook](#10-channel-playbook)
11. [Metrics & milestones](#11-metrics--milestones)
12. [Expansion playbook](#12-expansion-playbook)
13. [Risk mitigation](#13-risk-mitigation)
14. [Open source: pros/cons + recommended approach](#14-open-source-proscons--recommended-approach)
15. [Appendix: pitches, talk tracks, and templates](#15-appendix-pitches-talk-tracks-and-templates)

---

## 1. The core challenge

### 1.1 What makes this hard
OmoiOS is not “a coding assistant.” It’s an execution system that touches:
- **Trust**: teams must believe the system won’t silently do the wrong thing.
- **Workflow integration**: Git, PR review, CI, tickets, and team habits.
- **Risk**: security, code quality, and operational costs.

### 1.2 The strategic implication
You don’t win by being “smarter.” You win by being **more operationally reliable**:
- Reviewable outputs (PRs)
- Clear workflow state (board/graph)
- Controlled autonomy (phase gates)
- Self-healing execution (monitoring + interventions)

---

## 2. Target users + buying committee

### 2.1 Primary user personas (end users)

#### Persona A — CTO / Head of Engineering (Buyer)
- **Goal**: increase output without linear headcount growth.
- **Pain**: hiring pressure, roadmap slippage, coordination overhead.
- **Objection**: “Will this create risk or chaos?”
- **Win condition**: predictable delivery, measurable throughput improvements, controlled spend.

#### Persona B — Engineering Manager (Champion)
- **Goal**: ship reliably; reduce planning + coordination tax.
- **Pain**: status updates, unblock work, aligning multiple contributors.
- **Objection**: “Will this add another tool I must babysit?”
- **Win condition**: fewer escalations, clearer blockers, faster cycle time.

#### Persona C — Staff/Senior Engineer (Power user)
- **Goal**: offload boilerplate and repetitive implementation; keep architectural integrity.
- **Pain**: context switching, backlog grooming, repetitive scaffolding.
- **Objection**: “Will the code be maintainable?”
- **Win condition**: PRs that are easy to review and merge; fewer boring tasks.

### 2.2 Secondary personas

#### Persona D — Product-leaning technical PM
- **Goal**: shorten idea → shipped loop.
- **Pain**: dependency on engineering bandwidth.
- **Win condition**: faster iteration and clearer progress reporting.

#### Persona E — Startup founder / tiny team
- **Goal**: ship fast with limited resources.
- **Win condition**: “I can move faster than my headcount.”

### 2.3 Buying committee and what each needs
- **Buyer (CTO/Head Eng)**: ROI + risk + security story + pricing predictability.
- **Champion (EM/Staff)**: daily usability + reliability + visibility.
- **Approver (Security/IT)**: controls, auditability, permissions, data handling.

---

## 3. Competitive landscape

### 3.1 Categories you will be compared to

#### (A) AI coding assistants (developer productivity)
Examples: GitHub Copilot, Cursor, Sourcegraph Cody, Codeium.
- **Their promise**: make individual developers faster.
- **Your wedge**: team-level execution + coordination + governance.

#### (B) Autonomous/agentic coding products
Examples: Devin (Cognition), SWE-agent style tools, OpenHands-based products, Sweep.
- **Their promise**: autonomous coding.
- **Your wedge**: structured workflow (spec → phases), visibility, approvals, diagnostics, steering.

#### (C) Workflow/ticket tools
Examples: Jira, Linear, GitHub Projects.
- **Their promise**: track work.
- **Your wedge**: work is not only tracked—**it’s executed**.

#### (D) Agent orchestration frameworks (builders)
Examples: LangGraph, CrewAI, AutoGPT.
- **Their promise**: primitives to build agent workflows.
- **Your wedge**: productized system: dashboards, gates, monitoring, budgets, multi-tenant setup.

### 3.2 How to talk about competitors
Do not fight on model quality. Fight on:
- **Time to first merged PR**
- **Approval/gate controls**
- **Traceability (why did it do this?)**
- **Operational visibility (what’s blocked? what’s at risk?)**
- **Self-healing (stuck detection + interventions)**

---

## 4. Positioning + differentiation

### 4.1 Positioning statement
**OmoiOS turns feature requests into reviewed pull requests using spec-driven, multi-agent workflows—with real-time visibility, discovery-based branching, and steering.**

### 4.2 Differentiation (simple)
- **Not chat-to-code** → spec-driven execution.
- **Not ticketing** → ticketing + execution.
- **Not an agent framework** → governance + monitoring + UI.

### 4.3 What you should NOT claim early
- “Fully autonomous shipping to production.”
- “No human review needed.”

Instead claim:
- “Autonomous execution with oversight.”
- “PR-based delivery with phase gates.”

---

## 5. Market strategy (wedge + pricing direction)

### 5.1 Beachhead (best initial wedge)
**Mid-market SaaS engineering orgs (10–100 engineers)** where:
- GitHub + PR review is standard
- Backlog is real
- Hiring is expensive
- Coordination overhead is high

### 5.2 First use case to sell (single sentence)
**“Turn well-scoped feature requests into reviewed PRs without daily babysitting.”**

### 5.3 Start narrow: target work types that convert
- **Internal tools / admin panels**
- **Integrations** (Stripe, Slack, webhooks)
- **Well-bounded backend features**
- **Refactors with clear tests**

Avoid early:
- Large greenfield rewrites
- "Magic product work" with unclear requirements

> **Deep Dive**: See [Sub-Niche Targeting](./sub_niche_targeting.md) for these broken into 2 layers with specific targeting, pain points, and messaging hooks.
>
> **Beyond Software**: See [Cross-Market Niche Ideas](./cross_market_niche_ideas.md) for 15 industries outside pure software where spec-driven execution applies (real estate, legal, healthcare admin, etc.).

### 5.4 Pricing direction (choose one early)
- **Per active agent / runtime** (transparent to buyer, maps to cost)
- **Per workspace/org** with usage caps (budget-friendly)
- **Open-core** (OSS core, paid governance/hosting)

---

## 6. Pre-launch validation

### 6.1 Concierge MVP (fastest validation)
Before scaling product-led acquisition, run a manual pilot:
1. Choose 3–5 design partners.
2. For each: pick 1–3 tickets/week.
3. Run OmoiOS against their repo and deliver **PRs**.
4. Track: time saved, acceptance rate, failure modes.

### 6.2 What you’re testing
- **Trust**: will they merge?
- **Quality**: do tests pass? do reviewers accept diffs?
- **Workflow fit**: do phase gates + visibility reduce oversight time?
- **Cost**: is the spend predictable and worth it?

### 6.3 Validation success criteria (minimum)
- **Time to first PR**: < 60 minutes for a small ticket
- **PR merge rate**: ≥ 50% of PRs merged (after revisions)
- **Reviewer effort**: review time not worse than a human PR
- **Repeat usage**: partner asks for a second ticket within 2 weeks

### 6.4 Pre-launch artifacts you must produce
- 2–3 short case studies (before/after)
- A “trust page”: how permissions, branching, gates, and logs work
- A demo video showing end-to-end flow

---

## 7. Customer acquisition (supply/demand equivalent)

For this product, “supply” and “demand” map to:
- **Supply-side**: design partners, credible proof, integrations, and distribution surfaces.
- **Demand-side**: buyer pipeline (CTOs/EMs) and user adoption inside teams.

### 7.1 Supply acquisition (design partners + proof)
- Recruit 3–5 design partners by profile:
  - mid-market SaaS
  - strong PR culture
  - clear backlog
- Offer: “We’ll ship 5 PRs in 30 days together.”
- Convert outputs into: testimonials, metrics, and demos.

### 7.2 Demand acquisition (pipeline)
- CTO/EM outreach to teams already spending on:
  - Copilot/Cursor (AI budget exists)
  - contractors (augmentation exists)
  - internal platform tooling (workflow appetite exists)

---

## 8. Launch sequence

### Phase 0 — Message + proof (2–4 weeks)
- Ship 3 case studies.
- Define one wedge use case.
- Create landing page + waitlist + demo request.

### Phase 1 — Private beta (4–8 weeks)
- 5–10 teams.
- Weekly cadence: pick tickets, run, review, improve.
- Build “known-good workflows” playbook (types of tickets that work best).

### Phase 2 — Public beta (8–12 weeks)
- Open signup (or “apply” gating).
- Self-serve onboarding (connect repo → create first spec → watch execution).
- Publish content around trust + governance + visibility.

### Phase 3 — Sales assist
- Convert teams that have active usage into paid plans.
- Introduce org controls: budgets, roles, policies.

---

## 9. Incentives + offers

### 9.1 Offers that reduce perceived risk
- **“First PR free”**: deliver one PR on a real repo.
- **“Pilot package”**: fixed-price 30 days with a cap.
- **“Merge guarantee”**: if nothing merges, you refund pilot (strong signal).

### 9.2 Incentives to drive the right behavior
- Reward “good tickets”:
  - templates for scoping
  - recommended ticket types
- Encourage gated adoption:
  - start with non-critical services
  - move to core paths after trust is earned

---

## 10. Channel playbook

### 10.1 Founder-led outbound (fastest early)
- Targets: CTOs/EMs at SaaS companies with visible engineering content.
- Ask: “Can I ship one PR in your repo to prove it?”

### 10.2 Content (compounding)
- “From feature request to PR in X minutes: walkthrough.”
- “Why agent workflows fail (and how we steer them).”
- “Discovery branching: how plans adapt without chaos.”

### 10.3 Communities
- Hacker News / r/programming (show real demo + repo).
- DevOps/platform communities (governance + reliability angle).

### 10.4 Partnerships
- Dev agencies / fractional CTOs (they sell delivery; you increase throughput).
- Tooling partners: GitHub Apps, CI platforms (integration listing).

### 10.5 Events
- Small, focused: platform engineering meetups; CTO circles.
- Demo the “execution dashboard” angle.

---

## 11. Metrics & milestones

### 11.1 North star metrics
- **Merged PRs per week per customer**
- **Time from ticket creation → PR opened**
- **Time from PR opened → merged**

### 11.2 Trust + quality metrics
- **PR merge rate**
- **CI pass rate on first PR**
- **# of human interventions per workflow** (should fall over time)
- **Rollback/incident rate attributable to agent PRs** (must be near-zero)

### 11.3 Economics metrics
- **Cost per merged PR** (compute + model + overhead)
- **Budget utilization predictability**
- **Gross margin per customer** (hosted)

### 11.4 Milestones (practical)
- **Milestone 1**: 10 PRs opened across 3 repos
- **Milestone 2**: 10 PRs merged across 3 repos
- **Milestone 3**: 3 paying customers renewing month 2
- **Milestone 4**: 1 repeatable wedge workflow with predictable success

---

## 12. Expansion playbook

### 12.1 Expand within an account
- Start: one repo, one team, one workflow type
- Expand: more repos + more workflow types
- Expand: org controls (roles, budgets, policies)

### 12.2 Expand product scope
- Add more “governance features” before more autonomy:
  - better policy controls
  - safer permissions
  - clearer audit trails

### 12.3 Expand market
- After mid-market SaaS: agencies/platform teams.
- Only later: enterprise (requires security, SOC2, SSO, audit exports).

---

## 13. Risk mitigation

### 13.1 Risk matrix

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Low trust / low merge rate | High | Critical | Start with safe ticket types; PR-based delivery; strong gates + logs; design partner pilots |
| Security concerns (repo access) | High | Critical | Min permissions; clear GitHub App model; audit logs; token handling; on-prem option later |
| Cost blowups | Medium | High | Budgets/alerts; runtime caps; predictable pricing; monitoring |
| “Agent chaos” / too many spawned tasks | Medium | High | Guardrails: discovery thresholds, approval gates, WIP limits |
| Competitors commoditize features | High | Medium | Differentiate on operations/governance; open-source strategy; brand + trust |

### 13.2 Trust narrative (must be explicit)
- Everything is **reviewable** (PRs)
- Execution is **visible** (board/graph/timeline)
- Autonomy is **gated** (phase gates + approvals)
- Work is **traceable** (“why” trail)

---

## 14. Open source: pros/cons + recommended approach

You’re right that “software value” is compressing, while usage is expanding. That pushes you toward monetizing **operations, trust, hosting, governance, and distribution**, not raw code.

### 14.1 Pros of open sourcing OmoiOS
- **Trust**: buyers can inspect how repo access, policies, and gates work.
- **Distribution**: developers share OSS; it becomes a channel.
- **Faster iteration**: community contributions, bug reports, integrations.
- **Category ownership**: you define the “autonomous execution dashboard” narrative.
- **Defensive moat**: if core becomes commodity, you still lead the ecosystem.

### 14.2 Cons of open sourcing OmoiOS
- **Fork risk**: hosted competitors can clone and undercut.
- **Monetization pressure**: harder to charge for “the code.”
- **Support burden**: self-host users create noisy demands.
- **Security optics**: vulnerabilities become public; need strong process.
- **Roadmap tension**: community wants features that don’t match revenue.

### 14.3 Recommended strategy (open-core with clear boundaries)

**Recommendation**: Open source the core “workflow engine + basic UI,” keep **enterprise/hosted governance** paid.

Suggested split:
- **Open Source (Core)**:
  - local/dev single-tenant
  - base workflows/specs/board/graph
  - basic agent execution loop
- **Paid (Hosted / Enterprise)**:
  - multi-tenant orgs, roles, SSO
  - advanced policy controls (tool permissions, budget enforcement)
  - audit exports, compliance features
  - “mission control” operational dashboards
  - managed hosting + updates + SLAs

Licensing choices (pick intentionally):
- **Permissive (Apache/MIT)**: max adoption, max fork risk.
- **Source-available (BSL/Elastic-like)**: protects hosted business, reduces adoption friction vs closed.
- **Dual licensing**: OSS for community, commercial for hosted/enterprise.

### 14.4 When to go OSS vs stay closed initially
- Go OSS now if your top constraint is **trust + distribution**.
- Stay closed for 8–12 weeks if your top constraint is **product coherence** (avoid support + forks while you find wedge).

A practical path:
1. Pilot closed with design partners.
2. Open source a “community edition” once you have a repeatable wedge + messaging.
3. Sell hosted governance and reliability.

---

## 15. Appendix: pitches, talk tracks, and templates

### 15.1 One-liners
- “Turn feature requests into reviewed PRs with autonomous, spec-driven workflows.”
- “Autonomous execution with oversight: phase gates, real-time visibility, and self-healing workflows.”

### 15.2 30-second pitch
Connect your repo, describe a feature, and OmoiOS generates a requirements/design/task plan, then runs parallel agents to implement and test in isolated branches. When agents discover missing requirements, bugs, or optimizations, OmoiOS spawns and links the right follow-up work instead of stalling. You stay in control at phase gates and PR review, with full visibility into progress and blockers.

### 15.3 Cold email (design partner)
Subject: Can I ship one PR in your repo to prove this?

Hi {{name}},

I’m building OmoiOS: an autonomous engineering execution dashboard that turns feature requests into reviewed PRs via spec-driven, multi-agent workflows (with phase gates + real-time visibility).

If you’re open to it, I’d like to take one well-scoped ticket in your repo and deliver a PR end-to-end so you can judge quality and review effort.

Worth a 20-minute call this week?

— {{you}}

### 15.4 Demo checklist (2 minutes)
- Create a spec → show Requirements/Design/Tasks
- Start execution → show board moving + dependencies
- Show a discovery spawning a task + linked reasoning
- Show phase gate / validation
- Show PR creation + review loop

### 15.5 Competitor framing (safe)
- “Assistants help individuals write code faster.”
- “OmoiOS helps teams ship more by executing and coordinating work with governance.”
