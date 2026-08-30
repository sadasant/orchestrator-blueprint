#!/bin/sh

# This file is sourced by the executable scripts in this directory.
ORCHESTRATOR_REPO=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd -P)
ORCHESTRATOR_REPO_NAME=$(basename -- "$ORCHESTRATOR_REPO")

: "${ORCHESTRATOR_REMOTE:=origin}"
: "${ORCHESTRATOR_BRANCH:=main}"
: "${ORCHESTRATOR_TMUX:=$(command -v tmux 2>/dev/null || true)}"

if [ -z "${ORCHESTRATOR_STATE_DIR:-}" ]; then
  state_home=${XDG_STATE_HOME:-"$HOME/.local/state"}
  ORCHESTRATOR_STATE_DIR="$state_home/$ORCHESTRATOR_REPO_NAME"
fi

ORCHESTRATOR_LOCK_DIR="$ORCHESTRATOR_STATE_DIR/run.lock"
ORCHESTRATOR_PROCESSED_FILE="$ORCHESTRATOR_STATE_DIR/processed-head"
ORCHESTRATOR_NOTIFIED_FILE="$ORCHESTRATOR_STATE_DIR/notified-head"
ORCHESTRATOR_REGISTRATION_FILE="$ORCHESTRATOR_STATE_DIR/root-pane"
ORCHESTRATOR_LOG_FILE="$ORCHESTRATOR_STATE_DIR/watcher.log"

export ORCHESTRATOR_REPO ORCHESTRATOR_REPO_NAME ORCHESTRATOR_REMOTE
export ORCHESTRATOR_BRANCH ORCHESTRATOR_TMUX ORCHESTRATOR_STATE_DIR
export ORCHESTRATOR_LOCK_DIR ORCHESTRATOR_PROCESSED_FILE
export ORCHESTRATOR_NOTIFIED_FILE ORCHESTRATOR_REGISTRATION_FILE
export ORCHESTRATOR_LOG_FILE

orchestrator_die() {
  printf '%s\n' "$*" >&2
  exit 1
}

orchestrator_require() {
  command -v "$1" >/dev/null 2>&1 || orchestrator_die "missing required command: $1"
}

orchestrator_valid_sha() {
  [ "${#1}" -eq 40 ] || return 1
  case "$1" in
    *[!0-9a-f]*) return 1 ;;
    *) return 0 ;;
  esac
}

orchestrator_prepare_state() {
  umask 077
  mkdir -p "$ORCHESTRATOR_STATE_DIR"
  chmod 700 "$ORCHESTRATOR_STATE_DIR"
}

orchestrator_atomic_write() {
  target=$1
  content=$2
  temporary="$target.$$"
  umask 077
  printf '%s\n' "$content" > "$temporary"
  chmod 600 "$temporary"
  mv -f "$temporary" "$target"
}
