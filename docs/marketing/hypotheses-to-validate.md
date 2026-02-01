# Hypotheses to Validate

> Track market hypotheses before building. Validate with conversations, not code.

---

## Active Hypothesis

### Hypothesis 1: AI Coding Army for Engineering Leaders

**The Bet:** Engineering leaders at scaling startups (50-500 employees) will pay for AI agents that turn specs into working code, reducing their dependency on hiring.

**Target ICP:**
- VP Engineering, Engineering Manager, CTO
- Series A/B/C funded startups
- 50-500 employees
- Backlog growing faster than team can ship

**Evidence Needed to Validate:**
| Signal | Target | Current |
|--------|--------|---------|
| Outreach sent | 500+ | 0 |
| Conversations | 10+ | 0 |
| People who try it | 5 | 0 |
| "Holy shit" moments | 3 | 0 |
| Willing to pay (any amount) | 1 | 0 |

**Key Questions to Answer:**
- What's the aha moment?
- What task/workflow do they try first?
- What makes them come back (or not)?
- What would they pay?

**Status:** 🟡 Testing (outreach starting)

**Pivot Signal:** 30+ right-fit conversations, people understand it, nobody cares enough to pay or keep using.

---

## Parked Hypotheses

### Hypothesis 2: AI-Powered n8n/Automation Pipelines

**The Bet:** Someone wants AI to build and manage automation pipelines (n8n, Zapier, Make style workflows).

**Origin:** Conversation with someone who said they "love automation pipelines."

**Questions Before Building:**
1. Who is the buyer? (Same as H1 or different?)
   - Engineering leaders?
   - Ops/RevOps people?
   - Marketing automation folks?
   - Solo founders/indie hackers?

2. What's the actual pain?
   - Building pipelines is tedious?
   - Debugging broken automations?
   - Connecting systems that don't integrate?
   - Something else?

3. What exists today and why isn't it enough?
   - n8n (open source, self-host)
   - Zapier (easy but expensive at scale)
   - Make (cheap but complex)
   - Tray.io (enterprise)

**Evidence Needed to Validate:**
| Signal | Target | Current |
|--------|--------|---------|
| People who mention automation pain unprompted | 5 | 1 |
| "I'd pay for AI-powered automation" | 3 | 0 |
| Waitlist signups (if landing page) | 50 | N/A |

**How to Test (Without Building):**
- [ ] Add automation question to outreach: "Do you use n8n/Zapier/Make? What's broken?"
- [ ] Search Reddit/Twitter for n8n complaints
- [ ] Check n8n community forums for common pain points
- [ ] Optional: Create simple landing page, run $50 in ads, measure signups

**Status:** 🔴 Parked (validate H1 first)

**Promotion Signal:** H1 fails AND 5+ people mention automation pain in conversations.

---

## Hypothesis Lifecycle

```
PARKED → TESTING → VALIDATED → BUILDING
                 ↓
              KILLED
```

**Parked:** Interesting idea, not enough evidence yet. Don't build.

**Testing:** Actively gathering evidence through conversations/outreach. Don't build features yet.

**Validated:** Evidence shows people will pay. Build the minimum to deliver value.

**Killed:** Tested and failed. Move on, don't revisit for 6+ months.

---

## Rules

1. **One hypothesis in "Testing" at a time.** Focus beats breadth.

2. **Validate with conversations, not code.** Building is expensive. Talking is cheap.

3. **Set clear evidence thresholds.** "5 people say X" not "I feel like people want X."

4. **Time-box testing.** 4-8 weeks max before deciding to build, pivot, or kill.

5. **Park, don't kill, interesting ideas.** They might become relevant later.

6. **Let the market promote hypotheses.** If automation keeps coming up in H1 conversations, that's a signal to promote H2 to testing.

---

## Adding a New Hypothesis

When you hear something interesting:

```markdown
### Hypothesis N: [Name]

**The Bet:** [One sentence on who will pay for what]

**Origin:** [Where did this idea come from?]

**Questions Before Building:**
1. Who is the buyer?
2. What's the actual pain?
3. What exists today?

**Evidence Needed:**
- [ ] X people mention this unprompted
- [ ] Y people say they'd pay
- [ ] Z other signal

**Status:** 🔴 Parked

**Promotion Signal:** [What would make you test this?]
```

---

## Log

| Date | Hypothesis | Action | Notes |
|------|------------|--------|-------|
| 2026-01-30 | H1: AI Coding Army | Created | Primary focus |
| 2026-01-30 | H2: AI n8n Pipelines | Parked | One conversation, need more signal |
