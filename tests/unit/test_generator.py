"""Unit tests for the synthetic data generator (US-07)."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, datetime
from pathlib import Path

import pytest

from ingestion.generator.__main__ import run
from ingestion.generator.config import DefectConfig, GeneratorConfig
from ingestion.generator.writer import MANIFEST_NAME, v1_line, v2_line

END = date(2026, 11, 20)


def small_cfg(root: Path, seed: int = 7) -> GeneratorConfig:
    return GeneratorConfig(
        meters=120,
        feeders=6,
        zones=3,
        days=4,
        end_date=END,
        seed=seed,
        out_dir=root / "landing",
        seeds_dir=root / "seeds",
        defects=DefectConfig(
            late_file_rate=0.1,
            resend_file_rate=0.05,
            spike_meters=2,
            tamper_meters=2,
            rollover_meters=2,
            register_reset_meters=1,
            low_completeness_meters=2,
            negative_events=5,
            offgrid_snappable_events=5,
            offgrid_reject_events=5,
            unknown_meters=2,
        ),
    )


def read_events(landing: Path) -> tuple[list[dict], int]:
    events, corrupt = [], 0
    for f in sorted(landing.glob("dt=*/*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                corrupt += 1
                continue
            ev["_file"] = f"{f.parent.name}/{f.name}"
            events.append(ev)
    return events, corrupt


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory) -> tuple[GeneratorConfig, dict, list[dict]]:
    cfg = small_cfg(tmp_path_factory.mktemp("gen"))
    manifest = run(cfg)
    events, _ = read_events(cfg.out_dir)
    return cfg, manifest, events


def test_v1_line_is_valid_json() -> None:
    ev = json.loads(v1_line("MTR-00001", "2026-11-20T10:15:00+05:30", 1500, "OK"))
    assert ev == {
        "meter_id": "MTR-00001",
        "ts": "2026-11-20T10:15:00+05:30",
        "energy_wh": 1500,
        "status": "OK",
    }


@pytest.mark.parametrize(("unit_kwh", "energy", "unit"), [(True, 1.5, "kWh"), (False, 1500, "Wh")])
def test_v2_line_units(unit_kwh: bool, energy: float, unit: str) -> None:
    ev = json.loads(
        v2_line("MTR-1", "2026-11-20T10:15:00+05:30", 1500, unit_kwh, "OK", 231.4, "2.3.1")
    )
    assert ev["schema_version"] == 2
    assert ev["energy"] == energy
    assert ev["unit"] == unit
    assert ev["voltage"] == 231.4


def test_seeds_written(generated: tuple) -> None:
    cfg, _, _ = generated
    with (cfg.seeds_dir / "meter_master.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == cfg.meters
    assert {r["schema_version"] for r in rows} == {"1", "2"}
    assert {r["unit"] for r in rows} == {"Wh", "kWh"}
    with (cfg.seeds_dir / "feeder_zone.csv").open(encoding="utf-8") as fh:
        assert len(list(csv.DictReader(fh))) == cfg.feeders


def test_landing_layout_and_schema_versions(generated: tuple) -> None:
    cfg, manifest, events = generated
    dts = sorted(p.name for p in cfg.out_dir.glob("dt=*"))
    assert dts[0] == f"dt={cfg.start_date.isoformat()}"
    assert all(p.name.startswith("gw-") for p in cfg.out_dir.glob("dt=*/*.jsonl"))
    assert any(e.get("schema_version") == 2 for e in events)
    assert any("energy_wh" in e for e in events)
    assert {e["unit"] for e in events if "unit" in e} == {"Wh", "kWh"}
    assert manifest["stats"]["lines"] == len(events) + manifest["stats"]["corrupt_lines"]


def test_timestamps_on_15_min_grid_except_injected(generated: tuple) -> None:
    _, manifest, events = generated
    # distinct: an off-grid event inside a re-sent gateway file appears twice
    off = {(e["meter_id"], e["ts"]) for e in events if datetime.fromisoformat(e["ts"]).minute % 15}
    expected = manifest["stats"]["offgrid_snap_events"] + manifest["stats"]["offgrid_reject_events"]
    assert len(off) == expected > 0
    assert any(len(e["ts"]) == 19 for e in events), "some v1 events have naive timestamps"


def test_defects_present(generated: tuple) -> None:
    cfg, manifest, events = generated
    s = manifest["stats"]
    keys = [(e["meter_id"], e["ts"]) for e in events]
    assert len(keys) - len(set(keys)) >= s["duplicate_events"] > 0
    negatives = {
        (e["meter_id"], e["ts"]) for e in events if e.get("energy_wh", e.get("energy", 0)) < 0
    }
    assert len(negatives) == s["negative_events"]
    assert s["late_files"] > 0 and manifest["late_files"]
    for late in manifest["late_files"]:
        dt_part, name = late["file"].split("/")
        arrived = date.fromisoformat(dt_part.removeprefix("dt="))
        slot_day = datetime.strptime(name.split("-")[2], "%Y%m%d").date()
        assert (arrived - slot_day).days >= late["days_late"] >= 1
    assert any(e["meter_id"].startswith("MTR-9") for e in events)
    assert s["resent_files"] > 0 and s["corrupt_lines"] == 3


def test_crafted_anomalies_in_manifest(generated: tuple) -> None:
    _, manifest, events = generated
    exp = manifest["expected"]
    assert len(exp["spike"]) == 2 and len(exp["tamper"]) == 2
    assert len({t["feeder_id"] for t in exp["tamper"]}) == 2
    (outage,) = exp["outage"]
    assert outage["meters_affected"] / outage["feeder_meters"] >= 0.30
    (control,) = exp["outage_negative_control"]
    assert control["meters_affected"] / control["feeder_meters"] < 0.30
    rollover_ids = set(exp["rollover"])
    assert any(e["meter_id"] in rollover_ids and e["status"] == "ROLLOVER" for e in events)


def test_tamper_meter_register_is_flat(generated: tuple) -> None:
    _, manifest, events = generated
    t = manifest["expected"]["tamper"][0]
    lo = datetime.fromisoformat(t["zero_from_reading_ts"])
    hi = datetime.fromisoformat(t["zero_to_reading_ts"])
    vals = {
        e.get("energy_wh", e.get("energy"))
        for e in events
        if e["meter_id"] == t["meter_id"]
        and "+05:30" in e["ts"]
        and lo <= datetime.fromisoformat(e["ts"]) <= hi
        and e.get("energy_wh", e.get("energy", 0)) >= 0
        and datetime.fromisoformat(e["ts"]).minute % 15 == 0
    }
    assert len(vals) == 1


def _digest(landing: Path) -> dict[str, str]:
    return {
        p.relative_to(landing).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(landing.rglob("*"))
        if p.is_file()
    }


def test_deterministic_for_same_seed(tmp_path: Path) -> None:
    a, b = small_cfg(tmp_path / "a"), small_cfg(tmp_path / "b")
    run(a)
    run(b)
    assert _digest(a.out_dir) == _digest(b.out_dir)
    run(a)  # rerun into the same directory is identical too
    assert _digest(a.out_dir) == _digest(b.out_dir)


def test_different_seed_differs(tmp_path: Path) -> None:
    a, b = small_cfg(tmp_path / "a"), small_cfg(tmp_path / "b", seed=8)
    run(a)
    run(b)
    assert _digest(a.out_dir) != _digest(b.out_dir)
    assert (a.out_dir / MANIFEST_NAME).exists()


def test_install_dates_do_not_depend_on_wall_clock(tmp_path: Path) -> None:
    # DEF-012: install dates must be a pure function of (seed, end_date), not of "now".
    from ingestion.generator.topology import build_topology

    cfg = small_cfg(tmp_path)
    dates = build_topology(cfg).install_dates
    assert dates == build_topology(cfg).install_dates
    lo, hi = date(END.year - 8, END.month, END.day), date(END.year - 1, END.month, END.day)
    assert all(lo <= date.fromisoformat(d) <= hi for d in dates)
    leap = GeneratorConfig(meters=6, feeders=3, zones=1, days=1, end_date=date(2028, 2, 29))
    assert len(build_topology(leap).install_dates) == 6
