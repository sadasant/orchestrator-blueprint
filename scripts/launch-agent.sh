#!/bin/sh
set -eu

# shellcheck source-path=SCRIPTDIR
. "$(dirname -- "$0")/_runtime.sh"
[ -n "$ORCHESTRATOR_TMUX" ] || orchestrator_die "missing required command: tmux"

agent_id=${1:-}
harness=${2:-}
workdir=${3:-}
model=${4:-}
effort=${5:-}

if [ "$#" -lt 3 ] || [ "$#" -gt 5 ]; then
  orchestrator_die "usage: $(basename -- "$0") AGENT_ID HARNESS WORKTREE [MODEL] [EFFORT]"
fi

case "$agent_id" in
  '' | *[!a-z0-9-]*) orchestrator_die "invalid agent ID" ;;
esac
case "$harness" in
  '' | *[!a-z0-9-]*) orchestrator_die "invalid harness ID" ;;
esac

dossier="$ORCHESTRATOR_REPO/sub-agents/active/$agent_id"
prompt_file="$dossier/launch-prompt.md"
adapter="$ORCHESTRATOR_REPO/harnesses/$harness.sh"
log_file="$dossier/runner.log"
session="orchestrator-$agent_id"

[ -d "$dossier" ] || orchestrator_die "active dossier is absent: $agent_id"
[ -f "$ORCHESTRATOR_REPO/sub-agents/active.md" ] || orchestrator_die "active authority table is absent"
grep -Eq "^\|[[:space:]]*${agent_id}[[:space:]]*\|" \
  "$ORCHESTRATOR_REPO/sub-agents/active.md" || \
  orchestrator_die "agent has no active authority row: $agent_id"
[ -f "$prompt_file" ] || orchestrator_die "launch prompt is absent: $prompt_file"
[ -x "$adapter" ] || orchestrator_die "executable harness adapter is absent: $adapter"

workdir=$(CDPATH='' cd -- "$workdir" && pwd -P) || orchestrator_die "worktree is unavailable"
root=$(git -C "$workdir" rev-parse --show-toplevel 2>/dev/null) || \
  orchestrator_die "worktree is not a Git checkout"
root=$(CDPATH='' cd -- "$root" && pwd -P)
[ "$workdir" = "$root" ] || orchestrator_die "worktree argument must be its Git root"

"$ORCHESTRATOR_TMUX" has-session -t "$session" 2>/dev/null && \
  orchestrator_die "tmux session already exists: $session"

shell_quote() {
  printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
}

command="exec $(shell_quote "$adapter") $(shell_quote "$ORCHESTRATOR_REPO") $(shell_quote "$workdir") $(shell_quote "$prompt_file") $(shell_quote "$model") $(shell_quote "$effort")"
umask 077
: > "$log_file"
chmod 600 "$log_file"

"$ORCHESTRATOR_TMUX" new-session -d -s "$session" -c "$workdir" "$command"
pipe_command="exec cat >> $(shell_quote "$log_file")"
"$ORCHESTRATOR_TMUX" pipe-pane -o -t "$session" "$pipe_command"
sleep 1
"$ORCHESTRATOR_TMUX" has-session -t "$session" 2>/dev/null || \
  orchestrator_die "harness exited before its runtime receipt could be observed"

"$ORCHESTRATOR_TMUX" display-message -p -t "$session" \
  'session=#{session_name} pane=#{pane_id} pane_pid=#{pane_pid} command=#{pane_current_command}'
printf 'harness=%s\nworktree=%s\nlog=%s\n' "$harness" "$workdir" "$log_file"
