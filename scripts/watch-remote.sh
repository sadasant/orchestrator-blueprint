#!/bin/sh
set -eu

# shellcheck source-path=SCRIPTDIR
. "$(dirname -- "$0")/_runtime.sh"
orchestrator_require python3
exec python3 "$ORCHESTRATOR_REPO/scripts/agent-channel.py" poll
