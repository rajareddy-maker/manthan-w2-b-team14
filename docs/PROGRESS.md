# GridPulse — Progress

**Current sprint:** S4 (Phases 6 + 7) — S0, S1, S2, S3 APPROVED by PO (27-Nov-2026). Accepted 96/111 pts; US-18…22 in review.
**PO:** Mahendra Umath · **Builder:** Claude session · Last update: 27-Nov-2026 (S1 + S2 built on Sagar Kalthiya's Windows 11 host)
S0 and S1 were APPROVED by the PO on 27-Nov-2026 (relayed by Sagar Kalthiya).

## Phase status
| Phase | Sprint | Status |
|---|---|---|
| 0 Requirements | S0 | Done — approved |
| 1 Environment | S0 | Done on Windows host — stack healthy, smoke 9/9 (US-04 in review) |
| 2 Architecture | S1 | Done — approved (ADR-003/004/005 accepted; ADR-006 accepted in S2) |
| 3 Detailed design | S1 | Done — approved; LLD updated in S2 |
| 4 Development | S1–S3 | Generator → bronze → dbt → Postgres publish → Superset chart, all run inside Docker. Missing: DAG (US-15), GX gates (US-14), dashboard (US-16) |
| 5 Testing | S3 | Ongoing — 31 unit + 13 crafted-history dbt tests (90% coverage), 84 dbt checks, manifest reconciliation |
| 6 Deployment | S4 | Not started |
| 7 Monitoring & handover | S4 | Not started |

## What exists and is verified
| Step | Command | Result |
|---|---|---|
| Generate | `python -m ingestion.generator --days 7` | 3,392,136 events, 15 s, `_manifest.json` ground truth |
| Bronze | `python -m ingestion.extractors.landing_to_bronze --all` | 48 partitions, 1 file each, idempotent, 1:1 with landing |
| dbt | `dbt build --project-dir dbt_project --profiles-dir dbt_project` | PASS=84 in 62 s |
| Reconciliation | dbt singular tests | Σ hourly = Σ staging deltas; register span exact; feeder = zone = billing = meter totals |
| Anomalies vs manifest | `docs/evidence/sprint_2/anomalies_vs_manifest.txt` | 5/5 spike, 3/3 tamper, 1/1 outage, 0 false positives, 20% control silent |
| Tests | `pytest tests` (`make test`, `make test-dbt`) | 44 passed, 90% coverage |

## Branches (stacked, pushed to origin; PRs not opened yet)
`main` ← `feature/US-01-inception-docs` ← `US-07-data-generator` ← `US-08-bronze-ingestion` ← `US-06-architecture-adrs` ← `US-09-lld-walking-skeleton` ← `US-11-interval-grid` ← `US-12-consumption-marts` ← `US-13-anomaly-detection` ← `US-10-staging-acceptance-tests` ← `US-23-split-sprint2-docs` ← `US-23-publish-postgres-superset` (all prefixed `feature/`)

## Decisions (ADR log)
| ADR | Decision |
|---|---|
| ADR-001 | Airflow 3.3.2 LocalExecutor; project venv `/opt/gridpulse-venv` in image; runtime Py 3.13, local tooling Py 3.14 |
| ADR-002 | No Kafka, no Spark — files + DuckDB/Parquet (LITE profile) |
| ADR-003 | Bronze partitioned by **arrival** `dt` + `zone`; 1 file per partition; retention raw 30 d, hourly 13 mo |
| ADR-004 | Daily run for D reloads landing `[D−3, D+1]`, rebuilds intervals `[D−3, D]`; older → backfill DAG + alert |
| ADR-005 | Schema-on-read: raw payload in bronze, one CTE per version in staging, unknown → quarantine |
| ADR-006 | Spike = z > 3 **and** kWh ≥ 8 × trailing mean (z alone flags 4,998 of 5,000 meters) |

## How to run (Windows host, Git Bash) — see docs/setup.md §2b
```bash
export PATH="$LOCALAPPDATA/Programs/DockerDesktop/resources/bin:$PATH" MSYS_NO_PATHCONV=1
bash scripts/init_env.sh && docker compose up -d --wait --wait-timeout 600 && bash scripts/smoke_test.sh
docker compose exec -T airflow-scheduler bash -c 'cd /opt/gridpulse && P=/opt/gridpulse-venv/bin \
  && $P/python -m ingestion.generator --days 7 \
  && $P/python -m ingestion.extractors.landing_to_bronze --all \
  && $P/dbt build --project-dir dbt_project --profiles-dir dbt_project \
  && $P/python -m ingestion.publish.to_postgres'
python scripts/superset_first_chart.py      # Superset: http://127.0.0.1:8088 · Airflow: http://127.0.0.1:8080
```
The user's other compose project `airflow` is stopped (volumes kept). Restart it with `docker compose -p airflow start` after `docker compose down` here.

## Open blockers
- None. DEF-002, DEF-005 and DEF-006 are closed.

## Production build (27-Nov-2026, final hour) — built, docs/tests deferred by PO request
| Story | What runs | Evidence |
|---|---|---|
| US-15 | `gridpulse_daily` (01:30 IST, 3-day lookback) + `gridpulse_backfill` (start/end): ingest → dbt build → publish → ops metrics/alerts → retention; 2 retries; `duckdb` pool | backfill 2026-11-20..26 **success in 174 s** (`evidence/sprint_3/airflow_backfill_run.txt`) |
| US-19 | `ops.pipeline_runs` (rows, quarantine, dup rate 1.28%, completeness 99.47%, lag p50 35 / p95 59 min) + `ops.alerts` (completeness < 90%, late data) | same |
| US-16 | Superset dashboard `/superset/dashboard/gridpulse/`: 4 tabs, 9 charts, created by `scripts/superset_dashboard.py` | `evidence/sprint_3/superset_dashboard.txt` |
| US-18 | `.github/workflows/ci.yml` — committed locally, **not pushed**: gh token lacks `workflow` scope (`gh auth refresh -s workflow`) | — |
| demo | `bash scripts/demo.sh` (Docker only, no make) | — |

**Deferred (come back after submission):** US-14 GX gates · US-17 test plan + performance test · US-20 runbook + drill · US-21 voltage view · US-22 retro · sprint/RTM/test_results updates for this hour.

## Next steps
1. PO: Sprint 2 review → APPROVED; review US-04 + US-23 evidence.
2. Open stacked PRs (on request) and squash-merge in order after review.
3. Sprint 3 remainder:
   - US-15 `gridpulse_daily` / `gridpulse_backfill` DAGs (3-day incremental window, retention, ops metrics);
   - US-14 GX gates;
   - US-16 dashboard (4 tabs, exported as code);
   - US-17 test plan.
