# Hacker News Posts for OmoiOS

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

Simple continuous agents (like Ralph) just loop: `while not done: do_thing()`. But "done" is poorly defined. The agent doesn't know if it achieved the goal — it just knows if it stopped erroring.

OmoiOS gives the loop a brain. It knows what "done" looks like because it has a spec to check against.

**Tech stack:**

- Backend: Python/FastAPI
- Agents: Claude Code (Anthropic's agent SDK) running in sandboxes
- Execution: DAG-based task queue with dependency resolution
- State checking: Continuous comparison against structured spec

**Current state:**

Early. Buggy. But the core loop works. I've shipped features overnight that would have taken days of back-and-forth with traditional prompting.

Code isn't open source yet (cleaning it up), but happy to discuss the architecture.

Looking for feedback, especially from people who've tried to make autonomous coding agents reliable.

---

## Post 2: Technical Discussion Post

**Title:** Ask HN: Has anyone solved the "babysitting problem" with AI coding agents?

**Body:**

I've been using AI coding tools for a while — Copilot, Cursor, Claude directly, etc. They're good at generating code, but I keep running into the same issue:

I end up babysitting.

The AI works, but I'm constantly checking in. Is it on track? Did it drift? Is it stuck? Should I re-prompt? I'm the oversight layer, and that oversight takes more time than I expected.

Continuous agents (like Ralph) help — just "loop until done." But they don't actually know what "done" means. They loop until they stop erroring, which isn't the same thing.

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

## Post 4: Failure/Learning Post

**Title:** What I learned failing to make AI coding agents reliable

**Body:**

I've spent months trying to make AI coding agents actually useful for autonomous work. Here's what failed and what finally worked.

**Attempt 1: Just use Claude/GPT directly**

Paste context, get code, paste into project. Works for small stuff. For anything complex, you're constantly re-explaining context. The AI forgets, drifts, makes inconsistent decisions.

**Attempt 2: Copilot/Cursor**

Great for autocomplete. Still doing 95% of the thinking myself. Not autonomous.

**Attempt 3: Continuous agents (Ralph-style)**

```python
while not done:
    agent.do_next_thing()
```

Better — the agent keeps working without prompting. But "done" is undefined. The agent loops until it stops erroring, not until it achieves the goal. And you end up checking in constantly to see if it's on track.

**What finally worked:**

Specs as source of truth + DAG execution + continuous state checking.

1. Define what "done" looks like upfront (structured spec)
2. Break into tasks with dependencies (DAG)
3. Run Claude Code agents in sandboxes
4. After each task, check: did this move us toward the spec?
5. If not, adapt. The system babysits itself.

The insight: the AI isn't the bottleneck. The oversight is. If you automate the oversight, the AI becomes useful.

I built this into a tool (OmoiOS). Early and buggy, but the core loop works. Happy to discuss the architecture if anyone's interested.

---

## Comment Templates for HN

### When someone asks about AI coding tools:

> The main issue I've hit with most AI coding tools is babysitting. They generate good code, but you spend hours checking in, re-prompting, catching drift.
>
> I've been working on a system (OmoiOS) that runs Claude Code agents in sandboxes with a DAG for task dependencies. The key difference: it continuously checks state against a spec, so you're not the oversight layer.
>
> Still early, but the architecture might be interesting if you're hitting the same problems.

### When someone complains about AI reliability:

> The reliability issue I've seen is less about the AI being bad and more about nobody watching it.
>
> With traditional tools, you become the reliability layer. You're checking if it's on track, catching drift, re-prompting.
>
> I've been experimenting with automating that oversight — run agents in a loop, but check state against a spec after each task. The spec defines "done," so the system can measure progress without human checking.

### When someone discusses autonomous coding agents:

> The challenge I've found with autonomous agents is defining "done."
>
> Most continuous agents loop until they stop erroring. But "no errors" ≠ "achieved the goal."
>
> I've been working on spec-driven execution — you define what done looks like upfront, break it into a DAG of tasks, run Claude Code agents in sandboxes, and check state against spec after each task. The system babysits itself.
>
> Happy to discuss the architecture if useful.

---

## HN-Specific Tips

1. **Don't oversell.** HN will tear apart any claim that sounds like marketing.

2. **Invite criticism.** "What am I missing?" "Where does this break?" — HN respects humility.

3. **Be technical.** Mention Claude Code, DAG, sandboxes. HN wants to understand how it works.

4. **Acknowledge limitations.** "Early and buggy" is honest. "Revolutionary" gets downvoted.

5. **Engage deeply.** Answer every technical question thoroughly. This is where credibility is built.

6. **Don't post and disappear.** First few hours of comments determine success.
