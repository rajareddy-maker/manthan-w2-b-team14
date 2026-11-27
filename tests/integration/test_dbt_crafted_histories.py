"""Crafted meter histories through the real pipeline (landing -> bronze -> dbt build).

Covers the acceptance criteria of US-10 (staging), US-11 (grid/gaps/deltas), US-12 (marts) and
US-13 (anomalies incl. negative controls). Each meter is built to exercise exactly one rule:

    F1 (Z01): A1 spike · A2 negative / +1 min / +7 min · A3 triplicate · A4 naive ts + 3 gaps ·
              A5 flat register (tamper)
    F2 (Z01): B1 rollover · B2 register reset · B3 + B4 miss the same 2 slots (50% -> outage)
    F3 (Z02): C1..C4 all flat (whole-feeder zero -> must NOT be tamper)
    F4 (Z02): U1 v1 Wh, U2 v2 kWh, U3 v2 Wh with identical registers · D1 misses 15 slots on day 2
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ingestion.generator.writer import v1_line, v2_line
from tests.integration.dbt_harness import connect, copy_dbt_project, run_pipeline, write_seeds

pytestmark = pytest.mark.dbt

IST = timezone(timedelta(hours=5, minutes=30))
START = datetime(2026, 11, 20, tzinfo=IST)
N = 3 * 96  # readings k = 0..N
MAX_WH = 100_000 * 1000


def ts(k: int, minutes: int = 0) -> datetime:
    return START + timedelta(minutes=15 * k + minutes)


def normal_wh(k: int, seed: int) -> int:
    return 100 + (k * 7 + seed) % 13


def registers(start_wh: int, wh) -> list[int]:  # noqa: ANN001 - callable
    regs = [start_wh]
    for k in range(1, N + 1):
        regs.append(regs[-1] + wh(k))
    return regs


SPIKE_K, GAP_KS, DUP_K = 250, (101, 102, 103), 30
NEG_K, SNAP_K, REJECT_K = 40, 60, 70
RESET_K, OUTAGE_KS = 150, (200, 201)
LOW_KS = tuple(range(97, 112))  # 15 readings closing day-2 intervals

FEEDERS = {"F1": "Z01", "F2": "Z01", "F3": "Z02", "F4": "Z02"}
METERS = {
    "A1": ("F1", 1, "Wh"),
    "A2": ("F1", 2, "Wh"),
    "A3": ("F1", 1, "Wh"),
    "A4": ("F1", 1, "Wh"),
    "A5": ("F1", 1, "Wh"),
    "B1": ("F2", 1, "Wh"),
    "B2": ("F2", 1, "Wh"),
    "B3": ("F2", 1, "Wh"),
    "B4": ("F2", 1, "Wh"),
    "C1": ("F3", 1, "Wh"),
    "C2": ("F3", 1, "Wh"),
    "C3": ("F3", 1, "Wh"),
    "C4": ("F3", 1, "Wh"),
    "U1": ("F4", 1, "Wh"),
    "U2": ("F4", 2, "kWh"),
    "U3": ("F4", 2, "Wh"),
    "D1": ("F4", 1, "Wh"),
}


def build_series() -> dict[str, dict]:
    """Per meter: registers (Wh), status per k and the set of k that are not sent."""
    s: dict[str, dict] = {}
    for i, m in enumerate(METERS):
        s[m] = {
            "regs": registers(1_000_000 + i * 10_000, lambda k, i=i: normal_wh(k, i)),
            "status": {},
            "skip": set(),
        }
    s["A1"]["regs"] = registers(
        2_000_000, lambda k: 2000 if k == SPIKE_K else normal_wh(k, 1)
    )  # ~19x
    s["A5"]["regs"] = [3_000_000] * (N + 1)
    for c in ("C1", "C2", "C3", "C4"):
        s[c]["regs"] = [4_000_000] * (N + 1)
    raw = registers(MAX_WH - 1_000, lambda k: normal_wh(k, 5))
    s["B1"]["regs"] = [r % MAX_WH for r in raw]
    s["B1"]["wrap_k"] = next(k for k in range(1, N + 1) if raw[k] >= MAX_WH)
    s["B1"]["status"][s["B1"]["wrap_k"]] = "ROLLOVER"
    regs = s["B2"]["regs"]
    s["B2"]["regs"] = regs[:RESET_K] + [r - regs[RESET_K] + 500 for r in regs[RESET_K:]]
    shared = registers(1_500_000, lambda k: normal_wh(k, 9))
    for u in ("U1", "U2", "U3"):
        s[u]["regs"] = shared
    s["A4"]["skip"] |= set(GAP_KS)
    s["B3"]["skip"] |= set(OUTAGE_KS)
    s["B4"]["skip"] |= set(OUTAGE_KS)
    s["D1"]["skip"] |= set(LOW_KS)
    return s


def landing_lines(series: dict[str, dict]) -> tuple[dict[tuple[str, str], list[str]], list[str]]:
    """Return {(zone, yyyymmdd): lines} and the extra lines of a gateway re-send."""
    files: dict[tuple[str, str], list[str]] = {}
    resend: list[str] = []
    for m, (feeder, version, unit) in METERS.items():
        zone = FEEDERS[feeder]
        sr = series[m]
        for k in range(N + 1):
            if k in sr["skip"]:
                continue
            t, energy = ts(k), sr["regs"][k]
            if m == "A2" and k == NEG_K:
                energy = -50
            if m == "A2" and k in (SNAP_K, REJECT_K):
                t = ts(k, 1 if k == SNAP_K else 7)
            stamp = t.strftime("%Y-%m-%dT%H:%M:%S") if m == "A4" else t.isoformat()  # naive=IST
            status = sr["status"].get(k, "OK")
            if version == 1:
                line = v1_line(m, stamp, energy, status)
            else:
                line = v2_line(m, stamp, energy, unit == "kWh", status, 230.0, "2.3.1")
            day = (ts(k) - timedelta(minutes=15)).strftime("%Y%m%d")
            files.setdefault((zone, day), []).append(line)
            if m == "A3" and k == DUP_K:
                resend += [line, line]
    files[("Z01", START.strftime("%Y%m%d"))] += [
        v1_line("X99", ts(5).isoformat(), 10, "OK"),
        v1_line("X99", ts(6).isoformat(), 20, "OK"),
        '{"meter_id":"A1","ts":"2026-',
    ]
    return files, resend


@pytest.fixture(scope="module")
def db(tmp_path_factory: pytest.TempPathFactory):
    work = tmp_path_factory.mktemp("crafted")
    project = copy_dbt_project(work)
    write_seeds(
        project,
        [
            {
                "meter_id": m,
                "feeder_id": f,
                "zone_id": FEEDERS[f],
                "schema_version": v,
                "unit": u,
                "install_date": "2020-01-01",
                "register_max_kwh": 100000,
            }
            for m, (f, v, u) in METERS.items()
        ],
        [{"feeder_id": f, "zone_id": z, "zone_name": f"Zone {z}"} for f, z in FEEDERS.items()],
    )
    series = build_series()
    files, resend = landing_lines(series)
    landing = work / "landing"
    for (zone, day), lines in sorted(files.items(), reverse=True):  # write newest first
        part = landing / f"dt={day[:4]}-{day[4:6]}-{day[6:]}"
        part.mkdir(parents=True, exist_ok=True)
        (part / f"gw-{zone}-{day}-00.jsonl").write_text(
            "\n".join(reversed(lines)) + "\n", encoding="utf-8", newline="\n"
        )
    (landing / "dt=2026-11-21" / "gw-Z01-20261120-00-r1.jsonl").write_text(
        "\n".join(resend) + "\n", encoding="utf-8", newline="\n"
    )
    con = connect(run_pipeline(work, project, landing))
    yield con, series
    con.close()


def q(con, sql: str, *params):  # noqa: ANN001, ANN201
    return con.execute(sql, params).fetchall()


# ---------------------------------------------------------------- US-10 staging
def test_us10_ac1_units_converge_to_same_kwh(db) -> None:  # noqa: ANN001
    con, series = db
    rows = q(
        con,
        "select meter_id, register_kwh from main_staging.stg_meter__readings "
        "where meter_id in ('U1','U2','U3') and reading_ts = ? order by 1",
        ts(5),
    )
    expected = (Decimal(series["U1"]["regs"][5]) / 1000).quantize(Decimal("0.0001"))
    assert rows == [("U1", expected), ("U2", expected), ("U3", expected)]


def test_us10_ac2_triplicate_kept_once(db) -> None:  # noqa: ANN001
    con, _ = db
    ranks = q(
        con,
        "select dup_rank from main_staging.stg_meter__readings_validated "
        "where meter_id = 'A3' and reading_ts = ? order by 1",
        ts(DUP_K),
    )
    assert ranks == [(1,), (2,), (3,)]
    assert q(
        con,
        "select count(*) from main_staging.stg_meter__readings "
        "where meter_id = 'A3' and reading_ts = ?",
        ts(DUP_K),
    ) == [(1,)]


def test_us10_ac3_out_of_order_files_give_ordered_deltas(db) -> None:  # noqa: ANN001
    con, _ = db
    flagged = q(
        con,
        "select distinct meter_id from main_intermediate.int_meter_intervals "
        "where dq_flag = 'register_decrease'",
    )
    assert flagged == [("B2",)]


def test_quarantine_reasons_and_snapping(db) -> None:  # noqa: ANN001
    con, _ = db
    reasons = dict(
        q(con, "select reject_reason, count(*) from main_staging.stg_meter__quarantine group by 1")
    )
    assert reasons == {
        "negative_energy": 1,
        "off_grid": 1,
        "unknown_meter": 2,
        "invalid_json": 1,
    }
    assert q(
        con,
        "select snap_seconds from main_staging.stg_meter__readings "
        "where meter_id = 'A2' and reading_ts = ?",
        ts(SNAP_K),
    ) == [(60,)]


def test_naive_timestamps_are_ist(db) -> None:  # noqa: ANN001
    con, _ = db
    n, first = q(
        con,
        "select count(*), min(reading_ts) from main_staging.stg_meter__readings "
        "where meter_id = 'A4'",
    )[0]
    assert n == N + 1 - len(GAP_KS)
    assert first == START


# ---------------------------------------------------------------- US-11 grid / deltas
def test_us11_ac1_gaps_marked_and_delta_kept_once(db) -> None:  # noqa: ANN001
    con, series = db
    rows = q(
        con,
        "select interval_start_ts, is_gap, gap_intervals, delta_kwh "
        "from main_intermediate.int_meter_intervals where meter_id = 'A4' "
        "and interval_start_ts between ? and ? order by 1",
        ts(GAP_KS[0] - 1),
        ts(GAP_KS[-1]),
    )
    assert [r[1] for r in rows] == [True, True, True, False]
    regs = series["A4"]["regs"]
    k_close = GAP_KS[-1] + 1
    assert rows[-1][2] == 3
    assert rows[-1][3] == Decimal(regs[k_close] - regs[GAP_KS[0] - 1]) / 1000


def test_grid_is_complete(db) -> None:  # noqa: ANN001
    con, _ = db
    assert q(con, "select count(*) from main_intermediate.int_meter_intervals") == [
        (len(METERS) * N,)
    ]


def test_us11_ac2_rollover_and_unflagged_decrease(db) -> None:  # noqa: ANN001
    con, series = db
    k = series["B1"]["wrap_k"]
    raw = [series["B1"]["regs"][k - 1], series["B1"]["regs"][k]]
    delta, flag = q(
        con,
        "select delta_kwh, dq_flag from main_intermediate.int_meter_intervals "
        "where meter_id = 'B1' and interval_start_ts = ?",
        ts(k - 1),
    )[0]
    assert delta == Decimal(MAX_WH - raw[0] + raw[1]) / 1000 and flag is None
    delta, flag = q(
        con,
        "select delta_kwh, dq_flag from main_intermediate.int_meter_intervals "
        "where meter_id = 'B2' and interval_start_ts = ?",
        ts(RESET_K - 1),
    )[0]
    assert delta is None and flag == "register_decrease"


# ---------------------------------------------------------------- US-12 marts
def test_us12_quality_flags(db) -> None:  # noqa: ANN001
    con, _ = db
    low = q(
        con,
        "select meter_id, interval_date_ist::varchar from main_marts.fct_consumption_daily "
        "where quality_flag = 'LOW_COMPLETENESS'",
    )
    assert low == [("D1", "2026-11-21")]
    flags = dict(q(con, "select meter_id, quality_flag from main_marts.mart_billing_monthly"))
    assert flags["B2"] == "REGISTER_DECREASE" and flags["A1"] == "OK"
    assert q(
        con,
        "select sum(consumption_kwh) from main_marts.mart_feeder_consumption_daily "
        "where feeder_id = 'F3'",
    ) == [(Decimal("0"),)]


def test_us12_ac1_billing_equals_register_span(db) -> None:  # noqa: ANN001
    con, series = db
    regs = series["U1"]["regs"]
    (billed,) = q(
        con, "select billed_kwh from main_marts.mart_billing_monthly where meter_id = 'U1'"
    )[0]
    assert billed == Decimal(regs[N] - regs[0]) / 1000


# ---------------------------------------------------------------- US-13 anomalies
def anomalies(con, kind: str) -> list[tuple]:  # noqa: ANN001
    return q(
        con,
        "select coalesce(meter_id, feeder_id), start_ts, intervals from main_marts.mart_anomalies "
        "where anomaly_type = ? order by 1",
        kind,
    )


def test_us13_ac1_spike_only_on_crafted_meter(db) -> None:  # noqa: ANN001
    con, _ = db
    assert anomalies(con, "SPIKE") == [("A1", ts(SPIKE_K - 1), 1)]


def test_us13_ac2_tamper_only_when_peers_active(db) -> None:  # noqa: ANN001
    con, _ = db
    # A5 is flat while F1 peers consume; C1..C4 are flat together (whole feeder) -> not tamper.
    assert anomalies(con, "TAMPER") == [("A5", START, N)]


def test_us13_ac3_outage_needs_30pct_of_feeder(db) -> None:  # noqa: ANN001
    con, _ = db
    # F2: 2 of 4 meters miss 2 slots (50%) -> outage. F1 (1 of 5 = 20%) and F4 (25%) -> none.
    assert anomalies(con, "OUTAGE") == [("F2", ts(OUTAGE_KS[0] - 1), 2)]
