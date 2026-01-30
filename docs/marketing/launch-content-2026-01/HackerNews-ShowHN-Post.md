# Hacker News Show HN Post: OmoiOS

## Title Options (pick one)

**Option A (Problem-focused):**
> Show HN: OmoiOS – I got tired of babysitting AI coding agents, so I built an orchestration layer

**Option B (Technical):**
> Show HN: OmoiOS – DAG-based orchestration for Claude Code agents with continuous spec validation

**Option C (Comparison hook — Ralph reference):**
> Show HN: OmoiOS – What happens when you add specs, DAGs, and a guardian to the Ralph loop

**Option D (Evolution narrative):**
> Show HN: OmoiOS – From `while true; do claude; done` to spec-driven parallel orchestration

---

## The Landscape: Where OmoiOS Fits

Before explaining OmoiOS, here's how the current AI coding tools stack up:

| Tool | What It Is | Approach |
|------|------------|----------|
| **Cursor** | AI-first IDE (VS Code fork) | You drive, AI assists. Real-time completions, in-editor diffs, up to 8 parallel agents |
| **Claude Code** | Anthropic's terminal-based agentic CLI | You describe a goal, it plans and executes across files. 200K context. |
| **Ralph/Ralphy** | Autonomous loop technique | `while true; do claude; done` — naive persistence until tests pass. PRD-driven. |
| **OmoiOS** | Spec-driven DAG orchestration | Parallel execution with continuous validation against specs. Catches drift before it compounds. |

**The evolution:**
- **Cursor/Copilot**: Human-in-the-loop, real-time assistance
- **Claude Code**: Agentic execution, but you still review output
- **Ralph**: Autonomous loops, but "no errors" = success (misses semantic drift)
- **OmoiOS**: Autonomous + spec-grounded + parallel + validated

---

## Post Body (Technical Version for HN)

### Option A: The "Ralph Evolution" Angle

If you've used Ralph (the `while true; do claude; done` technique), you know the power of naive persistence. Let the AI fail, loop, and eventually dream its way to a working solution.

I used Ralph extensively. It works. But I kept hitting the same wall:

**"No errors" ≠ "achieved the goal."**

The Ralph loop exits when tests pass and lints are clean. But what if the code is syntactically correct and completely misses the point? You only find out when you review the output — which defeats the purpose of autonomous execution.

So I built OmoiOS to add three things Ralph doesn't have:

**1. Specs as continuous ground truth**

Ralph uses PRDs and progress files, but validation is binary: tests pass or fail. OmoiOS treats specs as semantic validators. After every task, a "Guardian" LLM checks: "Did this move us toward the spec, or did the agent drift?" It catches the case where code works but doesn't do what you wanted.

**2. DAG-based parallelization**

Ralph runs sequentially — one loop iteration at a time. OmoiOS decomposes specs into a directed acyclic graph of atomic tasks. Independent tasks run in parallel across isolated sandboxes (Daytona). A feature that takes 3 hours in Ralph can finish in 45 minutes with proper parallelization.

**3. Dynamic discovery**

Ralph's task list is static (defined in the PRD). In OmoiOS, the DAG grows during execution. If an agent realizes "we need a migration before adding this column," it spawns a new task node, and the graph recomputes execution order automatically.

**Comparison:**

| | Cursor | Claude Code | Ralph/Ralphy | OmoiOS |
|---|---|---|---|---|
| **Mode** | Human drives | Goal-driven | Autonomous loop | Autonomous DAG |
| **Success metric** | Human judgment | Human review | Tests pass | Spec satisfaction |
| **Parallelization** | Up to 8 agents | Single agent | Single loop | Full DAG |
| **Drift detection** | Human | Human | None | Automated Guardian |
| **Context** | 70-120K effective | 200K | Fresh per loop | Fresh per task + spec |

**Stack:** FastAPI backend, PostgreSQL + pgvector, Redis + Taskiq for queueing, Claude Agent SDK for execution, Daytona for isolated sandboxes, Next.js frontend with React Flow for DAG visualization.

**Honest status:** It's early. The core orchestration loop works. There are bugs. The UI is functional but not beautiful. I'm probably a month of refinement away from something polished.

But the architecture is sound, and I've successfully used it to ship features I would have otherwise babysitted for hours.

Link: https://omoios.dev

Happy to answer questions about the architecture or share what didn't work along the way.

---

### Option B: More Technical Deep-Dive (For the "Show Me the Architecture" Crowd)

I've spent the last year in the autonomous coding space — started with Cursor for in-flow editing, moved to Claude Code for agentic execution, ran a lot of Ralph loops for autonomous persistence.

Each tool taught me something:
- **Cursor**: Great for flow state, but I'm still the bottleneck
- **Claude Code**: Powerful agentic execution, but I still review everything
- **Ralph**: Autonomous persistence works, but "tests pass" misses semantic correctness

OmoiOS is my attempt to synthesize what works and fix what doesn't.

**The core problem with Ralph-style loops:**

The Ralph pattern (`while true; do claude; done`) exits when backpressure clears — tests pass, lints clean, no errors. But what if the code works and completely misses the point?

Example: You want "users can reset passwords via email." Ralph produces a working password reset that... requires the user to be logged in first. Tests pass. Lint clean. Semantically wrong. You only catch this when you review — which means you're still babysitting.

**The architecture I landed on:**

1. **Spec-to-DAG transformation.** User input (natural language or structured specs) gets decomposed into a directed acyclic graph of atomic tasks. Each task has explicit inputs, outputs, and dependencies.

2. **Topological execution with parallelization.** Independent tasks run concurrently in isolated git workspaces (using Daytona). Dependencies block until upstream tasks complete. This gives meaningful speedups on features with parallelizable components.

3. **State validation loop.** After each task completion, the system runs a "guardian" check against the original spec. This catches semantic drift (correct code that misses the goal) before it compounds across dependent tasks.

4. **Discovery branching.** Tasks can spawn new tasks during execution. If an agent realizes "we need a migration before we can add this column," it creates a new task node, and the DAG recomputes execution order.

**Implementation details:**

- **Backend:** FastAPI + PostgreSQL (with pgvector for semantic search across specs/tasks) + Redis for pub/sub and task queuing (Taskiq)
- **Agent execution:** Claude Agent SDK running in Daytona sandboxes with 30-second heartbeats
- **Frontend:** Next.js 15 with React Flow for DAG visualization and xterm.js for live agent terminals
- **Workflow engine:** Custom state machine (EXPLORE → REQUIREMENTS → DESIGN → TASKS → SYNC) with phase-specific agent behaviors

**What I learned:**

1. Parallelization matters more than faster single-agent execution. A DAG that can run 4 independent tasks simultaneously beats a sequential agent that's 2x faster.

2. "No errors" is a terrible success metric. The guardian loop was the single biggest improvement to output quality.

3. Discovery is harder than it sounds. Agents spawning new tasks mid-execution creates race conditions and dependency cycles. Topological sort + cycle detection on every DAG mutation solved this.

4. Spec quality → output quality. The system is only as good as the spec it's grounded against. Garbage in, garbage out.

**Current state:** Core loop works. 57 database models, 80+ services, 277 tests. Still rough around the edges—I'd estimate a month more refinement before it feels polished.

Link: https://omoios.dev

I'm sharing because I think the spec-grounded DAG approach is underexplored in the agent space, and I'd be curious if others have tried similar architectures.

---

## Tips for HN Posting

1. **Post timing:** Weekday mornings (US time) tend to perform better. Tuesday-Thursday, 8-10am PT.

2. **Engage quickly:** Respond to every comment in the first hour. HN rewards active OPs.

3. **Be honest about limitations:** HN respects candor. "It's early, there are bugs" beats "revolutionary game-changer."

4. **Technical depth in comments:** Keep the post digestible; go deep in comment replies.

5. **Don't self-promote too hard:** Focus on the problem and architecture, not the product. Let people discover the link.

---

## Comment Replies to Prepare

**"How is this different from CrewAI/AutoGen?"**

> CrewAI and AutoGen are multi-agent frameworks focused on agent collaboration—agents talking to each other to reach consensus. OmoiOS is different in two ways: (1) the success metric is spec satisfaction, not agent consensus, and (2) execution is DAG-parallelized with continuous validation against the spec. The agents don't negotiate; they execute atomic tasks and get checked against ground truth after each one.

**"Why Claude specifically?"**

> Claude Agent SDK gives me the best developer experience for tool-using agents right now. The architecture isn't Claude-specific though—you could swap in any capable coding model. I just happened to build on Claude because the SDK made sandboxed execution straightforward.

**"What about hallucinations / incorrect code?"**

> That's exactly what the guardian loop is for. After every task, another LLM checks "did this actually move us toward the spec?" It catches semantic errors (correct syntax, wrong behavior) before they propagate. It doesn't eliminate errors, but it catches them earlier.

**"Isn't this just fancy CI/CD?"**

> Sort of, but the key difference is the agents write the code, not just run it. Think of it as spec-driven code generation with continuous integration built into the generation loop. The DAG isn't a pipeline of predefined steps—it's dynamically constructed from the spec.

**"Why not just use Cursor / Copilot?"**

> Cursor and Copilot are excellent for in-the-moment coding assistance. OmoiOS is for when you want to describe a feature, walk away, and come back to a PR. Different use cases. I use Cursor when I'm actively coding; I use OmoiOS when I want to batch delegate.

**"How is this different from Ralph/Ralphy?"**

> Ralph is brilliant for its simplicity — naive persistence until tests pass. OmoiOS builds on that foundation but adds three things: (1) semantic validation against specs (not just "tests pass"), (2) DAG parallelization (run independent tasks concurrently), and (3) dynamic task discovery (the graph grows during execution). Think of it as Ralph + specs + parallelization + a guardian that catches semantic drift.

**"What about the token costs?"**

> Similar to Ralph loops — autonomous execution consumes tokens. A complex feature might cost $10-50 in API credits. The tradeoff is wall-clock time and human attention. If you value your time at >$50/hour, the economics work out when the alternative is babysitting agents for 3 hours.

**"Why build this instead of using CrewAI/AutoGen/LangGraph?"**

> Those are multi-agent frameworks focused on agent collaboration — agents negotiating with each other. OmoiOS is different: agents don't negotiate, they execute atomic tasks and get validated against specs. The success metric isn't "agents agreed" but "spec satisfied." Also, full DAG parallelization is a first-class primitive here, not an afterthought.
