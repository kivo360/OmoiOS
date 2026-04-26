#!/usr/bin/env bash
# Replicates the EXACT opencode-LLM sequence the Modal sandbox runs,
# but in a fully isolated XDG_CONFIG_HOME / XDG_DATA_HOME so it doesn't
# touch your real opencode setup. If this works locally and the
# Modal version doesn't, the bug is sandbox-side (exec semantics,
# stdout capture, install timing). If it fails here, the bug is in
# the commands or configs themselves.
#
# Usage:
#   FIREWORKS_API_KEY=fw_... ./scripts/local_opencode_llm_smoke.sh

set -euo pipefail

WORK="/tmp/opencode-llm-smoke-$$"
CFG="$WORK/config/opencode"
DATA="$WORK/data/opencode"
mkdir -p "$CFG" "$DATA" "$WORK/cwd"

cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

step() { printf '  ▸ %s\n' "$1"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
fail() { printf '  \033[31m✗\033[0m %s\n' "$1"; exit 1; }

[[ -n "${FIREWORKS_API_KEY:-}" ]] || fail "FIREWORKS_API_KEY not set"

step "writing opencode.json"
# EXACT bytes the modal sandbox script writes.
cat > "$CFG/opencode.json" <<'EOF'
{"$schema":"https://opencode.ai/config.json","model":"fireworks-ai/accounts/fireworks/routers/kimi-k2p5-turbo"}
EOF
ok "wrote $CFG/opencode.json ($(wc -c < "$CFG/opencode.json") bytes)"

step "writing auth.json"
printf '{"fireworks-ai":{"type":"api","key":"%s"}}' "$FIREWORKS_API_KEY" > "$DATA/auth.json"
ok "wrote $DATA/auth.json ($(wc -c < "$DATA/auth.json") bytes)"

step "running opencode (timing)"
T0=$(python3 -c 'import time; print(time.time())')
cd "$WORK/cwd"
# Same command the sandbox issues.
set +e
OUT=$(XDG_CONFIG_HOME="$WORK/config" XDG_DATA_HOME="$WORK/data" \
  /Users/kevinhill/.opencode/bin/opencode run \
    --print-logs --log-level ERROR --dangerously-skip-permissions \
    "Reply with exactly: SBOXOK" 2>&1)
RC=$?
set -e
T1=$(python3 -c 'import time; print(time.time())')
ELAPSED=$(python3 -c "print(f'{$T1 - $T0:.1f}')")

if [[ $RC -eq 0 ]] && grep -q "SBOXOK" <<< "$OUT"; then
  ok "opencode run succeeded in ${ELAPSED}s"
  printf '  ─── output ───\n'
  printf '%s\n' "$OUT" | sed 's/^/      /'
else
  printf '  \033[31m✗\033[0m opencode run failed (rc=%s, %ss)\n' "$RC" "$ELAPSED"
  printf '  ─── output ───\n'
  printf '%s\n' "$OUT" | sed 's/^/      /'
  exit 1
fi
