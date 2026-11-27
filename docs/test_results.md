# Test Results

> Living document. Only real executed results are recorded here. Full execution summary and exit-criteria checklist are produced in Sprint 3 (Phase 5).

## Executed so far (Sprint 0)
| Test case | Requirement | Command | Expected | Actual | Status | Evidence |
|---|---|---|---|---|---|---|
| TC-ENV-01 | NFR-10 | `make system-check` | all OK | all OK except Docker daemon (Docker Desktop OOM-killed) | ❌ → see DEF-002 | [system_check.txt](evidence/sprint_0/system_check.txt) |
| TC-ENV-02 | US-02 | `make export-backlog` | 22 stories exported | `stories=22 points=111` | ✅ | [export_backlog.txt](evidence/sprint_0/export_backlog.txt) |
| TC-ENV-03 | US-05 | `make lint` | ruff + black clean | `All checks passed!` / `10 files would be left unchanged` | ✅ | — |
| TC-ENV-04 | US-05 | `make test` | pass, ≥ 80% cov | 10 passed, 82% coverage | ✅ | [pytest.txt](evidence/sprint_0/pytest.txt), [coverage.xml](evidence/coverage.xml) |
| TC-ENV-05 | US-04 | `dbt debug` (local venv) | All checks passed | `All checks passed!` | ✅ | [dbt_debug_local.txt](evidence/sprint_0/dbt_debug_local.txt) |
| TC-ENV-06 | US-04 | GX sample checkpoint (local venv) | PASSED | `success=True evaluated=5 successful=5` | ✅ | [gx_sample_local.txt](evidence/sprint_0/gx_sample_local.txt) |
| TC-ENV-07 | US-04 | `make smoke` (stack) | 9 checks pass | not run — blocked by DEF-002 | ⏸ Blocked | — |

## Executed in Sprint 1 (Windows 11 host, local venv, Python 3.14.5, DuckDB 2.0.1, dbt 1.12.7)
| Test case | Requirement | Command | Expected | Actual | Status | Evidence |
|---|---|---|---|---|---|---|
| TC-GEN-01 | FR-23 | `python -m ingestion.generator --days 7` | 5,000 meters × 7 days, v1+v2, all defect classes | 3,392,136 lines, 1,023 files, 15 s; every defect class > 0 in manifest | ✅ | [generator_run.txt](evidence/sprint_1/generator_run.txt) |
| TC-GEN-02 | FR-23 | `pytest tests/unit/test_generator.py` | deterministic per seed; defects + crafted anomalies present | 13 passed | ✅ | [pytest.txt](evidence/sprint_1/pytest.txt) |
| TC-ING-01/02 | FR-01, FR-02 | `python -m ingestion.extractors.landing_to_bronze --all` | v1 + v2 rows in bronze | v1 2,020,251 · v2 1,371,882 · invalid 3 | ✅ | [bronze_checks.txt](evidence/sprint_1/bronze_checks.txt) |
| TC-ING-03 | FR-03 | same + `pytest tests/unit/test_landing_to_bronze.py` | every line kept with raw_payload, schema_version, source_file, ingested_at | bronze rows 3,392,136 = landed lines 3,392,136; payload byte-identical (unit test) | ✅ | [bronze_checks.txt](evidence/sprint_1/bronze_checks.txt) |
| TC-IDEM-01 (bronze) | NFR-07 | reload `dt=2026-11-23` twice | same rows + payload hash | (482931, 4451049293925477286056492) before = after | ✅ | [bronze_checks.txt](evidence/sprint_1/bronze_checks.txt) |
| TC-STO-01 | FR-14 | pruning query + file count | 1 file per dt/zone; pruning by dt/zone | 48 files / 48 partitions; 48 → 6 → 1 files scanned | ✅ | [bronze_checks.txt](evidence/sprint_1/bronze_checks.txt) |
| TC-UNIT-01 | FR-04 | staging vs source per unit family | register_kwh exact for Wh and kWh | v1 Wh 2,018,747/2,018,747 · v2 Wh 952,165/952,165 · v2 kWh 419,704/419,704 exact | ✅ | [staging_vs_manifest.txt](evidence/sprint_1/staging_vs_manifest.txt) |
| TC-DUP-01 | FR-05 | dbt singular test + manifest | (meter_id, reading_ts) unique; dups dropped = injected | test PASS; 43,439 dropped = 9,936 in-file + 33,535 re-sent − 32 re-sent unknown-meter rows (quarantined instead) | ✅ | [dbt_build.txt](evidence/sprint_1/dbt_build.txt) |
| TC-DQ-01 | FR-19 | quarantine `unknown_meter` | 1,440 injected (+ re-sent copies) | 1,472 = 1,440 originals + 32 in re-sent files | ✅ | [staging_vs_manifest.txt](evidence/sprint_1/staging_vs_manifest.txt) |
| TC-DQ-02 | FR-20 | quarantine `negative_energy` | 25 | 25 | ✅ | same |
| TC-DQ-05 | FR-29 | quarantine reasons + reconciliation | bronze = kept + dups + quarantined | 3,392,136 = 3,347,177 + 43,439 + 1,520 | ✅ | same |
| TC-GRID-01 | CLAUDE.md grid rule | snapped / off-grid | 40 snapped (+1 min), 20 quarantined (+7 min) | 40 / 20 | ✅ | same |
| TC-DBT-01 | US-09 | `dbt build` | all seeds, models, tests pass | PASS=36 WARN=0 ERROR=0 | ✅ | [dbt_build.txt](evidence/sprint_1/dbt_build.txt) |
| TC-ENV-04 (S1) | US-05 | `pytest tests/unit --cov` | pass, ≥ 80% cov | 31 passed, 90% coverage | ✅ | [pytest.txt](evidence/sprint_1/pytest.txt) |
| TC-ENV-03 (S1) | US-05 | ruff + black --check + sqlfluff | clean | All checks passed / 18 files unchanged / sqlfluff All Finished (0 violations) | ✅ | — |
| TC-ENV-07 | US-04, US-09 AC2 | `make smoke`, publish to Postgres, Superset chart | stack healthy | not run: no Docker on this host (DEF-002) | ⏸ Blocked | — |

## Executed in Sprint 2 (Windows 11 host, local venv; full 7-day data set unless noted)
| Test case | Requirement | Command | Expected | Actual | Status | Evidence |
|---|---|---|---|---|---|---|
| TC-UNIT-01 (crafted) | FR-04, US-10 AC1 | `make test-dbt` | v1 1500 Wh = v2 1.5 kWh = v2 1500 Wh → 1.5000 | equal | ✅ | [pytest_dbt_crafted.txt](evidence/sprint_2/pytest_dbt_crafted.txt) |
| TC-DUP-01 (crafted) | FR-05, US-10 AC2 | same | 3 copies → 1 kept, ranks 2–3 dropped | as expected | ✅ | same |
| TC-ORD-01 | FR-06, US-10 AC3 | same (files written newest first, lines reversed) | no false register decreases | only B2 (crafted reset) flagged | ✅ | same |
| TC-GAP-01 | FR-07, US-11 AC1 | same + full set | 3 missing → 3 gap rows, next delta gap_intervals = 3 | as expected; full set 17,823 gaps in 3,360,000 grid rows | ✅ | same, [intervals_vs_manifest.txt](evidence/sprint_2/intervals_vs_manifest.txt) |
| TC-DQ-03 | FR-21, US-11 AC2 | same | ROLLOVER → (max − prev) + cur; other decrease → NULL + flag | as expected; flagged meters = manifest (3/3) | ✅ | same |
| TC-REC-01 | FR-08, NFR-11, US-12 AC1 | `dbt build` singular tests | Σ hourly = Σ staging deltas per meter-day; register span exact | PASS (both) | ✅ | [dbt_build.txt](evidence/sprint_2/dbt_build.txt) |
| TC-REC-02 | FR-09 | `dbt build` | feeder = zone = billing = meter totals | PASS | ✅ | same |
| TC-BILL-01 | FR-10, US-12 AC2 | crafted | billed kWh = register span; quality flags | as expected | ✅ | [pytest_dbt_crafted.txt](evidence/sprint_2/pytest_dbt_crafted.txt) |
| TC-DQ-04 | FR-22 | crafted | 15 missing on one day → LOW_COMPLETENESS for that meter-day only | as expected | ✅ | same |
| TC-ANO-01 | FR-11, US-13 AC1 | full set + crafted | crafted spikes flagged, controls clean | 5/5, 0 false positives (with ADR-006 guard) | ✅ | [anomalies_vs_manifest.txt](evidence/sprint_2/anomalies_vs_manifest.txt) |
| TC-ANO-01b | FR-11 | rule measurement | z > 3 alone is usable | **34,932 intervals on 4,998 meters flagged** → unusable without a guard | ❌ → ADR-006 | [spike_rule_measurement.txt](evidence/sprint_2/spike_rule_measurement.txt) |
| TC-ANO-02 | FR-12, US-13 AC2 | full set + crafted | tamper meters flagged; whole-feeder zero not flagged | 3/3, 0 false positives; flat feeder F3 silent | ✅ | same |
| TC-ANO-03 | FR-13, US-13 AC3 | full set + crafted | ≥ 30% missing for ≥ 2 intervals → OUTAGE; 20–25% → none | FDR-10, 8 intervals (102 meters); 20% control silent | ✅ | same |
| TC-MUT-01 | test quality | set `tamper_peer_active_share: 0.0` | negative-control test fails | `1 failed` | ✅ | — |
| TC-DBT-02 | all models | `dbt build` (full) | all pass | PASS=84 in 62 s | ✅ | [dbt_build.txt](evidence/sprint_2/dbt_build.txt) |
| TC-ENV-04 (S2) | US-05 | `pytest tests --cov` | pass, ≥ 80% coverage | 44 passed, 90% | ✅ | [pytest.txt](evidence/sprint_2/pytest.txt) |
| TC-PUB-01 | US-12 AC3 | publish marts → Postgres | tables in warehouse.marts | not run: no Postgres/Docker on host | ⏸ Blocked | — |

## Executed in Sprint 3 (Windows 11 host, Docker Desktop 29.9.3, everything in containers)
| Test case | Requirement | Command | Expected | Actual | Status | Evidence |
|---|---|---|---|---|---|---|
| TC-DEP-00 | FR-27, US-04 AC3 | `docker compose build` (one image at a time) | images build | superset 12 s; airflow 6 m 49 s (`duckdb 2.0.1 gx 1.25.0`) | ✅ | [build_airflow.txt](evidence/sprint_3/build_airflow.txt), [build_superset.txt](evidence/sprint_3/build_superset.txt) |
| TC-ENV-07 | US-04 AC1 | `docker compose up -d --wait` | all services healthy | 5 services healthy + 2 init exited 0 in 1 m 39 s; ~1.05 GB RAM in use | ✅ | [compose_up.txt](evidence/sprint_3/compose_up.txt) |
| TC-ENV-08 | US-04 AC2 | `bash scripts/smoke_test.sh` | 9 checks pass | `RESULT: 9 passed, 0 failed` | ✅ | [smoke_test.txt](evidence/sprint_3/smoke_test.txt) |
| TC-SEC-01 | NFR-08 | `bi_reader` tries `create table marts.x` | refused | refused (permission denied) | ✅ | — |
| TC-PIPE-01 | FR-27, US-23 | generate → bronze → `dbt build` → publish inside `airflow-scheduler` (Py 3.13, Linux) | exit 0, same totals as local | run 1: exit 0 in 225 s (58 + 98 + 65 + 4). Run 2 (after DEF-012 fix): generator ×2 hash-identical, bronze 64 s, `dbt build` PASS=84 in 69 s, publish 2 s; 3,392,136 lines; 445,848.1140 kWh | ✅ | [pipeline_in_docker.txt](evidence/sprint_3/pipeline_in_docker.txt) |
| TC-PUB-01 | US-23 AC1 | `python -m ingestion.publish.to_postgres` | 7 marts in `warehouse.marts`; rows and Σ kWh equal | 7/7 `reconciled=True`; `numeric(18,4)`; primary key on every table | ✅ | same |
| TC-PUB-02 | US-23 AC2 | publish twice (host, then container) | identical counts and totals | identical | ✅ | same |
| TC-UAT-23 | US-23 AC3 | `python scripts/superset_first_chart.py` | dataset + chart; chart query returns the mart | 42 rows, 445,848.1140 kWh, also after re-publish | ✅ | [superset_first_chart.txt](evidence/sprint_3/superset_first_chart.txt), [superset_chart_after_republish.txt](evidence/sprint_3/superset_chart_after_republish.txt) |
| TC-ENV-04 (S3) | US-05 | `pytest tests/unit` | pass | 37 passed | ✅ | — |

## Defect log
| Defect ID | Found in | Severity | Description | Root cause | Fix | Re-test | Status |
|---|---|---|---|---|---|---|---|
| DEF-001 | TC-ENV-04 | Low | `test_export_backlog.py` errored at collection: `AttributeError: 'NoneType' object has no attribute '__dict__'` | Module loaded via `importlib.util.spec_from_file_location` was not registered in `sys.modules`; Python 3.14 `dataclasses` looks the module up there | Register module in `sys.modules` before `exec_module` | 10 passed | Closed |
| DEF-002 | TC-ENV-01 / `docker compose build` | High | Docker Desktop killed during image build (`Result: oom-kill`, peak 10.2 GB); a restart was OOM-killed again at 8 GB | Docker Desktop VM memory set to 8164 MiB on a 14.8 GB host with ~7.5 GB used by desktop apps → systemd-oomd kills the service | Reduce Docker Desktop memory to 6 GB and/or close heavy apps (needs host owner); build images one at a time | Re-test on Windows host (S3): built one at a time, smoke 9/9 | Closed (stack runs on Sagar's Windows host; Ubuntu host not re-tested) |
| DEF-003 | TC-GEN-02 | Low | Generator test expected 10 off-grid events, got 11 | Test counted event lines; an injected event inside a gateway re-sent (`-r1`) file appears twice | Assert on distinct (meter_id, ts); same fix applied to the negative-value assertion | 31 passed | Closed |
| DEF-004 | TC-ENV-03 (S1) | Low | `sqlfluff lint`: "'env_var' is undefined" on `stg_meter__readings_validated.sql` | sqlfluff jinja templater has no dbt `env_var` builtin (used by the `bronze_meter_readings` macro) | Stub `env_var` macro in `[tool.sqlfluff.templater.jinja.macros]` | 0 violations | Closed |
| DEF-005 | Sprint 1 setup | Medium | Windows build host has no `make`, no `docker` CLI on PATH and no git identity | Build host changed from Ubuntu (Raja) to Windows (Sagar) | Repo-local git identity set; Makefile uses `.venv/Scripts` on Windows; Docker Desktop found in `%LOCALAPPDATA%` and put on PATH; make targets documented as Git Bash equivalents (docs/setup.md §2b) | stack up, smoke 9/9 | Closed (GNU make still not installed — documented workaround) |
| DEF-006 | Sprint 2 push | High | `git push` → 403: `sagarkalthiya-sudo` has only read access to `rajareddy-maker/manthan-w2-b-team14` | Repo owned by Raja; Sagar is not a collaborator | Repo owner (Raja) added `sagarkalthiya-sudo` as collaborator | push of 10 branches succeeded | Closed |
| DEF-007 | TC-ANO-01b | High | Spike rule (z > 3 vs trailing 30 d) flags 4,998 of 5,000 meters | Daily load shape plus noise push normal peaks above 3σ; 3σ base rate on 3.4M intervals | ADR-006: add guard kWh ≥ 8 × trailing mean | 5/5 found, 0 false positives | Closed (ADR-006 accepted) |
| DEF-008 | Sprint 2 harness | Low | Crafted tests errored: "Can't open a connection to same database file with a different configuration" | In-process `dbtRunner` keeps the DuckDB connection open | Run dbt in a subprocess | 13 passed | Closed |
| DEF-009 | TC-ENV-07 prep | High | All tracked files had CRLF in the Windows working copy (incl. `infra/postgres/init.sh`); `.env` came out with unreplaced `change_me` secrets | Checkout predates `.gitattributes` with `core.autocrlf=true`; `init_env.sh` patterns did not match lines ending in `\r`; Git Bash `grep` hides `\r` | Converted tracked container files to LF (no content diff); `init_env.sh` strips `\r` and uses UID 50000 off Linux | `.env` 0 placeholders; postgres-init ran | Closed |
| DEF-010 | TC-PUB-01 | Medium | Publish failed in turn: read-only attach, "cannot insert multiple commands into a prepared statement", wrong cache function name | Lake file opened read-only made `pg` read-only; `postgres_execute` prepares its SQL; function is `postgres_clear_cache` | In-memory DuckDB + `attach … (read_only)`; swap as one `DO $$ … $$` block; correct call | 7/7 reconciled | Closed |
| DEF-011 | TC-ENV-08 | Low | `docker compose exec … /opt/...` args mangled to `C:/Program Files/Git/opt/...` | Git Bash MSYS path conversion | `export MSYS_NO_PATHCONV=1` in container-exec scripts | 9/9 | Closed |
| DEF-012 | TC-PIPE-01 | Medium | Re-running the generator later the same day changed `install_date` in `meter_master.csv` (all other columns identical) | `fake.date_between("-8y", "-1y")` is relative to the wall clock; the S1 determinism test ran both runs within seconds | Anchor the range to `cfg.end_date` (29-Feb safe); regression test `test_install_dates_do_not_depend_on_wall_clock` | 12 generator tests pass; double run in Docker hash-identical (see pipeline_in_docker.txt) | Closed |
