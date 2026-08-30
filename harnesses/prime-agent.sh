#!/bin/sh
set -eu

repo=$1
workdir=$2
prompt_file=$3
model=$4
effort=$5
prompt=$(cat "$prompt_file")

[ -d "$repo" ] || { printf 'repository is unavailable\n' >&2; exit 1; }
[ -z "$model" ] || printf 'note: configure model selection in Prime Agent; launcher value recorded as %s\n' "$model" >&2
[ -z "$effort" ] || printf 'note: configure effort in Prime Agent; launcher value recorded as %s\n' "$effort" >&2
cd "$workdir"
exec prime-agent "$prompt"
