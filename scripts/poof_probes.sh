#!/usr/bin/env bash
# Per-layer probes for the proof-of-life flow. Each probe targets ONE
# specific question — run them in order; the first FAIL pinpoints the
# broken layer instead of leaving you guessing.
#
# Usage:
#   SESSION_ID=04465193-... DATABASE_URL=postgresql://... ./scripts/poof_probes.sh
#   # or pass on stdin: jq '.session_id' .sisyphus/poof.state.json | xargs -I{} env SESSION_ID={} ./scripts/poof_probes.sh
#
# Each probe:
#   1. echoes a one-line label
#   2. exits 0 (✓) or 1 (✗) per probe; full script exits at first failure

set -euo pipefail

SESSION_ID="${SESSION_ID:?SESSION_ID is required}"
DATABASE_URL="${DATABASE_URL:?DATABASE_URL is required}"
API_BASE_URL="${OMOIOS_API_BASE_URL:-http://localhost:18000}"
API_KEY="${OMOIOS_PLATFORM_API_KEY:-}"
PSQL_URL="$(echo "$DATABASE_URL" | sed 's/postgresql+psycopg/postgresql/')"

ok()   { printf '  \033[32m✓\033[0m %-45s %s\n' "$1" "$2"; }
fail() { printf '  \033[31m✗\033[0m %-45s %s\n' "$1" "$2"; exit 1; }
note() { printf '  \033[90m·\033[0m %-45s %s\n' "$1" "$2"; }

# ── 1. Session row exists ──────────────────────────────────────────────────
status=$(psql "$PSQL_URL" -tA -c \
  "SELECT status FROM tasks WHERE id = '$SESSION_ID'") || \
  fail "session row in DB" "psql failed"
[[ -n "$status" ]] || fail "session row in DB" "no row for $SESSION_ID"
ok "session row in DB" "status=$status"

# ── 2. session.created event present ──────────────────────────────────────
created_seq=$(psql "$PSQL_URL" -tA -c \
  "SELECT seq FROM events WHERE entity_id = '$SESSION_ID' AND event_type = 'session.created'")
[[ -n "$created_seq" ]] || fail "session.created event" "missing"
ok "session.created event" "seq=$created_seq"

# ── 3. chat_responder fired (any session.message from agent) ──────────────
agent_msg_count=$(psql "$PSQL_URL" -tA -c \
  "SELECT COUNT(*) FROM events WHERE entity_id = '$SESSION_ID' AND event_type = 'session.message' AND actor = 'agent'")
if [[ "$agent_msg_count" -lt 1 ]]; then
  # Show all events to help diagnose
  echo
  echo "  --- events for $SESSION_ID ---"
  psql "$PSQL_URL" -c \
    "SELECT seq, event_type, actor, LEFT(payload::text, 80) FROM events WHERE entity_id = '$SESSION_ID' ORDER BY seq" || true
  fail "chat_responder emitted agent message" "0 agent messages — likely asyncio task GC or LLM call failed"
fi
ok "chat_responder emitted agent message" "$agent_msg_count message(s)"

# ── 4. LLM call recorded in API logs (best-effort) ────────────────────────
if [[ -f /tmp/uvicorn-prod.log ]]; then
  llm_hits=$(grep -c "chat responder emitted agent reply" /tmp/uvicorn-prod.log 2>/dev/null || echo 0)
  note "uvicorn 'emitted agent reply' log lines" "$llm_hits"
  llm_failures=$(grep -c "chat responder failed" /tmp/uvicorn-prod.log 2>/dev/null || echo 0)
  if [[ "$llm_failures" -gt 0 ]]; then
    note "uvicorn 'chat responder failed' lines" "$llm_failures (recent below)"
    grep "chat responder failed" /tmp/uvicorn-prod.log | tail -2 | sed 's/^/      /'
  fi
fi

# ── 5. Task transitioned to completed ─────────────────────────────────────
final_status=$(psql "$PSQL_URL" -tA -c \
  "SELECT status FROM tasks WHERE id = '$SESSION_ID'")
case "$final_status" in
  completed) ok "task.status transitioned" "$final_status" ;;
  failed|cancelled) fail "task.status transitioned" "$final_status (terminal but not success)" ;;
  *) fail "task.status transitioned" "$final_status (still non-terminal — chat_responder didn't call update_task_status)" ;;
esac

# ── 6. session.succeeded envelope written ─────────────────────────────────
succeeded_seq=$(psql "$PSQL_URL" -tA -c \
  "SELECT seq FROM events WHERE entity_id = '$SESSION_ID' AND event_type = 'session.succeeded'")
[[ -n "$succeeded_seq" ]] || \
  fail "session.succeeded envelope" "missing — task_queue's status→event mapping broken or envelope write failed"
ok "session.succeeded envelope" "seq=$succeeded_seq"

# ── 7. SSE stream actually delivers terminal (live curl) ──────────────────
if [[ -n "$API_KEY" ]]; then
  echo
  echo "  --- SSE stream sample (5s budget) ---"
  timeout 5 curl -sN -H "Authorization: Bearer $API_KEY" -H "Accept: text/event-stream" \
    "$API_BASE_URL/api/v1/sessions/$SESSION_ID/events" 2>&1 | head -20 | sed 's/^/      /' || true
fi

echo
echo "  ✓ all probes passed for $SESSION_ID"
