"""CLI entry points: generator (args + GEN_* env), retention."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from ingestion.extractors import retention
from ingestion.generator import __main__ as gen_cli
from ingestion.generator.config import GeneratorConfig


def test_generator_cli_writes_landing_seeds_manifest(tmp_path: Path) -> None:
    out, seeds = tmp_path / "landing", tmp_path / "seeds"
    rc = gen_cli.main(
        [
            "--days", "2", "--meters", "40", "--feeders", "4", "--zones", "2",
            "--seed", "3", "--end-date", "2026-11-20", "--out", str(out), "--seeds-dir", str(seeds),
        ]
    )  # fmt: skip
    assert rc == 0
    manifest = json.loads((out / "_manifest.json").read_text(encoding="utf-8"))
    assert manifest["config"]["meters"] == 40 and manifest["config"]["days"] == 2
    assert (seeds / "meter_master.csv").exists()
    assert list(out.glob("dt=*/gw-*.jsonl"))


def test_config_from_env_and_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in {
        "GEN_METERS": "60",
        "GEN_FEEDERS": "6",
        "GEN_ZONES": "3",
        "GEN_DAYS": "4",
        "GEN_SEED": "9",
        "GEN_END_DATE": "2026-11-20",
    }.items():
        monkeypatch.setenv(k, v)
    cfg = GeneratorConfig.from_env(days=2)
    assert (cfg.meters, cfg.feeders, cfg.zones, cfg.seed, cfg.days) == (60, 6, 3, 9, 2)
    assert cfg.start_date == date(2026, 11, 19) and cfg.n_readings == 2 * 96 + 1


@pytest.mark.parametrize(
    "kwargs", [{"meters": 2, "feeders": 4, "zones": 1}, {"zones": 0}, {"days": 0}]
)
def test_config_rejects_invalid_topology(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        GeneratorConfig(**kwargs)


def test_retention_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    landing, bronze = tmp_path / "landing", tmp_path / "bronze"
    for root in (landing, bronze):
        (root / "dt=2026-01-01").mkdir(parents=True)
        (root / "dt=2026-11-26").mkdir(parents=True)
    monkeypatch.setenv("LANDING_ROOT", str(landing))
    monkeypatch.setenv("BRONZE_ROOT", str(bronze))
    assert retention.main(["--reference", "2026-11-27", "--raw-days", "30"]) == 0
    assert [p.name for p in landing.iterdir()] == ["dt=2026-11-26"]
    assert [p.name for p in bronze.iterdir()] == ["dt=2026-11-26"]
