#!/usr/bin/env bash
# Idempotent Superset bootstrap: migrate metadata DB, create admin, register the warehouse,
# and import dashboards exported as code (superset/*.zip) when present.
set -euo pipefail

echo "[superset-init] db upgrade"
superset db upgrade

echo "[superset-init] admin user"
superset fab create-admin \
  --username "${SUPERSET_ADMIN_USER}" --password "${SUPERSET_ADMIN_PASSWORD}" \
  --firstname GridPulse --lastname Admin --email admin@gridpulse.local 2>&1 \
  | grep -v -i "already exist" || true

echo "[superset-init] roles and permissions"
superset init

echo "[superset-init] warehouse connection (read-only role bi_reader)"
superset set-database-uri \
  --database_name "GridPulse Warehouse" \
  --uri "postgresql+psycopg2://bi_reader:${BI_READER_PASSWORD}@${WAREHOUSE_HOST:-postgres}:5432/warehouse"

shopt -s nullglob
for bundle in /app/gridpulse_superset/*.zip; do
  echo "[superset-init] importing dashboard bundle ${bundle}"
  superset import-dashboards --path "${bundle}" --username "${SUPERSET_ADMIN_USER}"
done

echo "[superset-init] done"
