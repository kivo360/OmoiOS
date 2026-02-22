# OmoiOS Website Copy — Final Draft

> Last updated: 2026-02-22
>
> This is the finalized section-by-section copy for omoios.dev.
> Decisions are locked in. Implementation notes are inline.

---

## Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Comparison table layout | **Hybrid** — Option B (4-col) on homepage, Option A (6-col) on `/compare` page | Homepage stays clean; `/compare` captures long-tail SEO |
| Hero one-liner | **"Open-source spec-to-PR. No IDE. No vendor lock."** | Competitor-agnostic, hits all 4 differentiators |
| Kiro positioning | Keep "open-source alternative to Kiro" for **meta tags + OpenAlternative listing only** | SEO value for "Kiro alternative" searches |
| Pain/solution cards | 4 cards (down from 8) | Each card now has a clear pain + specific OmoiOS solution |
| Agent feature cards | 4 cards (down from 6) | Removed overlap; self-correction was mentioned 3x before |
| Free tier workflows | 10/month (up from 5) | 5 is too tight for tire-kicking |
| Copilot in comparison | **Dropped** — replaced with Claude Code + Codex | Nobody on HN compares against Copilot anymore |
| Founder story section | **Added** | Critical for HN credibility and developer trust |
| Metric counters | **Fix or replace with static** | Currently show 0x, 0%, 0/7, 0 — looks broken |

---

## Nav Bar

```
OmoiOS | Why | Features | How It Works | Pricing | Compare | GitHub [star count]
```

- Added "Compare" link for the new `/compare` page
- GitHub link shows live star count via shields.io badge

---

## Hero Section

### Badge (above headline)

`Open Source · Spec-Driven · Autonomous`

### Headline

**Open-source spec-to-PR. No IDE. No vendor lock.**

### Subhead

Describe what you want built. OmoiOS turns it into requirements, a design, and an implementation plan — then agents execute autonomously in the cloud and deliver a pull request by morning. No IDE required.

### CTAs

- **Primary:** Get Started Free
- **Secondary:** Star on GitHub | Watch Demo

### Social Proof Strip (below CTAs)

`[star count] on GitHub · Listed on OpenAlternative · Built by a solo founder, open to everyone`

---

## "Why OmoiOS" Section

### Section Header

**AI coding tools still need you at the keyboard. OmoiOS doesn't.**

### Section Subhead

Kiro, Cursor, and Copilot help you code faster — but you're still the one coding. OmoiOS runs the full pipeline in the background so your team reviews pull requests, not prompts.

### Pain/Solution Cards (4 cards)

**Card 1: Your roadmap moves faster than your hiring**
Recruiting takes months. Your backlog grows daily. OmoiOS lets you add agent capacity tonight and wake up to shipped work tomorrow — no headcount required.

**Card 2: AI-generated code looks right until you run it**
Plausible code that breaks at build time wastes senior time. OmoiOS agents run tests, catch failures, and self-correct before you ever see the PR.

**Card 3: Plans drift. Context disappears. Reviews slow down.**
Decisions get scattered across Slack, docs, and tickets. OmoiOS traces every line of code back to the original spec — requirements, design, and implementation stay connected.

**Card 4: More contributors should mean more throughput, not more conflicts**
OmoiOS agents work in isolated sandboxes with dependency-aware sequencing. Parallel execution without merge chaos.

---

## Comparison Table — Homepage (Option B: 4 columns)

### Section Header

**How OmoiOS compares**

| | **OmoiOS** | **Kiro** (AWS) | **OpenAI Codex** | **Claude Code** |
|---|---|---|---|---|
| **Open source** | Yes | No | No | Yes |
| **Where it runs** | Cloud (autonomous) | Your IDE | Cloud + local | Your terminal |
| **Spec-to-code pipeline** | Full pipeline | Specs + hooks | Prompt-driven | Prompt-driven |
| **Multi-agent orchestration** | Parallel agents | Single agent | Parallel tasks | Subagents |
| **Self-hostable** | Yes | No | No | No |
| **BYOK (model provider)** | Anthropic, OpenAI | Claude only | GPT only | Claude only |

**Subheader copy:** *Kiro plans your code. Codex runs tasks. OmoiOS ships features — from spec to PR, overnight.*

---

## Comparison Table — `/compare` Page (Option A: 6 columns)

### Page Header

**How OmoiOS compares**

| | **OmoiOS** | **Kiro** (AWS) | **OpenAI Codex** | **Claude Code** | **OpenCode** (sst) | **Cursor** |
|---|---|---|---|---|---|---|
| **Open source** | Yes | No | No | Yes | Yes (MIT) | No |
| **Where it runs** | Cloud (autonomous) | Your IDE | Cloud + local CLI | Your terminal | Your terminal | Your IDE |
| **You need to be** | Asleep | At your desk | At your desk* | At your desk | At your desk | At your desk |
| **Spec-to-code pipeline** | Full pipeline | Specs + hooks | Prompt-driven | Prompt-driven | Prompt-driven | Prompt-driven |
| **Multi-agent orchestration** | Parallel agents | Single agent | Parallel tasks | Subagents | Multi-session | Single agent |
| **Output** | PR ready to merge | Code in editor | PR via GitHub | Code changes locally | Code changes locally | Code in editor |
| **Self-healing execution** | Retries + auto-fix | Manual | Runs tests to pass | Manual | Manual | Manual |
| **Self-hostable** | Yes | No | No | No | Local only | No |
| **BYOK (model provider)** | Anthropic, OpenAI | Claude only | GPT only | Claude only | 75+ providers | Multiple |
| **Pricing** | Free–$150/mo | Free (preview) | ChatGPT Plus+ | Pro/Max/API | Free (BYOK) | $20/mo+ |

\* *Codex cloud tasks run async, but still prompt-driven — no spec-to-code pipeline. You assign individual tasks, not a full feature spec.*

### Per-Competitor Sections (for `/compare` page body)

**How is OmoiOS different from Kiro?**
Kiro is a spec-driven IDE from AWS — it helps you plan and code interactively at your desk. OmoiOS is a spec-driven orchestration platform that runs autonomously in the cloud. You write the spec, approve the plan, and agents execute the full pipeline — delivering a PR while you focus on other work (or sleep). OmoiOS is also open-source and self-hostable, while Kiro is closed-source.

**How is OmoiOS different from OpenAI Codex?**
Codex is a cloud-based coding agent from OpenAI — you assign individual tasks via prompts, and it works in a sandbox to deliver code changes or PRs. OmoiOS is a spec-driven orchestration platform — you write a feature specification, agents generate requirements, design, and implementation plans, then execute the full pipeline autonomously. OmoiOS is also open-source, self-hostable, and supports multiple model providers (Anthropic + OpenAI), while Codex is closed-source, runs only on OpenAI's infrastructure, and uses GPT models exclusively.

**How is OmoiOS different from Claude Code?**
Claude Code is a powerful local coding agent that runs in your terminal alongside your IDE. It's excellent for interactive development — exploring codebases, debugging, and making changes with you in the loop. OmoiOS is designed for a different workflow: you define a spec, approve a plan, and agents execute the full pipeline in the cloud while you're away. Think of Claude Code as your pair programmer, and OmoiOS as your overnight engineering team.

**How is OmoiOS different from OpenCode?**
OpenCode (sst/opencode) is a great open-source CLI tool for interactive AI-assisted coding with support for 75+ model providers. Like Claude Code, it's a local tool that requires your presence. OmoiOS takes a different approach: cloud-based autonomous execution driven by specs, not prompts. Both are open source, but OmoiOS is infrastructure you deploy, not software you install.

**How is OmoiOS different from Cursor?**
Cursor is an AI-powered code editor that helps you write code faster with inline suggestions and chat. It's a productivity multiplier when you're at your desk. OmoiOS operates at a different layer — you're not writing code at all. You write a spec, agents plan and execute autonomously, and you review the PR when it's ready. Cursor makes you faster; OmoiOS works without you.

---

## "How It Works" Section

### Section Header

**You Sleep. Agents Ship.**

### Section Subhead

Write a spec, approve the plan, close your laptop. Agents execute in an orchestrated pipeline — with guardrails, tests, and retries — so you wake up to a PR you can trust.

### Step 1: You Write a Spec

Describe the feature in plain English. Add constraints — tech stack, architecture rules, coding standards. Your spec becomes the agent's contract. Write it in the browser, CLI, or API — no IDE required.

*Tag: Spec-driven constraints*

### Step 2: We Plan the Work

Your spec becomes an ordered plan with clear dependencies and a schedule. You see what will be built, in what order, and why. Approve or adjust before any code is written.

*Tag: Plan & dependencies*

### Step 3: Agents Execute Autonomously

Agents work in isolated sandboxes — writing code, running tests, fixing issues. If tests fail, agents debug and retry automatically. No Slack message, no escalation, no 3am page. They keep going until the plan is complete.

*Tag: Self-healing execution*

### Step 4: Wake Up to a PR

Morning: a pull request with working, tested code. Every change traced back to your spec. Review it, merge it, ship it.

*Tag: Ready when you are*

---

## "Agent Architecture" Section

### Section Header

**Orchestrated execution, not prompt-and-pray**

### Feature Cards (4 cards)

**1. Spec-driven guardrails**
Your spec is the contract. Agents can't go off-script. Requirements, constraints, and acceptance criteria are enforced at every step.

**2. Self-healing pipeline**
When tests fail or builds break, agents diagnose, fix, and retry automatically. You only hear about success.

**3. Full traceability**
Every decision, test result, and code change is linked back to the original requirement. Review with confidence because you can see *why* every line exists.

**4. Parallel orchestration**
Multiple agents, multiple tasks, dependency-aware sequencing. Scale throughput by adding agents — not meetings.

---

## "Why I Built This" Section

### Section Header

**Built by a developer who got tired of babysitting AI**

### Copy

I'm Kevin, a full-stack developer building OmoiOS as a solo founder. I've shipped production code in Python, Rust, TypeScript, and Dart — and I've used every AI coding tool out there.

Here's what I kept running into: tools like Kiro and Cursor are great when you're at your desk. But I wanted something that could take a spec, execute a plan, and deliver a PR while I was asleep, at the gym, or working on something else entirely.

So I built OmoiOS — an autonomous agent orchestration platform that treats specs as contracts and delivers tested code without requiring you at the keyboard.

I open-sourced it because I think this should be infrastructure, not a walled garden. Fork it, self-host it, build on top of it.

---

## Metrics Section

### Static values (recommended — current animated counters are broken)

- **10x** — idea to PR in hours, not weeks
- **80%** — less coordination overhead
- **24/7** — agents work while you don't
- **0** — babysitting required

> Implementation note: If animated counters are restored, test on multiple browsers and with JS disabled. Fallback of "0" is worse than no section.

---

## Pricing Section

### Starter — $0/month

- 1 concurrent agent
- 10 workflows per month
- 2 GB storage
- Community support

**CTA:** Start Free

### Pro — $50/month (Most Popular)

- 5 concurrent agents
- 100 workflows per month
- 50 GB storage
- Bring your own API keys (Anthropic, OpenAI)
- Priority support
- Advanced analytics

**CTA:** Get Pro

### Team — $150/month

- 10 concurrent agents
- 500 workflows per month
- 500 GB storage
- Bring your own API keys
- Team collaboration & role-based access
- Dedicated support
- Custom integrations

**CTA:** Get Team

### Enterprise — Custom

- Unlimited agents
- Self-hosted deployment
- Custom SLAs
- Dedicated support
- SSO & compliance

**CTA:** Talk to Sales

---

## FAQ Section

**How is OmoiOS different from Kiro?**
Kiro is a spec-driven IDE from AWS — it helps you plan and code interactively at your desk. OmoiOS is a spec-driven orchestration platform that runs autonomously in the cloud. You write the spec, approve the plan, and agents execute the full pipeline — delivering a PR while you focus on other work (or sleep). OmoiOS is also open-source and self-hostable, while Kiro is closed-source.

**How is OmoiOS different from OpenAI Codex?**
Codex is a cloud-based coding agent from OpenAI — you assign individual tasks via prompts, and it works in a sandbox to deliver code changes or PRs. OmoiOS is a spec-driven orchestration platform — you write a feature specification, agents generate requirements, design, and implementation plans, then execute the full pipeline autonomously. OmoiOS is also open-source, self-hostable, and supports multiple model providers (Anthropic + OpenAI), while Codex is closed-source, runs only on OpenAI's infrastructure, and uses GPT models exclusively.

**How is OmoiOS different from Cursor or Copilot?**
Cursor and Copilot are code assistants that help you write code faster inside your editor. OmoiOS is an autonomous execution platform — it doesn't help you code, it codes for you based on your spec. Different tool for a different workflow.

**How is OmoiOS different from Claude Code?**
Claude Code is a powerful local coding agent that runs in your terminal alongside your IDE. It's excellent for interactive development — exploring codebases, debugging, and making changes with you in the loop. OmoiOS is designed for a different workflow: you define a spec, approve a plan, and agents execute the full pipeline in the cloud while you're away. Think of Claude Code as your pair programmer, and OmoiOS as your overnight engineering team.

**How is OmoiOS different from OpenCode?**
OpenCode (sst/opencode) is a great open-source CLI tool for interactive AI-assisted coding with support for 75+ model providers. Like Claude Code, it's a local tool that requires your presence. OmoiOS takes a different approach: cloud-based autonomous execution driven by specs, not prompts. Both are open source, but OmoiOS is infrastructure you deploy, not software you install.

**Can I self-host OmoiOS?**
Yes. OmoiOS is open-source and can be deployed on your own infrastructure. The Enterprise plan includes dedicated support for self-hosted deployments.

**What models does OmoiOS support?**
OmoiOS works with Anthropic (Claude) and OpenAI models. On Pro and above, you can bring your own API keys to use your preferred provider.

**Is my code safe?**
Your code runs in isolated sandboxes. On the self-hosted plan, everything stays on your infrastructure. OmoiOS never trains on your code.

---

## Footer

- Link to GitHub repo
- Link to OpenAlternative listing
- Link to changelog/roadmap (GitHub Releases or Discussions)
- "Open Source" + license badge

---

## SEO & Meta Tags

**Title tag:** OmoiOS — Open-Source Spec-Driven AI Development Platform | Kiro Alternative

**Meta description:** The open-source alternative to Kiro. Describe features, approve a plan, and wake up to pull requests. Autonomous agent orchestration with specs, tests, and traceability. Free tier available.

**OG Title:** OmoiOS — Spec-driven development that ships while you sleep

**OG Description:** Open-source autonomous agent orchestration. Write a spec, agents deliver a tested PR by morning. The open-source Kiro alternative.

---

## OmoiOS Unique Position (No Other Tool Has All 5)

The combination that **only OmoiOS** offers:

1. Open source
2. Cloud autonomous execution
3. Spec-driven pipeline (not just prompts)
4. Self-hostable
5. Multi-model BYOK

| Competitor | Missing |
|------------|---------|
| **Codex** | Spec-driven, open source, self-host, BYOK |
| **Kiro** | Cloud autonomous, open source, self-host |
| **Claude Code** | Cloud autonomous, spec-driven, self-host |
| **OpenCode** | Cloud autonomous, spec-driven |
| **Cursor** | Cloud autonomous, spec-driven, open source, self-host |

---

## Implementation Priority

| Change | Impact | Effort |
|---|---|---|
| Update hero to new one-liner + badge | High | Low |
| Fix broken metric counters (0x, 0%) | High | Low |
| Add 4-column comparison table to homepage | High | Medium |
| Create `/compare` page with 6-column table | High | Medium |
| Add "Why I Built This" founder section | Medium | Low |
| Consolidate pain/solution cards (8 to 4) | Medium | Low |
| Consolidate agent feature cards (6 to 4) | Medium | Low |
| Update FAQ with new entries | Medium | Low |
| Bump free tier to 10 workflows | Medium | Low |
| Update SEO meta tags | Medium | Low |
| Add GitHub stars badge in hero | Medium | Low |
| Add footer links (changelog, license, OpenAlternative) | Low | Low |
