"""Essential tests for the production tasks: retention, ops window, bronze range, GX gates."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

import duckdb
import pytest

from ingestion.extractors.landing_to_bronze import main as bronze_main
from ingestion.extractors.retention import apply_retention, expired_partitions
from ingestion.ops.metrics import DDL, window

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- retention (ADR-003)
def make_parts(root: Path, days: list[str]) -> None:
    for d in days:
        (root / f"dt={d}").mkdir(parents=True)
    (root / "not-a-partition").mkdir()
    (root / "dt=garbage").mkdir()


def test_retention_drops_only_partitions_older_than_window(tmp_path: Path) -> None:
    make_parts(tmp_path, ["2026-10-01", "2026-10-27", "2026-10-28", "2026-11-26"])
    ref = date(2026, 11, 27)
    expired = [p.name for p in expired_partitions(tmp_path, ref, 30)]
    assert expired == ["dt=2026-10-01", "dt=2026-10-27"]  # cutoff 2026-10-28 is kept
    assert apply_retention([tmp_path], ref, 30) == 2
    left = sorted(p.name for p in tmp_path.iterdir())
    assert left == ["dt=2026-10-28", "dt=2026-11-26", "dt=garbage", "not-a-partition"]
    assert apply_retention([tmp_path], ref, 30) == 0  # idempotent


# ---------------------------------------------------------------- ops metrics (US-19)
def test_ops_window_is_lookback_inclusive() -> None:
    assert window(date(2026, 11, 26), 3) == (date(2026, 11, 23), date(2026, 11, 26))


def test_ops_ddl_is_single_quote_free_do_block() -> None:
    # sent through postgres_execute as a literal: must be one statement with no quotes
    assert DDL.startswith("do $$ begin ") and DDL.endswith(" end $$")
    assert "'" not in DDL
    assert "ops.pipeline_runs" in DDL and "ops.alerts" in DDL


# ---------------------------------------------------------------- bronze date range (US-15)
def test_bronze_range_loads_only_dates_in_range(tmp_path: Path) -> None:
    landing, bronze = tmp_path / "landing", tmp_path / "bronze"
    line = '{"meter_id":"MTR-00001","ts":"2026-11-20T10:15:00+05:30","energy_wh":1,"status":"OK"}'
    for d in ("2026-11-19", "2026-11-20", "2026-11-21", "2026-11-22"):
        part = landing / f"dt={d}"
        part.mkdir(parents=True)
        (part / "gw-Z01-20261120-10.jsonl").write_text(line + "\n", encoding="utf-8")
    argv = ["--from", "2026-11-20", "--to", "2026-11-21"]
    assert bronze_main([*argv, "--landing", str(landing), "--bronze", str(bronze)]) == 0
    assert sorted(p.name for p in bronze.glob("dt=*")) == ["dt=2026-11-20", "dt=2026-11-21"]


# ---------------------------------------------------------------- GX gates (US-14)
def load_gx():
    spec = importlib.util.spec_from_file_location(
        "run_checkpoint", ROOT / "data_quality/gx/run_checkpoint.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["run_checkpoint"] = mod
    spec.loader.exec_module(mod)
    return mod


def make_lake(path: Path, negative: bool) -> None:
    con = duckdb.connect(str(path))
    con.execute("create schema main_marts")
    kwh = -1.0 if negative else 1.5
    con.execute(
        "create table main_marts.fct_consumption_daily as select * from (values "
        f"('M1', date '2026-11-20', {kwh}, 100.0, 'OK'), "
        "('M2', date '2026-11-20', 2.0, 80.0, 'LOW_COMPLETENESS')) "
        "t(meter_id, interval_date_ist, consumption_kwh, completeness_pct, quality_flag)"
    )
    con.execute(
        "create table main_marts.mart_billing_monthly as select * from (values "
        f"(date '2026-11-01', 'M1', {kwh}, 'OK'), (date '2026-11-01', 'M2', 2.0, 'OK')) "
        "t(billing_month_ist, meter_id, billed_kwh, quality_flag)"
    )
    con.close()


@pytest.mark.parametrize(("negative", "expected"), [(False, True), (True, False)])
def test_gx_gates_pass_clean_and_block_negative_energy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, negative: bool, expected: bool
) -> None:
    db = tmp_path / "lake.duckdb"
    make_lake(db, negative)
    monkeypatch.setenv("DUCKDB_PATH", str(db))
    gx_mod = load_gx()
    assert gx_mod.run("silver") is expected
    assert gx_mod.run("gold") is expected
