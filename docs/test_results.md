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

## Defect log
| Defect ID | Found in | Severity | Description | Root cause | Fix | Re-test | Status |
|---|---|---|---|---|---|---|---|
| DEF-001 | TC-ENV-04 | Low | `test_export_backlog.py` errored at collection: `AttributeError: 'NoneType' object has no attribute '__dict__'` | Module loaded via `importlib.util.spec_from_file_location` was not registered in `sys.modules`; Python 3.14 `dataclasses` looks the module up there | Register module in `sys.modules` before `exec_module` | 10 passed | Closed |
| DEF-002 | TC-ENV-01 / `docker compose build` | High | Docker Desktop killed during image build (`Result: oom-kill`, peak 10.2 GB); a restart was OOM-killed again at 8 GB | Docker Desktop VM memory set to 8164 MiB on a 14.8 GB host with ~7.5 GB used by desktop apps → systemd-oomd kills the service | Reduce Docker Desktop memory to 6 GB and/or close heavy apps (needs host owner); build images one at a time | pending | Open |
