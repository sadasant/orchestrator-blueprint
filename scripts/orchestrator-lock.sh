#!/bin/sh
set -eu

# shellcheck source-path=SCRIPTDIR
. "$(dirname -- "$0")/_runtime.sh"
orchestrator_prepare_state

case "${1:-}" in
  acquire)
    if ! mkdir "$ORCHESTRATOR_LOCK_DIR" 2>/dev/null; then
      orchestrator_die "orchestrator writer lease is already held: $ORCHESTRATOR_LOCK_DIR"
    fi
    printf 'acquired %s\n' "$ORCHESTRATOR_LOCK_DIR"
    ;;
  release)
    if ! rmdir "$ORCHESTRATOR_LOCK_DIR" 2>/dev/null; then
      orchestrator_die "orchestrator writer lease is absent or not empty: $ORCHESTRATOR_LOCK_DIR"
    fi
    printf 'released %s\n' "$ORCHESTRATOR_LOCK_DIR"
    ;;
  status)
    if [ -d "$ORCHESTRATOR_LOCK_DIR" ]; then
      printf 'held %s\n' "$ORCHESTRATOR_LOCK_DIR"
      exit 0
    fi
    printf 'available %s\n' "$ORCHESTRATOR_LOCK_DIR"
    exit 1
    ;;
  *)
    orchestrator_die "usage: $(basename -- "$0") acquire|release|status"
    ;;
esac
