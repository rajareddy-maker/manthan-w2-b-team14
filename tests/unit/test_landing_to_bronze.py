"""Unit tests for the landing -> bronze extractor (US-08)."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import duckdb
import pytest

from ingestion.extractors.landing_to_bronze import (
    IST,
    compact_partition,
    landing_dates,
    load_landing_date,
    zone_from_filename,
)

DT = date(2026, 11, 20)
V1 = '{"meter_id":"MTR-00001","ts":"2026-11-20T10:15:00+05:30","energy_wh":1500,"status":"OK"}'
V2 = (
    '{"schema_version":2,"meter_id":"MTR-00002","ts":"2026-11-20T10:15:00+05:30","energy":1.5,'
    '"unit":"kWh","status":"OK","voltage":231.0,"firmware_version":"2.3.1"}'
)
CORRUPT = '{"meter_id":"MTR-00003","ts":"20'


def write(landing: Path, name: str, lines: list[str], dt: date = DT) -> Path:
    part = landing / f"dt={dt.isoformat()}"
    part.mkdir(parents=True, exist_ok=True)
    path = part / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path


def bronze_rows(bronze: Path) -> list[tuple]:
    con = duckdb.connect()
    con.execute("set timezone = 'Asia/Kolkata'")
    return con.execute(
        f"select dt, zone, meter_id, schema_version, is_valid_json, source_file, line_no "
        f"from read_parquet('{bronze.as_posix()}/*/*/*.parquet', hive_partitioning = true) "
        "order by zone, source_file, line_no"
    ).fetchall()


@pytest.fixture
def lake(tmp_path: Path) -> tuple[Path, Path]:
    landing, bronze = tmp_path / "landing", tmp_path / "bronze"
    write(landing, "gw-Z01-20261120-10.jsonl", [V1, V2, V1])
    write(landing, "gw-Z02-20261120-10.jsonl", [V2, CORRUPT])
    write(landing, "gw-Z01-20261120-10-r1.jsonl", [V1])
    return landing, bronze


@pytest.mark.parametrize(
    ("name", "zone"),
    [
        ("gw-Z01-20261120-10.jsonl", "Z01"),
        ("gw-Z06-20261120-23-r1.jsonl", "Z06"),
        ("random.jsonl", "UNKNOWN"),
    ],
)
def test_zone_from_filename(name: str, zone: str) -> None:
    assert zone_from_filename(name) == zone


def test_every_line_preserved_with_lineage(lake: tuple[Path, Path]) -> None:
    landing, bronze = lake
    res = load_landing_date(DT, landing, bronze)
    assert (res.files, res.rows, res.invalid_json, res.partitions) == (3, 6, 1, 2)
    rows = bronze_rows(bronze)
    assert len(rows) == 6
    assert {r[1] for r in rows} == {"Z01", "Z02"}
    assert all(r[0] == DT for r in rows)
    by_meter = {r[2]: r[3] for r in rows if r[4]}
    assert by_meter == {"MTR-00001": 1, "MTR-00002": 2}
    corrupt = [r for r in rows if not r[4]]
    assert len(corrupt) == 1 and corrupt[0][2] is None and corrupt[0][3] is None
    assert corrupt[0][5] == "dt=2026-11-20/gw-Z02-20261120-10.jsonl" and corrupt[0][6] == 2


def test_raw_payload_unchanged(lake: tuple[Path, Path]) -> None:
    landing, bronze = lake
    load_landing_date(DT, landing, bronze)
    con = duckdb.connect()
    payloads = sorted(
        r[0]
        for r in con.execute(
            f"select raw_payload from read_parquet('{bronze.as_posix()}/*/*/*.parquet')"
        ).fetchall()
    )
    assert payloads == sorted([V1, V2, V1, V2, CORRUPT, V1])


def test_reload_is_idempotent_and_one_file_per_partition(lake: tuple[Path, Path]) -> None:
    landing, bronze = lake
    first = load_landing_date(
        DT, landing, bronze, ingested_at=datetime(2026, 11, 21, 1, tzinfo=IST)
    )
    second = load_landing_date(DT, landing, bronze)
    assert first.rows == second.rows == len(bronze_rows(bronze))
    for zone_dir in bronze.glob("dt=*/zone=*"):
        assert [p.name for p in zone_dir.iterdir()] == ["part-0.parquet"]
    assert not list(bronze.glob("_tmp_*"))


def test_file_arrival_ts_from_mtime(tmp_path: Path) -> None:
    landing, bronze = tmp_path / "landing", tmp_path / "bronze"
    path = write(landing, "gw-Z01-20261120-10.jsonl", [V1])
    arrival = datetime(2026, 11, 20, 11, 7, tzinfo=IST)
    import os

    os.utime(path, (arrival.timestamp(), arrival.timestamp()))
    load_landing_date(DT, landing, bronze)
    con = duckdb.connect()
    con.execute("set timezone = 'Asia/Kolkata'")
    (ts,) = con.execute(
        f"select file_arrival_ts from read_parquet('{bronze.as_posix()}/*/*/*.parquet')"
    ).fetchone()
    assert ts == arrival


def test_empty_landing_date_is_noop(tmp_path: Path) -> None:
    res = load_landing_date(DT, tmp_path / "landing", tmp_path / "bronze")
    assert res.rows == 0 and not (tmp_path / "bronze").exists()


def test_compact_partition_merges_files(tmp_path: Path) -> None:
    part = tmp_path / "zone=Z01"
    part.mkdir()
    con = duckdb.connect()
    for i in range(3):
        con.execute(
            f"copy (select 'MTR-{i}' as meter_id, 'f' as source_file, {i} as line_no) "
            f"to '{(part / f'small-{i}.parquet').as_posix()}' (format parquet)"
        )
    assert compact_partition(part) == 3
    assert [p.name for p in part.iterdir()] == ["part-0.parquet"]
    (n,) = con.execute(f"select count(*) from '{(part / 'part-0.parquet').as_posix()}'").fetchone()
    assert n == 3


def test_landing_dates_sorted(tmp_path: Path) -> None:
    for d in ("2026-11-21", "2026-11-19"):
        (tmp_path / f"dt={d}").mkdir()
    assert landing_dates(tmp_path) == [date(2026, 11, 19), date(2026, 11, 21)]
