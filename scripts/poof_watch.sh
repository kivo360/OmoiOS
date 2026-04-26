#!/usr/bin/env bash
# Open the `poof` tmux session in a NEW Terminal window with a giant
# "how to exit" banner so you don't get stuck. Detach is `Ctrl-B then D`.
#
# Usage:
#   ./scripts/poof_watch.sh              # opens new Terminal.app window
#   ./scripts/poof_watch.sh --inline     # attach in current terminal
#   ./scripts/poof_watch.sh --kill       # tear down the whole session
#
# What this is NOT for: kicking off scripts. Use the management prompt
# in your other terminal / coding agent. This window is just for
# eyeballing the server and pressing Ctrl-C if you want to stop it.

set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

show_banner_and_attach() {
  clear
  cat <<'BANNER'

  ┌─────────────────────────────────────────────────────────────────┐
  │  poof tmux session  ·  local API + prod DB  ·  Fireworks-only   │
  ├─────────────────────────────────────────────────────────────────┤
  │                                                                 │
  │  Windows (switch with  Ctrl-B then a number):                   │
  │     Ctrl-B 0  →  api     (uvicorn server output)                │
  │     Ctrl-B 1  →  poof    (run scripts here)                     │
  │     Ctrl-B 2  →  logs    (tail -F /tmp/uvicorn-prod.log)        │
  │     Ctrl-B 3  →  probes  (psql + poof_probes.sh)                │
  │                                                                 │
  │  ╔═══════════════════════════════════════════════════════════╗  │
  │  ║  TO LEAVE WITHOUT KILLING ANYTHING:                       ║  │
  │  ║      Ctrl-B   then   D                                    ║  │
  │  ║  (everything keeps running in the background)             ║  │
  │  ╚═══════════════════════════════════════════════════════════╝  │
  │                                                                 │
  │  TO STOP THE SERVER:                                            │
  │     Ctrl-B 0     (jump to api window)                           │
  │     Ctrl-C       (interrupts uvicorn)                           │
  │     Ctrl-B D     (then detach)                                  │
  │                                                                 │
  │  TO KILL EVERYTHING (from outside this window):                 │
  │     ./scripts/poof_tmux.sh kill                                 │
  │                                                                 │
  │  IF YOU GET STUCK:                                              │
  │     Just close this Terminal window (Cmd-W). The tmux           │
  │     session keeps running; rerun ./scripts/poof_watch.sh        │
  │     to re-attach.                                               │
  │                                                                 │
  └─────────────────────────────────────────────────────────────────┘

BANNER
  printf "  Press ENTER to attach (or Ctrl-C to bail)… "
  read -r _ || true
  tmux attach -t poof || true
  clear
  cat <<'AFTER'

  ✓ Detached from poof. The session is still running.

      re-attach :  ./scripts/poof_watch.sh
      tear down :  ./scripts/poof_tmux.sh kill
      status    :  ./scripts/poof_tmux.sh status

  This Terminal window is yours — close it whenever.
AFTER
  # Drop into a usable shell so the window doesn't auto-close.
  exec "${SHELL:-/bin/bash}" -i
}

ensure_session() {
  if ! tmux has-session -t poof 2>/dev/null; then
    echo "  · poof session not running — starting it…"
    "$REPO/scripts/poof_tmux.sh" start
  fi
}

case "${1:-}" in
  --inner)
    show_banner_and_attach
    ;;
  --inline)
    ensure_session
    show_banner_and_attach
    ;;
  --kill)
    "$REPO/scripts/poof_tmux.sh" kill
    ;;
  "")
    ensure_session
    # Open in macOS Terminal.app via osascript.
    osascript <<EOF
tell application "Terminal"
  do script "exec bash '$REPO/scripts/poof_watch.sh' --inner"
  activate
end tell
EOF
    echo "  ✓ opened poof viewer in a new Terminal window"
    ;;
  *)
    echo "usage: $0 [--inline|--kill]"
    echo "  (no flag)   open in a new Terminal.app window (default)"
    echo "  --inline    attach in the current terminal"
    echo "  --kill      tear down the whole session"
    exit 1
    ;;
esac
