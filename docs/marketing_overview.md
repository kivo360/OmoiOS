# OmoiOS Marketing Overview

**Created**: 2025-12-15  
**Updated**: 2025-12-15  
**Status**: Active  
**Purpose**: Clear buyer-facing positioning, messaging, competitive intelligence, and actionable marketing playbook for OmoiOS.

---

## Table of Contents

1. [Product in One Sentence](#product-in-one-sentence)
2. [Product Concept (30 Seconds)](#product-concept-30-seconds)
3. [The Core Narrative to Sell](#the-core-narrative-to-sell)
4. [Value Metrics & ROI Framework](#value-metrics--roi-framework)
5. [What Buyers Are Buying](#what-buyers-are-buying-benefits)
6. [Key Features → Buyer-Visible Outcomes](#key-features--buyer-visible-outcomes)
7. [Ideal Customer Profile](#ideal-customer-profile-focus)
8. [Buyer Journey Map](#buyer-journey-map)
9. [Positioning & Category](#positioning-what-category-are-you-in)
10. [Competitive Battle Cards](#competitive-battle-cards)
11. [Messaging Framework](#messaging-framework)
12. [Objection Handling Playbook](#objection-handling-playbook)
13. [Content Strategy](#content-strategy)
14. [Landing Page Blueprint](#landing-page-blueprint)
15. [Email Sequences](#email-sequences)
16. [Sales Enablement Materials](#sales-enablement-materials)
17. [Case Study Template](#case-study-template)
18. [The Focus Statement](#the-focus-statement)

---

## Product in One Sentence

**OmoiOS is an autonomous engineering execution dashboard that turns feature requests into reviewed pull requests using spec-driven, multi-agent workflows—with real-time visibility, discovery-based branching, and steering.**

---

## Product Concept (30 Seconds)

Connect a GitHub repo, write a feature request, and OmoiOS produces an executable workflow: **Requirements → Design → Tasks → Execution**. Multiple agents work in parallel in isolated workspaces/branches, run tests/validation loops, and open PRs. When agents discover missing requirements, bugs, integration issues, or optimizations, OmoiOS **spawns and links new work** (tickets/tasks) in the right phase instead of stalling. Humans stay in control at the right moments via **phase gates** and **PR review**.

---

## The Core Narrative to Sell

### 1) Automated Workflows (Structured Autonomy)
- **Input**: feature request + repo context
- **Process**: spec-driven phases with done definitions and expected outputs
- **Output**: tasks, execution, artifacts, and PRs

### 2) Task/Ticket Discovery (Work Adapts to Reality)
- Agents **record discoveries** (bug, optimization, clarification needed, integration issue, technical debt, security/perf issue)
- Discoveries **spawn new tasks in any phase**, linked back to the source, so workflows can branch instead of breaking

### 3) Steering (Self-Healing Execution)
- Monitoring detects stuck/drifting/idle behavior and triggers interventions (diagnose, reallocate, override priority, cancel)
- Goal: **users intervene at decision points**, not as babysitters

---

## Value Metrics & ROI Framework

### Quantifiable Value Propositions

| Metric | Before OmoiOS | With OmoiOS | Improvement |
|--------|---------------|-------------|-------------|
| **Time to first PR** (small ticket) | 2-4 hours | < 60 minutes | 60-75% faster |
| **Engineering time on routine tasks** | 40% of sprint | 10% of sprint | 30% time saved |
| **Coordination overhead** (meetings/status) | 8-10 hrs/week | 2-3 hrs/week | 70% reduction |
| **Context switching interrupts** | 15-20/day | 3-5/day | 75% reduction |
| **Backlog velocity** | X tickets/sprint | 2-3X tickets/sprint | 2-3X throughput |

### ROI Calculator Framework

```
Monthly Value = (Hours Saved × Avg Engineer Rate) + (Additional Features Shipped × Feature Value)

Example for 20-engineer team:
- Hours saved: 20 engineers × 8 hrs/week × 4 weeks = 640 hours/month
- At $75/hr fully loaded cost: $48,000/month potential value
- If OmoiOS captures 25% of this: $12,000/month value
- Typical OmoiOS cost: $2,000-5,000/month
- ROI: 2.4-6X return
```

### Proof Points to Collect from Early Customers

**ACTION ITEM**: Track and document these metrics with every design partner:

1. **Time metrics**
   - Time from ticket creation → PR opened
   - Time from PR opened → merged
   - Total cycle time reduction

2. **Quality metrics**
   - PR merge rate (target: ≥50%)
   - CI pass rate on first PR submission
   - Rollback rate (target: <5%)

3. **Productivity metrics**
   - Number of human interventions per workflow
   - Hours saved per engineer per week
   - Additional tickets completed per sprint

4. **Cost metrics**
   - Cost per merged PR
   - Compute/model spend per feature

---

## What Buyers Are Buying (Benefits)

### Primary Benefits (Lead With These)

| Benefit | Buyer Resonance | Proof Point Needed |
|---------|-----------------|-------------------|
| **More shipped output without headcount growth** | CTOs under hiring pressure | "Shipped 3X more tickets with same team size" |
| **Less coordination tax** | EMs drowning in standups | "Reduced planning meetings by 70%" |
| **Workflows that adapt when reality changes** | Teams burned by rigid plans | "Discovered and fixed 12 edge cases automatically" |
| **Higher trust vs chat-to-code** | Security-conscious orgs | "Every change is PR-reviewed with full audit trail" |
| **Visible, controllable autonomy** | Risk-averse leaders | "Real-time dashboard + phase gates at every stage" |

### Secondary Benefits (Support Claims)

- **24/7 execution**: Agents work while the team sleeps
- **Institutional knowledge capture**: Learnings stored and reused across workflows
- **Reduced onboarding friction**: New team members can contribute faster via spec-driven workflows
- **Consistent quality**: Validation loops ensure standards are met every time

---

## Key Features → Buyer-Visible Outcomes

| Feature | Technical Description | Buyer-Facing Outcome |
|---------|----------------------|---------------------|
| **Spec workspace** | Requirements/Design/Tasks/Execution tabs | "Intent becomes an executable plan you can approve" |
| **Adaptive phase-based workflows** | Phase jumping, discovery branching | "The system can jump phases or branch when new info appears" |
| **Kanban board + dependency graph** | Real-time task visualization | "You always know what's blocked and why" |
| **Multi-agent parallel work** | Isolated workspaces/branches | "Multiple workstreams move at once without conflicts" |
| **Phase gates + validation** | Quality checks before progression | "Quality is enforced before progressing; no silent skipping" |
| **Diagnostic reasoning trail** | Full audit log of decisions | "Transparent 'why' behind spawned work and interventions" |
| **Git integration** | Commits/PRs linked to tickets | "Fits existing dev workflow; reviewable outputs" |
| **Guardian monitoring** | 60-second trajectory checks | "Self-healing: detects drift/stuck loops and corrects course" |
| **Cost/budget tracking** | Spend visibility per org/project | "Operational control with spend constraints" |

---

## Ideal Customer Profile (Focus)

### Primary ICP: Mid-Market SaaS Engineering Teams

**Firmographics:**
- **Company size**: 50-500 employees
- **Engineering team**: 10-100 engineers
- **Stage**: Series A-C funded or profitable
- **Industry**: B2B SaaS, developer tools, fintech, healthtech

**Technographics:**
- GitHub as primary repo (required)
- Established PR review culture
- Using or evaluated AI coding tools (Copilot, Cursor)
- Modern CI/CD pipeline (GitHub Actions, CircleCI)

**Psychographics:**
- **Pain**: Hiring pressure, backlog growing faster than capacity
- **Belief**: AI can help but needs governance
- **Budget**: Already spending on developer productivity tools
- **Decision style**: Data-driven, wants to pilot before committing

**Buying Triggers:**
- Failed to fill open engineering roles
- Missed a major release deadline
- Investor pressure to ship faster
- Recently evaluated AI coding tools but found them insufficient

### Secondary ICP: High-Velocity Startups

**Firmographics:**
- **Company size**: 5-50 employees
- **Engineering team**: 2-10 engineers
- **Stage**: Seed to Series A
- **Industry**: Any technology-focused

**Key Characteristics:**
- Moving fast with limited resources
- Technical founder(s) at the helm
- Need to punch above their weight in output

### Disqualified Profiles (Not a Fit)

| Profile | Why Not | Alternative Message |
|---------|---------|-------------------|
| "Zero human review" teams | OmoiOS requires PR approval | "We believe reviewable output is a feature, not a bug" |
| No Git/PR culture | Foundational requirement | "OmoiOS works best with established Git workflows" |
| Highly regulated (strict) | Unless they accept gated model | "Our approval workflow can support compliance needs" |
| Junior-only teams | Need senior judgment for approvals | "Best for teams with senior engineers who can validate output" |

---

## Buyer Journey Map

### Stage 1: Problem Aware

**Trigger events:**
- Missed sprint goals 2+ times
- Engineering team > 10 people
- Backlog growing faster than velocity
- Failed hire or long open req

**Questions they're asking:**
- "How do we ship more without hiring?"
- "Why is so much time spent on coordination?"
- "Can AI actually help with real development work?"

**Content to serve:**
- Blog: "The Hidden Tax of Engineering Coordination"
- Calculator: "How Much Is Your Backlog Really Costing?"

### Stage 2: Solution Aware

**Behavior:**
- Researching AI coding tools
- Comparing agents, assistants, platforms
- Asking peers about experiences

**Questions they're asking:**
- "What's different about agentic approaches?"
- "How do I avoid the AI chaos stories I've heard?"
- "Can I trust this with production code?"

**Content to serve:**
- Comparison: "OmoiOS vs. AI Assistants: Different Problems, Different Solutions"
- Video: "From Feature Request to Merged PR in 45 Minutes"

### Stage 3: Product Aware

**Behavior:**
- On your website
- Signed up for waitlist
- Watching demos

**Questions they're asking:**
- "How does this integrate with our stack?"
- "What types of work does this handle well?"
- "What's the risk if it goes wrong?"

**Content to serve:**
- Interactive demo
- Integration guides
- Trust & security documentation

### Stage 4: Evaluation

**Behavior:**
- Pilot / design partner
- Running first workflows
- Comparing results to expectations

**Questions they're asking:**
- "Is the output quality acceptable?"
- "How much oversight does this really need?"
- "What's the TCO?"

**Content to serve:**
- ROI calculator
- Case studies with metrics
- Best practices guide

### Stage 5: Decision

**Behavior:**
- Internal champion building buy-in
- Procurement / security review
- Contract negotiation

**Questions they're asking:**
- "How do I justify this to leadership?"
- "What's the security posture?"
- "What does success look like at 6 months?"

**Content to serve:**
- Executive summary deck
- Security whitepaper
- Success roadmap template

---

## Positioning: What Category Are You In?

### Category Definition

**Primary**: Autonomous Engineering Execution Platform  
**Secondary**: AI-Powered Development Workflow Orchestration

### Positioning Statement

> For **engineering teams at mid-market SaaS companies** who struggle with **shipping velocity and coordination overhead**, OmoiOS is an **autonomous engineering execution platform** that **turns feature requests into reviewed PRs using spec-driven, multi-agent workflows**. Unlike **AI coding assistants** that help individuals write code faster, OmoiOS **orchestrates complete development workflows with governance, visibility, and self-healing execution**.

### Category Comparison

| Category | What They Do | OmoiOS Difference |
|----------|--------------|-------------------|
| **AI Coding Assistants** (Copilot, Cursor) | Help individual devs write code | System-level execution + coordination |
| **Ticketing Tools** (Jira, Linear) | Track work status | Track AND execute work |
| **Agent Frameworks** (LangGraph, CrewAI) | Primitives to build agent workflows | Productized: dashboards, gates, monitoring |
| **Autonomous Coding** (Devin) | Autonomous code generation | Structured workflow + governance + visibility |

---

## Competitive Battle Cards

### vs. GitHub Copilot / Cursor

**Their Positioning**: AI pair programmer that helps you write code faster

**Where They Win**:
- Per-developer productivity
- In-IDE experience
- Code completion accuracy

**Where We Win**:
- Team-level execution & coordination
- Complete workflow automation (not just code)
- Governance, visibility, and audit trail
- Self-healing execution

**Key Differentiator**: "Copilot helps one developer write code faster. OmoiOS helps teams ship complete features faster with governance."

**Objection Response**: "We're complementary—your devs can use Copilot for individual coding while OmoiOS handles the workflow orchestration and execution for defined features."

### vs. Devin / Cognition

**Their Positioning**: Fully autonomous AI software engineer

**Where They Win**:
- Strong "wow factor" demos
- End-to-end autonomy narrative
- Well-funded marketing

**Where We Win**:
- Structured workflow with approvals (safer)
- Real-time visibility (what's happening)
- Self-healing execution (doesn't stall)
- Discovery branching (adapts to reality)

**Key Differentiator**: "Devin promises full autonomy. OmoiOS delivers autonomy with oversight—so you get shipped code, not surprise disasters."

**Objection Response**: "Full autonomy sounds great until something goes wrong at 2am. OmoiOS gives you autonomy with phase gates, so you get speed AND control."

### vs. Linear / Jira

**Their Positioning**: Modern project management for software teams

**Where They Win**:
- Established category
- Team collaboration features
- Deep integrations

**Where We Win**:
- Work is executed, not just tracked
- Autonomous progress without human pushing
- Real-time visibility into actual execution

**Key Differentiator**: "Linear tracks what needs to be done. OmoiOS tracks it AND does it."

**Objection Response**: "We integrate with your existing tools. Think of OmoiOS as the execution layer that makes your Linear board actually move."

### vs. Build Your Own (LangGraph, CrewAI)

**Their Positioning**: Flexible agent orchestration frameworks

**Where They Win**:
- Full customization
- No vendor lock-in
- Developer appeal

**Where We Win**:
- Productized immediately (no build time)
- Dashboards, gates, monitoring included
- Self-healing already works
- Budget controls built in

**Key Differentiator**: "You could build it, but that's 6-12 months of engineering time. OmoiOS is ready now with enterprise governance included."

**Objection Response**: "How much is 6 months of your best engineers' time worth? And then you still need to maintain it."

---

## Messaging Framework

### By Persona

#### For CTOs / Heads of Engineering

**Primary message**: "Ship more without scaling headcount proportionally"

**Supporting messages**:
- "Predictable delivery with autonomous execution"
- "Governance and audit trails for enterprise confidence"
- "Budget controls that prevent runaway costs"

**Avoid**: Technical implementation details, agent framework comparisons

#### For Engineering Managers

**Primary message**: "Less coordination tax, more shipped features"

**Supporting messages**:
- "Real-time visibility into every workstream"
- "No more babysitting agents or manual intervention"
- "Blockers surface automatically, not in standups"

**Avoid**: ROI calculations, security deep-dives

#### For Staff/Senior Engineers

**Primary message**: "Offload the boring work, keep the interesting problems"

**Supporting messages**:
- "PRs that are actually reviewable and merge-ready"
- "Consistent quality via automated validation"
- "More time for architecture, less for scaffolding"

**Avoid**: Management metrics, cost justifications

### By Use Case

| Use Case | Headline | Subhead |
|----------|----------|---------|
| **Internal tools** | "Stop building admin panels manually" | "Describe what you need, get a working dashboard in hours" |
| **Integrations** | "Ship your Stripe integration by Friday" | "OmoiOS handles the boilerplate, you handle the edge cases" |
| **Refactoring** | "Refactor with confidence at scale" | "Spec-driven changes with validation at every step" |
| **Feature development** | "From idea to PR in 45 minutes" | "Autonomous execution with human approval at the right moments" |

### By Stage of Awareness

| Stage | Headline | CTA |
|-------|----------|-----|
| **Problem aware** | "Drowning in coordination? There's a better way." | Read our guide |
| **Solution aware** | "AI coding tools aren't enough. Here's what's next." | Watch the demo |
| **Product aware** | "Turn feature requests into reviewed PRs—autonomously." | Start free pilot |
| **Evaluating** | "See OmoiOS ship a real feature in your repo." | Book a pilot call |

---

## Objection Handling Playbook

### Trust & Safety Objections

**"Can I trust it?"**

> "Trust is earned, not assumed. That's why OmoiOS is designed for reviewable outputs: every change goes through a PR, every phase has approval gates, and every decision has a reasoning trail. You approve when it matters, and the system explains its choices. Start with low-risk tickets and expand as confidence grows."

**Evidence to provide**: Security whitepaper, audit log demo, customer testimonial about trust

---

**"Will it create chaos in my repo?"**

> "Everything happens in isolated branches with ticket/commit traceability. Nothing merges without your explicit approval. If anything goes sideways, you roll back a single branch—your main is never touched without PR review."

**Evidence to provide**: Branch isolation diagram, rollback demo

---

**"What if it makes mistakes?"**

> "It will—AI isn't perfect. But OmoiOS is designed for recoverable mistakes: isolated branches, validation loops, and phase gates catch issues early. When mistakes happen, you see them in PR review like any other code. The question isn't 'will it be perfect?' but 'is it faster than the alternative, with acceptable quality?'"

**Evidence to provide**: Error recovery demo, customer quote about acceptable error rate

---

### Value & ROI Objections

**"Why not just use ChatGPT/Copilot?"**

> "Those help individuals write code faster—great for productivity. OmoiOS is about team-level execution: planning, parallelization, tracking, validation loops, approvals, and keeping workflows unstuck. It's the difference between helping one person type faster and helping the whole team ship more."

**Evidence to provide**: Comparison table, workflow demo showing full execution

---

**"What's the ROI?"**

> "Let's calculate it for your team. [Use ROI calculator] The typical pattern: teams save 8-10 hours per engineer per week on coordination and routine implementation. At a 20-engineer team, that's 160-200 hours/week. Even capturing 25% of that value significantly exceeds OmoiOS costs."

**Evidence to provide**: ROI calculator, customer case study with metrics

---

**"We're not sure this is a priority right now."**

> "I get it—there's always more to do than time to do it. But here's the thing: coordination overhead compounds. The bigger your team gets, the worse it gets. Teams that solve this now ship faster while teams that wait fall further behind. Would a low-commitment pilot help you evaluate without a big time investment?"

**Evidence to provide**: Data on coordination overhead scaling, pilot offer

---

### Technical Objections

**"What if requirements are unclear?"**

> "The system is designed for reality, not perfect inputs. When agents discover unclear requirements, they spawn a 'clarification-needed' task and block dependent work rather than guessing. The workflow branches back to requirements phase—you get a clear question instead of garbage output."

**Evidence to provide**: Discovery branching demo, clarification workflow example

---

**"How does it handle complex codebases?"**

> "OmoiOS analyzes your codebase to understand patterns, conventions, and architecture before execution. It works in isolated branches with your existing test suites. For complex codebases, we recommend starting with bounded features and expanding as the system learns your patterns."

**Evidence to provide**: Codebase analysis demo, complex integration customer story

---

**"What about security and code access?"**

> "We use GitHub's OAuth with minimal required permissions—read/write access scoped to repos you connect. All execution happens in isolated workspaces. We're working toward SOC2 compliance for enterprise customers. We can walk through our security architecture in detail."

**Evidence to provide**: Security whitepaper, permission scope documentation

---

### Competitive Objections

**"We're looking at [Devin / competitor]."**

> "Great—you should evaluate options. Here's what we've heard from teams who looked at both: Devin is impressive for demos, but OmoiOS is built for production workflows. The key differences are governance (phase gates and approvals), visibility (real-time dashboard), and reliability (self-healing execution). We're happy to do a side-by-side comparison on your actual tickets."

**Evidence to provide**: Competitive comparison, side-by-side pilot offer

---

**"We might build something ourselves."**

> "You could, and some teams do. The question is whether that's the best use of your engineering capacity. Building a production-grade system like OmoiOS takes 6-12 months of your best engineers, plus ongoing maintenance. Most teams decide that time is better spent on their core product. But if you do build, we'd love to share what we've learned."

**Evidence to provide**: Build-vs-buy analysis, complexity breakdown

---

## Content Strategy

### Content Pillars

| Pillar | Goal | Formats | Keywords |
|--------|------|---------|----------|
| **Education** | Build problem awareness | Blog posts, guides, calculators | engineering productivity, coordination overhead, backlog management |
| **Differentiation** | Distinguish from alternatives | Comparisons, battle cards, webinars | AI coding, autonomous engineering, Devin alternative |
| **Social proof** | Build credibility | Case studies, testimonials, demos | AI development workflow, automated PRs |
| **Technical depth** | Win power users | Architecture posts, integration guides | multi-agent workflow, spec-driven development |

### Editorial Calendar (First 90 Days)

**Week 1-2: Foundation**
- [ ] Publish "What Is Autonomous Engineering Execution?"
- [ ] Publish security whitepaper
- [ ] Create interactive demo

**Week 3-4: Problem Education**
- [ ] "The True Cost of Engineering Coordination" (blog)
- [ ] "Why AI Coding Assistants Aren't Enough" (blog)
- [ ] Coordination cost calculator (tool)

**Week 5-6: Differentiation**
- [ ] "OmoiOS vs. AI Assistants: Different Problems, Different Solutions" (comparison)
- [ ] "Structured Autonomy: Why Governance Matters for AI Engineering" (blog)

**Week 7-8: Social Proof**
- [ ] First customer case study
- [ ] "From Feature Request to PR in 45 Minutes" (video demo)

**Week 9-10: Technical Depth**
- [ ] "How Discovery Branching Keeps Workflows Unstuck" (technical blog)
- [ ] GitHub integration guide

**Week 11-12: Scaling**
- [ ] Webinar: "Autonomous Engineering in Practice"
- [ ] Second case study
- [ ] Community launch (Discord or similar)

### SEO Keyword Targets

**Primary (high intent):**
- autonomous engineering platform
- AI development workflow automation
- automated PR generation
- Devin alternative

**Secondary (educational):**
- engineering coordination overhead
- multi-agent development workflow
- AI-powered code review
- spec-driven development

### Content Distribution Checklist

For each piece of content:
- [ ] Publish on blog
- [ ] Post to LinkedIn (company + founders)
- [ ] Post to Twitter/X
- [ ] Submit to Hacker News (if substantial)
- [ ] Share in relevant Discord/Slack communities
- [ ] Send to email list
- [ ] Add to sales enablement library

---

## Landing Page Blueprint

### Hero Section

**Headline**: "Autonomous Engineering Execution."

**Subhead**: "Turn feature requests into reviewed PRs with spec-driven, multi-agent workflows."

**Primary CTA**: "Start Your Free Pilot" (high intent)

**Secondary CTA**: "Watch Demo" (lower intent)

**Hero visual**: Animated workflow showing ticket → spec → execution → PR

### Value Propositions Section

**Structure**: 3-4 card layout

| Card | Icon | Headline | Description |
|------|------|----------|-------------|
| 1 | 📋 | Spec-Driven | Requirements → Design → Tasks → Execution |
| 2 | 🔀 | Adaptive | Discovery-based branching when reality changes |
| 3 | 👁️ | Visible | Real-time Kanban, dependency graph, activity timeline |
| 4 | ✅ | Controlled | Phase gates and PR reviews at strategic points |

### How It Works Section

**Structure**: 5-step visual timeline

1. **Connect GitHub** — Link your repo with OAuth
2. **Describe a feature** — Natural language input
3. **Approve the plan** — Review generated spec
4. **Agents implement** — Autonomous execution with visibility
5. **Review & merge** — Standard PR workflow

### Social Proof Section

**Components**:
- Logo bar of customer companies
- 2-3 testimonial quotes with photos
- Key metric callouts ("50% faster time to PR", "70% less coordination overhead")

### Use Cases Section

**Structure**: Tab interface

| Tab | Content |
|-----|---------|
| Internal Tools | "Ship admin panels in hours, not weeks" + mini case study |
| Integrations | "Stripe, Slack, webhooks—done right" + mini case study |
| Feature Development | "From idea to PR in 45 minutes" + mini case study |
| Refactoring | "Large-scale changes with confidence" + mini case study |

### Trust Section

**Components**:
- Security overview (permissions, isolation, audit trail)
- "How OmoiOS keeps you in control" (phase gates explainer)
- Link to security whitepaper

### FAQ Section

**Essential questions**:
1. How is this different from GitHub Copilot?
2. What happens if the AI makes a mistake?
3. What types of tasks work best with OmoiOS?
4. How much does OmoiOS cost?
5. Is my code secure?
6. Can I try it before committing?

### Final CTA Section

**Headline**: "Ready to ship more with the team you have?"

**CTA options**:
- Primary: "Start Your Free Pilot"
- Secondary: "Talk to Sales"
- Tertiary: "Watch Demo"

### Conversion Optimization Tips

- **Above the fold**: Hero + primary CTA visible without scrolling
- **Trust signals**: Security badges, customer logos visible early
- **Multiple CTAs**: Different intent levels at each section
- **Exit intent**: Popup offering demo or content download
- **Live chat**: Available for immediate questions
- **Page speed**: < 3 second load time

---

## Email Sequences

### Waitlist Welcome Sequence

**Email 1** (Immediately after signup)
- Subject: "You're on the OmoiOS waitlist 🎉"
- Content: Welcome, confirm subscription, set expectations for timeline
- CTA: Watch demo video

**Email 2** (Day 3)
- Subject: "How OmoiOS turns feature requests into PRs"
- Content: High-level product overview, key differentiators
- CTA: Read comparison guide

**Email 3** (Day 7)
- Subject: "The coordination tax is costing you more than you think"
- Content: Problem education, ROI framework
- CTA: Use coordination cost calculator

**Email 4** (Day 14)
- Subject: "See OmoiOS ship a real feature"
- Content: Video walkthrough of complete workflow
- CTA: Book pilot call

### Post-Demo Nurture Sequence

**Email 1** (Day 1 after demo)
- Subject: "Thanks for checking out OmoiOS"
- Content: Recap key points from demo, address common questions
- CTA: Start pilot

**Email 2** (Day 4)
- Subject: "Case study: [Company] shipped 3X more with OmoiOS"
- Content: Customer success story with metrics
- CTA: Start pilot

**Email 3** (Day 8)
- Subject: "The best tickets to start with on OmoiOS"
- Content: Best practices guide for first pilot
- CTA: Start pilot

**Email 4** (Day 14)
- Subject: "Quick question about your evaluation"
- Content: Check-in, offer to answer questions or do second demo
- CTA: Reply or book call

---

## Sales Enablement Materials

### One-Pager (PDF)

**Content structure**:
- Hero statement + key differentiators
- How it works (visual)
- Key metrics / proof points
- Customer logos
- Pricing overview
- Contact CTA

### Demo Checklist (2 Minutes)

**Setup** (30 seconds):
1. "Here's a feature request from a real backlog"
2. "Watch what OmoiOS does with it"

**Execution** (90 seconds):
3. "OmoiOS turns it into a spec: requirements, design, tasks" (show workspace)
4. "Now execution starts: multiple agents pick up unblocked tasks" (show board moving)
5. "Watch: a discovery happens—OmoiOS spawns a new task and links the reasoning" (show discovery)
6. "Phase gate triggers: artifacts/tests are checked; I approve" (show gate)
7. "A PR is opened; I review like normal" (show PR)

**Close** (30 seconds):
8. "From feature request to reviewable PR in [X] minutes"
9. "Want to see this on your repo?"

### Discovery Call Questions

**Problem qualification:**
- "How many engineers are on your team?"
- "What's your current sprint velocity vs. backlog growth?"
- "How much time does your team spend in planning/coordination meetings?"
- "Have you tried AI coding tools? What worked/didn't work?"

**Technical qualification:**
- "What's your GitHub setup? PR review process?"
- "What types of tickets take the most time but are most routine?"
- "Who would need to approve a tool like this?"

**Urgency/timeline:**
- "What's driving your interest in this now?"
- "If this worked, what would success look like in 6 months?"
- "What would make you not move forward?"

### Competitive Positioning Quick Reference

| Competitor | Our Advantage | Key Question to Ask Prospect |
|------------|---------------|----------------------------|
| Copilot | Team-level vs. individual | "Are you looking to help individual devs or increase team throughput?" |
| Devin | Governance + visibility | "How important is oversight and audit trails for your team?" |
| Build own | Time to value | "What's the opportunity cost of 6-12 months of engineering time?" |
| Do nothing | Compounding cost | "How is coordination overhead changing as your team grows?" |

---

## Case Study Template

### Structure

**1. Company Overview** (2 sentences)
- Who they are, size, industry

**2. The Challenge** (3-4 sentences)
- Specific problem they faced
- Impact on business (metrics if possible)
- What they tried before

**3. Why OmoiOS** (2-3 sentences)
- Why they chose OmoiOS
- Key deciding factors

**4. The Solution** (3-4 sentences)
- How they implemented
- What workflows they use
- How it fits their process

**5. The Results** (bullet points)
- Time saved: X%
- Throughput increase: X%
- Specific metrics

**6. Quote** (1-2 sentences)
- Attribution with name, title, company

**7. Key Takeaways** (3 bullets)
- Reusable insights for other prospects

### Example Draft

> **Company Overview**
> TechCorp is a Series B SaaS company with a 35-person engineering team building developer productivity tools.
>
> **The Challenge**
> TechCorp's engineering team was growing, but their backlog was growing faster. Planning meetings consumed 12 hours per week across the team, and context-switching between tasks killed deep work. They tried AI coding assistants but found them insufficient for complete workflow automation.
>
> **Why OmoiOS**
> TechCorp chose OmoiOS because of its structured approach to autonomous execution. The phase gates and PR-based delivery gave them confidence to trust the system with real features.
>
> **The Solution**
> TechCorp started with internal tools and integration features—bounded work with clear requirements. They now run 15-20 OmoiOS workflows per sprint alongside their normal development process.
>
> **The Results**
> - 60% reduction in time from ticket to PR for routine features
> - 70% less time spent in planning/coordination meetings
> - 2.5X increase in tickets completed per sprint
> - $0 rollbacks from OmoiOS-generated code in 6 months
>
> **Quote**
> "OmoiOS gave us back the time we were losing to coordination. Our engineers now spend their time on hard problems, not boilerplate." — Jane Smith, CTO, TechCorp
>
> **Key Takeaways**
> - Start with bounded features (internal tools, integrations)
> - Phase gates build trust over time
> - ROI comes from coordination savings, not just code generation

---

## The Focus Statement

**OmoiOS is for teams who want autonomous execution with oversight: fewer coordination cycles, adaptive workflows via discovery, and reviewable PR-based delivery.**

This is the filter for every marketing decision:
- Does this message emphasize **autonomous execution with oversight**?
- Does this feature reduce **coordination cycles**?
- Does this capability enable **adaptive workflows**?
- Does this maintain **reviewable, PR-based delivery**?

If not, it's probably drift.
