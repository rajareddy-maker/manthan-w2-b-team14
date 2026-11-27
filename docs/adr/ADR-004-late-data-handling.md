# ADR-004: Late and out-of-order data

- **Status:** Proposed (Sprint 1, 27-Nov-2026) · **Deciders:** Mahendra Umath (PO), Sagar Kalthiya
- **Req IDs:** FR-05, FR-06, FR-17, FR-28, NFR-05, NFR-07

## Context
Gateways send each hour's readings as one file, about 5–15 minutes after the hour.
- **Normal lateness:** the file for 23:00–24:00 arrives just after midnight, so it lands in the next day's partition.
- **Late files:** about 2% arrive 1–3 days late (gateway backlog). Rarely, a file is 5+ days late.
- **Out of order:** events inside a file are not sorted.
- **Re-sends:** gateways re-send whole files, which creates exact duplicates.

The generator reproduces all of these, and `_manifest.json` lists every late file.

## Options
| # | Approach | Verdict |
|---|---|---|
| A | Process only yesterday's arrivals; never revisit | Rejected: late readings would never reach the marts |
| B | Full rebuild of everything daily | Correct, but cost grows with history (90 days ≈ 43M rows) |
| C | **Fixed 3-day lookback, reprocessed idempotently each day, plus an explicit backfill DAG for older data** | **Chosen** |
| D | Streaming with watermarks | Needs Kafka/Spark, which ADR-002 rules out |

## Decision
1. **Daily run for logical date D** (Airflow data interval `D 00:00 → D+1 00:00 IST`, runs about 01:30 IST on D+1):
   1. Load landing `dt ∈ [D−3, D+1]` into bronze. Each partition is replaced atomically, so this is idempotent (ADR-003).
   2. Rebuild silver and gold for **reading dates `[D−3, D]`**: dbt incremental models with `delete+insert` on `reading_date_ist`.
      - The model also reads the day before the window (`D−4`) so the first delta of the window has its previous register.
   3. A reading date is considered final when it leaves the window (D−4).
2. **Duplicates:** the dedup key is (`meter_id`, `reading_ts`). Keep the row with the earliest `ingested_at`, then `file_arrival_ts`, `source_file`, `line_no`. Dropped duplicates are counted per run (ops metric `duplicate_rate`).
3. **Ordering:** the arrival order is never trusted. Deltas use `lag(register) over (partition by meter_id order by reading_ts)`.
4. **Beyond the window:** a file more than 3 days late is still loaded into bronze, because its arrival `dt` is in the window. Its readings fall outside the rebuilt reading dates, so:
   - the run counts them as `late_beyond_window_events` and writes an `ops.alerts` row;
   - the on-call engineer runs `make backfill START=… END=…`. That triggers the `gridpulse_backfill` DAG, which runs the same tasks over the reading-date range.
5. **Idempotency contract:** re-running D, or any backfill range, gives the same row counts and kWh totals. This is tested in TC-IDEM-01.

## Consequences
- Each daily run touches about 5 days of data (~2.4M rows). This is well within the 15-minute SLA on the laptop.
- Marts for the last 3 days can change between runs. The dashboard shows "provisional" for reading dates newer than D−3.
- Billing for month M is final once `M-end + 4 days` has run. Billing analysts are told to bill after the 5th.
