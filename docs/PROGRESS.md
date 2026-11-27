# GridPulse — Progress

**Current sprint:** S1 (Phases 2 + 3) — in review, awaiting PO approval · **S0** also still awaiting PO approval · **Next:** S2 (Phase 4)
**PO:** Mahendra Umath · **Builder:** Claude session · Last update: 27-Nov-2026 (S1 on Sagar Kalthiya's Windows 11 host)

## Phase status
| Phase | Sprint | Status |
|---|---|---|
| 0 Requirements | S0 | Done — pending PO approval |
| 1 Environment | S0 | Partial — local toolchain verified on both hosts; Docker stack blocked (DEF-002, DEF-005) |
| 2 Architecture | S1 | Done — architecture.md + ADR-003/004/005 (status Proposed → PO) |
| 3 Detailed design | S1 | Done — docs/lld.md; walking skeleton runs locally to a DuckDB mart; Postgres + Superset leg blocked |
| 4 Development | S1–S3 | Started — generator, bronze extractor, dbt staging + quarantine + zone completeness mart |
| 5 Testing | S3 | Ongoing — 31 unit tests (90% cov), 36 dbt checks, manifest reconciliation |
| 6 Deployment | S4 | Not started |
| 7 Monitoring & handover | S4 | Not started |

## What exists and is verified (Sprint 1)
- `python -m ingestion.generator --days 7`: 3,392,136 events, 1,023 files, 15 s. Writes `data/landing/_manifest.json`, which is the ground truth for the tests.
- `python -m ingestion.extractors.landing_to_bronze --all`: 48 partitions, one file each, 38 MB. Reconciles 1:1 with the landing files and is idempotent.
- `dbt build`: PASS=36. Reconciliation: `bronze = kept 3,347,177 + dups 43,439 + quarantined 1,520`.
- Evidence is in `docs/evidence/sprint_1/`; test cases and defects are in `docs/test_results.md`.

## Branches (stacked, local only — not pushed, not merged)
`main` ← `feature/US-01-inception-docs` (S0, pushed) ← `feature/US-07-data-generator` ← `feature/US-08-bronze-ingestion` ← `feature/US-06-architecture-adrs` ← `feature/US-09-lld-walking-skeleton`

## Decisions (ADR log)
| ADR | Decision |
|---|---|
| ADR-001 | Airflow 3.3.2 LocalExecutor; project venv `/opt/gridpulse-venv` in image; runtime Py 3.13, local tooling Py 3.14 |
| ADR-002 | No Kafka, no Spark — files + DuckDB/Parquet (LITE profile) |
| ADR-003 | Bronze partitioned by **arrival** `dt` + `zone`; 1 file per partition; retention raw 30 d, hourly 13 mo (hourly per-meter stays in the lake) |
| ADR-004 | Daily run for D reloads landing `[D−3, D+1]`, rebuilds intervals `[D−3, D]`; older → backfill DAG + alert |
| ADR-005 | Schema-on-read: raw payload in bronze, one CTE per version in staging, unknown → quarantine |

## Confirmed by PO
- `energy` = cumulative register · timestamps are IST · demo = 7 days · gates per sprint review · PO = Mahendra Umath.

## Open blockers
- **DEF-002 / DEF-005:** no running Docker stack on either host, and no `make` on the Windows host. This blocks `make up`/`smoke`, the Postgres publish and Superset (US-04, US-09 AC2).

## Next steps
1. PO review of S0 and S1 → APPROVED (or change requests).
2. Fix the Docker blocker: install Docker Desktop + GNU make on the Windows host, or fix memory on the Ubuntu host.
   Then `make up`, `make smoke`, and finish US-09 AC2 (publish → Postgres → one Superset chart).
3. Push the stacked branches and open PRs, after PO OK.
4. Sprint 2:
   - US-10 formal ACs + 3-day incremental window;
   - US-11 `int_meter_intervals` (date spine, gaps, deltas, rollover);
   - US-12 consumption marts + publish;
   - US-13 anomalies, checked against `_manifest.json` expected spike/tamper/outage.
