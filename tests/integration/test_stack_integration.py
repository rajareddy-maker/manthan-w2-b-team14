"""Integration tests against the running Docker stack (Postgres :5433, Superset :8088).

Skipped automatically when the stack is not reachable (e.g. in CI). Nothing here touches the
live marts: publishing goes to the scratch schema ``marts_test``, and every row written to
``ops`` is deleted afterwards.
"""

from __future__ import annotations

import importlib.util
import socket
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import duckdb
import psycopg2
import pytest

ROOT = Path(__file__).resolve().parents[2]
IST = timezone(timedelta(hours=5, minutes=30))
LAKE = ROOT / "data/warehouse/gridpulse.duckdb"
pytestmark = pytest.mark.integration


def _env() -> dict[str, str]:
    env = {}
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def _up(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            return True
    except OSError:
        return False


ENV = _env()
needs_pg = pytest.mark.skipif(
    not (_up(5433) and ENV.get("WAREHOUSE_DB_PASSWORD")), reason="stack Postgres not running"
)
needs_superset = pytest.mark.skipif(not _up(8088), reason="stack Superset not running")


@pytest.fixture
def warehouse(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WAREHOUSE_HOST", "127.0.0.1")
    monkeypatch.setenv("WAREHOUSE_PORT", "5433")
    monkeypatch.setenv("WAREHOUSE_DB_PASSWORD", ENV["WAREHOUSE_DB_PASSWORD"])
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5433,
        dbname="warehouse",
        user="gridpulse",
        password=ENV["WAREHOUSE_DB_PASSWORD"],
    )
    conn.autocommit = True
    yield conn
    conn.close()


def q(conn, sql: str, *params):  # noqa: ANN001, ANN201
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall() if cur.description else None


# ---------------------------------------------------------------- publish (US-23)
@needs_pg
def test_publish_reconciles_and_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, warehouse
) -> None:  # noqa: ANN001
    from ingestion.publish import to_postgres

    lake = tmp_path / "lake.duckdb"
    con = duckdb.connect(str(lake))
    con.execute("create schema main_marts")
    con.execute(
        "create table main_marts.mart_billing_monthly as select * from (values "
        "(date '2026-11-01', 'M1', 1.2345::decimal(18,4), 'OK'), "
        "(date '2026-11-01', 'M2', 2.0000::decimal(18,4), 'LOW_COMPLETENESS')) "
        "t(billing_month_ist, meter_id, billed_kwh, quality_flag)"
    )
    con.close()
    q(warehouse, "create schema if not exists marts_test")
    monkeypatch.setattr(to_postgres, "TARGET_SCHEMA", "marts_test")
    try:
        for _ in range(2):  # second run proves the swap is idempotent
            (res,) = to_postgres.publish_all(str(lake), ["mart_billing_monthly"])
            assert res.reconciled and res.postgres_rows == 2 and res.postgres_kwh == "3.2345"
        assert q(
            warehouse, "select sum(billed_kwh)::text from marts_test.mart_billing_monthly"
        ) == [("3.2345",)]
        pk = q(
            warehouse,
            "select count(*) from pg_constraint where contype = 'p' "
            "and conrelid = 'marts_test.mart_billing_monthly'::regclass",
        )
        assert pk == [(1,)]
    finally:
        q(warehouse, "drop schema if exists marts_test cascade")


@needs_pg
def test_publish_cli_rejects_unknown_table() -> None:
    from ingestion.publish import to_postgres

    with pytest.raises(SystemExit):
        to_postgres.main(["--table", "not_a_mart"])


# ---------------------------------------------------------------- ops metrics (US-19)
@needs_pg
@pytest.mark.skipif(not LAKE.exists(), reason="no DuckDB lake (run the pipeline first)")
def test_ops_metrics_written_for_a_run(
    monkeypatch: pytest.MonkeyPatch, warehouse
) -> None:  # noqa: ANN001
    from ingestion.ops import metrics

    monkeypatch.setenv("DUCKDB_PATH", str(LAKE))
    run_id = f"pytest__{uuid.uuid4().hex[:8]}"
    try:
        m = metrics.record_run(
            run_id, "pytest", date(2026, 11, 26), datetime.now(IST), lookback=3, threshold=101.0
        )
        assert m["bronze_rows"] > 0 and m["status"] == "success"
        row = q(
            warehouse, "select status, bronze_rows from ops.pipeline_runs where run_id=%s", run_id
        )
        assert row == [("success", m["bronze_rows"])]
        # threshold 101% forces a completeness alert per zone-day in the window
        n = q(warehouse, "select count(*) from ops.alerts where run_id=%s", run_id)[0][0]
        assert n >= 1
    finally:
        q(warehouse, "delete from ops.alerts where run_id=%s", run_id)
        q(warehouse, "delete from ops.pipeline_runs where run_id=%s", run_id)


@needs_pg
@pytest.mark.skipif(not LAKE.exists(), reason="no DuckDB lake (run the pipeline first)")
def test_ops_metrics_cli(monkeypatch: pytest.MonkeyPatch, warehouse) -> None:  # noqa: ANN001
    from ingestion.ops import metrics

    monkeypatch.setenv("DUCKDB_PATH", str(LAKE))
    run_id = f"pytest__{uuid.uuid4().hex[:8]}"
    try:
        assert (
            metrics.main(
                [
                    "--run-id",
                    run_id,
                    "--dag-id",
                    "pytest",
                    "--logical-date",
                    "2026-11-26",
                    "--started",
                    "2026-11-27T10:00:00",
                ]
            )
            == 0
        )
        assert q(warehouse, "select count(*) from ops.pipeline_runs where run_id=%s", run_id) == [
            (1,)
        ]
    finally:
        q(warehouse, "delete from ops.alerts where run_id=%s", run_id)
        q(warehouse, "delete from ops.pipeline_runs where run_id=%s", run_id)


# ---------------------------------------------------------------- failure alert (US-26)
@needs_pg
def test_failure_alert_recorded_in_warehouse(
    monkeypatch: pytest.MonkeyPatch, warehouse
) -> None:  # noqa: ANN001
    from ingestion.ops import alerting

    run_id = f"pytest__{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("ALERT_EMAIL", "sagar.kalthiya@nucleusteq.com")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    ctx = {
        "ti": SimpleNamespace(dag_id="pytest_dag", task_id="t1", try_number=1),
        "dag_run": SimpleNamespace(run_id=run_id, start_date=datetime.now(IST)),
        "run_id": run_id,
        "exception": ValueError("integration"),
    }
    try:
        alerting.on_failure(ctx)
        rows = q(
            warehouse,
            "select severity, alert_type, scope from ops.alerts where run_id=%s",
            run_id,
        )
        assert rows == [("CRITICAL", "task_failed", "dag=pytest_dag task=t1")]
        assert q(warehouse, "select status from ops.pipeline_runs where run_id=%s", run_id) == [
            ("failed",)
        ]
    finally:
        q(warehouse, "delete from ops.alerts where run_id=%s", run_id)
        q(warehouse, "delete from ops.pipeline_runs where run_id=%s", run_id)


# ---------------------------------------------------------------- Superset (US-16, US-23)
def _load(name: str):  # noqa: ANN202
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@needs_superset
def test_superset_dashboard_as_code_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    first = _load("superset_first_chart")
    assert first.main([]) == 0
    dash = _load("superset_dashboard")
    assert dash.main([]) == 0
    assert dash.main([]) == 0  # re-run updates in place
    env = first.load_env()
    api = first.Superset(
        "http://127.0.0.1:8088", env["SUPERSET_ADMIN_USER"], env["SUPERSET_ADMIN_PASSWORD"]
    )
    charts = api.call("GET", "/api/v1/dashboard/gridpulse/charts")["result"]
    assert len(charts) == len(dash.CHARTS)
    tabs = [
        v
        for v in dash.layout({"A": [(1, "x")], "B": [(2, "y"), (3, "z")]}).values()
        if isinstance(v, dict) and v.get("type") == "TAB"
    ]
    assert [t["meta"]["text"] for t in tabs] == ["A", "B"]
