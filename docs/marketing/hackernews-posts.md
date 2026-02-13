# Hacker News Posts for OmoiOS

**One-liner:** *"Define the spec. Agents build in sandboxes. The system verifies. You review the PR."*

*HN is technical, skeptical, and hates marketing speak. Be honest, be technical, invite criticism.*

---

## Post 1: Show HN Launch Post

**Title:** Show HN: OmoiOS – DAG-based orchestration for Claude Code agents

**Body:**

Hey HN,

I built OmoiOS to solve a problem I kept hitting with AI coding tools: I was spending more time babysitting them than I would have spent writing the code myself.

The core idea: run Claude Code agents in sandboxes, but orchestrate them with a DAG that continuously checks state against a spec.

**How it works:**

1. You write a spec (or describe an idea loosely — the system helps structure it)
2. OmoiOS breaks the spec into tickets and atomic tasks with dependencies
3. Tasks get organized into a DAG — independent tasks can run in parallel
4. Claude Code agents execute tasks in isolated sandboxes
5. After each task: state is checked against the spec. Did this actually move us closer to the goal?
6. If drift is detected: retry, adapt, or spawn new tasks
7. Loop until spec is satisfied, not just until no errors

**Why this matters:**

Simple continuous agents just loop: `while not done: do_thing()`. But "done" is poorly defined. The agent doesn't know if it achieved the goal — it just knows if it stopped erroring.

OmoiOS gives the loop a brain. It knows what "done" looks like because it has a spec to check against.

**Tech stack:**

- Backend: Python/FastAPI
- Agents: Claude Code (Anthropic's agent SDK) running in sandboxes
- Execution: DAG-based task queue with dependency resolution
- State checking: Continuous comparison against structured spec

**Current state:**

Early. Still iterating. But the core loop works. I've shipped features overnight that would have taken days of back-and-forth with traditional prompting.

Looking for feedback, especially from people who've tried to make autonomous coding agents reliable.

---

## Post 2: Technical Discussion Post

**Title:** Ask HN: Has anyone solved the "babysitting problem" with AI coding agents?

**Body:**

I've been using AI coding tools for a while — Copilot, Cursor, Claude directly, etc. They're good at generating code, but I keep running into the same issue:

I end up babysitting.

The AI works, but I'm constantly checking in. Is it on track? Did it drift? Is it stuck? Should I re-prompt? I'm the oversight layer, and that oversight takes more time than I expected.

Continuous agents help — just "loop until done." But they don't actually know what "done" means. They loop until they stop erroring, which isn't the same thing.

I've been working on a different approach:

1. Start with a structured spec (source of truth)
2. Break spec into tasks with dependencies (DAG)
3. Run Claude Code agents in sandboxes on each task
4. After each task, check state against spec
5. If drifting, adapt. If stuck, retry or spawn new tasks.
6. Loop until spec is satisfied.

The key difference: the system does the babysitting. It watches the agents, checks progress, catches drift.

Has anyone else tried something similar? What's worked? What's failed?

Curious if there's prior art I'm missing or if this is a known-hard problem.

---

## Post 3: Architecture Deep-Dive Post

**Title:** DAG-based execution for LLM agents: lessons learned

**Body:**

I've been building a system that orchestrates Claude Code agents using a DAG (directed acyclic graph) for task dependencies. Wanted to share some lessons learned.

**The problem with sequential agent execution:**

```
while not done:
    result = agent.run(next_task)
    if result.failed:
        retry()
```

This works for simple cases, but:
- No parallelization
- "done" is poorly defined
- No way to handle discovered dependencies
- Agent drift accumulates

**DAG-based approach:**

1. Decompose spec into tasks with explicit dependencies
2. Topologically sort to find execution order
3. Run independent tasks in parallel (separate sandboxes)
4. After each task: validate state against spec
5. If new dependencies discovered: add to DAG, re-sort
6. Continue until all leaf nodes complete AND spec is satisfied

**What worked:**

- Claude Code in sandboxes is surprisingly reliable for atomic tasks
- Parallel execution dramatically reduces wall-clock time
- State checking catches drift before it compounds
- DAG makes it easy to visualize what's happening

**What's hard:**

- Spec decomposition is the bottleneck. Garbage spec = garbage DAG.
- State checking requires knowing what "good state" looks like. This is domain-specific.
- Recovery from failed tasks is tricky. Sometimes retry works, sometimes you need to backtrack.
- The DAG can grow unexpectedly when agents discover missing requirements.

**Open questions:**

- How do you define "spec satisfied" in a way that's checkable?
- What's the right granularity for tasks? Too big = agent drift. Too small = overhead.
- How do you handle tasks that modify shared state?

Would love to hear from others who've tried orchestrating LLM agents at this level.

---

## Post 4: Failure/Learning Post (RECOMMENDED LEAD POST)

**Title:** Show HN: OmoiOS – I failed 4 times making AI agents reliable, then automated the oversight

**Alt titles:**
- "What I learned failing to make AI coding agents reliable"
- "Show HN: OmoiOS – Spec-driven agent swarms that verify their own work"

**Body:**

I've spent months trying to make AI coding agents actually useful for autonomous work. Here's what failed and what finally worked.

**Attempt 1: Just use Claude/GPT directly**

```
you: "Build me a user settings page"
claude: [generates code]
you: "Wait, it forgot the auth middleware..."
you: "Actually, the DB schema is wrong too..."
you: [re-explains context for the 4th time]
```

Works for small stuff. For anything complex, you're constantly re-explaining context. The AI forgets, drifts, makes inconsistent decisions.

**Attempt 2: Copilot/Cursor**

Great for autocomplete. Still doing 95% of the thinking myself. Not autonomous.

**Attempt 3: Continuous agents**

```python
while not done:
    result = agent.do_next_thing()
    if not result.errors:
        done = True  # but... did it actually work?
```

Better — the agent keeps working without prompting. But "done" is undefined. `not result.errors` doesn't mean the feature works. It means the agent stopped crashing. You end up checking in constantly to see if it's on track.

**Attempt 4: Parallel agents (subagents, multi-agent)**

```python
tasks = split_work(feature)
results = await asyncio.gather(*[
    agent.run(task) for task in tasks
])
# results are in... but did they actually satisfy the goal?
# who checks? you do. manually. for each one.
```

Faster wall-clock time. But the core problem doesn't change — nobody is verifying whether the output actually satisfies the goal. You still end up reviewing everything manually, except now there's more of it.

**What finally worked: automated oversight**

The problem was never the AI. The AI generates decent code. The problem was me — I was the oversight layer. The one checking progress, catching drift, deciding if it's done. That's the job I needed to automate.

So I built OmoiOS. Here's what it actually does:

**1. Structured spec pipeline — not just a prompt.**

You describe a feature loosely. The system walks it through a 7-phase pipeline:

```
EXPLORE → PRD → REQUIREMENTS → DESIGN → TASKS → SYNC → COMPLETE
  │         │         │            │        │
  └── LLM evaluator at each gate ──┘        │
      score < threshold? retry phase         │
      score >= threshold? advance ───────────┘
```

Each phase has an LLM evaluator that scores the output and retries on failure — a quality gate before moving forward. By the time agents start coding, the spec has structured requirements with acceptance criteria that are machine-checkable.

This matters because it gives the system a real definition of "done." Not "did it compile" — "did it satisfy the requirement, as defined by the acceptance criteria the planning phase produced?"

**2. Sandboxed execution — you keep coding.**

```
Your machine                    Daytona Cloud
┌──────────────┐    ┌─────────────────────────────────┐
│ your editor  │    │ Sandbox A: auth-service (impl)  │
│ your branch  │    │ Sandbox B: api-tests (validate) │
│ your work    │    │ Sandbox C: db-migration (impl)  │
│   ...        │    │   ...each ephemeral, isolated   │
└──────────────┘    └──────────┬──────────────────────┘
                               │ done
                               ▼
                          Pull Request
```

Each task spawns an isolated cloud sandbox (Daytona). Agents work in their own ephemeral containers with full filesystem and git access. Your local dev environment is completely untouched.

This is the part I personally care about most: while agents are executing in their sandboxes, I'm still coding in my own editor on my own branch. I'm not waiting. I'm not locked out. When agents are done, I get a PR — not a diff dumped into my working tree. Three execution modes: exploration (read-only analysis), implementation (full access), and validation (test execution only).

**3. Continuous verification, not just completion.**

```python
# this is roughly what happens after each task completes
for task in completed_tasks:
    # separate validator agent, separate sandbox
    result = validator.check(
        implementation=task.output,
        criteria=spec.acceptance_criteria[task.requirement_id]
    )
    if result.passed:
        merge(task.branch)
    else:
        # feed failure reason back — agent retries with context
        task.retry(feedback=result.reason)

    # agents can discover new work mid-execution
    if result.discoveries:
        for discovery in result.discoveries:
            dag.add_task(discovery)  # graph grows dynamically
```

After each task, a separate validator agent runs in its own sandbox and checks the implementation against the spec's acceptance criteria. Did this actually satisfy the requirement? If validation fails, the failure reason and context get fed back to the implementation agent for retry. No human in the loop.

Tasks are organized as a dependency graph — independent work runs in parallel, dependent work waits. But here's the part that surprised me: the graph isn't static. Agents discover new requirements during execution. A validation agent finding a missing edge case can spawn new investigation tasks. The system calls this "discovery branching" — the work adapts as agents learn more about the problem.

**4. Monitoring and coordination (partially shipped, partially WIP).**

```
Shipped:
  Validator ──► per-task acceptance criteria checking
  │             pass → merge branch
  │             fail → retry with feedback context
  │
  Merge ──► parallel branches finish:
            conflict_score = dry_run_merge_tree(branches)
            if conflicts: resolve_with_llm(conflicts)

Work in progress:
  Guardian ──► per-agent trajectory analysis (60s cycles)
  Conductor ──► system-wide duplicate detection + coherence
```

The validation loop is shipped and working — separate validator agents check each task against acceptance criteria, and failures trigger retries with context. The merge system handles parallel branch conflicts with dry-run scoring and LLM-powered resolution.

The Guardian (per-agent trajectory monitoring) and Conductor (system-wide coherence) are architecturally complete but currently disabled — ran into duplication issues in the monitoring loop that need to be resolved. The pieces exist, the wiring needs work. Mentioning it because the architecture is designed for it, not because it's running in production today.

Agents learn from execution history via a memory service with hybrid search (semantic + keyword), so the system improves on similar tasks over time.

**5. The insight.**

None of this is about running agents faster. It's about automating the oversight loop. If the system has a checkable definition of "done" and can verify progress autonomously, you stop being the bottleneck. You review specs and PRs. The system handles everything in between.

**Tech stack:**

- Python/FastAPI, PostgreSQL + pgvector, Redis
- Claude Agent SDK for agent execution
- Daytona Cloud for isolated sandboxes (ephemeral containers per task)
- LLM-powered spec validation (structured output with acceptance criteria)
- Next.js 15 dashboard — Kanban boards, dependency graphs, real-time agent monitoring
- ~60 database models, 71 migrations, ~30 API route files

**What's hard:**

- Spec quality is the bottleneck. Vague spec = vague validation = agents spinning. The 7-phase pipeline helps, but garbage in still equals garbage out.
- Validation is domain-specific. "Does this API endpoint return the right data?" is easy to verify. "Is this UI intuitive?" is not.
- Discovery branching can cause the task graph to grow unexpectedly. Need better heuristics for when to stop spawning.
- Sandbox overhead isn't free. Spinning up Daytona containers adds latency per task. Worth it for isolation, but it's a tradeoff.
- Merging parallel branches with real conflicts is still the hardest coordination problem.

**How this compares to tools you're probably already using:**

- **Claude Code / Cursor agent mode** — Great for single-task execution. You give it a task, it works, you review. But you're still the one deciding what to work on next, checking if the output matches your goal, and coordinating when multiple things need to happen. OmoiOS is the layer above — it breaks a spec into tasks, dispatches them, and verifies the results so you don't have to be in the loop between each step.

- **OpenHands / OpenCode** — Similar story. Strong autonomous agents, but one-task-at-a-time with you as the orchestrator. OmoiOS can run these agents inside sandboxes and handle the planning, verification, and coordination around them.

- **Devin** — Closest comparison. Full autonomy, end-to-end. But it's a black box — you can't see the plan, you can't approve the approach before execution starts, and you can't plug in your own agents. OmoiOS is open source, spec-driven (you see and approve the plan), and agent-agnostic.

- **CrewAI / LangGraph / AutoGen** — These are agent frameworks. They give you primitives for building multi-agent systems. OmoiOS is an opinionated system built on top of those ideas — it handles the full lifecycle from "here's a feature idea" to "here's a PR," including the spec pipeline, sandbox isolation, validation, and monitoring. Less flexible, more batteries-included.

The short version: tools like Claude Code and OpenHands are excellent agents. OmoiOS is the orchestration and verification layer that makes them work autonomously without you babysitting.

**Current state:**

Early and evolving. Rough edges. But the core loop works — I describe features, agents plan and execute in sandboxes while I do other work, the system verifies against the spec, handles conflicts, and I review a PR.

Open source, Apache 2.0: https://github.com/kivo360/OmoiOS

Interested in feedback from people who've tried to make autonomous agents reliable. Where does this architecture break? What am I over-engineering? What's missing?

---

## Comment Templates for HN

### When someone asks about AI coding tools:

> Most AI coding tools are good at generating code. The problem I kept hitting was oversight — checking if it's on track, catching drift, deciding when it's actually done.
>
> I built OmoiOS to automate that part. You write a spec with acceptance criteria, agents execute in isolated cloud sandboxes (so your local env stays clean), and a separate validation step checks each task against the spec. If validation fails, the agent gets the failure reason and retries — no human in the loop.
>
> The nice part is your dev environment isn't locked up. Agents work in their sandboxes, you keep coding, and you review a PR when it's done.

### When someone complains about AI reliability:

> The reliability issue isn't the AI being bad. It's that nobody is verifying the output against the actual goal.
>
> Most tools check "did it compile?" or "did it stop erroring?" That's not the same as "did it satisfy the requirement."
>
> I've been working on automated spec verification — you define acceptance criteria upfront, agents execute in sandboxes, and a validator checks each task against those criteria. Separate validation agent, separate sandbox, structured pass/fail with reasoning. If it fails, the system retries with the failure context. You're not the verification layer anymore.

### When someone discusses autonomous coding agents:

> The challenge with autonomous agents is defining and verifying "done."
>
> Running more agents in parallel makes things faster but doesn't solve the core problem — somebody has to check if the output actually satisfies the goal. Usually that somebody is you.
>
> I've been working on spec-driven execution where the system handles verification autonomously. You write requirements with acceptance criteria. Agents execute in isolated sandboxes. A separate validator checks each completed task against the criteria. A monitoring service watches agent trajectories for drift. You review the final PR, not every intermediate step.
>
> Open source (OmoiOS) if anyone wants to look at the architecture.

---

## HN-Specific Tips

1. **Don't oversell.** HN will tear apart any claim that sounds like marketing.

2. **Invite criticism.** "What am I missing?" "Where does this break?" — HN respects humility.

3. **Be technical.** Mention Claude Code, DAG, sandboxes. HN wants to understand how it works.

4. **Acknowledge limitations.** "Still iterating" is honest. "Revolutionary" gets downvoted.

5. **Engage deeply.** Answer every technical question thoroughly. This is where credibility is built.

6. **Don't post and disappear.** First few hours of comments determine success.
