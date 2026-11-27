"""Pipeline health metrics + completeness alerts (US-19, FR-24/25).

Computes, from the DuckDB lake, the run's bronze rows, quarantine count, duplicate rate,
completeness and ingest lag p50/p95. Writes one row to ``warehouse.ops.pipeline_runs``.
Writes an ``ops.alerts`` row plus a WARNING log line for every zone-day below the
completeness threshold in the run window, and for late data beyond the lookback window.
"""

from __future__ import annotations

import argparse
import logging
import os
from datetime import date, datetime, timedelta, timezone

from ingestion.publish.to_postgres import connect

log = logging.getLogger("ops_metrics")
IST = timezone(timedelta(hours=5, minutes=30))

DDL = (
    "do $$ begin "
    "create table if not exists ops.pipeline_runs ("
    " run_id text primary key, dag_id text not null, logical_date_ist date not null,"
    " started_ts timestamptz not null, finished_ts timestamptz, status text not null,"
    " bronze_rows bigint, quarantined_rows bigint, duplicate_rate_pct numeric(6,3),"
    " completeness_pct numeric(6,2), ingest_lag_p50_min numeric(8,1),"
    " ingest_lag_p95_min numeric(8,1), late_beyond_window_events bigint, duration_s int); "
    "create table if not exists ops.alerts ("
    " alert_id bigserial primary key, raised_ts timestamptz not null default now(),"
    " run_id text, severity text not null, alert_type text not null, scope text not null,"
    " message text not null); "
    "end $$"
)

METRICS_SQL = """
with v as (
    select
        count(*) as bronze_rows,
        count(*) filter (where reject_reason is not null) as quarantined_rows,
        count(*) filter (where dup_rank > 1) as duplicates
    from lake.main_staging.stg_meter__readings_validated
),
lag as (
    select
        quantile_cont(epoch(file_arrival_ts - reading_ts) / 60.0, 0.5) as p50,
        quantile_cont(epoch(file_arrival_ts - reading_ts) / 60.0, 0.95) as p95,
        count(*) filter (where landing_date_ist - interval_date_ist > {lookback}) as late
    from lake.main_staging.stg_meter__readings
),
c as (
    select
        100.0 * sum(intervals_received) / sum(intervals_expected) as completeness_pct
    from lake.main_marts.mart_zone_completeness_daily
    where interval_date_ist between date '{start}' and date '{end}'
)
select
    v.bronze_rows, v.quarantined_rows,
    round(100.0 * v.duplicates / nullif(v.bronze_rows, 0), 3),
    round(c.completeness_pct, 2), round(lag.p50, 1), round(lag.p95, 1), lag.late
from v, lag, c
"""


def window(logical: date, lookback: int) -> tuple[date, date]:
    """Interval dates the run is responsible for (ADR-004): [D - lookback, D]."""
    return logical - timedelta(days=lookback), logical


def record_run(
    run_id: str,
    dag_id: str,
    logical: date,
    started: datetime,
    lookback: int = 3,
    threshold: float = 90.0,
) -> dict:
    """Compute metrics, upsert ops.pipeline_runs, raise ops.alerts. Returns the metrics."""
    duck = os.environ.get("DUCKDB_PATH", "data/warehouse/gridpulse.duckdb")
    con = connect(duck)
    start, end = window(logical, lookback)
    try:
        con.execute(f"call postgres_execute('pg', '{DDL}')")
        row = con.execute(METRICS_SQL.format(lookback=lookback, start=start, end=end)).fetchone()
        assert row is not None
        finished = datetime.now(IST)
        m = {
            "run_id": run_id,
            "dag_id": dag_id,
            "logical_date_ist": logical,
            "started_ts": started,
            "finished_ts": finished,
            "status": "success",
            "bronze_rows": row[0],
            "quarantined_rows": row[1],
            "duplicate_rate_pct": row[2],
            "completeness_pct": row[3],
            "ingest_lag_p50_min": row[4],
            "ingest_lag_p95_min": row[5],
            "late_beyond_window_events": row[6],
            "duration_s": int((finished - started).total_seconds()),
        }
        con.execute("delete from pg.ops.pipeline_runs where run_id = ?", [run_id])
        cols = ", ".join(m)
        con.execute(
            f"insert into pg.ops.pipeline_runs ({cols}) values ({', '.join('?' * len(m))})",
            list(m.values()),
        )
        log.info("pipeline_run %s", " ".join(f"{k}={v}" for k, v in m.items()))

        low = con.execute(
            "select zone_id, interval_date_ist, completeness_pct "
            "from lake.main_marts.mart_zone_completeness_daily "
            "where interval_date_ist between ? and ? and completeness_pct < ? order by 2, 1",
            [start, end, threshold],
        ).fetchall()
        alerts = [
            (
                "WARNING",
                "completeness_drop",
                f"zone={z} date={d}",
                f"completeness {pct}% < {threshold}% in zone {z} on {d}",
            )
            for z, d, pct in low
        ]
        if m["late_beyond_window_events"]:
            alerts.append(
                (
                    "WARNING",
                    "late_beyond_window",
                    f"run={run_id}",
                    f"{m['late_beyond_window_events']} readings arrived > {lookback} days late"
                    " - run gridpulse_backfill for the affected dates",
                )
            )
        con.execute("delete from pg.ops.alerts where run_id = ?", [run_id])
        for sev, kind, scope, msg in alerts:
            con.execute(
                "insert into pg.ops.alerts (run_id, severity, alert_type, scope, message) "
                "values (?, ?, ?, ?, ?)",
                [run_id, sev, kind, scope, msg],
            )
            log.warning("ALERT %s %s %s", kind, scope, msg)
        log.info("ops metrics done run_id=%s alerts=%d", run_id, len(alerts))
        return m
    finally:
        con.close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--run-id", required=True)
    p.add_argument("--dag-id", required=True)
    p.add_argument("--logical-date", type=date.fromisoformat, required=True)
    p.add_argument("--started", type=datetime.fromisoformat, required=True)
    p.add_argument("--lookback", type=int, default=3)
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    started = a.started if a.started.tzinfo else a.started.replace(tzinfo=IST)
    record_run(a.run_id, a.dag_id, a.logical_date, started, a.lookback)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
