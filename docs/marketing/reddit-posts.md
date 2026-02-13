# Reddit Posts for OmoiOS

*Ready to copy-paste. Customize the personal details.*

---

## Post 1: The Journey Post (r/SideProject, r/startups, r/EntrepreneurRideAlong)

**Title:** I spent mass amounts of time babysitting AI coding tools. So I built one that babysits itself.

---

I've been building software for years, and like everyone else, I got excited about AI coding assistants.

Copilot. Cursor. Claude. ChatGPT. I tried them all.

And they're genuinely impressive. The code they produce is often good. Sometimes great.

But here's what nobody talks about: **you become the babysitter.**

You prompt. You wait. You check. Is it done? Is it stuck? Did it go off track? You check again. You re-prompt. You course-correct. Suddenly you're spending more time managing the AI than you would have spent just writing the code yourself.

I kept thinking: why am I the one doing this? The AI is supposed to help ME, not the other way around.

So I started building something different.

The idea was simple: what if AI could babysit itself?

Not just "loop until done" like some continuous agents do. But actually understand the goal, track progress against it, and course-correct without me hovering.

After months of work, I built OmoiOS. Here's how it works:

1. You describe what you want — even loosely
2. The system helps you turn that into a structured spec
3. It breaks the spec into tickets and tasks with dependencies (a DAG)
4. Claude Code agents execute tasks in parallel sandboxes
5. The system constantly checks: are we closer to the goal? Is this task actually done? Are agents stuck?
6. You wake up to a PR

Under the hood, it's running Claude Code (Anthropic's coding agent) in isolated sandboxes. But the key difference: I don't check in. The system checks itself. OmoiOS watches the agents so I don't have to.

It's still evolving. There are bugs. But the core loop works, and I've shipped features overnight that would have taken me days of back-and-forth with traditional AI tools.

If you've ever felt like a babysitter for your AI tools, I'd love your feedback. What's the most annoying part of working with AI assistants for you?

---

## Post 2: The Failure Post (r/Entrepreneur, r/startups, r/SaaS)

**Title:** I failed 4 times trying to make AI coding tools useful before figuring out the real problem

---

I've been chasing the "AI writes code for me" dream for a while now.

**Attempt 1:** Just use ChatGPT/Claude directly. Copy-paste code into my project. Result: worked for small stuff, became a nightmare for anything complex. No context, no memory, constant re-explaining.

**Attempt 2:** Use Copilot in my IDE. Result: great for autocomplete, useless for actual features. Still doing 95% of the thinking myself.

**Attempt 3:** Try Cursor and similar tools. Result: better, but I found myself checking in constantly. "Did it break something? Is it going in the right direction? Is it stuck?" I became a babysitter.

**Attempt 4:** Try continuous agents. Just let it loop until done. Result: it loops, but toward what? No sense of the actual goal. Redoes work. Misses dependencies. Still needs me to check progress.

After all these failures, I realized the problem wasn't the AI. **The problem was me.**

I was the missing piece. The oversight. The "is this actually working?" check. The one tracking progress toward the goal.

But that's exactly what I was trying to automate away.

So I built something that does THAT job — the babysitting.

OmoiOS doesn't just run AI agents. It watches them. It knows what "done" looks like (because it helps you build a spec first). It tracks state against that spec. It catches drift. It course-corrects.

The insight: specs as source of truth. If the system knows your goal, it can measure progress toward it. It can answer "are we there yet?" without asking you.

Now I describe features before bed and wake up to PRs. Not because the AI got smarter — but because something is finally doing the oversight job I was doing manually.

Still evolving. Still has bugs. But the loop works.

Anyone else been through this cycle of trying to make AI coding tools actually useful? What's worked for you?

---

## Post 3: The Technical Post (r/programming, r/artificial, r/MachineLearning)

**Title:** Why I think DAG-based execution is the missing piece for AI coding agents

---

Been thinking a lot about why autonomous coding agents (Devin, etc.) feel like black boxes, while simpler tools (Copilot) feel limited.

The problem with simple continuous agents:

```
while not done:
    do_next_thing()
```

This works, but "done" is poorly defined. The agent doesn't truly know if it achieved the goal. It just knows if it stopped erroring. These are different things.

The problem with complex autonomous agents:

They're smart, but opaque. You can't see the plan. You can't verify the approach. You just wait and hope.

What I've been experimenting with: **DAG-based execution with continuous state checking.**

The flow:

1. Start with a spec (structured requirements, not just "build me X")
2. Decompose into tickets (features) and tasks (atomic work units)
3. Build a dependency graph — which tasks can run in parallel, which are blocked
4. Run Claude Code agents on independent tasks simultaneously across sandboxes
5. After each task: check state against spec. Did this actually move us closer?
6. If drift detected: adapt, retry, or spawn new tasks
7. Loop until spec is satisfied, not just until no errors

Under the hood, it's running Claude Code (Anthropic's coding agent SDK) in isolated sandboxes. Each task gets its own environment.

The key difference from simple loops: **the system has a definition of "done" that it can check against.**

The key difference from black-box agents: **you can see the DAG, approve the plan, trace every task back to requirements.**

I've been building this into a tool (OmoiOS) and it's changed how I think about AI-assisted development. Instead of babysitting Claude Code agents, I review specs and approve plans. The system handles the "are we there yet?" question.

Curious what others think about this approach. Is DAG-based execution overkill? Is the spec-first approach too heavyweight? What would you want from an AI coding system?

---

## Post 4: The Productivity Post (r/productivity, r/Entrepreneur)

**Title:** I automated 4 hours of my day by letting AI babysit itself

---

Used to be: I'd describe a feature to an AI tool, then spend hours going back and forth. Checking progress. Re-prompting. Fixing drift. Answering questions.

AI was supposed to save me time. Instead, I just traded coding for babysitting.

Here's what changed.

I built a system (OmoiOS) where:

1. I describe what I want in the morning (takes 10-15 min to write a decent spec)
2. The system breaks it into tasks with dependencies
3. Claude Code agents work on it in parallel sandboxes
4. OmoiOS watches them — checks progress against the spec, catches drift, course-corrects
5. I review the PR in the evening

The "babysitting" is automated. I don't check in every 30 minutes. I don't re-prompt when it goes off track. The system handles that.

Rough time comparison:

**Before:**
- 15 min: describe feature
- 3+ hours: back-and-forth, checking, re-prompting, fixing
- 1 hour: final review and fixes
- Total: ~4.5 hours of my attention

**After:**
- 15 min: write spec
- 0 min: system works, I do other things
- 30 min: review PR
- Total: ~45 min of my attention

The AI isn't faster. But I am, because I'm not the bottleneck anymore.

It's not magic. The specs need to be decent. The system still has bugs. But the core idea works: AI should babysit itself so you can do literally anything else.

What's eating your time that you wish AI could handle autonomously?

---

## Post 5: The AMA Post (r/SideProject, r/SaaS, r/indiehackers)

**Title:** I built an AI system that babysits other AIs so you don't have to. AMA.

---

Hey everyone,

I'm Kevin. I built OmoiOS — a system that orchestrates AI coding agents with a focus on one thing: **you shouldn't have to babysit them.**

The basic idea:

- You write a spec (the system helps you structure it)
- It generates tickets and tasks with dependencies (a DAG)
- Claude Code agents execute tasks in parallel sandboxes
- The system continuously checks progress against your spec
- If agents drift, it course-corrects
- You review the final PR, not every intermediate step

I built this because I got tired of being the oversight layer for AI tools. They'd work fine, but I'd spend hours checking in, re-prompting, fixing drift. The system does that now.

Happy to answer questions about:

- The technical architecture (DAG execution, state checking)
- Why specs as "source of truth" matters
- How this compares to tools like Devin, Cursor, Copilot
- The honest bugs and limitations (there are many)
- The business side (pricing, early traction, etc.)

AMA!

---

## Post 6: The "Show HN" Style Post (r/programming, r/SideProject)

**Title:** Show r/SideProject: OmoiOS – Continuous AI agents that know when they're actually done

---

I've been building OmoiOS and wanted to share it with this community.

**The problem it solves:**

Continuous agents are great — just "loop until done." But they don't actually know what "done" means. They loop until they stop erroring, which isn't the same as achieving your goal.

**How OmoiOS is different:**

1. **Spec-first:** You describe what you want. OmoiOS helps structure it into requirements. This becomes the source of truth.

2. **DAG execution:** Tasks get organized with dependencies. Independent tasks run in parallel. No sequential bottleneck.

3. **Continuous state checking:** After each task, the system checks: did this actually move us toward the spec? If not, adapt.

4. **Babysits itself:** The oversight loop that you'd normally do manually — checking progress, catching drift, re-prompting — is automated.

**What you get:**

Describe a feature → approve the plan → walk away → review the PR.

**Current state:**

Still evolving. Has rough edges. But the core loop works. I've shipped features overnight that would have taken days of traditional AI back-and-forth.

Looking for feedback from developers who've struggled with the same "AI babysitting" problem.

Link in bio if you want to try it.

---

## Post 7: The Python Architecture Post (r/Python)

**Title:** How I'm using FastAPI + SQLAlchemy + Redis to orchestrate autonomous AI coding agents

---

Wanted to share a Python architecture I've been working on — it's an orchestration system for AI coding agents, and the backend is almost entirely Python. Thought this community might find the patterns interesting (or tear them apart — also useful).

**The problem:** AI coding agents (Claude Code, OpenHands, etc.) are good at executing single tasks. But when you need multiple agents working on a feature in parallel — planning, coding, validating, merging — somebody has to coordinate them. Usually that's you. I wanted that to be code.

**The architecture:**

```python
# Simplified version of what the orchestrator does

class OrchestratorWorker:
    """Polls for tasks, spawns sandboxes, dispatches agents."""

    async def run_loop(self):
        while True:
            tasks = await self.task_queue.get_ready_tasks()  # DAG-aware
            for task in tasks:
                sandbox = await self.daytona.spawn(
                    image="python-nodejs",
                    ephemeral=True
                )
                await self.dispatch_agent(task, sandbox)

    async def dispatch_agent(self, task, sandbox):
        # Three execution modes
        if task.mode == "exploration":
            agent = ReadOnlyAgent(sandbox)
        elif task.mode == "implementation":
            agent = FullAccessAgent(sandbox)
        elif task.mode == "validation":
            agent = TestRunnerAgent(sandbox)

        result = await agent.execute(task)
        await self.validate_against_spec(task, result)
```

**Key Python patterns used:**

**1. Pydantic everywhere for structured LLM output**

```python
from pydantic import BaseModel, Field

class AcceptanceCriterionResult(BaseModel):
    met: bool
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str
    reasoning: str

# LLM returns validated, typed data — no JSON parsing
result = await llm.structured_output(
    prompt=validation_prompt,
    output_type=AcceptanceCriterionResult,
    output_retries=3
)
```

No manual JSON parsing from LLM responses. Ever. `structured_output()` with Pydantic models handles validation and retries. This alone eliminated an entire class of bugs.

**2. SQLAlchemy 2.0 async with ~60 models**

```python
# Specs, tickets, tasks, agents, discoveries, trajectories...
# All tracked in PostgreSQL with pgvector for semantic search

class Task(Base):
    __tablename__ = "tasks"
    dependencies: Mapped[Optional[dict]] = mapped_column(JSONB)
    # JSONB for flexible dependency graphs with GIN indexes
```

One lesson learned the hard way: **never name a SQLAlchemy column `metadata`**. It's reserved by the declarative API and causes silent import failures. Cost me hours.

**3. Redis pub/sub as the event bus**

```python
class EventBusService:
    """All inter-service communication goes through here."""

    async def publish(self, event: SystemEvent):
        await self.redis.publish(
            channel=f"events:{event.entity_type}",
            message=event.model_dump_json()
        )

# Everything publishes events: task created, agent heartbeat,
# validation passed, sandbox spawned, discovery found...
# Frontend gets real-time updates via WebSocket bridge
```

Every state change is an event. The orchestrator worker and API server are separate processes that communicate through Redis. This was a deliberate choice — the worker shouldn't block the API, and the API shouldn't know about execution details.

**4. Spec state machine with LLM evaluators as quality gates**

```python
# 7-phase pipeline: EXPLORE → PRD → REQUIREMENTS → DESIGN → TASKS → SYNC → COMPLETE
# Each phase has an evaluator that scores output and retries on failure

class PhaseEvaluator:
    async def evaluate(self, phase_output: str, spec: Spec) -> EvalResult:
        result = await self.llm.structured_output(
            prompt=f"Score this {phase_output} against standards...",
            output_type=EvalResult
        )
        if result.score < self.threshold:
            return EvalResult(passed=False, retry=True, feedback=result.reasoning)
        return EvalResult(passed=True)
```

By the time agents start coding, the spec has structured requirements with acceptance criteria. Agents aren't working from a vague prompt — they have a machine-checkable definition of "done."

**5. Daytona SDK for sandbox management**

```python
# Each task gets an ephemeral container — full filesystem, git, terminal
sandbox = await daytona.create_workspace(
    image="nikolaik/python-nodejs",
    ephemeral=True,  # auto-deleted on stop
    env_vars=task.env_config
)
# Agent works here. Your local machine is untouched.
# When done → PR, not a diff in your working tree.
```

**The full stack:**

- FastAPI 0.104+ (async everything)
- SQLAlchemy 2.0+ with PostgreSQL 16 + pgvector
- Redis 7 for pub/sub event bus + task queue
- Pydantic v2 for all LLM structured output
- Alembic for migrations (71 and counting)
- Daytona SDK for cloud sandboxes
- Claude Agent SDK for the actual coding agents

**What I'd do differently:**

- The service initialization split (API server vs. orchestrator worker) causes confusion. Some services exist in both, some in only one. Should have designed a cleaner service registry from the start.
- JSONB for task dependencies was the right call for flexibility, but querying nested dependency graphs in PostgreSQL gets ugly fast. Might move to a proper graph structure eventually.
- The `structured_output()` pattern is worth adopting early. Every time I tried manual JSON parsing from LLM responses, it broke in production.

Open source, Apache 2.0: https://github.com/kivo360/OmoiOS

Happy to discuss any of the patterns. What would you do differently?

---

## Post 8: The Self-Hosted Post (r/selfhosted)

**Title:** Self-hosted AI agent orchestration — open source alternative to Devin that runs on your infrastructure

---

I built OmoiOS as a self-hosted system for orchestrating AI coding agents. Sharing it here because I think this community would appreciate having full control over something like this rather than depending on a SaaS black box.

**What it does:**

You describe a feature. The system plans it (structured spec with requirements and acceptance criteria), breaks it into tasks, runs AI coding agents in isolated sandboxes to execute each task, validates the output against your spec, and hands you a pull request. You keep coding on your own machine the whole time — agents work in their sandboxes, not in your environment.

**The self-hosted stack:**

```yaml
# docker-compose.yml (simplified)
services:
  api:
    build: ./backend
    ports: ["18000:18000"]
    depends_on: [postgres, redis]

  orchestrator:
    build: ./backend
    command: python -m omoi_os.workers.orchestrator_worker
    depends_on: [postgres, redis]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]

  postgres:
    image: pgvector/pgvector:pg16
    ports: ["15432:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    ports: ["16379:6379"]
```

Standard stuff: PostgreSQL 16 (with pgvector for semantic search), Redis 7 for the event bus and task queue, FastAPI backend, Next.js frontend. All on non-standard ports (+10000 offset) to avoid conflicts with anything else you're running.

**Why self-host this instead of using Devin/similar:**

| | Devin | OmoiOS (self-hosted) |
|---|---|---|
| **See the plan before execution** | No — black box | Yes — 7-phase spec pipeline, you approve before agents start |
| **Control your data** | Their servers | Your infrastructure |
| **Choose your agents** | Their agent | Claude Agent SDK, extensible to others |
| **Cost** | $500/mo | Your compute + LLM API costs |
| **Modify the system** | No | Apache 2.0, fork it |
| **Sandboxes** | Their cloud | Daytona (cloud or self-hosted) |

**What you get in the dashboard:**

- Kanban board for specs/tickets/tasks
- Dependency graph visualization (which tasks are blocked, which are running)
- Real-time agent status monitoring
- Live event stream (task created, agent heartbeat, validation pass/fail)
- Spec workspace with structured requirements and designs

**What you need to provide:**

- An Anthropic API key (for Claude Agent SDK — the actual coding agents)
- A Daytona account or self-hosted Daytona instance (for sandboxes)
- Docker Compose-capable machine (the orchestration layer itself is lightweight — the heavy lifting happens in sandboxes)

**Honest limitations:**

- Early stage. Rough edges. The core spec → tasks → sandboxes → validation → PR loop works, but expect to hit bugs.
- The monitoring system (agent trajectory analysis, duplicate work detection) is architecturally built but currently disabled while I fix some issues.
- Sandbox overhead: Daytona containers aren't instant. There's latency per task spawn. Worth it for isolation, but it's a tradeoff.
- LLM costs add up. Each spec phase, each task execution, each validation step is an LLM call. You're trading compute cost for your time.

**Getting started:**

```bash
git clone https://github.com/kivo360/OmoiOS.git
cd OmoiOS
cp .env.example .env  # add your API keys
docker-compose up -d
# Frontend: http://localhost:3000
# API docs: http://localhost:18000/docs
```

Open source, Apache 2.0: https://github.com/kivo360/OmoiOS

Looking for feedback from people who've self-hosted similar AI tools. What matters most to you — data privacy, cost control, customization, or something else?

---

## Post 9: The Claude Ecosystem Post (r/ClaudeAI)

**Title:** I built an open-source orchestration layer on top of Claude Agent SDK — agents plan from specs, execute in sandboxes, and verify their own work

---

Been building with Claude Agent SDK for a while now and wanted to share what I've been working on.

**The short version:** OmoiOS is an orchestration system that runs Claude agents in isolated cloud sandboxes, coordinated by a structured spec. You describe a feature, the system plans it, dispatches agents, validates the output against acceptance criteria, and hands you a PR.

**Why I built this on Claude Agent SDK specifically:**

Claude is genuinely good at following structured instructions and producing consistent output. The `structured_output()` pattern with Pydantic models is a game-changer — I use it for everything from spec evaluation to acceptance criteria validation. Every LLM call in the system returns typed, validated data:

```python
class AcceptanceCriterionResult(BaseModel):
    met: bool
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str
    reasoning: str

result = await llm.structured_output(
    prompt=validation_prompt,
    output_type=AcceptanceCriterionResult,
    output_retries=3  # auto-retry if validation fails
)
```

No manual JSON parsing. No stripping markdown code blocks. Claude returns structured data, Pydantic validates it, the system acts on it. This pattern alone eliminated an entire class of bugs.

**How the system uses Claude at each layer:**

```
Feature idea
    │
    ▼
┌─────────────────────────────────────────┐
│ SPEC PIPELINE (Claude evaluates each)   │
│ EXPLORE → PRD → REQUIREMENTS → DESIGN   │
│ → TASKS → SYNC → COMPLETE              │
│                                         │
│ Each phase: Claude scores output,       │
│ retries if below threshold              │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ EXECUTION (Claude Agent SDK in sandbox) │
│                                         │
│ Sandbox A: implementation (full access) │
│ Sandbox B: validation (test execution)  │
│ Sandbox C: exploration (read-only)      │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ VERIFICATION (Claude checks criteria)   │
│                                         │
│ Did implementation satisfy the spec?    │
│ Pass → merge branch                     │
│ Fail → retry with failure context       │
└─────────────────────────────────────────┘
```

Claude isn't just the coding agent — it's the evaluator at every quality gate, the validator that checks acceptance criteria, and the planner that structures your loose idea into a machine-checkable spec.

**What's working well with Claude Agent SDK:**

- Structured output is incredibly reliable with Pydantic models
- Claude follows spec-driven instructions well — if you give it clear acceptance criteria, it can genuinely evaluate whether something meets them
- Running multiple Claude agents in parallel sandboxes works. Each gets its own context, its own files, its own git branch
- The Agent SDK's tool-use capabilities mean agents can genuinely navigate codebases, run tests, check git status

**What's still challenging:**

- Token costs compound fast when you have spec evaluation + task execution + validation + monitoring all making LLM calls
- Claude sometimes "agrees with itself" during validation — the validator passes work that a fresh human eye would catch. Working on better separation between implementation and validation prompts
- Context window management across long-running tasks requires careful summarization

**Current state:**

Early, evolving, has bugs. But the core loop of spec → plan → sandbox execution → validation → PR is working. I've shipped real features with it.

Open source, Apache 2.0: https://github.com/kivo360/OmoiOS

Curious what patterns others have found useful with Claude Agent SDK. Anyone else building orchestration layers on top of it?

---

## Post 10: The Self-Hosted AI Post (r/LocalLLaMA)

**Title:** Open-source AI agent orchestration with sandboxed execution — not an LLM, but the infrastructure layer for running coding agents autonomously

---

I know this sub is primarily about local models, but I think the infrastructure side of running AI agents autonomously is relevant here — especially for folks who care about controlling their own stack.

**What this is:**

OmoiOS is an orchestration system for AI coding agents. Currently uses Claude Agent SDK, but the architecture is agent-agnostic — the orchestration layer doesn't care what's running inside the sandbox, it only cares about the interface: give it a task, get back a result, validate against a spec.

**Why this might interest this community:**

The sandbox architecture means agents run in isolated Daytona containers. Your local machine is untouched. If you eventually want to swap in a local model running coding tasks (via OpenHands, Aider, or something custom), the orchestration layer — spec pipeline, task queue, validation, merge system — stays the same.

```
┌─────────────────────────────┐
│    Orchestration Layer       │
│  (spec, tasks, validation)   │
│         agent-agnostic       │
└──────────────┬──────────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐
│Sandbox │ │Sandbox │ │Sandbox │
│Claude  │ │OpenHands│ │Custom │
│Agent   │ │Agent   │ │Agent  │
└────────┘ └────────┘ └────────┘
```

**The problem it solves:**

Running one AI agent on one task is solved. The hard part is: how do you run multiple agents on a feature, verify the output actually satisfies your goal, handle failures, merge parallel work, and not babysit the whole process?

OmoiOS handles that coordination:

1. **Spec pipeline** — 7-phase planning (EXPLORE → REQUIREMENTS → DESIGN → TASKS) with LLM evaluation at each gate
2. **Sandboxed execution** — ephemeral containers per task, three modes (exploration, implementation, validation)
3. **Automated validation** — separate validator checks output against acceptance criteria, retries with feedback on failure
4. **Dependency-aware scheduling** — tasks form a graph, independent work parallelizes, dependent work waits
5. **Branch merging** — parallel branches get conflict-scored and merged with LLM-assisted conflict resolution

**The stack:**

- Python/FastAPI, PostgreSQL + pgvector, Redis
- Daytona for sandbox containers (cloud or self-hostable)
- Next.js dashboard for monitoring
- Docker Compose for the whole thing

**Honest limitations:**

- Currently requires Anthropic API key (Claude Agent SDK). Not running local models yet.
- Sandbox overhead per task (container spawn time)
- LLM costs add up across spec evaluation, execution, and validation
- Early stage — expect rough edges

Open source, Apache 2.0: https://github.com/kivo360/OmoiOS

Anyone here working on similar orchestration for local model-based agents? Curious if there's interest in plugging local coding agents into this kind of coordination layer.

---

## Post 11: The AI Coding Comparison Post (r/ChatGPTCoding)

**Title:** I tried Claude, GPT, Copilot, Cursor, and continuous agents for coding. Here's where each one broke down and what I built instead.

---

I've been through the full spectrum of AI coding tools over the past year. Each one got me further, but each one hit a wall. Here's what I found:

**ChatGPT / Claude (direct prompting)**

```
You: "Build a user settings page with auth"
AI: [generates code]
You: "Wait, you forgot the middleware..."
AI: [regenerates, different approach this time]
You: "Now the DB schema doesn't match what you did earlier..."
[repeat for 2 hours]
```

Good for isolated questions. Falls apart when the feature has multiple moving parts. No memory between prompts, no awareness of the broader codebase, constant re-explaining.

**Copilot**

Great autocomplete. Not autonomous. You're still doing 95% of the architecture and decision-making. It finishes your sentences but doesn't write the essay.

**Cursor (agent mode)**

Real step up. It can navigate files, run commands, make multi-file changes. But for anything beyond a single task, you're still the coordinator:
- "Is it done?" (you check)
- "Did it drift?" (you check)
- "What should it do next?" (you decide)

**Continuous agents (Claude Code in a loop, OpenHands, etc.)**

```python
while not done:
    result = agent.do_next_thing()
    if not result.errors:
        done = True  # but did it actually work?
```

Better — agents keep working without re-prompting. But "done" means "stopped erroring," not "satisfied the goal." You still babysit.

**Parallel agents / subagents**

Faster wall-clock time. Same oversight problem, but now multiplied. Multiple agents producing output nobody is verifying.

**Where I ended up:**

The problem was never the AI. It was me — I was the oversight layer. The one verifying, coordinating, deciding when things are "done."

So I built OmoiOS to automate that specific job:

1. You describe a feature → system structures it into a spec with acceptance criteria
2. Spec breaks into tasks with dependencies
3. Each task runs in an isolated cloud sandbox (your machine stays clean, you keep coding)
4. A separate validator checks each task against the acceptance criteria — not "did it compile" but "did it satisfy the requirement"
5. Fail → agent retries with failure context. Pass → merge.
6. You review the PR

The key difference from everything above: **the system has a machine-checkable definition of "done" and verifies it autonomously.**

Claude Code, OpenHands, Cursor — they're all good agents. OmoiOS is the layer that coordinates them and checks their work so you don't have to.

**Honest take:**

Still early. Has bugs. Spec quality determines everything — garbage spec = garbage output. But the core loop works and it's changed how I use AI for coding. I review PRs now, not agent output mid-flight.

Open source, Apache 2.0: https://github.com/kivo360/OmoiOS

What's your current AI coding setup? What's the most annoying part of it?

---

## Post 12: The Cursor Frustration Post (r/cursor)

**Title:** I love Cursor but kept hitting a ceiling — here's the orchestration layer I built on top of it

---

Cursor is my daily driver for in-editor AI coding. Agent mode is genuinely useful. Not here to trash it.

But I kept hitting the same wall: Cursor is great for **single tasks**. When I need a full feature — API endpoint + database migration + frontend component + tests + validation — I'm back to being the project manager. Tab back and forth. Check progress. Re-prompt when it drifts. Decide what to do next.

**The specific problems:**

1. **No spec.** Cursor works from your prompt. If you're vague, it guesses. If you're detailed, you just wrote half the code in English instead of Python. There's no structured definition of "done" it can verify against.

2. **Your editor is locked up.** While Cursor agent is working, you're watching. Your dev environment is the execution environment. You can't really code on something else simultaneously.

3. **No parallel execution.** One task at a time. A feature with 5 independent subtasks still runs sequentially through your editor.

4. **No automated verification.** "Done" means the agent stopped making changes. Not "the acceptance criteria are satisfied."

**What I built:**

OmoiOS sits above tools like Cursor. It handles the planning, coordination, and verification layer:

```
You: "Add user settings with email preferences"
    │
    ▼
OmoiOS spec pipeline:
    EXPLORE → REQUIREMENTS → DESIGN → TASKS
    (7 phases, LLM evaluator at each gate)
    │
    ▼
Task graph:
    ┌─ settings API endpoint (sandbox A)
    ├─ email preferences model (sandbox B)  ← parallel
    ├─ settings UI component (sandbox C)    ← parallel
    └─ integration tests (sandbox D)        ← waits for A,B,C
    │
    ▼
Validation:
    Each task checked against acceptance criteria
    Fail → retry with context
    Pass → merge branch
    │
    ▼
You: review the PR
```

Each task runs in an isolated cloud sandbox (Daytona). Your local Cursor environment is completely free. You can keep using Cursor for quick edits while OmoiOS handles the bigger feature in the background.

**It's not a Cursor replacement.** It's what I use when the task is too big for a single agent session. Cursor for quick stuff, OmoiOS for features.

Open source, Apache 2.0: https://github.com/kivo360/OmoiOS

Anyone else hit this ceiling? What's your workflow when a feature is too complex for a single Cursor agent session?

---

## Post 13: The DevOps Post (r/devops)

**Title:** Ephemeral sandbox containers for AI coding agents — how I'm using Daytona + Docker to isolate autonomous agent execution

---

Building an AI agent orchestration system and wanted to share the infrastructure patterns, since the execution layer is fundamentally a DevOps problem.

**The setup:**

AI coding agents need to run code, modify files, execute tests, and make git commits. Letting them do that on your local machine is a bad idea. Letting multiple agents do it simultaneously on the same machine is worse.

So each task gets its own ephemeral sandbox:

```yaml
# What each sandbox gets:
- Isolated filesystem (full project clone)
- Own git branch (created before sandbox spawn)
- Terminal access
- Network access (for package installs, API calls)
- Optional public port (for dev server previews)
- Auto-deleted on completion (ephemeral: true)
```

**The orchestration flow:**

```
Orchestrator (FastAPI worker process)
    │
    ├── polls task queue (PostgreSQL + Redis)
    ├── resolves dependency graph (which tasks are unblocked?)
    ├── for each ready task:
    │       │
    │       ├── create Daytona workspace (ephemeral container)
    │       ├── clone repo, checkout task branch
    │       ├── inject task context (spec, requirements, acceptance criteria)
    │       ├── run agent inside sandbox
    │       ├── on completion: validate against spec
    │       │       ├── pass → merge branch
    │       │       └── fail → retry with feedback
    │       └── destroy sandbox
    │
    └── publish events to Redis (real-time monitoring)
```

**Three execution modes per sandbox:**

| Mode | Filesystem | Git | Use case |
|------|-----------|-----|----------|
| **Exploration** | Read-only | No commits | Codebase analysis, architecture review |
| **Implementation** | Full access | Commits + push | Feature development |
| **Validation** | Full access | No commits | Test execution, acceptance criteria checking |

**The branch strategy:**

```
main
  └── feature/TKT-042-user-settings
        ├── task/TSK-101-api-endpoint     (sandbox A)
        ├── task/TSK-102-db-migration     (sandbox B)
        ├── task/TSK-103-frontend-component (sandbox C)
        └── task/TSK-104-integration-tests  (sandbox D, depends on A+B+C)
```

Each task gets its own branch off the ticket branch. When parallel tasks complete, the merge system:
1. Runs `git merge-tree` dry-run to score conflicts
2. Clean merge → auto-merge
3. Conflicts → LLM-powered resolution (or flag for human review)

**The monitoring layer:**

Every sandbox publishes events to Redis:
- Agent heartbeats (30s intervals)
- Task status transitions
- File changes
- Git operations
- Validation results

A background monitor detects stale sandboxes (no heartbeat for 90s) and terminates them. Idle sandbox monitor catches agents that are running but not producing output.

**What I'd do differently:**

- Daytona container spawn time adds latency. For small tasks, the overhead isn't worth the isolation. Working on a heuristic to skip sandboxing for trivial tasks.
- The orchestrator and API server are separate processes but share the same PostgreSQL. Service initialization is split and some services exist in one but not the other. A proper service mesh would be cleaner.
- Log aggregation across ephemeral containers is painful. Events via Redis help, but debugging a dead sandbox requires good event discipline.

**The stack:**

- Daytona Cloud SDK for sandbox lifecycle
- PostgreSQL 16 + pgvector for task/agent state
- Redis 7 for event bus + pub/sub
- FastAPI orchestrator worker (separate from API server)
- Docker Compose for the control plane
- Next.js dashboard for real-time monitoring

Open source, Apache 2.0: https://github.com/kivo360/OmoiOS

Curious what this community thinks about the sandbox-per-task approach. Overkill? What would you do differently for agent isolation?

---

## Post 14: The Open Source Post (r/opensource)

**Title:** OmoiOS — open source AI agent orchestration (FastAPI + PostgreSQL + Next.js, Apache 2.0)

---

Sharing an open-source project I've been building: OmoiOS is an orchestration platform for AI coding agents.

**What it does in one line:** Define the spec. Agents build in sandboxes. The system verifies. You review the PR.

**Why open source matters for this specifically:**

Tools like Devin are closed-source black boxes. You can't see the plan before execution. You can't modify the agent behavior. You can't self-host. You're trusting a $500/mo service with your codebase.

I think AI agent orchestration should be open. You should be able to:
- See exactly what the agents are doing
- Approve the plan before agents start coding
- Modify the spec pipeline, validation logic, or agent configuration
- Self-host on your own infrastructure
- Swap in different agents (Claude, OpenHands, whatever comes next)

**The scope:**

| Component | Tech | Size |
|-----------|------|------|
| Backend API | FastAPI + SQLAlchemy 2.0 | ~30 route files, ~60 models |
| Database | PostgreSQL 16 + pgvector | 71 Alembic migrations |
| Event system | Redis 7 pub/sub | Real-time WebSocket bridge |
| Sandboxes | Daytona Cloud | Ephemeral containers per task |
| Frontend | Next.js 15 + ShadCN UI | ~94 pages, Kanban boards, dependency graphs |
| Agent runtime | Claude Agent SDK | Structured output with Pydantic |

**Key features:**

- **Spec-driven workflow** — 7-phase pipeline (EXPLORE → REQUIREMENTS → DESIGN → TASKS) with LLM quality gates at each phase
- **Sandboxed execution** — each task runs in an isolated cloud container. Your local environment stays clean. You keep coding.
- **Automated validation** — separate validator agent checks each task against acceptance criteria. Fail → retry with context.
- **Dependency-aware scheduling** — task graph with parallel execution for independent work
- **Discovery branching** — agents discover new requirements mid-execution and spawn new tasks
- **Branch merging** — conflict scoring + LLM-assisted merge for parallel branches
- **Real-time dashboard** — Kanban, dependency graphs, agent monitoring, event stream

**Honest state:**

Early stage. The core loop (spec → tasks → sandboxes → validation → PR) works. Some subsystems (monitoring loop for agent trajectory analysis) are architecturally built but currently disabled while I fix issues. Expect rough edges. Contributions welcome.

**Getting started:**

```bash
git clone https://github.com/kivo360/OmoiOS.git
cd OmoiOS
cp .env.example .env
docker-compose up -d
```

Apache 2.0: https://github.com/kivo360/OmoiOS

Looking for contributors and feedback. What would make you want to contribute to a project like this?

---

## Post 15: The Web Dev Productivity Post (r/webdev)

**Title:** How I ship full-stack features while my AI agents code in sandboxes — my workflow for not babysitting Claude Code

---

I'm a web dev and like most of you, I use AI coding tools daily. But I kept running into the same frustration: for anything bigger than a single-file change, I'd spend more time managing the AI than coding.

Here's my current workflow with OmoiOS (something I built):

**Morning:**
1. Write a spec — "Add user notification preferences with email digest settings"
2. System structures it: requirements, acceptance criteria, design, task breakdown
3. I review the plan, approve it
4. Agents start working in cloud sandboxes

**During the day:**
5. I code on my own stuff — different feature, bug fixes, whatever
6. My local environment is completely untouched. Agents work in isolated Daytona containers.
7. Each agent has its own git branch, its own filesystem, its own terminal.

**End of day:**
8. System has validated each task against acceptance criteria
9. Parallel branches are merged
10. I review a PR

**The key insight for web devs specifically:**

When you need a full-stack feature (Next.js component + API route + database migration + tests), the tasks are naturally parallelizable. The frontend component doesn't depend on the API route being finished first — they can be built simultaneously by different agents in different sandboxes, then integrated.

```
┌─ Next.js page component (sandbox A)
├─ API route + middleware (sandbox B)     ← parallel
├─ Prisma/SQLAlchemy migration (sandbox C) ← parallel
└─ Integration tests (sandbox D)          ← waits for A+B+C
```

Each sandbox is an ephemeral container. Three execution modes: exploration (read-only — agent analyzes your codebase first), implementation (full access — writes code, commits), validation (runs tests against acceptance criteria).

**What this doesn't replace:**

- Your IDE. I still use Cursor/VS Code for my own coding.
- Quick edits. If it's a 5-minute fix, just do it yourself.
- Design decisions. You still write the spec and approve the plan.

**What it does replace:**

- The 3 hours of back-and-forth getting an AI to build a feature correctly
- The tab-switching to check if the agent is stuck
- The manual coordination when multiple parts of a feature need to come together

Open source, Apache 2.0: https://github.com/kivo360/OmoiOS

The frontend is Next.js 15, App Router, ShadCN UI — so if you're into that stack, the codebase itself might be interesting to look at. Kanban boards, React Flow dependency graphs, real-time WebSocket updates.

What's your current workflow for AI-assisted full-stack features? Curious how others handle multi-file AI coding.

---

## Post 16: The Senior Dev Post (r/ExperiencedDevs)

**Title:** Lessons from building an AI agent orchestration system — the hard problems aren't the agents

---

I've been building a system that orchestrates AI coding agents (Claude Agent SDK, running in isolated sandboxes). Wanted to share some lessons that might be interesting to experienced devs, because the hard problems turned out to be different from what I expected.

**Lesson 1: The agent isn't the bottleneck. Verification is.**

Claude Code is surprisingly good at writing code when given clear instructions. The problem is: how do you know if the output is correct? Not "does it compile" — "does it satisfy the requirement?"

I ended up building a 7-phase spec pipeline (EXPLORE → PRD → REQUIREMENTS → DESIGN → TASKS → SYNC → COMPLETE) where each phase has an LLM evaluator as a quality gate. By the time agents start coding, there are structured acceptance criteria that a separate validator can check against.

The validator runs in its own sandbox, checks the implementation against each criterion, and returns structured pass/fail with reasoning. Failure feeds back to the implementation agent with context for retry.

This is just software testing applied to AI output. But it took me months to realize that "let the AI code" is the easy part and "verify the AI's work programmatically" is the actual engineering problem.

**Lesson 2: Sandboxing changes everything about the development experience.**

```
Without sandboxes:
- Agent works in your repo → your editor, your branch, your machine
- You wait. You watch. You're blocked.

With sandboxes:
- Agent works in a Daytona container → its own filesystem, its own branch
- You keep coding on your own stuff. Review the PR later.
```

This sounds obvious, but the UX difference is massive. When agents can't mess up your local state, you stop caring about what they're doing mid-execution. You just care about the PR at the end.

**Lesson 3: Task granularity is the key design decision.**

Too coarse: "Build the user settings feature" — agent drifts, scope creeps, impossible to validate intermediate state.

Too fine: "Add line 47 to settings.py" — overhead per task (sandbox spawn, context injection, validation) dominates actual execution time.

The sweet spot I've found: one task per logical unit that has a testable outcome. "API endpoint that returns user preferences with test coverage" — small enough to validate, large enough to be worth the sandbox overhead.

**Lesson 4: Service boundaries matter more than you'd think.**

The system has two main processes: the API server (FastAPI) and the orchestrator worker. They share PostgreSQL and Redis but initialize different services.

```
API Server:        MonitoringLoop, MemoryService, DiscoveryService, BillingService, ...
Orchestrator:      PhaseProgressionService, SynthesisService, CoordinationService, ...
Both:              DatabaseService, EventBusService, TaskQueueService, ...
```

This split causes real confusion. Some services exist in both processes with separate instances. Some exist in only one. There's no service registry enforcing this — it's just convention. I'd redesign this if I were starting over.

**Lesson 5: Git merge is the hardest coordination problem.**

When you have 3 agents working on parallel tasks on separate branches, they all need to merge back. Merge conflicts from AI-generated code are particularly tricky because the agents didn't coordinate their approaches — they just independently solved their tasks.

Current approach: `git merge-tree` dry-run to score conflicts, auto-merge clean branches, LLM-powered conflict resolution for conflicts. Works okay. Not great. This is the area where I've made the least progress.

**Lesson 6: Discovery branching is powerful but dangerous.**

Agents discover new requirements during execution — a validation agent finds an edge case, an implementation agent realizes a dependency is missing. The system can spawn new tasks dynamically.

This is powerful because the work adapts to reality. It's dangerous because the task graph can grow unexpectedly. Need heuristics for "stop discovering and ship what you have" — haven't solved this well yet.

**The system:**

OmoiOS — open source, Apache 2.0: https://github.com/kivo360/OmoiOS

~60 database models, 71 migrations, ~30 API route files, Next.js dashboard. Early stage, rough edges, but the core loop works.

What hard problems have you hit building with AI agents? Curious if others have found different solutions to the verification and coordination challenges.

---

## Post 17: The Learn Programming Post (r/learnprogramming)

**Title:** How AI coding agents actually work behind the scenes — a breakdown of agent orchestration

---

Seeing a lot of questions here about AI coding tools and how they work under the hood. I build an AI agent orchestration system, so I thought I'd explain the concepts in simple terms.

**What is an AI coding agent?**

A coding agent is an LLM (like Claude or GPT) that can do more than just chat. It can:
- Read and write files
- Run terminal commands
- Execute code
- Make git commits
- Navigate a codebase

Think of it as an AI that has hands, not just a mouth. It doesn't just tell you what to write — it writes it, runs it, and checks if it works.

**The simplest agent loop:**

```python
while not done:
    # 1. Look at current state (files, errors, tests)
    state = observe_environment()

    # 2. Decide what to do next
    action = llm.decide(state, goal)

    # 3. Do it
    result = execute(action)  # edit file, run command, etc.

    # 4. Check if we're done
    if result.no_errors:
        done = True
```

This is basically what tools like Cursor agent mode and Claude Code do. It works surprisingly well for single tasks.

**The problem with the simple loop:**

`result.no_errors` doesn't mean the task is done correctly. It means the code runs without crashing. Those are very different things.

Example: You ask the agent to "add user authentication." The agent adds a login form that accepts any password. No errors. Tests pass (because there are no tests for password validation). The agent thinks it's done. It's not.

**How orchestration solves this:**

Instead of one agent in one loop, you use a system that:

1. **Plans first** — breaks the goal into smaller tasks with clear acceptance criteria

```
Goal: "Add user authentication"
  ├── Task 1: "Password hashing with bcrypt"
  │     Criteria: passwords are never stored in plaintext
  ├── Task 2: "Login endpoint"
  │     Criteria: returns JWT token, rejects wrong password
  ├── Task 3: "Auth middleware"
  │     Criteria: protected routes return 401 without token
  └── Task 4: "Integration tests"
        Criteria: all above criteria tested
```

2. **Runs tasks in isolation** — each task gets its own sandbox (a separate computer in the cloud). One agent can't break another agent's work.

3. **Verifies the output** — after each task, a separate process checks: "Did this actually satisfy the criteria?" Not "did it crash?" but "did it do what was asked?"

4. **Retries intelligently** — if verification fails, the failure reason gets sent back to the agent: "Password hashing is missing — bcrypt not used." The agent retries with that context.

**Why sandboxes matter:**

Imagine 3 agents all editing the same file at the same time on your computer. Chaos.

With sandboxes, each agent has its own copy of the project in an isolated container:

```
Your computer:  untouched, you keep working
Sandbox A:      Agent 1 works on authentication
Sandbox B:      Agent 2 works on the frontend
Sandbox C:      Agent 3 writes tests
```

When they're all done, their work gets merged together — like how developers use git branches.

**This is what I'm building:**

I built a system called OmoiOS that does all of the above. It's open source if you want to look at how it works: https://github.com/kivo360/OmoiOS

The codebase itself is a real-world example of:
- FastAPI (Python web framework)
- SQLAlchemy (database ORM)
- PostgreSQL + Redis
- Next.js (React frontend)
- Docker Compose (running multiple services)

If you're learning any of these technologies, reading through a real production codebase can be more educational than tutorials.

Questions welcome — happy to explain any of these concepts in more detail.

---

## Post 18: The FastAPI Post (r/FastAPI)

**Title:** Patterns from building a 30-route FastAPI app with separate worker processes, Redis event bus, and LLM structured output

---

Building an AI agent orchestration system in FastAPI and wanted to share some patterns that might be useful — especially around service architecture, worker processes, and integrating LLMs.

**The setup:** ~30 route files, ~60 SQLAlchemy models, 71 Alembic migrations, separate API server + background worker process.

**Pattern 1: Separate API server and worker process**

```python
# api/main.py — handles HTTP requests
app = FastAPI()

@asynccontextmanager
async def lifespan(app):
    # Initialize 25+ services
    db = DatabaseService(...)
    event_bus = EventBusService(...)
    monitoring = MonitoringLoop(...)
    yield

# workers/orchestrator_worker.py — handles task execution
async def init_services():
    # Initialize 9 services (different set!)
    db = DatabaseService(...)  # Own connection
    task_queue = TaskQueueService(...)
    coordination = CoordinationService(...)
```

The API server and orchestrator worker are separate processes. They share PostgreSQL and Redis but initialize different services. This was intentional — the worker shouldn't block API responses, and the API shouldn't know about sandbox execution details.

**The gotcha:** No service registry enforces which services live where. It's convention. I've had bugs where code in the API tried to use a service that only exists in the worker. If I were starting over, I'd use a stricter dependency injection pattern.

**Pattern 2: Pydantic structured output for all LLM calls**

```python
from pydantic import BaseModel, Field

class TaskAnalysis(BaseModel):
    execution_mode: Literal["exploration", "implementation", "validation"]
    requires_git: bool
    requires_tests: bool
    estimated_complexity: float = Field(ge=0.0, le=1.0)

# Never parse JSON from LLM responses manually
analysis = await llm_service.structured_output(
    prompt=f"Analyze this task: {task.description}",
    output_type=TaskAnalysis,
    output_retries=3  # Auto-retry if Pydantic validation fails
)

# analysis.execution_mode is typed, validated, ready to use
```

Every LLM interaction returns a Pydantic model. The `structured_output()` method handles prompting for JSON, parsing, Pydantic validation, and retry on failure. This eliminated all my "LLM returned markdown instead of JSON" bugs.

**Pattern 3: Redis pub/sub as the event bus**

```python
class EventBusService:
    async def publish(self, event: SystemEvent):
        await self.redis.publish(
            channel=f"events:{event.entity_type}",
            message=event.model_dump_json()
        )

    async def subscribe(self, entity_type: str):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(f"events:{entity_type}")
        async for message in pubsub.listen():
            yield SystemEvent.model_validate_json(message["data"])
```

Every state change publishes an event. The frontend connects via WebSocket and gets real-time updates. The worker publishes task status, agent heartbeats, validation results. The API server publishes spec phase transitions, user actions.

**Pattern 4: YAML config + .env secrets with OmoiBaseSettings**

```python
class TaskQueueSettings(OmoiBaseSettings):
    yaml_section = "task_queue"
    model_config = SettingsConfigDict(env_prefix="TASK_QUEUE_")

    age_ceiling: int = 3600        # From config/base.yaml
    priority_weight: float = 0.45  # From config/base.yaml
    # Secrets come from env vars only

@lru_cache(maxsize=1)
def load_task_queue_settings() -> TaskQueueSettings:
    return TaskQueueSettings()
```

YAML files (version controlled) for application settings. `.env` files (gitignored) for secrets only. Pydantic Settings handles the merge. Took a few iterations to land on this — started with everything in `.env` which was a mess.

**Pattern 5: SQLAlchemy reserved words will ruin your day**

```python
# This will crash your entire application on import:
class TicketHistory(Base):
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB)  # DON'T

# This works:
class TicketHistory(Base):
    change_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)  # DO
```

`metadata` is reserved by SQLAlchemy's declarative API. The error is a cryptic `InvalidRequestError` at import time. Spent hours on this. Also avoid `registry` and `declared_attr`.

**The project:**

OmoiOS — AI agent orchestration. Open source, Apache 2.0: https://github.com/kivo360/OmoiOS

If you're building a FastAPI app with similar patterns (background workers, event-driven, LLM integration), happy to discuss what worked and what didn't.

---

## Post 19: The Next.js Frontend Post (r/nextjs)

**Title:** Building a real-time agent monitoring dashboard with Next.js 15, React Flow, and WebSocket — patterns from a ~94 page app

---

I'm building an AI agent orchestration platform and the frontend is a Next.js 15 App Router application. Wanted to share some patterns from building a real-time dashboard that monitors autonomous agents.

**The scope:** ~94 pages, ShadCN UI, Zustand + React Query for state, React Flow for dependency graph visualization, WebSocket for real-time updates.

**Pattern 1: Dual state management — Zustand for client, React Query for server**

```typescript
// Server state: React Query handles caching, refetching, optimistic updates
const { data: tasks } = useQuery({
  queryKey: ['tasks', specId],
  queryFn: () => fetchTasks(specId),
})

// Client state: Zustand handles UI state, WebSocket-driven updates
const useAgentStore = create((set) => ({
  activeAgents: {},
  updateAgent: (id, status) =>
    set((state) => ({
      activeAgents: { ...state.activeAgents, [id]: status }
    })),
}))
```

React Query manages everything that comes from the API. Zustand manages everything that comes from WebSocket events (agent heartbeats, live status changes). The WebSocket bridge invalidates React Query caches when server state changes.

**Pattern 2: React Flow for dependency graph visualization**

The task dependency graph is the core visualization — which tasks are running, which are blocked, which are complete:

```typescript
// Tasks become nodes, dependencies become edges
const nodes = tasks.map(task => ({
  id: task.id,
  data: {
    label: task.title,
    status: task.status,  // pending | running | validating | complete | failed
  },
  type: 'taskNode',  // custom node with status indicator
}))

const edges = tasks.flatMap(task =>
  task.dependencies.map(depId => ({
    id: `${depId}-${task.id}`,
    source: depId,
    target: task.id,
    animated: task.status === 'running',
  }))
)
```

Animated edges when a task is actively running. Color-coded nodes by status. The graph updates in real-time as agents complete work — pretty satisfying to watch.

**Pattern 3: App Router route groups for auth separation**

```
app/
├── (auth)/           # Login, callback, signup
│   ├── login/
│   └── callback/
├── (dashboard)/      # Protected routes
│   ├── layout.tsx    # Auth check wrapper
│   ├── specs/
│   ├── tasks/
│   └── agents/
└── (marketing)/      # Public landing pages
    ├── page.tsx
    └── pricing/
```

Three route groups with different layouts and auth requirements. The dashboard layout wraps everything in an auth check and provides the sidebar navigation. Marketing pages are fully public.

**Pattern 4: WebSocket → React Query cache invalidation**

```typescript
// WebSocket event bridge
useEffect(() => {
  ws.on('task_completed', (event) => {
    // Invalidate React Query cache → automatic refetch
    queryClient.invalidateQueries(['tasks', event.specId])

    // Update Zustand immediately for snappy UI
    useAgentStore.getState().updateAgent(event.agentId, 'idle')
  })
}, [])
```

WebSocket events do two things: invalidate React Query caches (triggers a clean refetch from the API) and update Zustand directly (immediate UI response). The user sees the status change instantly, and the full data arrives moments later via the refetch.

**What the dashboard shows:**

- **Kanban board** — specs and tasks organized by phase/status
- **Dependency graph** — React Flow visualization of task relationships, live-updating
- **Agent monitor** — real-time agent status (active, idle, stuck, failed) with heartbeat indicators
- **Event stream** — chronological feed of everything happening (task created, agent started, validation passed, branch merged)
- **Spec workspace** — multi-tab view for requirements, design, tasks, execution — all linked

**ShadCN UI has been excellent for this.** The component library + Tailwind means consistent styling without fighting CSS. The data table, command palette (Cmd+K), sheet panels, and toast notifications all came from ShadCN with minimal customization.

Open source, Apache 2.0: https://github.com/kivo360/OmoiOS

If you're building real-time dashboards with Next.js 15 + App Router, happy to discuss patterns. The WebSocket + React Query + Zustand combination has worked well but there are definitely rough edges.

---

## Comment Templates

### When someone asks "what AI coding tools do you use?"

> I've tried most of them — Copilot, Cursor, Claude, ChatGPT for code. They're all good at generating code, but I kept spending hours babysitting them. Checking if they're on track, re-prompting when they drift, etc.
>
> Been using OmoiOS (something I built) which handles the oversight automatically. You write a spec, it executes with multiple agents, and checks progress against your goal. Still evolving but it's changed my workflow.
>
> The others are great for autocomplete and quick questions though. Different tools for different jobs.

### When someone complains about AI coding tools being unreliable

> Yeah, this is the problem I kept hitting too. The AI isn't bad — it's just that nobody's watching it.
>
> With traditional tools, YOU become the reliability layer. You're the one checking if it's on track, catching mistakes, re-prompting.
>
> I built something (OmoiOS) that does that oversight automatically. It has a "spec" it checks against, so it knows when things are drifting. Doesn't fix the AI being unreliable — just automates the babysitting you'd do anyway.

### When someone asks about autonomous coding agents

> The main ones I know of:
>
> - **Devin** — impressive but black box. Hard to know what it's doing.
> - **Cursor agent mode** — good for IDE workflows but still pretty hands-on
> - **OpenHands/other open source** — promising, varying levels of maturity
>
> I built OmoiOS as a different approach — spec-driven, DAG-based execution, continuous state checking. The key difference is you see the plan and the system babysits itself against your spec.
>
> Depends what you're looking for. If you want full autonomy, OmoiOS is worth trying. If you want in-IDE help, Cursor is solid.

---

## DM Template

**First message (no link):**

> hey, saw your post about [specific problem — e.g., "AI tools being unreliable" or "spending too much time checking on Claude"].
>
> i've been dealing with the same thing and actually built something to fix it. would you be open to trying it? looking for honest feedback from people who get this problem.

**If they respond positively:**

> awesome, it's called OmoiOS. basic idea: you write a spec, it breaks it into tasks, runs AI agents in parallel, and continuously checks progress against your goal. the "babysitting" is automated.
>
> still evolving but the core works. here's the link: [link]
>
> would love to know what you think, even if it's "this sucks because X" — that's useful too.

---

## Bio Template

Make sure your Reddit profile bio includes:

> Building OmoiOS — AI that babysits itself so you don't have to. [link]
>
> DMs open for feedback.

---

*Remember: 90% value, 10% product. Help first, promote second. The link is in your bio — let people discover it.*
