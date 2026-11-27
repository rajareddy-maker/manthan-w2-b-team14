"""Configuration for the synthetic smart-meter telemetry generator (US-07).

All values can be overridden from the CLI; defaults match the PRD scale
(5,000 meters / 20 feeders / 6 zones, 15-minute readings, 7-day demo window).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30), name="IST")
INTERVAL_MINUTES = 15
INTERVALS_PER_DAY = 96
REGISTER_MAX_KWH = 100_000  # register wraps to 0 at this value (5-digit kWh register)


def yesterday_ist() -> date:
    """Return yesterday's date in Asia/Kolkata."""
    return (datetime.now(IST) - timedelta(days=1)).date()


@dataclass(frozen=True)
class DefectConfig:
    """Rates and counts of injected data defects and crafted anomalies."""

    duplicate_event_rate: float = 0.003  # same event twice in one file
    resend_file_rate: float = 0.01  # gateway re-sends a whole hourly file
    late_file_rate: float = 0.02  # file arrives 1-3 days late
    very_late_files: int = 1  # file arrives 5 days late (backfill path)
    missing_reading_rate: float = 0.005  # random single missing readings
    naive_ts_rate: float = 0.01  # v1 timestamps without offset (= IST)
    error_status_rate: float = 0.0005  # status ERROR with a valid value
    negative_events: int = 25
    unknown_meters: int = 15
    offgrid_snappable_events: int = 40  # +1 min -> snapped to grid
    offgrid_reject_events: int = 20  # +7 min -> quarantined
    corrupt_lines: int = 3
    rollover_meters: int = 5
    register_reset_meters: int = 3  # register decrease without ROLLOVER
    spike_meters: int = 5
    tamper_meters: int = 3
    low_completeness_meters: int = 10


@dataclass(frozen=True)
class GeneratorConfig:
    """Top-level generator settings."""

    meters: int = 5000
    feeders: int = 20
    zones: int = 6
    days: int = 7
    end_date: date = field(default_factory=yesterday_ist)
    seed: int = 42
    v2_share: float = 0.40
    v2_kwh_share: float = 0.30
    out_dir: Path = Path("data/landing")
    seeds_dir: Path = Path("dbt_project/seeds")
    defects: DefectConfig = field(default_factory=DefectConfig)

    def __post_init__(self) -> None:
        if self.meters < self.feeders or self.feeders < self.zones or self.zones < 1:
            raise ValueError("need meters >= feeders >= zones >= 1")
        if self.days < 1:
            raise ValueError("days must be >= 1")

    @property
    def start_date(self) -> date:
        """First IST day whose intervals are generated."""
        return self.end_date - timedelta(days=self.days - 1)

    @property
    def n_readings(self) -> int:
        """Readings per meter: one opening reading at start 00:00 plus 96 per day."""
        return self.days * INTERVALS_PER_DAY + 1

    @classmethod
    def from_env(cls, **overrides: object) -> GeneratorConfig:
        """Build a config from GEN_* environment variables, then apply overrides."""
        env: dict[str, object] = {}
        for name, cast in (("meters", int), ("feeders", int), ("zones", int), ("days", int)):
            if f"GEN_{name.upper()}" in os.environ:
                env[name] = cast(os.environ[f"GEN_{name.upper()}"])
        if "GEN_SEED" in os.environ:
            env["seed"] = int(os.environ["GEN_SEED"])
        if "GEN_END_DATE" in os.environ:
            env["end_date"] = date.fromisoformat(os.environ["GEN_END_DATE"])
        env.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**env)  # type: ignore[arg-type]
