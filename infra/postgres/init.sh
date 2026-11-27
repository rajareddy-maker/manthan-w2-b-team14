#!/usr/bin/env bash
# Runs once on first Postgres start (docker-entrypoint-initdb.d).
# Creates: airflow + superset metadata DBs, the warehouse DB (schemas marts, ops),
# a writer role (gridpulse) and a read-only BI role (bi_reader) used by Superset.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-SQL
  CREATE ROLE airflow  LOGIN PASSWORD '${AIRFLOW_DB_PASSWORD}';
  CREATE ROLE superset LOGIN PASSWORD '${SUPERSET_DB_PASSWORD}';
  CREATE ROLE gridpulse LOGIN PASSWORD '${WAREHOUSE_DB_PASSWORD}';
  CREATE ROLE bi_reader LOGIN PASSWORD '${BI_READER_PASSWORD}';
  CREATE DATABASE airflow  OWNER airflow;
  CREATE DATABASE superset OWNER superset;
  CREATE DATABASE warehouse OWNER gridpulse;
SQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname warehouse <<-SQL
  ALTER DATABASE warehouse SET timezone TO 'Asia/Kolkata';
  CREATE SCHEMA marts AUTHORIZATION gridpulse;
  CREATE SCHEMA ops   AUTHORIZATION gridpulse;
  GRANT CONNECT ON DATABASE warehouse TO bi_reader;
  GRANT USAGE ON SCHEMA marts, ops TO bi_reader;
  ALTER DEFAULT PRIVILEGES FOR ROLE gridpulse IN SCHEMA marts GRANT SELECT ON TABLES TO bi_reader;
  ALTER DEFAULT PRIVILEGES FOR ROLE gridpulse IN SCHEMA ops   GRANT SELECT ON TABLES TO bi_reader;

  SET ROLE gridpulse;
  CREATE TABLE ops.healthcheck (
    id         integer PRIMARY KEY,
    checked_ts timestamptz NOT NULL DEFAULT now(),
    note       text NOT NULL
  );
  INSERT INTO ops.healthcheck (id, note) VALUES (1, 'warehouse initialised');
SQL

echo "[postgres-init] databases, roles and schemas created"
