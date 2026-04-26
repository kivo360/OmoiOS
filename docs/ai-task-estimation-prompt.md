# AI Coding Task Estimator

> Drop this whole file into a coding agent (Claude Opus 4.7+, GPT-5, etc.)
> followed by a task description. The agent will gather signals from your
> codebase, score the factors, and return a structured estimate of both
> AI wall-clock time and the equivalent senior-human hours, with a ratio
> and confidence.

---

## Why traditional estimates fail for AI

A senior dev's mental model assumes serial work: think → type → run → wait
→ debug → repeat, with frequent context-switches and tab-aways. That
predicts 12-14 hours for a task an LLM finishes in 30 minutes — not
because the LLM is "smarter," but because it does several things humans
can't:

- **Reads in parallel.** Holds a 4,000-line file + 12 related files in
  context simultaneously. No tab-aways.
- **Generates at sustained throughput.** No think-type-think-type cadence.
- **Doesn't context-switch costs**: keeps every variable name and contract
  fresh across an hour of work.
- **Tool-use loop is tight.** Bash + Edit round-trips are sub-second; the
  human-equivalent is open-terminal + run + read + edit + save.

But it also has failure modes humans don't (silent hallucinations,
loops on bad assumptions). The estimate has to weigh both.

---

## The estimation formula

```
LLM_wall_clock = (iterations × test_cycle_time)
                + research_time
                + edit_time
                + tool_friction_time

Iterations ≈ f(hallucination_prior_on_APIs_touched,
              specification_clarity,
              hidden_state_volume)

Edit_time ≈ files_touched × ~30s (well-scoped) to ~3min (cross-cutting)

Research_time ≈ 0 if API in training data,
              ~2min if Context7-fetchable,
              ~10min if undocumented (read source)
```

The **iterations × test_cycle** term dominates almost everything else.
A 5-second test loop with 4 iterations = 20 seconds. A 5-minute CI
loop with 4 iterations = 20 minutes. Same agent, same task, 60× delta.

---

## Inputs the agent should gather BEFORE estimating

Run these and report findings:

```bash
# 1. Surface area
git status                    # what's already in flight
git log --oneline -10         # recent style
find <task_scope> -name '*.py' -o -name '*.ts' | wc -l

# 2. Distinct external SDK calls (the real complexity, not LOC)
grep -RhE 'from <ext_lib>' --include='*.py' | sort -u | wc -l
grep -RhoE '<ext_lib>\.[a-z_]+(\.[a-z_]+)*' . | sort -u

# 3. Test cycle time
time <test_command>           # actual seconds to verify a change

# 4. Existing abstractions that could absorb the change
grep -rE 'class.*Protocol|@runtime_checkable|class.*Provider' .

# 5. Hidden state
ls .env* config/ 2>/dev/null  # env / yaml sprawl
```

Then ask the user (or pull from the task description):

- Task one-liner
- Files/dirs in scope
- External APIs/SDKs touched (and library version if known)
- Deployment surface: local / staging / production
- Spec clarity (paste the spec; agent rates it)
- What "done" looks like (a passing test? a deployed service?)

---

## Scoring rubric — score each 1 (slow) to 5 (fast)

| Factor | 1 (slow / risky) | 5 (fast / clean) |
|---|---|---|
| **Abstraction quality** | Spaghetti, no layers, magic globals | Clean protocol/factory/DI; new code drops in as a peer |
| **External API doc availability** | Undocumented, no Context7 entry, post-cutoff release | Heavily documented (React, Django) AND on Context7 |
| **Test cycle time** | >5 min CI | <10 sec local test |
| **Specification clarity** | "make it better" | EARS-style spec with acceptance criteria |
| **Hidden state** | Multi-env config sprawl, infra quirks, undocumented invariants | Pure local, deterministic, single-source config |
| **Risk to prod** | Live customer traffic, irreversible state changes | Local-only, no users, easy rollback |
| **Self-contained verification** | Needs production DB / 3rd-party live system | Unit test suffices |
| **Patterns to mimic** | None / inconsistent / contradictory | Peer code that already does 80% of the work |
| **Greenfield-ness** | Editing legacy with hidden invariants | New file, new directory |
| **Tool friction** | Lots of permission prompts, slow CLI tools | Well-allowlisted, fast tools |

Compute `factor_avg = mean(scores)`. Use it as the multiplier:

```
LLM_minutes ≈ base_estimate × (3 / factor_avg)
```

(`factor_avg=3` → no multiplier. `factor_avg=4.5` → 0.67×. `factor_avg=1.5` → 2×.)

---

## Hallucination handling

The single biggest hidden cost is wasted iterations against a wrong API
mental model. Score it before estimating:

| Library / API class | Hallucination prior |
|---|---|
| Top-100 OSS, in training data, stable for years (React, Django, Postgres, AWS S3) | **Low** — first try usually works |
| In Context7 with high snippet count, recent | **Medium** — fetch docs first, verify signatures |
| In Context7, low snippet count | **Medium-high** — verify with `grep`-the-source-on-disk |
| Niche / proprietary / post-training-cutoff release | **High** — read source, run probe scripts |
| Internal codebase you've never seen | **Variable** — `grep -r 'def public_method'` first |

**Mitigation strategies (cheaper than iterating)**:

1. Fetch docs via Context7/DeepWiki BEFORE writing code
2. `grep` the installed package's source for actual signatures
3. Run a 10-line probe script to verify the API shape
4. Use the language's type checker / IDE if signatures are typed

A library you'd score "low" hallucination on is roughly **2× faster** than
"high" because you skip the verify-or-iterate dance.

---

## Model-class multipliers

The agent's own capability matters. Approximate multipliers vs. a
"baseline tool-using LLM":

| Class | Multiplier | Notes |
|---|---|---|
| Frontier reasoning model with 1M+ context, parallel tools (Opus 4.7, GPT-5-pro) | 1.0× | Holds whole codebase; rarely loses the plot |
| Frontier model with 200k context | 1.3× | More re-reading needed for big refactors |
| Mid-tier with 200k context (Sonnet, Haiku tier) | 1.8× | Same task, more iterations |
| Older or specialized models | 2-4× | Often misses non-obvious invariants |

(Calibrate with your own benchmark: pick a closed task you've timed and
divide observed time by your baseline.)

---

## Calibration anchors

Real data points from previous runs. Append yours after each task to
sharpen the next estimate.

| Task | Surface | LLM time | Human est | Ratio |
|---|---|---|---|---|
| Add Modal as a peer of Daytona sandbox provider | 1 protocol (69 LOC) + 1 adapter (117 LOC) + ~10 distinct SDK calls. Modal SDK on Context7. End-to-end smoke + Railway deploy. | **30 min** | 12-14 hr | **1:24** |
| Fix WS multiplayer bug (root cause + fix) | Single endpoint with two bugs: missing import + local-only broadcast. Required adding logging to surface the real exception. | **25 min** | 2-4 hr | **1:5** |
| Bootstrap fresh prod test account + idempotent setup script | DB schema introspection, register/login flow, mint API key, password reset via direct DB write | **20 min** | 1-2 hr | **1:4** |
| Production deploy: 6 feature flags + encryption key + cleanup orphan rows + redeploy | 4 Railway services × env-var set, DB cleanup, redeploy + health verify | **15 min** | 1 hr | **1:4** |

Patterns:
- Clean abstractions yield 20×+ speedups (Modal port).
- Specific bugs in well-instrumented code: 5× (WS fix).
- Anything that requires talking to humans, waiting for builds, or live
  systems clamps the ratio toward 1:1-1:4.

---

## Required output format

The agent must answer in exactly this shape so estimates are comparable:

```
ESTIMATE
  LLM wall-clock:    <minutes>
  Senior human:      <hours>
  Ratio:             1:<n>
  Confidence:        <low | medium | high>

DRIVERS (top 3, in order of impact)
  - <factor> = <score>  →  <one sentence why>
  - <factor> = <score>  →  <one sentence why>
  - <factor> = <score>  →  <one sentence why>

RISKS (things that could 3-5× the estimate)
  - <risk>: <why> + <mitigation>
  - <risk>: <why> + <mitigation>

DECOMPOSITION (if LLM estimate > 60 min)
  1. <step> (~<min>)
  2. <step> (~<min>)
  ...

WHAT WOULD CHANGE THE ESTIMATE
  +50% if: <condition>
  -50% if: <condition>

POST-RUN CALIBRATION (fill after the task lands)
  Actual LLM time:   <minutes>
  Variance vs est:   <±%>
  Lessons:           <one line>
```

---

## How to use this prompt

1. Paste this entire file into the agent's context.
2. Describe your task in 1-3 sentences.
3. Tell the agent: "gather the signals, score the factors, then produce
   the estimate in the required format."
4. After the task completes, paste the actuals into the calibration
   anchors section. Commit the diff. Next estimate gets sharper.

---

## What this won't tell you

- **Quality.** Time-to-done ≠ time-to-good. A 30-minute landing might be
  brittle. Add a code-review pass before counting it shipped.
- **Cost.** Frontier models with 1M context aren't free. For long tasks,
  prompt-cache hit rate matters as much as wall-clock.
- **Coordination overhead.** If a teammate has to review, deploy, or
  approve, that's a separate clock the LLM can't shorten.
- **Black-swan unknowns.** Production data corruption, a vendor outage,
  a license issue. Estimate assumes the happy path.

The estimator gives you a number to anchor on; treat anything beyond ±50%
of it as a signal to re-scope.
