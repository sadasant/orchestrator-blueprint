#!/bin/sh
set -eu

repo=$1
workdir=$2
prompt_file=$3
model=$4
effort=$5
prompt=$(cat "$prompt_file")

cd "$workdir"
set -- claude --add-dir "$repo" --permission-mode manual
[ -n "$model" ] && set -- "$@" --model "$model"
[ -n "$effort" ] && set -- "$@" --effort "$effort"
exec "$@" "$prompt"
