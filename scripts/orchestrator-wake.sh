#!/bin/sh
set -eu

# shellcheck source-path=SCRIPTDIR
. "$(dirname -- "$0")/_runtime.sh"
orchestrator_require git
[ -n "$ORCHESTRATOR_TMUX" ] || orchestrator_die "missing required command: tmux"
orchestrator_prepare_state

reg_version=
reg_pane_id=
reg_pane_pid=
reg_pane_tty=
reg_current_command=
reg_session_id=
reg_window_id=
reg_harness=
reg_registered_at=

valid_agent_name() {
  case "$1" in
    '' | *[!a-z0-9-]*) return 1 ;;
    *) return 0 ;;
  esac
}

load_registration() {
  [ -f "$ORCHESTRATOR_REGISTRATION_FILE" ] || orchestrator_die \
    "root pane is not registered; run $(basename -- "$0") register PANE HARNESS"

  while IFS='=' read -r key value; do
    case "$key" in
      version) reg_version=$value ;;
      pane_id) reg_pane_id=$value ;;
      pane_pid) reg_pane_pid=$value ;;
      pane_tty) reg_pane_tty=$value ;;
      current_command) reg_current_command=$value ;;
      session_id) reg_session_id=$value ;;
      window_id) reg_window_id=$value ;;
      harness) reg_harness=$value ;;
      registered_at) reg_registered_at=$value ;;
      '') ;;
      *) orchestrator_die "unexpected registration field: $key" ;;
    esac
  done < "$ORCHESTRATOR_REGISTRATION_FILE"

  [ "$reg_version" = 1 ] || orchestrator_die "unsupported pane registration version"
  valid_agent_name "$reg_harness" || orchestrator_die "invalid registered harness"
  [ -n "$reg_pane_id" ] && [ -n "$reg_pane_pid" ] && [ -n "$reg_pane_tty" ] || \
    orchestrator_die "incomplete pane registration"
  [ -n "$reg_session_id" ] && [ -n "$reg_window_id" ] && [ -n "$reg_registered_at" ] || \
    orchestrator_die "incomplete tmux registration"
}

registration_marker() {
  printf 'v1 repo=%s harness=%s pane-pid=%s' \
    "$ORCHESTRATOR_REPO_NAME" "$reg_harness" "$reg_pane_pid"
}

validate_registration() {
  load_registration
  fields=$(
    "$ORCHESTRATOR_TMUX" display-message -p -t "$reg_pane_id" \
      '#{pane_id}|#{pane_pid}|#{pane_tty}|#{pane_dead}|#{pane_current_command}|#{session_id}|#{window_id}|#{@orchestrator_root}'
  ) || orchestrator_die "registered tmux pane is unavailable: $reg_pane_id"

  IFS='|' read -r pane_id pane_pid pane_tty pane_dead current_command \
    session_id window_id marker <<EOF
$fields
EOF

  [ "$pane_id" = "$reg_pane_id" ] && [ "$pane_pid" = "$reg_pane_pid" ] && \
    [ "$pane_tty" = "$reg_pane_tty" ] && [ "$pane_dead" = 0 ] && \
    [ "$current_command" = "$reg_current_command" ] && \
    [ "$session_id" = "$reg_session_id" ] && [ "$window_id" = "$reg_window_id" ] || \
    orchestrator_die "registered tmux pane identity changed; register it again"
  [ "$marker" = "$(registration_marker)" ] || \
    orchestrator_die "registered tmux pane marker changed; register it again"
}

register_pane() {
  target=${1:-${TMUX_PANE:-}}
  harness=${2:-}
  [ -n "$target" ] || orchestrator_die "usage: $(basename -- "$0") register PANE HARNESS"
  valid_agent_name "$harness" || orchestrator_die "harness must use lowercase letters, digits, and hyphens"

  fields=$(
    "$ORCHESTRATOR_TMUX" display-message -p -t "$target" \
      '#{pane_id}|#{pane_pid}|#{pane_tty}|#{pane_dead}|#{pane_current_command}|#{session_id}|#{window_id}'
  ) || orchestrator_die "tmux pane is unavailable: $target"

  IFS='|' read -r pane_id pane_pid pane_tty pane_dead current_command \
    session_id window_id <<EOF
$fields
EOF
  [ -n "$pane_id" ] && [ -n "$window_id" ] && [ "$pane_dead" = 0 ] || \
    orchestrator_die "tmux returned an invalid or dead pane"

  reg_pane_id=$pane_id
  reg_pane_pid=$pane_pid
  reg_pane_tty=$pane_tty
  reg_current_command=$current_command
  reg_session_id=$session_id
  reg_window_id=$window_id
  reg_harness=$harness
  reg_registered_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

  "$ORCHESTRATOR_TMUX" set-option -p -t "$reg_pane_id" \
    @orchestrator_root "$(registration_marker)"
  content="version=1
pane_id=$reg_pane_id
pane_pid=$reg_pane_pid
pane_tty=$reg_pane_tty
current_command=$reg_current_command
session_id=$reg_session_id
window_id=$reg_window_id
harness=$reg_harness
registered_at=$reg_registered_at"
  orchestrator_atomic_write "$ORCHESTRATOR_REGISTRATION_FILE" "$content"
  validate_registration
  printf 'registered pane=%s harness=%s pane_pid=%s\n' \
    "$reg_pane_id" "$reg_harness" "$reg_pane_pid"
}

wake_message() {
  previous=$1
  remote=$2
  printf '%s\n' "# orchestrator-wake $remote after $previous: $ORCHESTRATOR_REMOTE/$ORCHESTRATOR_BRANCH advanced. Acquire the repository writer lease, fetch the exact remote range, reconcile collaborator input, record the operator trail, commit, fetch and rebase again, push normally, verify the hosted head, acknowledge the checkpoint, and release the lease."
}

deliver_message() {
  message=$1
  validate_registration
  "$ORCHESTRATOR_TMUX" send-keys -t "$reg_pane_id" -l -- "$message"
  sleep 1
  "$ORCHESTRATOR_TMUX" send-keys -t "$reg_pane_id" C-m
  printf '%s\n' "$reg_pane_id"
}

notify_pane() {
  previous=$1
  remote=$2
  orchestrator_valid_sha "$previous" || orchestrator_die "invalid previous head"
  orchestrator_valid_sha "$remote" || orchestrator_die "invalid remote head"
  deliver_message "$(wake_message "$previous" "$remote")"
}

acknowledge() {
  response=$1
  orchestrator_valid_sha "$response" || orchestrator_die "invalid response head"
  local_head=$(git -C "$ORCHESTRATOR_REPO" rev-parse HEAD)
  tracked_head=$(git -C "$ORCHESTRATOR_REPO" rev-parse \
    "refs/remotes/$ORCHESTRATOR_REMOTE/$ORCHESTRATOR_BRANCH")
  [ "$local_head" = "$response" ] && [ "$tracked_head" = "$response" ] || \
    orchestrator_die "response head does not match local and fetched remote-tracking heads"
  orchestrator_atomic_write "$ORCHESTRATOR_PROCESSED_FILE" "$response"
  rm -f "$ORCHESTRATOR_NOTIFIED_FILE"
  printf 'acknowledged processed head %s\n' "$response"
}

unregister() {
  if [ -f "$ORCHESTRATOR_REGISTRATION_FILE" ]; then
    load_registration
    "$ORCHESTRATOR_TMUX" set-option -p -u -t "$reg_pane_id" \
      @orchestrator_root 2>/dev/null || true
  fi
  rm -f "$ORCHESTRATOR_REGISTRATION_FILE" "$ORCHESTRATOR_NOTIFIED_FILE"
  printf 'unregistered root Orchestrator pane\n'
}

case "${1:-}" in
  register)
    [ "$#" -eq 3 ] || orchestrator_die "usage: $(basename -- "$0") register PANE HARNESS"
    register_pane "$2" "$3"
    ;;
  status)
    validate_registration
    if [ -f "$ORCHESTRATOR_PROCESSED_FILE" ]; then
      processed=$(sed -n '1p' "$ORCHESTRATOR_PROCESSED_FILE")
    else
      processed=none
    fi
    if [ -f "$ORCHESTRATOR_NOTIFIED_FILE" ]; then
      notified=$(sed -n '1p' "$ORCHESTRATOR_NOTIFIED_FILE")
    else
      notified=none
    fi
    printf 'registered pane=%s harness=%s since=%s\n' \
      "$reg_pane_id" "$reg_harness" "$reg_registered_at"
    printf 'processed=%s\nnotified=%s\n' "$processed" "$notified"
    ;;
  dry-run)
    [ "$#" -eq 3 ] || orchestrator_die "usage: $(basename -- "$0") dry-run PREVIOUS REMOTE"
    orchestrator_valid_sha "$2" || orchestrator_die "invalid previous head"
    orchestrator_valid_sha "$3" || orchestrator_die "invalid remote head"
    validate_registration
    printf 'target=%s harness=%s\n' "$reg_pane_id" "$reg_harness"
    wake_message "$2" "$3"
    ;;
  notify)
    [ "$#" -eq 3 ] || orchestrator_die "usage: $(basename -- "$0") notify PREVIOUS REMOTE"
    notify_pane "$2" "$3"
    ;;
  acknowledge)
    [ "$#" -eq 2 ] || orchestrator_die "usage: $(basename -- "$0") acknowledge RESPONSE_HEAD"
    acknowledge "$2"
    ;;
  unregister)
    unregister
    ;;
  *)
    orchestrator_die "usage: $(basename -- "$0") register|status|dry-run|notify|acknowledge|unregister"
    ;;
esac
