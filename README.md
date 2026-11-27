# GridPulse — Smart Meter Telemetry Platform

Team 14 · Track B · NucleusTeq Indore · 27-Nov-2026 · PO: Mahendra Umath

GridPulse turns raw smart-meter telemetry into billing-ready consumption and anomaly flags:
- **Sources:** 5,000 meters · 20 feeders · 6 zones · 96 readings/meter/day, in two schema versions with mixed Wh/kWh.
- **Processing:** readings are converted to kWh in IST, de-duplicated, ordered and placed on a 15-min grid. Gaps are marked, never filled.
- **Outputs:**
  - hourly, daily and monthly consumption per meter, feeder and zone;
  - spike, tamper and outage flags;
  - a Superset dashboard for network ops, billing and revenue protection.

## Quick start — one command
Prerequisites: Docker (Desktop) with about 6 GB for the VM, bash, python3.

```bash
make demo            # Linux/macOS
bash scripts/demo.sh # Windows Git Bash (no make): see docs/setup.md §2b for the PATH line
```

**What you will see:**
1. `.env` is created with random secrets.
2. The images build and the stack starts. Every healthcheck goes green.
3. `RESULT: 9 passed, 0 failed` from the smoke test.
4. 7 days of synthetic data are generated (3.39M events).
5. The Airflow backfill runs ingest → dbt build → GX gates → publish → ops metrics → retention, ending in `-> success`.
6. The dashboard is created. URLs are printed at the end; passwords are in `.env`.

**Where to look:**

| What | URL / location |
|---|---|
| Dashboard *GridPulse — Network Operations* (tabs: feeder consumption, anomalies, completeness per zone, pipeline health) | http://localhost:8088/superset/dashboard/gridpulse/ |
| Airflow (`gridpulse_daily` 01:30 IST, `gridpulse_backfill`) | http://localhost:8080 |
| Warehouse (read-only user `bi_reader`) | `postgresql://localhost:5433/warehouse`, schemas `marts`, `ops` |

## Architecture
`landing JSONL → bronze Parquet (dt/zone) → dbt on DuckDB (staging → intervals → marts) → GX gates → Postgres marts → Superset`, orchestrated by Airflow 3.3.2. Diagram: [docs/architecture.md](docs/architecture.md). Decisions: [docs/adr/](docs/adr/).

## Everyday commands
| Task | Command |
|---|---|
| Start / stop | `make up` / `make down` (Windows: `docker compose up -d --wait` / `docker compose down`) |
| Verify services | `bash scripts/smoke_test.sh` |
| Backfill a range | `make backfill START=2026-11-20 END=2026-11-26` |
| Tests | `make test` (unit), `make test-dbt` (crafted histories), `make lint` |
| Rebuild the dashboard | `make dashboard` |

## Documentation
| Topic | Document |
|---|---|
| Operations: alerts, backfill, rollback | [docs/runbook.md](docs/runbook.md) |
| Tables and columns | [docs/data_dictionary.md](docs/data_dictionary.md) |
| Design | [docs/lld.md](docs/lld.md) |
| Testing | [docs/test_plan.md](docs/test_plan.md), [docs/test_results.md](docs/test_results.md) |
| Status and handover | [docs/PROGRESS.md](docs/PROGRESS.md), [docs/completion_report.md](docs/completion_report.md) |
| Backlog | [docs/scrum/product_backlog.xlsx](docs/scrum/product_backlog.xlsx) |
