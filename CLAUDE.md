# CLAUDE.md — GridPulse (Smart Meter Telemetry Platform)

Team 14 · Track B · NucleusTeq Indore · 27-Nov-2026 · PO: Mahendra Umath.
Read `docs/PROGRESS.md` first in every session — it is the source of truth for sprint/phase status.

## What we are building
Daily batch platform: smart-meter JSON telemetry (schema v1 + v2) → raw preserved → normalised
15-min intervals (kWh, deduped, ordered, gaps marked) → hourly/daily/monthly consumption →
anomaly flags (spike, tamper, outage) → Superset dashboard for network ops, billing, revenue protection.
Scale: 5,000 meters · 20 feeders · 6 zones · 96 readings/meter/day ≈ 480k events/day. Demo = 7 days.

## Stack (LITE profile — host has 14 GB RAM; see docs/adr/)
| Layer | Tool (pinned) |
|---|---|
| Landing | JSONL files from gateways → `data/landing/dt=YYYY-MM-DD/*.jsonl` (no Kafka — ADR-002) |
| Bronze lake | Parquet, Hive-partitioned `dt=/zone=` under `data/lake/bronze/` |
| Compute | DuckDB 2.0.1 + dbt-duckdb 1.11.1 (no Spark — ADR-002) |
| Serving | PostgreSQL 16.16 — `warehouse` DB, schemas `marts`, `ops` (host port **5433**) |
| DQ | dbt tests + Great Expectations 1.25.0 (gates between layers) |
| Orchestration | Airflow 3.3.2, LocalExecutor, Python 3.13 image (ADR-001) |
| BI | Superset 6.1.0 on :8088 |
| Local tooling | `.venv` (system Python 3.14) — runtime is always the containers (Py 3.13) |

## Commands (always via make)
```
make setup          # venv + pinned deps + pre-commit + .env from .env.example
make up / down      # docker compose stack (gridpulse project)
make demo           # ONE command: setup → up → wait healthy → seed 7 days → run DAG → print URLs
make test           # pytest (unit + integration) with coverage
make lint           # ruff + black --check + sqlfluff
make dbt-run / dbt-test / gx-validate
make export-backlog # docs/scrum/product_backlog.md → .xlsx
make smoke          # scripts/smoke_test.sh — every service verified
```
Ports: Airflow 8080 · Superset 8088 · Postgres 5433 (5432 is taken on the host).

## Domain rules — NON-NEGOTIABLE
### Time zone
- Source timestamps are **IST** ISO-8601 (`2026-11-20T10:15:00+05:30`). Naive timestamps = IST.
- Store as `TIMESTAMPTZ` (`reading_ts`). All buckets (hour/day/month), partitions (`dt`) and
  billing periods are computed in **Asia/Kolkata**. Never bucket on UTC. IST has no DST.
- Interval convention: a reading at `T` closes the interval `(T-15m, T]`; `interval_start = T - 15m`.
  Hourly/daily buckets use `interval_start` (so the 00:00 reading belongs to the previous day).
- Valid readings sit on the 15-min grid (:00/:15/:30/:45). Off-grid → snap to nearest grid point
  only if within ±2 min, else quarantine.

### Energy & units
- `energy` is a **cumulative register**, not per-interval energy. Interval kWh = register delta.
- v1: `energy_wh` (Wh). v2: `energy` + `unit` ∈ {`Wh`,`kWh`}. Convert **everything to kWh**
  in staging (`Wh / 1000`). Never mix units after staging. Column suffix `_kwh` is mandatory.
- Billing quantities use `DECIMAL(18,4)`; never FLOAT for billed totals.
- Register decrease: if `status = 'ROLLOVER'` → delta = (max_register − prev) + current;
  otherwise delta is NULL and the row is DQ-flagged `register_decrease`.
- Negative energy values are rejected to quarantine (DQ rule), never silently abs()'d.

### Normalisation
- Raw/bronze is append-only and keeps the original payload + `schema_version` + `source_file`
  + `ingested_at`. Never mutate bronze.
- Dedup key = (`meter_id`, `reading_ts`). Keep the earliest `ingested_at`; count dropped dups.
- Order by `reading_ts` per meter (late/out-of-order files are normal).
- Missing intervals are **marked as gaps** in `int_meter_intervals` (`is_gap = true`) — never
  filled/interpolated. A delta spanning a gap is kept once with `gap_intervals = n`.
- Late data: daily run reprocesses a **3-day lookback** idempotently; older → backfill DAG.

### DQ rules (PRD)
1. `meter_id` exists in meter master (seed `meter_master.csv`) — else quarantine.
2. Energy reading ≥ 0. 3. Register never decreases unless ROLLOVER flagged.
4. Completeness per meter per day ≥ 90% (≥ 87 of 96 intervals) else `quality_flag = 'LOW_COMPLETENESS'`.

### Anomalies (defaults — change only via ADR)
- **Spike**: interval kWh z-score > 3.0 vs the meter's trailing 30 days (min 96 points)
  **and** kWh ≥ 8 × trailing mean (ADR-006 — z alone flags 4,998/5,000 meters).
- **Tamper**: meter has 0 kWh for ≥ 48 h (192 intervals) while ≥ 70% of other meters on the same
  feeder have non-zero consumption in that window.
- **Outage**: ≥ 30% of a feeder's meters missing the same interval (≥ 2 consecutive intervals).

## Repo layout
```
airflow/dags/            thin DAG files only — logic lives in ingestion/ and dbt_project/
ingestion/generator/     synthetic data (Faker) incl. injected defects
ingestion/extractors/    landing JSONL → bronze Parquet, compaction, retention
dbt_project/             staging (stg_) → intermediate (int_) → marts (fct_/dim_/mart_)
data_quality/gx/         GX suites + checkpoints per layer
infra/                   Dockerfiles, superset_config.py, postgres/init.sql
superset/                dashboard exports (as code)
scripts/                 system_check.sh, smoke_test.sh, seed_data.py, export_backlog.py, demo.sh
tests/                   unit/ integration/ e2e/ fixtures/
docs/                    PROGRESS, ideation, requirements, rtm, architecture, lld, adr/, scrum/, test_*
```

## Coding conventions
- Python: type hints, docstrings, `logging` (structured key=value), config via env vars only,
  small pure functions (unit-testable). ruff + black (line 100). No business logic in DAG files.
- SQL: lowercase keywords, snake_case, one model per file, CTE style, sqlfluff (duckdb dialect).
- dbt naming: `stg_<source>__<entity>`, `int_<entity>_<verb>`, `fct_`, `dim_`, `mart_`.
  Every model has a `schema.yml` entry with description + tests.
- Every timestamp column name ends in `_ts`, every IST date column in `_date_ist`.
- Pin all versions (images, pip, dbt packages). Never use `latest`.
- Secrets only in `.env` (git-ignored); `.env.example` is committed. Never print secrets.

## Git / Scrum workflow
- Branch per story: `feature/US-xx-short-name`; conventional commits with story ID
  (`feat(US-12): ...`). Squash-merge to `main`. PR template = DoD checklist.
- Gates: approval by PO (Mahendra) at each **Sprint Review** — stop and ask for APPROVED.
- After every sprint: update `docs/PROGRESS.md`, sprint file, `velocity.md`, RTM, re-run
  `make export-backlog`. Log every defect in `docs/test_results.md`, evidence in `docs/evidence/`.
- Never invent test results — only paste real command output.

## Gotchas
- Host RAM is tight: keep Kafka/Spark out; stop other compose stacks before `make up`.
- DuckDB file is single-writer: dbt + extractor tasks run in Airflow pool `duckdb` (1 slot).
- Airflow 3: tasks reach the API server via `AIRFLOW__CORE__EXECUTION_API_SERVER_URL`;
  `AIRFLOW_UID` must match host uid (written to `.env` by `make setup`).
- dbt + GX + ingestion deps live in a separate venv inside the Airflow image (`/opt/gridpulse-venv`) to avoid
  dependency clashes with Airflow.
