#!/usr/bin/env bash
# Phase-1 verification: every service in the stack works end to end.
# Requires `make up`. Prints PASS/FAIL per check; exits 1 on any failure.
set -uo pipefail
cd "$(dirname "$0")/.."
# Git Bash on Windows rewrites args starting with "/" into Windows paths; keep them verbatim.
export MSYS_NO_PATHCONV=1
set -a; . ./.env; set +a

PASS=0; FAILN=0
check() {  # name, command...
  local name=$1; shift
  local out
  if out=$("$@" 2>&1); then
    PASS=$((PASS+1)); printf '  [PASS] %-44s %s\n' "$name" "$(tail -1 <<<"$out" | cut -c1-70)"
  else
    FAILN=$((FAILN+1)); printf '  [FAIL] %-44s\n%s\n' "$name" "$(tail -15 <<<"$out")"
  fi
}
EXEC=(docker compose exec -T)

echo "GridPulse smoke test — $(date '+%Y-%m-%d %H:%M:%S %Z')"

check "Postgres accepts connections" "${EXEC[@]}" postgres pg_isready -U postgres -d warehouse
check "Warehouse readable by bi_reader" "${EXEC[@]}" -e PGPASSWORD="$BI_READER_PASSWORD" postgres \
  psql -h localhost -U bi_reader -d warehouse -tAc "select note from ops.healthcheck where id = 1"
check "Airflow API :8080 healthy" curl -fsS http://localhost:8080/api/v2/monitor/health
check "Airflow scheduler healthy" "${EXEC[@]}" airflow-scheduler curl -fsS http://localhost:8974/health
check "hello_gridpulse DAG run succeeds" bash scripts/airflow_trigger_wait.sh hello_gridpulse '{}' 300
check "dbt debug passes" "${EXEC[@]}" airflow-scheduler bash -c \
  'cd /opt/gridpulse && /opt/gridpulse-venv/bin/dbt debug --project-dir dbt_project --profiles-dir dbt_project | tail -3'
check "GX sample checkpoint passes" "${EXEC[@]}" airflow-scheduler \
  /opt/gridpulse-venv/bin/python /opt/gridpulse/data_quality/gx/run_checkpoint.py --suite sample
check "Superset UI :8088 healthy" curl -fsS http://localhost:8088/health
check "Superset queries the warehouse" "${EXEC[@]}" superset /app/.venv/bin/python -c '
from sqlalchemy import text
from superset.app import create_app
app = create_app()
with app.app_context():
    from superset.extensions import db
    from superset.models.core import Database
    d = db.session.query(Database).filter_by(database_name="GridPulse Warehouse").one()
    with d.get_sqla_engine() as engine, engine.connect() as conn:
        print("superset->warehouse:", conn.execute(text("select note from ops.healthcheck")).scalar())
'
echo "  [SKIP] Kafka topic produce/consume                     dropped by design (ADR-002)"
echo "  [SKIP] Spark UI :8081 sample job                        dropped by design (ADR-002)"

echo "RESULT: ${PASS} passed, ${FAILN} failed"
[[ $FAILN -eq 0 ]]
