#!/bin/sh
set -eu

repo=$1
workdir=$2
prompt_file=$3
model=$4
effort=$5

: "${CUSTOM_HARNESS_COMMAND:?set CUSTOM_HARNESS_COMMAND to one executable path}"
prompt=$(cat "$prompt_file")
export ORCHESTRATOR_REPOSITORY="$repo"
export ORCHESTRATOR_MODEL="$model"
export ORCHESTRATOR_EFFORT="$effort"
cd "$workdir"
exec "$CUSTOM_HARNESS_COMMAND" "$prompt"
