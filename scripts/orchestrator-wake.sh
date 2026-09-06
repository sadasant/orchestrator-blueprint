#!/bin/sh
set -eu

# shellcheck source-path=SCRIPTDIR
. "$(dirname -- "$0")/_runtime.sh"
orchestrator_require git
[ -n "$ORCHESTRATOR_TMUX" ] || orchestrator_die "missing required command: tmux"
orchestrator_prepare_state

agent=orchestrator
if [ "${1:-}" = -a ]; then
  [ "$#" -ge 3 ] || orchestrator_die "usage: -a AGENT COMMAND"
  agent=$2
  shift 2
fi
case "$agent" in
  '' | *[!a-z0-9-]* | -*) orchestrator_die "invalid agent name" ;;
esac
mkdir -p "$ORCHESTRATOR_STATE_DIR/panes"
ORCHESTRATOR_REGISTRATION_FILE="$ORCHESTRATOR_STATE_DIR/panes/$agent"

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
    "agent pane is not registered; run $(basename -- "$0") register PANE HARNESS"
  [ ! -L "$ORCHESTRATOR_REGISTRATION_FILE" ] || orchestrator_die "registration must not be a symlink"

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
  if [ -z "$reg_pane_id" ] || [ -z "$reg_pane_pid" ] || [ -z "$reg_pane_tty" ]; then
    orchestrator_die "incomplete pane registration"
  fi
  if [ -z "$reg_session_id" ] || [ -z "$reg_window_id" ] || [ -z "$reg_registered_at" ]; then
    orchestrator_die "incomplete tmux registration"
  fi
}

registration_marker() {
  printf 'v1 repo=%s harness=%s pane-pid=%s' \
    "$ORCHESTRATOR_REPO_NAME" "$reg_harness" "$reg_pane_pid"
  printf ' agent=%s' "$agent"
}

validate_registration() {
  load_registration
  fields=$(
    "$ORCHESTRATOR_TMUX" display-message -p -t "$reg_pane_id" \
      '#{pane_id}|#{pane_pid}|#{pane_tty}|#{pane_dead}|#{pane_current_command}|#{session_id}|#{window_id}|#{@orchestrator_agent}'
  ) || orchestrator_die "registered tmux pane is unavailable: $reg_pane_id"

  IFS='|' read -r pane_id pane_pid pane_tty pane_dead current_command \
    session_id window_id marker <<EOF
$fields
EOF

  if [ "$pane_id" != "$reg_pane_id" ] || [ "$pane_pid" != "$reg_pane_pid" ] || \
    [ "$pane_tty" != "$reg_pane_tty" ] || [ "$pane_dead" != 0 ] || \
    [ "$current_command" != "$reg_current_command" ] || \
    [ "$session_id" != "$reg_session_id" ] || [ "$window_id" != "$reg_window_id" ]; then
    orchestrator_die "registered tmux pane identity changed; register it again"
  fi
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
  if [ -z "$pane_id" ] || [ -z "$window_id" ] || [ "$pane_dead" != 0 ]; then
    orchestrator_die "tmux returned an invalid or dead pane"
  fi

  reg_pane_id=$pane_id
  reg_pane_pid=$pane_pid
  reg_pane_tty=$pane_tty
  reg_current_command=$current_command
  reg_session_id=$session_id
  reg_window_id=$window_id
  reg_harness=$harness
  reg_registered_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

  "$ORCHESTRATOR_TMUX" set-option -p -t "$reg_pane_id" \
    @orchestrator_agent "$(registration_marker)"
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

deliver_message() {
  message=$1
  validate_registration
  "$ORCHESTRATOR_TMUX" send-keys -t "$reg_pane_id" -l -- "$message"
  sleep 1
  "$ORCHESTRATOR_TMUX" send-keys -t "$reg_pane_id" C-m
  printf '%s\n' "$reg_pane_id"
}

unregister() {
  if [ -f "$ORCHESTRATOR_REGISTRATION_FILE" ]; then
    load_registration
    "$ORCHESTRATOR_TMUX" set-option -p -u -t "$reg_pane_id" \
      @orchestrator_agent 2>/dev/null || true
  fi
  rm -f "$ORCHESTRATOR_REGISTRATION_FILE"
  printf 'unregistered agent %s\n' "$agent"
}

case "${1:-}" in
  message|dry-run)
    [ "$#" -eq 3 ] || orchestrator_die "usage: -a AGENT message ID COMMIT"
    case "$2" in '' | *[!0-9a-f]*) orchestrator_die "invalid message ID" ;; esac
    [ "${#2}" -eq 32 ] || orchestrator_die "invalid message ID"
    orchestrator_valid_sha "$3" || orchestrator_die "invalid message commit"
    notice="# orchestrator-message $2 $3 for $agent: Read AGENT-PROTOCOL.md and the complete committed instruction. This is a locator, not expanded authority. Reply in the repository and acknowledge this message after verified publication."
    if [ "$1" = dry-run ]; then
      validate_registration
      printf '%s\n' "$notice"
    else
      deliver_message "$notice"
    fi
    ;;
  register)
    [ "$#" -eq 3 ] || orchestrator_die "usage: $(basename -- "$0") register PANE HARNESS"
    register_pane "$2" "$3"
    ;;
  status)
    validate_registration
    printf 'registered pane=%s harness=%s since=%s\n' \
      "$reg_pane_id" "$reg_harness" "$reg_registered_at"
    ;;
  unregister)
    unregister
    ;;
  *)
    orchestrator_die "usage: $(basename -- "$0") [-a AGENT] register|status|dry-run|message|unregister"
    ;;
esac
