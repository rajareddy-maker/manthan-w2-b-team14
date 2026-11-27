# GridPulse — Product Backlog

Product Owner: **Mahendra Umath** · Scrum Master / builder: Claude (this session) · Team 14
Points: Fibonacci. Stories > 8 pts are split at refinement. Excel export: `make export-backlog` → `product_backlog.xlsx`.

## Epics
| Epic | Name | Sprint(s) |
|---|---|---|
| E1 | Inception & setup | S0 |
| E2 | Architecture, design & walking skeleton | S1 |
| E3 | Normalisation & consumption | S2 |
| E4 | Anomalies, quality & orchestration | S2, S3 |
| E5 | Analytics & testing | S3 |
| E6 | Deployment & operations | S4 |

## Release plan (27-Nov-2026, 5-hour time box, 6 people ≈ 30 person-hours)
| Sprint | Time (IST) | SDLC phases | Goal | Stories | Pts |
|---|---|---|---|---|---|
| S0 | 10:00–10:40 | 0, 1 | Requirements, ideation, backlog in Excel, stack running locally | US-01…US-05 | 21 |
| S1 | 10:40–11:20 | 2, 3 | Architecture + LLD signed off; walking skeleton via `make demo` | US-06…US-09 | 23 |
| S2 | 11:20–13:00 | 4 | Normalised intervals, consumption marts, anomaly flags | US-10…US-13 | 26 |
| S3 | 13:00–14:10 | 4, 5 | DQ gates, scheduled DAG + backfill, dashboard, tests executed | US-14…US-17 | 26 |
| S4 | 14:10–15:00 | 6, 7 | CI, ops metrics + alerts, runbook drill, handover | US-18…US-22 | 15 |

---

## US-01: Requirement analysis & ideation
**Epic:** E1 Inception & setup **Req IDs:** all FR/NFR
**Priority:** Must **Points:** 5 **Sprint:** S0 **Owner:** Mahendra Umath **Status:** In review

**Story**
As the PO, I want the PRD analysed into requirements, an RTM and an ideation document, so that scope is clear, traceable and the approach is justified.

**Acceptance criteria**
- AC1: Given the PRD, when docs/requirements.md is reviewed, then every must-have bullet and DQ rule maps to an FR ID with a PRD source reference.
- AC2: Given docs/ideation.md, when reviewed, then 3 options are compared in a weighted matrix and the chosen/rejected options are justified.
- AC3: Given docs/rtm.md, when reviewed, then every FR has a story, a design reference and a planned test case.

**Tasks**
| Task | Estimate (h) | Status |
|------|--------------|--------|
| FR/NFR, sources, KPIs, scope, risks | 0.5 | Done |
| Ideation doc + options matrix | 0.5 | Done |
| RTM skeleton | 0.25 | Done |

## US-02: Prioritised backlog and release plan (Markdown + Excel)
**Epic:** E1 Inception & setup **Req IDs:** —
**Priority:** Must **Points:** 3 **Sprint:** S0 **Owner:** Mahendra Umath **Status:** In review

**Story**
As the PO, I want a prioritised backlog and release plan in Markdown and Excel, so that I can track delivery.

**Acceptance criteria**
- AC1: Given product_backlog.md, when `make export-backlog` runs, then product_backlog.xlsx has one row per story with acceptance criteria, a frozen header, auto-filter and Status/Priority dropdowns.
- AC2: Given the release plan, when summed, then each sprint's points fit its capacity, and every Must FR maps to at least one story.

**Tasks**
| Task | Estimate (h) | Status |
|------|--------------|--------|
| Write stories + release plan | 0.5 | Done |
| scripts/export_backlog.py (openpyxl) | 0.25 | Done |

## US-03: System check script
**Epic:** E1 Inception & setup **Req IDs:** NFR-10
**Priority:** Must **Points:** 2 **Sprint:** S0 **Owner:** Raja Rao Reddy **Status:** In review

**Story**
As a data engineer, I want a system check script, so that I know my machine can run the stack.

**Acceptance criteria**
- AC1: Given a Linux host, when `scripts/system_check.sh` runs, then it prints OS, CPU, RAM, disk, virtualisation and tool versions in an Item | Found | Required | Status table.
- AC2: Given a missing or old tool, when the script runs, then that row shows MISSING/UPGRADE and the script exits non-zero.

**Tasks**
| Task | Estimate (h) | Status |
|------|--------------|--------|
| Write and run system_check.sh | 0.25 | Done |

## US-04: Full stack in Docker Compose
**Epic:** E1 Inception & setup **Req IDs:** FR-27
**Priority:** Must **Points:** 8 **Sprint:** S0 **Owner:** Raja Rao Reddy **Status:** In progress

**Story**
As a data engineer, I want the full stack in Docker Compose, so that every tool runs locally.

**Acceptance criteria**
- AC1: Given `make up`, when the stack starts, then Postgres, Airflow (api-server, scheduler, dag-processor) and Superset are all healthy.
- AC2: Given the running stack, when `make smoke` runs, then Postgres connects, the hello DAG succeeds, `dbt debug` passes, a GX checkpoint passes and Superset queries the warehouse.
- AC3: Given the compose file, when inspected, then every image is pinned and every service has a healthcheck and a memory limit.

**Tasks**
| Task | Estimate (h) | Status |
|------|--------------|--------|
| docker-compose.yml + Airflow/Superset Dockerfiles + init.sql | 1.0 | In progress |
| Hello DAG, dbt skeleton, GX sample checkpoint | 0.5 | In progress |
| smoke_test.sh + verification/troubleshooting doc | 0.5 | In progress |

## US-05: Repo skeleton, Makefile, linting, pre-commit
**Epic:** E1 Inception & setup **Req IDs:** FR-27
**Priority:** Must **Points:** 3 **Sprint:** S0 **Owner:** Raja Rao Reddy **Status:** In progress

**Story**
As a data engineer, I want a repo skeleton with Makefile, linting and pre-commit, so that standards are enforced from day one.

**Acceptance criteria**
- AC1: Given a fresh clone, when `make setup`, `make lint` and `make test` run, then all exit 0.
- AC2: Given the repo, when inspected, then CLAUDE.md (≤ 200 lines), .env.example, pinned requirements and a PR template with the DoD exist.

**Tasks**
| Task | Estimate (h) | Status |
|------|--------------|--------|
| Makefile, pyproject, requirements, pre-commit, PR template | 0.5 | In progress |

## US-06: Architecture and ADRs
**Epic:** E2 Architecture, design & walking skeleton **Req IDs:** FR-14, FR-15, FR-28
**Priority:** Must **Points:** 5 **Sprint:** S1 **Owner:** Mahendra Umath **Status:** To do

**Story**
As an architect, I want an architecture diagram and ADRs for partitioning, retention, late data and schema evolution, so that tool and storage choices are documented.

**Acceptance criteria**
- AC1: Given docs/architecture.md, when reviewed, then a Mermaid diagram shows sources → landing → bronze → silver → gold → serving → BI, with the orchestration and DQ layers.
- AC2: Given docs/adr/, when reviewed, then ADRs exist for the stack, partitioning + compaction + retention, late data and schema evolution, each with options, decision and consequences.
- AC3: Given the partitioning ADR, when the predicted query patterns are tested on bronze, then the partition-pruning results are recorded.

## US-07: Synthetic data generator with injected defects
**Epic:** E2 Architecture, design & walking skeleton **Req IDs:** FR-23, FR-01, FR-02
**Priority:** Must **Points:** 5 **Sprint:** S1 **Owner:** Sagar Kalthiya **Status:** To do

**Story**
As a data engineer, I want a synthetic generator for 5,000 meters / 20 feeders / 6 zones, so that the pipeline can be tested without real data.

**Acceptance criteria**
- AC1: Given `--days 7`, when the generator runs, then hourly JSONL files land under data/landing/dt=…/ with v1 and v2 events at 15-min IST timestamps.
- AC2: Given the defect config, when generated, then duplicates, out-of-order and late files, gaps, kWh-unit meters, unknown meters, negative values, rollovers, plus crafted spike/tamper/outage meters are present, and a manifest lists the expected anomalies.
- AC3: Given the same seed, when run twice, then the output is identical (deterministic).

## US-08: Bronze ingestion for both schema versions with compaction
**Epic:** E2 Architecture, design & walking skeleton **Req IDs:** FR-01, FR-02, FR-03, FR-14, NFR-07
**Priority:** Must **Points:** 5 **Sprint:** S1 **Owner:** Sagar Kalthiya **Status:** To do

**Story**
As a data engineer, I want landing files loaded into bronze Parquet partitioned by date and zone, with the raw payload and schema version kept, so that raw data is preserved and queryable by time.

**Acceptance criteria**
- AC1: Given landing files for a date, when the extractor runs, then bronze has a row per event with raw_payload, schema_version, source_file and ingested_at under dt=/zone=.
- AC2: Given the same date loaded twice, when counts are compared, then the bronze row count is unchanged (idempotent partition overwrite).
- AC3: Given many small hourly files, when compaction runs, then each dt/zone partition holds one Parquet file.

## US-09: LLD, star schema DDL and walking skeleton
**Epic:** E2 Architecture, design & walking skeleton **Req IDs:** FR-08…FR-13, FR-16, FR-18
**Priority:** Must **Points:** 8 **Sprint:** S1 **Owner:** Mahendra Umath **Status:** To do

**Story**
As a data engineer, I want an LLD (components, data model, interfaces) and a walking skeleton from one source to one chart, so that development has a clear spec and integration risk is retired early.

**Acceptance criteria**
- AC1: Given docs/lld.md, when reviewed, then it has the components (with repo paths), data model (ER + DDL + source-to-target mapping) and interfaces sections.
- AC2: Given `make demo`, when run, then one Airflow run moves data landing → bronze → mart → Postgres and a Superset chart shows it.

## US-10: Staging — kWh, IST, dedup, ordering
**Epic:** E3 Normalisation & consumption **Req IDs:** FR-04, FR-05, FR-06, NFR-12
**Priority:** Must **Points:** 5 **Sprint:** S2 **Owner:** Shantanu Kale **Status:** To do

**Story**
As an analyst, I want events normalised to kWh in IST with duplicates removed and readings ordered, so that every downstream number is consistent.

**Acceptance criteria**
- AC1: Given a v1 event of 1500 Wh and a v2 event of 1.5 kWh, when staged, then both show register_kwh = 1.5000.
- AC2: Given 3 copies of the same meter+timestamp, when staged, then 1 row remains and 2 are counted as duplicates.
- AC3: Given out-of-order arrival, when staged, then a per-meter sequence follows reading_ts order.

## US-11: Interval grid, gaps and register deltas
**Epic:** E3 Normalisation & consumption **Req IDs:** FR-07, FR-21
**Priority:** Must **Points:** 5 **Sprint:** S2 **Owner:** Shantanu Kale **Status:** To do

**Story**
As a billing analyst, I want each meter's 15-min grid with gaps marked and consumption derived from register deltas, so that missing data is visible and never invented.

**Acceptance criteria**
- AC1: Given a meter missing 3 intervals, when modelled, then 3 grid rows have is_gap = true, and the next delta carries gap_intervals = 3.
- AC2: Given a register decrease with status ROLLOVER, when modelled, then the delta = (register_max − prev) + current; without ROLLOVER the delta is NULL and the row is flagged.

## US-12: Consumption marts and publish to Postgres
**Epic:** E3 Normalisation & consumption **Req IDs:** FR-08, FR-09, FR-10, NFR-11
**Priority:** Must **Points:** 8 **Sprint:** S2 **Owner:** Shantanu Kale **Status:** To do

**Story**
As a billing analyst / network engineer, I want hourly and daily kWh per meter, feeder and zone plus a monthly billing table, so that I can bill and monitor load from ready tables.

**Acceptance criteria**
- AC1: Given marts, when Σ hourly kWh per meter-day is compared with Σ register deltas in staging, then the difference is 0.
- AC2: Given mart_billing_monthly, when queried, then each meter-month has billed_kwh, completeness_pct, gap_intervals and quality_flag.
- AC3: Given a pipeline run, when publishing completes, then the marts exist in Postgres warehouse.marts.

## US-13: Anomaly detection — spike, tamper, outage
**Epic:** E4 Anomalies, quality & orchestration **Req IDs:** FR-11, FR-12, FR-13
**Priority:** Must **Points:** 8 **Sprint:** S2 **Owner:** Rituja Kekatpure **Status:** To do

**Story**
As a revenue-protection / ops engineer, I want spike, suspected-tamper and outage flags, so that problems are found before customers complain.

**Acceptance criteria**
- AC1: Given the crafted spike meter, when detection runs, then a SPIKE row exists with z > 3, and control meters have none.
- AC2: Given a meter at 0 kWh for 48 h with normal feeder peers, then a TAMPER row exists. A whole-feeder zero period does not raise TAMPER.
- AC3: Given ≥ 30% of a feeder's meters missing the same intervals, then an OUTAGE row with start/end and the affected meter count exists.

## US-14: DQ rules, quarantine and GX gates
**Epic:** E4 Anomalies, quality & orchestration **Req IDs:** FR-19, FR-20, FR-21, FR-22, FR-29
**Priority:** Must **Points:** 5 **Sprint:** S3 **Owner:** Rituja Kekatpure **Status:** To do

**Story**
As a data steward, I want the PRD's DQ rules enforced with quarantine and GX checkpoints between layers, so that bad data stops before the marts.

**Acceptance criteria**
- AC1: Given unknown meter IDs and negative readings, when staged, then they land in quarantine with a reason code and are excluded from the marts.
- AC2: Given a meter-day < 90% complete, when marts build, then quality_flag = LOW_COMPLETENESS.
- AC3: Given a GX checkpoint failure on silver, when the DAG runs, then downstream tasks are skipped and an alert is recorded.

## US-15: Daily Airflow DAG with retries, backfill and retention
**Epic:** E4 Anomalies, quality & orchestration **Req IDs:** FR-15, FR-16, FR-17, NFR-05, NFR-07
**Priority:** Must **Points:** 5 **Sprint:** S3 **Owner:** Raja Rao Reddy **Status:** To do

**Story**
As a data engineer, I want a scheduled daily DAG with retries, a 3-day lookback, a date-range backfill and retention tasks, so that the pipeline runs unattended and can be replayed.

**Acceptance criteria**
- AC1: Given the schedule, when a run executes, then ingest → DQ → dbt → publish → anomalies succeed, with 2 retries per task.
- AC2: Given `make backfill START=… END=…`, when it runs, then every date in the range is reprocessed and the totals equal a fresh run.
- AC3: Given data older than 30 days (raw) or 13 months (hourly), when retention runs, then those partitions/rows are removed and logged.

## US-16: Superset network operations dashboard
**Epic:** E5 Analytics & testing **Req IDs:** FR-18
**Priority:** Must **Points:** 8 **Sprint:** S3 **Owner:** Ishika Sadhwani **Status:** To do

**Story**
As a network operations engineer, I want a dashboard with feeder consumption, anomaly list, completeness % per zone and pipeline health, so that I can monitor the network daily.

**Acceptance criteria**
- AC1: Given `make demo`, when Superset opens, then the GridPulse dashboard has 4 tabs with the defined metrics and date/zone/feeder filters.
- AC2: Given the repo, when inspected, then the dashboard is exported as code under superset/ and is imported automatically.

## US-17: Test plan, automated tests and published results
**Epic:** E5 Analytics & testing **Req IDs:** all Must FRs, NFR-03, NFR-11
**Priority:** Must **Points:** 8 **Sprint:** S3 **Owner:** Ishika Sadhwani **Status:** To do

**Story**
As QA / PO, I want unit, reconciliation, duplicate/out-of-order, anomaly and performance tests with a test plan and real results, so that each requirement can be signed off.

**Acceptance criteria**
- AC1: Given `make test`, when it runs, then the unit tests (unit conversion, gap detection) pass with ≥ 80% coverage on Python code.
- AC2: Given crafted meter histories, when anomaly tests run, then expected flags appear and control meters stay clean.
- AC3: Given docs/test_results.md, when reviewed, then it holds executed cases, a defect log and links to evidence under docs/evidence/.

## US-18: CI on every pull request + clean-start proof
**Epic:** E6 Deployment & operations **Req IDs:** FR-27
**Priority:** Must **Points:** 3 **Sprint:** S4 **Owner:** Raja Rao Reddy **Status:** To do

**Story**
As a data engineer, I want CI running lint, unit tests, dbt build and GX on every PR, plus a proven clean start, so that only tested code merges.

**Acceptance criteria**
- AC1: Given a PR, when CI runs, then lint → pytest → dbt build (DuckDB) → GX validate → docker build all pass.
- AC2: Given a fresh clone, when `make demo` runs, then the dashboard is live, and the run time is recorded.

## US-19: Ops metrics and completeness-drop alert
**Epic:** E6 Deployment & operations **Req IDs:** FR-24, FR-25
**Priority:** Must **Points:** 5 **Sprint:** S4 **Owner:** Rituja Kekatpure **Status:** To do

**Story**
As an on-call engineer, I want ingest lag, completeness, duplicate rate and run duration recorded, with an alert when completeness drops, so that I hear about problems first.

**Acceptance criteria**
- AC1: Given each DAG run, when it finishes, then ops.pipeline_runs has the lag p50/p95, duplicate rate, completeness % and duration.
- AC2: Given a zone whose completeness falls below 90%, when the run finishes, then an ops.alerts row and a WARNING log line are produced.

## US-20: Runbook, backfill and rollback drill, README, data dictionary
**Epic:** E6 Deployment & operations **Req IDs:** FR-26
**Priority:** Must **Points:** 3 **Sprint:** S4 **Owner:** Ishika Sadhwani **Status:** To do

**Story**
As a new team member, I want a README, data dictionary and ops runbook with a practised backfill and rollback, so that I can run and maintain the platform.

**Acceptance criteria**
- AC1: Given docs/runbook.md, when the backfill and rollback steps are executed once, then the output is saved as evidence.
- AC2: Given README.md, when followed on a fresh clone, then `make demo` gives a live dashboard in < 15 min.

## US-21: Voltage quality view for v2 meters
**Epic:** E6 Deployment & operations **Req IDs:** FR-30
**Priority:** Could **Points:** 2 **Sprint:** S4 **Owner:** Sagar Kalthiya **Status:** To do

**Story**
As a network engineer, I want min/max/avg voltage per feeder per day from v2 meters, so that I can see voltage quality issues.

**Acceptance criteria**
- AC1: Given v2 events, when marts build, then mart_feeder_voltage_daily has min/avg/max voltage and the reporting meter count.

## US-22: Retrospective, roadmap and artifact checklist
**Epic:** E6 Deployment & operations **Req IDs:** —
**Priority:** Should **Points:** 2 **Sprint:** S4 **Owner:** Mahendra Umath **Status:** To do

**Story**
As the PO, I want a retrospective, known limitations, future roadmap and a confirmed artifact checklist, so that next steps are agreed.

**Acceptance criteria**
- AC1: Given docs/PROGRESS.md, when the project ends, then it lists the retro notes, limitations and enhancements, and every hackathon artifact is confirmed present and current.
