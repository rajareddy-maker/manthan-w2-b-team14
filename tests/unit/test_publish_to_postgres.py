"""Unit tests for the Postgres publisher (US-23) — pure functions, no database needed."""

from __future__ import annotations

import pytest

from ingestion.publish.to_postgres import PUBLISHED, PublishResult, pg_dsn, swap_sql


def test_swap_is_one_transaction_with_primary_key() -> None:
    sql = swap_sql("mart_billing_monthly", ("billing_month_ist", "meter_id"))
    assert sql.startswith("do $$ begin ") and sql.endswith(" end $$")  # one atomic statement
    assert "'" not in sql
    assert "drop table if exists marts.mart_billing_monthly;" in sql
    assert "alter table marts._load_mart_billing_monthly rename to mart_billing_monthly;" in sql
    assert "primary key (billing_month_ist, meter_id)" in sql


def test_dsn_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WAREHOUSE_HOST", "db")
    monkeypatch.setenv("WAREHOUSE_PORT", "6543")
    monkeypatch.setenv("WAREHOUSE_DB_PASSWORD", "pw")
    monkeypatch.delenv("WAREHOUSE_USER", raising=False)
    assert pg_dsn() == "host=db port=6543 dbname=warehouse user=gridpulse password=pw"


def test_dsn_requires_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WAREHOUSE_DB_PASSWORD", raising=False)
    with pytest.raises(KeyError):
        pg_dsn()


def test_hourly_meter_fact_is_not_published() -> None:
    # ADR-003: per-meter hourly stays in the lake (13-month retention), not in Postgres.
    assert "fct_consumption_hourly" not in PUBLISHED
    assert {"mart_anomalies", "mart_billing_monthly", "mart_zone_completeness_daily"} <= set(
        PUBLISHED
    )


@pytest.mark.parametrize(
    ("d", "p", "ok"),
    [((10, "1.5000"), (10, "1.5000"), True), ((10, "1.5000"), (9, "1.5000"), False)],
)
def test_reconciled(d: tuple, p: tuple, ok: bool) -> None:
    assert PublishResult("t", d[0], p[0], d[1], p[1]).reconciled is ok
