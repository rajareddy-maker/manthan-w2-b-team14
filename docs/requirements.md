# GridPulse — Requirement Analysis (Phase 0)

Source: Track-B PRD "GridPulse – Smart Meter Telemetry Platform". Section refs: **PS** = problem statement, **SRC** = sources, **MH-n** = must-have bullet n, **DQ** = data quality rules, **PPE** = phase-by-phase expectations table.

## Functional requirements
| ID | Requirement | MoSCoW | PRD source |
|---|---|---|---|
| FR-01 | Ingest schema v1 events (meter_id, timestamp, energy Wh, status) from landed JSON files | Must | SRC, MH-1 |
| FR-02 | Ingest schema v2 events (+ voltage, firmware_version, energy in Wh or kWh) | Must | SRC, MH-1 |
| FR-03 | Preserve raw payload, and record the schema version + source file per event | Must | MH-1 |
| FR-04 | Convert all energy to kWh | Must | MH-2 |
| FR-05 | Remove duplicate events (same meter + timestamp) | Must | MH-2, PS |
| FR-06 | Order events per meter by reading time (handle out-of-order/late files) | Must | MH-2 |
| FR-07 | Mark missing 15-min intervals as gaps; never fill them | Must | MH-2 |
| FR-08 | Hourly and daily kWh per meter | Must | MH-3 |
| FR-09 | Hourly and daily kWh per feeder and per zone | Must | MH-3 |
| FR-10 | Monthly billing-ready table per meter | Must | MH-3 |
| FR-11 | Spike detection: z-score vs the meter's own history | Must | MH-4 |
| FR-12 | Suspected tamper: zero consumption 48 h while feeder neighbours are normal | Must | MH-4 |
| FR-13 | Outage: many meters on one feeder missing readings at the same time | Must | MH-4 |
| FR-14 | Time-series storage layout: date + zone partitioning and a file compaction approach | Must | MH-5 |
| FR-15 | Retention: raw 30 days, hourly 13 months; reasons recorded in an ADR | Must | MH-5 |
| FR-16 | Orchestrated daily run with retries | Must | MH-6 |
| FR-17 | Backfill for a date range | Must | MH-6 |
| FR-18 | Superset dashboard: feeder consumption, anomaly list, completeness % per zone, pipeline-health tab | Must | MH-7, PPE-Insight |
| FR-19 | DQ: meter_id exists in the meter master | Must | DQ-1 |
| FR-20 | DQ: energy reading is not negative | Must | DQ-2 |
| FR-21 | DQ: cumulative register never decreases unless a rollover is flagged | Must | DQ-3 |
| FR-22 | DQ: completeness per meter per day > 90%, otherwise a quality flag on that day | Must | DQ-4 |
| FR-23 | Synthetic data generator: 5,000 meters / 20 feeders / 6 zones, 15-min, v1+v2, configurable days, injected defects | Must | SRC |
| FR-24 | Ops metrics: ingest lag, completeness, duplicate rate, run duration | Must | PPE-Support |
| FR-25 | Alert on completeness drop | Must | PPE-Support |
| FR-26 | Backfill and rollback runbook, exercised once | Must | PPE-Support |
| FR-27 | Docker Compose (orchestrator, compute, storage, DB, Superset), CI with tests, one-command start | Must | PPE-Deployment |
| FR-28 | ADR on late-data handling and on the schema-evolution approach | Must | PPE-Architecture |
| FR-29 | Raw quarantine of rejected records with a reason code (viewable) | Should | DQ (derived) |
| FR-30 | Voltage quality view for v2 meters (min/max/avg per feeder) | Could | SRC (v2 fields) |

## Non-functional requirements
| ID | Category | Requirement |
|---|---|---|
| NFR-01 | Volume | 480k events/day; 43.2M events over 90 days (~100 MB/day JSON, ~15 MB/day Parquet). Demo: 7 days ≈ 3.36M events. |
| NFR-02 | Velocity | Readings every 15 min; gateways land files in hourly batches; daily processing |
| NFR-03 | Latency / SLA | Daily run for D-1 finished by 06:00 IST; one day's run ≤ 15 min on the dev laptop |
| NFR-04 | Freshness | Marts ≤ 1 day old; ingest lag (landing → bronze) tracked p50/p95 |
| NFR-05 | Late data | Late files ≤ 3 days absorbed automatically (lookback window); older via backfill |
| NFR-06 | Retention | Raw/bronze 30 days; hourly marts 13 months; daily/monthly marts kept indefinitely (assumption A7) |
| NFR-07 | Idempotency | Re-running any date or range gives identical row counts and totals |
| NFR-08 | Security | No secrets in git (.env); least-privilege DB roles (Superset read-only on marts); no customer PII stored (meter IDs only) |
| NFR-09 | Availability | Single-node dev; tasks retry 2× with 2-min delay; failures visible in pipeline-health tab |
| NFR-10 | Cost | ₹0 — local open source only; runs on 14 GB RAM (LITE profile) |
| NFR-11 | Accuracy | Aggregates reconcile to raw register deltas exactly (DECIMAL arithmetic) |
| NFR-12 | Time zone | All business time in Asia/Kolkata (IST); source timestamps are IST |

## Data source inventory
| Source | Type | Format | Frequency | Est. volume |
|---|---|---|---|---|
| Meter telemetry v1 | File (gateway drop) | JSONL: `meter_id, ts, energy_wh, status` | 15-min readings, hourly files | ~60% of meters → ~288k events/day |
| Meter telemetry v2 | File (gateway drop) | JSONL: `meter_id, ts, energy, unit, status, voltage, firmware_version, schema_version` | 15-min readings, hourly files | ~40% of meters → ~192k events/day |
| Meter master | File (reference, dbt seed) | CSV: `meter_id, feeder_id, zone_id, schema_version, unit, install_date, register_max_kwh` | On change | 5,000 rows |
| Feeder/zone master | File (dbt seed) | CSV: `feeder_id, zone_id, zone_name` | Static | 20 / 6 rows |
| Pipeline run metadata | Airflow + extractor | Postgres `ops.*` tables | Per run | ~10 rows/day |

## KPIs / metrics the dashboard must show
| KPI | Definition | Grain |
|---|---|---|
| Feeder consumption (kWh) | Σ interval kWh of the feeder's meters | hour / day, feeder, zone |
| Zone consumption (kWh) | Σ interval kWh per zone | day, zone |
| Billed kWh | Σ valid interval kWh per meter per IST month | month, meter |
| Completeness % | received distinct on-grid intervals ÷ expected (96 × meters × days) | day, meter / feeder / zone |
| Low-completeness meter-days | count of meter-days < 90% | day, zone |
| Anomaly count | count of spike / tamper / outage events | day, type, feeder |
| Duplicate rate % | duplicates dropped ÷ raw events | run / day |
| Ingest lag | landing file time − reading time (p50/p95, minutes) | run / day |
| Run duration | DAG run end − start (min) | run |
| Quarantine count | rejected records by reason | day, reason |

## Scope
**In scope:** everything FR-01…FR-29; synthetic data only; local Docker Compose deployment; CI on GitHub Actions; one Superset dashboard (4 tabs).
**Out of scope:** real meter/HES integration, Kafka streaming, Spark, cloud deployment (notes only), customer/tariff billing calculation (₹), real email/Slack delivery (alerts go to a log + an `ops.alerts` table), SSO.

## Assumptions
| ID | Assumption |
|---|---|
| A1 | `energy` is a cumulative register; interval consumption = delta between consecutive readings |
| A2 | Timestamps are IST (`+05:30` or naive); buckets/billing in Asia/Kolkata (confirmed by PO) |
| A3 | Each v2 event carries `schema_version: 2`; v1 events have no version field → inferred as 1 by field shape |
| A4 | Meter master is a static CSV seed with each meter's feeder, zone and register max (rollover point) |
| A5 | `status` ∈ {`OK`, `ROLLOVER`, `POWER_FAIL`, `ERROR`}; `ROLLOVER` marks a legitimate register wrap |
| A6 | Spike: z > 3 vs the meter's trailing 30-day intervals; Tamper: ≥ 192 zero intervals while ≥ 70% of feeder peers non-zero; Outage: ≥ 30% of feeder meters missing ≥ 2 consecutive intervals |
| A7 | Daily and monthly marts are small and kept indefinitely; only raw (30 d) and hourly (13 mo) have retention rules |
| A8 | Demo data = 7 days ending yesterday (IST); performance run = 30 days (scaled 10× vs one-day) |
| A9 | Alerts are written to `ops.alerts` + task logs (no real email/Slack in the hackathon) |
| A10 | One builder (this Claude session); team members own workstreams for review/QA; PO = Mahendra Umath |

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| R1 Host RAM (14 GB) exhausted by the stack | M | H | LITE profile; no Kafka/Spark; container memory limits; stop other stacks |
| R2 Airflow 3 / dbt / GX dependency clash | M | M | Separate venv for dbt+GX inside the Airflow image |
| R3 5-hour time box | H | H | Walking skeleton first; Must stories only; Could stories dropped first |
| R4 DuckDB single-writer lock contention | M | M | Airflow pool `duckdb` with 1 slot |
| R5 Anomaly thresholds give false positives | M | M | Crafted meter histories with expected flags; thresholds in dbt vars |
| R6 Large image pulls slow the first `make demo` | M | M | Reuse cached images; pinned tags |

## Final tech stack decision
| Tool | Decision | Justification |
|---|---|---|
| Airflow 3.3.2 (LocalExecutor) | Keep (version changed) | Orchestration + backfill; 2.x is EOL and 3.3.2 is cached locally (ADR-001) |
| Kafka | **Dropped** | PRD allows files; daily SLA; saves ~2 GB RAM (ADR-002) |
| Spark | **Dropped** | ~100 MB/day ≪ 10 GB/run threshold (ADR-002) |
| dbt Core 1.11 + dbt-duckdb | Keep | All transforms are SQL; tests + docs built in |
| DuckDB 2.0 + Parquet | Keep | Columnar, Hive-partitioned time-series lake; zero ops |
| PostgreSQL 16.16 | Keep | Multi-user serving for Superset + Airflow/Superset metadata |
| Great Expectations 1.25 | Keep | Layer DQ gates with checkpoint results as evidence |
| Superset 6.1.0 | Keep | Required BI layer |
| Docker Compose + GitHub Actions | Keep | One-command start + CI |
| Python 3.13 (runtime) / 3.14 (local tooling) | Changed from 3.11 | Matches the Airflow 3.3.2 image; uv could not be installed (ADR-001) |
