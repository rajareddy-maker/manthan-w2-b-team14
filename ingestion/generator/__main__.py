"""CLI: ``python -m ingestion.generator --days 7`` -> data/landing + dbt seeds + manifest."""

from __future__ import annotations

import argparse
import logging
import time
from datetime import date
from pathlib import Path

from ingestion.generator.config import GeneratorConfig
from ingestion.generator.simulate import simulate
from ingestion.generator.topology import build_topology, write_master_seeds
from ingestion.generator.writer import write_landing

log = logging.getLogger("generator")


def run(cfg: GeneratorConfig) -> dict[str, object]:
    """Generate seeds, landing files and the manifest for ``cfg``."""
    t0 = time.perf_counter()
    topo = build_topology(cfg)
    write_master_seeds(topo, cfg.seeds_dir)
    sim = simulate(cfg, topo)
    manifest = write_landing(cfg, topo, sim)
    log.info(
        "generator done start=%s end=%s meters=%d files=%s lines=%s seconds=%.1f",
        cfg.start_date,
        cfg.end_date,
        cfg.meters,
        manifest["stats"]["files"],  # type: ignore[index]
        manifest["stats"]["lines"],  # type: ignore[index]
        time.perf_counter() - t0,
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="GridPulse synthetic smart-meter data generator")
    p.add_argument("--days", type=int)
    p.add_argument("--meters", type=int)
    p.add_argument("--feeders", type=int)
    p.add_argument("--zones", type=int)
    p.add_argument("--seed", type=int)
    p.add_argument("--end-date", type=date.fromisoformat, help="last IST day (default: yesterday)")
    p.add_argument("--out", type=Path, dest="out_dir")
    p.add_argument("--seeds-dir", type=Path)
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    cfg = GeneratorConfig.from_env(
        days=a.days,
        meters=a.meters,
        feeders=a.feeders,
        zones=a.zones,
        seed=a.seed,
        end_date=a.end_date,
        out_dir=a.out_dir,
        seeds_dir=a.seeds_dir,
    )
    run(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
