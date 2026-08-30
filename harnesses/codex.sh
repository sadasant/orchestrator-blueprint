#!/bin/sh
set -eu

repo=$1
workdir=$2
prompt_file=$3
model=$4
effort=$5
prompt=$(cat "$prompt_file")

cd "$workdir"
set -- codex -C "$workdir" --add-dir "$repo" \
  --sandbox workspace-write --ask-for-approval on-request
[ -n "$model" ] && set -- "$@" --model "$model"
[ -n "$effort" ] && set -- "$@" -c "model_reasoning_effort=\"$effort\""
exec "$@" "$prompt"
