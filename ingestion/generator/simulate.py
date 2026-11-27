"""Simulate cumulative energy registers per meter and decide every injected defect.

Everything here is numpy-vectorised over a (meters x readings) grid. Reading index ``k`` is the
reading at ``start 00:00 IST + 15 min * k``; it closes the interval ``(k-1, k]``. Index 0 is the
opening reading, so a 7-day window has 7 * 96 + 1 readings per meter.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

import numpy as np

from ingestion.generator.config import (
    INTERVAL_MINUTES,
    INTERVALS_PER_DAY,
    IST,
    REGISTER_MAX_KWH,
    GeneratorConfig,
)
from ingestion.generator.topology import Topology

log = logging.getLogger(__name__)

STATUS_OK, STATUS_ROLLOVER, STATUS_POWER_FAIL, STATUS_ERROR = 0, 1, 2, 3
STATUS_NAMES = ["OK", "ROLLOVER", "POWER_FAIL", "ERROR"]
REGISTER_MAX_WH = REGISTER_MAX_KWH * 1000

# Relative load by hour of day (Indian residential profile: morning + evening peaks).
HOURLY_SHAPE = np.array(
    [0.55, 0.5, 0.45, 0.45, 0.5, 0.65, 0.95, 1.3, 1.4, 1.15, 0.95, 0.9]
    + [0.9, 0.9, 0.95, 0.95, 1.0, 1.15, 1.6, 1.85, 1.8, 1.55, 1.15, 0.8]
)

# Special single-cell defects (m, k) -> kind
NEGATIVE, OFFGRID_SNAP, OFFGRID_REJECT = "negative", "offgrid_snap", "offgrid_reject"


@dataclass
class Simulation:
    """Result of the simulation: registers, masks and the ground-truth manifest."""

    start_ts: datetime
    registers_wh: np.ndarray  # int64 (M, K) register as reported
    status: np.ndarray  # int8 (M, K)
    voltage: np.ndarray  # float (M, K), only used for v2 meters
    missing: np.ndarray  # bool (M, K) reading not sent
    duplicate: np.ndarray  # bool (M, K) reading sent twice in the same file
    naive_ts: np.ndarray  # bool (M, K) timestamp without offset
    special: dict[tuple[int, int], str] = field(default_factory=dict)
    expected: dict[str, object] = field(default_factory=dict)

    def reading_ts(self, k: int) -> datetime:
        return self.start_ts + timedelta(minutes=INTERVAL_MINUTES * k)


def _iso(ts: datetime) -> str:
    return ts.isoformat()


def _pick(pool: list[int], n: int) -> list[int]:
    """Take up to n items from the front of pool (already shuffled), removing them."""
    taken = pool[:n]
    del pool[:n]
    return [int(x) for x in taken]


def simulate(cfg: GeneratorConfig, topo: Topology) -> Simulation:
    """Build registers and defect masks for every meter and reading."""
    rng = np.random.default_rng(cfg.seed + 1)
    d = cfg.defects
    n_m, n_k = topo.n_meters, cfg.n_readings
    start_ts = datetime.combine(cfg.start_date, time(0, 0), tzinfo=IST)

    # --- consumption per interval (Wh) -------------------------------------------------------
    k_idx = np.arange(n_k)
    hour_of_interval = ((np.maximum(k_idx - 1, 0)) % INTERVALS_PER_DAY) // 4
    shape = HOURLY_SHAPE[hour_of_interval]
    base_kw = np.clip(rng.lognormal(np.log(0.45), 0.5, n_m), 0.08, 4.0)
    noise = rng.lognormal(0.0, 0.25, (n_m, n_k))
    wh = np.rint(base_kw[:, None] * shape[None, :] * noise * 250.0).astype(np.int64)
    wh[:, 0] = 0

    status = np.zeros((n_m, n_k), dtype=np.int8)
    missing = rng.random((n_m, n_k)) < d.missing_reading_rate
    missing[:, 0] = False
    expected: dict[str, object] = {}

    # --- crafted meters: keep outage feeders separate from per-meter anomalies --------------
    outage_feeder = int(rng.integers(cfg.feeders))
    control_feeder = (outage_feeder + 1) % cfg.feeders
    excluded = np.isin(topo.meter_feeder, [outage_feeder, control_feeder])
    pool = [int(m) for m in rng.permutation(np.flatnonzero(~excluded))]
    crafted_meters: list[int] = []

    # Spike: two consecutive intervals at 12x load, late in the window (>= 96 history points).
    spikes = []
    if cfg.days >= 2:
        spike_day = max(1, cfg.days - 2)
        k0 = spike_day * INTERVALS_PER_DAY + 14 * 4 + 1
        for m in _pick(pool, d.spike_meters):
            wh[m, k0 : k0 + 2] = np.rint(base_kw[m] * 12 * 250).astype(np.int64) + 500
            missing[m, k0 - 1 : k0 + 3] = False
            crafted_meters.append(m)
            spikes.append(
                {
                    "meter_id": topo.meter_ids[m],
                    "reading_ts": [
                        _iso(start_ts + timedelta(minutes=15 * k)) for k in (k0, k0 + 1)
                    ],
                }
            )
    expected["spike"] = spikes

    # Tamper: 60 h of zero consumption (>= 192 intervals) on distinct, otherwise-normal feeders.
    tampers = []
    zero_len = 240
    if n_k - 1 >= INTERVALS_PER_DAY + zero_len:
        k0 = INTERVALS_PER_DAY + 1
        used_feeders: set[int] = set()
        for m in list(pool):
            if len(tampers) >= d.tamper_meters:
                break
            if int(topo.meter_feeder[m]) in used_feeders:
                continue
            pool.remove(m)
            crafted_meters.append(m)
            used_feeders.add(int(topo.meter_feeder[m]))
            wh[m, k0 : k0 + zero_len] = 0
            tampers.append(
                {
                    "meter_id": topo.meter_ids[m],
                    "feeder_id": topo.feeder_ids[topo.meter_feeder[m]],
                    "zero_from_reading_ts": _iso(start_ts + timedelta(minutes=15 * k0)),
                    "zero_to_reading_ts": _iso(
                        start_ts + timedelta(minutes=15 * (k0 + zero_len - 1))
                    ),
                    "zero_intervals": zero_len,
                }
            )
    expected["tamper"] = tampers

    # Outage: >= 30% of one feeder's meters miss 8 consecutive readings; control feeder 20% x 4.
    outages = []
    if cfg.days >= 3:
        for feeder, share, length, kind in (
            (outage_feeder, 0.40, 8, "outage"),
            (control_feeder, 0.20, 4, "control"),
        ):
            k0 = 2 * INTERVALS_PER_DAY + 18 * 4 + 1 + (0 if kind == "outage" else 16)
            on_feeder = topo.meters_on_feeder(feeder)
            n_hit = (
                int(np.ceil(share * len(on_feeder)))
                if kind == "outage"
                else int(np.floor(share * len(on_feeder)))
            )
            hit = rng.choice(on_feeder, n_hit, replace=False)
            missing[np.ix_(hit, np.arange(k0, k0 + length))] = True
            wh[np.ix_(hit, np.arange(k0, k0 + length + 1))] = 0  # no power -> no energy
            status[hit, k0 + length] = STATUS_POWER_FAIL
            outages.append(
                {
                    "kind": kind,
                    "feeder_id": topo.feeder_ids[feeder],
                    "from_reading_ts": _iso(start_ts + timedelta(minutes=15 * k0)),
                    "to_reading_ts": _iso(start_ts + timedelta(minutes=15 * (k0 + length - 1))),
                    "missing_intervals": length,
                    "meters_affected": n_hit,
                    "feeder_meters": len(on_feeder),
                }
            )
    expected["outage"] = [o for o in outages if o["kind"] == "outage"]
    expected["outage_negative_control"] = [o for o in outages if o["kind"] == "control"]

    # --- registers ---------------------------------------------------------------------------
    initial = rng.integers(1_000_000, 90_000_000, n_m, dtype=np.int64)
    rollover_meters = _pick(pool, d.rollover_meters)
    crafted_meters.extend(rollover_meters)
    for m in rollover_meters:
        initial[m] = REGISTER_MAX_WH - int(rng.integers(3_000, 8_000))
    raw = initial[:, None] + np.cumsum(wh, axis=1)
    registers = raw % REGISTER_MAX_WH
    wrapped = np.zeros_like(missing)
    wrapped[:, 1:] = registers[:, 1:] < registers[:, :-1]
    status[wrapped] = STATUS_ROLLOVER
    missing[wrapped] = False  # the wrap reading itself is always sent (keeps the flag visible)
    # a wrap that happens during a missing reading must be flagged on the next sent reading
    expected["rollover"] = [topo.meter_ids[m] for m in rollover_meters]

    resets = []
    for m in _pick(pool, d.register_reset_meters):
        crafted_meters.append(m)
        k_r = int(rng.integers(INTERVALS_PER_DAY // 2, n_k - 1))
        registers[m, k_r:] = registers[m, k_r:] - registers[m, k_r] + 100
        missing[m, k_r] = False
        resets.append(
            {
                "meter_id": topo.meter_ids[m],
                "reading_ts": _iso(start_ts + timedelta(minutes=15 * k_r)),
            }
        )
    expected["register_decrease"] = resets

    low = []
    for m in _pick(pool, d.low_completeness_meters):
        crafted_meters.append(m)
        day = int(rng.integers(cfg.days))
        ks = rng.choice(np.arange(day * 96 + 1, day * 96 + 97), 15, replace=False)
        missing[m, ks] = True
        low.append(
            {
                "meter_id": topo.meter_ids[m],
                "date_ist": (cfg.start_date + timedelta(days=day)).isoformat(),
            }
        )
    expected["low_completeness"] = low

    # --- other defects -----------------------------------------------------------------------
    err = (rng.random((n_m, n_k)) < d.error_status_rate) & (status == STATUS_OK)
    status[err] = STATUS_ERROR
    duplicate = (rng.random((n_m, n_k)) < d.duplicate_event_rate) & ~missing
    naive = (rng.random((n_m, n_k)) < d.naive_ts_rate) & ~topo.is_v2[:, None]
    voltage = np.round(230.0 + rng.normal(0.0, 4.0, (n_m, n_k)), 1)

    special: dict[tuple[int, int], str] = {}
    sendable = np.flatnonzero(~missing.ravel() & (status.ravel() == STATUS_OK))
    crafted = np.zeros(n_m, dtype=bool)
    crafted[crafted_meters] = True
    plain = sendable[~crafted[sendable // n_k]]
    n_special = d.negative_events + d.offgrid_snappable_events + d.offgrid_reject_events
    cells = rng.choice(plain, min(n_special, len(plain)), replace=False)
    kinds = (
        [NEGATIVE] * d.negative_events
        + [OFFGRID_SNAP] * d.offgrid_snappable_events
        + [OFFGRID_REJECT] * d.offgrid_reject_events
    )
    for cell, kind in zip(cells, kinds, strict=False):
        m, k = divmod(int(cell), n_k)
        if k == 0:
            continue
        special[(m, k)] = kind
        duplicate[m, k] = False

    log.info(
        "simulated meters=%d readings=%d missing=%d duplicates=%d specials=%d",
        n_m,
        n_k,
        int(missing.sum()),
        int(duplicate.sum()),
        len(special),
    )
    return Simulation(
        start_ts=start_ts,
        registers_wh=registers,
        status=status,
        voltage=voltage,
        missing=missing,
        duplicate=duplicate,
        naive_ts=naive,
        special=special,
        expected=expected,
    )
