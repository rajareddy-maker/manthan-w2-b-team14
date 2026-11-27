"""Retention (ADR-003): drop landing + bronze ``dt=`` partitions older than N days. Logged."""

from __future__ import annotations

import argparse
import logging
import os
import shutil
from datetime import date, timedelta
from pathlib import Path

log = logging.getLogger("retention")


def expired_partitions(root: Path, reference: date, keep_days: int) -> list[Path]:
    """``dt=YYYY-MM-DD`` directories under root strictly older than reference - keep_days."""
    cutoff = reference - timedelta(days=keep_days)
    out = []
    for p in sorted(root.glob("dt=*")):
        try:
            if p.is_dir() and date.fromisoformat(p.name.removeprefix("dt=")) < cutoff:
                out.append(p)
        except ValueError:
            continue
    return out


def apply_retention(roots: list[Path], reference: date, keep_days: int) -> int:
    """Delete expired partitions under every root. Returns the number removed."""
    removed = 0
    for root in roots:
        for p in expired_partitions(root, reference, keep_days):
            shutil.rmtree(p)
            removed += 1
            log.info("retention removed partition=%s keep_days=%d", p, keep_days)
    log.info("retention done reference=%s keep_days=%d removed=%d", reference, keep_days, removed)
    return removed


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference", type=date.fromisoformat, default=date.today())
    p.add_argument("--raw-days", type=int, default=int(os.environ.get("RAW_RETENTION_DAYS", "30")))
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    roots = [
        Path(os.environ.get("LANDING_ROOT", "data/landing")),
        Path(os.environ.get("BRONZE_ROOT", "data/lake/bronze")),
    ]
    apply_retention(roots, a.reference, a.raw_days)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
