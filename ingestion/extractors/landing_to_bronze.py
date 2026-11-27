"""Landing JSONL -> bronze Parquet (US-08).

Bronze layout: ``<bronze_root>/dt=<landing arrival date>/zone=<gateway zone>/part-0.parquet``.
Every landed line becomes one bronze row, including lines that are not valid JSON: bronze is the
raw, replayable record (CLAUDE.md "Never mutate bronze"). Loading a landing date replaces that
whole ``dt`` partition atomically, so re-running a date is idempotent (ADR-003).

Bronze columns:
    raw_payload, is_valid_json, schema_version, meter_id, source_file, line_no,
    file_arrival_ts, ingested_at  (+ hive keys dt, zone)
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import shutil
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import duckdb
import pyarrow as pa

log = logging.getLogger("landing_to_bronze")

IST = timezone(timedelta(hours=5, minutes=30), name="IST")
FILE_RE = re.compile(r"^gw-(?P<zone>Z\d{2})-\d{8}-\d{2}(-r\d+)?\.jsonl$")
UNKNOWN_ZONE = "UNKNOWN"

PARSE_SQL = """
select
    raw_payload,
    json_valid(raw_payload) as is_valid_json,
    case
        when not json_valid(raw_payload) then null
        when json_exists(raw_payload, '$.schema_version')
            then try_cast(json_extract_string(raw_payload, '$.schema_version') as smallint)
        when json_exists(raw_payload, '$.energy_wh') then 1::smallint
    end as schema_version,
    case when json_valid(raw_payload) then json_extract_string(raw_payload, '$.meter_id') end
        as meter_id,
    source_file,
    line_no,
    file_arrival_ts,
    ingested_at,
    zone
from landed
order by zone, meter_id, source_file, line_no
"""


@dataclass(frozen=True)
class LoadResult:
    """Outcome of loading one landing date into bronze."""

    landing_dt: date
    files: int
    rows: int
    invalid_json: int
    partitions: int
    seconds: float


def zone_from_filename(name: str) -> str:
    """Extract the gateway zone from ``gw-<zone>-<YYYYMMDD>-<HH>[-rN].jsonl``."""
    m = FILE_RE.match(name)
    return m.group("zone") if m else UNKNOWN_ZONE


def read_landing(landing_root: Path, landing_dt: date, ingested_at: datetime) -> pa.Table:
    """Read every line of every file in ``landing_root/dt=<landing_dt>`` into an Arrow table."""
    part = landing_root / f"dt={landing_dt.isoformat()}"
    cols: dict[str, list] = {
        k: []
        for k in ("raw_payload", "source_file", "line_no", "file_arrival_ts", "ingested_at", "zone")
    }
    for path in sorted(part.glob("*.jsonl")):
        arrival = datetime.fromtimestamp(path.stat().st_mtime, IST)
        zone = zone_from_filename(path.name)
        source = f"{part.name}/{path.name}"
        with path.open(encoding="utf-8") as fh:
            for i, line in enumerate(fh, start=1):
                line = line.rstrip("\r\n")
                if not line:
                    continue
                cols["raw_payload"].append(line)
                cols["source_file"].append(source)
                cols["line_no"].append(i)
                cols["file_arrival_ts"].append(arrival)
                cols["ingested_at"].append(ingested_at)
                cols["zone"].append(zone)
    schema = pa.schema(
        [
            ("raw_payload", pa.string()),
            ("source_file", pa.string()),
            ("line_no", pa.int32()),
            ("file_arrival_ts", pa.timestamp("us", tz="Asia/Kolkata")),
            ("ingested_at", pa.timestamp("us", tz="Asia/Kolkata")),
            ("zone", pa.string()),
        ]
    )
    return pa.table(cols, schema=schema)


def _connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("set timezone = 'Asia/Kolkata'")
    con.execute(f"set threads = {int(os.environ.get('DUCKDB_THREADS', '2'))}")
    return con


def load_landing_date(
    landing_dt: date,
    landing_root: Path,
    bronze_root: Path,
    ingested_at: datetime | None = None,
) -> LoadResult:
    """Load one landing date into bronze, replacing the bronze ``dt`` partition atomically."""
    t0 = time.perf_counter()
    ingested_at = ingested_at or datetime.now(IST)
    landed = read_landing(landing_root, landing_dt, ingested_at)
    n_files = len(set(landed.column("source_file").to_pylist()))
    target = bronze_root / f"dt={landing_dt.isoformat()}"
    if landed.num_rows == 0:
        log.warning("no landing files landing_dt=%s", landing_dt)
        return LoadResult(landing_dt, 0, 0, 0, 0, time.perf_counter() - t0)

    bronze_root.mkdir(parents=True, exist_ok=True)
    tmp = bronze_root / f"_tmp_dt={landing_dt.isoformat()}"
    shutil.rmtree(tmp, ignore_errors=True)
    con = _connect()
    try:
        con.register("landed", landed)
        con.execute(
            f"copy ({PARSE_SQL}) to '{tmp.as_posix()}' "
            "(format parquet, partition_by (zone), compression zstd, "
            "filename_pattern 'part-{i}')"
        )
        invalid = con.execute("select count(*) from landed where not json_valid(raw_payload)")
        n_invalid = int(invalid.fetchone()[0])  # type: ignore[index]
    finally:
        con.close()
    for zone_dir in tmp.iterdir():
        compact_partition(zone_dir)
    shutil.rmtree(target, ignore_errors=True)
    tmp.rename(target)
    result = LoadResult(
        landing_dt=landing_dt,
        files=n_files,
        rows=landed.num_rows,
        invalid_json=n_invalid,
        partitions=sum(1 for _ in target.iterdir()),
        seconds=round(time.perf_counter() - t0, 2),
    )
    log.info(
        "bronze loaded landing_dt=%s files=%d rows=%d invalid_json=%d partitions=%d seconds=%.2f",
        result.landing_dt,
        result.files,
        result.rows,
        result.invalid_json,
        result.partitions,
        result.seconds,
    )
    return result


def compact_partition(partition_dir: Path) -> int:
    """Merge all Parquet files in one partition directory into a single ``part-0.parquet``.

    Returns the number of files that were merged (0 or 1 means nothing to do).
    """
    files = sorted(partition_dir.glob("*.parquet"))
    if len(files) <= 1:
        if files and files[0].name != "part-0.parquet":
            files[0].rename(partition_dir / "part-0.parquet")
        return 0
    merged = partition_dir / "_compacted.parquet.tmp"
    con = _connect()
    try:
        file_list = ", ".join(f"'{f.as_posix()}'" for f in files)
        con.execute(
            f"copy (select * from read_parquet([{file_list}]) "
            "order by meter_id, source_file, line_no) "
            f"to '{merged.as_posix()}' (format parquet, compression zstd)"
        )
    finally:
        con.close()
    for f in files:
        f.unlink()
    merged.rename(partition_dir / "part-0.parquet")
    log.info("compacted partition=%s files=%d", partition_dir, len(files))
    return len(files)


def compact_all(bronze_root: Path) -> int:
    """Compact every ``dt=/zone=`` partition under bronze. Returns partitions compacted."""
    return sum(1 for p in bronze_root.glob("dt=*/zone=*") if compact_partition(p) > 1)


def landing_dates(landing_root: Path) -> list[date]:
    """All landing dates present on disk, ascending."""
    return sorted(
        date.fromisoformat(p.name.removeprefix("dt="))
        for p in landing_root.glob("dt=*")
        if p.is_dir()
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Load landing JSONL into bronze Parquet")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--dt", type=date.fromisoformat, help="one landing date (IST)")
    g.add_argument("--all", action="store_true", help="every landing date on disk")
    g.add_argument("--compact", action="store_true", help="only compact existing partitions")
    g.add_argument("--from", dest="date_from", type=date.fromisoformat, help="range start (IST)")
    p.add_argument("--to", dest="date_to", type=date.fromisoformat, help="range end, inclusive")
    p.add_argument(
        "--landing", type=Path, default=Path(os.environ.get("LANDING_ROOT", "data/landing"))
    )
    p.add_argument(
        "--bronze", type=Path, default=Path(os.environ.get("BRONZE_ROOT", "data/lake/bronze"))
    )
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    if a.compact:
        log.info("compaction done partitions_compacted=%d", compact_all(a.bronze))
        return 0
    if a.date_from:
        end = a.date_to or a.date_from
        dates = [d for d in landing_dates(a.landing) if a.date_from <= d <= end]
    else:
        dates = landing_dates(a.landing) if a.all else [a.dt]
    log.info("bronze run landing_dates=%s", [d.isoformat() for d in dates])
    for d in dates:
        load_landing_date(d, a.landing, a.bronze)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
