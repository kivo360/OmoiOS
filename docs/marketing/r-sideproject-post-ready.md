# r/SideProject Post — Ready to Copy

**Subreddit:** r/SideProject

---

## Title (copy this)

I spent mass amounts of time babysitting AI coding tools. So I built one that babysits itself.

---

## Body (copy this)

I've been building software for years, and like everyone else, I got excited about AI coding assistants.

Copilot. Cursor. Claude. ChatGPT. I tried them all.

And they're genuinely impressive. The code they produce is often good. Sometimes great.

But here's what nobody talks about: **you become the babysitter.**

You prompt. You wait. You check. Is it done? Is it stuck? Did it go off track? You check again. You re-prompt. You course-correct. Suddenly you're spending more time managing the AI than you would have spent just writing the code yourself.

I kept thinking: why am I the one doing this?

Then I realized something. **The babysitting problem isn't the real problem. It's a symptom.**

The real problem: the AI has no idea what you're actually building. It doesn't know your requirements. It doesn't remember your design decisions. It can't see how this task connects to the bigger picture. So it drifts. And you become the glue holding it all together.

The fix wasn't making the AI smarter. It was giving it a source of truth.

So I built OmoiOS. Here's how it works:

1. You describe what you want (even loosely)
2. The system helps you turn that into a **structured spec** — your requirements, your design, in one place
3. It breaks the spec into tasks with dependencies
4. Claude Code agents execute tasks in parallel sandboxes
5. The system constantly checks progress **against the spec** — not just "did it error?" but "are we actually closer to the goal?"
6. You come back to a PR

The spec is the key. It's what lets the system babysit itself. It knows what "done" looks like because you defined it upfront.

**Current state:** It works. It's also rough around the edges — I'm in the middle of a cleanup sprint. But the core loop is solid, and I've shipped features overnight that would've taken days of back-and-forth before.

If you've felt either problem — the babysitting, or the "AI keeps losing context on what I'm building" — I'd love feedback:

- Where do you get stuck?
- Does the spec → tasks flow make sense?
- What's confusing or broken?

Link in comments.

---

## First Comment (post immediately after)

Link: omoios.dev

Happy to answer questions about the architecture or why I went spec-first instead of just "let it loop."
