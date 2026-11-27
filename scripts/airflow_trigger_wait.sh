#!/usr/bin/env bash
# Trigger an Airflow DAG run inside the stack and wait for it to finish.
# Usage: scripts/airflow_trigger_wait.sh <dag_id> [conf_json] [timeout_seconds]
set -euo pipefail
cd "$(dirname "$0")/.."
# Git Bash on Windows rewrites args starting with "/" into Windows paths; keep them verbatim.
export MSYS_NO_PATHCONV=1

DAG_ID=$1
CONF=${2:-'{}'}
TIMEOUT=${3:-900}
RUN_ID="manual__$(date +%Y%m%dT%H%M%S)_$RANDOM"
AF=(docker compose exec -T airflow-scheduler airflow)

"${AF[@]}" dags unpause "$DAG_ID" >/dev/null
"${AF[@]}" dags trigger "$DAG_ID" --run-id "$RUN_ID" --conf "$CONF" >/dev/null
echo "[trigger] $DAG_ID run_id=$RUN_ID conf=$CONF"

start=$(date +%s)
state=queued
while :; do
  state=$("${AF[@]}" dags list-runs "$DAG_ID" -o plain 2>/dev/null \
          | awk -v r="$RUN_ID" '$0 ~ r {for (i=1;i<=NF;i++) if ($i ~ /^(queued|running|success|failed)$/) {print $i; exit}}')
  case "$state" in
    success) echo "[trigger] $DAG_ID $RUN_ID -> success in $(( $(date +%s) - start ))s"; exit 0 ;;
    failed)  echo "[trigger] $DAG_ID $RUN_ID -> FAILED"; "${AF[@]}" tasks states-for-dag-run "$DAG_ID" "$RUN_ID" || true; exit 1 ;;
  esac
  if (( $(date +%s) - start > TIMEOUT )); then echo "[trigger] timeout after ${TIMEOUT}s (state=${state:-unknown})"; exit 1; fi
  sleep 5
done
