# Next Session — Start Here

**Single goal:** make `agent_proof_of_life.py` exit 0 with all 7 steps green.
The lane is **Fireworks Kimi K2.5 Turbo only** (no Z.AI, no GLM, no OpenAI).

---

## 0 · Read in this order (5 min)

1. `MEMORY.md` (auto-loaded) — scan the bullets at the top of every memory.
2. **`docs/poof-cheatsheet.md`** — one-page reference for tmux + `just poof-*` commands.
3. This file.

That's it. Don't read everything else unless you hit a wall — the cheatsheet covers 95%.

---

## 1 · State of the world (where we left off)

- A `poof` tmux session may already be running (4 windows: `api`, `poof`, `logs`, `probes`).
  Check with `just poof-status`. If it's down, `just poof-start`.
- Local API runs on `:18000`, points at the **production Railway DB**.
- Fireworks-only: `LLM_*` env vars on Railway AND in the local launcher are pinned to
  `fw_WZk1n8qVwHxTeNPK8JWZ6Y` / `https://api.fireworks.ai/inference/v1` /
  `accounts/fireworks/routers/kimi-k2p5-turbo`.
- Helper scripts: `scripts/agent_proof_of_life.py`, `scripts/poof_probes.sh`,
  `scripts/poof_tmux.sh`, `scripts/poof_watch.sh`, `scripts/modal_sandbox_smoke.py`,
  `scripts/local_opencode_llm_smoke.sh`.
- `Justfile` has 17 `just poof-*` recipes — see `just --list | grep poof`.

---

## 2 · The exact commands to run (in order)

```bash
# 1. Make sure the session is up + healthy
just poof-status

# 2. Reload (kill + start) if you want a clean uvicorn against the latest code
just poof-reload

# 3. Watch what's happening (opens a NEW Terminal window with a banner;
#    detach with Ctrl-B then D)
just poof

# 4. Kick off the proof-of-life — fresh state, all 7 steps
just poof-run-fresh

# 5. Snapshot output without attaching
just poof-snap            # poof window
just poof-snap logs       # uvicorn log

# 6. If step 7 hangs or fails, layered probes pinpoint the broken layer
just poof-probes

# 7. Inspect the events table for the cached session id
just poof-events
```

---

## 3 · Success criteria (what "done" looks like)

- The script prints `✓ all done — state cached in .sisyphus/poof.state.json`.
- `.sisyphus/evidence/poof-*.json` shows `final_status: "succeeded"` and `agent_msg_count >= 1`.
- `/tmp/uvicorn-prod.log` contains a `chat responder emitted agent reply` line for the new session id, with no follow-on warnings.

If those three hit: commit `scripts/agent_proof_of_life.py` plus the evidence file, mark task #8 completed, then move on to the queued work in `MEMORY.md` → `feedback_terminal_first.md`.

---

## 4 · If you get stuck

| Symptom | First move |
|---|---|
| Step 7 hangs, no agent message | `just poof-snap logs` and grep for `chat responder` — most likely cause is asyncio GC (already fixed, but verify) or LLM endpoint timeout |
| `httpx.ReadTimeout` in chat_responder | The lane drifted off Fireworks. Check `/tmp/poof-tmux.env` and Railway `LLM_BASE_URL` — both must be `https://api.fireworks.ai/inference/v1` |
| Step 7 has agent message but `final.status != "succeeded"` | `chat_responder` failed to call `update_task_status` — read the traceback in `/tmp/uvicorn-prod.log` |
| `ProviderModelNotFoundError` (OpenCode side) | OpenCode side, not chat_responder. Use built-in `fireworks-ai` provider id (already in renderer) |
| Tmux confuses you | `just poof-watch` opens a new Terminal with a giant banner showing `Ctrl-B then D` to detach. Or just close the window |
| You can't find a process | `ps aux \| grep -E 'uvicorn\|agent_proof'` |

---

## 5 · What's queued AFTER proof-of-life is green

Per `MEMORY.md` index — strict order, no skipping:

1. **Wire Modal as the actual agent runtime.** `sandboxed_agent.py` is Daytona-only.
   Build a `ModalSandboxedAgent` that uses the `modal_sandbox_smoke.py` patterns we
   already proved (bake opencode in image, `< /dev/null`, `timeout 60`). Then chat_responder
   can route through it instead of the direct LLM fallback, and Kimi actually drives
   the answer.
2. **Decompose the proof-of-life into per-prior probes** under `scripts/poof/` with a
   shared `PoofSettings(OmoiBaseSettings)`. See
   `project_poof_settings_and_decomposition.md`.
3. **Terminal-first CLIs** — `omoios providers add/list`, `omoios auth github` (device-code),
   `omoios signup`. See `feedback_terminal_first.md`.

Don't start any of these until proof-of-life is green and committed.

---

## 6 · Quick orientation

- Repo root: `/Users/kevinhill/Coding/Experiments/senior-sandbox/omoi_os`
- Cheatsheet: `docs/poof-cheatsheet.md`
- Active task: `#8` in TaskList — "Verify proof-of-life all 7 steps PASS end-to-end"
- All `just poof-*` recipes: `just --list | grep poof`
- All memories: `MEMORY.md`
