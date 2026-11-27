# GridPulse — Progress

**Current sprint:** S2 (Phase 4) — in review, awaiting PO approval (+ ADR-006 decision) · **Next:** S3 (Phases 4 + 5)
**PO:** Mahendra Umath · **Builder:** Claude session · Last update: 27-Nov-2026 (S1 + S2 built on Sagar Kalthiya's Windows 11 host)
S0 and S1 were APPROVED by the PO on 27-Nov-2026 (relayed by Sagar Kalthiya).

## Phase status
| Phase | Sprint | Status |
|---|---|---|
| 0 Requirements | S0 | Done — approved |
| 1 Environment | S0 | Partial — local toolchain verified on both hosts; Docker stack blocked (DEF-002, DEF-005) |
| 2 Architecture | S1 | Done — approved (ADR-003/004/005 accepted; ADR-006 proposed in S2) |
| 3 Detailed design | S1 | Done — approved; LLD updated in S2 |
| 4 Development | S1–S3 | S2 done locally: staging, interval grid, consumption marts, anomalies. Missing: Postgres publish, DAG, GX gates, dashboard |
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

## Branches (stacked, committed locally — NOT pushed: DEF-006)
`main` ← `feature/US-01-inception-docs` ← `US-07-data-generator` ← `US-08-bronze-ingestion` ← `US-06-architecture-adrs` ← `US-09-lld-walking-skeleton` ← `US-11-interval-grid` ← `US-12-consumption-marts` ← `US-13-anomaly-detection` ← `US-10-staging-acceptance-tests` (all prefixed `feature/`)

## Decisions (ADR log)
| ADR | Decision |
|---|---|
| ADR-001 | Airflow 3.3.2 LocalExecutor; project venv `/opt/gridpulse-venv` in image; runtime Py 3.13, local tooling Py 3.14 |
| ADR-002 | No Kafka, no Spark — files + DuckDB/Parquet (LITE profile) |
| ADR-003 | Bronze partitioned by **arrival** `dt` + `zone`; 1 file per partition; retention raw 30 d, hourly 13 mo |
| ADR-004 | Daily run for D reloads landing `[D−3, D+1]`, rebuilds intervals `[D−3, D]`; older → backfill DAG + alert |
| ADR-005 | Schema-on-read: raw payload in bronze, one CTE per version in staging, unknown → quarantine |
| ADR-006 (proposed) | Spike = z > 3 **and** kWh ≥ 8 × trailing mean (z alone flags 4,998 of 5,000 meters) |

## Open blockers
- **DEF-002 / DEF-005:** no Docker stack and no `make` on the Windows host. This blocks the Postgres publish (US-12 AC3), Superset (US-09 AC2, US-16) and the Airflow DAG run (US-15).
- **DEF-006:** push refused. `sagarkalthiya-sudo` needs Write access to `rajareddy-maker/manthan-w2-b-team14`.

## Next steps
1. PO Sprint 2 review: APPROVED, plus a decision on ADR-006.
2. Raja grants collaborator access, then push all branches and open stacked PRs.
3. Get the Docker stack up (Docker Desktop + make on Windows, or the Ubuntu host).
4. Sprint 3:
   - US-23 (proposed): publish marts → Postgres + the US-09 AC2 chart;
   - US-14 GX gates;
   - US-15 DAG with 3-day incremental window + backfill + retention;
   - US-16 Superset dashboard;
   - US-17 test plan.
