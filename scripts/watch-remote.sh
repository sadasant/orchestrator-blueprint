#!/bin/sh
set -eu

# shellcheck source-path=SCRIPTDIR
. "$(dirname -- "$0")/_runtime.sh"
orchestrator_require git
orchestrator_prepare_state

# Peer routing has separate durable scan/delivery state and acquires this lease.
case "${ORCHESTRATOR_AGENT_ROUTING:-0}" in
  1) exec python3 "$ORCHESTRATOR_REPO/scripts/agent-channel.py" poll ;;
  0) ;;
  *) orchestrator_die "ORCHESTRATOR_AGENT_ROUTING must be 0 or 1" ;;
esac

log() {
  printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >> "$ORCHESTRATOR_LOG_FILE"
}

if ! mkdir "$ORCHESTRATOR_LOCK_DIR" 2>/dev/null; then
  exit 0
fi

cleanup() {
  if ! rmdir "$ORCHESTRATOR_LOCK_DIR" 2>/dev/null; then
    log "warning: watcher could not release its writer lease"
  fi
}
trap cleanup EXIT HUP INT TERM

git -C "$ORCHESTRATOR_REPO" rev-parse --git-dir >/dev/null 2>&1 || {
  log "blocked: repository checkout is unavailable"
  exit 1
}

remote_head() {
  line=$(GIT_TERMINAL_PROMPT=0 git -C "$ORCHESTRATOR_REPO" ls-remote \
    "$ORCHESTRATOR_REMOTE" "refs/heads/$ORCHESTRATOR_BRANCH") || return 1
  sha=${line%%[[:space:]]*}
  orchestrator_valid_sha "$sha" || return 1
  printf '%s\n' "$sha"
}

current_remote=$(remote_head) || {
  log "blocked: remote branch did not resolve to one commit"
  exit 1
}

if [ ! -f "$ORCHESTRATOR_PROCESSED_FILE" ]; then
  orchestrator_atomic_write "$ORCHESTRATOR_PROCESSED_FILE" "$current_remote"
  log "initialized at $current_remote"
  exit 0
fi

processed=$(sed -n '1p' "$ORCHESTRATOR_PROCESSED_FILE")
orchestrator_valid_sha "$processed" || {
  log "blocked: processed-head state is invalid"
  exit 1
}

if [ "$current_remote" = "$processed" ]; then
  rm -f "$ORCHESTRATOR_NOTIFIED_FILE"
  exit 0
fi

if [ -f "$ORCHESTRATOR_NOTIFIED_FILE" ]; then
  notified=$(sed -n '1p' "$ORCHESTRATOR_NOTIFIED_FILE")
  [ "$notified" = "$current_remote" ] && exit 0
fi

log "observed $processed -> $current_remote"
if ! pane_id=$("$ORCHESTRATOR_REPO/scripts/orchestrator-wake.sh" \
  notify "$processed" "$current_remote" 2>> "$ORCHESTRATOR_LOG_FILE"); then
  log "blocked: registered root pane is unavailable or changed"
  exit 0
fi

orchestrator_atomic_write "$ORCHESTRATOR_NOTIFIED_FILE" "$current_remote"
log "notified $pane_id for $current_remote"
