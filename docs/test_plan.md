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
| Local dev (cross-host re-run) | Ubuntu 26.04 venv (Python 3.14.4), DuckDB 2.0.1, dbt 1.12.7, no stack | Same demo set, seed 42; proves results do not depend on the OS |
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

## 9. Test case catalogue (every available test)
Scenario IDs (TC-…) are the requirement-level cases used in [test_results.md](test_results.md) and the [RTM](rtm.md). Each automated test below implements one or more of them. Latest status = the Ubuntu re-run of 27-Nov-2026 (see test_results.md §1); "stack" tests skip when Docker is down, and their last pass is from the Sprint 3 Windows run.

### 9.1 Unit tests — `pytest tests/unit` (no stack, 54 cases)
| File | Test | Cases | Verifies | Scenario | Req |
|---|---|---|---|---|---|
| test_generator.py | test_v1_line_is_valid_json | 1 | v1 payload shape (`energy_wh`, no version field) | TC-GEN-02 | FR-01, FR-23 |
| test_generator.py | test_v2_line_units | 2 | v2 payload in kWh and in Wh | TC-GEN-02 | FR-02 |
| test_generator.py | test_seeds_written | 1 | meter master + feeder/zone seeds | TC-GEN-02 | FR-23 |
| test_generator.py | test_landing_layout_and_schema_versions | 1 | `dt=` layout, v1 + v2 mix | TC-GEN-02 | FR-01, FR-02 |
| test_generator.py | test_timestamps_on_15_min_grid_except_injected | 1 | IST 15-min grid, only injected off-grid | TC-GEN-02 | NFR-12 |
| test_generator.py | test_defects_present | 1 | dups, gaps, unknown, negative, late, rollover injected | TC-GEN-02 | FR-23 |
| test_generator.py | test_crafted_anomalies_in_manifest | 1 | spike/tamper/outage ground truth written | TC-GEN-02 | FR-11…13 |
| test_generator.py | test_tamper_meter_register_is_flat | 1 | tamper meter register constant 48 h+ | TC-GEN-02 | FR-12 |
| test_generator.py | test_deterministic_for_same_seed / test_different_seed_differs | 2 | reproducibility | TC-GEN-02 | FR-23 |
| test_generator.py | test_install_dates_do_not_depend_on_wall_clock | 1 | DEF-012 regression | TC-GEN-02 | FR-23 |
| test_landing_to_bronze.py | test_zone_from_filename | 3 | zone partition key (incl. re-sent and unknown files) | TC-STO-01 | FR-14 |
| test_landing_to_bronze.py | test_every_line_preserved_with_lineage | 1 | schema_version, source_file, ingested_at per line | TC-ING-03 | FR-03 |
| test_landing_to_bronze.py | test_raw_payload_unchanged | 1 | raw payload byte-identical | TC-ING-03 | FR-03 |
| test_landing_to_bronze.py | test_reload_is_idempotent_and_one_file_per_partition | 1 | rerun = same rows, 1 file / partition | TC-IDEM-01 | NFR-07, FR-14 |
| test_landing_to_bronze.py | test_file_arrival_ts_from_mtime | 1 | arrival time for ingest lag | TC-OPS-01 | FR-24 |
| test_landing_to_bronze.py | test_empty_landing_date_is_noop | 1 | empty day does not fail | TC-ING-01 | FR-16 |
| test_landing_to_bronze.py | test_compact_partition_merges_files | 1 | compaction | TC-STO-01 | FR-14 |
| test_landing_to_bronze.py | test_landing_dates_sorted | 1 | deterministic processing order | TC-ING-01 | FR-06 |
| test_production_tasks.py | test_retention_drops_only_partitions_older_than_window | 1 | raw 30-day retention boundary | TC-STO-02 | FR-15 |
| test_production_tasks.py | test_ops_window_is_lookback_inclusive | 1 | 3-day lookback window | TC-ORC-01 | NFR-05 |
| test_production_tasks.py | test_ops_ddl_is_single_quote_free_do_block | 1 | ops DDL safe as one DO block | TC-OPS-01 | FR-24 |
| test_production_tasks.py | test_bronze_range_loads_only_dates_in_range | 1 | backfill date range | TC-ORC-02 | FR-17 |
| test_production_tasks.py | test_gx_gates_pass_clean_and_block_negative_energy | 2 | GX gate passes clean data, blocks negative energy | TC-DQ-02 | FR-20, US-14 |
| test_publish_to_postgres.py | test_swap_is_one_transaction_with_primary_key | 1 | atomic swap + PK | TC-PUB-01 | US-12 AC3 |
| test_publish_to_postgres.py | test_dsn_from_env / test_dsn_requires_password | 2 | config from env, no default secret | TC-SEC-01 | NFR-08 |
| test_publish_to_postgres.py | test_hourly_meter_fact_is_not_published | 1 | only serving marts are published | TC-PUB-01 | US-12 |
| test_publish_to_postgres.py | test_reconciled | 2 | rows + Σ kWh reconciliation check (pass and fail) | TC-PUB-01 | NFR-11 |
| test_alerting.py | test_build_alert_names_task_recipient_and_ist_date | 1 | alert content, IST date | TC-OPS-02 | FR-25 |
| test_alerting.py | test_email_disabled_without_smtp / test_email_sent_via_smtp_when_configured | 2 | e-mail path on/off | TC-OPS-02 | FR-25 |
| test_alerting.py | test_callback_records_and_never_raises | 1 | callback never masks the original failure | TC-OPS-02 | FR-25 |
| test_cli_entrypoints.py | test_generator_cli_writes_landing_seeds_manifest | 1 | generator CLI end to end (small config) | TC-GEN-01 | FR-23 |
| test_cli_entrypoints.py | test_config_from_env_and_overrides / test_config_rejects_invalid_topology | 4 | config validation | TC-GEN-01 | FR-23 |
| test_cli_entrypoints.py | test_retention_cli | 1 | retention CLI | TC-STO-02 | FR-15 |
| test_export_backlog.py | 5 tests (incl. 6 parametrised point values) | 10 | backlog → xlsx export | TC-ENV-02 | US-02 |

### 9.2 Crafted-history integration — `pytest tests/integration -m dbt` (landing → bronze → dbt on DuckDB, no stack, 13 cases)
| Test | Verifies | Scenario | Req |
|---|---|---|---|
| test_us10_ac1_units_converge_to_same_kwh | 1500 Wh (v1) = 1.5 kWh (v2) = 1500 Wh (v2) → 1.5000 kWh | TC-UNIT-01 | FR-04 |
| test_us10_ac2_triplicate_kept_once | 3 copies → 1 row, 2 counted as dups | TC-DUP-01 | FR-05 |
| test_us10_ac3_out_of_order_files_give_ordered_deltas | reversed files/lines → no false decreases | TC-ORD-01 | FR-06 |
| test_quarantine_reasons_and_snapping | reason codes; ±2 min snap, else quarantine | TC-DQ-05, TC-GRID-01 | FR-19, FR-20, FR-29 |
| test_naive_timestamps_are_ist | naive timestamps treated as IST | TC-TZ-01 | NFR-12 |
| test_us11_ac1_gaps_marked_and_delta_kept_once | 3 missing → 3 gap rows, next delta `gap_intervals = 3` | TC-GAP-01 | FR-07 |
| test_grid_is_complete | 96 slots per meter-day | TC-GAP-01 | FR-07 |
| test_us11_ac2_rollover_and_unflagged_decrease | ROLLOVER delta formula; unflagged decrease → NULL + flag | TC-DQ-03 | FR-21 |
| test_us12_quality_flags | < 90% → LOW_COMPLETENESS on that meter-day only | TC-DQ-04 | FR-22 |
| test_us12_ac1_billing_equals_register_span | billed kWh = register span | TC-BILL-01 | FR-10, NFR-11 |
| test_us13_ac1_spike_only_on_crafted_meter | spike flagged; control meters clean | TC-ANO-01 | FR-11 |
| test_us13_ac2_tamper_only_when_peers_active | tamper flagged; whole-feeder zero not flagged | TC-ANO-02 | FR-12 |
| test_us13_ac3_outage_needs_30pct_of_feeder | ≥ 30% → OUTAGE; 20–25% → none | TC-ANO-03 | FR-13 |

### 9.3 Stack integration — `pytest tests/integration` (needs `make up`; skips otherwise, 6 cases)
| Test | Verifies | Scenario | Req |
|---|---|---|---|
| test_publish_reconciles_and_is_idempotent | publish to scratch schema `marts_test`, reconcile, re-publish | TC-PUB-01/02 | US-12 AC3, NFR-07 |
| test_publish_cli_rejects_unknown_table | CLI input validation | TC-PUB-01 | US-12 |
| test_ops_metrics_written_for_a_run / test_ops_metrics_cli | `ops.pipeline_runs` metrics row | TC-OPS-01 | FR-24 |
| test_failure_alert_recorded_in_warehouse | CRITICAL row in `ops.alerts` | TC-OPS-02 | FR-25 |
| test_superset_dashboard_as_code_is_idempotent | dashboard rebuilt from code, same result | TC-UAT-18 | FR-18 |

### 9.4 dbt data tests — `dbt build` (70 tests on the 7-day set)
| Group | Count | Models |
|---|---|---|
| Schema tests (not_null, unique, accepted_values, relationships) | 63 | seeds 11 · staging 13 · intermediate 10 · marts 29 |
| Singular business-rule tests | 7 | `assert_stg_readings_unique_meter_ts` (TC-DUP-01) · `assert_intervals_unique_meter_slot` (TC-GAP-01) · `assert_deltas_non_negative` (TC-DQ-03) · `assert_register_span_reconciles` (TC-REC-01) · `assert_hourly_reconciles_to_staging_deltas` (TC-REC-01) · `assert_feeder_daily_equals_meter_daily` (TC-REC-02) · `assert_completeness_pct_in_range` (TC-DQ-04) |

### 9.5 Great Expectations suites — `data_quality/gx/run_checkpoint.py`
| Suite | Expectations | Data | Scenario | Req |
|---|---|---|---|---|
| sample | 5 | tests/fixtures/sample_readings.csv | TC-ENV-06 | US-04 |
| silver | 6 | daily facts (meter-day) | TC-DQ-06 | FR-20, FR-22, US-14 |
| gold | 5 | monthly billing | TC-DQ-07 | FR-10, US-14 |

### 9.6 Scripted / system / manual cases
| Scenario | How | Req |
|---|---|---|
| TC-ENV-01 system check | `bash scripts/system_check.sh` | NFR-10 |
| TC-ENV-08 smoke (9 checks) | `bash scripts/smoke_test.sh` | US-04, FR-27 |
| TC-REC-03 ground truth | anomalies, quarantine and totals vs `data/landing/_manifest.json` | FR-11…13, FR-19…20, FR-29 |
| TC-ORC-01 daily run | `gridpulse_daily` triggered, `-> success` | FR-16 |
| TC-ORC-02 backfill | `gridpulse_backfill` 2026-11-20..26, `-> success` | FR-17 |
| TC-OPS-03 drills | runbook backfill drill + rollback (pg_dump/pg_restore) drill | FR-26 |
| TC-OPS-02 failure drill | `gridpulse_alert_drill` must FAIL and record a CRITICAL alert | FR-25 |
| TC-DEP-01 one-command demo | `scripts/demo.sh` / `make demo` | FR-27 |
| TC-SEC-01 read-only BI role | `bi_reader` cannot create tables | NFR-08 |
| TC-MUT-01 mutation | break `tamper_peer_active_share` → negative control must fail | test quality |
| TC-PERF-01 10× volume | 70 days generated + backfill, timed | NFR-03 |
