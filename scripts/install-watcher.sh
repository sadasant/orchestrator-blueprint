#!/bin/sh
set -eu

# shellcheck source-path=SCRIPTDIR
. "$(dirname -- "$0")/_runtime.sh"
orchestrator_require python3
orchestrator_prepare_state

poll_seconds=${ORCHESTRATOR_POLL_SECONDS:-300}
case "$poll_seconds" in
  '' | *[!0-9]*) orchestrator_die "ORCHESTRATOR_POLL_SECONDS must be an integer" ;;
esac
[ "$poll_seconds" -ge 30 ] || orchestrator_die "poll interval must be at least 30 seconds"

service_id=$(printf '%s' "$ORCHESTRATOR_REPO_NAME" | tr -c 'a-zA-Z0-9-' '-')
launcher="$ORCHESTRATOR_STATE_DIR/watcher-run.sh"

shell_quote() {
  printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
}

launcher_content="#!/bin/sh
export ORCHESTRATOR_AGENT_ROUTING=$(shell_quote "${ORCHESTRATOR_AGENT_ROUTING:-0}")
export ORCHESTRATOR_STATE_DIR=$(shell_quote "$ORCHESTRATOR_STATE_DIR")
export ORCHESTRATOR_REMOTE=$(shell_quote "$ORCHESTRATOR_REMOTE")
export ORCHESTRATOR_BRANCH=$(shell_quote "$ORCHESTRATOR_BRANCH")
exec $(shell_quote "$ORCHESTRATOR_REPO/scripts/watch-remote.sh")"
orchestrator_atomic_write "$launcher" "$launcher_content"
chmod 700 "$launcher"

render_template() {
  template=$1
  target=$2
  shift 2
  python3 - "$template" "$target" "$@" <<'PY'
import html
import os
import pathlib
import sys

template = pathlib.Path(sys.argv[1])
target = pathlib.Path(sys.argv[2])
values = dict(arg.split("=", 1) for arg in sys.argv[3:])
text = template.read_text(encoding="utf-8")
for key, value in values.items():
    if template.suffix == ".template" and template.name.endswith("plist.template"):
        value = html.escape(value)
    elif key == "LAUNCHER":
        value = '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'
    text = text.replace(f"@{key}@", value)
target.parent.mkdir(parents=True, exist_ok=True)
temporary = target.with_name(target.name + f".{os.getpid()}")
temporary.write_text(text, encoding="utf-8")
os.chmod(temporary, 0o600)
temporary.replace(target)
PY
}

case "$(uname -s)" in
  Darwin)
    label="local.orchestrator.$service_id"
    target="$HOME/Library/LaunchAgents/$label.plist"
    render_template "$ORCHESTRATOR_REPO/automation/macos.plist.template" "$target" \
      "LABEL=$label" "LAUNCHER=$launcher" "POLL_SECONDS=$poll_seconds" \
      "STDOUT=$ORCHESTRATOR_STATE_DIR/launchd.out.log" \
      "STDERR=$ORCHESTRATOR_STATE_DIR/launchd.err.log"
    launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$target"
    launchctl kickstart "gui/$(id -u)/$label"
    printf 'installed macOS LaunchAgent: %s\n' "$target"
    ;;
  Linux)
    orchestrator_require systemctl
    unit_dir=${XDG_CONFIG_HOME:-"$HOME/.config"}/systemd/user
    service="orchestrator-$service_id.service"
    timer="orchestrator-$service_id.timer"
    render_template "$ORCHESTRATOR_REPO/automation/linux.service.template" \
      "$unit_dir/$service" "LAUNCHER=$launcher"
    render_template "$ORCHESTRATOR_REPO/automation/linux.timer.template" \
      "$unit_dir/$timer" "POLL_SECONDS=$poll_seconds"
    systemctl --user daemon-reload
    systemctl --user enable --now "$timer"
    printf 'installed Linux user timer: %s\n' "$timer"
    ;;
  *)
    orchestrator_die "unsupported host; run scripts/watch-remote.sh from a local scheduler"
    ;;
esac
