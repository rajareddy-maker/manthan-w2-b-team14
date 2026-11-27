"""Write simulated readings as hourly gateway JSONL files under data/landing/dt=<arrival date>/.

One file per zone gateway per reading hour: ``gw-<zone>-<YYYYMMDD>-<HH>.jsonl`` holds the readings
that close the four intervals starting in that hour. The landing ``dt`` partition is the IST date
the file *arrived*, so late files land in a later partition (ADR-004). File mtime = arrival time.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from ingestion.generator.config import INTERVALS_PER_DAY, GeneratorConfig
from ingestion.generator.simulate import (
    NEGATIVE,
    OFFGRID_REJECT,
    OFFGRID_SNAP,
    STATUS_NAMES,
    Simulation,
)
from ingestion.generator.topology import Topology

log = logging.getLogger(__name__)
MANIFEST_NAME = "_manifest.json"


def v1_line(meter_id: str, ts: str, energy_wh: int, status: str) -> str:
    """Serialise a schema v1 event (no schema_version field, energy in Wh)."""
    return f'{{"meter_id":"{meter_id}","ts":"{ts}","energy_wh":{energy_wh},"status":"{status}"}}'


def v2_line(
    meter_id: str, ts: str, energy_wh: int, unit_kwh: bool, status: str, voltage: float, fw: str
) -> str:
    """Serialise a schema v2 event; energy is reported in the meter's unit (Wh or kWh)."""
    energy = f"{energy_wh / 1000:.3f}" if unit_kwh else str(energy_wh)
    unit = "kWh" if unit_kwh else "Wh"
    return (
        f'{{"schema_version":2,"meter_id":"{meter_id}","ts":"{ts}","energy":{energy},'
        f'"unit":"{unit}","status":"{status}","voltage":{voltage},"firmware_version":"{fw}"}}'
    )


def clean_landing(out_dir: Path) -> None:
    """Remove previously generated landing partitions so reruns are byte-identical."""
    if not out_dir.exists():
        return
    for child in out_dir.iterdir():
        if child.is_dir() and child.name.startswith("dt="):
            shutil.rmtree(child)
        elif child.name == MANIFEST_NAME:
            child.unlink()


def _slot_readings(slot: int) -> list[int]:
    """Reading indices whose interval starts in hour-slot ``slot`` (slot -1 = opening reading)."""
    return [0] if slot < 0 else list(range(4 * slot + 1, 4 * slot + 5))


def write_landing(cfg: GeneratorConfig, topo: Topology, sim: Simulation) -> dict[str, object]:
    """Write every landing file and the manifest. Returns the manifest dict."""
    rng = np.random.default_rng(cfg.seed + 2)
    d = cfg.defects
    out_dir = cfg.out_dir
    clean_landing(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    n_k = cfg.n_readings
    ts_aware = [sim.reading_ts(k).isoformat() for k in range(n_k)]
    ts_naive = [sim.reading_ts(k).strftime("%Y-%m-%dT%H:%M:%S") for k in range(n_k)]
    end_arrival_date = cfg.end_date + timedelta(days=1)
    slots = list(range(-1, cfg.days * 24))
    zone_meters = [topo.meters_in_zone(z) for z in range(cfg.zones)]
    stats: Counter[str] = Counter()

    # Unknown meters (not in the master): v1 readings for one full day, one gateway each.
    unknown: dict[tuple[int, int], list[str]] = {}
    unk_day = min(1, cfg.days - 1)
    for i in range(d.unknown_meters):
        z = i % cfg.zones
        for j in range(1, INTERVALS_PER_DAY + 1):
            k = unk_day * INTERVALS_PER_DAY + j
            line = v1_line(f"MTR-9{i:04d}", ts_aware[k], 5_000_000 + i * 1000 + 100 * j, "OK")
            unknown.setdefault(((k - 1) // 4, z), []).append(line)
            stats["unknown_meter_events"] += 1

    file_keys = [(s, z) for s in slots for z in range(cfg.zones)]
    corrupt_at = {file_keys[i] for i in rng.choice(len(file_keys), d.corrupt_lines, replace=False)}
    resend_at = {k for k in file_keys if rng.random() < d.resend_file_rate}
    late_delay: dict[tuple[int, int], int] = {}
    for key in file_keys:
        if rng.random() < d.late_file_rate:
            late_delay[key] = int(rng.integers(1, 4))
    very_late = [file_keys[i] for i in rng.choice(len(file_keys) // 3, d.very_late_files)]
    for key in very_late:
        late_delay[key] = 5

    files: list[dict[str, object]] = []
    for slot in slots:
        ks = _slot_readings(slot)
        slot_start = sim.start_ts + timedelta(hours=slot)
        for z in range(cfg.zones):
            meters = zone_meters[z]
            regs = sim.registers_wh[np.ix_(meters, ks)].tolist()
            stat = sim.status[np.ix_(meters, ks)].tolist()
            volt = sim.voltage[np.ix_(meters, ks)].tolist()
            miss = sim.missing[np.ix_(meters, ks)].tolist()
            dup = sim.duplicate[np.ix_(meters, ks)].tolist()
            naive = sim.naive_ts[np.ix_(meters, ks)].tolist()
            lines: list[str] = []
            for i, m in enumerate(meters.tolist()):
                mid = topo.meter_ids[m]
                v2 = bool(topo.is_v2[m])
                for j, k in enumerate(ks):
                    if miss[i][j]:
                        continue
                    ts = ts_naive[k] if naive[i][j] else ts_aware[k]
                    energy = regs[i][j]
                    kind = sim.special.get((m, k))
                    if kind == NEGATIVE:
                        energy = -(100 + (m * 7 + k) % 900)
                    elif kind in (OFFGRID_SNAP, OFFGRID_REJECT):
                        shift = 1 if kind == OFFGRID_SNAP else 7
                        ts = (sim.reading_ts(k) + timedelta(minutes=shift)).isoformat()
                    if kind:
                        stats[f"{kind}_events"] += 1
                    status = STATUS_NAMES[stat[i][j]]
                    if v2:
                        line = v2_line(
                            mid,
                            ts,
                            energy,
                            bool(topo.unit_kwh[m]),
                            status,
                            volt[i][j],
                            topo.firmware[m],
                        )
                    else:
                        line = v1_line(mid, ts, energy, status)
                        stats["naive_ts_events"] += int(naive[i][j])
                    lines.append(line)
                    if dup[i][j]:
                        lines.append(line)
                        stats["duplicate_events"] += 1
            lines.extend(unknown.get((slot, z), []))
            if (slot, z) in corrupt_at:
                lines.append('{"meter_id":"' + topo.meter_ids[int(meters[0])] + '","ts":"20')
                stats["corrupt_lines"] += 1
            order = rng.permutation(len(lines))  # gateways do not sort: out-of-order within file
            body = ("\n".join(lines[i] for i in order) + "\n").encode("utf-8")

            arrival = slot_start + timedelta(hours=1, minutes=5, seconds=int(rng.integers(600)))
            delay = late_delay.get((slot, z), 0)
            if delay:
                room = (end_arrival_date - arrival.date()).days
                delay = min(delay, room) if delay < 5 else (delay if delay <= room else 0)
            arrival += timedelta(days=delay)
            name = f"gw-{topo.zone_ids[z]}-{slot_start:%Y%m%d-%H}.jsonl"
            files.append(_write(out_dir, name, body, arrival, len(lines), delay))
            if (slot, z) in resend_at:
                re_arrival = arrival + timedelta(hours=2)
                files.append(
                    _write(
                        out_dir,
                        name.replace(".jsonl", "-r1.jsonl"),
                        body,
                        re_arrival,
                        len(lines),
                        delay,
                    )
                )
                stats["resent_files"] += 1
                stats["resent_events"] += len(lines)

    stats["files"] = len(files)
    stats["lines"] = sum(int(f["lines"]) for f in files)  # type: ignore[call-overload]
    stats["late_files"] = sum(1 for f in files if int(f["days_late"]) > 0)  # type: ignore[call-overload]
    stats["missing_readings"] = int(sim.missing.sum())
    manifest = {
        "config": {
            **{
                k: v for k, v in asdict(cfg).items() if k not in ("out_dir", "seeds_dir", "defects")
            },
            "end_date": cfg.end_date.isoformat(),
            "start_date": cfg.start_date.isoformat(),
            "defects": asdict(d),
        },
        "stats": dict(sorted(stats.items())),
        "expected": sim.expected,
        "late_files": [f for f in files if int(f["days_late"]) > 0],  # type: ignore[call-overload]
    }
    (out_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8"
    )
    log.info(
        "landing written out_dir=%s files=%d lines=%d", out_dir, stats["files"], stats["lines"]
    )
    return manifest


def _write(
    out_dir: Path, name: str, body: bytes, arrival: datetime, n_lines: int, days_late: int
) -> dict[str, object]:
    part = out_dir / f"dt={arrival.date().isoformat()}"
    part.mkdir(parents=True, exist_ok=True)
    path = part / name
    path.write_bytes(body)
    epoch = arrival.timestamp()
    os.utime(path, (epoch, epoch))
    return {
        "file": f"{part.name}/{name}",
        "arrival_ts": arrival.isoformat(),
        "lines": n_lines,
        "days_late": days_late,
    }
