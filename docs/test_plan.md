# GridPulse — Test Plan (Phase 5, US-17)

Owner: Ishika Sadhwani (QA) · Approver: Mahendra Umath (PO) · Executed results: [test_results.md](test_results.md) · Evidence: `docs/evidence/`

## 1. Scope
**In scope (by Req ID):**

| Area | Requirements |
|---|---|
| Ingestion | FR-01…03 |
| Normalisation | FR-04…07 |
| Consumption marts | FR-08…10 |
| Anomalies | FR-11…13 |
| Storage layout and retention | FR-14…15 |
| Orchestration and backfill | FR-16…17 |
| Dashboard | FR-18 |
| DQ rules | FR-19…22, FR-29 |
| Generator | FR-23 |
| Ops metrics and alerts | FR-24…25 |
| Runbook drills | FR-26 |
| Deployment | FR-27 |
| Voltage | FR-30 |
| Non-functional | NFR-03 (SLA), NFR-07 (idempotency), NFR-08 (security), NFR-11 (accuracy), NFR-12 (time zone) |

**Out of scope:**

| Excluded | Reason |
|---|---|
| Kafka and Spark tests | Both dropped by ADR-002 |
| Real HES/meter integration | Synthetic data only |
| Cloud deployment | Local Compose only |
| Email/Slack delivery | Alerts go to `ops.alerts` (A9) |
| Browser UI automation of Superset | Charts are verified through the Superset API |

## 2. Test approach
| Level / type | Tool | What | Automated | Command |
|---|---|---|---|---|
| Unit | pytest + pytest-cov | Generator, extractor, retention, publisher, ops metrics, GX gate logic, backlog exporter | Yes | `pytest tests/unit --cov` |
| dbt schema tests | dbt | not_null, unique, accepted_values, relationships on every model | Yes | `dbt build` |
| dbt business-rule tests | dbt singular | Unique dedup key; non-negative deltas; register-span reconciliation; Σ hourly = Σ staging deltas; feeder = zone = billing totals; completeness 0–100 | Yes | `dbt build` |
| Crafted histories (integration) | pytest + dbt (DuckDB) | One meter per rule, including negative controls (whole-feeder zero, 20–25% missing) | Yes | `pytest tests/integration -m dbt` |
| Data quality | Great Expectations | `silver` (daily facts) and `gold` (billing) suites; gate before publish | Yes, in the DAG | `run_checkpoint.py --suite silver --suite gold` |
| Ground-truth reconciliation | DuckDB SQL vs `_manifest.json` | Every injected defect and anomaly found, with no false positives | Scripted | `docs/evidence/sprint_*/…_vs_manifest.txt` |
| Integration / E2E | Airflow + Docker | `gridpulse_backfill` and `gridpulse_daily` runs; publish reconciliation; dashboard data checks | Yes | `scripts/demo.sh` |
| Smoke | bash | 9 service checks | Yes | `scripts/smoke_test.sh` |
| Performance | timed runs | 7-day run vs SLA (≤ 15 min per day of data); 10× volume (70 days) | Manual trigger | `python -m ingestion.generator --days 70` + backfill |
| Mutation check | manual | Break a threshold → the negative-control test must fail | Manual | see TC-MUT-01 |
| UAT | PO | One case per FR, mapped in the RTM | Manual | [rtm.md](rtm.md) |

## 3. Environments and test data
| Environment | Where | Data |
|---|---|---|
| Local dev | Windows 11 venv (Python 3.14) and DuckDB | Crafted fixtures; small generator configs (60–120 meters) |
| Stack | Docker Desktop: Airflow 3.3.2 (Python 3.13), Postgres 16.16, Superset 6.1.0 | Demo set: 5,000 meters × 7 days = 3,392,136 events, seed 42 |
| CI | GitHub Actions, ubuntu-24.04 | Unit + crafted dbt tests (no stack) |
| Performance | Docker stack | 10× = 70 days ≈ 34M events |

Ground truth for every data set is `data/landing/_manifest.json`, written by the generator.

## 4. Risks
| Test risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Host RAM (Docker VM 7.65 GB) is exhausted at 10× volume | M | H | Run performance tests with the stack otherwise idle; DuckDB `memory_limit` 1.5 GB |
| Bind-mounted repo is slow (OneDrive) | H | M | Timings recorded as-is; production keeps `data/` on a named volume |
| Statistical anomaly rules give flaky results | M | M | Crafted margins (≥ 14× spikes); fixed seeds; negative controls |
| Time-box (hackathon day) | H | H | Must requirements tested first; Could items last |

## 5. Entry criteria
- The stack is healthy (`docker compose up --wait`) and `smoke_test.sh` passes 9/9.
- The code is merged to `main`.
- Lint is clean.
- Test data is generated with the fixed seed.
- Requirements are frozen for the sprint.

## 6. Exit criteria
- 100% of Must FRs have a passing test in the RTM.
- ≥ 80% Python coverage.
- Zero open Critical/High defects; every Medium defect triaged.
- 7-day run within the SLA, and the 10× run recorded.
- CI green on the PR.
- UAT signed off by the PO.

## 7. Defect management
| Severity | Definition | Response |
|---|---|---|
| Critical | Wrong billed kWh, data loss or stack down | Fix before any merge |
| High | A rule produces wrong flags or a pipeline stage fails | Fix within the sprint |
| Medium | Workaround exists, or tooling/platform issue | Triage at standup |
| Low | Cosmetic or test-only issue | Backlog |

Every defect is logged in `test_results.md` (ID, test, severity, root cause, fix, re-test). It is closed only after a re-test with real output.

## 8. Schedule and responsibilities
| Sprint | Tests | Owner |
|---|---|---|
| S0 | Environment, system check, lint, sample GX | Raja Rao Reddy |
| S1 | Generator, bronze, staging reconciliation | Sagar Kalthiya |
| S2 | Grid, marts, anomaly crafted histories, mutation | Shantanu Kale, Rituja Kekatpure |
| S3 | Stack smoke, publish, DAG runs, GX gates, dashboard, drills, performance | Raja Rao Reddy, Ishika Sadhwani |
| UAT | One case per FR via the RTM | Mahendra Umath |
