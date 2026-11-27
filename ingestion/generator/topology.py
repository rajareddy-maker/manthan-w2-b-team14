"""Network topology and meter master for the generator: zones -> feeders -> meters."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from faker import Faker

from ingestion.generator.config import REGISTER_MAX_KWH, GeneratorConfig

ZONE_NAMES = [
    "Vijay Nagar",
    "Rajwada",
    "Palasia",
    "Bhawarkua",
    "Sanwer Road",
    "Rau",
    "Mhow",
    "Pithampur",
]
FIRMWARE_VERSIONS = ["2.1.0", "2.3.1", "2.4.0"]


@dataclass(frozen=True)
class Topology:
    """Static description of the simulated network (index-aligned arrays per meter)."""

    zone_ids: list[str]
    zone_names: list[str]
    feeder_ids: list[str]
    feeder_zone: np.ndarray  # feeder index -> zone index
    meter_ids: list[str]
    meter_feeder: np.ndarray  # meter index -> feeder index
    meter_zone: np.ndarray  # meter index -> zone index
    is_v2: np.ndarray  # bool per meter
    unit_kwh: np.ndarray  # bool per meter (v2 only)
    firmware: list[str]
    install_dates: list[str]

    @property
    def n_meters(self) -> int:
        return len(self.meter_ids)

    def meters_in_zone(self, zone: int) -> np.ndarray:
        return np.flatnonzero(self.meter_zone == zone)

    def meters_on_feeder(self, feeder: int) -> np.ndarray:
        return np.flatnonzero(self.meter_feeder == feeder)


def build_topology(cfg: GeneratorConfig) -> Topology:
    """Deterministically build zones, feeders and meters from the config seed."""
    rng = np.random.default_rng(cfg.seed)
    fake = Faker("en_IN")
    Faker.seed(cfg.seed)

    zone_ids = [f"Z{z + 1:02d}" for z in range(cfg.zones)]
    zone_names = [ZONE_NAMES[z % len(ZONE_NAMES)] for z in range(cfg.zones)]
    feeder_ids = [f"FDR-{f + 1:02d}" for f in range(cfg.feeders)]
    feeder_zone = np.arange(cfg.feeders) % cfg.zones

    meter_ids = [f"MTR-{m + 1:05d}" for m in range(cfg.meters)]
    meter_feeder = np.arange(cfg.meters) % cfg.feeders
    meter_zone = feeder_zone[meter_feeder]
    is_v2 = rng.random(cfg.meters) < cfg.v2_share
    unit_kwh = is_v2 & (rng.random(cfg.meters) < cfg.v2_kwh_share)
    fw_idx = rng.integers(0, len(FIRMWARE_VERSIONS), cfg.meters)
    firmware = [FIRMWARE_VERSIONS[i] if v2 else "" for i, v2 in zip(fw_idx, is_v2, strict=True)]
    install_dates = [
        fake.date_between(start_date="-8y", end_date="-1y").isoformat() for _ in meter_ids
    ]
    return Topology(
        zone_ids=zone_ids,
        zone_names=zone_names,
        feeder_ids=feeder_ids,
        feeder_zone=feeder_zone,
        meter_ids=meter_ids,
        meter_feeder=meter_feeder,
        meter_zone=meter_zone,
        is_v2=is_v2,
        unit_kwh=unit_kwh,
        firmware=firmware,
        install_dates=install_dates,
    )


def write_master_seeds(topo: Topology, seeds_dir: Path) -> tuple[Path, Path]:
    """Write meter_master.csv and feeder_zone.csv (dbt seeds). Returns both paths."""
    seeds_dir.mkdir(parents=True, exist_ok=True)
    meter_path = seeds_dir / "meter_master.csv"
    with meter_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(
            [
                "meter_id",
                "feeder_id",
                "zone_id",
                "schema_version",
                "unit",
                "install_date",
                "register_max_kwh",
            ]
        )
        for m, meter_id in enumerate(topo.meter_ids):
            w.writerow(
                [
                    meter_id,
                    topo.feeder_ids[topo.meter_feeder[m]],
                    topo.zone_ids[topo.meter_zone[m]],
                    2 if topo.is_v2[m] else 1,
                    "kWh" if topo.unit_kwh[m] else "Wh",
                    topo.install_dates[m],
                    REGISTER_MAX_KWH,
                ]
            )
    feeder_path = seeds_dir / "feeder_zone.csv"
    with feeder_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["feeder_id", "zone_id", "zone_name"])
        for f, feeder_id in enumerate(topo.feeder_ids):
            z = topo.feeder_zone[f]
            w.writerow([feeder_id, topo.zone_ids[z], topo.zone_names[z]])
    return meter_path, feeder_path
