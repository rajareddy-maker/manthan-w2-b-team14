# GridPulse — Operations Runbook (US-20)

**Audience:** on-call data engineers. **Stack:** Docker Compose project `gridpulse`:
- Airflow 3.3.2 (`localhost:8080`)
- Postgres 16.16 (`localhost:5433`, DB `warehouse`)
- Superset 6.1.0 (`localhost:8088`)

**Credentials:** only in `.env`. Never paste them into tickets or chat.

**On Windows (Git Bash), first run:**
```bash
export PATH="$LOCALAPPDATA/Programs/DockerDesktop/resources/bin:$PATH" MSYS_NO_PATHCONV=1
```
On Linux, `make <target>` wraps the same commands.

## 1. Start, stop, verify
| Action | Command |
|---|---|
| Start + wait healthy | `docker compose up -d --wait --wait-timeout 900` |
| Verify every service | `bash scripts/smoke_test.sh` (expect `RESULT: 9 passed, 0 failed`) |
| Stop (keep data) | `docker compose down` |
| Status / logs | `docker compose ps` · `docker compose logs -f --tail 100 <service>` |
| Full demo from a fresh clone | `bash scripts/demo.sh` |

## 2. Daily operation
`gridpulse_daily` runs at **01:30 IST** for logical date **D = yesterday (IST)**. The tasks run in this order:

| # | Task | What it does |
|---|---|---|
| 1 | `ingest_bronze` | Reloads landing arrival dates `[D-3, D+1]` into bronze (ADR-004 lookback) |
| 2 | `dbt_build` | All models and dbt data tests; a test failure stops the run |
| 3 | `gx_gates` | GX `silver` (daily meter facts) and `gold` (billing) suites; a failure blocks the publish |
| 4 | `publish_postgres` | 8 marts → `warehouse.marts`. Each table is swapped atomically and reconciled on rows + kWh |
| 5 | `ops_metrics_alerts` | Writes a row to `ops.pipeline_runs`, plus `ops.alerts` for zones below 90% completeness or for late data |
| 6 | `retention` | Drops landing + bronze partitions older than 30 days |

Every task retries twice, 2 minutes apart. Tasks that touch DuckDB share pool `duckdb` (1 slot), because DuckDB allows a single writer.

**Morning check (2 min):**
1. Superset → *GridPulse — Network Operations* → **Pipeline health** tab. The latest run should show `success`, completeness ≥ 90% and duplicate rate ≈ 1–2%. The **Alerts** list should be empty.
2. Airflow UI → `gridpulse_daily` → the last run is green.

## 3. Alerts → action
| Alert / symptom | Meaning | Action |
|---|---|---|
| `completeness_drop zone=Zxx date=…` | Zone completeness < 90% for that day | Check the **Completeness** tab and the anomaly list for an `OUTAGE`. If a gateway is late, its files arrive within 3 days and the next daily runs absorb them. Otherwise escalate to field ops. |
| `late_beyond_window` | Readings arrived more than 3 days late, outside the lookback | Run a backfill for the affected dates (§4) |
| `dbt_build` failed | A model or data test failed | Read the task log for the failing test name; fix the data or code; clear the task |
| `gx_gates` failed | Silver or gold suite failed; nothing was published, so yesterday's marts stay live | Read the task log (`suite=… successful=x/y`); fix; clear the task |
| `publish_postgres` failed with `reconciliation failed` | Postgres differs from DuckDB after the swap | Re-run the task (the publish is idempotent). If it persists, roll back (§5). |
| Task stuck in `queued` | Pool `duckdb` busy, or the scheduler is unhealthy | `docker compose logs airflow-scheduler`; check no manual dbt/DuckDB session is holding the file |

## 4. Backfill (late data, reprocessing, corrections)
```bash
bash scripts/airflow_trigger_wait.sh gridpulse_backfill '{"start":"2026-11-20","end":"2026-11-26"}' 2400
# Linux: make backfill START=2026-11-20 END=2026-11-26
```
- The backfill loads landing arrival dates `[start, end+4]`, then runs the same task chain.
- It is idempotent: bronze partitions are replaced, dbt rebuilds, and the publish swaps tables. Re-running gives the same totals.
- **Drill performed 27-Nov-2026:** backfill 2026-11-20 → 26 with the GX gates. Evidence: `docs/evidence/sprint_3/runbook_backfill_drill.txt`.

## 5. Rollback
Code and data roll back separately.

1. **Bad code release:**
   ```bash
   git revert <sha>
   docker compose up -d --build --wait
   ```
   Then run a backfill (§4) for the affected dates. The DAG files reload automatically.
2. **Bad data published to Postgres:**
   - Restore the marts snapshot taken before the risky change:
     ```bash
     # before a risky change: snapshot
     docker compose exec -T postgres pg_dump -U postgres -d warehouse -n marts -Fc > marts_backup.dump
     # rollback: restore the snapshot over the current marts
     docker compose exec -T postgres pg_restore -U postgres -d warehouse --clean --if-exists < marts_backup.dump
     ```
   - Or re-publish from the last good DuckDB build:
     ```bash
     docker compose exec -T airflow-scheduler bash -c \
       'cd /opt/gridpulse && $GRIDPULSE_PYTHON -m ingestion.publish.to_postgres'
     ```
3. **Bad bronze partition:** bronze is never edited.
   - Fix or replace the landing files for that arrival date.
   - Reload with `python -m ingestion.extractors.landing_to_bronze --dt YYYY-MM-DD`; the partition swap is atomic.
   - Then backfill.

## 6. Capacity and limits (7-day demo, 5,000 meters, Windows host)
- **Run times:**
  - backfill of 7 days: 174 s;
  - daily run: about 3–5 min.
- **Resources:**
  - the stack uses about 1.1 GB of RAM at idle;
  - raw JSON is 397 MB/week, which becomes 38 MB of bronze Parquet.
- **Storage:** the repo is bind-mounted, so I/O is about 4× slower than native.
  - Keep `data/` out of OneDrive sync for production.
  - Or move `data/` to a named Docker volume.
- **Changing thresholds:**
  - anomaly and data-quality thresholds are dbt vars in `dbt_project/dbt_project.yml`;
  - change them only via an ADR (e.g. ADR-006, spike guard).
