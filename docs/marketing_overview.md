# OmoiOS Marketing Overview

**Created**: 2025-12-15  
**Status**: Draft  
**Purpose**: Clear buyer-facing positioning, messaging, and focus for OmoiOS.

---

## Product in one sentence

**OmoiOS is an autonomous engineering execution dashboard that turns feature requests into reviewed pull requests using spec-driven, multi-agent workflows—with real-time visibility, discovery-based branching, and steering.**

## Product concept (30 seconds)

Connect a GitHub repo, write a feature request, and OmoiOS produces an executable workflow: **Requirements → Design → Tasks → Execution**. Multiple agents work in parallel in isolated workspaces/branches, run tests/validation loops, and open PRs. When agents discover missing requirements, bugs, integration issues, or optimizations, OmoiOS **spawns and links new work** (tickets/tasks) in the right phase instead of stalling. Humans stay in control at the right moments via **phase gates** and **PR review**.

---

## The core narrative to sell

### 1) Automated workflows (structured autonomy)
- **Input**: feature request + repo context
- **Process**: spec-driven phases with done definitions and expected outputs
- **Output**: tasks, execution, artifacts, and PRs

### 2) Task/ticket discovery (work adapts to reality)
- Agents **record discoveries** (bug, optimization, clarification needed, integration issue, technical debt, security/perf issue)
- Discoveries **spawn new tasks in any phase**, linked back to the source, so workflows can branch instead of breaking

### 3) Steering (self-healing execution)
- Monitoring detects stuck/drifting/idle behavior and triggers interventions (diagnose, reallocate, override priority, cancel)
- Goal: **users intervene at decision points**, not as babysitters

---

## What buyers are buying (benefits)

- **More shipped output without proportional headcount growth**: parallel agent execution extends team throughput.
- **Less coordination tax**: fewer status updates/meetings and less hand-holding of step-by-step work.
- **Workflows that don’t snap when reality changes**: discovery branching handles surprises without derailing delivery.
- **Higher trust vs “chat-to-code”**: phase gates, validation loops, and a reasoning trail make delegation safer.
- **Visibility and control**: real-time board/graph/activity timeline + explicit approval points.

---

## Key features → buyer-visible outcomes

- **Spec workspace (Requirements/Design/Tasks/Execution)** → “Intent becomes an executable plan you can approve.”
- **Adaptive phase-based workflows** → “The system can jump phases or branch when new info appears.”
- **Kanban board + dependency graph (real time)** → “You always know what’s blocked and why.”
- **Multi-agent parallel work with workspace/branch isolation** → “Multiple workstreams move at once without conflicts.”
- **Phase gates + quality validation** → “Quality is enforced before progressing; no silent skipping.”
- **Diagnostic reasoning trail** → “Transparent ‘why’ behind spawned work, transitions, and interventions.”
- **Git integration (commits/PRs linked to tickets)** → “Fits existing dev workflow; reviewable outputs.”
- **Monitoring/Guardian interventions** → “Self-healing: detects drift/stuck loops and corrects course.”
- **Cost/budget tracking** → “Operational control: spend visibility and constraints by org/project.”

---

## Ideal customer profile (focus)

### Primary ICP (strongest fit)
- **CTOs / Engineering Managers** at **mid-size SaaS (10–100 engineers)**
- GitHub-first teams already using tickets/boards
- Pain: coordination overhead, hiring pressure, backlog growth, and inconsistent execution

### Secondary ICP (fastest early adoption)
- **Senior IC-led teams / small startups (2–10 people)** who want to ship faster with fewer interrupts

### Not a fit (for now)
- Teams wanting “fully autonomous merges to production” with no approvals
- Teams without mature Git/code review culture
- Highly regulated environments unless they accept a gated approval model

---

## Positioning: what category are you in?

**Autonomous engineering execution + workflow orchestration** (not a code assistant, not a generic agent runner).

- Compared to “AI coding assistants”: OmoiOS is **system-level execution + coordination**, not per-developer autocomplete.
- Compared to “ticketing tools”: OmoiOS doesn’t just track work—it **creates and executes work**.
- Compared to “agent frameworks”: OmoiOS adds **productized oversight** (board, gates, diagnostics, monitoring).

---

## Messaging you can reuse

### One-liners
- “Turn feature requests into reviewed PRs with autonomous, spec-driven workflows.”
- “Ship more with the team you have—without babysitting agents.”
- “Adaptive workflows: when reality changes, the plan branches instead of breaking.”

### 30-second pitch
“Connect your repo, describe a feature, and OmoiOS generates a requirements/design/task plan, then runs parallel agents to implement and test in isolated branches. If agents discover missing requirements, bugs, or optimizations, OmoiOS automatically spawns and links the right follow-up work. You stay in control at phase gates and PR review—with full real-time visibility into progress and blockers.”

### 2-minute demo script (talk track)
1. “Here’s a feature request.”
2. “OmoiOS turns it into a spec: requirements, design, tasks.”
3. “Now execution starts: multiple agents pick up unblocked tasks.”
4. “Watch: tickets move across phases; dependencies unblock automatically.”
5. “A discovery happens—OmoiOS spawns a new task and links the reasoning.”
6. “Phase gate triggers: artifacts/tests are checked; I approve.”
7. “A PR is opened; I review like normal.”

---

## Common objections (and clean answers)

- **“Why not just use ChatGPT/Copilot?”**
  - Those help individuals write code. OmoiOS is about **execution at the system level**: planning, parallelization, tracking, validation loops, approvals, and keeping workflows unstuck.

- **“Can I trust it?”**
  - It’s designed for **reviewable outputs**: gated transitions, test/validation phases, linked reasoning, and PR-based delivery.

- **“Will it create chaos in my repo?”**
  - Work happens in **isolated workspaces/branches** with ticket/commit traceability. Humans still approve merges.

- **“What if requirements are unclear?”**
  - The system can **branch back to requirements** (clarification-needed) and block dependent work rather than guessing.

---

## Landing page copy (draft)

### Hero
**Autonomous Engineering Execution.**  
Turn feature requests into reviewed PRs with spec-driven, multi-agent workflows.

**CTA**: Connect your repo · Create your first spec · Watch execution in real time

### Why OmoiOS
- **Spec-driven**: Requirements → Design → Tasks → Execution
- **Adaptive**: discovery-based branching when reality changes
- **Visible**: real-time Kanban, dependency graph, activity timeline
- **Controlled**: phase gates and PR reviews at strategic points

### How it works
1. Connect GitHub
2. Describe a feature
3. Approve the plan
4. Agents implement + validate
5. Review PRs and merge

---

## The focus statement (so you don’t drift)

**OmoiOS is for teams who want autonomous execution with oversight: fewer coordination cycles, adaptive workflows via discovery, and reviewable PR-based delivery.**
