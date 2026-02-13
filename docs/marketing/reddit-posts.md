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
