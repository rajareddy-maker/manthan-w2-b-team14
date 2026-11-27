"""Run the real pipeline (landing -> bronze -> dbt build) on a crafted data set in a temp dir.

The dbt project is copied so seeds can be replaced by a small hand-written meter master; bronze and
the DuckDB file live in the temp dir. No Docker needed (DuckDB only).
"""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

import duckdb

from ingestion.extractors.landing_to_bronze import landing_dates, load_landing_date

ROOT = Path(__file__).resolve().parents[2]


def copy_dbt_project(dest: Path) -> Path:
    """Copy dbt_project without build artefacts or seed CSVs."""
    target = dest / "dbt_project"
    shutil.copytree(
        ROOT / "dbt_project",
        target,
        ignore=shutil.ignore_patterns("target", "logs", "dbt_packages", "*.csv", ".user.yml"),
    )
    return target


def write_seeds(project: Path, meters: Iterable[dict], feeders: Iterable[dict]) -> None:
    """Write meter_master.csv and feeder_zone.csv seeds into the copied project."""
    seeds = project / "seeds"
    for name, rows, cols in (
        (
            "meter_master.csv",
            list(meters),
            [
                "meter_id",
                "feeder_id",
                "zone_id",
                "schema_version",
                "unit",
                "install_date",
                "register_max_kwh",
            ],
        ),
        ("feeder_zone.csv", list(feeders), ["feeder_id", "zone_id", "zone_name"]),
    ):
        with (seeds / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)


def run_pipeline(workdir: Path, project: Path, landing: Path) -> Path:
    """Load every landing date into bronze, then `dbt build`. Returns the DuckDB path."""
    bronze = workdir / "bronze"
    for d in landing_dates(landing):
        load_landing_date(d, landing, bronze)
    db = workdir / "warehouse.duckdb"
    env = {**os.environ, "BRONZE_ROOT": bronze.as_posix(), "DUCKDB_PATH": db.as_posix()}
    exe = Path(sys.executable).parent / ("dbt.exe" if os.name == "nt" else "dbt")
    cmd = [str(exe), "build", "--project-dir", str(project), "--profiles-dir", str(project)]
    res = subprocess.run(
        [*cmd, "--no-use-colors"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if res.returncode != 0:
        tail = "\n".join([res.stdout[-4000:], res.stderr[-2000:]])
        raise AssertionError(f"dbt build failed:\n{tail}")
    return db


def connect(db: Path) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(db), read_only=True)
    con.execute("set timezone = 'Asia/Kolkata'")
    return con
