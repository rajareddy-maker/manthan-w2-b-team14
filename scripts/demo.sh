#!/usr/bin/env bash
# `make demo` / `bash scripts/demo.sh` — fresh clone -> running pipeline + dashboard.
# Everything runs in Docker (Airflow 3.3.2 + project venv, Postgres 16.16, Superset 6.1.0).
# Idempotent: safe to run twice. Needs only docker, bash and python3 (stdlib) on the host.
set -euo pipefail
cd "$(dirname "$0")/.."
# Git Bash on Windows rewrites args starting with "/" into Windows paths; keep them verbatim.
export MSYS_NO_PATHCONV=1
DAYS=${GRIDPULSE_DEMO_DAYS:-7}
PYHOST=$(command -v python3 || command -v python)
T0=$(date +%s)
step() { printf '\n=== [demo %4ss] %s\n' "$(( $(date +%s) - T0 ))" "$*"; }
in_airflow() { docker compose exec -T airflow-scheduler bash -c "cd /opt/gridpulse && $*"; }

step "1/6 environment (.env with random secrets)"
bash scripts/init_env.sh

step "2/6 build images one at a time, start the stack, wait for healthchecks"
docker compose build superset-init
docker compose build airflow-init
docker compose up -d --wait --wait-timeout 900

step "3/6 verify every service"
bash scripts/smoke_test.sh

step "4/6 synthetic gateway data: ${DAYS} days x 5,000 meters (in Docker)"
in_airflow "/opt/gridpulse-venv/bin/python -m ingestion.generator --days ${DAYS}"
read -r START END < <(in_airflow "/opt/gridpulse-venv/bin/python -c \"import json; \
c = json.load(open('data/landing/_manifest.json'))['config']; print(c['start_date'], c['end_date'])\"")

step "5/6 Airflow: gridpulse_backfill ${START} -> ${END} (ingest, dbt build, publish, ops metrics, retention)"
bash scripts/airflow_trigger_wait.sh gridpulse_backfill "{\"start\":\"${START}\",\"end\":\"${END}\"}" 2400
in_airflow "airflow dags unpause gridpulse_daily >/dev/null" && echo "gridpulse_daily unpaused (01:30 IST)"

step "6/6 Superset dashboard as code"
"$PYHOST" scripts/superset_dashboard.py

set -a; . ./.env; set +a
step "ready in $(( $(date +%s) - T0 ))s"
cat <<EOF
  Dashboard http://localhost:8088/superset/dashboard/gridpulse/   (user: ${SUPERSET_ADMIN_USER}, password in .env)
  Airflow   http://localhost:8080                                  (user: ${AIRFLOW_ADMIN_USER}, password in .env)
  Warehouse postgresql://localhost:${POSTGRES_HOST_PORT:-5433}/warehouse  (read-only user bi_reader, password in .env)
EOF
