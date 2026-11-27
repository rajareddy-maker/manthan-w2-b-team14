#!/usr/bin/env bash
# `make demo` — one command from a fresh clone to a running pipeline + dashboard.
# Idempotent: safe to run twice. Stages grow per sprint (see docs/PROGRESS.md).
set -euo pipefail
cd "$(dirname "$0")/.."
T0=$(date +%s)
step() { printf '\n=== [demo %4ss] %s\n' "$(( $(date +%s) - T0 ))" "$*"; }

step "1/5 environment (.env + local venv)"
make --no-print-directory setup

step "2/5 build images and start the stack (waits for healthchecks)"
make --no-print-directory up

step "3/5 verify services"
bash scripts/smoke_test.sh

step "4/5 run the pipeline"
if [[ -f airflow/dags/gridpulse_daily.py ]]; then
  bash scripts/airflow_trigger_wait.sh gridpulse_daily '{"demo_days": '"${GRIDPULSE_DEMO_DAYS:-7}"'}' 1800
else
  echo "gridpulse_daily DAG not built yet (Sprint 0) — walking skeleton = hello_gridpulse (run above)"
fi

set -a; . ./.env; set +a
step "5/5 ready in $(( $(date +%s) - T0 ))s"
cat <<EOF
  Airflow   http://localhost:8080   user: ${AIRFLOW_ADMIN_USER}  password: ${AIRFLOW_ADMIN_PASSWORD}
  Superset  http://localhost:8088   user: ${SUPERSET_ADMIN_USER}  password: ${SUPERSET_ADMIN_PASSWORD}
  Warehouse postgresql://localhost:${POSTGRES_HOST_PORT:-5433}/warehouse (read-only user: bi_reader, password in .env)
EOF
