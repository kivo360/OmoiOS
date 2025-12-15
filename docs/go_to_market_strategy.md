# OmoiOS — Go-to-Market Strategy

**Created**: 2025-12-15  
**Updated**: 2025-12-15  
**Status**: Active  
**Purpose**: Comprehensive, actionable go-to-market playbook with specific tactics, timelines, and execution guidance for OmoiOS.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [The Core Challenge](#2-the-core-challenge)
3. [Target Users & Buying Committee](#3-target-users--buying-committee)
4. [Lead Qualification Framework](#4-lead-qualification-framework)
5. [Competitive Landscape](#5-competitive-landscape)
6. [Positioning & Differentiation](#6-positioning--differentiation)
7. [Pricing Strategy](#7-pricing-strategy)
8. [Pre-Launch Validation](#8-pre-launch-validation)
9. [Customer Acquisition Playbook](#9-customer-acquisition-playbook)
10. [Warm Outreach Playbook](#10-warm-outreach-playbook) ⭐ **Start Here**
11. [Cold Outbound (Supplemental)](#11-cold-outbound-supplemental)
12. [Inbound & Product-Led Growth](#12-inbound--product-led-growth)
13. [Launch Sequence](#13-launch-sequence)
14. [Channel Playbook](#14-channel-playbook)
15. [Partnerships Strategy](#15-partnerships-strategy)
16. [Customer Success Playbook](#16-customer-success-playbook)
17. [Onboarding Playbook](#17-onboarding-playbook)
18. [Retention & Expansion](#18-retention--expansion)
19. [Metrics & Milestones](#19-metrics--milestones)
20. [Risk Mitigation](#20-risk-mitigation)
21. [Open Source Strategy](#21-open-source-strategy)
22. [90-Day Execution Plan](#22-90-day-execution-plan)
23. [Appendix: Templates & Scripts](#23-appendix-templates--scripts)

---

## 1. Executive Summary

### The Opportunity
Engineering teams at mid-market SaaS companies are constrained by coordination overhead, not coding speed. AI assistants help individuals but don't solve the systemic problem. OmoiOS fills this gap with autonomous engineering execution that includes governance.

### The Strategy
1. **Land**: Design partner pilots proving value with low-risk tickets (internal tools, integrations)
2. **Prove**: Collect metrics and case studies demonstrating 2-3X throughput improvements
3. **Expand**: Product-led + sales-assisted growth to more repos, teams, and workflow types
4. **Differentiate**: Win on operations, governance, and reliability—not model quality

### 90-Day Goals
- **Month 1**: 5 design partners running pilots, first case study documented
- **Month 2**: 10+ active pilot teams, pricing validated, waitlist > 500
- **Month 3**: 3 paying customers, public beta launch, repeatable sales motion

---

## 2. The Core Challenge

### What Makes This Hard

OmoiOS is not "a coding assistant." It's an execution system that requires:

| Challenge | Why It's Hard | How We Address It |
|-----------|---------------|-------------------|
| **Trust** | Teams must believe system won't silently do wrong things | PR-based delivery, phase gates, reasoning trails |
| **Workflow integration** | Must fit Git, PR review, CI, tickets, and team habits | GitHub-native, works with existing tools |
| **Risk** | Security, code quality, and cost concerns | Minimal permissions, isolated branches, budget controls |
| **Behavior change** | Teams must shift from tracking to delegating | Start with bounded tasks, build confidence incrementally |

### Strategic Implication

**You don't win by being "smarter."** You win by being **more operationally reliable**:
- Reviewable outputs (PRs)
- Clear workflow state (board/graph)
- Controlled autonomy (phase gates)
- Self-healing execution (monitoring + interventions)

---

## 3. Target Users & Buying Committee

### Primary Personas

#### Persona A: CTO / Head of Engineering (Economic Buyer)

| Attribute | Detail |
|-----------|--------|
| **Goal** | Increase output without linear headcount growth |
| **Pain** | Hiring pressure, roadmap slippage, coordination overhead |
| **Primary objection** | "Will this create risk or chaos?" |
| **Win condition** | Predictable delivery, measurable throughput improvements, controlled spend |
| **Budget authority** | Yes |
| **Decision power** | Final approval |

**How to reach them**: LinkedIn, CTO communities, executive referrals, board/investor introductions

**Messaging focus**: ROI, risk mitigation, operational control, competitive advantage

---

#### Persona B: Engineering Manager (Champion/User Buyer)

| Attribute | Detail |
|-----------|--------|
| **Goal** | Ship reliably; reduce planning + coordination tax |
| **Pain** | Status updates, unblocking work, aligning multiple contributors |
| **Primary objection** | "Will this add another tool I must babysit?" |
| **Win condition** | Fewer escalations, clearer blockers, faster cycle time |
| **Budget authority** | Usually recommends, doesn't approve |
| **Decision power** | Strong influence |

**How to reach them**: Developer communities, team blogs, engineering podcasts, LinkedIn

**Messaging focus**: Daily usability, visibility, time savings, team productivity

---

#### Persona C: Staff/Senior Engineer (Power User)

| Attribute | Detail |
|-----------|--------|
| **Goal** | Offload boilerplate and repetitive implementation |
| **Pain** | Context switching, backlog grooming, repetitive scaffolding |
| **Primary objection** | "Will the code be maintainable?" |
| **Win condition** | PRs that are easy to review and merge; fewer boring tasks |
| **Budget authority** | None |
| **Decision power** | Technical veto |

**How to reach them**: Hacker News, GitHub, Twitter/X, technical conferences

**Messaging focus**: Code quality, review experience, interesting problems vs. boring work

---

### Secondary Personas

| Persona | Goal | Win Condition |
|---------|------|---------------|
| **Technical PM** | Shorten idea → shipped loop | Faster iteration, clearer progress |
| **Startup Founder** | Ship fast with limited resources | Move faster than headcount |
| **Security/IT** | Ensure controls and compliance | Audit trails, permissions, data handling |

### Buying Committee Needs

| Role | What They Need to Say Yes |
|------|--------------------------|
| **CTO (Buyer)** | ROI story + risk mitigation + security posture + pricing predictability |
| **EM (Champion)** | Daily usability + reliability + time savings |
| **Staff Eng (User)** | Code quality + good PR experience + reduced grunt work |
| **Security (Approver)** | Permission model + audit logs + data handling |

---

## 4. Lead Qualification Framework

### BANT Qualification

| Criterion | Qualified | Disqualified |
|-----------|-----------|--------------|
| **Budget** | AI/productivity budget exists; spending on Copilot or contractors | No budget for tools; waiting for next fiscal year |
| **Authority** | Can reach decision-maker within 2 calls | No access to budget holder |
| **Need** | Backlog growing faster than velocity; hiring pressure | Happy with current throughput |
| **Timeline** | Evaluating now; decision within 30-60 days | "Maybe next quarter" |

### Scoring Model

| Signal | Points | Notes |
|--------|--------|-------|
| Engineering team 10-100 people | +20 | Sweet spot ICP |
| Already using AI tools (Copilot, etc.) | +15 | Budget exists, behavior familiar |
| GitHub as primary repo | +15 | Required for integration |
| Expressed backlog/velocity pain | +15 | High intent |
| Recently missed release deadline | +10 | Urgency trigger |
| Failed to fill engineering roles | +10 | Headcount alternative |
| Requested demo/pilot | +10 | Active evaluation |
| CTO/VP level engaged | +10 | Access to decision-maker |
| No PR review culture | -20 | Foundational gap |
| "Zero human review" requirement | -30 | Misaligned expectations |

**Qualified threshold**: 50+ points  
**Priority threshold**: 70+ points

### Ideal First Conversation Indicators

✅ "We're growing but can't ship fast enough"  
✅ "We've tried AI tools but they don't solve the coordination problem"  
✅ "We spend too much time in planning meetings"  
✅ "We need to ship more with the team we have"

❌ "We want fully autonomous with no oversight"  
❌ "We don't really use PRs or code review"  
❌ "We're looking for something free"

---

## 5. Competitive Landscape

### Category Map

| Category | Examples | Their Promise | Our Wedge |
|----------|----------|---------------|-----------|
| **AI coding assistants** | Copilot, Cursor, Cody | Make individual devs faster | Team-level execution + coordination |
| **Autonomous coding** | Devin, SWE-agent | Autonomous code generation | Structured workflow + governance + visibility |
| **Workflow/ticket tools** | Jira, Linear | Track work | Track AND execute work |
| **Agent frameworks** | LangGraph, CrewAI | Build agent workflows | Productized: dashboards, gates, monitoring |

### Competitive Response Matrix

| Competitor | When Prospect Mentions | Our Response |
|------------|----------------------|--------------|
| **Copilot** | "We're already using Copilot" | "Great—Copilot helps individuals. OmoiOS helps teams. They're complementary." |
| **Devin** | "We're looking at Devin" | "Devin demos well. OmoiOS ships well. Want to see both on your actual repo?" |
| **Linear/Jira** | "We just implemented Linear" | "Perfect—OmoiOS integrates with your workflow. It's the execution layer that makes your board actually move." |
| **Build own** | "We might build this ourselves" | "You could. Is 6-12 months of your best engineers the best use of your capacity?" |

### Differentiation Talking Points

**DO talk about:**
- Time to first merged PR
- Approval/gate controls
- Traceability ("why did it do this?")
- Operational visibility
- Self-healing execution

**DON'T compete on:**
- Model quality
- Benchmark performance
- Autonomous capability claims

---

## 6. Positioning & Differentiation

### Positioning Statement

> For **engineering teams at mid-market SaaS companies** who struggle with **shipping velocity and coordination overhead**, OmoiOS is an **autonomous engineering execution platform** that **turns feature requests into reviewed PRs using spec-driven, multi-agent workflows**. Unlike **AI coding assistants** that help individuals, OmoiOS **orchestrates complete development workflows with governance, visibility, and self-healing execution**.

### Key Differentiators

| Differentiator | What It Means | Why It Matters |
|----------------|---------------|----------------|
| **Spec-driven execution** | Requirements → Design → Tasks → Code | Structured > chaotic |
| **Discovery branching** | Workflow adapts when reality changes | Doesn't break when surprised |
| **Phase gates** | Human approval at strategic points | Trust without babysitting |
| **Self-healing** | Guardian agents detect and fix stuck workflows | Doesn't stall at 2am |
| **Full visibility** | Real-time board, graph, activity feed | Know what's happening always |

### What NOT to Claim (Early)

❌ "Fully autonomous shipping to production"  
❌ "No human review needed"  
❌ "Replace your engineering team"

✅ "Autonomous execution with oversight"  
✅ "PR-based delivery with phase gates"  
✅ "Extend your team's capacity"

---

## 7. Pricing Strategy

### Recommended Model: Usage-Based with Seat Minimum

**Rationale**: Aligns cost with value delivered, predictable for buyers, scales with usage

### Pricing Tiers

| Tier | Monthly Price | Included | Best For |
|------|---------------|----------|----------|
| **Starter** | $0 | 5 workflows/month, 1 repo, basic support | Evaluation, small teams |
| **Team** | $499/month | 50 workflows/month, 5 repos, email support | Growing teams (5-15 engineers) |
| **Business** | $1,499/month | 200 workflows/month, unlimited repos, priority support, SSO | Mid-market (15-50 engineers) |
| **Enterprise** | Custom | Unlimited workflows, dedicated support, SLAs, custom integrations | Large teams (50+ engineers) |

**Overage pricing**: $10 per additional workflow

### Workflow Definition
A "workflow" = one feature request executed through to PR creation (regardless of how many tasks/agents involved)

### Pricing Psychology

- **Free tier exists**: Reduces friction to try
- **Team tier is anchor**: Makes Business look reasonable
- **Enterprise is custom**: Signals seriousness for large deals

### Pilot/Design Partner Pricing

- **Design partners**: Free for 90 days in exchange for feedback + case study rights
- **Early adopters**: 50% discount on first year if signed before public launch
- **Pilot package**: $500 fixed for 30 days, unlimited workflows, includes onboarding

### Pricing FAQ

**"How does this compare to hiring?"**
> "A senior engineer costs $150-200K+/year fully loaded. OmoiOS Business tier is $18K/year and handles the equivalent of 1-2 engineers' worth of routine implementation work."

**"What if we go over our workflow limit?"**
> "You're billed for overages at $10/workflow. We'll alert you at 80% usage so there are no surprises. You can also upgrade mid-cycle."

**"Can we start smaller?"**
> "Yes—Starter is free with 5 workflows/month. Perfect to validate the fit before committing."

---

## 8. Pre-Launch Validation

### Design Partner Criteria

**Must have:**
- [ ] GitHub as primary repo
- [ ] Established PR review culture
- [ ] 10+ person engineering team
- [ ] Clear backlog of bounded features
- [ ] Technical decision-maker engaged
- [ ] Willing to provide feedback + testimonial

**Nice to have:**
- [ ] Already using AI coding tools
- [ ] Recently missed delivery goals
- [ ] Open to recorded case study

### Design Partner Program Structure

**Duration**: 90 days

**Week 1-2: Setup**
- Connect GitHub repo
- Select 3-5 pilot tickets
- Configure workflow preferences
- Training session for key users

**Week 3-8: Active Piloting**
- Run 2-3 workflows per week
- Weekly 30-minute feedback call
- Track all metrics (see below)
- Iterate on workflow configurations

**Week 9-12: Documentation**
- Compile case study
- Record testimonial
- Finalize metrics
- Discuss conversion to paid

### Metrics to Track for Each Partner

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Time to first PR** | < 60 min for small ticket | Timestamp: ticket created → PR opened |
| **PR merge rate** | ≥ 50% | PRs merged / PRs created |
| **CI pass rate** | ≥ 80% on first submit | CI passes / PR submissions |
| **Human interventions** | < 3 per workflow | Count manual overrides needed |
| **User satisfaction** | ≥ 4/5 | Post-workflow survey |
| **Repeat usage** | Request 2nd workflow within 2 weeks | Organic request tracking |

### Validation Success Criteria

**Minimum Viable Signal (to proceed):**
- 3/5 partners have ≥ 50% merge rate
- Average time to PR < 90 minutes
- 3/5 partners request continued access
- 1+ partner willing to provide testimonial

**Strong Signal (to accelerate):**
- 4/5 partners have ≥ 60% merge rate
- Average time to PR < 60 minutes
- 4/5 partners want to convert to paid
- 2+ partners willing to do case study

### Pre-Launch Artifacts Checklist

- [ ] 2-3 written case studies with metrics
- [ ] 1-2 video testimonials
- [ ] Security/trust documentation
- [ ] Demo video (2-3 minutes)
- [ ] Integration guide
- [ ] Best practices guide ("tickets that work well")
- [ ] FAQ document
- [ ] Pricing page

---

## 9. Customer Acquisition Playbook

### Acquisition Funnel

```
Awareness → Interest → Consideration → Intent → Evaluation → Purchase
   |           |            |            |          |           |
Content    Demo video    Comparison   Waitlist   Pilot      Contract
   |           |            |            |          |           |
Blog/HN    Website       Battle cards  Sign-up   Free trial  Sales call
```

### Channel Mix (First 6 Months)

| Channel | % of Effort | Expected Contribution |
|---------|-------------|----------------------|
| **Founder-led outbound** | 40% | 60% of early customers |
| **Content + SEO** | 25% | 20% of pipeline (compounding) |
| **Community + social** | 20% | 15% of pipeline |
| **Partnerships** | 10% | 5% of pipeline |
| **Paid ads** | 5% | Testing only |

### Customer Acquisition Cost Targets

| Stage | Target CAC | Rationale |
|-------|------------|-----------|
| **Design partners** | $0 | Investment in learning |
| **Early adopters** | < $500 | Low-friction conversion |
| **Growth phase** | < $2,000 | Sustainable unit economics |
| **At scale** | < $5,000 | With 12-month LTV of $15K+ |

---

## 10. Warm Outreach Playbook

> **Why warm outreach first**: Cold calling and cold emailing have 1-3% response rates. Warm outreach—where you've built some relationship or provided value first—has 20-40% response rates. Invest here first.

### The Warm Outreach Hierarchy

| Method | Conversion Rate | Effort | Best For |
|--------|-----------------|--------|----------|
| **Warm introductions** | 30-50% | Low (per intro) | Fastest closes |
| **Build in public followers** | 15-30% | High (ongoing) | Compounding pipeline |
| **Community relationships** | 15-25% | Medium | Trust + credibility |
| **Content engagement** | 10-20% | Medium | Scale + positioning |
| **Event connections** | 20-35% | High (per event) | Deep relationships |
| **Cold outreach** | 1-3% | Low (per touch) | Volume when needed |

---

### Strategy 1: Warm Introductions (Highest Conversion)

**The math**: 10 warm intros → 3-5 meetings → 1-2 customers  
**Compare to cold**: 100 cold emails → 2-3 meetings → 0-1 customers

#### How to Generate Warm Intros

**Step 1: Map your network**
Create a spreadsheet with:
- Your LinkedIn connections (export)
- Investors you know or can reach
- Advisors, mentors, former colleagues
- Other founders in your space
- People who've used your content

**Step 2: Identify who knows your ICP**
For each connection, ask:
- Do they work at a target company?
- Do they know CTOs/engineering leaders?
- Are they investors in SaaS companies?
- Are they in engineering communities?

**Step 3: Request intros systematically**

**Template: Asking a friend for an intro**
```
Hey [Name],

I'm working on OmoiOS—we help engineering teams ship 2-3X more by
automating workflow execution (like a spec-driven AI that turns
feature requests into PRs).

I noticed you're connected to [Target Person] at [Company]. Given
their role, I think they might find this relevant—especially if
[specific pain point like "they're scaling the team" or "hiring
a lot right now"].

Would you be comfortable making an intro? I've drafted something
below you can forward if helpful:

---

"Hey [Target], I wanted to introduce you to [Your Name]. They're
building OmoiOS, which helps engineering teams ship more without
scaling headcount proportionally. Given [Company]'s growth, thought
it might be worth a conversation. I'll let [Your Name] follow up
from here if you're interested."

---

Totally understand if the timing isn't right. Thanks either way!
```

**Template: Asking an investor for intros**
```
Hi [Investor Name],

Quick update on OmoiOS: we're seeing [traction metric] and are
now looking for design partners to pilot with.

Our ideal profile is:
- Mid-market SaaS (10-100 engineers)
- GitHub-first
- Feeling hiring/velocity pressure

Looking at your portfolio, [Company A], [Company B], and [Company C]
seem like potential fits. Would you be comfortable making intros to
their engineering leaders?

Happy to share a brief deck or demo video you can forward.
```

**Template: Asking a former colleague**
```
Hey [Name], hope you're doing well at [Company]!

I've been building OmoiOS—it's an autonomous engineering execution
platform that helps teams ship more without scaling headcount.

Given [Company]'s growth, I thought [CTO/VP Eng Name] might find it
interesting. Any chance you could connect us? Happy to send you a
quick overview to share.

(Also genuinely curious how things are going there—would love to
catch up regardless!)
```

#### Intro Request Tracking

| Contact | Relationship | Target Person | Company | Asked | Status | Follow-up |
|---------|--------------|---------------|---------|-------|--------|-----------|
| [Name] | Former colleague | [Target] | [Co] | [Date] | Pending | [Date] |

**Goal**: Ask 5-10 people per week for intros. Expect 30-40% to help.

---

### Strategy 2: Build in Public (Compounding Pipeline)

**The concept**: Share your journey building OmoiOS publicly. People who follow along become warm leads when they have the problem you solve.

#### Where to Build in Public

| Platform | Best For | Frequency | Content Type |
|----------|----------|-----------|--------------|
| **Twitter/X** | Tech audience, developers | Daily | Insights, learnings, progress |
| **LinkedIn** | Decision-makers, CTOs | 3-5x/week | Professional insights |
| **YouTube** | Deep dives, demos | Weekly | Tutorials, behind-scenes |
| **Newsletter** | Nurturing interested leads | Weekly | Updates, insights |
| **Blog** | SEO, credibility | 1-2x/week | Educational content |

#### Content Ideas for Building in Public

**Weekly rhythm:**
- **Monday**: Problem insight ("Here's what I learned talking to 10 CTOs...")
- **Tuesday**: Product progress ("Shipped discovery branching this week...")
- **Wednesday**: Customer story ("[Company] just merged their first PR...")
- **Thursday**: Tactical advice ("3 tickets that work best for AI execution...")
- **Friday**: Week recap + metrics ("Week 12: 5 pilots, 23 merged PRs...")

**High-engagement post templates:**

**The "Aha Moment" post:**
```
I used to think AI coding tools would replace developers.

After 6 months building OmoiOS, I realized I was wrong.

The bottleneck isn't coding speed. It's coordination overhead.

Engineering teams spend 30-40% of their time on:
- Planning meetings
- Status updates
- Unblocking work
- Context switching

AI assistants make individuals faster.
But they don't solve the systemic problem.

That's why we built OmoiOS differently: [brief explanation]

Anyone else seeing this pattern?
```

**The "Counter-intuitive insight" post:**
```
Hot take: Your AI coding assistant isn't making your team ship faster.

Here's why:

[Individual productivity] ≠ [Team throughput]

When every developer is 30% faster at coding, you'd expect 30% more output.

But coordination overhead scales with team size.
More people = more meetings, more handoffs, more "quick questions."

The real leverage is reducing coordination—not coding speed.

We've seen teams ship 2-3X more by automating the execution workflow,
not just the coding.

Curious if others are seeing the same pattern?
```

**The "Behind the curtain" post:**
```
Real numbers from OmoiOS pilot #7:

- Ticket selected: "Add Stripe webhook handling"
- Time to first PR: 47 minutes
- CI pass on first submit: Yes
- Human interventions needed: 1 (clarifying a field name)
- PR merged: Yes, after 2 comment cycles

6 months ago, this would have taken a developer half a day.

Here's what the workflow looked like: [screenshot or breakdown]

Not perfect yet, but getting there. What would you want to see improved?
```

#### Converting Followers to Customers

**The funnel:**
1. **Follow** → They see your content regularly
2. **Engage** → They comment, like, share
3. **DM conversation** → Natural dialogue starts
4. **Problem emerges** → They mention relevant pain
5. **Offer help** → "Happy to show you how we solved this"

**DM templates after engagement:**

**After they comment on your post:**
```
Hey [Name], thanks for the thoughtful comment on my post about
[topic]. Sounds like you're dealing with [pain they mentioned]
at [Company].

Curious—how are you handling [specific challenge] right now?
```

**After they share your content:**
```
Hey [Name], really appreciate you sharing that post! Noticed
you're [role] at [Company]—is [topic of post] something you're
actively thinking about?
```

**After multiple engagements:**
```
Hey [Name], I've noticed you engaging with a lot of my content
about [topic]. Seems like this is top of mind for you.

Would love to hear more about what you're dealing with at [Company].
Coffee chat sometime?
```

---

### Strategy 3: Community-First Outreach

**The concept**: Become a valuable member of communities where your ICP hangs out. Relationships lead to opportunities.

#### Target Communities

| Community | Where | Your ICP There | How to Engage |
|-----------|-------|----------------|---------------|
| **Hacker News** | news.ycombinator.com | Senior engineers, CTOs | Thoughtful comments, occasional posts |
| **r/ExperiencedDevs** | Reddit | Senior engineers | Answer questions, share experiences |
| **Engineering Twitter** | Twitter/X | All levels | Conversations, threads |
| **CTO Craft Slack** | Slack | CTOs | Private discussions |
| **Rands Leadership Slack** | Slack | Engineering managers | Advice, discussions |
| **Local tech meetups** | In-person | Mixed | Conversations, talks |
| **Discord servers** | Discord | Developers | Ongoing conversations |

#### Community Engagement Rules

**DO:**
- Provide value first (answer questions, share insights)
- Be genuinely helpful without pitching
- Share your honest experiences and learnings
- Engage consistently over weeks/months
- Remember people and reference past conversations

**DON'T:**
- Drop links to your product unprompted
- Pitch in every conversation
- Only show up when you want something
- Treat people as leads, not humans
- Disappear after getting what you want

#### Community → Conversation Templates

**When someone asks about your problem space:**
```
[Answer their question genuinely with useful advice]

We've been thinking about this a lot at OmoiOS since we're building
in this space. Happy to share more about what we've learned if helpful.
```

**When someone mentions a pain you solve:**
```
Oof, I feel this. We talked to 30+ engineering teams about exactly
this problem. The pattern we kept seeing was [insight].

One thing that helped some teams: [actionable advice that doesn't
require your product]

If you want to chat more about it, DM me—I'm always happy to
share what we've learned.
```

**After helping someone via DM:**
```
Glad that was helpful! By the way, this is exactly the problem
we're solving with OmoiOS. We're running pilots right now if
you ever want to try it—no pressure, but figured I'd mention it.
```

---

### Strategy 4: Content-First Outreach

**The concept**: Lead with value. Share useful content before asking for anything.

#### The Content-First Sequence

**Instead of:**
"Hi, I'm selling X. Want a demo?"

**Do this:**
1. **Day 0**: Share valuable content with no ask
2. **Day 3**: Follow up with more related value
3. **Day 7**: Ask a genuine question about their situation
4. **Day 14**: Offer to help (not pitch)

#### Content-First Email Sequence

**Email 1: Pure value (Day 0)**

Subject: Thought you'd find this useful—[topic]

```
Hi [Name],

I've been researching how engineering teams are handling [specific
challenge] and put together [a guide/analysis/framework].

Given [Company]'s growth, thought you might find it relevant:
[link to genuinely useful content]

Key takeaway: [one actionable insight]

No ask here—just thought it'd be useful.

—[Your name]
```

**Email 2: Related value (Day 3)**

Subject: Re: Thought you'd find this useful—[topic]

```
Hi [Name],

Following up with one more thing on this topic—

[Interesting data point or insight related to first email]

We've seen teams like [Company] address this by [specific approach].

Here's a quick breakdown: [2-3 bullet points of actionable advice]

—[Your name]
```

**Email 3: Genuine question (Day 7)**

Subject: Quick question about [Company]

```
Hi [Name],

Curious—how is [Company] currently handling [specific challenge
related to your content]?

I'm talking to a lot of engineering leaders about this and trying
to understand the different approaches.

Would love to hear your perspective if you have a minute.

—[Your name]
```

**Email 4: Offer to help (Day 14)**

Subject: Offer to help with [specific challenge]

```
Hi [Name],

Based on what I've been learning, it sounds like a lot of teams
like [Company] are struggling with [specific challenge].

We've been working on an approach that [brief value prop]. A few
teams have seen [specific result].

Would it be helpful to show you how they did it? Happy to share
what's working—even if OmoiOS isn't the right fit, the approach
might be useful.

15 minutes this week?

—[Your name]
```

---

### Strategy 5: Event-Based Relationship Building

**The concept**: Meet people in person at events. Follow up to build relationships.

#### Before the Event

**Research attendees:**
- Check speaker list for targets
- Look at attendee list if available
- Search "[Event name]" + "attending" on LinkedIn/Twitter
- Identify 5-10 specific people to meet

**Prepare conversation starters:**
- "What brings you to [event]?"
- "What's the biggest challenge your team is facing right now?"
- "I loved your talk on [topic]—we're seeing similar patterns with [insight]"

#### At the Event

**Goal**: Have 5-10 meaningful conversations, not 50 card exchanges.

**Conversation flow:**
1. **Open**: Genuine interest in them ("What are you working on?")
2. **Listen**: Understand their situation and challenges
3. **Share**: Relate with your experience (not a pitch)
4. **Exchange**: Get their contact for follow-up
5. **Note**: Write down what you discussed immediately after

**What to say when asked what you do:**
```
"I'm building OmoiOS—we help engineering teams ship more without
scaling headcount. Basically, you describe a feature, and the
system handles the execution workflow: planning, implementation,
testing, and opens PRs. You approve at strategic points.

The insight that led to it was that AI coding tools help individuals,
but don't solve the coordination problem teams face. [pause for
their reaction]"
```

#### After the Event (Critical)

**Within 24 hours:**

```
Subject: Great meeting you at [Event]

Hi [Name],

Really enjoyed our conversation at [Event] about [specific topic
you discussed].

[Reference something specific they said]: I've been thinking about
that and wanted to share [relevant resource or insight].

Would love to continue the conversation—coffee or call sometime?

—[Your name]
```

**Within 1 week:**

```
Subject: Following up from [Event]

Hi [Name],

Hope the week's been good since [Event].

I mentioned we're running pilots with engineering teams on the
workflow automation side. Given what you shared about [their
challenge], I thought it might be worth showing you what we're doing.

Would 20 minutes be useful to see if there's a fit?

—[Your name]
```

---

### Strategy 6: Podcast & Speaking (Borrowed Audiences)

**The concept**: Get in front of other people's audiences to build credibility and pipeline.

#### Podcast Outreach

**Target podcasts:**
- Engineering leadership podcasts
- SaaS/startup podcasts
- Developer productivity podcasts
- AI/automation podcasts

**Pitch template:**
```
Subject: Podcast guest pitch: [Your topic angle]

Hi [Host name],

I'm [Your name], founder of OmoiOS. I've been listening to [Podcast]
and loved the episode on [specific episode].

I'd love to come on and discuss: [specific topic with a hook]

For example:
- Why AI coding assistants aren't actually making teams ship faster
- The coordination tax that grows faster than your engineering team
- How we're seeing teams 3X their output without hiring

I can share specific stories and data from [X] engineering teams
we've worked with.

Here's a bit more about me: [brief bio or link]

Worth a conversation?

—[Your name]
```

#### Speaking Opportunities

**Where to speak:**
- Local tech meetups (easiest to start)
- Engineering manager meetups
- Platform engineering events
- Company engineering all-hands (reach out to targets)
- Virtual conferences

**Topic angles:**
- "The Coordination Tax: Why Scaling Teams Doesn't Scale Output"
- "Beyond AI Assistants: What Engineering Automation Actually Looks Like"
- "Spec-Driven Development: Structured Autonomy for Engineering Teams"

---

### Strategy 7: Strategic Commenting

**The concept**: Add value in comments on other people's content. Get noticed by the right people.

#### Where to Comment

| Platform | What to Comment On |
|----------|-------------------|
| **LinkedIn** | Posts by CTOs, VPs Eng, engineering influencers |
| **Twitter/X** | Threads about engineering productivity, AI, team scaling |
| **Hacker News** | Stories about AI coding, engineering management |
| **Substack** | Engineering newsletters |

#### Good vs. Bad Comments

**Bad comments (ignored):**
- "Great post!" 
- "This is so true!"
- "Check out our product that solves this!"

**Good comments (get noticed):**
```
This resonates. We've seen the same pattern with teams we work with.

The insight that surprised me: [specific data point or experience]

One thing I'd add: [genuine additional value]

Curious if you've seen [related question]?
```

#### Comment → Relationship Flow

1. **Comment thoughtfully** on 3-5 of their posts over 2 weeks
2. **Get noticed** when they respond or like your comments
3. **Connect** with a personalized request referencing your engagement
4. **Continue** engaging after connecting
5. **Natural conversation** emerges from mutual interest

---

### Strategy 8: The "Trojan Horse" Value Offer

**The concept**: Offer something valuable for free that naturally leads to showing your product.

#### Value Offers That Work

| Offer | What You Provide | Natural Segue |
|-------|------------------|---------------|
| **Workflow audit** | Review their development workflow | "Based on what I see, here's where OmoiOS could help..." |
| **ROI calculation** | Calculate their coordination overhead | "Here's how much you'd save with automation..." |
| **Best practices guide** | Share what top teams are doing | "We built OmoiOS around these patterns..." |
| **Architecture review** | Review their codebase structure | "This would be a great fit for spec-driven execution..." |

#### Workflow Audit Offer

**Outreach:**
```
Subject: Free workflow audit for [Company]

Hi [Name],

I've been researching engineering productivity patterns and would
love to offer [Company] a free development workflow audit.

I'll analyze:
- Where time is going (coordination vs. execution)
- Common bottlenecks in your ticket-to-PR flow
- Opportunities to automate without adding complexity

Takes about 30 minutes of your time. You get actionable insights
regardless of whether you use any tools.

Interested?

—[Your name]

P.S. I'm doing this to learn more about how different teams work,
and to test some hypotheses. Zero pitch—just value.
```

---

### Weekly Warm Outreach Rhythm

| Day | Activity | Goal |
|-----|----------|------|
| **Monday** | Ask 3 people for warm intros | 1-2 new intro requests |
| **Tuesday** | Build in public post + engage with 10 posts | Visibility + relationships |
| **Wednesday** | Community participation (HN, Reddit, Discord) | 3-5 helpful interactions |
| **Thursday** | Follow up on open conversations | Move relationships forward |
| **Friday** | Content-first outreach to 5 new prospects | Start new relationships |

### Warm Outreach Tracking

| Prospect | Source | Stage | Last Touch | Next Action | Notes |
|----------|--------|-------|------------|-------------|-------|
| [Name] | Twitter engage | Engaged | 12/10 | DM conversation | Liked 3 posts |
| [Name] | Intro from [X] | Meeting scheduled | 12/12 | Demo on 12/15 | Pain: backlog |
| [Name] | Event | Connected | 12/8 | Follow-up email | CTO, 50 engs |

---

## 11. Cold Outbound (Supplemental)

> **Note**: Cold outreach should supplement warm strategies, not replace them. Use cold outreach to fill gaps and scale when warm channels are working.

### Prospecting Criteria

**Company signals:**
- Series A-C funded SaaS company
- 50-500 employees
- Recently raised (within 12 months)
- Engineering content on blog (shows investment in eng)
- Open engineering roles (hiring pressure)

**Individual signals:**
- CTO, VP Engineering, Head of Engineering title
- Active on LinkedIn/Twitter
- Speaks at conferences
- Previously at scaled engineering org

### Finding Prospects

**Tools:**
- LinkedIn Sales Navigator
- Crunchbase (funding data)
- GitHub (company repos, activity)
- Otta/Wellfound (job postings)

**Search queries:**
- "CTO" + "SaaS" + "Series B" + [location]
- "VP Engineering" + "hiring" + "growth"
- "Head of Engineering" + "platform" + "remote"

### Outbound Sequence (Email)

**Day 1: Initial outreach**

Subject: Quick question about [Company]'s engineering velocity

```
Hi [Name],

I noticed [Company] is hiring for [X engineering roles]. When teams grow,
the coordination overhead often grows faster than the output.

We built OmoiOS to address this: it turns feature requests into reviewed PRs
using spec-driven, multi-agent workflows. Teams ship 2-3X more with the
same headcount because the system handles execution while humans approve
at strategic points.

Would it be worth 15 minutes to see if this could help [Company] ship
faster without scaling proportionally?

—[Your name]
```

**Day 4: Follow-up with value**

Subject: Re: Quick question about [Company]'s engineering velocity

```
Hi [Name],

Following up in case this got buried. I wanted to share a quick data point:

[Case study company] used OmoiOS to ship 60% faster on routine features,
which freed their senior engineers to focus on architecture and hard problems.

If velocity is a priority for [Company], I'd love to show you how we do it.

15 minutes this week?

—[Your name]
```

**Day 9: Social proof**

Subject: How [Similar Company] increased engineering output

```
Hi [Name],

Last touch on this thread. I wanted to share what [Similar Company] achieved:

• 60% reduction in time from ticket to PR
• 70% less time in coordination meetings
• 2.5X tickets completed per sprint

They started with internal tools and integrations—bounded work where
they could validate quality before expanding.

If this isn't a priority now, no worries. But if it is, I'd love to show
you how it works in 15 minutes.

—[Your name]
```

**Day 14: Breakup email**

Subject: Should I close your file?

```
Hi [Name],

I haven't heard back, so I'm guessing the timing isn't right.

I'll close your file for now, but if engineering velocity becomes a
priority, feel free to reply to this thread.

In the meantime, here's a 3-minute video showing OmoiOS in action:
[link]

Best,
[Your name]
```

### Outbound Sequence (LinkedIn)

**Connection request:**
```
Hi [Name], I'm working on autonomous engineering execution (turning
feature requests into PRs with governance). Given your role at [Company],
thought you might find it interesting. Would love to connect.
```

**After connection accepted:**
```
Thanks for connecting! I'm curious—what's the biggest bottleneck for
[Company]'s engineering team right now? Hiring, coordination, tooling?
We've been helping teams ship 2-3X more with the same headcount.
```

**After response:**
```
That resonates with what we hear a lot. [Address their specific point]

We built OmoiOS specifically for this: spec-driven workflows where
agents handle execution and humans approve at strategic points.

Would a 15-minute demo be worth your time to see if it fits?
```

### Cold Call Script

**Opening:**
"Hi [Name], this is [Your name] from OmoiOS. We help engineering teams ship more without scaling headcount. Do you have 30 seconds?"

**If yes:**
"Great. We've noticed that as teams grow, coordination overhead grows faster than output. Teams tell us they spend 30-40% of their time on planning and status updates instead of shipping.

OmoiOS addresses this by turning feature requests into reviewed PRs using spec-driven agent workflows—with governance and visibility so you're not babysitting.

I'd love to show you a quick demo. Would 15 minutes this week work?"

**If no time:**
"Totally understand. Can I send you a 3-minute video that shows how it works? If it looks relevant, we can schedule something."

### Meeting Booking Rate Targets

| Sequence | Target |
|----------|--------|
| Cold email (4-touch) | 2-3% meeting rate |
| LinkedIn | 5-8% meeting rate |
| Warm intro | 25-30% meeting rate |
| Cold call | 3-5% conversation rate |

---

## 12. Inbound & Product-Led Growth

### PLG Funnel

```
Visitor → Sign-up → Activation → Value Moment → Conversion → Expansion
   |          |          |            |             |            |
Website   Free tier   Connect      First PR      Upgrade     More repos
                        repo       merged         to paid
```

### Activation Milestones

| Milestone | Target Time | Action if Not Met |
|-----------|-------------|-------------------|
| Account created | Immediate | — |
| Repo connected | < 24 hours | Email: "Complete your setup" |
| First spec created | < 48 hours | Email: "Start your first workflow" |
| First workflow executed | < 7 days | Email: "Let us help you get started" |
| First PR opened | < 7 days | In-app celebration |
| First PR merged | < 14 days | Email: "You just saved X hours" |

### In-App Guidance

**New user onboarding flow:**
1. Welcome modal → "Let's ship your first feature"
2. Repo connection wizard → GitHub OAuth
3. Ticket template selection → "What do you want to build?"
4. Guided first workflow → Step-by-step walkthrough
5. Success celebration → "Your PR is ready for review!"

### Product-Qualified Lead (PQL) Definition

A user becomes a PQL when:
- [ ] Completed at least 3 workflows
- [ ] Had at least 1 PR merged
- [ ] Active in the last 7 days
- [ ] On a free tier (room to upgrade)

**PQL actions:**
- Alert sales for outreach
- Trigger email: "You're getting value—let's talk about scaling"
- In-app prompt: "Upgrade for more workflows"

### Self-Serve Upgrade Flow

**Triggers:**
- Approaching workflow limit (80%)
- Trying to add team member on free tier
- Attempting to connect additional repo
- Completing 5+ successful workflows

**Upgrade prompt:**
```
You've shipped [X] features with OmoiOS. 🎉

To keep shipping at this pace, upgrade to Team:
• 50 workflows/month
• 5 repos
• Priority support

[Upgrade Now] [Talk to Sales]
```

---

## 13. Launch Sequence

### Phase 0: Pre-Launch Preparation (Weeks 1-4)

**Goals:**
- 5 design partners actively piloting
- Core messaging and positioning finalized
- Landing page live with waitlist
- 3 case studies in progress

**Weekly actions:**

| Week | Focus | Deliverables |
|------|-------|--------------|
| 1 | Partner recruitment | 10 outreach emails sent, 3 intro calls |
| 2 | Partner onboarding | 5 partners connected, first workflows running |
| 3 | Content foundation | Security doc, integration guide, FAQ |
| 4 | Website launch | Landing page, waitlist, demo video |

**Success criteria for Phase 0:**
- [ ] 5 design partners running workflows
- [ ] Landing page live with waitlist
- [ ] Demo video completed
- [ ] 100+ waitlist signups

### Phase 1: Private Beta (Weeks 5-10)

**Goals:**
- 10+ teams actively using product
- Validate pricing and packaging
- Collect case studies and testimonials
- Refine onboarding and activation

**Weekly actions:**

| Week | Focus | Deliverables |
|------|-------|--------------|
| 5-6 | Expand partners | 5 more teams onboarded |
| 7-8 | Feedback integration | Key UX improvements shipped |
| 9-10 | Case study production | 2-3 case studies published |

**Success criteria for Phase 1:**
- [ ] 10+ active pilot teams
- [ ] ≥ 50% average PR merge rate
- [ ] 2+ published case studies
- [ ] 500+ waitlist signups

### Phase 2: Public Beta (Weeks 11-16)

**Goals:**
- Open signup (with qualification)
- Self-serve onboarding working
- First paying customers
- Content marketing engine running

**Weekly actions:**

| Week | Focus | Deliverables |
|------|-------|--------------|
| 11-12 | Public launch | Open signup, PR push, HN post |
| 13-14 | Conversion optimization | Payment flow, upgrade prompts |
| 15-16 | Content scaling | 2 blog posts/week, social presence |

**Launch day checklist:**
- [ ] Landing page updated for public access
- [ ] Pricing page live
- [ ] Self-serve signup enabled
- [ ] Onboarding flow polished
- [ ] Help documentation complete
- [ ] Social media posts scheduled
- [ ] HN post drafted
- [ ] Email to waitlist ready
- [ ] PR outreach done

**Success criteria for Phase 2:**
- [ ] 50+ new signups in first week
- [ ] 3+ paying customers
- [ ] 1000+ waitlist total
- [ ] Press/blog coverage

### Phase 3: Sales-Assisted Growth (Weeks 17+)

**Goals:**
- Repeatable sales motion
- Predictable pipeline
- Expansion revenue from existing customers
- Team scaling

**Activities:**
- Hire first sales rep
- Implement sales tooling (CRM, sequences)
- Build sales playbook
- Create partner program

---

## 14. Channel Playbook

### Founder-Led Outbound (Primary Channel)

**Time investment**: 10-15 hours/week

**Daily activities:**
- 10 personalized cold emails
- 5 LinkedIn connection requests
- 2 LinkedIn DMs to connections
- Follow up on open threads

**Weekly activities:**
- 2 intro calls from referrals
- 2 demo calls
- 1 design partner check-in

**Templates and scripts**: See Appendix

### Content Marketing (Compounding Channel)

**Publish cadence**: 2 posts/week

**Content types:**
| Type | Frequency | Goal |
|------|-----------|------|
| Educational blog | 1/week | SEO + problem awareness |
| Case study | 1/month | Social proof |
| Technical deep-dive | 2/month | Developer credibility |
| Comparison post | 1/month | Capture competitor searches |

**Distribution per piece:**
- [ ] Publish on blog
- [ ] LinkedIn (company + founder posts)
- [ ] Twitter/X thread
- [ ] Relevant subreddits
- [ ] Hacker News (if substantial)
- [ ] Email to list

### Community (Relationship Channel)

**Where to participate:**
- Hacker News (comment thoughtfully, occasional Show HN)
- r/programming, r/ExperiencedDevs
- Engineering Twitter/X
- Discord servers (platform engineering, DevOps)
- CTO/engineering manager Slack communities

**Rules of engagement:**
- Provide value first, promote second
- Share real experiences and learnings
- Answer questions genuinely
- Only mention OmoiOS when directly relevant

**Goal**: 5 meaningful community interactions/week

### Events (Relationship Channel)

**Target events:**
| Type | Frequency | Approach |
|------|-----------|----------|
| Platform engineering meetups | Monthly | Demo slot or attendee |
| CTO roundtables | Quarterly | Attendee, share experiences |
| Dev conferences | 2/year | Sponsor booth or talk |

**Event ROI tracking:**
- Leads collected
- Meetings booked
- Deals influenced

---

## 15. Partnerships Strategy

### Partnership Types

| Type | Examples | Value Proposition | Effort |
|------|----------|-------------------|--------|
| **Integration partners** | GitHub, Linear, CI platforms | Better together | Medium |
| **Channel partners** | Dev agencies, fractional CTOs | We increase their delivery capacity | High |
| **Technology partners** | AI companies, cloud providers | Co-marketing, bundling | Low |

### Integration Partners

**Priority integrations:**
1. **GitHub** (Required) - Core functionality
2. **Linear** - Popular with ICP
3. **GitHub Actions** - CI integration
4. **Slack** - Notifications

**Outreach approach:**
- Start as customer (use their product)
- Build integration
- Apply to partner program
- Request co-marketing

### Channel Partners

**Ideal channel partners:**
- Development agencies (10-50 person)
- Fractional CTO services
- DevOps consulting firms

**Partner value proposition:**
```
"OmoiOS helps you deliver 2-3X more client work with the same team.
You sell the implementation, we provide the execution capacity.
15-20% referral commission on all referred deals."
```

**Partner program structure:**
- **Referral tier**: 15% commission for introductions that close
- **Reseller tier**: 20% margin, requires training and certification
- **Solution partner**: Custom pricing, joint go-to-market

### Partnership Development Process

1. **Identify**: List potential partners in each category
2. **Qualify**: Check fit (ICP overlap, no conflict, capacity)
3. **Engage**: Initial conversation about mutual benefit
4. **Pilot**: Run 1-2 joint deals to validate
5. **Formalize**: Create partner agreement
6. **Enable**: Training, materials, regular check-ins

---

## 16. Customer Success Playbook

### Success Framework

**Definition of success**: Customer achieves measurable throughput improvement and chooses to expand usage

### Health Score Model

| Factor | Weight | Healthy | At Risk |
|--------|--------|---------|---------|
| **Workflow completion rate** | 25% | ≥ 70% | < 50% |
| **PR merge rate** | 25% | ≥ 50% | < 30% |
| **Weekly active workflows** | 20% | Increasing | Declining |
| **Login frequency** | 15% | Weekly | < monthly |
| **Support tickets** | 15% | < 2/month | > 5/month |

**Health score actions:**
- **Green (80+)**: Expansion conversation
- **Yellow (50-79)**: Check-in call, identify blockers
- **Red (<50)**: Urgent intervention, exec escalation

### Customer Success Milestones

| Milestone | Timeline | CS Action |
|-----------|----------|-----------|
| **Onboarding complete** | Day 7 | Welcome call, confirm setup |
| **First value** | Day 14 | Review first merged PR, celebrate |
| **Regular usage** | Day 30 | Check-in, address friction |
| **Expansion ready** | Day 60 | Discuss additional use cases |
| **Renewal prep** | Day 75 | Review value, plan renewal |

### Check-In Meeting Agenda (30 minutes)

1. **Wins** (5 min): What's working well?
2. **Metrics review** (10 min): Workflows completed, merge rate, time savings
3. **Challenges** (10 min): What's not working? Blockers?
4. **Next steps** (5 min): Actions before next check-in

### Escalation Process

**Level 1**: CS rep handles (workflow issues, configuration)
**Level 2**: CS manager + engineering (product bugs, performance)
**Level 3**: Exec + CS lead (churn risk, major issues)

---

## 17. Onboarding Playbook

### Onboarding Goals

- **Day 1**: Account created, repo connected
- **Day 3**: First workflow started
- **Day 7**: First PR opened
- **Day 14**: First PR merged
- **Day 30**: Regular usage established

### High-Touch Onboarding (Enterprise/Business)

**Day 0: Pre-kickoff**
- [ ] Send welcome email with agenda
- [ ] Create shared Slack channel
- [ ] Provision account with correct tier
- [ ] Review their GitHub org/repos

**Day 1: Kickoff call (60 min)**
- [ ] Introductions (10 min)
- [ ] Product walkthrough (20 min)
- [ ] Connect first repo together (15 min)
- [ ] Select pilot tickets (10 min)
- [ ] Q&A and next steps (5 min)

**Day 3: First workflow**
- [ ] Async check-in: "How's your first workflow going?"
- [ ] Offer quick call if stuck

**Day 7: Check-in call (30 min)**
- [ ] Review first workflow results
- [ ] Address any issues
- [ ] Set up additional workflows
- [ ] Identify success metrics together

**Day 14: Value confirmation**
- [ ] Review merged PRs
- [ ] Calculate time savings
- [ ] Identify next use cases
- [ ] Introduce expansion opportunities

**Day 30: Success review (30 min)**
- [ ] Comprehensive metrics review
- [ ] Document wins for case study
- [ ] Plan for broader rollout
- [ ] Transition to regular cadence

### Low-Touch Onboarding (Self-Serve)

**Automated sequence:**

| Trigger | Action |
|---------|--------|
| Sign-up | Welcome email + getting started guide |
| +24h, no repo connected | Email: "Complete your setup" |
| Repo connected | Email: "Start your first workflow" |
| First workflow started | In-app guidance |
| First PR opened | Email: "Your first PR is ready!" |
| +7d, no workflow | Email: "Need help getting started?" |
| First PR merged | Email: "You just saved X hours! Here's what to try next" |

### Onboarding Content

| Content | Purpose | Format |
|---------|---------|--------|
| Getting started guide | Step-by-step setup | Doc |
| "Best tickets to start with" | Reduce friction | Blog post |
| Demo video | Show end-to-end flow | Video (3 min) |
| FAQ | Answer common questions | Doc |
| Office hours | Live help | Weekly Zoom |

---

## 18. Retention & Expansion

### Retention Levers

| Lever | Action | Impact |
|-------|--------|--------|
| **Fast time to value** | Strong onboarding | Prevents early churn |
| **Consistent quality** | Maintain merge rate | Builds trust |
| **Visible ROI** | Regular metrics reports | Justifies renewal |
| **Sticky integration** | Deep workflow embedding | Increases switching cost |
| **Relationship** | Regular check-ins | Early warning on issues |

### Churn Prevention

**Early warning signals:**
- Usage declining week-over-week
- Support tickets increasing
- Champion leaving company
- Budget discussions starting
- Silence (no engagement)

**Intervention playbook:**

| Signal | Response |
|--------|----------|
| Usage declining | Reach out for check-in, identify blockers |
| Support increasing | Escalate to engineering, priority fix |
| Champion leaving | Identify and engage new champion |
| Budget concerns | ROI review, consider downtier vs. churn |
| Silence | Outreach sequence: email → call → exec email |

### Expansion Playbook

**Expansion triggers:**
- Hitting workflow limits
- Requesting additional repos
- New team members joining
- Successful use case completed
- Renewal approaching

**Expansion conversation:**

```
"You've shipped [X] features with OmoiOS in the last [timeframe].
Based on your usage, you're [close to/hitting] your workflow limit.

I've noticed [specific success]: [example].

Would it make sense to expand to [more repos/more workflows/team tier]
so you can [specific benefit]?"
```

**Expansion offers:**
- **Upgrade tier**: More workflows, more repos
- **Add repos**: Additional teams using OmoiOS
- **Add users**: More people with access
- **Annual commit**: Discount for yearly payment

### Net Revenue Retention Target

**Goal**: 110%+ NRR

- **Gross churn**: < 5% monthly
- **Expansion revenue**: > 15% of renewals
- **Downgrades**: < 3% of renewals

---

## 19. Metrics & Milestones

### North Star Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Merged PRs per customer per week** | Primary value delivery | ≥ 3 |
| **Net Revenue Retention** | Overall business health | ≥ 110% |
| **Time to first merged PR** | Activation quality | < 60 min |

### Funnel Metrics

| Stage | Metric | Target |
|-------|--------|--------|
| Awareness | Website visitors | 10K/month |
| Interest | Waitlist signups | 500/month |
| Consideration | Demo requests | 50/month |
| Intent | Pilot starts | 20/month |
| Evaluation | Pilot completions | 15/month |
| Purchase | New customers | 5/month |

### Product Metrics

| Metric | Target | Why It Matters |
|--------|--------|----------------|
| PR merge rate | ≥ 50% | Quality indicator |
| CI pass rate (first submit) | ≥ 80% | Code quality |
| Time ticket → PR | < 60 min | Speed value |
| Human interventions per workflow | < 3 | Autonomy quality |
| Workflow completion rate | ≥ 70% | Reliability |

### Business Metrics

| Metric | Target | Timeline |
|--------|--------|----------|
| Monthly Recurring Revenue | $50K | Month 6 |
| Customers | 30 | Month 6 |
| CAC | < $2,000 | Ongoing |
| LTV:CAC | > 3:1 | Month 12 |
| Gross margin | > 70% | Month 6 |

### Milestone Checklist

**Month 1:**
- [ ] 5 design partners piloting
- [ ] Landing page live
- [ ] 100 waitlist signups

**Month 2:**
- [ ] 10 active pilot teams
- [ ] 1 case study published
- [ ] 500 waitlist signups

**Month 3:**
- [ ] 3 paying customers
- [ ] $5K MRR
- [ ] Public beta launched

**Month 6:**
- [ ] 30 paying customers
- [ ] $50K MRR
- [ ] 110%+ NRR
- [ ] Repeatable sales motion

---

## 20. Risk Mitigation

### Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Low trust/merge rate** | High | Critical | Start with safe tickets; strong gates + logs; design partner pilots |
| **Security concerns** | High | Critical | Min permissions; audit logs; security whitepaper; SOC2 roadmap |
| **Cost unpredictability** | Medium | High | Budgets/alerts; runtime caps; transparent pricing |
| **"Agent chaos"** | Medium | High | WIP limits; approval gates; discovery thresholds |
| **Competitor commoditization** | High | Medium | Differentiate on ops/governance; open-source strategy |
| **Champion churn** | Medium | Medium | Multi-thread relationships; document value broadly |
| **Slow activation** | Medium | High | Improve onboarding; high-touch for early customers |

### Risk Response Plans

**If merge rate < 30% after 30 days:**
1. Analyze failed PRs for patterns
2. Narrow to even safer ticket types
3. Add more validation steps
4. Consider manual review step before PR

**If security concerns block deals:**
1. Prioritize security whitepaper
2. Accelerate SOC2 compliance
3. Offer on-prem option for enterprise
4. Get security audit from known firm

**If competitors commoditize features:**
1. Double down on operations/governance messaging
2. Accelerate open-source strategy
3. Build community and ecosystem
4. Focus on customer success stories

---

## 21. Open Source Strategy

### Strategic Context

Software value is compressing while usage expands. This pushes toward monetizing **operations, trust, hosting, and governance**—not raw code.

### Recommended Approach: Open-Core

**Open Source (Core):**
- Local/dev single-tenant deployment
- Base workflows, specs, board, graph
- Basic agent execution loop
- Core integrations (GitHub)

**Paid (Hosted/Enterprise):**
- Multi-tenant orgs, roles, SSO
- Advanced policy controls
- Audit exports, compliance features
- Managed hosting + SLAs
- Priority support

### Pros of Open Sourcing

| Benefit | Impact |
|---------|--------|
| **Trust** | Buyers can inspect how system works |
| **Distribution** | Developers share OSS; becomes channel |
| **Community** | Contributions, bug reports, integrations |
| **Category ownership** | Define "autonomous execution" narrative |
| **Defensive moat** | If commoditized, you still lead ecosystem |

### Cons of Open Sourcing

| Risk | Mitigation |
|------|------------|
| **Fork risk** | Use source-available license (BSL) |
| **Monetization pressure** | Clear value split: core vs. enterprise |
| **Support burden** | Community forums; paid support tier |
| **Security optics** | Strong vuln disclosure process |
| **Roadmap tension** | Clear governance model |

### Licensing Options

| License | Pros | Cons |
|---------|------|------|
| **Apache/MIT** | Max adoption | Max fork risk |
| **BSL** | Protects hosted business | Some adoption friction |
| **Dual licensing** | Best of both | Complexity |

**Recommendation**: BSL or dual licensing to protect hosted business while enabling self-host evaluation.

### Timing

**Stay closed for now if:**
- Product coherence is top constraint
- Avoiding support burden while finding wedge

**Open source when:**
- Repeatable wedge found
- Core messaging stable
- Enterprise features differentiated

**Practical path:**
1. Pilot closed with design partners (now)
2. Open-source community edition once wedge proven (Month 6-9)
3. Sell hosted governance and reliability

---

## 22. 90-Day Execution Plan

### Month 1: Foundation

**Week 1:**
| Day | Focus | Deliverables |
|-----|-------|--------------|
| Mon | Outreach prep | 50 prospect list, email templates ready |
| Tue | Partner outreach | 10 personalized emails sent |
| Wed | Partner outreach | 10 more emails, follow-ups |
| Thu | Content creation | Security whitepaper draft |
| Fri | Website | Landing page wireframe |

**Week 2:**
| Day | Focus | Deliverables |
|-----|-------|--------------|
| Mon | Partner calls | 2-3 intro calls |
| Tue | Partner onboarding | First partner connected |
| Wed | Content | Integration guide draft |
| Thu | Website | Landing page development |
| Fri | Demo | Demo video scripted |

**Week 3:**
| Day | Focus | Deliverables |
|-----|-------|--------------|
| Mon | Partner support | Help partners run first workflows |
| Tue | Content | FAQ document |
| Wed | Demo | Record demo video |
| Thu | Website | Landing page polish |
| Fri | Launch | Soft launch landing page |

**Week 4:**
| Day | Focus | Deliverables |
|-----|-------|--------------|
| Mon | Outreach | Send 20 new prospect emails |
| Tue | Partner check-ins | 30-min calls with each partner |
| Wed | Content | First blog post |
| Thu | Analysis | Review partner metrics |
| Fri | Planning | Month 2 planning |

**Month 1 checklist:**
- [ ] 5 design partners running workflows
- [ ] Landing page live with waitlist
- [ ] Demo video completed
- [ ] Security whitepaper published
- [ ] 100+ waitlist signups

### Month 2: Validation

**Focus areas:**
- Expand to 10+ pilot teams
- Validate pricing with early adopters
- Produce first case studies
- Begin content marketing

**Key activities:**
- 20 new outbound emails/week
- 2 blog posts
- 2 case study interviews
- Weekly partner check-ins
- Pricing page development

**Month 2 checklist:**
- [ ] 10+ active pilot teams
- [ ] 500+ waitlist signups
- [ ] 2 case studies drafted
- [ ] Pricing validated with 3+ partners
- [ ] First paid customer commit

### Month 3: Launch

**Focus areas:**
- Public beta launch
- Convert pilots to paid
- Scale content marketing
- Build repeatable sales motion

**Key activities:**
- Launch announcement (HN, Product Hunt, LinkedIn)
- Email waitlist
- PR outreach
- Paid customer onboarding
- Sales process documentation

**Month 3 checklist:**
- [ ] Public beta live
- [ ] 3+ paying customers
- [ ] $10K+ MRR
- [ ] 1000+ waitlist signups
- [ ] Sales playbook documented

---

## 23. Appendix: Templates & Scripts

### Cold Email Templates

**Template 1: Pain-based opener**
```
Subject: [Company]'s engineering velocity

Hi [Name],

I saw [Company] is [hiring engineers / recently raised / launching new product].
When engineering teams grow, coordination overhead often grows faster than output.

We built OmoiOS to address this: it turns feature requests into reviewed PRs
using spec-driven, multi-agent workflows. Teams ship 2-3X more with the same
headcount because the system handles execution while humans approve at
strategic points.

Worth 15 minutes to see if this could help [Company]?

—[Your name]
```

**Template 2: Social proof opener**
```
Subject: How [Similar Company] increased shipping velocity

Hi [Name],

[Similar Company] was struggling with [specific pain]. After implementing
OmoiOS, they:
• Reduced time-to-PR by 60%
• Cut coordination meetings by 70%
• Shipped 2.5X more tickets per sprint

Given [Company]'s growth, I thought you might face similar challenges.

Would 15 minutes be worth seeing how they did it?

—[Your name]
```

**Template 3: Direct ask**
```
Subject: Can I ship one PR in your repo?

Hi [Name],

I'm building OmoiOS: an autonomous engineering execution dashboard that turns
feature requests into reviewed PRs via spec-driven, multi-agent workflows.

Rather than pitch you, I'd like to prove it. Give me one well-scoped ticket
from your backlog, and I'll deliver a PR end-to-end so you can judge the
quality yourself.

Worth a 20-minute call this week to set it up?

—[Your name]
```

### LinkedIn Templates

**Connection request:**
```
Hi [Name], I'm working on autonomous engineering execution for SaaS teams.
Given your role at [Company], thought you'd find it interesting. Would love
to connect.
```

**First message after connection:**
```
Thanks for connecting, [Name]!

Quick question: What's the biggest bottleneck for [Company]'s engineering
team right now? Hiring? Coordination? Something else?

We've been helping teams ship 2-3X more with the same headcount, curious
if our approach might help.
```

**Follow-up:**
```
That resonates with what we hear from a lot of [Company type] teams.

OmoiOS addresses exactly that by [specific solution to their pain].

Would a 15-minute demo be worth your time to see if it fits?
```

### Demo Script

**Opening (2 min):**
"Thanks for taking the time. Before I dive in, what's the main challenge
you're hoping OmoiOS might solve?"

[Listen and acknowledge]

"Perfect, I'll make sure to address that. Let me show you how OmoiOS works."

**Core demo (5-7 min):**
1. "Here's a real feature request from a backlog"
2. "OmoiOS turns it into a spec: requirements, design, tasks" [show workspace]
3. "Now execution starts: agents pick up unblocked tasks" [show board]
4. "Watch: a discovery happens—spawns a new task with reasoning" [show discovery]
5. "Phase gate: artifacts/tests checked; I approve" [show gate]
6. "PR opens; I review like normal" [show PR]

**Wrap-up (3 min):**
"From feature request to reviewable PR in [X] minutes. The key differences
from other AI tools: structured workflow, full visibility, and approval
gates so you stay in control.

Questions? And would you want to see this on your actual repo?"

### Follow-up Email After Demo

```
Subject: OmoiOS demo follow-up

Hi [Name],

Thanks for taking the time today. Here's a quick summary:

**What we covered:**
- Spec-driven workflow: Requirements → Design → Tasks → Execution
- Discovery branching: workflows adapt when reality changes
- Phase gates: you approve at strategic points, not every step

**What you mentioned matters to you:**
- [Specific pain point they mentioned]
- [Second point if applicable]

**Next steps we discussed:**
- [Whatever you agreed on]

Let me know if any questions come up. Happy to do another session with
your team if helpful.

—[Your name]

P.S. Here's the demo video in case you want to share with colleagues: [link]
```

### Objection Response Cheat Sheet

| Objection | Response |
|-----------|----------|
| "We use Copilot" | "Great—they're complementary. Copilot helps individuals, we help teams." |
| "How's this different from Devin?" | "Devin demos well. We ship well. Want to try both on your repo?" |
| "What if it makes mistakes?" | "It will. But mistakes are in isolated branches, caught at PR review." |
| "We might build this ourselves" | "You could. Is 6-12 months of your best engineers the best use?" |
| "Not a priority right now" | "Understood. Coordination overhead compounds. Worth a quick look?" |
| "Need to talk to my team" | "Of course. Want me to join a call to answer technical questions?" |
| "What's the pricing?" | "Starts at $499/month for teams. Want to discuss what tier fits?" |

---

*This document should be reviewed and updated monthly based on market feedback and learnings.*
