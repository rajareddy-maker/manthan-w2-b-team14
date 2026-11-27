"""Run a Great Expectations (GX Core 1.x) checkpoint for a GridPulse data layer.

Sprint 0 ships the ``sample`` suite (validates tests/fixtures/sample_readings.csv) to prove the
GX toolchain works. Layer suites (bronze/silver/gold) are added in US-14.

Usage:
    python data_quality/gx/run_checkpoint.py --suite sample
Exit code 0 when every expectation passes, 1 otherwise.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import great_expectations as gx
import pandas as pd

LOG = logging.getLogger("gx_checkpoint")
ROOT = Path(__file__).resolve().parents[2]


def sample_suite() -> tuple[pd.DataFrame, list[gx.expectations.Expectation]]:
    """Fixture readings plus the PRD DQ rules that apply to a single reading."""
    df = pd.read_csv(ROOT / "tests/fixtures/sample_readings.csv")
    expectations = [
        gx.expectations.ExpectColumnValuesToNotBeNull(column="meter_id"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="ts"),
        gx.expectations.ExpectColumnValuesToBeBetween(column="energy_wh", min_value=0),
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="status", value_set=["OK", "ROLLOVER", "POWER_FAIL", "ERROR"]
        ),
        gx.expectations.ExpectCompoundColumnsToBeUnique(column_list=["meter_id", "ts"]),
    ]
    return df, expectations


SUITES = {"sample": sample_suite}


def run(suite_name: str) -> bool:
    """Build an ephemeral GX context, run the checkpoint and log a summary."""
    df, expectations = SUITES[suite_name]()
    context = gx.get_context(mode="ephemeral")
    batch_def = (
        context.data_sources.add_pandas(f"{suite_name}_src")
        .add_dataframe_asset(f"{suite_name}_asset")
        .add_batch_definition_whole_dataframe(f"{suite_name}_batch")
    )
    suite = context.suites.add(gx.ExpectationSuite(name=f"{suite_name}_suite"))
    for exp in expectations:
        suite.add_expectation(exp)
    vd = context.validation_definitions.add(
        gx.ValidationDefinition(name=f"{suite_name}_vd", data=batch_def, suite=suite)
    )
    checkpoint = context.checkpoints.add(
        gx.Checkpoint(name=f"{suite_name}_checkpoint", validation_definitions=[vd])
    )
    result = checkpoint.run(batch_parameters={"dataframe": df})
    stats = next(iter(result.run_results.values())).statistics
    LOG.info(
        "suite=%s success=%s evaluated=%s successful=%s rows=%d",
        suite_name,
        result.success,
        stats["evaluated_expectations"],
        stats["successful_expectations"],
        len(df),
    )
    return bool(result.success)


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    for noisy in ("great_expectations", "py.warnings"):
        logging.getLogger(noisy).setLevel(logging.ERROR)
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=sorted(SUITES), default="sample")
    ok = run(parser.parse_args().suite)
    print(f"GX checkpoint {'PASSED' if ok else 'FAILED'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
