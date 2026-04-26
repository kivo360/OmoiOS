#!/usr/bin/env bash
# Spin up a `poof` tmux session with everything wired:
#   window 0 (api)     — local uvicorn on :18000, prod DB, prod LLM_*
#   window 1 (poof)    — shell ready to run agent_proof_of_life.py
#   window 2 (logs)    — tail of /tmp/uvicorn-prod.log
#   window 3 (probes)  — shell ready for ./scripts/poof_probes.sh + psql
#
# Usage:
#   ./scripts/poof_tmux.sh start    # boot the session (idempotent)
#   ./scripts/poof_tmux.sh attach   # attach to it
#   ./scripts/poof_tmux.sh kill     # tear it down
#   ./scripts/poof_tmux.sh status   # show running windows + uvicorn health

set -euo pipefail

SESSION="poof"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG=/tmp/uvicorn-prod.log

cmd_status() {
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "  ✓ session '$SESSION' running"
    tmux list-windows -t "$SESSION" -F '    [#{window_index}] #{window_name}'
  else
    echo "  · session '$SESSION' not running"
  fi
  api_code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 http://localhost:18000/health 2>/dev/null || echo "000")
  echo "  api: http://localhost:18000/health → $api_code"
}

cmd_kill() {
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  pkill -f "agent_proof_of_life\|uvicorn omoi_os" 2>/dev/null || true
  echo "  ✓ killed"
}

cmd_start() {
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "  · session '$SESSION' already running"
    cmd_status
    echo ""
    echo "  attach with:  tmux attach -t $SESSION"
    return 0
  fi

  # Pre-fetch DB URL from railway. Everything else is HARDCODED to
  # Fireworks-only — we don't want chat_responder hitting Z.AI/GLM and
  # we don't want any OpenCode/Modal config drifting to a different
  # provider. Single Fireworks Kimi K2.5 Turbo lane, end-to-end.
  echo "  ▸ fetching railway secrets…"
  RW=$(railway variables --kv 2>/dev/null)
  DB_URL=$(echo "$RW" | grep '^DATABASE_URL=' | cut -d= -f2-)

  # Fireworks-only configuration (per user preference 2026-04-26).
  FW_KEY="fw_WZk1n8qVwHxTeNPK8JWZ6Y"
  LLM_KEY="$FW_KEY"
  LLM_URL="https://api.fireworks.ai/inference/v1"
  # chat_responder.py calls Fireworks directly via OpenAI-compatible
  # API, so the model id is the RAW Fireworks id (no provider prefix).
  LLM_MODEL="accounts/fireworks/routers/kimi-k2p5-turbo"

  if [[ -z "$DB_URL" ]]; then
    echo "  ✗ couldn't load DATABASE_URL from railway"
    exit 1
  fi
  : > "$LOG"

  # Build the env-prelude that every window inherits via .smoke.env file.
  ENV_FILE="/tmp/poof-tmux.env"
  cat > "$ENV_FILE" <<EOF
export DATABASE_URL="$DB_URL"
export FIREWORKS_API_KEY="$FW_KEY"
export LLM_API_KEY="$LLM_KEY"
export LLM_BASE_URL="$LLM_URL"
export LLM_MODEL="$LLM_MODEL"
export OMOIOS_API_BASE_URL="http://localhost:18000"
set -a
source "$REPO/backend/.env" 2>/dev/null || true
source "$REPO/backend/.env.local" 2>/dev/null || true
source "$REPO/backend/.env.smoke-test" 2>/dev/null || true
# These five MUST come AFTER .env.smoke-test sourcing — that file overrides
# OMOIOS_API_BASE_URL with the prod URL, but we want to hit the local API.
export DATABASE_URL="$DB_URL"
export FIREWORKS_API_KEY="$FW_KEY"
export LLM_API_KEY="$LLM_KEY"
export LLM_BASE_URL="$LLM_URL"
export LLM_MODEL="$LLM_MODEL"
export OMOIOS_API_BASE_URL="http://localhost:18000"
set +a
cd "$REPO"
echo "  ✓ env loaded — \$OMOIOS_API_BASE_URL = \$OMOIOS_API_BASE_URL"
EOF

  # Window 0: api (uvicorn)
  # --reload + --reload-dir omoi_os: watch the backend source tree only so
  # module-level changes (e.g. observability init, new middleware) pick up
  # without a manual restart. Scoping the watcher to omoi_os keeps the .venv
  # (tens of thousands of files) and tests/ out of the FS-event firehose.
  tmux new-session -d -s "$SESSION" -n api -c "$REPO" \
    "bash -c 'source $ENV_FILE && cd backend && uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 18000 --no-access-log --reload --reload-dir omoi_os 2>&1 | tee $LOG; exec bash'"

  # Window 1: poof (script ready, prints help)
  tmux new-window -t "$SESSION:" -n poof -c "$REPO" \
    "bash -c 'source $ENV_FILE; echo; echo \"  ready. run:  .venv/bin/python scripts/agent_proof_of_life.py\"; echo \"            or: rm -f .sisyphus/poof.state.json && .venv/bin/python scripts/agent_proof_of_life.py\"; exec bash'"

  # Window 2: logs (tail uvicorn)
  tmux new-window -t "$SESSION:" -n logs -c "$REPO" \
    "bash -c 'tail -F $LOG'"

  # Window 3: probes (shell w/ env, ready for ./scripts/poof_probes.sh)
  tmux new-window -t "$SESSION:" -n probes -c "$REPO" \
    "bash -c 'source $ENV_FILE; echo; echo \"  ready. SESSION_ID=<id> ./scripts/poof_probes.sh\"; echo \"  or psql \\\"\$DATABASE_URL\\\" for ad-hoc queries\"; exec bash'"

  tmux select-window -t "$SESSION":1

  echo "  ✓ started session '$SESSION'"
  echo ""
  echo "  attach:        tmux attach -t $SESSION"
  echo "  switch window: ctrl-b 0|1|2|3   (api|poof|logs|probes)"
  echo "  detach:        ctrl-b d"
  echo "  status:        ./scripts/poof_tmux.sh status"
  echo "  kill:          ./scripts/poof_tmux.sh kill"
}

case "${1:-attach}" in
  start)  cmd_start ;;
  attach) tmux attach -t "$SESSION" ;;
  kill)   cmd_kill ;;
  status) cmd_status ;;
  *)      echo "usage: $0 {start|attach|kill|status}"; exit 1 ;;
esac
