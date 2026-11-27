"""Publish DuckDB marts to the Postgres serving warehouse (US-23, LLD C6).

For every table in ``PUBLISHED``: copy ``<duckdb>.main_marts.<table>`` into
``warehouse.marts._load_<table>`` through the DuckDB postgres extension, then in ONE Postgres
transaction drop the live table, rename the load table into place and add the primary key.
Readers never see a half-loaded table and re-running is idempotent (full refresh).
``bi_reader`` gets SELECT through the schema's default privileges (infra/postgres/init.sh).

Config (env vars only): DUCKDB_PATH, WAREHOUSE_HOST, WAREHOUSE_PORT, WAREHOUSE_DB,
WAREHOUSE_USER, WAREHOUSE_DB_PASSWORD, DUCKDB_EXTENSION_DIR (optional, pre-installed in image).
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from dataclasses import dataclass

import duckdb

log = logging.getLogger("publish_to_postgres")

# table -> (primary key columns, kWh column used for the reconciliation check or None)
PUBLISHED: dict[str, tuple[tuple[str, ...], str | None]] = {
    "fct_consumption_daily": (("meter_id", "interval_date_ist"), "consumption_kwh"),
    "mart_feeder_consumption_hourly": (("feeder_id", "hour_start_ts"), "consumption_kwh"),
    "mart_feeder_consumption_daily": (("feeder_id", "interval_date_ist"), "consumption_kwh"),
    "mart_zone_consumption_daily": (("zone_id", "interval_date_ist"), "consumption_kwh"),
    "mart_zone_completeness_daily": (("zone_id", "interval_date_ist"), None),
    "mart_billing_monthly": (("billing_month_ist", "meter_id"), "billed_kwh"),
    "mart_anomalies": (("anomaly_id",), None),
    "mart_feeder_voltage_daily": (("feeder_id", "interval_date_ist"), None),
}
SOURCE_SCHEMA = "lake.main_marts"
TARGET_SCHEMA = "marts"


@dataclass(frozen=True)
class PublishResult:
    """Row count and kWh total on both sides of one published table."""

    table: str
    duckdb_rows: int
    postgres_rows: int
    duckdb_kwh: str | None
    postgres_kwh: str | None

    @property
    def reconciled(self) -> bool:
        return self.duckdb_rows == self.postgres_rows and self.duckdb_kwh == self.postgres_kwh


def pg_dsn() -> str:
    """libpq connection string for the warehouse writer role, from env vars."""
    parts = {
        "host": os.environ.get("WAREHOUSE_HOST", "postgres"),
        "port": os.environ.get("WAREHOUSE_PORT", "5432"),
        "dbname": os.environ.get("WAREHOUSE_DB", "warehouse"),
        "user": os.environ.get("WAREHOUSE_USER", "gridpulse"),
        "password": os.environ["WAREHOUSE_DB_PASSWORD"],
    }
    return " ".join(f"{k}={v}" for k, v in parts.items())


def swap_sql(table: str, pk: tuple[str, ...]) -> str:
    """Postgres statements that atomically replace marts.<table> with the freshly loaded copy."""
    t, load = f"{TARGET_SCHEMA}.{table}", f"{TARGET_SCHEMA}._load_{table}"
    # One DO block = one statement, executed atomically (postgres_execute prepares its SQL,
    # so a multi-statement "begin; ...; commit;" string is rejected).
    return (
        "do $$ begin "
        f"drop table if exists {t}; "
        f"alter table {load} rename to {table}; "
        f"alter table {t} add constraint {table}_pk primary key ({', '.join(pk)}); "
        "end $$"
    )


def connect(duckdb_path: str) -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB with the lake file attached read-only as ``lake`` and Postgres as ``pg``.

    (Opening the lake file itself read-only would make every attached database read-only.)
    """
    con = duckdb.connect()
    con.execute("set timezone = 'Asia/Kolkata'")
    con.execute(f"attach '{duckdb_path}' as lake (read_only)")
    ext_dir = os.environ.get("DUCKDB_EXTENSION_DIR")
    if ext_dir:
        con.execute(f"set extension_directory = '{ext_dir}'")
    con.execute("install postgres")
    con.execute("load postgres")
    con.execute(f"attach '{pg_dsn()}' as pg (type postgres)")
    return con


def _totals(
    con: duckdb.DuckDBPyConnection, relation: str, kwh: str | None
) -> tuple[int, str | None]:
    sel = f"count(*), {f'sum({kwh})::varchar' if kwh else 'null'}"
    rows, total = con.execute(f"select {sel} from {relation}").fetchone()  # type: ignore[misc]
    return int(rows), total


def publish_table(con: duckdb.DuckDBPyConnection, table: str) -> PublishResult:
    """Copy one mart to Postgres, swap it in, and reconcile rows + kWh on both sides."""
    pk, kwh = PUBLISHED[table]
    load = f"pg.{TARGET_SCHEMA}._load_{table}"
    con.execute(f"drop table if exists {load}")
    con.execute(f"create table {load} as select * from {SOURCE_SCHEMA}.{table}")
    sql = swap_sql(table, pk)
    if "'" in sql:  # identifiers come from PUBLISHED only; guard the literal anyway
        raise ValueError("unexpected quote in swap SQL")
    con.execute(f"call postgres_execute('pg', '{sql}')")
    con.execute("call postgres_clear_cache()")
    d_rows, d_kwh = _totals(con, f"{SOURCE_SCHEMA}.{table}", kwh)
    p_rows, p_kwh = _totals(con, f"pg.{TARGET_SCHEMA}.{table}", kwh)
    return PublishResult(table, d_rows, p_rows, d_kwh, p_kwh)


def publish_all(duckdb_path: str, tables: list[str] | None = None) -> list[PublishResult]:
    """Publish the given (default: all) marts. Raises if any table fails to reconcile."""
    t0 = time.perf_counter()
    con = connect(duckdb_path)
    try:
        results = [publish_table(con, t) for t in (tables or list(PUBLISHED))]
    finally:
        con.close()
    for r in results:
        log.info(
            "published table=%s duckdb_rows=%d postgres_rows=%d duckdb_kwh=%s postgres_kwh=%s "
            "reconciled=%s",
            r.table,
            r.duckdb_rows,
            r.postgres_rows,
            r.duckdb_kwh,
            r.postgres_kwh,
            r.reconciled,
        )
    bad = [r.table for r in results if not r.reconciled]
    if bad:
        raise RuntimeError(f"publish reconciliation failed for: {', '.join(bad)}")
    log.info("publish done tables=%d seconds=%.1f", len(results), time.perf_counter() - t0)
    return results


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Publish DuckDB marts to Postgres warehouse.marts")
    p.add_argument("--table", action="append", choices=sorted(PUBLISHED), help="repeatable")
    p.add_argument(
        "--duckdb", default=os.environ.get("DUCKDB_PATH", "data/warehouse/gridpulse.duckdb")
    )
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    publish_all(a.duckdb, a.table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
