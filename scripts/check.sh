#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd -P)

find "$repo/scripts" "$repo/harnesses" -type f -name '*.sh' -print | \
  while IFS= read -r script; do
    sh -n "$script"
  done

python3 -c 'import pathlib; compile(pathlib.Path("scripts/reconcile-agents.py").read_text(), "scripts/reconcile-agents.py", "exec"); compile(pathlib.Path("scripts/check.py").read_text(), "scripts/check.py", "exec")'
python3 "$repo/scripts/check.py"
sh -n "$repo/.githooks/prepare-commit-msg"
GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 python3 -B -m unittest discover -s "$repo/tests"

if git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$repo" diff --check
fi

printf 'shell, Python, privacy, Markdown, and diff checks passed\n'
