#!/usr/bin/env bash
# OmoiOS sandbox bootstrap.
#
# Runs before OpenCode/OmO starts. Responsibilities:
#   1. If SESSION_TOKEN + BROKER_URL + OMOIOS_CREDENTIAL_ALIASES are set,
#      fetch each alias from the broker and render auth.json.
#   2. Render opencode.json and oh-my-openagent.jsonc from env templates.
#   3. Start the VNC stack (Xvfb + fluxbox + x11vnc + websockify/noVNC).
#   4. exec whatever command the caller passed (default: sleep infinity).
#
# Env contract:
#   SESSION_TOKEN                 — sess_tok_... (broker bearer)
#   BROKER_URL                    — e.g. https://api.omoios.dev/broker
#   OMOIOS_CREDENTIAL_ALIASES     — comma-separated: "anthropic,openrouter,github"
#   OMOIOS_OPENCODE_CONFIG        — JSON content for opencode.json (optional)
#   OMOIOS_OMO_CONFIG             — JSONC content for oh-my-openagent.jsonc (optional)
#   DISABLE_VNC                   — "1" to skip VNC startup

set -euo pipefail
log() { printf '[bootstrap %s] %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; }

: "${HOME:?HOME must be set}"
OPENCODE_CONFIG_DIR="$HOME/.config/opencode"
OPENCODE_DATA_DIR="$HOME/.local/share/opencode"
mkdir -p "$OPENCODE_CONFIG_DIR" "$OPENCODE_DATA_DIR"
chmod 0700 "$OPENCODE_DATA_DIR"

# ─── 1. auth.json from the credential broker ──────────────────────────────────
AUTH_JSON_PATH="$OPENCODE_DATA_DIR/auth.json"

# Fetch a URL with 3 retries and exponential backoff (1s, 2s, 4s).
# Returns the response body on stdout, or exits 1 on failure.
fetch_with_retry() {
  local url="$1"
  local attempt=1
  local max_attempts=3
  local delay=1

  while [[ $attempt -le $max_attempts ]]; do
    if resp="$(curl -fsS \
        --max-time 10 \
        -H "Authorization: Bearer $SESSION_TOKEN" \
        "$url" 2>/dev/null)"; then
      printf '%s\n' "$resp"
      return 0
    fi

    if [[ $attempt -eq $max_attempts ]]; then
      return 1
    fi

    log "  retry $attempt/$max_attempts for $url (backing off ${delay}s)"
    sleep "$delay"
    delay=$((delay * 2))
    attempt=$((attempt + 1))
  done

  return 1
}

# Render a broker credential response into an OpenCode auth.json entry.
# Branches on the broker response "kind" field.
render_auth_entry() {
  local alias="$1"
  local resp="$2"
  local kind
  kind="$(jq -r '.kind // empty' <<< "$resp")"

  case "$kind" in
    bearer_secret)
      local value
      value="$(jq -r '.value // empty' <<< "$resp")"
      jq -n --arg v "$value" '{type: "api", key: $v}'
      ;;
    user_oauth)
      local access_token refresh_token expires_at
      access_token="$(jq -r '.access_token // empty' <<< "$resp")"
      refresh_token="$(jq -r '.refresh_token // empty' <<< "$resp")"
      expires_at="$(jq -r '.expires_at // empty' <<< "$resp")"
      jq -n \
        --arg a "$access_token" \
        --arg r "$refresh_token" \
        --argjson e "${expires_at:-0}" \
        '{type: "oauth", access: $a, refresh: $r, expires: $e}'
      ;;
    github_app)
      local token expires_at
      token="$(jq -r '.token // empty' <<< "$resp")"
      expires_at="$(jq -r '.expires_at // empty' <<< "$resp")"
      jq -n \
        --arg a "$token" \
        --argjson e "${expires_at:-0}" \
        '{type: "oauth", access: $a, expires: $e}'
      ;;
    *)
      log "  ✗ $alias (unknown broker kind: $kind)"
      return 1
      ;;
  esac
}

if [[ -n "${SESSION_TOKEN:-}" && -n "${BROKER_URL:-}" && -n "${OMOIOS_CREDENTIAL_ALIASES:-}" ]]; then
  log "minting auth.json via broker (aliases=$OMOIOS_CREDENTIAL_ALIASES)"
  auth_json="{}"
  IFS=',' read -ra aliases <<< "$OMOIOS_CREDENTIAL_ALIASES"
  for alias in "${aliases[@]}"; do
    alias="$(echo "$alias" | tr -d '[:space:]')"
    [[ -z "$alias" ]] && continue

    resp=""
    if ! resp="$(fetch_with_retry "$BROKER_URL/creds/$alias")"; then
      log "  ✗ $alias (broker failed after retries)"
      exit 1
    fi

    entry=""
    if ! entry="$(render_auth_entry "$alias" "$resp")"; then
      log "  ✗ $alias (failed to render auth entry)"
      exit 1
    fi

    auth_json="$(jq --arg a "$alias" --argjson e "$entry" '. + {($a): $e}' <<< "$auth_json")"
    log "  ✓ $alias"
  done

  # Validate: every entry must have type "api" or "oauth"
  if ! jq -e 'to_entries | all(.value.type == "api" or .value.type == "oauth")' <<< "$auth_json" >/dev/null 2>&1; then
    log "auth.json validation failed: every entry must have type \"api\" or \"oauth\""
    exit 1
  fi

  printf '%s\n' "$auth_json" > "$AUTH_JSON_PATH"
  chmod 0600 "$AUTH_JSON_PATH"
  log "wrote $AUTH_JSON_PATH (mode 0600)"
else
  log "skipping auth.json: broker env not set"
fi

# ─── 2. opencode.json + oh-my-openagent.jsonc from env templates ──────────────
if [[ -n "${OMOIOS_OPENCODE_CONFIG:-}" ]]; then
  printf '%s\n' "$OMOIOS_OPENCODE_CONFIG" > "$OPENCODE_CONFIG_DIR/opencode.json"
  log "wrote $OPENCODE_CONFIG_DIR/opencode.json"
fi
if [[ -n "${OMOIOS_OMO_CONFIG:-}" ]]; then
  printf '%s\n' "$OMOIOS_OMO_CONFIG" > "$OPENCODE_CONFIG_DIR/oh-my-openagent.jsonc"
  log "wrote $OPENCODE_CONFIG_DIR/oh-my-openagent.jsonc"
fi

# ─── 3. Egress proxy ──────────────────────────────────────────────────────────
# Starts the allowlist-based egress proxy before any outbound traffic occurs.
if [[ -n "${OMOIOS_EGRESS_ALLOWED_HOSTS:-}" ]]; then
  if ! command -v omoios-egress-proxy >/dev/null 2>&1; then
    log "egress proxy binary missing; exiting"
    exit 1
  fi
  log "starting egress proxy (allowlist=$OMOIOS_EGRESS_ALLOWED_HOSTS)"
  PORT=8888 ALLOWED_HOSTS="$OMOIOS_EGRESS_ALLOWED_HOSTS" \
    /usr/local/bin/omoios-egress-proxy >/tmp/omoios-egress-proxy.log 2>&1 &
  EGRESS_PID=$!
  # Liveness gate: wait up to 5s
  for _ in 1 2 3 4 5; do
    if curl -fsS -m 1 -x http://127.0.0.1:8888 https://api.github.com/zen >/dev/null 2>&1; then
      log "egress proxy ready (pid=$EGRESS_PID)"
      break
    fi
    sleep 1
  done
  if ! kill -0 "$EGRESS_PID" 2>/dev/null; then
    log "egress proxy crashed; exiting"
    exit 1
  fi
fi

# ─── 4. VNC stack ─────────────────────────────────────────────────────────────
# Uses the xvfb + x11vnc + novnc + xfce4 stack shipped in daytonaio/sandbox.
if [[ "${DISABLE_VNC:-0}" != "1" ]]; then
  export DISPLAY="${DISPLAY:-:0}"
  log "starting VNC stack on $DISPLAY (noVNC on ${NOVNC_PORT:-6080}, raw VNC on ${VNC_PORT:-5900})"
  # Xvfb: headless X server on :0.
  Xvfb "$DISPLAY" -screen 0 "${VNC_RESOLUTION:-1920x1080x24}" -nolisten tcp &
  sleep 1
  # D-Bus session bus (xfce4 needs it to register services).
  if command -v dbus-launch >/dev/null; then
    eval "$(dbus-launch --sh-syntax)" >/dev/null 2>&1 || true
  fi
  # xfce4: full desktop environment (already in the base image).
  startxfce4 >/dev/null 2>&1 &
  # x11vnc: bridges X to VNC RFB protocol.
  x11vnc -display "$DISPLAY" -forever -shared -nopw \
         -rfbport "${VNC_PORT:-5900}" -quiet >/dev/null 2>&1 &
  # noVNC: browser-accessible VNC over WebSocket.
  websockify --web=/usr/share/novnc "${NOVNC_PORT:-6080}" "localhost:${VNC_PORT:-5900}" \
    >/dev/null 2>&1 &
  log "VNC stack launched in background (xfce4 + x11vnc + noVNC)"
fi

# ─── 5. hand off ──────────────────────────────────────────────────────────────
if [[ $# -gt 0 ]]; then
  log "exec: $*"
  exec "$@"
else
  log "no command given; keeping container alive (sleep infinity)"
  exec sleep infinity
fi
